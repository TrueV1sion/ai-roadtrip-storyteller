from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import uuid
import time

from app.core.unified_ai_client import StoryStyle
from app.core.unified_ai_client_cached import cached_ai_client
from app.core.authorization import get_current_active_user, get_optional_user, UserRole
from app.database import get_db
from app.models import User, Story
from app.core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class LocationCoordinates(BaseModel):
    """Model for location coordinates."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    
    @validator('latitude')
    def validate_latitude(cls, v):
        if not -90 <= v <= 90:
            raise ValueError('Latitude must be between -90 and 90')
        return v
        
    @validator('longitude')
    def validate_longitude(cls, v):
        if not -180 <= v <= 180:
            raise ValueError('Longitude must be between -180 and 180')
        return v


class GenerateStoryRequest(BaseModel):
    """Request model for story generation."""
    location: LocationCoordinates
    interests: List[str] = Field(..., min_items=1, max_items=5)
    style: Optional[StoryStyle] = StoryStyle.DEFAULT
    context: Optional[Dict[str, Any]] = None
    conversation_id: Optional[str] = None
    save: bool = False  # Whether to save the story to the database
    force_refresh: bool = False  # Whether to bypass the cache


class StoryResponse(BaseModel):
    """Response model for generated stories."""
    id: Optional[str] = None
    text: str
    location: LocationCoordinates
    interests: List[str]
    style: StoryStyle
    metadata: Dict[str, Any]
    saved: bool
    from_cache: Optional[bool] = None


@router.post("/generate", response_model=StoryResponse)
async def generate_story(
    request: GenerateStoryRequest,
    client_request: Request,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Generate a location-based story.
    
    This endpoint supports both authenticated and anonymous users, with
    different rate limits and capabilities based on user status.
    """
    # Get client IP for logging
    client_ip = client_request.client.host if client_request.client else None
    
    # Determine user status
    is_premium = current_user and (current_user.is_premium or current_user.role in [UserRole.PREMIUM, UserRole.ADMIN])
    user_id = current_user.id if current_user else None
    
    # Apply rate limiting for anonymous and standard users
    if not current_user:
        # Log anonymous request
        logger.info(f"Anonymous story generation request from IP {client_ip}")
        
        # Anonymous users can only use basic styles
        if request.style not in [StoryStyle.DEFAULT, StoryStyle.FAMILY]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This storytelling style is only available for authenticated users."
            )
            
        # Anonymous users cannot save stories
        if request.save:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Saving stories is only available for authenticated users."
            )
            
        # Anonymous users cannot use conversation context
        if request.conversation_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Conversation context is only available for authenticated users."
            )
    
    elif not is_premium:
        # Standard users are limited in some features
        # Check specific style restrictions
        if request.style in [StoryStyle.HISTORIC, StoryStyle.MYSTERY]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This storytelling style is only available for premium users."
            )
            
        # Rate limit check would go here
        # For example, checking how many stories generated in the last 24 hours
        if db:
            recent_stories_count = db.query(Story).filter(
                Story.user_id == user_id,
                Story.created_at >= time.time() - 86400  # Last 24 hours
            ).count()
            
            if recent_stories_count >= 10:  # Limit for standard users
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Story generation limit reached. Upgrade to premium for unlimited stories."
                )
    
    # Add user preferences to context if authenticated
    context = request.context or {}
    if current_user and hasattr(current_user, 'preferences') and current_user.preferences:
        context['user_preferences'] = current_user.preferences
    
    try:
        # Generate the story with caching
        story_result = await cached_ai_client.generate_story(
            location=request.location.dict(),
            interests=request.interests,
            context=context,
            style=request.style,
            conversation_id=request.conversation_id,
            force_refresh=request.force_refresh,
            user_id=str(user_id) if user_id else None,
            is_premium=is_premium
        )
        
        if story_result.get("is_fallback", False) and current_user:
            # Log fallback for authenticated users for better monitoring
            logger.warning(f"Fallback story generated for user {user_id}: {story_result.get('error', 'Unknown error')}")
        
        # Create response object
        story_id = None
        saved = False
        
        # Save to database if requested and authenticated
        if request.save and current_user:
            story_db = Story(
                id=str(uuid.uuid4()),
                user_id=current_user.id,
                content=story_result["text"],
                location_latitude=request.location.latitude,
                location_longitude=request.location.longitude,
                style=request.style.value,
                interests=request.interests,
                metadata={
                    "generation_time": story_result.get("generation_time"),
                    "word_count": story_result.get("word_count"),
                    "provider": story_result.get("provider"),
                    "model": story_result.get("model"),
                    "sentiment": story_result.get("sentiment"),
                    "is_fallback": story_result.get("is_fallback", False)
                }
            )
            
            db.add(story_db)
            db.commit()
            db.refresh(story_db)
            
            story_id = story_db.id
            saved = True
        
        return StoryResponse(
            id=story_id,
            text=story_result["text"],
            location=request.location,
            interests=request.interests,
            style=request.style,
            metadata={
                "generation_time": story_result.get("generation_time"),
                "word_count": story_result.get("word_count"),
                "provider": story_result.get("provider"),
                "model": story_result.get("model"),
                "sentiment": story_result.get("sentiment"),
                "is_fallback": story_result.get("is_fallback", False)
            },
            saved=saved,
            from_cache=story_result.get("from_cache", False)
        )
        
    except Exception as e:
        logger.error(f"Error in story generation endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during story generation."
        )


@router.post("/personalized", response_model=StoryResponse)
async def generate_personalized_story(
    request: GenerateStoryRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Generate a personalized story based on user preferences.
    
    This endpoint requires authentication and uses the user's saved preferences
    to generate a story tailored to their interests and preferences.
    """
    try:
        # Get user preferences
        user_preferences = current_user.preferences.dict() if hasattr(current_user, 'preferences') and current_user.preferences else {}
        
        # Add preferences to context
        context = request.context or {}
        context['user_preferences'] = user_preferences
        
        # Generate the personalized story with caching
        is_premium = current_user.is_premium or current_user.role in [UserRole.PREMIUM, UserRole.ADMIN]
        
        story_result = await cached_ai_client.generate_personalized_story(
            user_id=str(current_user.id),
            location=request.location.dict(),
            interests=request.interests,
            user_preferences=user_preferences,
            context=context,
            style=request.style,
            force_refresh=request.force_refresh,
            is_premium=is_premium
        )
        
        # Create response object
        story_id = None
        saved = False
        
        # Save to database if requested
        if request.save:
            story_db = Story(
                id=str(uuid.uuid4()),
                user_id=current_user.id,
                content=story_result["text"],
                location_latitude=request.location.latitude,
                location_longitude=request.location.longitude,
                style=request.style.value,
                interests=request.interests,
                is_personalized=True,
                metadata={
                    "generation_time": story_result.get("generation_time"),
                    "word_count": story_result.get("word_count"),
                    "provider": story_result.get("provider"),
                    "model": story_result.get("model"),
                    "sentiment": story_result.get("sentiment"),
                    "is_fallback": story_result.get("is_fallback", False),
                    "personalization_factors": list(user_preferences.keys())
                }
            )
            
            db.add(story_db)
            db.commit()
            db.refresh(story_db)
            
            story_id = story_db.id
            saved = True
        
        return StoryResponse(
            id=story_id,
            text=story_result["text"],
            location=request.location,
            interests=request.interests,
            style=request.style,
            metadata={
                "generation_time": story_result.get("generation_time"),
                "word_count": story_result.get("word_count"),
                "provider": story_result.get("provider"),
                "model": story_result.get("model"),
                "sentiment": story_result.get("sentiment"),
                "is_fallback": story_result.get("is_fallback", False),
                "personalized": True
            },
            saved=saved,
            from_cache=story_result.get("from_cache", False)
        )
        
    except Exception as e:
        logger.error(f"Error in personalized story generation endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during personalized story generation."
        )


@router.get("/saved", response_model=List[StoryResponse])
async def get_saved_stories(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all saved stories for the current user.
    """
    try:
        stories = db.query(Story).filter(Story.user_id == current_user.id).all()
        
        return [
            StoryResponse(
                id=story.id,
                text=story.content,
                location=LocationCoordinates(
                    latitude=story.location_latitude,
                    longitude=story.location_longitude
                ),
                interests=story.interests,
                style=StoryStyle(story.style) if hasattr(StoryStyle, story.style) else StoryStyle.DEFAULT,
                metadata=story.story_metadata or {},
                saved=True
            )
            for story in stories
        ]
        
    except Exception as e:
        logger.error(f"Error fetching saved stories: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching saved stories."
        )