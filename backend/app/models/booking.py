"""Booking model for tracking transactions."""

from enum import Enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.core.enums import BookingType



class BookingStatus(str, Enum):
    """Booking status options."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class Booking(Base):
    """Booking model for tracking all transactions."""
    
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_reference = Column(String(100), unique=True, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    partner_id = Column(Integer, ForeignKey("partners.id"), nullable=False, index=True)
    booking_type = Column(SQLEnum(BookingType), nullable=False)
    booking_status = Column(SQLEnum(BookingStatus), nullable=False, default=BookingStatus.PENDING)
    booking_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    service_date = Column(DateTime, nullable=False)
    gross_amount = Column(Numeric(10, 2), nullable=False)
    net_amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    partner_booking_id = Column(String(100), nullable=True)
    booking_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="bookings")
    partner = relationship("Partner", back_populates="bookings")
    commission = relationship("Commission", back_populates="booking", uselist=False)