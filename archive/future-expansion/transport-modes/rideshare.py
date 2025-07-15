"""
API routes for rideshare mode functionality.
"""
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.core.auth import get_current_user
from backend.app.models.user import User
from backend.app.services.rideshare_service import (
    RideshareService,
    RideshareMode,
    RideshareContext
)

router = APIRouter(prefix="/rideshare", tags=["rideshare"])


class LocationPoint(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class DriverPreferences(BaseModel):
    find_food: bool = True
    find_charging: bool = False
    find_rest_stops: bool = True
    max_detour_minutes: int = 5
    prefer_quick_action: bool = True


class PassengerInterests(BaseModel):
    interests: List[str] = Field(default_factory=list)
    entertainment_types: List[str] = Field(default_factory=lambda: ["trivia", "insights"])


class DriverRouteRequest(BaseModel):
    pickup: LocationPoint
    dropoff: LocationPoint
    preferences: Optional[DriverPreferences] = None
    avoid_surge_areas: bool = True


class PassengerEntertainmentRequest(BaseModel):
    pickup: LocationPoint
    dropoff: LocationPoint
    duration_minutes: int = Field(..., ge=1, le=180)
    interests: Optional[List[str]] = None


class QuickActionRequest(BaseModel):
    location: LocationPoint
    action_type: str = "all"  # "all", "food", "charging", "rest"


@router.post("/driver/route")
async def get_driver_route(
    request: DriverRouteRequest,
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get optimized route for rideshare drivers with opportunities."""
    service = RideshareService()
    
    result = await service.get_optimized_driver_route(
        pickup=request.pickup.dict(),
        dropoff=request.dropoff.dict(),
        driver_preferences=request.preferences.dict() if request.preferences else None,
        avoid_surge_areas=request.avoid_surge_areas
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result


@router.post("/passenger/entertainment")
async def get_passenger_entertainment(
    request: PassengerEntertainmentRequest,
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get entertainment package for passengers during ride."""
    service = RideshareService()
    
    result = await service.get_passenger_entertainment(
        pickup=request.pickup.dict(),
        dropoff=request.dropoff.dict(),
        duration_minutes=request.duration_minutes,
        interests=request.interests
    )
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result


@router.post("/quick-actions")
async def find_quick_actions(
    request: QuickActionRequest,
    current_user: User = Depends(get_current_user)
) -> List[Dict]:
    """Find quick action opportunities near current location."""
    service = RideshareService()
    
    actions = await service.find_quick_actions(
        location=request.location.dict(),
        action_type=request.action_type
    )
    
    return actions


@router.get("/surge-areas")
async def get_surge_areas(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user)
) -> List[Dict]:
    """Get current surge pricing areas."""
    service = RideshareService()
    
    # Get surge areas around the specified location
    areas = await service._get_surge_areas(
        pickup={"lat": lat, "lng": lng},
        dropoff={"lat": lat, "lng": lng}  # Same location for area search
    )
    
    return [
        {
            "location": area.location,
            "radius": area.radius,
            "surge_multiplier": area.surge_multiplier,
            "estimated_end_time": area.estimated_end_time.isoformat() if area.estimated_end_time else None
        }
        for area in areas
    ]


@router.post("/driver/earnings-tips")
async def get_earnings_tips(
    pickup: LocationPoint,
    dropoff: LocationPoint,
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get earnings optimization tips for a specific route."""
    service = RideshareService()
    
    # Get route first
    route = await service.directions_service.get_directions(
        origin=f"{pickup.lat},{pickup.lng}",
        destination=f"{dropoff.lat},{dropoff.lng}",
        mode="driving"
    )
    
    if not route or not route.get("routes"):
        raise HTTPException(status_code=400, detail="No route found")
        
    tips = await service._calculate_earnings_optimization(
        route["routes"][0],
        pickup.dict(),
        dropoff.dict()
    )
    
    return tips


@router.get("/driver/best-times")
async def get_best_driving_times(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get best times to drive in a specific area."""
    # This would integrate with historical data
    # Simplified for demo
    from datetime import datetime
    
    current_hour = datetime.now().hour
    
    return {
        "current_demand": "high" if 7 <= current_hour <= 9 or 17 <= current_hour <= 19 else "moderate",
        "best_hours": [
            {"hour": 7, "demand": "high", "typical_surge": 1.3},
            {"hour": 8, "demand": "high", "typical_surge": 1.5},
            {"hour": 17, "demand": "high", "typical_surge": 1.4},
            {"hour": 18, "demand": "high", "typical_surge": 1.6},
            {"hour": 22, "demand": "moderate", "typical_surge": 1.2}
        ],
        "recommendations": [
            "Morning rush (7-9 AM) has consistent high demand",
            "Evening rush (5-7 PM) typically has highest fares",
            "Late night weekend hours often have surge pricing"
        ]
    }