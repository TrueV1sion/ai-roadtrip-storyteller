import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import timedelta
import json

from backend.app.core.cache import CacheManager


@pytest.fixture
async def cache_manager():
    manager = CacheManager()
    yield manager
    await manager.close()


@pytest.mark.asyncio
async def test_initialize_redis_success():
    """Test successful Redis initialization."""
    with patch('aioredis.create_redis_pool') as mock_redis:
        manager = CacheManager()
        mock_redis.return_value = AsyncMock()
        await manager.initialize()
        assert manager._redis is not None


@pytest.mark.asyncio
async def test_initialize_redis_failure():
    """Test graceful handling of Redis initialization failure."""
    with patch('aioredis.create_redis_pool') as mock_redis:
        manager = CacheManager()
        mock_redis.side_effect = Exception("Connection failed")
        await manager.initialize()
        assert manager._redis is None


@pytest.mark.asyncio
async def test_cache_set_get(cache_manager):
    """Test setting and getting values from cache."""
    mock_redis = AsyncMock()
    cache_manager._redis = mock_redis
    
    # Test data
    key = "test_key"
    value = {"data": "test_value"}
    
    # Mock Redis get/set methods
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.get = AsyncMock(return_value=json.dumps(value))
    
    # Test set
    success = await cache_manager.set(key, value)
    assert success is True
    mock_redis.set.assert_called_once_with(key, json.dumps(value))
    
    # Test get
    result = await cache_manager.get(key)
    assert result == value
    mock_redis.get.assert_called_once_with(key)


@pytest.mark.asyncio
async def test_cache_set_with_expiry(cache_manager):
    """Test setting cache with expiration time."""
    mock_redis = AsyncMock()
    cache_manager._redis = mock_redis
    
    key = "test_key"
    value = {"data": "test_value"}
    expire = timedelta(minutes=5)
    
    mock_redis.setex = AsyncMock(return_value=True)
    
    success = await cache_manager.set(key, value, expire=expire)
    assert success is True
    mock_redis.setex.assert_called_once_with(
        key,
        int(expire.total_seconds()),
        json.dumps(value)
    )


@pytest.mark.asyncio
async def test_offline_cache_fallback(cache_manager):
    """Test fallback to offline cache when Redis is unavailable."""
    key = "test_key"
    value = {"data": "test_value"}
    
    # Set value (Redis unavailable)
    cache_manager._redis = None
    success = await cache_manager.set(key, value)
    assert success is False
    
    # Value should still be in offline cache
    result = await cache_manager.get(key)
    assert result == value


@pytest.mark.asyncio
async def test_cache_delete(cache_manager):
    """Test deleting values from cache."""
    mock_redis = AsyncMock()
    cache_manager._redis = mock_redis
    
    key = "test_key"
    value = {"data": "test_value"}
    
    # Set value in offline cache
    cache_manager._offline_cache[key] = value
    mock_redis.delete = AsyncMock(return_value=1)
    
    # Delete value
    success = await cache_manager.delete(key)
    assert success is True
    assert key not in cache_manager._offline_cache
    mock_redis.delete.assert_called_once_with(key)


@pytest.mark.asyncio
async def test_cache_error_handling(cache_manager):
    """Test error handling in cache operations."""
    mock_redis = AsyncMock()
    cache_manager._redis = mock_redis
    
    key = "test_key"
    value = {"data": "test_value"}
    
    # Mock Redis errors
    mock_redis.set = AsyncMock(side_effect=Exception("Redis error"))
    mock_redis.get = AsyncMock(side_effect=Exception("Redis error"))
    
    # Test set error handling
    success = await cache_manager.set(key, value)
    assert success is False
    
    # Test get error handling
    result = await cache_manager.get(key)
    assert result is None 