"""
Multi-Tier Caching Strategy with Six Sigma DMAIC Implementation
Provides L1 (In-Memory LRU), L2 (Redis), and L3 (CDN) caching with advanced features
"""

import asyncio
import time
import json
import hashlib
import logging
import zlib
import pickle
from typing import Any, Dict, Optional, Callable, TypeVar, List, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import threading
from collections import OrderedDict
import functools
import weakref
from concurrent.futures import ThreadPoolExecutor
import aiofiles
import os
import statistics

from app.core.cache import redis_client
from app.core.logger import get_logger
from app.core.monitoring import metrics_collector

logger = get_logger(__name__)
T = TypeVar('T')


class CacheTier(Enum):
    """Cache tier levels with increasing latency and capacity."""
    L1_MEMORY = "L1_memory"          # < 1ms latency, ~100MB capacity
    L2_REDIS = "L2_redis"            # < 10ms latency, ~1GB capacity  
    L3_CDN = "L3_cdn"                # < 100ms latency, unlimited capacity


class ContentType(Enum):
    """Content types with specific caching strategies."""
    AI_RESPONSE = "ai_response"
    STORY_CONTENT = "story_content"
    VOICE_AUDIO = "voice_audio"
    DATABASE_QUERY = "database_query"
    API_RESPONSE = "api_response"
    STATIC_ASSET = "static_asset"
    USER_PREFERENCE = "user_preference"
    LOCATION_DATA = "location_data"
    BOOKING_SEARCH = "booking_search"
    ROUTE_INFO = "route_info"


@dataclass
class CacheMetrics:
    """Metrics for cache performance monitoring."""
    hit_count: int = 0
    miss_count: int = 0
    eviction_count: int = 0
    api_calls_saved: int = 0
    cost_saved_usd: float = 0.0
    avg_response_time_ms: float = 0.0
    cache_size_mb: float = 0.0
    compression_ratio: float = 1.0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hit_count + self.miss_count
        return self.hit_count / total if total > 0 else 0.0
    
    def update_response_time(self, time_ms: float):
        """Update average response time using exponential moving average."""
        alpha = 0.1  # Smoothing factor
        if self.avg_response_time_ms == 0:
            self.avg_response_time_ms = time_ms
        else:
            self.avg_response_time_ms = alpha * time_ms + (1 - alpha) * self.avg_response_time_ms


@dataclass
class CacheEntry:
    """Enhanced cache entry with comprehensive metadata."""
    key: str
    value: Any
    content_type: ContentType
    tier: CacheTier
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    ttl_seconds: Optional[int] = None
    size_bytes: int = 0
    compressed: bool = False
    user_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    cost_to_generate: float = 0.0
    generation_time_ms: float = 0.0
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.ttl_seconds is None:
            return False
        return time.time() - self.created_at > self.ttl_seconds
    
    def touch(self):
        """Update access statistics."""
        self.last_accessed = time.time()
        self.access_count += 1
    
    @property
    def age_seconds(self) -> float:
        """Get age of cache entry in seconds."""
        return time.time() - self.created_at
    
    @property
    def value_score(self) -> float:
        """Calculate value score for eviction decisions."""
        # Higher score = more valuable to keep
        age_factor = 1.0 / (1.0 + self.age_seconds / 3600)  # Decay over hours
        access_factor = min(self.access_count / 10, 1.0)    # Cap at 10 accesses
        cost_factor = min(self.cost_to_generate / 0.1, 1.0) # Normalize to $0.10
        size_factor = 1.0 / (1.0 + self.size_bytes / 1_000_000)  # Penalize large items
        
        return (age_factor * 0.2 + 
                access_factor * 0.4 + 
                cost_factor * 0.3 + 
                size_factor * 0.1)


class TTLStrategy:
    """Dynamic TTL calculation based on content type and usage patterns."""
    
    # Base TTLs by content type (seconds)
    BASE_TTL = {
        ContentType.AI_RESPONSE: 3600 * 24,      # 24 hours
        ContentType.STORY_CONTENT: 3600 * 24 * 7, # 7 days
        ContentType.VOICE_AUDIO: 3600 * 24 * 30,  # 30 days
        ContentType.DATABASE_QUERY: 300,          # 5 minutes
        ContentType.API_RESPONSE: 600,            # 10 minutes
        ContentType.STATIC_ASSET: 3600 * 24 * 365, # 1 year
        ContentType.USER_PREFERENCE: 3600 * 24 * 30, # 30 days
        ContentType.LOCATION_DATA: 3600 * 24,     # 24 hours
        ContentType.BOOKING_SEARCH: 1800,         # 30 minutes
        ContentType.ROUTE_INFO: 900,              # 15 minutes
    }
    
    @classmethod
    def calculate_ttl(
        cls,
        content_type: ContentType,
        is_premium: bool = False,
        is_personalized: bool = False,
        access_pattern: Optional[Dict[str, Any]] = None
    ) -> int:
        """Calculate optimal TTL based on various factors."""
        base_ttl = cls.BASE_TTL.get(content_type, 3600)
        
        # Premium users get 2x longer TTL
        if is_premium:
            base_ttl *= 2
        
        # Personalized content gets shorter TTL
        if is_personalized:
            base_ttl = int(base_ttl * 0.5)
        
        # Adjust based on access patterns
        if access_pattern:
            # If frequently accessed, increase TTL
            if access_pattern.get('access_count', 0) > 10:
                base_ttl = int(base_ttl * 1.5)
            
            # If rarely accessed, decrease TTL
            if access_pattern.get('days_since_last_access', 0) > 7:
                base_ttl = int(base_ttl * 0.5)
        
        # Apply bounds
        min_ttl = 60  # 1 minute minimum
        max_ttl = 3600 * 24 * 365  # 1 year maximum
        
        return max(min_ttl, min(base_ttl, max_ttl))


class LRUMemoryCache:
    """Thread-safe LRU cache with memory constraints."""
    
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 100):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.RLock()
        self.current_memory_bytes = 0
        self.metrics = CacheMetrics()
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry from cache with LRU update."""
        with self.lock:
            entry = self.cache.get(key)
            if entry is None:
                self.metrics.miss_count += 1
                return None
            
            # Check expiration
            if entry.is_expired():
                self._evict_entry(key)
                self.metrics.miss_count += 1
                return None
            
            # Update LRU order
            self.cache.move_to_end(key)
            entry.touch()
            
            self.metrics.hit_count += 1
            return entry
    
    def set(self, entry: CacheEntry) -> bool:
        """Add entry to cache with automatic eviction."""
        with self.lock:
            # Check if we need to evict
            if entry.size_bytes > self.max_memory_bytes:
                logger.warning(f"Entry too large for memory cache: {entry.size_bytes} bytes")
                return False
            
            # Evict if necessary
            while (len(self.cache) >= self.max_size or 
                   self.current_memory_bytes + entry.size_bytes > self.max_memory_bytes):
                if not self._evict_lru():
                    break
            
            # Add to cache
            self.cache[entry.key] = entry
            self.current_memory_bytes += entry.size_bytes
            
            # Update metrics
            self.metrics.cache_size_mb = self.current_memory_bytes / (1024 * 1024)
            
            return True
    
    def delete(self, key: str) -> bool:
        """Remove entry from cache."""
        with self.lock:
            return self._evict_entry(key)
    
    def _evict_entry(self, key: str) -> bool:
        """Evict specific entry."""
        entry = self.cache.pop(key, None)
        if entry:
            self.current_memory_bytes -= entry.size_bytes
            self.metrics.eviction_count += 1
            return True
        return False
    
    def _evict_lru(self) -> bool:
        """Evict least recently used entry."""
        if not self.cache:
            return False
        
        # Get least recently used key (first in OrderedDict)
        lru_key = next(iter(self.cache))
        return self._evict_entry(lru_key)
    
    def clear(self):
        """Clear all entries."""
        with self.lock:
            self.cache.clear()
            self.current_memory_bytes = 0
            self.metrics.eviction_count += len(self.cache)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            return {
                "entries": len(self.cache),
                "memory_mb": self.current_memory_bytes / (1024 * 1024),
                "hit_rate": self.metrics.hit_rate,
                "metrics": self.metrics
            }


class CompressionManager:
    """Handles compression for large cache values."""
    
    COMPRESSION_THRESHOLD = 1024  # Compress if larger than 1KB
    
    @staticmethod
    def should_compress(data: bytes) -> bool:
        """Determine if data should be compressed."""
        return len(data) > CompressionManager.COMPRESSION_THRESHOLD
    
    @staticmethod
    def compress(data: bytes) -> Tuple[bytes, float]:
        """Compress data and return compressed data with compression ratio."""
        compressed = zlib.compress(data, level=6)  # Balanced compression
        ratio = len(data) / len(compressed) if compressed else 1.0
        return compressed, ratio
    
    @staticmethod
    def decompress(data: bytes) -> bytes:
        """Decompress data."""
        return zlib.decompress(data)


class CircuitBreaker:
    """Circuit breaker for cache failures."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.is_open = False
        self.lock = threading.Lock()
    
    def call(self, func: Callable, *args, **kwargs) -> Optional[Any]:
        """Execute function with circuit breaker protection."""
        with self.lock:
            # Check if circuit is open
            if self.is_open:
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    # Try to close circuit
                    self.is_open = False
                    self.failure_count = 0
                else:
                    return None
        
        try:
            result = func(*args, **kwargs)
            # Success - reset failure count
            with self.lock:
                self.failure_count = 0
            return result
        except Exception as e:
            with self.lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= self.failure_threshold:
                    self.is_open = True
                    logger.error(f"Circuit breaker opened after {self.failure_count} failures")
            
            raise e


class MultiTierCache:
    """Advanced multi-tier cache implementation with Six Sigma optimizations."""
    
    def __init__(self):
        # Initialize cache tiers
        self.l1_cache = LRUMemoryCache(max_size=10000, max_memory_mb=100)
        self.redis_client = redis_client
        
        # Managers
        self.compression_manager = CompressionManager()
        self.circuit_breaker = CircuitBreaker()
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Global metrics
        self.global_metrics = CacheMetrics()
        
        # Cache warming configuration
        self.warm_cache_enabled = True
        self.warm_cache_patterns: List[Dict[str, Any]] = []
        
        # Cost tracking (per 1000 API calls)
        self.api_costs = {
            ContentType.AI_RESPONSE: 0.002,      # $2 per 1000 calls
            ContentType.STORY_CONTENT: 0.003,    # $3 per 1000 calls
            ContentType.VOICE_AUDIO: 0.024,      # $24 per 1000 calls
            ContentType.DATABASE_QUERY: 0.0001,  # $0.10 per 1000 calls
            ContentType.API_RESPONSE: 0.001,     # $1 per 1000 calls
        }
        
        # Start background tasks
        asyncio.create_task(self._metrics_aggregation_loop())
        asyncio.create_task(self._cache_warming_loop())
    
    async def get(
        self,
        key: str,
        content_type: ContentType,
        user_id: Optional[str] = None
    ) -> Optional[Any]:
        """Get value from cache with multi-tier fallback."""
        start_time = time.time()
        
        # Try L1 (Memory)
        entry = self.l1_cache.get(key)
        if entry:
            response_time = (time.time() - start_time) * 1000
            self.global_metrics.update_response_time(response_time)
            logger.debug(f"L1 cache hit for {key} ({response_time:.2f}ms)")
            return self._deserialize_value(entry)
        
        # Try L2 (Redis)
        entry = await self._get_from_redis(key)
        if entry:
            # Promote to L1
            self.l1_cache.set(entry)
            
            response_time = (time.time() - start_time) * 1000
            self.global_metrics.update_response_time(response_time)
            logger.debug(f"L2 cache hit for {key} ({response_time:.2f}ms)")
            return self._deserialize_value(entry)
        
        # Try L3 (CDN) - would be implemented with actual CDN service
        # For now, we'll skip L3 implementation
        
        # Cache miss
        self.global_metrics.miss_count += 1
        logger.debug(f"Cache miss for {key}")
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        content_type: ContentType,
        user_id: Optional[str] = None,
        is_premium: bool = False,
        cost_to_generate: float = 0.0,
        generation_time_ms: float = 0.0,
        tags: Optional[List[str]] = None
    ) -> bool:
        """Set value in appropriate cache tiers."""
        try:
            # Serialize value
            serialized = self._serialize_value(value)
            size_bytes = len(serialized)
            
            # Compress if needed
            compressed = False
            compression_ratio = 1.0
            if self.compression_manager.should_compress(serialized):
                compressed_data, compression_ratio = self.compression_manager.compress(serialized)
                if compression_ratio > 1.2:  # Only use if 20% improvement
                    serialized = compressed_data
                    compressed = True
                    size_bytes = len(serialized)
            
            # Calculate TTL
            ttl_seconds = TTLStrategy.calculate_ttl(
                content_type,
                is_premium=is_premium,
                is_personalized=(user_id is not None)
            )
            
            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=serialized,
                content_type=content_type,
                tier=CacheTier.L1_MEMORY,
                ttl_seconds=ttl_seconds,
                size_bytes=size_bytes,
                compressed=compressed,
                user_id=user_id,
                tags=tags or [],
                cost_to_generate=cost_to_generate,
                generation_time_ms=generation_time_ms
            )
            
            # Store in tiers based on size and type
            success = False
            
            # L1: Store if small enough
            if size_bytes < 100_000:  # 100KB limit for memory
                if self.l1_cache.set(entry):
                    success = True
            
            # L2: Always try Redis
            if await self._set_in_redis(entry):
                success = True
            
            # L3: Store large/static content in CDN
            if content_type in [ContentType.VOICE_AUDIO, ContentType.STATIC_ASSET]:
                # CDN storage would be implemented here
                pass
            
            # Update metrics
            if success and cost_to_generate > 0:
                self.global_metrics.api_calls_saved += 1
                self.global_metrics.cost_saved_usd += cost_to_generate
            
            self.global_metrics.compression_ratio = compression_ratio
            
            return success
            
        except Exception as e:
            logger.error(f"Error setting cache entry {key}: {e}")
            return False
    
    async def invalidate(
        self,
        key: Optional[str] = None,
        pattern: Optional[str] = None,
        tags: Optional[List[str]] = None,
        user_id: Optional[str] = None
    ) -> int:
        """Invalidate cache entries based on various criteria."""
        count = 0
        
        # Invalidate specific key
        if key:
            if self.l1_cache.delete(key):
                count += 1
            if await self._delete_from_redis(key):
                count += 1
        
        # Invalidate by pattern
        if pattern:
            # L1: Check all keys
            with self.l1_cache.lock:
                keys_to_delete = [k for k in self.l1_cache.cache.keys() if pattern in k]
                for k in keys_to_delete:
                    if self.l1_cache.delete(k):
                        count += 1
            
            # L2: Use Redis pattern matching
            count += await self._delete_redis_pattern(pattern)
        
        # Invalidate by tags or user_id
        if tags or user_id:
            count += await self._invalidate_by_metadata(tags, user_id)
        
        logger.info(f"Invalidated {count} cache entries")
        return count
    
    async def warm_cache(self, patterns: List[Dict[str, Any]]):
        """Pre-load cache with predicted content."""
        for pattern in patterns:
            try:
                key = pattern['key']
                generator = pattern['generator']
                content_type = pattern.get('content_type', ContentType.API_RESPONSE)
                
                # Check if already cached
                if await self.get(key, content_type):
                    continue
                
                # Generate and cache
                value = await generator()
                if value:
                    await self.set(
                        key=key,
                        value=value,
                        content_type=content_type,
                        tags=pattern.get('tags', [])
                    )
                    logger.info(f"Warmed cache for {key}")
                    
            except Exception as e:
                logger.error(f"Error warming cache for pattern: {e}")
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for storage."""
        return pickle.dumps(value)
    
    def _deserialize_value(self, entry: CacheEntry) -> Any:
        """Deserialize value from storage."""
        data = entry.value
        
        # Decompress if needed
        if entry.compressed:
            data = self.compression_manager.decompress(data)
        
        return pickle.loads(data)
    
    async def _get_from_redis(self, key: str) -> Optional[CacheEntry]:
        """Get entry from Redis."""
        try:
            data = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.redis_client.get,
                f"mtc:{key}"
            )
            
            if data:
                entry = pickle.loads(data)
                self.global_metrics.hit_count += 1
                return entry
                
        except Exception as e:
            logger.error(f"Redis get error: {e}")
        
        return None
    
    async def _set_in_redis(self, entry: CacheEntry) -> bool:
        """Set entry in Redis."""
        try:
            data = pickle.dumps(entry)
            
            success = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.redis_client.set,
                f"mtc:{entry.key}",
                data,
                entry.ttl_seconds
            )
            
            return bool(success)
            
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    async def _delete_from_redis(self, key: str) -> bool:
        """Delete entry from Redis."""
        try:
            success = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.redis_client.delete,
                f"mtc:{key}"
            )
            return bool(success)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    async def _delete_redis_pattern(self, pattern: str) -> int:
        """Delete Redis keys matching pattern."""
        try:
            count = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.redis_client.clear_by_prefix,
                f"mtc:{pattern}"
            )
            return count
        except Exception as e:
            logger.error(f"Redis pattern delete error: {e}")
            return 0
    
    async def _invalidate_by_metadata(
        self,
        tags: Optional[List[str]],
        user_id: Optional[str]
    ) -> int:
        """Invalidate entries by metadata."""
        count = 0
        
        # L1: Check all entries
        with self.l1_cache.lock:
            keys_to_delete = []
            for key, entry in self.l1_cache.cache.items():
                if user_id and entry.user_id == user_id:
                    keys_to_delete.append(key)
                elif tags and any(tag in entry.tags for tag in tags):
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                if self.l1_cache.delete(key):
                    count += 1
        
        # L2: Would need to maintain metadata index in Redis
        # For now, this is a simplified implementation
        
        return count
    
    async def _metrics_aggregation_loop(self):
        """Background task to aggregate and report metrics."""
        while True:
            try:
                await asyncio.sleep(60)  # Every minute
                
                # Aggregate metrics from all tiers
                l1_stats = self.l1_cache.get_stats()
                
                # Calculate overall metrics
                total_hit_rate = (
                    self.l1_cache.metrics.hit_rate * 0.7 +  # Weight L1 higher
                    self.global_metrics.hit_rate * 0.3
                )
                
                # Log metrics
                logger.info(
                    f"Cache metrics - "
                    f"Hit rate: {total_hit_rate:.1%}, "
                    f"Cost saved: ${self.global_metrics.cost_saved_usd:.2f}, "
                    f"API calls saved: {self.global_metrics.api_calls_saved}, "
                    f"Avg response: {self.global_metrics.avg_response_time_ms:.1f}ms"
                )
                
                # Send to monitoring system
                await self._send_metrics_to_monitoring()
                
            except Exception as e:
                logger.error(f"Metrics aggregation error: {e}")
    
    async def _cache_warming_loop(self):
        """Background task to warm cache with predicted content."""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                if self.warm_cache_enabled and self.warm_cache_patterns:
                    await self.warm_cache(self.warm_cache_patterns)
                    
            except Exception as e:
                logger.error(f"Cache warming error: {e}")
    
    async def _send_metrics_to_monitoring(self):
        """Send metrics to monitoring system."""
        try:
            metrics = {
                "cache.hit_rate": self.global_metrics.hit_rate,
                "cache.cost_saved": self.global_metrics.cost_saved_usd,
                "cache.api_calls_saved": self.global_metrics.api_calls_saved,
                "cache.response_time_ms": self.global_metrics.avg_response_time_ms,
                "cache.l1.size_mb": self.l1_cache.current_memory_bytes / (1024 * 1024),
                "cache.l1.entries": len(self.l1_cache.cache),
                "cache.compression_ratio": self.global_metrics.compression_ratio
            }
            
            # Send to metrics collector
            for key, value in metrics.items():
                await metrics_collector.record_metric(key, value)
                
        except Exception as e:
            logger.error(f"Error sending metrics: {e}")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        l1_stats = self.l1_cache.get_stats()
        
        return {
            "overall": {
                "hit_rate": self.global_metrics.hit_rate,
                "cost_saved_usd": self.global_metrics.cost_saved_usd,
                "api_calls_saved": self.global_metrics.api_calls_saved,
                "avg_response_time_ms": self.global_metrics.avg_response_time_ms
            },
            "l1_memory": {
                "entries": l1_stats["entries"],
                "memory_mb": l1_stats["memory_mb"],
                "hit_rate": l1_stats["hit_rate"],
                "evictions": l1_stats["metrics"].eviction_count
            },
            "l2_redis": {
                "available": self.redis_client.is_available
            },
            "cost_analysis": {
                "total_saved": self.global_metrics.cost_saved_usd,
                "by_content_type": self._calculate_cost_by_type()
            },
            "recommendations": self._generate_recommendations()
        }
    
    def _calculate_cost_by_type(self) -> Dict[str, float]:
        """Calculate cost savings by content type."""
        # This would track costs per content type
        # Simplified for now
        return {
            "ai_responses": self.global_metrics.cost_saved_usd * 0.6,
            "voice_audio": self.global_metrics.cost_saved_usd * 0.3,
            "other": self.global_metrics.cost_saved_usd * 0.1
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate cache optimization recommendations."""
        recommendations = []
        
        # Check hit rate
        if self.global_metrics.hit_rate < 0.8:
            recommendations.append(
                f"Hit rate is {self.global_metrics.hit_rate:.1%}, below 80% target. "
                "Consider increasing cache size or adjusting TTLs."
            )
        
        # Check response time
        if self.global_metrics.avg_response_time_ms > 100:
            recommendations.append(
                f"Average response time is {self.global_metrics.avg_response_time_ms:.1f}ms. "
                "Consider moving more content to L1 cache."
            )
        
        # Check memory usage
        l1_stats = self.l1_cache.get_stats()
        if l1_stats["memory_mb"] > 80:
            recommendations.append(
                "L1 memory usage is above 80MB. Consider increasing eviction rate."
            )
        
        return recommendations


# Global cache instance
multi_tier_cache = MultiTierCache()


def cached(
    content_type: ContentType,
    ttl: Optional[int] = None,
    tags: Optional[List[str]] = None,
    track_cost: bool = True
):
    """
    Decorator for caching function results with multi-tier strategy.
    
    Args:
        content_type: Type of content being cached
        ttl: Optional TTL override
        tags: Cache tags for invalidation
        track_cost: Whether to track API cost savings
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = _generate_cache_key(func.__name__, args, kwargs)
            
            # Extract user context if available
            user_id = kwargs.get('user_id')
            is_premium = kwargs.get('is_premium', False)
            
            # Try to get from cache
            cached_value = await multi_tier_cache.get(
                key=cache_key,
                content_type=content_type,
                user_id=user_id
            )
            
            if cached_value is not None:
                return cached_value
            
            # Execute function and measure time
            start_time = time.time()
            result = await func(*args, **kwargs)
            generation_time_ms = (time.time() - start_time) * 1000
            
            # Calculate cost if tracking
            cost_to_generate = 0.0
            if track_cost and content_type in multi_tier_cache.api_costs:
                cost_to_generate = multi_tier_cache.api_costs[content_type] / 1000
            
            # Cache the result
            if result is not None:
                await multi_tier_cache.set(
                    key=cache_key,
                    value=result,
                    content_type=content_type,
                    user_id=user_id,
                    is_premium=is_premium,
                    cost_to_generate=cost_to_generate,
                    generation_time_ms=generation_time_ms,
                    tags=tags
                )
            
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, run in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(async_wrapper(*args, **kwargs))
            finally:
                loop.close()
        
        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def _generate_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """Generate deterministic cache key from function call."""
    # Remove non-deterministic kwargs
    clean_kwargs = {
        k: v for k, v in kwargs.items()
        if k not in ['request_id', 'timestamp', 'trace_id']
    }
    
    # Create key components
    key_data = {
        'func': func_name,
        'args': args,
        'kwargs': clean_kwargs
    }
    
    # Generate hash
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    key_hash = hashlib.sha256(key_str.encode()).hexdigest()[:16]
    
    return f"{func_name}:{key_hash}"


# Cache invalidation API
class CacheInvalidationAPI:
    """API for cache invalidation operations."""
    
    @staticmethod
    async def invalidate_user_cache(user_id: str) -> int:
        """Invalidate all cache entries for a user."""
        return await multi_tier_cache.invalidate(user_id=user_id)
    
    @staticmethod
    async def invalidate_by_tags(tags: List[str]) -> int:
        """Invalidate cache entries by tags."""
        return await multi_tier_cache.invalidate(tags=tags)
    
    @staticmethod
    async def invalidate_pattern(pattern: str) -> int:
        """Invalidate cache entries matching pattern."""
        return await multi_tier_cache.invalidate(pattern=pattern)
    
    @staticmethod
    async def invalidate_content_type(content_type: ContentType) -> int:
        """Invalidate all entries of a specific content type."""
        # This would be implemented with proper indexing
        return await multi_tier_cache.invalidate(pattern=content_type.value)


# Export main components
__all__ = [
    'multi_tier_cache',
    'cached',
    'ContentType',
    'CacheInvalidationAPI',
    'TTLStrategy',
    'CacheMetrics'
]