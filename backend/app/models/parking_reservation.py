"""Parking reservation model for airport and venue parking."""

from sqlalchemy import Column, String, DateTime, Boolean, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.db.base import Base


class ParkingReservation(Base):
    """Parking reservation model for tracking parking bookings."""
    
    __tablename__ = "parking_reservations"
    
    # Primary key is inherited from Reservation table (1-to-1 relationship)
    id = Column(String, ForeignKey("reservations.id"), primary_key=True)
    
    # Parking location details
    parking_type = Column(String, nullable=False)  # airport, venue, etc.
    location_name = Column(String, nullable=False)
    terminal = Column(String, nullable=True)
    lot_name = Column(String, nullable=True)
    spot_number = Column(String, nullable=True)
    
    # Vehicle information
    vehicle_make = Column(String, nullable=True)
    vehicle_model = Column(String, nullable=True)
    vehicle_color = Column(String, nullable=True)
    license_plate = Column(String, nullable=True)
    
    # Parking duration
    check_in_time = Column(DateTime, nullable=False)
    check_out_time = Column(DateTime, nullable=False)
    
    # Pricing
    daily_rate = Column(Float, nullable=True)
    total_cost = Column(Float, nullable=True)
    
    # Photo documentation
    parking_photo_url = Column(String, nullable=True)
    photo_uploaded_at = Column(DateTime, nullable=True)
    photo_metadata = Column(JSON, nullable=True)
    
    # Return journey features
    return_reminder_sent = Column(Boolean, default=False, nullable=True)
    return_journey_scheduled = Column(Boolean, default=False, nullable=True)
    estimated_pickup_time = Column(DateTime, nullable=True)
    
    # Flight information (for airport parking)
    outbound_flight = Column(String, nullable=True)
    return_flight = Column(String, nullable=True)
    airline = Column(String, nullable=True)
    
    # Relationship to parent reservation
    reservation = relationship("Reservation", back_populates="parking_details", uselist=False)
    
    def __repr__(self):
        return f"<ParkingReservation {self.id} - {self.location_name}>"