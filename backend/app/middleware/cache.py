"""
Intelligent caching middleware for performance optimization
"""

from functools import wraps
from typing import Optional, Callable, Any
import hashlib
import json
import time
from fastapi import Request
from app.core.cache import redis_client
import logging

logger = logging.getLogger(__name__)


class CacheMiddleware:
    """Intelligent caching middleware with performance optimization"""
    
    def __init__(self):
        self.cache_ttl = {
            "voice_synthesis": 3600,  # 1 hour
            "story_generation": 1800,  # 30 minutes
            "navigation_route": 300,  # 5 minutes
            "booking_search": 600  # 10 minutes
        }
    
    async def __call__(self, request: Request, call_next):
        # Skip caching for non-GET requests
        if request.method != "GET":
            return await call_next(request)
        
        # Generate cache key
        cache_key = self._generate_cache_key(request)
        
        # Check cache
        cached_response = await self._get_cached_response(cache_key)
        if cached_response:
            logger.info(f"Cache hit for {request.url.path}")
            return cached_response
        
        # Process request
        response = await call_next(request)
        
        # Cache successful responses
        if response.status_code == 200:
            await self._cache_response(cache_key, response)
        
        return response
    
    def _generate_cache_key(self, request: Request) -> str:
        """Generate unique cache key based on request"""
        key_parts = [
            request.url.path,
            str(request.query_params),
            request.headers.get("authorization", "")
        ]
        
        key_string = "|".join(key_parts)
        return f"cache:{hashlib.md5(key_string.encode()).hexdigest()}"
    
    async def _get_cached_response(self, cache_key: str) -> Optional[Any]:
        """Retrieve cached response"""
        try:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
        
        return None
    
    async def _cache_response(self, cache_key: str, response: Any):
        """Cache response with appropriate TTL"""
        try:
            # Determine TTL based on endpoint
            ttl = self._get_ttl_for_endpoint(response.url.path)
            
            # Serialize and cache
            response_data = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.body.decode() if hasattr(response.body, 'decode') else str(response.body),
                "cached_at": time.time()
            }
            
            await redis_client.setex(
                cache_key,
                ttl,
                json.dumps(response_data)
            )
            logger.info(f"Cached response for {ttl}s")
            
        except Exception as e:
            logger.error(f"Cache storage error: {e}")
    
    def _get_ttl_for_endpoint(self, path: str) -> int:
        """Get TTL for specific endpoint"""
        for endpoint, ttl in self.cache_ttl.items():
            if endpoint in path:
                return ttl
        return 300  # Default 5 minutes


def cache_endpoint(ttl: int = 300):
    """Decorator for caching specific endpoints"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function and arguments
            cache_key = f"func:{func.__name__}:{hashlib.md5(str(kwargs).encode()).hexdigest()}"
            
            # Check cache
            cached = await redis_client.get(cache_key)
            if cached:
                logger.info(f"Cache hit for {func.__name__}")
                return json.loads(cached)
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            await redis_client.setex(cache_key, ttl, json.dumps(result))
            
            return result
        
        return wrapper
    return decorator
