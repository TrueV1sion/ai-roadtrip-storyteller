"""
Two-Factor Authentication Service for centralized 2FA operations.
"""
from typing import Tuple, Optional
from datetime import datetime
import pyotp
import bcrypt
from sqlalchemy.orm import Session

from app.models.user import User
from app.core.logger import get_logger
from app.core.rate_limiter import RateLimiter

logger = get_logger(__name__)


class TwoFactorService:
    """Service for handling 2FA operations."""
    
    def __init__(self):
        # Rate limiter for 2FA verification attempts
        self.verify_limiter = RateLimiter(max_requests=10, window_seconds=300)  # 10 attempts per 5 minutes
    
    async def verify_2fa_code(
        self, 
        db: Session, 
        user: User, 
        code: str
    ) -> Tuple[bool, bool, int]:
        """
        Verify a 2FA code (TOTP or backup code).
        
        Returns:
            Tuple of (is_valid, is_backup_code, remaining_backup_codes)
        """
        # Rate limiting
        if not self.verify_limiter.check_rate_limit(f"2fa_verify:{user.id}"):
            raise ValueError("Too many 2FA verification attempts. Please try again later.")
        
        # Check if 2FA is enabled
        if not user.two_factor_enabled or not user.two_factor_secret:
            logger.warning(f"2FA verification attempted for user without 2FA enabled: {user.id}")
            return False, False, 0
        
        # Normalize code
        code = code.strip().upper()
        
        # Try TOTP first (6 digits)
        if len(code) == 6 and code.isdigit():
            totp = pyotp.TOTP(user.two_factor_secret)
            if totp.verify(code, valid_window=1):
                # Update last used timestamp
                user.two_factor_last_used = datetime.utcnow()
                db.commit()
                
                logger.info(f"TOTP code verified for user {user.id}")
                return True, False, len(user.two_factor_backup_codes or [])
        
        # Try backup code (format: XXXX-XXXX or XXXXXXXX)
        if len(code) in [8, 9]:  # 8 chars or 9 with hyphen
            # Remove hyphen if present
            clean_code = code.replace("-", "")
            
            if len(clean_code) == 8 and clean_code.isalnum():
                # Check against stored backup codes
                for i, hashed_code in enumerate(user.two_factor_backup_codes or []):
                    if bcrypt.checkpw(clean_code.encode('utf-8'), hashed_code.encode('utf-8')):
                        # Remove used backup code
                        user.two_factor_backup_codes.pop(i)
                        user.two_factor_last_used = datetime.utcnow()
                        db.commit()
                        
                        remaining = len(user.two_factor_backup_codes)
                        logger.info(f"Backup code used for user {user.id}. {remaining} codes remaining.")
                        
                        # Warn if low on backup codes
                        if remaining <= 2:
                            logger.warning(f"User {user.id} has only {remaining} backup codes remaining")
                        
                        return True, True, remaining
        
        logger.warning(f"Invalid 2FA code attempted for user {user.id}")
        return False, False, len(user.two_factor_backup_codes or [])
    
    def generate_totp_uri(self, user: User, issuer: str = "AI Road Trip") -> str:
        """Generate provisioning URI for TOTP setup."""
        if not user.two_factor_secret:
            raise ValueError("User does not have a 2FA secret")
        
        totp = pyotp.TOTP(user.two_factor_secret)
        return totp.provisioning_uri(
            name=user.email,
            issuer_name=issuer
        )
    
    def is_valid_totp_secret(self, secret: str) -> bool:
        """Validate TOTP secret format."""
        try:
            # Check if it's a valid base32 string
            pyotp.TOTP(secret).now()
            return True
        except Exception:
            return False


# Global instance
two_factor_service = TwoFactorService()