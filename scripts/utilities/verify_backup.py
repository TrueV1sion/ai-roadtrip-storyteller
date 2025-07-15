#!/usr/bin/env python3
"""
TASK-006: Verify Cloud SQL backups are successful and test restoration

This script:
1. Lists recent backups
2. Verifies backup completion
3. Optionally tests restoration to a temporary instance
4. Sends notifications on failure

Usage:
    python scripts/verify_backup.py --instance INSTANCE_NAME [--test-restore]
"""

import argparse
import logging
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

from google.cloud import sql_v1
from google.cloud import monitoring_v3
from google.cloud import storage
import google.auth

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BackupVerifier:
    """Verifies Cloud SQL backups and tests restoration"""
    
    def __init__(self, project_id: str, instance_name: str):
        self.project_id = project_id
        self.instance_name = instance_name
        
        # Initialize clients
        self.sql_client = sql_v1.SqlBackupRunsServiceClient()
        self.instances_client = sql_v1.SqlInstancesServiceClient()
        self.monitoring_client = monitoring_v3.MetricServiceClient()
        self.storage_client = storage.Client()
        
        # Get instance details
        self.instance_path = f"projects/{project_id}/instances/{instance_name}"
        
    def list_recent_backups(self, days: int = 7) -> List[sql_v1.BackupRun]:
        """List backups from the last N days"""
        logger.info(f"Listing backups for {self.instance_name} from last {days} days")
        
        try:
            request = sql_v1.SqlBackupRunsListRequest(
                project=self.project_id,
                instance=self.instance_name
            )
            
            backups = []
            page_result = self.sql_client.list(request=request)
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
            
            for backup in page_result:
                if backup.end_time and backup.end_time > cutoff_time:
                    backups.append(backup)
                    
            return sorted(backups, key=lambda b: b.end_time or datetime.min, reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            raise
            
    def verify_backup_status(self, backup: sql_v1.BackupRun) -> Dict[str, any]:
        """Verify a specific backup's status"""
        result = {
            "id": backup.id,
            "status": backup.status,
            "type": backup.type_,
            "start_time": backup.start_time,
            "end_time": backup.end_time,
            "success": False,
            "error": None,
            "size_bytes": 0
        }
        
        # Check if backup was successful
        if backup.status == sql_v1.BackupRun.Status.SUCCESSFUL:
            result["success"] = True
            result["size_bytes"] = backup.backup_size_bytes or 0
            
            # Calculate duration
            if backup.start_time and backup.end_time:
                duration = backup.end_time - backup.start_time
                result["duration_seconds"] = duration.total_seconds()
                
        elif backup.status == sql_v1.BackupRun.Status.FAILED:
            result["error"] = backup.error.message if backup.error else "Unknown error"
            
        return result
        
    def verify_recent_backups(self, required_count: int = 1) -> bool:
        """Verify that recent backups exist and are successful"""
        logger.info(f"Verifying at least {required_count} successful backups in last 24 hours")
        
        # Get backups from last 24 hours
        backups = self.list_recent_backups(days=1)
        
        successful_backups = []
        failed_backups = []
        
        for backup in backups:
            status = self.verify_backup_status(backup)
            
            if status["success"]:
                successful_backups.append(status)
                logger.info(f"✅ Backup {status['id']} successful - "
                          f"Size: {status['size_bytes'] / 1024 / 1024:.2f} MB")
            else:
                failed_backups.append(status)
                logger.error(f"❌ Backup {status['id']} failed: {status['error']}")
                
        logger.info(f"Found {len(successful_backups)} successful backups in last 24 hours")
        
        if failed_backups:
            logger.warning(f"Found {len(failed_backups)} failed backups")
            
        return len(successful_backups) >= required_count
        
    def test_restore(self, backup_id: str, test_instance_name: str = None) -> bool:
        """Test restoration of a backup to a temporary instance"""
        if not test_instance_name:
            test_instance_name = f"{self.instance_name}-restore-test-{int(time.time())}"
            
        logger.info(f"Testing restore of backup {backup_id} to {test_instance_name}")
        
        try:
            # Get the original instance configuration
            original = self.instances_client.get(
                request=sql_v1.SqlInstancesGetRequest(
                    project=self.project_id,
                    instance=self.instance_name
                )
            )
            
            # Create restore request
            restore_request = sql_v1.InstancesRestoreBackupRequest(
                project=self.project_id,
                instance=test_instance_name,
                body=sql_v1.RestoreBackupContext(
                    backup_run_id=backup_id,
                    instance_id=self.instance_name,
                    project=self.project_id
                )
            )
            
            # Create test instance from backup
            logger.info("Creating test instance from backup...")
            
            instance = sql_v1.DatabaseInstance(
                name=test_instance_name,
                database_version=original.database_version,
                settings=sql_v1.Settings(
                    tier=original.settings.tier,
                    backup_configuration=sql_v1.BackupConfiguration(
                        enabled=False  # Don't backup the test instance
                    ),
                    ip_configuration=sql_v1.IpConfiguration(
                        ipv4_enabled=True
                    )
                ),
                region=original.region,
                restore_backup_context=sql_v1.RestoreBackupContext(
                    backup_run_id=backup_id,
                    instance_id=self.instance_name
                )
            )
            
            operation = self.instances_client.insert(
                request=sql_v1.SqlInstancesInsertRequest(
                    project=self.project_id,
                    body=instance
                )
            )
            
            # Wait for operation to complete
            logger.info("Waiting for restore to complete...")
            operation = self._wait_for_operation(operation)
            
            if operation.error:
                logger.error(f"Restore failed: {operation.error}")
                return False
                
            logger.info("✅ Restore completed successfully")
            
            # Verify the restored instance
            restored = self.instances_client.get(
                request=sql_v1.SqlInstancesGetRequest(
                    project=self.project_id,
                    instance=test_instance_name
                )
            )
            
            if restored.state == sql_v1.DatabaseInstance.State.RUNNABLE:
                logger.info("✅ Restored instance is runnable")
                
                # Clean up test instance
                logger.info("Cleaning up test instance...")
                self._delete_test_instance(test_instance_name)
                
                return True
            else:
                logger.error(f"Restored instance in unexpected state: {restored.state}")
                return False
                
        except Exception as e:
            logger.error(f"Restore test failed: {e}")
            # Try to clean up
            try:
                self._delete_test_instance(test_instance_name)
            except:
                pass
            return False
            
    def _wait_for_operation(self, operation, timeout: int = 1800):
        """Wait for a Cloud SQL operation to complete"""
        start_time = time.time()
        
        while not operation.done:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Operation timed out after {timeout} seconds")
                
            time.sleep(10)
            
            # Check operation status
            operation = self.sql_client.get_operation(
                request={"name": operation.name}
            )
            
        return operation
        
    def _delete_test_instance(self, instance_name: str):
        """Delete a test instance"""
        logger.info(f"Deleting test instance {instance_name}")
        
        try:
            self.instances_client.delete(
                request=sql_v1.SqlInstancesDeleteRequest(
                    project=self.project_id,
                    instance=instance_name
                )
            )
        except Exception as e:
            logger.error(f"Failed to delete test instance: {e}")
            
    def check_backup_metrics(self) -> Dict[str, float]:
        """Check backup-related metrics"""
        logger.info("Checking backup metrics...")
        
        metrics = {}
        
        # Query for backup count in last 24 hours
        interval = monitoring_v3.TimeInterval(
            {
                "end_time": {"seconds": int(time.time())},
                "start_time": {"seconds": int(time.time() - 86400)},
            }
        )
        
        project_name = f"projects/{self.project_id}"
        
        # Backup count metric
        results = self.monitoring_client.list_time_series(
            request={
                "name": project_name,
                "filter": f'metric.type="cloudsql.googleapis.com/database/backup/count" '
                         f'AND resource.labels.database_id="{self.project_id}:{self.instance_name}"',
                "interval": interval,
            }
        )
        
        for result in results:
            if result.points:
                metrics["backup_count_24h"] = result.points[0].value.double_value
                
        return metrics
        
    def send_notification(self, success: bool, message: str):
        """Send notification about backup status"""
        # This would integrate with your notification system
        # For now, just log
        if success:
            logger.info(f"📧 Notification: {message}")
        else:
            logger.error(f"🚨 Alert: {message}")


def main():
    parser = argparse.ArgumentParser(description="Verify Cloud SQL backups")
    parser.add_argument("--project", help="GCP project ID", 
                       default=os.environ.get("GOOGLE_AI_PROJECT_ID"))
    parser.add_argument("--instance", required=True, help="Cloud SQL instance name")
    parser.add_argument("--test-restore", action="store_true", 
                       help="Test restoration of latest backup")
    parser.add_argument("--required-backups", type=int, default=1,
                       help="Required number of successful backups in last 24h")
    
    args = parser.parse_args()
    
    if not args.project:
        logger.error("Project ID not provided. Use --project or set GOOGLE_AI_PROJECT_ID")
        sys.exit(1)
        
    # Create verifier
    verifier = BackupVerifier(args.project, args.instance)
    
    try:
        # Check recent backups
        success = verifier.verify_recent_backups(args.required_backups)
        
        if not success:
            verifier.send_notification(
                False, 
                f"Backup verification failed for {args.instance}"
            )
            sys.exit(1)
            
        # Check metrics
        metrics = verifier.check_backup_metrics()
        logger.info(f"Backup metrics: {metrics}")
        
        # Test restore if requested
        if args.test_restore:
            backups = verifier.list_recent_backups(days=1)
            if backups and backups[0].status == sql_v1.BackupRun.Status.SUCCESSFUL:
                restore_success = verifier.test_restore(str(backups[0].id))
                if not restore_success:
                    verifier.send_notification(
                        False,
                        f"Restore test failed for {args.instance}"
                    )
                    sys.exit(1)
            else:
                logger.error("No successful backup available for restore test")
                sys.exit(1)
                
        # All checks passed
        verifier.send_notification(
            True,
            f"All backup checks passed for {args.instance}"
        )
        
        logger.info("✅ Backup verification completed successfully")
        
    except Exception as e:
        logger.error(f"Backup verification failed: {e}")
        verifier.send_notification(
            False,
            f"Backup verification error for {args.instance}: {str(e)}"
        )
        sys.exit(1)


if __name__ == "__main__":
    import os
    main()