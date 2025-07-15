"""
Enhanced rate limiting specifically for authentication endpoints.
Implements different limits for login, registration, and password reset.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import asyncio
from collections import defaultdict
from app.core.logger import get_logger
from app.core.cache import get_cache

logger = get_logger(__name__)


class AuthRateLimiter:
    """
    Specialized rate limiter for authentication endpoints with Redis backend.
    Tracks attempts by IP address and implements exponential backoff.
    """
    
    # Rate limit configurations per endpoint
    LIMITS = {
        "login": {"attempts": 5, "window": 60},  # 5 attempts per minute
        "register": {"attempts": 3, "window": 3600},  # 3 attempts per hour
        "reset_password": {"attempts": 3, "window": 3600},  # 3 attempts per hour
        "verify_2fa": {"attempts": 10, "window": 300},  # 10 attempts per 5 minutes
    }
    
    # Lockout configuration
    LOCKOUT_THRESHOLD = 5  # Failed attempts before lockout
    LOCKOUT_DURATION = 1800  # 30 minutes in seconds
    
    def __init__(self):
        self.cache = None
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Lazy initialization of cache connection"""
        if not self._initialized:
            self.cache = await get_cache()
            self._initialized = True
    
    def _get_cache_key(self, endpoint: str, identifier: str) -> str:
        """Generate cache key for rate limiting"""
        return f"rate_limit:{endpoint}:{identifier}"
    
    def _get_lockout_key(self, identifier: str) -> str:
        """Generate cache key for account lockout"""
        return f"auth_lockout:{identifier}"
    
    async def check_rate_limit(
        self, 
        endpoint: str, 
        identifier: str,
        increment: bool = True
    ) -> Tuple[bool, Optional[int]]:
        """
        Check if request is within rate limit.
        
        Args:
            endpoint: The endpoint being accessed (login, register, etc.)
            identifier: IP address or user identifier
            increment: Whether to increment the counter
            
        Returns:
            Tuple of (allowed, seconds_until_reset)
        """
        await self._ensure_initialized()
        
        if endpoint not in self.LIMITS:
            logger.warning(f"Unknown endpoint for rate limiting: {endpoint}")
            return True, None
        
        limit_config = self.LIMITS[endpoint]
        cache_key = self._get_cache_key(endpoint, identifier)
        
        try:
            # Get current attempt count
            current = await self.cache.get(cache_key)
            current_count = int(current) if current else 0
            
            # Check if limit exceeded
            if current_count >= limit_config["attempts"]:
                ttl = await self.cache.ttl(cache_key)
                logger.warning(
                    f"Rate limit exceeded for {endpoint} by {identifier}. "
                    f"Attempts: {current_count}/{limit_config['attempts']}"
                )
                return False, ttl
            
            # Increment counter if requested
            if increment:
                if current_count == 0:
                    # First attempt, set with expiration
                    await self.cache.setex(
                        cache_key, 
                        limit_config["window"], 
                        1
                    )
                else:
                    # Increment existing counter
                    await self.cache.incr(cache_key)
            
            return True, None
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open to avoid blocking legitimate users
            return True, None
    
    async def check_lockout(self, identifier: str) -> Tuple[bool, Optional[int]]:
        """
        Check if an account/IP is locked out.
        
        Args:
            identifier: User email or IP address
            
        Returns:
            Tuple of (is_locked, seconds_remaining)
        """
        await self._ensure_initialized()
        
        lockout_key = self._get_lockout_key(identifier)
        
        try:
            lockout_data = await self.cache.get(lockout_key)
            if lockout_data:
                ttl = await self.cache.ttl(lockout_key)
                logger.warning(f"Account locked out: {identifier}")
                return True, ttl
            
            return False, None
            
        except Exception as e:
            logger.error(f"Lockout check failed: {e}")
            return False, None
    
    async def record_failed_attempt(
        self, 
        identifier: str,
        ip_address: str
    ) -> Tuple[int, bool]:
        """
        Record a failed authentication attempt.
        
        Args:
            identifier: User email or username
            ip_address: IP address of the attempt
            
        Returns:
            Tuple of (total_attempts, is_locked_out)
        """
        await self._ensure_initialized()
        
        failed_key = f"auth_failed:{identifier}"
        
        try:
            # Increment failed attempts
            current = await self.cache.get(failed_key)
            attempts = int(current) + 1 if current else 1
            
            # Set/update with 1 hour expiration
            await self.cache.setex(failed_key, 3600, attempts)
            
            # Check if we should lock out
            if attempts >= self.LOCKOUT_THRESHOLD:
                lockout_key = self._get_lockout_key(identifier)
                await self.cache.setex(
                    lockout_key,
                    self.LOCKOUT_DURATION,
                    f"{attempts}:{ip_address}:{datetime.utcnow().isoformat()}"
                )
                
                logger.warning(
                    f"Account locked out after {attempts} failed attempts: {identifier} from {ip_address}"
                )
                
                # Also lock out the IP
                ip_lockout_key = self._get_lockout_key(ip_address)
                await self.cache.setex(
                    ip_lockout_key,
                    self.LOCKOUT_DURATION,
                    f"ip_lockout:{identifier}"
                )
                
                return attempts, True
            
            return attempts, False
            
        except Exception as e:
            logger.error(f"Failed to record failed attempt: {e}")
            return 0, False
    
    async def clear_failed_attempts(self, identifier: str):
        """Clear failed attempts after successful login"""
        await self._ensure_initialized()
        
        failed_key = f"auth_failed:{identifier}"
        try:
            await self.cache.delete(failed_key)
        except Exception as e:
            logger.error(f"Failed to clear failed attempts: {e}")
    
    async def unlock_account(self, identifier: str):
        """Manually unlock an account (admin function)"""
        await self._ensure_initialized()
        
        lockout_key = self._get_lockout_key(identifier)
        failed_key = f"auth_failed:{identifier}"
        
        try:
            await self.cache.delete(lockout_key)
            await self.cache.delete(failed_key)
            logger.info(f"Account manually unlocked: {identifier}")
        except Exception as e:
            logger.error(f"Failed to unlock account: {e}")
            raise
    
    async def get_lockout_info(self, identifier: str) -> Optional[Dict]:
        """Get detailed lockout information"""
        await self._ensure_initialized()
        
        lockout_key = self._get_lockout_key(identifier)
        
        try:
            lockout_data = await self.cache.get(lockout_key)
            if not lockout_data:
                return None
            
            # Parse lockout data
            parts = lockout_data.split(":")
            if len(parts) >= 3:
                attempts = int(parts[0])
                ip_address = parts[1]
                locked_at = parts[2]
                ttl = await self.cache.ttl(lockout_key)
                
                return {
                    "attempts": attempts,
                    "ip_address": ip_address,
                    "locked_at": locked_at,
                    "seconds_remaining": ttl
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get lockout info: {e}")
            return None


# Global instance
_auth_rate_limiter = None


def get_auth_rate_limiter() -> AuthRateLimiter:
    """Get the global AuthRateLimiter instance"""
    global _auth_rate_limiter
    if _auth_rate_limiter is None:
        _auth_rate_limiter = AuthRateLimiter()
    return _auth_rate_limiter