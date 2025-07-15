"""
Google Secret Manager integration for secure credential management.
This module provides a secure way to access secrets in production.
"""

import os
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class SecretManagerClient:
    """
    Client for Google Secret Manager with caching and fallback support.
    
    In production, this will use Google Secret Manager.
    In development, it falls back to environment variables.
    """
    
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID", "roadtrip-460720")
        self.cache: Dict[str, tuple[Any, datetime]] = {}
        self.cache_ttl = timedelta(minutes=5)
        self._client = None
        self._initialized = False
        
    def _initialize_client(self):
        """Lazy initialization of Secret Manager client"""
        if self._initialized:
            return
            
        try:
            from google.cloud import secretmanager
            self._client = secretmanager.SecretManagerServiceClient()
            self._initialized = True
            logger.info("Google Secret Manager client initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Secret Manager client: {e}")
            logger.info("Falling back to environment variables")
            self._initialized = True
    
    def _is_cache_valid(self, cached_time: datetime) -> bool:
        """Check if cached value is still valid"""
        return datetime.now() - cached_time < self.cache_ttl
    
    def get_secret(self, secret_id: str, version: str = "latest") -> Optional[str]:
        """
        Retrieve a secret value from Secret Manager or environment variables.
        
        Args:
            secret_id: The ID of the secret to retrieve
            version: The version of the secret (default: "latest")
            
        Returns:
            The secret value as a string, or None if not found
        """
        # Check cache first
        if secret_id in self.cache:
            value, cached_time = self.cache[secret_id]
            if self._is_cache_valid(cached_time):
                return value
        
        # Initialize client if not done
        self._initialize_client()
        
        # Try Secret Manager first
        if self._client:
            try:
                name = f"projects/{self.project_id}/secrets/{secret_id}/versions/{version}"
                response = self._client.access_secret_version(request={"name": name})
                value = response.payload.data.decode("UTF-8")
                
                # Cache the value
                self.cache[secret_id] = (value, datetime.now())
                
                return value
            except Exception as e:
                logger.debug(f"Secret Manager lookup failed for {secret_id}: {e}")
        
        # Fallback to environment variables
        env_key = secret_id.upper().replace("-", "_")
        value = os.getenv(env_key)
        
        if value:
            # Cache the value
            self.cache[secret_id] = (value, datetime.now())
            logger.debug(f"Using environment variable for secret: {env_key}")
        else:
            logger.warning(f"Secret not found: {secret_id}")
        
        return value
    
    def create_secret(self, secret_id: str, secret_value: str) -> bool:
        """
        Create a new secret in Secret Manager.
        
        Args:
            secret_id: The ID for the new secret
            secret_value: The secret value to store
            
        Returns:
            True if successful, False otherwise
        """
        self._initialize_client()
        
        if not self._client:
            logger.error("Cannot create secret: Secret Manager client not available")
            return False
        
        try:
            from google.cloud import secretmanager
            
            # Create the secret
            parent = f"projects/{self.project_id}"
            secret = self._client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
            
            # Add the secret version
            self._client.add_secret_version(
                request={
                    "parent": secret.name,
                    "payload": {"data": secret_value.encode("UTF-8")},
                }
            )
            
            logger.info(f"Secret created successfully: {secret_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create secret {secret_id}: {e}")
            return False
    
    def update_secret(self, secret_id: str, secret_value: str) -> bool:
        """
        Update an existing secret by adding a new version.
        
        Args:
            secret_id: The ID of the secret to update
            secret_value: The new secret value
            
        Returns:
            True if successful, False otherwise
        """
        self._initialize_client()
        
        if not self._client:
            logger.error("Cannot update secret: Secret Manager client not available")
            return False
        
        try:
            # Add a new version to the existing secret
            parent = f"projects/{self.project_id}/secrets/{secret_id}"
            self._client.add_secret_version(
                request={
                    "parent": parent,
                    "payload": {"data": secret_value.encode("UTF-8")},
                }
            )
            
            # Clear cache for this secret
            if secret_id in self.cache:
                del self.cache[secret_id]
            
            logger.info(f"Secret updated successfully: {secret_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update secret {secret_id}: {e}")
            return False
    
    def delete_secret(self, secret_id: str) -> bool:
        """
        Delete a secret from Secret Manager.
        
        Args:
            secret_id: The ID of the secret to delete
            
        Returns:
            True if successful, False otherwise
        """
        self._initialize_client()
        
        if not self._client:
            logger.error("Cannot delete secret: Secret Manager client not available")
            return False
        
        try:
            name = f"projects/{self.project_id}/secrets/{secret_id}"
            self._client.delete_secret(request={"name": name})
            
            # Clear cache for this secret
            if secret_id in self.cache:
                del self.cache[secret_id]
            
            logger.info(f"Secret deleted successfully: {secret_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete secret {secret_id}: {e}")
            return False
    
    def clear_cache(self):
        """Clear all cached secrets"""
        self.cache.clear()
        logger.info("Secret cache cleared")


# Global instance
_secret_manager = None


def get_secret_manager() -> SecretManagerClient:
    """Get the global SecretManagerClient instance"""
    global _secret_manager
    if _secret_manager is None:
        _secret_manager = SecretManagerClient()
    return _secret_manager


def get_secret(secret_id: str, default: Optional[str] = None) -> Optional[str]:
    """
    Convenience function to get a secret value.
    
    Args:
        secret_id: The ID of the secret to retrieve
        default: Default value if secret not found
        
    Returns:
        The secret value or default
    """
    manager = get_secret_manager()
    value = manager.get_secret(secret_id)
    return value if value is not None else default