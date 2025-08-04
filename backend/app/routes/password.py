"""
API routes for password-related operations.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.core.auth import get_current_user
from app.core.auth_rate_limiter import get_auth_rate_limiter
from app.database import get_db
from app.models.user import User
from app.schemas.password import (
    PasswordChangeRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordStrengthRequest,
    PasswordStrengthResponse,
    PasswordPolicyResponse,
    PasswordExpiryInfo
)
from app.services.password_service import get_password_service
from app.crud.crud_user import authenticate_user, update_user
from app.schemas.user import UserUpdate

logger = get_logger(__name__)
router = APIRouter()


@router.post("/change", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change the current user's password."""
    try:
        # Verify current password
        if not authenticate_user(db, current_user.email, password_data.current_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password using CRUD with validation
        user_update = UserUpdate(password=password_data.new_password)
        updated_user = await update_user(db, str(current_user.id), user_update)
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update password"
            )
        
        logger.info(f"Password changed for user: {current_user.email}")
        
        return {"message": "Password successfully changed"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.post("/reset-request", status_code=status.HTTP_200_OK)
async def request_password_reset(
    reset_data: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Request a password reset email."""
    try:
        # Rate limit password reset requests
        rate_limiter = get_auth_rate_limiter()
        ip_address = request.client.host if request.client else "unknown"
        
        allowed, retry_after = await rate_limiter.check_rate_limit(
            "reset_password",
            ip_address
        )
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many password reset requests. Try again in {retry_after} seconds"
            )
        
        # Create reset token and send email
        password_service = get_password_service()
        token = await password_service.create_password_reset_token(db, reset_data.email)
        
        # Always return success to avoid email enumeration
        return {
            "message": "If an account exists with this email, you will receive password reset instructions"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        # Still return success to avoid enumeration
        return {
            "message": "If an account exists with this email, you will receive password reset instructions"
        }


@router.post("/reset-confirm", status_code=status.HTTP_200_OK)
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """Confirm password reset with token."""
    try:
        password_service = get_password_service()
        success, error_message = await password_service.reset_password(
            db,
            reset_data.token,
            reset_data.new_password
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message or "Password reset failed"
            )
        
        return {"message": "Password successfully reset"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset confirmation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )


@router.post("/check-strength", response_model=PasswordStrengthResponse)
async def check_password_strength(
    strength_data: PasswordStrengthRequest
):
    """Check password strength without saving."""
    try:
        password_service = get_password_service()
        strength_info = await password_service.check_password_strength(
            strength_data.password,
            strength_data.email,
            strength_data.name
        )
        
        return PasswordStrengthResponse(**strength_info)
        
    except Exception as e:
        logger.error(f"Password strength check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check password strength"
        )


@router.get("/policy", response_model=PasswordPolicyResponse)
async def get_password_policy():
    """Get password policy requirements."""
    try:
        password_service = get_password_service()
        policy_info = password_service.get_password_policy_info()
        
        return PasswordPolicyResponse(**policy_info)
        
    except Exception as e:
        logger.error(f"Get password policy error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get password policy"
        )


@router.get("/expiry", response_model=PasswordExpiryInfo)
async def check_password_expiry(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if current user's password has expired."""
    try:
        password_service = get_password_service()
        expiry_info = await password_service.check_password_expiry(
            db,
            str(current_user.id)
        )
        
        return PasswordExpiryInfo(**expiry_info)
        
    except Exception as e:
        logger.error(f"Password expiry check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check password expiry"
        )


@router.post("/generate-secure")
async def generate_secure_password(length: int = 16):
    """Generate a secure random password."""
    try:
        if length < 12 or length > 128:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password length must be between 12 and 128 characters"
            )
        
        password_service = get_password_service()
        secure_password = password_service.generate_secure_password(length)
        
        # Also return strength info
        strength_info = await password_service.check_password_strength(secure_password)
        
        return {
            "password": secure_password,
            "strength": strength_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Generate secure password error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate secure password"
        )