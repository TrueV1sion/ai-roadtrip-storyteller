"""
Voice API Schemas
Pydantic models for voice orchestration endpoints
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class LocationData(BaseModel):
    """Location information for context"""
    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude") 
    heading: Optional[float] = Field(None, description="Direction of travel in degrees")
    speed: Optional[float] = Field(None, description="Speed in mph")


class VoiceProcessRequest(BaseModel):
    """Request model for voice processing"""
    audio_input: str = Field(..., description="Base64 encoded audio data")
    location: LocationData = Field(..., description="Current location")
    context_data: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional context (personality, preferences, etc.)"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "audio_input": "base64_encoded_audio_string",
                "location": {
                    "lat": 37.7749,
                    "lng": -122.4194,
                    "heading": 45.0,
                    "speed": 65.0
                },
                "context_data": {
                    "personality": "wise_narrator",
                    "audio_priority": "balanced",
                    "party_size": 2
                }
            }
        }


class VoiceProcessResponse(BaseModel):
    """Response model for voice processing"""
    voice_audio: str = Field(..., description="Base64 encoded voice response audio")
    transcript: str = Field(..., description="Text transcript of the response")
    visual_data: Optional[Dict[str, Any]] = Field(
        None, 
        description="Visual data to display when vehicle is stopped"
    )
    actions_taken: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Actions completed by the assistant"
    )
    state: str = Field(..., description="Current conversation state")
    
    class Config:
        schema_extra = {
            "example": {
                "voice_audio": "base64_encoded_audio_response",
                "transcript": "I found a great steakhouse 15 miles ahead...",
                "visual_data": {
                    "restaurants": [
                        {
                            "name": "The Rustic Fork",
                            "cuisine": "Steakhouse",
                            "rating": 4.8,
                            "price_per_meal": 45,
                            "distance_miles": 15,
                            "wait_time": "20 minutes"
                        }
                    ]
                },
                "actions_taken": [
                    {
                        "type": "restaurant_search",
                        "detail": "Found 3 restaurants ahead"
                    }
                ],
                "state": "awaiting_confirmation"
            }
        }


class ProactiveSuggestionRequest(BaseModel):
    """Request model for proactive suggestions"""
    user_id: str = Field(..., description="User identifier")
    trigger: str = Field(..., description="Trigger type (meal_time, low_fuel, etc.)")
    context_data: Dict[str, Any] = Field(
        ..., 
        description="Context including location, time, preferences"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "user_123",
                "trigger": "meal_time",
                "context_data": {
                    "location": {
                        "lat": 37.7749,
                        "lng": -122.4194
                    },
                    "time_of_day": 12,
                    "meal": "lunch",
                    "distance": "10 miles"
                }
            }
        }


class ProactiveSuggestionResponse(BaseModel):
    """Response model for proactive suggestions"""
    voice_audio: str = Field(..., description="Base64 encoded suggestion audio")
    transcript: str = Field(..., description="Text of the suggestion")
    trigger: str = Field(..., description="The trigger that prompted this suggestion")
    can_dismiss: bool = Field(True, description="Whether user can dismiss this suggestion")
    
    class Config:
        schema_extra = {
            "example": {
                "voice_audio": "base64_encoded_suggestion_audio",
                "transcript": "I notice it's getting close to lunch. There's a wonderful Italian place in 10 miles that locals love.",
                "trigger": "meal_time",
                "can_dismiss": True
            }
        }


class VoicePreferences(BaseModel):
    """User voice preferences"""
    personality: str = Field(
        "wise_narrator",
        description="Selected voice personality"
    )
    proactive_suggestions: bool = Field(
        True,
        description="Enable proactive suggestions"
    )
    audio_priority: str = Field(
        "balanced",
        description="Audio priority mode: balanced, navigation, story"
    )
    voice_activation_phrase: Optional[str] = Field(
        None,
        description="Custom wake phrase"
    )
    suggestion_frequency: str = Field(
        "moderate",
        description="How often to provide suggestions: minimal, moderate, frequent"
    )