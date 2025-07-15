from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from app.core.logger import get_logger
from app.core.security import get_current_user
from app.core.authorization import require_admin
from app.core.enums import Action, ResourceType
from app.models.user import User
from app.core.unified_ai_client_cached import cached_ai_client
from app.core.ai_cache import ai_cache

logger = get_logger(__name__)
router = APIRouter()


class CacheStatsResponse(BaseModel):
    hit_count: int
    miss_count: int
    hit_rate: float
    total_time_saved: float


class CacheClearResponse(BaseModel):
    cleared_entries: int
    success: bool
    message: str


@router.get("/cache/stats", response_model=CacheStatsResponse, tags=["Cache"])
async def get_cache_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Get AI response cache statistics.
    Requires admin permissions.
    """
    # Ensure the user has admin permissions
    require_admin(current_user, Action.READ, ResourceType.SYSTEM)
    
    try:
        stats = cached_ai_client.get_cache_stats()
        return CacheStatsResponse(
            hit_count=stats["hit_count"],
            miss_count=stats["miss_count"],
            hit_rate=stats["hit_rate"],
            total_time_saved=stats["total_time_saved"]
        )
    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cache statistics"
        )


@router.delete("/cache/all", response_model=CacheClearResponse, tags=["Cache"])
async def clear_all_cache(
    current_user: User = Depends(get_current_user)
):
    """
    Clear all AI response caches.
    Requires admin permissions.
    """
    # Ensure the user has admin permissions
    require_admin(current_user, Action.DELETE, ResourceType.SYSTEM)
    
    try:
        story_count = cached_ai_client.clear_story_cache()
        personalized_count = cached_ai_client.clear_personalized_cache()
        total_count = story_count + personalized_count
        
        return CacheClearResponse(
            cleared_entries=total_count,
            success=True,
            message=f"Successfully cleared {total_count} cache entries"
        )
    except Exception as e:
        logger.error(f"Error clearing all cache: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cache"
        )


@router.delete("/cache/story", response_model=CacheClearResponse, tags=["Cache"])
async def clear_story_cache(
    current_user: User = Depends(get_current_user)
):
    """
    Clear all story caches.
    Requires admin permissions.
    """
    # Ensure the user has admin permissions
    require_admin(current_user, Action.DELETE, ResourceType.SYSTEM)
    
    try:
        count = cached_ai_client.clear_story_cache()
        return CacheClearResponse(
            cleared_entries=count,
            success=True,
            message=f"Successfully cleared {count} story cache entries"
        )
    except Exception as e:
        logger.error(f"Error clearing story cache: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear story cache"
        )


@router.delete("/cache/personalized", response_model=CacheClearResponse, tags=["Cache"])
async def clear_personalized_cache(
    current_user: User = Depends(get_current_user)
):
    """
    Clear all personalized story caches.
    Requires admin permissions.
    """
    # Ensure the user has admin permissions
    require_admin(current_user, Action.DELETE, ResourceType.SYSTEM)
    
    try:
        count = cached_ai_client.clear_personalized_cache()
        return CacheClearResponse(
            cleared_entries=count,
            success=True,
            message=f"Successfully cleared {count} personalized cache entries"
        )
    except Exception as e:
        logger.error(f"Error clearing personalized cache: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear personalized cache"
        )


@router.delete("/cache/user/{user_id}", response_model=CacheClearResponse, tags=["Cache"])
async def clear_user_cache(
    user_id: str = Path(..., description="User ID to clear cache for"),
    current_user: User = Depends(get_current_user)
):
    """
    Clear all cached responses for a specific user.
    Requires admin permissions or the user themselves.
    """
    # Ensure the user has admin permissions or is the user themselves
    if not current_user.is_admin and str(current_user.id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to clear another user's cache"
        )
    
    try:
        count = cached_ai_client.clear_user_cache(user_id)
        return CacheClearResponse(
            cleared_entries=count,
            success=True,
            message=f"Successfully cleared {count} cache entries for user {user_id}"
        )
    except Exception as e:
        logger.error(f"Error clearing user cache: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear user cache"
        )