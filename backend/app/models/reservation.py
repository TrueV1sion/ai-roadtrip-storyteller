from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, JSON, func
from sqlalchemy.orm import relationship
import uuid

from app.db.base import Base


class Reservation(Base):
    """Reservation database model."""
    __tablename__ = "reservations"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Reservation details
    type = Column(String, nullable=False)  # Restaurant, attraction, etc.
    provider_id = Column(String, nullable=True)  # ID from external provider if applicable
    venue_name = Column(String, nullable=False)
    venue_id = Column(String, nullable=True)  # External ID for the venue if available
    venue_address = Column(Text, nullable=True)
    reservation_time = Column(DateTime, nullable=False, index=True)
    party_size = Column(String, nullable=False)  # Store as string for flexibility (e.g., "2 adults, 1 child")
    special_requests = Column(Text, nullable=True)
    
    # Additional information
    confirmation_number = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
    
    # Status and metadata
    status = Column(String, nullable=False)
    reservation_metadata = Column(JSON, nullable=True)  # For provider-specific details
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    cancelled_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="reservations")
    
    def __repr__(self):
        return f"<Reservation {self.id} - {self.venue_name} at {self.reservation_time}>"
    
    def to_dict(self):
        """Convert reservation to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type,
            "venue_name": self.venue_name,
            "venue_address": self.venue_address,
            "reservation_time": self.reservation_time.isoformat() if self.reservation_time else None,
            "party_size": self.party_size,
            "special_requests": self.special_requests,
            "confirmation_number": self.confirmation_number,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
        }