"""
Enhanced Multi-Layer Caching System with Performance Optimizations
Provides in-memory, Redis, and persistent caching with intelligent cache management
"""

import asyncio
import time
import json
import hashlib
import logging
from typing import Any, Dict, Optional, Callable, TypeVar, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import pickle
import threading
from concurrent.futures import ThreadPoolExecutor

from app.core.cache import redis_client
from app.core.logger import get_logger

logger = get_logger(__name__)
T = TypeVar('T')


class CacheLevel(Enum):
    """Cache levels in order of priority."""
    MEMORY = "memory"
    REDIS = "redis"
    PERSISTENT = "persistent"


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    value: Any
    created_at: float
    ttl: Optional[int]
    access_count: int = 0
    last_accessed: float = 0
    
    def is_expired(self) -> bool:
        """Check if the cache entry is expired."""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    def touch(self):
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = time.time()


class MemoryCache:
    """In-memory cache with LRU eviction and size limits."""
    
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 100):
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self._lock = threading.RLock()
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache."""
        with self._lock:
            entry = self.cache.get(key)
            if entry is None:
                return None
            
            if entry.is_expired():
                del self.cache[key]
                return None
            
            entry.touch()
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in memory cache."""
        with self._lock:
            try:
                # Check memory usage (approximate)
                estimated_size = len(str(value))
                if estimated_size > self.max_memory_bytes:
                    logger.warning(f"Cache value too large: {estimated_size} bytes")
                    return False
                
                # Create cache entry
                entry = CacheEntry(
                    value=value,
                    created_at=time.time(),
                    ttl=ttl
                )
                
                # Add to cache
                self.cache[key] = entry
                
                # Evict if necessary
                self._evict_if_needed()
                
                return True
            except Exception as e:
                logger.error(f"Error setting memory cache key {key}: {e}")
                return False
    
    def delete(self, key: str) -> bool:
        """Delete key from memory cache."""
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def clear(self):
        """Clear all entries from memory cache."""
        with self._lock:
            self.cache.clear()
    
    def _evict_if_needed(self):
        """Evict entries if cache is full."""
        if len(self.cache) <= self.max_size:
            return
        
        # Sort by last accessed time and access count
        sorted_entries = sorted(
            self.cache.items(),
            key=lambda x: (x[1].last_accessed, x[1].access_count)
        )
        
        # Remove least recently used entries
        entries_to_remove = len(self.cache) - self.max_size + 10  # Remove extra for buffer
        for i in range(min(entries_to_remove, len(sorted_entries))):
            key = sorted_entries[i][0]
            del self.cache[key]
        
        logger.debug(f"Evicted {entries_to_remove} entries from memory cache")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hit_rate": self._calculate_hit_rate(),
                "expired_entries": sum(1 for entry in self.cache.values() if entry.is_expired())
            }
    
    def _calculate_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total_accesses = sum(entry.access_count for entry in self.cache.values())
        if total_accesses == 0:
            return 0.0
        return len(self.cache) / total_accesses


class EnhancedCacheManager:
    """Multi-layer cache manager with intelligent caching strategies."""
    
    def __init__(self):
        self.memory_cache = MemoryCache()
        self.redis_client = redis_client
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Cache strategies
        self.cache_strategies = {
            "story": {"memory_ttl": 300, "redis_ttl": 3600, "levels": [CacheLevel.MEMORY, CacheLevel.REDIS]},
            "user": {"memory_ttl": 600, "redis_ttl": 7200, "levels": [CacheLevel.MEMORY, CacheLevel.REDIS]},
            "api": {"memory_ttl": 60, "redis_ttl": 300, "levels": [CacheLevel.MEMORY, CacheLevel.REDIS]},
            "tts": {"memory_ttl": None, "redis_ttl": 86400, "levels": [CacheLevel.REDIS]},  # Don't cache large audio in memory
            "directions": {"memory_ttl": 1800, "redis_ttl": 3600, "levels": [CacheLevel.MEMORY, CacheLevel.REDIS]},
            "booking": {"memory_ttl": 120, "redis_ttl": 300, "levels": [CacheLevel.MEMORY, CacheLevel.REDIS]},
        }
    
    async def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """
        Get value from cache with multi-layer fallback.
        
        Args:
            key: Cache key
            namespace: Cache namespace for strategy selection
            
        Returns:
            Cached value or None
        """
        strategy = self.cache_strategies.get(namespace, self.cache_strategies["api"])
        
        # Try each cache level in order
        for level in strategy["levels"]:
            try:
                if level == CacheLevel.MEMORY:
                    value = self.memory_cache.get(key)
                    if value is not None:
                        logger.debug(f"Memory cache hit for {key}")
                        return value
                
                elif level == CacheLevel.REDIS:
                    value = await self._get_from_redis(key)
                    if value is not None:
                        logger.debug(f"Redis cache hit for {key}")
                        # Populate higher cache levels
                        if CacheLevel.MEMORY in strategy["levels"]:
                            self.memory_cache.set(key, value, strategy["memory_ttl"])
                        return value
                        
            except Exception as e:
                logger.error(f"Error getting from {level.value} cache: {e}")
                continue
        
        logger.debug(f"Cache miss for {key}")
        return None
    
    async def set(self, key: str, value: Any, namespace: str = "default", custom_ttl: Optional[int] = None) -> bool:
        """
        Set value in appropriate cache levels.
        
        Args:
            key: Cache key
            value: Value to cache
            namespace: Cache namespace for strategy selection
            custom_ttl: Override TTL for all levels
            
        Returns:
            True if at least one cache level succeeded
        """
        strategy = self.cache_strategies.get(namespace, self.cache_strategies["api"])
        success_count = 0
        
        # Set in each cache level
        for level in strategy["levels"]:
            try:
                if level == CacheLevel.MEMORY:
                    ttl = custom_ttl or strategy["memory_ttl"]
                    if self.memory_cache.set(key, value, ttl):
                        success_count += 1
                
                elif level == CacheLevel.REDIS:
                    ttl = custom_ttl or strategy["redis_ttl"]
                    if await self._set_in_redis(key, value, ttl):
                        success_count += 1
                        
            except Exception as e:
                logger.error(f"Error setting in {level.value} cache: {e}")
                continue
        
        return success_count > 0
    
    async def delete(self, key: str, namespace: str = "default") -> bool:
        """Delete key from all cache levels."""
        strategy = self.cache_strategies.get(namespace, self.cache_strategies["api"])
        success_count = 0
        
        for level in strategy["levels"]:
            try:
                if level == CacheLevel.MEMORY:
                    if self.memory_cache.delete(key):
                        success_count += 1
                
                elif level == CacheLevel.REDIS:
                    if await self._delete_from_redis(key):
                        success_count += 1
                        
            except Exception as e:
                logger.error(f"Error deleting from {level.value} cache: {e}")
                continue
        
        return success_count > 0
    
    async def get_or_set(
        self,
        key: str,
        callback: Callable[[], Any],
        namespace: str = "default",
        custom_ttl: Optional[int] = None
    ) -> Any:
        """
        Get value from cache or set it using callback.
        
        Args:
            key: Cache key
            callback: Function to call if cache miss
            namespace: Cache namespace
            custom_ttl: Override TTL
            
        Returns:
            Cached or computed value
        """
        # Try to get from cache
        value = await self.get(key, namespace)
        if value is not None:
            return value
        
        # Cache miss - execute callback
        start_time = time.time()
        value = await self._execute_callback(callback)
        execution_time = time.time() - start_time
        
        logger.debug(f"Cache miss execution took {execution_time:.4f}s for {key}")
        
        # Cache the result
        if value is not None:
            await self.set(key, value, namespace, custom_ttl)
        
        return value
    
    async def invalidate_namespace(self, namespace: str) -> int:
        """Invalidate all keys in a namespace."""
        count = 0
        
        # Clear memory cache (basic implementation)
        if namespace == "all":
            self.memory_cache.clear()
            count += 1
        
        # Clear Redis keys with namespace prefix
        try:
            redis_count = self.redis_client.clear_by_prefix(f"{namespace}:")
            count += redis_count
        except Exception as e:
            logger.error(f"Error clearing Redis namespace {namespace}: {e}")
        
        logger.info(f"Invalidated {count} cache entries for namespace {namespace}")
        return count
    
    async def preload_cache(self, preload_configs: List[Dict[str, Any]]):
        """Preload cache with commonly accessed data."""
        logger.info("Starting cache preload")
        
        preload_tasks = []
        for config in preload_configs:
            task = self._preload_single_item(config)
            preload_tasks.append(task)
        
        results = await asyncio.gather(*preload_tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        logger.info(f"Cache preload completed: {success_count}/{len(preload_configs)} items loaded")
    
    async def _preload_single_item(self, config: Dict[str, Any]):
        """Preload a single cache item."""
        try:
            key = config["key"]
            callback = config["callback"]
            namespace = config.get("namespace", "default")
            
            # Check if already cached
            if await self.get(key, namespace) is not None:
                return
            
            # Load and cache
            value = await self._execute_callback(callback)
            if value is not None:
                await self.set(key, value, namespace)
                
        except Exception as e:
            logger.error(f"Error preloading cache item: {e}")
    
    async def _execute_callback(self, callback: Callable) -> Any:
        """Execute callback in thread pool if it's not async."""
        if asyncio.iscoroutinefunction(callback):
            return await callback()
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self.executor, callback)
    
    async def _get_from_redis(self, key: str) -> Optional[Any]:
        """Get value from Redis asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.redis_client.get, key)
    
    async def _set_in_redis(self, key: str, value: Any, ttl: Optional[int]) -> bool:
        """Set value in Redis asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.redis_client.set, key, value, ttl)
    
    async def _delete_from_redis(self, key: str) -> bool:
        """Delete key from Redis asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.redis_client.delete, key)
    
    def generate_smart_key(self, namespace: str, params: Dict[str, Any], user_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate intelligent cache key based on parameters and user context.
        
        Args:
            namespace: Cache namespace
            params: Request parameters
            user_context: User-specific context for personalization
            
        Returns:
            Generated cache key
        """
        key_parts = [namespace]
        
        # Add sorted parameters
        if params:
            sorted_params = sorted(params.items())
            param_hash = hashlib.md5(str(sorted_params).encode()).hexdigest()[:8]
            key_parts.append(param_hash)
        
        # Add user context for personalized caching
        if user_context:
            user_id = user_context.get("user_id")
            if user_id:
                key_parts.append(f"user:{user_id}")
            
            # Add relevant user preferences
            preferences = user_context.get("preferences", {})
            if preferences:
                pref_hash = hashlib.md5(str(sorted(preferences.items())).encode()).hexdigest()[:6]
                key_parts.append(f"pref:{pref_hash}")
        
        return ":".join(key_parts)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        memory_stats = self.memory_cache.get_stats()
        
        redis_stats = {"available": False}
        if self.redis_client.is_available:
            try:
                redis_info = self.redis_client.client.info()
                redis_stats = {
                    "available": True,
                    "used_memory": redis_info.get("used_memory_human"),
                    "connected_clients": redis_info.get("connected_clients"),
                    "commands_processed": redis_info.get("total_commands_processed")
                }
            except Exception as e:
                logger.error(f"Error getting Redis stats: {e}")
        
        return {
            "memory": memory_stats,
            "redis": redis_stats,
            "strategies": list(self.cache_strategies.keys())
        }


# Global enhanced cache manager
cache_manager = EnhancedCacheManager()


def smart_cache(
    namespace: str,
    ttl: Optional[int] = None,
    include_user_context: bool = False
):
    """
    Enhanced caching decorator with smart key generation.
    
    Args:
        namespace: Cache namespace
        ttl: Custom TTL override
        include_user_context: Include user context in cache key
        
    Returns:
        Decorator function
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract request and user context
            request = None
            user_context = None
            
            for arg in args:
                if hasattr(arg, 'method') and hasattr(arg, 'url'):  # Likely a Request object
                    request = arg
                    break
            
            if include_user_context and request:
                # Try to get user context from request
                user_context = getattr(request.state, 'user_context', None)
            
            # Extract parameters for cache key
            params = {}
            if request:
                params.update(dict(request.query_params))
                params.update(dict(request.path_params))
            
            # Generate smart cache key
            cache_key = cache_manager.generate_smart_key(namespace, params, user_context)
            
            # Try cache first
            cached_result = await cache_manager.get(cache_key, namespace)
            if cached_result is not None:
                return cached_result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            if result is not None:
                await cache_manager.set(cache_key, result, namespace, ttl)
            
            return result
        
        return wrapper
    return decorator