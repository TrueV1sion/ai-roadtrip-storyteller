"""
Security monitoring and alerting system for detecting and responding to security events.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import json
from enum import Enum

from app.core.logger import get_logger
from app.core.cache import cache_manager
from app.core.config import settings
from app.db.base import get_db
from app.models.user import User
from sqlalchemy.orm import Session

logger = get_logger(__name__)


class SecurityEventType(Enum):
    """Types of security events to monitor."""
    FAILED_LOGIN = "failed_login"
    BRUTE_FORCE_ATTEMPT = "brute_force_attempt"
    SUSPICIOUS_IP = "suspicious_ip"
    ACCOUNT_LOCKOUT = "account_lockout"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    SUSPICIOUS_API_PATTERN = "suspicious_api_pattern"
    DATA_EXFILTRATION = "data_exfiltration"
    INVALID_TOKEN = "invalid_token"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    CONCURRENT_SESSIONS = "concurrent_sessions"
    GEO_ANOMALY = "geo_anomaly"
    TWO_FACTOR_BYPASS_ATTEMPT = "2fa_bypass_attempt"
    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
    XSS_ATTEMPT = "xss_attempt"


class SecurityEventSeverity(Enum):
    """Severity levels for security events."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEvent:
    """Represents a security event."""
    
    def __init__(
        self,
        event_type: SecurityEventType,
        severity: SecurityEventSeverity,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ):
        self.event_type = event_type
        self.severity = severity
        self.user_id = user_id
        self.ip_address = ip_address
        self.details = details or {}
        self.timestamp = timestamp or datetime.utcnow()
        self.id = f"{event_type.value}_{self.timestamp.timestamp()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "user_id": self.user_id,
            "ip_address": self.ip_address,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


class SecurityMonitor:
    """Main security monitoring service."""
    
    def __init__(self):
        self.event_handlers = {
            SecurityEventType.FAILED_LOGIN: self._handle_failed_login,
            SecurityEventType.BRUTE_FORCE_ATTEMPT: self._handle_brute_force,
            SecurityEventType.SUSPICIOUS_IP: self._handle_suspicious_ip,
            SecurityEventType.ACCOUNT_LOCKOUT: self._handle_account_lockout,
            SecurityEventType.UNAUTHORIZED_ACCESS: self._handle_unauthorized_access,
            SecurityEventType.PRIVILEGE_ESCALATION: self._handle_privilege_escalation,
            SecurityEventType.TWO_FACTOR_BYPASS_ATTEMPT: self._handle_2fa_bypass,
            SecurityEventType.SQL_INJECTION_ATTEMPT: self._handle_injection_attempt,
            SecurityEventType.DATA_EXFILTRATION: self._handle_data_exfiltration,
        }
        
        # Thresholds for triggering alerts
        self.thresholds = {
            SecurityEventType.FAILED_LOGIN: 5,  # 5 failures trigger alert
            SecurityEventType.RATE_LIMIT_EXCEEDED: 10,  # 10 rate limit hits
            SecurityEventType.INVALID_TOKEN: 10,  # 10 invalid tokens
        }
        
        # Time windows for event aggregation (in seconds)
        self.time_windows = {
            SecurityEventType.FAILED_LOGIN: 300,  # 5 minutes
            SecurityEventType.RATE_LIMIT_EXCEEDED: 60,  # 1 minute
            SecurityEventType.INVALID_TOKEN: 300,  # 5 minutes
        }
        
        self.alert_queue = asyncio.Queue()
        self.is_running = False
    
    async def start(self):
        """Start the security monitoring service."""
        self.is_running = True
        logger.info("Security monitoring service started")
        
        # Start background tasks
        asyncio.create_task(self._process_alerts())
        asyncio.create_task(self._cleanup_old_events())
    
    async def stop(self):
        """Stop the security monitoring service."""
        self.is_running = False
        logger.info("Security monitoring service stopped")
    
    async def log_event(self, event: SecurityEvent):
        """Log a security event and trigger appropriate actions."""
        try:
            # Store event
            await self._store_event(event)
            
            # Check if event requires immediate action
            if event.severity in [SecurityEventSeverity.HIGH, SecurityEventSeverity.CRITICAL]:
                await self.alert_queue.put(event)
            
            # Run event-specific handler
            handler = self.event_handlers.get(event.event_type)
            if handler:
                await handler(event)
            
            # Check for patterns
            await self._check_event_patterns(event)
            
            # Log event
            logger.warning(
                f"Security event: {event.event_type.value} | "
                f"Severity: {event.severity.value} | "
                f"User: {event.user_id} | "
                f"IP: {event.ip_address} | "
                f"Details: {json.dumps(event.details)}"
            )
            
        except Exception as e:
            logger.error(f"Error logging security event: {e}")
    
    async def _store_event(self, event: SecurityEvent):
        """Store event in cache and database."""
        # Store in cache for quick access
        cache_key = f"security_event:{event.id}"
        await cache_manager.set(
            cache_key,
            json.dumps(event.to_dict()),
            ttl=86400  # 24 hours
        )
        
        # Add to event type index
        index_key = f"security_events:{event.event_type.value}:{event.timestamp.date()}"
        await cache_manager.sadd(index_key, event.id)
        await cache_manager.expire(index_key, 86400 * 7)  # 7 days
        
        # Store in database for long-term retention
        # TODO: Implement database storage
    
    async def _check_event_patterns(self, event: SecurityEvent):
        """Check for suspicious patterns in events."""
        # Check threshold-based patterns
        threshold = self.thresholds.get(event.event_type)
        time_window = self.time_windows.get(event.event_type)
        
        if threshold and time_window:
            count = await self._count_recent_events(
                event.event_type,
                event.user_id or event.ip_address,
                time_window
            )
            
            if count >= threshold:
                # Create escalated event
                escalated_event = SecurityEvent(
                    event_type=SecurityEventType.BRUTE_FORCE_ATTEMPT,
                    severity=SecurityEventSeverity.HIGH,
                    user_id=event.user_id,
                    ip_address=event.ip_address,
                    details={
                        "original_event_type": event.event_type.value,
                        "event_count": count,
                        "time_window": time_window,
                        "threshold": threshold
                    }
                )
                await self.log_event(escalated_event)
    
    async def _count_recent_events(
        self,
        event_type: SecurityEventType,
        identifier: str,
        time_window: int
    ) -> int:
        """Count recent events of a specific type."""
        count_key = f"event_count:{event_type.value}:{identifier}"
        
        # Increment counter
        count = await cache_manager.incr(count_key)
        
        # Set expiration on first increment
        if count == 1:
            await cache_manager.expire(count_key, time_window)
        
        return count
    
    async def _handle_failed_login(self, event: SecurityEvent):
        """Handle failed login attempts."""
        if event.user_id:
            # Track failed attempts per user
            attempts_key = f"failed_login_attempts:{event.user_id}"
            attempts = await cache_manager.incr(attempts_key)
            await cache_manager.expire(attempts_key, 3600)  # 1 hour
            
            # Lock account after too many attempts
            if attempts >= 10:
                await self._lock_account(event.user_id, "Too many failed login attempts")
    
    async def _handle_brute_force(self, event: SecurityEvent):
        """Handle brute force attempts."""
        # Block IP temporarily
        if event.ip_address:
            block_key = f"blocked_ip:{event.ip_address}"
            await cache_manager.set(block_key, "1", ttl=3600)  # 1 hour block
            
            logger.critical(f"Blocking IP {event.ip_address} due to brute force attempt")
    
    async def _handle_suspicious_ip(self, event: SecurityEvent):
        """Handle suspicious IP addresses."""
        # Add to watchlist
        if event.ip_address:
            watchlist_key = "suspicious_ip_watchlist"
            await cache_manager.sadd(watchlist_key, event.ip_address)
    
    async def _handle_account_lockout(self, event: SecurityEvent):
        """Handle account lockout events."""
        # Notify user via email
        # TODO: Implement email notification
        pass
    
    async def _handle_unauthorized_access(self, event: SecurityEvent):
        """Handle unauthorized access attempts."""
        # Immediate alert
        await self.alert_queue.put(event)
        
        # Terminate any active sessions
        if event.user_id:
            await self._terminate_user_sessions(event.user_id)
    
    async def _handle_privilege_escalation(self, event: SecurityEvent):
        """Handle privilege escalation attempts."""
        # Critical alert
        await self.alert_queue.put(event)
        
        # Revert any privilege changes
        # TODO: Implement privilege reversion
    
    async def _handle_2fa_bypass(self, event: SecurityEvent):
        """Handle 2FA bypass attempts."""
        # Lock account immediately
        if event.user_id:
            await self._lock_account(event.user_id, "2FA bypass attempt detected")
    
    async def _handle_injection_attempt(self, event: SecurityEvent):
        """Handle SQL injection attempts."""
        # Block IP
        if event.ip_address:
            block_key = f"blocked_ip:{event.ip_address}"
            await cache_manager.set(block_key, "1", ttl=86400)  # 24 hour block
    
    async def _handle_data_exfiltration(self, event: SecurityEvent):
        """Handle potential data exfiltration."""
        # Critical alert
        await self.alert_queue.put(event)
        
        # Rate limit user
        if event.user_id:
            rate_limit_key = f"strict_rate_limit:{event.user_id}"
            await cache_manager.set(rate_limit_key, "1", ttl=3600)
    
    async def _lock_account(self, user_id: str, reason: str):
        """Lock a user account."""
        try:
            lock_key = f"account_locked:{user_id}"
            await cache_manager.set(
                lock_key,
                json.dumps({"reason": reason, "timestamp": datetime.utcnow().isoformat()}),
                ttl=3600  # 1 hour lock
            )
            
            # Log lockout event
            lockout_event = SecurityEvent(
                event_type=SecurityEventType.ACCOUNT_LOCKOUT,
                severity=SecurityEventSeverity.HIGH,
                user_id=user_id,
                details={"reason": reason}
            )
            await self.log_event(lockout_event)
            
        except Exception as e:
            logger.error(f"Error locking account {user_id}: {e}")
    
    async def _terminate_user_sessions(self, user_id: str):
        """Terminate all active sessions for a user."""
        # Invalidate all tokens
        token_blacklist_key = f"token_blacklist:{user_id}:*"
        # TODO: Implement token invalidation
    
    async def _process_alerts(self):
        """Process security alerts from the queue."""
        while self.is_running:
            try:
                # Get alert from queue with timeout
                event = await asyncio.wait_for(
                    self.alert_queue.get(),
                    timeout=1.0
                )
                
                # Send alert based on severity
                if event.severity == SecurityEventSeverity.CRITICAL:
                    await self._send_critical_alert(event)
                else:
                    await self._send_alert(event)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing alert: {e}")
    
    async def _send_alert(self, event: SecurityEvent):
        """Send security alert."""
        # TODO: Implement actual alert sending (email, SMS, webhook)
        logger.warning(f"SECURITY ALERT: {event.to_dict()}")
    
    async def _send_critical_alert(self, event: SecurityEvent):
        """Send critical security alert."""
        # TODO: Implement critical alert (page on-call, etc.)
        logger.critical(f"CRITICAL SECURITY ALERT: {event.to_dict()}")
    
    async def _cleanup_old_events(self):
        """Clean up old events periodically."""
        while self.is_running:
            try:
                # Run cleanup every hour
                await asyncio.sleep(3600)
                
                # TODO: Implement cleanup logic
                
            except Exception as e:
                logger.error(f"Error cleaning up events: {e}")
    
    async def get_security_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get security event summary for the specified time period."""
        summary = {
            "time_period": f"Last {hours} hours",
            "total_events": 0,
            "events_by_type": defaultdict(int),
            "events_by_severity": defaultdict(int),
            "top_ips": defaultdict(int),
            "top_users": defaultdict(int),
            "blocked_ips": [],
            "locked_accounts": []
        }
        
        # TODO: Implement summary generation from stored events
        
        return dict(summary)
    
    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if an IP address is blocked."""
        block_key = f"blocked_ip:{ip_address}"
        return asyncio.run(cache_manager.exists(block_key))
    
    def is_account_locked(self, user_id: str) -> bool:
        """Check if a user account is locked."""
        lock_key = f"account_locked:{user_id}"
        return asyncio.run(cache_manager.exists(lock_key))


# Global security monitor instance
security_monitor = SecurityMonitor()