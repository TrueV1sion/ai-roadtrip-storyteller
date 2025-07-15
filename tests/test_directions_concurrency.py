import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta

from backend.app.services.directions_service import DirectionsService
from backend.app.core.cache import cache_manager


@pytest.fixture
async def directions_service():
    service = DirectionsService()
    service.api_key = "test_api_key"
    yield service


@pytest.fixture
async def mock_cache():
    with patch('backend.app.core.cache.cache_manager') as mock:
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock(return_value=True)
        yield mock


@pytest.mark.asyncio
async def test_concurrent_same_route(directions_service, mock_cache):
    """Test handling of concurrent requests for the same route."""
    # Simulate slow API response
    async def slow_api_response(*args, **kwargs):
        await asyncio.sleep(0.1)
        return AsyncMock(
            status_code=200,
            json=AsyncMock(return_value={
                "status": "OK",
                "routes": [{"summary": "Test Route"}]
            })
        )

    with patch('httpx.AsyncClient.get', side_effect=slow_api_response):
        # Make concurrent requests for same route
        tasks = []
        for _ in range(5):
            tasks.append(
                directions_service.get_directions(
                    origin="40.7128,-74.0060",
                    destination="40.7614,-73.9776"
                )
            )
        
        results = await asyncio.gather(*tasks)
        
        # Only one API call should be made, others should use cache
        assert len(results) == 5
        assert all(
            "Test Route" in result["routes"][0]["summary"]
            for result in results
        )


@pytest.mark.asyncio
async def test_concurrent_different_routes(directions_service, mock_cache):
    """Test handling of concurrent requests for different routes."""
    routes_requested = set()
    
    async def mock_api_call(*args, **kwargs):
        # Extract origin from request
        origin = kwargs.get('params', {}).get('origin')
        routes_requested.add(origin)
        return AsyncMock(
            status_code=200,
            json=AsyncMock(return_value={
                "status": "OK",
                "routes": [{"summary": f"Route from {origin}"}]
            })
        )

    with patch('httpx.AsyncClient.get', side_effect=mock_api_call):
        # Make concurrent requests for different routes
        tasks = []
        origins = [
            "40.7128,-74.0060",
            "40.7129,-74.0061",
            "40.7130,-74.0062"
        ]
        for origin in origins:
            tasks.append(
                directions_service.get_directions(
                    origin=origin,
                    destination="40.7614,-73.9776"
                )
            )
        
        results = await asyncio.gather(*tasks)
        
        # Each unique route should make its own API call
        assert len(routes_requested) == len(origins)
        assert all(
            origin in routes_requested
            for origin in origins
        )


@pytest.mark.asyncio
async def test_cache_race_condition(directions_service, mock_cache):
    """Test handling of cache race conditions."""
    cache_hits = 0
    api_calls = 0
    
    async def mock_cache_get(*args, **kwargs):
        nonlocal cache_hits
        await asyncio.sleep(0.05)  # Simulate slow cache
        cache_hits += 1
        return None

    async def mock_api_call(*args, **kwargs):
        nonlocal api_calls
        await asyncio.sleep(0.1)  # Simulate slow API
        api_calls += 1
        return AsyncMock(
            status_code=200,
            json=AsyncMock(return_value={
                "status": "OK",
                "routes": [{"summary": "Test Route"}]
            })
        )

    mock_cache.get.side_effect = mock_cache_get
    
    with patch('httpx.AsyncClient.get', side_effect=mock_api_call):
        # Make concurrent requests
        tasks = []
        for _ in range(3):
            tasks.append(
                directions_service.get_directions(
                    origin="40.7128,-74.0060",
                    destination="40.7614,-73.9776"
                )
            )
        
        results = await asyncio.gather(*tasks)
        
        # Should handle race condition gracefully
        assert cache_hits == 3  # Each request checks cache
        assert api_calls == 1  # Only one API call made


@pytest.mark.asyncio
async def test_cache_expiry_concurrent(directions_service, mock_cache):
    """Test cache expiry behavior with concurrent requests."""
    cache_data = {
        "routes": [{"summary": "Cached Route"}],
        "timestamp": datetime.now().isoformat()
    }
    
    # First request gets cached data
    mock_cache.get.return_value = cache_data
    
    result1 = await directions_service.get_directions(
        origin="40.7128,-74.0060",
        destination="40.7614,-73.9776"
    )
    
    # Simulate cache expiry
    cache_data["timestamp"] = (
        datetime.now() - timedelta(minutes=10)
    ).isoformat()
    
    # Second concurrent requests after expiry
    tasks = []
    for _ in range(3):
        tasks.append(
            directions_service.get_directions(
                origin="40.7128,-74.0060",
                destination="40.7614,-73.9776"
            )
        )
    
    results = await asyncio.gather(*tasks)
    
    # First request should have used cache
    assert result1["cached"]
    # Later requests should have triggered refresh
    assert any(not r["cached"] for r in results)


@pytest.mark.asyncio
async def test_concurrent_error_handling(directions_service, mock_cache):
    """Test error handling during concurrent requests."""
    api_calls = 0
    
    async def failing_api_call(*args, **kwargs):
        nonlocal api_calls
        api_calls += 1
        if api_calls % 2 == 0:
            raise Exception("API Error")
        return AsyncMock(
            status_code=200,
            json=AsyncMock(return_value={
                "status": "OK",
                "routes": [{"summary": "Success Route"}]
            })
        )

    with patch('httpx.AsyncClient.get', side_effect=failing_api_call):
        # Make concurrent requests
        tasks = []
        for _ in range(4):
            tasks.append(
                directions_service.get_directions(
                    origin="40.7128,-74.0060",
                    destination="40.7614,-73.9776"
                )
            )
        
        # Some requests should succeed, others should fail
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successes = [
            r for r in results
            if isinstance(r, dict)
        ]
        failures = [
            r for r in results
            if isinstance(r, Exception)
        ]
        
        assert len(successes) > 0
        assert len(failures) > 0 