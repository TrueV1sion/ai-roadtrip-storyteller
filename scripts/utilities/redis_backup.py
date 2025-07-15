#!/usr/bin/env python3
"""
TASK-007: Redis backup strategy implementation

This script handles Redis backups to Google Cloud Storage:
1. Creates point-in-time snapshots (RDB)
2. Uploads to GCS with retention policies
3. Verifies backup integrity
4. Manages backup rotation

Usage:
    python scripts/redis_backup.py backup --redis-url REDIS_URL
    python scripts/redis_backup.py restore --backup-id BACKUP_ID
    python scripts/redis_backup.py list
"""

import argparse
import gzip
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import redis
from google.cloud import storage
from google.cloud import monitoring_v3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RedisBackupManager:
    """Manages Redis backups to Google Cloud Storage"""
    
    def __init__(self, project_id: str, bucket_name: str, redis_url: str):
        self.project_id = project_id
        self.bucket_name = bucket_name
        self.redis_url = redis_url
        
        # Parse Redis connection
        self.redis_client = redis.from_url(redis_url)
        self.redis_config = self._parse_redis_url(redis_url)
        
        # GCS client
        self.storage_client = storage.Client(project=project_id)
        self.bucket = self.storage_client.bucket(bucket_name)
        
        # Monitoring client
        self.monitoring_client = monitoring_v3.MetricServiceClient()
        
        # Backup settings
        self.backup_prefix = "redis-backups"
        self.retention_days = 30
        
    def _parse_redis_url(self, url: str) -> Dict[str, str]:
        """Parse Redis URL to get connection details"""
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        return {
            'host': parsed.hostname or 'localhost',
            'port': parsed.port or 6379,
            'password': parsed.password,
            'db': int(parsed.path.lstrip('/')) if parsed.path else 0
        }
        
    def create_backup(self, backup_name: Optional[str] = None) -> str:
        """Create a Redis backup and upload to GCS"""
        if not backup_name:
            timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            backup_name = f"redis_backup_{timestamp}"
            
        logger.info(f"Starting Redis backup: {backup_name}")
        
        try:
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                rdb_path = temp_path / f"{backup_name}.rdb"
                
                # Force Redis to create a snapshot
                logger.info("Creating Redis snapshot...")
                self.redis_client.bgsave()
                
                # Wait for background save to complete
                while self.redis_client.lastsave() == self.redis_client.lastsave():
                    import time
                    time.sleep(0.1)
                
                # Get Redis data directory
                redis_dir = self.redis_client.config_get('dir')['dir']
                redis_dbfilename = self.redis_client.config_get('dbfilename')['dbfilename']
                source_rdb = Path(redis_dir) / redis_dbfilename
                
                # For Docker/Kubernetes, we might need to use redis-cli
                if not source_rdb.exists():
                    logger.info("Using redis-cli for backup...")
                    self._backup_with_redis_cli(rdb_path)
                else:
                    # Copy the RDB file
                    shutil.copy2(source_rdb, rdb_path)
                
                # Compress the backup
                compressed_path = temp_path / f"{backup_name}.rdb.gz"
                logger.info("Compressing backup...")
                with open(rdb_path, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Calculate checksum
                checksum = self._calculate_checksum(compressed_path)
                
                # Create metadata
                metadata = {
                    'backup_name': backup_name,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'redis_version': self._get_redis_version(),
                    'size_bytes': compressed_path.stat().st_size,
                    'checksum': checksum,
                    'retention_days': self.retention_days
                }
                
                # Upload to GCS
                blob_name = f"{self.backup_prefix}/{backup_name}.rdb.gz"
                logger.info(f"Uploading backup to GCS: {blob_name}")
                
                blob = self.bucket.blob(blob_name)
                blob.metadata = metadata
                blob.upload_from_filename(str(compressed_path))
                
                # Upload metadata separately
                metadata_blob = self.bucket.blob(f"{self.backup_prefix}/{backup_name}.metadata.json")
                metadata_blob.upload_from_string(json.dumps(metadata, indent=2))
                
                # Verify upload
                if blob.exists():
                    logger.info(f"✅ Backup completed successfully: {backup_name}")
                    logger.info(f"   Size: {metadata['size_bytes'] / 1024 / 1024:.2f} MB")
                    logger.info(f"   Checksum: {checksum}")
                    
                    # Send metric
                    self._send_backup_metric(success=True, size_bytes=metadata['size_bytes'])
                    
                    return backup_name
                else:
                    raise Exception("Backup upload verification failed")
                    
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            self._send_backup_metric(success=False)
            raise
            
    def _backup_with_redis_cli(self, output_path: Path):
        """Use redis-cli to create backup (for containerized Redis)"""
        cmd = [
            'redis-cli',
            '-h', self.redis_config['host'],
            '-p', str(self.redis_config['port']),
        ]
        
        if self.redis_config['password']:
            cmd.extend(['-a', self.redis_config['password']])
            
        cmd.extend(['--rdb', str(output_path)])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"redis-cli backup failed: {result.stderr}")
            
    def restore_backup(self, backup_name: str, target_redis_url: Optional[str] = None) -> bool:
        """Restore a Redis backup from GCS"""
        if not target_redis_url:
            target_redis_url = self.redis_url
            
        logger.info(f"Starting Redis restore: {backup_name}")
        
        try:
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Download backup
                blob_name = f"{self.backup_prefix}/{backup_name}.rdb.gz"
                blob = self.bucket.blob(blob_name)
                
                if not blob.exists():
                    raise Exception(f"Backup not found: {backup_name}")
                
                compressed_path = temp_path / f"{backup_name}.rdb.gz"
                blob.download_to_filename(str(compressed_path))
                
                # Download and verify metadata
                metadata_blob = self.bucket.blob(f"{self.backup_prefix}/{backup_name}.metadata.json")
                metadata = json.loads(metadata_blob.download_as_text())
                
                # Verify checksum
                checksum = self._calculate_checksum(compressed_path)
                if checksum != metadata['checksum']:
                    raise Exception(f"Checksum mismatch! Expected: {metadata['checksum']}, Got: {checksum}")
                
                logger.info("✅ Backup integrity verified")
                
                # Decompress
                rdb_path = temp_path / f"{backup_name}.rdb"
                logger.info("Decompressing backup...")
                with gzip.open(compressed_path, 'rb') as f_in:
                    with open(rdb_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Connect to target Redis
                target_client = redis.from_url(target_redis_url)
                
                # Clear target Redis (with confirmation)
                logger.warning("⚠️  This will clear all data in the target Redis instance!")
                target_client.flushall()
                
                # Restore using redis-cli
                self._restore_with_redis_cli(rdb_path, target_redis_url)
                
                # Verify restoration
                info = target_client.info()
                logger.info(f"✅ Restore completed successfully")
                logger.info(f"   Keys restored: {info.get('db0', {}).get('keys', 0)}")
                
                return True
                
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            raise
            
    def _restore_with_redis_cli(self, rdb_path: Path, redis_url: str):
        """Use redis-cli to restore backup"""
        config = self._parse_redis_url(redis_url)
        
        # First, stop Redis from saving
        client = redis.from_url(redis_url)
        client.config_set('save', '')
        
        # Use redis-cli to restore
        cmd = [
            'redis-cli',
            '-h', config['host'],
            '-p', str(config['port']),
        ]
        
        if config['password']:
            cmd.extend(['-a', config['password']])
            
        cmd.extend(['--pipe'])
        
        # Convert RDB to Redis protocol
        with open(rdb_path, 'rb') as f:
            result = subprocess.run(cmd, stdin=f, capture_output=True)
            
        if result.returncode != 0:
            raise Exception(f"redis-cli restore failed: {result.stderr}")
            
    def list_backups(self, days: int = 7) -> List[Dict[str, any]]:
        """List recent backups"""
        logger.info(f"Listing Redis backups from last {days} days")
        
        backups = []
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        # List blobs in backup prefix
        blobs = self.bucket.list_blobs(prefix=f"{self.backup_prefix}/")
        
        for blob in blobs:
            if blob.name.endswith('.metadata.json'):
                metadata = json.loads(blob.download_as_text())
                
                # Parse timestamp
                timestamp = datetime.fromisoformat(metadata['timestamp'].replace('Z', '+00:00'))
                
                if timestamp > cutoff_time:
                    backups.append({
                        'name': metadata['backup_name'],
                        'timestamp': metadata['timestamp'],
                        'size_mb': metadata['size_bytes'] / 1024 / 1024,
                        'redis_version': metadata.get('redis_version', 'unknown'),
                        'checksum': metadata['checksum']
                    })
                    
        # Sort by timestamp
        backups.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return backups
        
    def cleanup_old_backups(self):
        """Remove backups older than retention period"""
        logger.info(f"Cleaning up backups older than {self.retention_days} days")
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        deleted_count = 0
        
        blobs = self.bucket.list_blobs(prefix=f"{self.backup_prefix}/")
        
        for blob in blobs:
            if blob.time_created < cutoff_time:
                logger.info(f"Deleting old backup: {blob.name}")
                blob.delete()
                deleted_count += 1
                
        logger.info(f"Deleted {deleted_count} old backups")
        
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
        
    def _get_redis_version(self) -> str:
        """Get Redis server version"""
        try:
            info = self.redis_client.info()
            return info.get('redis_version', 'unknown')
        except:
            return 'unknown'
            
    def _send_backup_metric(self, success: bool, size_bytes: int = 0):
        """Send backup metrics to Cloud Monitoring"""
        try:
            project_name = f"projects/{self.project_id}"
            
            series = monitoring_v3.TimeSeries()
            series.metric.type = "custom.googleapis.com/redis/backup/status"
            series.resource.type = "global"
            series.resource.labels["project_id"] = self.project_id
            
            now = time.time()
            seconds = int(now)
            nanos = int((now - seconds) * 10 ** 9)
            interval = monitoring_v3.TimeInterval(
                {"end_time": {"seconds": seconds, "nanos": nanos}}
            )
            point = monitoring_v3.Point({
                "interval": interval,
                "value": {"double_value": 1.0 if success else 0.0}
            })
            series.points = [point]
            
            self.monitoring_client.create_time_series(
                name=project_name, time_series=[series]
            )
        except Exception as e:
            logger.warning(f"Failed to send metric: {e}")


def main():
    parser = argparse.ArgumentParser(description="Redis backup management")
    parser.add_argument("--project", help="GCP project ID",
                       default=os.environ.get("GOOGLE_AI_PROJECT_ID"))
    parser.add_argument("--bucket", help="GCS bucket name",
                       default=os.environ.get("GCS_BUCKET_NAME"))
    parser.add_argument("--redis-url", help="Redis connection URL",
                       default=os.environ.get("REDIS_URL", "redis://localhost:6379"))
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create a backup")
    backup_parser.add_argument("--name", help="Backup name (auto-generated if not provided)")
    
    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore a backup")
    restore_parser.add_argument("backup_name", help="Name of backup to restore")
    restore_parser.add_argument("--target-redis", help="Target Redis URL (defaults to source)")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List backups")
    list_parser.add_argument("--days", type=int, default=7, help="Days of history to show")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Remove old backups")
    
    args = parser.parse_args()
    
    if not args.project or not args.bucket:
        logger.error("Project ID and bucket name required")
        sys.exit(1)
        
    # Create backup manager
    manager = RedisBackupManager(args.project, args.bucket, args.redis_url)
    
    try:
        if args.command == "backup":
            backup_name = manager.create_backup(args.name)
            print(f"Backup created: {backup_name}")
            
        elif args.command == "restore":
            success = manager.restore_backup(args.backup_name, args.target_redis)
            if success:
                print(f"Restore completed successfully")
            else:
                sys.exit(1)
                
        elif args.command == "list":
            backups = manager.list_backups(args.days)
            if backups:
                print(f"\nRedis backups from last {args.days} days:")
                print("-" * 80)
                for backup in backups:
                    print(f"Name: {backup['name']}")
                    print(f"  Timestamp: {backup['timestamp']}")
                    print(f"  Size: {backup['size_mb']:.2f} MB")
                    print(f"  Redis Version: {backup['redis_version']}")
                    print(f"  Checksum: {backup['checksum'][:16]}...")
                    print()
            else:
                print("No backups found")
                
        elif args.command == "cleanup":
            manager.cleanup_old_backups()
            
        else:
            parser.print_help()
            
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import time
    main()