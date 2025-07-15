from enum import Enum
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator


class TravelMode(str, Enum):
    """Travel mode for directions."""
    DRIVING = "driving"
    WALKING = "walking"
    BICYCLING = "bicycling"
    TRANSIT = "transit"


class TrafficModel(str, Enum):
    """Traffic prediction model."""
    BEST_GUESS = "best_guess"
    PESSIMISTIC = "pessimistic"
    OPTIMISTIC = "optimistic"


class Location(BaseModel):
    """Geographic location."""
    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude")


class Distance(BaseModel):
    """Distance information."""
    text: str = Field(..., description="Human readable distance")
    value: int = Field(..., description="Distance in meters")


class Duration(BaseModel):
    """Duration information."""
    text: str = Field(..., description="Human readable duration")
    value: int = Field(..., description="Duration in seconds")


class PlaceDetails(BaseModel):
    """Details about a place."""
    name: Optional[str] = Field(None, description="Place name")
    formatted_address: Optional[str] = Field(
        None,
        description="Formatted address"
    )
    rating: Optional[float] = Field(
        None,
        description="Place rating"
    )
    opening_hours: Optional[dict] = Field(
        None,
        description="Opening hours"
    )


class RouteStep(BaseModel):
    """A step in the route."""
    distance: Distance
    duration: Duration
    instructions: str = Field(
        ...,
        description="HTML formatted instructions"
    )
    maneuver: Optional[str] = Field(None, description="Maneuver type")
    coordinates: List[List[float]] = Field(
        ...,
        description="Step coordinates"
    )
    travel_mode: str = Field(
        ...,
        description="Travel mode for this step"
    )
    transit_details: Optional[dict] = Field(None, description="Transit details")


class RouteLeg(BaseModel):
    """A leg of the route."""
    distance: Distance
    duration: Duration
    duration_in_traffic: Optional[Duration] = None
    start_location: Location
    end_location: Location
    start_address: str
    end_address: str
    steps: List[RouteStep]
    start_place_details: Optional[PlaceDetails] = None
    end_place_details: Optional[PlaceDetails] = None


class Route(BaseModel):
    """A complete route."""
    summary: str = Field(..., description="Route summary")
    bounds: dict = Field(..., description="Route bounds")
    copyrights: str = Field(..., description="Route copyrights")
    legs: List[RouteLeg]
    traffic_speed: List[dict] = Field(
        default_list=[],
        description="Traffic speed data"
    )
    fare: Optional[dict] = Field(None, description="Fare information")
    warnings: List[str] = Field(default_list=[], description="Route warnings")
    overview_coordinates: List[List[float]] = Field(
        ...,
        description="Route overview coordinates"
    )


class DirectionsResponse(BaseModel):
    """Response model for directions API."""
    routes: List[Route]
    cached: bool = Field(
        default=False,
        description="Whether response is from cache"
    )
    offline: bool = Field(
        default=False,
        description="Whether offline data is being used"
    )
    timestamp: datetime = Field(..., description="Response timestamp")
    optimized_waypoints: Optional[List[str]] = Field(
        None,
        description="Optimized waypoint order"
    )


class DirectionsRequest(BaseModel):
    """Request model for directions API."""
    origin: str = Field(
        ...,
        description="Origin location (lat,lng or place name)"
    )
    destination: str = Field(
        ...,
        description="Destination location (lat,lng or place name)"
    )
    mode: TravelMode = Field(
        default=TravelMode.DRIVING,
        description="Travel mode"
    )
    waypoints: Optional[List[str]] = Field(
        None,
        description="List of waypoint locations"
    )
    optimize_route: bool = Field(
        default=False,
        description="Whether to optimize waypoint order"
    )
    alternatives: bool = Field(
        default=False,
        description="Whether to return alternative routes"
    )
    include_traffic: bool = Field(
        default=True,
        description="Include live traffic data"
    )
    include_places: bool = Field(
        default=False,
        description="Include detailed place information"
    )
    departure_time: Optional[datetime] = Field(
        None,
        description="Future departure time"
    )
    traffic_model: TrafficModel = Field(
        default=TrafficModel.BEST_GUESS,
        description="Traffic prediction model"
    )


class DeprecatedDirectionsRequest(BaseModel):
    """Request model for deprecated directions endpoint."""
    origin_lat: float = Field(..., description="Origin latitude")
    origin_lng: float = Field(..., description="Origin longitude")
    dest_lat: float = Field(..., description="Destination latitude")
    dest_lng: float = Field(..., description="Destination longitude")
    departure_time: Optional[str] = Field(None, description="Departure time in ISO format")

    @validator('departure_time')
    def validate_departure_time(cls, v):
        """Validate departure time format."""
        if v:
            try:
                dt = datetime.fromisoformat(v)
                if dt < datetime.now():
                    raise ValueError("Departure time must be in the future")
            except ValueError as e:
                raise ValueError(f"Invalid departure time format: {str(e)}")
        return v 