"""
Security Monitoring Dashboard API Endpoints
Production endpoints for real-time security monitoring
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.core.auth import get_current_admin_user
from app.models.user import User
from app.monitoring.security_monitor_v2 import security_monitor_v2, SecurityEventType
from app.security.intrusion_detection_v2 import intrusion_detection_system_v2
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/security/monitoring", tags=["Security Monitoring V2"])


@router.get("/dashboard")
async def get_security_dashboard(
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Get comprehensive security dashboard data.
    
    Returns real-time security metrics, active threats, and system health.
    """
    try:
        # Get security monitor summary
        security_summary = await security_monitor_v2.get_security_summary()
        
        # Get IDS threat report
        threat_report = await intrusion_detection_system_v2.get_threat_report()
        
        # Calculate security score (0-100)
        security_score = calculate_security_score(security_summary, threat_report)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "security_score": security_score,
            "status": get_security_status(security_score),
            "security_summary": security_summary,
            "threat_report": threat_report,
            "recommendations": generate_recommendations(security_summary, threat_report)
        }
    except Exception as e:
        logger.error(f"Error generating security dashboard: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate dashboard")


@router.get("/events")
async def get_security_events(
    event_type: Optional[SecurityEventType] = None,
    threat_level: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(100, le=1000),
    current_user: User = Depends(get_current_admin_user)
) -> List[Dict[str, Any]]:
    """
    Get security events with filtering options.
    
    Args:
        event_type: Filter by specific event type
        threat_level: Filter by threat level (low, medium, high, critical)
        start_time: Start of time range
        end_time: End of time range
        limit: Maximum number of events to return
    """
    try:
        # This would typically query from a database
        # For now, return recent events from memory
        events = []
        
        # Get events from security monitor's queue
        all_events = list(security_monitor_v2._events_queue)
        
        # Apply filters
        filtered_events = all_events
        
        if event_type:
            filtered_events = [e for e in filtered_events if e.event_type == event_type]
        
        if threat_level:
            filtered_events = [e for e in filtered_events if e.threat_level.value == threat_level]
        
        if start_time:
            filtered_events = [e for e in filtered_events if e.timestamp >= start_time]
        
        if end_time:
            filtered_events = [e for e in filtered_events if e.timestamp <= end_time]
        
        # Sort by timestamp descending and limit
        filtered_events.sort(key=lambda x: x.timestamp, reverse=True)
        filtered_events = filtered_events[:limit]
        
        # Convert to response format
        for event in filtered_events:
            events.append({
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "timestamp": event.timestamp.isoformat(),
                "user_id": event.user_id,
                "ip_address": event.ip_address,
                "endpoint": event.endpoint,
                "threat_level": event.threat_level.value,
                "details": event.details
            })
        
        return events
    except Exception as e:
        logger.error(f"Error retrieving security events: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve events")


@router.get("/threats/active")
async def get_active_threats(
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Get currently active threats and attacks."""
    try:
        threat_report = await intrusion_detection_system_v2.get_threat_report()
        
        # Add threat intelligence for each active attack
        enhanced_threats = {}
        for ip, attack_info in threat_report['active_attacks'].items():
            threat_intel = await security_monitor_v2.get_threat_intelligence(ip_address=ip)
            enhanced_threats[ip] = {
                **attack_info,
                'threat_intelligence': threat_intel
            }
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "active_threat_count": len(enhanced_threats),
            "threats": enhanced_threats,
            "high_risk_ips": [
                ip for ip, info in enhanced_threats.items()
                if info.get('threat_intelligence', {}).get('risk_level') in ['high', 'critical']
            ]
        }
    except Exception as e:
        logger.error(f"Error retrieving active threats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve threats")


@router.get("/blocked")
async def get_blocked_entities(
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Get list of blocked IPs and users."""
    try:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "blocked_ips": list(security_monitor_v2._blocked_ips),
            "blocked_users": list(security_monitor_v2._blocked_users),
            "total_blocked": len(security_monitor_v2._blocked_ips) + len(security_monitor_v2._blocked_users)
        }
    except Exception as e:
        logger.error(f"Error retrieving blocked entities: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve blocked list")


@router.post("/block/ip/{ip_address}")
async def block_ip_address(
    ip_address: str,
    duration_seconds: int = 3600,
    reason: str = "Manual block by admin",
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Manually block an IP address."""
    try:
        await security_monitor_v2.block_ip(ip_address, duration_seconds, reason)
        
        logger.info(f"IP {ip_address} blocked by admin {current_user.id} for {duration_seconds}s. Reason: {reason}")
        
        return {
            "message": f"IP {ip_address} has been blocked",
            "duration_seconds": duration_seconds,
            "reason": reason,
            "blocked_by": current_user.email,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error blocking IP: {e}")
        raise HTTPException(status_code=500, detail="Failed to block IP")


@router.delete("/block/ip/{ip_address}")
async def unblock_ip_address(
    ip_address: str,
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Manually unblock an IP address."""
    try:
        await security_monitor_v2.unblock_ip(ip_address)
        
        logger.info(f"IP {ip_address} unblocked by admin {current_user.id}")
        
        return {
            "message": f"IP {ip_address} has been unblocked",
            "unblocked_by": current_user.email,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error unblocking IP: {e}")
        raise HTTPException(status_code=500, detail="Failed to unblock IP")


@router.get("/threat-intelligence/{ip_address}")
async def get_ip_threat_intelligence(
    ip_address: str,
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Get detailed threat intelligence for a specific IP."""
    try:
        threat_intel = await security_monitor_v2.get_threat_intelligence(ip_address=ip_address)
        
        # Add IDS analysis
        ids_events = [
            event for event in intrusion_detection_system_v2._ip_behavior[ip_address]
        ][-50:]  # Last 50 events
        
        return {
            "ip_address": ip_address,
            "threat_intelligence": threat_intel,
            "ids_analysis": {
                "total_events": len(ids_events),
                "unique_endpoints": len(set(e['endpoint'] for e in ids_events)),
                "time_range": {
                    "first": ids_events[0]['timestamp'].isoformat() if ids_events else None,
                    "last": ids_events[-1]['timestamp'].isoformat() if ids_events else None
                }
            },
            "is_blocked": ip_address in security_monitor_v2._blocked_ips,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error retrieving threat intelligence: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve threat intelligence")


@router.get("/statistics")
async def get_security_statistics(
    time_range: str = Query("1h", regex="^(1h|24h|7d|30d)$"),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Get security statistics for specified time range."""
    try:
        # Parse time range
        now = datetime.utcnow()
        if time_range == "1h":
            start_time = now - timedelta(hours=1)
        elif time_range == "24h":
            start_time = now - timedelta(hours=24)
        elif time_range == "7d":
            start_time = now - timedelta(days=7)
        else:  # 30d
            start_time = now - timedelta(days=30)
        
        # Get events in time range
        all_events = list(security_monitor_v2._events_queue)
        range_events = [e for e in all_events if e.timestamp >= start_time]
        
        # Calculate statistics
        event_types = {}
        threat_levels = {}
        
        for event in range_events:
            event_types[event.event_type.value] = event_types.get(event.event_type.value, 0) + 1
            threat_levels[event.threat_level.value] = threat_levels.get(event.threat_level.value, 0) + 1
        
        return {
            "time_range": time_range,
            "start_time": start_time.isoformat(),
            "end_time": now.isoformat(),
            "total_events": len(range_events),
            "events_by_type": event_types,
            "events_by_threat_level": threat_levels,
            "unique_ips": len(set(e.ip_address for e in range_events if e.ip_address)),
            "unique_users": len(set(e.user_id for e in range_events if e.user_id))
        }
    except Exception as e:
        logger.error(f"Error calculating security statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to calculate statistics")


# Helper functions

def calculate_security_score(security_summary: Dict[str, Any], threat_report: Dict[str, Any]) -> float:
    """Calculate overall security score (0-100)."""
    score = 100.0
    
    # Deduct for threat levels
    last_hour = security_summary['last_hour']
    score -= last_hour['threat_levels'].get('critical', 0) * 10
    score -= last_hour['threat_levels'].get('high', 0) * 5
    score -= last_hour['threat_levels'].get('medium', 0) * 2
    
    # Deduct for active attacks
    score -= len(threat_report['active_attacks']) * 5
    
    # Deduct for blocked entities
    score -= security_summary['current_blocks']['blocked_ips'] * 0.5
    
    return max(0, min(100, score))


def get_security_status(score: float) -> str:
    """Get security status based on score."""
    if score >= 90:
        return "excellent"
    elif score >= 75:
        return "good"
    elif score >= 60:
        return "fair"
    elif score >= 40:
        return "poor"
    else:
        return "critical"


def generate_recommendations(security_summary: Dict[str, Any], threat_report: Dict[str, Any]) -> List[str]:
    """Generate security recommendations."""
    recommendations = []
    
    # Check for high threat activity
    if security_summary['last_hour']['threat_levels'].get('critical', 0) > 0:
        recommendations.append("Critical threats detected - review logs immediately")
    
    if len(threat_report['active_attacks']) > 5:
        recommendations.append("Multiple active attacks - consider enabling stricter rate limiting")
    
    # Add IDS recommendations
    recommendations.extend(threat_report.get('recommendations', []))
    
    return recommendations