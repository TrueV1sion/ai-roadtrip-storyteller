from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, and_, or_
from typing import Optional, List, Dict, Any, Type
from datetime import datetime, date

from app import models, schemas
from app.core.logger import get_logger
from app.models.experience import UserSavedExperience
from app.schemas.experience import UserSavedExperienceCreate, UserSavedExperienceUpdate

logger = get_logger(__name__)


def get_experience(db: Session, experience_id: str) -> Optional[models.Experience]:
    """Get a single experience by its ID."""
    return db.query(models.Experience).filter(models.Experience.id == experience_id).first()


def get_experiences(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    status: Optional[str] = None,
    user_id: Optional[str] = None
) -> List[models.Experience]:
    """Get a list of experiences with optional filtering."""
    query = db.query(models.Experience)
    
    if status:
        query = query.filter(models.Experience.status == status)
    
    if user_id:
        query = query.filter(models.Experience.user_id == user_id)
    
    return query.order_by(models.Experience.created_at.desc()).offset(skip).limit(limit).all()


def get_experiences_by_user(
    db: Session, 
    user_id: str, 
    skip: int = 0, 
    limit: int = 100
) -> List[models.Experience]:
    """Get experiences for a specific user."""
    return db.query(models.Experience)\
             .filter(models.Experience.user_id == user_id)\
             .order_by(models.Experience.created_at.desc())\
             .offset(skip)\
             .limit(limit)\
             .all()


def create_experience(db: Session, experience: UserSavedExperienceCreate) -> models.Experience:
    """Create a new experience in the database."""
    try:
        experience_data = experience.dict(exclude_unset=True)
        db_experience = models.Experience(**experience_data)
        
        db.add(db_experience)
        db.commit()
        db.refresh(db_experience)
        return db_experience
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Error creating experience: {e}")
        raise ValueError("Error creating experience")


def update_experience(
    db: Session, 
    experience_id: str, 
    experience_update: UserSavedExperienceUpdate
) -> Optional[models.Experience]:
    """Update an existing experience."""
    db_experience = get_experience(db, experience_id)
    if not db_experience:
        return None
        
    update_data = experience_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(db_experience, field, value)
    
    db.commit()
    db.refresh(db_experience)
    return db_experience


def delete_experience(db: Session, experience_id: str) -> bool:
    """Delete an experience by ID."""
    db_experience = get_experience(db, experience_id)
    if db_experience:
        db.delete(db_experience)
        db.commit()
        return True
    return False


def update_experience_status(
    db: Session, 
    experience_id: str, 
    status: str
) -> Optional[models.Experience]:
    """Update the status of an experience."""
    db_experience = get_experience(db, experience_id)
    if db_experience:
        db_experience.status = status
        
        # Update timestamps based on status
        if status == "active":
            db_experience.started_at = datetime.utcnow()
        elif status == "completed":
            db_experience.completed_at = datetime.utcnow()
        elif status == "cancelled":
            db_experience.cancelled_at = datetime.utcnow()
            
        db.commit()
        db.refresh(db_experience)
    return db_experience


def get_experiences_by_location(
    db: Session,
    latitude: float,
    longitude: float,
    radius: float = 0.1,  # Approx 11km at equator
    limit: int = 20
) -> List[models.Experience]:
    """Get experiences near a specific location."""
    return db.query(models.Experience)\
            .filter(
                models.Experience.start_latitude.between(latitude - radius, latitude + radius),
                models.Experience.start_longitude.between(longitude - radius, longitude + radius)
            )\
            .order_by(models.Experience.created_at.desc())\
            .limit(limit)\
            .all()


def get_experiences_by_date_range(
    db: Session,
    user_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 50
) -> List[models.Experience]:
    """Get experiences within a date range."""
    query = db.query(models.Experience)
    
    if user_id:
        query = query.filter(models.Experience.user_id == user_id)
    
    if start_date:
        query = query.filter(func.date(models.Experience.created_at) >= start_date)
    
    if end_date:
        query = query.filter(func.date(models.Experience.created_at) <= end_date)
    
    return query.order_by(models.Experience.created_at.desc()).limit(limit).all()


def get_active_experiences(db: Session, user_id: Optional[str] = None) -> List[models.Experience]:
    """Get all active experiences, optionally for a specific user."""
    query = db.query(models.Experience).filter(models.Experience.status == "active")
    
    if user_id:
        query = query.filter(models.Experience.user_id == user_id)
    
    return query.order_by(models.Experience.started_at.desc()).all()


def get_experience_statistics(db: Session, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Get experience statistics."""
    query = db.query(models.Experience)
    
    if user_id:
        query = query.filter(models.Experience.user_id == user_id)
    
    total_count = query.count()
    
    # Count by status
    status_counts = db.query(
        models.Experience.status,
        func.count(models.Experience.id).label('count')
    )
    
    if user_id:
        status_counts = status_counts.filter(models.Experience.user_id == user_id)
    
    status_counts = status_counts.group_by(models.Experience.status).all()
    
    # Average duration for completed experiences
    completed_query = query.filter(
        models.Experience.status == "completed",
        models.Experience.started_at.isnot(None),
        models.Experience.completed_at.isnot(None)
    )
    
    avg_duration = None
    if completed_query.count() > 0:
        durations = []
        for exp in completed_query.all():
            if exp.started_at and exp.completed_at:
                duration = (exp.completed_at - exp.started_at).total_seconds()
                durations.append(duration)
        
        if durations:
            avg_duration = sum(durations) / len(durations)
    
    return {
        "total_experiences": total_count,
        "status_breakdown": {status: count for status, count in status_counts},
        "average_duration_seconds": avg_duration
    }


def search_experiences(
    db: Session,
    query: str,
    user_id: Optional[str] = None,
    limit: int = 20
) -> List[models.Experience]:
    """Search experiences by title, description, or location name."""
    search_query = db.query(models.Experience).filter(
        or_(
            models.Experience.title.ilike(f"%{query}%"),
            models.Experience.description.ilike(f"%{query}%"),
            models.Experience.start_location_name.ilike(f"%{query}%"),
            models.Experience.end_location_name.ilike(f"%{query}%")
        )
    )
    
    if user_id:
        search_query = search_query.filter(models.Experience.user_id == user_id)
    
    return search_query.order_by(models.Experience.created_at.desc()).limit(limit).all()


def get_popular_experiences(
    db: Session,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius: float = 0.5,
    limit: int = 10
) -> List[models.Experience]:
    """Get popular experiences, optionally filtered by location."""
    query = db.query(models.Experience).filter(
        models.Experience.status == "completed"
    )
    
    # If location provided, filter by location
    if latitude is not None and longitude is not None:
        query = query.filter(
            models.Experience.start_latitude.between(latitude - radius, latitude + radius),
            models.Experience.start_longitude.between(longitude - radius, longitude + radius)
        )
    
    # Order by some popularity metric (could be enhanced with ratings, views, etc.)
    return query.order_by(models.Experience.created_at.desc()).limit(limit).all()


def update_experience_metadata(
    db: Session,
    experience_id: str,
    metadata: Dict[str, Any]
) -> Optional[models.Experience]:
    """Update experience metadata."""
    db_experience = get_experience(db, experience_id)
    if db_experience:
        if db_experience.metadata:
            # Merge with existing metadata
            current_metadata = db_experience.metadata
            current_metadata.update(metadata)
            db_experience.metadata = current_metadata
        else:
            # Set new metadata
            db_experience.metadata = metadata
            
        db.commit()
        db.refresh(db_experience)
    return db_experience


def get_experiences_requiring_action(db: Session, user_id: Optional[str] = None) -> List[models.Experience]:
    """Get experiences that require user action (e.g., pending, needs_input)."""
    action_statuses = ["pending", "needs_input", "waiting_confirmation"]
    
    query = db.query(models.Experience).filter(
        models.Experience.status.in_(action_statuses)
    )
    
    if user_id:
        query = query.filter(models.Experience.user_id == user_id)
    
    return query.order_by(models.Experience.created_at.asc()).all()


# UserSavedExperience CRUD operations
class CRUDUserSavedExperience:
    def __init__(self, model: Type[UserSavedExperience]):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).

        **Parameters**

        * `model`: A SQLAlchemy model class
        """
        self.model = model

    def get_saved_experience(self, db: Session, experience_id: str) -> Optional[UserSavedExperience]:
        return db.query(self.model).filter(self.model.id == experience_id).first()

    def get_saved_experiences_by_user(
        self, db: Session, *, user_id: str, skip: int = 0, limit: int = 100
    ) -> List[UserSavedExperience]:
        return (
            db.query(self.model)
            .filter(self.model.user_id == user_id)
            .order_by(self.model.saved_at.desc()) # Show most recently saved first
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def count_saved_experiences_by_user(self, db: Session, *, user_id: str) -> int:
        return (
            db.query(self.model)
            .filter(self.model.user_id == user_id)
            .count()
        )

    def create_saved_experience(
        self, db: Session, *, obj_in: UserSavedExperienceCreate
    ) -> UserSavedExperience:
        # Extract playlist tracks as a list of dicts for JSON storage
        playlist_tracks_data = [track.dict() for track in obj_in.playlist.tracks]

        db_obj = self.model(
            user_id=obj_in.user_id,
            story_text=obj_in.story,
            playlist_name=obj_in.playlist.playlist_name,
            playlist_tracks=playlist_tracks_data,
            playlist_provider=obj_in.playlist.provider,
            tts_audio_identifier=obj_in.tts_audio_identifier, # Use the value from the Pydantic schema
            location_latitude=obj_in.location.latitude if obj_in.location else None,
            location_longitude=obj_in.location.longitude if obj_in.location else None,
            interests=obj_in.interests if obj_in.interests else None,
            context_time_of_day=obj_in.context.time_of_day if obj_in.context else None,
            context_weather=obj_in.context.weather if obj_in.context else None,
            context_mood=obj_in.context.mood if obj_in.context else None,
            # generated_at and saved_at have server defaults in the model,
            # but can be overridden if provided in obj_in (e.g., if preserving original generation time)
            generated_at=obj_in.generated_at if hasattr(obj_in, 'generated_at') and obj_in.generated_at else None,
            # saved_at is typically set at the moment of saving, so server_default is often best.
            # If obj_in explicitly provides saved_at, it could be used, but less common for create.
            # saved_at=obj_in.saved_at if hasattr(obj_in, 'saved_at') and obj_in.saved_at else None 
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # Placeholder for update if needed in the future
    # def update_saved_experience(
    #     self, db: Session, *, db_obj: UserSavedExperience, obj_in: UserSavedExperienceUpdate
    # ) -> UserSavedExperience:
    #     pass

    def remove_saved_experience(self, db: Session, *, experience_id: str, user_id: str) -> Optional[UserSavedExperience]: # Added user_id for ownership check
        obj = db.query(self.model).filter(self.model.id == experience_id, self.model.user_id == user_id).first()
        if obj:
            db.delete(obj)
            db.commit()
            return obj
        return None

# Create an instance of the CRUD class for UserSavedExperience
user_saved_experience_crud = CRUDUserSavedExperience(UserSavedExperience)