"""
Unit tests for the Dynamic Personality System
"""

import pytest
from datetime import datetime, date
from unittest.mock import Mock, patch, AsyncMock

from backend.app.services.dynamic_personality_system import (
    DynamicPersonalitySystem,
    PersonalityContext,
    PersonalityMetadata,
    ContextFactor
)
from backend.app.services.personality_registry import (
    PersonalityRegistry,
    ExtendedPersonalityMetadata
)
from backend.app.services.personality_integration import (
    PersonalityIntegrationService,
    PersonalitySelectionResult
)
from backend.app.services.personality_engine import VoicePersonality, PersonalityType


class TestDynamicPersonalitySystem:
    """Test the core Dynamic Personality System"""
    
    @pytest.fixture
    def system(self):
        """Create a test instance of the system"""
        return DynamicPersonalitySystem()
    
    @pytest.fixture
    def disney_context(self):
        """Create a Disney trip context"""
        return PersonalityContext(
            event_metadata={
                "name": "Disneyland Visit",
                "venue": {"name": "Disneyland Park"},
                "classifications": [{"segment": "theme_park", "genre": "disney"}]
            },
            location={"state": "california", "city": "anaheim"},
            datetime=datetime(2024, 7, 15, 10, 0),  # Summer morning
            weather={"condition": "sunny", "temperature": 75},
            journey_type="family_vacation",
            passenger_info={
                "passengers": [
                    {"age": 35, "name": "Parent"},
                    {"age": 8, "name": "Child"}
                ],
                "count": 2
            }
        )
    
    @pytest.fixture
    def christmas_context(self):
        """Create a Christmas season context"""
        return PersonalityContext(
            datetime=datetime(2024, 12, 20, 18, 0),  # December evening
            location={"state": "colorado", "city": "denver"},
            weather={"condition": "snow", "temperature": 28},
            special_occasion="christmas_shopping"
        )
    
    @pytest.fixture
    def concert_context(self):
        """Create a rock concert context"""
        return PersonalityContext(
            event_metadata={
                "name": "Metallica Concert",
                "venue": {"name": "Red Rocks Amphitheatre"},
                "classifications": [{"segment": "music", "genre": "rock"}]
            },
            location={"state": "colorado", "city": "morrison"},
            datetime=datetime(2024, 8, 15, 20, 0),  # Evening concert
            user_mood="excited",
            journey_type="entertainment"
        )
    
    @pytest.mark.asyncio
    async def test_disney_personality_selection(self, system, disney_context):
        """Test that Mickey Mouse is selected for Disney trips"""
        # Calculate scores
        scores = await system._calculate_personality_scores(disney_context)
        
        # Mickey should have high score
        assert "mickey_mouse" in scores
        assert scores["mickey_mouse"] > 100  # High priority + event match
        
        # Select personality
        selected = await system.select_personality(disney_context)
        assert selected.id in ["mickey_mouse", PersonalityType.FRIENDLY_GUIDE]
    
    @pytest.mark.asyncio
    async def test_christmas_personality_selection(self, system, christmas_context):
        """Test that Santa is selected during Christmas season"""
        # Mock the holiday calendar to ensure Christmas is active
        with patch.object(system.personality_engine, 'holiday_calendar', {
            "christmas": [date(2024, 12, 1), date(2024, 12, 25)]
        }):
            scores = await system._calculate_personality_scores(christmas_context)
            
            # Santa should have highest score during Christmas
            assert PersonalityType.SANTA in scores
            assert scores[PersonalityType.SANTA] > 100  # Base priority + holiday match
    
    @pytest.mark.asyncio
    async def test_regional_personality_selection(self, system):
        """Test regional personality selection"""
        texas_context = PersonalityContext(
            location={"state": "texas", "city": "austin"},
            datetime=datetime.now()
        )
        
        scores = await system._calculate_personality_scores(texas_context)
        
        # Texas Ranger should score well in Texas
        assert PersonalityType.TEXAS_RANGER in scores
        assert scores[PersonalityType.TEXAS_RANGER] > 50  # Base priority + region
    
    @pytest.mark.asyncio
    async def test_time_based_selection(self, system):
        """Test time-of-day personality selection"""
        # Morning context
        morning_context = PersonalityContext(
            datetime=datetime(2024, 6, 15, 7, 0)  # 7 AM
        )
        
        scores = await system._calculate_personality_scores(morning_context)
        
        # Morning motivator should score well
        assert "morning_motivator" in scores
        assert scores["morning_motivator"] > 50
    
    @pytest.mark.asyncio
    async def test_exclusion_rules(self, system):
        """Test personality exclusion rules"""
        # Young children present for Halloween
        halloween_context = PersonalityContext(
            datetime=datetime(2024, 10, 31, 20, 0),
            passenger_info={
                "passengers": [{"age": 5}],
                "count": 1
            }
        )
        
        scores = await system._calculate_personality_scores(halloween_context)
        
        # Halloween narrator should be excluded
        assert scores.get(PersonalityType.HALLOWEEN_NARRATOR, 0) == 0
    
    @pytest.mark.asyncio
    async def test_mood_matching(self, system):
        """Test mood-based personality matching"""
        romantic_context = PersonalityContext(
            user_mood="romantic",
            special_occasion="date_night",
            datetime=datetime(2024, 2, 14, 19, 0)  # Valentine's evening
        )
        
        scores = await system._calculate_personality_scores(romantic_context)
        
        # Cupid should score high
        assert PersonalityType.CUPID in scores
        assert scores[PersonalityType.CUPID] > 80
    
    @pytest.mark.asyncio
    async def test_personality_suggestions(self, system, concert_context):
        """Test getting multiple personality suggestions"""
        suggestions = await system.get_personality_suggestions(concert_context, count=3)
        
        assert len(suggestions) <= 3
        assert all(isinstance(p[0], VoicePersonality) for p in suggestions)
        assert all(isinstance(p[1], (int, float)) for p in suggestions)
        
        # Should be sorted by score
        scores = [s[1] for s in suggestions]
        assert scores == sorted(scores, reverse=True)


class TestPersonalityRegistry:
    """Test the Personality Registry"""
    
    @pytest.fixture
    def registry(self):
        """Create a test registry"""
        return PersonalityRegistry()
    
    def test_get_personality_by_id(self, registry):
        """Test retrieving personality by ID"""
        mickey = registry.get_personality("mickey_mouse")
        assert mickey is not None
        assert mickey.name == "Mickey Mouse"
        assert mickey.category == "event"
        assert "theme_park" in mickey.event_types
    
    def test_get_personalities_by_category(self, registry):
        """Test filtering personalities by category"""
        holiday_personalities = registry.get_personalities_by_category("holiday")
        
        assert len(holiday_personalities) > 0
        assert all(p.category == "holiday" for p in holiday_personalities)
        
        # Should include Santa, Easter Bunny, etc.
        holiday_ids = [p.id for p in holiday_personalities]
        assert "santa_claus" in holiday_ids
        assert "easter_bunny" in holiday_ids
    
    def test_get_personalities_for_event(self, registry):
        """Test finding personalities for specific events"""
        concert_personalities = registry.get_personalities_for_event("rock_concert")
        
        assert len(concert_personalities) > 0
        rock_star = next((p for p in concert_personalities if p.id == "rock_star"), None)
        assert rock_star is not None
        assert "rock_concert" in rock_star.event_types
    
    def test_search_personalities(self, registry):
        """Test searching personalities by criteria"""
        # Search for morning personalities
        morning_results = registry.search_personalities(
            time_slot="morning"
        )
        
        assert len(morning_results) > 0
        assert all("morning" in p.time_slots for p in morning_results)
        
        # Search for high-priority event personalities
        priority_results = registry.search_personalities(
            category="event",
            min_priority=85
        )
        
        assert len(priority_results) > 0
        assert all(p.priority >= 85 for p in priority_results)


class TestPersonalityIntegration:
    """Test the Personality Integration Service"""
    
    @pytest.fixture
    def integration_service(self):
        """Create a test integration service"""
        return PersonalityIntegrationService()
    
    @pytest.mark.asyncio
    async def test_select_personality_for_journey(self, integration_service):
        """Test complete journey personality selection"""
        journey_data = {
            "destination": "Orlando, FL",
            "destination_state": "florida",
            "destination_city": "orlando",
            "event_metadata": {
                "name": "Universal Studios Visit",
                "venue": {"name": "Universal Studios Florida"},
                "classifications": [{"segment": "theme_park"}]
            },
            "journey_type": "family_vacation",
            "passengers": [
                {"age": 40, "name": "Adult"},
                {"age": 12, "name": "Teen"}
            ],
            "passenger_count": 2
        }
        
        result = await integration_service.select_personality_for_journey(
            user_id="test_user",
            journey_data=journey_data
        )
        
        assert isinstance(result, PersonalitySelectionResult)
        assert isinstance(result.selected_personality, VoicePersonality)
        assert 0 <= result.confidence_score <= 1
        assert result.selection_reason != ""
        assert isinstance(result.alternatives, list)
    
    @pytest.mark.asyncio
    async def test_context_analysis(self, integration_service):
        """Test context analysis functionality"""
        journey_data = {
            "destination_state": "louisiana",
            "destination_city": "new orleans",
            "event_name": "Jazz Festival",
            "journey_type": "music_event",
            "user_mood": "excited",
            "passenger_count": 2
        }
        
        context = await integration_service._build_journey_context(
            "test_user",
            journey_data,
            None
        )
        
        analysis = integration_service._analyze_context(context)
        
        assert "primary_factors" in analysis
        assert "time_analysis" in analysis
        assert "environmental_factors" in analysis
        assert "user_factors" in analysis
        
        # Should detect mood
        assert any("mood: excited" in f for f in analysis["user_factors"])
    
    @pytest.mark.asyncio
    async def test_personality_recommendations(self, integration_service):
        """Test getting personality recommendations"""
        with patch.object(
            integration_service.dynamic_system,
            'get_personality_suggestions',
            return_value=[
                (Mock(id="rock_star", name="Johnny Riff", description="Rock star"), 95),
                (Mock(id="jazz_cat", name="Miles Blue", description="Jazz cat"), 85),
                (Mock(id="friendly_guide", name="Alex", description="Guide"), 75)
            ]
        ):
            recommendations = await integration_service.get_personality_recommendations(
                user_id="test_user",
                context={"event_type": "concert", "user_mood": "excited"}
            )
            
            assert len(recommendations) == 3
            assert recommendations[0]["id"] == "rock_star"
            assert recommendations[0]["match_score"] == 95
            assert "why_recommended" in recommendations[0]
    
    def test_special_occasion_detection(self, integration_service):
        """Test special occasion detection"""
        # Wedding detection
        wedding_data = {"event_name": "Smith Wedding Reception"}
        occasion = integration_service._detect_special_occasion(wedding_data)
        assert occasion == "wedding"
        
        # Birthday detection
        birthday_data = {"event_name": "Johnny's 10th Birthday Party"}
        occasion = integration_service._detect_special_occasion(birthday_data)
        assert occasion == "birthday"
        
        # No special occasion
        regular_data = {"event_name": "Morning Commute"}
        occasion = integration_service._detect_special_occasion(regular_data)
        assert occasion is None
    
    def test_region_determination(self, integration_service):
        """Test region determination from state"""
        assert integration_service._determine_region("texas") == "southwest"
        assert integration_service._determine_region("california") == "west"
        assert integration_service._determine_region("georgia") == "south"
        assert integration_service._determine_region("maine") == "northeast"
        assert integration_service._determine_region("illinois") == "midwest"
        assert integration_service._determine_region("unknown_state") == "unknown"


@pytest.mark.asyncio
async def test_analytics_tracking():
    """Test that personality selection analytics are tracked"""
    system = DynamicPersonalitySystem()
    
    # Make several selections
    contexts = [
        PersonalityContext(
            event_metadata={"classifications": [{"segment": "music"}]},
            datetime=datetime(2024, 6, 15, 20, 0)
        ),
        PersonalityContext(
            location={"state": "texas"},
            datetime=datetime(2024, 6, 16, 10, 0)
        ),
        PersonalityContext(
            special_occasion="birthday",
            datetime=datetime(2024, 6, 17, 14, 0)
        )
    ]
    
    for context in contexts:
        await system.select_personality(context)
    
    # Get analytics
    analytics = system.get_analytics()
    
    assert analytics["total_selections"] == 3
    assert "personality_distribution" in analytics
    assert "time_distribution" in analytics
    assert "context_patterns" in analytics