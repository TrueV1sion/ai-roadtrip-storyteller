"""
Production-Ready Rate Limiting Middleware

Implements distributed rate limiting using Redis with sliding window algorithm.
Supports per-user, per-IP, per-endpoint, and global rate limits with proper
429 responses and rate limit headers.
"""

import time
import logging
from typing import Optional, Dict, Any, Tuple, List
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from redis.exceptions import RedisError
import json
import hashlib

from app.core.cache import redis_client
from app.core.config import settings

logger = logging.getLogger(__name__)


class RateLimitConfig:
    """Configuration for rate limiting rules."""
    
    def __init__(
        self,
        requests: int,
        window_seconds: int,
        burst_multiplier: float = 1.5,
        key_prefix: str = "rl"
    ):
        self.requests = requests
        self.window_seconds = window_seconds
        self.burst_multiplier = burst_multiplier
        self.burst_limit = int(requests * burst_multiplier)
        self.key_prefix = key_prefix


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Production-ready rate limiting middleware with Redis backend."""
    
    # Default rate limits
    DEFAULT_LIMITS = {
        "global": RateLimitConfig(10000, 3600),  # 10k/hour globally
        "per_ip": RateLimitConfig(1000, 3600),   # 1k/hour per IP
        "per_user": RateLimitConfig(2000, 3600), # 2k/hour per user
    }
    
    # Endpoint-specific limits
    ENDPOINT_LIMITS = {
        # Authentication endpoints - strict limits
        "/api/v1/auth/login": RateLimitConfig(5, 300, burst_multiplier=1.0),
        "/api/v1/auth/register": RateLimitConfig(3, 900, burst_multiplier=1.0),
        "/api/v1/auth/password-reset": RateLimitConfig(3, 900, burst_multiplier=1.0),
        "/api/v1/auth/verify-2fa": RateLimitConfig(10, 300, burst_multiplier=1.0),
        
        # AI endpoints - expensive operations
        "/api/v1/stories/generate": RateLimitConfig(50, 3600, burst_multiplier=1.2),
        "/api/v1/voice/synthesize": RateLimitConfig(100, 3600, burst_multiplier=1.2),
        "/api/v1/ai/chat": RateLimitConfig(200, 3600, burst_multiplier=1.5),
        
        # Booking endpoints - moderate limits
        "/api/v1/bookings": RateLimitConfig(20, 300, burst_multiplier=1.0),
        "/api/v1/bookings/search": RateLimitConfig(50, 300, burst_multiplier=1.2),
        
        # Data endpoints
        "/api/v1/trips": RateLimitConfig(100, 300, burst_multiplier=1.5),
        "/api/v1/stories": RateLimitConfig(200, 300, burst_multiplier=1.5),
    }
    
    # Paths to exclude from rate limiting
    EXCLUDED_PATHS = [
        "/health",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/health",
        "/api/metrics",
        "/favicon.ico",
    ]
    
    def __init__(
        self,
        app,
        enable_global_limit: bool = True,
        enable_per_ip_limit: bool = True,
        enable_per_user_limit: bool = True,
        enable_endpoint_limits: bool = True,
        custom_limits: Optional[Dict[str, RateLimitConfig]] = None,
        admin_bypass: bool = True
    ):
        super().__init__(app)
        self.enable_global_limit = enable_global_limit
        self.enable_per_ip_limit = enable_per_ip_limit
        self.enable_per_user_limit = enable_per_user_limit
        self.enable_endpoint_limits = enable_endpoint_limits
        self.admin_bypass = admin_bypass
        
        # Merge custom limits with defaults
        if custom_limits:
            self.ENDPOINT_LIMITS.update(custom_limits)
            
        logger.info(
            f"Rate Limiting Middleware initialized - "
            f"Global: {enable_global_limit}, Per-IP: {enable_per_ip_limit}, "
            f"Per-User: {enable_per_user_limit}, Endpoints: {enable_endpoint_limits}"
        )
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with rate limiting checks."""
        # Skip excluded paths
        if self._is_excluded_path(request.url.path):
            return await call_next(request)
        
        # Skip OPTIONS requests
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Check if Redis is available
        if not redis_client.is_available:
            logger.warning("Redis not available, skipping rate limiting")
            return await call_next(request)
        
        # Extract identifiers
        user_id = self._get_user_id(request)
        client_ip = self._get_client_ip(request)
        
        # Check admin bypass
        if self.admin_bypass and user_id and await self._is_admin(user_id):
            logger.debug(f"Admin bypass for user {user_id}")
            response = await call_next(request)
            response.headers["X-RateLimit-Bypass"] = "admin"
            return response
        
        # Collect all applicable rate limits
        rate_checks = []
        
        # Global limit
        if self.enable_global_limit:
            rate_checks.append((
                "global",
                "global",
                self.DEFAULT_LIMITS["global"]
            ))
        
        # Per-IP limit
        if self.enable_per_ip_limit and client_ip:
            rate_checks.append((
                f"ip:{client_ip}",
                "per_ip",
                self.DEFAULT_LIMITS["per_ip"]
            ))
        
        # Per-user limit
        if self.enable_per_user_limit and user_id:
            rate_checks.append((
                f"user:{user_id}",
                "per_user",
                self.DEFAULT_LIMITS["per_user"]
            ))
        
        # Endpoint-specific limit
        if self.enable_endpoint_limits:
            endpoint_config = self._get_endpoint_config(request.url.path)
            if endpoint_config:
                key = f"endpoint:{request.url.path}:"
                if user_id:
                    key += f"user:{user_id}"
                else:
                    key += f"ip:{client_ip}"
                rate_checks.append((key, "endpoint", endpoint_config))
        
        # Check all rate limits
        for key, limit_type, config in rate_checks:
            allowed, retry_after, metadata = await self._check_rate_limit(
                key, config, request
            )
            
            if not allowed:
                logger.warning(
                    f"Rate limit exceeded - Type: {limit_type}, Key: {key}, "
                    f"Path: {request.url.path}, User: {user_id}, IP: {client_ip}"
                )
                
                # Log to monitoring/intrusion detection
                await self._log_rate_limit_violation(
                    limit_type, key, request, metadata
                )
                
                return self._build_rate_limit_response(
                    retry_after, metadata, limit_type
                )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers for the most restrictive limit
        await self._add_rate_limit_headers(response, rate_checks)
        
        return response
    
    async def _check_rate_limit(
        self,
        key: str,
        config: RateLimitConfig,
        request: Request
    ) -> Tuple[bool, Optional[int], Dict[str, Any]]:
        """Check rate limit using Redis sliding window algorithm."""
        current_time = time.time()
        window_start = current_time - config.window_seconds
        
        # Create Redis key with prefix
        redis_key = f"{config.key_prefix}:{key}"
        
        try:
            # Use pipeline for atomic operations
            pipe = redis_client.client.pipeline()
            
            # Remove old entries outside the window
            pipe.zremrangebyscore(redis_key, 0, window_start)
            
            # Count requests in current window
            pipe.zcard(redis_key)
            
            # Execute pipeline
            results = pipe.execute()
            current_count = results[1]
            
            # Determine limit (with burst if applicable)
            limit = config.burst_limit if current_count < config.requests else config.requests
            
            # Check if limit exceeded
            if current_count >= limit:
                # Get oldest request to calculate retry_after
                oldest = redis_client.client.zrange(
                    redis_key, 0, 0, withscores=True
                )
                
                if oldest:
                    oldest_timestamp = oldest[0][1]
                    retry_after = int(
                        oldest_timestamp + config.window_seconds - current_time
                    ) + 1
                else:
                    retry_after = config.window_seconds
                
                metadata = {
                    "limit": limit,
                    "window_seconds": config.window_seconds,
                    "current_usage": current_count,
                    "remaining": 0,
                    "reset": int(current_time + retry_after),
                    "burst_active": limit > config.requests
                }
                
                return False, retry_after, metadata
            
            # Add current request with unique identifier
            request_id = f"{current_time}:{hashlib.md5(f'{key}{current_time}'.encode()).hexdigest()[:8]}"
            pipe = redis_client.client.pipeline()
            pipe.zadd(redis_key, {request_id: current_time})
            pipe.expire(redis_key, config.window_seconds + 60)  # Extra time for cleanup
            pipe.execute()
            
            # Calculate remaining requests
            remaining = limit - (current_count + 1)
            
            metadata = {
                "limit": limit,
                "remaining": remaining,
                "reset": int(current_time + config.window_seconds),
                "window_seconds": config.window_seconds,
                "current_usage": current_count + 1,
                "burst_active": limit > config.requests
            }
            
            return True, None, metadata
            
        except RedisError as e:
            logger.error(f"Redis error in rate limiter: {e}")
            # Fail open - allow request on Redis errors
            return True, None, {}
        except Exception as e:
            logger.error(f"Unexpected error in rate limiter: {e}")
            return True, None, {}
    
    def _build_rate_limit_response(
        self,
        retry_after: int,
        metadata: Dict[str, Any],
        limit_type: str
    ) -> JSONResponse:
        """Build 429 response with proper headers."""
        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limit_exceeded",
                "message": "Too many requests. Please retry after some time.",
                "retry_after": retry_after,
                "limit": metadata.get("limit"),
                "window_seconds": metadata.get("window_seconds"),
                "limit_type": limit_type,
                "burst_active": metadata.get("burst_active", False)
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(metadata.get("limit", 0)),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(metadata.get("reset", 0)),
                "X-RateLimit-Type": limit_type,
                "Cache-Control": "no-cache, no-store, must-revalidate"
            }
        )
    
    async def _add_rate_limit_headers(
        self,
        response: Response,
        rate_checks: List[Tuple[str, str, RateLimitConfig]]
    ) -> None:
        """Add rate limit headers for the most restrictive limit."""
        if not rate_checks:
            return
        
        # Find the most restrictive limit (least remaining)
        most_restrictive = None
        min_remaining = float('inf')
        
        for key, limit_type, config in rate_checks:
            redis_key = f"{config.key_prefix}:{key}"
            try:
                current_count = redis_client.client.zcard(redis_key)
                remaining = config.requests - current_count
                
                if remaining < min_remaining:
                    min_remaining = remaining
                    most_restrictive = {
                        "limit": config.requests,
                        "remaining": max(0, remaining),
                        "reset": int(time.time() + config.window_seconds),
                        "type": limit_type
                    }
            except:
                pass
        
        if most_restrictive:
            response.headers["X-RateLimit-Limit"] = str(most_restrictive["limit"])
            response.headers["X-RateLimit-Remaining"] = str(most_restrictive["remaining"])
            response.headers["X-RateLimit-Reset"] = str(most_restrictive["reset"])
            response.headers["X-RateLimit-Type"] = most_restrictive["type"]
    
    def _get_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request."""
        # Check request state (set by auth middleware)
        if hasattr(request.state, "user") and request.state.user:
            return str(request.state.user.id)
        
        if hasattr(request.state, "user_id") and request.state.user_id:
            return str(request.state.user_id)
        
        return None
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, considering proxies."""
        # Check X-Forwarded-For header (comma-separated list)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get the first IP in the chain (original client)
            client_ip = forwarded_for.split(",")[0].strip()
            return client_ip
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to direct client IP
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _is_excluded_path(self, path: str) -> bool:
        """Check if path should be excluded from rate limiting."""
        for excluded in self.EXCLUDED_PATHS:
            if path.startswith(excluded):
                return True
        return False
    
    def _get_endpoint_config(self, path: str) -> Optional[RateLimitConfig]:
        """Get endpoint-specific rate limit configuration."""
        # Exact match
        if path in self.ENDPOINT_LIMITS:
            return self.ENDPOINT_LIMITS[path]
        
        # Prefix match for parameterized routes
        for endpoint, config in self.ENDPOINT_LIMITS.items():
            if path.startswith(endpoint.rstrip("/")):
                return config
        
        return None
    
    async def _is_admin(self, user_id: str) -> bool:
        """Check if user is admin (from cache or database)."""
        # Check cache first
        cache_key = f"user:admin:{user_id}"
        is_admin = redis_client.get(cache_key)
        
        if is_admin is not None:
            return bool(is_admin)
        
        # TODO: Query database for admin status
        # For now, return False
        return False
    
    async def _log_rate_limit_violation(
        self,
        limit_type: str,
        key: str,
        request: Request,
        metadata: Dict[str, Any]
    ) -> None:
        """Log rate limit violation for monitoring and intrusion detection."""
        violation_data = {
            "timestamp": time.time(),
            "limit_type": limit_type,
            "key": key,
            "path": request.url.path,
            "method": request.method,
            "client_ip": self._get_client_ip(request),
            "user_id": self._get_user_id(request),
            "user_agent": request.headers.get("User-Agent", "unknown"),
            "limit": metadata.get("limit"),
            "current_usage": metadata.get("current_usage"),
            "burst_active": metadata.get("burst_active", False)
        }
        
        # Store in Redis for analysis
        violation_key = f"rate_limit:violations:{int(time.time() / 60)}"
        try:
            redis_client.client.lpush(violation_key, json.dumps(violation_data))
            redis_client.client.expire(violation_key, 86400)  # Keep for 24 hours
        except:
            pass
        
        # Log warning for monitoring
        logger.warning(f"Rate limit violation: {json.dumps(violation_data)}")


# Utility functions for manual rate limit management

async def reset_rate_limit(key: str, limit_type: str = "all") -> bool:
    """Reset rate limit for a specific key."""
    try:
        if limit_type == "all":
            # Reset all limits for this key
            pattern = f"rl:*{key}*"
            cursor = 0
            while True:
                cursor, keys = redis_client.client.scan(
                    cursor, match=pattern, count=100
                )
                if keys:
                    redis_client.client.delete(*keys)
                if cursor == 0:
                    break
        else:
            # Reset specific limit type
            redis_key = f"rl:{limit_type}:{key}"
            redis_client.client.delete(redis_key)
        
        logger.info(f"Rate limit reset for key: {key}, type: {limit_type}")
        return True
    except Exception as e:
        logger.error(f"Failed to reset rate limit: {e}")
        return False


async def get_rate_limit_status(key: str) -> Dict[str, Any]:
    """Get current rate limit status for a key."""
    status = {}
    
    try:
        # Check all limit types
        for limit_type, config in RateLimitMiddleware.DEFAULT_LIMITS.items():
            redis_key = f"{config.key_prefix}:{limit_type}:{key}"
            current_count = redis_client.client.zcard(redis_key)
            
            status[limit_type] = {
                "current": current_count,
                "limit": config.requests,
                "remaining": max(0, config.requests - current_count),
                "window_seconds": config.window_seconds,
                "reset": int(time.time() + config.window_seconds)
            }
        
        return status
    except Exception as e:
        logger.error(f"Failed to get rate limit status: {e}")
        return {}


async def get_rate_limit_violations(
    start_time: Optional[int] = None,
    end_time: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Get rate limit violations within time range."""
    violations = []
    
    try:
        # Default to last hour
        if not end_time:
            end_time = int(time.time())
        if not start_time:
            start_time = end_time - 3600
        
        # Scan for violation keys
        pattern = "rate_limit:violations:*"
        cursor = 0
        
        while True:
            cursor, keys = redis_client.client.scan(
                cursor, match=pattern, count=100
            )
            
            for key in keys:
                # Extract timestamp from key
                key_time = int(key.split(":")[-1]) * 60
                
                if start_time <= key_time <= end_time:
                    # Get violations from this key
                    items = redis_client.client.lrange(key, 0, -1)
                    for item in items:
                        try:
                            violation = json.loads(item)
                            if start_time <= violation["timestamp"] <= end_time:
                                violations.append(violation)
                        except:
                            pass
            
            if cursor == 0:
                break
        
        # Sort by timestamp
        violations.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return violations
    except Exception as e:
        logger.error(f"Failed to get rate limit violations: {e}")
        return []