from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, and_, or_
from typing import Optional, List, Dict, Any
from datetime import datetime

from app import models, schemas
from app.core.logger import get_logger

logger = get_logger(__name__)


def get_theme(db: Session, theme_id: str) -> Optional[models.Theme]:
    """Get a single theme by its ID."""
    return db.query(models.Theme).filter(models.Theme.id == theme_id).first()


def get_theme_by_name(db: Session, name: str) -> Optional[models.Theme]:
    """Get a theme by its name."""
    return db.query(models.Theme).filter(models.Theme.name == name).first()


def get_themes(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    is_active: Optional[bool] = None,
    category: Optional[str] = None
) -> List[models.Theme]:
    """Get a list of themes with optional filtering."""
    query = db.query(models.Theme)
    
    if is_active is not None:
        query = query.filter(models.Theme.is_active == is_active)
    
    if category:
        query = query.filter(models.Theme.category == category)
    
    return query.order_by(models.Theme.name).offset(skip).limit(limit).all()


def create_theme(db: Session, theme: schemas.ThemeCreate) -> models.Theme:
    """Create a new theme in the database."""
    try:
        theme_data = theme.dict(exclude_unset=True)
        db_theme = models.Theme(**theme_data)
        
        db.add(db_theme)
        db.commit()
        db.refresh(db_theme)
        return db_theme
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Error creating theme: {e}")
        raise ValueError("Theme with this name already exists")


def update_theme(
    db: Session, 
    theme_id: str, 
    theme_update: schemas.ThemeUpdate
) -> Optional[models.Theme]:
    """Update an existing theme."""
    db_theme = get_theme(db, theme_id)
    if not db_theme:
        return None
        
    update_data = theme_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(db_theme, field, value)
    
    db.commit()
    db.refresh(db_theme)
    return db_theme


def delete_theme(db: Session, theme_id: str) -> bool:
    """Delete a theme by ID."""
    db_theme = get_theme(db, theme_id)
    if db_theme:
        db.delete(db_theme)
        db.commit()
        return True
    return False


def activate_theme(db: Session, theme_id: str) -> Optional[models.Theme]:
    """Activate a theme."""
    db_theme = get_theme(db, theme_id)
    if db_theme:
        db_theme.is_active = True
        db.commit()
        db.refresh(db_theme)
    return db_theme


def deactivate_theme(db: Session, theme_id: str) -> Optional[models.Theme]:
    """Deactivate a theme."""
    db_theme = get_theme(db, theme_id)
    if db_theme:
        db_theme.is_active = False
        db.commit()
        db.refresh(db_theme)
    return db_theme


def get_themes_by_category(db: Session, category: str) -> List[models.Theme]:
    """Get all themes in a specific category."""
    return db.query(models.Theme)\
             .filter(models.Theme.category == category, models.Theme.is_active == True)\
             .order_by(models.Theme.name)\
             .all()


def get_active_themes(db: Session) -> List[models.Theme]:
    """Get all active themes."""
    return db.query(models.Theme)\
             .filter(models.Theme.is_active == True)\
             .order_by(models.Theme.name)\
             .all()


def search_themes(db: Session, query: str, limit: int = 20) -> List[models.Theme]:
    """Search themes by name or description."""
    return db.query(models.Theme).filter(
        or_(
            models.Theme.name.ilike(f"%{query}%"),
            models.Theme.description.ilike(f"%{query}%")
        ),
        models.Theme.is_active == True
    ).order_by(models.Theme.name).limit(limit).all()


def get_theme_statistics(db: Session) -> Dict[str, Any]:
    """Get theme usage statistics."""
    # Count total themes
    total_themes = db.query(models.Theme).count()
    active_themes = db.query(models.Theme).filter(models.Theme.is_active == True).count()
    
    # Count by category
    category_counts = db.query(
        models.Theme.category,
        func.count(models.Theme.id).label('count')
    ).filter(models.Theme.is_active == True).group_by(models.Theme.category).all()
    
    # Count stories using themes
    themes_with_stories = db.query(models.Theme.id).join(models.Story).distinct().count()
    
    return {
        "total_themes": total_themes,
        "active_themes": active_themes,
        "inactive_themes": total_themes - active_themes,
        "category_breakdown": {category: count for category, count in category_counts},
        "themes_with_stories": themes_with_stories,
        "themes_without_stories": active_themes - themes_with_stories
    }


def get_popular_themes(db: Session, limit: int = 10) -> List[Dict[str, Any]]:
    """Get most popular themes based on story usage."""
    theme_usage = db.query(
        models.Theme,
        func.count(models.Story.id).label('story_count')
    ).outerjoin(models.Story)\
     .filter(models.Theme.is_active == True)\
     .group_by(models.Theme.id)\
     .order_by(func.count(models.Story.id).desc())\
     .limit(limit)\
     .all()
    
    return [
        {
            "theme": theme,
            "story_count": story_count
        }
        for theme, story_count in theme_usage
    ]


# UserThemePreference CRUD operations
def get_user_theme_preferences(db: Session, user_id: str) -> List[models.UserThemePreference]:
    """Get all theme preferences for a user."""
    return db.query(models.UserThemePreference)\
             .filter(models.UserThemePreference.user_id == user_id)\
             .order_by(models.UserThemePreference.preference_strength.desc())\
             .all()


def get_user_theme_preference(
    db: Session, 
    user_id: str, 
    theme_id: str
) -> Optional[models.UserThemePreference]:
    """Get a specific user's preference for a theme."""
    return db.query(models.UserThemePreference)\
             .filter(
                 models.UserThemePreference.user_id == user_id,
                 models.UserThemePreference.theme_id == theme_id
             ).first()


def create_user_theme_preference(
    db: Session, 
    preference: schemas.UserThemePreferenceCreate
) -> models.UserThemePreference:
    """Create a new user theme preference."""
    try:
        # Check if preference already exists
        existing = get_user_theme_preference(db, preference.user_id, preference.theme_id)
        if existing:
            # Update existing preference
            existing.preference_strength = preference.preference_strength
            existing.notes = preference.notes
            db.commit()
            db.refresh(existing)
            return existing
        
        # Create new preference
        preference_data = preference.dict(exclude_unset=True)
        db_preference = models.UserThemePreference(**preference_data)
        
        db.add(db_preference)
        db.commit()
        db.refresh(db_preference)
        return db_preference
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Error creating user theme preference: {e}")
        raise ValueError("Error creating theme preference")


def update_user_theme_preference(
    db: Session,
    user_id: str,
    theme_id: str,
    preference_strength: float,
    notes: Optional[str] = None
) -> Optional[models.UserThemePreference]:
    """Update a user's theme preference."""
    db_preference = get_user_theme_preference(db, user_id, theme_id)
    if db_preference:
        db_preference.preference_strength = preference_strength
        if notes is not None:
            db_preference.notes = notes
        db.commit()
        db.refresh(db_preference)
    return db_preference


def delete_user_theme_preference(db: Session, user_id: str, theme_id: str) -> bool:
    """Delete a user's theme preference."""
    db_preference = get_user_theme_preference(db, user_id, theme_id)
    if db_preference:
        db.delete(db_preference)
        db.commit()
        return True
    return False


def get_recommended_themes_for_user(
    db: Session, 
    user_id: str, 
    limit: int = 5
) -> List[models.Theme]:
    """Get recommended themes for a user based on their preferences and usage patterns."""
    # Get user's current preferences
    user_preferences = get_user_theme_preferences(db, user_id)
    preferred_theme_ids = [pref.theme_id for pref in user_preferences if pref.preference_strength > 0.5]
    
    # Get themes in same categories as user's preferred themes
    if preferred_theme_ids:
        preferred_categories = db.query(models.Theme.category)\
                               .filter(models.Theme.id.in_(preferred_theme_ids))\
                               .distinct()\
                               .all()
        
        category_list = [cat[0] for cat in preferred_categories]
        
        # Find themes in those categories that user hasn't tried
        recommended = db.query(models.Theme)\
                       .filter(
                           models.Theme.category.in_(category_list),
                           models.Theme.is_active == True,
                           ~models.Theme.id.in_(preferred_theme_ids)
                       )\
                       .order_by(func.random())\
                       .limit(limit)\
                       .all()
    else:
        # If no preferences, recommend popular themes
        popular_themes = get_popular_themes(db, limit=limit)
        recommended = [result["theme"] for result in popular_themes]
    
    return recommended


def get_user_theme_statistics(db: Session, user_id: str) -> Dict[str, Any]:
    """Get theme usage statistics for a specific user."""
    # Count user's theme preferences
    total_preferences = db.query(models.UserThemePreference)\
                         .filter(models.UserThemePreference.user_id == user_id)\
                         .count()
    
    # Count stories by theme for this user
    theme_usage = db.query(
        models.Theme.name,
        func.count(models.Story.id).label('story_count')
    ).join(models.Story)\
     .filter(models.Story.user_id == user_id)\
     .group_by(models.Theme.id, models.Theme.name)\
     .order_by(func.count(models.Story.id).desc())\
     .all()
    
    # Calculate average preference strength
    avg_preference = db.query(func.avg(models.UserThemePreference.preference_strength))\
                      .filter(models.UserThemePreference.user_id == user_id)\
                      .scalar()
    
    return {
        "total_theme_preferences": total_preferences,
        "theme_usage": {name: count for name, count in theme_usage},
        "average_preference_strength": float(avg_preference) if avg_preference else 0.0,
        "most_used_theme": theme_usage[0][0] if theme_usage else None
    }