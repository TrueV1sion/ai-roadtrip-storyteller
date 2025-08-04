"""
Centralized settings manager for accessing configuration values.
This module provides a clean interface for accessing settings throughout the application.
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.config import Settings

# Global settings instance will be injected here
_settings: Optional['Settings'] = None


def inject_settings(settings: 'Settings'):
    """Inject the settings instance (called once at startup)"""
    global _settings
    _settings = settings


def get_settings() -> 'Settings':
    """Get the current settings instance"""
    if _settings is None:
        # Fallback: try to import and create settings
        from app.core.config import settings
        return settings
    return _settings


# Convenience functions for commonly accessed settings
def get_api_key(key_name: str) -> Optional[str]:
    """Get an API key from settings"""
    settings = get_settings()
    return getattr(settings, key_name, None)


def get_database_url() -> str:
    """Get database URL"""
    settings = get_settings()
    return settings.DATABASE_URL or ""


def get_secret_key() -> str:
    """Get application secret key"""
    settings = get_settings()
    return settings.SECRET_KEY or ""


def is_mock_mode() -> bool:
    """Check if running in mock mode"""
    settings = get_settings()
    return getattr(settings, 'TEST_MODE', 'live') == 'mock'


def get_google_project_id() -> str:
    """Get Google Cloud project ID"""
    settings = get_settings()
    return settings.GOOGLE_AI_PROJECT_ID