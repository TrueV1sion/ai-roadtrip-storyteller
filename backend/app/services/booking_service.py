"""Booking service for managing transactions."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from backend.app.models.booking import Booking, BookingStatus
from backend.app.models.partner import Partner
from backend.app.schemas.booking import BookingCreate, BookingUpdate
from backend.app.services.commission_calculator import CommissionCalculator
from backend.app.core.logger import logger


class BookingService:
    """Service for managing bookings and related operations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.commission_calculator = CommissionCalculator(db)
    
    def create_booking(
        self,
        user_id: int,
        booking_data: BookingCreate
    ) -> Booking:
        """Create a new booking with commission calculation."""
        # Verify partner exists and is active
        partner = self.db.query(Partner).filter(
            and_(
                Partner.id == booking_data.partner_id,
                Partner.is_active == True
            )
        ).first()
        
        if not partner:
            raise ValueError(f"Partner {booking_data.partner_id} not found or inactive")
        
        # Generate booking reference
        booking_reference = f"BK-{uuid.uuid4().hex[:8].upper()}"
        
        # Calculate commission
        temp_booking = Booking(
            partner_id=booking_data.partner_id,
            booking_type=booking_data.booking_type,
            gross_amount=booking_data.gross_amount
        )
        
        commission_amount, commission_rate = self.commission_calculator.calculate_commission(
            temp_booking
        )
        
        # Calculate net amount
        net_amount = booking_data.gross_amount - commission_amount
        
        # Create booking
        booking = Booking(
            booking_reference=booking_reference,
            user_id=user_id,
            partner_id=booking_data.partner_id,
            booking_type=booking_data.booking_type,
            booking_status=BookingStatus.PENDING,
            booking_date=datetime.utcnow(),
            service_date=booking_data.service_date,
            gross_amount=booking_data.gross_amount,
            net_amount=net_amount,
            currency=booking_data.currency,
            partner_booking_id=booking_data.partner_booking_id,
            metadata=booking_data.metadata
        )
        
        self.db.add(booking)
        self.db.commit()
        self.db.refresh(booking)
        
        # Create commission record
        self.commission_calculator.create_commission_record(
            booking,
            commission_amount,
            commission_rate
        )
        
        logger.info(
            f"Created booking {booking.booking_reference} for user {user_id} "
            f"with commission {commission_amount} ({commission_rate * 100}%)"
        )
        
        return booking
    
    def update_booking_status(
        self,
        booking_id: int,
        new_status: BookingStatus,
        user_id: Optional[int] = None
    ) -> Booking:
        """Update booking status."""
        query = self.db.query(Booking).filter(Booking.id == booking_id)
        
        if user_id:
            query = query.filter(Booking.user_id == user_id)
        
        booking = query.first()
        
        if not booking:
            raise ValueError(f"Booking {booking_id} not found")
        
        # Validate status transition
        valid_transitions = {
            BookingStatus.PENDING: [BookingStatus.CONFIRMED, BookingStatus.CANCELLED],
            BookingStatus.CONFIRMED: [BookingStatus.COMPLETED, BookingStatus.CANCELLED],
            BookingStatus.COMPLETED: [BookingStatus.REFUNDED],
            BookingStatus.CANCELLED: [],
            BookingStatus.REFUNDED: []
        }
        
        if new_status not in valid_transitions.get(booking.booking_status, []):
            raise ValueError(
                f"Invalid status transition from {booking.booking_status} to {new_status}"
            )
        
        booking.booking_status = new_status
        self.db.commit()
        self.db.refresh(booking)
        
        # Update commission status if booking is completed
        if new_status == BookingStatus.COMPLETED and booking.commission:
            from backend.app.models.commission import CommissionStatus
            self.commission_calculator.update_commission_status(
                booking.commission.id,
                CommissionStatus.APPROVED
            )
        
        logger.info(f"Updated booking {booking.booking_reference} status to {new_status}")
        
        return booking
    
    def get_user_bookings(
        self,
        user_id: int,
        status: Optional[BookingStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Booking]:
        """Get bookings for a user."""
        query = self.db.query(Booking).filter(Booking.user_id == user_id)
        
        if status:
            query = query.filter(Booking.booking_status == status)
        
        bookings = query.order_by(
            Booking.booking_date.desc()
        ).limit(limit).offset(offset).all()
        
        return bookings
    
    def get_booking_by_reference(
        self,
        booking_reference: str,
        user_id: Optional[int] = None
    ) -> Optional[Booking]:
        """Get booking by reference number."""
        query = self.db.query(Booking).filter(
            Booking.booking_reference == booking_reference
        )
        
        if user_id:
            query = query.filter(Booking.user_id == user_id)
        
        return query.first()
    
    def cancel_booking(
        self,
        booking_id: int,
        user_id: int,
        reason: Optional[str] = None
    ) -> Booking:
        """Cancel a booking."""
        booking = self.update_booking_status(
            booking_id,
            BookingStatus.CANCELLED,
            user_id
        )
        
        if reason and booking.metadata:
            booking.metadata["cancellation_reason"] = reason
        elif reason:
            booking.metadata = {"cancellation_reason": reason}
        
        self.db.commit()
        
        # Update commission status
        if booking.commission:
            from backend.app.models.commission import CommissionStatus
            self.commission_calculator.update_commission_status(
                booking.commission.id,
                CommissionStatus.DISPUTED,
                notes=f"Booking cancelled: {reason}"
            )
        
        return booking