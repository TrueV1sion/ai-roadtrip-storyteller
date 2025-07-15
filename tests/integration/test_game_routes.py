"""
Comprehensive integration tests for game API endpoints
Tests all game-related routes with various scenarios
"""

import pytest
import asyncio
import json
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, AsyncMock, patch

from backend.app.main import app
from backend.app.database import Base, get_db
from backend.app.models.user import User
from backend.app.core.auth import create_access_token


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


class TestGameRoutes:
    """Test suite for game-related API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test database and cleanup after each test"""
        Base.metadata.create_all(bind=engine)
        yield
        Base.metadata.drop_all(bind=engine)
    
    @pytest.fixture
    def test_user(self):
        """Create a test user"""
        db = TestingSessionLocal()
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        db.close()
        return user
    
    @pytest.fixture
    def auth_headers(self, test_user):
        """Generate authentication headers"""
        token = create_access_token(data={"sub": test_user.username})
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture
    def mock_game_engine(self):
        """Mock game engine for testing"""
        with patch('backend.app.routes.games.trivia_engine') as mock:
            mock.generate_question = AsyncMock()
            mock.create_game_session = AsyncMock()
            mock.submit_answer = AsyncMock()
            mock.get_session_summary = AsyncMock()
            mock.end_session = AsyncMock()
            yield mock
    
    def test_start_trivia_game_success(self, auth_headers, mock_game_engine):
        """Test starting a new trivia game"""
        mock_game_engine.create_game_session.return_value = "session_123"
        
        response = client.post(
            "/api/games/trivia/start",
            headers=auth_headers,
            json={
                "game_mode": "standard",
                "difficulty": "medium"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "session_123"
        assert data["status"] == "started"
    
    def test_start_trivia_game_unauthorized(self):
        """Test starting game without authentication"""
        response = client.post(
            "/api/games/trivia/start",
            json={"game_mode": "standard"}
        )
        
        assert response.status_code == 401
    
    def test_get_trivia_question(self, auth_headers, mock_game_engine):
        """Test getting a trivia question"""
        mock_question = {
            "question": "What year was New York founded?",
            "options": ["1624", "1650", "1700", "1750"],
            "category": "history",
            "difficulty": "medium"
        }
        
        mock_game_engine.generate_question.return_value = mock_question
        
        response = client.post(
            "/api/games/trivia/session/session_123/question",
            headers=auth_headers,
            json={
                "location": {
                    "lat": 40.7128,
                    "lng": -74.0060,
                    "name": "New York City"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["question"] == mock_question["question"]
        assert len(data["options"]) == 4
    
    def test_submit_answer_correct(self, auth_headers, mock_game_engine):
        """Test submitting a correct answer"""
        mock_game_engine.submit_answer.return_value = {
            "correct": True,
            "score": 100,
            "streak": 3,
            "explanation": "Great job!"
        }
        
        response = client.post(
            "/api/games/trivia/session/session_123/answer",
            headers=auth_headers,
            json={
                "answer_index": 0,
                "time_taken": 5.5
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["correct"] is True
        assert data["score"] == 100
        assert data["streak"] == 3
    
    def test_submit_answer_incorrect(self, auth_headers, mock_game_engine):
        """Test submitting an incorrect answer"""
        mock_game_engine.submit_answer.return_value = {
            "correct": False,
            "correct_answer": 2,
            "explanation": "The correct answer was 1700",
            "streak": 0
        }
        
        response = client.post(
            "/api/games/trivia/session/session_123/answer",
            headers=auth_headers,
            json={
                "answer_index": 1,
                "time_taken": 8.2
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["correct"] is False
        assert data["correct_answer"] == 2
    
    def test_get_game_session_summary(self, auth_headers, mock_game_engine):
        """Test getting game session summary"""
        mock_game_engine.get_session_summary.return_value = {
            "total_score": 850,
            "questions_answered": 10,
            "correct_answers": 7,
            "accuracy": 70.0,
            "max_streak": 5,
            "categories_played": ["history", "geography", "culture"],
            "duration": 300  # 5 minutes
        }
        
        response = client.get(
            "/api/games/trivia/session/session_123/summary",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_score"] == 850
        assert data["accuracy"] == 70.0
    
    def test_end_game_session(self, auth_headers, mock_game_engine):
        """Test ending a game session"""
        mock_game_engine.end_session.return_value = {
            "final_score": 1200,
            "achievements": [
                {"id": "streak_master", "name": "Streak Master", "points": 50}
            ]
        }
        
        response = client.post(
            "/api/games/trivia/session/session_123/end",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["final_score"] == 1200
        assert len(data["achievements"]) == 1
    
    def test_get_leaderboard(self, auth_headers):
        """Test getting game leaderboard"""
        response = client.get(
            "/api/games/leaderboard",
            headers=auth_headers,
            params={
                "game_type": "trivia",
                "time_range": "weekly",
                "limit": 10
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "leaderboard" in data
        assert isinstance(data["leaderboard"], list)


class TestScavengerHuntRoutes:
    """Test suite for scavenger hunt endpoints"""
    
    @pytest.fixture
    def mock_hunt_engine(self):
        """Mock scavenger hunt engine"""
        with patch('backend.app.routes.games.hunt_engine') as mock:
            mock.create_hunt = AsyncMock()
            mock.get_hunt_status = AsyncMock()
            mock.submit_task = AsyncMock()
            mock.get_hint = AsyncMock()
            mock.complete_hunt = AsyncMock()
            yield mock
    
    def test_create_scavenger_hunt(self, auth_headers, mock_hunt_engine):
        """Test creating a new scavenger hunt"""
        mock_hunt_engine.create_hunt.return_value = {
            "hunt_id": "hunt_456",
            "tasks": [
                {
                    "id": "task1",
                    "title": "Find the Liberty Bell",
                    "type": "photo",
                    "points": 50
                },
                {
                    "id": "task2",
                    "title": "Visit Independence Hall",
                    "type": "location",
                    "points": 30
                }
            ],
            "total_points": 80,
            "theme": "Historic Philadelphia"
        }
        
        response = client.post(
            "/api/games/scavenger-hunt/create",
            headers=auth_headers,
            json={
                "region": {
                    "center": {"lat": 39.9526, "lng": -75.1652},
                    "radius": 5,
                    "name": "Philadelphia"
                },
                "difficulty": "medium",
                "theme": "historical"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["hunt_id"] == "hunt_456"
        assert len(data["tasks"]) == 2
    
    def test_submit_photo_task(self, auth_headers, mock_hunt_engine):
        """Test submitting a photo for verification"""
        mock_hunt_engine.submit_task.return_value = {
            "verified": True,
            "points_earned": 50,
            "feedback": "Great photo of the Liberty Bell!"
        }
        
        response = client.post(
            "/api/games/scavenger-hunt/hunt_456/task/task1/submit",
            headers=auth_headers,
            json={
                "submission_type": "photo",
                "data": {
                    "photo_url": "https://example.com/photo.jpg",
                    "metadata": {
                        "timestamp": datetime.now().isoformat(),
                        "location": {"lat": 39.9496, "lng": -75.1503}
                    }
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["verified"] is True
        assert data["points_earned"] == 50
    
    def test_submit_location_task(self, auth_headers, mock_hunt_engine):
        """Test submitting location check-in"""
        mock_hunt_engine.submit_task.return_value = {
            "verified": True,
            "points_earned": 30,
            "feedback": "You've reached Independence Hall!"
        }
        
        response = client.post(
            "/api/games/scavenger-hunt/hunt_456/task/task2/submit",
            headers=auth_headers,
            json={
                "submission_type": "location",
                "data": {
                    "lat": 39.9495,
                    "lng": -75.1499,
                    "accuracy": 10  # meters
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["verified"] is True
    
    def test_get_hint(self, auth_headers, mock_hunt_engine):
        """Test requesting a hint"""
        mock_hunt_engine.get_hint.return_value = {
            "hint": "Look for the crack in the bell",
            "hint_number": 1,
            "points_deduction": 5
        }
        
        response = client.post(
            "/api/games/scavenger-hunt/hunt_456/task/task1/hint",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "hint" in data
        assert data["points_deduction"] == 5
    
    def test_complete_hunt(self, auth_headers, mock_hunt_engine):
        """Test completing a scavenger hunt"""
        mock_hunt_engine.complete_hunt.return_value = {
            "total_score": 75,
            "tasks_completed": 2,
            "total_tasks": 2,
            "completion_rate": 100.0,
            "duration": 3600,  # 1 hour
            "achievements": [
                {"id": "explorer", "name": "Explorer", "points": 100}
            ]
        }
        
        response = client.post(
            "/api/games/scavenger-hunt/hunt_456/complete",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["completion_rate"] == 100.0


class TestFamilyGameRoutes:
    """Test suite for family game endpoints"""
    
    @pytest.fixture
    def mock_family_coordinator(self):
        """Mock family game coordinator"""
        with patch('backend.app.routes.games.family_coordinator') as mock:
            mock.create_family_session = AsyncMock()
            mock.generate_family_trivia = AsyncMock()
            mock.update_family_score = AsyncMock()
            mock.get_family_leaderboard = AsyncMock()
            mock.end_family_session = AsyncMock()
            yield mock
    
    def test_create_family_session(self, auth_headers, mock_family_coordinator):
        """Test creating a family game session"""
        mock_family_coordinator.create_family_session.return_value = "family_session_789"
        
        response = client.post(
            "/api/games/family/session/create",
            headers=auth_headers,
            json={
                "family_id": "family_123",
                "members": [
                    {"user_id": 1, "name": "Dad", "age_group": "adult"},
                    {"user_id": 2, "name": "Mom", "age_group": "adult"},
                    {"user_id": 3, "name": "Teen", "age_group": "teen"},
                    {"user_id": 4, "name": "Kid", "age_group": "child"}
                ],
                "game_mode": "collaborative"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "family_session_789"
    
    def test_get_family_appropriate_question(self, auth_headers, mock_family_coordinator):
        """Test getting age-appropriate question for family"""
        mock_family_coordinator.generate_family_trivia.return_value = {
            "question": "What color is the Statue of Liberty?",
            "options": ["Green", "Blue", "Red", "Yellow"],
            "difficulty": "easy",
            "age_appropriate": True
        }
        
        response = client.post(
            "/api/games/family/session/family_session_789/question",
            headers=auth_headers,
            json={
                "location": {"lat": 40.6892, "lng": -74.0445}
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["age_appropriate"] is True
        assert data["difficulty"] == "easy"
    
    def test_collaborative_scoring(self, auth_headers, mock_family_coordinator):
        """Test collaborative family scoring"""
        mock_family_coordinator.update_family_score.return_value = {
            "team_score": 500,
            "contributor": "Kid",
            "bonus_reason": "Everyone participated!"
        }
        
        response = client.post(
            "/api/games/family/session/family_session_789/score",
            headers=auth_headers,
            json={
                "points": 100,
                "answered_by": 4  # Kid's user_id
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["team_score"] == 500


class TestAchievementRoutes:
    """Test suite for achievement endpoints"""
    
    def test_get_user_achievements(self, auth_headers):
        """Test getting user's achievements"""
        response = client.get(
            "/api/games/achievements",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "unlocked" in data
        assert "available" in data
        assert "progress" in data
    
    def test_get_achievement_details(self, auth_headers):
        """Test getting specific achievement details"""
        response = client.get(
            "/api/games/achievements/streak_master",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "description" in data
        assert "criteria" in data


class TestGameErrorHandling:
    """Test error handling in game routes"""
    
    def test_invalid_session_id(self, auth_headers):
        """Test handling invalid session ID"""
        response = client.post(
            "/api/games/trivia/session/invalid_session/answer",
            headers=auth_headers,
            json={"answer_index": 0, "time_taken": 5}
        )
        
        assert response.status_code == 404
        assert "Session not found" in response.json()["detail"]
    
    def test_invalid_location_data(self, auth_headers):
        """Test handling invalid location data"""
        response = client.post(
            "/api/games/trivia/session/session_123/question",
            headers=auth_headers,
            json={
                "location": {
                    "lat": "invalid",  # Should be float
                    "lng": -74.0060
                }
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_rate_limiting(self, auth_headers):
        """Test rate limiting on game endpoints"""
        # Simulate many rapid requests
        responses = []
        for _ in range(100):
            response = client.post(
                "/api/games/trivia/start",
                headers=auth_headers,
                json={"game_mode": "standard"}
            )
            responses.append(response.status_code)
        
        # Should eventually get rate limited
        assert 429 in responses  # Too Many Requests


if __name__ == "__main__":
    pytest.main([__file__, "-v"])