"""
Production Configuration - Enforces real API usage only
No mocks, no simulations, no fake data allowed.
"""

import os
import sys
from typing import Optional
from pydantic import BaseSettings, Field, validator


class ProductionSettings(BaseSettings):
    """Production-only settings that enforce real API usage"""
    
    # Override test mode to always be live
    TEST_MODE: str = Field(default="live", const=True, description="Always live in production")
    
    # Enforce environment
    ENVIRONMENT: str = Field(default="production", const=True)
    
    # Disable all mock modes
    USE_MOCK_APIS: bool = Field(default=False, const=True)
    MOCK_REDIS: bool = Field(default=False, const=True)
    SKIP_DB_CHECK: bool = Field(default=False, const=True)
    
    # Required API configurations
    GOOGLE_MAPS_API_KEY: str = Field(..., description="Required for navigation")
    GOOGLE_AI_PROJECT_ID: str = Field(..., description="Required for AI features")
    GOOGLE_APPLICATION_CREDENTIALS: str = Field(..., description="Required for Google Cloud services")
    OPENWEATHERMAP_API_KEY: str = Field(..., description="Required for weather features")
    TICKETMASTER_API_KEY: str = Field(..., description="Required for event detection")
    
    # Database must be configured
    DATABASE_URL: str = Field(..., description="PostgreSQL connection required")
    REDIS_URL: str = Field(..., description="Redis connection required")
    
    # Security keys
    SECRET_KEY: str = Field(..., min_length=32, description="Application secret key")
    JWT_SECRET_KEY: str = Field(..., min_length=32, description="JWT signing key")
    
    @validator("TEST_MODE", pre=True, always=True)
    def enforce_live_mode(cls, v):
        """Ensure we're always in live mode"""
        if v != "live":
            raise ValueError("Production must use TEST_MODE='live'")
        return "live"
    
    @validator("GOOGLE_MAPS_API_KEY", "GOOGLE_AI_PROJECT_ID", "OPENWEATHERMAP_API_KEY", "TICKETMASTER_API_KEY")
    def validate_api_keys(cls, v, field):
        """Ensure API keys are not dummy values"""
        if not v or v.startswith("your-") or v == "dummy" or len(v) < 10:
            raise ValueError(f"{field.name} must be a valid API key, not a placeholder")
        return v
    
    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        """Ensure database URL is not local/mock"""
        if "localhost" in v or "sqlite" in v:
            raise ValueError("Production must use a real PostgreSQL database, not localhost or SQLite")
        return v
    
    @validator("REDIS_URL")
    def validate_redis_url(cls, v):
        """Ensure Redis URL is not local/mock"""
        if "localhost" in v:
            raise ValueError("Production must use a real Redis instance, not localhost")
        return v
    
    @validator("SECRET_KEY", "JWT_SECRET_KEY")
    def validate_secret_keys(cls, v, field):
        """Ensure secret keys are secure"""
        if v == "dev-secret-key-change-in-production" or "dev" in v or "test" in v:
            raise ValueError(f"{field.name} must be a secure production key")
        return v
    
    class Config:
        # Prevent any environment variable from overriding critical settings
        fields = {
            'TEST_MODE': {'env': []},  # Cannot be overridden by env
            'ENVIRONMENT': {'env': []},  # Cannot be overridden by env
            'USE_MOCK_APIS': {'env': []},  # Cannot be overridden by env
            'MOCK_REDIS': {'env': []},  # Cannot be overridden by env
        }


def validate_production_readiness():
    """Validate that all production requirements are met"""
    errors = []
    
    # Check for mock mode environment variables
    dangerous_env_vars = [
        "USE_MOCK_APIS",
        "MOCK_REDIS",
        "SKIP_DB_CHECK",
        "OPENTABLE_MOCK_MODE",
        "RECREATION_GOV_MOCK_MODE"
    ]
    
    for var in dangerous_env_vars:
        if os.getenv(var, "").lower() in ["true", "1", "yes"]:
            errors.append(f"Environment variable {var} is set to enable mocking - not allowed in production")
    
    # Check TEST_MODE
    if os.getenv("TEST_MODE", "live") != "live":
        errors.append("TEST_MODE must be 'live' in production")
    
    # Verify critical services are available
    try:
        import google.cloud.texttospeech
    except ImportError:
        errors.append("Google Cloud Text-to-Speech library not installed")
    
    try:
        import google.cloud.speech
    except ImportError:
        errors.append("Google Cloud Speech-to-Text library not installed")
    
    # Check for Google Cloud credentials
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path or not os.path.exists(creds_path):
        errors.append("Google Cloud credentials file not found")
    
    if errors:
        print("PRODUCTION VALIDATION FAILED:")
        for error in errors:
            print(f"  ❌ {error}")
        sys.exit(1)
    
    print("✅ Production validation passed - all systems using real APIs")
    return True


# Don't instantiate here - let the application do it with proper env vars
# This module should only define the class and validation function