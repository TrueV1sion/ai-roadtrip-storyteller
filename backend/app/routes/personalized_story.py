from fastapi import APIRouter, HTTPException, Depends, Request, Query, Body, status
from typing import Dict, List, Optional, Any
import uuid
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import time

from app.core.enhanced_ai_client import enhanced_ai_client
from app.core.enhanced_personalization import enhanced_personalization_engine
from app.core.cache import cacheable, redis_client, generate_cache_key
from app.core.config import settings
from app.core.logger import get_logger
from app.schemas.user import UserPreferencesBase
from app.schemas.story import StoryCreate, StoryResponse, StoryAnalysisResponse
from app.database import get_db
# Import specific CRUD functions
from app.crud.crud_preferences import get_preferences_dict
from app.crud.crud_story import create_story, get_story, update_story_rating
from app import models

logger = get_logger(__name__)
router = APIRouter()


class PersonalizedStoryRequest(BaseModel):
    """Request model for personalized story generation."""
    user_id: str # Keep user_id to fetch preferences
    location: Dict[str, float]
    interests: List[str]
    context: Optional[Dict[str, Any]] = None
    personalization_strategy: Optional[str] = "balanced"  # Added for enhanced personalization
    include_persona: Optional[bool] = True  # Added for enhanced personalization


class StoryRatingRequest(BaseModel):
    """Request model for rating a story."""
    rating: int = Field(..., ge=1, le=5)
    feedback: Optional[str] = None
    topics: Optional[List[str]] = None  # Added for tracking content interactions


class PersonalizedStoryResponse(BaseModel):
    """Response model for personalized story."""
    id: str
    story: str
    metadata: Dict[str, Any]


class ContentAnalysisRequest(BaseModel):
    """Request model for analyzing content relevance to user preferences."""
    user_id: str
    content: str
    target_interests: Optional[List[str]] = None


class ContentAdjustmentRequest(BaseModel):
    """Request model for adjusting content based on user preferences."""
    content: str
    user_id: Optional[str] = None
    filters: Optional[List[str]] = None


def _get_personalized_story_cache_key(payload: PersonalizedStoryRequest) -> str:
    """
    Generate a cache key for personalized story requests.
    
    Args:
        payload: The personalized story request
        
    Returns:
        str: Cache key
    """
    # Round coordinates to 4 decimal places for better cache hits
    location = payload.location
    lat = round(location.get("latitude", 0.0), 4)
    lng = round(location.get("longitude", 0.0), 4)
    
    # Sort interests for consistent key generation
    interests = sorted(payload.interests)
    
    # Extract context parameters if available
    context = payload.context or {}
    time_of_day = context.get("time_of_day")
    weather = context.get("weather")
    mood = context.get("mood")
    
    # Include personalization strategy in cache key
    personalization_strategy = payload.personalization_strategy or "balanced"
    
    # User-specific portion of the key
    user_key = f"user:{payload.user_id}"
    
    # Create a hash of the parameters
    params_dict = {
        "lat": lat,
        "lng": lng,
        "interests": ",".join(interests),
        "time_of_day": time_of_day,
        "weather": weather,
        "mood": mood,
        "strategy": personalization_strategy,
        "persona": "yes" if payload.include_persona else "no"
    }
    
    return generate_cache_key("personalized", user_key, params_dict)


@router.post("/stories/personalized", response_model=PersonalizedStoryResponse, tags=["Story"])
@cacheable(
    namespace="personalized_story",
    ttl=getattr(settings, "REDIS_CACHE_TTL_STORY", 86400),
    key_builder=lambda payload, db: _get_personalized_story_cache_key(payload) if isinstance(payload, PersonalizedStoryRequest) else None,
    skip_cache_if=lambda request: request.headers.get("X-Skip-Cache") == "true"
)
async def generate_personalized_story(
    payload: PersonalizedStoryRequest,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Generate a personalized story based on user preferences and context.
    Uses the enhanced personalization engine for more targeted content creation.
    """
    start_time = time.time()
    try:
        # 1. Fetch user preferences from DB
        user_prefs_dict = get_preferences_dict(db=db, user_id=payload.user_id)
        if not user_prefs_dict:
            logger.warning(f"Preferences not found for user {payload.user_id}. Using defaults.")
            user_prefs_dict = {}

        # 2. Extract location features using the enhanced personalization engine
        location_features = await enhanced_personalization_engine.extract_location_features(
            payload.location["latitude"], 
            payload.location["longitude"]
        )
        
        # 3. Generate dynamic persona for this request
        persona = await enhanced_personalization_engine.generate_dynamic_persona(
            user_id=payload.user_id,
            preferences=user_prefs_dict,
            context=payload.context
        )
        
        # 4. Generate the personalized story using the AI client
        generation_result = await enhanced_ai_client.generate_personalized_story(
            user_id=payload.user_id,
            location=payload.location,
            interests=payload.interests,
            user_preferences=user_prefs_dict,
            context=payload.context
        )

        # 5. Analyze content relevance to user interests
        relevance_analysis = await enhanced_personalization_engine.analyze_content_relevance(
            content=generation_result["text"],
            user_id=payload.user_id,
            user_preferences=user_prefs_dict,
            target_interests=payload.interests
        )
        
        # 6. Potentially adjust content to better match preferences if relevance is low
        adjusted_content = generation_result["text"]
        if relevance_analysis["overall_relevance"] < 0.4:
            logger.info(f"Low content relevance ({relevance_analysis['overall_relevance']:.2f}), adjusting content")
            adjusted_content = enhanced_personalization_engine.adjust_content_for_preferences(
                content=generation_result["text"],
                user_preferences=user_prefs_dict
            )
            
            # Update the text if it was adjusted
            if adjusted_content != generation_result["text"]:
                generation_result["text"] = adjusted_content
                generation_result["was_adjusted"] = True

        # 7. Create Story object data for DB
        story_data_for_db = StoryCreate(
            user_id=payload.user_id,
            content=generation_result["text"],
            latitude=payload.location["latitude"],
            longitude=payload.location["longitude"],
            interests=payload.interests,
            context=payload.context,
            # Store additional metadata
            metadata={
                "model": generation_result.get("model"),
                "generation_time": generation_result.get("generation_time"),
                "persona_used": persona.get("story_perspective"),
                "content_topics": relevance_analysis.get("content_topics", []),
                "personalization_strategy": payload.personalization_strategy,
                "relevance_score": relevance_analysis.get("overall_relevance", 0),
                "was_adjusted": generation_result.get("was_adjusted", False)
            }
        )

        # 8. Save the generated story to the DB
        created_story = create_story(db=db, story=story_data_for_db)
        if not created_story:
            raise HTTPException(status_code=500, detail="Failed to save generated story")

        # 9. Asynchronously track story generation as a view interaction
        try:
            content_topics = relevance_analysis.get("content_topics", [])
            await enhanced_personalization_engine.track_content_interaction(
                user_id=payload.user_id,
                content_id=str(created_story.id),
                interaction_type="view",
                content_topics=content_topics
            )
        except Exception as e:
            logger.warning(f"Failed to track content interaction: {e}")

        # 10. Return the response using the saved story ID
        total_time = time.time() - start_time
        logger.info(f"Personalized story generated in {total_time:.2f}s (AI: {generation_result.get('generation_time', 0):.2f}s)")
        
        return {
            "id": created_story.id,
            "story": created_story.content,
            "metadata": {
                "model": generation_result.get("model"),
                "generation_time": generation_result.get("generation_time"),
                "total_time": total_time,
                "sentiment": generation_result.get("sentiment"),
                "word_count": generation_result.get("word_count"),
                "is_fallback": generation_result.get("is_fallback", False),
                "matched_interests": relevance_analysis.get("matching_interests", []),
                "content_topics": relevance_analysis.get("content_topics", []),
                "persona_used": persona.get("story_perspective"),
                "relevance_score": relevance_analysis.get("overall_relevance", 0),
                "was_adjusted": generation_result.get("was_adjusted", False)
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating personalized story for user {payload.user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate personalized story: {str(e)}"
        )


@router.post("/stories/{story_id}/rate", tags=["Story"])
async def rate_story(
    story_id: str,
    rating_data: StoryRatingRequest,
    db: Session = Depends(get_db)
):
    """
    Record a rating for a story in the database and track the interaction
    to improve personalization.
    """
    try:
        # 1. Fetch the story from the DB
        story = get_story(db=db, story_id=story_id)
        if not story:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")

        # 2. Update the story rating in the DB
        updated_story = update_story_rating(
            db=db,
            story_id=story_id,
            rating=rating_data.rating,
            feedback=rating_data.feedback
        )
        if not updated_story:
            raise HTTPException(status_code=500, detail="Failed to update story rating")

        # 3. Track the rating interaction for personalization
        interaction_type = "like" if rating_data.rating >= 4 else "dislike" if rating_data.rating <= 2 else "neutral"
        
        # Use provided topics or extract from story content
        content_topics = rating_data.topics
        if not content_topics and hasattr(story, "metadata") and story.story_metadata:
            content_topics = story.story_metadata.get("content_topics", [])
            
        # Track the interaction asynchronously
        try:
            await enhanced_personalization_engine.track_content_interaction(
                user_id=story.user_id,
                content_id=story_id,
                interaction_type=interaction_type,
                content_topics=content_topics,
                interaction_data={"rating": rating_data.rating, "feedback": rating_data.feedback}
            )
        except Exception as e:
            logger.warning(f"Failed to track rating interaction: {e}")

        return {
            "status": "success",
            "story_id": story_id,
            "rating": rating_data.rating,
            "interaction_tracked": True
        }
        
    except Exception as e:
        logger.error(f"Error rating story {story_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record story rating: {str(e)}"
        )


@router.get("/stories/{story_id}/feedback", tags=["Story"])
async def get_story_feedback(story_id: str, db: Session = Depends(get_db)):
    """
    Get feedback/rating for a specific story from the database.
    """
    try:
        # 1. Fetch the story from the DB
        story = get_story(db=db, story_id=story_id)
        if not story:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")

        # 2. Extract feedback/rating info from the story object
        feedback_list = []
        if story.feedback:
            feedback_list.append({"feedback": story.feedback})

        return {
            "story_id": story_id,
            "rating": story.rating,
            "feedback": feedback_list,
            "metadata": story.story_metadata if hasattr(story, "metadata") else {}
        }
        
    except Exception as e:
        logger.error(f"Error getting feedback for story {story_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get story feedback: {str(e)}"
        )


@router.post("/stories/analyze", response_model=StoryAnalysisResponse, tags=["Story"])
async def analyze_story_relevance(
    payload: ContentAnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Analyze how relevant a piece of content is to a user's preferences and interests.
    """
    try:
        # Fetch user preferences if not provided with specific target interests
        user_preferences = None
        if not payload.target_interests:
            user_preferences = get_preferences_dict(db=db, user_id=payload.user_id)
            
        # Analyze content relevance using enhanced personalization engine
        relevance_results = await enhanced_personalization_engine.analyze_content_relevance(
            content=payload.content,
            user_id=payload.user_id,
            user_preferences=user_preferences,
            target_interests=payload.target_interests
        )
        
        return StoryAnalysisResponse(
            content_topics=relevance_results.get("content_topics", []),
            matching_interests=relevance_results.get("matching_interests", []),
            missing_interests=relevance_results.get("missing_interests", []),
            relevance_score=relevance_results.get("overall_relevance", 0),
            personalization_quality=relevance_results.get("personalization_quality", "low")
        )
        
    except Exception as e:
        logger.error(f"Error analyzing content relevance for user {payload.user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze content relevance: {str(e)}"
        )


@router.post("/stories/adjust", tags=["Story"])
async def adjust_story_content(
    payload: ContentAdjustmentRequest,
    db: Session = Depends(get_db)
):
    """
    Adjust content to better match user preferences and filters.
    """
    try:
        user_preferences = None
        if payload.user_id:
            user_preferences = get_preferences_dict(db=db, user_id=payload.user_id)
            
        # Adjust content using enhanced personalization engine
        adjusted_content = enhanced_personalization_engine.adjust_content_for_preferences(
            content=payload.content,
            user_preferences=user_preferences,
            content_filters=payload.filters
        )
        
        # Analyze changes
        was_adjusted = adjusted_content != payload.content
        if was_adjusted:
            word_count_before = len(payload.content.split())
            word_count_after = len(adjusted_content.split())
            change_percentage = abs(word_count_after - word_count_before) / word_count_before * 100
        else:
            word_count_before = len(payload.content.split())
            word_count_after = word_count_before
            change_percentage = 0
            
        return {
            "original_word_count": word_count_before,
            "adjusted_word_count": word_count_after,
            "change_percentage": round(change_percentage, 2),
            "was_adjusted": was_adjusted,
            "adjusted_content": adjusted_content
        }
        
    except Exception as e:
        logger.error(f"Error adjusting content: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to adjust content: {str(e)}"
        )


@router.get("/stories/trending-topics", tags=["Story"])
async def get_trending_topics(
    latitude: Optional[float] = None,
    longitude: Optional[float] = None
):
    """
    Get trending story topics, optionally filtered by location.
    """
    try:
        location = None
        if latitude is not None and longitude is not None:
            location = {"latitude": latitude, "longitude": longitude}
            
        # Get trending topics using enhanced personalization engine
        trending_topics = await enhanced_personalization_engine.get_trending_topics(location)
        
        return {
            "topics": trending_topics,
            "timestamp": int(time.time()),
            "location_specific": location is not None
        }
        
    except Exception as e:
        logger.error(f"Error getting trending topics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trending topics: {str(e)}"
        )