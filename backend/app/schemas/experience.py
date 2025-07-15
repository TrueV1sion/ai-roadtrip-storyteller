from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# Pydantic Schemas for Immersive Experience Save/History

class TrackSchema(BaseModel):
    id: str
    title: str
    artist: str
    uri: str
    duration_ms: int

class PlaylistSchema(BaseModel):
    playlist_name: Optional[str] = None
    tracks: List[TrackSchema]
    provider: Optional[str] = None

class LocationSchema(BaseModel):
    latitude: float
    longitude: float

class ImmersiveContextSchema(BaseModel):
    time_of_day: Optional[str] = None
    weather: Optional[str] = None
    mood: Optional[str] = None

# Schema for the data to be saved (POST /api/immersive/save)
class ExperienceSavePayload(BaseModel):
    story: str
    playlist: PlaylistSchema
    tts_audio_url: Optional[HttpUrl] = None  # The mobile app might send the temporary URL
    location: Optional[LocationSchema] = None
    interests: Optional[List[str]] = None
    context: Optional[ImmersiveContextSchema] = None

# Schema for a single saved experience item in the history list (GET /api/immersive/history)
class SavedExperienceItem(BaseModel):
    id: str = Field(..., description="Unique ID of the saved experience")
    story_text: str = Field(..., description="The AI-generated story")
    playlist: PlaylistSchema
    # For TTS, the URL might be dynamically generated or fetched from permanent storage
    # For now, let's assume it could be present or not based on availability
    tts_audio_url: Optional[HttpUrl] = None 
    location: Optional[LocationSchema] = None
    interests: Optional[List[str]] = None
    context: Optional[ImmersiveContextSchema] = None
    generated_at: datetime
    saved_at: datetime

    class Config:
        orm_mode = True  # To allow easy conversion from SQLAlchemy model instance

# Schema for the response of the history endpoint
class ExperienceHistoryResponse(BaseModel):
    items: List[SavedExperienceItem]
    total: int
    page: int
    size: int
    # pages: Optional[int] = None # Could add total pages as a calculated field if needed

# You might also want a schema for creating a UserSavedExperience directly in CRUD operations
# if you have a more direct CRUD layer, but ExperienceSavePayload is for the API endpoint.
class UserSavedExperienceCreate(ExperienceSavePayload):
    user_id: str # Required when creating the DB record
    tts_audio_identifier: Optional[str] = None # To store the GCS path
    generated_at: Optional[datetime] = None # Can be set by server
    saved_at: Optional[datetime] = None # Can be set by server

class UserSavedExperienceUpdate(BaseModel):
    # Define fields that can be updated if any (e.g., user notes, rating - not currently in scope)
    pass
