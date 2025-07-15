import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import os

from backend.app.main import app
from backend.app.core.cache import cache_manager


@pytest.fixture(scope="module")
async def test_app():
    await cache_manager.initialize()
    yield TestClient(app)
    await cache_manager.close()


@pytest.mark.integration
async def test_invalid_coordinates(test_app):
    """Test handling of invalid coordinates."""
    params = {
        "origin": "invalid,coords",
        "destination": "40.7614,-73.9776"
    }
    response = test_app.get("/directions", params=params)
    assert response.status_code == 400
    assert "error" in response.json()


@pytest.mark.integration
async def test_same_origin_destination(test_app):
    """Test route when origin equals destination."""
    coords = "40.7128,-74.0060"
    params = {
        "origin": coords,
        "destination": coords
    }
    response = test_app.get("/directions", params=params)
    assert response.status_code == 200
    data = response.json()
    assert len(data["routes"]) == 1
    assert data["routes"][0]["legs"][0]["distance"]["value"] == 0


@pytest.mark.integration
async def test_max_waypoints(test_app):
    """Test handling of maximum waypoint limit."""
    # Generate 25 waypoints (exceeds Google's limit)
    waypoints = "|".join([
        "40.7128,-74.0060" for _ in range(25)
    ])
    params = {
        "origin": "40.7128,-74.0060",
        "destination": "40.7614,-73.9776",
        "waypoints": waypoints
    }
    response = test_app.get("/directions", params=params)
    assert response.status_code == 400
    assert "exceeded" in response.json()["detail"].lower()


@pytest.mark.integration
async def test_unreachable_destination(test_app):
    """Test route to unreachable destination."""
    params = {
        "origin": "40.7128,-74.0060",  # New York
        "destination": "35.6762,139.6503",  # Tokyo (overseas)
        "mode": "driving"
    }
    response = test_app.get("/directions", params=params)
    assert response.status_code == 400
    assert "zero results" in response.json()["detail"].lower()


@pytest.mark.integration
async def test_past_departure_time(test_app):
    """Test handling of past departure times."""
    yesterday = datetime.now() - timedelta(days=1)
    params = {
        "origin": "40.7128,-74.0060",
        "destination": "40.7614,-73.9776",
        "departure_time": yesterday.isoformat()
    }
    response = test_app.get("/directions", params=params)
    assert response.status_code == 400
    assert "past" in response.json()["detail"].lower()


@pytest.mark.integration
async def test_far_future_departure(test_app):
    """Test handling of far future departure times."""
    far_future = datetime.now() + timedelta(days=365)
    params = {
        "origin": "40.7128,-74.0060",
        "destination": "40.7614,-73.9776",
        "departure_time": far_future.isoformat()
    }
    response = test_app.get("/directions", params=params)
    assert response.status_code == 400
    assert "too far" in response.json()["detail"].lower()


@pytest.mark.integration
async def test_transit_without_schedule(test_app):
    """Test transit route outside of service hours."""
    params = {
        "origin": "40.7128,-74.0060",
        "destination": "40.7614,-73.9776",
        "mode": "transit",
        "departure_time": datetime.now().replace(hour=3).isoformat()
    }
    response = test_app.get("/directions", params=params)
    assert response.status_code == 200
    data = response.json()
    assert "no transit service" in str(data).lower()


@pytest.mark.integration
async def test_concurrent_requests(test_app):
    """Test handling of concurrent requests."""
    import asyncio
    
    async def make_request():
        return test_app.get("/directions", params={
            "origin": "40.7128,-74.0060",
            "destination": "40.7614,-73.9776"
        })
    
    # Make 10 concurrent requests
    tasks = [make_request() for _ in range(10)]
    responses = await asyncio.gather(*tasks)
    
    # Verify all requests succeeded
    assert all(r.status_code == 200 for r in responses)
    # Verify rate limiting worked
    assert any(r.json().get("cached") for r in responses)


@pytest.mark.integration
async def test_large_response_caching(test_app):
    """Test caching of large responses with many waypoints."""
    waypoints = "|".join([
        f"40.{i},-74.0" for i in range(10)
    ])
    params = {
        "origin": "40.7128,-74.0060",
        "destination": "40.7614,-73.9776",
        "waypoints": waypoints,
        "alternatives": True,
        "include_places": True
    }
    
    # First request
    response1 = test_app.get("/directions", params=params)
    assert response1.status_code == 200
    
    # Second request should be cached
    response2 = test_app.get("/directions", params=params)
    assert response2.status_code == 200
    assert response2.json().get("cached")
    
    # Verify large response was cached correctly
    assert response1.json()["routes"] == response2.json()["routes"]


@pytest.mark.integration
async def test_partial_failures(test_app):
    """Test handling of partial API failures."""
    params = {
        "origin": "40.7128,-74.0060",
        "destination": "40.7614,-73.9776",
        "include_places": True  # Places API might fail independently
    }
    response = test_app.get("/directions", params=params)
    assert response.status_code == 200
    data = response.json()
    
    # Route should succeed even if place details fail
    assert len(data["routes"]) > 0
    leg = data["routes"][0]["legs"][0]
    if "start_place_details" not in leg:
        assert "end_place_details" not in leg 