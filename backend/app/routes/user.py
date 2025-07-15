from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.authorization import get_current_active_user, ResourcePermission, has_role
from app.core.enums import ResourceType, Action, UserRole
from app.database import get_db
from app.models import User
from app.schemas import UserUpdate, UserResponse


router = APIRouter()

# Create permission checkers
user_read_permission = ResourcePermission(ResourceType.USER, Action.READ)
user_update_permission = ResourcePermission(ResourceType.USER, Action.UPDATE)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    _: bool = Depends(user_read_permission.check)
):
    """Get user profile by ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user's profile."""
    # Save the original values
    original_data = {
        "role": current_user.role,
        "is_premium": current_user.is_premium
    }
    
    # Remove restricted fields for non-admin users
    if current_user.role != UserRole.ADMIN:
        user_data_dict = user_data.dict(exclude_unset=True)
        if "role" in user_data_dict:
            del user_data_dict["role"]
        if "is_premium" in user_data_dict and not current_user.is_premium:
            del user_data_dict["is_premium"]
    else:
        user_data_dict = user_data.dict(exclude_unset=True)
    
    # Update user fields
    for field, value in user_data_dict.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.get("/me/trips")
async def get_user_trips(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's trips."""
    return current_user.trips


@router.get("/me/stories")
async def get_user_stories(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's saved stories."""
    return current_user.stories


@router.get("/", response_model=list[UserResponse], dependencies=[Depends(has_role(UserRole.ADMIN))])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all users in the system.
    This endpoint is restricted to admin users only.
    """
    users = db.query(User).offset(skip).limit(limit).all()
    return users