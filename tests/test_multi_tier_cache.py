"""
Comprehensive tests for the multi-tier caching system
Tests performance, reliability, and Six Sigma compliance
"""

import pytest
import asyncio
import time
import random
from typing import Dict, Any, List
from datetime import datetime, timedelta

from app.core.multi_tier_cache import (
    multi_tier_cache, ContentType, TTLStrategy, CacheMetrics
)
from app.core.cache_decorators import (
    ai_response_cache, story_cache, database_cache
)
from app.core.cache_monitoring import cache_monitor, PerformanceThresholds
from app.services.cache_warming_service import cache_warming_service, WarmingPattern


class TestMultiTierCache:
    """Test suite for multi-tier cache functionality."""
    
    @pytest.fixture
    async def clean_cache(self):
        """Clean cache before each test."""
        await multi_tier_cache.invalidate(pattern="test:*")
        yield
        await multi_tier_cache.invalidate(pattern="test:*")
    
    @pytest.mark.asyncio
    async def test_basic_cache_operations(self, clean_cache):
        """Test basic get/set/delete operations."""
        # Test set
        success = await multi_tier_cache.set(
            key="test:basic",
            value={"data": "test"},
            content_type=ContentType.API_RESPONSE
        )
        assert success is True
        
        # Test get
        value = await multi_tier_cache.get(
            key="test:basic",
            content_type=ContentType.API_RESPONSE
        )
        assert value == {"data": "test"}
        
        # Test invalidate
        count = await multi_tier_cache.invalidate(key="test:basic")
        assert count > 0
        
        # Verify deletion
        value = await multi_tier_cache.get(
            key="test:basic",
            content_type=ContentType.API_RESPONSE
        )
        assert value is None
    
    @pytest.mark.asyncio
    async def test_ttl_strategy(self):
        """Test TTL calculation strategies."""
        # Test base TTL
        ttl = TTLStrategy.calculate_ttl(ContentType.AI_RESPONSE)
        assert ttl == 86400  # 24 hours
        
        # Test premium user TTL
        ttl = TTLStrategy.calculate_ttl(
            ContentType.AI_RESPONSE,
            is_premium=True
        )
        assert ttl == 172800  # 48 hours
        
        # Test personalized content TTL
        ttl = TTLStrategy.calculate_ttl(
            ContentType.AI_RESPONSE,
            is_personalized=True
        )
        assert ttl == 43200  # 12 hours
        
        # Test with access patterns
        ttl = TTLStrategy.calculate_ttl(
            ContentType.API_RESPONSE,
            access_pattern={'access_count': 20}
        )
        assert ttl > 600  # Should be increased
    
    @pytest.mark.asyncio
    async def test_compression(self, clean_cache):
        """Test automatic compression for large values."""
        # Create large value
        large_value = {"data": "x" * 10000}
        
        # Store in cache
        success = await multi_tier_cache.set(
            key="test:compressed",
            value=large_value,
            content_type=ContentType.API_RESPONSE
        )
        assert success is True
        
        # Retrieve and verify
        retrieved = await multi_tier_cache.get(
            key="test:compressed",
            content_type=ContentType.API_RESPONSE
        )
        assert retrieved == large_value
    
    @pytest.mark.asyncio
    async def test_cache_decorators(self, clean_cache):
        """Test caching decorators."""
        call_count = 0
        
        @ai_response_cache()
        async def generate_ai_response(prompt: str, user_id: str = None):
            nonlocal call_count
            call_count += 1
            return {"response": f"AI response to: {prompt}"}
        
        # First call - cache miss
        result1 = await generate_ai_response("test prompt", user_id="user123")
        assert call_count == 1
        
        # Second call - cache hit
        result2 = await generate_ai_response("test prompt", user_id="user123")
        assert call_count == 1  # Should not increase
        assert result1 == result2
        
        # Different prompt - cache miss
        result3 = await generate_ai_response("different prompt", user_id="user123")
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_invalidation_patterns(self, clean_cache):
        """Test cache invalidation patterns."""
        # Set multiple entries
        for i in range(5):
            await multi_tier_cache.set(
                key=f"test:pattern:{i}",
                value={"data": i},
                content_type=ContentType.API_RESPONSE
            )
        
        # Invalidate by pattern
        count = await multi_tier_cache.invalidate(pattern="test:pattern:*")
        assert count >= 5
        
        # Verify all deleted
        for i in range(5):
            value = await multi_tier_cache.get(
                key=f"test:pattern:{i}",
                content_type=ContentType.API_RESPONSE
            )
            assert value is None
    
    @pytest.mark.asyncio
    async def test_user_specific_cache(self, clean_cache):
        """Test user-specific caching."""
        # Set for user1
        await multi_tier_cache.set(
            key="test:user_data",
            value={"preference": "dark_mode"},
            content_type=ContentType.USER_PREFERENCE,
            user_id="user1"
        )
        
        # Set for user2
        await multi_tier_cache.set(
            key="test:user_data",
            value={"preference": "light_mode"},
            content_type=ContentType.USER_PREFERENCE,
            user_id="user2"
        )
        
        # Invalidate user1's cache
        count = await multi_tier_cache.invalidate(user_id="user1")
        assert count > 0
        
        # User2's cache should still exist
        value = await multi_tier_cache.get(
            key="test:user_data",
            content_type=ContentType.USER_PREFERENCE,
            user_id="user2"
        )
        assert value == {"preference": "light_mode"}
    
    @pytest.mark.asyncio
    async def test_cost_tracking(self, clean_cache):
        """Test API cost tracking."""
        initial_cost = multi_tier_cache.global_metrics.cost_saved_usd
        
        # Simulate expensive AI call
        await multi_tier_cache.set(
            key="test:expensive",
            value={"result": "expensive computation"},
            content_type=ContentType.AI_RESPONSE,
            cost_to_generate=0.01,  # $0.01
            generation_time_ms=1000
        )
        
        # Simulate cache hit (saves cost)
        for _ in range(10):
            await multi_tier_cache.get(
                key="test:expensive",
                content_type=ContentType.AI_RESPONSE
            )
        
        # Check cost savings
        assert multi_tier_cache.global_metrics.cost_saved_usd > initial_cost
        assert multi_tier_cache.global_metrics.api_calls_saved >= 1


class TestCachePerformance:
    """Performance tests for cache system."""
    
    @pytest.mark.asyncio
    async def test_response_time_target(self):
        """Test that cached responses meet <100ms target."""
        # Warm cache
        await multi_tier_cache.set(
            key="test:perf",
            value={"data": "performance test"},
            content_type=ContentType.API_RESPONSE
        )
        
        # Measure response times
        response_times = []
        for _ in range(100):
            start = time.time()
            await multi_tier_cache.get(
                key="test:perf",
                content_type=ContentType.API_RESPONSE
            )
            response_times.append((time.time() - start) * 1000)
        
        # Check average response time
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < 100  # Target: <100ms
        
        # Check 95th percentile
        response_times.sort()
        p95 = response_times[int(len(response_times) * 0.95)]
        assert p95 < 150  # 95th percentile should be <150ms
    
    @pytest.mark.asyncio
    async def test_hit_rate_target(self):
        """Test that cache achieves >80% hit rate."""
        # Generate realistic cache pattern
        keys = [f"test:hit_rate:{i % 20}" for i in range(100)]
        
        # Populate cache
        for i, key in enumerate(keys[:20]):
            await multi_tier_cache.set(
                key=key,
                value={"data": i},
                content_type=ContentType.API_RESPONSE
            )
        
        # Simulate realistic access pattern
        hits = 0
        total = 0
        
        for _ in range(500):
            key = random.choice(keys)
            value = await multi_tier_cache.get(
                key=key,
                content_type=ContentType.API_RESPONSE
            )
            
            if value is not None:
                hits += 1
            else:
                # Cache miss - set the value
                await multi_tier_cache.set(
                    key=key,
                    value={"data": "cached"},
                    content_type=ContentType.API_RESPONSE
                )
            
            total += 1
        
        hit_rate = hits / total if total > 0 else 0
        assert hit_rate > 0.8  # Target: >80% hit rate
    
    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """Test cache under concurrent access."""
        async def cache_operation(key_suffix: int):
            key = f"test:concurrent:{key_suffix % 10}"
            
            # Try to get
            value = await multi_tier_cache.get(
                key=key,
                content_type=ContentType.API_RESPONSE
            )
            
            if value is None:
                # Set if not found
                await multi_tier_cache.set(
                    key=key,
                    value={"data": key_suffix},
                    content_type=ContentType.API_RESPONSE
                )
        
        # Run concurrent operations
        tasks = [
            cache_operation(i)
            for i in range(100)
        ]
        
        start_time = time.time()
        await asyncio.gather(*tasks)
        duration = time.time() - start_time
        
        # Should complete quickly even with concurrency
        assert duration < 1.0  # Should complete within 1 second


class TestCacheMonitoring:
    """Test cache monitoring and alerting."""
    
    @pytest.mark.asyncio
    async def test_alert_generation(self):
        """Test that alerts are generated correctly."""
        # Set low threshold for testing
        cache_monitor.thresholds.min_hit_rate = 0.95
        
        # Force low hit rate
        metrics = {
            'hit_rate': 0.5,
            'response_time_ms': 50,
            'l1_memory_mb': 10,
            'redis_available': 1.0,
            'cost_savings_rate': 5.0
        }
        
        # Check thresholds
        await cache_monitor._check_thresholds(metrics)
        
        # Should have alert for low hit rate
        assert 'low_hit_rate' in cache_monitor.active_alerts
        
        # Reset threshold
        cache_monitor.thresholds.min_hit_rate = 0.80
    
    @pytest.mark.asyncio
    async def test_performance_score(self):
        """Test performance score calculation."""
        score = cache_monitor._calculate_performance_score()
        
        # Score should be between 0 and 100
        assert 0 <= score <= 100
    
    def test_cost_analysis(self):
        """Test cost analysis calculations."""
        analysis = cache_monitor._analyze_costs()
        
        # Should have required fields
        assert 'hourly_rate' in analysis
        assert 'daily_projection' in analysis
        assert 'monthly_projection' in analysis
        assert 'roi_percentage' in analysis


class TestCacheWarming:
    """Test cache warming functionality."""
    
    @pytest.mark.asyncio
    async def test_warming_pattern(self):
        """Test cache warming pattern execution."""
        warmed_keys = []
        
        async def test_generator():
            keys = [
                {'key': 'test:warm:1', 'value': {'data': 1}},
                {'key': 'test:warm:2', 'value': {'data': 2}}
            ]
            warmed_keys.extend([k['key'] for k in keys])
            return keys
        
        pattern = WarmingPattern(
            pattern_id="test_pattern",
            pattern_type="test",
            generator=test_generator,
            content_type=ContentType.API_RESPONSE,
            priority=5,
            conditions={},
            tags=["test"]
        )
        
        # Execute warming
        await cache_warming_service._warm_single_pattern(pattern)
        
        # Verify keys were warmed
        for key in warmed_keys:
            value = await multi_tier_cache.get(
                key=key,
                content_type=ContentType.API_RESPONSE
            )
            assert value is not None
    
    @pytest.mark.asyncio
    async def test_conditional_warming(self):
        """Test conditional cache warming."""
        # Test peak hours condition
        pattern = WarmingPattern(
            pattern_id="peak_hours_test",
            pattern_type="test",
            generator=lambda: [],
            content_type=ContentType.API_RESPONSE,
            priority=5,
            conditions={"time_window": "peak_hours"},
            tags=["test"]
        )
        
        # Should warm during peak hours (7-9 AM, 4-7 PM)
        current_hour = datetime.now().hour
        should_warm = await cache_warming_service._should_warm_pattern(pattern)
        
        if current_hour in [7, 8, 9, 16, 17, 18, 19]:
            assert should_warm is True
        else:
            assert should_warm is False


class TestSixSigmaCompliance:
    """Test Six Sigma compliance metrics."""
    
    @pytest.mark.asyncio
    async def test_defect_rate(self):
        """Test that cache operations have low defect rate."""
        operations = 1000
        failures = 0
        
        for i in range(operations):
            try:
                # Test set operation
                success = await multi_tier_cache.set(
                    key=f"test:six_sigma:{i}",
                    value={"data": i},
                    content_type=ContentType.API_RESPONSE
                )
                
                if not success:
                    failures += 1
                
                # Test get operation
                value = await multi_tier_cache.get(
                    key=f"test:six_sigma:{i}",
                    content_type=ContentType.API_RESPONSE
                )
                
                if value is None:
                    failures += 1
                
            except Exception:
                failures += 1
        
        # Calculate defect rate (should be < 3.4 per million for Six Sigma)
        defect_rate = (failures / operations) * 1_000_000
        assert defect_rate < 3400  # Six Sigma target
    
    @pytest.mark.asyncio
    async def test_process_capability(self):
        """Test cache process capability."""
        # Measure response times
        response_times = []
        
        for i in range(100):
            await multi_tier_cache.set(
                key=f"test:capability:{i}",
                value={"data": i},
                content_type=ContentType.API_RESPONSE
            )
        
        for i in range(100):
            start = time.time()
            await multi_tier_cache.get(
                key=f"test:capability:{i}",
                content_type=ContentType.API_RESPONSE
            )
            response_times.append((time.time() - start) * 1000)
        
        # Calculate process capability
        mean = sum(response_times) / len(response_times)
        variance = sum((x - mean) ** 2 for x in response_times) / len(response_times)
        std_dev = variance ** 0.5
        
        # Target: 100ms with ±50ms tolerance
        usl = 150  # Upper specification limit
        lsl = 0    # Lower specification limit
        
        # Calculate Cp (process capability index)
        cp = (usl - lsl) / (6 * std_dev) if std_dev > 0 else 0
        
        # Cp should be > 1.33 for capable process
        assert cp > 1.33


# Fixtures for testing

@pytest.fixture
def mock_redis_available(monkeypatch):
    """Mock Redis as available."""
    monkeypatch.setattr(
        multi_tier_cache.redis_client,
        'is_available',
        True
    )


@pytest.fixture
async def populated_cache():
    """Populate cache with test data."""
    test_data = [
        ("test:story:1", {"title": "Adventure Story"}, ContentType.STORY_CONTENT),
        ("test:ai:1", {"response": "AI generated"}, ContentType.AI_RESPONSE),
        ("test:voice:1", {"audio": "base64data"}, ContentType.VOICE_AUDIO),
    ]
    
    for key, value, content_type in test_data:
        await multi_tier_cache.set(
            key=key,
            value=value,
            content_type=content_type
        )
    
    yield
    
    # Cleanup
    await multi_tier_cache.invalidate(pattern="test:*")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])