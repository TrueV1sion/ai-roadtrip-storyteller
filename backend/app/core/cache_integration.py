"""
Cache Integration Module
Provides easy integration of the multi-tier caching system with existing services
"""

from typing import Dict, Any, Optional
import functools

from app.core.multi_tier_cache import multi_tier_cache, ContentType
from app.core.cache_decorators import (
    ai_response_cache,
    story_cache,
    voice_audio_cache,
    database_cache,
    api_response_cache,
    location_cache
)
from app.core.cache_monitoring import cache_monitor
from app.services.cache_warming_service import cache_warming_service
from app.core.logger import get_logger

logger = get_logger(__name__)


class CacheIntegration:
    """Main integration point for the multi-tier caching system."""
    
    @staticmethod
    def initialize():
        """Initialize the caching system."""
        logger.info("Initializing multi-tier caching system...")
        
        # Start monitoring
        logger.info("Cache monitoring started")
        
        # Configure cache warming patterns
        cache_warming_service.set_warming_enabled(True)
        logger.info("Cache warming service enabled")
        
        # Log initial status
        report = multi_tier_cache.get_performance_report()
        logger.info(
            f"Cache initialized - "
            f"L1 Memory: {report['l1_memory']['memory_mb']:.1f}MB, "
            f"L2 Redis: {'Available' if report['l2_redis']['available'] else 'Unavailable'}"
        )
    
    @staticmethod
    def get_cache_health() -> Dict[str, Any]:
        """Get cache system health status."""
        report = multi_tier_cache.get_performance_report()
        monitor_data = cache_monitor.get_dashboard_data()
        
        return {
            'status': 'healthy' if report['l2_redis']['available'] else 'degraded',
            'hit_rate': report['overall']['hit_rate'],
            'cost_saved': report['overall']['cost_saved_usd'],
            'performance_score': monitor_data['performance_score'],
            'active_alerts': len(monitor_data['active_alerts']),
            'recommendations': report['recommendations']
        }
    
    @staticmethod
    async def invalidate_user_cache(user_id: str) -> int:
        """Invalidate all cache entries for a user."""
        count = await multi_tier_cache.invalidate(user_id=user_id)
        logger.info(f"Invalidated {count} cache entries for user {user_id}")
        return count
    
    @staticmethod
    async def warm_cache_for_trip(trip_id: str):
        """Warm cache for an upcoming trip."""
        await cache_warming_service.warm_for_trip(trip_id)
    
    @staticmethod
    async def warm_cache_for_user(user_id: str):
        """Warm cache based on user preferences."""
        await cache_warming_service.warm_for_user(user_id)


# Migration helpers for existing code

def migrate_to_multi_tier_cache(old_cache_decorator):
    """
    Migrate from old cache decorator to new multi-tier system.
    
    Usage:
        @migrate_to_multi_tier_cache(old_cacheable_decorator)
        async def my_function():
            ...
    """
    def decorator(func):
        # Determine content type based on function name/module
        if 'story' in func.__name__:
            return story_cache()(func)
        elif 'ai' in func.__name__ or 'generate' in func.__name__:
            return ai_response_cache()(func)
        elif 'voice' in func.__name__ or 'tts' in func.__name__:
            return voice_audio_cache()(func)
        elif 'db' in func.__module__ or 'repository' in func.__module__:
            return database_cache()(func)
        else:
            return api_response_cache()(func)
    
    return decorator


# Compatibility layer for existing cache usage

class CacheCompatibilityLayer:
    """Provides compatibility with existing cache interface."""
    
    def __init__(self):
        self.cache = multi_tier_cache
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (compatibility method)."""
        return await self.cache.get(
            key=key,
            content_type=ContentType.API_RESPONSE
        )
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache (compatibility method)."""
        ttl_seconds = expire or ttl
        return await self.cache.set(
            key=key,
            value=value,
            content_type=ContentType.API_RESPONSE
        )
    
    async def delete(self, key: str) -> bool:
        """Delete from cache (compatibility method)."""
        count = await self.cache.invalidate(key=key)
        return count > 0
    
    def get_or_set(self, key: str, callback, ttl: Optional[int] = None):
        """Get or set with callback (compatibility method)."""
        async def async_wrapper():
            value = await self.get(key)
            if value is not None:
                return value
            
            value = await callback()
            if value is not None:
                await self.set(key, value, ttl=ttl)
            
            return value
        
        return async_wrapper()


# Quick migration guide

MIGRATION_GUIDE = """
# Multi-Tier Cache Migration Guide

## 1. Update imports in your service files:

```python
# Old:
from app.core.cache import cacheable, redis_client

# New:
from app.core.cache_decorators import ai_response_cache, story_cache
from app.core.cache_integration import CacheIntegration
```

## 2. Replace decorators:

```python
# Old:
@cacheable(namespace="story", ttl=3600)
async def generate_story():
    ...

# New:
@story_cache()
async def generate_story():
    ...
```

## 3. Use specialized decorators:

- `@ai_response_cache()` - For AI/LLM responses
- `@story_cache()` - For story content
- `@voice_audio_cache()` - For TTS audio
- `@database_cache()` - For DB queries
- `@api_response_cache()` - For external API calls
- `@location_cache()` - For location-based data

## 4. Invalidate cache:

```python
# Old:
redis_client.delete(key)

# New:
from app.core.multi_tier_cache import CacheInvalidationAPI
await CacheInvalidationAPI.invalidate_pattern("story:*")
```

## 5. Monitor performance:

```python
from app.core.cache_integration import CacheIntegration
health = CacheIntegration.get_cache_health()
print(f"Hit rate: {health['hit_rate']:.1%}")
print(f"Cost saved: ${health['cost_saved']:.2f}")
```
"""


# Initialize cache on module import
CacheIntegration.initialize()


# Export main components
__all__ = [
    'CacheIntegration',
    'CacheCompatibilityLayer',
    'migrate_to_multi_tier_cache',
    'MIGRATION_GUIDE'
]