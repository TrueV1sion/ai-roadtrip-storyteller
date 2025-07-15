"""
Security audit logging system for tracking all security-relevant actions.
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import hashlib
import hmac
from pathlib import Path

from sqlalchemy import Column, String, DateTime, JSON, Index, Boolean, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.core.config import settings
from app.db.base import Base
from app.models.user import User

logger = get_logger(__name__)


class AuditEventType(Enum):
    """Types of audit events."""
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"
    
    # 2FA events
    TWO_FACTOR_ENABLED = "2fa_enabled"
    TWO_FACTOR_DISABLED = "2fa_disabled"
    TWO_FACTOR_SUCCESS = "2fa_success"
    TWO_FACTOR_FAILURE = "2fa_failure"
    TWO_FACTOR_BACKUP_USED = "2fa_backup_used"
    
    # Account events
    ACCOUNT_CREATED = "account_created"
    ACCOUNT_UPDATED = "account_updated"
    ACCOUNT_DELETED = "account_deleted"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    
    # Permission events
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_REVOKED = "permission_revoked"
    ROLE_CHANGED = "role_changed"
    
    # Data access events
    DATA_ACCESSED = "data_accessed"
    DATA_MODIFIED = "data_modified"
    DATA_DELETED = "data_deleted"
    DATA_EXPORTED = "data_exported"
    
    # API events
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    API_RATE_LIMIT = "api_rate_limit"
    
    # Security events
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    SECURITY_ALERT = "security_alert"
    IP_BLOCKED = "ip_blocked"
    INTRUSION_DETECTED = "intrusion_detected"
    
    # System events
    CONFIG_CHANGED = "config_changed"
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    BACKUP_CREATED = "backup_created"
    BACKUP_RESTORED = "backup_restored"


class AuditLog(Base):
    """Database model for audit logs."""
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    user_id = Column(String, index=True)
    ip_address = Column(String, index=True)
    user_agent = Column(String)
    session_id = Column(String, index=True)
    resource_type = Column(String)
    resource_id = Column(String)
    action = Column(String)
    result = Column(String)  # success, failure, error
    details = Column(JSON)
    risk_score = Column(Integer, default=0)
    
    # Audit trail integrity
    previous_hash = Column(String)
    hash = Column(String, nullable=False)
    
    # Compliance fields
    data_classification = Column(String)  # public, internal, confidential, restricted
    compliance_tags = Column(JSON)  # GDPR, HIPAA, PCI-DSS, etc.
    retention_days = Column(Integer, default=365)
    
    # Indexing for common queries
    __table_args__ = (
        Index("idx_audit_user_time", "user_id", "timestamp"),
        Index("idx_audit_event_time", "event_type", "timestamp"),
        Index("idx_audit_ip_time", "ip_address", "timestamp"),
        Index("idx_audit_session", "session_id"),
    )


class AuditLogger:
    """Main audit logging service."""
    
    def __init__(self):
        self.queue = asyncio.Queue(maxsize=1000)
        self.is_running = False
        self.batch_size = 100
        self.flush_interval = 5  # seconds
        
        # HMAC key for audit log integrity
        self.hmac_key = settings.AUDIT_HMAC_KEY or settings.SECRET_KEY.encode()
    
    async def start(self):
        """Start the audit logging service."""
        self.is_running = True
        logger.info("Audit logging service started")
        
        # Start background tasks
        asyncio.create_task(self._process_queue())
        asyncio.create_task(self._periodic_flush())
        
        # Log system startup
        await self.log(
            event_type=AuditEventType.SYSTEM_STARTUP,
            details={"version": settings.APP_VERSION}
        )
    
    async def stop(self):
        """Stop the audit logging service."""
        # Log system shutdown
        await self.log(
            event_type=AuditEventType.SYSTEM_SHUTDOWN,
            details={"uptime": self._get_uptime()}
        )
        
        # Flush remaining logs
        await self._flush_queue()
        
        self.is_running = False
        logger.info("Audit logging service stopped")
    
    async def log(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[str] = None,
        result: str = "success",
        details: Optional[Dict[str, Any]] = None,
        data_classification: Optional[str] = None,
        compliance_tags: Optional[List[str]] = None,
        risk_score: int = 0
    ):
        """Log an audit event."""
        try:
            # Create audit entry
            audit_entry = {
                "id": self._generate_id(),
                "timestamp": datetime.utcnow(),
                "event_type": event_type.value,
                "user_id": user_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "session_id": session_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "action": action,
                "result": result,
                "details": details or {},
                "data_classification": data_classification or "internal",
                "compliance_tags": compliance_tags or [],
                "risk_score": risk_score,
                "retention_days": self._get_retention_days(event_type)
            }
            
            # Add to queue
            await self.queue.put(audit_entry)
            
            # Log high-risk events immediately
            if risk_score >= 8:
                logger.warning(f"High-risk audit event: {audit_entry}")
            
        except asyncio.QueueFull:
            # If queue is full, log directly (fallback)
            logger.error(f"Audit queue full, logging directly: {event_type.value}")
            await self._write_audit_log([audit_entry])
        except Exception as e:
            logger.error(f"Error logging audit event: {e}")
    
    async def log_data_access(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        fields_accessed: Optional[List[str]] = None,
        **kwargs
    ):
        """Log data access for compliance."""
        details = {
            "fields_accessed": fields_accessed or [],
            "access_time": datetime.utcnow().isoformat()
        }
        
        await self.log(
            event_type=AuditEventType.DATA_ACCESSED,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details,
            **kwargs
        )
    
    async def log_authentication(
        self,
        user_id: Optional[str],
        success: bool,
        method: str,
        ip_address: str,
        user_agent: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log authentication attempts."""
        event_type = AuditEventType.LOGIN_SUCCESS if success else AuditEventType.LOGIN_FAILURE
        risk_score = 0 if success else 3
        
        # Increase risk for multiple failures
        if not success and details and details.get("attempt_count", 0) > 3:
            risk_score = 6
        
        await self.log(
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            result="success" if success else "failure",
            details={**details, "method": method} if details else {"method": method},
            risk_score=risk_score
        )
    
    async def log_permission_change(
        self,
        admin_user_id: str,
        target_user_id: str,
        permission_type: str,
        old_value: Any,
        new_value: Any,
        **kwargs
    ):
        """Log permission changes."""
        details = {
            "admin_user": admin_user_id,
            "permission_type": permission_type,
            "old_value": old_value,
            "new_value": new_value,
            "changed_at": datetime.utcnow().isoformat()
        }
        
        event_type = (
            AuditEventType.PERMISSION_GRANTED 
            if new_value and not old_value 
            else AuditEventType.PERMISSION_REVOKED
        )
        
        await self.log(
            event_type=event_type,
            user_id=target_user_id,
            resource_type="user",
            resource_id=target_user_id,
            details=details,
            risk_score=5,  # Permission changes are medium risk
            compliance_tags=["access_control"],
            **kwargs
        )
    
    async def query_logs(
        self,
        db: Session,
        event_types: Optional[List[AuditEventType]] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """Query audit logs with filters."""
        query = db.query(AuditLog)
        
        if event_types:
            query = query.filter(
                AuditLog.event_type.in_([e.value for e in event_types])
            )
        
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        
        if ip_address:
            query = query.filter(AuditLog.ip_address == ip_address)
        
        if start_time:
            query = query.filter(AuditLog.timestamp >= start_time)
        
        if end_time:
            query = query.filter(AuditLog.timestamp <= end_time)
        
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        
        if resource_id:
            query = query.filter(AuditLog.resource_id == resource_id)
        
        return query.order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset).all()
    
    async def generate_compliance_report(
        self,
        db: Session,
        compliance_type: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate compliance report for auditors."""
        # Query relevant logs
        logs = await self.query_logs(
            db=db,
            start_time=start_date,
            end_time=end_date
        )
        
        report = {
            "compliance_type": compliance_type,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_events": len(logs),
                "authentication_events": 0,
                "data_access_events": 0,
                "permission_changes": 0,
                "security_incidents": 0
            },
            "details": []
        }
        
        # Process logs for report
        for log in logs:
            if log.event_type in ["login_success", "login_failure"]:
                report["summary"]["authentication_events"] += 1
            elif log.event_type in ["data_accessed", "data_modified"]:
                report["summary"]["data_access_events"] += 1
            elif log.event_type in ["permission_granted", "permission_revoked"]:
                report["summary"]["permission_changes"] += 1
            elif log.risk_score >= 6:
                report["summary"]["security_incidents"] += 1
            
            # Add to details if matches compliance tags
            if compliance_type in (log.compliance_tags or []):
                report["details"].append(log.to_dict())
        
        return report
    
    async def verify_integrity(
        self,
        db: Session,
        start_id: Optional[str] = None,
        end_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verify audit log integrity using hash chain."""
        query = db.query(AuditLog).order_by(AuditLog.timestamp)
        
        if start_id:
            query = query.filter(AuditLog.id >= start_id)
        if end_id:
            query = query.filter(AuditLog.id <= end_id)
        
        logs = query.all()
        
        valid_count = 0
        invalid_logs = []
        previous_hash = None
        
        for log in logs:
            # Verify hash
            computed_hash = self._compute_hash(log, previous_hash)
            
            if computed_hash == log.hash:
                valid_count += 1
                previous_hash = log.hash
            else:
                invalid_logs.append({
                    "id": log.id,
                    "timestamp": log.timestamp.isoformat(),
                    "expected_hash": computed_hash,
                    "actual_hash": log.hash
                })
        
        return {
            "total_logs": len(logs),
            "valid_logs": valid_count,
            "invalid_logs": len(invalid_logs),
            "integrity": len(invalid_logs) == 0,
            "invalid_details": invalid_logs[:10]  # Limit details
        }
    
    def _generate_id(self) -> str:
        """Generate unique audit log ID."""
        timestamp = datetime.utcnow().timestamp()
        random_part = hashlib.sha256(
            f"{timestamp}{id(self)}".encode()
        ).hexdigest()[:8]
        return f"audit_{int(timestamp)}_{random_part}"
    
    def _compute_hash(self, log_data: Union[Dict, AuditLog], previous_hash: Optional[str] = None) -> str:
        """Compute cryptographic hash for audit log."""
        if isinstance(log_data, AuditLog):
            # Convert to dict for hashing
            data = {
                "id": log_data.id,
                "timestamp": log_data.timestamp.isoformat(),
                "event_type": log_data.event_type,
                "user_id": log_data.user_id,
                "resource_type": log_data.resource_type,
                "resource_id": log_data.resource_id,
                "result": log_data.result
            }
        else:
            data = log_data
        
        # Include previous hash for chain integrity
        if previous_hash:
            data["previous_hash"] = previous_hash
        
        # Create HMAC
        message = json.dumps(data, sort_keys=True).encode()
        return hmac.new(self.hmac_key, message, hashlib.sha256).hexdigest()
    
    def _get_retention_days(self, event_type: AuditEventType) -> int:
        """Get retention period based on event type."""
        # Compliance-critical events retained longer
        long_retention_events = [
            AuditEventType.PERMISSION_GRANTED,
            AuditEventType.PERMISSION_REVOKED,
            AuditEventType.ROLE_CHANGED,
            AuditEventType.DATA_DELETED,
            AuditEventType.ACCOUNT_DELETED,
            AuditEventType.SECURITY_ALERT,
            AuditEventType.INTRUSION_DETECTED
        ]
        
        if event_type in long_retention_events:
            return 2555  # 7 years
        
        return 365  # 1 year default
    
    def _get_uptime(self) -> str:
        """Get system uptime."""
        # TODO: Implement actual uptime calculation
        return "Unknown"
    
    async def _process_queue(self):
        """Process audit log queue in batches."""
        batch = []
        
        while self.is_running:
            try:
                # Get item with timeout
                item = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=1.0
                )
                batch.append(item)
                
                # Write batch if full
                if len(batch) >= self.batch_size:
                    await self._write_audit_log(batch)
                    batch = []
                
            except asyncio.TimeoutError:
                # Timeout - write partial batch if exists
                if batch:
                    await self._write_audit_log(batch)
                    batch = []
            except Exception as e:
                logger.error(f"Error processing audit queue: {e}")
    
    async def _periodic_flush(self):
        """Periodically flush audit logs."""
        while self.is_running:
            await asyncio.sleep(self.flush_interval)
            await self._flush_queue()
    
    async def _flush_queue(self):
        """Flush all pending audit logs."""
        batch = []
        
        while not self.queue.empty():
            try:
                batch.append(self.queue.get_nowait())
                if len(batch) >= self.batch_size:
                    await self._write_audit_log(batch)
                    batch = []
            except asyncio.QueueEmpty:
                break
        
        if batch:
            await self._write_audit_log(batch)
    
    async def _write_audit_log(self, entries: List[Dict[str, Any]]):
        """Write audit log entries to storage."""
        try:
            # TODO: Implement actual database writing
            # For now, just log to file
            for entry in entries:
                logger.info(f"AUDIT: {json.dumps(entry, default=str)}")
        except Exception as e:
            logger.error(f"Error writing audit logs: {e}")


# Global audit logger instance
audit_logger = AuditLogger()