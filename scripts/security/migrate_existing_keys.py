#!/usr/bin/env python3
"""
Migrate existing JWT keys from local storage to Google Secret Manager.
This script helps transition from file-based to Secret Manager-based key storage.
"""
import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from app.core.secret_manager import secret_manager
from app.core.logger import logger


def load_existing_keys(keys_path: Path):
    """Load existing JWT keys from local file."""
    key_file = keys_path / "jwt_keys.json"
    
    if not key_file.exists():
        logger.error(f"No existing keys found at: {key_file}")
        return None
        
    try:
        with open(key_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load existing keys: {e}")
        return None


def migrate_keys_to_secret_manager(keys_data: dict, project_id: str):
    """Migrate JWT keys to Google Secret Manager."""
    
    # Prepare metadata
    metadata = {
        "current_key_id": keys_data['current_key_id'],
        "keys": [],
        "migrated_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    # Migrate each key pair
    for key_id, key_info in keys_data['keys'].items():
        logger.info(f"Migrating key: {key_id}")
        
        # Store private key
        private_key = key_info['private']
        if secret_manager.create_or_update_secret(f"roadtrip-jwt-private-key-{key_id}", private_key):
            logger.info(f"✓ Migrated private key: roadtrip-jwt-private-key-{key_id}")
        else:
            logger.error(f"Failed to migrate private key for {key_id}")
            return False
        
        # Store public key
        public_key = key_info['public']
        if secret_manager.create_or_update_secret(f"roadtrip-jwt-public-key-{key_id}", public_key):
            logger.info(f"✓ Migrated public key: roadtrip-jwt-public-key-{key_id}")
        else:
            logger.error(f"Failed to migrate public key for {key_id}")
            return False
        
        # Add to metadata
        metadata["keys"].append({
            "key_id": key_id,
            "created_at": key_info.get('created_at', datetime.utcnow().isoformat()),
            "active": key_id == keys_data['current_key_id']
        })
    
    # Store metadata
    if secret_manager.create_or_update_secret("roadtrip-jwt-key-metadata", json.dumps(metadata)):
        logger.info("✓ Stored key metadata: roadtrip-jwt-key-metadata")
    else:
        logger.error("Failed to store metadata")
        return False
    
    return True


def verify_migration():
    """Verify that keys were successfully migrated."""
    logger.info("\nVerifying migration...")
    
    # Check metadata
    metadata_json = secret_manager.get_secret("roadtrip-jwt-key-metadata")
    if not metadata_json:
        logger.error("❌ Metadata not found in Secret Manager")
        return False
    
    metadata = json.loads(metadata_json)
    logger.info(f"✓ Found metadata with {len(metadata['keys'])} key(s)")
    
    # Verify each key
    for key_info in metadata['keys']:
        key_id = key_info['key_id']
        
        # Check private key
        private_key = secret_manager.get_secret(f"roadtrip-jwt-private-key-{key_id}")
        if private_key:
            logger.info(f"✓ Verified private key: {key_id}")
        else:
            logger.error(f"❌ Private key not found: {key_id}")
            return False
        
        # Check public key
        public_key = secret_manager.get_secret(f"roadtrip-jwt-public-key-{key_id}")
        if public_key:
            logger.info(f"✓ Verified public key: {key_id}")
        else:
            logger.error(f"❌ Public key not found: {key_id}")
            return False
    
    logger.info("\n✅ All keys successfully migrated and verified!")
    return True


def main():
    parser = argparse.ArgumentParser(description='Migrate existing JWT keys to Secret Manager')
    parser.add_argument('--project-id', required=True, help='Google Cloud project ID')
    parser.add_argument('--keys-path', default='backend/app/core/keys', 
                       help='Path to existing JWT keys directory')
    parser.add_argument('--verify-only', action='store_true', 
                       help='Only verify existing migration')
    parser.add_argument('--delete-local', action='store_true',
                       help='Delete local keys after successful migration')
    
    args = parser.parse_args()
    
    # Set project ID
    os.environ['GOOGLE_CLOUD_PROJECT'] = args.project_id
    
    if args.verify_only:
        if verify_migration():
            logger.info("Migration verification successful!")
        else:
            logger.error("Migration verification failed!")
        return
    
    # Load existing keys
    keys_path = Path(args.keys_path)
    keys_data = load_existing_keys(keys_path)
    
    if not keys_data:
        logger.error("No keys to migrate")
        return
    
    logger.info(f"Found {len(keys_data['keys'])} key pair(s) to migrate")
    logger.info(f"Current key ID: {keys_data['current_key_id']}")
    
    # Perform migration
    if migrate_keys_to_secret_manager(keys_data, args.project_id):
        logger.info("\n✅ Migration completed successfully!")
        
        # Verify migration
        if verify_migration():
            logger.info("\n✅ Migration verified successfully!")
            
            if args.delete_local:
                # Backup before deletion
                backup_file = keys_path / f"jwt_keys_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                os.rename(keys_path / "jwt_keys.json", backup_file)
                logger.info(f"Local keys backed up to: {backup_file}")
                logger.warning("Consider deleting the backup after confirming production works correctly")
            else:
                logger.info("\nNext steps:")
                logger.info("1. Update your code to use jwt_secret_manager module")
                logger.info("2. Test JWT functionality in staging")
                logger.info("3. Remove local key files from version control")
                logger.info("4. Run with --delete-local to remove local keys")
        else:
            logger.error("Migration verification failed!")
    else:
        logger.error("Migration failed!")


if __name__ == "__main__":
    main()