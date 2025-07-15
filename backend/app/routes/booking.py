"""Booking API endpoints."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.core.auth import get_current_user
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.booking import BookingStatus
from backend.app.services.booking_service import BookingService
from backend.app.schemas.booking import (
    BookingCreate,
    BookingUpdate,
    BookingResponse,
    BookingListResponse
)
from backend.app.core.logger import logger


router = APIRouter(
    prefix="/api/bookings",
    tags=["bookings"]
)


@router.post("/", response_model=BookingResponse)
async def create_booking(
    booking_data: BookingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new booking.
    
    This endpoint creates a booking and automatically calculates the commission
    based on the partner's commission rates.
    """
    try:
        booking_service = BookingService(db)
        booking = booking_service.create_booking(
            user_id=current_user.id,
            booking_data=booking_data
        )
        
        # Enrich response with commission data
        response = BookingResponse.from_orm(booking)
        if booking.commission:
            response.commission_amount = booking.commission.commission_amount
            response.commission_rate = booking.commission.commission_rate
        if booking.partner:
            response.partner_name = booking.partner.name
        
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating booking: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create booking")


@router.get("/", response_model=BookingListResponse)
async def list_bookings(
    status: Optional[BookingStatus] = Query(None, description="Filter by booking status"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List user's bookings.
    
    Returns a paginated list of bookings for the authenticated user.
    """
    try:
        booking_service = BookingService(db)
        offset = (page - 1) * per_page
        
        bookings = booking_service.get_user_bookings(
            user_id=current_user.id,
            status=status,
            limit=per_page,
            offset=offset
        )
        
        # Get total count
        from sqlalchemy import func
        from backend.app.models.booking import Booking
        
        query = db.query(func.count(Booking.id)).filter(
            Booking.user_id == current_user.id
        )
        if status:
            query = query.filter(Booking.booking_status == status)
        total = query.scalar()
        
        # Enrich responses
        booking_responses = []
        for booking in bookings:
            response = BookingResponse.from_orm(booking)
            if booking.commission:
                response.commission_amount = booking.commission.commission_amount
                response.commission_rate = booking.commission.commission_rate
            if booking.partner:
                response.partner_name = booking.partner.name
            booking_responses.append(response)
        
        return BookingListResponse(
            bookings=booking_responses,
            total=total,
            page=page,
            per_page=per_page
        )
    except Exception as e:
        logger.error(f"Error listing bookings: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list bookings")


@router.get("/{booking_reference}", response_model=BookingResponse)
async def get_booking(
    booking_reference: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get booking details by reference.
    
    Returns detailed information about a specific booking.
    """
    try:
        booking_service = BookingService(db)
        booking = booking_service.get_booking_by_reference(
            booking_reference=booking_reference,
            user_id=current_user.id
        )
        
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        # Enrich response
        response = BookingResponse.from_orm(booking)
        if booking.commission:
            response.commission_amount = booking.commission.commission_amount
            response.commission_rate = booking.commission.commission_rate
        if booking.partner:
            response.partner_name = booking.partner.name
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching booking: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch booking")


@router.patch("/{booking_id}/status")
async def update_booking_status(
    booking_id: int,
    status: BookingStatus,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update booking status.
    
    Updates the status of a booking following valid status transitions.
    """
    try:
        booking_service = BookingService(db)
        booking = booking_service.update_booking_status(
            booking_id=booking_id,
            new_status=status,
            user_id=current_user.id
        )
        
        return {
            "message": "Booking status updated successfully",
            "booking_reference": booking.booking_reference,
            "new_status": booking.booking_status
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating booking status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update booking status")


@router.post("/{booking_id}/cancel")
async def cancel_booking(
    booking_id: int,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel a booking.
    
    Cancels a booking and updates the associated commission status.
    """
    try:
        booking_service = BookingService(db)
        booking = booking_service.cancel_booking(
            booking_id=booking_id,
            user_id=current_user.id,
            reason=reason
        )
        
        return {
            "message": "Booking cancelled successfully",
            "booking_reference": booking.booking_reference,
            "status": booking.booking_status
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error cancelling booking: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cancel booking")