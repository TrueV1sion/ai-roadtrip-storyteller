from typing import Any, Callable, Dict, Optional, Tuple, Type, TypeVar, Union, cast
import json
import hashlib
import inspect
import logging
import time
from functools import wraps
import os

import redis
from redis.exceptions import RedisError
from fastapi import Request, Response

from app.core.config import settings

logger = logging.getLogger(__name__)

# Import mock mode if enabled
if os.getenv('MOCK_REDIS', 'false').lower() == 'true':
    from app.core.mock_mode import MockRedis

T = TypeVar('T')

class RedisClient:
    """Redis client for caching data."""
    
    def __init__(self):
        """Initialize Redis client with configuration from settings."""
        # Check if we should use mock Redis
        if os.getenv('MOCK_REDIS', 'false').lower() == 'true':
            logger.info("Using mock Redis for development")
            self._redis = MockRedis()
            self.pool = None
            return
            
        try:
            # Create Redis connection pool
            self.pool = redis.ConnectionPool(
                host=getattr(settings, "REDIS_HOST", "localhost"),
                port=getattr(settings, "REDIS_PORT", 6379),
                db=getattr(settings, "REDIS_DB", 0),
                password=getattr(settings, "REDIS_PASSWORD", None),
                socket_timeout=getattr(settings, "REDIS_SOCKET_TIMEOUT", 5),
                socket_connect_timeout=getattr(settings, "REDIS_SOCKET_CONNECT_TIMEOUT", 5),
                retry_on_timeout=True,
                decode_responses=False,  # We handle serialization ourselves
            )
            
            # Create Redis client
            self._redis = redis.Redis(connection_pool=self.pool)
            
            # Test connection
            self._redis.ping()
            logger.info("Redis client initialized successfully")
            
        except RedisError as e:
            logger.error(f"Failed to initialize Redis client: {str(e)}")
            # Create a dummy Redis client that doesn't do anything
            self._redis = None
    
    @property
    def client(self) -> Optional[redis.Redis]:
        """Get the Redis client."""
        return self._redis
    
    @property
    def is_available(self) -> bool:
        """Check if Redis is available."""
        if self._redis is None:
            return False
        
        try:
            self._redis.ping()
            return True
        except RedisError:
            logger.warning("Redis is not available")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from Redis.
        
        Args:
            key: Cache key
            
        Returns:
            Optional[Any]: Deserialized value or None if not found
        """
        if not self.is_available:
            return None
        
        try:
            data = self._redis.get(key)
            if data is None:
                return None
            
            return self._deserialize(data)
        except RedisError as e:
            logger.error(f"Error getting key {key} from Redis: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error deserializing data for key {key}: {str(e)}")
            return None
    
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set a value in Redis.
        
        Args:
            key: Cache key
            value: Value to store
            ttl: Time-to-live in seconds (None for no expiration)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_available:
            return False
        
        try:
            serialized = self._serialize(value)
            
            if ttl is None:
                ttl = getattr(settings, "REDIS_CACHE_TTL_DEFAULT", 3600)  # Default 1 hour
                
            success = self._redis.set(key, serialized, ex=ttl)
            return bool(success)
        except RedisError as e:
            logger.error(f"Error setting key {key} in Redis: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error serializing data for key {key}: {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete a key from Redis.
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_available:
            return False
        
        try:
            success = self._redis.delete(key)
            return bool(success)
        except RedisError as e:
            logger.error(f"Error deleting key {key} from Redis: {str(e)}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in Redis.
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if the key exists, False otherwise
        """
        if not self.is_available:
            return False
        
        try:
            return bool(self._redis.exists(key))
        except RedisError as e:
            logger.error(f"Error checking if key {key} exists in Redis: {str(e)}")
            return False
    
    def get_or_set(
        self, 
        key: str, 
        callback: Callable[[], T], 
        ttl: Optional[int] = None
    ) -> T:
        """
        Get a value from Redis or set it using the callback.
        
        Args:
            key: Cache key
            callback: Function to call if key not found
            ttl: Time-to-live in seconds (None for default)
            
        Returns:
            T: Deserialized value from cache or callback result
        """
        # Try to get from cache first
        cached_value = self.get(key)
        if cached_value is not None:
            logger.debug(f"Cache hit for key {key}")
            return cast(T, cached_value)
        
        # Cache miss, get value from callback
        logger.debug(f"Cache miss for key {key}")
        value = callback()
        
        # Store value in cache if available
        if value is not None:
            self.set(key, value, ttl)
        
        return value
    
    def clear_by_prefix(self, prefix: str) -> int:
        """
        Clear all keys with a specific prefix.
        
        Args:
            prefix: Key prefix to match
            
        Returns:
            int: Number of keys deleted
        """
        if not self.is_available:
            return 0
        
        try:
            # Find all keys with the given prefix
            keys = self._redis.keys(f"{prefix}*")
            if not keys:
                return 0
            
            # Delete all matching keys
            return self._redis.delete(*keys)
        except RedisError as e:
            logger.error(f"Error clearing keys with prefix {prefix}: {str(e)}")
            return 0
    
    def _serialize(self, value: Any) -> bytes:
        """
        Serialize value to JSON and encode to bytes.
        
        Args:
            value: Any JSON-serializable value
            
        Returns:
            bytes: Serialized value
        """
        return json.dumps(value).encode('utf-8')
    
    def _deserialize(self, data: bytes) -> Any:
        """
        Deserialize bytes to Python object.
        
        Args:
            data: Serialized data
            
        Returns:
            Any: Deserialized value
        """
        return json.loads(data.decode('utf-8'))
    
    def __del__(self):
        """Clean up resources on deletion."""
        if hasattr(self, 'pool'):
            self.pool.disconnect()


# Singleton instance
redis_client = RedisClient()


def generate_cache_key(
    namespace: str,
    identifier: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate a cache key with namespace and optional identifier and params.
    
    Args:
        namespace: Key namespace (e.g., 'story', 'user')
        identifier: Optional identifier (e.g., user_id, story_id)
        params: Optional parameters to include in key
        
    Returns:
        str: Cache key
    """
    key_parts = [namespace]
    
    if identifier:
        key_parts.append(str(identifier))
        
    if params:
        # Sort params to ensure consistent key generation
        sorted_params = sorted(params.items())
        # Create a hash of the parameters
        param_hash = hashlib.md5(str(sorted_params).encode()).hexdigest()
        key_parts.append(param_hash)
    
    return ":".join(key_parts)


def cacheable(
    namespace: str,
    ttl: Optional[int] = None,
    key_builder: Optional[Callable] = None,
    skip_cache_if: Optional[Callable[[Request], bool]] = None
):
    """
    Decorator for FastAPI endpoint to cache responses.
    
    Args:
        namespace: Cache namespace for the endpoint
        ttl: Time-to-live in seconds (None for default)
        key_builder: Optional function to build cache key
        skip_cache_if: Optional function to determine if cache should be skipped
        
    Returns:
        Callable: Decorated endpoint function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request object from args or kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
                    
            if request is None:
                request = kwargs.get('request')
                
            # Skip cache if necessary
            if request and skip_cache_if and skip_cache_if(request):
                return await func(*args, **kwargs)
                
            # Check if no-cache header is present
            if request and request.headers.get('Cache-Control') == 'no-cache':
                return await func(*args, **kwargs)
                
            # Generate cache key
            if key_builder:
                # Custom key builder function
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default key building
                # Extract path parameters from kwargs
                path_params = {}
                sig = inspect.signature(func)
                for param_name, param in sig.parameters.items():
                    if param_name in kwargs:
                        path_params[param_name] = kwargs[param_name]
                
                # Extract query parameters from request
                query_params = {}
                if request:
                    for k, v in request.query_params.items():
                        query_params[k] = v
                
                # Combine parameters
                params = {**path_params, **query_params}
                
                # Get identifier from path parameters if any
                identifier = next(iter(path_params.values()), None)
                
                cache_key = generate_cache_key(namespace, identifier, params)
                
            # Try to get from cache
            cached_response = redis_client.get(cache_key)
            if cached_response is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_response
                
            # Cache miss, call the original function
            logger.debug(f"Cache miss for {cache_key}")
            start_time = time.time()
            response = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Cache the response
            if response is not None:
                redis_client.set(cache_key, response, ttl)
                logger.debug(f"Cached response for {cache_key} (took {execution_time:.4f}s)")
                
            return response
        return wrapper
    return decorator


# Create singleton instance
_redis_client = None

def get_cache() -> RedisClient:
    """Get or create the Redis client singleton instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client

# Create a default cache manager instance for backward compatibility
cache_manager = RedisClient()
