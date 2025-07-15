import pytest
from unittest.mock import patch
import asyncio
import time
from datetime import datetime, timedelta
from app.services.directions_service import DirectionsService
from app.core.rate_limiter import rate_limiter

@pytest.fixture
def mock_place_details():
    return {
        "name": "Test Place",
        "formatted_address": "123 Test St",
        "rating": 4.5,
        "opening_hours": {
            "open_now": True
        }
    }

@pytest.mark.asyncio
async def test_cache_hit_scenario(mock_cache_manager):
    """Test the cache hit path with various parameters."""
    service = DirectionsService()
    cached_response = {
        "routes": [{
            "summary": "Cached Route",
            "legs": [{"steps": []}]
        }],
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Setup cache hit
    mock_cache_manager.get.return_value = cached_response
    
    result = await service.get_directions(
        origin="40.7128,-74.0060",
        destination="40.7614,-73.9776",
        include_places=True
    )
    
    assert result["cached"] is True
    assert "Cached Route" in result["routes"][0]["summary"]
    assert "timestamp" in result
    mock_cache_manager.get.assert_called_once()

@pytest.mark.asyncio
async def test_rate_limiter_enforcement():
    """Test rate limiting behavior with multiple rapid requests."""
    service = DirectionsService()
    
    # Reset rate limiter
    await rate_limiter.reset("test_client")
    
    # Make multiple requests rapidly
    results = []
    for _ in range(6):  # Assuming rate limit is 5 requests per minute
        try:
            result = await service.get_directions(
                origin="40.7128,-74.0060",
                destination="40.7614,-73.9776",
                client_id="test_client"
            )
            results.append({"success": True, "data": result})
        except Exception as e:
            results.append({"success": False, "error": str(e)})
    
    # Verify rate limiting
    successes = sum(1 for r in results if r["success"])
    failures = sum(1 for r in results if not r["success"])
    assert successes == 5  # First 5 should succeed
    assert failures == 1   # 6th should fail
    assert "Rate limit exceeded" in results[-1]["error"]

@pytest.mark.asyncio
async def test_offline_fallback(mock_cache_manager):
    """Test fallback behavior when Google Maps API is unreachable."""
    service = DirectionsService()
    
    # Setup cache miss but API failure
    mock_cache_manager.get.return_value = None
    
    with patch('httpx.AsyncClient.get', side_effect=Exception("API Unreachable")):
        result = await service.get_directions(
            origin="40.7128,-74.0060",
            destination="40.7614,-73.9776"
        )
        
        assert result["offline"] is True
        assert "routes" in result
        assert len(result["routes"]) > 0  # Should have fallback route

@pytest.mark.asyncio
async def test_place_details_integration(mock_place_details):
    """Test place details integration with the main directions flow."""
    service = DirectionsService()
    
    with patch.object(service, 'get_place_details', return_value=mock_place_details):
        result = await service.get_directions(
            origin="40.7128,-74.0060",
            destination="40.7614,-73.9776",
            include_places=True
        )
        
        # Verify place details are included
        route = result["routes"][0]
        leg = route["legs"][0]
        assert "start_place_details" in leg
        assert leg["start_place_details"]["name"] == "Test Place"
        assert "end_place_details" in leg
        assert leg["end_place_details"]["name"] == "Test Place"

@pytest.mark.asyncio
async def test_concurrent_place_details():
    """Test concurrent place details fetching performance."""
    service = DirectionsService()
    start_time = time.time()
    
    # Create a slow mock for place details
    async def slow_get_place_details(place_id):
        await asyncio.sleep(0.1)  # Simulate API latency
        return {"name": f"Place {place_id}"}
    
    with patch.object(
        service,
        'get_place_details',
        side_effect=slow_get_place_details
    ):
        result = await service.get_directions(
            origin="40.7128,-74.0060",
            destination="40.7614,-73.9776",
            waypoints="40.7,-74.0|40.8,-74.1|40.9,-74.2",
            include_places=True
        )
    
    duration = time.time() - start_time
    # Should take ~0.1s due to concurrent fetching, not 0.5s sequential
    assert duration < 0.3  # Allow some overhead but ensure concurrent
    
    # Verify all place details were fetched
    route = result["routes"][0]
    assert all("place_details" in leg for leg in route["legs"])

@pytest.mark.asyncio
async def test_large_waypoint_performance():
    """Test performance with many waypoints."""
    service = DirectionsService()
    
    # Generate 10 waypoints
    waypoints = "|".join([
        f"40.{i},-74.{i}" for i in range(10)
    ])
    
    start_time = time.time()
    result = await service.get_directions(
        origin="40.7128,-74.0060",
        destination="40.7614,-73.9776",
        waypoints=waypoints,
        optimize_route=True
    )
    duration = time.time() - start_time
    
    # Verify performance is reasonable
    assert duration < 2.0  # Should complete within 2 seconds
    assert len(result["routes"]) > 0
    # Origin -> 10 waypoints -> Destination
    assert len(result["routes"][0]["legs"]) == 11

@pytest.mark.asyncio
async def test_cache_ttl_behavior(mock_cache_manager):
    """Test cache TTL behavior with traffic data."""
    service = DirectionsService()
    
    # Setup initial cache hit with old timestamp
    old_response = {
        "routes": [{
            "summary": "Cached Route",
            "legs": [{"duration_in_traffic": {"value": 600}}]
        }],
        "timestamp": (datetime.utcnow() - timedelta(minutes=16)).isoformat()
    }
    mock_cache_manager.get.return_value = old_response
    
    # Request with traffic data should ignore old cache
    result = await service.get_directions(
        origin="40.7128,-74.0060",
        destination="40.7614,-73.9776",
        include_traffic=True
    )
    
    assert result.get("cached") is False  # Should be a fresh request

@pytest.mark.asyncio
async def test_real_addresses():
    """Test with real-world addresses and verify geocoding."""
    service = DirectionsService()
    
    result = await service.get_directions(
        origin="Times Square, New York, NY",
        destination="Empire State Building, NY",
        include_places=True
    )
    
    # Verify geocoding worked
    route = result["routes"][0]
    leg = route["legs"][0]
    # Times Square latitude
    assert "40.7" in str(leg["start_location"]["lat"])
    # Times Square longitude
    assert "-73.9" in str(leg["start_location"]["lng"]) 