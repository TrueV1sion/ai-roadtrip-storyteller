from typing import Optional, Dict, List, Any
from pydantic import BaseModel, EmailStr, Field, validator
from app.core.authorization import UserRole


class UserBase(BaseModel):
    """Base schema for user data."""
    email: EmailStr
    name: str


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=12, max_length=128, description="User password")
    interests: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('password')
    def validate_password_complexity(cls, v):
        """Basic password validation - full validation happens in password policy."""
        if len(v) < 12:
            raise ValueError('Password must be at least 12 characters long')
        return v


class UserUpdate(BaseModel):
    """Schema for updating user data."""
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_premium: Optional[bool] = None
    role: Optional[UserRole] = None
    password: Optional[str] = Field(None, min_length=12, max_length=128, description="New password")


class UserResponse(UserBase):
    """Schema for user response."""
    id: str
    avatar_url: Optional[str] = None
    is_active: bool
    is_premium: bool
    role: UserRole
    created_at: str

    class Config:
        from_attributes = True


class UserPreferencesBase(BaseModel):
    """Enhanced base schema for user preferences with advanced personalization."""
    # General preferences
    interests: Optional[List[str]] = None
    family_friendly: Optional[bool] = None
    voice_interaction: Optional[bool] = None
    
    # Enhanced personalization attributes
    age_group: Optional[str] = None  # "child", "teen", "young_adult", "adult", "senior"
    education_level: Optional[str] = None  # "elementary", "high_school", "college", "graduate"
    travel_style: Optional[str] = None  # "luxury", "budget", "adventure", "cultural", "relaxation", "family"
    accessibility_needs: Optional[List[str]] = None  # ["visual", "mobility", "hearing", "cognitive"]
    content_filters: Optional[List[str]] = None  # ["no_politics", "no_sensitive_topics", "family_friendly"]
    preferred_topics: Optional[Dict[str, float]] = None  # Weighted topics, e.g. {"history": 0.8, "nature": 0.5}
    avoided_topics: Optional[List[str]] = None  # Topics to avoid, e.g. ["war", "disaster", "crime"]
    
    # Story preferences
    storytelling_style: Optional[str] = None  # "educational", "entertaining", "balanced", "adventure", etc.
    content_length_preference: Optional[str] = None  # "brief", "medium", "detailed"
    detail_level: Optional[str] = None  # "simple", "balanced", "detailed", "technical"
    preferred_voice: Optional[str] = None  # Voice ID for TTS
    
    # Content format preferences
    preferred_media_types: Optional[List[str]] = None  # ["text", "audio", "image", "video", "interactive"]
    language_preference: Optional[str] = None
    translation_enabled: Optional[bool] = None
    
    # Music preferences
    music_enabled: Optional[bool] = None
    preferred_music_genres: Optional[List[str]] = None
    music_volume: Optional[int] = None
    
    # Privacy and data settings
    allow_analytics: Optional[bool] = None
    allow_location_tracking: Optional[bool] = None
    offline_mode_preferred: Optional[bool] = None
    data_saving_mode: Optional[bool] = None
    
    # Personalization system settings
    personalization_enabled: Optional[bool] = None
    personalization_strategy: Optional[str] = None  # "conservative", "balanced", "aggressive"


class UserPreferencesCreate(UserPreferencesBase):
    """Schema for creating user preferences."""
    pass


class UserPreferencesUpdate(UserPreferencesBase):
    """Schema for updating user preferences."""
    pass


class UserPreferencesResponse(UserPreferencesBase):
    """Schema for user preferences response."""
    id: int
    user_id: str
    last_updated: Optional[str] = None
    preference_version: Optional[int] = None

    class Config:
        from_attributes = True


class UserWithPreferences(UserResponse):
    """Schema for user with preferences included."""
    preferences: Optional[UserPreferencesResponse] = None

    class Config:
        from_attributes = True
