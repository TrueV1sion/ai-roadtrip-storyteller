"""
Distributed rate limiting middleware using Redis.
Replaces the in-memory rate limiter for production scalability.
"""
import time
from typing import Optional, Dict, Any, Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logger import logger
from app.core.distributed_rate_limiter import (
    DistributedRateLimiter,
    get_api_rate_limiter,
    get_auth_rate_limiter,
    get_ai_rate_limiter
)


class DistributedRateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for distributed rate limiting across multiple instances.
    """
    
    def __init__(
        self,
        app,
        default_limit: int = 1000,
        window_seconds: int = 3600,
        exclude_paths: Optional[list] = None,
        custom_limits: Optional[Dict[str, Dict[str, Any]]] = None
    ):
        """
        Initialize distributed rate limit middleware.
        
        Args:
            app: FastAPI application
            default_limit: Default requests per window
            window_seconds: Default time window in seconds
            exclude_paths: Paths to exclude from rate limiting
            custom_limits: Custom limits for specific paths
        """
        super().__init__(app)
        
        # Default rate limiter
        self.default_limiter = DistributedRateLimiter(
            requests_per_window=default_limit,
            window_seconds=window_seconds,
            enable_burst=True
        )
        
        # Specialized rate limiters
        self.auth_limiter = get_auth_rate_limiter()
        self.ai_limiter = get_ai_rate_limiter()
        self.api_limiter = get_api_rate_limiter()
        
        # Excluded paths
        self.exclude_paths = exclude_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/health",
            "/api/metrics"
        ]
        
        # Custom limits for specific endpoints
        self.custom_limits = custom_limits or {
            "/api/auth/login": {"requests": 10, "window": 300},  # 10 per 5 min
            "/api/auth/register": {"requests": 5, "window": 900},  # 5 per 15 min
            "/api/auth/password-reset": {"requests": 3, "window": 900},  # 3 per 15 min
            "/api/stories/generate": {"requests": 50, "window": 3600},  # 50 per hour
            "/api/voice/synthesize": {"requests": 100, "window": 3600},  # 100 per hour
            "/api/bookings": {"requests": 20, "window": 300},  # 20 per 5 min
        }
        
        logger.info("Distributed rate limiting middleware initialized")
    
    def _get_rate_limit_key(self, request: Request) -> str:
        """
        Extract rate limit key from request.
        Prioritizes authenticated user ID over IP address.
        """
        # Try to get user ID from request state (set by auth middleware)
        if hasattr(request.state, "user") and request.state.user:
            return f"user:{request.state.user.id}"
        
        # Try to get user ID from JWT token
        if hasattr(request.state, "user_id") and request.state.user_id:
            return f"user:{request.state.user_id}"
        
        # Fall back to IP address
        if request.client:
            return f"ip:{request.client.host}"
        
        return "unknown"
    
    def _select_limiter(self, path: str) -> DistributedRateLimiter:
        """Select appropriate rate limiter based on path."""
        # Check for auth endpoints
        if path.startswith("/api/auth"):
            return self.auth_limiter
        
        # Check for AI endpoints
        if any(ai_path in path for ai_path in ["/stories", "/voice", "/ai"]):
            return self.ai_limiter
        
        # Check for custom limits
        if path in self.custom_limits:
            config = self.custom_limits[path]
            return DistributedRateLimiter(
                requests_per_window=config["requests"],
                window_seconds=config["window"],
                enable_burst=False  # No burst for custom limits
            )
        
        # Default to API limiter
        return self.api_limiter
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request through distributed rate limiter."""
        # Skip excluded paths
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            return await call_next(request)
        
        # Skip OPTIONS requests
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Get rate limit key
        key = self._get_rate_limit_key(request)
        
        # Select appropriate limiter
        limiter = self._select_limiter(path)
        
        # Check rate limit
        allowed, retry_after, metadata = await limiter.check_rate_limit(key)
        
        if not allowed:
            # Log rate limit violation
            logger.warning(
                f"Rate limit exceeded - Key: {key}, Path: {path}, "
                f"Limit: {metadata.get('limit')}, Current: {metadata.get('current_usage')}"
            )
            
            # Return 429 response
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": retry_after,
                    "limit": metadata.get("limit"),
                    "window_seconds": metadata.get("window_seconds")
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(metadata.get("limit", 0)),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + retry_after)),
                    "X-RateLimit-Key": key.split(":")[0]  # Show key type (user/ip)
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to successful responses
        if metadata:
            response.headers["X-RateLimit-Limit"] = str(metadata.get("limit", 0))
            response.headers["X-RateLimit-Remaining"] = str(metadata.get("remaining", 0))
            response.headers["X-RateLimit-Reset"] = str(metadata.get("reset", 0))
            response.headers["X-RateLimit-Window"] = str(metadata.get("window_seconds", 0))
        
        return response


# Utility function to create custom rate limited endpoints
def create_endpoint_limiter(
    requests: int,
    window: int,
    burst: bool = False
) -> Callable:
    """
    Create a custom rate limiter for specific endpoints.
    
    Usage:
        limiter = create_endpoint_limiter(10, 60)
        
        @router.get("/endpoint")
        async def endpoint(request: Request):
            await limiter(request)
            ...
    """
    limiter = DistributedRateLimiter(
        requests_per_window=requests,
        window_seconds=window,
        enable_burst=burst
    )
    
    async def check_limit(request: Request, user_id: Optional[str] = None):
        """Check rate limit for request."""
        # Determine key
        if user_id:
            key = f"user:{user_id}"
        elif request.client:
            key = f"ip:{request.client.host}"
        else:
            key = "unknown"
        
        # Add endpoint to key for granular limiting
        key = f"{key}:{request.url.path}"
        
        # Check limit
        allowed, retry_after, metadata = await limiter.check_rate_limit(key)
        
        if not allowed:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "retry_after": retry_after,
                    "limit": metadata.get("limit"),
                    "remaining": 0
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(metadata.get("limit", 0)),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(metadata.get("reset", 0))
                }
            )
        
        return metadata
    
    return check_limit