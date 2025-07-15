from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List, Optional, Callable, Any, Dict, Union

from app.database import get_db
from app.models import User, Story, Experience, Preferences
from app.core.security import get_token_subject, validate_token, ACCESS_TOKEN_TYPE
from app.core.logger import get_logger
from app.core.enums import UserRole, ResourceType, Action

logger = get_logger(__name__)

# OAuth2 Bearer token scheme
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/token",
    # Allow token to be passed in header, cookie, or query parameter
    auto_error=False
)




async def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get the current user if authenticated, or None if not.
    
    This dependency can be used for endpoints that support both
    authenticated and unauthenticated access.
    """
    if not token:
        return None
        
    payload = validate_token(token, ACCESS_TOKEN_TYPE)
    if not payload:
        return None
        
    user_id = payload.get("sub")
    if not user_id:
        return None
        
    user = db.query(User).filter(User.id == user_id).first()
    return user


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user or raise an exception.
    
    This is a required dependency for endpoints that require authentication.
    """
    if not token:
        logger.warning("Authentication attempt with missing token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    payload = validate_token(token, ACCESS_TOKEN_TYPE)
    if not payload:
        logger.warning("Authentication attempt with invalid token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user_id = payload.get("sub")
    if not user_id:
        logger.warning("Token missing subject claim")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"User not found for ID: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get the current authenticated user and verify they are active.
    """
    if not current_user.is_active:
        logger.warning(f"Inactive user attempted access: {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


def has_role(required_role: UserRole):
    """
    Dependency factory that checks if the current user has the required role.
    
    Usage:
        @router.get("/admin-only", dependencies=[Depends(has_role(UserRole.ADMIN))])
        def admin_endpoint():
            ...
    """
    async def _has_role(current_user: User = Depends(get_current_active_user)) -> bool:
        if not current_user.role:
            logger.warning(f"User {current_user.id} has no role assigned")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
            
        # Admin role has access to everything
        if current_user.role == UserRole.ADMIN:
            return True
            
        # Role hierarchy: ADMIN > PREMIUM > STANDARD > GUEST
        role_hierarchy = {
            UserRole.ADMIN: 3,
            UserRole.PREMIUM: 2,
            UserRole.STANDARD: 1,
            UserRole.GUEST: 0
        }
        
        user_role_level = role_hierarchy.get(current_user.role, 0)
        required_role_level = role_hierarchy.get(required_role, 0)
        
        if user_role_level < required_role_level:
            logger.warning(
                f"User {current_user.id} with role {current_user.role} "
                f"attempted to access resource requiring {required_role}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
            
        return True
        
    return _has_role


def is_owner_or_admin():
    """
    Checks if the current user is either an admin or the owner of the resource.
    
    Usage:
        @router.put("/stories/{story_id}", dependencies=[Depends(is_owner_or_admin())])
        def update_story(story_id: str):
            ...
    
    This dependency assumes there is a resource_id path parameter that corresponds
    to the ID of the resource being accessed.
    """
    async def _is_owner_or_admin(
        resource_id: str,
        resource_type: ResourceType,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> bool:
        # Admin always has access
        if current_user.role == UserRole.ADMIN:
            return True
            
        # Check ownership based on resource type
        if resource_type == ResourceType.STORY:
            story = db.query(Story).filter(Story.id == resource_id).first()
            if not story:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Story not found"
                )
            return story.user_id == current_user.id
            
        elif resource_type == ResourceType.EXPERIENCE:
            experience = db.query(Experience).filter(Experience.id == resource_id).first()
            if not experience:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Experience not found"
                )
            return experience.user_id == current_user.id
            
        elif resource_type == ResourceType.USER:
            return resource_id == current_user.id
            
        elif resource_type == ResourceType.PREFERENCES:
            preferences = db.query(Preferences).filter(Preferences.id == resource_id).first()
            if not preferences:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Preferences not found"
                )
            return preferences.user_id == current_user.id
            
        else:
            logger.warning(f"Unsupported resource type: {resource_type}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot verify ownership of this resource type"
            )
            
    return _is_owner_or_admin


class ResourcePermission:
    """
    A flexible permission checker for resources.
    
    This class can be used to:
    1. Check if a user can perform an action on a resource
    2. Apply filters to query objects based on user permissions
    3. Validate resource access before performing operations
    
    Usage:
        permission = ResourcePermission(
            resource_type=ResourceType.STORY,
            action=Action.UPDATE,
            owner_field="user_id"
        )
        
        @router.put("/stories/{story_id}", dependencies=[Depends(permission.check)])
        def update_story(story_id: str):
            ...
    """
    
    def __init__(
        self,
        resource_type: ResourceType,
        action: Action,
        owner_field: str = "user_id",
        role_requirements: Dict[UserRole, List[Action]] = None
    ):
        self.resource_type = resource_type
        self.action = action
        self.owner_field = owner_field
        
        # Default role requirements if none provided
        self.role_requirements = role_requirements or {
            UserRole.ADMIN: [Action.ANY],
            UserRole.PREMIUM: [Action.CREATE, Action.READ, Action.UPDATE, Action.DELETE, Action.LIST],
            UserRole.STANDARD: [Action.CREATE, Action.READ, Action.UPDATE, Action.DELETE, Action.LIST],
            UserRole.GUEST: [Action.READ, Action.LIST]
        }
        
    async def check(
        self,
        resource_id: Optional[str] = None,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> bool:
        """
        Check if the current user has permission to perform the action on the resource.
        """
        # Admin can do anything
        if current_user.role == UserRole.ADMIN:
            return True
            
        # Check role-based permissions
        user_role = current_user.role or UserRole.GUEST
        allowed_actions = self.role_requirements.get(user_role, [])
        
        if Action.ANY in allowed_actions or self.action in allowed_actions:
            # If it's a read operation or there's no specific resource, we're done
            if self.action == Action.READ or self.action == Action.LIST or not resource_id:
                return True
                
            # For write operations on a specific resource, check ownership
            resource_class = self._get_model_class()
            if not resource_class:
                logger.warning(f"No model class found for resource type: {self.resource_type}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot verify ownership of this resource type"
                )
                
            resource = db.query(resource_class).filter(getattr(resource_class, "id") == resource_id).first()
            if not resource:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{self.resource_type.capitalize()} not found"
                )
                
            # Check if user owns the resource
            if hasattr(resource, self.owner_field) and getattr(resource, self.owner_field) == current_user.id:
                return True
                
        # If we get here, permission is denied
        logger.warning(
            f"Permission denied: User {current_user.id} with role {user_role} "
            f"attempted {self.action} on {self.resource_type} {resource_id or 'collection'}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
        
    def filter_query(self, query, user: User):
        """
        Filter a query based on the user's permissions.
        
        This method modifies the query to only return resources
        the user has permission to access.
        """
        # Admin can see everything
        if user.role == UserRole.ADMIN:
            return query
            
        model_class = self._get_model_class()
        if not model_class:
            logger.warning(f"No model class found for resource type: {self.resource_type}")
            # Return empty query as a fallback
            return query.filter(False)
            
        # For list/read actions, users can see their own resources
        if self.action in [Action.READ, Action.LIST]:
            # Filter by ownership
            if hasattr(model_class, self.owner_field):
                query = query.filter(getattr(model_class, self.owner_field) == user.id)
                
        return query
        
    def _get_model_class(self):
        """Get the model class for the resource type."""
        if self.resource_type == ResourceType.USER:
            return User
        elif self.resource_type == ResourceType.STORY:
            return Story
        elif self.resource_type == ResourceType.EXPERIENCE:
            return Experience
        elif self.resource_type == ResourceType.PREFERENCES:
            return Preferences
        else:
            return None