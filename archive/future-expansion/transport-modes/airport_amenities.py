"""
Airport Amenities API Routes

Endpoints for airport lounge, dining, and amenity management.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.core.auth import get_current_user
from backend.app.core.logger import get_logger
from backend.app.models.user import User
from backend.app.services.airport_amenities_service import AirportAmenitiesService
from backend.app.services.terminal_navigation_service import TerminalNavigationService

logger = get_logger(__name__)
router = APIRouter(prefix="/api/airport", tags=["airport_amenities"])

# Initialize services
amenities_service = AirportAmenitiesService()
navigation_service = TerminalNavigationService()


# Request/Response Models
class AmenityQuery(BaseModel):
    airport_code: str = Field(..., description="IATA airport code")
    terminal: Optional[str] = Field(None, description="Terminal identifier")
    amenity_types: Optional[List[str]] = Field(None, description="Filter by amenity types")
    user_preferences: Optional[dict] = Field(None, description="User preferences for filtering")


class BookingRequest(BaseModel):
    amenity_id: str = Field(..., description="Amenity ID to book")
    access_type: Optional[str] = Field(None, description="Type of access (for lounges)")
    arrival_time: datetime = Field(..., description="Planned arrival time")
    party_size: int = Field(1, ge=1, le=10, description="Number of people")
    flight_number: Optional[str] = Field(None, description="Flight number")
    airline: Optional[str] = Field(None, description="Airline code")
    departure_time: Optional[datetime] = Field(None, description="Flight departure time")
    special_requests: Optional[str] = Field(None, description="Special requests or notes")
    member_id: Optional[str] = Field(None, description="Membership ID (Priority Pass, etc)")


class NavigationRequest(BaseModel):
    airport_code: str = Field(..., description="IATA airport code")
    from_location: str = Field(..., description="Starting location")
    to_location: str = Field(..., description="Destination")
    route_type: str = Field("fastest", description="Route preference: fastest, accessible, scenic")
    user_preferences: Optional[dict] = Field(None, description="User navigation preferences")


class DiningAvailabilityRequest(BaseModel):
    restaurant_id: str = Field(..., description="Restaurant ID")
    party_size: int = Field(..., ge=1, le=20, description="Party size")
    preferred_time: datetime = Field(..., description="Preferred dining time")
    duration_minutes: int = Field(60, description="Expected meal duration")


@router.get("/amenities/{airport_code}")
async def get_airport_amenities(
    airport_code: str,
    terminal: Optional[str] = Query(None),
    amenity_types: Optional[str] = Query(None, description="Comma-separated amenity types"),
    current_user: User = Depends(get_current_user)
):
    """Get amenities at a specific airport."""
    try:
        # Parse amenity types
        types_list = None
        if amenity_types:
            types_list = [t.strip() for t in amenity_types.split(",")]
        
        # Get user preferences
        user_preferences = {
            "dietary_restrictions": getattr(current_user, "dietary_restrictions", []),
            "preferred_amenities": getattr(current_user, "preferred_amenities", []),
            "max_price_range": getattr(current_user, "price_preference", "$$$"),
            "min_rating": 4.0  # Default minimum rating
        }
        
        amenities = await amenities_service.get_airport_amenities(
            airport_code,
            terminal,
            types_list,
            user_preferences
        )
        
        return {
            "airport_code": airport_code,
            "terminal": terminal,
            "amenities": amenities,
            "total": len(amenities)
        }
        
    except Exception as e:
        logger.error(f"Failed to get amenities: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve amenities")


@router.get("/recommendations")
async def get_amenity_recommendations(
    airport: str = Query(..., description="IATA airport code"),
    terminal: str = Query(..., description="Terminal identifier"),
    wait_time_minutes: int = Query(..., ge=0, le=480, description="Available wait time"),
    current_user: User = Depends(get_current_user)
):
    """Get personalized amenity recommendations based on wait time."""
    try:
        user_preferences = {
            "dietary_restrictions": getattr(current_user, "dietary_restrictions", []),
            "preferred_amenities": getattr(current_user, "preferred_amenities", []),
            "max_price_range": getattr(current_user, "price_preference", "$$$")
        }
        
        recommendations = await amenities_service.get_recommendations_by_wait_time(
            airport,
            terminal,
            wait_time_minutes,
            user_preferences
        )
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate recommendations")


@router.get("/lounges/{lounge_id}/access-options")
async def get_lounge_access_options(
    lounge_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get available access options for a specific lounge."""
    try:
        # Mock flight details - in production would come from user's itinerary
        flight_details = {
            "airline": "UA",
            "flight_number": "UA123",
            "class": "economy",
            "departure_time": datetime.utcnow().isoformat()
        }
        
        access_options = await amenities_service.get_lounge_access_options(
            lounge_id,
            str(current_user.id),
            flight_details
        )
        
        return {
            "lounge_id": lounge_id,
            "access_options": access_options,
            "total_options": len(access_options)
        }
        
    except Exception as e:
        logger.error(f"Failed to get lounge access options: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve access options")


@router.post("/dining/check-availability")
async def check_dining_availability(
    request: DiningAvailabilityRequest,
    current_user: User = Depends(get_current_user)
):
    """Check restaurant availability."""
    try:
        availability = await amenities_service.check_dining_availability(
            request.restaurant_id,
            request.party_size,
            request.preferred_time,
            request.duration_minutes
        )
        
        if not availability:
            raise HTTPException(status_code=404, detail="No availability found")
        
        return availability
        
    except Exception as e:
        logger.error(f"Failed to check dining availability: {e}")
        raise HTTPException(status_code=500, detail="Failed to check availability")


@router.post("/amenities/book")
async def book_amenity(
    booking: BookingRequest,
    current_user: User = Depends(get_current_user)
):
    """Book an airport amenity (lounge, restaurant, etc)."""
    try:
        # Prepare booking details
        booking_details = booking.dict()
        booking_details["user_name"] = current_user.name
        booking_details["user_email"] = current_user.email
        booking_details["user_phone"] = getattr(current_user, "phone", None)
        
        # Make booking
        result = await amenities_service.book_amenity(
            booking.amenity_id,
            str(current_user.id),
            booking_details
        )
        
        if not result:
            raise HTTPException(status_code=400, detail="Booking failed")
        
        # Log commission if applicable
        if result.get("commission"):
            logger.info(
                f"Amenity booking commission: ${result['commission']:.2f} "
                f"for booking {result['booking_id']}"
            )
        
        return {
            "success": True,
            "booking": result,
            "message": "Booking confirmed successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to book amenity: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete booking")


@router.post("/terminal/navigate")
async def get_terminal_navigation(
    request: NavigationRequest,
    current_user: User = Depends(get_current_user)
):
    """Get navigation route within terminal."""
    try:
        route = await navigation_service.calculate_route(
            request.airport_code,
            request.from_location,
            request.to_location,
            request.route_type,
            request.user_preferences
        )
        
        if not route:
            raise HTTPException(status_code=404, detail="Unable to calculate route")
        
        return {
            "route": route,
            "walking_time_minutes": route.total_walking_time_minutes,
            "distance_meters": route.total_distance_meters
        }
        
    except Exception as e:
        logger.error(f"Failed to calculate route: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate navigation")


@router.get("/terminal/nearby-amenities")
async def get_nearby_amenities(
    location: str = Query(..., description="Current location in terminal"),
    amenity_type: str = Query(None, description="Type of amenity to find"),
    max_results: int = Query(3, ge=1, le=10),
    current_user: User = Depends(get_current_user)
):
    """Find nearest amenities of specified type."""
    try:
        amenities = await navigation_service.find_nearest_amenity(
            location,
            amenity_type or "all",
            max_results
        )
        
        return {
            "current_location": location,
            "amenity_type": amenity_type,
            "nearby_amenities": amenities
        }
        
    except Exception as e:
        logger.error(f"Failed to find nearby amenities: {e}")
        raise HTTPException(status_code=500, detail="Failed to find amenities")


@router.get("/terminal/security-wait-times")
async def get_security_wait_times(
    airport: str = Query(..., description="IATA airport code"),
    terminal: str = Query(..., description="Terminal identifier"),
    current_user: User = Depends(get_current_user)
):
    """Get current security checkpoint wait times."""
    try:
        wait_times = await navigation_service.get_security_wait_times(
            airport,
            terminal
        )
        
        return wait_times
        
    except Exception as e:
        logger.error(f"Failed to get security wait times: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve wait times")


@router.get("/terminal/accessibility-info")
async def get_accessibility_services(
    airport: str = Query(..., description="IATA airport code"),
    terminal: str = Query(..., description="Terminal identifier"),
    current_user: User = Depends(get_current_user)
):
    """Get information about accessibility services."""
    try:
        services = await navigation_service.get_accessibility_services(
            airport,
            terminal
        )
        
        return services
        
    except Exception as e:
        logger.error(f"Failed to get accessibility info: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve accessibility information")