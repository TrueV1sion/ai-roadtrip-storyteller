"""Partner model for managing booking partners."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship

from backend.app.db.base import Base


class Partner(Base):
    """Partner model for managing external booking partners."""
    
    __tablename__ = "partners"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    partner_code = Column(String(50), unique=True, nullable=False)
    api_endpoint = Column(String(500), nullable=True)
    api_key = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    bookings = relationship("Booking", back_populates="partner")
    commission_rates = relationship("CommissionRate", back_populates="partner")