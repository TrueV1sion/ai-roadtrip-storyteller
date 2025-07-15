"""Airport parking routes with photo upload functionality."""

import io
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_

from backend.app.core.auth import get_current_user
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.models.parking_reservation import ParkingReservation
from backend.app.services.photo_storage_service import photo_storage_service
from backend.app.services.return_journey_service import ReturnJourneyService
from backend.app.services.booking_service import BookingService
from backend.app.schemas.booking import BookingCreate
from backend.app.core.logger import logger


router = APIRouter(
    prefix="/api/airport-parking",
    tags=["airport-parking"]
)


@router.post("/reservations/{booking_reference}/upload-photo")
async def upload_parking_photo(
    booking_reference: str,
    photo: UploadFile = File(...),
    spot_number: Optional[str] = Form(None),
    lot_name: Optional[str] = Form(None),
    terminal: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a photo of the parking spot for a reservation.
    
    This endpoint allows users to upload a photo of their parking location
    to help them find their car when they return.
    """
    try:
        # Validate file type
        allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/heic", "image/heif"]
        if photo.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
            )
        
        # Get parking reservation
        reservation = db.query(ParkingReservation).filter(
            and_(
                ParkingReservation.confirmation_number == booking_reference,
                ParkingReservation.user_id == current_user.id
            )
        ).first()
        
        if not reservation:
            raise HTTPException(status_code=404, detail="Parking reservation not found")
        
        # Read file content
        file_content = await photo.read()
        file_obj = io.BytesIO(file_content)
        
        # Get file extension
        file_extension = photo.filename.split(".")[-1].lower()
        if file_extension not in ["jpg", "jpeg", "png", "heic", "heif"]:
            file_extension = "jpg"
        
        # Upload to Google Cloud Storage
        photo_url = photo_storage_service.upload_parking_photo(
            file=file_obj,
            user_id=current_user.id,
            booking_reference=booking_reference,
            file_extension=file_extension
        )
        
        if not photo_url:
            raise HTTPException(status_code=500, detail="Failed to upload photo")
        
        # Update reservation with photo URL and additional details
        reservation.parking_photo_url = photo_url
        reservation.photo_uploaded_at = datetime.utcnow()
        
        if spot_number:
            reservation.spot_number = spot_number
        if lot_name:
            reservation.lot_name = lot_name
        if terminal:
            reservation.terminal = terminal
        
        # Store photo metadata
        reservation.photo_metadata = {
            "original_filename": photo.filename,
            "content_type": photo.content_type,
            "size_bytes": len(file_content),
            "uploaded_via": "mobile_app"
        }
        
        db.commit()
        
        # Schedule return journey automation
        return_service = ReturnJourneyService(db)
        scheduling_result = return_service.schedule_return_journey(
            parking_reservation_id=reservation.id,
            user_id=current_user.id
        )
        
        return {
            "message": "Photo uploaded successfully",
            "photo_url": photo_url,
            "booking_reference": booking_reference,
            "return_journey_scheduled": scheduling_result.get("scheduled", False),
            "estimated_pickup_time": scheduling_result.get("estimated_pickup_time")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading parking photo: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload parking photo")


@router.get("/reservations/{booking_reference}/parking-details")
async def get_parking_details(
    booking_reference: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get parking details including photo for a reservation.
    
    Returns all parking information including the photo URL to help
    users locate their vehicle.
    """
    try:
        reservation = db.query(ParkingReservation).filter(
            and_(
                ParkingReservation.confirmation_number == booking_reference,
                ParkingReservation.user_id == current_user.id
            )
        ).first()
        
        if not reservation:
            raise HTTPException(status_code=404, detail="Parking reservation not found")
        
        # Get return journey context if photo exists
        return_service = ReturnJourneyService(db)
        parking_context = None
        if reservation.parking_photo_url:
            parking_context = return_service.get_parking_photo_context(reservation.id)
        
        return {
            "booking_reference": booking_reference,
            "location": reservation.location_name,
            "terminal": reservation.terminal,
            "lot_name": reservation.lot_name,
            "spot_number": reservation.spot_number,
            "vehicle": {
                "make": reservation.vehicle_make,
                "model": reservation.vehicle_model,
                "color": reservation.vehicle_color,
                "license_plate": reservation.license_plate
            },
            "parking_times": {
                "check_in": reservation.check_in_time.isoformat(),
                "check_out": reservation.check_out_time.isoformat()
            },
            "photo": {
                "url": reservation.parking_photo_url,
                "uploaded_at": reservation.photo_uploaded_at.isoformat() if reservation.photo_uploaded_at else None
            },
            "return_journey": {
                "scheduled": reservation.return_journey_scheduled,
                "estimated_pickup_time": reservation.estimated_pickup_time.isoformat() if reservation.estimated_pickup_time else None,
                "reminder_sent": reservation.return_reminder_sent
            },
            "parking_context": parking_context
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting parking details: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get parking details")


@router.post("/reservations")
async def create_parking_reservation(
    location_name: str = Form(...),
    parking_type: str = Form("airport"),
    check_in_time: datetime = Form(...),
    check_out_time: datetime = Form(...),
    vehicle_make: Optional[str] = Form(None),
    vehicle_model: Optional[str] = Form(None),
    vehicle_color: Optional[str] = Form(None),
    license_plate: Optional[str] = Form(None),
    terminal: Optional[str] = Form(None),
    outbound_flight: Optional[str] = Form(None),
    return_flight: Optional[str] = Form(None),
    airline: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new airport parking reservation.
    
    This endpoint creates a parking reservation that can later have
    a photo attached for easy vehicle location.
    """
    try:
        # Create base booking data
        booking_data = BookingCreate(
            partner_id=1,  # Airport parking partner
            service_type="parking",
            booking_datetime=check_in_time,
            guest_count=1,
            total_amount=0.0,  # Will be calculated by service
            guest_name=current_user.username,
            guest_email=current_user.email,
            special_requests=f"Parking from {check_in_time} to {check_out_time}"
        )
        
        # Create booking through booking service
        booking_service = BookingService(db)
        booking = booking_service.create_booking(
            user_id=current_user.id,
            booking_data=booking_data
        )
        
        # Create parking-specific reservation
        parking_reservation = ParkingReservation(
            id=booking.id,
            user_id=current_user.id,
            type="parking",
            venue_name=location_name,
            reservation_time=check_in_time,
            party_size="1 vehicle",
            status="confirmed",
            confirmation_number=booking.booking_reference,
            parking_type=parking_type,
            location_name=location_name,
            terminal=terminal,
            check_in_time=check_in_time,
            check_out_time=check_out_time,
            vehicle_make=vehicle_make,
            vehicle_model=vehicle_model,
            vehicle_color=vehicle_color,
            license_plate=license_plate,
            outbound_flight=outbound_flight,
            return_flight=return_flight,
            airline=airline,
            metadata={
                "booking_id": booking.id,
                "origin_address": current_user.preferences.get("home_address") if hasattr(current_user, "preferences") else None
            }
        )
        
        db.add(parking_reservation)
        db.commit()
        
        return {
            "message": "Parking reservation created successfully",
            "booking_reference": booking.booking_reference,
            "reservation_id": parking_reservation.id,
            "location": location_name,
            "check_in": check_in_time.isoformat(),
            "check_out": check_out_time.isoformat(),
            "upload_photo_url": f"/api/airport-parking/reservations/{booking.booking_reference}/upload-photo"
        }
        
    except Exception as e:
        logger.error(f"Error creating parking reservation: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create parking reservation")


@router.get("/upcoming-returns")
async def get_upcoming_returns(
    hours_ahead: int = Query(24, description="Hours to look ahead for returns"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get upcoming parking returns for the user.
    
    Returns a list of parking reservations with upcoming check-out times
    to help users prepare for their return journey.
    """
    try:
        return_service = ReturnJourneyService(db)
        
        # Get all pending returns
        all_pending = return_service.check_pending_returns()
        
        # Filter for current user
        user_pending = [
            reservation for reservation in all_pending
            if reservation["user_id"] == current_user.id
        ]
        
        return {
            "upcoming_returns": user_pending,
            "total": len(user_pending)
        }
        
    except Exception as e:
        logger.error(f"Error getting upcoming returns: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get upcoming returns")


@router.post("/reservations/{booking_reference}/send-reminder")
async def send_return_reminder(
    booking_reference: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger a return journey reminder.
    
    Sends a reminder with the parking photo and helps plan the return journey.
    """
    try:
        # Get reservation
        reservation = db.query(ParkingReservation).filter(
            and_(
                ParkingReservation.confirmation_number == booking_reference,
                ParkingReservation.user_id == current_user.id
            )
        ).first()
        
        if not reservation:
            raise HTTPException(status_code=404, detail="Parking reservation not found")
        
        if not reservation.parking_photo_url:
            raise HTTPException(
                status_code=400,
                detail="No parking photo uploaded. Please upload a photo first."
            )
        
        # Send reminder
        return_service = ReturnJourneyService(db)
        success = return_service.send_return_reminder(reservation.id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send reminder")
        
        return {
            "message": "Return journey reminder sent successfully",
            "booking_reference": booking_reference,
            "parking_location": reservation.location_name,
            "estimated_pickup_time": reservation.estimated_pickup_time.isoformat() if reservation.estimated_pickup_time else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending return reminder: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to send return reminder")