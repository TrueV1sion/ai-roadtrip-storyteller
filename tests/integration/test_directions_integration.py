import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import os
import aioredis
import json

from backend.app.main import app
from backend.app.core.cache import cache_manager
from backend.app.core.rate_limiter import rate_limiter


@pytest.fixture(scope="module")
async def test_app():
    # Initialize cache and rate limiter
    await cache_manager.initialize()
    yield TestClient(app)
    await cache_manager.close()


@pytest.fixture(scope="module")
def valid_api_key():
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        pytest.skip("Google Maps API key not configured")
    return api_key


@pytest.mark.integration
async def test_directions_e2e(test_app, valid_api_key):
    """Test the complete directions flow with real API calls."""
    params = {
        "origin": "40.7128,-74.0060",  # New York
        "destination": "40.7614,-73.9776",  # Empire State Building
        "mode": "driving",
        "include_traffic": True,
        "include_places": True
    }
    
    response = test_app.get("/directions", params=params)
    assert response.status_code == 200
    
    data = response.json()
    assert "routes" in data
    assert len(data["routes"]) > 0
    
    # Verify route structure
    route = data["routes"][0]
    assert "summary" in route
    assert "bounds" in route
    assert "legs" in route
    assert "traffic_speed" in route
    
    # Verify leg details
    leg = route["legs"][0]
    assert "duration_in_traffic" in leg
    assert "distance" in leg
    assert "steps" in leg
    
    # Verify place details if available
    if "start_place_details" in leg:
        assert "name" in leg["start_place_details"]
        assert "formatted_address" in leg["start_place_details"]


@pytest.mark.integration
async def test_directions_caching(test_app, valid_api_key):
    """Test caching behavior with real Redis instance."""
    params = {
        "origin": "40.7128,-74.0060",
        "destination": "40.7614,-73.9776",
        "mode": "driving"
    }
    
    # First request - should hit API
    response1 = test_app.get("/directions", params=params)
    assert response1.status_code == 200
    assert not response1.json().get("cached")
    
    # Second request - should hit cache
    response2 = test_app.get("/directions", params=params)
    assert response2.status_code == 200
    assert response2.json().get("cached")
    
    # Verify responses match
    assert response1.json()["routes"] == response2.json()["routes"]


@pytest.mark.integration
async def test_waypoint_optimization(test_app, valid_api_key):
    """Test waypoint optimization with real API calls."""
    params = {
        "origin": "40.7128,-74.0060",  # New York
        "destination": "40.7614,-73.9776",  # Empire State Building
        "waypoints": "optimize:true|40.7527,-73.9772|40.7589,-73.9851",  # Times Square, Madison Square Garden
        "mode": "driving"
    }
    
    response = test_app.get("/directions", params=params)
    assert response.status_code == 200
    
    data = response.json()
    assert "routes" in data
    assert len(data["routes"]) > 0
    
    # Verify optimized waypoints
    route = data["routes"][0]
    assert len(route["legs"]) == 3  # Origin -> Waypoint1 -> Waypoint2 -> Destination


@pytest.mark.integration
async def test_rate_limiting(test_app, valid_api_key):
    """Test rate limiting behavior."""
    params = {
        "origin": "40.7128,-74.0060",
        "destination": "40.7614,-73.9776"
    }
    
    # Make multiple requests rapidly
    responses = []
    for _ in range(60):  # Exceed rate limit
        response = test_app.get(
            "/directions",
            params=params,
            headers={"X-Client-ID": "test_client"}
        )
        responses.append(response)
    
    # Verify rate limiting
    success_count = sum(1 for r in responses if r.status_code == 200)
    rate_limited_count = sum(1 for r in responses if r.status_code == 429)
    
    assert rate_limited_count > 0  # Some requests should be rate limited
    assert success_count <= 50  # Should not exceed rate limit


@pytest.mark.integration
async def test_traffic_predictions(test_app, valid_api_key):
    """Test traffic predictions for future departures."""
    # Test for tomorrow morning rush hour
    tomorrow = datetime.now().replace(hour=9, minute=0) + timedelta(days=1)
    
    params = {
        "origin": "40.7128,-74.0060",
        "destination": "40.7614,-73.9776",
        "departure_time": tomorrow.isoformat(),
        "include_traffic": True
    }
    
    response = test_app.get("/directions", params=params)
    assert response.status_code == 200
    
    data = response.json()
    route = data["routes"][0]
    leg = route["legs"][0]
    
    # Verify traffic predictions
    assert "duration_in_traffic" in leg
    assert leg["duration_in_traffic"].get("value") > leg["duration"].get("value")
    assert "traffic_speed" in route


@pytest.mark.integration
async def test_alternative_routes(test_app, valid_api_key):
    """Test alternative routes functionality."""
    params = {
        "origin": "40.7128,-74.0060",
        "destination": "40.7614,-73.9776",
        "alternatives": True,
        "include_traffic": True
    }
    
    response = test_app.get("/directions", params=params)
    assert response.status_code == 200
    
    data = response.json()
    assert len(data["routes"]) > 1  # Should return multiple routes
    
    # Verify each route has unique characteristics
    summaries = set(route["summary"] for route in data["routes"])
    assert len(summaries) == len(data["routes"])  # Each route should be unique 