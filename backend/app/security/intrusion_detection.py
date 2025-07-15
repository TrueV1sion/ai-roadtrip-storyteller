"""
Intrusion Detection System - Production Implementation
Routes to V2 implementation for backward compatibility
"""

import logging
from typing import Dict, Any

from app.security.intrusion_detection_v2 import intrusion_detection_system_v2

logger = logging.getLogger(__name__)


class IntrusionDetectionSystem:
    """IDS facade for backward compatibility."""
    
    def __init__(self):
        self._v2_system = intrusion_detection_system_v2
        logger.info("Intrusion Detection System initialized (production)")
    
    @property
    def active(self) -> bool:
        """Check if IDS is active."""
        return self._v2_system.active
    
    async def start(self):
        """Start the intrusion detection system."""
        await self._v2_system.start()
    
    async def stop(self):
        """Stop the intrusion detection system."""
        await self._v2_system.stop()
    
    async def analyze_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze request for potential threats."""
        result = await self._v2_system.analyze_request(request_data)
        
        # Map to old format for compatibility
        threat_level = "low"
        if result['confidence'] >= 0.8:
            threat_level = "critical"
        elif result['confidence'] >= 0.6:
            threat_level = "high"
        elif result['confidence'] >= 0.4:
            threat_level = "medium"
        
        return {
            "threat_level": threat_level,
            "analysis": result.get('attack_type', 'none'),
            "confidence": result['confidence'],
            "indicators": result['indicators']
        }


# Global instance
intrusion_detection_system = IntrusionDetectionSystem()
