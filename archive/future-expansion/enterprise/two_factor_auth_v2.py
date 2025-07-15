"""
Two-Factor Authentication (2FA) endpoints using TOTP.
Provides setup, verification, and management of 2FA.
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pyotp
import qrcode
import io
import base64
import secrets
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import bcrypt

from app.db.base import get_db
from app.models.user import User
from app.core.auth import get_current_user
from app.core.logger import get_logger
from app.schemas.auth import (
    TwoFactorSetupResponse,
    TwoFactorEnableRequest,
    TwoFactorVerifyRequest,
    TwoFactorDisableRequest,
    BackupCodesResponse
)
from app.core.config import settings
from app.core.rate_limiter import RateLimiter
from app.core.security import verify_password

logger = get_logger(__name__)
router = APIRouter(prefix="/api/auth/2fa", tags=["2fa"])

# Rate limiters for 2FA operations
setup_limiter = RateLimiter(max_requests=5, window_seconds=3600)  # 5 setup attempts per hour
verify_limiter = RateLimiter(max_requests=10, window_seconds=300)  # 10 verify attempts per 5 minutes
disable_limiter = RateLimiter(max_requests=3, window_seconds=3600)  # 3 disable attempts per hour


def generate_secret() -> str:
    """Generate a secure TOTP secret."""
    return pyotp.random_base32()


def generate_qr_code(provisioning_uri: str) -> str:
    """Generate QR code as base64 encoded image."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return base64.b64encode(buffer.getvalue()).decode()


def generate_backup_codes(count: int = 10) -> List[str]:
    """Generate secure backup codes."""
    codes = []
    for _ in range(count):
        # Generate 8-character alphanumeric code
        code = ''.join(secrets.choice('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(8))
        # Format as XXXX-XXXX
        formatted_code = f"{code[:4]}-{code[4:]}"
        codes.append(formatted_code)
    return codes


def hash_backup_code(code: str) -> str:
    """Hash backup code for secure storage."""
    # Remove formatting
    clean_code = code.replace("-", "")
    return bcrypt.hashpw(clean_code.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_backup_code(code: str, hashed_codes: List[str]) -> Optional[str]:
    """Verify backup code against hashed codes. Returns the matched hash if valid."""
    clean_code = code.replace("-", "")
    
    for hashed_code in hashed_codes:
        if bcrypt.checkpw(clean_code.encode('utf-8'), hashed_code.encode('utf-8')):
            return hashed_code
    return None


@router.post("/setup", response_model=TwoFactorSetupResponse)
async def setup_two_factor(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initialize 2FA setup for the current user.
    Returns a QR code and backup codes.
    """
    # Rate limiting
    if not setup_limiter.check_rate_limit(f"2fa_setup:{current_user.id}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many 2FA setup attempts. Please try again later."
        )
    
    # Check if 2FA is already enabled
    if current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is already enabled"
        )
    
    try:
        # Generate new secret
        secret = generate_secret()
        
        # Generate provisioning URI
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=current_user.email,
            issuer_name=settings.APP_TITLE
        )
        
        # Generate QR code
        qr_code = generate_qr_code(provisioning_uri)
        
        # Generate backup codes
        backup_codes = generate_backup_codes()
        hashed_backup_codes = [hash_backup_code(code) for code in backup_codes]
        
        # Store secret and backup codes (temporarily, not enabled yet)
        current_user.two_factor_secret = secret
        current_user.two_factor_backup_codes = hashed_backup_codes
        db.commit()
        
        logger.info(f"2FA setup initiated for user {current_user.id}")
        
        return TwoFactorSetupResponse(
            qr_code=f"data:image/png;base64,{qr_code}",
            secret=secret,
            backup_codes=backup_codes,
            setup_complete=False
        )
        
    except Exception as e:
        logger.error(f"Failed to setup 2FA for user {current_user.id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to setup two-factor authentication"
        )


@router.post("/enable")
async def enable_two_factor(
    request: Request,
    enable_request: TwoFactorEnableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Enable 2FA after verifying the TOTP code.
    """
    # Rate limiting
    if not verify_limiter.check_rate_limit(f"2fa_enable:{current_user.id}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many verification attempts. Please try again later."
        )
    
    # Check if 2FA is already enabled
    if current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is already enabled"
        )
    
    # Check if secret exists
    if not current_user.two_factor_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication setup not initiated"
        )
    
    # Verify the TOTP code
    totp = pyotp.TOTP(current_user.two_factor_secret)
    if not totp.verify(enable_request.code, valid_window=1):
        logger.warning(f"Invalid 2FA code during enable for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    try:
        # Enable 2FA
        current_user.two_factor_enabled = True
        current_user.two_factor_enabled_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"2FA enabled for user {current_user.id}")
        
        return {
            "message": "Two-factor authentication enabled successfully",
            "enabled": True,
            "enabled_at": current_user.two_factor_enabled_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to enable 2FA for user {current_user.id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enable two-factor authentication"
        )


@router.post("/verify")
async def verify_two_factor(
    request: Request,
    verify_request: TwoFactorVerifyRequest,
    db: Session = Depends(get_db)
):
    """
    Verify 2FA code during login.
    This endpoint is called after successful password authentication.
    """
    # Rate limiting by session ID (from login flow)
    session_id = verify_request.session_id
    if not verify_limiter.check_rate_limit(f"2fa_verify:{session_id}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many verification attempts. Please try again later."
        )
    
    # Get user from session (established during login)
    # In production, this would use a secure session store
    user = db.query(User).filter(User.id == verify_request.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid session"
        )
    
    # Check if 2FA is enabled
    if not user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled"
        )
    
    verified = False
    
    # Try TOTP code first
    if verify_request.code and len(verify_request.code) == 6:
        totp = pyotp.TOTP(user.two_factor_secret)
        verified = totp.verify(verify_request.code, valid_window=1)
        
        if verified:
            user.two_factor_last_used = datetime.utcnow()
    
    # Try backup code if TOTP failed
    if not verified and verify_request.backup_code:
        matched_hash = verify_backup_code(
            verify_request.backup_code,
            user.two_factor_backup_codes or []
        )
        
        if matched_hash:
            # Remove used backup code
            user.two_factor_backup_codes = [
                code for code in user.two_factor_backup_codes
                if code != matched_hash
            ]
            user.two_factor_last_used = datetime.utcnow()
            verified = True
            
            logger.info(f"Backup code used for user {user.id}")
    
    if not verified:
        logger.warning(f"Invalid 2FA code for user {user.id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    try:
        db.commit()
        
        # Return success (actual token generation happens in login flow)
        return {
            "verified": True,
            "backup_codes_remaining": len(user.two_factor_backup_codes or [])
        }
        
    except Exception as e:
        logger.error(f"Failed to verify 2FA for user {user.id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify two-factor authentication"
        )


@router.post("/disable")
async def disable_two_factor(
    request: Request,
    disable_request: TwoFactorDisableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disable 2FA after password verification.
    """
    # Rate limiting
    if not disable_limiter.check_rate_limit(f"2fa_disable:{current_user.id}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many disable attempts. Please try again later."
        )
    
    # Check if 2FA is enabled
    if not current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled"
        )
    
    # Verify password
    if not verify_password(disable_request.password, current_user.hashed_password):
        logger.warning(f"Invalid password during 2FA disable for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    
    try:
        # Disable 2FA
        current_user.two_factor_enabled = False
        current_user.two_factor_secret = None
        current_user.two_factor_backup_codes = []
        current_user.two_factor_enabled_at = None
        db.commit()
        
        logger.info(f"2FA disabled for user {current_user.id}")
        
        return {
            "message": "Two-factor authentication disabled successfully",
            "enabled": False
        }
        
    except Exception as e:
        logger.error(f"Failed to disable 2FA for user {current_user.id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable two-factor authentication"
        )


@router.post("/backup-codes/regenerate", response_model=BackupCodesResponse)
async def regenerate_backup_codes(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Regenerate backup codes for the current user.
    """
    # Check if 2FA is enabled
    if not current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled"
        )
    
    try:
        # Generate new backup codes
        backup_codes = generate_backup_codes()
        hashed_backup_codes = [hash_backup_code(code) for code in backup_codes]
        
        # Update user
        current_user.two_factor_backup_codes = hashed_backup_codes
        db.commit()
        
        logger.info(f"Backup codes regenerated for user {current_user.id}")
        
        return BackupCodesResponse(
            backup_codes=backup_codes,
            generated_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Failed to regenerate backup codes for user {current_user.id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to regenerate backup codes"
        )


@router.get("/status")
async def two_factor_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get 2FA status for the current user.
    """
    return {
        "enabled": current_user.two_factor_enabled,
        "enabled_at": current_user.two_factor_enabled_at.isoformat() if current_user.two_factor_enabled_at else None,
        "last_used": current_user.two_factor_last_used.isoformat() if current_user.two_factor_last_used else None,
        "backup_codes_count": len(current_user.two_factor_backup_codes or [])
    }