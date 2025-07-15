from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any

from app.core.logger import get_logger
from app.core.security import get_current_active_user, get_current_admin_user
from app.database import get_db
from app.models.user import User
from app.services.side_quest_generator import get_side_quest_generator, SideQuestGenerator
from app.services.directions_service import get_directions_service, DirectionsService
from app.schemas.side_quest import (
    SideQuestCreate,
    SideQuestUpdate,
    SideQuestResponse,
    SideQuestCategoryCreate,
    SideQuestCategoryUpdate,
    SideQuestCategoryResponse,
    UserSideQuestCreate,
    UserSideQuestUpdate,
    UserSideQuestResponse,
    UserSideQuestDetailResponse,
    NearbyQuestRequest,
    RouteQuestRequest,
    RecommendQuestRequest,
    SideQuestStatus
)

router = APIRouter()
logger = get_logger(__name__)


# Side Quest Categories endpoints
@router.get("/side-quests/categories", response_model=List[SideQuestCategoryResponse], tags=["Side Quests"])
async def list_side_quest_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all side quest categories.
    """
    side_quest_generator = get_side_quest_generator(db)
    categories = await side_quest_generator.seed_side_quest_categories()
    return categories


@router.post("/admin/side-quests/categories", response_model=SideQuestCategoryResponse, tags=["Admin"], status_code=status.HTTP_201_CREATED)
async def create_side_quest_category(
    category: SideQuestCategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Create a new side quest category (admin only).
    """
    # Implementation to be added
    pass


# Side Quests endpoints
@router.get("/side-quests", response_model=List[SideQuestResponse], tags=["Side Quests"])
async def list_side_quests(
    latitude: Optional[float] = Query(None, description="Latitude for nearby search"),
    longitude: Optional[float] = Query(None, description="Longitude for nearby search"),
    radius: Optional[float] = Query(10.0, description="Search radius in kilometers"),
    limit: Optional[int] = Query(20, description="Maximum number of results to return"),
    category: Optional[str] = Query(None, description="Category ID to filter by"),
    difficulty: Optional[str] = Query(None, description="Difficulty level to filter by"),
    max_detour_time: Optional[int] = Query(None, description="Maximum detour time in minutes"),
    min_uniqueness: Optional[float] = Query(None, description="Minimum uniqueness score (0-100)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    side_quest_generator: SideQuestGenerator = Depends(get_side_quest_generator)
):
    """
    List side quests, optionally filtering by location and other criteria.
    """
    try:
        if latitude is None or longitude is None:
            # Return general quests or an error
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Latitude and longitude are required for side quest search"
            )
        
        categories = [category] if category else None
        
        side_quests = await side_quest_generator.get_nearby_side_quests(
            latitude=latitude,
            longitude=longitude,
            radius=radius,
            limit=limit,
            categories=categories,
            difficulty=difficulty,
            max_detour_time=max_detour_time,
            min_uniqueness=min_uniqueness
        )
        
        return side_quests
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing side quests: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list side quests"
        )


@router.post("/side-quests/nearby", response_model=List[SideQuestResponse], tags=["Side Quests"])
async def find_nearby_side_quests(
    request: NearbyQuestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    side_quest_generator: SideQuestGenerator = Depends(get_side_quest_generator)
):
    """
    Find side quests near a location.
    """
    try:
        side_quests = await side_quest_generator.get_nearby_side_quests(
            latitude=request.latitude,
            longitude=request.longitude,
            radius=request.radius,
            limit=request.limit,
            categories=request.categories,
            difficulty=request.difficulty,
            max_detour_time=request.max_detour_time,
            min_uniqueness=request.min_uniqueness,
            include_inactive=request.include_inactive,
            include_seasonal=request.include_seasonal
        )
        
        return side_quests
    except Exception as e:
        logger.error(f"Error finding nearby side quests: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to find nearby side quests"
        )


@router.post("/side-quests/route", tags=["Side Quests"])
async def find_side_quests_along_route(
    request: RouteQuestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    side_quest_generator: SideQuestGenerator = Depends(get_side_quest_generator),
    directions_service: DirectionsService = Depends(get_directions_service)
):
    """
    Find side quests along a route.
    """
    try:
        # Get the route from the directions service
        route = await directions_service.get_route(request.route_id)
        if not route:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Route not found"
            )
        
        # Get side quests along the route
        quest_distances = await side_quest_generator.get_side_quests_along_route(
            route=route,
            max_distance=request.max_distance,
            limit=request.limit,
            categories=request.categories,
            difficulty=request.difficulty,
            max_detour_time=request.max_detour_time,
            min_uniqueness=request.min_uniqueness,
            include_inactive=request.include_inactive,
            include_seasonal=request.include_seasonal
        )
        
        # Format the response
        results = []
        for quest, distance in quest_distances:
            quest_data = {
                "side_quest": quest,
                "distance_from_route": distance
            }
            results.append(quest_data)
        
        return {"results": results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding side quests along route: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to find side quests along route"
        )


@router.post("/side-quests/recommend", response_model=List[SideQuestResponse], tags=["Side Quests"])
async def recommend_side_quests(
    request: RecommendQuestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    side_quest_generator: SideQuestGenerator = Depends(get_side_quest_generator),
    directions_service: DirectionsService = Depends(get_directions_service)
):
    """
    Recommend side quests for a user based on route and preferences.
    """
    try:
        # Get the route from the directions service
        route = await directions_service.get_route(request.route_id)
        if not route:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Route not found"
            )
        
        # Get recommended side quests
        recommendations = await side_quest_generator.recommend_side_quests(
            user_id=current_user.id,
            route=route,
            current_location=request.current_location,
            user_interests=request.user_interests,
            available_time=request.available_time,
            count=request.count,
            trip_id=request.trip_id
        )
        
        return recommendations
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recommending side quests: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to recommend side quests"
        )


@router.get("/side-quests/{side_quest_id}", response_model=SideQuestResponse, tags=["Side Quests"])
async def get_side_quest(
    side_quest_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    side_quest_generator: SideQuestGenerator = Depends(get_side_quest_generator)
):
    """
    Get a specific side quest by ID.
    """
    try:
        side_quest = await side_quest_generator.get_side_quest(side_quest_id)
        if not side_quest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Side quest not found"
            )
        
        return side_quest
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving side quest: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve side quest"
        )


@router.post("/side-quests", response_model=SideQuestResponse, tags=["Side Quests"], status_code=status.HTTP_201_CREATED)
async def create_side_quest(
    side_quest: SideQuestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    side_quest_generator: SideQuestGenerator = Depends(get_side_quest_generator)
):
    """
    Create a new side quest (user-generated).
    """
    try:
        # Set created_by to current user and mark as user-generated
        new_side_quest = await side_quest_generator.create_side_quest(
            title=side_quest.title,
            description=side_quest.description,
            latitude=side_quest.latitude,
            longitude=side_quest.longitude,
            location_name=side_quest.location_name,
            address=side_quest.address,
            category=side_quest.category,
            difficulty=side_quest.difficulty,
            estimated_duration=side_quest.estimated_duration,
            distance_from_route=side_quest.distance_from_route,
            detour_time=side_quest.detour_time,
            uniqueness_score=side_quest.uniqueness_score,
            image_url=side_quest.image_url,
            thumbnail_url=side_quest.thumbnail_url,
            external_id=side_quest.external_id,
            external_rating=side_quest.external_rating,
            external_url=side_quest.external_url,
            requirements=side_quest.requirements,
            rewards=side_quest.rewards,
            tags=side_quest.tags,
            operating_hours=side_quest.operating_hours,
            price_level=side_quest.price_level,
            is_verified=False,  # User-created quests need verification
            is_user_generated=True,
            is_active=True,
            is_seasonal=side_quest.is_seasonal,
            seasonal_start=side_quest.seasonal_start,
            seasonal_end=side_quest.seasonal_end,
            created_by=current_user.id,
            source="user"
        )
        
        return new_side_quest
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating side quest: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create side quest"
        )


@router.put("/admin/side-quests/{side_quest_id}", response_model=SideQuestResponse, tags=["Admin"])
async def update_side_quest(
    side_quest_id: str,
    side_quest: SideQuestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Update a side quest (admin only).
    """
    # Implementation to be added
    pass


@router.delete("/admin/side-quests/{side_quest_id}", tags=["Admin"])
async def delete_side_quest(
    side_quest_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Delete a side quest (admin only).
    """
    # Implementation to be added
    pass


# User Side Quests endpoints
@router.get("/user/side-quests", tags=["Side Quests"])
async def get_user_side_quests(
    status: Optional[str] = Query(None, description="Filter by status"),
    trip_id: Optional[str] = Query(None, description="Filter by trip ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    side_quest_generator: SideQuestGenerator = Depends(get_side_quest_generator)
):
    """
    Get a user's side quests.
    """
    try:
        user_side_quests = await side_quest_generator.get_user_side_quests(
            user_id=current_user.id,
            status=status,
            include_details=True,
            trip_id=trip_id
        )
        
        return {"user_side_quests": user_side_quests}
    except Exception as e:
        logger.error(f"Error retrieving user side quests: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user side quests"
        )


@router.post("/user/side-quests", response_model=UserSideQuestResponse, tags=["Side Quests"], status_code=status.HTTP_201_CREATED)
async def add_user_side_quest(
    user_side_quest: UserSideQuestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    side_quest_generator: SideQuestGenerator = Depends(get_side_quest_generator)
):
    """
    Add a side quest to a user's list.
    """
    try:
        # Check if the side quest exists
        side_quest = await side_quest_generator.get_side_quest(user_side_quest.side_quest_id)
        if not side_quest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Side quest not found"
            )
        
        # Check if the user already has this side quest
        existing = await side_quest_generator.get_user_side_quest(current_user.id, user_side_quest.side_quest_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already has this side quest"
            )
        
        # Update the user's side quest status
        updated = await side_quest_generator.update_user_side_quest_status(
            user_id=current_user.id,
            side_quest_id=user_side_quest.side_quest_id,
            status=user_side_quest.status.value if user_side_quest.status else SideQuestStatus.AVAILABLE.value,
            progress=user_side_quest.progress,
            feedback=user_side_quest.feedback,
            user_rating=user_side_quest.user_rating
        )
        
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding user side quest: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add user side quest"
        )


@router.put("/user/side-quests/{side_quest_id}", response_model=UserSideQuestResponse, tags=["Side Quests"])
async def update_user_side_quest(
    side_quest_id: str,
    update: UserSideQuestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    side_quest_generator: SideQuestGenerator = Depends(get_side_quest_generator)
):
    """
    Update a user's side quest status.
    """
    try:
        # Update the user's side quest status
        updated = await side_quest_generator.update_user_side_quest_status(
            user_id=current_user.id,
            side_quest_id=side_quest_id,
            status=update.status,
            progress=update.progress,
            feedback=update.feedback,
            user_rating=update.user_rating
        )
        
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user side quest: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user side quest"
        )


@router.put("/user/side-quests/{side_quest_id}/accept", response_model=UserSideQuestResponse, tags=["Side Quests"])
async def accept_side_quest(
    side_quest_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    side_quest_generator: SideQuestGenerator = Depends(get_side_quest_generator)
):
    """
    Accept a side quest.
    """
    try:
        # Update the user's side quest status to ACCEPTED
        updated = await side_quest_generator.update_user_side_quest_status(
            user_id=current_user.id,
            side_quest_id=side_quest_id,
            status=SideQuestStatus.ACCEPTED.value
        )
        
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accepting side quest: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to accept side quest"
        )


@router.put("/user/side-quests/{side_quest_id}/complete", response_model=UserSideQuestResponse, tags=["Side Quests"])
async def complete_side_quest(
    side_quest_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    side_quest_generator: SideQuestGenerator = Depends(get_side_quest_generator)
):
    """
    Mark a side quest as completed.
    """
    try:
        # Update the user's side quest status to COMPLETED
        updated = await side_quest_generator.update_user_side_quest_status(
            user_id=current_user.id,
            side_quest_id=side_quest_id,
            status=SideQuestStatus.COMPLETED.value,
            progress=100
        )
        
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing side quest: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete side quest"
        )


@router.put("/user/side-quests/{side_quest_id}/skip", response_model=UserSideQuestResponse, tags=["Side Quests"])
async def skip_side_quest(
    side_quest_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    side_quest_generator: SideQuestGenerator = Depends(get_side_quest_generator)
):
    """
    Skip a side quest.
    """
    try:
        # Update the user's side quest status to SKIPPED
        updated = await side_quest_generator.update_user_side_quest_status(
            user_id=current_user.id,
            side_quest_id=side_quest_id,
            status=SideQuestStatus.SKIPPED.value
        )
        
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error skipping side quest: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to skip side quest"
        )