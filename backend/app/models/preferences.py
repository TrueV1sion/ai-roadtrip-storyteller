from sqlalchemy import Column, String, Boolean, ForeignKey, JSON, Integer, ARRAY, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import datetime

from app.db.base import Base


class UserPreferences(Base):
    """Enhanced user preferences for advanced personalization."""
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # General preferences
    interests = Column(JSON, nullable=True, default=list)  # e.g. ["history", "nature", "architecture"]
    family_friendly = Column(Boolean, default=True)
    voice_interaction = Column(Boolean, default=True)
    
    # Enhanced personalization attributes
    age_group = Column(String, nullable=True)  # "child", "teen", "young_adult", "adult", "senior"
    education_level = Column(String, nullable=True)  # "elementary", "high_school", "college", "graduate"
    travel_style = Column(String, nullable=True)  # "luxury", "budget", "adventure", "cultural", "relaxation", "family"
    accessibility_needs = Column(JSON, nullable=True, default=list)  # ["visual", "mobility", "hearing", "cognitive"]
    content_filters = Column(JSON, nullable=True, default=list)  # ["no_politics", "no_sensitive_topics", "family_friendly"]
    preferred_topics = Column(JSON, nullable=True, default=list)  # Weighted topics, e.g. {"history": 0.8, "nature": 0.5}
    avoided_topics = Column(JSON, nullable=True, default=list)  # Topics to avoid, e.g. ["war", "disaster", "crime"]
    
    # Story preferences
    storytelling_style = Column(String, default="balanced")  # "educational", "entertaining", "balanced", "adventure", etc.
    content_length_preference = Column(String, default="medium")  # "brief", "medium", "detailed"
    detail_level = Column(String, default="balanced")  # "simple", "balanced", "detailed", "technical"
    preferred_voice = Column(String, nullable=True)  # Voice ID for TTS
    
    # Content format preferences
    preferred_media_types = Column(JSON, nullable=True, default=list)  # ["text", "audio", "image", "video", "interactive"]
    language_preference = Column(String, default="en-US")
    translation_enabled = Column(Boolean, default=False)
    
    # Music preferences
    music_enabled = Column(Boolean, default=True)
    preferred_music_genres = Column(JSON, nullable=True, default=list)  # ["rock", "ambient", "classical"]
    music_volume = Column(Integer, default=50)  # 0-100
    
    # Privacy and data settings
    allow_analytics = Column(Boolean, default=True)
    allow_location_tracking = Column(Boolean, default=True)
    offline_mode_preferred = Column(Boolean, default=False)
    data_saving_mode = Column(Boolean, default=False)
    
    # Personalization system settings
    personalization_enabled = Column(Boolean, default=True)
    personalization_strategy = Column(String, default="balanced")  # "conservative", "balanced", "aggressive"
    
    # Metadata
    last_updated = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    preference_version = Column(Integer, default=1)
    
    # Relationship back to user
    user = relationship("User", back_populates="preferences")

    def __repr__(self):
        return f"<UserPreferences for user_id={self.user_id}>"
        
    def to_dict(self):
        """Convert preferences to dictionary."""
        return {
            "user_id": self.user_id,
            "interests": self.interests or [],
            "family_friendly": self.family_friendly,
            "voice_interaction": self.voice_interaction,
            "age_group": self.age_group,
            "education_level": self.education_level,
            "travel_style": self.travel_style,
            "accessibility_needs": self.accessibility_needs or [],
            "content_filters": self.content_filters or [],
            "preferred_topics": self.preferred_topics or {},
            "avoided_topics": self.avoided_topics or [],
            "storytelling_style": self.storytelling_style,
            "content_length_preference": self.content_length_preference,
            "detail_level": self.detail_level,
            "preferred_voice": self.preferred_voice,
            "preferred_media_types": self.preferred_media_types or [],
            "language_preference": self.language_preference,
            "translation_enabled": self.translation_enabled,
            "music_enabled": self.music_enabled,
            "preferred_music_genres": self.preferred_music_genres or [],
            "music_volume": self.music_volume,
            "allow_analytics": self.allow_analytics,
            "allow_location_tracking": self.allow_location_tracking,
            "offline_mode_preferred": self.offline_mode_preferred,
            "data_saving_mode": self.data_saving_mode,
            "personalization_enabled": self.personalization_enabled,
            "personalization_strategy": self.personalization_strategy,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "preference_version": self.preference_version
        }
