"""
Advanced Response Caching System with Smart Invalidation
"""
from typing import Optional, Any, Dict, List, Callable, Union
from datetime import datetime, timedelta
import hashlib
import json
import pickle
from functools import wraps
import asyncio
from enum import Enum

import redis.asyncio as redis
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class CacheStrategy(str, Enum):
    """Cache strategies for different use cases"""
    AGGRESSIVE = "aggressive"  # Long TTL, cache everything
    MODERATE = "moderate"      # Medium TTL, selective caching
    CONSERVATIVE = "conservative"  # Short TTL, minimal caching
    SMART = "smart"           # Adaptive TTL based on content


class ResponseCache:
    """
    Advanced response caching system with smart invalidation and compression.
    """
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis: Optional[redis.Redis] = None
        self._connected = False
        self.default_ttl = 300  # 5 minutes
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "invalidations": 0,
            "errors": 0
        }
    
    async def connect(self):
        """Connect to Redis"""
        if not self._connected:
            try:
                self._redis = await redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=False  # Handle binary data
                )
                self._connected = True
                logger.info("Response cache connected to Redis")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self._connected = False
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self._redis:
            await self._redis.close()
            self._connected = False
    
    def _generate_cache_key(
        self, 
        path: str, 
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        extra: Optional[str] = None
    ) -> str:
        """Generate a unique cache key"""
        key_parts = [
            "response_cache",
            method.upper(),
            path
        ]
        
        # Add sorted parameters to key
        if params:
            sorted_params = sorted(params.items())
            params_str = "&".join([f"{k}={v}" for k, v in sorted_params])
            key_parts.append(params_str)
        
        # Add user context if needed
        if user_id is not None:
            key_parts.append(f"user:{user_id}")
        
        # Add extra context
        if extra:
            key_parts.append(extra)
        
        # Create hash of the key for consistent length
        key_str = ":".join(key_parts)
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        
        return f"cache:{key_hash}"
    
    def _determine_ttl(
        self, 
        strategy: CacheStrategy, 
        content_type: str,
        content_size: int
    ) -> int:
        """Determine TTL based on caching strategy"""
        base_ttls = {
            CacheStrategy.AGGRESSIVE: 3600,    # 1 hour
            CacheStrategy.MODERATE: 600,       # 10 minutes
            CacheStrategy.CONSERVATIVE: 60,    # 1 minute
            CacheStrategy.SMART: 300          # 5 minutes (will be adjusted)
        }
        
        ttl = base_ttls.get(strategy, self.default_ttl)
        
        if strategy == CacheStrategy.SMART:
            # Adjust TTL based on content characteristics
            if "static" in content_type or "image" in content_type:
                ttl = 7200  # 2 hours for static content
            elif content_size < 1024:  # Small responses
                ttl = 900   # 15 minutes
            elif content_size > 1024 * 100:  # Large responses
                ttl = 300   # 5 minutes
            
            # Adjust based on time of day (cache longer during off-peak)
            current_hour = datetime.now().hour
            if 0 <= current_hour <= 6:  # Off-peak hours
                ttl = int(ttl * 1.5)
        
        return ttl
    
    async def get(
        self, 
        cache_key: str,
        deserialize: bool = True
    ) -> Optional[Any]:
        """Get value from cache"""
        if not self._connected:
            await self.connect()
        
        if not self._connected:
            return None
        
        try:
            value = await self._redis.get(cache_key)
            
            if value is None:
                self.cache_stats["misses"] += 1
                return None
            
            self.cache_stats["hits"] += 1
            
            if deserialize:
                # Try JSON first, then pickle
                try:
                    return json.loads(value)
                except Exception as e:
                    return pickle.loads(value)
            
            return value
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self.cache_stats["errors"] += 1
            return None
    
    async def set(
        self, 
        cache_key: str,
        value: Any,
        ttl: Optional[int] = None,
        serialize: bool = True
    ) -> bool:
        """Set value in cache"""
        if not self._connected:
            await self.connect()
        
        if not self._connected:
            return False
        
        try:
            if serialize:
                # Try JSON for better interoperability, fall back to pickle
                try:
                    value = json.dumps(value)
                except Exception as e:
                    value = pickle.dumps(value)
            
            ttl = ttl or self.default_ttl
            await self._redis.setex(cache_key, ttl, value)
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            self.cache_stats["errors"] += 1
            return False
    
    async def invalidate(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern"""
        if not self._connected:
            await self.connect()
        
        if not self._connected:
            return 0
        
        try:
            # Find all keys matching pattern
            keys = []
            async for key in self._redis.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                deleted = await self._redis.delete(*keys)
                self.cache_stats["invalidations"] += deleted
                return deleted
            
            return 0
            
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            self.cache_stats["errors"] += 1
            return 0
    
    async def invalidate_user_cache(self, user_id: int):
        """Invalidate all cache entries for a specific user"""
        pattern = f"cache:*user:{user_id}*"
        return await self.invalidate(pattern)
    
    async def invalidate_path_cache(self, path: str):
        """Invalidate all cache entries for a specific path"""
        pattern = f"cache:*{path}*"
        return await self.invalidate(pattern)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = (self.cache_stats["hits"] / total * 100) if total > 0 else 0
        
        # Get Redis info
        redis_info = {}
        if self._connected:
            try:
                info = await self._redis.info()
                redis_info = {
                    "used_memory": info.get("used_memory_human", "N/A"),
                    "connected_clients": info.get("connected_clients", 0),
                    "total_commands": info.get("total_commands_processed", 0),
                    "keyspace": info.get("db0", {})
                }
            except Exception as e:
                pass
        
        return {
            **self.cache_stats,
            "hit_rate": f"{hit_rate:.2f}%",
            "total_requests": total,
            "redis_info": redis_info
        }
    
    def cache_response(
        self,
        strategy: CacheStrategy = CacheStrategy.MODERATE,
        ttl: Optional[int] = None,
        key_func: Optional[Callable] = None,
        user_specific: bool = False,
        invalidate_on: Optional[List[str]] = None
    ):
        """
        Decorator for caching FastAPI responses.
        
        Args:
            strategy: Caching strategy to use
            ttl: Override TTL in seconds
            key_func: Custom function to generate cache key
            user_specific: Whether to cache per user
            invalidate_on: List of HTTP methods that invalidate this cache
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(request: Request, *args, **kwargs):
                # Generate cache key
                if key_func:
                    cache_key = key_func(request, *args, **kwargs)
                else:
                    user_id = None
                    if user_specific and hasattr(request.state, "user"):
                        user_id = request.state.user.id
                    
                    cache_key = self._generate_cache_key(
                        path=str(request.url.path),
                        method=request.method,
                        params=dict(request.query_params),
                        user_id=user_id
                    )
                
                # Check if this is an invalidating request
                if invalidate_on and request.method in invalidate_on:
                    await self.invalidate(f"{cache_key}*")
                
                # Try to get from cache for GET requests
                if request.method == "GET":
                    cached = await self.get(cache_key)
                    if cached is not None:
                        # Return cached response
                        return JSONResponse(
                            content=cached["content"],
                            status_code=cached.get("status_code", 200),
                            headers={
                                **cached.get("headers", {}),
                                "X-Cache": "HIT",
                                "X-Cache-Key": cache_key[-8:]
                            }
                        )
                
                # Execute the function
                response = await func(request, *args, **kwargs)
                
                # Cache the response for GET requests
                if request.method == "GET" and response.status_code == 200:
                    # Determine TTL
                    content_size = len(json.dumps(response.body) if hasattr(response, 'body') else "")
                    cache_ttl = ttl or self._determine_ttl(
                        strategy=strategy,
                        content_type=response.headers.get("content-type", ""),
                        content_size=content_size
                    )
                    
                    # Prepare cache data
                    cache_data = {
                        "content": response.body if hasattr(response, 'body') else None,
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                        "cached_at": datetime.utcnow().isoformat()
                    }
                    
                    # Store in cache
                    await self.set(cache_key, cache_data, cache_ttl)
                    
                    # Add cache headers
                    response.headers["X-Cache"] = "MISS"
                    response.headers["X-Cache-TTL"] = str(cache_ttl)
                    response.headers["X-Cache-Key"] = cache_key[-8:]
                
                return response
            
            return wrapper
        return decorator


# Global response cache instance
response_cache = ResponseCache()


# Cache management utilities
async def clear_all_cache():
    """Clear all response cache"""
    return await response_cache.invalidate("cache:*")


async def clear_user_cache(user_id: int):
    """Clear cache for specific user"""
    return await response_cache.invalidate_user_cache(user_id)


async def clear_path_cache(path: str):
    """Clear cache for specific path"""
    return await response_cache.invalidate_path_cache(path)


async def get_cache_statistics():
    """Get cache statistics"""
    return await response_cache.get_stats()


# Middleware for automatic cache invalidation
class CacheInvalidationMiddleware:
    """Middleware to automatically invalidate cache on data mutations"""
    
    def __init__(self, app):
        self.app = app
        self.invalidation_rules = {
            # Path patterns and their invalidation rules
            r"/api/bookings": ["GET /api/bookings*", "GET /api/users/*/bookings"],
            r"/api/stories": ["GET /api/stories*", "GET /api/journeys/*/stories"],
            r"/api/users": ["GET /api/users*", "GET /api/auth/me"],
        }
    
    async def __call__(self, request: Request, call_next):
        response = await call_next(request)
        
        # Check if this is a mutating request
        if request.method in ["POST", "PUT", "PATCH", "DELETE"] and response.status_code < 400:
            # Invalidate related caches
            for pattern, invalidations in self.invalidation_rules.items():
                if pattern in str(request.url.path):
                    for invalidation in invalidations:
                        method, path_pattern = invalidation.split(" ", 1)
                        await response_cache.invalidate(f"cache:*{method}*{path_pattern}")
        
        return response