from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class RestStopBase(BaseModel):
    """Base schema for rest stop"""
    name: str
    location: Dict[str, float]
    distance_from_current: float
    distance_from_route: float
    facilities: List[str]
    estimated_duration: int
    category: str
    
class RestStopCreate(RestStopBase):
    """Schema for creating a rest stop"""
    rating: Optional[float] = None
    amenities: Dict[str, bool] = Field(default_factory=dict)
    
class RestStop(RestStopBase):
    """Schema for rest stop response"""
    id: str
    rating: Optional[float] = None
    arrival_time: datetime
    amenities: Dict[str, bool]
    
    class Config:
        orm_mode = True
        
class FuelStationBase(BaseModel):
    """Base schema for fuel station"""
    name: str
    location: Dict[str, float]
    distance_from_current: float
    distance_from_route: float
    fuel_types: List[str]
    
class FuelStationCreate(FuelStationBase):
    """Schema for creating a fuel station"""
    prices: Optional[Dict[str, float]] = None
    brand: Optional[str] = None
    rating: Optional[float] = None
    amenities: Dict[str, bool] = Field(default_factory=dict)
    busy_level: Optional[str] = None
    
class FuelStation(FuelStationBase):
    """Schema for fuel station response"""
    id: str
    prices: Optional[Dict[str, float]] = None
    brand: Optional[str] = None
    rating: Optional[float] = None
    amenities: Dict[str, bool]
    busy_level: Optional[str] = None
    
    class Config:
        orm_mode = True
        
class TrafficIncidentBase(BaseModel):
    """Base schema for traffic incident"""
    type: str
    severity: int
    description: str
    location: Dict[str, float]
    affected_roads: List[str]
    
class TrafficIncidentCreate(TrafficIncidentBase):
    """Schema for creating a traffic incident"""
    start_time: datetime
    end_time: Optional[datetime] = None
    delay_minutes: Optional[int] = None
    
class TrafficIncident(TrafficIncidentBase):
    """Schema for traffic incident response"""
    id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    delay_minutes: Optional[int] = None
    
    class Config:
        orm_mode = True
        
class RouteSegmentBase(BaseModel):
    """Base schema for route segment"""
    start_location: Dict[str, float]
    end_location: Dict[str, float]
    distance: float
    normal_duration: int
    current_duration: int
    traffic_level: str
    
class RouteSegmentCreate(RouteSegmentBase):
    """Schema for creating a route segment"""
    speed_limit: Optional[float] = None
    
class RouteSegment(RouteSegmentBase):
    """Schema for route segment response"""
    segment_id: str
    speed_limit: Optional[float] = None
    incidents: List[TrafficIncident] = Field(default_factory=list)
    
    class Config:
        orm_mode = True
        
class DrivingStatusBase(BaseModel):
    """Base schema for driving status"""
    driving_time: int
    distance_covered: float
    fuel_level: float
    estimated_range: float
    rest_break_due: bool
    
class DrivingStatus(DrivingStatusBase):
    """Schema for driving status response"""
    next_rest_recommended_in: Optional[int] = None
    alerts: List[str] = Field(default_factory=list)
    driver_fatigue_level: str
    
    class Config:
        orm_mode = True
        
# Request/Response schemas

class RestBreakRequest(BaseModel):
    """Request schema for getting rest break recommendations"""
    current_location: Dict[str, float]
    destination: Dict[str, float]
    route_polyline: str
    driving_time_minutes: int
    vehicle_type: str = "car"
    preferences: Optional[Dict[str, Any]] = None
    
class FuelStationRequest(BaseModel):
    """Request schema for getting fuel station recommendations"""
    current_location: Dict[str, float]
    route_polyline: str
    fuel_level: float
    fuel_type: str = "regular"
    range_km: Optional[float] = None
    preferences: Optional[Dict[str, Any]] = None
    
class TrafficInfoRequest(BaseModel):
    """Request schema for getting traffic information"""
    route_id: str
    route_polyline: str
    current_location: Dict[str, float]
    destination: Dict[str, float]
    
class DrivingStatusRequest(BaseModel):
    """Request schema for getting driving status"""
    driving_time_minutes: int
    distance_covered: float
    fuel_level: float
    estimated_range: float
    last_break_time: Optional[datetime] = None
    
class TrafficInfoResponse(BaseModel):
    """Response schema for traffic information"""
    route_id: str
    overall_traffic: str
    total_distance: float
    normal_duration: int
    current_duration: int
    delay_seconds: int
    delay_percentage: float
    incidents: List[TrafficIncident] = Field(default_factory=list)
    segments: List[RouteSegment] = Field(default_factory=list)
    alternate_routes: List[Dict[str, Any]] = Field(default_factory=list)