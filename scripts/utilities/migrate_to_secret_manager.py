#!/usr/bin/env python3
"""
Migrate secrets from environment variables to Google Secret Manager.

This script identifies all sensitive configuration values and migrates them
to Google Secret Manager for secure storage in production.
"""

import os
import sys
import json
import asyncio
from typing import Dict, List, Tuple
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import from backend, fallback to basic logging
try:
    from backend.app.core.secrets import get_secret_manager
    from backend.app.core.logger import logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Mock SecretManagerClient for testing
    class MockSecretManager:
        def get_secret(self, secret_id, version="latest"):
            logger.info(f"[MOCK] Would fetch secret: {secret_id}")
            return None
        
        def create_secret(self, secret_id, value):
            logger.info(f"[MOCK] Would create secret: {secret_id}")
            return True
        
        def update_secret(self, secret_id, value):
            logger.info(f"[MOCK] Would update secret: {secret_id}")
            return True
    
    def get_secret_manager():
        return MockSecretManager()


# Define secrets to migrate
SECRETS_TO_MIGRATE = [
    # Core Authentication
    ("SECRET_KEY", "roadtrip-secret-key", "Application secret key for session management"),
    ("JWT_SECRET_KEY", "roadtrip-jwt-secret", "JWT token signing key"),
    
    # Database
    ("DATABASE_URL", "roadtrip-database-url", "PostgreSQL connection string"),
    ("DB_PASSWORD", "roadtrip-db-password", "Database password"),
    
    # Redis
    ("REDIS_URL", "roadtrip-redis-url", "Redis connection string"),
    
    # Google Cloud Services
    ("GOOGLE_AI_PROJECT_ID", "roadtrip-google-ai-project", "Google AI project ID"),
    ("GOOGLE_MAPS_API_KEY", "roadtrip-google-maps-key", "Google Maps API key"),
    ("GCS_BUCKET_NAME", "roadtrip-gcs-bucket", "Google Cloud Storage bucket"),
    
    # External API Keys
    ("TICKETMASTER_API_KEY", "roadtrip-ticketmaster-key", "Ticketmaster API key"),
    ("OPENWEATHERMAP_API_KEY", "roadtrip-openweather-key", "OpenWeatherMap API key"),
    ("RECREATION_GOV_API_KEY", "roadtrip-recreation-key", "Recreation.gov API key"),
    
    # Partner API Keys (for future use)
    ("OPENTABLE_API_KEY", "roadtrip-opentable-key", "OpenTable API key"),
    ("OPENTABLE_PARTNER_ID", "roadtrip-opentable-partner", "OpenTable Partner ID"),
    ("SHELL_RECHARGE_API_KEY", "roadtrip-shell-key", "Shell Recharge API key"),
    ("CHARGEPOINT_CLIENT_ID", "roadtrip-chargepoint-id", "ChargePoint Client ID"),
    ("CHARGEPOINT_CLIENT_SECRET", "roadtrip-chargepoint-secret", "ChargePoint Client Secret"),
    ("VIATOR_API_KEY", "roadtrip-viator-key", "Viator API key"),
    ("VIATOR_PARTNER_ID", "roadtrip-viator-partner", "Viator Partner ID"),
    ("RESY_API_KEY", "roadtrip-resy-key", "Resy API key"),
    ("RESY_CLIENT_ID", "roadtrip-resy-id", "Resy Client ID"),
    ("RESY_CLIENT_SECRET", "roadtrip-resy-secret", "Resy Client Secret"),
    
    # Optional Services
    ("SPOTIFY_CLIENT_ID", "roadtrip-spotify-id", "Spotify Client ID"),
    ("SPOTIFY_CLIENT_SECRET", "roadtrip-spotify-secret", "Spotify Client Secret"),
    
    # Flight Tracking APIs
    ("FLIGHTSTATS_API_KEY", "roadtrip-flightstats-key", "FlightStats API key"),
    ("FLIGHTSTATS_APP_ID", "roadtrip-flightstats-id", "FlightStats App ID"),
    ("FLIGHTAWARE_API_KEY", "roadtrip-flightaware-key", "FlightAware API key"),
    ("AVIATIONSTACK_API_KEY", "roadtrip-aviationstack-key", "AviationStack API key"),
    ("FLIGHTLABS_API_KEY", "roadtrip-flightlabs-key", "FlightLabs API key"),
]


class SecretMigrator:
    """Handles migration of secrets to Google Secret Manager."""
    
    def __init__(self):
        self.secret_manager = get_secret_manager()
        self.migration_report = {
            "timestamp": datetime.utcnow().isoformat(),
            "migrated": [],
            "skipped": [],
            "failed": [],
            "warnings": []
        }
    
    def check_prerequisites(self) -> bool:
        """Check if Google Cloud is properly configured."""
        try:
            # Check if project ID is set
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
            if not project_id:
                logger.error("GOOGLE_CLOUD_PROJECT_ID not set")
                return False
            
            # Check if credentials are available
            creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if not creds_path:
                logger.warning("GOOGLE_APPLICATION_CREDENTIALS not set - using default credentials")
            elif not os.path.exists(creds_path):
                logger.error(f"Credentials file not found: {creds_path}")
                return False
            
            logger.info(f"Using Google Cloud project: {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"Prerequisites check failed: {e}")
            return False
    
    def load_env_file(self, env_file: str = ".env") -> Dict[str, str]:
        """Load environment variables from .env file."""
        env_vars = {}
        
        if os.path.exists(env_file):
            logger.info(f"Loading environment from {env_file}")
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip().strip('"\'')
        
        # Also include current environment variables
        env_vars.update(os.environ)
        
        return env_vars
    
    def validate_secret_value(self, env_key: str, value: str) -> Tuple[bool, str]:
        """Validate a secret value before migration."""
        if not value:
            return False, "Empty value"
        
        # Check for placeholder values
        placeholders = ["your-", "xxx", "change-me", "todo", "placeholder"]
        if any(placeholder in value.lower() for placeholder in placeholders):
            return False, "Appears to be a placeholder value"
        
        # Validate specific secret formats
        if env_key == "DATABASE_URL" and not value.startswith("postgresql://"):
            return False, "Invalid PostgreSQL URL format"
        
        if env_key == "REDIS_URL" and not value.startswith("redis://"):
            return False, "Invalid Redis URL format"
        
        if "_KEY" in env_key and len(value) < 10:
            return False, "API key seems too short"
        
        return True, "Valid"
    
    async def migrate_secret(self, env_key: str, secret_id: str, description: str, 
                           env_vars: Dict[str, str]) -> bool:
        """Migrate a single secret to Secret Manager."""
        try:
            # Get value from environment
            value = env_vars.get(env_key)
            
            if not value:
                self.migration_report["skipped"].append({
                    "env_key": env_key,
                    "secret_id": secret_id,
                    "reason": "Not found in environment"
                })
                logger.info(f"Skipped {env_key}: Not found in environment")
                return False
            
            # Validate the value
            is_valid, validation_msg = self.validate_secret_value(env_key, value)
            if not is_valid:
                self.migration_report["warnings"].append({
                    "env_key": env_key,
                    "secret_id": secret_id,
                    "warning": validation_msg
                })
                logger.warning(f"Warning for {env_key}: {validation_msg}")
            
            # Check if secret already exists
            existing_value = self.secret_manager.get_secret(secret_id)
            if existing_value:
                if existing_value == value:
                    self.migration_report["skipped"].append({
                        "env_key": env_key,
                        "secret_id": secret_id,
                        "reason": "Already exists with same value"
                    })
                    logger.info(f"Skipped {env_key}: Already in Secret Manager")
                    return True
                else:
                    # Update existing secret
                    success = self.secret_manager.update_secret(secret_id, value)
                    if success:
                        self.migration_report["migrated"].append({
                            "env_key": env_key,
                            "secret_id": secret_id,
                            "action": "updated",
                            "description": description
                        })
                        logger.info(f"Updated {env_key} in Secret Manager")
                        return True
            else:
                # Create new secret
                success = self.secret_manager.create_secret(secret_id, value)
                if success:
                    self.migration_report["migrated"].append({
                        "env_key": env_key,
                        "secret_id": secret_id,
                        "action": "created",
                        "description": description
                    })
                    logger.info(f"Created {env_key} in Secret Manager")
                    return True
            
            self.migration_report["failed"].append({
                "env_key": env_key,
                "secret_id": secret_id,
                "reason": "Failed to create/update"
            })
            return False
            
        except Exception as e:
            self.migration_report["failed"].append({
                "env_key": env_key,
                "secret_id": secret_id,
                "reason": str(e)
            })
            logger.error(f"Failed to migrate {env_key}: {e}")
            return False
    
    async def run_migration(self, dry_run: bool = False):
        """Run the complete migration process."""
        logger.info("Starting secret migration to Google Secret Manager")
        
        if not self.check_prerequisites():
            logger.error("Prerequisites check failed - aborting migration")
            return
        
        # Load environment variables
        env_vars = self.load_env_file()
        logger.info(f"Loaded {len(env_vars)} environment variables")
        
        if dry_run:
            logger.info("Running in DRY RUN mode - no changes will be made")
        
        # Migrate each secret
        for env_key, secret_id, description in SECRETS_TO_MIGRATE:
            if dry_run:
                value = env_vars.get(env_key)
                if value:
                    is_valid, msg = self.validate_secret_value(env_key, value)
                    status = "VALID" if is_valid else f"WARNING: {msg}"
                    logger.info(f"[DRY RUN] Would migrate {env_key} -> {secret_id} [{status}]")
                else:
                    logger.info(f"[DRY RUN] Would skip {env_key} (not found)")
            else:
                await self.migrate_secret(env_key, secret_id, description, env_vars)
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate and save migration report."""
        report_file = f"secret_migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, 'w') as f:
            json.dump(self.migration_report, f, indent=2)
        
        # Print summary
        print("\n=== Secret Migration Summary ===")
        print(f"Total secrets processed: {len(SECRETS_TO_MIGRATE)}")
        print(f"Successfully migrated: {len(self.migration_report['migrated'])}")
        print(f"Skipped: {len(self.migration_report['skipped'])}")
        print(f"Failed: {len(self.migration_report['failed'])}")
        print(f"Warnings: {len(self.migration_report['warnings'])}")
        print(f"\nDetailed report saved to: {report_file}")
        
        if self.migration_report['failed']:
            print("\n⚠️  Failed migrations:")
            for item in self.migration_report['failed']:
                print(f"  - {item['env_key']}: {item['reason']}")
        
        if self.migration_report['warnings']:
            print("\n⚠️  Warnings:")
            for item in self.migration_report['warnings']:
                print(f"  - {item['env_key']}: {item['warning']}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate secrets to Google Secret Manager"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes"
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to environment file (default: .env)"
    )
    
    args = parser.parse_args()
    
    # Run migration
    migrator = SecretMigrator()
    asyncio.run(migrator.run_migration(dry_run=args.dry_run))


if __name__ == "__main__":
    main()