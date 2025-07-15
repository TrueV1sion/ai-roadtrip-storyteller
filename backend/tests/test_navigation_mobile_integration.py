"""
Test the complete navigation voice integration with mobile
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from app.services.navigation_voice_service import (
    NavigationVoiceService,
    NavigationContext,
    NavigationPriority
)
from app.services.master_orchestration_agent import MasterOrchestrationAgent
from app.models.directions import Route, RouteLeg, RouteStep, Distance, Duration, Location


@pytest.fixture
def mock_route():
    """Create a mock route for testing"""
    return Route(
        summary="Test route via I-95",
        bounds={},
        copyrights="Test",
        legs=[
            RouteLeg(
                distance=Distance(text="10 miles", value=16093),
                duration=Duration(text="15 mins", value=900),
                start_location=Location(lat=40.7128, lng=-74.0060),
                end_location=Location(lat=40.7589, lng=-73.9851),
                start_address="Start",
                end_address="End",
                steps=[
                    RouteStep(
                        distance=Distance(text="2 miles", value=3218),
                        duration=Duration(text="3 mins", value=180),
                        instructions="Turn right onto Broadway",
                        maneuver="turn-right",
                        coordinates=[],
                        travel_mode="driving"
                    ),
                    RouteStep(
                        distance=Distance(text="5 miles", value=8046),
                        duration=Duration(text="7 mins", value=420),
                        instructions="Take exit 16E for I-495 E",
                        maneuver="exit",
                        coordinates=[],
                        travel_mode="driving"
                    )
                ]
            )
        ],
        overview_coordinates=[]
    )


@pytest.fixture
def navigation_context():
    """Create a navigation context for testing"""
    return NavigationContext(
        current_step_index=0,
        distance_to_next_maneuver=1500,  # 1.5km
        time_to_next_maneuver=120,  # 2 minutes
        current_speed=50,  # 50 km/h
        is_on_highway=False,
        approaching_complex_intersection=False,
        story_playing=True,
        last_instruction_time=None
    )


@pytest.mark.asyncio
async def test_navigation_voice_integration(mock_route, navigation_context):
    """Test the full navigation voice flow"""
    # Create services
    nav_service = NavigationVoiceService()
    
    # Mock TTS service
    with patch.object(nav_service.tts_service, 'synthesize_and_upload') as mock_tts:
        mock_tts.return_value = "https://storage.googleapis.com/audio/nav-instruction.mp3"
        
        # Process route for voice
        voice_data = await nav_service.process_route_for_voice(
            mock_route,
            {"lat": 40.7128, "lng": -74.0060},
            {"user_id": "test", "preferences": {}}
        )
        
        assert voice_data['route_id'] is not None
        assert len(voice_data['instruction_templates']) == 2  # Two steps
        assert voice_data['route_characteristics']['total_distance_km'] == pytest.approx(16.093, 0.1)
        
        # Get current instruction
        orchestration_state = {
            'route_id': voice_data['route_id'],
            'story_playing': True,
            'audio_priority': 'balanced'
        }
        
        instruction = await nav_service.get_current_instruction(
            navigation_context,
            orchestration_state
        )
        
        assert instruction is not None
        assert instruction.timing == "reminder"  # At 1.5km should be reminder
        assert instruction.priority == NavigationPriority.HIGH
        assert instruction.requires_story_pause is True
        assert "Turn right" in instruction.text
        assert "Broadway" in instruction.text


@pytest.mark.asyncio
async def test_distance_based_instruction_selection(mock_route):
    """Test that correct instructions are selected based on distance"""
    nav_service = NavigationVoiceService()
    
    with patch.object(nav_service.tts_service, 'synthesize_and_upload') as mock_tts:
        mock_tts.return_value = "https://test-audio.mp3"
        
        voice_data = await nav_service.process_route_for_voice(
            mock_route,
            {"lat": 40.7128, "lng": -74.0060},
            {}
        )
        
        # Test different distances
        test_cases = [
            (3000, "initial"),     # 3km - initial announcement
            (1500, "reminder"),    # 1.5km - reminder
            (700, "prepare"),      # 700m - prepare
            (150, "prepare"),      # 150m - still prepare
            (40, "immediate"),     # 40m - immediate
        ]
        
        for distance, expected_timing in test_cases:
            context = NavigationContext(
                current_step_index=0,
                distance_to_next_maneuver=distance,
                time_to_next_maneuver=distance / 13.89,  # ~50km/h
                current_speed=50,
                is_on_highway=False,
                approaching_complex_intersection=False,
                story_playing=False,
                last_instruction_time=None
            )
            
            instruction = await nav_service.get_current_instruction(
                context,
                {'route_id': voice_data['route_id']}
            )
            
            if instruction:
                assert instruction.timing == expected_timing, f"At {distance}m expected {expected_timing}, got {instruction.timing}"


@pytest.mark.asyncio
async def test_orchestration_integration():
    """Test integration with master orchestration agent"""
    # Mock AI client
    mock_ai_client = Mock()
    orchestrator = MasterOrchestrationAgent(mock_ai_client)
    
    # Mock route
    mock_route = {
        "legs": [{
            "steps": [{
                "distance": {"value": 1000},
                "duration": {"value": 60},
                "instructions": "Turn left onto Main St",
                "maneuver": "turn-left"
            }]
        }]
    }
    
    # Start navigation
    result = await orchestrator.start_navigation_voice(
        mock_route,
        {
            "current_location": {"lat": 40.7128, "lng": -74.0060},
            "preferences": {}
        }
    )
    
    assert result['status'] == 'success'
    assert result['route_id'] is not None
    assert orchestrator.navigation_voice_state['voice_navigation_active'] is True
    
    # Test coordination
    nav_context = {
        'navigation_state': NavigationContext(
            current_step_index=0,
            distance_to_next_maneuver=150,  # Prepare distance
            time_to_next_maneuver=10,
            current_speed=50,
            is_on_highway=False,
            approaching_complex_intersection=False,
            story_playing=True,
            last_instruction_time=None
        ),
        'story_playing': True,
        'audio_priority': 'safety_first'
    }
    
    with patch('app.services.navigation_voice_service.navigation_voice_service.get_current_instruction') as mock_get:
        mock_instruction = Mock()
        mock_instruction.priority.value = 'critical'
        mock_instruction.text = "Turn left now"
        mock_instruction.timing = "immediate"
        mock_get.return_value = mock_instruction
        
        with patch('app.services.navigation_voice_service.navigation_voice_service.generate_voice_audio') as mock_audio:
            mock_audio.return_value = {
                'audio_url': 'https://test.mp3',
                'duration': 3,
                'metadata': {'priority': 'critical'}
            }
            
            coord_result = await orchestrator.coordinate_navigation_voice(nav_context)
            
            assert coord_result['status'] == 'success'
            assert coord_result['orchestration']['action'] == 'interrupt_all'
            assert coord_result['next_check_seconds'] == 5  # Immediate instruction check interval


@pytest.mark.asyncio
async def test_audio_priority_handling():
    """Test that audio priorities are handled correctly"""
    nav_service = NavigationVoiceService()
    
    # Test priority assignment
    test_maneuvers = [
        ("turn-left", "immediate", NavigationPriority.CRITICAL),
        ("turn-right", "prepare", NavigationPriority.CRITICAL),
        ("exit", "reminder", NavigationPriority.HIGH),
        ("straight", "initial", NavigationPriority.MEDIUM),
    ]
    
    for maneuver, timing, expected_priority in test_maneuvers:
        step = RouteStep(
            distance=Distance(text="1 mi", value=1609),
            duration=Duration(text="2 min", value=120),
            instructions=f"Test {maneuver}",
            maneuver=maneuver,
            coordinates=[],
            travel_mode="driving"
        )
        
        instructions = await nav_service._generate_step_instructions(
            step, None, {'highway_percentage': 0}
        )
        
        timing_instruction = next((i for i in instructions if i.timing == timing), None)
        assert timing_instruction is not None
        assert timing_instruction.priority == expected_priority


@pytest.mark.asyncio
async def test_ssml_generation():
    """Test SSML markup generation for navigation"""
    nav_service = NavigationVoiceService()
    
    # Create instruction
    from app.services.navigation_voice_service import NavigationInstruction, ManeuverType
    
    instruction = NavigationInstruction(
        text="Turn left onto Main Street in 500 feet",
        priority=NavigationPriority.HIGH,
        timing="prepare",
        maneuver_type=ManeuverType.TURN_LEFT,
        street_name="Main Street",
        exit_number=None,
        audio_cues={},
        requires_story_pause=True,
        estimated_duration=3.0
    )
    
    ssml = nav_service._create_ssml_instruction(instruction)
    
    assert "<speak>" in ssml
    assert "</speak>" in ssml
    assert '<emphasis level="strong">left</emphasis>' in ssml
    assert '<break time="200ms"/>' in ssml  # Before numbers
    assert "500" in ssml


if __name__ == "__main__":
    asyncio.run(test_navigation_voice_integration(None, None))