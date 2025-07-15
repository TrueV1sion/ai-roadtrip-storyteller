from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, Float
from sqlalchemy.sql import func
import uuid

from app.db.base import Base  # Assuming Base is correctly located here


class UserSavedExperience(Base):
    __tablename__ = "user_saved_experiences"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    story_text = Column(Text, nullable=False)
    playlist_name = Column(String, nullable=True)
    playlist_tracks = Column(JSON, nullable=False)  # Stores list of track objects
    playlist_provider = Column(String, nullable=True)

    tts_audio_identifier = Column(String, nullable=True)

    location_latitude = Column(Float, nullable=True)
    location_longitude = Column(Float, nullable=True)
    
    interests = Column(JSON, nullable=True)  # Stores list of interests used

    context_time_of_day = Column(String, nullable=True)
    context_weather = Column(String, nullable=True)
    context_mood = Column(String, nullable=True)

    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    saved_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # To add a relationship back to User model (optional, requires User model update):
    # from .user import User # Assuming User is in app.models.user
    # user = relationship("User", back_populates="saved_experiences")

    def __repr__(self):
        return f"<UserSavedExperience id={self.id} user_id={self.user_id}>"
