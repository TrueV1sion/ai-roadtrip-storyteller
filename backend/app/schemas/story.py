from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime


class StoryBase(BaseModel):
    """Base schema for story data."""
    title: Optional[str] = None
    content: str
    latitude: float
    longitude: float
    location_name: Optional[str] = None
    interests: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None
    language: Optional[str] = "en-US"


class StoryCreate(StoryBase):
    """Schema for creating a new story."""
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class StoryUpdate(BaseModel):
    """Schema for updating a story."""
    title: Optional[str] = None
    is_favorite: Optional[bool] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    play_count: Optional[int] = None
    completion_rate: Optional[float] = Field(None, ge=0, le=1)
    feedback: Optional[str] = None


class StoryResponse(StoryBase):
    """Schema for story response."""
    id: str
    user_id: Optional[str] = None
    audio_url: Optional[str] = None
    image_url: Optional[str] = None
    is_favorite: bool
    rating: Optional[int] = None
    play_count: int
    completion_rate: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class StoryListResponse(BaseModel):
    """Schema for list of stories response."""
    stories: List[StoryResponse]
    total: int
    page: int
    page_size: int
    
    class Config:
        from_attributes = True


class StoryAnalysisResponse(BaseModel):
    """Schema for content analysis response."""
    content_topics: List[str]
    matching_interests: List[str]
    missing_interests: List[str]
    relevance_score: float = Field(..., ge=0, le=1)
    personalization_quality: str

    class Config:
        from_attributes = True


# Event Journey Schemas
class EventJourneyBase(BaseModel):
    """Base schema for event journeys."""
    event_id: str
    event_name: str
    event_type: Optional[str] = None
    event_date: datetime
    venue_id: Optional[str] = None
    venue_name: str
    venue_address: str
    venue_lat: float
    venue_lon: float
    origin_address: str
    origin_lat: float
    origin_lon: float
    departure_time: datetime
    estimated_arrival: datetime
    voice_personality: Dict[str, Any]
    journey_content: Dict[str, Any]
    theme: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


class EventJourneyCreate(EventJourneyBase):
    """Schema for creating event journeys."""
    pass


class EventJourneyUpdate(BaseModel):
    """Schema for updating event journeys."""
    status: Optional[str] = None
    actual_departure: Optional[datetime] = None
    actual_arrival: Optional[datetime] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    feedback: Optional[str] = None
    milestones_completed: Optional[List[str]] = None
    trivia_score: Optional[int] = None


class EventJourneyResponse(EventJourneyBase):
    """Schema for event journey responses."""
    id: str
    user_id: str
    status: str = "planned"
    actual_departure: Optional[datetime] = None
    actual_arrival: Optional[datetime] = None
    rating: Optional[int] = None
    feedback: Optional[str] = None
    milestones_completed: Optional[List[str]] = None
    trivia_score: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class EventJourneyRequest(BaseModel):
    """Request schema for creating an event journey."""
    origin: str = Field(..., description="Starting location address")
    event_id: str = Field(..., description="Ticketmaster event ID")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences for the journey")
    
    class Config:
        schema_extra = {
            "example": {
                "origin": "123 Main St, San Francisco, CA",
                "event_id": "G5vYZ4VoFkeep",
                "preferences": {
                    "formality": "casual",
                    "detail_level": "detailed",
                    "music_preference": "upbeat"
                }
            }
        }


class EventSearchRequest(BaseModel):
    """Request schema for searching events."""
    keyword: Optional[str] = None
    location: Optional[Dict[str, float]] = Field(None, description="Lat/lon coordinates")
    radius: int = Field(50, description="Search radius in miles")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    event_type: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "keyword": "Taylor Swift",
                "location": {"lat": 37.7749, "lon": -122.4194},
                "radius": 50,
                "event_type": "music"
            }
        }


class StoryRequest(BaseModel):
    """Request schema for generating a story."""
    location: Dict[str, float] = Field(..., description="Location coordinates with latitude and longitude")
    interests: List[str] = Field(..., description="User interests for story generation")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences for story generation")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for story generation")
    
    @validator('preferences')
    def validate_story_preferences(cls, v):
        """Validate story preferences format and values."""
        if v is None:
            return v
            
        # Validate theme if present
        if 'theme' in v:
            valid_themes = ['adventure', 'historical', 'spooky', 'educational', 'romantic', 'mystery']
            if v['theme'] not in valid_themes:
                raise ValueError(f"Theme must be one of: {', '.join(valid_themes)}")
        
        # Validate tone if present
        if 'tone' in v:
            valid_tones = ['casual', 'formal', 'humorous', 'dramatic', 'educational']
            if v['tone'] not in valid_tones:
                raise ValueError(f"Tone must be one of: {', '.join(valid_tones)}")
                
        # Validate language if present
        if 'language' in v:
            # Basic language code validation
            if not isinstance(v['language'], str) or len(v['language']) < 2:
                raise ValueError("Language must be a valid language code")
                
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "location": {"latitude": 37.7749, "longitude": -122.4194},
                "interests": ["history", "architecture", "food"],
                "preferences": {
                    "theme": "historical",
                    "tone": "educational",
                    "language": "en-US"
                },
                "context": {
                    "time_of_day": "afternoon",
                    "weather": "sunny"
                }
            }
        }