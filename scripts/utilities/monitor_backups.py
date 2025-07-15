#!/usr/bin/env python3
"""
Monitor database backup health and send alerts for issues.
"""

import os
import sys
import json
import datetime
from typing import List, Dict, Optional
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from google.cloud import storage
    from google.cloud import monitoring_v3
    GCS_AVAILABLE = True
except ImportError:
    logger.warning("Google Cloud libraries not available")
    GCS_AVAILABLE = False


class BackupMonitor:
    """Monitors database backup health and alerts on issues."""
    
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID", "roadtrip-460720")
        self.bucket_name = os.getenv("GCS_BACKUP_BUCKET", "roadtrip-db-backups")
        self.alert_threshold_hours = int(os.getenv("BACKUP_ALERT_THRESHOLD_HOURS", "26"))
        self.min_backup_size_mb = float(os.getenv("MIN_BACKUP_SIZE_MB", "1.0"))
        
        if GCS_AVAILABLE:
            self.storage_client = storage.Client()
            self.monitoring_client = monitoring_v3.MetricServiceClient()
        else:
            self.storage_client = None
            self.monitoring_client = None
    
    def check_latest_backup(self) -> Dict:
        """Check the status of the latest backup."""
        if not self.storage_client:
            return {"status": "error", "message": "GCS client not available"}
        
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blobs = list(bucket.list_blobs(prefix="postgres/"))
            
            if not blobs:
                return {
                    "status": "critical",
                    "message": "No backups found",
                    "last_backup": None,
                    "backup_count": 0
                }
            
            # Sort by creation time
            blobs.sort(key=lambda x: x.time_created, reverse=True)
            latest_blob = blobs[0]
            
            # Calculate age
            age = datetime.datetime.utcnow() - latest_blob.time_created.replace(tzinfo=None)
            age_hours = age.total_seconds() / 3600
            
            # Check size
            size_mb = latest_blob.size / 1024 / 1024
            
            # Determine status
            status = "healthy"
            issues = []
            
            if age_hours > self.alert_threshold_hours:
                status = "warning"
                issues.append(f"Backup is {age_hours:.1f} hours old (threshold: {self.alert_threshold_hours}h)")
            
            if age_hours > self.alert_threshold_hours * 2:
                status = "critical"
            
            if size_mb < self.min_backup_size_mb:
                status = "critical"
                issues.append(f"Backup size is {size_mb:.2f} MB (minimum: {self.min_backup_size_mb} MB)")
            
            return {
                "status": status,
                "message": ", ".join(issues) if issues else "Backup is healthy",
                "last_backup": {
                    "name": latest_blob.name,
                    "created": latest_blob.time_created.isoformat(),
                    "size_mb": size_mb,
                    "age_hours": age_hours
                },
                "backup_count": len(blobs),
                "total_size_gb": sum(b.size for b in blobs) / 1024 / 1024 / 1024
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to check backups: {str(e)}",
                "last_backup": None
            }
    
    def check_backup_consistency(self) -> Dict:
        """Check if backups are being created consistently."""
        if not self.storage_client:
            return {"status": "error", "message": "GCS client not available"}
        
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            
            # Get backups from last 7 days
            cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=7)
            recent_blobs = []
            
            for blob in bucket.list_blobs(prefix="postgres/"):
                if blob.time_created.replace(tzinfo=None) > cutoff:
                    recent_blobs.append(blob)
            
            # Group by date
            backups_by_date = {}
            for blob in recent_blobs:
                date = blob.time_created.date()
                if date not in backups_by_date:
                    backups_by_date[date] = []
                backups_by_date[date].append(blob)
            
            # Check for missing days
            missing_days = []
            for i in range(7):
                check_date = (datetime.datetime.utcnow() - datetime.timedelta(days=i)).date()
                if check_date not in backups_by_date:
                    missing_days.append(check_date.isoformat())
            
            status = "healthy"
            if len(missing_days) > 0:
                status = "warning"
            if len(missing_days) > 2:
                status = "critical"
            
            return {
                "status": status,
                "days_with_backups": len(backups_by_date),
                "missing_days": missing_days,
                "backup_schedule": {
                    date.isoformat(): len(blobs) 
                    for date, blobs in backups_by_date.items()
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to check consistency: {str(e)}"
            }
    
    def send_metric(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """Send custom metric to Cloud Monitoring."""
        if not self.monitoring_client:
            logger.warning("Monitoring client not available")
            return
        
        try:
            series = monitoring_v3.TimeSeries()
            series.metric.type = f"custom.googleapis.com/backup/{metric_name}"
            
            if labels:
                for key, val in labels.items():
                    series.metric.labels[key] = val
            
            series.resource.type = "global"
            series.resource.labels["project_id"] = self.project_id
            
            now = datetime.datetime.utcnow()
            seconds = int(now.timestamp())
            nanos = int((now.timestamp() % 1) * 10**9)
            
            interval = monitoring_v3.TimeInterval(
                {"end_time": {"seconds": seconds, "nanos": nanos}}
            )
            point = monitoring_v3.Point({
                "interval": interval,
                "value": {"double_value": value}
            })
            series.points = [point]
            
            # Send metric
            project_name = f"projects/{self.project_id}"
            self.monitoring_client.create_time_series(
                name=project_name,
                time_series=[series]
            )
            
        except Exception as e:
            logger.error(f"Failed to send metric: {e}")
    
    def run_health_check(self) -> Dict:
        """Run complete health check and return results."""
        results = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "overall_status": "healthy",
            "checks": {}
        }
        
        # Check latest backup
        latest_check = self.check_latest_backup()
        results["checks"]["latest_backup"] = latest_check
        
        # Check consistency
        consistency_check = self.check_backup_consistency()
        results["checks"]["consistency"] = consistency_check
        
        # Determine overall status
        statuses = [
            latest_check.get("status", "unknown"),
            consistency_check.get("status", "unknown")
        ]
        
        if "critical" in statuses:
            results["overall_status"] = "critical"
        elif "warning" in statuses:
            results["overall_status"] = "warning"
        elif "error" in statuses:
            results["overall_status"] = "error"
        
        # Send metrics
        if latest_check.get("last_backup"):
            self.send_metric("age_hours", latest_check["last_backup"]["age_hours"])
            self.send_metric("size_mb", latest_check["last_backup"]["size_mb"])
        
        self.send_metric("backup_count", latest_check.get("backup_count", 0))
        self.send_metric("consistency_score", 
                        7 - len(consistency_check.get("missing_days", [])))
        
        return results
    
    def format_report(self, results: Dict) -> str:
        """Format health check results as human-readable report."""
        report = []
        report.append("=== Database Backup Health Report ===")
        report.append(f"Timestamp: {results['timestamp']}")
        report.append(f"Overall Status: {results['overall_status'].upper()}")
        report.append("")
        
        # Latest backup info
        latest = results["checks"]["latest_backup"]
        if latest.get("last_backup"):
            lb = latest["last_backup"]
            report.append("Latest Backup:")
            report.append(f"  - Name: {lb['name']}")
            report.append(f"  - Age: {lb['age_hours']:.1f} hours")
            report.append(f"  - Size: {lb['size_mb']:.2f} MB")
            report.append(f"  - Status: {latest['status']}")
            if latest.get("message"):
                report.append(f"  - Issues: {latest['message']}")
        else:
            report.append("Latest Backup: NO BACKUPS FOUND")
        
        report.append("")
        
        # Consistency info
        consistency = results["checks"]["consistency"]
        report.append("Backup Consistency (Last 7 Days):")
        report.append(f"  - Days with backups: {consistency.get('days_with_backups', 0)}/7")
        if consistency.get("missing_days"):
            report.append(f"  - Missing days: {', '.join(consistency['missing_days'])}")
        report.append(f"  - Status: {consistency['status']}")
        
        report.append("")
        
        # Summary
        if results["overall_status"] == "critical":
            report.append("⚠️  CRITICAL: Immediate attention required!")
        elif results["overall_status"] == "warning":
            report.append("⚠️  WARNING: Please investigate backup issues.")
        else:
            report.append("✅ All backup checks passed.")
        
        return "\n".join(report)


def main():
    """Main entry point for monitoring script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor database backups")
    parser.add_argument("--json", action="store_true",
                       help="Output results as JSON")
    parser.add_argument("--alert-only", action="store_true",
                       help="Only output if there are issues")
    
    args = parser.parse_args()
    
    monitor = BackupMonitor()
    results = monitor.run_health_check()
    
    # Check if we should output
    if args.alert_only and results["overall_status"] == "healthy":
        sys.exit(0)
    
    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(monitor.format_report(results))
    
    # Exit with appropriate code
    exit_codes = {
        "healthy": 0,
        "warning": 1,
        "critical": 2,
        "error": 3
    }
    sys.exit(exit_codes.get(results["overall_status"], 3))


if __name__ == "__main__":
    main()