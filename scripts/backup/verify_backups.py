#!/usr/bin/env python3
"""
Automated backup verification for AI Road Trip Storyteller.
This script verifies database and Redis backups are valid and can be restored.
"""
import os
import sys
import subprocess
import tempfile
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import json
import hashlib
import psycopg2
from google.cloud import storage
import redis
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BackupVerifier:
    """Verifies backup integrity and restorability."""
    
    def __init__(self, project_id: str, bucket_name: str):
        self.project_id = project_id
        self.bucket_name = bucket_name
        self.storage_client = storage.Client(project=project_id)
        self.bucket = self.storage_client.bucket(bucket_name)
        
    def verify_postgres_backup(self, backup_path: str, test_connection: str) -> dict:
        """
        Verify PostgreSQL backup integrity and restorability.
        
        Args:
            backup_path: Path to backup file (local or GCS)
            test_connection: Test database connection string
            
        Returns:
            Verification results
        """
        results = {
            "backup_file": backup_path,
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Download backup if from GCS
            local_backup = backup_path
            if backup_path.startswith("gs://"):
                blob_name = backup_path.replace(f"gs://{self.bucket_name}/", "")
                local_backup = os.path.join(tmpdir, "backup.sql")
                blob = self.bucket.blob(blob_name)
                blob.download_to_filename(local_backup)
                logger.info(f"Downloaded backup from GCS: {backup_path}")
            
            # Check 1: File integrity
            results["checks"]["file_exists"] = os.path.exists(local_backup)
            results["checks"]["file_size"] = os.path.getsize(local_backup)
            
            # Check 2: Calculate checksum
            with open(local_backup, 'rb') as f:
                checksum = hashlib.sha256(f.read()).hexdigest()
            results["checks"]["checksum"] = checksum
            
            # Check 3: Verify backup format
            try:
                with open(local_backup, 'r') as f:
                    first_line = f.readline()
                    results["checks"]["format_valid"] = first_line.startswith("--")
            except Exception as e:
                results["checks"]["format_valid"] = False
                results["checks"]["format_error"] = str(e)
            
            # Check 4: Test restoration to temporary database
            if test_connection:
                restore_success = self._test_postgres_restore(
                    local_backup, test_connection
                )
                results["checks"]["restore_test"] = restore_success
            
            # Check 5: Verify backup contains expected tables
            expected_tables = [
                "users", "stories", "bookings", "reservations",
                "user_preferences", "audit_logs"
            ]
            
            table_check = self._check_backup_tables(local_backup, expected_tables)
            results["checks"]["tables_present"] = table_check
            
        return results
    
    def _test_postgres_restore(self, backup_file: str, connection_string: str) -> bool:
        """Test restoring PostgreSQL backup to a test database."""
        try:
            # Create test database
            conn = psycopg2.connect(connection_string)
            conn.autocommit = True
            cursor = conn.cursor()
            
            test_db_name = f"backup_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            cursor.execute(f"CREATE DATABASE {test_db_name}")
            logger.info(f"Created test database: {test_db_name}")
            
            # Restore backup
            restore_cmd = [
                "psql",
                f"{connection_string}/{test_db_name}",
                "-f", backup_file,
                "-v", "ON_ERROR_STOP=1"
            ]
            
            result = subprocess.run(
                restore_cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("Backup restored successfully")
                
                # Verify data integrity
                test_conn = psycopg2.connect(f"{connection_string}/{test_db_name}")
                test_cursor = test_conn.cursor()
                
                # Check row counts
                test_cursor.execute("SELECT COUNT(*) FROM users")
                user_count = test_cursor.fetchone()[0]
                logger.info(f"Restored database has {user_count} users")
                
                test_conn.close()
                
                # Clean up test database
                cursor.execute(f"DROP DATABASE {test_db_name}")
                logger.info(f"Cleaned up test database: {test_db_name}")
                
                return True
            else:
                logger.error(f"Restore failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error testing restore: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _check_backup_tables(self, backup_file: str, expected_tables: list) -> dict:
        """Check if backup contains expected tables."""
        table_status = {}
        
        try:
            with open(backup_file, 'r') as f:
                content = f.read()
                
            for table in expected_tables:
                # Check for CREATE TABLE and COPY statements
                create_found = f"CREATE TABLE {table}" in content
                copy_found = f"COPY {table}" in content
                table_status[table] = create_found or copy_found
                
        except Exception as e:
            logger.error(f"Error checking tables: {e}")
            return {"error": str(e)}
            
        return table_status
    
    def verify_redis_backup(self, backup_path: str) -> dict:
        """
        Verify Redis backup integrity.
        
        Args:
            backup_path: Path to RDB file
            
        Returns:
            Verification results
        """
        results = {
            "backup_file": backup_path,
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Download backup if from GCS
            local_backup = backup_path
            if backup_path.startswith("gs://"):
                blob_name = backup_path.replace(f"gs://{self.bucket_name}/", "")
                local_backup = os.path.join(tmpdir, "dump.rdb")
                blob = self.bucket.blob(blob_name)
                blob.download_to_filename(local_backup)
                logger.info(f"Downloaded Redis backup from GCS: {backup_path}")
            
            # Check 1: File integrity
            results["checks"]["file_exists"] = os.path.exists(local_backup)
            results["checks"]["file_size"] = os.path.getsize(local_backup)
            
            # Check 2: RDB file header
            try:
                with open(local_backup, 'rb') as f:
                    header = f.read(9)
                    results["checks"]["rdb_header_valid"] = header.startswith(b'REDIS')
            except Exception as e:
                results["checks"]["rdb_header_valid"] = False
                results["checks"]["header_error"] = str(e)
            
            # Check 3: Use redis-check-rdb if available
            try:
                check_cmd = ["redis-check-rdb", local_backup]
                result = subprocess.run(
                    check_cmd,
                    capture_output=True,
                    text=True
                )
                results["checks"]["rdb_check_passed"] = result.returncode == 0
                if result.returncode != 0:
                    results["checks"]["rdb_check_error"] = result.stderr
            except FileNotFoundError:
                results["checks"]["rdb_check_passed"] = "redis-check-rdb not available"
            
        return results
    
    def list_recent_backups(self, prefix: str, days: int = 7) -> list:
        """List backups from the last N days."""
        cutoff_date = datetime.now() - timedelta(days=days)
        backups = []
        
        for blob in self.bucket.list_blobs(prefix=prefix):
            if blob.time_created > cutoff_date.replace(tzinfo=blob.time_created.tzinfo):
                backups.append({
                    "name": blob.name,
                    "size": blob.size,
                    "created": blob.time_created.isoformat(),
                    "md5_hash": blob.md5_hash
                })
        
        return sorted(backups, key=lambda x: x["created"], reverse=True)
    
    def generate_verification_report(self, results: list) -> str:
        """Generate a verification report."""
        report = ["# Backup Verification Report", ""]
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        report.append("")
        
        # Summary
        total_checks = len(results)
        passed_checks = sum(1 for r in results if all(
            v for k, v in r.get("checks", {}).items() 
            if isinstance(v, bool)
        ))
        
        report.append("## Summary")
        report.append(f"- Total backups checked: {total_checks}")
        report.append(f"- Passed verification: {passed_checks}")
        report.append(f"- Failed verification: {total_checks - passed_checks}")
        report.append("")
        
        # Detailed results
        report.append("## Detailed Results")
        
        for i, result in enumerate(results, 1):
            report.append(f"\n### Backup {i}: {result['backup_file']}")
            report.append(f"Timestamp: {result['timestamp']}")
            report.append("\nChecks:")
            
            for check, value in result.get("checks", {}).items():
                status = "✅" if value else "❌"
                report.append(f"- {check}: {status} {value}")
        
        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description='Verify database and Redis backups')
    parser.add_argument('--project-id', required=True, help='GCP Project ID')
    parser.add_argument('--bucket-name', required=True, help='GCS bucket name')
    parser.add_argument('--backup-type', choices=['postgres', 'redis', 'all'], default='all')
    parser.add_argument('--test-db-connection', help='Test database connection string')
    parser.add_argument('--days', type=int, default=7, help='Check backups from last N days')
    parser.add_argument('--output', help='Output report file')
    args = parser.parse_args()
    
    verifier = BackupVerifier(args.project_id, args.bucket_name)
    results = []
    
    # Verify PostgreSQL backups
    if args.backup_type in ['postgres', 'all']:
        logger.info("Checking PostgreSQL backups...")
        pg_backups = verifier.list_recent_backups("backups/postgres/", args.days)
        
        for backup in pg_backups[:3]:  # Check last 3 backups
            logger.info(f"Verifying {backup['name']}...")
            result = verifier.verify_postgres_backup(
                f"gs://{args.bucket_name}/{backup['name']}",
                args.test_db_connection
            )
            results.append(result)
    
    # Verify Redis backups
    if args.backup_type in ['redis', 'all']:
        logger.info("Checking Redis backups...")
        redis_backups = verifier.list_recent_backups("backups/redis/", args.days)
        
        for backup in redis_backups[:3]:  # Check last 3 backups
            logger.info(f"Verifying {backup['name']}...")
            result = verifier.verify_redis_backup(
                f"gs://{args.bucket_name}/{backup['name']}"
            )
            results.append(result)
    
    # Generate report
    report = verifier.generate_verification_report(results)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        logger.info(f"Report saved to {args.output}")
    else:
        print("\n" + report)
    
    # Exit with error if any verification failed
    if any(not all(v for k, v in r.get("checks", {}).items() if isinstance(v, bool)) 
           for r in results):
        sys.exit(1)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())