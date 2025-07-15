"""
Enhanced session management service with security features.
"""

import uuid
import json
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any, Set
from enum import Enum

from app.core.logger import get_logger
from app.core.cache import cache_manager
from app.core.config import settings
from app.monitoring.security_monitor import security_monitor, SecurityEvent, SecurityEventType, SecurityEventSeverity
from app.monitoring.audit_logger import audit_logger, AuditEventType

logger = get_logger(__name__)


class SessionStatus(Enum):
    """Session status types."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    LOCKED = "locked"


class DeviceInfo:
    """Device information for session tracking."""
    
    def __init__(
        self,
        user_agent: str,
        ip_address: str,
        device_id: Optional[str] = None,
        platform: Optional[str] = None,
        browser: Optional[str] = None
    ):
        self.user_agent = user_agent
        self.ip_address = ip_address
        self.device_id = device_id or self._generate_device_id(user_agent, ip_address)
        self.platform = platform
        self.browser = browser
        self.fingerprint = self._generate_fingerprint()
    
    def _generate_device_id(self, user_agent: str, ip_address: str) -> str:
        """Generate a device ID from user agent and IP."""
        import hashlib
        data = f"{user_agent}:{ip_address}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _generate_fingerprint(self) -> str:
        """Generate device fingerprint for tracking."""
        import hashlib
        data = f"{self.device_id}:{self.platform}:{self.browser}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "device_id": self.device_id,
            "ip_address": self.ip_address,
            "platform": self.platform,
            "browser": self.browser,
            "fingerprint": self.fingerprint
        }


class Session:
    """Enhanced session with security features."""
    
    def __init__(
        self,
        session_id: str,
        user_id: str,
        device_info: DeviceInfo,
        created_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
        is_persistent: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.device_info = device_info
        self.created_at = created_at or datetime.utcnow()
        self.expires_at = expires_at or self._calculate_expiry(is_persistent)
        self.last_activity = self.created_at
        self.is_persistent = is_persistent
        self.status = SessionStatus.ACTIVE
        self.metadata = metadata or {}
        self.activity_count = 0
        self.refresh_token = None
        self.csrf_token = secrets.token_urlsafe(32)
    
    def _calculate_expiry(self, is_persistent: bool) -> datetime:
        """Calculate session expiry time."""
        if is_persistent:
            # Persistent sessions last 30 days
            return datetime.utcnow() + timedelta(days=30)
        else:
            # Regular sessions last 24 hours
            return datetime.utcnow() + timedelta(hours=24)
    
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at
    
    def is_active(self) -> bool:
        """Check if session is active."""
        return self.status == SessionStatus.ACTIVE and not self.is_expired()
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()
        self.activity_count += 1
    
    def extend_expiry(self, hours: int = 1):
        """Extend session expiry."""
        self.expires_at = datetime.utcnow() + timedelta(hours=hours)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "device_info": self.device_info.to_dict(),
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "is_persistent": self.is_persistent,
            "status": self.status.value,
            "activity_count": self.activity_count,
            "csrf_token": self.csrf_token,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """Create session from dictionary."""
        device_info = DeviceInfo(
            user_agent=data["device_info"].get("user_agent", ""),
            ip_address=data["device_info"]["ip_address"],
            device_id=data["device_info"].get("device_id"),
            platform=data["device_info"].get("platform"),
            browser=data["device_info"].get("browser")
        )
        
        session = cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            device_info=device_info,
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            is_persistent=data.get("is_persistent", False),
            metadata=data.get("metadata", {})
        )
        
        session.last_activity = datetime.fromisoformat(data["last_activity"])
        session.status = SessionStatus(data["status"])
        session.activity_count = data.get("activity_count", 0)
        session.csrf_token = data.get("csrf_token", secrets.token_urlsafe(32))
        
        return session


class SessionManager:
    """Enhanced session management with security features."""
    
    def __init__(self):
        self.max_sessions_per_user = 5
        self.max_sessions_per_device = 2
        self.session_timeout = 3600  # 1 hour idle timeout
        self.concurrent_session_limit = 3
        self.geo_anomaly_detection = True
        self.device_tracking = True
    
    async def create_session(
        self,
        user_id: str,
        device_info: DeviceInfo,
        is_persistent: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Session:
        """Create a new session."""
        try:
            # Check concurrent session limit
            active_sessions = await self.get_active_sessions(user_id)
            if len(active_sessions) >= self.concurrent_session_limit:
                # Revoke oldest session
                oldest = min(active_sessions, key=lambda s: s.created_at)
                await self.revoke_session(oldest.session_id, "Concurrent session limit reached")
            
            # Check for suspicious activity
            await self._check_suspicious_login(user_id, device_info)
            
            # Create session
            session_id = str(uuid.uuid4())
            session = Session(
                session_id=session_id,
                user_id=user_id,
                device_info=device_info,
                is_persistent=is_persistent,
                metadata=metadata
            )
            
            # Store session
            await self._store_session(session)
            
            # Track device
            if self.device_tracking:
                await self._track_device(user_id, device_info)
            
            # Log session creation
            await audit_logger.log(
                event_type=AuditEventType.LOGIN_SUCCESS,
                user_id=user_id,
                ip_address=device_info.ip_address,
                session_id=session_id,
                details={
                    "device_id": device_info.device_id,
                    "persistent": is_persistent
                }
            )
            
            logger.info(f"Session created for user {user_id}: {session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        try:
            session_key = f"session:{session_id}"
            session_data = await cache_manager.get(session_key)
            
            if not session_data:
                return None
            
            session = Session.from_dict(json.loads(session_data))
            
            # Check if expired
            if session.is_expired():
                await self.revoke_session(session_id, "Session expired")
                return None
            
            # Check idle timeout
            idle_time = (datetime.utcnow() - session.last_activity).total_seconds()
            if idle_time > self.session_timeout and not session.is_persistent:
                await self.revoke_session(session_id, "Session idle timeout")
                return None
            
            return session
            
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return None
    
    async def update_session_activity(
        self,
        session_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """Update session activity and check for anomalies."""
        try:
            session = await self.get_session(session_id)
            if not session:
                return False
            
            # Check for IP change
            if ip_address and ip_address != session.device_info.ip_address:
                await self._handle_ip_change(session, ip_address)
            
            # Check for user agent change
            if user_agent and user_agent != session.device_info.user_agent:
                await self._handle_device_change(session, user_agent)
            
            # Update activity
            session.update_activity()
            
            # Extend expiry for active sessions
            if session.activity_count % 10 == 0:  # Every 10 requests
                session.extend_expiry()
            
            # Store updated session
            await self._store_session(session)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating session activity: {e}")
            return False
    
    async def get_active_sessions(self, user_id: str) -> List[Session]:
        """Get all active sessions for a user."""
        try:
            # Get session IDs from index
            index_key = f"user_sessions:{user_id}"
            session_ids = await cache_manager.smembers(index_key)
            
            sessions = []
            for session_id in session_ids:
                session = await self.get_session(session_id)
                if session and session.is_active():
                    sessions.append(session)
            
            return sorted(sessions, key=lambda s: s.last_activity, reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting active sessions: {e}")
            return []
    
    async def revoke_session(self, session_id: str, reason: str = "Manual revocation"):
        """Revoke a session."""
        try:
            session = await self.get_session(session_id)
            if not session:
                return
            
            # Update status
            session.status = SessionStatus.REVOKED
            await self._store_session(session)
            
            # Remove from indexes
            await self._remove_session_from_indexes(session)
            
            # Log revocation
            await audit_logger.log(
                event_type=AuditEventType.LOGOUT,
                user_id=session.user_id,
                session_id=session_id,
                ip_address=session.device_info.ip_address,
                details={"reason": reason}
            )
            
            logger.info(f"Session revoked: {session_id} - {reason}")
            
        except Exception as e:
            logger.error(f"Error revoking session: {e}")
    
    async def revoke_all_sessions(self, user_id: str, except_current: Optional[str] = None):
        """Revoke all sessions for a user."""
        try:
            sessions = await self.get_active_sessions(user_id)
            
            for session in sessions:
                if session.session_id != except_current:
                    await self.revoke_session(session.session_id, "Bulk revocation")
            
            # Log security event
            await security_monitor.log_event(SecurityEvent(
                event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
                severity=SecurityEventSeverity.MEDIUM,
                user_id=user_id,
                details={"action": "all_sessions_revoked"}
            ))
            
        except Exception as e:
            logger.error(f"Error revoking all sessions: {e}")
    
    async def get_session_info(self, user_id: str) -> Dict[str, Any]:
        """Get detailed session information for a user."""
        try:
            sessions = await self.get_active_sessions(user_id)
            devices = await self._get_known_devices(user_id)
            
            return {
                "active_sessions": [
                    {
                        "session_id": s.session_id,
                        "device": s.device_info.to_dict(),
                        "created_at": s.created_at.isoformat(),
                        "last_activity": s.last_activity.isoformat(),
                        "expires_at": s.expires_at.isoformat(),
                        "is_current": False  # Set by caller
                    }
                    for s in sessions
                ],
                "session_count": len(sessions),
                "known_devices": devices,
                "concurrent_limit": self.concurrent_session_limit
            }
            
        except Exception as e:
            logger.error(f"Error getting session info: {e}")
            return {"active_sessions": [], "session_count": 0}
    
    async def validate_csrf_token(self, session_id: str, csrf_token: str) -> bool:
        """Validate CSRF token for session."""
        try:
            session = await self.get_session(session_id)
            if not session:
                return False
            
            return session.csrf_token == csrf_token
            
        except Exception as e:
            logger.error(f"Error validating CSRF token: {e}")
            return False
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions (background task)."""
        try:
            # Get all session keys
            session_keys = await cache_manager.keys("session:*")
            
            expired_count = 0
            for key in session_keys:
                session_data = await cache_manager.get(key)
                if session_data:
                    session = Session.from_dict(json.loads(session_data))
                    if session.is_expired():
                        await self.revoke_session(session.session_id, "Expired")
                        expired_count += 1
            
            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} expired sessions")
            
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")
    
    async def _store_session(self, session: Session):
        """Store session in cache."""
        session_key = f"session:{session.session_id}"
        session_data = json.dumps(session.to_dict())
        
        # Calculate TTL
        ttl = int((session.expires_at - datetime.utcnow()).total_seconds())
        ttl = max(ttl, 60)  # Minimum 1 minute
        
        # Store session
        await cache_manager.set(session_key, session_data, ttl=ttl)
        
        # Update indexes
        await self._update_session_indexes(session)
    
    async def _update_session_indexes(self, session: Session):
        """Update session indexes for quick lookups."""
        # User index
        user_index_key = f"user_sessions:{session.user_id}"
        await cache_manager.sadd(user_index_key, session.session_id)
        await cache_manager.expire(user_index_key, 86400 * 30)  # 30 days
        
        # Device index
        device_index_key = f"device_sessions:{session.device_info.device_id}"
        await cache_manager.sadd(device_index_key, session.session_id)
        await cache_manager.expire(device_index_key, 86400 * 30)
    
    async def _remove_session_from_indexes(self, session: Session):
        """Remove session from indexes."""
        # User index
        user_index_key = f"user_sessions:{session.user_id}"
        await cache_manager.srem(user_index_key, session.session_id)
        
        # Device index
        device_index_key = f"device_sessions:{session.device_info.device_id}"
        await cache_manager.srem(device_index_key, session.session_id)
    
    async def _check_suspicious_login(self, user_id: str, device_info: DeviceInfo):
        """Check for suspicious login patterns."""
        # Check for rapid location changes
        if self.geo_anomaly_detection:
            recent_sessions = await self.get_active_sessions(user_id)
            for session in recent_sessions[-5:]:  # Last 5 sessions
                if session.device_info.ip_address != device_info.ip_address:
                    # TODO: Implement geo-location check
                    time_diff = (datetime.utcnow() - session.last_activity).total_seconds()
                    if time_diff < 300:  # 5 minutes
                        await security_monitor.log_event(SecurityEvent(
                            event_type=SecurityEventType.GEO_ANOMALY,
                            severity=SecurityEventSeverity.HIGH,
                            user_id=user_id,
                            ip_address=device_info.ip_address,
                            details={
                                "previous_ip": session.device_info.ip_address,
                                "time_difference": time_diff
                            }
                        ))
        
        # Check for new device
        known_devices = await self._get_known_devices(user_id)
        if device_info.device_id not in known_devices:
            await audit_logger.log(
                event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
                user_id=user_id,
                ip_address=device_info.ip_address,
                details={"reason": "new_device", "device_id": device_info.device_id}
            )
    
    async def _handle_ip_change(self, session: Session, new_ip: str):
        """Handle IP address change during session."""
        await security_monitor.log_event(SecurityEvent(
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            severity=SecurityEventSeverity.LOW,
            user_id=session.user_id,
            ip_address=new_ip,
            details={
                "session_id": session.session_id,
                "old_ip": session.device_info.ip_address,
                "new_ip": new_ip
            }
        ))
    
    async def _handle_device_change(self, session: Session, new_user_agent: str):
        """Handle device change during session."""
        # This is highly suspicious - possible session hijacking
        await security_monitor.log_event(SecurityEvent(
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            severity=SecurityEventSeverity.HIGH,
            user_id=session.user_id,
            ip_address=session.device_info.ip_address,
            details={
                "session_id": session.session_id,
                "reason": "user_agent_changed",
                "old_agent": session.device_info.user_agent,
                "new_agent": new_user_agent
            }
        ))
        
        # Optionally revoke session
        await self.revoke_session(session.session_id, "Device change detected")
    
    async def _track_device(self, user_id: str, device_info: DeviceInfo):
        """Track user devices."""
        device_key = f"user_devices:{user_id}"
        device_data = {
            "device_id": device_info.device_id,
            "last_seen": datetime.utcnow().isoformat(),
            "ip_address": device_info.ip_address,
            "platform": device_info.platform,
            "browser": device_info.browser
        }
        
        await cache_manager.hset(
            device_key,
            device_info.device_id,
            json.dumps(device_data)
        )
        await cache_manager.expire(device_key, 86400 * 90)  # 90 days
    
    async def _get_known_devices(self, user_id: str) -> Set[str]:
        """Get known device IDs for a user."""
        device_key = f"user_devices:{user_id}"
        devices = await cache_manager.hgetall(device_key)
        return set(devices.keys()) if devices else set()


# Global session manager instance
session_manager = SessionManager()