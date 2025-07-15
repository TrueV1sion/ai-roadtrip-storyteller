"""
Password service for handling password reset, validation, and security operations.
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.core.cache import get_cache
from app.core.security import get_password_hash, create_token
from app.core.password_policy import get_password_policy
from app.core.config import settings
from app.models.user import User
from app.crud.crud_user import get_user_by_email, get_user
from app.services.email_service import send_password_reset_email

logger = get_logger(__name__)


class PasswordService:
    """Service for password-related operations."""
    
    def __init__(self):
        self.password_policy = get_password_policy()
        self.cache = None
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Lazy initialization of cache connection."""
        if not self._initialized:
            self.cache = await get_cache()
            self._initialized = True
    
    async def create_password_reset_token(
        self,
        db: Session,
        email: str
    ) -> Optional[str]:
        """
        Create a password reset token for the user.
        
        Args:
            db: Database session
            email: User's email address
            
        Returns:
            Reset token if successful, None otherwise
        """
        user = get_user_by_email(db, email)
        if not user:
            # Don't reveal if email exists
            logger.warning(f"Password reset requested for non-existent email: {email}")
            return None
        
        if not user.is_active:
            logger.warning(f"Password reset requested for inactive user: {email}")
            return None
        
        # Generate secure reset token
        reset_token = secrets.token_urlsafe(32)
        
        # Store token in cache with expiration
        await self._ensure_initialized()
        cache_key = f"password_reset:{reset_token}"
        cache_data = {
            "user_id": str(user.id),
            "email": user.email,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Token expires in 1 hour
        await self.cache.setex(cache_key, 3600, cache_data)
        
        # Send reset email
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        await send_password_reset_email(user.email, user.name, reset_url)
        
        logger.info(f"Password reset token created for user: {user.email}")
        return reset_token
    
    async def validate_reset_token(
        self,
        db: Session,
        token: str
    ) -> Optional[User]:
        """
        Validate a password reset token.
        
        Args:
            db: Database session
            token: Reset token
            
        Returns:
            User if token is valid, None otherwise
        """
        await self._ensure_initialized()
        cache_key = f"password_reset:{token}"
        
        # Get token data from cache
        token_data = await self.cache.get(cache_key)
        if not token_data:
            logger.warning(f"Invalid or expired reset token")
            return None
        
        # Get user
        user = get_user(db, token_data["user_id"])
        if not user or not user.is_active:
            logger.warning(f"User not found or inactive for reset token")
            return None
        
        return user
    
    async def reset_password(
        self,
        db: Session,
        token: str,
        new_password: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Reset user's password using a valid token.
        
        Args:
            db: Database session
            token: Reset token
            new_password: New password
            
        Returns:
            Tuple of (success, error_message)
        """
        # Validate token
        user = await self.validate_reset_token(db, token)
        if not user:
            return False, "Invalid or expired reset token"
        
        # Validate new password
        strength = self.password_policy.validate_password(
            new_password,
            user_email=user.email,
            user_name=user.name
        )
        
        if not strength.meets_requirements:
            return False, f"Password does not meet requirements: {'; '.join(strength.feedback)}"
        
        # Check password history
        in_history = await self.password_policy.check_password_history(
            db, str(user.id), new_password
        )
        if in_history:
            return False, "Password was used recently. Please choose a different password."
        
        # Check if password has been pwned
        is_pwned, pwned_count = await self.password_policy.check_pwned_password(new_password)
        if is_pwned and pwned_count > 100:
            return False, "This password has been exposed in data breaches. Please choose a different password."
        
        # Update password
        hashed_password = get_password_hash(new_password)
        user.hashed_password = hashed_password
        user.password_changed_at = datetime.utcnow()
        
        # Save to password history
        await self.password_policy.save_password_history(
            db, str(user.id), hashed_password
        )
        
        # Invalidate the reset token
        await self._ensure_initialized()
        cache_key = f"password_reset:{token}"
        await self.cache.delete(cache_key)
        
        # Clear any failed login attempts
        await self.password_policy.clear_failed_attempts(user.email)
        
        db.commit()
        logger.info(f"Password reset successful for user: {user.email}")
        
        return True, None
    
    async def check_password_strength(
        self,
        password: str,
        email: Optional[str] = None,
        name: Optional[str] = None
    ) -> dict:
        """
        Check password strength and return detailed information.
        
        Args:
            password: Password to check
            email: User email for context
            name: User name for context
            
        Returns:
            Dictionary with strength information
        """
        strength = self.password_policy.validate_password(password, email, name)
        
        # Check if pwned
        is_pwned, pwned_count = await self.password_policy.check_pwned_password(password)
        
        return {
            "score": strength.score,
            "level": strength.level,
            "feedback": strength.feedback,
            "meets_requirements": strength.meets_requirements,
            "details": strength.details,
            "is_pwned": is_pwned,
            "pwned_count": pwned_count
        }
    
    def get_password_policy_info(self) -> dict:
        """Get password policy configuration for client display."""
        config = self.password_policy.config
        return {
            "min_length": config.min_length,
            "max_length": config.max_length,
            "require_uppercase": config.require_uppercase,
            "require_lowercase": config.require_lowercase,
            "require_numbers": config.require_numbers,
            "require_special": config.require_special,
            "special_chars": config.special_chars,
            "password_expiry_days": config.max_password_age_days
        }
    
    async def check_password_expiry(
        self,
        db: Session,
        user_id: str
    ) -> dict:
        """
        Check if user's password has expired.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Dictionary with expiry information
        """
        is_expired, expiry_date = await self.password_policy.check_password_age(db, user_id)
        
        user = get_user(db, user_id)
        days_until_expiry = None
        
        if expiry_date and not is_expired:
            days_until_expiry = (expiry_date - datetime.utcnow()).days
        
        return {
            "is_expired": is_expired,
            "expiry_date": expiry_date.isoformat() if expiry_date else None,
            "days_until_expiry": days_until_expiry,
            "last_changed": user.password_changed_at.isoformat() if user and user.password_changed_at else None
        }
    
    def generate_secure_password(self, length: int = 16) -> str:
        """Generate a secure random password."""
        return self.password_policy.generate_secure_password(length)


# Global instance
_password_service = None


def get_password_service() -> PasswordService:
    """Get the global PasswordService instance."""
    global _password_service
    if _password_service is None:
        _password_service = PasswordService()
    return _password_service