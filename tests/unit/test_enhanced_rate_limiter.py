"""
Test enhanced rate limiting functionality.
"""

import pytest
import time
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from app.core.enhanced_rate_limiter import (
    EnhancedRateLimiter,
    RateLimitTier,
    RateLimitConfig,
    TokenBucket,
    RateLimitTracker
)


class TestTokenBucket:
    """Test token bucket algorithm."""
    
    @pytest.mark.asyncio
    async def test_token_consumption(self):
        """Test basic token consumption."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        
        # Should be able to consume initial tokens
        assert await bucket.consume(5) is True
        assert bucket.available_tokens() == pytest.approx(5, rel=0.1)
        
        # Should not be able to consume more than available
        assert await bucket.consume(6) is False
        
        # Should be able to consume exact amount
        assert await bucket.consume(5) is True
        assert bucket.available_tokens() == pytest.approx(0, rel=0.1)
    
    @pytest.mark.asyncio
    async def test_token_refill(self):
        """Test token refill over time."""
        bucket = TokenBucket(capacity=10, refill_rate=10.0)  # 10 tokens per second
        
        # Consume all tokens
        await bucket.consume(10)
        assert bucket.available_tokens() == pytest.approx(0, rel=0.1)
        
        # Wait for refill
        await asyncio.sleep(0.5)  # Should refill 5 tokens
        assert bucket.available_tokens() == pytest.approx(5, rel=0.5)
        
        # Should be able to consume refilled tokens
        assert await bucket.consume(4) is True
    
    @pytest.mark.asyncio
    async def test_token_capacity_limit(self):
        """Test that tokens don't exceed capacity."""
        bucket = TokenBucket(capacity=10, refill_rate=100.0)  # Fast refill
        
        # Wait for potential overfill
        await asyncio.sleep(1)
        
        # Should still be at capacity
        assert bucket.available_tokens() == 10


class TestRateLimitTracker:
    """Test rate limit tracking."""
    
    def test_request_tracking(self):
        """Test request history tracking."""
        tracker = RateLimitTracker()
        
        # Add requests
        now = datetime.utcnow()
        tracker.add_request("user:123", now, cost=1.0)
        tracker.add_request("user:123", now - timedelta(seconds=30), cost=2.0)
        tracker.add_request("user:123", now - timedelta(seconds=90), cost=1.0)
        
        # Check counts
        assert tracker.get_request_count("user:123", 60) == 2  # Last minute
        assert tracker.get_request_count("user:123", 120) == 3  # Last 2 minutes
        
        # Check cost tracking
        assert tracker.cost_tracking["user:123"] == 4.0
    
    def test_violation_tracking(self):
        """Test violation history tracking."""
        tracker = RateLimitTracker()
        
        # Add violations
        tracker.add_violation("user:123", "rate_limit_exceeded")
        tracker.add_violation("user:123", "concurrent_limit_exceeded")
        
        # Check counts
        assert tracker.get_violation_count("user:123", 3600) == 2
        assert tracker.get_violation_count("user:456", 3600) == 0


class TestEnhancedRateLimiter:
    """Test enhanced rate limiter."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create rate limiter instance."""
        return EnhancedRateLimiter()
    
    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock()
        request.client = Mock(host="192.168.1.1")
        request.headers = {}
        request.url = Mock(path="/api/test")
        return request
    
    def test_user_tier_determination(self, rate_limiter):
        """Test user tier determination."""
        assert rate_limiter.get_user_tier(None, None) == RateLimitTier.ANONYMOUS
        assert rate_limiter.get_user_tier("123", None) == RateLimitTier.BASIC
        assert rate_limiter.get_user_tier("123", "premium") == RateLimitTier.PREMIUM
        assert rate_limiter.get_user_tier("123", "enterprise") == RateLimitTier.ENTERPRISE
        assert rate_limiter.get_user_tier("123", "admin") == RateLimitTier.ADMIN
        assert rate_limiter.get_user_tier("123", "super_admin") == RateLimitTier.ADMIN
    
    def test_rate_limit_key_generation(self, rate_limiter, mock_request):
        """Test rate limit key generation."""
        # Test with user ID
        key = rate_limiter.get_rate_limit_key(mock_request, "user123")
        assert key == "user:user123"
        
        # Test without user ID (uses IP)
        key = rate_limiter.get_rate_limit_key(mock_request, None)
        assert key == "ip:192.168.1.1"
        
        # Test with X-Forwarded-For header
        mock_request.headers = {"X-Forwarded-For": "10.0.0.1, 192.168.1.1"}
        key = rate_limiter.get_rate_limit_key(mock_request, None)
        assert key == "ip:10.0.0.1"
    
    @pytest.mark.asyncio
    async def test_rate_limit_check_allowed(self, rate_limiter, mock_request):
        """Test rate limit check when request is allowed."""
        with patch.object(rate_limiter, "_is_blocked", return_value=False):
            allowed, info = await rate_limiter.check_rate_limit(
                mock_request,
                user_id="test_user",
                user_role="basic"
            )
            
            assert allowed is True
            assert info["tier"] == "basic"
            assert "limit" in info
            assert "remaining" in info
    
    @pytest.mark.asyncio
    async def test_rate_limit_check_blocked(self, rate_limiter, mock_request):
        """Test rate limit check when key is blocked."""
        # Block the key
        await rate_limiter._block_key("user:blocked_user", 3600)
        
        allowed, info = await rate_limiter.check_rate_limit(
            mock_request,
            user_id="blocked_user",
            user_role="basic"
        )
        
        assert allowed is False
        assert info["reason"] == "blocked"
    
    @pytest.mark.asyncio
    async def test_concurrent_request_limits(self, rate_limiter, mock_request):
        """Test concurrent request limiting."""
        # Set up high concurrent requests
        key = "user:test_concurrent"
        rate_limiter.tracker.concurrent_requests[key] = 100
        
        allowed, info = await rate_limiter.check_rate_limit(
            mock_request,
            user_id="test_concurrent",
            user_role="basic"  # Has limit of 5 concurrent
        )
        
        assert allowed is False
        assert info["reason"] == "concurrent_limit_exceeded"
    
    @pytest.mark.asyncio
    async def test_endpoint_specific_limits(self, rate_limiter):
        """Test endpoint-specific rate limits."""
        mock_request = Mock()
        mock_request.client = Mock(host="192.168.1.1")
        mock_request.headers = {}
        mock_request.url = Mock(path="/api/auth/login")
        
        # Get effective limits for login endpoint
        limits = rate_limiter._get_effective_limits(
            RateLimitTier.BASIC,
            "/api/auth/login"
        )
        
        # Should use stricter endpoint limits
        assert limits["requests_per_minute"] == 5  # From ENDPOINT_LIMITS
        assert limits["requests_per_hour"] == 20
    
    def test_dynamic_adjustments(self, rate_limiter):
        """Test dynamic rate limit adjustments."""
        # Set high load adjustment
        rate_limiter.set_dynamic_adjustment("high_load", 0.5)
        
        limits = rate_limiter._get_effective_limits(
            RateLimitTier.BASIC,
            "/api/test"
        )
        
        # Limits should be reduced by 50%
        assert limits["requests_per_minute"] == 30  # 60 * 0.5
        
        # Remove adjustment
        rate_limiter.remove_dynamic_adjustment("high_load")
        
        limits = rate_limiter._get_effective_limits(
            RateLimitTier.BASIC,
            "/api/test"
        )
        
        # Limits should be back to normal
        assert limits["requests_per_minute"] == 60
    
    @pytest.mark.asyncio
    async def test_violation_auto_blocking(self, rate_limiter, mock_request):
        """Test automatic blocking after violations."""
        key = "user:violator"
        
        # Add many violations
        for _ in range(11):
            rate_limiter.tracker.add_violation(key, "rate_limit_exceeded")
        
        # Mock the security monitor
        with patch("app.core.enhanced_rate_limiter.security_monitor.log_event") as mock_log:
            # Trigger check that would cause blocking
            bucket_key = f"{key}:/api/test"
            rate_limiter.token_buckets[bucket_key] = TokenBucket(capacity=1, refill_rate=0.01)
            
            # Consume all tokens
            await rate_limiter.token_buckets[bucket_key].consume(1)
            
            # This should trigger violation and auto-block
            allowed, info = await rate_limiter.check_rate_limit(
                mock_request,
                user_id="violator",
                user_role="basic"
            )
            
            assert allowed is False
            assert info["reason"] == "rate_limit_exceeded"
            
            # Should be blocked now
            assert await rate_limiter._is_blocked(key) is True
    
    @pytest.mark.asyncio
    async def test_usage_stats(self, rate_limiter):
        """Test usage statistics retrieval."""
        key = "user:stats_test"
        
        # Add some requests
        now = datetime.utcnow()
        rate_limiter.tracker.add_request(key, now)
        rate_limiter.tracker.add_request(key, now - timedelta(seconds=30))
        rate_limiter.tracker.add_violation(key, "test_violation")
        
        stats = await rate_limiter.get_usage_stats(key)
        
        assert stats["requests_last_minute"] == 2
        assert stats["violations_last_hour"] == 1
        assert stats["is_blocked"] is False
    
    def test_metrics(self, rate_limiter):
        """Test metrics collection."""
        # Simulate some activity
        rate_limiter.metrics["total_requests"] = 100
        rate_limiter.metrics["rate_limited_requests"] = 10
        rate_limiter.metrics["blocked_requests"] = 2
        
        metrics = rate_limiter.get_metrics()
        
        assert metrics["total_requests"] == 100
        assert metrics["rate_limited_requests"] == 10
        assert metrics["blocked_requests"] == 2
        assert "active_buckets" in metrics
        assert "blocked_keys" in metrics


@pytest.mark.asyncio
async def test_rate_limit_middleware_function():
    """Test rate limit middleware function."""
    from app.core.enhanced_rate_limiter import rate_limit_middleware
    
    mock_request = Mock()
    mock_request.client = Mock(host="192.168.1.1")
    mock_request.headers = {}
    mock_request.url = Mock(path="/api/test")
    mock_request.state = Mock()
    
    # Test allowed request
    with patch("app.core.enhanced_rate_limiter.enhanced_rate_limiter.check_rate_limit") as mock_check:
        mock_check.return_value = (True, {"limit": 60, "remaining": 59})
        
        # Should not raise
        await rate_limit_middleware(mock_request)
        
        # Should set rate limit info
        assert hasattr(mock_request.state, "rate_limit_info")
    
    # Test denied request
    with patch("app.core.enhanced_rate_limiter.enhanced_rate_limiter.check_rate_limit") as mock_check:
        mock_check.return_value = (False, {
            "reason": "rate_limit_exceeded",
            "limit": 60,
            "remaining": 0,
            "reset": int(time.time() + 60),
            "retry_after": 60
        })
        
        # Should raise HTTPException
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await rate_limit_middleware(mock_request)
        
        assert exc_info.value.status_code == 429
        assert "rate limit exceeded" in str(exc_info.value.detail).lower()
        assert "Retry-After" in exc_info.value.headers