from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.security import validate_token, ACCESS_TOKEN_TYPE
from app.core.logger import get_logger
from app.db.base import get_db
from app.crud.crud_user import get_user, update_user_last_login
from app.models.user import User

logger = get_logger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


class AuthenticationError(HTTPException):
    """Custom authentication error."""
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class AuthorizationError(HTTPException):
    """Custom authorization error."""
    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


async def get_current_user_optional(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """
    Get the current user from token, returns None if no valid token.
    Used for optional authentication.
    """
    if not credentials:
        return None
        
    try:
        # Validate the access token
        payload = validate_token(credentials.credentials, ACCESS_TOKEN_TYPE)
        if not payload:
            return None
            
        # Reject partial tokens requiring 2FA
        if payload.get("partial") or payload.get("requires_2fa"):
            return None
            
        # Get user from database
        user_id = payload.get("sub")
        if not user_id:
            return None
            
        user = get_user(db, user_id)
        if not user or not user.is_active:
            return None
            
        # Update last login timestamp (optional, can be removed for performance)
        try:
            update_user_last_login(db, user_id)
        except Exception as e:
            logger.warning(f"Failed to update last login for user {user_id}: {e}")
            
        return user
        
    except Exception as e:
        logger.warning(f"Authentication failed: {e}")
        return None


async def get_current_user(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> User:
    """
    Get the current user from token, raises exception if invalid.
    Used for required authentication.
    """
    if not credentials:
        raise AuthenticationError("No authentication token provided")
        
    try:
        # Validate the access token
        payload = validate_token(credentials.credentials, ACCESS_TOKEN_TYPE)
        if not payload:
            raise AuthenticationError("Invalid or expired token")
            
        # Check if this is a partial token requiring 2FA
        if payload.get("partial") or payload.get("requires_2fa"):
            raise AuthenticationError("2FA verification required")
            
        # Get user from database
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Invalid token payload")
            
        user = get_user(db, user_id)
        if not user:
            raise AuthenticationError("User not found")
            
        if not user.is_active:
            raise AuthenticationError("User account is disabled")
            
        # Update last login timestamp (optional, can be removed for performance)
        try:
            update_user_last_login(db, user_id)
        except Exception as e:
            logger.warning(f"Failed to update last login for user {user_id}: {e}")
            
        return user
        
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise AuthenticationError("Authentication failed")


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get the current active user.
    """
    if not current_user.is_active:
        raise AuthenticationError("User account is disabled")
    return current_user


async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get the current user and verify admin permissions.
    """
    if not current_user.is_active:
        raise AuthenticationError("User account is disabled")
        
    if current_user.role not in ["admin", "super_admin"]:
        raise AuthorizationError("Admin access required")
        
    return current_user


async def get_current_premium_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get the current user and verify premium subscription.
    """
    if not current_user.is_active:
        raise AuthenticationError("User account is disabled")
        
    if not current_user.is_premium:
        raise AuthorizationError("Premium subscription required")
        
    return current_user


def require_permissions(*required_permissions: str):
    """
    Decorator factory for requiring specific permissions.
    
    Usage:
        @require_permissions("manage_themes", "moderate_content")
        async def some_endpoint(user: User = Depends(get_permission_user)):
            ...
    """
    def get_permission_user(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.is_active:
            raise AuthenticationError("User account is disabled")
            
        # Check if user has required permissions
        user_permissions = set()
        
        # Add role-based permissions
        if current_user.role == "admin":
            user_permissions.update([
                "manage_themes", "moderate_content", "view_analytics",
                "manage_users", "manage_reservations"
            ])
        elif current_user.role == "super_admin":
            user_permissions.add("*")  # All permissions
        elif current_user.role == "moderator":
            user_permissions.update(["moderate_content", "manage_themes"])
            
        # Add premium user permissions
        if current_user.is_premium:
            user_permissions.update([
                "advanced_personalization", "priority_support", 
                "export_data", "unlimited_stories"
            ])
            
        # Check if user has all required permissions
        if "*" not in user_permissions:
            missing_permissions = set(required_permissions) - user_permissions
            if missing_permissions:
                raise AuthorizationError(
                    f"Missing required permissions: {', '.join(missing_permissions)}"
                )
                
        return current_user
    
    return get_permission_user


def get_user_from_token_payload(db: Session, payload: Dict[str, Any]) -> Optional[User]:
    """
    Helper function to get user from token payload.
    """
    try:
        user_id = payload.get("sub")
        if not user_id:
            return None
            
        user = get_user(db, user_id)
        if not user or not user.is_active:
            return None
            
        return user
    except Exception as e:
        logger.error(f"Error getting user from token payload: {e}")
        return None


def verify_user_access(current_user: User, resource_user_id: str) -> bool:
    """
    Verify that the current user has access to a resource belonging to another user.
    Users can access their own resources, admins can access any resource.
    """
    if current_user.role in ["admin", "super_admin"]:
        return True
        
    return str(current_user.id) == str(resource_user_id)


def require_user_access(resource_user_id: str, current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to require that the current user has access to a resource.
    """
    if not verify_user_access(current_user, resource_user_id):
        raise AuthorizationError("Access denied to this resource")
        
    return current_user


# Convenience dependencies for common authentication scenarios
CurrentUser = Depends(get_current_user)
CurrentActiveUser = Depends(get_current_active_user)
CurrentAdminUser = Depends(get_current_admin_user)
CurrentPremiumUser = Depends(get_current_premium_user)
OptionalUser = Depends(get_current_user_optional)