"""
Security Monitor - Production Implementation
Routes to the new V2 implementation for backward compatibility.
"""

import logging
from typing import Dict, Any, Optional

from app.monitoring.security_monitor_v2 import (
    security_monitor_v2,
    SecurityEventType,
    ThreatLevel
)

logger = logging.getLogger(__name__)


class SecurityMonitor:
    """Security monitoring facade for backward compatibility."""
    
    def __init__(self):
        self._v2_monitor = security_monitor_v2
        logger.info("Security Monitor initialized (production)")
    
    async def start(self):
        """Start security monitoring."""
        await self._v2_monitor.start()
    
    async def stop(self):
        """Stop security monitoring."""
        await self._v2_monitor.stop()
    
    async def log_security_event(self, event_data: Dict[str, Any]):
        """Log a security event (backward compatibility)."""
        # Map old event data to new format
        event_type_map = {
            'login_failed': SecurityEventType.LOGIN_FAILURE,
            'login_success': SecurityEventType.LOGIN_SUCCESS,
            'unauthorized': SecurityEventType.UNAUTHORIZED_ACCESS,
            'rate_limit': SecurityEventType.RATE_LIMIT_EXCEEDED,
            'suspicious': SecurityEventType.SUSPICIOUS_PATTERN
        }
        
        event_type = event_type_map.get(
            event_data.get('type', 'suspicious'),
            SecurityEventType.SUSPICIOUS_PATTERN
        )
        
        await self._v2_monitor.log_event(
            event_type=event_type,
            user_id=event_data.get('user_id'),
            ip_address=event_data.get('ip_address'),
            endpoint=event_data.get('endpoint'),
            details=event_data.get('details', {})
        )
    
    @property
    def active(self) -> bool:
        """Check if monitoring is active."""
        return self._v2_monitor.active
    
    # Additional convenience methods for backward compatibility
    async def analyze_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze request for threats."""
        return await self._v2_monitor.analyze_request(request_data)
    
    async def get_threat_intelligence(
        self,
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get threat intelligence."""
        return await self._v2_monitor.get_threat_intelligence(ip_address, user_id)


# Global instance
security_monitor = SecurityMonitor()
