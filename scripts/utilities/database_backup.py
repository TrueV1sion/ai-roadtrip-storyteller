#!/usr/bin/env python3
"""
Automated database backup script for PostgreSQL.
Supports both local and Google Cloud Storage backups.
"""

import os
import sys
import subprocess
import datetime
import gzip
import shutil
from typing import Optional, List
import logging
from pathlib import Path

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
    from backend.app.core.config import settings
    GCS_AVAILABLE = True
except ImportError:
    logger.warning("Google Cloud Storage not available. Only local backups will be created.")
    GCS_AVAILABLE = False
    settings = None


class DatabaseBackup:
    """Handles automated PostgreSQL database backups."""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL not found in environment")
        
        # Parse database URL
        self._parse_database_url()
        
        # Setup paths
        self.backup_dir = Path("/var/backups/postgres")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # GCS settings
        self.gcs_bucket = os.getenv("GCS_BACKUP_BUCKET", "roadtrip-db-backups")
        self.gcs_client = None
        if GCS_AVAILABLE:
            try:
                self.gcs_client = storage.Client()
                logger.info(f"Google Cloud Storage initialized. Bucket: {self.gcs_bucket}")
            except Exception as e:
                logger.warning(f"Failed to initialize GCS client: {e}")
    
    def _parse_database_url(self):
        """Parse PostgreSQL connection URL."""
        # Format: postgresql://user:password@host:port/database
        url = self.database_url.replace("postgresql://", "")
        
        # Extract components
        auth, rest = url.split("@")
        self.user, self.password = auth.split(":")
        host_port, self.database = rest.split("/")
        
        if ":" in host_port:
            self.host, self.port = host_port.split(":")
        else:
            self.host = host_port
            self.port = "5432"
    
    def create_backup(self, compress: bool = True) -> str:
        """Create a database backup using pg_dump."""
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = f"roadtrip_backup_{timestamp}.sql"
        backup_path = self.backup_dir / backup_name
        
        logger.info(f"Starting backup: {backup_name}")
        
        # Set PGPASSWORD environment variable
        env = os.environ.copy()
        env["PGPASSWORD"] = self.password
        
        # Build pg_dump command
        cmd = [
            "pg_dump",
            "-h", self.host,
            "-p", self.port,
            "-U", self.user,
            "-d", self.database,
            "-f", str(backup_path),
            "--verbose",
            "--no-owner",
            "--no-privileges",
            "--no-tablespaces",
            "--clean",
            "--if-exists"
        ]
        
        try:
            # Run pg_dump
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Backup created successfully: {backup_path}")
            
            # Compress if requested
            if compress:
                compressed_path = self._compress_backup(backup_path)
                return str(compressed_path)
            
            return str(backup_path)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Backup failed: {e.stderr}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during backup: {e}")
            raise
    
    def _compress_backup(self, backup_path: Path) -> Path:
        """Compress backup file using gzip."""
        compressed_path = backup_path.with_suffix(".sql.gz")
        
        logger.info(f"Compressing backup to: {compressed_path}")
        
        with open(backup_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb', compresslevel=9) as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Remove uncompressed file
        backup_path.unlink()
        
        # Get compression ratio
        compressed_size = compressed_path.stat().st_size
        logger.info(f"Backup compressed to {compressed_size / 1024 / 1024:.2f} MB")
        
        return compressed_path
    
    def upload_to_gcs(self, local_path: str) -> bool:
        """Upload backup to Google Cloud Storage."""
        if not self.gcs_client:
            logger.warning("GCS client not available. Skipping upload.")
            return False
        
        try:
            bucket = self.gcs_client.bucket(self.gcs_bucket)
            blob_name = f"postgres/{os.path.basename(local_path)}"
            blob = bucket.blob(blob_name)
            
            logger.info(f"Uploading to GCS: gs://{self.gcs_bucket}/{blob_name}")
            
            # Upload with progress
            blob.upload_from_filename(local_path, timeout=600)
            
            logger.info("Upload completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload to GCS: {e}")
            return False
    
    def cleanup_old_backups(self, retention_days: int = 7):
        """Remove old backup files."""
        logger.info(f"Cleaning up backups older than {retention_days} days")
        
        cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=retention_days)
        
        # Clean local backups
        for backup_file in self.backup_dir.glob("roadtrip_backup_*.sql*"):
            if backup_file.stat().st_mtime < cutoff_date.timestamp():
                logger.info(f"Removing old backup: {backup_file}")
                backup_file.unlink()
        
        # Clean GCS backups
        if self.gcs_client:
            try:
                bucket = self.gcs_client.bucket(self.gcs_bucket)
                for blob in bucket.list_blobs(prefix="postgres/"):
                    if blob.time_created < cutoff_date:
                        logger.info(f"Removing old GCS backup: {blob.name}")
                        blob.delete()
            except Exception as e:
                logger.error(f"Failed to clean GCS backups: {e}")
    
    def verify_backup(self, backup_path: str) -> bool:
        """Verify backup file integrity."""
        logger.info(f"Verifying backup: {backup_path}")
        
        # Check file exists and has size
        path = Path(backup_path)
        if not path.exists():
            logger.error("Backup file does not exist")
            return False
        
        size_mb = path.stat().st_size / 1024 / 1024
        if size_mb < 0.1:  # Less than 100KB is suspicious
            logger.error(f"Backup file too small: {size_mb:.2f} MB")
            return False
        
        logger.info(f"Backup verified: {size_mb:.2f} MB")
        return True
    
    def list_backups(self) -> List[dict]:
        """List all available backups."""
        backups = []
        
        # List local backups
        for backup_file in sorted(self.backup_dir.glob("roadtrip_backup_*.sql*")):
            backups.append({
                "name": backup_file.name,
                "location": "local",
                "size_mb": backup_file.stat().st_size / 1024 / 1024,
                "created": datetime.datetime.fromtimestamp(backup_file.stat().st_mtime)
            })
        
        # List GCS backups
        if self.gcs_client:
            try:
                bucket = self.gcs_client.bucket(self.gcs_bucket)
                for blob in bucket.list_blobs(prefix="postgres/"):
                    backups.append({
                        "name": os.path.basename(blob.name),
                        "location": "gcs",
                        "size_mb": blob.size / 1024 / 1024,
                        "created": blob.time_created
                    })
            except Exception as e:
                logger.error(f"Failed to list GCS backups: {e}")
        
        return sorted(backups, key=lambda x: x["created"], reverse=True)
    
    def restore_backup(self, backup_name: str, target_database: Optional[str] = None):
        """Restore a backup to the database."""
        logger.info(f"Restoring backup: {backup_name}")
        
        # Find backup file
        backup_path = self.backup_dir / backup_name
        
        # Download from GCS if not local
        if not backup_path.exists() and self.gcs_client:
            logger.info("Backup not found locally. Downloading from GCS...")
            bucket = self.gcs_client.bucket(self.gcs_bucket)
            blob = bucket.blob(f"postgres/{backup_name}")
            blob.download_to_filename(str(backup_path))
        
        # Decompress if needed
        if backup_path.suffix == ".gz":
            logger.info("Decompressing backup...")
            decompressed_path = backup_path.with_suffix("")
            with gzip.open(backup_path, 'rb') as f_in:
                with open(decompressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            backup_path = decompressed_path
        
        # Restore using psql
        env = os.environ.copy()
        env["PGPASSWORD"] = self.password
        
        target_db = target_database or self.database
        
        cmd = [
            "psql",
            "-h", self.host,
            "-p", self.port,
            "-U", self.user,
            "-d", target_db,
            "-f", str(backup_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            logger.info("Backup restored successfully")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Restore failed: {e.stderr}")
            raise


def main():
    """Main entry point for backup script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database backup management")
    parser.add_argument("action", choices=["backup", "list", "restore", "cleanup"],
                       help="Action to perform")
    parser.add_argument("--no-compress", action="store_true",
                       help="Skip compression for backup")
    parser.add_argument("--no-upload", action="store_true",
                       help="Skip upload to GCS")
    parser.add_argument("--retention-days", type=int, default=7,
                       help="Days to retain backups (default: 7)")
    parser.add_argument("--backup-name", help="Name of backup to restore")
    parser.add_argument("--target-database", help="Target database for restore")
    
    args = parser.parse_args()
    
    try:
        backup_manager = DatabaseBackup()
        
        if args.action == "backup":
            # Create backup
            backup_path = backup_manager.create_backup(compress=not args.no_compress)
            
            # Verify backup
            if backup_manager.verify_backup(backup_path):
                # Upload to GCS
                if not args.no_upload:
                    backup_manager.upload_to_gcs(backup_path)
                
                # Cleanup old backups
                backup_manager.cleanup_old_backups(args.retention_days)
                
                logger.info("Backup completed successfully")
            else:
                logger.error("Backup verification failed")
                sys.exit(1)
        
        elif args.action == "list":
            # List backups
            backups = backup_manager.list_backups()
            
            print(f"\nAvailable backups ({len(backups)} total):")
            print("-" * 80)
            print(f"{'Name':<50} {'Location':<10} {'Size (MB)':<10} {'Created'}")
            print("-" * 80)
            
            for backup in backups[:20]:  # Show latest 20
                print(f"{backup['name']:<50} {backup['location']:<10} "
                      f"{backup['size_mb']:<10.2f} {backup['created']}")
        
        elif args.action == "restore":
            # Restore backup
            if not args.backup_name:
                parser.error("--backup-name required for restore")
            
            backup_manager.restore_backup(
                args.backup_name,
                args.target_database
            )
        
        elif args.action == "cleanup":
            # Cleanup old backups
            backup_manager.cleanup_old_backups(args.retention_days)
            logger.info("Cleanup completed")
            
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()