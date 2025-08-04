#!/usr/bin/env python3
"""
Production Database Backup Solution
Automated backup for PostgreSQL with Google Cloud Storage integration
"""

import os
import sys
import json
import logging
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import tempfile
import gzip
import hashlib

from google.cloud import storage
from google.cloud import secretmanager
from google.cloud import logging as cloud_logging
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import boto3  # For cross-cloud backup redundancy

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Cloud Logging
cloud_client = cloud_logging.Client()
cloud_client.setup_logging()

class DatabaseBackupManager:
    """Manages automated database backups with multiple storage providers"""
    
    def __init__(self):
        self.project_id = os.environ.get('GOOGLE_CLOUD_PROJECT', 'roadtrip-460720')
        self.environment = os.environ.get('ENVIRONMENT', 'production')
        self.backup_bucket = f"{self.project_id}-backups-{self.environment}"
        self.retention_days = int(os.environ.get('BACKUP_RETENTION_DAYS', '30'))
        self.storage_client = storage.Client()
        self.secret_client = secretmanager.SecretManagerServiceClient()
        
        # Get database connection from Secret Manager
        self.db_url = self._get_secret('DATABASE_URL')
        
        # Parse database URL
        self._parse_db_url()
        
    def _get_secret(self, secret_id: str) -> str:
        """Retrieve secret from Google Secret Manager"""
        name = f"projects/{self.project_id}/secrets/{secret_id}-{self.environment}/versions/latest"
        try:
            response = self.secret_client.access_secret_version(request={"name": name})
            return response.payload.data.decode('UTF-8')
        except Exception as e:
            logger.error(f"Failed to retrieve secret {secret_id}: {e}")
            raise
    
    def _parse_db_url(self):
        """Parse database connection URL"""
        # Handle Cloud SQL socket connection format
        if '?host=/cloudsql/' in self.db_url:
            # Parse Cloud SQL connection
            parts = self.db_url.split('/')
            self.db_user = parts[2].split(':')[0]
            self.db_pass = parts[2].split(':')[1].split('@')[0]
            self.db_name = parts[3].split('?')[0]
            self.db_host = self.db_url.split('?host=')[1]
            self.db_port = '5432'
            self.is_cloud_sql = True
        else:
            # Parse standard PostgreSQL URL
            from urllib.parse import urlparse
            parsed = urlparse(self.db_url)
            self.db_host = parsed.hostname
            self.db_port = parsed.port or 5432
            self.db_user = parsed.username
            self.db_pass = parsed.password
            self.db_name = parsed.path[1:]
            self.is_cloud_sql = False
    
    def create_backup(self) -> Dict[str, str]:
        """Create a database backup"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_name = f"roadtrip_{self.environment}_backup_{timestamp}"
        
        logger.info(f"Starting backup: {backup_name}")
        
        # Create temporary file for backup
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.sql') as tmp_file:
            backup_file = tmp_file.name
        
        try:
            # Run pg_dump
            self._run_pg_dump(backup_file)
            
            # Compress backup
            compressed_file = self._compress_backup(backup_file)
            
            # Calculate checksum
            checksum = self._calculate_checksum(compressed_file)
            
            # Upload to multiple storage providers
            gcs_url = self._upload_to_gcs(compressed_file, backup_name)
            
            # Upload to AWS S3 for redundancy (if configured)
            s3_url = self._upload_to_s3(compressed_file, backup_name) if self._is_s3_configured() else None
            
            # Create backup metadata
            metadata = {
                'backup_name': backup_name,
                'timestamp': timestamp,
                'environment': self.environment,
                'database': self.db_name,
                'size_bytes': os.path.getsize(compressed_file),
                'checksum': checksum,
                'gcs_url': gcs_url,
                's3_url': s3_url,
                'retention_until': (datetime.utcnow() + timedelta(days=self.retention_days)).isoformat(),
                'status': 'completed'
            }
            
            # Save metadata
            self._save_backup_metadata(metadata)
            
            logger.info(f"Backup completed successfully: {backup_name}")
            return metadata
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            raise
        finally:
            # Cleanup temporary files
            for file in [backup_file, compressed_file]:
                if os.path.exists(file):
                    os.remove(file)
    
    def _run_pg_dump(self, output_file: str):
        """Run pg_dump to create database backup"""
        logger.info("Running pg_dump...")
        
        # Build pg_dump command
        cmd = [
            'pg_dump',
            '--no-owner',
            '--no-acl',
            '--clean',
            '--if-exists',
            '--verbose',
            '--file', output_file
        ]
        
        # Set environment variables for pg_dump
        env = os.environ.copy()
        if self.is_cloud_sql:
            # For Cloud SQL socket connection
            env['PGHOST'] = self.db_host
            env['PGUSER'] = self.db_user
            env['PGPASSWORD'] = self.db_pass
            env['PGDATABASE'] = self.db_name
        else:
            # For standard connection
            cmd.extend([
                '--host', self.db_host,
                '--port', str(self.db_port),
                '--username', self.db_user,
                '--dbname', self.db_name
            ])
            env['PGPASSWORD'] = self.db_pass
        
        # Execute pg_dump
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"pg_dump failed: {result.stderr}")
        
        logger.info(f"pg_dump completed. File size: {os.path.getsize(output_file)} bytes")
    
    def _compress_backup(self, backup_file: str) -> str:
        """Compress backup file using gzip"""
        logger.info("Compressing backup...")
        compressed_file = f"{backup_file}.gz"
        
        with open(backup_file, 'rb') as f_in:
            with gzip.open(compressed_file, 'wb', compresslevel=9) as f_out:
                f_out.writelines(f_in)
        
        original_size = os.path.getsize(backup_file)
        compressed_size = os.path.getsize(compressed_file)
        compression_ratio = (1 - compressed_size / original_size) * 100
        
        logger.info(f"Compression completed. Ratio: {compression_ratio:.1f}%")
        return compressed_file
    
    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _upload_to_gcs(self, file_path: str, backup_name: str) -> str:
        """Upload backup to Google Cloud Storage"""
        logger.info("Uploading to Google Cloud Storage...")
        
        # Ensure bucket exists
        self._ensure_gcs_bucket()
        
        # Upload file
        bucket = self.storage_client.bucket(self.backup_bucket)
        blob_name = f"database/{self.environment}/{backup_name}.sql.gz"
        blob = bucket.blob(blob_name)
        
        # Set metadata
        blob.metadata = {
            'environment': self.environment,
            'backup_type': 'database',
            'created_at': datetime.utcnow().isoformat(),
            'retention_days': str(self.retention_days)
        }
        
        # Upload with retry
        blob.upload_from_filename(file_path)
        
        # Set lifecycle rule
        blob.lifecycle_rules = [{
            'action': {'type': 'Delete'},
            'condition': {'age': self.retention_days}
        }]
        
        gcs_url = f"gs://{self.backup_bucket}/{blob_name}"
        logger.info(f"Upload completed: {gcs_url}")
        return gcs_url
    
    def _ensure_gcs_bucket(self):
        """Ensure GCS bucket exists with proper configuration"""
        try:
            bucket = self.storage_client.get_bucket(self.backup_bucket)
        except Exception as e:
            logger.info(f"Creating bucket: {self.backup_bucket}")
            bucket = self.storage_client.create_bucket(
                self.backup_bucket,
                location='us-central1'
            )
            
            # Set bucket lifecycle
            rule = {
                'action': {'type': 'Delete'},
                'condition': {'age': self.retention_days}
            }
            bucket.lifecycle_rules = [rule]
            bucket.patch()
            
            # Enable versioning
            bucket.versioning_enabled = True
            bucket.patch()
    
    def _upload_to_s3(self, file_path: str, backup_name: str) -> Optional[str]:
        """Upload backup to AWS S3 for cross-cloud redundancy"""
        if not self._is_s3_configured():
            return None
        
        logger.info("Uploading to AWS S3 for redundancy...")
        
        try:
            s3_client = boto3.client('s3')
            bucket_name = os.environ.get('AWS_BACKUP_BUCKET')
            key = f"database/{self.environment}/{backup_name}.sql.gz"
            
            s3_client.upload_file(
                file_path, 
                bucket_name, 
                key,
                ExtraArgs={
                    'ServerSideEncryption': 'AES256',
                    'StorageClass': 'GLACIER_IR',
                    'Metadata': {
                        'environment': self.environment,
                        'backup_type': 'database',
                        'created_at': datetime.utcnow().isoformat()
                    }
                }
            )
            
            s3_url = f"s3://{bucket_name}/{key}"
            logger.info(f"S3 upload completed: {s3_url}")
            return s3_url
        except Exception as e:
            logger.warning(f"S3 upload failed (non-critical): {e}")
            return None
    
    def _is_s3_configured(self) -> bool:
        """Check if AWS S3 is configured for backup"""
        return all([
            os.environ.get('AWS_ACCESS_KEY_ID'),
            os.environ.get('AWS_SECRET_ACCESS_KEY'),
            os.environ.get('AWS_BACKUP_BUCKET')
        ])
    
    def _save_backup_metadata(self, metadata: Dict):
        """Save backup metadata to Cloud Storage"""
        bucket = self.storage_client.bucket(self.backup_bucket)
        blob_name = f"metadata/{metadata['backup_name']}.json"
        blob = bucket.blob(blob_name)
        
        blob.upload_from_string(
            json.dumps(metadata, indent=2),
            content_type='application/json'
        )
    
    def cleanup_old_backups(self):
        """Clean up backups older than retention period"""
        logger.info("Cleaning up old backups...")
        
        bucket = self.storage_client.bucket(self.backup_bucket)
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
        
        deleted_count = 0
        for blob in bucket.list_blobs(prefix=f"database/{self.environment}/"):
            if blob.time_created < cutoff_date.replace(tzinfo=blob.time_created.tzinfo):
                logger.info(f"Deleting old backup: {blob.name}")
                blob.delete()
                deleted_count += 1
        
        logger.info(f"Deleted {deleted_count} old backups")
    
    def verify_backup(self, backup_name: str) -> bool:
        """Verify backup integrity"""
        logger.info(f"Verifying backup: {backup_name}")
        
        # Download backup metadata
        bucket = self.storage_client.bucket(self.backup_bucket)
        metadata_blob = bucket.blob(f"metadata/{backup_name}.json")
        metadata = json.loads(metadata_blob.download_as_text())
        
        # Download backup file
        backup_blob = bucket.blob(f"database/{self.environment}/{backup_name}.sql.gz")
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            backup_blob.download_to_filename(tmp_file.name)
            
            # Verify checksum
            calculated_checksum = self._calculate_checksum(tmp_file.name)
            if calculated_checksum != metadata['checksum']:
                logger.error("Backup verification failed: checksum mismatch")
                return False
            
            # Verify file can be decompressed
            try:
                with gzip.open(tmp_file.name, 'rb') as f:
                    f.read(1024)  # Read first 1KB to verify
                logger.info("Backup verification passed")
                return True
            except Exception as e:
                logger.error(f"Backup verification failed: {e}")
                return False
            finally:
                os.remove(tmp_file.name)
    
    def restore_backup(self, backup_name: str, target_db: Optional[str] = None):
        """Restore database from backup"""
        logger.warning(f"Starting database restore from: {backup_name}")
        
        if not target_db:
            target_db = f"{self.db_name}_restored_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Download backup
        bucket = self.storage_client.bucket(self.backup_bucket)
        backup_blob = bucket.blob(f"database/{self.environment}/{backup_name}.sql.gz")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.sql.gz') as tmp_compressed:
            backup_blob.download_to_filename(tmp_compressed.name)
            
            # Decompress
            with tempfile.NamedTemporaryFile(delete=False, suffix='.sql') as tmp_sql:
                with gzip.open(tmp_compressed.name, 'rb') as f_in:
                    tmp_sql.write(f_in.read())
                
                # Create target database if needed
                self._create_database(target_db)
                
                # Restore backup
                self._run_pg_restore(tmp_sql.name, target_db)
                
                logger.info(f"Restore completed to database: {target_db}")
        
        # Cleanup
        os.remove(tmp_compressed.name)
        os.remove(tmp_sql.name)
    
    def _create_database(self, db_name: str):
        """Create a new database"""
        conn = psycopg2.connect(
            host=self.db_host if not self.is_cloud_sql else None,
            port=self.db_port,
            user=self.db_user,
            password=self.db_pass,
            database='postgres'  # Connect to default database
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE {db_name}")
        
        conn.close()
    
    def _run_pg_restore(self, backup_file: str, target_db: str):
        """Run psql to restore database"""
        cmd = [
            'psql',
            '--file', backup_file,
            '--dbname', target_db
        ]
        
        env = os.environ.copy()
        if self.is_cloud_sql:
            env['PGHOST'] = self.db_host
            env['PGUSER'] = self.db_user
            env['PGPASSWORD'] = self.db_pass
        else:
            cmd.extend([
                '--host', self.db_host,
                '--port', str(self.db_port),
                '--username', self.db_user
            ])
            env['PGPASSWORD'] = self.db_pass
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Restore failed: {result.stderr}")
    
    def get_backup_status(self) -> List[Dict]:
        """Get status of recent backups"""
        bucket = self.storage_client.bucket(self.backup_bucket)
        backups = []
        
        for blob in bucket.list_blobs(prefix=f"metadata/"):
            if blob.name.endswith('.json'):
                metadata = json.loads(blob.download_as_text())
                backups.append(metadata)
        
        # Sort by timestamp
        backups.sort(key=lambda x: x['timestamp'], reverse=True)
        return backups[:10]  # Return last 10 backups


def main():
    """Main execution function"""
    try:
        manager = DatabaseBackupManager()
        
        # Parse command line arguments
        if len(sys.argv) > 1:
            command = sys.argv[1]
            
            if command == 'backup':
                # Create backup
                metadata = manager.create_backup()
                print(json.dumps(metadata, indent=2))
                
            elif command == 'cleanup':
                # Cleanup old backups
                manager.cleanup_old_backups()
                
            elif command == 'verify' and len(sys.argv) > 2:
                # Verify specific backup
                backup_name = sys.argv[2]
                result = manager.verify_backup(backup_name)
                print(f"Verification {'passed' if result else 'failed'}")
                
            elif command == 'restore' and len(sys.argv) > 2:
                # Restore backup
                backup_name = sys.argv[2]
                target_db = sys.argv[3] if len(sys.argv) > 3 else None
                manager.restore_backup(backup_name, target_db)
                
            elif command == 'status':
                # Get backup status
                backups = manager.get_backup_status()
                print(json.dumps(backups, indent=2))
                
            else:
                print("Usage: database_backup.py [backup|cleanup|verify|restore|status] [args...]")
                sys.exit(1)
        else:
            # Default: create backup and cleanup
            metadata = manager.create_backup()
            manager.cleanup_old_backups()
            print(json.dumps(metadata, indent=2))
            
    except Exception as e:
        logger.error(f"Backup operation failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()