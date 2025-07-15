from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


class ThemeStyleGuide(BaseModel):
    """Schema for theme style guide settings."""
    tone: str = Field(..., description="Tone of the content (e.g., spooky, educational, adventurous)")
    language: str = Field(..., description="Language style (e.g., simple, poetic, technical)")
    narrative_style: str = Field(..., description="Narrative style (e.g., first-person, storytelling, factual)")
    keywords: Optional[List[str]] = Field(None, description="Keywords to include in themed content")
    avoid_words: Optional[List[str]] = Field(None, description="Words to avoid in themed content")
    example: Optional[str] = Field(None, description="Example of themed content")


class ThemeBase(BaseModel):
    """Base model for theme data."""
    name: str = Field(..., description="Name of the theme")
    description: str = Field(..., description="Description of the theme")
    image_url: Optional[str] = Field(None, description="URL to theme image")
    category: Optional[str] = Field(None, description="Category of the theme (historical, adventure, haunted, etc.)")
    tags: Optional[List[str]] = Field(None, description="Tags for searching and filtering")
    is_seasonal: Optional[bool] = Field(False, description="Whether theme is seasonal")
    available_from: Optional[datetime] = Field(None, description="Start date if seasonal")
    available_until: Optional[datetime] = Field(None, description="End date if seasonal")
    is_active: Optional[bool] = Field(True, description="Whether theme is active")
    is_featured: Optional[bool] = Field(False, description="Whether theme is featured")


class ThemeCreate(ThemeBase):
    """Schema for creating a new theme."""
    prompt_template: str = Field(..., description="Base prompt template for this theme")
    style_guide: Dict[str, Any] = Field(..., description="Style guidelines for stories")
    recommended_interests: Optional[List[str]] = Field(None, description="Interests that work well with this theme")
    music_genres: Optional[List[str]] = Field(None, description="Music genres that match this theme")


class ThemeUpdate(BaseModel):
    """Schema for updating a theme."""
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    prompt_template: Optional[str] = None
    style_guide: Optional[Dict[str, Any]] = None
    recommended_interests: Optional[List[str]] = None
    music_genres: Optional[List[str]] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_seasonal: Optional[bool] = None
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None


class ThemeResponse(ThemeBase):
    """Schema for theme responses (public API)."""
    id: str
    created_at: datetime
    updated_at: datetime
    recommended_interests: Optional[List[str]] = None
    music_genres: Optional[List[str]] = None

    class Config:
        orm_mode = True


class ThemeDetailResponse(ThemeResponse):
    """Schema for detailed theme responses (admin API)."""
    prompt_template: str
    style_guide: Dict[str, Any]

    class Config:
        orm_mode = True


class UserThemePreferenceBase(BaseModel):
    """Base model for user theme preference data."""
    theme_id: str = Field(..., description="ID of the theme")
    is_favorite: Optional[bool] = Field(False, description="Whether the theme is a favorite")
    preference_level: Optional[str] = Field(None, description="User's preference level (love, like, dislike)")


class UserThemePreferenceCreate(UserThemePreferenceBase):
    """Schema for creating a user theme preference."""
    pass


class UserThemePreferenceUpdate(BaseModel):
    """Schema for updating a user theme preference."""
    is_favorite: Optional[bool] = None
    preference_level: Optional[str] = None


class UserThemePreferenceResponse(UserThemePreferenceBase):
    """Schema for user theme preference responses."""
    id: str
    user_id: str
    last_used: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class ThemedPromptRequest(BaseModel):
    """Schema for generating a themed prompt."""
    theme_id: str = Field(..., description="ID of the theme to use")
    base_prompt: str = Field(..., description="Base prompt to enhance")
    location: Dict[str, Any] = Field(..., description="Dictionary with location information")
    interests: List[str] = Field(..., description="List of user interests")
    context: Dict[str, Any] = Field({}, description="Additional context information")


class ThemedPromptResponse(BaseModel):
    """Schema for themed prompt responses."""
    prompt: str = Field(..., description="Generated themed prompt")
    theme_id: str = Field(..., description="ID of the theme used")
    theme_name: str = Field(..., description="Name of the theme used")


class ThemedStoryRequest(BaseModel):
    """Schema for generating a themed story."""
    theme_id: str = Field(..., description="ID of the theme to use")
    latitude: float = Field(..., description="Latitude for the story location")
    longitude: float = Field(..., description="Longitude for the story location")
    location_name: Optional[str] = Field(None, description="Name of the location")
    interests: List[str] = Field(..., description="List of user interests")
    context: Dict[str, Any] = Field({}, description="Additional context information")
    language: Optional[str] = Field("en-US", description="Language for the story")


class ThemeRecommendationRequest(BaseModel):
    """Schema for theme recommendation requests."""
    location: Dict[str, Any] = Field(..., description="Dictionary with location information")
    interests: Optional[List[str]] = Field(None, description="List of user interests")
    limit: Optional[int] = Field(5, description="Maximum number of themes to recommend")