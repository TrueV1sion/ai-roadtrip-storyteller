from fastapi import APIRouter, Header, Depends, status, HTTPException
from typing import Optional
from sqlalchemy.orm import Session

from app.models.directions import (
    DirectionsRequest,
    DirectionsResponse,
    DeprecatedDirectionsRequest
)
from app.services.directions_service import directions_service
from app.core.logger import get_logger
from app.core.authorization import get_optional_user, get_current_active_user, UserRole
from app.database import get_db
from app.models import User

router = APIRouter()
logger = get_logger(__name__)


@router.get("/directions", response_model=DirectionsResponse)
async def get_directions(
    request: DirectionsRequest,
    x_client_id: Optional[str] = Header(None),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
) -> DirectionsResponse:
    """
    Get enhanced directions with features like traffic, waypoints,
    and place details.
    
    This endpoint supports both authenticated and unauthenticated users,
    with rate limits and feature restrictions for unauthenticated users.
    """
    # Check rate limits and feature restrictions based on user status
    if not current_user:
        # Unauthenticated user restrictions
        if request.include_traffic or request.include_places or request.alternatives:
            # These features are only available to authenticated users
            logger.warning(f"Unauthenticated request attempted to use premium features: {request}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Authentication required for advanced features. Please sign in."
            )
            
        # Check IP-based rate limiting would go here
        # For simplicity, we're not implementing this now
        
    elif current_user.role not in [UserRole.PREMIUM, UserRole.ADMIN]:
        # Standard user restrictions
        if request.alternatives:
            # Route alternatives are premium features
            logger.warning(f"Standard user attempted to use route alternatives: {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Route alternatives are a premium feature. Please upgrade your account."
            )
    
    # All checks passed, proceed with the request
    return await directions_service.get_directions(
        origin=request.origin,
        destination=request.destination,
        mode=request.mode.value,
        waypoints=request.waypoints,
        optimize_route=request.optimize_route,
        alternatives=request.alternatives,
        include_traffic=request.include_traffic,
        include_places=request.include_places,
        departure_time=request.departure_time,
        traffic_model=request.traffic_model.value,
        client_id=x_client_id
    )


@router.get(
    "/directions/v1",
    response_model=DirectionsResponse,
    deprecated=True
)
async def get_directions_deprecated(
    request: DeprecatedDirectionsRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
) -> DirectionsResponse:
    """
    [DEPRECATED] Legacy endpoint for backwards compatibility.
    Please use the new /directions endpoint with string location format.
    
    This endpoint will be removed in a future version.
    """
    # Log deprecated endpoint usage
    user_id = current_user.id if current_user else "unauthenticated"
    logger.info(
        f"Deprecated endpoint call by user {user_id}: ({request.origin_lat},{request.origin_lng}) to ({request.dest_lat},{request.dest_lng})"
    )
    
    # Apply basic rate limiting for unauthenticated users
    if not current_user:
        # Simple rate limiting could be implemented here
        # For now, we'll just let them through but with a warning in logs
        logger.warning("Unauthenticated user accessing deprecated endpoint")
    
    # Convert to new format and call service
    return await directions_service.get_directions(
        origin=f"{request.origin_lat},{request.origin_lng}",
        destination=f"{request.dest_lat},{request.dest_lng}",
        mode="driving"
    )