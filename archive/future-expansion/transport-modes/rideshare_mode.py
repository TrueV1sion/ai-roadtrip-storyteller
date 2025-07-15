"""
Rideshare Mode API Routes
Endpoints for driver and passenger rideshare features
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..core.auth import get_current_user
from ..core.logger import get_logger
from ..models.user import User
from ..schemas.rideshare import (
    RideshareModeRequest,
    RideshareModeResponse,
    DriverQuickAction,
    DriverStats,
    QuickActionRequest,
    QuickActionResponse,
    EntertainmentRequest,
    EntertainmentResponse,
    VoiceCommandRequest,
    VoiceCommandResponse,
    BreakLocation,
    OptimalRoute,
    TripTracking,
    EarningsReport
)
from ..services.rideshare_mode_manager import rideshare_mode_manager, RideshareUserType
from ..services.rideshare_voice_assistant import rideshare_voice_assistant

logger = get_logger(__name__)
router = APIRouter(prefix="/api/rideshare", tags=["rideshare"])


@router.post("/mode", response_model=RideshareModeResponse)
async def set_rideshare_mode(
    request: RideshareModeRequest,
    current_user: User = Depends(get_current_user)
):
    """Set or switch rideshare mode"""
    try:
        # Convert string mode to enum
        mode = RideshareUserType(request.mode.value)
        
        # Set mode
        success = await rideshare_mode_manager.set_mode(
            current_user.id,
            mode,
            request.preferences
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to set rideshare mode"
            )
        
        # Get available features
        features = []
        if mode == RideshareUserType.DRIVER:
            features = [
                "quick_actions",
                "earnings_tracking",
                "optimal_routes",
                "break_suggestions",
                "voice_commands"
            ]
        elif mode == RideshareUserType.PASSENGER:
            features = [
                "entertainment",
                "games",
                "stories",
                "music",
                "local_trivia"
            ]
        
        return RideshareModeResponse(
            mode=request.mode,
            active=True,
            features=features
        )
        
    except Exception as e:
        logger.error(f"Error setting rideshare mode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/mode", response_model=RideshareModeResponse)
async def get_rideshare_mode(
    current_user: User = Depends(get_current_user)
):
    """Get current rideshare mode"""
    try:
        mode = await rideshare_mode_manager.detect_mode(
            current_user.id,
            {},
            None
        )
        
        features = []
        if mode == RideshareUserType.DRIVER:
            features = ["quick_actions", "earnings_tracking", "optimal_routes"]
        elif mode == RideshareUserType.PASSENGER:
            features = ["entertainment", "games", "stories"]
        
        return RideshareModeResponse(
            mode=mode.value,
            active=mode != RideshareUserType.NONE,
            features=features
        )
        
    except Exception as e:
        logger.error(f"Error getting rideshare mode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/driver/quick-actions", response_model=List[DriverQuickAction])
async def get_driver_quick_actions(
    lat: float,
    lng: float,
    current_user: User = Depends(get_current_user)
):
    """Get contextual quick actions for drivers"""
    try:
        location = {"lat": lat, "lng": lng}
        actions = await rideshare_mode_manager.get_driver_quick_actions(
            location
        )
        
        return [DriverQuickAction(**action) for action in actions]
        
    except Exception as e:
        logger.error(f"Error getting quick actions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/driver/quick-action", response_model=QuickActionResponse)
async def execute_quick_action(
    request: QuickActionRequest,
    current_user: User = Depends(get_current_user)
):
    """Execute a driver quick action"""
    try:
        # Process based on action type
        result = {}
        voice_response = ""
        follow_up = []
        
        if request.action_id == "find_gas":
            # Would integrate with maps API
            result = {
                "stations": [
                    {"name": "Shell", "distance": 0.8, "price": 3.49},
                    {"name": "Chevron", "distance": 1.2, "price": 3.59}
                ]
            }
            voice_response = "Shell station 0.8 miles ahead"
            follow_up = ["Navigate", "Find cheaper"]
            
        elif request.action_id == "quick_food":
            result = {
                "restaurants": [
                    {"name": "McDonald's", "distance": 0.5, "wait": "5 min"},
                    {"name": "Subway", "distance": 0.7, "wait": "3 min"}
                ]
            }
            voice_response = "McDonald's drive-thru half mile ahead"
            follow_up = ["Navigate", "Other options"]
            
        elif request.action_id == "take_break":
            spots = await rideshare_mode_manager.suggest_break_locations(
                request.location,
                {}
            )
            result = {"spots": spots}
            voice_response = f"Rest stop {spots[0]['distance']} away"
            follow_up = ["Navigate", "Skip"]
        
        return QuickActionResponse(
            action_id=request.action_id,
            result=result,
            voice_response=voice_response,
            follow_up_actions=follow_up
        )
        
    except Exception as e:
        logger.error(f"Error executing quick action: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/driver/stats", response_model=DriverStats)
async def get_driver_stats(
    period: Optional[str] = "today",
    current_user: User = Depends(get_current_user)
):
    """Get driver earnings and stats"""
    try:
        # Get cached stats
        stats = await rideshare_mode_manager.track_driver_earnings(
            current_user.id,
            {"earnings": 0}  # Just retrieve
        )
        
        return DriverStats(**stats)
        
    except Exception as e:
        logger.error(f"Error getting driver stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/driver/trip", response_model=DriverStats)
async def record_trip(
    trip: TripTracking,
    current_user: User = Depends(get_current_user)
):
    """Record completed trip for earnings tracking"""
    try:
        trip_data = {
            "earnings": trip.earnings,
            "distance": trip.distance,
            "duration": trip.duration
        }
        
        stats = await rideshare_mode_manager.track_driver_earnings(
            current_user.id,
            trip_data
        )
        
        return DriverStats(**stats)
        
    except Exception as e:
        logger.error(f"Error recording trip: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/driver/optimal-routes", response_model=List[OptimalRoute])
async def get_optimal_routes(
    lat: float,
    lng: float,
    current_user: User = Depends(get_current_user)
):
    """Get optimal routes based on demand"""
    try:
        location = {"lat": lat, "lng": lng}
        time_of_day = "evening"  # Would calculate from current time
        
        routes = await rideshare_mode_manager.get_optimal_driver_routes(
            location,
            time_of_day
        )
        
        return [OptimalRoute(**route) for route in routes]
        
    except Exception as e:
        logger.error(f"Error getting optimal routes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/passenger/entertainment", response_model=EntertainmentResponse)
async def get_entertainment_options(
    request: EntertainmentRequest,
    current_user: User = Depends(get_current_user)
):
    """Get entertainment options for passengers"""
    try:
        options = await rideshare_mode_manager.get_passenger_entertainment(
            current_user.id,
            request.max_duration
        )
        
        # Flatten options for response
        all_options = []
        
        for game in options.get("quick_games", []):
            all_options.append({
                "id": game["id"],
                "name": game["name"],
                "type": "game",
                "duration": game["duration"],
                "description": game["description"]
            })
            
        for story in options.get("stories", []):
            all_options.append({
                "id": story["id"],
                "name": story["name"],
                "type": "story",
                "duration": story["duration"],
                "description": story["description"]
            })
        
        return EntertainmentResponse(
            options=all_options,
            recommended="trivia" if request.max_duration and request.max_duration < 10 else "short_mystery",
            reason="Perfect for your trip duration"
        )
        
    except Exception as e:
        logger.error(f"Error getting entertainment options: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/voice/command", response_model=VoiceCommandResponse)
async def process_voice_command(
    request: VoiceCommandRequest,
    current_user: User = Depends(get_current_user)
):
    """Process voice commands for rideshare mode"""
    try:
        # Add user context
        context = request.context
        context.update({
            "location": request.location,
            "vehicle_speed": request.vehicle_speed,
            "is_moving": request.is_moving
        })
        
        # Process command
        result = await rideshare_voice_assistant.process_rideshare_command(
            current_user.id,
            request.voice_input,
            RideshareUserType(request.mode.value),
            context
        )
        
        return VoiceCommandResponse(**result)
        
    except Exception as e:
        logger.error(f"Error processing voice command: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/voice/prompts")
async def get_voice_prompts(
    mode: RideshareMode,
    current_user: User = Depends(get_current_user)
):
    """Get example voice prompts for the current mode"""
    try:
        if mode == RideshareMode.DRIVER:
            prompts = rideshare_voice_assistant.get_driver_voice_prompts()
        else:
            prompts = rideshare_voice_assistant.get_passenger_voice_prompts()
            
        return {
            "mode": mode.value,
            "prompts": prompts,
            "tips": [
                "Keep commands simple and clear",
                "Wait for the beep before speaking",
                "Commands work best when stopped (drivers)"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting voice prompts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/mode")
async def end_rideshare_mode(
    current_user: User = Depends(get_current_user)
):
    """End rideshare mode and return to normal"""
    try:
        success = await rideshare_mode_manager.set_mode(
            current_user.id,
            RideshareUserType.NONE
        )
        
        return {
            "success": success,
            "message": "Rideshare mode ended"
        }
        
    except Exception as e:
        logger.error(f"Error ending rideshare mode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )