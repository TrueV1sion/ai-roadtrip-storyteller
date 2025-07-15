"""
Voice Assistant Route - Unified endpoint for all voice interactions

This route provides a single entry point for all voice-based interactions,
coordinating with the Master Orchestration Agent to handle diverse user requests
including storytelling, bookings, navigation, and general assistance.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
import json
import logging

from ..core.unified_ai_client import get_unified_ai_client
from ..core.authorization import get_current_active_user
from ..core.cache import get_cache_manager
from ..database import get_db
from ..models.user import User
from ..services.master_orchestration_agent import (
    MasterOrchestrationAgent, 
    JourneyContext,
    AgentResponse
)
from ..services.tts_service import TTSService
from ..services.stt_service import STTService
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice-assistant", tags=["Voice Assistant"])


class VoiceInput(BaseModel):
    """Voice input from user"""
    audio_data: Optional[str] = Field(None, description="Base64 encoded audio data")
    text: Optional[str] = Field(None, description="Text input (if already transcribed)")
    session_id: str = Field(..., description="Session ID for conversation continuity")
    

class LocationContext(BaseModel):
    """Current location context"""
    latitude: float
    longitude: float
    name: Optional[str] = None
    address: Optional[str] = None
    place_id: Optional[str] = None


class JourneyContextInput(BaseModel):
    """Journey context information"""
    current_location: LocationContext
    destination: Optional[LocationContext] = None
    journey_stage: str = Field(default="traveling", description="pre_trip, traveling, arrived")
    passengers: List[Dict[str, Any]] = Field(default_factory=list)
    vehicle_info: Dict[str, Any] = Field(default_factory=dict)
    weather: Optional[Dict[str, Any]] = None
    route_info: Optional[Dict[str, Any]] = None


class VoiceAssistantRequest(BaseModel):
    """Complete voice assistant request"""
    voice_input: VoiceInput
    journey_context: JourneyContextInput
    preferences: Optional[Dict[str, Any]] = None


class VoiceAssistantResponse(BaseModel):
    """Voice assistant response"""
    text: str
    audio_url: Optional[str] = None
    session_id: str
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    booking_opportunities: List[Dict[str, Any]] = Field(default_factory=list)
    requires_followup: bool = False
    conversation_id: Optional[str] = None


# Session management
class SessionManager:
    """Manages conversation sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, MasterOrchestrationAgent] = {}
        self.session_metadata: Dict[str, Dict[str, Any]] = {}
    
    def get_or_create_session(self, session_id: str, ai_client) -> MasterOrchestrationAgent:
        """Get existing session or create new one"""
        if session_id not in self.sessions:
            self.sessions[session_id] = MasterOrchestrationAgent(ai_client)
            self.session_metadata[session_id] = {
                'created_at': datetime.now(),
                'last_interaction': datetime.now(),
                'interaction_count': 0
            }
        
        # Update last interaction time
        self.session_metadata[session_id]['last_interaction'] = datetime.now()
        self.session_metadata[session_id]['interaction_count'] += 1
        
        return self.sessions[session_id]
    
    def clean_old_sessions(self, max_age_hours: int = 24):
        """Remove old sessions"""
        current_time = datetime.now()
        sessions_to_remove = []
        
        for session_id, metadata in self.session_metadata.items():
            age = current_time - metadata['created_at']
            if age.total_seconds() > max_age_hours * 3600:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            self.sessions.pop(session_id, None)
            self.session_metadata.pop(session_id, None)


# Global session manager
session_manager = SessionManager()


def get_tts_service() -> TTSService:
    """Get TTS service instance"""
    return TTSService()


def get_stt_service() -> STTService:
    """Get STT service instance"""
    return STTService()


@router.post("/interact", response_model=VoiceAssistantResponse)
async def voice_interaction(
    request: VoiceAssistantRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    ai_client = Depends(get_unified_ai_client),
    tts_service: TTSService = Depends(get_tts_service),
    stt_service: STTService = Depends(get_stt_service),
    cache_manager = Depends(get_cache_manager)
):
    """
    Main voice interaction endpoint.
    
    Accepts either audio or text input and returns a voice response
    with structured data for actions and booking opportunities.
    """
    try:
        # Get or create session
        master_agent = session_manager.get_or_create_session(
            request.voice_input.session_id, 
            ai_client
        )
        
        # Process audio input if provided
        user_text = request.voice_input.text
        if request.voice_input.audio_data and not user_text:
            try:
                transcription_result = await stt_service.transcribe_audio(
                    request.voice_input.audio_data
                )
                user_text = transcription_result.get('text', '')
                logger.info(f"Transcribed audio: {user_text}")
            except Exception as e:
                logger.error(f"Audio transcription failed: {e}")
                raise HTTPException(
                    status_code=400,
                    detail="Failed to process audio input"
                )
        
        if not user_text:
            raise HTTPException(
                status_code=400,
                detail="No input provided (neither text nor valid audio)"
            )
        
        # Create journey context
        journey_context = JourneyContext(
            current_location={
                'latitude': request.journey_context.current_location.latitude,
                'longitude': request.journey_context.current_location.longitude,
                'name': request.journey_context.current_location.name,
                'address': request.journey_context.current_location.address,
                'place_id': request.journey_context.current_location.place_id
            },
            current_time=datetime.now(),
            journey_stage=request.journey_context.journey_stage,
            passengers=request.journey_context.passengers,
            vehicle_info=request.journey_context.vehicle_info,
            weather=request.journey_context.weather or {},
            route_info=request.journey_context.route_info or {}
        )
        
        # Check cache for similar requests
        cache_key = f"voice_response:{current_user.id}:{hash(user_text[:50])}"
        cached_response = await cache_manager.get(cache_key)
        
        if cached_response and isinstance(cached_response, dict):
            logger.info("Returning cached voice response")
            return VoiceAssistantResponse(**cached_response)
        
        # Process through master orchestration agent
        agent_response: AgentResponse = await master_agent.process_user_input(
            user_input=user_text,
            context=journey_context,
            user=current_user
        )
        
        # Generate audio response in background
        audio_url = None
        if agent_response.text:
            # Get appropriate voice character based on context
            voice_settings = {
                'voice_id': request.preferences.get('voice_id', 'default') if request.preferences else 'default',
                'speaking_rate': request.preferences.get('speaking_rate', 1.0) if request.preferences else 1.0,
                'pitch': request.preferences.get('pitch', 0) if request.preferences else 0
            }
            
            try:
                audio_result = await tts_service.synthesize_speech(
                    text=agent_response.text,
                    voice_settings=voice_settings
                )
                audio_url = audio_result.get('audio_url')
            except Exception as e:
                logger.error(f"TTS generation failed: {e}")
                # Continue without audio - text response is still valuable
        
        # Prepare response
        response_data = VoiceAssistantResponse(
            text=agent_response.text,
            audio_url=audio_url,
            session_id=request.voice_input.session_id,
            actions=agent_response.actions,
            booking_opportunities=agent_response.booking_opportunities,
            requires_followup=agent_response.requires_followup,
            conversation_id=f"{current_user.id}_{request.voice_input.session_id}"
        )
        
        # Cache the response for 5 minutes
        await cache_manager.set(
            cache_key, 
            response_data.dict(), 
            expire=300
        )
        
        # Clean old sessions in background
        background_tasks.add_task(session_manager.clean_old_sessions)
        
        # Log interaction for analytics
        logger.info(f"Voice interaction completed for user {current_user.id}")
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice interaction failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Voice assistant encountered an error"
        )


@router.post("/booking-action")
async def process_booking_action(
    booking_id: str,
    action: str,
    session_id: str,
    additional_info: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    ai_client = Depends(get_unified_ai_client)
):
    """
    Process a booking action initiated from voice interaction.
    
    This endpoint handles confirmations, modifications, or cancellations
    of booking opportunities presented during voice interactions.
    """
    try:
        # Get session
        master_agent = session_manager.get_or_create_session(session_id, ai_client)
        
        # Find booking opportunity in conversation state
        booking_opportunity = None
        for opportunity in master_agent.conversation_state.booking_context.get('opportunities', []):
            if opportunity.get('id') == booking_id:
                booking_opportunity = opportunity
                break
        
        if not booking_opportunity:
            raise HTTPException(
                status_code=404,
                detail="Booking opportunity not found in session"
            )
        
        # Process action through booking agent
        booking_agent = master_agent.sub_agents.get('booking')
        if not booking_agent:
            raise HTTPException(
                status_code=500,
                detail="Booking service unavailable"
            )
        
        # Execute booking action
        result = await booking_agent.execute_booking(
            booking_opportunity=booking_opportunity,
            action=action,
            user=current_user,
            additional_info=additional_info
        )
        
        return {
            "status": "success",
            "booking_id": booking_id,
            "action": action,
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Booking action failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process booking action"
        )


@router.get("/session-history/{session_id}")
async def get_session_history(
    session_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get conversation history for a session.
    
    Useful for displaying chat history or debugging conversations.
    """
    try:
        if session_id not in session_manager.sessions:
            raise HTTPException(
                status_code=404,
                detail="Session not found"
            )
        
        master_agent = session_manager.sessions[session_id]
        conversation_state = master_agent.conversation_state
        
        # Get recent messages
        messages = conversation_state.message_history[-limit:]
        
        # Format for response
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                'timestamp': msg['timestamp'].isoformat(),
                'speaker': msg['speaker'],
                'content': msg['content'],
                'actions': msg.get('actions', []),
                'booking_opportunities': msg.get('booking_opportunities', [])
            })
        
        return {
            'session_id': session_id,
            'messages': formatted_messages,
            'active_topics': conversation_state.active_topics,
            'pending_actions': conversation_state.pending_actions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session history: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve session history"
        )


@router.post("/end-session/{session_id}")
async def end_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    End a conversation session.
    
    Cleans up resources and saves any pending state.
    """
    try:
        if session_id in session_manager.sessions:
            # Could save conversation history to database here
            session_manager.sessions.pop(session_id, None)
            session_manager.session_metadata.pop(session_id, None)
            
            return {
                "status": "success",
                "message": "Session ended successfully"
            }
        else:
            return {
                "status": "not_found",
                "message": "Session not found or already ended"
            }
            
    except Exception as e:
        logger.error(f"Failed to end session: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to end session"
        )