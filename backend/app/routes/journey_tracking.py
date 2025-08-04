"""
Journey Tracking Routes - Manage active journey monitoring for proactive stories
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.core.auth import get_current_user
from app.core.logger import get_logger
from app.core.cache import cache_manager
from app.services.story_opportunity_scheduler import story_scheduler
from app.schemas.journey_tracking import (
    StartJourneyRequest,
    UpdateLocationRequest,
    RecordEngagementEventRequest,
    JourneyStatusResponse,
    PendingStoryResponse
)

logger = get_logger(__name__)

router = APIRouter()


@router.post("/start-journey", response_model=Dict[str, Any])
async def start_journey_tracking(
    journey_data: StartJourneyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Start tracking a journey for proactive story opportunities.
    
    Call this when a user begins their trip to enable automatic story generation.
    """
    try:
        user_id = str(current_user.id)
        
        # Convert Pydantic models to dict for caching
        journey_context = {
            "user_id": user_id,
            "started_at": datetime.utcnow().isoformat(),
            "current_location": journey_data.current_location.dict(),
            "destination": journey_data.destination.dict() if journey_data.destination else None,
            "journey_stage": "departure",
            "passengers": [p.dict() for p in journey_data.passengers] or [{"user_id": user_id}],
            "vehicle_info": journey_data.vehicle_info.dict() if journey_data.vehicle_info else {},
            "route_info": journey_data.route_info.dict() if journey_data.route_info else {},
            "preferences": journey_data.preferences or {}
        }
        
        # Cache journey context
        await cache_manager.set(
            f"journey_context_{user_id}",
            journey_context,
            ttl=86400  # 24 hours
        )
        
        # Add to active monitoring
        await story_scheduler.add_active_journey(user_id)
        
        logger.info(f"Started journey tracking for user {user_id}")
        
        return {
            "status": "success",
            "message": "Journey tracking started",
            "user_id": user_id,
            "proactive_stories_enabled": True,
            "check_interval_seconds": story_scheduler.check_interval_seconds
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error starting journey tracking: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start journey tracking"
        )


@router.put("/update-location")
async def update_journey_location(
    location_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current location and journey context.
    
    Call this periodically (e.g., every 30-60 seconds) to keep journey context current.
    """
    try:
        user_id = str(current_user.id)
        
        # Get existing journey context
        journey_context = await cache_manager.get(f"journey_context_{user_id}")
        if not journey_context:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active journey found. Call /start-journey first."
            )
        
        # Update context
        journey_context.update({
            "current_location": location_data.get("current_location"),
            "last_update": datetime.utcnow().isoformat(),
            "journey_stage": location_data.get("journey_stage", journey_context.get("journey_stage")),
            "vehicle_info": {
                **journey_context.get("vehicle_info", {}),
                **location_data.get("vehicle_info", {})
            },
            "route_info": {
                **journey_context.get("route_info", {}),
                **location_data.get("route_info", {})
            },
            "weather": location_data.get("weather", {})
        })
        
        # Update cache
        await cache_manager.set(
            f"journey_context_{user_id}",
            journey_context,
            ttl=86400  # 24 hours
        )
        
        # Check if there's a pending story
        pending_story = await cache_manager.get(f"pending_story_{user_id}")
        
        return {
            "status": "success",
            "message": "Location updated",
            "has_pending_story": pending_story is not None,
            "journey_stage": journey_context.get("journey_stage")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating location: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update location: {str(e)}"
        )


@router.post("/end-journey")
async def end_journey_tracking(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    End journey tracking and disable proactive stories.
    
    Call this when the user completes their trip.
    """
    try:
        user_id = str(current_user.id)
        
        # Remove from active monitoring
        story_scheduler.remove_active_journey(user_id)
        
        # Clear journey context
        await cache_manager.delete(f"journey_context_{user_id}")
        await cache_manager.delete(f"pending_story_{user_id}")
        
        logger.info(f"Ended journey tracking for user {user_id}")
        
        return {
            "status": "success",
            "message": "Journey tracking ended",
            "user_id": user_id
        }
        
    except Exception as e:
        logger.error(f"Error ending journey tracking: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to end journey tracking: {str(e)}"
        )


@router.get("/journey-status")
async def get_journey_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current journey tracking status."""
    try:
        user_id = str(current_user.id)
        
        # Check if journey is active
        is_active = story_scheduler.is_journey_active(user_id)
        
        # Get journey context if exists
        journey_context = await cache_manager.get(f"journey_context_{user_id}")
        
        # Check for pending story
        pending_story = await cache_manager.get(f"pending_story_{user_id}")
        
        return {
            "is_active": is_active,
            "journey_context": journey_context,
            "has_pending_story": pending_story is not None,
            "pending_story": pending_story
        }
        
    except Exception as e:
        logger.error(f"Error getting journey status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get journey status: {str(e)}"
        )


@router.get("/check-pending-story")
async def check_pending_story(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if there's a pending story ready to be delivered.
    
    The mobile app should poll this endpoint to know when to trigger a story.
    """
    try:
        user_id = str(current_user.id)
        
        # Check for pending story
        pending_story = await cache_manager.get(f"pending_story_{user_id}")
        
        if pending_story:
            # Clear the pending flag
            await cache_manager.delete(f"pending_story_{user_id}")
            
            return {
                "has_story": True,
                "triggered_at": pending_story.get("triggered_at"),
                "journey_context": pending_story.get("journey_context"),
                "message": "Story opportunity available!"
            }
        
        return {
            "has_story": False,
            "message": "No story pending"
        }
        
    except Exception as e:
        logger.error(f"Error checking pending story: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check pending story: {str(e)}"
        )