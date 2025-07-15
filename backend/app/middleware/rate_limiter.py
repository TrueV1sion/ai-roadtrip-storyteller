"""
Redis-based Rate Limiting Middleware
"""

from typing import Optional, Callable
import time
import json
from fastapi import Request, Response, HTTPException, status
from backend.app.core.cache import redis_client
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Redis-based rate limiting with sliding window"""
    
    def __init__(
        self,
        requests: int = 100,
        window: int = 60,
        identifier: Optional[Callable] = None
    ):
        self.requests = requests
        self.window = window
        self.identifier = identifier or self._default_identifier
    
    def _default_identifier(self, request: Request) -> str:
        """Default identifier using IP address"""
        # Get real IP behind proxy
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0]
        else:
            ip = request.client.host
        
        return f"ratelimit:{ip}"
    
    async def __call__(self, request: Request, call_next):
        # Get identifier
        identifier = self.identifier(request)
        
        # Check rate limit
        allowed = await self._check_rate_limit(identifier)
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        limit_info = await self._get_limit_info(identifier)
        response.headers["X-RateLimit-Limit"] = str(self.requests)
        response.headers["X-RateLimit-Remaining"] = str(limit_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(limit_info["reset"])
        
        return response
    
    async def _check_rate_limit(self, identifier: str) -> bool:
        """Check if request is within rate limit"""
        now = time.time()
        window_start = now - self.window
        
        # Use Redis sorted set for sliding window
        pipe = redis_client.pipeline()
        
        # Remove old entries
        pipe.zremrangebyscore(identifier, 0, window_start)
        
        # Count requests in window
        pipe.zcard(identifier)
        
        # Add current request
        pipe.zadd(identifier, {str(now): now})
        
        # Set expiry
        pipe.expire(identifier, self.window + 1)
        
        results = await pipe.execute()
        request_count = results[1]
        
        return request_count < self.requests
    
    async def _get_limit_info(self, identifier: str) -> dict:
        """Get rate limit information"""
        now = time.time()
        window_start = now - self.window
        
        # Count requests
        request_count = await redis_client.zcount(
            identifier,
            window_start,
            now
        )
        
        # Get oldest request
        oldest = await redis_client.zrange(
            identifier,
            0,
            0,
            withscores=True
        )
        
        if oldest:
            reset_time = oldest[0][1] + self.window
        else:
            reset_time = now + self.window
        
        return {
            "remaining": max(0, self.requests - request_count),
            "reset": int(reset_time)
        }


# Endpoint-specific rate limiters
class EndpointRateLimiter:
    """Configure different rate limits for different endpoints"""
    
    def __init__(self):
        self.limiters = {
            # Strict limit for auth endpoints
            "/api/v1/auth/login": RateLimiter(5, 300),  # 5 per 5 minutes
            "/api/v1/auth/register": RateLimiter(3, 3600),  # 3 per hour
            
            # Moderate limit for AI endpoints
            "/api/v1/voice/synthesize": RateLimiter(30, 60),  # 30 per minute
            "/api/v1/stories/generate": RateLimiter(20, 60),  # 20 per minute
            
            # Higher limit for regular endpoints
            "/api/v1/trips": RateLimiter(100, 60),  # 100 per minute
            "/api/v1/bookings": RateLimiter(100, 60),  # 100 per minute
            
            # Default limit
            "default": RateLimiter(200, 60)  # 200 per minute
        }
    
    async def __call__(self, request: Request, call_next):
        # Get appropriate limiter
        path = request.url.path
        limiter = self.limiters.get(path, self.limiters["default"])
        
        # Apply rate limit
        return await limiter(request, call_next)


# User-based rate limiting
class UserRateLimiter(RateLimiter):
    """Rate limiting based on authenticated user"""
    
    def __init__(self, requests: int = 1000, window: int = 3600):
        super().__init__(requests, window)
    
    def _default_identifier(self, request: Request) -> str:
        """Use user ID as identifier"""
        # Get user from request state (set by auth middleware)
        user = getattr(request.state, "user", None)
        
        if user:
            return f"ratelimit:user:{user.id}"
        else:
            # Fall back to IP for unauthenticated requests
            return super()._default_identifier(request)


# DDoS protection
class DDoSProtection:
    """Advanced DDoS protection"""
    
    def __init__(self):
        self.burst_threshold = 1000  # requests
        self.burst_window = 10  # seconds
        self.block_duration = 3600  # 1 hour
    
    async def check_burst(self, ip: str) -> bool:
        """Check for burst traffic patterns"""
        key = f"burst:{ip}"
        current = await redis_client.incr(key)
        
        if current == 1:
            await redis_client.expire(key, self.burst_window)
        
        if current > self.burst_threshold:
            # Block IP
            await redis_client.setex(
                f"blocked:{ip}",
                self.block_duration,
                "burst_traffic"
            )
            return False
        
        return True
    
    async def is_blocked(self, ip: str) -> bool:
        """Check if IP is blocked"""
        return await redis_client.exists(f"blocked:{ip}")
    
    async def __call__(self, request: Request, call_next):
        # Get IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0]
        else:
            ip = request.client.host
        
        # Check if blocked
        if await self.is_blocked(ip):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Check burst
        if not await self.check_burst(ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Burst traffic detected"
            )
        
        return await call_next(request)


# Initialize middleware
endpoint_rate_limiter = EndpointRateLimiter()
user_rate_limiter = UserRateLimiter()
ddos_protection = DDoSProtection()
