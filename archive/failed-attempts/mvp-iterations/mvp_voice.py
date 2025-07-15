"""
MVP Voice Assistant Route - Streamlined endpoint using orchestration

This route provides a streamlined voice assistant endpoint for MVP testing,
using the master orchestration system but focusing only on essential features.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from ..core.unified_ai_client import get_unified_ai_client
from ..services.master_orchestration_agent import MasterOrchestrationAgent, JourneyContext
from ..services.tts_service import tts_synthesizer
from ..models.user import User

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
    

# Simple session management for MVP
mvp_sessions: Dict[str, MasterOrchestrationAgent] = {}


def get_or_create_mvp_session(session_id: str, ai_client) -> MasterOrchestrationAgent:
    """Get or create a simplified session for MVP"""
    if session_id not in mvp_sessions:
        mvp_sessions[session_id] = MasterOrchestrationAgent(ai_client)
    return mvp_sessions[session_id]


@router.post("/voice", response_model=MVPVoiceResponse)
async def mvp_voice_interaction(
    request: MVPVoiceRequest,
    ai_client = Depends(get_unified_ai_client)
):
    """
    Streamlined voice interaction endpoint for MVP using orchestration.
    
    Handles:
    - Navigation commands with AI-generated stories
    - Location-based storytelling
    - TTS audio generation
    
    Uses the master orchestration agent for intelligent processing.
    """
    try:
        # Create a simple session (in production, this would come from auth)
        session_id = "mvp_session"
        orchestrator = get_or_create_mvp_session(session_id, ai_client)
        
        # Build journey context from request
        location = request.context.get("location", {})
        location_name = request.context.get("location_name", "your current location")
        
        journey_context = JourneyContext(
            current_location={
                "lat": location.get("lat", 0),
                "lng": location.get("lng", 0),
                "name": location_name
            },
            current_time=datetime.now(),
            journey_stage="traveling",
            passengers=[],  # MVP doesn't need passenger info
            vehicle_info={},
            weather={},  # Could be added later
            route_info={}
        )
        
        # Create a minimal user object for MVP
        mvp_user = User(
            id=1,
            email="mvp@example.com",
            username="mvp_user",
            preferences={
                "story_style": "entertaining",
                "personality": "storyteller"
            }
        )
        
        # Process through orchestration agent
        logger.info(f"Processing MVP voice command: {request.user_input}")
        
        agent_response = await orchestrator.process_user_input(
            user_input=request.user_input,
            context=journey_context,
            user=mvp_user
        )
        
        # Extract response data
        response_data = {
            "text": agent_response.text,
            "type": "navigation" if "navigate" in request.user_input.lower() else "story"
        }
        
        # Check if navigation command
        if any(phrase in request.user_input.lower() for phrase in [
            "navigate to", "take me to", "go to", "drive to"
        ]):
            # Extract destination from the response or input
            for phrase in ["navigate to", "take me to", "go to", "drive to"]:
                if phrase in request.user_input.lower():
                    destination = request.user_input.lower().split(phrase)[-1].strip()
                    response_data["destination"] = destination
                    response_data["action"] = "start_navigation"
                    break
        
        # Handle actions if any
        if agent_response.actions:
            response_data["actions"] = agent_response.actions
        
        # Use audio URL from orchestration if available
        audio_url = agent_response.audio_url
        
        # If no audio URL but we have text, generate TTS
        if not audio_url and agent_response.text and tts_synthesizer.tts_client:
            try:
                # Get user's preferred personality
                from ..services.personality_engine import personality_engine
                personality = personality_engine.get_personality(
                    mvp_user.preferences.get("personality", "storyteller")
                )
                
                audio_url = tts_synthesizer.synthesize_and_upload(
                    text=agent_response.text,
                    personality=personality,
                    user_id=str(mvp_user.id),
                    is_premium=False
                )
                
                if audio_url:
                    logger.info(f"Generated TTS audio: {audio_url}")
            except Exception as e:
                logger.error(f"TTS synthesis failed: {str(e)}")
                # Continue without audio
        
        return MVPVoiceResponse(
            response=response_data,
            audio_url=audio_url
        )
        
    except Exception as e:
        logger.error(f"MVP voice interaction error: {str(e)}")
        # Provide a helpful fallback response
        fallback_response = {
            "text": "I'm having trouble processing that request. Try saying 'Navigate to' followed by your destination.",
            "type": "error"
        }
        return MVPVoiceResponse(
            response=fallback_response,
            audio_url=None
        )


@router.get("/health")
async def mvp_health_check():
    """Simple health check for MVP endpoints"""
    return {
        "status": "healthy",
        "service": "mvp_voice_orchestrated",
        "tts_available": tts_synthesizer.tts_client is not None,
        "ai_available": True,
        "orchestration": "enabled",
        "active_sessions": len(mvp_sessions)
    }