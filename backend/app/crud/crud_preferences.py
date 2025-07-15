from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import json # Import json for potential deserialization if needed

from app import models, schemas

# Placeholder functions - Implement logic using SQLAlchemy Session

def get_preferences(db: Session, user_id: str) -> Optional[models.UserPreferences]:
    """Get preferences for a specific user."""
    return db.query(models.UserPreferences).filter(models.UserPreferences.user_id == user_id).first()

def get_preferences_dict(db: Session, user_id: str) -> Dict[str, Any]:
    """Get preferences for a specific user as a dictionary."""
    db_prefs = get_preferences(db, user_id=user_id)
    if db_prefs:
        # Convert SQLAlchemy model to dict. SQLAlchemy's JSON type usually handles
        # deserialization automatically, but manual handling is shown as a fallback.
        prefs_dict = {}
        for c in db_prefs.__table__.columns:
            value = getattr(db_prefs, c.name)
            # Example manual JSON deserialization if needed:
            # if c.name in ["interests", "preferred_music_genres"] and isinstance(value, str):
            #     try:
            #         prefs_dict[c.name] = json.loads(value)
            #     except json.JSONDecodeError:
            #         prefs_dict[c.name] = value # Keep original if not valid JSON
            # else:
            prefs_dict[c.name] = value
        return prefs_dict
    return {} # Return empty dict if no preferences found


def create_or_update_preferences(db: Session, user_id: str, preferences: schemas.UserPreferencesCreate) -> models.UserPreferences:
    """Create new preferences or update existing ones for a user."""
    db_prefs = get_preferences(db, user_id=user_id)

    # Convert Pydantic model to dict, excluding unset fields to only update provided values
    # For Pydantic v2: update_data = preferences.model_dump(exclude_unset=True)
    # For Pydantic v1: update_data = preferences.dict(exclude_unset=True)
    # Assuming Pydantic v2 based on recent library versions
    update_data = preferences.model_dump(exclude_unset=True)

    if db_prefs:
        # Update existing preferences
        for key, value in update_data.items():
            setattr(db_prefs, key, value)
        # Note: user_id should not be updated here
    else:
        # Create new preferences
        # Ensure user_id is included when creating
        db_prefs = models.UserPreferences(**update_data, user_id=user_id)
        db.add(db_prefs)

    db.commit()
    db.refresh(db_prefs)
    return db_prefs

# Add other necessary CRUD functions if needed