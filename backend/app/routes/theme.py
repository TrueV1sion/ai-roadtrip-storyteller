from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Dict, List, Optional

from app.core.logger import get_logger
from app.core.security import get_current_active_user, get_current_admin_user
from app.database import get_db
from app.models.user import User
from app.schemas.theme import (
    ThemeCreate,
    ThemeUpdate,
    ThemeResponse,
    ThemeDetailResponse,
    UserThemePreferenceCreate,
    UserThemePreferenceUpdate,
    UserThemePreferenceResponse,
    ThemedPromptRequest,
    ThemedPromptResponse,
    ThemeRecommendationRequest
)
from app.services.theme_engine import get_theme_engine, ThemeEngine

router = APIRouter()
logger = get_logger(__name__)


# Theme management endpoints (admin only)
@router.post("/admin/themes", response_model=ThemeDetailResponse, tags=["Themes"], status_code=status.HTTP_201_CREATED)
async def create_theme(
    theme: ThemeCreate,
    theme_engine: ThemeEngine = Depends(get_theme_engine),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Create a new theme (admin only).
    """
    try:
        new_theme = await theme_engine.create_theme(theme.dict())
        return new_theme
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating theme: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create theme"
        )


@router.put("/admin/themes/{theme_id}", response_model=ThemeDetailResponse, tags=["Themes"])
async def update_theme(
    theme_id: str,
    theme: ThemeUpdate,
    theme_engine: ThemeEngine = Depends(get_theme_engine),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing theme (admin only).
    """
    try:
        updated_theme = await theme_engine.update_theme(theme_id, theme.dict(exclude_unset=True))
        if not updated_theme:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Theme not found"
            )
        return updated_theme
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating theme: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update theme"
        )


@router.delete("/admin/themes/{theme_id}", tags=["Themes"])
async def delete_theme(
    theme_id: str,
    theme_engine: ThemeEngine = Depends(get_theme_engine),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Delete a theme (admin only).
    """
    try:
        success = await theme_engine.delete_theme(theme_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Theme not found"
            )
        return {"detail": "Theme deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting theme: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete theme"
        )


# Public theme endpoints
@router.get("/themes", response_model=List[ThemeResponse], tags=["Themes"])
async def list_themes(
    active_only: bool = Query(True, description="If true, only return active themes"),
    seasonal_check: bool = Query(True, description="If true, filter seasonal themes by current date"),
    theme_engine: ThemeEngine = Depends(get_theme_engine),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all available themes.
    """
    try:
        themes = await theme_engine.get_all_themes(
            active_only=active_only,
            seasonal_check=seasonal_check
        )
        return themes
    except Exception as e:
        logger.error(f"Error listing themes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list themes"
        )


@router.get("/themes/{theme_id}", response_model=ThemeResponse, tags=["Themes"])
async def get_theme(
    theme_id: str,
    theme_engine: ThemeEngine = Depends(get_theme_engine),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific theme by ID.
    """
    try:
        theme = await theme_engine.get_theme(theme_id)
        if not theme:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Theme not found"
            )
        return theme
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving theme: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve theme"
        )


@router.post("/themes/recommend", response_model=List[ThemeResponse], tags=["Themes"])
async def recommend_themes(
    request: ThemeRecommendationRequest,
    theme_engine: ThemeEngine = Depends(get_theme_engine),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Recommend themes based on location and interests.
    """
    try:
        themes = await theme_engine.recommend_themes(
            location=request.location,
            interests=request.interests,
            user_id=current_user.id,
            limit=request.limit
        )
        return themes
    except Exception as e:
        logger.error(f"Error recommending themes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to recommend themes"
        )


# User theme preferences
@router.get("/user/theme-preferences", tags=["Themes"])
async def get_user_theme_preferences(
    theme_engine: ThemeEngine = Depends(get_theme_engine),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a user's theme preferences.
    """
    try:
        preferences = await theme_engine.get_user_theme_preferences(current_user.id)
        return preferences
    except Exception as e:
        logger.error(f"Error retrieving theme preferences: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve theme preferences"
        )


@router.post("/user/theme-preferences", response_model=UserThemePreferenceResponse, tags=["Themes"])
async def set_theme_preference(
    preference: UserThemePreferenceCreate,
    theme_engine: ThemeEngine = Depends(get_theme_engine),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Set a user's preference for a theme.
    """
    try:
        result = await theme_engine.set_user_theme_preference(
            user_id=current_user.id,
            theme_id=preference.theme_id,
            is_favorite=preference.is_favorite,
            preference_level=preference.preference_level
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting theme preference: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set theme preference"
        )


# AI theme integration
@router.post("/themes/generate-prompt", response_model=ThemedPromptResponse, tags=["Themes"])
async def generate_themed_prompt(
    request: ThemedPromptRequest,
    theme_engine: ThemeEngine = Depends(get_theme_engine),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Generate a themed prompt by enhancing a base prompt with theme elements.
    """
    try:
        # Get theme details for the response
        theme = await theme_engine.get_theme(request.theme_id)
        if not theme:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Theme not found"
            )
        
        # Generate the themed prompt
        prompt = await theme_engine.generate_themed_prompt(
            theme_id=request.theme_id,
            base_prompt=request.base_prompt,
            location=request.location,
            interests=request.interests,
            context=request.context
        )
        
        return {
            "prompt": prompt,
            "theme_id": theme.id,
            "theme_name": theme.name
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating themed prompt: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate themed prompt"
        )