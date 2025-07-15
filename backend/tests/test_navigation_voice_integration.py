"""
Test script for navigation voice integration
"""

import asyncio
import logging
from datetime import datetime

# Add the backend directory to the Python path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.navigation_voice_service import (
    NavigationVoiceService, 
    NavigationContext,
    NavigationPriority
)
from app.models.directions import Route, RouteLeg, RouteStep, Distance, Duration, Location

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_test_route():
    """Create a test route with sample data"""
    return Route(
        summary="Test route via I-95",
        bounds={"northeast": {"lat": 40.7128, "lng": -74.0060}, "southwest": {"lat": 40.7000, "lng": -74.0200}},
        copyrights="Map data ©2023 Google",
        legs=[
            RouteLeg(
                distance=Distance(text="5.2 miles", value=8368),
                duration=Duration(text="12 mins", value=720),
                start_location=Location(lat=40.7128, lng=-74.0060),
                end_location=Location(lat=40.7589, lng=-73.9851),
                start_address="New York, NY, USA",
                end_address="Times Square, NY, USA",
                steps=[
                    RouteStep(
                        distance=Distance(text="0.3 miles", value=483),
                        duration=Duration(text="1 min", value=60),
                        instructions="Head north on Broadway toward W 42nd St",
                        maneuver="turn-right",
                        coordinates=[[40.7128, -74.0060], [40.7150, -74.0058]],
                        travel_mode="driving"
                    ),
                    RouteStep(
                        distance=Distance(text="2.1 miles", value=3379),
                        duration=Duration(text="5 mins", value=300),
                        instructions="Take exit 16E to merge onto I-495 E toward Lincoln Tunnel",
                        maneuver="exit",
                        coordinates=[[40.7150, -74.0058], [40.7400, -74.0040]],
                        travel_mode="driving"
                    ),
                    RouteStep(
                        distance=Distance(text="1.5 miles", value=2414),
                        duration=Duration(text="4 mins", value=240),
                        instructions="Turn left onto 6th Ave",
                        maneuver="turn-left",
                        coordinates=[[40.7400, -74.0040], [40.7550, -73.9900]],
                        travel_mode="driving"
                    )
                ]
            )
        ],
        overview_coordinates=[[40.7128, -74.0060], [40.7589, -73.9851]]
    )


async def test_navigation_voice_service():
    """Test the navigation voice service"""
    logger.info("Starting navigation voice service test...")
    
    # Create service instance
    nav_service = NavigationVoiceService()
    
    # Create test route
    test_route = create_test_route()
    current_location = {"lat": 40.7128, "lng": -74.0060}
    journey_context = {
        "user_id": "test_user",
        "trip_id": "test_trip",
        "preferences": {
            "navigation_verbosity": "detailed",
            "audio_priority": "safety_first"
        }
    }
    
    # Process route for voice
    logger.info("Processing route for voice navigation...")
    voice_data = await nav_service.process_route_for_voice(
        test_route,
        current_location,
        journey_context
    )
    
    logger.info(f"Route processed successfully!")
    logger.info(f"Route ID: {voice_data['route_id']}")
    logger.info(f"Total instruction templates: {len(voice_data['instruction_templates'])}")
    logger.info(f"Route characteristics: {voice_data['route_characteristics']}")
    
    # Test getting current instruction
    nav_context = NavigationContext(
        current_step_index=0,
        distance_to_next_maneuver=1500,  # 1.5km away
        time_to_next_maneuver=120,  # 2 minutes
        current_speed=50,  # 50 km/h
        is_on_highway=False,
        approaching_complex_intersection=False,
        story_playing=True,
        last_instruction_time=None
    )
    
    orchestration_state = {
        'route_id': voice_data['route_id'],
        'story_playing': True,
        'audio_priority': 'balanced'
    }
    
    logger.info("\nGetting navigation instruction for current position...")
    instruction = await nav_service.get_current_instruction(nav_context, orchestration_state)
    
    if instruction:
        logger.info(f"Instruction: {instruction.text}")
        logger.info(f"Priority: {instruction.priority.value}")
        logger.info(f"Timing: {instruction.timing}")
        logger.info(f"Requires story pause: {instruction.requires_story_pause}")
        
        # Test voice generation (without actual TTS)
        logger.info("\nTesting voice generation...")
        try:
            voice_audio = await nav_service.generate_voice_audio(instruction)
            logger.info(f"Voice audio would be generated with URL: {voice_audio.get('audio_url', 'N/A')}")
            logger.info(f"Duration: {voice_audio.get('duration', 0)} seconds")
        except Exception as e:
            logger.warning(f"Voice generation skipped (expected without TTS setup): {e}")
    else:
        logger.info("No instruction needed at current position")
    
    # Test different distances
    logger.info("\nTesting instructions at different distances...")
    test_distances = [3000, 1500, 700, 150, 40]  # meters
    
    for distance in test_distances:
        nav_context.distance_to_next_maneuver = distance
        instruction = await nav_service.get_current_instruction(nav_context, orchestration_state)
        if instruction:
            logger.info(f"At {distance}m: {instruction.timing} - {instruction.text}")
        else:
            logger.info(f"At {distance}m: No instruction")
    
    logger.info("\nNavigation voice service test completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_navigation_voice_service())