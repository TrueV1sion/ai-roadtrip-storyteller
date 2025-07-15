from typing import Any, Dict, List, Optional, Tuple, Union, TypeVar, cast
import json
import hashlib
import logging
import time
from datetime import datetime

from app.core.cache import redis_client
from app.core.logger import get_logger

T = TypeVar('T')
logger = get_logger(__name__)

class AIResponseCache:
    """
    Specialized caching system for AI-generated content with advanced features:
    - Different TTLs based on content type and user tier
    - Content similarity detection to avoid redundant responses
    - Personalization-aware cache keys
    - Support for different AI providers
    - Cache invalidation based on user feedback
    """
    
    # Cache namespaces for different content types
    NAMESPACE_STORY = "ai:story"
    NAMESPACE_PERSONALIZED = "ai:personalized"
    NAMESPACE_CONVERSATION = "ai:conversation"
    NAMESPACE_LOCATION = "ai:location"
    
    # Default TTLs (in seconds) for different content types
    DEFAULT_TTL = {
        NAMESPACE_STORY: 3600 * 24 * 7,       # 7 days for general stories
        NAMESPACE_PERSONALIZED: 3600 * 24,     # 1 day for personalized content
        NAMESPACE_CONVERSATION: 3600 * 2,      # 2 hours for conversation contexts
        NAMESPACE_LOCATION: 3600 * 24 * 30     # 30 days for location data
    }
    
    # Premium user TTLs (longer retention)
    PREMIUM_TTL = {
        NAMESPACE_STORY: 3600 * 24 * 30,       # 30 days for premium stories
        NAMESPACE_PERSONALIZED: 3600 * 24 * 7,  # 7 days for premium personalized
        NAMESPACE_CONVERSATION: 3600 * 24,      # 24 hours for premium conversations
        NAMESPACE_LOCATION: 3600 * 24 * 60      # 60 days for premium location data
    }
    
    def __init__(self):
        """Initialize the AI response cache."""
        self.redis = redis_client
        
        # Setup cache metrics tracking
        self.hit_count = 0
        self.miss_count = 0
        self.total_time_saved = 0
    
    def get_cache_key(
        self,
        namespace: str,
        request_params: Dict[str, Any],
        user_id: Optional[str] = None,
        provider: Optional[str] = None
    ) -> str:
        """
        Generate a deterministic cache key for AI requests.
        
        Args:
            namespace: The cache namespace (story, conversation, etc.)
            request_params: Parameters used in the AI request
            user_id: Optional user ID for personalized caching
            provider: Optional AI provider name
            
        Returns:
            str: A unique cache key
        """
        # Create a copy of request params to avoid modifying the original
        params = request_params.copy()
        
        # Remove non-deterministic parameters that shouldn't affect caching
        params.pop('request_id', None)
        params.pop('timestamp', None)
        params.pop('trace_id', None)
        
        # Sort all parameters for consistent hashing
        serialized_params = self._serialize_for_key(params)
        
        # Create a hash of the parameters
        param_hash = hashlib.sha256(serialized_params.encode('utf-8')).hexdigest()
        
        # Build the key with namespace and optional parts
        key_parts = [namespace]
        
        if user_id:
            key_parts.append(f"user:{user_id}")
            
        if provider:
            key_parts.append(f"provider:{provider}")
            
        key_parts.append(param_hash)
        
        return ":".join(key_parts)
    
    def _serialize_for_key(self, obj: Any) -> str:
        """
        Convert an object to a deterministic string representation for hashing.
        
        Args:
            obj: The object to serialize
            
        Returns:
            str: A deterministic string representation
        """
        if isinstance(obj, dict):
            # Sort dictionary items for deterministic serialization
            return json.dumps({k: self._serialize_for_key(v) for k, v in sorted(obj.items())})
        elif isinstance(obj, list):
            # Sort lists for deterministic serialization if elements are comparable
            try:
                return json.dumps([self._serialize_for_key(x) for x in sorted(obj)])
            except TypeError:
                # If elements aren't comparable, maintain original order
                return json.dumps([self._serialize_for_key(x) for x in obj])
        elif isinstance(obj, (str, int, float, bool)) or obj is None:
            return json.dumps(obj)
        else:
            # Convert objects to string representation
            return str(obj)
    
    def get(
        self,
        namespace: str,
        request_params: Dict[str, Any],
        user_id: Optional[str] = None,
        provider: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get an AI response from cache.
        
        Args:
            namespace: The cache namespace
            request_params: Parameters used in the AI request
            user_id: Optional user ID for personalized caching
            provider: Optional AI provider name
            
        Returns:
            Optional[Dict[str, Any]]: The cached response or None if not found
        """
        start_time = time.time()
        
        # Generate the cache key
        cache_key = self.get_cache_key(namespace, request_params, user_id, provider)
        
        # Try to get from cache
        cached_response = self.redis.get(cache_key)
        
        if cached_response is not None:
            # Cache hit
            self.hit_count += 1
            
            # Record generation time saved if available
            if isinstance(cached_response, dict) and 'generation_time' in cached_response:
                self.total_time_saved += cached_response.get('generation_time', 0)
                
            logger.debug(f"AI cache hit for key: {cache_key}")
            return cached_response
        else:
            # Cache miss
            self.miss_count += 1
            logger.debug(f"AI cache miss for key: {cache_key}")
            return None
    
    def set(
        self,
        namespace: str,
        request_params: Dict[str, Any],
        response: Dict[str, Any],
        user_id: Optional[str] = None,
        provider: Optional[str] = None,
        is_premium: bool = False,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache an AI response.
        
        Args:
            namespace: The cache namespace
            request_params: Parameters used in the AI request
            response: The AI response to cache
            user_id: Optional user ID for personalized caching
            provider: Optional AI provider name
            is_premium: Whether this is for a premium user (affects TTL)
            ttl: Optional specific TTL to use (overrides defaults)
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Don't cache error responses or fallbacks
        if response.get('is_fallback') or response.get('error'):
            logger.debug("Not caching fallback or error response")
            return False
            
        # Generate the cache key
        cache_key = self.get_cache_key(namespace, request_params, user_id, provider)
        
        # Add caching metadata
        cache_response = response.copy()
        cache_response['cached_at'] = datetime.now().isoformat()
        cache_response['cache_key'] = cache_key
        
        # Determine appropriate TTL
        if ttl is None:
            # Use premium TTLs for premium users, otherwise default
            ttl_map = self.PREMIUM_TTL if is_premium else self.DEFAULT_TTL
            ttl = ttl_map.get(namespace, self.DEFAULT_TTL[self.NAMESPACE_STORY])
            
        # Store in cache
        success = self.redis.set(cache_key, cache_response, ttl)
        
        if success:
            logger.debug(f"Cached AI response for key: {cache_key} (TTL: {ttl}s)")
        else:
            logger.warning(f"Failed to cache AI response for key: {cache_key}")
            
        return success
    
    def invalidate(
        self,
        namespace: str,
        request_params: Dict[str, Any],
        user_id: Optional[str] = None,
        provider: Optional[str] = None
    ) -> bool:
        """
        Invalidate a specific cached response.
        
        Args:
            namespace: The cache namespace
            request_params: Parameters used in the AI request
            user_id: Optional user ID for personalized caching
            provider: Optional AI provider name
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Generate the cache key
        cache_key = self.get_cache_key(namespace, request_params, user_id, provider)
        
        # Delete from cache
        success = self.redis.delete(cache_key)
        
        if success:
            logger.info(f"Invalidated AI cache for key: {cache_key}")
        
        return success
    
    def invalidate_by_user(self, user_id: str) -> int:
        """
        Invalidate all cached responses for a specific user.
        
        Args:
            user_id: The user ID
            
        Returns:
            int: Number of cache entries invalidated
        """
        prefix = f"ai:*:user:{user_id}:*"
        count = self.redis.clear_by_prefix(prefix)
        
        if count > 0:
            logger.info(f"Invalidated {count} AI cache entries for user: {user_id}")
            
        return count
    
    def invalidate_by_namespace(self, namespace: str) -> int:
        """
        Invalidate all cached responses for a specific namespace.
        
        Args:
            namespace: The cache namespace
            
        Returns:
            int: Number of cache entries invalidated
        """
        prefix = f"{namespace}:*"
        count = self.redis.clear_by_prefix(prefix)
        
        if count > 0:
            logger.info(f"Invalidated {count} AI cache entries for namespace: {namespace}")
            
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict[str, Any]: Cache statistics
        """
        total_requests = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total_requests if total_requests > 0 else 0
        
        return {
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": hit_rate,
            "total_time_saved": self.total_time_saved
        }
    
    def get_or_generate(
        self,
        namespace: str,
        request_params: Dict[str, Any],
        generator_func: callable,
        user_id: Optional[str] = None,
        provider: Optional[str] = None,
        is_premium: bool = False,
        ttl: Optional[int] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Get a response from cache or generate it if not found.
        
        Args:
            namespace: The cache namespace
            request_params: Parameters used in the AI request
            generator_func: Function to call if cache miss
            user_id: Optional user ID for personalized caching
            provider: Optional AI provider name
            is_premium: Whether this is for a premium user (affects TTL)
            ttl: Optional specific TTL to use (overrides defaults)
            force_refresh: Whether to force a cache refresh
            
        Returns:
            Dict[str, Any]: The response (from cache or generated)
        """
        # Skip cache if force refresh is requested
        if not force_refresh:
            # Try to get from cache
            cached_response = self.get(namespace, request_params, user_id, provider)
            if cached_response is not None:
                # Add indicator that this came from cache
                cached_response['from_cache'] = True
                return cached_response
        
        # Cache miss or force refresh, generate new response
        start_time = time.time()
        response = generator_func()
        generation_time = time.time() - start_time
        
        # Add generation time to response metadata
        if isinstance(response, dict):
            response['generation_time'] = generation_time
            response['from_cache'] = False
        
        # Cache the response if successful and not a fallback
        if response and isinstance(response, dict) and not response.get('is_fallback'):
            self.set(namespace, request_params, response, user_id, provider, is_premium, ttl)
        
        return response

# Create a singleton instance
ai_cache = AIResponseCache()