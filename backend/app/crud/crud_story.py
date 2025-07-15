from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List, Dict, Any
import uuid

from app import models, schemas


def get_story(db: Session, story_id: str) -> Optional[models.Story]:
    """Get a single story by its ID."""
    return db.query(models.Story).filter(models.Story.id == story_id).first()


def get_stories_by_user(db: Session, user_id: str, skip: int = 0, limit: int = 100) -> List[models.Story]:
    """Get stories created by a specific user, ordered by creation date descending."""
    return db.query(models.Story)\
             .filter(models.Story.user_id == user_id)\
             .order_by(models.Story.created_at.desc())\
             .offset(skip)\
             .limit(limit)\
             .all()


def create_story(db: Session, story: schemas.StoryCreate) -> models.Story:
    """Create a new story in the database."""
    # Build dictionary of model attributes from schema
    story_data = story.dict(exclude_unset=True)
    
    # Create the story object
    db_story = models.Story(**story_data)
    
    db.add(db_story)
    db.commit()
    db.refresh(db_story)
    return db_story


def update_story_rating(
    db: Session, 
    story_id: str, 
    rating: int,
    feedback: Optional[str] = None
) -> Optional[models.Story]:
    """Update the rating and optional feedback of an existing story."""
    db_story = get_story(db, story_id=story_id)
    if db_story:
        # Basic validation
        if 1 <= rating <= 5:
            db_story.rating = rating
            
            # Update feedback if provided
            if feedback:
                db_story.feedback = feedback
                
            db.commit()
            db.refresh(db_story)
    return db_story


def update_story_metadata(
    db: Session, 
    story_id: str, 
    metadata: Dict[str, Any]
) -> Optional[models.Story]:
    """Update the metadata of an existing story."""
    db_story = get_story(db, story_id=story_id)
    if db_story:
        if db_story.story_metadata:
            # Merge with existing metadata
            current_metadata = db_story.story_metadata
            current_metadata.update(metadata)
            db_story.story_metadata = current_metadata
        else:
            # Set new metadata
            db_story.story_metadata = metadata
            
        db.commit()
        db.refresh(db_story)
    return db_story


def increment_story_play_count(db: Session, story_id: str) -> Optional[models.Story]:
    """Increment the play count of a story."""
    db_story = get_story(db, story_id=story_id)
    if db_story:
        db_story.play_count = (db_story.play_count or 0) + 1
        db.commit()
        db.refresh(db_story)
    return db_story


def update_story_completion_rate(
    db: Session, 
    story_id: str, 
    completion_rate: float
) -> Optional[models.Story]:
    """Update the completion rate of a story."""
    db_story = get_story(db, story_id=story_id)
    if db_story and 0 <= completion_rate <= 1:
        db_story.completion_rate = completion_rate
        db.commit()
        db.refresh(db_story)
    return db_story


def toggle_story_favorite(db: Session, story_id: str) -> Optional[models.Story]:
    """Toggle the favorite status of a story."""
    db_story = get_story(db, story_id=story_id)
    if db_story:
        db_story.is_favorite = not db_story.is_favorite
        db.commit()
        db.refresh(db_story)
    return db_story


def get_average_rating(db: Session, user_id: Optional[str] = None) -> float:
    """Get average rating of stories, optionally filtered by user."""
    query = db.query(func.avg(models.Story.rating).label('average'))
    
    if user_id:
        query = query.filter(models.Story.user_id == user_id)
        
    # Only include records with non-null ratings
    query = query.filter(models.Story.rating.isnot(None))
    
    result = query.first()
    return result.average if result and result.average is not None else 0.0


def delete_story(db: Session, story_id: str) -> bool:
    """Delete a story by ID."""
    db_story = get_story(db, story_id=story_id)
    if db_story:
        db.delete(db_story)
        db.commit()
        return True
    return False


def get_stories_by_location(
    db: Session, 
    latitude: float,
    longitude: float,
    radius: float = 0.1,  # Approx 11km at equator
    limit: int = 10
) -> List[models.Story]:
    """
    Get stories near a specific location.
    Simple implementation using rectangular boundary.
    """
    return db.query(models.Story)\
            .filter(
                models.Story.latitude.between(latitude - radius, latitude + radius),
                models.Story.longitude.between(longitude - radius, longitude + radius)
            )\
            .order_by(models.Story.created_at.desc())\
            .limit(limit)\
            .all()