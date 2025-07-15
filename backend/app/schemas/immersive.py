from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class LocationData(BaseModel):
    """Schema for location data."""
    latitude: float
    longitude: float


class ImmersiveContext(BaseModel):
    """Schema for immersive experience context."""
    time_of_day: Optional[str] = None
    weather: Optional[str] = None
    mood: Optional[str] = None


class ImmersiveRequest(BaseModel):
    """Schema for immersive experience request."""
    conversation_id: str
    location: LocationData
    interests: List[str]
    context: Optional[ImmersiveContext] = None


class Track(BaseModel):
    """Schema for a music track."""
    title: str
    artist: str


class Playlist(BaseModel):
    """Schema for a playlist."""
    playlist_name: str
    tracks: List[Track]
    provider: str


class ImmersiveResponse(BaseModel):
    """Schema for immersive experience response."""
    story: str
    playlist: Playlist
    tts_audio: str  # Base64 encoded audio
