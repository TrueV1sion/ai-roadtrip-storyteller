"""CRUD operations for Booking model."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.crud.optimized_crud_base import CRUDBase
from app.models.booking import Booking, BookingStatus
from app.schemas.booking import BookingCreate, BookingUpdate


class CRUDBooking(CRUDBase[Booking, BookingCreate, BookingUpdate]):
    """CRUD operations for bookings."""
    
    def get_by_reference(
        self, db: Session, *, booking_reference: str
    ) -> Optional[Booking]:
        """Get booking by reference number."""
        return db.query(Booking).filter(
            Booking.booking_reference == booking_reference
        ).first()
    
    def get_user_bookings(
        self, db: Session, *, user_id: str, skip: int = 0, limit: int = 100
    ) -> List[Booking]:
        """Get all bookings for a user."""
        return (
            db.query(Booking)
            .filter(Booking.user_id == user_id)
            .order_by(Booking.booking_date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_active_bookings(
        self, db: Session, *, user_id: str, skip: int = 0, limit: int = 100
    ) -> List[Booking]:
        """Get active bookings for a user (pending or confirmed)."""
        return (
            db.query(Booking)
            .filter(
                Booking.user_id == user_id,
                Booking.booking_status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED])
            )
            .order_by(Booking.service_date.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def update_status(
        self, db: Session, *, db_obj: Booking, status: BookingStatus
    ) -> Booking:
        """Update booking status."""
        update_data = {"booking_status": status, "updated_at": datetime.utcnow()}
        return super().update(db, db_obj=db_obj, obj_in=update_data)
    
    def get_by_partner_booking_id(
        self, db: Session, *, partner_booking_id: str
    ) -> Optional[Booking]:
        """Get booking by partner's booking ID."""
        return db.query(Booking).filter(
            Booking.partner_booking_id == partner_booking_id
        ).first()
    
    def get_by_date_range(
        self, db: Session, *, 
        user_id: Optional[str] = None,
        start_date: datetime = None,
        end_date: datetime = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Booking]:
        """Get bookings within a date range."""
        query = db.query(Booking)
        
        if user_id:
            query = query.filter(Booking.user_id == user_id)
        if start_date:
            query = query.filter(Booking.service_date >= start_date)
        if end_date:
            query = query.filter(Booking.service_date <= end_date)
        
        return query.order_by(Booking.service_date.asc()).offset(skip).limit(limit).all()


crud_booking = CRUDBooking(Booking)