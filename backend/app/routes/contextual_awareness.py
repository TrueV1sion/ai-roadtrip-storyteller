from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.core.logger import get_logger
from app.core.security import get_current_active_user
from app.database import get_db
from app.models.user import User
from app.services.contextual_awareness import get_contextual_awareness, ContextualAwareness, ContextType

router = APIRouter()
logger = get_logger(__name__)


@router.post("/awareness/analyze", tags=["Contextual Awareness"])
async def analyze_context(
    current_location: Dict[str, float],
    current_time: Optional[datetime] = None,
    route_id: Optional[str] = None,
    trip_id: Optional[str] = None,
    vehicle_data: Optional[Dict[str, Any]] = None,
    weather_data: Optional[Dict[str, Any]] = None,
    user_preferences: Optional[Dict[str, Any]] = None,
    recent_contexts: Optional[List[Dict[str, Any]]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    contextual_awareness: ContextualAwareness = Depends(get_contextual_awareness)
):
    """
    Analyze the user's current context and generate relevant awareness items.
    """
    try:
        # Validate current location
        if "latitude" not in current_location or "longitude" not in current_location:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current location must include latitude and longitude"
            )
        
        # Use current time if not provided
        if current_time is None:
            current_time = datetime.utcnow()
        
        # Analyze the context
        context_results = await contextual_awareness.analyze_context(
            user_id=current_user.id,
            current_location=current_location,
            current_time=current_time,
            route_id=route_id,
            trip_id=trip_id,
            vehicle_data=vehicle_data,
            weather_data=weather_data,
            user_preferences=user_preferences,
            recent_contexts=recent_contexts
        )
        
        return {
            "success": True,
            "context_count": len(context_results),
            "contexts": context_results
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing context: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze context"
        )


@router.get("/awareness/types", tags=["Contextual Awareness"])
async def list_context_types():
    """
    List all available context types.
    """
    try:
        context_types = {
            ContextType.MEAL_TIME: "Meal time detection and restaurant suggestions",
            ContextType.REST_BREAK: "Driver rest break reminders based on driving duration",
            ContextType.TRAFFIC_ALERT: "Traffic alerts and route alternatives",
            ContextType.SCENIC_SPOT: "Nearby scenic spot suggestions",
            ContextType.WEATHER_ALERT: "Weather alerts and driving condition warnings",
            ContextType.HISTORICAL_POI: "Historical points of interest suggestions",
            ContextType.NEARBY_ATTRACTION: "Nearby attraction and point of interest suggestions",
            ContextType.LOCAL_EVENT: "Local event discovery and recommendations",
            ContextType.FUEL_REMINDER: "Fuel or charging station reminders and suggestions",
            ContextType.LODGING: "Lodging suggestions as day ends",
            ContextType.ITINERARY_UPDATE: "Itinerary updates, including reservation reminders",
            ContextType.DRIVING_MILESTONE: "Driving milestone achievements and statistics"
        }
        
        return {
            "success": True,
            "context_types": context_types
        }
    except Exception as e:
        logger.error(f"Error listing context types: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list context types"
        )


@router.post("/awareness/meal-time", tags=["Contextual Awareness"])
async def check_meal_time(
    current_location: Dict[str, float],
    current_time: Optional[datetime] = None,
    user_preferences: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    contextual_awareness: ContextualAwareness = Depends(get_contextual_awareness)
):
    """
    Check specifically for meal time context.
    """
    try:
        # Validate current location
        if "latitude" not in current_location or "longitude" not in current_location:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current location must include latitude and longitude"
            )
        
        # Use current time if not provided
        if current_time is None:
            current_time = datetime.utcnow()
        
        # Check for meal time context
        context = await contextual_awareness._check_meal_time(
            current_time=current_time,
            latitude=current_location.get("latitude"),
            longitude=current_location.get("longitude"),
            user_id=current_user.id,
            user_preferences=user_preferences
        )
        
        if not context:
            return {
                "success": True,
                "has_meal_time_context": False,
                "message": "No meal time context detected"
            }
        
        return {
            "success": True,
            "has_meal_time_context": True,
            "context": context
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking meal time context: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check meal time context"
        )


@router.post("/awareness/driving-break", tags=["Contextual Awareness"])
async def check_driving_break(
    driving_duration: float,  # In minutes
    current_location: Dict[str, float],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    contextual_awareness: ContextualAwareness = Depends(get_contextual_awareness)
):
    """
    Check if the user needs a driving break based on continuous driving time.
    """
    try:
        # Validate current location
        if "latitude" not in current_location or "longitude" not in current_location:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current location must include latitude and longitude"
            )
        
        # Validate driving duration
        if driving_duration < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Driving duration must be a positive number"
            )
        
        # Check for rest break context
        context = await contextual_awareness._check_rest_break(
            driving_duration=driving_duration,
            latitude=current_location.get("latitude"),
            longitude=current_location.get("longitude"),
            user_id=current_user.id
        )
        
        if not context:
            return {
                "success": True,
                "needs_break": False,
                "message": "No driving break needed yet"
            }
        
        return {
            "success": True,
            "needs_break": True,
            "context": context
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking driving break: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check driving break"
        )


@router.post("/awareness/nearby-attractions", tags=["Contextual Awareness"])
async def check_nearby_attractions(
    current_location: Dict[str, float],
    route_id: Optional[str] = None,
    user_preferences: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    contextual_awareness: ContextualAwareness = Depends(get_contextual_awareness)
):
    """
    Check for interesting attractions near the current location.
    """
    try:
        # Validate current location
        if "latitude" not in current_location or "longitude" not in current_location:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current location must include latitude and longitude"
            )
        
        # Check for nearby attractions
        context = await contextual_awareness._check_nearby_attractions(
            latitude=current_location.get("latitude"),
            longitude=current_location.get("longitude"),
            route_id=route_id,
            user_id=current_user.id,
            user_preferences=user_preferences
        )
        
        if not context:
            return {
                "success": True,
                "has_attractions": False,
                "message": "No notable attractions found nearby"
            }
        
        return {
            "success": True,
            "has_attractions": True,
            "context": context
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking nearby attractions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check nearby attractions"
        )


@router.post("/awareness/reservations", tags=["Contextual Awareness"])
async def check_upcoming_reservations(
    current_location: Dict[str, float],
    current_time: Optional[datetime] = None,
    route_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    contextual_awareness: ContextualAwareness = Depends(get_contextual_awareness)
):
    """
    Check for upcoming reservations and provide reminders.
    """
    try:
        # Validate current location
        if "latitude" not in current_location or "longitude" not in current_location:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current location must include latitude and longitude"
            )
        
        # Use current time if not provided
        if current_time is None:
            current_time = datetime.utcnow()
        
        # Check for upcoming reservations
        context = await contextual_awareness._check_upcoming_reservations(
            current_time=current_time,
            user_id=current_user.id,
            latitude=current_location.get("latitude"),
            longitude=current_location.get("longitude"),
            route_id=route_id
        )
        
        if not context:
            return {
                "success": True,
                "has_upcoming_reservations": False,
                "message": "No upcoming reservations that require attention"
            }
        
        return {
            "success": True,
            "has_upcoming_reservations": True,
            "context": context
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking upcoming reservations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check upcoming reservations"
        )