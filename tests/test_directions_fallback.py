import pytest
from unittest.mock import AsyncMock, patch
import httpx
from datetime import datetime, timedelta

from backend.app.services.directions_service import DirectionsService
from backend.app.core.cache import cache_manager


@pytest.fixture
async def directions_service():
    service = DirectionsService()
    # Initialize with test API key
    service.api_key = "test_api_key"
    yield service


@pytest.fixture
async def mock_cache():
    with patch('backend.app.core.cache.cache_manager') as mock:
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock(return_value=True)
        yield mock


@pytest.mark.asyncio
async def test_api_timeout(directions_service, mock_cache):
    """Test handling of API timeout."""
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.side_effect = httpx.TimeoutException("Request timed out")
        
        # Set up cached response for fallback
        cached_response = {
            "routes": [{"summary": "Cached Route"}],
            "timestamp": datetime.now().isoformat()
        }
        mock_cache.get.return_value = cached_response
        
        result = await directions_service.get_directions(
            origin="40.7128,-74.0060",
            destination="40.7614,-73.9776"
        )
        
        assert result["cached"]
        assert result["offline"]
        assert "Cached Route" in result["routes"][0]["summary"]


@pytest.mark.asyncio
async def test_api_connection_error(directions_service, mock_cache):
    """Test handling of connection errors."""
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.side_effect = httpx.ConnectError("Connection failed")
        
        # No cached data available
        mock_cache.get.return_value = None
        
        with pytest.raises(Exception) as exc_info:
            await directions_service.get_directions(
                origin="40.7128,-74.0060",
                destination="40.7614,-73.9776"
            )
        
        assert "Service temporarily unavailable" in str(exc_info.value)


@pytest.mark.asyncio
async def test_expired_cache_fallback(directions_service, mock_cache):
    """Test fallback to expired cache when API fails."""
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.side_effect = httpx.RequestError("API error")
        
        # Set up expired cached response
        expired_response = {
            "routes": [{"summary": "Expired Route"}],
            "timestamp": (
                datetime.now() - timedelta(minutes=10)
            ).isoformat()
        }
        mock_cache.get.side_effect = [
            None,  # First call (normal cache check)
            expired_response  # Second call (expired cache check)
        ]
        
        result = await directions_service.get_directions(
            origin="40.7128,-74.0060",
            destination="40.7614,-73.9776"
        )
        
        assert result["cached"]
        assert result["offline"]
        assert "Expired Route" in result["routes"][0]["summary"]


@pytest.mark.asyncio
async def test_partial_api_failure(directions_service, mock_cache):
    """Test handling of partial API failures (e.g., place details fail)."""
    with patch('httpx.AsyncClient.get') as mock_get:
        # Main directions request succeeds
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "status": "OK",
            "routes": [{
                "summary": "Test Route",
                "legs": [{
                    "start_place_id": "test_place_id",
                    "steps": []
                }]
            }]
        }
        
        # But place details request fails
        with patch.object(
            directions_service,
            'get_place_details',
            side_effect=Exception("Place API error")
        ):
            result = await directions_service.get_directions(
                origin="40.7128,-74.0060",
                destination="40.7614,-73.9776",
                include_places=True
            )
        
        # Should still return route without place details
        assert "Test Route" in result["routes"][0]["summary"]
        assert "place_details" not in result["routes"][0]["legs"][0]


@pytest.mark.asyncio
async def test_waypoint_optimization_failure(directions_service, mock_cache):
    """Test handling of waypoint optimization failure."""
    with patch.object(
        directions_service,
        '_optimize_waypoints',
        side_effect=Exception("Optimization failed")
    ):
        result = await directions_service.get_directions(
            origin="40.7128,-74.0060",
            destination="40.7614,-73.9776",
            waypoints="40.7,-74.0|40.8,-74.1",
            optimize_route=True
        )
        
        # Should fall back to original waypoint order
        assert not result.get("optimized_waypoints")


@pytest.mark.asyncio
async def test_invalid_response_handling(directions_service, mock_cache):
    """Test handling of invalid API responses."""
    with patch('httpx.AsyncClient.get') as mock_get:
        # Return invalid JSON
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.side_effect = ValueError("Invalid JSON")
        
        with pytest.raises(Exception) as exc_info:
            await directions_service.get_directions(
                origin="40.7128,-74.0060",
                destination="40.7614,-73.9776"
            )
        
        assert "Internal server error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_rate_limit_exceeded(directions_service, mock_cache):
    """Test handling of rate limit exceeded response."""
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.return_value.status_code = 429
        mock_get.return_value.text = "Rate limit exceeded"
        
        with pytest.raises(Exception) as exc_info:
            await directions_service.get_directions(
                origin="40.7128,-74.0060",
                destination="40.7614,-73.9776"
            )
        
        assert "429" in str(exc_info.value)


@pytest.mark.asyncio
async def test_multiple_fallback_attempts(directions_service, mock_cache):
    """Test multiple fallback attempts when primary and secondary options fail."""
    with patch('httpx.AsyncClient.get') as mock_get:
        # API request fails
        mock_get.side_effect = httpx.RequestError("API error")
        
        # Cache is empty
        mock_cache.get.return_value = None
        
        # Offline cache is empty
        with patch.object(
            cache_manager,
            '_offline_cache',
            {}
        ):
            with pytest.raises(Exception) as exc_info:
                await directions_service.get_directions(
                    origin="40.7128,-74.0060",
                    destination="40.7614,-73.9776"
                )
            
            assert (
                "Service temporarily unavailable"
                in str(exc_info.value)
            ) 