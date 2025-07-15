"""
MVP Navigation and Safety Tests
Tests navigation assistance and safety features
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from backend.app.services.navigation_agent import NavigationAgent
from backend.app.services.voice_safety_validator import (
    VoiceSafetyValidator, 
    SafetyContext, 
    SafetyLevel
)
from backend.app.models.user import User


@pytest.mark.mvp
class TestMVPNavigation:
    """Test navigation assistance features"""
    
    @pytest.fixture
    def navigation_agent(self):
        """Create navigation agent with mocked dependencies"""
        mock_ai = Mock()
        mock_ai.generate_response = AsyncMock(
            return_value="Take the next exit in 2 miles for Highway 101 South"
        )
        
        agent = NavigationAgent(mock_ai)
        agent.maps_client = Mock()
        return agent
    
    @pytest.mark.asyncio
    async def test_route_planning(self, navigation_agent):
        """Test: Plan route from origin to destination"""
        # Mock route response
        navigation_agent.maps_client.get_directions = AsyncMock(
            return_value={
                "routes": [{
                    "distance": {"text": "382 miles", "value": 615000},
                    "duration": {"text": "6 hours 15 mins", "value": 22500},
                    "steps": [
                        {
                            "instruction": "Head south on I-5",
                            "distance": {"text": "150 miles"},
                            "duration": {"text": "2 hours 30 mins"}
                        },
                        {
                            "instruction": "Take exit 234 for CA-152 West",
                            "distance": {"text": "45 miles"},
                            "duration": {"text": "50 mins"}
                        }
                    ]
                }]
            }
        )
        
        # Plan route
        route = await navigation_agent.plan_route(
            origin="San Francisco, CA",
            destination="Los Angeles, CA",
            preferences={"avoid": "tolls"}
        )
        
        # Verify
        assert route is not None
        assert route["distance_miles"] == 382
        assert route["duration_hours"] == 6.25
        assert len(route["steps"]) >= 2
    
    @pytest.mark.asyncio
    async def test_real_time_navigation(self, navigation_agent):
        """Test: Provide real-time navigation guidance"""
        # Current location and route
        current_location = {"lat": 37.7749, "lng": -122.4194}
        
        # Mock next instruction
        navigation_agent.get_next_instruction = AsyncMock(
            return_value={
                "instruction": "In 800 feet, turn right onto Market Street",
                "distance_to_turn": 0.15,  # miles
                "time_to_turn": 30  # seconds
            }
        )
        
        # Get navigation guidance
        guidance = await navigation_agent.get_navigation_guidance(
            current_location,
            speed_mph=25
        )
        
        # Verify
        assert guidance is not None
        assert "turn right" in guidance["instruction"].lower()
        assert guidance["distance_to_turn"] < 0.2  # Less than 0.2 miles
    
    @pytest.mark.asyncio
    async def test_traffic_aware_routing(self, navigation_agent):
        """Test: Adjust route based on traffic conditions"""
        # Mock traffic data
        navigation_agent.maps_client.get_traffic = AsyncMock(
            return_value={
                "congestion_level": "heavy",
                "delay_minutes": 25,
                "incidents": [{
                    "type": "accident",
                    "location": {"lat": 37.5, "lng": -122.3},
                    "severity": "major",
                    "description": "Multi-vehicle accident blocking 2 lanes"
                }]
            }
        )
        
        # Check for better route
        alternative = await navigation_agent.find_alternative_route(
            current_route_id="route1",
            reason="heavy_traffic"
        )
        
        # Verify traffic awareness
        assert alternative is not None
        assert alternative.get("saves_time", False) or alternative.get("avoids_traffic", False)
    
    @pytest.mark.asyncio
    async def test_poi_search_along_route(self, navigation_agent):
        """Test: Find points of interest along route"""
        # Mock POI search
        navigation_agent.maps_client.search_along_route = AsyncMock(
            return_value=[
                {
                    "name": "Shell Gas Station",
                    "type": "gas_station",
                    "distance_miles": 2.3,
                    "detour_minutes": 3,
                    "price_info": {"regular": "$4.29"}
                },
                {
                    "name": "Chevron",
                    "type": "gas_station", 
                    "distance_miles": 5.1,
                    "detour_minutes": 5,
                    "price_info": {"regular": "$4.19"}
                }
            ]
        )
        
        # Search for gas stations
        pois = await navigation_agent.find_poi_along_route(
            poi_type="gas_station",
            max_detour_minutes=10
        )
        
        # Verify
        assert len(pois) >= 2
        assert all(poi["type"] == "gas_station" for poi in pois)
        assert all(poi["detour_minutes"] <= 10 for poi in pois)


@pytest.mark.mvp
class TestMVPSafetyFeatures:
    """Test safety-related features"""
    
    @pytest.fixture
    def safety_validator(self):
        """Create safety validator"""
        return VoiceSafetyValidator()
    
    def test_speed_based_content_control(self, safety_validator):
        """Test: Content adjusts based on speed"""
        # Low speed - full content
        low_speed_context = SafetyContext(
            safety_level=SafetyLevel.NORMAL,
            speed_mph=25,
            is_navigating=False
        )
        safety_validator.update_context(low_speed_context)
        
        should_pause, _ = safety_validator.should_auto_pause()
        assert should_pause is False
        
        # High speed - may pause
        high_speed_context = SafetyContext(
            safety_level=SafetyLevel.HIGHWAY,
            speed_mph=75,
            is_navigating=True,
            traffic_density="heavy"
        )
        safety_validator.update_context(high_speed_context)
        
        # Heavy traffic at high speed should affect content
        content_level = safety_validator.get_content_complexity_level()
        assert content_level in ["simple", "none"]
    
    def test_maneuver_based_pausing(self, safety_validator):
        """Test: Pause during complex maneuvers"""
        # Approaching complex maneuver
        maneuver_context = SafetyContext(
            safety_level=SafetyLevel.CRITICAL,
            speed_mph=45,
            is_navigating=True,
            upcoming_maneuver_distance=0.1,  # 0.1 miles away
            traffic_density="moderate"
        )
        
        safety_validator.update_context(maneuver_context)
        should_pause, reason = safety_validator.should_auto_pause()
        
        # Should pause for nearby maneuver
        assert should_pause is True
        assert "maneuver" in reason.lower() or "critical" in reason.lower()
    
    def test_weather_impact_on_safety(self, safety_validator):
        """Test: Weather conditions affect safety level"""
        # Bad weather context
        weather_context = SafetyContext(
            safety_level=SafetyLevel.NORMAL,
            speed_mph=55,
            is_navigating=True,
            weather_condition="heavy_rain",
            visibility="poor"
        )
        
        safety_validator.update_context(weather_context)
        
        # Should increase caution in bad weather
        adjusted_level = safety_validator.get_adjusted_safety_level()
        assert adjusted_level.value > SafetyLevel.NORMAL.value
    
    def test_emergency_content_override(self, safety_validator):
        """Test: Emergency information overrides all content"""
        # Emergency context
        emergency_context = SafetyContext(
            safety_level=SafetyLevel.EMERGENCY,
            speed_mph=0,
            is_navigating=False,
            emergency_type="medical"
        )
        
        safety_validator.update_context(emergency_context)
        
        # Should allow emergency content only
        allowed_content = safety_validator.get_allowed_content_types()
        assert allowed_content == ["emergency"]
        
        # Should not pause emergency content
        should_pause, _ = safety_validator.should_auto_pause()
        assert should_pause is False


@pytest.mark.mvp
class TestMVPRouteMonitoring:
    """Test route monitoring and adjustments"""
    
    @pytest.mark.asyncio
    async def test_off_route_detection(self):
        """Test: Detect when user goes off route"""
        mock_ai = Mock()
        nav_agent = NavigationAgent(mock_ai)
        
        # Current location off the planned route
        current_location = {"lat": 37.7749, "lng": -122.4194}
        planned_route = {
            "points": [
                {"lat": 37.7849, "lng": -122.4094},
                {"lat": 37.7949, "lng": -122.3994}
            ]
        }
        
        # Check if off route
        is_off_route = await nav_agent.check_off_route(
            current_location,
            planned_route,
            threshold_meters=500
        )
        
        # Should detect off route
        assert is_off_route is True
    
    @pytest.mark.asyncio
    async def test_automatic_rerouting(self):
        """Test: Automatically reroute when off course"""
        mock_ai = Mock()
        nav_agent = NavigationAgent(mock_ai)
        
        # Mock rerouting
        nav_agent.maps_client = Mock()
        nav_agent.maps_client.get_directions = AsyncMock(
            return_value={
                "routes": [{
                    "distance": {"value": 5000},
                    "duration": {"value": 600},
                    "steps": [{"instruction": "Make a U-turn when possible"}]
                }]
            }
        )
        
        # Trigger reroute
        new_route = await nav_agent.reroute_from_current_location(
            current_location={"lat": 37.7749, "lng": -122.4194},
            destination="Golden Gate Bridge"
        )
        
        # Verify new route
        assert new_route is not None
        assert len(new_route["steps"]) > 0
        assert "u-turn" in new_route["steps"][0]["instruction"].lower()
    
    @pytest.mark.asyncio
    async def test_eta_updates(self):
        """Test: Update ETA based on current progress"""
        mock_ai = Mock()
        nav_agent = NavigationAgent(mock_ai)
        
        # Initial route with ETA
        route = {
            "total_distance": 100,  # miles
            "distance_remaining": 75,  # miles  
            "original_eta": datetime.now().replace(hour=14, minute=30),
            "current_speed": 60  # mph
        }
        
        # Calculate updated ETA
        updated_eta = await nav_agent.calculate_updated_eta(route)
        
        # Verify ETA calculation
        assert updated_eta is not None
        # 75 miles at 60 mph = 1.25 hours
        expected_minutes = 75
        assert abs((updated_eta - datetime.now()).total_seconds() / 60 - expected_minutes) < 5


@pytest.mark.mvp
class TestMVPVoiceNavigation:
    """Test voice-based navigation features"""
    
    @pytest.mark.asyncio
    async def test_voice_navigation_commands(self):
        """Test: Process voice navigation commands"""
        from backend.app.services.voice_services import VoiceService
        
        voice_service = VoiceService()
        voice_service.speech_client = Mock()
        
        # Mock voice recognition
        voice_service.speech_client.recognize.return_value = Mock(
            results=[Mock(alternatives=[Mock(transcript="Navigate to the nearest gas station")])]
        )
        
        # Process command
        result = await voice_service.process_voice_command(b'audio_data')
        
        # Verify command recognized
        assert result["status"] == "success"
        assert "gas station" in result["text"].lower()
        assert "navigate" in result["text"].lower()
    
    @pytest.mark.asyncio
    async def test_navigation_voice_prompts(self):
        """Test: Generate voice prompts for navigation"""
        from backend.app.services.tts_service import TTSService
        
        tts_service = TTSService()
        tts_service.tts_client = Mock()
        
        # Mock TTS generation
        tts_service.tts_client.synthesize_speech.return_value = Mock(
            audio_content=b'turn_right_audio'
        )
        
        # Generate navigation prompt
        audio = await tts_service.generate_navigation_prompt(
            "In 500 feet, turn right onto Main Street",
            voice="concise_navigator"
        )
        
        # Verify audio generated
        assert audio is not None
        assert len(audio) > 0
    
    @pytest.mark.asyncio
    async def test_multi_modal_navigation(self):
        """Test: Combine voice and visual navigation"""
        mock_ai = Mock()
        nav_agent = NavigationAgent(mock_ai)
        
        # Get multi-modal guidance
        guidance = await nav_agent.get_multimodal_guidance(
            instruction="Turn right at the next light",
            visual_enabled=True,
            voice_enabled=True
        )
        
        # Verify both modes
        assert guidance["voice_prompt"] is not None
        assert guidance["visual_instruction"] is not None
        assert guidance["visual_instruction"]["arrow"] == "right"
        assert guidance["visual_instruction"]["distance"] == "next light"


@pytest.mark.mvp
class TestMVPEmergencyFeatures:
    """Test emergency and safety features"""
    
    @pytest.mark.asyncio
    async def test_emergency_services_location(self):
        """Test: Find nearest emergency services"""
        mock_ai = Mock()
        nav_agent = NavigationAgent(mock_ai)
        
        # Mock emergency services search
        nav_agent.maps_client = Mock()
        nav_agent.maps_client.search_nearby = AsyncMock(
            return_value=[
                {
                    "name": "SF General Hospital",
                    "type": "hospital",
                    "distance_miles": 2.3,
                    "phone": "415-555-1234",
                    "address": "1001 Potrero Ave"
                },
                {
                    "name": "UCSF Medical Center",
                    "type": "hospital",
                    "distance_miles": 3.1,
                    "phone": "415-555-5678",
                    "address": "505 Parnassus Ave"
                }
            ]
        )
        
        # Find nearest hospital
        emergency_locations = await nav_agent.find_emergency_services(
            service_type="hospital",
            current_location={"lat": 37.7749, "lng": -122.4194}
        )
        
        # Verify
        assert len(emergency_locations) >= 1
        assert emergency_locations[0]["type"] == "hospital"
        assert emergency_locations[0]["distance_miles"] < 5
        assert "phone" in emergency_locations[0]
    
    @pytest.mark.asyncio
    async def test_emergency_route_priority(self):
        """Test: Emergency routes get priority routing"""
        mock_ai = Mock()
        nav_agent = NavigationAgent(mock_ai)
        
        # Mock emergency routing
        nav_agent.maps_client = Mock()
        nav_agent.maps_client.get_directions = AsyncMock(
            return_value={
                "routes": [{
                    "distance": {"value": 3700},
                    "duration": {"value": 420},  # 7 minutes
                    "priority": "emergency",
                    "steps": [
                        {"instruction": "Head north on Mission St"},
                        {"instruction": "Turn right on 16th St"},
                        {"instruction": "Arrive at SF General Hospital"}
                    ]
                }]
            }
        )
        
        # Get emergency route
        emergency_route = await nav_agent.get_emergency_route(
            destination="SF General Hospital",
            emergency_type="medical"
        )
        
        # Verify fast routing
        assert emergency_route is not None
        assert emergency_route["duration_minutes"] < 10
        assert emergency_route["priority"] == "emergency"