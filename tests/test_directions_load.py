import pytest
import asyncio
import time
from unittest.mock import patch
from app.services.directions_service import DirectionsService


@pytest.mark.asyncio
async def test_concurrent_requests_performance():
    """Test performance under concurrent request load."""
    service = DirectionsService()
    num_concurrent = 10
    
    async def make_request(i: int):
        # Vary coordinates slightly to avoid cache hits
        lat_offset = i * 0.001
        return await service.get_directions(
            origin=f"40.{7128+lat_offset},-74.0060",
            destination=f"40.{7614+lat_offset},-73.9776",
            include_traffic=True
        )
    
    start_time = time.time()
    tasks = [make_request(i) for i in range(num_concurrent)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    duration = time.time() - start_time
    
    # Verify performance and success rate
    successes = sum(1 for r in results if not isinstance(r, Exception))
    assert successes >= num_concurrent * 0.8  # At least 80% success rate
    assert duration < 5.0  # All requests should complete within 5 seconds


@pytest.mark.asyncio
async def test_place_details_memory_usage():
    """Test memory usage with large number of place details requests."""
    service = DirectionsService()
    
    # Mock place details to return large response
    large_place_details = {
        "name": "Test Place",
        "formatted_address": "123 Test St" * 100,  # Large string
        "photos": [{"photo_reference": "x" * 1000} for _ in range(50)],
        "reviews": [{"text": "Review" * 100} for _ in range(20)]
    }
    
    with patch.object(
        service,
        'get_place_details',
        return_value=large_place_details
    ):
        # Request with multiple waypoints to trigger many place details
        waypoints = "|".join([
            f"40.{i},-74.{i}" for i in range(20)
        ])
        
        start_time = time.time()
        result = await service.get_directions(
            origin="40.7128,-74.0060",
            destination="40.7614,-73.9776",
            waypoints=waypoints,
            include_places=True
        )
        duration = time.time() - start_time
        
        # Verify reasonable memory usage indirectly via response time
        assert duration < 3.0
        assert len(result["routes"]) > 0


@pytest.mark.asyncio
async def test_route_complexity_handling():
    """Test handling of complex routes with many turns and steps."""
    service = DirectionsService()
    
    # Create a route with many waypoints in a zig-zag pattern
    waypoints = []
    for i in range(10):
        # Alternate between points to create a complex path
        if i % 2 == 0:
            waypoints.append(f"40.{7128+i*0.01},-73.{9776+i*0.01}")
        else:
            waypoints.append(f"40.{7128-i*0.01},-73.{9776-i*0.01}")
    
    result = await service.get_directions(
        origin="40.7128,-74.0060",
        destination="40.7614,-73.9776",
        waypoints="|".join(waypoints),
        alternatives=True
    )
    
    # Verify complex route handling
    assert len(result["routes"]) > 0
    main_route = result["routes"][0]
    total_steps = sum(len(leg["steps"]) for leg in main_route["legs"])
    assert total_steps > 20  # Complex route should have many steps


@pytest.mark.asyncio
async def test_traffic_data_consistency():
    """Test consistency of traffic data over multiple requests."""
    service = DirectionsService()
    num_requests = 5
    results = []
    
    # Make multiple requests over a short time period
    for _ in range(num_requests):
        result = await service.get_directions(
            origin="40.7128,-74.0060",
            destination="40.7614,-73.9776",
            include_traffic=True
        )
        results.append(result)
        await asyncio.sleep(1)  # Small delay between requests
    
    # Compare traffic durations across requests
    traffic_durations = []
    for result in results:
        duration = result["routes"][0]["legs"][0].get(
            "duration_in_traffic", {}).get("value", 0)
        traffic_durations.append(duration)
    
    # Verify reasonable consistency
    if len(traffic_durations) >= 2:
        max_variation = max(traffic_durations) - min(traffic_durations)
        assert max_variation < 300  # Max 5-minute variation in short period


@pytest.mark.asyncio
async def test_error_recovery():
    """Test service recovery after various error conditions."""
    service = DirectionsService()
    
    # Simulate sequence of API failures and recoveries
    error_responses = [
        Exception("Timeout"),
        Exception("Rate limit"),
        {"status": "OK", "routes": [{"summary": "Success"}]},
        Exception("Network error"),
        {"status": "OK", "routes": [{"summary": "Recovery"}]}
    ]
    
    results = []
    with patch('httpx.AsyncClient.get') as mock_get:
        for response in error_responses:
            if isinstance(response, Exception):
                mock_get.side_effect = response
            else:
                mock_get.return_value.status_code = 200
                mock_get.return_value.json.return_value = response
            
            try:
                result = await service.get_directions(
                    origin="40.7128,-74.0060",
                    destination="40.7614,-73.9776"
                )
                results.append({"success": True, "data": result})
            except Exception as e:
                results.append({"success": False, "error": str(e)})
    
    # Verify error handling and recovery
    assert len(results) == len(error_responses)
    # Service should recover after errors
    assert results[-1]["success"]
    # Should handle intermittent failures
    assert any(not r["success"] for r in results)
    assert any(r["success"] for r in results) 