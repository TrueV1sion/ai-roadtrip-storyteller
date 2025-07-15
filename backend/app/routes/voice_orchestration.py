"""
Voice Orchestration API Routes
Provides the single endpoint for all voice interactions from mobile app
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
from datetime import datetime
import base64
import logging

from ..services.voice_orchestrator_enhanced import VoiceOrchestratorEnhanced
from ..services.master_orchestration_agent import MasterOrchestrationAgent
from ..core.unified_ai_client import unified_ai_client
from ..core.auth import get_current_user
from ..models.user import User
from ..schemas.voice import (
    VoiceProcessRequest,
    VoiceProcessResponse,
    ProactiveSuggestionRequest,
    ProactiveSuggestionResponse
)
from ..monitoring.voice_monitoring_dashboard import voice_monitoring

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])

# Initialize orchestrators
master_agent = MasterOrchestrationAgent(unified_ai_client)
voice_orchestrator = VoiceOrchestratorEnhanced(master_agent, unified_ai_client)


@router.post("/process", response_model=VoiceProcessResponse)
async def process_voice_input(
    request: VoiceProcessRequest,
    current_user: User = Depends(get_current_user)
) -> VoiceProcessResponse:
    """
    Main endpoint for processing voice input from mobile app.
    Returns voice audio and any visual data for display when stopped.
    """
    try:
        # Decode base64 audio
        try:
            audio_bytes = base64.b64decode(request.audio_input)
        except Exception as e:
            logger.error(f"Failed to decode audio: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid audio data"
            )
        
        # Record start time for monitoring
        start_time = datetime.now()
        
        # Process through enhanced voice orchestrator
        result = await voice_orchestrator.process_voice_input(
            user_id=str(current_user.id),
            audio_input=audio_bytes,
            location={
                "lat": request.location.lat,
                "lng": request.location.lng,
                "heading": request.location.heading,
                "speed": request.location.speed
            },
            context_data=request.context_data or {}
        )
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Record metrics for monitoring
        voice_monitoring.record_request(
            user_id=str(current_user.id),
            duration=processing_time,
            intent=result.get("intent", "unknown"),
            success=True,
            cache_hit=result.get("performance_metrics", {}).get("cache_hits", 0) > 0
        )
        
        # Encode response audio back to base64
        voice_audio_base64 = base64.b64encode(result["voice_audio"]).decode('utf-8')
        
        # Log interaction for analytics
        logger.info(f"Processed voice interaction for user {current_user.id}: {result['state']} in {processing_time:.2f}s")
        
        return VoiceProcessResponse(
            voice_audio=voice_audio_base64,
            transcript=result["transcript"],
            visual_data=result.get("visual_data"),
            actions_taken=result.get("actions_taken", []),
            state=result["state"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice processing error: {e}")
        
        # Record error for monitoring
        voice_monitoring.record_request(
            user_id=str(current_user.id),
            duration=(datetime.now() - start_time).total_seconds() if 'start_time' in locals() else 0,
            intent="error",
            success=False,
            error=str(e)
        )
        
        # Generate error response in character
        error_audio = await voice_orchestrator._generate_voice_response(
            "I'm having a bit of trouble understanding that. Could you try again?",
            {"personality": request.context_data.get("personality", "wise_narrator")}
        )
        
        return VoiceProcessResponse(
            voice_audio=base64.b64encode(error_audio).decode('utf-8'),
            transcript="Error processing request",
            visual_data=None,
            actions_taken=[],
            state="idle"
        )


@router.post("/proactive", response_model=ProactiveSuggestionResponse)
async def get_proactive_suggestion(
    request: ProactiveSuggestionRequest,
    current_user: User = Depends(get_current_user)
) -> Optional[ProactiveSuggestionResponse]:
    """
    Get proactive suggestions based on context and triggers.
    Returns None if no suggestion is appropriate.
    """
    try:
        # Check if user has proactive suggestions enabled
        if not current_user.preferences.get("proactive_suggestions", True):
            return None
        
        # Get suggestion from orchestrator
        suggestion = await voice_orchestrator.proactive_suggestion(
            user_id=str(current_user.id),
            trigger=request.trigger,
            context_data=request.context_data
        )
        
        if not suggestion:
            return None
        
        # Encode audio
        voice_audio_base64 = base64.b64encode(suggestion["voice_audio"]).decode('utf-8')
        
        return ProactiveSuggestionResponse(
            voice_audio=voice_audio_base64,
            transcript=suggestion["transcript"],
            trigger=suggestion["trigger"],
            can_dismiss=suggestion.get("can_dismiss", True)
        )
        
    except Exception as e:
        logger.error(f"Proactive suggestion error: {e}")
        return None


@router.put("/preferences")
async def update_voice_preferences(
    preferences: Dict[str, Any],
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    """
    Update user's voice interaction preferences.
    """
    try:
        # Update user preferences
        current_user.preferences["voice"] = preferences
        
        # Save to database (assuming we have a user service)
        # await user_service.update_preferences(current_user.id, current_user.preferences)
        
        logger.info(f"Updated voice preferences for user {current_user.id}")
        
        return JSONResponse(
            content={"message": "Preferences updated successfully"},
            status_code=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Failed to update preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences"
        )


@router.get("/status")
async def get_voice_status(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current voice orchestration status and capabilities.
    """
    return {
        "available": True,
        "supported_personalities": [
            "wise_narrator",
            "enthusiastic_buddy", 
            "local_expert"
        ],
        "features": {
            "proactive_suggestions": True,
            "multi_language": False,  # Coming soon
            "offline_mode": True,     # Now supported!
            "spatial_audio": True,
            "response_caching": True,
            "circuit_breakers": True
        },
        "user_preferences": current_user.preferences.get("voice", {})
    }


@router.get("/metrics")
async def get_voice_metrics(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get real-time voice system metrics and performance data.
    """
    # Get real-time metrics
    metrics = voice_monitoring.get_real_time_metrics()
    
    # Get performance trends
    trends = voice_monitoring.get_performance_trends(window_minutes=30)
    
    # Get error analysis
    errors = voice_monitoring.get_error_analysis()
    
    return {
        "real_time": metrics,
        "trends": trends,
        "errors": errors,
        "circuit_breakers": {
            "stt": voice_orchestrator.circuit_breakers["stt"].state,
            "tts": voice_orchestrator.circuit_breakers["tts"].state,
            "ai": voice_orchestrator.circuit_breakers["ai"].state,
            "booking": voice_orchestrator.circuit_breakers["booking"].state
        }
    }