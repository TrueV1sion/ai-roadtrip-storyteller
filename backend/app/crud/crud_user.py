from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from app import models, schemas
from app.core.security import get_password_hash, verify_password
from app.core.password_policy import get_password_policy
from app.core.logger import get_logger

logger = get_logger(__name__)


def get_user(db: Session, user_id: str) -> Optional[models.User]:
    """Get a single user by their ID."""
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """Get a single user by their email address."""
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    """Get a single user by their username."""
    return db.query(models.User).filter(models.User.username == username).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    """Get a list of users."""
    return db.query(models.User).offset(skip).limit(limit).all()


async def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    """Create a new user in the database with password policy validation."""
    try:
        # Validate password against policy
        password_policy = get_password_policy()
        strength = password_policy.validate_password(
            user.password,
            user_email=user.email,
            user_name=user.name
        )
        
        if not strength.meets_requirements:
            raise ValueError(f"Password does not meet requirements: {'; '.join(strength.feedback)}")
        
        # Check if password has been pwned
        is_pwned, pwned_count = await password_policy.check_pwned_password(user.password)
        if is_pwned and pwned_count > 100:  # Allow if rarely seen in breaches
            raise ValueError("This password has been exposed in data breaches. Please choose a different password.")
        
        hashed_password = get_password_hash(user.password)
        db_user = models.User(
            email=user.email,
            username=user.username if hasattr(user, 'username') else user.email.split('@')[0],
            name=user.name,
            hashed_password=hashed_password,
            is_active=True,
            password_changed_at=datetime.utcnow()
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Save initial password to history
        await password_policy.save_password_history(db, str(db_user.id), hashed_password)
        
        return db_user
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Error creating user: {e}")
        raise ValueError("User with this email already exists")


async def update_user(db: Session, user_id: str, user_update: schemas.UserUpdate) -> Optional[models.User]:
    """Update an existing user with password policy validation."""
    db_user = get_user(db, user_id)
    if not db_user:
        return None
        
    update_data = user_update.dict(exclude_unset=True)
    
    # Handle password update separately with policy validation
    if "password" in update_data:
        password_policy = get_password_policy()
        
        # Check if user can change password (minimum age)
        can_change, reason = await password_policy.can_change_password(db, user_id)
        if not can_change:
            raise ValueError(reason)
        
        # Validate new password
        strength = password_policy.validate_password(
            update_data["password"],
            user_email=db_user.email,
            user_name=db_user.name
        )
        
        if not strength.meets_requirements:
            raise ValueError(f"Password does not meet requirements: {'; '.join(strength.feedback)}")
        
        # Check password history
        in_history = await password_policy.check_password_history(db, user_id, update_data["password"])
        if in_history:
            raise ValueError(f"Password was used recently. Please choose a different password.")
        
        # Check if password has been pwned
        is_pwned, pwned_count = await password_policy.check_pwned_password(update_data["password"])
        if is_pwned and pwned_count > 100:
            raise ValueError("This password has been exposed in data breaches. Please choose a different password.")
        
        # Hash and update password
        hashed_password = get_password_hash(update_data.pop("password"))
        update_data["hashed_password"] = hashed_password
        update_data["password_changed_at"] = datetime.utcnow()
        
        # Save to password history
        await password_policy.save_password_history(db, user_id, hashed_password)
    
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: str) -> bool:
    """Delete a user by ID."""
    db_user = get_user(db, user_id)
    if db_user:
        db.delete(db_user)
        db.commit()
        return True
    return False


def activate_user(db: Session, user_id: str) -> Optional[models.User]:
    """Activate a user account."""
    db_user = get_user(db, user_id)
    if db_user:
        db_user.is_active = True
        db.commit()
        db.refresh(db_user)
    return db_user


def deactivate_user(db: Session, user_id: str) -> Optional[models.User]:
    """Deactivate a user account."""
    db_user = get_user(db, user_id)
    if db_user:
        db_user.is_active = False
        db.commit()
        db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, email: str, password: str) -> Optional[models.User]:
    """Authenticate a user by email and password."""
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def update_user_last_login(db: Session, user_id: str) -> Optional[models.User]:
    """Update the last login timestamp for a user."""
    db_user = get_user(db, user_id)
    if db_user:
        db_user.last_login = datetime.utcnow()
        db.commit()
        db.refresh(db_user)
    return db_user


def update_user_settings(
    db: Session, 
    user_id: str, 
    settings_type: str, 
    settings: Dict[str, Any]
) -> Optional[models.User]:
    """Update user settings (notification, privacy, or accessibility)."""
    db_user = get_user(db, user_id)
    if not db_user:
        return None
        
    if settings_type == "notification":
        db_user.notification_settings = settings
    elif settings_type == "privacy":
        db_user.privacy_settings = settings
    elif settings_type == "accessibility":
        db_user.accessibility_settings = settings
    else:
        raise ValueError(f"Invalid settings type: {settings_type}")
    
    db.commit()
    db.refresh(db_user)
    return db_user


def get_user_stats(db: Session, user_id: str) -> Optional[Dict[str, Any]]:
    """Get user statistics including story count, ratings, etc."""
    db_user = get_user(db, user_id)
    if not db_user:
        return None
        
    # Count user's stories
    story_count = db.query(models.Story).filter(models.Story.user_id == user_id).count()
    
    # Get average rating of user's stories
    from sqlalchemy import func
    avg_rating = db.query(func.avg(models.Story.rating)).filter(
        models.Story.user_id == user_id,
        models.Story.rating.isnot(None)
    ).scalar()
    
    # Count favorites
    favorite_count = db.query(models.Story).filter(
        models.Story.user_id == user_id,
        models.Story.is_favorite == True
    ).count()
    
    return {
        "story_count": story_count,
        "average_rating": float(avg_rating) if avg_rating else 0.0,
        "favorite_count": favorite_count,
        "member_since": db_user.created_at.isoformat() if db_user.created_at else None,
        "last_login": db_user.last_login.isoformat() if db_user.last_login else None
    }


def search_users(db: Session, query: str, limit: int = 10) -> List[models.User]:
    """Search users by email, username, or full name."""
    return db.query(models.User).filter(
        models.User.email.ilike(f"%{query}%") |
        models.User.username.ilike(f"%{query}%") |
        models.User.full_name.ilike(f"%{query}%")
    ).limit(limit).all()