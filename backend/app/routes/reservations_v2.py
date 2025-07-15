from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from ..database import get_db
from ..core.auth import get_current_user
from ..schemas.reservation import (
    ReservationCreate,
    ReservationResponse,
    ReservationUpdate,
    ReservationSearchRequest,
    ReservationSearchResponse,
    AvailabilityCheckRequest,
    AvailabilityCheckResponse
)
from ..crud.crud_reservation import crud_reservation
from ..models.user import User
from ..models.reservation import Reservation
from ..services.reservation_management_service import (
    ReservationManagementService,
    BookingProvider
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize reservation management service
reservation_service = ReservationManagementService()

@router.post("/search", response_model=ReservationSearchResponse)
async def search_restaurants(
    search_request: ReservationSearchRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Search for available restaurants across all providers
    """
    try:
        results = await reservation_service.search_all_providers(
            query=search_request.query,
            location=search_request.location,
            date=search_request.date,
            party_size=search_request.party_size,
            cuisine=search_request.cuisines,
            price_range=search_request.price_range,
            amenities=search_request.amenities
        )
        
        # Transform results for response
        formatted_results = []
        for result in results:
            formatted_results.append({
                "provider": result["provider"],
                "venueId": result["venue_id"],
                "name": result["name"],
                "cuisine": result.get("cuisine", "Various"),
                "rating": result.get("rating", 4.0),
                "priceRange": result.get("price_range", "2"),
                "distance": result.get("distance", 0),
                "availableTimes": result.get("available_times", []),
                "imageUrl": result.get("image_url"),
                "description": result.get("description"),
                "amenities": result.get("amenities", [])
            })
        
        return ReservationSearchResponse(results=formatted_results)
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail="Search failed")

@router.post("/book", response_model=ReservationResponse)
async def create_reservation(
    reservation_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new reservation through the unified booking system
    """
    try:
        # Extract provider from request
        provider_str = reservation_data.get("provider", "opentable")
        provider = BookingProvider[provider_str.upper()]
        
        # Create reservation through service
        booking_result = await reservation_service.create_reservation(
            user_id=str(current_user.id),
            provider=provider,
            venue_id=reservation_data["venueId"],
            date_time=datetime.fromisoformat(reservation_data["dateTime"].replace('Z', '+00:00')),
            party_size=reservation_data["partySize"],
            customer_info=reservation_data["customerInfo"],
            special_requests=reservation_data.get("specialRequests"),
            occasion_type=reservation_data.get("occasionType"),
            dietary_restrictions=reservation_data.get("dietaryRestrictions", []),
            marketing_opt_in=reservation_data.get("marketingOptIn", False)
        )
        
        # Store in database
        db_reservation = Reservation(
            user_id=current_user.id,
            provider=provider_str,
            venue_id=reservation_data["venueId"],
            venue_name=booking_result.get("venue_name", "Restaurant"),
            confirmation_number=booking_result["confirmation_number"],
            date_time=datetime.fromisoformat(reservation_data["dateTime"].replace('Z', '+00:00')),
            party_size=reservation_data["partySize"],
            status="confirmed",
            special_requests=reservation_data.get("specialRequests"),
            customer_info=reservation_data["customerInfo"],
            cancellation_policy=booking_result.get("cancellation_policy"),
            modification_allowed=booking_result.get("modification_allowed", True),
            cancellation_deadline=booking_result.get("cancellation_deadline")
        )
        db.add(db_reservation)
        db.commit()
        db.refresh(db_reservation)
        
        return ReservationResponse.from_orm(db_reservation)
    except Exception as e:
        logger.error(f"Booking error: {str(e)}")
        raise HTTPException(status_code=500, detail="Booking failed")

@router.get("/my-reservations", response_model=Dict[str, List[ReservationResponse]])
async def get_my_reservations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all user reservations organized by status
    """
    reservations = crud_reservation.get_multi_by_user(
        db=db,
        user_id=current_user.id,
        skip=0,
        limit=100
    )
    
    # Update status for past reservations
    now = datetime.utcnow()
    for reservation in reservations:
        if reservation.status == "confirmed" and reservation.date_time < now:
            reservation.status = "completed"
            db.commit()
    
    return {
        "reservations": [ReservationResponse.from_orm(r) for r in reservations]
    }

@router.post("/check-availability", response_model=AvailabilityCheckResponse)
async def check_availability(
    request: AvailabilityCheckRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Check availability for modification
    """
    try:
        provider = BookingProvider[request.provider.upper()]
        available_times = await reservation_service.check_availability(
            provider=provider,
            venue_id=request.venue_id,
            date=request.date,
            party_size=request.party_size
        )
        
        # Filter out the current reservation time if modifying
        if request.exclude_reservation_id:
            # Implementation depends on how times are stored
            pass
        
        return AvailabilityCheckResponse(available_times=available_times)
    except Exception as e:
        logger.error(f"Availability check error: {str(e)}")
        raise HTTPException(status_code=500, detail="Availability check failed")

@router.put("/{reservation_id}/modify", response_model=ReservationResponse)
async def modify_reservation(
    reservation_id: int,
    modification_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Modify an existing reservation
    """
    # Get existing reservation
    reservation = crud_reservation.get(db=db, id=reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    if reservation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        provider = BookingProvider[reservation.provider.upper()]
        
        # Modify through service
        modification_result = await reservation_service.modify_reservation(
            user_id=str(current_user.id),
            provider=provider,
            confirmation_number=reservation.confirmation_number,
            new_date_time=datetime.fromisoformat(modification_data["dateTime"].replace('Z', '+00:00')),
            new_party_size=modification_data.get("partySize", reservation.party_size),
            special_requests=modification_data.get("specialRequests")
        )
        
        # Update database
        reservation.date_time = datetime.fromisoformat(modification_data["dateTime"].replace('Z', '+00:00'))
        reservation.party_size = modification_data.get("partySize", reservation.party_size)
        reservation.special_requests = modification_data.get("specialRequests")
        db.commit()
        db.refresh(reservation)
        
        return ReservationResponse.from_orm(reservation)
    except Exception as e:
        logger.error(f"Modification error: {str(e)}")
        raise HTTPException(status_code=500, detail="Modification failed")

@router.post("/{reservation_id}/cancel")
async def cancel_reservation(
    reservation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel a reservation
    """
    reservation = crud_reservation.get(db=db, id=reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    if reservation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        provider = BookingProvider[reservation.provider.upper()]
        
        # Cancel through service
        await reservation_service.cancel_reservation(
            user_id=str(current_user.id),
            provider=provider,
            confirmation_number=reservation.confirmation_number
        )
        
        # Update database
        reservation.status = "cancelled"
        db.commit()
        
        return {"detail": "Reservation cancelled successfully"}
    except Exception as e:
        logger.error(f"Cancellation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Cancellation failed")

@router.get("/upcoming-reminders")
async def get_upcoming_reminders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get reservations that need reminders
    """
    # Get reservations in the next 24 hours
    tomorrow = datetime.utcnow() + timedelta(days=1)
    
    upcoming_reservations = db.query(Reservation).filter(
        Reservation.user_id == current_user.id,
        Reservation.status == "confirmed",
        Reservation.date_time >= datetime.utcnow(),
        Reservation.date_time <= tomorrow
    ).all()
    
    return {
        "reminders": [
            {
                "reservation_id": r.id,
                "venue_name": r.venue_name,
                "date_time": r.date_time,
                "party_size": r.party_size,
                "confirmation_number": r.confirmation_number
            }
            for r in upcoming_reservations
        ]
    }

@router.post("/{reservation_id}/add-to-waitlist")
async def add_to_waitlist(
    reservation_id: int,
    waitlist_preferences: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add user to waitlist for a fully booked time slot
    """
    try:
        result = await reservation_service.add_to_waitlist(
            user_id=str(current_user.id),
            venue_id=waitlist_preferences["venue_id"],
            provider=BookingProvider[waitlist_preferences["provider"].upper()],
            desired_date=datetime.fromisoformat(waitlist_preferences["desired_date"].replace('Z', '+00:00')),
            party_size=waitlist_preferences["party_size"],
            time_flexibility=waitlist_preferences.get("time_flexibility", "1_hour"),
            contact_preferences=waitlist_preferences.get("contact_preferences", ["email", "sms"])
        )
        
        return {
            "waitlist_id": result["waitlist_id"],
            "position": result.get("position"),
            "estimated_wait": result.get("estimated_wait"),
            "message": "Successfully added to waitlist"
        }
    except Exception as e:
        logger.error(f"Waitlist error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to join waitlist")