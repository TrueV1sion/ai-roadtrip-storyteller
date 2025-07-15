"""
Account security service for managing authentication security features.
Includes account lockout, 2FA support, and security notifications.
"""

import secrets
import pyotp
import qrcode
from io import BytesIO
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.models.user import User
from app.core.auth_rate_limiter import get_auth_rate_limiter
from app.schemas.user import UserSecurityUpdate
from app.core.cache import get_cache

logger = get_logger(__name__)


class AccountSecurityService:
    """
    Manages account security features including:
    - Failed login tracking
    - Account lockout
    - Two-factor authentication
    - Security notifications
    """
    
    def __init__(self):
        self.rate_limiter = get_auth_rate_limiter()
        self._cache = None
    
    async def _get_cache(self):
        """Lazy cache initialization"""
        if self._cache is None:
            self._cache = await get_cache()
        return self._cache
    
    async def handle_failed_login(
        self,
        identifier: str,
        ip_address: str,
        db: Session
    ) -> Dict[str, any]:
        """
        Handle a failed login attempt.
        
        Args:
            identifier: Email or username
            ip_address: IP address of attempt
            db: Database session
            
        Returns:
            Dict with lockout status and details
        """
        # Record the failed attempt
        attempts, is_locked = await self.rate_limiter.record_failed_attempt(
            identifier, ip_address
        )
        
        # Send notification if locked out
        if is_locked:
            # Get user for email notification
            user = db.query(User).filter(
                (User.email == identifier) | (User.username == identifier)
            ).first()
            
            if user:
                await self._send_lockout_notification(user, ip_address)
        
        # Get lockout info
        lockout_info = await self.rate_limiter.get_lockout_info(identifier)
        
        return {
            "attempts": attempts,
            "is_locked": is_locked,
            "lockout_info": lockout_info,
            "message": self._get_failure_message(attempts, is_locked)
        }
    
    async def handle_successful_login(
        self,
        user: User,
        ip_address: str,
        db: Session
    ):
        """
        Handle successful login - clear failed attempts and log.
        
        Args:
            user: User who logged in
            ip_address: IP address of login
            db: Database session
        """
        # Clear failed attempts
        await self.rate_limiter.clear_failed_attempts(user.email)
        await self.rate_limiter.clear_failed_attempts(user.username)
        
        # Log successful login
        await self._log_login_event(user, ip_address, True)
        
        # Check for suspicious activity
        await self._check_suspicious_login(user, ip_address)
    
    def _get_failure_message(self, attempts: int, is_locked: bool) -> str:
        """Generate appropriate failure message"""
        if is_locked:
            return (
                "Account has been locked due to too many failed login attempts. "
                "Please try again in 30 minutes or contact support."
            )
        elif attempts >= 3:
            remaining = AccountSecurityService.LOCKOUT_THRESHOLD - attempts
            return (
                f"Invalid credentials. {remaining} attempts remaining before "
                "account lockout."
            )
        else:
            return "Invalid credentials."
    
    # Two-Factor Authentication Methods
    
    def generate_2fa_secret(self, user: User) -> str:
        """Generate a new 2FA secret for user"""
        secret = pyotp.random_base32()
        return secret
    
    def generate_2fa_qr_code(self, user: User, secret: str) -> str:
        """
        Generate QR code for 2FA setup.
        
        Returns:
            Base64 encoded QR code image
        """
        # Create TOTP URI
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.email,
            issuer_name='AI Road Trip Storyteller'
        )
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode()
    
    def verify_2fa_token(self, secret: str, token: str) -> bool:
        """Verify a 2FA token"""
        totp = pyotp.TOTP(secret)
        # Allow for time drift (accepts current, previous, and next tokens)
        return totp.verify(token, valid_window=1)
    
    def generate_backup_codes(self, count: int = 10) -> list[str]:
        """Generate backup codes for 2FA"""
        codes = []
        for _ in range(count):
            # Generate 8-character alphanumeric codes
            code = ''.join(secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') 
                          for _ in range(8))
            # Format as XXXX-XXXX
            formatted = f"{code[:4]}-{code[4:]}"
            codes.append(formatted)
        return codes
    
    async def enable_2fa(
        self,
        user: User,
        secret: str,
        backup_codes: list[str],
        db: Session
    ):
        """Enable 2FA for a user"""
        # Store encrypted secret and backup codes
        user.two_factor_secret = secret  # Should be encrypted in production
        user.two_factor_backup_codes = ",".join(backup_codes)  # Should be hashed
        user.two_factor_enabled = True
        user.two_factor_enabled_at = datetime.utcnow()
        
        db.commit()
        
        # Log security event
        await self._log_security_event(
            user, 
            "2fa_enabled",
            {"method": "totp"}
        )
    
    async def disable_2fa(self, user: User, db: Session):
        """Disable 2FA for a user"""
        user.two_factor_secret = None
        user.two_factor_backup_codes = None
        user.two_factor_enabled = False
        
        db.commit()
        
        # Log security event
        await self._log_security_event(
            user,
            "2fa_disabled",
            {}
        )
    
    # Security Event Logging
    
    async def _log_login_event(
        self,
        user: User,
        ip_address: str,
        success: bool
    ):
        """Log login attempt"""
        cache = await self._get_cache()
        
        event_key = f"login_event:{user.id}:{datetime.utcnow().isoformat()}"
        event_data = {
            "user_id": user.id,
            "email": user.email,
            "ip_address": ip_address,
            "success": success,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Store for 30 days
        await cache.setex(event_key, 2592000, str(event_data))
    
    async def _log_security_event(
        self,
        user: User,
        event_type: str,
        details: Dict
    ):
        """Log security-related events"""
        cache = await self._get_cache()
        
        event_key = f"security_event:{user.id}:{datetime.utcnow().isoformat()}"
        event_data = {
            "user_id": user.id,
            "event_type": event_type,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Store for 90 days
        await cache.setex(event_key, 7776000, str(event_data))
    
    async def _check_suspicious_login(
        self,
        user: User,
        ip_address: str
    ):
        """Check for suspicious login patterns"""
        cache = await self._get_cache()
        
        # Get recent login IPs
        recent_ips_key = f"recent_login_ips:{user.id}"
        recent_ips = await cache.get(recent_ips_key)
        
        if recent_ips:
            ip_list = recent_ips.split(",")
            if ip_address not in ip_list:
                # New IP detected
                await self._send_new_device_notification(user, ip_address)
            
            # Add new IP to list
            ip_list.append(ip_address)
            # Keep last 10 IPs
            ip_list = list(set(ip_list[-10:]))
        else:
            ip_list = [ip_address]
        
        # Update recent IPs (expire after 30 days)
        await cache.setex(
            recent_ips_key,
            2592000,
            ",".join(ip_list)
        )
    
    async def _send_lockout_notification(
        self,
        user: User,
        ip_address: str
    ):
        """Send email notification about account lockout"""
        # TODO: Integrate with email service
        logger.info(
            f"Lockout notification would be sent to {user.email} "
            f"regarding lockout from IP {ip_address}"
        )
    
    async def _send_new_device_notification(
        self,
        user: User,
        ip_address: str
    ):
        """Send email notification about login from new device"""
        # TODO: Integrate with email service
        logger.info(
            f"New device notification would be sent to {user.email} "
            f"regarding login from IP {ip_address}"
        )
    
    # Admin Functions
    
    async def admin_unlock_account(
        self,
        identifier: str,
        admin_user: User,
        db: Session
    ):
        """Admin function to unlock an account"""
        # Verify admin privileges
        if not admin_user.is_admin:
            raise PermissionError("Admin privileges required")
        
        # Unlock the account
        await self.rate_limiter.unlock_account(identifier)
        
        # Log admin action
        await self._log_security_event(
            admin_user,
            "admin_unlock",
            {"unlocked_account": identifier}
        )
    
    async def get_security_status(
        self,
        user: User
    ) -> Dict:
        """Get comprehensive security status for a user"""
        lockout_info = await self.rate_limiter.get_lockout_info(user.email)
        
        return {
            "two_factor_enabled": user.two_factor_enabled,
            "two_factor_enabled_at": user.two_factor_enabled_at,
            "is_locked_out": lockout_info is not None,
            "lockout_info": lockout_info,
            "last_login": user.last_login,
            "password_changed_at": user.password_changed_at
        }


# Global instance
_account_security_service = None


def get_account_security_service() -> AccountSecurityService:
    """Get the global AccountSecurityService instance"""
    global _account_security_service
    if _account_security_service is None:
        _account_security_service = AccountSecurityService()
    return _account_security_service