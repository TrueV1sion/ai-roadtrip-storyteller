"""
Redis-based token blacklist for production use.
Handles token revocation with automatic expiration.
"""
from typing import Optional
from datetime import datetime, timedelta
import redis
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class TokenBlacklist:
    """Redis-based token blacklist implementation."""
    
    def __init__(self):
        """Initialize Redis connection for token blacklist."""
        self.redis_client = None
        self.prefix = "token_blacklist:"
        self._connect()
    
    def _connect(self):
        """Connect to Redis."""
        try:
            # Parse Redis URL to get connection parameters
            if settings.REDIS_URL:
                self.redis_client = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                # Test connection
                self.redis_client.ping()
                logger.info("Connected to Redis for token blacklist")
            else:
                logger.warning("REDIS_URL not configured, token blacklist will not persist")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
    
    def add(self, token_id: str, expires_at: Optional[datetime] = None) -> bool:
        """
        Add a token to the blacklist.
        
        Args:
            token_id: The JWT token ID (jti claim)
            expires_at: Token expiration time for automatic cleanup
            
        Returns:
            bool: True if added successfully
        """
        if not self.redis_client:
            logger.warning("Redis not available, token blacklist operation skipped")
            return False
        
        try:
            key = f"{self.prefix}{token_id}"
            
            # Calculate TTL based on token expiration
            if expires_at:
                ttl = int((expires_at - datetime.utcnow()).total_seconds())
                if ttl > 0:
                    self.redis_client.setex(key, ttl, "revoked")
                else:
                    # Token already expired, no need to blacklist
                    return True
            else:
                # Default TTL of 30 days if no expiration provided
                self.redis_client.setex(key, 30 * 24 * 60 * 60, "revoked")
            
            logger.info(f"Token {token_id} added to blacklist")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add token to blacklist: {e}")
            return False
    
    def contains(self, token_id: str) -> bool:
        """
        Check if a token is in the blacklist.
        
        Args:
            token_id: The JWT token ID (jti claim)
            
        Returns:
            bool: True if token is blacklisted
        """
        if not self.redis_client:
            # If Redis is not available, we can't check blacklist
            # This is a fail-open approach - consider fail-closed for higher security
            return False
        
        try:
            key = f"{self.prefix}{token_id}"
            return self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Failed to check token blacklist: {e}")
            # Fail-open approach - consider security implications
            return False
    
    def remove(self, token_id: str) -> bool:
        """
        Remove a token from the blacklist (unrevoke).
        
        Args:
            token_id: The JWT token ID (jti claim)
            
        Returns:
            bool: True if removed successfully
        """
        if not self.redis_client:
            return False
        
        try:
            key = f"{self.prefix}{token_id}"
            result = self.redis_client.delete(key)
            if result > 0:
                logger.info(f"Token {token_id} removed from blacklist")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to remove token from blacklist: {e}")
            return False
    
    def clear_expired(self) -> int:
        """
        Clear expired tokens from blacklist.
        Redis handles this automatically with TTL, but this method
        can be used for manual cleanup if needed.
        
        Returns:
            int: Number of tokens cleared
        """
        # Redis automatically removes expired keys, so this is a no-op
        # Included for API compatibility
        return 0
    
    def get_blacklist_size(self) -> int:
        """
        Get the current size of the blacklist.
        
        Returns:
            int: Number of blacklisted tokens
        """
        if not self.redis_client:
            return 0
        
        try:
            # Use SCAN to count keys with our prefix
            count = 0
            cursor = 0
            while True:
                cursor, keys = self.redis_client.scan(
                    cursor=cursor,
                    match=f"{self.prefix}*",
                    count=100
                )
                count += len(keys)
                if cursor == 0:
                    break
            return count
        except Exception as e:
            logger.error(f"Failed to get blacklist size: {e}")
            return 0


# Global token blacklist instance
token_blacklist = TokenBlacklist()