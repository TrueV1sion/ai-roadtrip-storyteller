from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, JSON, Integer, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.db.base import Base


class EventJourney(Base):
    """Event journey model for storing event-based trip experiences."""
    __tablename__ = "event_journeys"
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Event information
    event_id = Column(String, nullable=False, index=True)  # Ticketmaster event ID
    event_name = Column(String, nullable=False)
    event_type = Column(String, nullable=True)  # concert, sports, theater, etc.
    event_date = Column(DateTime, nullable=False)
    
    # Venue information
    venue_id = Column(String, nullable=True)  # Ticketmaster venue ID
    venue_name = Column(String, nullable=False)
    venue_address = Column(String, nullable=False)
    venue_lat = Column(Float, nullable=False)
    venue_lon = Column(Float, nullable=False)
    
    # Journey details
    origin_address = Column(String, nullable=False)
    origin_lat = Column(Float, nullable=False)
    origin_lon = Column(Float, nullable=False)
    departure_time = Column(DateTime, nullable=False)
    estimated_arrival = Column(DateTime, nullable=False)
    
    # Content and personalization
    voice_personality = Column(JSON, nullable=False)  # Selected voice personality
    journey_content = Column(JSON, nullable=False)  # Generated content for journey
    theme = Column(String, nullable=True)  # Journey theme
    preferences = Column(JSON, nullable=True)  # User preferences for this journey
    
    # Status tracking
    status = Column(String, default="planned")  # planned, in_progress, completed, cancelled
    actual_departure = Column(DateTime, nullable=True)
    actual_arrival = Column(DateTime, nullable=True)
    
    # Engagement metrics
    rating = Column(Integer, nullable=True)  # User rating (1-5)
    feedback = Column(Text, nullable=True)
    milestones_completed = Column(JSON, nullable=True)  # Which milestones were triggered
    trivia_score = Column(Integer, nullable=True)  # Score from trivia games
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="event_journeys")
    
    def __repr__(self):
        return f"<EventJourney {self.id} - {self.event_name}>"


class Story(Base):
    """Story model for storing generated stories."""
    __tablename__ = "stories"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    
    # Theme relationship
    theme_id = Column(String, ForeignKey("themes.id"), nullable=True)
    theme_attributes_used = Column(JSON, nullable=True)  # Store which theme attributes were used
    
    # Location metadata
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location_name = Column(String, nullable=True)
    
    # Story metadata
    interests = Column(JSON, nullable=True)  # List of interests used to generate the story
    context = Column(JSON, nullable=True)  # Additional context like time_of_day, weather, etc.
    language = Column(String, default="en-US")
    
    # Enhanced personalization metadata
    story_metadata = Column(JSON, nullable=True)  # Additional metadata including personalization info
    feedback = Column(Text, nullable=True)  # User feedback on story content
    
    # Media
    audio_url = Column(String, nullable=True)  # URL to synthesized audio file
    image_url = Column(String, nullable=True)  # URL to associated image
    
    # User engagement metrics
    is_favorite = Column(Boolean, default=False)
    rating = Column(Integer, nullable=True)  # User rating (1-5)
    play_count = Column(Integer, default=0)
    completion_rate = Column(Float, nullable=True)  # Percentage of story listened to
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="stories")
    theme = relationship("Theme", back_populates="stories")
    
    def __repr__(self):
        return f"<Story {self.id}>"
        
    def to_dict(self):
        """Convert story to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "content": self.content,
            "theme_id": self.theme_id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "location_name": self.location_name,
            "interests": self.interests,
            "context": self.context,
            "language": self.language,
            "metadata": self.story_metadata,
            "feedback": self.feedback,
            "audio_url": self.audio_url,
            "image_url": self.image_url,
            "is_favorite": self.is_favorite,
            "rating": self.rating,
            "play_count": self.play_count,
            "completion_rate": self.completion_rate,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }