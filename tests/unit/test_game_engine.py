"""
Comprehensive unit tests for the game engine components
Tests cover: TriviaGameEngine, ScavengerHuntEngine, AchievementSystem, FamilyGameCoordinator
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json

from backend.app.services.game_engine import (
    TriviaGameEngine, ScavengerHuntEngine, AchievementSystem, 
    FamilyGameCoordinator, GameSession, TriviaQuestion,
    ScavengerHuntTask, Achievement, GameDifficulty
)
from backend.app.models.user import User


class TestTriviaGameEngine:
    """Test suite for TriviaGameEngine"""
    
    @pytest.fixture
    def trivia_engine(self):
        """Create a TriviaGameEngine instance with mocked AI client"""
        mock_ai_client = AsyncMock()
        mock_db = Mock()
        return TriviaGameEngine(mock_ai_client, mock_db)
    
    @pytest.fixture
    def sample_location(self):
        """Sample location data for testing"""
        return {
            "lat": 40.7128,
            "lng": -74.0060,
            "name": "New York City",
            "state": "NY",
            "country": "USA"
        }
    
    @pytest.fixture
    def sample_user(self):
        """Sample user for testing"""
        user = Mock(spec=User)
        user.id = 1
        user.username = "test_user"
        return user
    
    @pytest.mark.asyncio
    async def test_generate_question_success(self, trivia_engine, sample_location):
        """Test successful trivia question generation"""
        # Mock AI response
        trivia_engine.ai_client.generate_structured_response.return_value = {
            "question": "What year was the Statue of Liberty dedicated?",
            "options": ["1886", "1890", "1875", "1901"],
            "correct_answer": 0,
            "explanation": "The Statue of Liberty was dedicated on October 28, 1886.",
            "category": "history",
            "fun_fact": "The statue was a gift from France."
        }
        
        question = await trivia_engine.generate_question(
            location=sample_location,
            difficulty="medium",
            age_group="adult"
        )
        
        assert isinstance(question, dict)
        assert question["question"] == "What year was the Statue of Liberty dedicated?"
        assert len(question["options"]) == 4
        assert question["correct_answer"] == 0
        assert "explanation" in question
        assert question["category"] == "history"
    
    @pytest.mark.asyncio
    async def test_generate_question_with_category_filter(self, trivia_engine, sample_location):
        """Test question generation with specific category"""
        trivia_engine.ai_client.generate_structured_response.return_value = {
            "question": "Which river flows through New York?",
            "options": ["Hudson River", "Mississippi River", "Colorado River", "Columbia River"],
            "correct_answer": 0,
            "explanation": "The Hudson River flows through eastern New York.",
            "category": "geography",
            "fun_fact": "The Hudson River is 315 miles long."
        }
        
        question = await trivia_engine.generate_question(
            location=sample_location,
            difficulty="easy",
            category="geography"
        )
        
        assert question["category"] == "geography"
        trivia_engine.ai_client.generate_structured_response.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_question_ai_failure(self, trivia_engine, sample_location):
        """Test question generation when AI fails"""
        trivia_engine.ai_client.generate_structured_response.side_effect = Exception("AI Error")
        
        question = await trivia_engine.generate_question(sample_location)
        
        # Should return a fallback question
        assert isinstance(question, dict)
        assert "question" in question
        assert question["question"] == "What interesting fact can you discover about this location?"
    
    @pytest.mark.asyncio
    async def test_create_game_session(self, trivia_engine, sample_user):
        """Test creating a new game session"""
        session_id = await trivia_engine.create_game_session(
            user_id=1,
            game_mode="standard",
            difficulty="medium"
        )
        
        assert session_id in trivia_engine.active_sessions
        session = trivia_engine.active_sessions[session_id]
        assert session.user_id == 1
        assert session.game_mode == "standard"
        assert session.difficulty == "medium"
        assert session.score == 0
        assert session.questions_answered == 0
    
    @pytest.mark.asyncio
    async def test_submit_answer_correct(self, trivia_engine, sample_user):
        """Test submitting a correct answer"""
        # Create session and add a question
        session_id = await trivia_engine.create_game_session(user_id=1)
        session = trivia_engine.active_sessions[session_id]
        
        question = TriviaQuestion(
            id="q1",
            question="Test question?",
            options=["A", "B", "C", "D"],
            correct_answer=1,
            category="test",
            difficulty="medium"
        )
        session.current_question = question
        
        result = await trivia_engine.submit_answer(
            session_id=session_id,
            answer_index=1,
            time_taken=5.0
        )
        
        assert result["correct"] is True
        assert result["score"] > 0
        assert result["streak"] == 1
        assert session.score > 0
        assert session.questions_answered == 1
    
    @pytest.mark.asyncio
    async def test_submit_answer_incorrect(self, trivia_engine):
        """Test submitting an incorrect answer"""
        session_id = await trivia_engine.create_game_session(user_id=1)
        session = trivia_engine.active_sessions[session_id]
        
        question = TriviaQuestion(
            id="q1",
            question="Test question?",
            options=["A", "B", "C", "D"],
            correct_answer=1,
            category="test",
            difficulty="medium"
        )
        session.current_question = question
        session.streak = 3
        
        result = await trivia_engine.submit_answer(
            session_id=session_id,
            answer_index=0,  # Wrong answer
            time_taken=5.0
        )
        
        assert result["correct"] is False
        assert result["correct_answer"] == 1
        assert result["streak"] == 0
        assert session.streak == 0
    
    @pytest.mark.asyncio
    async def test_calculate_score_with_bonuses(self, trivia_engine):
        """Test score calculation with time and streak bonuses"""
        base_score = 100
        
        # Fast answer with streak
        score = trivia_engine._calculate_score(
            difficulty="hard",
            time_taken=2.0,
            streak=5
        )
        assert score > base_score * 2  # Hard difficulty multiplier + bonuses
        
        # Slow answer, no streak
        score = trivia_engine._calculate_score(
            difficulty="easy",
            time_taken=30.0,
            streak=0
        )
        assert score == 50  # Easy difficulty, no bonuses
    
    @pytest.mark.asyncio
    async def test_get_session_summary(self, trivia_engine):
        """Test getting game session summary"""
        session_id = await trivia_engine.create_game_session(user_id=1)
        session = trivia_engine.active_sessions[session_id]
        
        # Simulate some gameplay
        session.score = 500
        session.questions_answered = 10
        session.correct_answers = 7
        session.categories_played.update(["history", "geography", "culture"])
        
        summary = await trivia_engine.get_session_summary(session_id)
        
        assert summary["total_score"] == 500
        assert summary["questions_answered"] == 10
        assert summary["accuracy"] == 70.0
        assert len(summary["categories_played"]) == 3
        assert "duration" in summary
    
    @pytest.mark.asyncio
    async def test_end_session_with_achievements(self, trivia_engine):
        """Test ending a session and checking for achievements"""
        # Mock achievement system
        mock_achievement_system = AsyncMock()
        trivia_engine.achievement_system = mock_achievement_system
        
        session_id = await trivia_engine.create_game_session(user_id=1)
        session = trivia_engine.active_sessions[session_id]
        session.score = 1000
        session.max_streak = 10
        
        result = await trivia_engine.end_session(session_id)
        
        assert result["final_score"] == 1000
        assert session_id not in trivia_engine.active_sessions
        mock_achievement_system.check_game_achievements.assert_called_once()


class TestScavengerHuntEngine:
    """Test suite for ScavengerHuntEngine"""
    
    @pytest.fixture
    def hunt_engine(self):
        """Create a ScavengerHuntEngine instance"""
        mock_ai_client = AsyncMock()
        mock_db = Mock()
        return ScavengerHuntEngine(mock_ai_client, mock_db)
    
    @pytest.fixture
    def sample_region(self):
        """Sample region for scavenger hunt"""
        return {
            "center": {"lat": 40.7128, "lng": -74.0060},
            "radius": 10,
            "name": "Manhattan"
        }
    
    @pytest.mark.asyncio
    async def test_create_hunt_success(self, hunt_engine, sample_region):
        """Test creating a scavenger hunt"""
        # Mock AI response for tasks
        hunt_engine.ai_client.generate_structured_response.return_value = {
            "tasks": [
                {
                    "id": "task1",
                    "title": "Find the Charging Bull",
                    "description": "Locate and photograph the famous Wall Street Bull",
                    "type": "photo",
                    "points": 50,
                    "hints": ["It's in the Financial District", "Near Bowling Green"],
                    "verification_criteria": "Photo must show the bull statue"
                },
                {
                    "id": "task2",
                    "title": "Visit Times Square",
                    "description": "Take a selfie in Times Square",
                    "type": "location",
                    "points": 30,
                    "location": {"lat": 40.7580, "lng": -73.9855},
                    "radius": 100
                }
            ],
            "theme": "NYC Icons",
            "estimated_duration": 120
        }
        
        hunt = await hunt_engine.create_hunt(
            user_id=1,
            region=sample_region,
            difficulty="medium",
            theme="tourist"
        )
        
        assert hunt["hunt_id"] in hunt_engine.active_hunts
        assert len(hunt["tasks"]) == 2
        assert hunt["total_points"] == 80
        assert hunt["theme"] == "NYC Icons"
    
    @pytest.mark.asyncio
    async def test_submit_task_photo_verification(self, hunt_engine):
        """Test submitting a photo task for verification"""
        # Create a hunt with a photo task
        hunt_id = "test_hunt"
        hunt_engine.active_hunts[hunt_id] = {
            "user_id": 1,
            "tasks": {
                "task1": ScavengerHuntTask(
                    id="task1",
                    title="Photo Task",
                    description="Take a photo",
                    task_type="photo",
                    points=50,
                    verification_criteria="Must show landmark"
                )
            },
            "completed_tasks": [],
            "score": 0
        }
        
        # Mock photo verification
        hunt_engine._verify_photo_task = AsyncMock(return_value=(True, "Great photo!"))
        
        result = await hunt_engine.submit_task(
            hunt_id=hunt_id,
            task_id="task1",
            submission_type="photo",
            data={"photo_url": "http://example.com/photo.jpg"}
        )
        
        assert result["verified"] is True
        assert result["points_earned"] == 50
        assert "task1" in hunt_engine.active_hunts[hunt_id]["completed_tasks"]
    
    @pytest.mark.asyncio
    async def test_submit_task_location_verification(self, hunt_engine):
        """Test submitting a location-based task"""
        hunt_id = "test_hunt"
        task_location = {"lat": 40.7580, "lng": -73.9855}
        
        hunt_engine.active_hunts[hunt_id] = {
            "user_id": 1,
            "tasks": {
                "task1": ScavengerHuntTask(
                    id="task1",
                    title="Location Task",
                    description="Visit location",
                    task_type="location",
                    points=30,
                    location=task_location,
                    radius=100
                )
            },
            "completed_tasks": [],
            "score": 0
        }
        
        # Submit location within radius
        result = await hunt_engine.submit_task(
            hunt_id=hunt_id,
            task_id="task1",
            submission_type="location",
            data={"lat": 40.7579, "lng": -73.9856}  # Very close to target
        )
        
        assert result["verified"] is True
        assert result["points_earned"] == 30
    
    @pytest.mark.asyncio
    async def test_submit_task_location_too_far(self, hunt_engine):
        """Test location task rejection when too far"""
        hunt_id = "test_hunt"
        task_location = {"lat": 40.7580, "lng": -73.9855}
        
        hunt_engine.active_hunts[hunt_id] = {
            "user_id": 1,
            "tasks": {
                "task1": ScavengerHuntTask(
                    id="task1",
                    title="Location Task",
                    description="Visit location",
                    task_type="location",
                    points=30,
                    location=task_location,
                    radius=50  # 50 meters
                )
            },
            "completed_tasks": [],
            "score": 0
        }
        
        # Submit location too far away
        result = await hunt_engine.submit_task(
            hunt_id=hunt_id,
            task_id="task1",
            submission_type="location",
            data={"lat": 40.7484, "lng": -73.9857}  # ~1km away
        )
        
        assert result["verified"] is False
        assert result["points_earned"] == 0
        assert "message" in result
    
    @pytest.mark.asyncio
    async def test_calculate_distance(self, hunt_engine):
        """Test distance calculation between coordinates"""
        # Test known distance (approximately 1.85 km)
        coord1 = {"lat": 40.7128, "lng": -74.0060}  # NYC
        coord2 = {"lat": 40.7260, "lng": -73.9897}  # Brooklyn Bridge
        
        distance = hunt_engine._calculate_distance(
            coord1["lat"], coord1["lng"],
            coord2["lat"], coord2["lng"]
        )
        
        # Should be approximately 1850 meters
        assert 1800 < distance < 1900
    
    @pytest.mark.asyncio
    async def test_get_hint(self, hunt_engine):
        """Test getting hints for tasks"""
        hunt_id = "test_hunt"
        hunt_engine.active_hunts[hunt_id] = {
            "user_id": 1,
            "tasks": {
                "task1": ScavengerHuntTask(
                    id="task1",
                    title="Test Task",
                    description="Test",
                    task_type="photo",
                    points=50,
                    hints=["Hint 1", "Hint 2", "Hint 3"]
                )
            },
            "hints_used": {"task1": 0}
        }
        
        # Get first hint
        hint1 = await hunt_engine.get_hint(hunt_id, "task1")
        assert hint1["hint"] == "Hint 1"
        assert hint1["hint_number"] == 1
        assert hint1["points_deduction"] == 5
        
        # Get second hint
        hint2 = await hunt_engine.get_hint(hunt_id, "task1")
        assert hint2["hint"] == "Hint 2"
        assert hint2["points_deduction"] == 5
    
    @pytest.mark.asyncio
    async def test_complete_hunt(self, hunt_engine):
        """Test completing a scavenger hunt"""
        hunt_id = "test_hunt"
        hunt_engine.active_hunts[hunt_id] = {
            "user_id": 1,
            "tasks": {"task1": Mock(), "task2": Mock()},
            "completed_tasks": ["task1", "task2"],
            "score": 80,
            "start_time": datetime.now() - timedelta(minutes=30)
        }
        
        # Mock achievement check
        hunt_engine.achievement_system = AsyncMock()
        
        summary = await hunt_engine.complete_hunt(hunt_id)
        
        assert summary["total_score"] == 80
        assert summary["tasks_completed"] == 2
        assert summary["completion_rate"] == 100.0
        assert "duration" in summary
        assert hunt_id not in hunt_engine.active_hunts


class TestAchievementSystem:
    """Test suite for AchievementSystem"""
    
    @pytest.fixture
    def achievement_system(self):
        """Create an AchievementSystem instance"""
        mock_db = Mock()
        return AchievementSystem(mock_db)
    
    @pytest.fixture
    def sample_achievements(self):
        """Sample achievement definitions"""
        return {
            "first_game": Achievement(
                id="first_game",
                name="First Steps",
                description="Complete your first trivia game",
                points=10,
                icon="🎮",
                criteria={"games_completed": 1}
            ),
            "streak_master": Achievement(
                id="streak_master",
                name="Streak Master",
                description="Achieve a 10-answer streak",
                points=50,
                icon="🔥",
                criteria={"max_streak": 10}
            ),
            "explorer": Achievement(
                id="explorer",
                name="Explorer",
                description="Complete 5 scavenger hunts",
                points=100,
                icon="🗺️",
                criteria={"hunts_completed": 5}
            )
        }
    
    @pytest.mark.asyncio
    async def test_check_game_achievements_unlocked(self, achievement_system, sample_achievements):
        """Test checking and unlocking game achievements"""
        # Add achievements to system
        achievement_system.achievements.update(sample_achievements)
        
        # Mock database to show no previous achievements
        achievement_system.db.query().filter().all.return_value = []
        
        game_stats = {
            "games_completed": 1,
            "max_streak": 10,
            "total_score": 1000
        }
        
        unlocked = await achievement_system.check_game_achievements(
            user_id=1,
            game_stats=game_stats
        )
        
        assert len(unlocked) == 2
        achievement_ids = [a.id for a in unlocked]
        assert "first_game" in achievement_ids
        assert "streak_master" in achievement_ids
    
    @pytest.mark.asyncio
    async def test_check_achievements_already_unlocked(self, achievement_system, sample_achievements):
        """Test that already unlocked achievements aren't returned"""
        achievement_system.achievements.update(sample_achievements)
        
        # Mock database to show achievement already unlocked
        existing_achievement = Mock()
        existing_achievement.achievement_id = "first_game"
        achievement_system.db.query().filter().all.return_value = [existing_achievement]
        
        game_stats = {
            "games_completed": 5,
            "max_streak": 3
        }
        
        unlocked = await achievement_system.check_game_achievements(
            user_id=1,
            game_stats=game_stats
        )
        
        # Should not include first_game as it's already unlocked
        assert len(unlocked) == 0
    
    @pytest.mark.asyncio
    async def test_unlock_achievement(self, achievement_system, sample_achievements):
        """Test unlocking a specific achievement"""
        achievement = sample_achievements["explorer"]
        achievement_system.achievements["explorer"] = achievement
        
        # Mock database operations
        achievement_system.db.add = Mock()
        achievement_system.db.commit = Mock()
        
        result = await achievement_system.unlock_achievement(
            user_id=1,
            achievement_id="explorer"
        )
        
        assert result is True
        achievement_system.db.add.assert_called_once()
        achievement_system.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_achievements(self, achievement_system, sample_achievements):
        """Test retrieving user's achievements"""
        achievement_system.achievements.update(sample_achievements)
        
        # Mock database response
        user_achievements = [
            Mock(achievement_id="first_game", unlocked_at=datetime.now()),
            Mock(achievement_id="explorer", unlocked_at=datetime.now())
        ]
        achievement_system.db.query().filter().all.return_value = user_achievements
        
        achievements = await achievement_system.get_user_achievements(user_id=1)
        
        assert len(achievements) == 2
        assert achievements[0]["id"] == "first_game"
        assert achievements[0]["name"] == "First Steps"
        assert achievements[0]["unlocked"] is True
        assert achievements[1]["id"] == "explorer"
        assert achievements[1]["unlocked"] is True
    
    @pytest.mark.asyncio
    async def test_get_user_progress(self, achievement_system):
        """Test getting user's achievement progress"""
        # Mock database for user stats
        achievement_system.db.query().filter().first.return_value = Mock(
            total_points=160,
            achievements_unlocked=3
        )
        
        achievement_system.db.query().filter().count.return_value = 3
        
        progress = await achievement_system.get_user_progress(user_id=1)
        
        assert progress["total_points"] == 160
        assert progress["achievements_unlocked"] == 3
        assert progress["total_achievements"] == len(achievement_system.achievements)
        assert "completion_percentage" in progress
        assert "rank" in progress


class TestFamilyGameCoordinator:
    """Test suite for FamilyGameCoordinator"""
    
    @pytest.fixture
    def coordinator(self):
        """Create a FamilyGameCoordinator instance"""
        mock_trivia = AsyncMock()
        mock_hunt = AsyncMock()
        mock_achievements = AsyncMock()
        return FamilyGameCoordinator(mock_trivia, mock_hunt, mock_achievements)
    
    @pytest.mark.asyncio
    async def test_create_family_session(self, coordinator):
        """Test creating a family game session"""
        family_members = [
            {"user_id": 1, "name": "Parent", "age_group": "adult"},
            {"user_id": 2, "name": "Teen", "age_group": "teen"},
            {"user_id": 3, "name": "Child", "age_group": "child"}
        ]
        
        session_id = await coordinator.create_family_session(
            family_id="family123",
            members=family_members,
            game_mode="collaborative"
        )
        
        assert session_id in coordinator.family_sessions
        session = coordinator.family_sessions[session_id]
        assert session["family_id"] == "family123"
        assert len(session["members"]) == 3
        assert session["game_mode"] == "collaborative"
        assert session["active"] is True
    
    @pytest.mark.asyncio
    async def test_generate_family_trivia(self, coordinator):
        """Test generating age-appropriate trivia for family"""
        # Create family session
        session_id = "test_session"
        coordinator.family_sessions[session_id] = {
            "members": [
                {"user_id": 1, "age_group": "adult"},
                {"user_id": 2, "age_group": "child"}
            ],
            "scores": {1: 0, 2: 0}
        }
        
        # Mock trivia generation
        coordinator.trivia_engine.generate_question.return_value = {
            "question": "Family-friendly question",
            "options": ["A", "B", "C", "D"],
            "correct_answer": 0
        }
        
        question = await coordinator.generate_family_trivia(
            session_id=session_id,
            location={"lat": 0, "lng": 0}
        )
        
        assert "question" in question
        # Should be called with easiest age group (child)
        coordinator.trivia_engine.generate_question.assert_called_with(
            location={"lat": 0, "lng": 0},
            difficulty="easy",
            age_group="child"
        )
    
    @pytest.mark.asyncio
    async def test_collaborative_scoring(self, coordinator):
        """Test collaborative scoring mode"""
        session_id = "test_session"
        coordinator.family_sessions[session_id] = {
            "family_id": "family123",
            "members": [
                {"user_id": 1, "age_group": "adult"},
                {"user_id": 2, "age_group": "child"}
            ],
            "game_mode": "collaborative",
            "scores": {1: 100, 2: 50},
            "team_score": 150
        }
        
        # Add points collaboratively
        coordinator._update_collaborative_score(session_id, 50)
        
        session = coordinator.family_sessions[session_id]
        assert session["team_score"] == 200
    
    @pytest.mark.asyncio
    async def test_competitive_scoring(self, coordinator):
        """Test competitive scoring mode"""
        session_id = "test_session"
        coordinator.family_sessions[session_id] = {
            "family_id": "family123",
            "members": [
                {"user_id": 1, "age_group": "adult"},
                {"user_id": 2, "age_group": "teen"}
            ],
            "game_mode": "competitive",
            "scores": {1: 100, 2: 80}
        }
        
        # Update individual score
        coordinator._update_competitive_score(session_id, user_id=1, points=50)
        
        session = coordinator.family_sessions[session_id]
        assert session["scores"][1] == 150
        assert session["scores"][2] == 80  # Unchanged
    
    @pytest.mark.asyncio
    async def test_get_family_leaderboard(self, coordinator):
        """Test getting family leaderboard"""
        session_id = "test_session"
        coordinator.family_sessions[session_id] = {
            "members": [
                {"user_id": 1, "name": "Parent"},
                {"user_id": 2, "name": "Teen"},
                {"user_id": 3, "name": "Child"}
            ],
            "scores": {1: 300, 2: 250, 3: 400},
            "game_mode": "competitive"
        }
        
        leaderboard = await coordinator.get_family_leaderboard(session_id)
        
        assert len(leaderboard) == 3
        assert leaderboard[0]["name"] == "Child"  # Highest score
        assert leaderboard[0]["score"] == 400
        assert leaderboard[1]["name"] == "Parent"
        assert leaderboard[2]["name"] == "Teen"  # Lowest score
    
    @pytest.mark.asyncio
    async def test_end_family_session(self, coordinator):
        """Test ending a family game session"""
        session_id = "test_session"
        coordinator.family_sessions[session_id] = {
            "family_id": "family123",
            "members": [{"user_id": 1}, {"user_id": 2}],
            "game_mode": "collaborative",
            "team_score": 500,
            "start_time": datetime.now() - timedelta(minutes=45),
            "games_played": 3
        }
        
        # Mock achievement checking
        coordinator.achievements.check_family_achievements = AsyncMock(return_value=[])
        
        summary = await coordinator.end_family_session(session_id)
        
        assert summary["total_score"] == 500
        assert summary["games_played"] == 3
        assert "duration" in summary
        assert "achievements" in summary
        assert session_id not in coordinator.family_sessions
        
        # Verify achievement check was called
        coordinator.achievements.check_family_achievements.assert_called_once()


class TestGameEngineIntegration:
    """Integration tests for game engine components"""
    
    @pytest.mark.asyncio
    async def test_trivia_to_achievement_flow(self):
        """Test full flow from trivia game to achievement unlock"""
        # Setup
        mock_ai_client = AsyncMock()
        mock_db = Mock()
        
        trivia_engine = TriviaGameEngine(mock_ai_client, mock_db)
        achievement_system = AchievementSystem(mock_db)
        
        # Add achievement
        achievement_system.achievements["high_scorer"] = Achievement(
            id="high_scorer",
            name="High Scorer",
            description="Score over 1000 points",
            points=50,
            criteria={"min_score": 1000}
        )
        
        # Mock database
        mock_db.query().filter().all.return_value = []  # No existing achievements
        
        # Create game session
        session_id = await trivia_engine.create_game_session(user_id=1)
        session = trivia_engine.active_sessions[session_id]
        session.score = 1200  # High score
        
        # End session and check achievements
        trivia_engine.achievement_system = achievement_system
        result = await trivia_engine.end_session(session_id)
        
        # Verify achievement was checked
        assert mock_db.add.called
        assert mock_db.commit.called
    
    @pytest.mark.asyncio
    async def test_scavenger_hunt_with_location_validation(self):
        """Test scavenger hunt with real location validation"""
        mock_ai_client = AsyncMock()
        mock_db = Mock()
        
        hunt_engine = ScavengerHuntEngine(mock_ai_client, mock_db)
        
        # Create hunt with location task
        hunt_id = "test_hunt"
        statue_of_liberty = {"lat": 40.6892, "lng": -74.0445}
        
        hunt_engine.active_hunts[hunt_id] = {
            "user_id": 1,
            "tasks": {
                "liberty": ScavengerHuntTask(
                    id="liberty",
                    title="Visit Lady Liberty",
                    description="Visit the Statue of Liberty",
                    task_type="location",
                    points=100,
                    location=statue_of_liberty,
                    radius=500  # 500 meters
                )
            },
            "completed_tasks": [],
            "score": 0
        }
        
        # Test various locations
        test_cases = [
            # (lat, lng, should_pass, description)
            (40.6892, -74.0445, True, "Exact location"),
            (40.6895, -74.0448, True, "Within radius"),
            (40.6950, -74.0500, False, "Too far away"),
            (40.7128, -74.0060, False, "Manhattan - way too far")
        ]
        
        for lat, lng, should_pass, description in test_cases:
            result = await hunt_engine.submit_task(
                hunt_id=hunt_id,
                task_id="liberty",
                submission_type="location",
                data={"lat": lat, "lng": lng}
            )
            
            assert result["verified"] == should_pass, f"Failed for: {description}"
            
            # Reset for next test
            if should_pass:
                hunt_engine.active_hunts[hunt_id]["completed_tasks"].remove("liberty")
                hunt_engine.active_hunts[hunt_id]["score"] = 0


class TestGameEngineErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_invalid_session_id(self):
        """Test handling invalid session IDs"""
        trivia_engine = TriviaGameEngine(AsyncMock(), Mock())
        
        with pytest.raises(ValueError, match="Session not found"):
            await trivia_engine.submit_answer("invalid_id", 0, 5.0)
        
        with pytest.raises(ValueError, match="Session not found"):
            await trivia_engine.get_session_summary("invalid_id")
    
    @pytest.mark.asyncio
    async def test_concurrent_session_limit(self):
        """Test concurrent session limits per user"""
        trivia_engine = TriviaGameEngine(AsyncMock(), Mock())
        trivia_engine.MAX_SESSIONS_PER_USER = 3
        
        # Create maximum allowed sessions
        for i in range(3):
            await trivia_engine.create_game_session(user_id=1)
        
        # Try to create one more
        with pytest.raises(ValueError, match="Maximum concurrent sessions"):
            await trivia_engine.create_game_session(user_id=1)
    
    @pytest.mark.asyncio
    async def test_invalid_hunt_submission(self):
        """Test invalid hunt task submissions"""
        hunt_engine = ScavengerHuntEngine(AsyncMock(), Mock())
        
        # Invalid hunt ID
        with pytest.raises(ValueError, match="Hunt not found"):
            await hunt_engine.submit_task("invalid", "task1", "photo", {})
        
        # Create hunt but submit invalid task
        hunt_engine.active_hunts["hunt1"] = {
            "tasks": {},
            "completed_tasks": []
        }
        
        with pytest.raises(ValueError, match="Task not found"):
            await hunt_engine.submit_task("hunt1", "invalid_task", "photo", {})


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])