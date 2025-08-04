"""
Story Timing Routes - Endpoints for dynamic story timing system
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.core.auth import get_current_user
from app.core.logger import get_logger
from app.services.master_orchestration_agent import MasterOrchestrationAgent, JourneyContext
from app.core.unified_ai_client import get_unified_ai_client

logger = get_logger(__name__)

router = APIRouter()

# Singleton instance
_orchestrator_instance: Optional[MasterOrchestrationAgent] = None


def get_master_orchestrator() -> MasterOrchestrationAgent:
    """Get or create the master orchestrator singleton"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        ai_client = get_unified_ai_client()
        _orchestrator_instance = MasterOrchestrationAgent(ai_client)
    return _orchestrator_instance


@router.post("/check-story-opportunity")
async def check_story_opportunity(
    journey_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    orchestrator: MasterOrchestrationAgent = Depends(get_master_orchestrator),
    db: Session = Depends(get_db)
):
    """
    Check if it's time for a new story based on current journey context.
    
    This endpoint should be called periodically (e.g., every minute) during a journey
    to determine if a story should be triggered.
    """
    try:
        # Build journey context from request data
        journey_context = JourneyContext(
            current_location=journey_data.get("current_location", {"lat": 0, "lng": 0}),
            current_time=datetime.utcnow(),
            journey_stage=journey_data.get("journey_stage", "cruise"),
            passengers=journey_data.get("passengers", [{"user_id": current_user.id}]),
            vehicle_info=journey_data.get("vehicle_info", {}),
            weather=journey_data.get("weather", {}),
            route_info=journey_data.get("route_info", {})
        )
        
        # Check for story opportunity
        should_tell_story = await orchestrator.check_story_opportunity(journey_context)
        
        # Get timing explanation
        explanation = orchestrator.story_timing.get_timing_explanation()
        
        # Get current engagement level
        user_id = current_user.id
        engagement_level = 0.5
        if user_id in orchestrator.engagement_trackers:
            engagement_level = orchestrator.engagement_trackers[user_id].get_current_engagement_level()
        
        return {
            "should_tell_story": should_tell_story,
            "explanation": explanation,
            "engagement_level": engagement_level,
            "last_timing_context": orchestrator.story_timing_state.get('last_timing_context'),
            "stories_told": orchestrator.story_timing_state.get('stories_told_count', 0)
        }
        
    except Exception as e:
        logger.error(f"Error checking story opportunity: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check story opportunity: {str(e)}"
        )


@router.post("/record-story-delivered")
async def record_story_delivered(
    current_user: User = Depends(get_current_user),
    orchestrator: MasterOrchestrationAgent = Depends(get_master_orchestrator),
    db: Session = Depends(get_db)
):
    """Record that a story was delivered to update timing calculations"""
    try:
        orchestrator.record_story_delivered()
        
        return {
            "status": "success",
            "stories_told": orchestrator.story_timing_state.get('stories_told_count', 0),
            "message": "Story delivery recorded"
        }
        
    except Exception as e:
        logger.error(f"Error recording story delivery: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record story delivery: {str(e)}"
        )


@router.post("/record-engagement-event")
async def record_engagement_event(
    event_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    orchestrator: MasterOrchestrationAgent = Depends(get_master_orchestrator),
    db: Session = Depends(get_db)
):
    """Record a passenger engagement event"""
    try:
        from app.services.passenger_engagement_tracker import EngagementEventType
        
        event_type_str = event_data.get("event_type", "").upper()
        event_type = EngagementEventType[event_type_str]
        metadata = event_data.get("metadata", {})
        
        orchestrator.record_engagement_event(
            user_id=current_user.id,
            event_type=event_type,
            metadata=metadata
        )
        
        # Get updated engagement level
        engagement_level = orchestrator.engagement_trackers[current_user.id].get_current_engagement_level()
        
        return {
            "status": "success",
            "event_type": event_type.value,
            "engagement_level": engagement_level,
            "message": "Engagement event recorded"
        }
        
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid event type: {event_data.get('event_type')}"
        )
    except Exception as e:
        logger.error(f"Error recording engagement event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record engagement event: {str(e)}"
        )


@router.get("/timing-status")
async def get_timing_status(
    current_user: User = Depends(get_current_user),
    orchestrator: MasterOrchestrationAgent = Depends(get_master_orchestrator),
    db: Session = Depends(get_db)
):
    """Get current story timing status and configuration"""
    try:
        user_id = current_user.id
        
        # Get engagement status
        engagement_data = None
        if user_id in orchestrator.engagement_trackers:
            tracker = orchestrator.engagement_trackers[user_id]
            engagement_data = tracker.get_state_summary()
        
        # Get timing status
        timing_status = {
            "last_story_time": orchestrator.story_timing_state.get('last_story_time'),
            "stories_told_count": orchestrator.story_timing_state.get('stories_told_count', 0),
            "journey_start_time": orchestrator.story_timing_state.get('journey_start_time'),
            "last_explanation": orchestrator.story_timing.get_timing_explanation()
        }
        
        return {
            "timing_status": timing_status,
            "engagement_data": engagement_data,
            "dynamic_timing_enabled": True
        }
        
    except Exception as e:
        logger.error(f"Error getting timing status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get timing status: {str(e)}"
        )