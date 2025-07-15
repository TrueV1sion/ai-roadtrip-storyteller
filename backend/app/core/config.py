import os
from typing import List, Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field, model_validator
import logging

# Use the existing logger setup if available, otherwise basic config
try:
    from app.core.logger import get_logger
    logger = get_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

# Import our new Secret Manager integration
try:
    from .secret_manager import secret_manager, secure_config
    logger.info("Secret Manager integration loaded successfully")
except ImportError:
    logger.warning("Secret Manager not available, falling back to environment variables")
    secret_manager = None
    secure_config = None


class Settings(BaseSettings):
    # App settings
    APP_TITLE: str = "AI Road Trip Storyteller"
    APP_DESCRIPTION: str = "An Imagineering-inspired road trip companion"
    APP_VERSION: str = "1.0.0"

    # API settings
    API_V1_STR: str = "/api/v1"
    # OPENAI_API_KEY: Optional[str] = None # Keep if needed, fetch below if None
    # GPT_MODEL_NAME: str = "gpt-4"

    # Google Cloud settings
    GOOGLE_AI_MODEL: str = "gemini-2.0-pro-exp" # Using Gemini 2.0 Pro experimental (latest available)
    GOOGLE_AI_PROJECT_ID: Optional[str] = Field(default=None, description="Google Cloud Project ID")
    GOOGLE_CLOUD_PROJECT_ID: Optional[str] = Field(default=None, description="Alternative project ID env var")
    GOOGLE_AI_LOCATION: str = "us-central1"
    GOOGLE_MAPS_API_KEY: Optional[str] = None
    GCS_BUCKET_NAME: Optional[str] = None
    
    # AI Provider settings
    DEFAULT_AI_PROVIDER: str = "google" # Options: google, anthropic, openai
    
    # AR settings
    AR_ENABLED: bool = True
    AR_MAX_POINTS: int = 10  # Maximum number of AR points to display at once
    AR_POINT_DISTANCE_THRESHOLD: float = 20.0  # Minimum distance between AR points in meters
    
    # Redis settings
    REDIS_URL: Optional[str] = None
    
    # Email/SMTP settings
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = True
    SMTP_FROM_EMAIL: Optional[str] = None
    
    # JWT settings
    JWT_SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "RS256"  # Updated to RS256 for production security
    JWT_ISSUER: str = "roadtrip-api"  # Token issuer for validation
    JWT_AUDIENCE: str = "roadtrip-client"  # Token audience for validation
    
    # Mock mode for development/testing
    TEST_MODE: str = Field(default="mock", description="Test mode: 'mock' or 'live'")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    DEBUG: bool = Field(default=True, description="Debug mode")

    # CORS settings
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:19006",
        "capacitor://localhost",
        "http://localhost"
    ]
    
    # Environment settings
    ENVIRONMENT: str = Field(default="development", description="Current environment (development, staging, production)")
    PRODUCTION: bool = Field(default=False, description="Production mode flag")
    
    # HTTPS settings - Force secure defaults in production
    FORCE_HTTPS: bool = Field(default=False, description="Force HTTPS redirects")
    SECURE_COOKIES: bool = Field(default=False, description="Use secure flag on cookies")

    # Database settings - Will be fetched if not set
    DATABASE_URL: Optional[str] = None

    # Security settings - Will be fetched if not set
    SECRET_KEY: Optional[str] = None
    CSRF_SECRET_KEY: Optional[str] = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Content Security Policy (CSP) settings
    CSP_ENABLED: bool = True
    # Additional allowed domains for CSP directives, by default 'self' is always included
    CSP_IMG_SRC: List[str] = ["data:", "https://maps.googleapis.com", "https://i.imgur.com"]
    CSP_STYLE_SRC: List[str] = ["'unsafe-inline'"]  # Allow inline styles
    CSP_SCRIPT_SRC: List[str] = []  # Only 'self' by default
    CSP_FONT_SRC: List[str] = ["https://fonts.gstatic.com"]
    CSP_CONNECT_SRC: List[str] = ["https://maps.googleapis.com", "https://api.spotify.com"]
    CSP_MEDIA_SRC: List[str] = ["https://storage.googleapis.com"]
    
    # Enable other security headers
    SECURITY_HSTS_ENABLED: bool = True  # HTTP Strict Transport Security
    SECURITY_XFO_ENABLED: bool = True   # X-Frame-Options
    SECURITY_CONTENT_TYPE_OPTIONS_ENABLED: bool = True  # X-Content-Type-Options
    SECURITY_REFERRER_POLICY_ENABLED: bool = True  # Referrer-Policy
    SECURITY_XSS_PROTECTION_ENABLED: bool = True  # X-XSS-Protection

    # TTS settings (API Key often not needed with ADC)
    TTS_PROVIDER: str = "google" # Defaulting to Google
    # TTS_API_KEY: Optional[str] = None # Fetch if needed

    # Spotify settings - Will be fetched if not set
    SPOTIFY_CLIENT_ID: Optional[str] = None
    SPOTIFY_CLIENT_SECRET: Optional[str] = None
    SPOTIFY_REDIRECT_URI: str = "http://localhost:8000/api/spotify/callback"
    
    # Required API Keys
    TICKETMASTER_API_KEY: Optional[str] = None
    OPENWEATHERMAP_API_KEY: Optional[str] = None
    RECREATION_GOV_API_KEY: Optional[str] = None
    
    # Partner API Keys (currently in mock mode)
    OPENTABLE_API_KEY: Optional[str] = None
    OPENTABLE_PARTNER_ID: Optional[str] = None
    SHELL_RECHARGE_API_KEY: Optional[str] = None
    
    # Flight tracking APIs
    FLIGHTSTATS_API_KEY: Optional[str] = None
    FLIGHTSTATS_APP_ID: Optional[str] = None
    FLIGHTAWARE_API_KEY: Optional[str] = None
    AVIATIONSTACK_API_KEY: Optional[str] = None
    FLIGHTLABS_API_KEY: Optional[str] = None
    
    # Google Cloud Storage settings
    GCS_BUCKET_NAME: Optional[str] = Field(default=None, description="Google Cloud Storage bucket for photos")
    GOOGLE_CLOUD_PROJECT: Optional[str] = Field(default=None, description="Google Cloud project ID for storage")
    
    # Additional booking APIs
    VIATOR_API_KEY: Optional[str] = None
    VIATOR_PARTNER_ID: Optional[str] = None
    
    RESY_CLIENT_ID: Optional[str] = None
    RESY_CLIENT_SECRET: Optional[str] = None
    RESY_API_KEY: Optional[str] = None
    
    CHARGEPOINT_CLIENT_ID: Optional[str] = None
    CHARGEPOINT_CLIENT_SECRET: Optional[str] = None
    CHARGEPOINT_API_KEY: Optional[str] = None

    # Pydantic Settings Config
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = 'ignore' # Ignore extra fields from env/secret manager if any

    # Use model_validator to fetch secrets after initial load from env/.env
    # but before final validation
    @model_validator(mode='before')
    @classmethod
    def load_secrets_from_gcp(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        # Check if running in CI environment
        is_ci = os.getenv('CI', 'false').lower() in ('true', '1', 't')
        if is_ci:
            logger.info("CI environment detected. Skipping fetch from Secret Manager.")
            return values # Rely solely on env/.env in CI

        # Get project ID from various sources
        project_id = (
            values.get("GOOGLE_AI_PROJECT_ID") or 
            values.get("GOOGLE_CLOUD_PROJECT_ID") or 
            os.getenv("GOOGLE_AI_PROJECT_ID") or 
            os.getenv("GOOGLE_CLOUD_PROJECT_ID") or
            os.getenv("GCP_PROJECT_ID")
        )
        
        # Set both project ID fields if we found one
        if project_id:
            values["GOOGLE_AI_PROJECT_ID"] = project_id
            values["GOOGLE_CLOUD_PROJECT_ID"] = project_id

        # Check if Secret Manager is available
        if not secret_manager:
            logger.info("Secret Manager client not available. Using environment variables only.")
            return values

        logger.info(f"Attempting to load secrets from GCP Secret Manager...")

        # Define which settings fields correspond to which secret IDs
        secrets_to_fetch = {
            # Core secrets
            "DATABASE_URL": "roadtrip-database-url",
            "SECRET_KEY": "roadtrip-secret-key",
            "JWT_SECRET_KEY": "roadtrip-jwt-secret",
            "CSRF_SECRET_KEY": "roadtrip-csrf-secret",
            "REDIS_URL": "roadtrip-redis-url",
            
            # Google Cloud
            "GCS_BUCKET_NAME": "roadtrip-gcs-bucket",
            
            # API Keys - Required
            "GOOGLE_MAPS_API_KEY": "roadtrip-google-maps-key",
            "TICKETMASTER_API_KEY": "roadtrip-ticketmaster-key",
            "OPENWEATHERMAP_API_KEY": "roadtrip-openweather-key",
            "RECREATION_GOV_API_KEY": "roadtrip-recreation-key",
            
            # API Keys - Optional
            "SPOTIFY_CLIENT_ID": "roadtrip-spotify-id",
            "SPOTIFY_CLIENT_SECRET": "roadtrip-spotify-secret",
            
            # Partner APIs
            "OPENTABLE_API_KEY": "roadtrip-opentable-key",
            "OPENTABLE_PARTNER_ID": "roadtrip-opentable-partner",
            "SHELL_RECHARGE_API_KEY": "roadtrip-shell-key",
            "CHARGEPOINT_CLIENT_ID": "roadtrip-chargepoint-id",
            "CHARGEPOINT_CLIENT_SECRET": "roadtrip-chargepoint-secret",
            "VIATOR_API_KEY": "roadtrip-viator-key",
            "VIATOR_PARTNER_ID": "roadtrip-viator-partner",
            "RESY_API_KEY": "roadtrip-resy-key",
            "RESY_CLIENT_ID": "roadtrip-resy-id",
            "RESY_CLIENT_SECRET": "roadtrip-resy-secret",
            
            # Flight tracking
            "FLIGHTSTATS_API_KEY": "roadtrip-flightstats-key",
            "FLIGHTSTATS_APP_ID": "roadtrip-flightstats-id",
            "FLIGHTAWARE_API_KEY": "roadtrip-flightaware-key",
            "AVIATIONSTACK_API_KEY": "roadtrip-aviationstack-key",
            "FLIGHTLABS_API_KEY": "roadtrip-flightlabs-key",
        }

        for field, secret_id in secrets_to_fetch.items():
            # Only fetch if the value wasn't provided by env/.env
            if not values.get(field):
                logger.info(f"'{field}' not found in env/.env, attempting fetch from Secret Manager (ID: {secret_id})...")
                secret_value = _get_secret(secret_id)
                if secret_value:
                    values[field] = secret_value
                    logger.debug(f"Successfully loaded '{field}' from Secret Manager.")
                else:
                    logger.debug(f"'{field}' not found in Secret Manager, will use default or fail validation if required.")
            else:
                logger.debug(f"Using value for '{field}' provided by environment or .env file.")


        # Ensure required fields that weren't fetched are handled by Pydantic validation
        # (e.g., if DATABASE_URL is still None after this, Pydantic will raise error if not Optional)

        return values
    
    @model_validator(mode='after')
    def enforce_production_security(self) -> 'Settings':
        """Enforce security settings in production environment."""
        if self.ENVIRONMENT == "production" or self.PRODUCTION:
            if not self.FORCE_HTTPS:
                logger.warning("FORCE_HTTPS was False in production, overriding to True")
                self.FORCE_HTTPS = True
            if not self.SECURE_COOKIES:
                logger.warning("SECURE_COOKIES was False in production, overriding to True")
                self.SECURE_COOKIES = True
            # Ensure we're not in debug mode in production
            if hasattr(self, 'DEBUG') and self.DEBUG:
                logger.warning("DEBUG was True in production, overriding to False")
                self.DEBUG = False
        return self
    
    def get_spotify_redirect_uri(self, request_scheme: str = None) -> str:
        """
        Get Spotify redirect URI based on environment and request scheme.
        
        Args:
            request_scheme: The scheme from the current request (http/https)
            
        Returns:
            Appropriate redirect URI
        """
        if self.ENVIRONMENT == "production":
            return "https://api.roadtrip.app/api/spotify/callback"
        elif self.ENVIRONMENT == "staging":
            return "https://api-staging.roadtrip.app/api/spotify/callback"
        elif request_scheme == "https":
            # Use HTTPS if the request came via HTTPS
            return self.SPOTIFY_REDIRECT_URI.replace("http://", "https://")
        else:
            return self.SPOTIFY_REDIRECT_URI
    
    def get_base_url(self, request_scheme: str = None) -> str:
        """
        Get base URL for the application based on environment.
        
        Args:
            request_scheme: The scheme from the current request (http/https)
            
        Returns:
            Base URL for the application
        """
        if self.ENVIRONMENT == "production":
            return "https://api.roadtrip.app"
        elif self.ENVIRONMENT == "staging":
            return "https://api-staging.roadtrip.app"
        elif request_scheme == "https":
            # Use HTTPS if the request came via HTTPS
            return "https://localhost:8000"
        else:
            return "http://localhost:8000"


# Instantiate settings
try:
    settings = Settings()
    # Log loaded settings (excluding secrets)
    log_settings = {k: v for k, v in settings.model_dump().items() if 'KEY' not in k and 'SECRET' not in k and 'PASSWORD' not in k and 'DATABASE_URL' not in k}
    logger.info(f"Settings loaded: {log_settings}")
except Exception as e:
    logger.critical(f"CRITICAL: Failed to initialize settings: {e}")
    # Depending on the deployment, might want to exit or raise
    raise ValueError(f"Failed to initialize settings: {e}") from e