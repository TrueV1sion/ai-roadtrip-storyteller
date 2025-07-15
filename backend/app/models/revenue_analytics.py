"""Revenue analytics model for pre-calculated metrics."""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, Date, Numeric, DateTime, ForeignKey, UniqueConstraint, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.core.enums import BookingType


class RevenueAnalytics(Base):
    """Pre-calculated revenue analytics for performance."""
    
    __tablename__ = "revenue_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    partner_id = Column(Integer, ForeignKey("partners.id"), nullable=True, index=True)
    booking_type = Column(SQLEnum(BookingType), nullable=True)
    total_bookings = Column(Integer, nullable=False, default=0)
    completed_bookings = Column(Integer, nullable=False, default=0)
    cancelled_bookings = Column(Integer, nullable=False, default=0)
    gross_revenue = Column(Numeric(12, 2), nullable=False, default=0)
    net_revenue = Column(Numeric(12, 2), nullable=False, default=0)
    total_commission = Column(Numeric(12, 2), nullable=False, default=0)
    conversion_rate = Column(Numeric(5, 4), nullable=True)
    average_booking_value = Column(Numeric(10, 2), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('date', 'partner_id', 'booking_type', name='uq_revenue_analytics_date_partner_type'),
    )
    
    # Relationships
    partner = relationship("Partner")