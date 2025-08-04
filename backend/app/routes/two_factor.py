"""
Two-Factor Authentication Routes - Complete Implementation
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import pyotp
import qrcode
import io
import base64
import secrets
import bcrypt
from typing import List
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.core.auth import get_current_user, verify_password
from app.services.two_factor_service import two_factor_service
from app.schemas.two_factor import (
    TwoFactorSetupResponse,
    TwoFactorEnableRequest,
    TwoFactorDisableRequest,
    BackupCodesResponse,
    TwoFactorStatusResponse
)
from app.core.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


def generate_backup_codes(count: int = 8) -> List[str]:
    """Generate backup codes in format XXXX-XXXX."""
    codes = []
    for _ in range(count):
        code = ''.join(secrets.choice('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(8))
        formatted_code = f"{code[:4]}-{code[4:]}"
        codes.append(formatted_code)
    return codes


def hash_backup_codes(codes: List[str]) -> List[str]:
    """Hash backup codes for storage."""
    hashed_codes = []
    for code in codes:
        clean_code = code.replace("-", "")
        hashed = bcrypt.hashpw(clean_code.encode('utf-8'), bcrypt.gensalt())
        hashed_codes.append(hashed.decode('utf-8'))
    return hashed_codes


@router.get("/two-factor/status", response_model=TwoFactorStatusResponse)
async def get_two_factor_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get two-factor authentication status."""
    return TwoFactorStatusResponse(
        enabled=current_user.two_factor_enabled,
        enabled_at=current_user.two_factor_enabled_at.isoformat() if current_user.two_factor_enabled_at else None,
        last_used=current_user.two_factor_last_used.isoformat() if current_user.two_factor_last_used else None,
        backup_codes_count=len(current_user.two_factor_backup_codes or [])
    )


@router.post("/two-factor/setup", response_model=TwoFactorSetupResponse)
async def setup_two_factor(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initialize two-factor authentication setup.
    Returns QR code and backup codes but doesn't enable 2FA yet.
    """
    if current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is already enabled"
        )
    
    # Generate new TOTP secret
    secret = pyotp.random_base32()
    
    # Generate QR code
    provisioning_uri = pyotp.TOTP(secret).provisioning_uri(
        name=current_user.email,
        issuer_name="AI Road Trip"
    )
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_code_b64 = base64.b64encode(buf.getvalue()).decode()
    
    # Generate backup codes
    backup_codes = generate_backup_codes()
    
    # Store secret temporarily (not enabled yet)
    current_user.two_factor_secret = secret
    current_user.two_factor_enabled = False
    db.commit()
    
    logger.info(f"2FA setup initiated for user {current_user.id}")
    
    return TwoFactorSetupResponse(
        qr_code=f"data:image/png;base64,{qr_code_b64}",
        secret=secret,
        backup_codes=backup_codes,
        setup_complete=False
    )


@router.post("/two-factor/enable")
async def enable_two_factor(
    request: TwoFactorEnableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Complete 2FA setup by verifying a code and enabling 2FA.
    """
    if current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is already enabled"
        )
    
    if not current_user.two_factor_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor setup not initiated. Please call /setup first"
        )
    
    # Verify the provided code
    totp = pyotp.TOTP(current_user.two_factor_secret)
    if not totp.verify(request.code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    # Generate and hash backup codes
    backup_codes = generate_backup_codes()
    hashed_codes = hash_backup_codes(backup_codes)
    
    # Enable 2FA
    current_user.two_factor_enabled = True
    current_user.two_factor_enabled_at = datetime.utcnow()
    current_user.two_factor_backup_codes = hashed_codes
    db.commit()
    
    logger.info(f"2FA enabled for user {current_user.id}")
    
    return {
        "message": "Two-factor authentication has been enabled",
        "backup_codes": backup_codes,
        "backup_codes_count": len(backup_codes)
    }


@router.post("/two-factor/disable")
async def disable_two_factor(
    request: TwoFactorDisableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disable two-factor authentication.
    Requires password verification for security.
    """
    if not current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled"
        )
    
    # Verify password
    if not verify_password(request.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    
    # Disable 2FA
    current_user.two_factor_enabled = False
    current_user.two_factor_secret = None
    current_user.two_factor_backup_codes = []
    current_user.two_factor_enabled_at = None
    db.commit()
    
    logger.info(f"2FA disabled for user {current_user.id}")
    
    return {
        "message": "Two-factor authentication has been disabled"
    }


@router.post("/two-factor/regenerate-backup-codes", response_model=BackupCodesResponse)
async def regenerate_backup_codes(
    password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Regenerate backup codes.
    Requires password verification and replaces all existing codes.
    """
    if not current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled"
        )
    
    # Verify password
    if not verify_password(password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    
    # Generate new backup codes
    backup_codes = generate_backup_codes()
    hashed_codes = hash_backup_codes(backup_codes)
    
    # Update user
    current_user.two_factor_backup_codes = hashed_codes
    db.commit()
    
    logger.info(f"Backup codes regenerated for user {current_user.id}")
    
    return BackupCodesResponse(
        backup_codes=backup_codes,
        generated_at=datetime.utcnow().isoformat()
    )


@router.post("/two-factor/verify")
async def verify_two_factor_code(
    code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify a two-factor authentication code.
    This endpoint is for testing/verification purposes only.
    Actual login 2FA is handled in the auth routes.
    """
    if not current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled"
        )
    
    try:
        is_valid, is_backup, remaining = await two_factor_service.verify_2fa_code(
            db=db,
            user=current_user,
            code=code
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid code"
            )
        
        return {
            "verified": True,
            "is_backup_code": is_backup,
            "backup_codes_remaining": remaining,
            "message": "Code verified successfully"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e)
        )
