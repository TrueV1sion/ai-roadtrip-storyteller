"""
Startup validation to ensure all components are properly initialized.
"""
import sys
import asyncio
from typing import List, Tuple, Optional
import logging

from app.core.logger import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class StartupValidator:
    """Validates that all required services and configurations are available."""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    async def validate_all(self) -> Tuple[bool, List[str], List[str]]:
        """Run all validation checks."""
        logger.info("Starting application validation...")
        
        # Check required environment variables
        self._check_required_config()
        
        # Check database connection
        await self._check_database()
        
        # Check Redis connection
        await self._check_redis()
        
        # Check Google Cloud services
        await self._check_google_cloud()
        
        # Check optional services
        await self._check_optional_services()
        
        success = len(self.errors) == 0
        
        if success:
            logger.info("✅ All validation checks passed!")
        else:
            logger.error(f"❌ Validation failed with {len(self.errors)} errors")
        
        return success, self.errors, self.warnings
    
    def _check_required_config(self):
        """Check that all required configuration is present."""
        required_vars = [
            ("GOOGLE_AI_PROJECT_ID", settings.GOOGLE_AI_PROJECT_ID),
            ("DATABASE_URL", settings.DATABASE_URL),
            ("SECRET_KEY", settings.SECRET_KEY),
        ]
        
        for var_name, var_value in required_vars:
            if not var_value:
                self.errors.append(f"Required environment variable {var_name} is not set")
            else:
                logger.info(f"✓ {var_name} is configured")
    
    async def _check_database(self):
        """Check database connectivity."""
        try:
            from app.core.database_manager import db_manager, check_database_migrations
            
            # Test database connection
            health_status = db_manager.check_health()
            
            if health_status.get("status") == "healthy":
                logger.info("✓ Database connection successful")
                
                # Check migration status
                migration_status = await check_database_migrations()
                if migration_status.get("status") == "migrations_applied":
                    logger.info("✓ Database migrations are up to date")
                elif migration_status.get("status") == "no_migrations":
                    self.warnings.append("No database migrations found - run 'alembic upgrade head'")
                else:
                    self.warnings.append(f"Migration status: {migration_status.get('message', 'Unknown')}")
            else:
                error_msg = health_status.get("error", "Unknown database error")
                self.errors.append(f"Database connection failed: {error_msg}")
                
        except Exception as e:
            self.errors.append(f"Database validation failed: {str(e)}")
    
    async def _check_redis(self):
        """Check Redis connectivity."""
        try:
            from app.core.cache import cache_manager
            
            # Try to set and get a test value
            test_key = "startup_validation_test"
            test_value = "success"
            
            await cache_manager.set(test_key, test_value, ttl=10)
            result = await cache_manager.get(test_key)
            
            if result == test_value:
                logger.info("✓ Redis connection successful")
                await cache_manager.delete(test_key)
            else:
                self.errors.append("Redis connection test failed")
        except Exception as e:
            self.warnings.append(f"Redis connection failed (non-critical): {str(e)}")
    
    async def _check_google_cloud(self):
        """Check Google Cloud service connectivity."""
        try:
            from app.core.google_cloud_auth import google_cloud_auth, validate_permissions
            
            # Check authentication
            if google_cloud_auth.initialize():
                logger.info("✓ Google Cloud authentication successful")
                
                # Validate permissions
                permissions = validate_permissions()
                for service, has_permission in permissions.items():
                    if has_permission:
                        logger.info(f"✓ {service.replace('_', ' ').title()} access confirmed")
                    else:
                        self.warnings.append(f"{service.replace('_', ' ').title()} access not available")
            else:
                self.warnings.append("Google Cloud authentication failed - using fallback mode")
            
            # Check if Maps API key is set
            if getattr(settings, 'GOOGLE_MAPS_API_KEY', None):
                logger.info("✓ Google Maps API key configured")
            else:
                self.warnings.append("Google Maps API key not configured - directions features will not work")
                
            # Check if GCS bucket is configured
            if getattr(settings, 'GCS_BUCKET_NAME', None):
                logger.info("✓ Google Cloud Storage bucket configured")
            else:
                self.warnings.append("GCS bucket not configured - audio storage may not work")
                
        except Exception as e:
            self.warnings.append(f"Google Cloud validation failed: {str(e)}")
    
    async def _check_optional_services(self):
        """Check optional service configurations."""
        # Spotify
        if settings.SPOTIFY_CLIENT_ID and settings.SPOTIFY_CLIENT_SECRET:
            logger.info("✓ Spotify integration configured")
        else:
            self.warnings.append("Spotify credentials not configured - music features will be limited")
        
        # Third-party services
        optional_services = [
            ("Stripe", hasattr(settings, 'STRIPE_API_KEY') and settings.STRIPE_API_KEY),
            ("Twilio", hasattr(settings, 'TWILIO_ACCOUNT_SID') and settings.TWILIO_ACCOUNT_SID),
            ("SendGrid", hasattr(settings, 'SENDGRID_API_KEY') and settings.SENDGRID_API_KEY),
        ]
        
        for service_name, is_configured in optional_services:
            if is_configured:
                logger.info(f"✓ {service_name} integration configured")
            else:
                logger.debug(f"- {service_name} not configured (optional)")


async def run_startup_validation() -> bool:
    """Run startup validation and return success status."""
    validator = StartupValidator()
    success, errors, warnings = await validator.validate_all()
    
    # Log warnings
    for warning in warnings:
        logger.warning(f"⚠️  {warning}")
    
    # Log errors
    for error in errors:
        logger.error(f"❌ {error}")
    
    if not success:
        logger.error("\n" + "="*50)
        logger.error("STARTUP VALIDATION FAILED")
        logger.error("Please check your configuration and try again.")
        logger.error("="*50 + "\n")
    
    return success


if __name__ == "__main__":
    # Allow running this script directly for testing
    logging.basicConfig(level=logging.INFO)
    success = asyncio.run(run_startup_validation())
    sys.exit(0 if success else 1)