"""
Pydantic schemas for journey tracking validation
"""
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
from datetime import datetime


class LocationModel(BaseModel):
    """Location coordinates with validation"""
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lng: float = Field(..., ge=-180, le=180, description="Longitude")
    
    @validator('lat', 'lng')
    def validate_coordinates(cls, v):
        if not isinstance(v, (int, float)):
            raise ValueError('Coordinates must be numeric')
        return float(v)


class PassengerModel(BaseModel):
    """Passenger information"""
    user_id: str = Field(..., min_length=1, description="User ID")
    age: Optional[str] = Field("adult", regex="^(child|teen|adult|senior)$")
    name: Optional[str] = Field(None, max_length=100)


class VehicleInfoModel(BaseModel):
    """Vehicle information with validation"""
    type: Optional[str] = Field("car", regex="^(car|truck|van|bus|motorcycle)$")
    speed_kmh: Optional[float] = Field(0, ge=0, le=300)
    average_speed_kmh: Optional[float] = Field(None, ge=0, le=300)
    heading: Optional[float] = Field(None, ge=0, le=360)
    
    @validator('speed_kmh', 'average_speed_kmh')
    def validate_speed(cls, v):
        if v is not None and v < 0:
            raise ValueError('Speed cannot be negative')
        if v is not None and v > 300:
            raise ValueError('Speed exceeds reasonable limits')
        return v


class RouteInfoModel(BaseModel):
    """Route information with validation"""
    total_distance_km: Optional[float] = Field(None, ge=0, le=10000)
    remaining_distance_km: Optional[float] = Field(None, ge=0, le=10000)
    estimated_duration_minutes: Optional[float] = Field(None, ge=0, le=10080)  # Max 1 week
    traffic_level: Optional[str] = Field("moderate", regex="^(light|moderate|heavy|standstill)$")
    road_type: Optional[str] = Field(None, max_length=50)
    nearest_poi: Optional[Dict[str, Any]] = None
    
    @validator('total_distance_km', 'remaining_distance_km')
    def validate_distance(cls, v):
        if v is not None and v < 0:
            raise ValueError('Distance cannot be negative')
        return v


class WeatherModel(BaseModel):
    """Weather information"""
    condition: Optional[str] = Field("clear", regex="^(clear|cloudy|rain|snow|fog|storm)$")
    temperature_c: Optional[float] = Field(None, ge=-50, le=60)
    visibility_km: Optional[float] = Field(None, ge=0, le=100)


class StartJourneyRequest(BaseModel):
    """Request model for starting journey tracking"""
    current_location: LocationModel
    destination: Optional[LocationModel] = None
    passengers: List[PassengerModel] = Field(default_factory=list)
    vehicle_info: Optional[VehicleInfoModel] = Field(default_factory=VehicleInfoModel)
    route_info: Optional[RouteInfoModel] = Field(default_factory=RouteInfoModel)
    preferences: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @validator('passengers')
    def validate_passengers(cls, v):
        if len(v) > 10:
            raise ValueError('Too many passengers')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "current_location": {"lat": 37.7749, "lng": -122.4194},
                "destination": {"lat": 37.3382, "lng": -121.8863},
                "passengers": [{"user_id": "user123", "age": "adult"}],
                "vehicle_info": {"type": "car", "speed_kmh": 0},
                "route_info": {
                    "total_distance_km": 78.5,
                    "estimated_duration_minutes": 65
                }
            }
        }


class UpdateLocationRequest(BaseModel):
    """Request model for updating journey location"""
    current_location: LocationModel
    journey_stage: Optional[str] = Field(
        None, 
        regex="^(departure|early|cruise|approaching|arrival)$",
        description="Current stage of journey"
    )
    vehicle_info: Optional[Dict[str, Any]] = Field(default_factory=dict)
    route_info: Optional[Dict[str, Any]] = Field(default_factory=dict)
    weather: Optional[WeatherModel] = None
    
    @validator('vehicle_info')
    def validate_vehicle_info(cls, v):
        # Validate nested vehicle info if provided
        if v and 'speed_kmh' in v:
            if not isinstance(v['speed_kmh'], (int, float)) or v['speed_kmh'] < 0:
                raise ValueError('Invalid speed value')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "current_location": {"lat": 37.7749, "lng": -122.4194},
                "journey_stage": "cruise",
                "vehicle_info": {
                    "speed_kmh": 65,
                    "average_speed_kmh": 60
                },
                "route_info": {
                    "remaining_distance_km": 45.2,
                    "traffic_level": "moderate"
                }
            }
        }


class RecordEngagementEventRequest(BaseModel):
    """Request model for recording engagement events"""
    event_type: str = Field(
        ...,
        regex="^(USER_REQUEST_STORY|USER_FOLLOWUP_QUESTION|USER_POSITIVE_RESPONSE|"
              "USER_INTERACTION|STORY_COMPLETED|USER_NEUTRAL_RESPONSE|STORY_STARTED|"
              "STORY_SKIPPED|USER_NEGATIVE_RESPONSE|USER_SAYS_STOP|NO_RESPONSE)$"
    )
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    class Config:
        schema_extra = {
            "example": {
                "event_type": "USER_REQUEST_STORY",
                "metadata": {
                    "story_id": "story123",
                    "user_action": "voice_command"
                }
            }
        }


class JourneyStatusResponse(BaseModel):
    """Response model for journey status"""
    is_active: bool
    journey_context: Optional[Dict[str, Any]]
    has_pending_story: bool
    pending_story: Optional[Dict[str, Any]]


class PendingStoryResponse(BaseModel):
    """Response model for pending story check"""
    has_story: bool
    triggered_at: Optional[str]
    journey_context: Optional[Dict[str, Any]]
    message: str