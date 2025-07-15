"""
Personality System API Routes

Endpoints for personality selection, management, and analytics.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from datetime import datetime

from ..core.auth import get_current_user
from ..models.user import User
from ..services.personality_integration import personality_integration
from ..services.personality_registry import personality_registry
from ..services.dynamic_personality_system import PersonalityContext
from ..core.logger import logger

router = APIRouter(prefix="/api/personality", tags=["personality"])


class PersonalitySelectionRequest(BaseModel):
    """Request model for personality selection"""
    journey_data: Dict[str, Any] = Field(
        ..., 
        description="Complete journey context including destination, event, etc."
    )
    user_mood: Optional[str] = Field(
        None, 
        description="Current user mood (excited, relaxed, romantic, etc.)"
    )
    override_personality: Optional[str] = Field(
        None,
        description="User-requested personality override"
    )


class PersonalitySelectionResponse(BaseModel):
    """Response model for personality selection"""
    selected: Dict[str, Any]
    confidence_score: float
    selection_reason: str
    alternatives: List[Dict[str, Any]]
    context_analysis: Dict[str, Any]


class PersonalityFeedback(BaseModel):
    """User feedback on personality"""
    personality_id: str
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    feedback: Optional[str] = Field(None, description="Optional text feedback")
    journey_id: Optional[str] = Field(None, description="Associated journey ID")


class PersonalityRecommendationRequest(BaseModel):
    """Request for personality recommendations"""
    event_type: Optional[str] = None
    location: Optional[Dict[str, str]] = None
    time_of_day: Optional[str] = None
    mood: Optional[str] = None
    special_occasion: Optional[str] = None


@router.post("/select", response_model=PersonalitySelectionResponse)
async def select_personality(
    request: PersonalitySelectionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Select the best personality for a journey based on comprehensive context analysis.
    
    The system considers:
    - Event type and venue
    - Location and region
    - Time of day and season
    - Weather conditions
    - User preferences and mood
    - Special occasions
    """
    try:
        # Add user preferences to journey data
        request.journey_data["user_id"] = current_user.id
        
        # Handle personality override
        if request.override_personality:
            # Verify the personality exists
            if not personality_registry.get_personality(request.override_personality):
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown personality: {request.override_personality}"
                )
            request.journey_data["user_preference_override"] = request.override_personality
        
        # Add mood if provided
        if request.user_mood:
            request.journey_data["user_mood"] = request.user_mood
        
        # Perform selection
        result = await personality_integration.select_personality_for_journey(
            user_id=str(current_user.id),
            journey_data=request.journey_data,
            user_preferences=current_user.preferences
        )
        
        # Format response
        return PersonalitySelectionResponse(
            selected={
                "id": result.selected_personality.id,
                "name": result.selected_personality.name,
                "description": result.selected_personality.description,
                "voice_settings": personality_integration.personality_engine.get_voice_settings(
                    result.selected_personality
                ),
                "greeting": personality_integration.personality_engine.get_personality_greeting(
                    result.selected_personality
                )
            },
            confidence_score=result.confidence_score,
            selection_reason=result.selection_reason,
            alternatives=[
                {
                    "id": alt[0].id,
                    "name": alt[0].name,
                    "score": alt[1]
                }
                for alt in result.alternatives
            ],
            context_analysis=result.context_analysis
        )
        
    except Exception as e:
        logger.error(f"Error selecting personality: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations")
async def get_personality_recommendations(
    event_type: Optional[str] = Query(None),
    mood: Optional[str] = Query(None),
    special_occasion: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """
    Get personality recommendations based on context.
    
    Returns up to 5 personality suggestions with match scores.
    """
    try:
        context = {
            "user_id": str(current_user.id)
        }
        
        if event_type:
            context["event_type"] = event_type
        if mood:
            context["user_mood"] = mood
        if special_occasion:
            context["special_occasion"] = special_occasion
        
        recommendations = await personality_integration.get_personality_recommendations(
            user_id=str(current_user.id),
            context=context
        )
        
        return {
            "recommendations": recommendations,
            "total": len(recommendations)
        }
        
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback")
async def submit_personality_feedback(
    feedback: PersonalityFeedback,
    current_user: User = Depends(get_current_user)
):
    """Submit feedback on a personality experience."""
    try:
        await personality_integration.update_personality_preferences(
            user_id=str(current_user.id),
            personality_id=feedback.personality_id,
            rating=feedback.rating,
            feedback=feedback.feedback
        )
        
        return {
            "status": "success",
            "message": "Feedback recorded successfully"
        }
        
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/catalog")
async def get_personality_catalog(
    category: Optional[str] = Query(None, description="Filter by category"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    include_metadata: bool = Query(True, description="Include detailed metadata")
):
    """
    Get the complete personality catalog.
    
    Categories: event, holiday, regional, time_based, mood_based, special
    """
    try:
        # Get personalities based on filters
        if category:
            personalities = personality_registry.get_personalities_by_category(category)
        elif event_type:
            personalities = personality_registry.get_personalities_for_event(event_type)
        else:
            personalities = list(personality_registry.personalities.values())
        
        # Format response
        catalog = []
        for p in personalities:
            entry = {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "priority": p.priority
            }
            
            if include_metadata:
                entry.update({
                    "event_types": p.event_types,
                    "personality_traits": p.personality_traits,
                    "time_slots": p.time_slots,
                    "weather_preferences": p.weather_preferences,
                    "active_months": p.active_months,
                    "enthusiasm_level": p.enthusiasm_level,
                    "formality_level": p.formality_level
                })
            
            catalog.append(entry)
        
        return {
            "personalities": catalog,
            "total": len(catalog),
            "categories": ["event", "holiday", "regional", "time_based", "mood_based", "special"]
        }
        
    except Exception as e:
        logger.error(f"Error getting personality catalog: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics")
async def get_personality_analytics(
    current_user: User = Depends(get_current_user)
):
    """
    Get analytics on personality usage and selection patterns.
    
    Requires admin access.
    """
    # Check admin access
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        analytics = personality_integration.get_personality_analytics()
        
        return {
            "analytics": analytics,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preview/{personality_id}")
async def preview_personality(
    personality_id: str,
    sample_text: Optional[str] = Query(
        "Welcome to your journey! I'm excited to guide you today.",
        description="Sample text to preview"
    )
):
    """
    Preview how a personality would deliver text.
    
    Returns the personality's greeting and a sample of adjusted text.
    """
    try:
        # Get personality from registry
        metadata = personality_registry.get_personality(personality_id)
        if not metadata:
            raise HTTPException(
                status_code=404,
                detail=f"Personality not found: {personality_id}"
            )
        
        # Get full personality object
        personality = await personality_integration.dynamic_system._get_personality_by_id(
            personality_id
        )
        
        # Get greeting
        greeting = personality_integration.personality_engine.get_personality_greeting(
            personality
        )
        
        # Adjust sample text
        adjusted_text = personality_integration.personality_engine.adjust_text_for_personality(
            sample_text,
            personality
        )
        
        # Get voice settings
        voice_settings = personality_integration.personality_engine.get_voice_settings(
            personality
        )
        
        return {
            "personality": {
                "id": personality.id,
                "name": personality.name,
                "description": personality.description
            },
            "preview": {
                "greeting": greeting,
                "sample_text": adjusted_text,
                "voice_settings": voice_settings,
                "catchphrases": personality.catchphrases[:3] if hasattr(personality, 'catchphrases') else []
            },
            "metadata": {
                "category": metadata.category,
                "traits": metadata.personality_traits,
                "enthusiasm": metadata.enthusiasm_level,
                "formality": metadata.formality_level
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing personality: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active")
async def get_active_personalities():
    """
    Get currently active personalities based on time, season, and holidays.
    
    Shows which special personalities are currently available.
    """
    try:
        current_time = datetime.now()
        active_personalities = []
        
        # Check each personality for active status
        for p_id, metadata in personality_registry.personalities.items():
            is_active = False
            activation_reasons = []
            
            # Check time slots
            current_hour = current_time.hour
            if metadata.time_slots:
                time_slot = "morning" if 5 <= current_hour < 12 else \
                           "afternoon" if 12 <= current_hour < 17 else \
                           "evening" if 17 <= current_hour < 21 else "night"
                
                if time_slot in metadata.time_slots:
                    is_active = True
                    activation_reasons.append(f"Active during {time_slot}")
            
            # Check active months
            if metadata.active_months and current_time.month in metadata.active_months:
                is_active = True
                activation_reasons.append(f"Active in {current_time.strftime('%B')}")
            
            # Check specific dates
            if metadata.active_dates:
                current_date = (current_time.month, current_time.day)
                if current_date in metadata.active_dates:
                    is_active = True
                    activation_reasons.append("Active on this date")
            
            # Always active if no temporal restrictions
            if (not metadata.time_slots and 
                not metadata.active_months and 
                not metadata.active_dates):
                is_active = True
                activation_reasons.append("Always available")
            
            if is_active:
                active_personalities.append({
                    "id": p_id,
                    "name": metadata.name,
                    "category": metadata.category,
                    "activation_reasons": activation_reasons,
                    "priority": metadata.priority
                })
        
        # Sort by priority
        active_personalities.sort(key=lambda x: x["priority"], reverse=True)
        
        return {
            "active_personalities": active_personalities,
            "total_active": len(active_personalities),
            "current_time": current_time.isoformat(),
            "special_highlights": [
                p for p in active_personalities 
                if p["category"] in ["holiday", "special"]
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting active personalities: {e}")
        raise HTTPException(status_code=500, detail=str(e))