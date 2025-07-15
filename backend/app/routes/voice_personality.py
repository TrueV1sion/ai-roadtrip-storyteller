"""
Voice Personality API Routes

Endpoints for managing dynamic voice personalities based on context
"""

from typing import Optional, Dict, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..core.auth import get_current_user_optional
from ..core.cache import cache_manager
from ..core.logger import get_logger
from ..models.user import User
from ..services.personality_engine import personality_engine, VoicePersonality
from ..services.voice_personalities import (
    load_extended_personalities,
    get_personality_by_event,
    get_personality_for_mood
)
from ..services.tts_service import tts_synthesizer

logger = get_logger(__name__)
router = APIRouter(prefix="/api/voice", tags=["voice_personality"])


class LocationContext(BaseModel):
    lat: float
    lng: float
    state: Optional[str] = None
    region: Optional[str] = None


class PersonalityContextRequest(BaseModel):
    location: Optional[LocationContext] = None
    user_preferences: Optional[Dict[str, any]] = None
    user_id: Optional[str] = None
    event: Optional[str] = None
    mood: Optional[str] = None


class PersonalityResponse(BaseModel):
    personality: Dict[str, any]


class PersonalitiesListResponse(BaseModel):
    personalities: List[Dict[str, any]]


class GreetingResponse(BaseModel):
    audio_url: str
    greeting_text: str


def personality_to_dict(personality: VoicePersonality) -> Dict[str, any]:
    """Convert VoicePersonality to dictionary for API response"""
    return {
        "id": personality.id,
        "name": personality.name,
        "description": personality.description,
        "voice_id": personality.voice_id,
        "speaking_style": personality.speaking_style,
        "vocabulary_style": personality.vocabulary_style,
        "catchphrases": personality.catchphrases,
        "topics_of_expertise": personality.topics_of_expertise,
        "emotion_range": personality.emotion_range,
        "regional_accent": personality.regional_accent,
        "age_appropriate": personality.age_appropriate,
        "active_seasons": personality.active_seasons,
        "active_holidays": personality.active_holidays,
        "active_hours": personality.active_hours
    }


@router.post("/personalities", response_model=PersonalitiesListResponse)
async def get_available_personalities(
    request: PersonalityContextRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> PersonalitiesListResponse:
    """
    Get list of available voice personalities based on context
    """
    try:
        logger.info(f"Getting available personalities for user {current_user.id if current_user else 'anonymous'}")
        
        # Get all base personalities
        all_personalities = list(personality_engine.personalities.values())
        
        # Add extended personalities
        extended = load_extended_personalities()
        all_personalities.extend(extended.values())
        
        # Filter based on context
        available_personalities = []
        current_datetime = datetime.now()
        
        for personality in all_personalities:
            # Check if personality is currently active
            if personality.active_holidays:
                # Check if any holiday is active
                holiday_active = any(
                    personality_engine._check_holiday_personality(current_datetime)
                    for holiday in personality.active_holidays
                )
                if not holiday_active:
                    continue
                    
            # Check hour restrictions
            if personality.active_hours:
                current_hour = current_datetime.hour
                if not (personality.active_hours[0] <= current_hour <= personality.active_hours[1]):
                    continue
                    
            # Check age appropriateness if user has preferences
            if current_user and current_user.preferences:
                user_age_group = current_user.preferences.get("age_group", "adult")
                if personality.age_appropriate and user_age_group not in personality.age_appropriate:
                    continue
                    
            available_personalities.append(personality_to_dict(personality))
            
        return PersonalitiesListResponse(personalities=available_personalities)
        
    except Exception as e:
        logger.error(f"Error getting available personalities: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve personalities")


@router.post("/contextual-personality", response_model=PersonalityResponse)
async def get_contextual_personality(
    request: PersonalityContextRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> PersonalityResponse:
    """
    Get the best personality based on current context
    """
    try:
        logger.info(f"Getting contextual personality for user {current_user.id if current_user else 'anonymous'}")
        
        # Convert location context if provided
        location_dict = None
        if request.location:
            location_dict = {
                "lat": request.location.lat,
                "lng": request.location.lng,
                "state": request.location.state,
                "region": request.location.region
            }
            
        # Check for event-based personality first
        if request.event:
            event_personality = get_personality_by_event(request.event)
            if event_personality:
                return PersonalityResponse(personality=personality_to_dict(event_personality))
                
        # Check for mood-based personality
        if request.mood:
            mood_personality = get_personality_for_mood(request.mood)
            if mood_personality:
                return PersonalityResponse(personality=personality_to_dict(mood_personality))
        
        # Get contextual personality based on location and preferences
        personality = personality_engine.get_contextual_personality(
            location=location_dict,
            user_preferences=current_user.preferences if current_user else request.user_preferences,
            current_datetime=datetime.now()
        )
        
        return PersonalityResponse(personality=personality_to_dict(personality))
        
    except Exception as e:
        logger.error(f"Error getting contextual personality: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get contextual personality")


@router.get("/personality/{personality_id}/greeting", response_model=GreetingResponse)
async def get_personality_greeting(
    personality_id: str,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> GreetingResponse:
    """
    Get a sample greeting from a specific personality
    """
    try:
        # Check cache first
        cache_key = f"personality_greeting:{personality_id}"
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            return GreetingResponse(**cached_result)
        
        # Get the personality
        personality = personality_engine.personalities.get(personality_id)
        if not personality:
            # Check extended personalities
            extended = load_extended_personalities()
            personality = extended.get(personality_id)
            
        if not personality:
            raise HTTPException(status_code=404, detail="Personality not found")
            
        # Get greeting text
        greeting_text = personality_engine.get_personality_greeting(personality)
        
        # Synthesize greeting
        user_id = current_user.id if current_user else None
        ip_address = request.client.host if request.client else None
        
        audio_url = tts_synthesizer.synthesize_and_upload(
            text=greeting_text,
            personality=personality,
            user_id=user_id,
            ip_address=ip_address,
            is_premium=current_user.is_premium if current_user else False
        )
        
        if not audio_url:
            raise HTTPException(status_code=500, detail="Failed to synthesize greeting")
            
        result = {
            "audio_url": audio_url,
            "greeting_text": greeting_text
        }
        
        # Cache for 24 hours
        await cache_manager.set(cache_key, result, ttl=86400)
        
        return GreetingResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting personality greeting: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get personality greeting")


@router.post("/personality/{personality_id}/select")
async def select_personality(
    personality_id: str,
    current_user: User = Depends(get_current_user_optional)
) -> Dict[str, str]:
    """
    Save user's selected personality preference
    """
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
            
        # Verify personality exists
        personality = personality_engine.personalities.get(personality_id)
        if not personality:
            extended = load_extended_personalities()
            personality = extended.get(personality_id)
            
        if not personality:
            raise HTTPException(status_code=404, detail="Personality not found")
            
        # Update user preferences
        if not current_user.preferences:
            current_user.preferences = {}
            
        current_user.preferences["preferred_voice_personality"] = personality_id
        
        # Save to database (would need to implement this)
        # await update_user_preferences(current_user.id, current_user.preferences)
        
        logger.info(f"User {current_user.id} selected personality {personality_id}")
        
        return {"message": "Personality preference saved successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error selecting personality: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to save personality preference")