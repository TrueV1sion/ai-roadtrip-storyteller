"""
Navigation Schemas - Request/Response models for navigation endpoints
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..models.directions import Route, Location


class NavigationStartRequest(BaseModel):
    """Request to start navigation"""
    route: Route
    current_location: Location
    destination: Location
    navigation_preferences: Optional[Dict[str, Any]] = Field(
        None, 
        description="User preferences for navigation (voice, verbosity, etc.)"
    )


class NavigationUpdateRequest(BaseModel):
    """Request to update navigation based on current position"""
    current_location: Location
    current_step_index: int = Field(..., description="Index of current route step")
    distance_to_next_maneuver: float = Field(..., description="Distance in meters to next turn")
    time_to_next_maneuver: float = Field(..., description="Estimated seconds to next turn")
    current_speed: float = Field(..., description="Current speed in km/h")
    is_on_highway: bool = Field(default=False, description="Whether currently on highway")
    approaching_complex_intersection: bool = Field(
        default=False, 
        description="Whether approaching complex maneuver"
    )
    story_playing: bool = Field(default=False, description="Whether story is currently playing")
    audio_priority: Optional[str] = Field(
        default="balanced", 
        description="Audio priority mode: safety_first, balanced, story_focused"
    )
    last_instruction_time: Optional[datetime] = None


class NavigationInstructionResponse(BaseModel):
    """Response with navigation instruction"""
    has_instruction: bool
    instruction: Optional[Dict[str, Any]] = Field(
        None,
        description="Navigation instruction details if available"
    )
    audio_url: Optional[str] = Field(None, description="URL for voice instruction audio")
    audio_duration: Optional[float] = Field(None, description="Duration of audio in seconds")
    orchestration_action: Optional[Dict[str, Any]] = Field(
        None,
        description="How to orchestrate with other audio"
    )
    next_check_seconds: int = Field(
        30,
        description="Seconds until next position check"
    )


class NavigationStateResponse(BaseModel):
    """Current navigation state"""
    active: bool = Field(..., description="Whether voice navigation is active")
    route_id: Optional[str] = Field(None, description="Active route ID")
    current_instruction_index: int = Field(0, description="Current instruction index")
    last_instruction_time: Optional[datetime] = None


class NavigationPreferences(BaseModel):
    """User preferences for navigation"""
    voice_personality: Optional[str] = Field(
        None,
        description="Preferred voice for navigation"
    )
    instruction_timing: Optional[str] = Field(
        default="normal",
        description="Timing preference: early, normal, late"
    )
    verbosity: Optional[str] = Field(
        default="normal",
        description="Instruction detail level: minimal, normal, detailed"
    )
    audio_priority: Optional[str] = Field(
        default="balanced",
        description="Audio priority: safety_first, balanced, story_focused"
    )
    announce_street_names: bool = Field(
        default=True,
        description="Whether to announce street names"
    )
    announce_distances: bool = Field(
        default=True,
        description="Whether to announce distances"
    )