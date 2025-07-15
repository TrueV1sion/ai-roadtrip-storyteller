"""
Automated threat response system for immediate security actions.
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import json

from app.core.logger import get_logger
from app.core.cache import cache_manager
from app.monitoring.security_monitor import (
    security_monitor, SecurityEvent, SecurityEventType, SecurityEventSeverity
)
from app.security.intrusion_detection import intrusion_detection_system
from app.core.enhanced_rate_limiter import enhanced_rate_limiter
from app.services.session_manager import session_manager
from app.monitoring.audit_logger import audit_logger

logger = get_logger(__name__)


class ThreatResponseAction(Enum):
    """Types of automated response actions."""
    BLOCK_IP = "block_ip"
    TERMINATE_SESSION = "terminate_session"
    LOCK_ACCOUNT = "lock_account"
    INCREASE_MONITORING = "increase_monitoring"
    NOTIFY_ADMIN = "notify_admin"
    ENABLE_CAPTCHA = "enable_captcha"
    REDUCE_RATE_LIMITS = "reduce_rate_limits"
    ENABLE_EMERGENCY_MODE = "enable_emergency_mode"
    QUARANTINE_REQUEST = "quarantine_request"
    RESET_PASSWORD = "reset_password"


class ThreatLevel(Enum):
    """Threat severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ResponseRule:
    """Rule for automated threat response."""
    
    def __init__(
        self,
        name: str,
        condition: Callable[[SecurityEvent], bool],
        actions: List[ThreatResponseAction],
        threat_level: ThreatLevel,
        cooldown_minutes: int = 5
    ):
        self.name = name
        self.condition = condition
        self.actions = actions
        self.threat_level = threat_level
        self.cooldown_minutes = cooldown_minutes
        self.last_triggered = {}


class AutomatedThreatResponse:
    """Automated threat response system."""
    
    def __init__(self):
        self.rules = self._initialize_rules()
        self.response_history = []
        self.emergency_mode = False
        self.response_queue = asyncio.Queue()
        self._running = False
        self._response_worker = None
        
    def _initialize_rules(self) -> List[ResponseRule]:
        """Initialize threat response rules."""
        return [
            # Brute force attack detection
            ResponseRule(
                name="brute_force_response",
                condition=lambda e: (
                    e.event_type == SecurityEventType.LOGIN_FAILED and
                    e.details.get("attempt_count", 0) > 5
                ),
                actions=[
                    ThreatResponseAction.BLOCK_IP,
                    ThreatResponseAction.NOTIFY_ADMIN,
                    ThreatResponseAction.ENABLE_CAPTCHA
                ],
                threat_level=ThreatLevel.HIGH,
                cooldown_minutes=30
            ),
            
            # SQL injection attempt
            ResponseRule(
                name="sql_injection_response",
                condition=lambda e: (
                    e.event_type == SecurityEventType.SQL_INJECTION_ATTEMPT
                ),
                actions=[
                    ThreatResponseAction.BLOCK_IP,
                    ThreatResponseAction.QUARANTINE_REQUEST,
                    ThreatResponseAction.NOTIFY_ADMIN,
                    ThreatResponseAction.INCREASE_MONITORING
                ],
                threat_level=ThreatLevel.CRITICAL,
                cooldown_minutes=60
            ),
            
            # Suspicious session activity
            ResponseRule(
                name="suspicious_session_response",
                condition=lambda e: (
                    e.event_type == SecurityEventType.SUSPICIOUS_ACTIVITY and
                    e.details.get("risk_score", 0) > 80
                ),
                actions=[
                    ThreatResponseAction.TERMINATE_SESSION,
                    ThreatResponseAction.LOCK_ACCOUNT,
                    ThreatResponseAction.NOTIFY_ADMIN
                ],
                threat_level=ThreatLevel.HIGH,
                cooldown_minutes=15
            ),
            
            # Rate limit violations
            ResponseRule(
                name="rate_limit_abuse_response",
                condition=lambda e: (
                    e.event_type == SecurityEventType.RATE_LIMIT_EXCEEDED and
                    e.details.get("violations_count", 0) > 10
                ),
                actions=[
                    ThreatResponseAction.BLOCK_IP,
                    ThreatResponseAction.REDUCE_RATE_LIMITS
                ],
                threat_level=ThreatLevel.MEDIUM,
                cooldown_minutes=10
            ),
            
            # Concurrent session violations
            ResponseRule(
                name="concurrent_session_response",
                condition=lambda e: (
                    e.event_type == SecurityEventType.CONCURRENT_SESSION_LIMIT and
                    e.details.get("session_count", 0) > 10
                ),
                actions=[
                    ThreatResponseAction.TERMINATE_SESSION,
                    ThreatResponseAction.LOCK_ACCOUNT,
                    ThreatResponseAction.NOTIFY_ADMIN
                ],
                threat_level=ThreatLevel.HIGH,
                cooldown_minutes=30
            ),
            
            # XSS attempt
            ResponseRule(
                name="xss_response",
                condition=lambda e: (
                    e.event_type == SecurityEventType.XSS_ATTEMPT
                ),
                actions=[
                    ThreatResponseAction.BLOCK_IP,
                    ThreatResponseAction.QUARANTINE_REQUEST,
                    ThreatResponseAction.INCREASE_MONITORING
                ],
                threat_level=ThreatLevel.HIGH,
                cooldown_minutes=30
            ),
            
            # Path traversal attempt
            ResponseRule(
                name="path_traversal_response",
                condition=lambda e: (
                    e.event_type == SecurityEventType.PATH_TRAVERSAL_ATTEMPT
                ),
                actions=[
                    ThreatResponseAction.BLOCK_IP,
                    ThreatResponseAction.NOTIFY_ADMIN
                ],
                threat_level=ThreatLevel.HIGH,
                cooldown_minutes=30
            ),
            
            # Emergency mode trigger
            ResponseRule(
                name="emergency_mode_trigger",
                condition=lambda e: (
                    e.severity == SecurityEventSeverity.CRITICAL and
                    e.details.get("attack_pattern", "") == "coordinated"
                ),
                actions=[
                    ThreatResponseAction.ENABLE_EMERGENCY_MODE,
                    ThreatResponseAction.NOTIFY_ADMIN,
                    ThreatResponseAction.REDUCE_RATE_LIMITS
                ],
                threat_level=ThreatLevel.CRITICAL,
                cooldown_minutes=60
            )
        ]
    
    async def start(self):
        """Start the automated threat response system."""
        if self._running:
            return
        
        self._running = True
        self._response_worker = asyncio.create_task(self._process_responses())
        
        # Subscribe to security events
        security_monitor.subscribe(self._handle_security_event)
        
        logger.info("Automated threat response system started")
    
    async def stop(self):
        """Stop the automated threat response system."""
        self._running = False
        
        if self._response_worker:
            await self.response_queue.put(None)  # Signal to stop
            await self._response_worker
        
        logger.info("Automated threat response system stopped")
    
    async def _handle_security_event(self, event: SecurityEvent):
        """Handle incoming security events."""
        try:
            # Check all rules
            for rule in self.rules:
                if await self._should_trigger_rule(rule, event):
                    await self.response_queue.put({
                        "rule": rule,
                        "event": event,
                        "timestamp": datetime.utcnow()
                    })
        except Exception as e:
            logger.error(f"Error handling security event: {e}")
    
    async def _should_trigger_rule(self, rule: ResponseRule, event: SecurityEvent) -> bool:
        """Check if a rule should be triggered."""
        # Check condition
        if not rule.condition(event):
            return False
        
        # Check cooldown
        key = f"{rule.name}:{event.user_id or event.ip_address}"
        if key in rule.last_triggered:
            last_time = rule.last_triggered[key]
            if datetime.utcnow() - last_time < timedelta(minutes=rule.cooldown_minutes):
                return False
        
        # Update last triggered time
        rule.last_triggered[key] = datetime.utcnow()
        
        return True
    
    async def _process_responses(self):
        """Process queued threat responses."""
        while self._running:
            try:
                # Get next response
                response_data = await self.response_queue.get()
                
                if response_data is None:  # Stop signal
                    break
                
                # Execute response actions
                await self._execute_response(
                    response_data["rule"],
                    response_data["event"]
                )
                
            except Exception as e:
                logger.error(f"Error processing threat response: {e}")
    
    async def _execute_response(self, rule: ResponseRule, event: SecurityEvent):
        """Execute automated response actions."""
        logger.info(
            f"Executing automated response '{rule.name}' "
            f"for event {event.event_type.value}"
        )
        
        response_record = {
            "rule_name": rule.name,
            "event_id": event.id,
            "event_type": event.event_type.value,
            "threat_level": rule.threat_level.value,
            "actions": [],
            "timestamp": datetime.utcnow(),
            "success": True
        }
        
        # Execute each action
        for action in rule.actions:
            try:
                result = await self._execute_action(action, event)
                response_record["actions"].append({
                    "action": action.value,
                    "result": result,
                    "success": True
                })
            except Exception as e:
                logger.error(f"Failed to execute action {action.value}: {e}")
                response_record["actions"].append({
                    "action": action.value,
                    "error": str(e),
                    "success": False
                })
                response_record["success"] = False
        
        # Record response
        self.response_history.append(response_record)
        
        # Log to audit trail
        await audit_logger.log(
            action="automated_threat_response",
            user_id=event.user_id,
            resource_type="security",
            resource_id=event.id,
            details=response_record
        )
    
    async def _execute_action(
        self,
        action: ThreatResponseAction,
        event: SecurityEvent
    ) -> Dict[str, Any]:
        """Execute a specific response action."""
        if action == ThreatResponseAction.BLOCK_IP:
            return await self._block_ip(event.ip_address, event)
        
        elif action == ThreatResponseAction.TERMINATE_SESSION:
            return await self._terminate_session(event.user_id, event)
        
        elif action == ThreatResponseAction.LOCK_ACCOUNT:
            return await self._lock_account(event.user_id, event)
        
        elif action == ThreatResponseAction.INCREASE_MONITORING:
            return await self._increase_monitoring(event)
        
        elif action == ThreatResponseAction.NOTIFY_ADMIN:
            return await self._notify_admin(event)
        
        elif action == ThreatResponseAction.ENABLE_CAPTCHA:
            return await self._enable_captcha(event)
        
        elif action == ThreatResponseAction.REDUCE_RATE_LIMITS:
            return await self._reduce_rate_limits(event)
        
        elif action == ThreatResponseAction.ENABLE_EMERGENCY_MODE:
            return await self._enable_emergency_mode(event)
        
        elif action == ThreatResponseAction.QUARANTINE_REQUEST:
            return await self._quarantine_request(event)
        
        elif action == ThreatResponseAction.RESET_PASSWORD:
            return await self._reset_password(event.user_id, event)
        
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _block_ip(self, ip_address: str, event: SecurityEvent) -> Dict[str, Any]:
        """Block an IP address."""
        if not ip_address:
            return {"error": "No IP address to block"}
        
        # Block in IDS
        await intrusion_detection_system.block_ip(
            ip_address,
            reason=f"Automated response to {event.event_type.value}",
            duration=3600  # 1 hour default
        )
        
        # Block in rate limiter
        await enhanced_rate_limiter._block_key(f"ip:{ip_address}", 3600)
        
        logger.warning(f"Blocked IP {ip_address} due to {event.event_type.value}")
        
        return {
            "ip_address": ip_address,
            "duration": 3600,
            "reason": event.event_type.value
        }
    
    async def _terminate_session(self, user_id: str, event: SecurityEvent) -> Dict[str, Any]:
        """Terminate user sessions."""
        if not user_id:
            return {"error": "No user ID for session termination"}
        
        # Get all user sessions
        sessions = await session_manager.get_user_sessions(user_id)
        terminated = []
        
        for session in sessions:
            await session_manager.revoke_session(
                session["session_id"],
                reason=f"Automated response to {event.event_type.value}"
            )
            terminated.append(session["session_id"])
        
        logger.warning(
            f"Terminated {len(terminated)} sessions for user {user_id} "
            f"due to {event.event_type.value}"
        )
        
        return {
            "user_id": user_id,
            "sessions_terminated": len(terminated),
            "session_ids": terminated
        }
    
    async def _lock_account(self, user_id: str, event: SecurityEvent) -> Dict[str, Any]:
        """Lock a user account."""
        if not user_id:
            return {"error": "No user ID for account lock"}
        
        # Lock account
        lock_key = f"account_locked:{user_id}"
        await cache_manager.set(
            lock_key,
            json.dumps({
                "reason": event.event_type.value,
                "locked_at": datetime.utcnow().isoformat(),
                "event_id": event.id
            }),
            ttl=3600  # 1 hour lock
        )
        
        # Terminate all sessions
        await self._terminate_session(user_id, event)
        
        logger.warning(f"Locked account {user_id} due to {event.event_type.value}")
        
        return {
            "user_id": user_id,
            "lock_duration": 3600,
            "reason": event.event_type.value
        }
    
    async def _increase_monitoring(self, event: SecurityEvent) -> Dict[str, Any]:
        """Increase monitoring for user or IP."""
        target = event.user_id or event.ip_address
        if not target:
            return {"error": "No target for increased monitoring"}
        
        # Set high priority monitoring flag
        monitor_key = f"high_priority_monitor:{target}"
        await cache_manager.set(
            monitor_key,
            json.dumps({
                "reason": event.event_type.value,
                "started_at": datetime.utcnow().isoformat(),
                "event_id": event.id
            }),
            ttl=7200  # 2 hours
        )
        
        logger.info(f"Increased monitoring for {target} due to {event.event_type.value}")
        
        return {
            "target": target,
            "duration": 7200,
            "monitoring_level": "high"
        }
    
    async def _notify_admin(self, event: SecurityEvent) -> Dict[str, Any]:
        """Send notification to administrators."""
        notification = {
            "type": "security_alert",
            "severity": event.severity.value,
            "event_type": event.event_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            "details": {
                "event_id": event.id,
                "user_id": event.user_id,
                "ip_address": event.ip_address,
                "description": event.details.get("description", "Security event detected")
            }
        }
        
        # Queue notification (would send to notification service)
        await cache_manager.lpush("admin_notifications", json.dumps(notification))
        
        logger.info(f"Admin notification sent for {event.event_type.value}")
        
        return {
            "notification_sent": True,
            "severity": event.severity.value
        }
    
    async def _enable_captcha(self, event: SecurityEvent) -> Dict[str, Any]:
        """Enable CAPTCHA for IP or user."""
        target = event.ip_address or f"user:{event.user_id}"
        if not target:
            return {"error": "No target for CAPTCHA"}
        
        # Enable CAPTCHA requirement
        captcha_key = f"captcha_required:{target}"
        await cache_manager.set(
            captcha_key,
            json.dumps({
                "reason": event.event_type.value,
                "enabled_at": datetime.utcnow().isoformat(),
                "event_id": event.id
            }),
            ttl=1800  # 30 minutes
        )
        
        logger.info(f"CAPTCHA enabled for {target} due to {event.event_type.value}")
        
        return {
            "target": target,
            "duration": 1800,
            "captcha_enabled": True
        }
    
    async def _reduce_rate_limits(self, event: SecurityEvent) -> Dict[str, Any]:
        """Reduce rate limits during attack."""
        # Apply dynamic rate limit adjustment
        enhanced_rate_limiter.set_dynamic_adjustment("attack_detected", 0.2)
        
        logger.warning("Rate limits reduced to 20% due to detected attack")
        
        return {
            "adjustment_factor": 0.2,
            "reason": event.event_type.value
        }
    
    async def _enable_emergency_mode(self, event: SecurityEvent) -> Dict[str, Any]:
        """Enable emergency security mode."""
        self.emergency_mode = True
        
        # Set emergency mode flag
        await cache_manager.set(
            "security_emergency_mode",
            json.dumps({
                "enabled": True,
                "reason": event.event_type.value,
                "enabled_at": datetime.utcnow().isoformat(),
                "event_id": event.id
            }),
            ttl=3600  # 1 hour
        )
        
        # Apply strict rate limits
        enhanced_rate_limiter.set_dynamic_adjustment("emergency_mode", 0.1)
        
        # Notify all admins
        await self._notify_admin(event)
        
        logger.critical(f"EMERGENCY MODE ENABLED due to {event.event_type.value}")
        
        return {
            "emergency_mode": True,
            "restrictions": ["rate_limits_10%", "enhanced_monitoring", "admin_notified"]
        }
    
    async def _quarantine_request(self, event: SecurityEvent) -> Dict[str, Any]:
        """Quarantine suspicious request data."""
        quarantine_data = {
            "event_id": event.id,
            "event_type": event.event_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": event.user_id,
            "ip_address": event.ip_address,
            "request_data": event.details.get("request_data", {}),
            "threat_indicators": event.details.get("threat_indicators", [])
        }
        
        # Store in quarantine
        quarantine_key = f"quarantine:{event.id}"
        await cache_manager.set(
            quarantine_key,
            json.dumps(quarantine_data),
            ttl=86400  # 24 hours
        )
        
        logger.warning(f"Request quarantined: {event.id}")
        
        return {
            "quarantine_id": event.id,
            "retention": 86400
        }
    
    async def _reset_password(self, user_id: str, event: SecurityEvent) -> Dict[str, Any]:
        """Force password reset for user."""
        if not user_id:
            return {"error": "No user ID for password reset"}
        
        # Set password reset flag
        reset_key = f"force_password_reset:{user_id}"
        await cache_manager.set(
            reset_key,
            json.dumps({
                "reason": event.event_type.value,
                "required_at": datetime.utcnow().isoformat(),
                "event_id": event.id
            }),
            ttl=None  # No expiry until password is reset
        )
        
        # Terminate all sessions
        await self._terminate_session(user_id, event)
        
        logger.warning(f"Password reset required for user {user_id}")
        
        return {
            "user_id": user_id,
            "password_reset_required": True,
            "sessions_terminated": True
        }
    
    async def get_response_history(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get automated response history."""
        history = self.response_history
        
        # Filter by time range
        if start_time:
            history = [h for h in history if h["timestamp"] >= start_time]
        if end_time:
            history = [h for h in history if h["timestamp"] <= end_time]
        
        # Sort by timestamp descending
        history.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return history[:limit]
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get automated response statistics."""
        total_responses = len(self.response_history)
        successful_responses = sum(1 for r in self.response_history if r["success"])
        
        # Count by threat level
        by_threat_level = {}
        for response in self.response_history:
            level = response["threat_level"]
            by_threat_level[level] = by_threat_level.get(level, 0) + 1
        
        # Count by action type
        by_action = {}
        for response in self.response_history:
            for action_result in response["actions"]:
                action = action_result["action"]
                by_action[action] = by_action.get(action, 0) + 1
        
        return {
            "total_responses": total_responses,
            "successful_responses": successful_responses,
            "success_rate": successful_responses / total_responses if total_responses > 0 else 0,
            "emergency_mode": self.emergency_mode,
            "by_threat_level": by_threat_level,
            "by_action_type": by_action,
            "active_rules": len(self.rules)
        }
    
    async def test_rule(self, rule_name: str, test_event: SecurityEvent) -> Dict[str, Any]:
        """Test a specific rule with a test event."""
        rule = next((r for r in self.rules if r.name == rule_name), None)
        if not rule:
            return {"error": f"Rule '{rule_name}' not found"}
        
        # Check if rule would trigger
        would_trigger = rule.condition(test_event)
        
        # Simulate actions
        simulated_actions = []
        if would_trigger:
            for action in rule.actions:
                simulated_actions.append({
                    "action": action.value,
                    "description": f"Would execute: {action.value}"
                })
        
        return {
            "rule_name": rule_name,
            "would_trigger": would_trigger,
            "threat_level": rule.threat_level.value,
            "simulated_actions": simulated_actions
        }


# Global instance
automated_threat_response = AutomatedThreatResponse()