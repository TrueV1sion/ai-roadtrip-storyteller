#!/usr/bin/env python3
"""
Migrate existing unencrypted 2FA secrets to encrypted format.
This script should be run once after deploying the encryption update.
"""
import asyncio
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import argparse
import logging

# Add the backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.core.config import settings
from backend.app.core.encryption import get_encryption_manager
from backend.app.models.user import User
from backend.app.db.base import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_2fa_secrets(dry_run: bool = False):
    """Migrate all unencrypted 2FA secrets to encrypted format."""
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    encryption_manager = get_encryption_manager()
    
    with SessionLocal() as db:
        # Find all users with 2FA enabled
        users_with_2fa = db.query(User).filter(
            User.two_factor_enabled == True,
            User._two_factor_secret_encrypted.isnot(None)
        ).all()
        
        logger.info(f"Found {len(users_with_2fa)} users with 2FA enabled")
        
        migrated_count = 0
        failed_count = 0
        
        for user in users_with_2fa:
            try:
                # Check if the secret is already encrypted
                current_secret = user._two_factor_secret_encrypted
                
                if not current_secret:
                    continue
                
                # Try to decrypt it - if it fails, it's not encrypted
                try:
                    decrypted = encryption_manager.decrypt(current_secret)
                    logger.info(f"User {user.email} already has encrypted 2FA secret")
                    continue
                except Exception:
                    # Not encrypted, needs migration
                    pass
                
                if dry_run:
                    logger.info(f"[DRY RUN] Would encrypt 2FA secret for user {user.email}")
                else:
                    # Encrypt the secret
                    encrypted_secret = encryption_manager.encrypt(current_secret)
                    user._two_factor_secret_encrypted = encrypted_secret
                    logger.info(f"Encrypted 2FA secret for user {user.email}")
                
                migrated_count += 1
                
            except Exception as e:
                logger.error(f"Failed to migrate 2FA secret for user {user.email}: {e}")
                failed_count += 1
        
        if not dry_run and migrated_count > 0:
            db.commit()
            logger.info(f"Committed {migrated_count} encrypted 2FA secrets to database")
        
        # Also encrypt backup codes if they're stored in plaintext
        users_with_backup_codes = db.query(User).filter(
            User.two_factor_backup_codes.isnot(None)
        ).all()
        
        backup_migrated = 0
        for user in users_with_backup_codes:
            try:
                if user.two_factor_backup_codes and isinstance(user.two_factor_backup_codes, list):
                    # Check if codes are already hashed (they should start with a hash prefix)
                    if user.two_factor_backup_codes and not user.two_factor_backup_codes[0].startswith('$'):
                        if dry_run:
                            logger.info(f"[DRY RUN] Would hash backup codes for user {user.email}")
                        else:
                            # Import bcrypt for hashing
                            from passlib.context import CryptContext
                            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
                            
                            hashed_codes = [pwd_context.hash(code) for code in user.two_factor_backup_codes]
                            user.two_factor_backup_codes = hashed_codes
                            logger.info(f"Hashed backup codes for user {user.email}")
                        backup_migrated += 1
            except Exception as e:
                logger.error(f"Failed to hash backup codes for user {user.email}: {e}")
        
        if not dry_run and backup_migrated > 0:
            db.commit()
            logger.info(f"Committed {backup_migrated} hashed backup codes to database")
    
    logger.info(f"\nMigration Summary:")
    logger.info(f"  2FA Secrets Encrypted: {migrated_count}")
    logger.info(f"  2FA Secrets Failed: {failed_count}")
    logger.info(f"  Backup Codes Hashed: {backup_migrated}")
    
    return migrated_count, failed_count


def main():
    parser = argparse.ArgumentParser(description='Encrypt existing 2FA secrets')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without doing it')
    args = parser.parse_args()
    
    logger.info("Starting 2FA secret encryption migration...")
    
    try:
        migrated, failed = migrate_2fa_secrets(dry_run=args.dry_run)
        
        if failed > 0:
            logger.error(f"Migration completed with {failed} errors")
            return 1
        else:
            logger.info("Migration completed successfully")
            return 0
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())