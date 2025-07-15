from typing import Dict, List, Optional, Any, Union, Callable
import json
import logging
import uuid
import time
from datetime import datetime

from app.core.unified_ai_client import UnifiedAIClient, StoryStyle, AIModelProvider
from app.core.ai_cache import ai_cache
from app.core.logger import get_logger

logger = get_logger(__name__)


class CachedAIClient(UnifiedAIClient):
    """
    Enhanced AI client that extends the UnifiedAIClient with specialized caching
    functionality for optimal performance and cost savings.
    """
    
    def __init__(self, initialize_now: bool = True):
        """
        Initialize the cached AI client.
        
        Args:
            initialize_now: Whether to initialize the AI models immediately
        """
        super().__init__(initialize_now)
        self.cache = ai_cache
        logger.info("CachedAIClient initialized with specialized AI cache")
        
    async def generate_story(
        self,
        location: Dict[str, float],
        interests: List[str],
        context: Optional[Dict[str, Any]] = None,
        style: StoryStyle = StoryStyle.DEFAULT,
        conversation_id: Optional[str] = None,
        force_refresh: bool = False,
        user_id: Optional[str] = None,
        is_premium: bool = False
    ) -> Dict[str, Any]:
        """
        Generate a location-based story with caching support.
        
        Args:
            location: Dictionary with 'latitude' and 'longitude'
            interests: List of user interests
            context: Optional context information (weather, time, etc.)
            style: Storytelling style
            conversation_id: Optional ID for maintaining conversation context
            force_refresh: Whether to bypass cache and generate a new response
            user_id: Optional user ID for personalized caching
            is_premium: Whether the request is from a premium user (affects cache TTL)
            
        Returns:
            Dict with story text and metadata
        """
        start_time = time.time()
        
        # Make sure we're initialized
        if not self.initialized:
            success = self.initialize()
            if not success:
                return self._create_fallback_response(
                    location, interests, start_time,
                    "AI client initialization failed"
                )
        
        # Skip cache for conversation-based stories (they're typically more dynamic)
        if conversation_id:
            return await super().generate_story(
                location=location,
                interests=interests,
                context=context,
                style=style,
                conversation_id=conversation_id
            )
        
        # Prepare request parameters for cache key generation
        request_params = {
            "location": {
                "latitude": location.get("latitude"),
                "longitude": location.get("longitude")
            },
            "interests": sorted(interests) if interests else [],
            "style": style.value if style else StoryStyle.DEFAULT.value
        }
        
        # Add context parameters that affect story generation
        if context:
            # Only include relevant context values that affect the story
            cacheable_context = {}
            for key in ["time_of_day", "weather", "mood", "special_requests"]:
                if key in context:
                    cacheable_context[key] = context[key]
                    
            if cacheable_context:
                request_params["context"] = cacheable_context
        
        # Define generator function for cache miss
        async def story_generator() -> Dict[str, Any]:
            response = await super().generate_story(
                location=location,
                interests=interests,
                context=context,
                style=style,
                conversation_id=None  # Don't use conversation for cached stories
            )
            return response
        
        # Use cache with appropriate namespace
        namespace = ai_cache.NAMESPACE_STORY
        if context and context.get("user_preferences"):
            # If this is a personalized story, use personalized namespace
            namespace = ai_cache.NAMESPACE_PERSONALIZED
            
        # Get from cache or generate new
        response = self.cache.get_or_generate(
            namespace=namespace,
            request_params=request_params,
            generator_func=story_generator,
            user_id=user_id,
            provider=self.provider,
            is_premium=is_premium,
            force_refresh=force_refresh
        )
        
        return response
        
    async def generate_personalized_story(
        self,
        user_id: Optional[str],
        location: Dict[str, float],
        interests: List[str],
        user_preferences: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        style: Optional[StoryStyle] = None,
        force_refresh: bool = False,
        is_premium: bool = False
    ) -> Dict[str, Any]:
        """
        Generate a personalized story based on user preferences with caching.
        
        Args:
            user_id: Optional user identifier for logging and context
            location: Dictionary with 'latitude' and 'longitude'
            interests: List of user interests
            user_preferences: User preferences for personalization
            context: Optional additional context
            style: Optional storytelling style (will be derived from preferences if not provided)
            force_refresh: Whether to bypass cache and generate a new response
            is_premium: Whether the request is from a premium user (affects cache TTL)
            
        Returns:
            Dict with story text and metadata
        """
        start_time = time.time()
        
        # Determine style from preferences if not provided
        if not style and user_preferences and "storytelling_style" in user_preferences:
            pref_style = user_preferences["storytelling_style"]
            try:
                style = StoryStyle(pref_style)
            except ValueError:
                style = StoryStyle.DEFAULT
                logger.warning(f"Unknown storytelling style: {pref_style}, using default")
        
        if not style:
            style = StoryStyle.DEFAULT
        
        # Make sure we're initialized
        if not self.initialized:
            success = self.initialize()
            if not success:
                return self._create_fallback_response(
                    location, interests, start_time,
                    "AI client initialization failed"
                )
        
        # Prepare request parameters for cache key generation
        request_params = {
            "location": {
                "latitude": location.get("latitude"),
                "longitude": location.get("longitude")
            },
            "interests": sorted(interests) if interests else [],
            "style": style.value
        }
        
        # Add user preferences that affect story generation
        if user_preferences:
            # Only include relevant preference values
            cacheable_prefs = {}
            for key, value in user_preferences.items():
                # Skip complex objects and lists, focus on simple preferences
                if isinstance(value, (str, int, float, bool)) or value is None:
                    cacheable_prefs[key] = value
                    
            if cacheable_prefs:
                request_params["preferences"] = cacheable_prefs
        
        # Add other context parameters
        if context:
            cacheable_context = {}
            for key in ["time_of_day", "weather", "mood", "special_requests"]:
                if key in context:
                    cacheable_context[key] = context[key]
                    
            if cacheable_context:
                request_params["context"] = cacheable_context
        
        # Define generator function for cache miss
        async def personalized_story_generator() -> Dict[str, Any]:
            # Combine context with user preferences
            enhanced_context = context or {}
            if user_preferences:
                enhanced_context["user_preferences"] = user_preferences
            
            # Call the base story generation method with enhanced context
            story_result = await super().generate_story(
                location=location,
                interests=interests,
                context=enhanced_context,
                style=style
            )
            
            # Add user ID to the result if provided
            if user_id:
                story_result["user_id"] = user_id
            
            return story_result
        
        # Use personalized cache namespace
        namespace = ai_cache.NAMESPACE_PERSONALIZED
        
        # Get from cache or generate new
        response = self.cache.get_or_generate(
            namespace=namespace,
            request_params=request_params,
            generator_func=personalized_story_generator,
            user_id=user_id,
            provider=self.provider,
            is_premium=is_premium,
            force_refresh=force_refresh
        )
        
        return response
    
    def clear_user_cache(self, user_id: str) -> int:
        """
        Clear all cached responses for a specific user.
        
        Args:
            user_id: The user ID
            
        Returns:
            int: Number of cache entries invalidated
        """
        return self.cache.invalidate_by_user(user_id)
    
    def clear_story_cache(self) -> int:
        """
        Clear all story caches.
        
        Returns:
            int: Number of cache entries invalidated
        """
        return self.cache.invalidate_by_namespace(ai_cache.NAMESPACE_STORY)
    
    def clear_personalized_cache(self) -> int:
        """
        Clear all personalized story caches.
        
        Returns:
            int: Number of cache entries invalidated
        """
        return self.cache.invalidate_by_namespace(ai_cache.NAMESPACE_PERSONALIZED)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict[str, Any]: Cache statistics
        """
        return self.cache.get_stats()


# Create a singleton instance
cached_ai_client = CachedAIClient()