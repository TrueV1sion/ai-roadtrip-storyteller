"""
Google Secret Manager integration for secure credential management.
This module provides a centralized way to access secrets in production.
"""
import os
from typing import Optional, Dict, Any
from functools import lru_cache
import json

from google.cloud import secretmanager
from google.api_core import exceptions as gcp_exceptions

from app.core.logger import logger


class SecretManager:
    """Manages access to secrets using Google Secret Manager."""
    
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.client = None
        self._cache: Dict[str, Any] = {}
        
        if self.project_id:
            try:
                self.client = secretmanager.SecretManagerServiceClient()
            except Exception as e:
                logger.error(f"Failed to initialize Secret Manager client: {e}")
    
    @lru_cache(maxsize=128)
    def get_secret(self, secret_id: str, version: str = "latest") -> Optional[str]:
        """
        Retrieve a secret from Google Secret Manager.
        
        Args:
            secret_id: The ID of the secret to retrieve
            version: The version of the secret (default: "latest")
            
        Returns:
            The secret value as a string, or None if not found
        """
        # Check local cache first
        cache_key = f"{secret_id}:{version}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # In development, fall back to environment variables
        if not self.client or os.getenv("ENVIRONMENT", "development") == "development":
            return os.getenv(secret_id.upper().replace("-", "_"))
        
        try:
            # Build the resource name
            name = f"projects/{self.project_id}/secrets/{secret_id}/versions/{version}"
            
            # Access the secret
            response = self.client.access_secret_version(request={"name": name})
            secret_value = response.payload.data.decode("UTF-8")
            
            # Cache the result
            self._cache[cache_key] = secret_value
            
            return secret_value
            
        except gcp_exceptions.NotFound:
            logger.warning(f"Secret {secret_id} not found in Secret Manager")
            # Fall back to environment variable
            return os.getenv(secret_id.upper().replace("-", "_"))
        except Exception as e:
            logger.error(f"Error accessing secret {secret_id}: {e}")
            return None
    
    def get_json_secret(self, secret_id: str, version: str = "latest") -> Optional[Dict[str, Any]]:
        """
        Retrieve a JSON secret from Google Secret Manager.
        
        Args:
            secret_id: The ID of the secret to retrieve
            version: The version of the secret (default: "latest")
            
        Returns:
            The secret value as a dictionary, or None if not found
        """
        secret_value = self.get_secret(secret_id, version)
        if secret_value:
            try:
                return json.loads(secret_value)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON secret {secret_id}")
                return None
        return None
    
    def create_or_update_secret(self, secret_id: str, secret_value: str) -> bool:
        """
        Create or update a secret in Google Secret Manager.
        
        Args:
            secret_id: The ID of the secret
            secret_value: The secret value to store
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.client or not self.project_id:
            logger.error("Secret Manager client not initialized")
            return False
            
        try:
            parent = f"projects/{self.project_id}"
            secret_name = f"{parent}/secrets/{secret_id}"
            
            # Try to create the secret
            try:
                secret = {"replication": {"automatic": {}}}
                self.client.create_secret(
                    request={
                        "parent": parent,
                        "secret_id": secret_id,
                        "secret": secret
                    }
                )
                logger.info(f"Created new secret: {secret_id}")
            except gcp_exceptions.AlreadyExists:
                logger.debug(f"Secret {secret_id} already exists")
            
            # Add the secret version
            payload = {"data": secret_value.encode("UTF-8")}
            response = self.client.add_secret_version(
                request={
                    "parent": secret_name,
                    "payload": payload
                }
            )
            
            # Update cache
            self._cache[f"{secret_id}:latest"] = secret_value
            
            logger.info(f"Successfully stored secret {secret_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create/update secret {secret_id}: {e}")
            return False
    
    def clear_cache(self):
        """Clear the internal secret cache."""
        self._cache.clear()
        self.get_secret.cache_clear()


# Global instance
secret_manager = SecretManager()


class SecureConfig:
    """Configuration class that uses Secret Manager for sensitive values."""
    
    @property
    def DATABASE_URL(self) -> str:
        """Get database URL from Secret Manager or environment."""
        return secret_manager.get_secret("database-url") or os.getenv("DATABASE_URL", "")
    
    @property
    def JWT_SECRET_KEY(self) -> str:
        """Get JWT secret from Secret Manager or environment."""
        return secret_manager.get_secret("jwt-secret-key") or os.getenv("JWT_SECRET_KEY", "")
    
    @property
    def GOOGLE_MAPS_API_KEY(self) -> str:
        """Get Google Maps API key from Secret Manager or environment."""
        return secret_manager.get_secret("google-maps-api-key") or os.getenv("GOOGLE_MAPS_API_KEY", "")
    
    @property
    def TICKETMASTER_API_KEY(self) -> str:
        """Get Ticketmaster API key from Secret Manager or environment."""
        return secret_manager.get_secret("ticketmaster-api-key") or os.getenv("TICKETMASTER_API_KEY", "")
    
    @property
    def OPENWEATHERMAP_API_KEY(self) -> str:
        """Get OpenWeatherMap API key from Secret Manager or environment."""
        return secret_manager.get_secret("openweathermap-api-key") or os.getenv("OPENWEATHERMAP_API_KEY", "")
    
    @property
    def REDIS_PASSWORD(self) -> str:
        """Get Redis password from Secret Manager or environment."""
        return secret_manager.get_secret("redis-password") or os.getenv("REDIS_PASSWORD", "")
    
    @property
    def ENCRYPTION_KEY(self) -> str:
        """Get encryption key from Secret Manager or environment."""
        return secret_manager.get_secret("encryption-key") or os.getenv("ENCRYPTION_KEY", "")
    
    @property
    def CSRF_SECRET_KEY(self) -> str:
        """Get CSRF secret from Secret Manager or environment."""
        return secret_manager.get_secret("csrf-secret-key") or os.getenv("CSRF_SECRET_KEY", self.JWT_SECRET_KEY)
    
    @property
    def VERTEX_AI_CREDENTIALS(self) -> Optional[Dict[str, Any]]:
        """Get Vertex AI service account credentials from Secret Manager."""
        return secret_manager.get_json_secret("vertex-ai-credentials")
    
    @property
    def SPOTIFY_CLIENT_ID(self) -> str:
        """Get Spotify client ID from Secret Manager or environment."""
        return secret_manager.get_secret("spotify-client-id") or os.getenv("SPOTIFY_CLIENT_ID", "")
    
    @property
    def SPOTIFY_CLIENT_SECRET(self) -> str:
        """Get Spotify client secret from Secret Manager or environment."""
        return secret_manager.get_secret("spotify-client-secret") or os.getenv("SPOTIFY_CLIENT_SECRET", "")


# Export secure configuration instance
secure_config = SecureConfig()