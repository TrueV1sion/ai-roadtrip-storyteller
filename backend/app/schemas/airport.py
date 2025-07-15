"""
Pydantic schemas for airport-related endpoints.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class ParkingType(str, Enum):
    """Types of airport parking."""
    ECONOMY = "economy"
    DAILY = "daily"
    GARAGE = "garage"
    PREMIUM = "premium"
    VALET = "valet"


class AirportDetectionRequest(BaseModel):
    """Request to detect if destination is an airport."""
    destination: str = Field(..., description="Destination to check")


class JourneyContext(BaseModel):
    """Context for journey creation."""
    origin: str = Field(..., description="Starting location")
    destination: str = Field(..., description="Destination")
    departure_time: Optional[datetime] = None
    flight_number: Optional[str] = None
    user_preferences: Optional[Dict[str, Any]] = None


class AirportJourneyRequest(BaseModel):
    """Request to create an airport journey."""
    user_input: str = Field(..., description="User's natural language request")
    context: JourneyContext


class ParkingSearchRequest(BaseModel):
    """Request to search for airport parking."""
    airport_code: str = Field(..., description="IATA airport code")
    start_date: datetime
    end_date: datetime
    parking_type: Optional[ParkingType] = None
    preferences: Optional[Dict[str, Any]] = Field(
        None,
        description="User preferences like max_price, covered_only"
    )


class ParkingBookingRequest(BaseModel):
    """Request to book airport parking."""
    airport_code: str
    parking_type: ParkingType
    start_date: datetime
    end_date: datetime
    flight_info: Optional[Dict[str, Any]] = None


class FlightTrackingRequest(BaseModel):
    """Request to track a flight."""
    flight_number: str = Field(..., description="Flight number (e.g., AA100)")
    departure_date: datetime
    airline_code: Optional[str] = Field(None, description="Optional airline code")


class DepartureCalculationRequest(BaseModel):
    """Request to calculate optimal departure time."""
    flight_time: datetime
    origin: str
    airport_code: str
    has_bags_to_check: bool = True
    has_precheck: bool = False
    international: bool = False


# Response schemas
class AirportInfo(BaseModel):
    """Airport information."""
    code: str
    name: str
    terminals: List[str]
    coordinates: Dict[str, float]
    detected: bool = True


class ParkingOption(BaseModel):
    """A parking option at the airport."""
    type: str
    name: str
    lots: List[str]
    available_spots: int
    price_per_day: float
    total_price: float
    shuttle_frequency: int
    walk_time: int
    features: List[str]


class ParkingSearchResponse(BaseModel):
    """Response for parking search."""
    airport_code: str
    start_date: datetime
    end_date: datetime
    duration_days: int
    options: List[ParkingOption]
    recommendation: str


class FlightStatusResponse(BaseModel):
    """Flight status information."""
    flight_number: str
    airline: Dict[str, str]
    status: str
    departure: Dict[str, Any]
    arrival: Dict[str, Any]
    aircraft: Optional[Dict[str, Any]] = None


class DepartureCalculationResponse(BaseModel):
    """Optimal departure time calculation."""
    flight_time: datetime
    recommended_departure: datetime
    arrival_at_airport: datetime
    breakdown: Dict[str, int]
    total_journey_time: int
    timeline: List[Dict[str, Any]]
    alerts: List[Dict[str, Any]]


class TSAWaitTimeResponse(BaseModel):
    """TSA wait time information."""
    airport_code: str
    timestamp: datetime
    is_peak_time: bool
    checkpoints: Dict[str, int]
    recommendation: str