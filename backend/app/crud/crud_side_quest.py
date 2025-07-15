from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, and_, or_
from typing import Optional, List, Dict, Any
from datetime import datetime, date

from app import models, schemas
from app.core.logger import get_logger

logger = get_logger(__name__)


def get_side_quest(db: Session, quest_id: str) -> Optional[models.SideQuest]:
    """Get a single side quest by its ID."""
    return db.query(models.SideQuest).filter(models.SideQuest.id == quest_id).first()


def get_side_quests(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    category: Optional[str] = None
) -> List[models.SideQuest]:
    """Get a list of side quests with optional filtering."""
    query = db.query(models.SideQuest)
    
    if status:
        query = query.filter(models.SideQuest.status == status)
    
    if user_id:
        query = query.filter(models.SideQuest.user_id == user_id)
    
    if category:
        query = query.filter(models.SideQuest.category == category)
    
    return query.order_by(models.SideQuest.created_at.desc()).offset(skip).limit(limit).all()


def get_side_quests_by_user(
    db: Session, 
    user_id: str, 
    skip: int = 0, 
    limit: int = 100,
    status: Optional[str] = None
) -> List[models.SideQuest]:
    """Get side quests for a specific user."""
    query = db.query(models.SideQuest).filter(models.SideQuest.user_id == user_id)
    
    if status:
        query = query.filter(models.SideQuest.status == status)
    
    return query.order_by(models.SideQuest.created_at.desc()).offset(skip).limit(limit).all()


def create_side_quest(db: Session, quest: schemas.SideQuestCreate) -> models.SideQuest:
    """Create a new side quest in the database."""
    try:
        quest_data = quest.dict(exclude_unset=True)
        db_quest = models.SideQuest(**quest_data)
        
        db.add(db_quest)
        db.commit()
        db.refresh(db_quest)
        return db_quest
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Error creating side quest: {e}")
        raise ValueError("Error creating side quest")


def update_side_quest(
    db: Session, 
    quest_id: str, 
    quest_update: schemas.SideQuestUpdate
) -> Optional[models.SideQuest]:
    """Update an existing side quest."""
    db_quest = get_side_quest(db, quest_id)
    if not db_quest:
        return None
        
    update_data = quest_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(db_quest, field, value)
    
    db.commit()
    db.refresh(db_quest)
    return db_quest


def delete_side_quest(db: Session, quest_id: str) -> bool:
    """Delete a side quest by ID."""
    db_quest = get_side_quest(db, quest_id)
    if db_quest:
        db.delete(db_quest)
        db.commit()
        return True
    return False


def update_side_quest_status(
    db: Session, 
    quest_id: str, 
    status: str
) -> Optional[models.SideQuest]:
    """Update the status of a side quest."""
    db_quest = get_side_quest(db, quest_id)
    if db_quest:
        old_status = db_quest.status
        db_quest.status = status
        
        # Update timestamps based on status
        if status == "in_progress" and old_status != "in_progress":
            db_quest.started_at = datetime.utcnow()
        elif status == "completed" and old_status != "completed":
            db_quest.completed_at = datetime.utcnow()
        elif status == "skipped" and old_status != "skipped":
            db_quest.skipped_at = datetime.utcnow()
            
        db.commit()
        db.refresh(db_quest)
    return db_quest


def get_side_quests_by_location(
    db: Session,
    latitude: float,
    longitude: float,
    radius: float = 0.1,  # Approx 11km at equator
    limit: int = 20,
    user_id: Optional[str] = None
) -> List[models.SideQuest]:
    """Get side quests near a specific location."""
    query = db.query(models.SideQuest)\
            .filter(
                models.SideQuest.latitude.between(latitude - radius, latitude + radius),
                models.SideQuest.longitude.between(longitude - radius, longitude + radius)
            )
    
    if user_id:
        query = query.filter(models.SideQuest.user_id == user_id)
    
    return query.order_by(models.SideQuest.created_at.desc()).limit(limit).all()


def get_available_side_quests(
    db: Session,
    user_id: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius: float = 0.5,
    limit: int = 10
) -> List[models.SideQuest]:
    """Get available side quests for a user (not started, completed, or skipped)."""
    query = db.query(models.SideQuest).filter(
        models.SideQuest.user_id == user_id,
        models.SideQuest.status == "available"
    )
    
    # If location provided, filter by proximity
    if latitude is not None and longitude is not None:
        query = query.filter(
            models.SideQuest.latitude.between(latitude - radius, latitude + radius),
            models.SideQuest.longitude.between(longitude - radius, longitude + radius)
        )
    
    return query.order_by(models.SideQuest.created_at.desc()).limit(limit).all()


def get_active_side_quests(db: Session, user_id: str) -> List[models.SideQuest]:
    """Get all active (in progress) side quests for a user."""
    return db.query(models.SideQuest)\
             .filter(
                 models.SideQuest.user_id == user_id,
                 models.SideQuest.status == "in_progress"
             )\
             .order_by(models.SideQuest.started_at.desc())\
             .all()


def get_completed_side_quests(
    db: Session, 
    user_id: str,
    skip: int = 0,
    limit: int = 50
) -> List[models.SideQuest]:
    """Get completed side quests for a user."""
    return db.query(models.SideQuest)\
             .filter(
                 models.SideQuest.user_id == user_id,
                 models.SideQuest.status == "completed"
             )\
             .order_by(models.SideQuest.completed_at.desc())\
             .offset(skip)\
             .limit(limit)\
             .all()


def get_side_quest_statistics(db: Session, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Get side quest statistics."""
    query = db.query(models.SideQuest)
    
    if user_id:
        query = query.filter(models.SideQuest.user_id == user_id)
    
    total_count = query.count()
    
    # Count by status
    status_counts = db.query(
        models.SideQuest.status,
        func.count(models.SideQuest.id).label('count')
    )
    
    if user_id:
        status_counts = status_counts.filter(models.SideQuest.user_id == user_id)
    
    status_counts = status_counts.group_by(models.SideQuest.status).all()
    
    # Count by category
    category_counts = db.query(
        models.SideQuest.category,
        func.count(models.SideQuest.id).label('count')
    )
    
    if user_id:
        category_counts = category_counts.filter(models.SideQuest.user_id == user_id)
    
    category_counts = category_counts.group_by(models.SideQuest.category).all()
    
    # Average completion time for completed quests
    completed_query = query.filter(
        models.SideQuest.status == "completed",
        models.SideQuest.started_at.isnot(None),
        models.SideQuest.completed_at.isnot(None)
    )
    
    avg_completion_time = None
    if completed_query.count() > 0:
        durations = []
        for quest in completed_query.all():
            if quest.started_at and quest.completed_at:
                duration = (quest.completed_at - quest.started_at).total_seconds()
                durations.append(duration)
        
        if durations:
            avg_completion_time = sum(durations) / len(durations)
    
    return {
        "total_quests": total_count,
        "status_breakdown": {status: count for status, count in status_counts},
        "category_breakdown": {category: count for category, count in category_counts},
        "average_completion_time_seconds": avg_completion_time
    }


def search_side_quests(
    db: Session,
    query: str,
    user_id: Optional[str] = None,
    limit: int = 20
) -> List[models.SideQuest]:
    """Search side quests by title or description."""
    search_query = db.query(models.SideQuest).filter(
        or_(
            models.SideQuest.title.ilike(f"%{query}%"),
            models.SideQuest.description.ilike(f"%{query}%")
        )
    )
    
    if user_id:
        search_query = search_query.filter(models.SideQuest.user_id == user_id)
    
    return search_query.order_by(models.SideQuest.created_at.desc()).limit(limit).all()


def get_side_quests_by_category(
    db: Session, 
    category: str,
    user_id: Optional[str] = None,
    limit: int = 20
) -> List[models.SideQuest]:
    """Get side quests by category."""
    query = db.query(models.SideQuest).filter(models.SideQuest.category == category)
    
    if user_id:
        query = query.filter(models.SideQuest.user_id == user_id)
    
    return query.order_by(models.SideQuest.created_at.desc()).limit(limit).all()


def get_side_quests_by_difficulty(
    db: Session,
    difficulty: str,
    user_id: Optional[str] = None,
    limit: int = 20
) -> List[models.SideQuest]:
    """Get side quests by difficulty level."""
    query = db.query(models.SideQuest).filter(models.SideQuest.difficulty == difficulty)
    
    if user_id:
        query = query.filter(models.SideQuest.user_id == user_id)
    
    return query.order_by(models.SideQuest.created_at.desc()).limit(limit).all()


def get_recommended_side_quests(
    db: Session,
    user_id: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius: float = 0.5,
    limit: int = 5
) -> List[models.SideQuest]:
    """Get recommended side quests for a user based on their history and location."""
    # Get user's completed quest categories to understand preferences
    completed_categories = db.query(models.SideQuest.category)\
                            .filter(
                                models.SideQuest.user_id == user_id,
                                models.SideQuest.status == "completed"
                            )\
                            .distinct()\
                            .all()
    
    category_list = [cat[0] for cat in completed_categories]
    
    # Build query for available quests
    query = db.query(models.SideQuest).filter(
        models.SideQuest.user_id == user_id,
        models.SideQuest.status == "available"
    )
    
    # If location provided, filter by proximity
    if latitude is not None and longitude is not None:
        query = query.filter(
            models.SideQuest.latitude.between(latitude - radius, latitude + radius),
            models.SideQuest.longitude.between(longitude - radius, longitude + radius)
        )
    
    # Prioritize quest categories user has completed before
    if category_list:
        preferred_quests = query.filter(models.SideQuest.category.in_(category_list)).limit(limit // 2).all()
        other_quests = query.filter(~models.SideQuest.category.in_(category_list)).limit(limit - len(preferred_quests)).all()
        return preferred_quests + other_quests
    else:
        return query.limit(limit).all()


def update_side_quest_progress(
    db: Session,
    quest_id: str,
    progress_percentage: float,
    notes: Optional[str] = None
) -> Optional[models.SideQuest]:
    """Update the progress of a side quest."""
    db_quest = get_side_quest(db, quest_id)
    if db_quest:
        db_quest.progress_percentage = max(0, min(100, progress_percentage))  # Clamp between 0-100
        
        if notes:
            if db_quest.metadata:
                db_quest.metadata["progress_notes"] = notes
            else:
                db_quest.metadata = {"progress_notes": notes}
        
        # If progress reaches 100%, mark as completed
        if progress_percentage >= 100 and db_quest.status != "completed":
            db_quest.status = "completed"
            db_quest.completed_at = datetime.utcnow()
        
        db.commit()
        db.refresh(db_quest)
    return db_quest


def get_side_quests_by_date_range(
    db: Session,
    user_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 50
) -> List[models.SideQuest]:
    """Get side quests within a date range."""
    query = db.query(models.SideQuest)
    
    if user_id:
        query = query.filter(models.SideQuest.user_id == user_id)
    
    if start_date:
        query = query.filter(func.date(models.SideQuest.created_at) >= start_date)
    
    if end_date:
        query = query.filter(func.date(models.SideQuest.created_at) <= end_date)
    
    return query.order_by(models.SideQuest.created_at.desc()).limit(limit).all()


def get_overdue_side_quests(db: Session, user_id: Optional[str] = None) -> List[models.SideQuest]:
    """Get side quests that are overdue (have deadline and are past it)."""
    query = db.query(models.SideQuest).filter(
        models.SideQuest.deadline.isnot(None),
        models.SideQuest.deadline < datetime.utcnow(),
        models.SideQuest.status.in_(["available", "in_progress"])
    )
    
    if user_id:
        query = query.filter(models.SideQuest.user_id == user_id)
    
    return query.order_by(models.SideQuest.deadline.asc()).all()