"""Booking schemas for API requests and responses."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator

from app.core.enums import BookingType
from app.models.booking import BookingStatus


class BookingBase(BaseModel):
    """Base booking schema."""
    booking_type: BookingType
    service_date: datetime
    gross_amount: Decimal = Field(..., ge=0, decimal_places=2)
    currency: str = Field(default="USD", max_length=3)
    metadata: Optional[Dict[str, Any]] = None


class BookingCreate(BookingBase):
    """Schema for creating a booking."""
    partner_id: int
    partner_booking_id: Optional[str] = None
    
    @validator('gross_amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Gross amount must be positive')
        return v


class BookingUpdate(BaseModel):
    """Schema for updating a booking."""
    booking_status: Optional[BookingStatus] = None
    service_date: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class BookingResponse(BookingBase):
    """Schema for booking response."""
    id: int
    booking_reference: str
    user_id: int
    partner_id: int
    booking_status: BookingStatus
    booking_date: datetime
    net_amount: Decimal
    partner_booking_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    # Nested relationships
    commission_amount: Optional[Decimal] = None
    commission_rate: Optional[Decimal] = None
    partner_name: Optional[str] = None
    
    class Config:
        orm_mode = True


class BookingListResponse(BaseModel):
    """Schema for listing bookings."""
    bookings: list[BookingResponse]
    total: int
    page: int
    per_page: int
    
    class Config:
        orm_mode = True


# Restaurant-specific schemas
class RestaurantSearchRequest(BaseModel):
    """Request schema for restaurant search."""
    location: Dict[str, Any]  # latitude/longitude or city/state
    cuisine: Optional[str] = None
    party_size: int = Field(default=2, ge=1, le=20)
    date: Optional[str] = None
    time: Optional[str] = None
    price_range: Optional[str] = None
    radius_miles: float = Field(default=5.0, ge=0.1, le=50.0)


class RestaurantAvailabilityRequest(BaseModel):
    """Request schema for checking restaurant availability."""
    restaurant_id: str
    date: str
    time: str
    party_size: int = Field(ge=1, le=20)


class RestaurantReservationRequest(BaseModel):
    """Request schema for creating restaurant reservation."""
    restaurant_id: str
    date: str
    time: str
    party_size: int = Field(ge=1, le=20)
    guest_info: Dict[str, str]
    special_requests: Optional[str] = None