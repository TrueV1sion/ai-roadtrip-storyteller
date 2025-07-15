"""
Pytest configuration file for the roadtrip test suite.
This file sets up the Python path and common fixtures for all tests.
"""
import sys
import os
from pathlib import Path

# Add the project root to Python path so imports work correctly
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime

# Import app modules after path is set
os.environ["TEST_MODE"] = "true"
os.environ["DATABASE_URL"] = "postgresql://roadtrip:roadtrip_dev@localhost:5432/roadtrip_test"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret"

from backend.app.core.config import Settings
from backend.app.models.user import User, UserPreferences
from backend.app.services.master_orchestration_agent import JourneyContext

@pytest.fixture
def test_settings():
    """Provide test settings instance."""
    return Settings(
        _env_file=".env.test",
        TEST_MODE="true",
        DATABASE_URL="postgresql://roadtrip:roadtrip_dev@localhost:5432/roadtrip_test"
    )

@pytest.fixture
def mock_ai_client():
    """Mock AI client for testing without API calls."""
    client = Mock()
    client.generate_response = AsyncMock(return_value="Test AI response")
    client.generate_structured_response = AsyncMock(return_value={
        "primary_intent": "story_request",
        "secondary_intents": [],
        "required_agents": {"story": {"task": "generate_story"}},
        "urgency": "can_wait",
        "context_requirements": [],
        "expected_response_type": "story"
    })
    return client

@pytest.fixture
def sample_user():
    """Provide a sample user for testing."""
    return User(
        id=1,
        email="test@example.com",
        name="Test User",
        preferences=UserPreferences(
            preferred_voice_personality="friendly_guide",
            interests=["history", "nature"],
            family_friendly=True
        )
    )

@pytest.fixture
def sample_journey_context():
    """Provide sample journey context for testing."""
    return JourneyContext(
        current_location={"name": "San Francisco", "lat": 37.7749, "lng": -122.4194},
        current_time=datetime.now(),
        journey_stage="in_progress",
        passengers=[{"type": "adult", "count": 2}, {"type": "child", "count": 1}],
        vehicle_info={"type": "sedan", "fuel": "gas"},
        weather={"temp": 68, "condition": "sunny"},
        route_info={"distance": 100, "duration": 120, "destination": "Los Angeles"}
    )

@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    redis_mock = Mock()
    redis_mock.get = Mock(return_value=None)
    redis_mock.set = Mock(return_value=True)
    redis_mock.exists = Mock(return_value=False)
    redis_mock.expire = Mock(return_value=True)
    return redis_mock

@pytest.fixture
async def async_client():
    """Create async test client for API testing."""
    from httpx import AsyncClient
    from backend.app.main_mvp import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

# Configure pytest-asyncio
pytest_plugins = ['pytest_asyncio']

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests that test individual components"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests that test component interactions"
    )
    config.addinivalue_line(
        "markers", "mvp: Tests for MVP features only"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take more than 1 second"
    )
    config.addinivalue_line(
        "markers", "live_api: Tests that require real API connections"
    )