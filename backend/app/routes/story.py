from typing import Dict, List, Optional
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from pydantic import BaseModel
from app.core.ai_client import ai_client
from app.core.logger import get_logger
from app.core.authorization import get_current_active_user, ResourcePermission
from app.core.enums import ResourceType, Action, UserRole
from app.database import get_db
from app.models import User, Story


logger = get_logger(__name__)
router = APIRouter()

# Create permission checker for stories
story_permission = ResourcePermission(ResourceType.STORY, Action.CREATE)


class LocationRequest(BaseModel):
    latitude: float
    longitude: float
    interests: List[str]
    context: Optional[Dict] = None


@router.post("/generate")
async def generate_story(
    request: LocationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    _: bool = Depends(story_permission.check)
):
    """Generate a location-based story based on coordinates and interests."""
    try:
        # Check if user has reached their story generation limit (for non-premium users)
        if current_user.role not in [UserRole.PREMIUM, UserRole.ADMIN]:
            # Count stories generated in the last 24 hours
            recent_stories_count = db.query(Story).filter(
                Story.user_id == current_user.id,
                Story.created_at >= func.now() - timedelta(days=1)
            ).count()
            
            if recent_stories_count >= 10:  # Limit for standard users
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Story generation limit reached. Upgrade to premium for unlimited stories."
                )
        
        story_text = await ai_client.generate_location_story(
            location={"latitude": request.latitude, "longitude": request.longitude},
            interests=request.interests,
            context=request.context
        )
        
        # Save the story in the database
        new_story = Story(
            user_id=current_user.id,
            content=story_text,
            location_latitude=request.latitude,
            location_longitude=request.longitude,
            metadata={"interests": request.interests, "context": request.context}
        )
        
        db.add(new_story)
        db.commit()
        db.refresh(new_story)
        
        return {
            "status": "success",
            "story": story_text,
            "story_id": new_story.id,
            "location": {
                "latitude": request.latitude,
                "longitude": request.longitude
            }
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error generating story: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate story"
        )