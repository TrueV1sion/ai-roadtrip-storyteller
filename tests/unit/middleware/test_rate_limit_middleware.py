"""
Tests for production-ready rate limiting middleware.
"""

import pytest
import time
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
import redis

from backend.app.middleware.rate_limit_middleware import (
    RateLimitMiddleware,
    RateLimitConfig,
    reset_rate_limit,
    get_rate_limit_status,
    get_rate_limit_violations
)


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    mock_client = Mock()
    mock_client.is_available = True
    mock_client.client = Mock()
    mock_client.client.pipeline = Mock(return_value=Mock())
    return mock_client


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    
    @app.get("/api/v1/test")
    async def test_endpoint():
        return {"message": "success"}
    
    @app.get("/api/v1/auth/login")
    async def login_endpoint():
        return {"message": "login"}
    
    @app.get("/health")
    async def health_endpoint():
        return {"status": "ok"}
    
    return app


@pytest.fixture
def client_with_rate_limit(app, mock_redis_client):
    """Create test client with rate limiting middleware."""
    with patch("backend.app.middleware.rate_limit_middleware.redis_client", mock_redis_client):
        app.add_middleware(RateLimitMiddleware)
        return TestClient(app)


class TestRateLimitMiddleware:
    """Test rate limiting middleware functionality."""
    
    def test_excluded_paths_bypass_rate_limit(self, client_with_rate_limit):
        """Test that excluded paths bypass rate limiting."""
        # Health endpoint should always work
        for _ in range(10):
            response = client_with_rate_limit.get("/health")
            assert response.status_code == 200
    
    def test_rate_limit_headers_added(self, client_with_rate_limit, mock_redis_client):
        """Test that rate limit headers are added to responses."""
        # Mock Redis responses
        mock_redis_client.client.pipeline.return_value.execute.return_value = [None, 5]
        mock_redis_client.client.zcard.return_value = 5
        
        response = client_with_rate_limit.get("/api/v1/test")
        
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        assert "X-RateLimit-Type" in response.headers
    
    def test_rate_limit_exceeded_returns_429(self, client_with_rate_limit, mock_redis_client):
        """Test that exceeding rate limit returns 429 status."""
        # Mock Redis to indicate limit exceeded
        mock_redis_client.client.pipeline.return_value.execute.return_value = [None, 1001]  # Over limit
        mock_redis_client.client.zrange.return_value = [(b"timestamp", time.time())]
        
        response = client_with_rate_limit.get("/api/v1/test")
        
        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert response.json()["error"] == "rate_limit_exceeded"
    
    def test_endpoint_specific_limits(self, client_with_rate_limit, mock_redis_client):
        """Test endpoint-specific rate limits."""
        # Mock Redis for login endpoint (stricter limit)
        mock_redis_client.client.pipeline.return_value.execute.return_value = [None, 6]  # Over login limit
        mock_redis_client.client.zrange.return_value = [(b"timestamp", time.time())]
        
        response = client_with_rate_limit.get("/api/v1/auth/login")
        
        assert response.status_code == 429
        assert response.json()["limit_type"] == "endpoint"
    
    def test_burst_allowance(self, mock_redis_client):
        """Test burst allowance functionality."""
        config = RateLimitConfig(requests=100, window_seconds=3600, burst_multiplier=1.5)
        
        assert config.requests == 100
        assert config.burst_limit == 150
    
    def test_redis_unavailable_fallback(self, app):
        """Test that requests pass through when Redis is unavailable."""
        mock_redis = Mock()
        mock_redis.is_available = False
        
        with patch("backend.app.middleware.rate_limit_middleware.redis_client", mock_redis):
            app.add_middleware(RateLimitMiddleware)
            client = TestClient(app)
            
            response = client.get("/api/v1/test")
            assert response.status_code == 200
    
    def test_user_vs_ip_rate_limiting(self, client_with_rate_limit, mock_redis_client):
        """Test different rate limits for authenticated vs anonymous users."""
        # Test with user ID in request state
        mock_request = Mock()
        mock_request.state.user_id = "123"
        mock_request.url.path = "/api/v1/test"
        mock_request.method = "GET"
        mock_request.client.host = "127.0.0.1"
        
        middleware = RateLimitMiddleware(Mock())
        user_id = middleware._get_user_id(mock_request)
        
        assert user_id == "123"
    
    def test_admin_bypass(self, client_with_rate_limit, mock_redis_client):
        """Test that admin users bypass rate limits."""
        # Mock admin check
        mock_redis_client.get.return_value = True  # User is admin
        mock_redis_client.client.pipeline.return_value.execute.return_value = [None, 10000]  # Over limit
        
        # Mock request with admin user
        response = client_with_rate_limit.get(
            "/api/v1/test",
            headers={"X-User-ID": "admin_user"}
        )
        
        # Should succeed despite being over limit
        assert "X-RateLimit-Bypass" in response.headers
    
    def test_rate_limit_violation_logging(self, mock_redis_client):
        """Test that rate limit violations are logged."""
        middleware = RateLimitMiddleware(Mock())
        
        mock_request = Mock()
        mock_request.url.path = "/api/v1/test"
        mock_request.method = "GET"
        mock_request.headers = {"User-Agent": "TestAgent"}
        mock_request.client.host = "127.0.0.1"
        
        metadata = {"limit": 100, "current_usage": 101, "burst_active": False}
        
        # Should not raise exception
        asyncio.run(middleware._log_rate_limit_violation(
            "per_ip", "ip:127.0.0.1", mock_request, metadata
        ))


class TestRateLimitUtilities:
    """Test rate limit utility functions."""
    
    @pytest.mark.asyncio
    async def test_reset_rate_limit(self, mock_redis_client):
        """Test resetting rate limits."""
        with patch("backend.app.middleware.rate_limit_middleware.redis_client", mock_redis_client):
            mock_redis_client.client.scan.return_value = (0, [b"rl:per_ip:127.0.0.1"])
            mock_redis_client.client.delete.return_value = 1
            
            result = await reset_rate_limit("127.0.0.1")
            assert result is True
            mock_redis_client.client.delete.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_rate_limit_status(self, mock_redis_client):
        """Test getting rate limit status."""
        with patch("backend.app.middleware.rate_limit_middleware.redis_client", mock_redis_client):
            mock_redis_client.client.zcard.return_value = 50
            
            status = await get_rate_limit_status("user:123")
            
            assert "global" in status
            assert status["global"]["current"] == 50
            assert status["global"]["remaining"] > 0
    
    @pytest.mark.asyncio
    async def test_get_rate_limit_violations(self, mock_redis_client):
        """Test retrieving rate limit violations."""
        with patch("backend.app.middleware.rate_limit_middleware.redis_client", mock_redis_client):
            violation_data = {
                "timestamp": time.time(),
                "limit_type": "per_ip",
                "key": "ip:127.0.0.1",
                "path": "/api/v1/test",
                "limit": 100,
                "current_usage": 101
            }
            
            mock_redis_client.client.scan.return_value = (0, [b"rate_limit:violations:12345"])
            mock_redis_client.client.lrange.return_value = [json.dumps(violation_data).encode()]
            
            violations = await get_rate_limit_violations()
            
            assert len(violations) > 0
            assert violations[0]["limit_type"] == "per_ip"


class TestRateLimitConfig:
    """Test rate limit configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = RateLimitConfig(requests=100, window_seconds=60)
        
        assert config.requests == 100
        assert config.window_seconds == 60
        assert config.burst_multiplier == 1.5
        assert config.burst_limit == 150
        assert config.key_prefix == "rl"
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = RateLimitConfig(
            requests=50,
            window_seconds=300,
            burst_multiplier=2.0,
            key_prefix="custom"
        )
        
        assert config.requests == 50
        assert config.window_seconds == 300
        assert config.burst_multiplier == 2.0
        assert config.burst_limit == 100
        assert config.key_prefix == "custom"


class TestProxyHeaders:
    """Test handling of proxy headers for IP extraction."""
    
    def test_x_forwarded_for_header(self):
        """Test extraction of IP from X-Forwarded-For header."""
        middleware = RateLimitMiddleware(Mock())
        
        mock_request = Mock()
        mock_request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1, 172.16.0.1"}
        mock_request.client = None
        
        ip = middleware._get_client_ip(mock_request)
        assert ip == "192.168.1.1"
    
    def test_x_real_ip_header(self):
        """Test extraction of IP from X-Real-IP header."""
        middleware = RateLimitMiddleware(Mock())
        
        mock_request = Mock()
        mock_request.headers = {"X-Real-IP": "192.168.1.100"}
        mock_request.client = None
        
        ip = middleware._get_client_ip(mock_request)
        assert ip == "192.168.1.100"
    
    def test_direct_client_ip(self):
        """Test extraction of direct client IP."""
        middleware = RateLimitMiddleware(Mock())
        
        mock_request = Mock()
        mock_request.headers = {}
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        
        ip = middleware._get_client_ip(mock_request)
        assert ip == "127.0.0.1"