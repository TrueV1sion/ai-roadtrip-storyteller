import pytest
import asyncio
from unittest.mock import MagicMock, patch
import time
from typing import Dict, Any

from app.core.ai_cache import AIResponseCache
from app.core.unified_ai_client_cached import CachedAIClient
from app.core.unified_ai_client import StoryStyle


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    redis_mock = MagicMock()
    redis_mock.get.return_value = None  # Default to cache miss
    redis_mock.set.return_value = True  # Default to successful set
    redis_mock.delete.return_value = True  # Default to successful delete
    redis_mock.clear_by_prefix.return_value = 5  # Default to 5 entries cleared
    return redis_mock


@pytest.fixture
def ai_cache(mock_redis):
    """Create an AIResponseCache instance with a mock Redis client."""
    cache = AIResponseCache()
    cache.redis = mock_redis
    return cache


@pytest.fixture
def cached_ai_client():
    """Create a mock CachedAIClient instance."""
    client = MagicMock(spec=CachedAIClient)
    
    async def mock_generate_story(*args, **kwargs):
        """Mock the generate_story method."""
        return {
            "text": "This is a test story.",
            "provider": "google",
            "model": "gemini-pro",
            "style": "default",
            "generation_time": 2.5,
            "word_count": 10,
            "sentiment": "positive",
            "is_fallback": False
        }
    
    client.generate_story = mock_generate_story
    return client


class TestAICache:
    """Tests for the AIResponseCache class."""

    def test_cache_key_generation(self, ai_cache):
        """Test that cache keys are generated correctly."""
        # Test with simple params
        request_params = {"text": "test", "count": 5}
        key1 = ai_cache.get_cache_key(ai_cache.NAMESPACE_STORY, request_params)
        assert ai_cache.NAMESPACE_STORY in key1
        
        # Test with user ID
        key2 = ai_cache.get_cache_key(ai_cache.NAMESPACE_STORY, request_params, user_id="123")
        assert ai_cache.NAMESPACE_STORY in key2
        assert "user:123" in key2
        assert key1 != key2  # Different keys for different user IDs
        
        # Test with provider
        key3 = ai_cache.get_cache_key(ai_cache.NAMESPACE_STORY, request_params, 
                                       user_id="123", provider="google")
        assert "provider:google" in key3
        assert key2 != key3  # Different keys for different providers
        
        # Test deterministic behavior with same params in different order
        params1 = {"a": 1, "b": 2, "c": 3}
        params2 = {"c": 3, "b": 2, "a": 1}
        key4 = ai_cache.get_cache_key(ai_cache.NAMESPACE_STORY, params1)
        key5 = ai_cache.get_cache_key(ai_cache.NAMESPACE_STORY, params2)
        assert key4 == key5  # Same key for same params in different order

    def test_get_cache_hit(self, ai_cache, mock_redis):
        """Test cache hit behavior."""
        # Setup mock to return a cached response
        cached_data = {
            "text": "Cached story text",
            "generation_time": 1.5
        }
        mock_redis.get.return_value = cached_data
        
        # Call get method
        result = ai_cache.get(
            ai_cache.NAMESPACE_STORY,
            {"param": "value"},
            user_id="user123"
        )
        
        # Verify result
        assert result == cached_data
        assert ai_cache.hit_count == 1
        assert ai_cache.miss_count == 0

    def test_get_cache_miss(self, ai_cache, mock_redis):
        """Test cache miss behavior."""
        # Setup mock to return None (cache miss)
        mock_redis.get.return_value = None
        
        # Call get method
        result = ai_cache.get(
            ai_cache.NAMESPACE_STORY,
            {"param": "value"},
            user_id="user123"
        )
        
        # Verify result
        assert result is None
        assert ai_cache.hit_count == 0
        assert ai_cache.miss_count == 1

    def test_set_cache(self, ai_cache, mock_redis):
        """Test setting cache entries."""
        # Define test data
        namespace = ai_cache.NAMESPACE_STORY
        request_params = {"param": "value"}
        response = {"text": "Story text", "metadata": "test"}
        user_id = "user123"
        
        # Call set method
        result = ai_cache.set(namespace, request_params, response, user_id)
        
        # Verify result
        assert result is True
        mock_redis.set.assert_called_once()
        
        # Verify TTL selection based on user tier
        # Regular user TTL
        ai_cache.set(namespace, request_params, response, user_id, is_premium=False)
        ttl_regular = ai_cache.DEFAULT_TTL[namespace]
        
        # Premium user TTL
        ai_cache.set(namespace, request_params, response, user_id, is_premium=True)
        ttl_premium = ai_cache.PREMIUM_TTL[namespace]
        
        # Premium TTL should be longer
        assert ttl_premium > ttl_regular

    def test_get_or_generate_cached(self, ai_cache, mock_redis):
        """Test get_or_generate with a cache hit."""
        # Setup mock to return a cached response
        cached_data = {
            "text": "Cached story text",
            "from_cache": False  # This will be overwritten
        }
        mock_redis.get.return_value = cached_data
        
        # Mock generator function that should never be called
        generator_mock = MagicMock()
        generator_mock.return_value = {"text": "Generated text"}
        
        # Call get_or_generate
        result = ai_cache.get_or_generate(
            ai_cache.NAMESPACE_STORY,
            {"param": "value"},
            generator_mock,
            user_id="user123"
        )
        
        # Verify result
        assert result["text"] == "Cached story text"
        assert result["from_cache"] is True  # Should be added by get_or_generate
        generator_mock.assert_not_called()  # Generator should not be called on cache hit

    def test_get_or_generate_uncached(self, ai_cache, mock_redis):
        """Test get_or_generate with a cache miss."""
        # Setup mock to return None (cache miss)
        mock_redis.get.return_value = None
        
        # Mock generator function
        generated_data = {"text": "Generated text", "not_fallback": True}
        generator_mock = MagicMock()
        generator_mock.return_value = generated_data
        
        # Call get_or_generate
        result = ai_cache.get_or_generate(
            ai_cache.NAMESPACE_STORY,
            {"param": "value"},
            generator_mock,
            user_id="user123"
        )
        
        # Verify result
        assert result == generated_data
        generator_mock.assert_called_once()  # Generator should be called on cache miss
        mock_redis.set.assert_called_once()  # Result should be cached

    def test_get_or_generate_force_refresh(self, ai_cache, mock_redis):
        """Test get_or_generate with force_refresh=True."""
        # Setup mock to return a cached response
        cached_data = {"text": "Cached story text"}
        mock_redis.get.return_value = cached_data
        
        # Mock generator function
        generated_data = {"text": "Generated text", "not_fallback": True}
        generator_mock = MagicMock()
        generator_mock.return_value = generated_data
        
        # Call get_or_generate with force_refresh=True
        result = ai_cache.get_or_generate(
            ai_cache.NAMESPACE_STORY,
            {"param": "value"},
            generator_mock,
            user_id="user123",
            force_refresh=True
        )
        
        # Verify result
        assert result == generated_data
        generator_mock.assert_called_once()  # Generator should be called despite cache hit
        mock_redis.set.assert_called_once()  # Result should be cached

    def test_invalidate_cache(self, ai_cache, mock_redis):
        """Test cache invalidation."""
        # Setup test data
        namespace = ai_cache.NAMESPACE_STORY
        request_params = {"param": "value"}
        user_id = "user123"
        
        # Call invalidate method
        result = ai_cache.invalidate(namespace, request_params, user_id)
        
        # Verify result
        assert result is True
        mock_redis.delete.assert_called_once()

    def test_invalidate_by_user(self, ai_cache, mock_redis):
        """Test invalidation of all entries for a user."""
        # Call invalidate_by_user method
        count = ai_cache.invalidate_by_user("user123")
        
        # Verify result
        assert count == 5  # Our mock returns 5
        mock_redis.clear_by_prefix.assert_called_once()
        # Make sure the prefix includes the user ID
        assert "user:user123" in mock_redis.clear_by_prefix.call_args[0][0]

    def test_invalidate_by_namespace(self, ai_cache, mock_redis):
        """Test invalidation of all entries in a namespace."""
        # Call invalidate_by_namespace method
        count = ai_cache.invalidate_by_namespace(ai_cache.NAMESPACE_STORY)
        
        # Verify result
        assert count == 5  # Our mock returns 5
        mock_redis.clear_by_prefix.assert_called_once()
        # Make sure the prefix includes the namespace
        assert ai_cache.NAMESPACE_STORY in mock_redis.clear_by_prefix.call_args[0][0]


class TestCachedAIClient:
    """Tests for the CachedAIClient integration."""

    @pytest.mark.asyncio
    async def test_generate_story_with_cache(self):
        """Test that generate_story uses the cache properly."""
        # Create a real CachedAIClient but mock the parent class and cache
        with patch('app.core.unified_ai_client_cached.UnifiedAIClient') as mock_parent, \
             patch('app.core.unified_ai_client_cached.ai_cache') as mock_cache:
            
            # Setup mock cache to simulate a cache hit
            cached_response = {
                "text": "Cached story",
                "from_cache": True,
                "generation_time": 0  # Already generated
            }
            mock_cache.get_or_generate.return_value = cached_response
            
            # Create client and call generate_story
            client = CachedAIClient(initialize_now=False)
            client.initialized = True  # Skip initialization
            
            result = await client.generate_story(
                location={"latitude": 40.7128, "longitude": -74.0060},
                interests=["history", "architecture"],
                style=StoryStyle.DEFAULT,
                user_id="user123",
                is_premium=True
            )
            
            # Verify result uses cache
            assert result == cached_response
            assert result["from_cache"] is True
            assert mock_cache.get_or_generate.called
            
            # The parent's generate_story shouldn't be called directly for a cache hit
            mock_parent.generate_story.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_personalized_story_with_cache(self):
        """Test that generate_personalized_story uses the cache properly."""
        # Create a real CachedAIClient but mock the parent class and cache
        with patch('app.core.unified_ai_client_cached.UnifiedAIClient') as mock_parent, \
             patch('app.core.unified_ai_client_cached.ai_cache') as mock_cache:
            
            # Setup mock for super().generate_story used inside generate_personalized_story
            async def mock_generate():
                return {
                    "text": "Generated personalized story",
                    "from_cache": False,
                    "generation_time": 3.5
                }
            
            # Setup mock cache to simulate a cache miss then generation
            mock_cache.get_or_generate = MagicMock()
            mock_cache.get_or_generate.return_value = {
                "text": "Generated personalized story",
                "from_cache": False,
                "generation_time": 3.5
            }
            
            # Create client
            client = CachedAIClient(initialize_now=False)
            client.initialized = True  # Skip initialization
            
            # Call generate_personalized_story
            user_preferences = {"theme": "adventure", "detail_level": "high"}
            result = await client.generate_personalized_story(
                user_id="user123",
                location={"latitude": 40.7128, "longitude": -74.0060},
                interests=["history", "architecture"],
                user_preferences=user_preferences,
                style=StoryStyle.ADVENTURE,
                is_premium=True
            )
            
            # Verify result
            assert "text" in result
            assert mock_cache.get_or_generate.called
            
            # Verify it used the personalized namespace
            cache_call = mock_cache.get_or_generate.call_args
            assert cache_call[1]["namespace"] == mock_cache.NAMESPACE_PERSONALIZED

    def test_clear_user_cache(self):
        """Test user cache clearing functionality."""
        with patch('app.core.unified_ai_client_cached.ai_cache') as mock_cache:
            mock_cache.invalidate_by_user.return_value = 10
            
            client = CachedAIClient(initialize_now=False)
            result = client.clear_user_cache("user123")
            
            assert result == 10
            mock_cache.invalidate_by_user.assert_called_once_with("user123")

    def test_get_cache_stats(self):
        """Test cache statistics retrieval."""
        with patch('app.core.unified_ai_client_cached.ai_cache') as mock_cache:
            mock_cache.get_stats.return_value = {
                "hit_count": 150,
                "miss_count": 50,
                "hit_rate": 0.75,
                "total_time_saved": 375.5
            }
            
            client = CachedAIClient(initialize_now=False)
            stats = client.get_cache_stats()
            
            assert stats["hit_count"] == 150
            assert stats["miss_count"] == 50
            assert stats["hit_rate"] == 0.75
            assert stats["total_time_saved"] == 375.5
            mock_cache.get_stats.assert_called_once()