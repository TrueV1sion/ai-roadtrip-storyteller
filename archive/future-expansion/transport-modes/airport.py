"""
Database models for airport-related features.
"""

from sqlalchemy import Column, String, DateTime, Float, Integer, JSON, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from backend.app.db.base import Base


class FlightStatus(str, enum.Enum):
    """Flight status enumeration."""
    SCHEDULED = "scheduled"
    DELAYED = "delayed"
    BOARDING = "boarding"
    DEPARTED = "departed"
    IN_AIR = "in_air"
    LANDED = "landed"
    CANCELLED = "cancelled"


class AirportJourney(Base):
    """Model for airport trips with flight information."""
    
    __tablename__ = "airport_journeys"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Flight information
    flight_number = Column(String)
    airline = Column(String)
    departure_airport = Column(String, nullable=False)  # IATA code
    arrival_airport = Column(String)  # IATA code
    departure_time = Column(DateTime, nullable=False)
    arrival_time = Column(DateTime)
    flight_status = Column(SQLEnum(FlightStatus), default=FlightStatus.SCHEDULED)
    terminal = Column(String)
    gate = Column(String)
    
    # Journey information
    origin_location = Column(JSON)  # Starting point (home, hotel, etc.)
    is_pickup = Column(Boolean, default=False)  # False = dropoff, True = pickup
    
    # Parking information
    parking_booking_id = Column(String, ForeignKey("bookings.id"))
    parking_location = Column(JSON)  # GPS coordinates + photo URL
    parking_type = Column(String)
    parking_lot = Column(String)
    parking_spot = Column(String)
    
    # Timing calculations
    recommended_departure = Column(DateTime)
    actual_departure = Column(DateTime)
    arrival_at_airport = Column(DateTime)
    
    # TSA and airport info
    tsa_wait_time = Column(Integer)  # minutes
    used_precheck = Column(Boolean, default=False)
    checked_bags = Column(Boolean, default=True)
    
    # Return journey
    return_journey_id = Column(String, ForeignKey("airport_journeys.id"))
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", backref="airport_journeys")
    parking_booking = relationship("Booking", backref="airport_parking")
    return_journey = relationship("AirportJourney", remote_side=[id])


class ParkingReservation(Base):
    """Model for airport parking reservations."""
    
    __tablename__ = "parking_reservations"
    
    id = Column(String, primary_key=True)
    booking_id = Column(String, ForeignKey("bookings.id"), nullable=False)
    airport_journey_id = Column(String, ForeignKey("airport_journeys.id"))
    
    # Parking details
    airport_code = Column(String, nullable=False)
    lot_type = Column(String, nullable=False)  # economy, daily, garage, etc.
    lot_name = Column(String)
    spot_number = Column(String)
    
    # Dates
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    # Pricing
    price_per_day = Column(Float)
    total_price = Column(Float, nullable=False)
    
    # Access information
    confirmation_code = Column(String)
    qr_code_url = Column(String)
    access_instructions = Column(JSON)
    
    # Shuttle information
    shuttle_frequency = Column(Integer)  # minutes
    shuttle_pickup_location = Column(String)
    
    # Photos and notes
    parking_photos = Column(JSON)  # Array of photo URLs
    user_notes = Column(String)
    
    # Status
    is_active = Column(Boolean, default=True)
    checked_in = Column(DateTime)
    checked_out = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    booking = relationship("Booking", backref="parking_details")
    airport_journey = relationship("AirportJourney", backref="parking_reservation_details")


class TSAWaitTime(Base):
    """Model for tracking TSA wait times."""
    
    __tablename__ = "tsa_wait_times"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    airport_code = Column(String, nullable=False)
    terminal = Column(String)
    checkpoint = Column(String)
    
    # Wait times in minutes
    standard_wait = Column(Integer)
    precheck_wait = Column(Integer)
    clear_wait = Column(Integer)
    
    # Context
    timestamp = Column(DateTime, nullable=False)
    day_of_week = Column(Integer)  # 0-6
    hour_of_day = Column(Integer)  # 0-23
    is_holiday = Column(Boolean, default=False)
    
    # Source
    source = Column(String)  # "tsa_api", "user_report", "estimation"
    confidence = Column(Float)  # 0.0-1.0
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)


class AirportPickupZone(Base):
    """Model for airport pickup/dropoff zones."""
    
    __tablename__ = "airport_pickup_zones"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    airport_code = Column(String, nullable=False)
    terminal = Column(String, nullable=False)
    
    # Zone information
    zone_type = Column(String)  # "rideshare", "taxi", "private", "cell_phone_lot"
    zone_name = Column(String)
    level = Column(String)  # "arrivals", "departures", "ground"
    
    # Location
    coordinates = Column(JSON)  # {"lat": 0.0, "lng": 0.0}
    walking_time_to_baggage = Column(Integer)  # minutes
    
    # Instructions
    access_instructions = Column(String)
    signs_to_follow = Column(JSON)  # ["Follow Rideshare signs", "Turn left at Door 3"]
    
    # Real-time info
    current_wait_time = Column(Integer)  # minutes
    is_congested = Column(Boolean, default=False)
    last_updated = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FlightTracker(Base):
    """Model for tracking flight status updates."""
    
    __tablename__ = "flight_trackers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    airport_journey_id = Column(String, ForeignKey("airport_journeys.id"), nullable=False)
    
    # Flight identification
    flight_number = Column(String, nullable=False)
    flight_date = Column(DateTime, nullable=False)
    
    # Status tracking
    last_status = Column(SQLEnum(FlightStatus))
    last_update = Column(DateTime)
    
    # Delays and changes
    departure_delay_minutes = Column(Integer, default=0)
    arrival_delay_minutes = Column(Integer, default=0)
    gate_changes = Column(JSON)  # Array of {"from": "A1", "to": "A5", "time": "..."}
    
    # Notifications sent
    notifications_sent = Column(JSON)  # Array of {"type": "delay", "time": "...", "message": "..."}
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    airport_journey = relationship("AirportJourney", backref="flight_tracking")