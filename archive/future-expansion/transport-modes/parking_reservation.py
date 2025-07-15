"""Parking reservation database model."""

from sqlalchemy import Column, String, DateTime, Float, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
import uuid

from app.models.reservation import Reservation


class ParkingReservation(Reservation):
    """Extended reservation model for parking-specific data."""
    __tablename__ = "parking_reservations"
    
    # Foreign key to base reservation
    id = Column(String, ForeignKey("reservations.id"), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Parking-specific fields
    parking_type = Column(String, nullable=False)  # airport, event, hotel, etc.
    location_name = Column(String, nullable=False)  # Airport name, venue name, etc.
    terminal = Column(String, nullable=True)  # For airport parking
    lot_name = Column(String, nullable=True)  # Specific parking lot
    spot_number = Column(String, nullable=True)  # Assigned spot if applicable
    
    # Vehicle information
    vehicle_make = Column(String, nullable=True)
    vehicle_model = Column(String, nullable=True)
    vehicle_color = Column(String, nullable=True)
    license_plate = Column(String, nullable=True)
    
    # Parking details
    check_in_time = Column(DateTime, nullable=False)
    check_out_time = Column(DateTime, nullable=False)
    daily_rate = Column(Float, nullable=True)
    total_cost = Column(Float, nullable=True)
    
    # Photo storage
    parking_photo_url = Column(String, nullable=True)  # URL to the parking spot photo
    photo_uploaded_at = Column(DateTime, nullable=True)
    photo_metadata = Column(JSON, nullable=True)  # Additional photo info
    
    # Return journey automation
    return_reminder_sent = Column(Boolean, default=False)
    return_journey_scheduled = Column(Boolean, default=False)
    estimated_pickup_time = Column(DateTime, nullable=True)
    
    # Flight information (for airport parking)
    outbound_flight = Column(String, nullable=True)
    return_flight = Column(String, nullable=True)
    airline = Column(String, nullable=True)
    
    def __repr__(self):
        return f"<ParkingReservation {self.id} - {self.location_name} ({self.lot_name})>"
    
    def to_dict(self):
        """Convert parking reservation to dictionary."""
        base_dict = super().to_dict()
        base_dict.update({
            "parking_type": self.parking_type,
            "location_name": self.location_name,
            "terminal": self.terminal,
            "lot_name": self.lot_name,
            "spot_number": self.spot_number,
            "vehicle_make": self.vehicle_make,
            "vehicle_model": self.vehicle_model,
            "vehicle_color": self.vehicle_color,
            "license_plate": self.license_plate,
            "check_in_time": self.check_in_time.isoformat() if self.check_in_time else None,
            "check_out_time": self.check_out_time.isoformat() if self.check_out_time else None,
            "daily_rate": self.daily_rate,
            "total_cost": self.total_cost,
            "parking_photo_url": self.parking_photo_url,
            "photo_uploaded_at": self.photo_uploaded_at.isoformat() if self.photo_uploaded_at else None,
            "return_reminder_sent": self.return_reminder_sent,
            "return_journey_scheduled": self.return_journey_scheduled,
            "estimated_pickup_time": self.estimated_pickup_time.isoformat() if self.estimated_pickup_time else None,
            "outbound_flight": self.outbound_flight,
            "return_flight": self.return_flight,
            "airline": self.airline
        })
        return base_dict