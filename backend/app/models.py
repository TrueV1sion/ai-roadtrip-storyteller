from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    hashed_password = Column(String)
    interests = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
    trips = relationship("Trip", back_populates="user")
    stories = relationship("Story", back_populates="user")


class Trip(Base):
    __tablename__ = "trips"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    name = Column(String)
    start_location = Column(JSON)  # {lat: float, lng: float}
    end_location = Column(JSON)  # {lat: float, lng: float}
    waypoints = Column(JSON)  # [{lat: float, lng: float}]
    status = Column(String)  # planned, active, completed
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
    user = relationship("User", back_populates="trips")
    stories = relationship("Story", back_populates="trip")


class Story(Base):
    __tablename__ = "stories"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    trip_id = Column(String, ForeignKey("trips.id"))
    location = Column(JSON)  # {lat: float, lng: float}
    story_text = Column(String)
    interests = Column(JSON)  # List of interests this story matches
    context = Column(JSON)  # Additional context (time, weather, etc.)
    rating = Column(Float, nullable=True)  # User rating if provided
    is_favorite = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="stories")
    trip = relationship("Trip", back_populates="stories") 