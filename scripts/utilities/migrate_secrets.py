#!/usr/bin/env python3
"""
TASK-002: Migrate secrets from environment variables to Google Secret Manager

This script migrates all sensitive configuration from .env file to Google Secret Manager.
It creates secrets if they don't exist or updates them if they do.

Usage:
    python scripts/migrate_secrets.py [--dry-run] [--project-id PROJECT_ID]
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from dotenv import load_dotenv
from google.cloud import secretmanager
from google.api_core import exceptions

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define which environment variables are secrets
SECRETS_TO_MIGRATE = {
    # Database
    "DATABASE_URL": "roadtrip-db-url",
    
    # Security
    "SECRET_KEY": "roadtrip-secret-key",
    "JWT_SECRET_KEY": "roadtrip-jwt-secret",
    
    # API Keys - Production
    "GOOGLE_MAPS_API_KEY": "roadtrip-maps-api-key",
    "GOOGLE_AI_API_KEY": "roadtrip-google-ai-api-key",
    "TICKETMASTER_API_KEY": "roadtrip-ticketmaster-api-key",
    "OPENWEATHERMAP_API_KEY": "roadtrip-openweathermap-api-key",
    "RECREATION_GOV_API_KEY": "roadtrip-recreation-gov-api-key",
    
    # API Keys - Optional
    "SPOTIFY_CLIENT_ID": "roadtrip-spotify-client-id",
    "SPOTIFY_CLIENT_SECRET": "roadtrip-spotify-client-secret",
    
    # Partner APIs (when available)
    "OPENTABLE_API_KEY": "roadtrip-opentable-api-key",
    "SHELL_RECHARGE_API_KEY": "roadtrip-shell-recharge-api-key",
    "CHARGEPOINT_API_KEY": "roadtrip-chargepoint-api-key",
    "VIATOR_API_KEY": "roadtrip-viator-api-key",
    "RESY_API_KEY": "roadtrip-resy-api-key",
    
    # Flight APIs
    "FLIGHTSTATS_API_KEY": "roadtrip-flightstats-api-key",
    "FLIGHTSTATS_APP_ID": "roadtrip-flightstats-app-id",
    "FLIGHTAWARE_API_KEY": "roadtrip-flightaware-api-key",
    
    # Payment Processing
    "STRIPE_SECRET_KEY": "roadtrip-stripe-secret-key",
    "STRIPE_WEBHOOK_SECRET": "roadtrip-stripe-webhook-secret",
    
    # Communications
    "TWILIO_AUTH_TOKEN": "roadtrip-twilio-auth-token",
    "SENDGRID_API_KEY": "roadtrip-sendgrid-api-key",
    
    # Redis (if using auth)
    "REDIS_PASSWORD": "roadtrip-redis-password",
}

# Non-secret config that stays in .env
NON_SECRET_CONFIG = [
    "APP_VERSION",
    "LOG_LEVEL",
    "TEST_MODE",
    "REDIS_URL",  # URL structure is not secret
    "GOOGLE_AI_PROJECT_ID",  # Project ID is not secret
    "GOOGLE_AI_LOCATION",
    "GOOGLE_AI_MODEL",
    "GCS_BUCKET_NAME",
    "ALLOWED_ORIGINS",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
]


class SecretMigrator:
    """Handles migration of secrets to Google Secret Manager"""
    
    def __init__(self, project_id: str, dry_run: bool = False):
        self.project_id = project_id
        self.dry_run = dry_run
        self.client = None
        self.stats = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0
        }
        
    def initialize_client(self):
        """Initialize Secret Manager client"""
        try:
            self.client = secretmanager.SecretManagerServiceClient()
            logger.info(f"Initialized Secret Manager client for project: {self.project_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Secret Manager client: {e}")
            raise
            
    def secret_exists(self, secret_id: str) -> bool:
        """Check if a secret already exists"""
        try:
            name = f"projects/{self.project_id}/secrets/{secret_id}"
            self.client.get_secret(request={"name": name})
            return True
        except exceptions.NotFound:
            return False
        except Exception as e:
            logger.error(f"Error checking secret {secret_id}: {e}")
            return False
            
    def create_or_update_secret(self, secret_id: str, secret_value: str) -> bool:
        """Create a new secret or update existing one"""
        if self.dry_run:
            action = "Would create" if not self.secret_exists(secret_id) else "Would update"
            logger.info(f"[DRY RUN] {action} secret: {secret_id}")
            return True
            
        try:
            if not self.secret_exists(secret_id):
                # Create new secret
                parent = f"projects/{self.project_id}"
                secret = self.client.create_secret(
                    request={
                        "parent": parent,
                        "secret_id": secret_id,
                        "secret": {
                            "replication": {"automatic": {}},
                            "labels": {
                                "app": "roadtrip",
                                "managed-by": "migration-script"
                            }
                        },
                    }
                )
                logger.info(f"Created secret: {secret_id}")
                self.stats["created"] += 1
            else:
                logger.info(f"Secret already exists: {secret_id}")
                self.stats["updated"] += 1
                
            # Add secret version
            parent = f"projects/{self.project_id}/secrets/{secret_id}"
            self.client.add_secret_version(
                request={
                    "parent": parent,
                    "payload": {"data": secret_value.encode("UTF-8")},
                }
            )
            logger.info(f"Added version to secret: {secret_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create/update secret {secret_id}: {e}")
            self.stats["failed"] += 1
            return False
            
    def migrate_secrets(self, env_vars: Dict[str, str]) -> Tuple[int, int, int]:
        """Migrate all secrets from environment variables"""
        logger.info(f"Starting migration of {len(SECRETS_TO_MIGRATE)} secrets...")
        
        for env_key, secret_id in SECRETS_TO_MIGRATE.items():
            if env_key in env_vars:
                secret_value = env_vars[env_key]
                logger.info(f"Migrating {env_key} -> {secret_id}")
                self.create_or_update_secret(secret_id, secret_value)
            else:
                logger.warning(f"Environment variable {env_key} not found, skipping")
                self.stats["skipped"] += 1
                
        return self.stats["created"], self.stats["updated"], self.stats["failed"]
        
    def create_updated_env_file(self, original_env: Dict[str, str], output_path: str):
        """Create new .env file with secrets removed"""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would create updated .env file at: {output_path}")
            return
            
        with open(output_path, 'w') as f:
            f.write("# AI Road Trip Storyteller Configuration\n")
            f.write("# Secrets have been migrated to Google Secret Manager\n")
            f.write("# Generated by migrate_secrets.py\n\n")
            
            # Write non-secret config
            f.write("# Application Configuration\n")
            for key in NON_SECRET_CONFIG:
                if key in original_env:
                    f.write(f"{key}={original_env[key]}\n")
                    
            f.write("\n# Google Cloud Configuration\n")
            f.write(f"GOOGLE_AI_PROJECT_ID={self.project_id}\n")
            f.write("# Secrets are now managed by Google Secret Manager\n")
            f.write("# To add new secrets, use: gcloud secrets create SECRET_ID --data-file=-\n")
            
        logger.info(f"Created updated .env file at: {output_path}")


def load_env_file(env_path: str) -> Dict[str, str]:
    """Load environment variables from .env file"""
    if not os.path.exists(env_path):
        logger.error(f"Environment file not found: {env_path}")
        sys.exit(1)
        
    # Load the .env file
    load_dotenv(env_path)
    
    # Get all environment variables
    env_vars = {}
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip().strip('"').strip("'")
                
    return env_vars


def main():
    parser = argparse.ArgumentParser(description="Migrate secrets to Google Secret Manager")
    parser.add_argument("--dry-run", action="store_true", 
                      help="Show what would be done without making changes")
    parser.add_argument("--project-id", 
                      help="Google Cloud project ID (defaults to GOOGLE_AI_PROJECT_ID from .env)")
    parser.add_argument("--env-file", default=".env",
                      help="Path to .env file (default: .env)")
    parser.add_argument("--output-env", default=".env.nosecrets",
                      help="Path for new .env without secrets (default: .env.nosecrets)")
    
    args = parser.parse_args()
    
    # Load environment variables
    logger.info(f"Loading environment from: {args.env_file}")
    env_vars = load_env_file(args.env_file)
    
    # Get project ID
    project_id = args.project_id or env_vars.get("GOOGLE_AI_PROJECT_ID")
    if not project_id:
        logger.error("Project ID not specified. Use --project-id or set GOOGLE_AI_PROJECT_ID in .env")
        sys.exit(1)
        
    # Create migrator
    migrator = SecretMigrator(project_id, args.dry_run)
    
    try:
        # Initialize client
        migrator.initialize_client()
        
        # Migrate secrets
        created, updated, failed = migrator.migrate_secrets(env_vars)
        
        # Create updated .env file
        migrator.create_updated_env_file(env_vars, args.output_env)
        
        # Summary
        logger.info("\n" + "="*50)
        logger.info("Migration Summary:")
        logger.info(f"  Created: {created}")
        logger.info(f"  Updated: {updated}")
        logger.info(f"  Skipped: {migrator.stats['skipped']}")
        logger.info(f"  Failed: {failed}")
        logger.info("="*50)
        
        if failed > 0:
            logger.error("Some secrets failed to migrate!")
            sys.exit(1)
            
        if not args.dry_run:
            logger.info("\nNext steps:")
            logger.info("1. Review the new .env.nosecrets file")
            logger.info("2. Test the application with Secret Manager")
            logger.info("3. When confirmed working, replace .env with .env.nosecrets")
            logger.info("4. Update deployment configs to use Secret Manager")
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()