import pytest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
import json

from backend.app.routes.directions import get_directions, enhance_directions_data


@pytest.fixture
def mock_settings():
    with patch('backend.app.core.config.settings') as mock_settings:
        mock_settings.GOOGLE_MAPS_API_KEY = "test_api_key"
        yield mock_settings


@pytest.fixture
def mock_cache_manager():
    with patch('backend.app.core.cache.cache_manager') as mock_cache:
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock(return_value=True)
        yield mock_cache


@pytest.fixture
def sample_directions_response():
    return {
        "status": "OK",
        "routes": [{
            "summary": "Test Route",
            "bounds": {
                "northeast": {"lat": 40.7, "lng": -73.9},
                "southwest": {"lat": 40.6, "lng": -74.0}
            },
            "legs": [{
                "distance": {"text": "5 km", "value": 5000},
                "duration": {"text": "10 mins", "value": 600},
                "steps": [{
                    "distance": {"text": "1 km", "value": 1000},
                    "duration": {"text": "2 mins", "value": 120},
                    "html_instructions": "Drive straight",
                    "polyline": {"points": "test_polyline"},
                    "maneuver": "straight"
                }]
            }],
            "overview_polyline": {"points": "test_overview_polyline"}
        }]
    }


@pytest.mark.asyncio
async def test_get_directions_success(
    mock_settings,
    mock_cache_manager,
    sample_directions_response
):
    """Test successful directions fetch."""
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = sample_directions_response

        result = await get_directions(
            origin="40.7,-74.0",
            destination="40.6,-73.9",
            mode="driving"
        )

        assert result["routes"][0]["summary"] == "Test Route"
        assert not result["cached"]
        assert not result["offline"]


@pytest.mark.asyncio
async def test_get_directions_from_cache(
    mock_settings,
    mock_cache_manager,
    sample_directions_response
):
    """Test retrieving directions from cache."""
    mock_cache_manager.get.return_value = sample_directions_response

    result = await get_directions(
        origin="40.7,-74.0",
        destination="40.6,-73.9"
    )

    assert result["cached"] is True
    mock_cache_manager.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_directions_api_error(mock_settings, mock_cache_manager):
    """Test handling of API errors."""
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 400
        
        with pytest.raises(HTTPException) as exc_info:
            await get_directions(
                origin="40.7,-74.0",
                destination="40.6,-73.9"
            )
        
        assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_get_directions_network_error_with_cache(
    mock_settings,
    mock_cache_manager,
    sample_directions_response
):
    """Test fallback to cache on network error."""
    with patch('requests.get') as mock_get:
        mock_get.side_effect = Exception("Network error")
        mock_cache_manager.get.return_value = sample_directions_response

        result = await get_directions(
            origin="40.7,-74.0",
            destination="40.6,-73.9"
        )

        assert result["cached"] is True
        assert result["offline"] is True


def test_enhance_directions_data(sample_directions_response):
    """Test enhancement of directions data."""
    enhanced = enhance_directions_data(sample_directions_response)
    
    assert "routes" in enhanced
    assert len(enhanced["routes"]) == 1
    assert "timestamp" in enhanced
    
    route = enhanced["routes"][0]
    assert "summary" in route
    assert "bounds" in route
    assert "legs" in route
    assert len(route["legs"]) == 1
    
    leg = route["legs"][0]
    assert "steps" in leg
    assert len(leg["steps"]) == 1
    
    step = leg["steps"][0]
    assert "coordinates" in step
    assert "distance" in step
    assert "duration" in step
    assert "instructions" in step
    assert "maneuver" in step


@pytest.mark.asyncio
async def test_get_directions_with_waypoints(
    mock_settings,
    mock_cache_manager,
    sample_directions_response
):
    """Test directions fetch with waypoints."""
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = sample_directions_response

        result = await get_directions(
            origin="40.7,-74.0",
            destination="40.6,-73.9",
            waypoints="40.65,-73.95"
        )

        assert "waypoints" in mock_get.call_args[1]["params"]
        assert not result["cached"]
        assert not result["offline"]


@pytest.mark.asyncio
async def test_get_directions_with_alternatives(
    mock_settings,
    mock_cache_manager,
    sample_directions_response
):
    """Test directions fetch with alternative routes."""
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = sample_directions_response

        result = await get_directions(
            origin="40.7,-74.0",
            destination="40.6,-73.9",
            alternatives=True
        )

        params = mock_get.call_args[1]["params"]
        assert params["alternatives"] == "true"
        assert not result["cached"]
        assert not result["offline"] 