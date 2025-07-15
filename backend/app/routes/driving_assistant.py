from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from ..core.security import get_current_user
from ..core.enhanced_ai_client import get_enhanced_ai_client
from ..database import get_db
from ..models.user import User
from ..services.driving_assistant import DrivingAssistant
from ..schemas.driving_assistant import (
    RestStop,
    FuelStation,
    DrivingStatus,
    RestBreakRequest,
    FuelStationRequest,
    TrafficInfoRequest,
    DrivingStatusRequest,
    TrafficInfoResponse
)

router = APIRouter(prefix="/driving-assistant", tags=["Driving Assistant"])

def get_driving_assistant(
    ai_client = Depends(get_enhanced_ai_client)
) -> DrivingAssistant:
    return DrivingAssistant(ai_client)

@router.post("/rest-breaks", response_model=List[RestStop])
async def get_rest_breaks(
    request: RestBreakRequest,
    current_user: User = Depends(get_current_user),
    driving_assistant: DrivingAssistant = Depends(get_driving_assistant)
):
    """Get recommended rest breaks based on route and driving time"""
    try:
        rest_breaks = await driving_assistant.get_rest_breaks(
            user=current_user,
            current_location=request.current_location,
            destination=request.destination,
            route_polyline=request.route_polyline,
            driving_time_minutes=request.driving_time_minutes,
            vehicle_type=request.vehicle_type,
            preferences=request.preferences
        )
        return rest_breaks
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting rest breaks: {str(e)}")

@router.post("/fuel-stations", response_model=List[FuelStation])
async def get_fuel_stations(
    request: FuelStationRequest,
    current_user: User = Depends(get_current_user),
    driving_assistant: DrivingAssistant = Depends(get_driving_assistant)
):
    """Get nearby fuel stations, prioritizing if fuel is low"""
    try:
        fuel_stations = await driving_assistant.get_fuel_stations(
            current_location=request.current_location,
            route_polyline=request.route_polyline,
            fuel_level=request.fuel_level,
            fuel_type=request.fuel_type,
            range_km=request.range_km,
            preferences=request.preferences
        )
        return fuel_stations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting fuel stations: {str(e)}")

@router.post("/traffic-info", response_model=TrafficInfoResponse)
async def get_traffic_info(
    request: TrafficInfoRequest,
    current_user: User = Depends(get_current_user),
    driving_assistant: DrivingAssistant = Depends(get_driving_assistant)
):
    """Get traffic information for the current route"""
    try:
        traffic_info = await driving_assistant.get_traffic_info(
            route_id=request.route_id,
            route_polyline=request.route_polyline,
            current_location=request.current_location,
            destination=request.destination
        )
        return traffic_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting traffic information: {str(e)}")

@router.post("/driving-status", response_model=DrivingStatus)
async def get_driving_status(
    request: DrivingStatusRequest,
    current_user: User = Depends(get_current_user),
    driving_assistant: DrivingAssistant = Depends(get_driving_assistant)
):
    """Get the current driving status and recommendations"""
    try:
        driving_status = await driving_assistant.get_driving_status(
            user=current_user,
            driving_time_minutes=request.driving_time_minutes,
            distance_covered=request.distance_covered,
            fuel_level=request.fuel_level,
            estimated_range=request.estimated_range,
            last_break_time=request.last_break_time
        )
        return driving_status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting driving status: {str(e)}")

@router.get("/fuel-efficiency", response_model=Dict[str, Any])
async def estimate_fuel_efficiency(
    vehicle_type: str,
    speed: float,
    elevation_change: float = 0,
    has_climate_control: bool = False,
    driving_assistant: DrivingAssistant = Depends(get_driving_assistant)
):
    """Estimate fuel efficiency based on driving conditions"""
    try:
        efficiency = driving_assistant.estimate_fuel_efficiency(
            vehicle_type=vehicle_type,
            speed=speed,
            elevation_change=elevation_change,
            has_climate_control=has_climate_control
        )
        
        return {
            "vehicle_type": vehicle_type,
            "efficiency": efficiency,
            "units": "km/L",
            "conditions": {
                "speed": speed,
                "elevation_change": elevation_change,
                "climate_control": has_climate_control
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error estimating fuel efficiency: {str(e)}")