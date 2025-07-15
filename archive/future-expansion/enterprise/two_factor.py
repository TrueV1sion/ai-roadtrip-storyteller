"""
Two-Factor Authentication routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_active_user
from app.core.logger import get_logger
from app.db.base import get_db
from app.models.user import User
from app.schemas.two_factor import (
    TwoFactorEnableRequest,
    TwoFactorEnableResponse,
    TwoFactorVerifyRequest,
    TwoFactorVerifyResponse,
    TwoFactorDisableRequest,
    TwoFactorStatusResponse,
    TwoFactorBackupCodesRequest,
    TwoFactorBackupCodesResponse
)
from app.services.two_factor_service import two_factor_service

logger = get_logger(__name__)
router = APIRouter()


@router.get("/2fa/status", response_model=TwoFactorStatusResponse)
async def get_2fa_status(
    current_user: User = Depends(get_current_active_user)
):
    """Get current 2FA status for the authenticated user."""
    return two_factor_service.get_2fa_status(current_user)


@router.post("/2fa/enable", response_model=TwoFactorEnableResponse)
async def enable_2fa(
    request: TwoFactorEnableRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Enable 2FA for the authenticated user.
    
    Returns:
        - TOTP secret key
        - QR code for authenticator apps
        - Backup codes for recovery
    """
    try:
        secret, qr_code, backup_codes = await two_factor_service.enable_2fa(
            db=db,
            user=current_user,
            password=request.password
        )
        
        return TwoFactorEnableResponse(
            secret=secret,
            qr_code=qr_code,
            backup_codes=backup_codes
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to enable 2FA for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enable 2FA"
        )


@router.post("/2fa/verify", response_model=TwoFactorVerifyResponse)
async def verify_2fa(
    request: TwoFactorVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Verify a 2FA code (TOTP or backup code).
    
    This endpoint is used during login or sensitive operations.
    """
    try:
        is_valid, is_backup, remaining = await two_factor_service.verify_2fa_code(
            db=db,
            user=current_user,
            code=request.code
        )
        
        return TwoFactorVerifyResponse(
            verified=is_valid,
            backup_code_used=is_backup if is_valid else None,
            backup_codes_remaining=remaining if is_valid else None
        )
        
    except ValueError as e:
        # Rate limiting error
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to verify 2FA for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify 2FA code"
        )


@router.post("/2fa/disable", status_code=status.HTTP_204_NO_CONTENT)
async def disable_2fa(
    request: TwoFactorDisableRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Disable 2FA for the authenticated user.
    
    Requires both password and current TOTP code for security.
    """
    try:
        await two_factor_service.disable_2fa(
            db=db,
            user=current_user,
            password=request.password,
            code=request.code
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to disable 2FA for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable 2FA"
        )


@router.post("/2fa/backup-codes", response_model=TwoFactorBackupCodesResponse)
async def regenerate_backup_codes(
    request: TwoFactorBackupCodesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Regenerate backup codes for the authenticated user.
    
    Requires both password and current TOTP code for security.
    All existing backup codes will be invalidated.
    """
    try:
        backup_codes = await two_factor_service.regenerate_backup_codes(
            db=db,
            user=current_user,
            password=request.password,
            code=request.code
        )
        
        return TwoFactorBackupCodesResponse(backup_codes=backup_codes)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to regenerate backup codes for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to regenerate backup codes"
        )