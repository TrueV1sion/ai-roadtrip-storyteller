"""
Navigation Routes - Turn-by-turn voice navigation endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Body
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from ..schemas.navigation import (
    NavigationStartRequest,
    NavigationUpdateRequest,
    NavigationInstructionResponse,
    NavigationStateResponse
)
from ..services.master_orchestration_agent import MasterOrchestrationAgent
from ..services.navigation_voice_service import NavigationContext, navigation_voice_service
from ..core.auth import get_current_user
from ..core.unified_ai_client import UnifiedAIClient
from ..models.user import User
from ..db.base import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter()

# Global orchestrator instance (in production, this would be managed differently)
_orchestrator_instance = None

def get_master_orchestrator() -> MasterOrchestrationAgent:
    """Get or create the master orchestrator instance."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        ai_client = UnifiedAIClient()
        _orchestrator_instance = MasterOrchestrationAgent(ai_client)
    return _orchestrator_instance


@router.post("/navigation/start", response_model=Dict[str, Any])
async def start_navigation(
    request: NavigationStartRequest,
    current_user: User = Depends(get_current_user),
    orchestrator: MasterOrchestrationAgent = Depends(get_master_orchestrator)
):
    """
    Start turn-by-turn voice navigation for a route.
    
    This endpoint:
    - Processes the route for voice instructions
    - Initializes navigation state
    - Returns coordination rules for audio orchestration
    """
    try:
        # Build journey context
        journey_context = {
            'current_location': request.current_location.dict(),
            'destination': request.destination.dict(),
            'preferences': current_user.preferences,
            'navigation_preferences': request.navigation_preferences or {}
        }
        
        # Start navigation voice
        result = await orchestrator.start_navigation_voice(
            request.route.dict(),
            journey_context
        )
        
        if result['status'] != 'success':
            raise HTTPException(status_code=400, detail=result.get('message', 'Failed to start navigation'))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting navigation: {e}")
        raise HTTPException(status_code=500, detail="Failed to start navigation")


@router.post("/navigation/update", response_model=NavigationInstructionResponse)
async def update_navigation(
    request: NavigationUpdateRequest,
    current_user: User = Depends(get_current_user),
    orchestrator: MasterOrchestrationAgent = Depends(get_master_orchestrator)
):
    """
    Get navigation instruction based on current position.
    
    This endpoint:
    - Checks if navigation instruction is needed
    - Coordinates with audio playback
    - Returns voice instruction and orchestration actions
    """
    try:
        # Build navigation context
        navigation_context = {
            'navigation_state': NavigationContext(
                current_step_index=request.current_step_index,
                distance_to_next_maneuver=request.distance_to_next_maneuver,
                time_to_next_maneuver=request.time_to_next_maneuver,
                current_speed=request.current_speed,
                is_on_highway=request.is_on_highway,
                approaching_complex_intersection=request.approaching_complex_intersection,
                story_playing=request.story_playing,
                last_instruction_time=request.last_instruction_time
            ),
            'story_playing': request.story_playing,
            'audio_priority': request.audio_priority or 'balanced',
            'user_preference_voice': current_user.preferences.get('navigation_voice')
        }
        
        # Get navigation instruction
        result = await orchestrator.coordinate_navigation_voice(navigation_context)
        
        if result['status'] == 'no_instruction':
            return NavigationInstructionResponse(
                has_instruction=False,
                next_check_seconds=30
            )
        elif result['status'] == 'error':
            raise HTTPException(status_code=500, detail=result.get('message', 'Navigation update failed'))
        
        # Format response
        instruction = result['instruction']
        audio = result['audio']
        orchestration = result['orchestration']
        
        return NavigationInstructionResponse(
            has_instruction=True,
            instruction={
                'text': instruction.text,
                'priority': instruction.priority.value,
                'timing': instruction.timing,
                'maneuver_type': instruction.maneuver_type.value if instruction.maneuver_type else None,
                'street_name': instruction.street_name,
                'exit_number': instruction.exit_number
            },
            audio_url=audio['audio_url'],
            audio_duration=audio['duration'],
            orchestration_action=orchestration,
            next_check_seconds=result['next_check_seconds']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating navigation: {e}")
        raise HTTPException(status_code=500, detail="Failed to update navigation")


@router.get("/navigation/status", response_model=NavigationStateResponse)
async def get_navigation_status(
    current_user: User = Depends(get_current_user),
    orchestrator: MasterOrchestrationAgent = Depends(get_master_orchestrator)
):
    """Get current navigation state."""
    try:
        nav_state = orchestrator.navigation_voice_state
        
        return NavigationStateResponse(
            active=nav_state['voice_navigation_active'],
            route_id=nav_state['active_route_id'],
            current_instruction_index=nav_state['current_instruction_index'],
            last_instruction_time=nav_state['last_instruction_time']
        )
        
    except Exception as e:
        logger.error(f"Error getting navigation status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get navigation status")


@router.post("/navigation/stop")
async def stop_navigation(
    current_user: User = Depends(get_current_user),
    orchestrator: MasterOrchestrationAgent = Depends(get_master_orchestrator)
):
    """Stop turn-by-turn voice navigation."""
    try:
        orchestrator.stop_navigation_voice()
        return {"status": "success", "message": "Navigation stopped"}
        
    except Exception as e:
        logger.error(f"Error stopping navigation: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop navigation")


@router.post("/navigation/background-update")
async def update_background_position(
    request: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update position from background task.
    Lightweight endpoint for frequent position updates.
    """
    try:
        position = request.get('position', {})
        route_id = request.get('route_id')
        timestamp = request.get('timestamp')
        
        # Store position update (could be used for analytics/tracking)
        # For now, just acknowledge receipt
        logger.debug(f"Background position update for route {route_id}: {position}")
        
        return {
            "status": "success",
            "timestamp": timestamp
        }
        
    except Exception as e:
        logger.error(f"Error in background update: {e}")
        # Don't raise exception for background updates
        return {"status": "error", "message": str(e)}


@router.post("/navigation/voice/initialize")
async def initialize_voice_navigation(
    request: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user)
):
    """
    Initialize voice navigation for a route.
    Processes route data and prepares voice instruction templates.
    """
    try:
        route_data = request.get('route_data')
        current_location = request.get('current_location')
        journey_context = request.get('journey_context', {})
        
        # Process route for voice navigation
        voice_data = await navigation_voice_service.process_route_for_voice(
            route_data,
            current_location,
            journey_context
        )
        
        return {
            "status": "success",
            "route_id": voice_data['route_id'],
            "total_instructions": len(voice_data['instruction_templates']),
            "coordination_rules": voice_data['coordination_rules']
        }
        
    except Exception as e:
        logger.error(f"Error initializing voice navigation: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialize voice navigation")


@router.post("/navigation/voice/instruction")
async def get_voice_instruction(
    request: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user)
):
    """
    Get current navigation voice instruction based on position and context.
    Returns instruction with audio URL and spatial audio configuration.
    """
    try:
        route_id = request.get('route_id')
        nav_context = request.get('navigation_context', {})
        orch_state = request.get('orchestration_state', {})
        
        # Create NavigationContext from request
        navigation_context = NavigationContext(
            current_step_index=nav_context.get('current_step_index', 0),
            distance_to_next_maneuver=nav_context.get('distance_to_next_maneuver', 0),
            time_to_next_maneuver=nav_context.get('time_to_next_maneuver', 0),
            current_speed=nav_context.get('current_speed', 0),
            is_on_highway=nav_context.get('is_on_highway', False),
            approaching_complex_intersection=nav_context.get('approaching_complex_intersection', False),
            story_playing=nav_context.get('story_playing', False),
            last_instruction_time=datetime.fromisoformat(nav_context['last_instruction_time']) if nav_context.get('last_instruction_time') else None
        )
        
        # Add route_id to orchestration state
        orch_state['route_id'] = route_id
        
        # Get current instruction
        instruction = await navigation_voice_service.get_current_instruction(
            navigation_context,
            orch_state
        )
        
        if instruction:
            # Generate voice audio
            audio_data = await navigation_voice_service.generate_voice_audio(instruction)
            
            # Prepare spatial audio config based on maneuver
            spatial_config = {
                "position": {"x": 0, "y": 0, "z": 2.0},
                "environment": "car_interior",
                "distanceToManeuver": navigation_context.distance_to_next_maneuver
            }
            
            if instruction.audio_cues.get('spatial_position') == 'left':
                spatial_config["position"]["x"] = -2.0
            elif instruction.audio_cues.get('spatial_position') == 'right':
                spatial_config["position"]["x"] = 2.0
            
            return {
                "has_instruction": True,
                "instruction": {
                    "text": instruction.text,
                    "priority": instruction.priority.value,
                    "timing": instruction.timing,
                    "maneuver_type": instruction.maneuver_type.value if instruction.maneuver_type else None,
                    "street_name": instruction.street_name,
                    "exit_number": instruction.exit_number,
                    "audio_cues": instruction.audio_cues,
                    "requires_story_pause": instruction.requires_story_pause,
                    "estimated_duration": instruction.estimated_duration
                },
                "audio_url": audio_data['audio_url'],
                "next_check_seconds": 2,
                "spatial_audio_config": spatial_config
            }
        else:
            return {
                "has_instruction": False,
                "next_check_seconds": 5
            }
            
    except Exception as e:
        logger.error(f"Error getting voice instruction: {e}")
        return {
            "has_instruction": False,
            "next_check_seconds": 10,
            "error": str(e)
        }


@router.post("/navigation/check-instruction")
async def check_navigation_instruction(
    request: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    orchestrator: MasterOrchestrationAgent = Depends(get_master_orchestrator)
):
    """
    Quick check if navigation instruction is needed.
    Used by background tasks to determine if notification is needed.
    """
    try:
        # Simplified check - could be optimized for background use
        current_location = request.get('current_location')
        route_id = request.get('route_id')
        
        if not orchestrator.navigation_voice_state['active_route_id'] == route_id:
            return NavigationInstructionResponse(
                has_instruction=False,
                next_check_seconds=30
            )
        
        # TODO: Implement simplified distance check
        # For now, return no instruction
        return NavigationInstructionResponse(
            has_instruction=False,
            next_check_seconds=10
        )
        
    except Exception as e:
        logger.error(f"Error checking instruction: {e}")
        return NavigationInstructionResponse(
            has_instruction=False,
            next_check_seconds=30
        )


@router.post("/navigation/simulate-position")
async def simulate_position_update(
    position: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    orchestrator: MasterOrchestrationAgent = Depends(get_master_orchestrator)
):
    """
    Simulate position update for testing navigation voice.
    Only available in development mode.
    """
    import os
    if os.getenv("ENVIRONMENT") != "development":
        raise HTTPException(status_code=403, detail="This endpoint is only available in development")
    
    try:
        # Build navigation update request
        update_request = NavigationUpdateRequest(
            current_location=position['current_location'],
            current_step_index=position.get('current_step_index', 0),
            distance_to_next_maneuver=position['distance_to_next_maneuver'],
            time_to_next_maneuver=position.get('time_to_next_maneuver', 60),
            current_speed=position.get('current_speed', 50),
            is_on_highway=position.get('is_on_highway', False),
            approaching_complex_intersection=position.get('approaching_complex_intersection', False),
            story_playing=position.get('story_playing', False),
            audio_priority=position.get('audio_priority', 'balanced')
        )
        
        # Process as normal update
        return await update_navigation(update_request, current_user, orchestrator)
        
    except Exception as e:
        logger.error(f"Error simulating position: {e}")
        raise HTTPException(status_code=500, detail="Failed to simulate position")