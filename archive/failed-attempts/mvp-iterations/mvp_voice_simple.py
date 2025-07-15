"""
MVP Voice Assistant Route - Ultra-simplified for deployment
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import logging
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/mvp", tags=["MVP Voice"])


class MVPVoiceRequest(BaseModel):
    """Simplified voice request for MVP"""
    user_input: str = Field(..., description="User's voice command as text")
    context: Dict[str, Any] = Field(default_factory=dict, description="Current context (location, etc)")


class MVPVoiceResponse(BaseModel):
    """Simplified voice response for MVP"""
    response: Dict[str, Any] = Field(..., description="Response data")
    audio_url: Optional[str] = Field(None, description="URL to audio file if TTS was generated")
    

@router.post("/voice", response_model=MVPVoiceResponse)
async def mvp_voice_interaction(request: MVPVoiceRequest):
    """
    Ultra-simplified voice interaction endpoint for MVP deployment.
    """
    try:
        # Extract user input
        user_input = request.user_input.lower()
        location = request.context.get("location", {})
        location_name = request.context.get("location_name", "your current location")
        
        # Check if this is a navigation command
        is_navigation = any(phrase in user_input for phrase in [
            "navigate to", "take me to", "go to", "drive to"
        ])
        
        response_data = {}
        
        if is_navigation:
            # Extract destination
            destination = None
            for phrase in ["navigate to", "take me to", "go to", "drive to"]:
                if phrase in user_input:
                    destination = user_input.split(phrase)[-1].strip()
                    break
            
            if destination:
                response_data = {
                    "type": "navigation",
                    "destination": destination,
                    "action": "start_navigation",
                    "text": f"Starting navigation to {destination}. What an exciting journey awaits! As you head to {destination}, you'll discover fascinating stories along the way."
                }
            else:
                response_data = {
                    "type": "error",
                    "text": "I didn't catch the destination. Please say 'Navigate to' followed by where you'd like to go."
                }
        else:
            # General story request
            response_data = {
                "type": "story",
                "text": f"Welcome to {location_name}! This area has so much to discover. Did you know that every street corner here has its own unique story? Let me share some fascinating facts about where you are right now."
            }
        
        return MVPVoiceResponse(
            response=response_data,
            audio_url=None  # TTS disabled for initial deployment
        )
        
    except Exception as e:
        logger.error(f"MVP voice interaction error: {str(e)}")
        return MVPVoiceResponse(
            response={
                "type": "error",
                "text": "I'm having trouble processing that request. Please try again."
            },
            audio_url=None
        )


@router.get("/health")
async def mvp_health_check():
    """Simple health check for MVP endpoints"""
    return {
        "status": "healthy",
        "service": "mvp_voice_simple",
        "ai_available": bool(os.getenv("GOOGLE_AI_PROJECT_ID")),
        "maps_available": bool(os.getenv("GOOGLE_MAPS_API_KEY"))
    }