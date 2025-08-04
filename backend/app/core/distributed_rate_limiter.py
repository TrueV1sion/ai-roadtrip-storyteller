"""
Distributed rate limiting using Redis for production scalability.
Replaces in-memory rate limiting to work across multiple instances.
"""
import time
import asyncio
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
import json

from app.core.logger import logger
from app.core.cache import cache_manager
from app.core.config import settings


class DistributedRateLimiter:
    """
    Redis-based distributed rate limiter using sliding window algorithm.
    Works across multiple application instances.
    """
    
    def __init__(
        self,
        requests_per_window: int = 100,
        window_seconds: int = 60,
        enable_burst: bool = True,
        burst_multiplier: float = 1.5
    ):
        """
        Initialize distributed rate limiter.
        
        Args:
            requests_per_window: Number of requests allowed per window
            window_seconds: Time window in seconds
            enable_burst: Allow burst traffic
            burst_multiplier: Burst allowance multiplier
        """
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.enable_burst = enable_burst
        self.burst_limit = int(requests_per_window * burst_multiplier) if enable_burst else requests_per_window
        
    async def check_rate_limit(
        self,
        key: str,
        cost: int = 1
    ) -> Tuple[bool, Optional[int], Optional[Dict[str, Any]]]:
        """
        Check if request is within rate limit.
        
        Args:
            key: Unique identifier (e.g., user_id, IP address)
            cost: Cost of this request (default 1)
            
        Returns:
            Tuple of (allowed, retry_after_seconds, metadata)
        """
        current_time = time.time()
        window_start = current_time - self.window_seconds
        
        # Create Redis key
        redis_key = f"rate_limit:{key}"
        
        try:
            # Use Redis pipeline for atomic operations
            pipe = cache_manager.redis_client.pipeline()
            
            # Remove old entries outside the window
            pipe.zremrangebyscore(redis_key, 0, window_start)
            
            # Count requests in current window
            pipe.zcard(redis_key)
            
            # Execute pipeline
            results = await pipe.execute()
            current_count = results[1]
            
            # Check if limit exceeded
            limit = self.burst_limit if self.enable_burst else self.requests_per_window
            
            if current_count + cost > limit:
                # Calculate retry after
                pipe = cache_manager.redis_client.pipeline()
                pipe.zrange(redis_key, 0, 0, withscores=True)
                oldest = await pipe.execute()
                
                if oldest and oldest[0]:
                    oldest_timestamp = float(oldest[0][0][1])
                    retry_after = int(oldest_timestamp + self.window_seconds - current_time) + 1
                else:
                    retry_after = self.window_seconds
                
                metadata = {
                    "limit": limit,
                    "window_seconds": self.window_seconds,
                    "current_usage": current_count,
                    "retry_after": retry_after
                }
                
                logger.warning(f"Rate limit exceeded for {key}: {current_count}/{limit}")
                return False, retry_after, metadata
            
            # Add current request
            pipe = cache_manager.redis_client.pipeline()
            
            # Add request with timestamp as score
            for _ in range(cost):
                pipe.zadd(redis_key, {f"{current_time}:{_}": current_time})
            
            # Set expiry on the key
            pipe.expire(redis_key, self.window_seconds + 60)
            
            # Execute pipeline
            await pipe.execute()
            
            # Calculate remaining requests
            remaining = limit - (current_count + cost)
            
            metadata = {
                "limit": limit,
                "remaining": remaining,
                "reset": int(current_time + self.window_seconds),
                "window_seconds": self.window_seconds
            }
            
            return True, None, metadata
            
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            # On error, allow request but log
            return True, None, None
    
    async def reset_limit(self, key: str):
        """Reset rate limit for a specific key."""
        redis_key = f"rate_limit:{key}"
        await cache_manager.redis_client.delete(redis_key)
        logger.info(f"Rate limit reset for {key}")
    
    async def get_usage(self, key: str) -> Dict[str, Any]:
        """Get current usage statistics for a key."""
        current_time = time.time()
        window_start = current_time - self.window_seconds
        redis_key = f"rate_limit:{key}"
        
        try:
            # Remove old entries and count current
            pipe = cache_manager.redis_client.pipeline()
            pipe.zremrangebyscore(redis_key, 0, window_start)
            pipe.zcard(redis_key)
            results = await pipe.execute()
            
            current_count = results[1]
            limit = self.burst_limit if self.enable_burst else self.requests_per_window
            
            return {
                "key": key,
                "current_usage": current_count,
                "limit": limit,
                "remaining": max(0, limit - current_count),
                "window_seconds": self.window_seconds,
                "reset_time": int(current_time + self.window_seconds)
            }
        except Exception as e:
            logger.error(f"Error getting rate limit usage: {e}")
            return {}


class RateLimitMiddleware:
    """
    FastAPI middleware for distributed rate limiting.
    """
    
    def __init__(
        self,
        default_limit: int = 100,
        window_seconds: int = 60,
        key_func: Optional[callable] = None,
        exclude_paths: Optional[list] = None
    ):
        """
        Initialize rate limit middleware.
        
        Args:
            default_limit: Default requests per window
            window_seconds: Time window in seconds
            key_func: Function to extract rate limit key from request
            exclude_paths: Paths to exclude from rate limiting
        """
        self.limiter = DistributedRateLimiter(
            requests_per_window=default_limit,
            window_seconds=window_seconds
        )
        self.key_func = key_func
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
    
    async def __call__(self, request, call_next):
        """Process request through rate limiter."""
        # Skip excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Extract rate limit key
        if self.key_func:
            key = self.key_func(request)
        else:
            # Default: use IP address
            key = request.client.host if request.client else "unknown"
        
        # Check rate limit
        allowed, retry_after, metadata = await self.limiter.check_rate_limit(key)
        
        if not allowed:
            # Return 429 Too Many Requests
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "retry_after": retry_after,
                    "limit": metadata.get("limit"),
                    "window_seconds": metadata.get("window_seconds")
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(metadata.get("limit")),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + retry_after))
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        if metadata:
            response.headers["X-RateLimit-Limit"] = str(metadata.get("limit"))
            response.headers["X-RateLimit-Remaining"] = str(metadata.get("remaining"))
            response.headers["X-RateLimit-Reset"] = str(metadata.get("reset"))
        
        return response


# Pre-configured rate limiters for different scenarios
def get_api_rate_limiter() -> DistributedRateLimiter:
    """Get rate limiter for general API endpoints."""
    return DistributedRateLimiter(
        requests_per_window=1000,
        window_seconds=3600,  # 1 hour
        enable_burst=True
    )


def get_auth_rate_limiter() -> DistributedRateLimiter:
    """Get rate limiter for authentication endpoints."""
    return DistributedRateLimiter(
        requests_per_window=20,
        window_seconds=900,  # 15 minutes
        enable_burst=False  # No burst for auth
    )


def get_ai_rate_limiter() -> DistributedRateLimiter:
    """Get rate limiter for AI endpoints (expensive operations)."""
    return DistributedRateLimiter(
        requests_per_window=100,
        window_seconds=3600,  # 1 hour
        enable_burst=True,
        burst_multiplier=1.2  # Small burst allowance
    )


def get_booking_rate_limiter() -> DistributedRateLimiter:
    """Get rate limiter for booking endpoints."""
    return DistributedRateLimiter(
        requests_per_window=50,
        window_seconds=300,  # 5 minutes
        enable_burst=False  # No burst for bookings
    )


# Decorator for route-level rate limiting
def rate_limit(
    requests: int = 100,
    window: int = 60,
    key_func: Optional[callable] = None
):
    """
    Decorator for applying rate limiting to specific routes.
    
    Usage:
        @router.get("/endpoint")
        @rate_limit(requests=10, window=60)
        async def endpoint():
            ...
    """
    limiter = DistributedRateLimiter(
        requests_per_window=requests,
        window_seconds=window
    )
    
    def decorator(func):
        async def wrapper(request, *args, **kwargs):
            # Extract key
            if key_func:
                key = key_func(request)
            else:
                # Try to get user_id from request state
                if hasattr(request.state, "user_id"):
                    key = f"user:{request.state.user_id}"
                else:
                    key = request.client.host if request.client else "unknown"
            
            # Check rate limit
            allowed, retry_after, metadata = await limiter.check_rate_limit(key)
            
            if not allowed:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Rate limit exceeded",
                        "retry_after": retry_after
                    },
                    headers={
                        "Retry-After": str(retry_after)
                    }
                )
            
            # Call original function
            return await func(request, *args, **kwargs)
        
        return wrapper
    return decorator