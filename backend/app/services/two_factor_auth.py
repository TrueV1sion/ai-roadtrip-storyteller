"""
Two-Factor Authentication Service
"""

import pyotp
import qrcode
import io
import base64
from typing import Optional, Tuple
from datetime import datetime, timedelta
import secrets
import logging

logger = logging.getLogger(__name__)


class TwoFactorAuthService:
    """Handle 2FA operations using TOTP"""
    
    def __init__(self):
        self.issuer_name = "AI Road Trip Storyteller"
        self.backup_codes_count = 10
    
    def generate_secret(self) -> str:
        """Generate a new TOTP secret"""
        return pyotp.random_base32()
    
    def generate_qr_code(self, user_email: str, secret: str) -> str:
        """Generate QR code for 2FA setup"""
        # Create TOTP URI
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user_email,
            issuer_name=self.issuer_name
        )
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        # Convert to base64 image
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def verify_token(self, secret: str, token: str, window: int = 1) -> bool:
        """Verify TOTP token"""
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(token, valid_window=window)
        except Exception as e:
            logger.error(f"Error verifying TOTP token: {e}")
            return False
    
    def generate_backup_codes(self) -> List[str]:
        """Generate backup codes for account recovery"""
        codes = []
        for _ in range(self.backup_codes_count):
            # Generate 8-character alphanumeric code
            code = secrets.token_urlsafe(6).upper()
            codes.append(code)
        
        return codes
    
    def hash_backup_code(self, code: str) -> str:
        """Hash backup code for storage"""
        import hashlib
        return hashlib.sha256(code.encode()).hexdigest()
    
    async def enable_2fa(self, user_id: int, secret: str) -> Dict[str, Any]:
        """Enable 2FA for a user"""
        # Generate backup codes
        backup_codes = self.generate_backup_codes()
        hashed_codes = [self.hash_backup_code(code) for code in backup_codes]
        
        # Store in database
        # await update_user_2fa(user_id, secret, hashed_codes)
        
        return {
            "enabled": True,
            "backup_codes": backup_codes,
            "message": "2FA enabled successfully"
        }
    
    async def disable_2fa(self, user_id: int) -> Dict[str, Any]:
        """Disable 2FA for a user"""
        # Update database
        # await disable_user_2fa(user_id)
        
        return {
            "enabled": False,
            "message": "2FA disabled successfully"
        }
    
    def validate_backup_code(self, provided_code: str, stored_hashes: List[str]) -> Tuple[bool, Optional[str]]:
        """Validate a backup code"""
        provided_hash = self.hash_backup_code(provided_code)
        
        for stored_hash in stored_hashes:
            if provided_hash == stored_hash:
                return True, stored_hash
        
        return False, None


# Service instance
two_factor_service = TwoFactorAuthService()


# FastAPI routes
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

router = APIRouter()


class Enable2FARequest(BaseModel):
    token: str


class Verify2FARequest(BaseModel):
    token: str


@router.post("/2fa/setup")
async def setup_2fa(current_user: dict = Depends(get_current_user)):
    """Initialize 2FA setup"""
    user_id = current_user["user_id"]
    
    # Generate secret
    secret = two_factor_service.generate_secret()
    
    # Generate QR code
    qr_code = two_factor_service.generate_qr_code(
        current_user["email"],
        secret
    )
    
    # Store temporary secret
    # await store_temp_2fa_secret(user_id, secret)
    
    return {
        "qr_code": qr_code,
        "secret": secret,
        "manual_entry_key": secret
    }


@router.post("/2fa/enable")
async def enable_2fa(
    request: Enable2FARequest,
    current_user: dict = Depends(get_current_user)
):
    """Enable 2FA after verification"""
    user_id = current_user["user_id"]
    
    # Get temporary secret
    # secret = await get_temp_2fa_secret(user_id)
    secret = "TEMP_SECRET"  # Placeholder
    
    # Verify token
    if not two_factor_service.verify_token(secret, request.token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    
    # Enable 2FA
    result = await two_factor_service.enable_2fa(user_id, secret)
    
    return result


@router.post("/2fa/verify")
async def verify_2fa(
    request: Verify2FARequest,
    current_user: dict = Depends(get_current_user)
):
    """Verify 2FA token during login"""
    user_id = current_user["user_id"]
    
    # Get user's secret
    # user_2fa = await get_user_2fa(user_id)
    secret = "USER_SECRET"  # Placeholder
    
    # Verify token
    if two_factor_service.verify_token(secret, request.token):
        return {"verified": True}
    else:
        # Check backup codes
        # backup_codes = await get_user_backup_codes(user_id)
        # valid, used_code = two_factor_service.validate_backup_code(
        #     request.token, backup_codes
        # )
        
        # if valid:
        #     await mark_backup_code_used(user_id, used_code)
        #     return {"verified": True, "backup_code_used": True}
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 2FA code"
        )
