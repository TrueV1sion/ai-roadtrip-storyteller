"""
Security event logger for password and authentication events.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.monitoring.audit_logger import audit_logger
from app.core.cache import get_cache

logger = get_logger(__name__)


class SecurityEventLogger:
    """Logger for security-related events with special handling for passwords."""
    
    def __init__(self):
        self.cache = None
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Lazy initialization of cache connection."""
        if not self._initialized:
            self.cache = await get_cache()
            self._initialized = True
    
    async def log_password_change(
        self,
        user_id: str,
        user_email: str,
        ip_address: str,
        success: bool,
        reason: Optional[str] = None
    ):
        """Log password change attempt."""
        event_details = {
            "user_email": user_email,
            "ip_address": ip_address,
            "success": success,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await audit_logger.log_audit_event(
            event_type="password_change",
            user_id=user_id,
            details=event_details
        )
        
        logger.info(f"Password change {'successful' if success else 'failed'} for user {user_email}")
    
    async def log_password_reset_request(
        self,
        email: str,
        ip_address: str,
        success: bool
    ):
        """Log password reset request."""
        event_details = {
            "email": email,
            "ip_address": ip_address,
            "success": success,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await audit_logger.log_audit_event(
            event_type="password_reset_request",
            user_id=email,  # Use email as identifier since user might not be authenticated
            details=event_details
        )
        
        logger.info(f"Password reset requested for {email} from {ip_address}")
    
    async def log_password_reset_complete(
        self,
        user_id: str,
        user_email: str,
        ip_address: str,
        success: bool,
        reason: Optional[str] = None
    ):
        """Log password reset completion."""
        event_details = {
            "user_email": user_email,
            "ip_address": ip_address,
            "success": success,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await audit_logger.log_audit_event(
            event_type="password_reset_complete",
            user_id=user_id,
            details=event_details
        )
        
        logger.info(f"Password reset {'successful' if success else 'failed'} for user {user_email}")
    
    async def log_failed_login(
        self,
        username: str,
        ip_address: str,
        attempts: int,
        locked: bool
    ):
        """Log failed login attempt."""
        event_details = {
            "username": username,
            "ip_address": ip_address,
            "attempts": attempts,
            "locked": locked,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await audit_logger.log_audit_event(
            event_type="failed_login",
            user_id=username,
            details=event_details
        )
        
        if locked:
            logger.warning(f"Account {username} locked after {attempts} failed attempts from {ip_address}")
        else:
            logger.warning(f"Failed login attempt {attempts} for {username} from {ip_address}")
    
    async def log_account_lockout(
        self,
        identifier: str,
        ip_address: str,
        lockout_type: str,  # "account" or "ip"
        duration_seconds: int
    ):
        """Log account or IP lockout."""
        event_details = {
            "identifier": identifier,
            "ip_address": ip_address,
            "lockout_type": lockout_type,
            "duration_seconds": duration_seconds,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await audit_logger.log_audit_event(
            event_type="account_lockout",
            user_id=identifier,
            details=event_details
        )
        
        logger.warning(f"{lockout_type.title()} lockout for {identifier} from {ip_address} for {duration_seconds} seconds")
    
    async def log_password_policy_violation(
        self,
        user_id: Optional[str],
        email: Optional[str],
        violations: list,
        ip_address: str
    ):
        """Log password policy violations."""
        event_details = {
            "email": email,
            "violations": violations,
            "ip_address": ip_address,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await audit_logger.log_audit_event(
            event_type="password_policy_violation",
            user_id=user_id or email or "unknown",
            details=event_details
        )
        
        logger.warning(f"Password policy violations for {email or 'unknown'}: {', '.join(violations)}")
    
    async def log_pwned_password_attempt(
        self,
        user_id: Optional[str],
        email: Optional[str],
        pwned_count: int,
        ip_address: str
    ):
        """Log attempt to use a pwned password."""
        event_details = {
            "email": email,
            "pwned_count": pwned_count,
            "ip_address": ip_address,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await audit_logger.log_audit_event(
            event_type="pwned_password_attempt",
            user_id=user_id or email or "unknown",
            details=event_details
        )
        
        logger.warning(f"Pwned password attempt by {email or 'unknown'} - found {pwned_count} times in breaches")
    
    async def get_recent_security_events(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> list:
        """Get recent security events from cache/storage."""
        # In a real implementation, this would query a persistent store
        # For now, return empty list as this is a stub
        return []


# Global instance
_security_event_logger = None


def get_security_event_logger() -> SecurityEventLogger:
    """Get the global SecurityEventLogger instance."""
    global _security_event_logger
    if _security_event_logger is None:
        _security_event_logger = SecurityEventLogger()
    return _security_event_logger