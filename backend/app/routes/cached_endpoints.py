"""
Example of cached endpoints using the response cache system
"""
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.database_manager import get_db
from app.core.response_cache import response_cache, CacheStrategy
from app.core.auth import get_current_user_optional
from app.models.user import User
from app.models.story import Story
from app.models.booking import Booking
from app.schemas.story import StoryResponse
from app.schemas.booking import BookingResponse
from app.crud.crud_story import crud_story
from app.crud.crud_booking import crud_booking

router = APIRouter()


@router.get("/stories", response_model=List[StoryResponse])
@response_cache.cache_response(
    strategy=CacheStrategy.MODERATE,
    ttl=600,  # 10 minutes
    user_specific=True,
    invalidate_on=["POST", "PUT", "DELETE"]
)
async def get_cached_stories(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    journey_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Get stories with caching enabled.
    Cache is user-specific and invalidated on mutations.
    """
    filters = {}
    if journey_id:
        filters["journey_id"] = journey_id
    if current_user:
        filters["user_id"] = current_user.id
    
    stories = crud_story.get_multi(
        db, 
        skip=skip, 
        limit=limit,
        filters=filters,
        order_by=["-created_at"]
    )
    
    return stories


@router.get("/popular-stories", response_model=List[StoryResponse])
@response_cache.cache_response(
    strategy=CacheStrategy.AGGRESSIVE,
    ttl=3600,  # 1 hour for popular content
    user_specific=False
)
async def get_popular_stories(
    request: Request,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get popular stories with aggressive caching.
    Not user-specific, cached for 1 hour.
    """
    # This would typically involve more complex logic
    # to determine popularity (views, likes, etc.)
    stories = db.query(Story)\
        .filter(Story.is_active == True)\
        .order_by(Story.created_at.desc())\
        .limit(limit)\
        .all()
    
    return stories


@router.get("/bookings/recent", response_model=List[BookingResponse])
@response_cache.cache_response(
    strategy=CacheStrategy.CONSERVATIVE,
    ttl=60,  # 1 minute for time-sensitive data
    user_specific=True,
    invalidate_on=["POST", "PUT", "DELETE"]
)
async def get_recent_bookings(
    request: Request,
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Get recent bookings with conservative caching.
    Short TTL due to time-sensitive nature.
    """
    if not current_user:
        return []
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    bookings = db.query(Booking)\
        .filter(
            Booking.user_id == current_user.id,
            Booking.created_at >= cutoff_date
        )\
        .order_by(Booking.created_at.desc())\
        .all()
    
    return bookings


@router.get("/static-content/{content_id}")
@response_cache.cache_response(
    strategy=CacheStrategy.AGGRESSIVE,
    ttl=7200,  # 2 hours for static content
    user_specific=False
)
async def get_static_content(
    request: Request,
    content_id: str,
    db: Session = Depends(get_db)
):
    """
    Get static content with very aggressive caching.
    """
    # Simulate fetching static content
    # In real app, this might be terms of service, about page, etc.
    content = {
        "id": content_id,
        "title": f"Static Content {content_id}",
        "body": "This is cached static content...",
        "last_updated": "2024-01-01"
    }
    
    return content


@router.get("/dynamic-recommendations")
@response_cache.cache_response(
    strategy=CacheStrategy.SMART,  # Adaptive caching
    user_specific=True,
    key_func=lambda req, *args, **kwargs: f"recommendations:{req.state.user.id if hasattr(req.state, 'user') else 'anon'}:{req.url.query}"
)
async def get_recommendations(
    request: Request,
    location: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Get recommendations with smart adaptive caching.
    Cache TTL adjusts based on content and time of day.
    """
    # Simulate recommendation logic
    recommendations = []
    
    if location:
        # Location-based recommendations
        recommendations.append({
            "type": "location",
            "title": f"Top spots in {location}",
            "items": ["Restaurant A", "Museum B", "Park C"]
        })
    
    if category:
        # Category-based recommendations
        recommendations.append({
            "type": "category",
            "title": f"Popular {category} activities",
            "items": ["Activity 1", "Activity 2", "Activity 3"]
        })
    
    if current_user:
        # Personalized recommendations
        recommendations.append({
            "type": "personalized",
            "title": "Based on your interests",
            "items": ["Custom 1", "Custom 2", "Custom 3"]
        })
    
    return {
        "recommendations": recommendations,
        "generated_at": datetime.utcnow().isoformat()
    }


# Cache invalidation endpoint
@router.delete("/cache/invalidate")
async def invalidate_cache(
    pattern: Optional[str] = Query(None, description="Cache key pattern to invalidate"),
    user_id: Optional[int] = Query(None, description="Invalidate cache for specific user"),
    path: Optional[str] = Query(None, description="Invalidate cache for specific path")
):
    """
    Manually invalidate cache entries.
    Requires admin permissions in production.
    """
    invalidated = 0
    
    if pattern:
        invalidated = await response_cache.invalidate(pattern)
    elif user_id:
        invalidated = await response_cache.invalidate_user_cache(user_id)
    elif path:
        invalidated = await response_cache.invalidate_path_cache(path)
    else:
        # Clear all cache
        invalidated = await response_cache.invalidate("cache:*")
    
    return {
        "status": "success",
        "invalidated_entries": invalidated,
        "timestamp": datetime.utcnow().isoformat()
    }