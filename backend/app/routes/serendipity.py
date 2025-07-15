from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.core.logger import get_logger
from app.core.security import get_current_active_user
from app.database import get_db
from app.models.user import User
from app.services.serendipity_engine import get_serendipity_engine, SerendipityEngine, SerendipityType

router = APIRouter()
logger = get_logger(__name__)


@router.post("/serendipity/discovery", tags=["Serendipity"])
async def generate_discovery(
    current_location: Dict[str, float],
    environment_type: str,
    available_time: int,  # minutes
    current_time: Optional[datetime] = None,
    user_preferences: Optional[Dict[str, Any]] = None,
    route_id: Optional[str] = None,
    past_discoveries: Optional[List[str]] = None,
    weather: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    serendipity_engine: SerendipityEngine = Depends(get_serendipity_engine)
):
    """
    Generate a serendipitous discovery based on user context.
    """
    try:
        # Validate current location
        if "latitude" not in current_location or "longitude" not in current_location:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current location must include latitude and longitude"
            )
        
        # Validate available time
        if available_time <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Available time must be greater than 0"
            )
        
        # Generate surprise
        surprise = await serendipity_engine.generate_surprise(
            user_id=current_user.id,
            current_location=current_location,
            environment_type=environment_type,
            available_time=available_time,
            current_time=current_time,
            user_preferences=user_preferences,
            route_id=route_id,
            past_discoveries=past_discoveries,
            weather=weather
        )
        
        if not surprise:
            return {
                "success": True,
                "discovery_found": False,
                "message": "No serendipitous discovery generated"
            }
        
        return {
            "success": True,
            "discovery_found": True,
            "discovery": surprise
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating discovery: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate discovery"
        )


@router.post("/serendipity/route-discoveries", tags=["Serendipity"])
async def generate_route_discoveries(
    route: Dict[str, Any],
    total_trip_duration: int,  # minutes
    user_preferences: Optional[Dict[str, Any]] = None,
    count: int = 3,
    past_discoveries: Optional[List[str]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    serendipity_engine: SerendipityEngine = Depends(get_serendipity_engine)
):
    """
    Generate multiple serendipitous discoveries along a route.
    """
    try:
        # Validate route
        if "waypoints" not in route or not route["waypoints"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Route must include waypoints"
            )
        
        # Validate total trip duration
        if total_trip_duration <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Total trip duration must be greater than 0"
            )
        
        # Validate count
        if count <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Count must be greater than 0"
            )
        
        # Generate discoveries
        discoveries = await serendipity_engine.batch_generate_surprises(
            user_id=current_user.id,
            route=route,
            total_trip_duration=total_trip_duration,
            user_preferences=user_preferences,
            count=count,
            past_discoveries=past_discoveries
        )
        
        return {
            "success": True,
            "discovery_count": len(discoveries),
            "discoveries": discoveries
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating route discoveries: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate route discoveries"
        )


@router.post("/serendipity/detour", tags=["Serendipity"])
async def suggest_detour(
    current_location: Dict[str, float],
    destination: Dict[str, float],
    max_detour_time: int = 30,  # minutes
    max_detour_distance: float = 15.0,  # km
    user_preferences: Optional[Dict[str, Any]] = None,
    past_discoveries: Optional[List[str]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    serendipity_engine: SerendipityEngine = Depends(get_serendipity_engine)
):
    """
    Suggest a serendipitous detour between current location and destination.
    """
    try:
        # Validate locations
        if "latitude" not in current_location or "longitude" not in current_location:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current location must include latitude and longitude"
            )
        
        if "latitude" not in destination or "longitude" not in destination:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Destination must include latitude and longitude"
            )
        
        # Validate time and distance
        if max_detour_time <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum detour time must be greater than 0"
            )
        
        if max_detour_distance <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum detour distance must be greater than 0"
            )
        
        # Suggest detour
        detour = await serendipity_engine.suggest_detour(
            user_id=current_user.id,
            current_location=current_location,
            destination=destination,
            max_detour_time=max_detour_time,
            max_detour_distance=max_detour_distance,
            user_preferences=user_preferences,
            past_discoveries=past_discoveries
        )
        
        if not detour:
            return {
                "success": True,
                "detour_found": False,
                "message": "No suitable detour found"
            }
        
        return {
            "success": True,
            "detour_found": True,
            "detour": detour
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error suggesting detour: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to suggest detour"
        )


@router.get("/serendipity/types", tags=["Serendipity"])
async def list_serendipity_types():
    """
    List all available serendipity types.
    """
    try:
        serendipity_types = {
            SerendipityType.HIDDEN_GEM: "Places known only to locals and not in standard tourist guides",
            SerendipityType.LOCAL_SECRET: "Best-kept secrets that only residents typically know about",
            SerendipityType.UNUSUAL_SIGHT: "Odd or unexpected sights that are surprising and memorable",
            SerendipityType.VIEWPOINT: "Unexpected places with excellent views not on typical maps",
            SerendipityType.PHOTO_OPPORTUNITY: "Perfect spots for taking memorable or unique photos",
            SerendipityType.QUIRKY_ATTRACTION: "Unusual, offbeat, or eccentric attractions",
            SerendipityType.UNEXPECTED_DELIGHT: "Surprising and pleasant discoveries",
            SerendipityType.HISTORIC_DISCOVERY: "Lesser-known historical sites or artifacts",
            SerendipityType.NATURAL_WONDER: "Undiscovered natural phenomena or locations",
            SerendipityType.CULTURAL_EXPERIENCE: "Authentic local cultural experiences"
        }
        
        return {
            "success": True,
            "serendipity_types": serendipity_types
        }
    except Exception as e:
        logger.error(f"Error listing serendipity types: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list serendipity types"
        )