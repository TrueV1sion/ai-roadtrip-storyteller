import pytest
from datetime import datetime, timedelta
import asyncio

from backend.app.core.rate_limiter import RateLimiter


@pytest.fixture
async def rate_limiter():
    # Create a test rate limiter with lower limits for testing
    limiter = RateLimiter(rate=5, burst=2)  # 5 requests/min, burst of 2
    yield limiter


@pytest.mark.asyncio
async def test_basic_rate_limiting(rate_limiter):
    """Test basic rate limiting functionality."""
    # Should allow burst requests
    assert await rate_limiter.acquire()
    assert await rate_limiter.acquire()
    
    # Third request should be denied (exceeded burst)
    assert not await rate_limiter.acquire()


@pytest.mark.asyncio
async def test_token_replenishment(rate_limiter):
    """Test that tokens are replenished over time."""
    # Use up burst capacity
    assert await rate_limiter.acquire()
    assert await rate_limiter.acquire()
    assert not await rate_limiter.acquire()
    
    # Wait for token replenishment (1 token per 12 seconds at rate=5/min)
    await asyncio.sleep(13)
    assert await rate_limiter.acquire()


@pytest.mark.asyncio
async def test_client_specific_limits(rate_limiter):
    """Test per-client rate limiting."""
    client_1 = "test_client_1"
    client_2 = "test_client_2"
    
    # Client 1 uses their burst
    assert await rate_limiter.acquire(client_1)
    assert await rate_limiter.acquire(client_1)
    assert not await rate_limiter.acquire(client_1)
    
    # Client 2 should still have their burst available
    assert await rate_limiter.acquire(client_2)
    assert await rate_limiter.acquire(client_2)


@pytest.mark.asyncio
async def test_daily_limit(rate_limiter):
    """Test daily request limits per client."""
    client_id = "test_client"
    
    # Simulate hitting daily limit
    rate_limiter.client_usage[client_id] = {
        "count": 2500,  # Daily limit
        "first_request": datetime.now()
    }
    
    # Next request should be denied
    assert not await rate_limiter.acquire(client_id)
    
    # Simulate next day
    rate_limiter.client_usage[client_id]["first_request"] = (
        datetime.now() - timedelta(days=1, minutes=1)
    )
    
    # Should allow requests again
    assert await rate_limiter.acquire(client_id)


@pytest.mark.asyncio
async def test_concurrent_requests(rate_limiter):
    """Test behavior under concurrent requests."""
    async def make_request():
        return await rate_limiter.acquire()
    
    # Make 5 concurrent requests
    tasks = [make_request() for _ in range(5)]
    results = await asyncio.gather(*tasks)
    
    # Only burst size (2) should succeed
    assert sum(results) == 2


@pytest.mark.asyncio
async def test_client_usage_tracking(rate_limiter):
    """Test client usage statistics tracking."""
    client_id = "test_client"
    
    # Make some requests
    await rate_limiter.acquire(client_id)
    await rate_limiter.acquire(client_id)
    
    # Check usage statistics
    usage = rate_limiter.get_client_usage(client_id)
    assert usage["count"] == 2
    assert isinstance(usage["first_request"], datetime)


@pytest.mark.asyncio
async def test_burst_recovery(rate_limiter):
    """Test burst capacity recovery after waiting."""
    # Use up burst
    assert await rate_limiter.acquire()
    assert await rate_limiter.acquire()
    assert not await rate_limiter.acquire()
    
    # Wait for full burst recovery
    await asyncio.sleep(25)  # Wait for 2 tokens at 5/min rate
    
    # Should have burst capacity again
    assert await rate_limiter.acquire()
    assert await rate_limiter.acquire()


@pytest.mark.asyncio
async def test_rate_limit_precision(rate_limiter):
    """Test precise timing of rate limiting."""
    # Use one token
    assert await rate_limiter.acquire()
    
    # Wait for exactly one token worth of time
    await asyncio.sleep(12)  # 12 seconds for 1 token at 5/min
    
    # Should get exactly one token
    assert await rate_limiter.acquire()
    assert not await rate_limiter.acquire()  # No more tokens 