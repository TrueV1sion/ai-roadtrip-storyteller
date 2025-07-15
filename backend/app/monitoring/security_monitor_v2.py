"""
Production Security Monitor - Real-time security event monitoring and analysis.
Tracks authentication, authorization, and suspicious activity patterns.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import hashlib
import re
from dataclasses import dataclass, asdict
import ipaddress

from app.core.logger import get_logger
from app.core.cache import cache_manager
from app.monitoring.audit_logger import audit_logger
from app.monitoring.security_metrics import security_metrics
from app.core.config import settings

logger = get_logger(__name__)


class SecurityEventType(Enum):
    """Types of security events to monitor."""
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"
    ACCOUNT_LOCKOUT = "account_lockout"
    TWO_FACTOR_SUCCESS = "2fa_success"
    TWO_FACTOR_FAILURE = "2fa_failure"
    
    # Authorization events
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    PERMISSION_DENIED = "permission_denied"
    
    # Suspicious activity
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
    XSS_ATTEMPT = "xss_attempt"
    PATH_TRAVERSAL_ATTEMPT = "path_traversal_attempt"
    CSRF_VIOLATION = "csrf_violation"
    
    # API security
    INVALID_API_KEY = "invalid_api_key"
    API_ABUSE = "api_abuse"
    
    # System events
    SECURITY_CONFIG_CHANGE = "security_config_change"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"
    INTRUSION_DETECTED = "intrusion_detected"


class ThreatLevel(Enum):
    """Threat level classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    """Security event data structure."""
    event_id: str
    event_type: SecurityEventType
    timestamp: datetime
    user_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    endpoint: Optional[str]
    threat_level: ThreatLevel
    details: Dict[str, Any]
    metadata: Dict[str, Any]


class SecurityMonitorV2:
    """Production-grade security monitoring system."""
    
    def __init__(self):
        self.active = False
        self._events_queue: deque = deque(maxlen=10000)  # In-memory event buffer
        self._threat_scores: Dict[str, float] = defaultdict(float)  # IP -> threat score
        self._user_activity: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))  # User -> recent events
        self._blocked_ips: Set[str] = set()
        self._blocked_users: Set[str] = set()
        
        # Pattern detection
        self.suspicious_patterns = {
            'sql_injection': [
                r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b.*\b(from|where|table)\b)",
                r"(;|'|--|\/\*|\*\/|xp_|sp_)",
                r"(\b(cast|convert|concat|substring|ascii|char|exec)\s*\()"
            ],
            'xss': [
                r"(<script[^>]*>|<\/script>|javascript:|onerror=|onload=|onclick=|onmouseover=)",
                r"(document\.(cookie|write)|window\.location|eval\s*\()",
                r"(<iframe|<object|<embed|<img\s+src.*=)"
            ],
            'path_traversal': [
                r"(\.\.\/|\.\.\\|%2e%2e%2f|%2e%2e\/|\.\.%2f|%2e%2e%5c)",
                r"(\/etc\/passwd|\/windows\/system32|\/proc\/self)"
            ],
            'command_injection': [
                r"(;|\||&|`|\$\(|\$\{).*?(ls|cat|grep|find|wget|curl|nc|netcat)",
                r"(system\s*\(|exec\s*\(|shell_exec|passthru|popen)"
            ]
        }
        
        # Thresholds
        self.thresholds = {
            'failed_login_attempts': 5,  # Before lockout
            'rate_limit_requests': 100,  # Per minute
            'suspicious_events': 10,  # Before blocking
            'threat_score_block': 100.0  # Auto-block threshold
        }
        
        # Background tasks
        self._cleanup_task = None
        self._analysis_task = None
        
        logger.info("Security Monitor V2 initialized")
    
    async def start(self):
        """Start security monitoring with background tasks."""
        self.active = True
        
        # Start background tasks
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._analysis_task = asyncio.create_task(self._analysis_loop())
        
        # Load blocked IPs/users from cache
        await self._load_blocklists()
        
        logger.info("Security Monitor V2 started")
    
    async def stop(self):
        """Stop security monitoring and cleanup."""
        self.active = False
        
        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._analysis_task:
            self._analysis_task.cancel()
        
        # Save state to cache
        await self._save_blocklists()
        
        logger.info("Security Monitor V2 stopped")
    
    async def log_event(
        self,
        event_type: SecurityEventType,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SecurityEvent:
        """Log a security event and analyze threat level."""
        # Generate event ID
        event_id = self._generate_event_id(event_type, user_id, ip_address)
        
        # Analyze threat level
        threat_level = self._analyze_threat_level(
            event_type, details or {}, ip_address, user_id
        )
        
        # Create event
        event = SecurityEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            threat_level=threat_level,
            details=details or {},
            metadata=metadata or {}
        )
        
        # Add to queue
        self._events_queue.append(event)
        
        # Update tracking
        if ip_address:
            self._update_threat_score(ip_address, event)
        if user_id:
            self._user_activity[user_id].append(event)
        
        # Check for immediate action needed
        await self._check_immediate_action(event)
        
        # Log to audit trail
        await audit_logger.log_audit_event(
            event_type=event_type.value,
            user_id=user_id,
            details={
                "ip_address": ip_address,
                "endpoint": endpoint,
                "threat_level": threat_level.value,
                **details
            } if details else {}
        )
        
        # Update metrics
        await security_metrics.record_security_event(event_type.value, threat_level.value)
        
        return event
    
    def check_patterns(self, text: str) -> List[Dict[str, Any]]:
        """Check text for suspicious patterns."""
        detected = []
        
        for pattern_type, patterns in self.suspicious_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    detected.append({
                        'type': pattern_type,
                        'pattern': pattern,
                        'severity': 'high' if pattern_type in ['sql_injection', 'command_injection'] else 'medium'
                    })
        
        return detected
    
    async def analyze_request(
        self,
        request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze request for security threats."""
        threats = []
        threat_score = 0
        
        # Extract request components
        path = request_data.get('path', '')
        query_params = request_data.get('query_params', {})
        headers = request_data.get('headers', {})
        body = request_data.get('body', '')
        ip_address = request_data.get('ip_address')
        
        # Check path
        path_threats = self.check_patterns(path)
        if path_threats:
            threats.extend(path_threats)
            threat_score += len(path_threats) * 20
        
        # Check query parameters
        for key, value in query_params.items():
            param_threats = self.check_patterns(f"{key}={value}")
            if param_threats:
                threats.extend(param_threats)
                threat_score += len(param_threats) * 15
        
        # Check headers
        suspicious_headers = ['x-forwarded-for', 'x-real-ip', 'x-originating-ip']
        for header in suspicious_headers:
            if header in headers:
                # Check for IP spoofing attempts
                threat_score += 10
        
        # Check body
        if body:
            body_threats = self.check_patterns(str(body))
            if body_threats:
                threats.extend(body_threats)
                threat_score += len(body_threats) * 25
        
        # Check if IP is blocked
        if ip_address and ip_address in self._blocked_ips:
            threats.append({'type': 'blocked_ip', 'severity': 'critical'})
            threat_score += 100
        
        # Determine overall threat level
        if threat_score >= 100:
            threat_level = ThreatLevel.CRITICAL
        elif threat_score >= 50:
            threat_level = ThreatLevel.HIGH
        elif threat_score >= 20:
            threat_level = ThreatLevel.MEDIUM
        else:
            threat_level = ThreatLevel.LOW
        
        return {
            'threat_level': threat_level.value,
            'threat_score': threat_score,
            'threats': threats,
            'blocked': ip_address in self._blocked_ips if ip_address else False,
            'recommendation': self._get_recommendation(threat_level, threats)
        }
    
    async def get_threat_intelligence(
        self,
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get threat intelligence for IP or user."""
        intelligence = {
            'threat_score': 0,
            'risk_level': 'low',
            'recent_events': [],
            'patterns': [],
            'recommendations': []
        }
        
        if ip_address:
            # Get IP threat score
            intelligence['threat_score'] = self._threat_scores.get(ip_address, 0)
            
            # Get recent events from this IP
            recent_events = [
                event for event in self._events_queue
                if event.ip_address == ip_address
            ][-10:]  # Last 10 events
            
            intelligence['recent_events'] = [
                {
                    'type': event.event_type.value,
                    'timestamp': event.timestamp.isoformat(),
                    'threat_level': event.threat_level.value
                }
                for event in recent_events
            ]
            
            # Analyze patterns
            event_types = [e.event_type for e in recent_events]
            if event_types.count(SecurityEventType.LOGIN_FAILURE) >= 3:
                intelligence['patterns'].append('multiple_failed_logins')
            if event_types.count(SecurityEventType.RATE_LIMIT_EXCEEDED) >= 2:
                intelligence['patterns'].append('rate_limit_abuse')
        
        if user_id:
            # Get user activity
            user_events = list(self._user_activity.get(user_id, []))[-10:]
            
            # Check for suspicious user patterns
            if any(e.event_type == SecurityEventType.PRIVILEGE_ESCALATION for e in user_events):
                intelligence['patterns'].append('privilege_escalation_attempt')
        
        # Determine risk level
        if intelligence['threat_score'] >= 100:
            intelligence['risk_level'] = 'critical'
        elif intelligence['threat_score'] >= 50:
            intelligence['risk_level'] = 'high'
        elif intelligence['threat_score'] >= 20:
            intelligence['risk_level'] = 'medium'
        
        # Add recommendations
        if intelligence['risk_level'] in ['high', 'critical']:
            intelligence['recommendations'].append('Consider blocking this IP')
        if 'multiple_failed_logins' in intelligence['patterns']:
            intelligence['recommendations'].append('Enable stricter rate limiting')
        
        return intelligence
    
    async def block_ip(self, ip_address: str, duration_seconds: int = 3600, reason: str = ""):
        """Block an IP address."""
        self._blocked_ips.add(ip_address)
        
        # Store in cache with expiration
        await cache_manager.set(
            f"blocked_ip:{ip_address}",
            {'reason': reason, 'blocked_at': datetime.utcnow().isoformat()},
            expire=duration_seconds
        )
        
        # Log event
        await self.log_event(
            SecurityEventType.INTRUSION_DETECTED,
            ip_address=ip_address,
            details={'action': 'ip_blocked', 'duration': duration_seconds, 'reason': reason}
        )
        
        logger.warning(f"Blocked IP {ip_address} for {duration_seconds} seconds. Reason: {reason}")
    
    async def unblock_ip(self, ip_address: str):
        """Unblock an IP address."""
        self._blocked_ips.discard(ip_address)
        await cache_manager.delete(f"blocked_ip:{ip_address}")
        
        logger.info(f"Unblocked IP {ip_address}")
    
    async def get_security_summary(self) -> Dict[str, Any]:
        """Get security monitoring summary."""
        now = datetime.utcnow()
        last_hour = now - timedelta(hours=1)
        last_24h = now - timedelta(hours=24)
        
        # Count events by type and time
        recent_events = list(self._events_queue)
        hour_events = [e for e in recent_events if e.timestamp >= last_hour]
        day_events = [e for e in recent_events if e.timestamp >= last_24h]
        
        # Count by threat level
        threat_levels_hour = defaultdict(int)
        threat_levels_day = defaultdict(int)
        event_types_hour = defaultdict(int)
        event_types_day = defaultdict(int)
        
        for event in hour_events:
            threat_levels_hour[event.threat_level.value] += 1
            event_types_hour[event.event_type.value] += 1
        
        for event in day_events:
            threat_levels_day[event.threat_level.value] += 1
            event_types_day[event.event_type.value] += 1
        
        return {
            'timestamp': now.isoformat(),
            'active': self.active,
            'last_hour': {
                'total_events': len(hour_events),
                'threat_levels': dict(threat_levels_hour),
                'event_types': dict(event_types_hour)
            },
            'last_24_hours': {
                'total_events': len(day_events),
                'threat_levels': dict(threat_levels_day),
                'event_types': dict(event_types_day)
            },
            'current_blocks': {
                'blocked_ips': len(self._blocked_ips),
                'blocked_users': len(self._blocked_users)
            },
            'high_threat_ips': [
                {'ip': ip, 'score': score}
                for ip, score in sorted(
                    self._threat_scores.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
                if score >= 50
            ]
        }
    
    # Private methods
    
    def _generate_event_id(self, event_type: SecurityEventType, user_id: Optional[str], ip_address: Optional[str]) -> str:
        """Generate unique event ID."""
        data = f"{event_type.value}:{user_id or ''}:{ip_address or ''}:{datetime.utcnow().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _analyze_threat_level(
        self,
        event_type: SecurityEventType,
        details: Dict[str, Any],
        ip_address: Optional[str],
        user_id: Optional[str]
    ) -> ThreatLevel:
        """Analyze and determine threat level for an event."""
        # Critical events
        critical_events = {
            SecurityEventType.SQL_INJECTION_ATTEMPT,
            SecurityEventType.COMMAND_INJECTION,
            SecurityEventType.PRIVILEGE_ESCALATION,
            SecurityEventType.INTRUSION_DETECTED
        }
        
        if event_type in critical_events:
            return ThreatLevel.CRITICAL
        
        # High threat events
        high_events = {
            SecurityEventType.XSS_ATTEMPT,
            SecurityEventType.PATH_TRAVERSAL_ATTEMPT,
            SecurityEventType.ACCOUNT_LOCKOUT,
            SecurityEventType.CSRF_VIOLATION
        }
        
        if event_type in high_events:
            return ThreatLevel.HIGH
        
        # Check IP threat score
        if ip_address and self._threat_scores.get(ip_address, 0) >= 50:
            return ThreatLevel.HIGH
        
        # Medium threat events
        medium_events = {
            SecurityEventType.LOGIN_FAILURE,
            SecurityEventType.RATE_LIMIT_EXCEEDED,
            SecurityEventType.UNAUTHORIZED_ACCESS,
            SecurityEventType.TWO_FACTOR_FAILURE
        }
        
        if event_type in medium_events:
            return ThreatLevel.MEDIUM
        
        return ThreatLevel.LOW
    
    def _update_threat_score(self, ip_address: str, event: SecurityEvent):
        """Update threat score for an IP based on event."""
        score_delta = {
            ThreatLevel.LOW: 1,
            ThreatLevel.MEDIUM: 5,
            ThreatLevel.HIGH: 20,
            ThreatLevel.CRITICAL: 50
        }
        
        self._threat_scores[ip_address] += score_delta.get(event.threat_level, 1)
        
        # Decay factor - reduce old scores
        self._threat_scores[ip_address] *= 0.95
    
    async def _check_immediate_action(self, event: SecurityEvent):
        """Check if immediate action is needed for an event."""
        # Auto-block critical threats
        if event.threat_level == ThreatLevel.CRITICAL and event.ip_address:
            await self.block_ip(
                event.ip_address,
                duration_seconds=3600,  # 1 hour
                reason=f"Critical security event: {event.event_type.value}"
            )
        
        # Check for brute force
        if event.event_type == SecurityEventType.LOGIN_FAILURE and event.user_id:
            # Count recent failures
            recent_failures = sum(
                1 for e in self._user_activity[event.user_id]
                if e.event_type == SecurityEventType.LOGIN_FAILURE
                and e.timestamp >= datetime.utcnow() - timedelta(minutes=10)
            )
            
            if recent_failures >= self.thresholds['failed_login_attempts']:
                await self.log_event(
                    SecurityEventType.ACCOUNT_LOCKOUT,
                    user_id=event.user_id,
                    ip_address=event.ip_address,
                    details={'failed_attempts': recent_failures}
                )
    
    def _get_recommendation(self, threat_level: ThreatLevel, threats: List[Dict[str, Any]]) -> str:
        """Get security recommendation based on threat analysis."""
        if threat_level == ThreatLevel.CRITICAL:
            return "Block request immediately"
        elif threat_level == ThreatLevel.HIGH:
            return "Challenge with additional verification"
        elif threat_level == ThreatLevel.MEDIUM:
            return "Monitor closely"
        else:
            return "Allow with standard monitoring"
    
    async def _cleanup_loop(self):
        """Background task to cleanup old data."""
        while self.active:
            try:
                # Cleanup old events (keep last 10000)
                # This is handled by deque maxlen
                
                # Decay threat scores
                for ip in list(self._threat_scores.keys()):
                    self._threat_scores[ip] *= 0.99  # Slow decay
                    if self._threat_scores[ip] < 1:
                        del self._threat_scores[ip]
                
                # Cleanup user activity older than 24 hours
                cutoff = datetime.utcnow() - timedelta(hours=24)
                for user_id in list(self._user_activity.keys()):
                    self._user_activity[user_id] = deque(
                        (e for e in self._user_activity[user_id] if e.timestamp >= cutoff),
                        maxlen=100
                    )
                
                await asyncio.sleep(300)  # Run every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in security monitor cleanup: {e}")
                await asyncio.sleep(60)
    
    async def _analysis_loop(self):
        """Background task to analyze patterns and trends."""
        while self.active:
            try:
                # Analyze recent events for patterns
                recent_events = list(self._events_queue)[-1000:]  # Last 1000 events
                
                # Look for attack patterns
                ip_event_counts = defaultdict(list)
                for event in recent_events:
                    if event.ip_address:
                        ip_event_counts[event.ip_address].append(event)
                
                # Detect potential attacks
                for ip, events in ip_event_counts.items():
                    if len(events) >= 50:  # High activity
                        event_types = [e.event_type for e in events]
                        
                        # Check for scanning pattern
                        if event_types.count(SecurityEventType.UNAUTHORIZED_ACCESS) >= 10:
                            await self.log_event(
                                SecurityEventType.SUSPICIOUS_PATTERN,
                                ip_address=ip,
                                details={'pattern': 'potential_scan', 'event_count': len(events)}
                            )
                
                await asyncio.sleep(60)  # Run every minute
                
            except Exception as e:
                logger.error(f"Error in security analysis: {e}")
                await asyncio.sleep(60)
    
    async def _load_blocklists(self):
        """Load blocked IPs and users from cache."""
        # Load blocked IPs
        blocked_ip_keys = await cache_manager.keys("blocked_ip:*")
        for key in blocked_ip_keys:
            ip = key.split(":")[-1]
            self._blocked_ips.add(ip)
        
        logger.info(f"Loaded {len(self._blocked_ips)} blocked IPs")
    
    async def _save_blocklists(self):
        """Save blocklists to cache."""
        # IPs are already saved with expiration
        pass


# Global instance
security_monitor_v2 = SecurityMonitorV2()