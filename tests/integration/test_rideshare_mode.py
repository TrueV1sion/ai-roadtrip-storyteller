"""
Integration tests for Rideshare Mode functionality
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user import User
from backend.app.services.rideshare_mode_manager import RideshareUserType


@pytest.mark.asyncio
class TestRideshareMode:
    """Test rideshare mode functionality"""
    
    async def test_set_driver_mode(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict
    ):
        """Test setting driver mode"""
        response = await async_client.post(
            "/api/rideshare/mode",
            json={
                "mode": "driver",
                "preferences": {
                    "break_reminders": True,
                    "earnings_goals": 200
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "driver"
        assert data["active"] is True
        assert "quick_actions" in data["features"]
        assert "earnings_tracking" in data["features"]
    
    async def test_set_passenger_mode(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict
    ):
        """Test setting passenger mode"""
        response = await async_client.post(
            "/api/rideshare/mode",
            json={
                "mode": "passenger",
                "preferences": {
                    "entertainment_types": ["games", "stories"],
                    "trip_duration": 20
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "passenger"
        assert data["active"] is True
        assert "entertainment" in data["features"]
        assert "games" in data["features"]
    
    async def test_driver_quick_actions(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict
    ):
        """Test getting driver quick actions"""
        # Set driver mode first
        await async_client.post(
            "/api/rideshare/mode",
            json={"mode": "driver"},
            headers=auth_headers
        )
        
        # Get quick actions
        response = await async_client.get(
            "/api/rideshare/driver/quick-actions",
            params={"lat": 37.7749, "lng": -122.4194},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        actions = response.json()
        assert len(actions) > 0
        
        # Verify action structure
        action = actions[0]
        assert "id" in action
        assert "label" in action
        assert "icon" in action
        assert "voice_command" in action
        assert "priority" in action
    
    async def test_execute_quick_action(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict
    ):
        """Test executing a driver quick action"""
        # Set driver mode
        await async_client.post(
            "/api/rideshare/mode",
            json={"mode": "driver"},
            headers=auth_headers
        )
        
        # Execute find gas action
        response = await async_client.post(
            "/api/rideshare/driver/quick-action",
            json={
                "action_id": "find_gas",
                "location": {"lat": 37.7749, "lng": -122.4194}
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["action_id"] == "find_gas"
        assert "result" in data
        assert "voice_response" in data
        assert "stations" in data["result"]
    
    async def test_driver_earnings_tracking(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict
    ):
        """Test driver earnings tracking"""
        # Set driver mode
        await async_client.post(
            "/api/rideshare/mode",
            json={"mode": "driver"},
            headers=auth_headers
        )
        
        # Record a trip
        response = await async_client.post(
            "/api/rideshare/driver/trip",
            json={
                "trip_id": "TEST-123",
                "earnings": 15.50,
                "distance": 8.2,
                "duration": 22,
                "pickup_location": {"lat": 37.7749, "lng": -122.4194},
                "dropoff_location": {"lat": 37.7849, "lng": -122.4094},
                "timestamp": "2024-01-01T12:00:00Z"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        stats = response.json()
        assert stats["total_earnings"] >= 15.50
        assert stats["trips_completed"] >= 1
        assert stats["hourly_rate"] > 0
    
    async def test_passenger_entertainment_options(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict
    ):
        """Test getting passenger entertainment options"""
        # Set passenger mode
        await async_client.post(
            "/api/rideshare/mode",
            json={"mode": "passenger"},
            headers=auth_headers
        )
        
        # Get entertainment options
        response = await async_client.post(
            "/api/rideshare/passenger/entertainment",
            json={"max_duration": 15},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "options" in data
        assert len(data["options"]) > 0
        
        # Verify option structure
        option = data["options"][0]
        assert "id" in option
        assert "name" in option
        assert "type" in option
        assert "duration" in option
        assert "description" in option
    
    async def test_voice_command_driver_safety(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict
    ):
        """Test voice command safety for drivers"""
        # Set driver mode
        await async_client.post(
            "/api/rideshare/mode",
            json={"mode": "driver"},
            headers=auth_headers
        )
        
        # Try command while moving (should fail)
        response = await async_client.post(
            "/api/rideshare/voice/command",
            json={
                "voice_input": "find gas station",
                "mode": "driver",
                "context": {},
                "vehicle_speed": 45,
                "is_moving": True
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "safety_warning"
        assert "wait until you're stopped" in data["response"].lower()
    
    async def test_voice_command_passenger_trivia(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict
    ):
        """Test passenger trivia voice command"""
        # Set passenger mode
        await async_client.post(
            "/api/rideshare/mode",
            json={"mode": "passenger"},
            headers=auth_headers
        )
        
        # Start trivia
        response = await async_client.post(
            "/api/rideshare/voice/command",
            json={
                "voice_input": "play trivia",
                "mode": "passenger",
                "context": {}
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "trivia_question"
        assert "data" in data
        assert "question" in data["data"]
        assert "options" in data["data"]
        assert "correct" in data["data"]
    
    async def test_end_rideshare_mode(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict
    ):
        """Test ending rideshare mode"""
        # Set driver mode first
        await async_client.post(
            "/api/rideshare/mode",
            json={"mode": "driver"},
            headers=auth_headers
        )
        
        # End mode
        response = await async_client.delete(
            "/api/rideshare/mode",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # Verify mode is ended
        mode_response = await async_client.get(
            "/api/rideshare/mode",
            headers=auth_headers
        )
        assert mode_response.json()["mode"] == "none"
    
    async def test_optimal_driver_routes(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict
    ):
        """Test getting optimal driver routes"""
        # Set driver mode
        await async_client.post(
            "/api/rideshare/mode",
            json={"mode": "driver"},
            headers=auth_headers
        )
        
        # Get optimal routes
        response = await async_client.get(
            "/api/rideshare/driver/optimal-routes",
            params={"lat": 37.7749, "lng": -122.4194},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        routes = response.json()
        assert len(routes) > 0
        
        # Verify route structure
        route = routes[0]
        assert "area" in route
        assert "demand_level" in route
        assert "estimated_wait" in route
        assert "surge_multiplier" in route