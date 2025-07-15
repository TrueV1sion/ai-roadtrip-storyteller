"""Parking reservation schemas."""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class VehicleInfo(BaseModel):
    """Vehicle information schema."""
    make: Optional[str] = None
    model: Optional[str] = None
    color: Optional[str] = None
    license_plate: Optional[str] = None


class ParkingReservationCreate(BaseModel):
    """Schema for creating a parking reservation."""
    location_name: str = Field(..., description="Name of the parking location (e.g., 'LAX Airport')")
    parking_type: str = Field(default="airport", description="Type of parking (airport, event, hotel)")
    check_in_time: datetime = Field(..., description="When the vehicle will be parked")
    check_out_time: datetime = Field(..., description="When the vehicle will be retrieved")
    vehicle_info: Optional[VehicleInfo] = None
    terminal: Optional[str] = Field(None, description="Airport terminal if applicable")
    outbound_flight: Optional[str] = Field(None, description="Outbound flight number")
    return_flight: Optional[str] = Field(None, description="Return flight number")
    airline: Optional[str] = Field(None, description="Airline name")
    
    @validator('check_out_time')
    def validate_check_out_after_check_in(cls, v, values):
        if 'check_in_time' in values and v <= values['check_in_time']:
            raise ValueError('Check-out time must be after check-in time')
        return v


class ParkingPhotoUpload(BaseModel):
    """Schema for parking photo upload response."""
    message: str
    photo_url: str
    booking_reference: str
    return_journey_scheduled: bool
    estimated_pickup_time: Optional[datetime] = None


class ParkingPhotoContext(BaseModel):
    """Schema for parking photo context."""
    photo_url: str
    location: str
    lot: Optional[str] = None
    spot: Optional[str] = None
    vehicle: Optional[VehicleInfo] = None
    parked_at: Optional[datetime] = None
    terminal: Optional[str] = None
    walking_directions: str


class ParkingDetails(BaseModel):
    """Schema for parking reservation details."""
    booking_reference: str
    location: str
    terminal: Optional[str] = None
    lot_name: Optional[str] = None
    spot_number: Optional[str] = None
    vehicle: Optional[VehicleInfo] = None
    parking_times: Dict[str, datetime]
    photo: Dict[str, Any]
    return_journey: Dict[str, Any]
    parking_context: Optional[ParkingPhotoContext] = None


class ReturnJourneySchedule(BaseModel):
    """Schema for return journey scheduling."""
    scheduled: bool
    estimated_pickup_time: datetime
    travel_time_minutes: int
    buffer_minutes: int
    parking_location: str
    destination: str


class UpcomingReturn(BaseModel):
    """Schema for upcoming return information."""
    reservation_id: str
    user_id: str
    location: str
    check_out_time: datetime
    parking_photo_url: Optional[str] = None
    spot_info: Optional[str] = None


class UpcomingReturnsResponse(BaseModel):
    """Schema for upcoming returns response."""
    upcoming_returns: list[UpcomingReturn]
    total: int


class ParkingReservationResponse(BaseModel):
    """Schema for parking reservation response."""
    message: str
    booking_reference: str
    reservation_id: str
    location: str
    check_in: datetime
    check_out: datetime
    upload_photo_url: str