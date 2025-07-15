"""
Production startup validation and configuration.
Ensures all security settings are properly configured before starting the application.
"""

import sys
import os
from typing import List, Tuple

from app.core.logger import logger
from app.core.config import settings
from app.core.production_https_config import (
    ProductionSecurityConfig,
    validate_production_environment
)
from app.core.database import engine
from app.core.cache import cache_manager
from sqlalchemy import text


class ProductionStartupValidator:
    """Validates production configuration before application startup."""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    async def validate_all(self) -> bool:
        """Run all production validation checks."""
        logger.info("Starting production validation...")
        
        # Check environment
        if settings.ENVIRONMENT != "production":
            self.warnings.append(
                f"Running production validation in {settings.ENVIRONMENT} environment"
            )
        
        # Validate security settings
        self._validate_security()
        
        # Validate database
        await self._validate_database()
        
        # Validate cache
        await self._validate_cache()
        
        # Validate external services
        await self._validate_external_services()
        
        # Validate SSL/TLS
        self._validate_ssl()
        
        # Report results
        if self.errors:
            logger.error("Production validation failed:")
            for error in self.errors:
                logger.error(f"  ❌ {error}")
            return False
        
        if self.warnings:
            logger.warning("Production validation warnings:")
            for warning in self.warnings:
                logger.warning(f"  ⚠️  {warning}")
        
        logger.info("✅ Production validation passed")
        return True
    
    def _validate_security(self):
        """Validate security configuration."""
        # HTTPS enforcement
        if not settings.FORCE_HTTPS:
            self.errors.append("FORCE_HTTPS must be True in production")
        
        # Secure cookies
        if not settings.SECURE_COOKIES:
            self.errors.append("SECURE_COOKIES must be True in production")
        
        # Debug mode
        if settings.DEBUG:
            self.errors.append("DEBUG must be False in production")
        
        # Secret keys
        insecure_values = [
            "dev-secret-key-change-in-production",
            "your-secret-key-here",
            "changeme",
            "secret"
        ]
        
        if not settings.JWT_SECRET_KEY or any(
            insecure in settings.JWT_SECRET_KEY.lower() 
            for insecure in insecure_values
        ):
            self.errors.append("JWT_SECRET_KEY is not secure")
        
        if not settings.SECRET_KEY or any(
            insecure in settings.SECRET_KEY.lower() 
            for insecure in insecure_values
        ):
            self.errors.append("SECRET_KEY is not secure")
        
        # CORS settings
        if "*" in settings.ALLOWED_ORIGINS:
            self.errors.append("CORS allows all origins (security risk)")
        
        # CSRF settings
        if not hasattr(settings, "CSRF_SECRET_KEY") or not settings.CSRF_SECRET_KEY:
            self.errors.append("CSRF_SECRET_KEY not configured")
    
    async def _validate_database(self):
        """Validate database connectivity and configuration."""
        try:
            # Test connection
            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                if not result:
                    self.errors.append("Database connection test failed")
            
            # Check for production configuration
            if "localhost" in settings.DATABASE_URL:
                self.warnings.append("Database URL contains localhost")
            
            if "roadtrip123" in settings.DATABASE_URL:
                self.errors.append("Database using development password")
            
            # Verify SSL connection
            if "sslmode=require" not in settings.DATABASE_URL:
                self.warnings.append("Database connection not using SSL")
                
        except Exception as e:
            self.errors.append(f"Database validation failed: {e}")
    
    async def _validate_cache(self):
        """Validate Redis cache connectivity."""
        try:
            # Test Redis connection
            await cache_manager.ping()
            
            # Set and get test value
            test_key = "production_validation_test"
            test_value = "test_value"
            
            await cache_manager.set(test_key, test_value, expire=10)
            retrieved = await cache_manager.get(test_key)
            
            if retrieved != test_value:
                self.errors.append("Redis cache test failed")
            
            # Clean up
            await cache_manager.delete(test_key)
            
        except Exception as e:
            self.errors.append(f"Cache validation failed: {e}")
    
    async def _validate_external_services(self):
        """Validate external service configurations."""
        # Check API keys are set
        required_keys = [
            ("GOOGLE_MAPS_API_KEY", "Google Maps"),
            ("VERTEX_AI_PROJECT_ID", "Vertex AI"),
            ("TICKETMASTER_API_KEY", "Ticketmaster"),
            ("OPENWEATHERMAP_API_KEY", "OpenWeatherMap")
        ]
        
        for key, service in required_keys:
            if not getattr(settings, key, None):
                self.warnings.append(f"{service} API key not configured")
        
        # Check for test/development keys
        test_indicators = ["test", "demo", "sandbox", "development"]
        
        for key, service in required_keys:
            value = getattr(settings, key, "")
            if any(indicator in value.lower() for indicator in test_indicators):
                self.warnings.append(f"{service} appears to be using a test API key")
    
    def _validate_ssl(self):
        """Validate SSL/TLS configuration."""
        # Check if SSL certificates are configured
        ssl_cert = os.getenv("SSL_CERT_PATH")
        ssl_key = os.getenv("SSL_KEY_PATH")
        
        if not ssl_cert or not ssl_key:
            self.warnings.append(
                "SSL certificates not configured (may be handled by load balancer)"
            )
        
        # Verify HSTS is enabled
        if not settings.SECURITY_HSTS_ENABLED:
            self.errors.append("HSTS must be enabled in production")
    
    def get_startup_report(self) -> str:
        """Generate startup validation report."""
        report = ["=" * 60]
        report.append("PRODUCTION STARTUP VALIDATION REPORT")
        report.append("=" * 60)
        
        report.append(f"\nEnvironment: {settings.ENVIRONMENT}")
        report.append(f"Debug Mode: {settings.DEBUG}")
        report.append(f"HTTPS Enforcement: {settings.FORCE_HTTPS}")
        report.append(f"Secure Cookies: {settings.SECURE_COOKIES}")
        
        if self.errors:
            report.append(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                report.append(f"  - {error}")
        
        if self.warnings:
            report.append(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                report.append(f"  - {warning}")
        
        if not self.errors:
            report.append("\n✅ All production checks passed!")
        
        report.append("\n" + "=" * 60)
        
        return "\n".join(report)


async def run_production_startup_validation() -> bool:
    """Run production startup validation."""
    validator = ProductionStartupValidator()
    
    try:
        # Run validation
        is_valid = await validator.validate_all()
        
        # Print report
        print(validator.get_startup_report())
        
        # Log report
        if is_valid:
            logger.info("Production startup validation completed successfully")
        else:
            logger.error("Production startup validation failed")
        
        return is_valid
        
    except Exception as e:
        logger.error(f"Production startup validation error: {e}")
        return False


# Quick validation for deployment scripts
def validate_deployment_config() -> Tuple[bool, List[str]]:
    """Quick validation for deployment configuration."""
    errors = []
    
    # Check environment variables
    required_env_vars = [
        "GOOGLE_CLOUD_PROJECT",
        "DATABASE_URL",
        "REDIS_URL",
        "ENVIRONMENT"
    ]
    
    for var in required_env_vars:
        if not os.getenv(var):
            errors.append(f"Environment variable {var} not set")
    
    # Check production flag
    if os.getenv("ENVIRONMENT") != "production":
        errors.append("ENVIRONMENT must be set to 'production'")
    
    # Check debug flag
    if os.getenv("DEBUG", "").lower() == "true":
        errors.append("DEBUG must not be true in production")
    
    # Check HTTPS flag
    if os.getenv("FORCE_HTTPS", "").lower() != "true":
        errors.append("FORCE_HTTPS must be true in production")
    
    return len(errors) == 0, errors


if __name__ == "__main__":
    # Run validation when script is executed directly
    import asyncio
    
    is_valid, errors = validate_deployment_config()
    
    if not is_valid:
        logger.error("Deployment configuration errors:")
        for error in errors:
            logger.error(f"  - {error}")
        sys.exit(1)
    
    # Run async validation
    asyncio.run(run_production_startup_validation())