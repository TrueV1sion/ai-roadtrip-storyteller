import pytest
from unittest.mock import patch, Mock, MagicMock
import json
import redis
from redis.exceptions import RedisError
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient

from app.core.cache import (
    RedisClient, 
    redis_client, 
    generate_cache_key, 
    cacheable
)


class TestRedisClient:
    """Test suite for RedisClient class."""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        with patch('redis.Redis') as mock_redis:
            mock_instance = Mock()
            mock_redis.return_value = mock_instance
            yield mock_instance
    
    @pytest.fixture
    def mock_pool(self):
        """Mock Redis connection pool."""
        with patch('redis.ConnectionPool') as mock_pool:
            yield mock_pool
    
    def test_init_success(self, mock_redis, mock_pool):
        """Test successful initialization."""
        client = RedisClient()
        
        # Test connection pool is created
        mock_pool.assert_called_once()
        
        # Test Redis client is created
        assert client._redis is not None
    
    def test_init_failure(self, mock_redis, mock_pool):
        """Test initialization with connection error."""
        # Make Redis ping raise an exception
        mock_redis.return_value.ping.side_effect = RedisError("Connection failed")
        
        client = RedisClient()
        
        # Test Redis client is None on failure
        assert client._redis is None
    
    def test_is_available_success(self, mock_redis):
        """Test is_available returns True when Redis is available."""
        client = RedisClient()
        mock_redis.return_value.ping.return_value = True
        
        assert client.is_available is True
    
    def test_is_available_failure(self, mock_redis):
        """Test is_available returns False when Redis is not available."""
        client = RedisClient()
        mock_redis.return_value.ping.side_effect = RedisError("Connection failed")
        
        assert client.is_available is False
    
    def test_get_success(self, mock_redis):
        """Test get returns deserialized value on success."""
        client = RedisClient()
        mock_data = json.dumps({"key": "value"}).encode('utf-8')
        mock_redis.return_value.get.return_value = mock_data
        
        result = client.get("test_key")
        
        mock_redis.return_value.get.assert_called_once_with("test_key")
        assert result == {"key": "value"}
    
    def test_get_not_found(self, mock_redis):
        """Test get returns None when key not found."""
        client = RedisClient()
        mock_redis.return_value.get.return_value = None
        
        result = client.get("test_key")
        
        assert result is None
    
    def test_get_redis_error(self, mock_redis):
        """Test get handles RedisError."""
        client = RedisClient()
        mock_redis.return_value.get.side_effect = RedisError("Get failed")
        
        result = client.get("test_key")
        
        assert result is None
    
    def test_set_success(self, mock_redis):
        """Test set returns True on success."""
        client = RedisClient()
        mock_redis.return_value.set.return_value = True
        
        result = client.set("test_key", {"key": "value"}, 300)
        
        assert result is True
        mock_redis.return_value.set.assert_called_once()
    
    def test_set_redis_error(self, mock_redis):
        """Test set handles RedisError."""
        client = RedisClient()
        mock_redis.return_value.set.side_effect = RedisError("Set failed")
        
        result = client.set("test_key", {"key": "value"})
        
        assert result is False
    
    def test_delete_success(self, mock_redis):
        """Test delete returns True on success."""
        client = RedisClient()
        mock_redis.return_value.delete.return_value = 1
        
        result = client.delete("test_key")
        
        assert result is True
        mock_redis.return_value.delete.assert_called_once_with("test_key")
    
    def test_delete_redis_error(self, mock_redis):
        """Test delete handles RedisError."""
        client = RedisClient()
        mock_redis.return_value.delete.side_effect = RedisError("Delete failed")
        
        result = client.delete("test_key")
        
        assert result is False
    
    def test_exists_success(self, mock_redis):
        """Test exists returns True when key exists."""
        client = RedisClient()
        mock_redis.return_value.exists.return_value = 1
        
        result = client.exists("test_key")
        
        assert result is True
        mock_redis.return_value.exists.assert_called_once_with("test_key")
    
    def test_exists_redis_error(self, mock_redis):
        """Test exists handles RedisError."""
        client = RedisClient()
        mock_redis.return_value.exists.side_effect = RedisError("Exists failed")
        
        result = client.exists("test_key")
        
        assert result is False
    
    def test_get_or_set_cache_hit(self, mock_redis):
        """Test get_or_set returns cached value on cache hit."""
        client = RedisClient()
        mock_data = json.dumps({"key": "value"}).encode('utf-8')
        mock_redis.return_value.get.return_value = mock_data
        callback = Mock()
        
        result = client.get_or_set("test_key", callback)
        
        assert result == {"key": "value"}
        callback.assert_not_called()
    
    def test_get_or_set_cache_miss(self, mock_redis):
        """Test get_or_set calls callback on cache miss."""
        client = RedisClient()
        mock_redis.return_value.get.return_value = None
        callback = Mock(return_value={"key": "value"})
        
        result = client.get_or_set("test_key", callback)
        
        assert result == {"key": "value"}
        callback.assert_called_once()
        mock_redis.return_value.set.assert_called_once()
    
    def test_clear_by_prefix_success(self, mock_redis):
        """Test clear_by_prefix returns count of deleted keys."""
        client = RedisClient()
        mock_redis.return_value.keys.return_value = ["prefix:1", "prefix:2"]
        mock_redis.return_value.delete.return_value = 2
        
        result = client.clear_by_prefix("prefix")
        
        assert result == 2
        mock_redis.return_value.keys.assert_called_once_with("prefix*")
        mock_redis.return_value.delete.assert_called_once_with("prefix:1", "prefix:2")
    
    def test_clear_by_prefix_no_keys(self, mock_redis):
        """Test clear_by_prefix returns 0 when no keys match."""
        client = RedisClient()
        mock_redis.return_value.keys.return_value = []
        
        result = client.clear_by_prefix("prefix")
        
        assert result == 0
        mock_redis.return_value.delete.assert_not_called()
    
    def test_clear_by_prefix_redis_error(self, mock_redis):
        """Test clear_by_prefix handles RedisError."""
        client = RedisClient()
        mock_redis.return_value.keys.side_effect = RedisError("Keys failed")
        
        result = client.clear_by_prefix("prefix")
        
        assert result == 0


class TestCacheKeyGeneration:
    """Test suite for cache key generation functions."""
    
    def test_generate_cache_key_simple(self):
        """Test generate_cache_key with namespace only."""
        key = generate_cache_key("test")
        assert key == "test"
    
    def test_generate_cache_key_with_identifier(self):
        """Test generate_cache_key with namespace and identifier."""
        key = generate_cache_key("test", "123")
        assert key == "test:123"
    
    def test_generate_cache_key_with_params(self):
        """Test generate_cache_key with namespace, identifier, and params."""
        key = generate_cache_key("test", "123", {"a": 1, "b": 2})
        
        # The key should contain the namespace, identifier, and a hash of the params
        parts = key.split(":")
        assert len(parts) == 3
        assert parts[0] == "test"
        assert parts[1] == "123"
        # Don't check the exact hash, just that it's there
        assert len(parts[2]) > 0


@pytest.mark.asyncio
class TestCacheableDecorator:
    """Test suite for cacheable decorator."""
    
    @pytest.fixture
    def app(self):
        """Create FastAPI app with cached endpoint."""
        app = FastAPI()
        
        # Create a mock Redis client for testing
        redis_mock = Mock()
        redis_mock.get.return_value = None
        redis_mock.set.return_value = True
        redis_mock.is_available = True
        
        # Create test endpoints
        @app.get("/test")
        @cacheable(namespace="test")
        async def test_endpoint(request: Request):
            return {"value": "test"}
        
        @app.get("/test/{id}")
        @cacheable(namespace="test", ttl=60)
        async def test_with_id(id: str, request: Request):
            return {"id": id, "value": "test"}
        
        @app.get("/nocache")
        @cacheable(
            namespace="test",
            skip_cache_if=lambda req: req.headers.get("x-no-cache") == "true"
        )
        async def test_skip_cache(request: Request):
            return {"value": "nocache"}
        
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create TestClient for FastAPI app."""
        return TestClient(app)
    
    @patch("app.core.cache.redis_client")
    async def test_cacheable_cache_miss(self, mock_redis, client):
        """Test cacheable decorator with cache miss."""
        # Set up mock Redis
        mock_redis.get.return_value = None
        mock_redis.is_available = True
        
        # Make request
        response = client.get("/test")
        
        # Check response
        assert response.status_code == 200
        assert response.json() == {"value": "test"}
        
        # Check Redis interactions
        mock_redis.get.assert_called_once()
        mock_redis.set.assert_called_once()
    
    @patch("app.core.cache.redis_client")
    async def test_cacheable_cache_hit(self, mock_redis, client):
        """Test cacheable decorator with cache hit."""
        # Set up mock Redis
        mock_redis.get.return_value = {"value": "cached"}
        mock_redis.is_available = True
        
        # Make request
        response = client.get("/test")
        
        # Check response
        assert response.status_code == 200
        assert response.json() == {"value": "cached"}
        
        # Check Redis interactions
        mock_redis.get.assert_called_once()
        mock_redis.set.assert_not_called()
    
    @patch("app.core.cache.redis_client")
    async def test_cacheable_with_path_params(self, mock_redis, client):
        """Test cacheable decorator with path parameters."""
        # Set up mock Redis
        mock_redis.get.return_value = None
        mock_redis.is_available = True
        
        # Make request
        response = client.get("/test/123")
        
        # Check response
        assert response.status_code == 200
        assert response.json() == {"id": "123", "value": "test"}
        
        # Check Redis interactions
        mock_redis.get.assert_called_once()
        mock_redis.set.assert_called_once()
    
    @patch("app.core.cache.redis_client")
    async def test_cacheable_skip_cache(self, mock_redis, client):
        """Test cacheable decorator with skip_cache_if."""
        # Set up mock Redis
        mock_redis.get.return_value = {"value": "cached"}
        mock_redis.is_available = True
        
        # Make request with header to skip cache
        response = client.get("/nocache", headers={"x-no-cache": "true"})
        
        # Check response
        assert response.status_code == 200
        assert response.json() == {"value": "nocache"}
        
        # Check Redis interactions
        mock_redis.get.assert_not_called()
        # Still caches the response
        mock_redis.set.assert_called_once()
    
    @patch("app.core.cache.redis_client")
    async def test_cacheable_no_cache_header(self, mock_redis, client):
        """Test cacheable decorator with Cache-Control: no-cache header."""
        # Set up mock Redis
        mock_redis.get.return_value = {"value": "cached"}
        mock_redis.is_available = True
        
        # Make request with Cache-Control header
        response = client.get("/test", headers={"Cache-Control": "no-cache"})
        
        # Check response
        assert response.status_code == 200
        assert response.json() == {"value": "test"}
        
        # Check Redis interactions
        mock_redis.get.assert_not_called()
        # Still caches the response
        mock_redis.set.assert_called_once()
