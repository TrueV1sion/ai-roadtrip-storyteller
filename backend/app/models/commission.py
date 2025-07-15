"""Commission model for tracking revenue shares."""

from enum import Enum
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.core.enums import BookingType


class CommissionStatus(str, Enum):
    """Commission payment status."""
    PENDING = "pending"
    APPROVED = "approved"
    PAID = "paid"
    DISPUTED = "disputed"


class CommissionRate(Base):
    """Commission rate configuration by partner and booking type."""
    
    __tablename__ = "commission_rates"
    
    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey("partners.id"), nullable=False)
    booking_type = Column(SQLEnum(BookingType), nullable=False)
    base_rate = Column(Numeric(5, 4), nullable=False)  # e.g., 0.1500 for 15%
    tier_1_threshold = Column(Numeric(10, 2), nullable=True)
    tier_1_rate = Column(Numeric(5, 4), nullable=True)
    tier_2_threshold = Column(Numeric(10, 2), nullable=True)
    tier_2_rate = Column(Numeric(5, 4), nullable=True)
    tier_3_threshold = Column(Numeric(10, 2), nullable=True)
    tier_3_rate = Column(Numeric(5, 4), nullable=True)
    valid_from = Column(DateTime, nullable=False, default=datetime.utcnow)
    valid_to = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    partner = relationship("Partner", back_populates="commission_rates")
    commissions = relationship("Commission", back_populates="commission_rate")


class Commission(Base):
    """Commission record for each booking."""
    
    __tablename__ = "commissions"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    commission_rate_id = Column(Integer, ForeignKey("commission_rates.id"), nullable=False)
    commission_amount = Column(Numeric(10, 2), nullable=False)
    commission_rate = Column(Numeric(5, 4), nullable=False)
    commission_status = Column(SQLEnum(CommissionStatus), nullable=False, default=CommissionStatus.PENDING)
    payment_date = Column(DateTime, nullable=True)
    payment_reference = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    booking = relationship("Booking", back_populates="commission")
    commission_rate = relationship("CommissionRate", back_populates="commissions")