from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.schemas.reservation import (
    ReservationCreate, 
    ReservationResponse, 
    ReservationUpdate,
    ReservationStatusUpdate,
    ReservationCancellation,
    RestaurantReservationCreate,
    VoiceReservationRequest
)
from app.services.reservation_agent import (
    get_reservation_agent, 
    ReservationAgent, 
    RestaurantReservationAgent,
    ReservationStatus
)
from app.models.user import User
from app.core.logger import get_logger
from app.core.security import get_current_active_user

router = APIRouter()
logger = get_logger(__name__)

# Keep RESERVATIONS dict for backward compatibility during transition
# This can be removed once all components are updated to use the database
RESERVATIONS: dict[str, dict] = {}


@router.get("/reservations", response_model=List[ReservationResponse], tags=["Reservations"])
async def list_user_reservations(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    reservation_agent: ReservationAgent = Depends(get_reservation_agent)
):
    """
    List all reservations for the current user.
    Optionally filter by status.
    """
    try:
        status_enum = ReservationStatus(status) if status else None
        reservations = await reservation_agent.get_user_reservations(
            user_id=current_user.id,
            status=status_enum
        )
        return reservations
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status value: {status}"
        )
    except Exception as e:
        logger.error(f"Error listing reservations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to list reservations"
        )


@router.post("/reservations", response_model=ReservationResponse, tags=["Reservations"])
async def create_reservation(
    reservation: ReservationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    reservation_agent: ReservationAgent = Depends(get_reservation_agent)
):
    """
    Create a new generic reservation.
    """
    try:
        new_reservation = await reservation_agent.create_reservation(
            user_id=current_user.id,
            reservation_type=reservation.type,
            venue_name=reservation.venue_name,
            venue_address=reservation.venue_address,
            reservation_time=reservation.reservation_time,
            party_size=reservation.party_size,
            special_requests=reservation.special_requests,
            contact_phone=reservation.contact_phone,
            contact_email=reservation.contact_email,
            metadata=reservation.metadata,
        )
        return new_reservation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating reservation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to create reservation"
        )


@router.post("/reservations/restaurant", response_model=ReservationResponse, tags=["Reservations"])
async def create_restaurant_reservation(
    reservation: RestaurantReservationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    reservation_agent: RestaurantReservationAgent = Depends(lambda db=db: get_reservation_agent("restaurant", db))
):
    """
    Create a new restaurant reservation with restaurant-specific details.
    """
    try:
        new_reservation = await reservation_agent.create_restaurant_reservation(
            user_id=current_user.id,
            restaurant_name=reservation.restaurant_name,
            restaurant_address=reservation.restaurant_address,
            reservation_time=reservation.reservation_time,
            party_size=reservation.party_size,
            special_requests=reservation.special_requests,
            cuisine_type=reservation.cuisine_type,
            restaurant_phone=reservation.restaurant_phone,
            contact_phone=reservation.contact_phone,
            contact_email=reservation.contact_email,
        )
        return new_reservation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating restaurant reservation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to create restaurant reservation"
        )


@router.post("/reservations/voice", response_model=ReservationResponse, tags=["Reservations"])
async def create_voice_reservation(
    request: VoiceReservationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    reservation_agent: ReservationAgent = Depends(get_reservation_agent)
):
    """
    Create a reservation based on a voice command.
    This endpoint uses AI to parse the voice command and extract reservation details.
    """
    try:
        # TODO: Implement AI parsing of voice commands to extract reservation details
        # For now, return a simple error that this is not yet implemented
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Voice reservation parsing is not yet implemented"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing voice reservation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to process voice reservation request"
        )


@router.get("/reservations/{reservation_id}", response_model=ReservationResponse, tags=["Reservations"])
async def get_reservation(
    reservation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    reservation_agent: ReservationAgent = Depends(get_reservation_agent)
):
    """Get details of a reservation by ID."""
    try:
        reservation = await reservation_agent.get_reservation(reservation_id)
        if not reservation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Reservation not found"
            )
        
        # Check that the reservation belongs to the current user
        if reservation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this reservation"
            )
            
        return reservation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching reservation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Error fetching reservation"
        )


@router.put("/reservations/{reservation_id}", response_model=ReservationResponse, tags=["Reservations"])
async def update_reservation(
    reservation_id: str,
    update: ReservationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    reservation_agent: ReservationAgent = Depends(get_reservation_agent)
):
    """
    Update an existing reservation.
    Only allowed for reservations in PENDING or CONFIRMED status.
    """
    try:
        # Get existing reservation
        reservation = await reservation_agent.get_reservation(reservation_id)
        if not reservation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Reservation not found"
            )
        
        # Check that the reservation belongs to the current user
        if reservation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update this reservation"
            )
            
        # Check that the reservation is in an updatable state
        if reservation.status not in [ReservationStatus.PENDING.value, ReservationStatus.CONFIRMED.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot update reservation in {reservation.status} status"
            )
        
        # TODO: Implement updating reservation details
        # This will require implementing additional methods in the reservation agent
        # For now, return a simple error that this is not yet implemented
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Updating reservation details is not yet implemented"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating reservation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to update reservation"
        )


@router.put("/reservations/{reservation_id}/status", response_model=ReservationResponse, tags=["Reservations"])
async def update_reservation_status(
    reservation_id: str,
    status_update: ReservationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    reservation_agent: ReservationAgent = Depends(get_reservation_agent)
):
    """
    Update the status of a reservation.
    """
    try:
        # Get existing reservation
        reservation = await reservation_agent.get_reservation(reservation_id)
        if not reservation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Reservation not found"
            )
        
        # Check that the reservation belongs to the current user
        if reservation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update this reservation"
            )
        
        # Update the status
        updated_reservation = await reservation_agent.update_reservation_status(
            reservation_id=reservation_id,
            status=status_update.status,
            confirmation_number=status_update.confirmation_number,
            metadata_updates=status_update.metadata_updates
        )
        
        return updated_reservation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating reservation status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to update reservation status"
        )


@router.delete("/reservations/{reservation_id}", response_model=ReservationResponse, tags=["Reservations"])
async def cancel_reservation(
    reservation_id: str,
    cancellation: Optional[ReservationCancellation] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    reservation_agent: ReservationAgent = Depends(get_reservation_agent)
):
    """
    Cancel a reservation.
    Optionally provide a reason for cancellation.
    """
    try:
        # Get existing reservation
        reservation = await reservation_agent.get_reservation(reservation_id)
        if not reservation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Reservation not found"
            )
        
        # Check that the reservation belongs to the current user
        if reservation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to cancel this reservation"
            )
        
        # Check that the reservation is in a cancellable state
        if reservation.status in [ReservationStatus.CANCELLED.value, ReservationStatus.COMPLETED.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel reservation in {reservation.status} status"
            )
        
        # Cancel the reservation
        cancellation_reason = cancellation.cancellation_reason if cancellation else None
        cancelled_reservation = await reservation_agent.cancel_reservation(
            reservation_id=reservation_id,
            cancellation_reason=cancellation_reason
        )
        
        return cancelled_reservation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling reservation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to cancel reservation"
        )