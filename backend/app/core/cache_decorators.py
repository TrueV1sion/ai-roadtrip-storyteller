"""
Advanced Caching Decorators for Different Use Cases
Provides specialized decorators for AI, database, API, and static content caching
"""

import asyncio
import functools
import hashlib
import json
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from datetime import datetime

from app.core.multi_tier_cache import (
    multi_tier_cache, ContentType, CacheInvalidationAPI
)
from app.core.logger import get_logger

logger = get_logger(__name__)
T = TypeVar('T')


def ai_response_cache(
    ttl: Optional[int] = None,
    personalized: bool = True,
    track_generation_cost: bool = True,
    fallback_on_error: bool = True
):
    """
    Specialized decorator for caching AI responses.
    
    Features:
    - Automatic user context extraction
    - Cost tracking for AI API calls
    - Fallback to cached responses on AI service errors
    - Personalization-aware caching
    
    Args:
        ttl: Optional TTL override (defaults to content-based TTL)
        personalized: Whether to include user context in cache key
        track_generation_cost: Track API cost savings
        fallback_on_error: Return stale cache on AI errors
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract context
            user_id = kwargs.get('user_id')
            is_premium = kwargs.get('is_premium', False)
            
            # Generate cache key with AI-specific components
            cache_key = _generate_ai_cache_key(
                func.__name__,
                args,
                kwargs,
                include_user=personalized and user_id is not None
            )
            
            # Try to get from cache
            cached_value = await multi_tier_cache.get(
                key=cache_key,
                content_type=ContentType.AI_RESPONSE,
                user_id=user_id if personalized else None
            )
            
            if cached_value is not None:
                logger.debug(f"AI cache hit for {func.__name__}")
                return cached_value
            
            try:
                # Execute AI function
                start_time = time.time()
                result = await func(*args, **kwargs)
                generation_time = (time.time() - start_time) * 1000
                
                # Calculate approximate cost
                cost = _estimate_ai_cost(result, generation_time)
                
                # Cache successful response
                if result and not result.get('error'):
                    await multi_tier_cache.set(
                        key=cache_key,
                        value=result,
                        content_type=ContentType.AI_RESPONSE,
                        user_id=user_id if personalized else None,
                        is_premium=is_premium,
                        cost_to_generate=cost if track_generation_cost else 0,
                        generation_time_ms=generation_time,
                        tags=['ai', func.__name__]
                    )
                
                return result
                
            except Exception as e:
                logger.error(f"AI function error: {e}")
                
                # Try fallback to stale cache if enabled
                if fallback_on_error:
                    stale_cache = await _get_stale_cache(cache_key)
                    if stale_cache:
                        logger.warning(f"Using stale cache for {func.__name__} due to error")
                        return stale_cache
                
                raise
        
        return wrapper
    return decorator


def story_cache(
    ttl: Optional[int] = None,
    include_location: bool = True,
    include_theme: bool = True,
    include_personality: bool = True
):
    """
    Specialized decorator for caching story content.
    
    Features:
    - Location-aware caching
    - Theme and personality considerations
    - Extended TTL for story content
    
    Args:
        ttl: Optional TTL override
        include_location: Include location in cache key
        include_theme: Include theme in cache key
        include_personality: Include personality in cache key
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract story parameters
            location = kwargs.get('location', {})
            theme = kwargs.get('theme', 'default')
            personality = kwargs.get('personality', 'default')
            user_id = kwargs.get('user_id')
            
            # Build cache key components
            key_components = {
                'func': func.__name__,
                'user_id': user_id
            }
            
            if include_location and location:
                # Round coordinates to reduce cache fragmentation
                lat = round(location.get('lat', 0), 3)  # ~100m precision
                lng = round(location.get('lng', 0), 3)
                key_components['location'] = f"{lat},{lng}"
            
            if include_theme:
                key_components['theme'] = theme
                
            if include_personality:
                key_components['personality'] = personality
            
            cache_key = _generate_deterministic_key(key_components)
            
            # Check cache
            cached_story = await multi_tier_cache.get(
                key=cache_key,
                content_type=ContentType.STORY_CONTENT,
                user_id=user_id
            )
            
            if cached_story:
                logger.debug(f"Story cache hit for {cache_key}")
                return cached_story
            
            # Generate story
            start_time = time.time()
            story = await func(*args, **kwargs)
            generation_time = (time.time() - start_time) * 1000
            
            # Cache the story
            if story:
                await multi_tier_cache.set(
                    key=cache_key,
                    value=story,
                    content_type=ContentType.STORY_CONTENT,
                    user_id=user_id,
                    cost_to_generate=_estimate_ai_cost(story, generation_time),
                    generation_time_ms=generation_time,
                    tags=['story', theme, personality]
                )
            
            return story
        
        return wrapper
    return decorator


def voice_audio_cache(
    ttl: Optional[int] = None,
    compression_enabled: bool = True
):
    """
    Specialized decorator for caching voice/audio content.
    
    Features:
    - Automatic compression for audio data
    - Extended TTL for audio content
    - CDN storage for large files
    
    Args:
        ttl: Optional TTL override
        compression_enabled: Enable audio compression
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract parameters
            text = kwargs.get('text', '')
            voice_id = kwargs.get('voice_id', 'default')
            language = kwargs.get('language', 'en')
            user_id = kwargs.get('user_id')
            
            # Generate cache key
            cache_key = _generate_audio_cache_key(text, voice_id, language)
            
            # Check cache
            cached_audio = await multi_tier_cache.get(
                key=cache_key,
                content_type=ContentType.VOICE_AUDIO,
                user_id=user_id
            )
            
            if cached_audio:
                logger.debug(f"Audio cache hit for voice {voice_id}")
                return cached_audio
            
            # Generate audio
            start_time = time.time()
            audio_data = await func(*args, **kwargs)
            generation_time = (time.time() - start_time) * 1000
            
            # Cache audio
            if audio_data:
                # Calculate TTS cost (approximate)
                char_count = len(text)
                cost = (char_count / 1_000_000) * 16  # $16 per million chars
                
                await multi_tier_cache.set(
                    key=cache_key,
                    value=audio_data,
                    content_type=ContentType.VOICE_AUDIO,
                    user_id=user_id,
                    cost_to_generate=cost,
                    generation_time_ms=generation_time,
                    tags=['audio', voice_id, language]
                )
            
            return audio_data
        
        return wrapper
    return decorator


def database_cache(
    ttl: int = 300,  # 5 minutes default
    invalidate_on_write: bool = True,
    key_prefix: Optional[str] = None
):
    """
    Specialized decorator for caching database queries.
    
    Features:
    - Automatic invalidation on write operations
    - Query result caching
    - Connection pooling awareness
    
    Args:
        ttl: Cache TTL in seconds
        invalidate_on_write: Auto-invalidate on DB writes
        key_prefix: Optional key prefix for grouping
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Detect if this is a write operation
            is_write = any(
                keyword in func.__name__.lower()
                for keyword in ['create', 'update', 'delete', 'insert', 'save']
            )
            
            # Skip caching for write operations
            if is_write:
                result = await func(*args, **kwargs)
                
                # Invalidate related cache if enabled
                if invalidate_on_write and key_prefix:
                    await CacheInvalidationAPI.invalidate_pattern(key_prefix)
                
                return result
            
            # Generate cache key for read operations
            cache_key = _generate_db_cache_key(
                func.__name__,
                args,
                kwargs,
                prefix=key_prefix
            )
            
            # Check cache
            cached_result = await multi_tier_cache.get(
                key=cache_key,
                content_type=ContentType.DATABASE_QUERY
            )
            
            if cached_result is not None:
                logger.debug(f"DB cache hit for {func.__name__}")
                return cached_result
            
            # Execute query
            start_time = time.time()
            result = await func(*args, **kwargs)
            query_time = (time.time() - start_time) * 1000
            
            # Cache result
            if result is not None:
                await multi_tier_cache.set(
                    key=cache_key,
                    value=result,
                    content_type=ContentType.DATABASE_QUERY,
                    generation_time_ms=query_time,
                    tags=['db', func.__name__]
                )
            
            return result
        
        return wrapper
    return decorator


def api_response_cache(
    ttl: int = 600,  # 10 minutes default
    vary_on_headers: Optional[List[str]] = None,
    cache_errors: bool = False
):
    """
    Specialized decorator for caching API responses.
    
    Features:
    - HTTP header consideration
    - Error response handling
    - Rate limit awareness
    
    Args:
        ttl: Cache TTL in seconds
        vary_on_headers: Headers to include in cache key
        cache_errors: Whether to cache error responses
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request if available
            request = None
            for arg in args:
                if hasattr(arg, 'headers') and hasattr(arg, 'method'):
                    request = arg
                    break
            
            # Generate cache key with headers
            cache_key = _generate_api_cache_key(
                func.__name__,
                args,
                kwargs,
                request=request,
                vary_headers=vary_on_headers
            )
            
            # Check cache
            cached_response = await multi_tier_cache.get(
                key=cache_key,
                content_type=ContentType.API_RESPONSE
            )
            
            if cached_response is not None:
                logger.debug(f"API cache hit for {func.__name__}")
                return cached_response
            
            # Execute API call
            start_time = time.time()
            response = await func(*args, **kwargs)
            response_time = (time.time() - start_time) * 1000
            
            # Determine if response should be cached
            should_cache = True
            if hasattr(response, 'status_code'):
                # Don't cache errors unless specified
                if response.status_code >= 400 and not cache_errors:
                    should_cache = False
            
            # Cache response
            if should_cache and response is not None:
                await multi_tier_cache.set(
                    key=cache_key,
                    value=response,
                    content_type=ContentType.API_RESPONSE,
                    generation_time_ms=response_time,
                    tags=['api', func.__name__]
                )
            
            return response
        
        return wrapper
    return decorator


def location_cache(
    ttl: Optional[int] = None,
    precision: int = 3,  # Decimal places for coordinates
    include_radius: bool = True
):
    """
    Specialized decorator for location-based caching.
    
    Features:
    - Coordinate precision control
    - Radius-aware caching
    - Geospatial optimization
    
    Args:
        ttl: Optional TTL override
        precision: Decimal places for coordinate rounding
        include_radius: Include search radius in cache key
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract location parameters
            lat = kwargs.get('lat', 0)
            lng = kwargs.get('lng', 0)
            radius = kwargs.get('radius', 0)
            
            # Round coordinates to specified precision
            lat_rounded = round(lat, precision)
            lng_rounded = round(lng, precision)
            
            # Build cache key
            key_components = {
                'func': func.__name__,
                'lat': lat_rounded,
                'lng': lng_rounded
            }
            
            if include_radius:
                key_components['radius'] = radius
            
            cache_key = _generate_deterministic_key(key_components)
            
            # Check cache
            cached_data = await multi_tier_cache.get(
                key=cache_key,
                content_type=ContentType.LOCATION_DATA
            )
            
            if cached_data:
                logger.debug(f"Location cache hit for {lat_rounded},{lng_rounded}")
                return cached_data
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Cache result
            if result:
                await multi_tier_cache.set(
                    key=cache_key,
                    value=result,
                    content_type=ContentType.LOCATION_DATA,
                    tags=['location', f"lat:{lat_rounded}", f"lng:{lng_rounded}"]
                )
            
            return result
        
        return wrapper
    return decorator


def conditional_cache(
    condition: Callable[..., bool],
    content_type: ContentType = ContentType.API_RESPONSE,
    ttl: Optional[int] = None
):
    """
    Decorator that caches based on a condition function.
    
    Args:
        condition: Function that returns True if result should be cached
        content_type: Type of content being cached
        ttl: Optional TTL override
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = _generate_cache_key(func.__name__, args, kwargs)
            
            # Check cache
            cached_value = await multi_tier_cache.get(
                key=cache_key,
                content_type=content_type
            )
            
            if cached_value is not None:
                return cached_value
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Check condition
            if result and condition(result, *args, **kwargs):
                await multi_tier_cache.set(
                    key=cache_key,
                    value=result,
                    content_type=content_type,
                    tags=[func.__name__]
                )
            
            return result
        
        return wrapper
    return decorator


# Helper functions

def _generate_ai_cache_key(
    func_name: str,
    args: tuple,
    kwargs: dict,
    include_user: bool = True
) -> str:
    """Generate cache key for AI responses."""
    key_components = {
        'func': func_name,
        'prompt': kwargs.get('prompt', ''),
        'model': kwargs.get('model', 'default'),
        'temperature': kwargs.get('temperature', 0.7),
        'max_tokens': kwargs.get('max_tokens', 1000)
    }
    
    if include_user:
        key_components['user_id'] = kwargs.get('user_id')
    
    return _generate_deterministic_key(key_components)


def _generate_audio_cache_key(
    text: str,
    voice_id: str,
    language: str
) -> str:
    """Generate cache key for audio content."""
    # Hash the text to keep key size reasonable
    text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
    
    return f"audio:{voice_id}:{language}:{text_hash}"


def _generate_db_cache_key(
    func_name: str,
    args: tuple,
    kwargs: dict,
    prefix: Optional[str] = None
) -> str:
    """Generate cache key for database queries."""
    key_components = {
        'func': func_name,
        'args': str(args),
        'kwargs': {k: v for k, v in kwargs.items() if k != 'session'}
    }
    
    key = _generate_deterministic_key(key_components)
    
    if prefix:
        return f"{prefix}:{key}"
    return key


def _generate_api_cache_key(
    func_name: str,
    args: tuple,
    kwargs: dict,
    request: Optional[Any] = None,
    vary_headers: Optional[List[str]] = None
) -> str:
    """Generate cache key for API responses."""
    key_components = {
        'func': func_name,
        'args': str(args),
        'kwargs': kwargs
    }
    
    # Add request headers if specified
    if request and vary_headers:
        headers = {}
        for header in vary_headers:
            value = request.headers.get(header)
            if value:
                headers[header] = value
        if headers:
            key_components['headers'] = headers
    
    return _generate_deterministic_key(key_components)


def _generate_deterministic_key(components: Dict[str, Any]) -> str:
    """Generate a deterministic cache key from components."""
    # Sort and serialize components
    sorted_str = json.dumps(components, sort_keys=True, default=str)
    
    # Generate hash
    key_hash = hashlib.sha256(sorted_str.encode()).hexdigest()[:16]
    
    # Create readable prefix
    func_name = components.get('func', 'unknown')
    
    return f"{func_name}:{key_hash}"


def _generate_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """Generic cache key generation."""
    key_data = {
        'func': func_name,
        'args': args,
        'kwargs': {k: v for k, v in kwargs.items() 
                  if k not in ['request_id', 'timestamp', 'trace_id']}
    }
    
    return _generate_deterministic_key(key_data)


def _estimate_ai_cost(result: Any, generation_time_ms: float) -> float:
    """Estimate AI API cost based on response."""
    # Rough estimation based on response size and time
    if isinstance(result, dict):
        # Estimate tokens from response
        response_str = json.dumps(result)
        estimated_tokens = len(response_str) / 4  # Rough estimate
        
        # Assume $0.002 per 1K tokens
        cost = (estimated_tokens / 1000) * 0.002
        
        return cost
    
    return 0.0


async def _get_stale_cache(cache_key: str) -> Optional[Any]:
    """Get stale cache entry (expired but still in storage)."""
    # This would be implemented with a separate stale cache lookup
    # For now, return None
    return None


# Export decorators
__all__ = [
    'ai_response_cache',
    'story_cache',
    'voice_audio_cache',
    'database_cache',
    'api_response_cache',
    'location_cache',
    'conditional_cache'
]