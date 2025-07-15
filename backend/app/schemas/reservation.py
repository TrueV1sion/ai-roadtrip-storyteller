from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, EmailStr


class ReservationStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


class ReservationType(str, Enum):
    RESTAURANT = "restaurant"
    ATTRACTION = "attraction"
    ACTIVITY = "activity"
    ACCOMMODATION = "accommodation"
    OTHER = "other"


class ReservationBase(BaseModel):
    """Base schema for reservation data."""
    venue_name: str = Field(..., description="Name of the venue")
    venue_address: Optional[str] = Field(None, description="Address of the venue")
    reservation_time: datetime = Field(..., description="Date and time of the reservation")
    party_size: str = Field(..., description="Number of people in the party (e.g., '2 adults, 1 child')")
    special_requests: Optional[str] = Field(None, description="Any special requests for the reservation")
    contact_phone: Optional[str] = Field(None, description="Contact phone number")
    contact_email: Optional[EmailStr] = Field(None, description="Contact email")


class RestaurantReservationCreate(ReservationBase):
    """Schema for creating a restaurant reservation."""
    restaurant_name: str = Field(..., description="Name of the restaurant")
    restaurant_address: str = Field(..., description="Address of the restaurant")
    cuisine_type: Optional[str] = Field(None, description="Type of cuisine")
    restaurant_phone: Optional[str] = Field(None, description="Restaurant's phone number")


class AttractionReservationCreate(ReservationBase):
    """Schema for creating an attraction reservation."""
    attraction_name: str = Field(..., description="Name of the attraction")
    attraction_address: str = Field(..., description="Address of the attraction")
    attraction_type: Optional[str] = Field(None, description="Type of attraction")
    ticket_count: Optional[int] = Field(None, description="Number of tickets")


class ReservationCreate(BaseModel):
    """Generic schema for creating a reservation."""
    type: ReservationType = Field(..., description="Type of reservation")
    venue_name: str = Field(..., description="Name of the venue")
    venue_address: Optional[str] = Field(None, description="Address of the venue")
    reservation_time: datetime = Field(..., description="Date and time of the reservation")
    party_size: str = Field(..., description="Number of people in the party")
    special_requests: Optional[str] = Field(None, description="Any special requests for the reservation")
    contact_phone: Optional[str] = Field(None, description="Contact phone number")
    contact_email: Optional[EmailStr] = Field(None, description="Contact email")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata for the reservation")


class ReservationUpdate(BaseModel):
    """Schema for updating a reservation."""
    venue_name: Optional[str] = None
    venue_address: Optional[str] = None
    reservation_time: Optional[datetime] = None
    party_size: Optional[str] = None
    special_requests: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    metadata: Optional[Dict[str, Any]] = None


class ReservationStatusUpdate(BaseModel):
    """Schema for updating a reservation status."""
    status: ReservationStatus = Field(..., description="New status for the reservation")
    confirmation_number: Optional[str] = Field(None, description="Confirmation number from provider")
    metadata_updates: Optional[Dict[str, Any]] = Field(None, description="Additional metadata updates")


class ReservationCancellation(BaseModel):
    """Schema for cancelling a reservation."""
    cancellation_reason: Optional[str] = Field(None, description="Reason for cancellation")


class ReservationResponse(BaseModel):
    """Schema for reservation responses."""
    id: str
    user_id: str
    type: str
    venue_name: str
    venue_address: Optional[str] = None
    reservation_time: datetime
    party_size: str
    special_requests: Optional[str] = None
    confirmation_number: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    status: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    cancelled_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class VoiceReservationRequest(BaseModel):
    """Schema for voice-based reservation requests."""
    user_id: str = Field(..., description="ID of the user making the reservation")
    reservation_type: ReservationType = Field(..., description="Type of reservation")
    voice_query: str = Field(..., description="Voice command text for the reservation")
    current_location: Optional[Dict[str, float]] = Field(None, description="Current user location")
    datetime_context: Optional[datetime] = Field(None, description="Context date/time for relative times")
    party_size_default: Optional[str] = Field("2", description="Default party size if not specified")


# New schemas for comprehensive reservation system
class ReservationSearchRequest(BaseModel):
    """Schema for searching restaurants/venues."""
    query: str = Field(..., description="Search query")
    location: Dict[str, float] = Field(..., description="Location coordinates {lat, lng}")
    date: datetime = Field(..., description="Desired reservation date")
    party_size: int = Field(..., description="Number of guests")
    cuisines: Optional[List[str]] = Field(None, description="Preferred cuisine types")
    price_range: Optional[str] = Field(None, description="Price range (1-4)")
    amenities: Optional[List[str]] = Field(None, description="Desired amenities")


class SearchResult(BaseModel):
    """Schema for individual search result."""
    provider: str = Field(..., description="Booking provider")
    venueId: str = Field(..., description="Unique venue identifier")
    name: str = Field(..., description="Venue name")
    cuisine: str = Field(..., description="Cuisine type")
    rating: float = Field(..., description="Average rating")
    priceRange: str = Field(..., description="Price range indicator")
    distance: float = Field(..., description="Distance in miles")
    availableTimes: List[str] = Field(..., description="Available time slots")
    imageUrl: Optional[str] = Field(None, description="Venue image URL")
    description: Optional[str] = Field(None, description="Venue description")
    amenities: Optional[List[str]] = Field(None, description="Available amenities")


class ReservationSearchResponse(BaseModel):
    """Schema for search response."""
    results: List[SearchResult]


class AvailabilityCheckRequest(BaseModel):
    """Schema for checking availability."""
    provider: str = Field(..., description="Booking provider")
    venue_id: str = Field(..., description="Venue identifier")
    date: datetime = Field(..., description="Desired date")
    party_size: int = Field(..., description="Number of guests")
    exclude_reservation_id: Optional[str] = Field(None, description="Reservation to exclude (for modifications)")


class AvailabilityCheckResponse(BaseModel):
    """Schema for availability response."""
    available_times: List[str] = Field(..., description="Available time slots")


# Enhanced ReservationResponse for new system
class EnhancedReservationResponse(ReservationResponse):
    """Enhanced reservation response with additional fields."""
    provider: Optional[str] = Field(None, description="Booking provider")
    venue_id: Optional[str] = Field(None, description="Provider-specific venue ID")
    venue_phone: Optional[str] = Field(None, description="Venue phone number")
    date_time: Optional[datetime] = Field(None, description="Reservation date and time")
    customer_info: Optional[Dict[str, Any]] = Field(None, description="Customer information")
    cancellation_policy: Optional[str] = Field(None, description="Cancellation policy")
    modification_allowed: Optional[bool] = Field(True, description="Whether modification is allowed")
    cancellation_deadline: Optional[datetime] = Field(None, description="Deadline for cancellation")