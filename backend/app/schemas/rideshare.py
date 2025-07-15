"""
Rideshare schemas for request/response models
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class RideshareMode(str, Enum):
    DRIVER = "driver"
    PASSENGER = "passenger"
    NONE = "none"


class RideshareModeRequest(BaseModel):
    mode: RideshareMode
    preferences: Optional[Dict[str, Any]] = Field(default_factory=dict)
    auto_detect: bool = Field(default=False)


class RideshareModeResponse(BaseModel):
    mode: RideshareMode
    active: bool
    started_at: Optional[datetime] = None
    features: List[str]


class DriverQuickAction(BaseModel):
    id: str
    label: str
    icon: str
    voice_command: str
    priority: int = Field(ge=0, le=10)


class DriverStats(BaseModel):
    total_earnings: float = Field(ge=0)
    trips_completed: int = Field(ge=0)
    total_distance: float = Field(ge=0)
    hourly_rate: float = Field(ge=0)
    session_duration: Optional[int] = None  # minutes
    peak_hours: List[str] = Field(default_factory=list)


class PassengerPreferences(BaseModel):
    entertainment_types: List[str] = Field(default_factory=list)
    music_preferences: List[str] = Field(default_factory=list)
    game_difficulty: str = Field(default="medium")
    story_genres: List[str] = Field(default_factory=list)


class QuickActionRequest(BaseModel):
    action_id: str
    location: Dict[str, float]
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)


class QuickActionResponse(BaseModel):
    action_id: str
    result: Dict[str, Any]
    voice_response: str
    follow_up_actions: List[str] = Field(default_factory=list)


class EntertainmentOption(BaseModel):
    id: str
    name: str
    type: str  # game, story, music
    duration: str
    description: str
    difficulty: Optional[str] = None


class EntertainmentRequest(BaseModel):
    type: Optional[str] = None
    max_duration: Optional[int] = None  # minutes
    preferences: Optional[PassengerPreferences] = None


class EntertainmentResponse(BaseModel):
    options: List[EntertainmentOption]
    recommended: Optional[str] = None
    reason: Optional[str] = None


class VoiceCommandRequest(BaseModel):
    voice_input: str
    mode: RideshareMode
    context: Dict[str, Any] = Field(default_factory=dict)
    location: Optional[Dict[str, float]] = None
    vehicle_speed: Optional[float] = None
    is_moving: bool = Field(default=False)


class VoiceCommandResponse(BaseModel):
    response: str
    action: str
    speak: bool = Field(default=True)
    data: Optional[Dict[str, Any]] = None
    quick_actions: List[str] = Field(default_factory=list)
    safety_warning: bool = Field(default=False)


class BreakLocation(BaseModel):
    name: str
    distance: str
    amenities: List[str]
    rating: float = Field(ge=0, le=5)
    estimated_time: Optional[str] = None


class OptimalRoute(BaseModel):
    area: str
    demand_level: str
    estimated_wait: str
    surge_multiplier: float = Field(ge=1.0)
    distance: Optional[str] = None


class TripTracking(BaseModel):
    trip_id: str
    earnings: float
    distance: float
    duration: int  # minutes
    pickup_location: Dict[str, float]
    dropoff_location: Dict[str, float]
    timestamp: datetime


class EarningsReport(BaseModel):
    period: str  # today, week, month
    total_earnings: float
    total_trips: int
    total_hours: float
    average_per_trip: float
    average_hourly: float
    best_day: Optional[str] = None
    best_hour: Optional[int] = None