from fastapi import APIRouter, Depends, HTTPException, Query, Path, status, Body
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any

from app.database import get_db
from app.core.logger import get_logger
from app.core.enhanced_personalization import enhanced_personalization_engine
from app.core.security import get_current_user
from app.models.user import User
from app.models.preferences import UserPreferences
from app.crud.crud_preferences import preferences_crud
from app.schemas.user import UserPreferencesResponse

logger = get_logger(__name__)
router = APIRouter()


@router.get("/personalization/features/{user_id}", response_model=Dict[str, Any])
async def get_user_personalization_features(
    user_id: str = Path(..., description="User ID to get personalization features for"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get personalization features for a user.
    Requires authentication and authorization (either the user themselves or an admin).
    """
    # Check authorization
    if str(current_user.id) != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access personalization features for this user"
        )
    
    # Get user preferences from DB
    preferences = preferences_crud.get_by_user_id(db, user_id=user_id)
    if not preferences:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User preferences not found"
        )
    
    # Extract personalization features
    try:
        model = await enhanced_personalization_engine.extract_user_features(
            current_user,
            preferences
        )
        
        # Return model as dictionary with feature categories
        result = {
            "interests": {
                f.name: f.value for f in model.get_features_by_category("interest")
            },
            "demographics": {
                f.name: f.value for f in model.get_features_by_category("demographic")
            },
            "content_preferences": {
                f.name: f.value for f in model.get_features_by_category("content_preference")
            },
            "travel_preferences": {
                f.name: f.value for f in model.get_features_by_category("travel_preference")
            },
            "accessibility": {
                f.name: f.value for f in model.get_features_by_category("accessibility")
            },
            "topics": model.topics
        }
        
        return result
    except Exception as e:
        logger.error(f"Error extracting personalization features: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extract personalization features"
        )


@router.post("/personalization/enhance-prompt", response_model=Dict[str, str])
async def enhance_prompt(
    base_prompt: str = Body(..., embed=True),
    user_id: Optional[str] = Body(None, embed=True),
    user_preferences: Optional[Dict[str, Any]] = Body(None, embed=True),
    location: Optional[Dict[str, float]] = Body(None, embed=True),
    context: Optional[Dict[str, Any]] = Body(None, embed=True),
    personalization_strategy: str = Body("balanced", embed=True),
    include_persona: bool = Body(True, embed=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Enhance a prompt with personalization based on user preferences and context.
    Returns the enhanced prompt.
    """
    # Verify that the user has access to personalize for the requested user_id
    if user_id and str(current_user.id) != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to personalize content for this user"
        )
    
    # If user_id is provided but no preferences, get preferences from DB
    if user_id and not user_preferences:
        preferences_obj = preferences_crud.get_by_user_id(db, user_id=user_id)
        if preferences_obj:
            user_preferences = preferences_obj.to_dict()
    
    # Enhance the prompt
    try:
        enhanced = await enhanced_personalization_engine.enhance_prompt(
            base_prompt=base_prompt,
            user_id=user_id,
            user_preferences=user_preferences,
            location=location,
            context=context,
            personalization_strategy=personalization_strategy,
            include_persona=include_persona
        )
        
        return {
            "original_prompt": base_prompt,
            "enhanced_prompt": enhanced
        }
    except Exception as e:
        logger.error(f"Error enhancing prompt: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enhance prompt"
        )


@router.post("/personalization/dynamic-persona", response_model=Dict[str, Any])
async def generate_dynamic_persona(
    user_id: Optional[str] = Body(None, embed=True),
    preferences: Optional[Dict[str, Any]] = Body(None, embed=True),
    context: Optional[Dict[str, Any]] = Body(None, embed=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a dynamic persona for content creation based on user data and context.
    """
    # Verify that the user has access to the requested user_id
    if user_id and str(current_user.id) != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to generate a persona for this user"
        )
    
    # Generate the persona
    try:
        persona = await enhanced_personalization_engine.generate_dynamic_persona(
            user_id=user_id,
            preferences=preferences,
            context=context
        )
        
        return persona
    except Exception as e:
        logger.error(f"Error generating dynamic persona: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate dynamic persona"
        )


@router.post("/personalization/location-features", response_model=Dict[str, Any])
async def get_location_features(
    latitude: float = Body(..., embed=True),
    longitude: float = Body(..., embed=True),
    radius_km: float = Body(5.0, embed=True),
    current_user: User = Depends(get_current_user)
):
    """
    Extract rich features about a location for personalization.
    """
    try:
        features = await enhanced_personalization_engine.extract_location_features(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km
        )
        
        return features
    except Exception as e:
        logger.error(f"Error extracting location features: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extract location features"
        )


@router.post("/personalization/analyze-content", response_model=Dict[str, Any])
async def analyze_content_relevance(
    content: str = Body(..., embed=True),
    user_id: Optional[str] = Body(None, embed=True),
    user_preferences: Optional[Dict[str, Any]] = Body(None, embed=True),
    target_interests: Optional[List[str]] = Body(None, embed=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyze how well content matches a user's interests and preferences.
    """
    # Verify that the user has access to analyze for the requested user_id
    if user_id and str(current_user.id) != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to analyze content for this user"
        )
    
    # If user_id is provided but no preferences, get preferences from DB
    if user_id and not user_preferences and not target_interests:
        preferences_obj = preferences_crud.get_by_user_id(db, user_id=user_id)
        if preferences_obj:
            user_preferences = preferences_obj.to_dict()
    
    # Analyze the content
    try:
        analysis = await enhanced_personalization_engine.analyze_content_relevance(
            content=content,
            user_id=user_id,
            user_preferences=user_preferences,
            target_interests=target_interests
        )
        
        return analysis
    except Exception as e:
        logger.error(f"Error analyzing content relevance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze content relevance"
        )


@router.post("/personalization/adjust-content", response_model=Dict[str, str])
async def adjust_content_for_preferences(
    content: str = Body(..., embed=True),
    user_preferences: Optional[Dict[str, Any]] = Body(None, embed=True),
    content_filters: Optional[List[str]] = Body(None, embed=True),
    current_user: User = Depends(get_current_user)
):
    """
    Adjust content to better match user preferences and filters.
    """
    try:
        adjusted = enhanced_personalization_engine.adjust_content_for_preferences(
            content=content,
            user_preferences=user_preferences,
            content_filters=content_filters
        )
        
        return {
            "original_content": content,
            "adjusted_content": adjusted
        }
    except Exception as e:
        logger.error(f"Error adjusting content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to adjust content"
        )


@router.post("/personalization/track-interaction", response_model=Dict[str, bool])
async def track_content_interaction(
    user_id: str = Body(..., embed=True),
    content_id: str = Body(..., embed=True),
    interaction_type: str = Body(..., embed=True),
    content_topics: Optional[List[str]] = Body(None, embed=True),
    interaction_data: Optional[Dict[str, Any]] = Body(None, embed=True),
    current_user: User = Depends(get_current_user)
):
    """
    Track user interaction with content to improve personalization.
    """
    # Verify that the user has access to track interactions for the requested user_id
    if str(current_user.id) != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to track interactions for this user"
        )
    
    # Track the interaction
    try:
        success = await enhanced_personalization_engine.track_content_interaction(
            user_id=user_id,
            content_id=content_id,
            interaction_type=interaction_type,
            content_topics=content_topics,
            interaction_data=interaction_data
        )
        
        return {"success": success}
    except Exception as e:
        logger.error(f"Error tracking content interaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to track content interaction"
        )


@router.get("/personalization/trending-topics", response_model=List[Dict[str, Any]])
async def get_trending_topics(
    latitude: Optional[float] = Query(None, description="Optional latitude for location context"),
    longitude: Optional[float] = Query(None, description="Optional longitude for location context"),
    current_user: User = Depends(get_current_user)
):
    """
    Get trending topics, optionally filtered by location.
    """
    location = None
    if latitude is not None and longitude is not None:
        location = {"latitude": latitude, "longitude": longitude}
    
    try:
        topics = await enhanced_personalization_engine.get_trending_topics(location)
        return topics
    except Exception as e:
        logger.error(f"Error getting trending topics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get trending topics"
        )