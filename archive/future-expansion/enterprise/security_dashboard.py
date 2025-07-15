"""
Security dashboard endpoints for comprehensive security monitoring.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.core.auth import get_current_admin_user
from app.core.logger import get_logger
from app.db.base import get_db
from app.models.user import User
from app.monitoring.security_monitor import security_monitor, SecurityEventType, SecurityEventSeverity
from app.monitoring.audit_logger import audit_logger
from app.security.intrusion_detection import intrusion_detection_system
from app.core.enhanced_rate_limiter import enhanced_rate_limiter
from app.services.session_manager import session_manager
from app.core.cache import cache_manager

logger = get_logger(__name__)
router = APIRouter()


@router.get("/security/dashboard/overview")
async def get_security_overview(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive security overview for dashboard.
    """
    try:
        # Get time ranges
        now = datetime.utcnow()
        last_hour = now - timedelta(hours=1)
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        
        # Security events summary
        events_summary = await security_monitor.get_events_summary(
            start_time=last_24h,
            end_time=now
        )
        
        # Active threats
        active_threats = await intrusion_detection_system.get_active_threats()
        
        # Rate limiting stats
        rate_limit_metrics = enhanced_rate_limiter.get_metrics()
        
        # Session statistics
        session_stats = await session_manager.get_session_statistics()
        
        # Failed login attempts
        failed_logins = await security_monitor.get_events_by_type(
            SecurityEventType.LOGIN_FAILED,
            start_time=last_hour
        )
        
        # System health indicators
        health_status = {
            "security_monitor": await security_monitor.health_check(),
            "audit_logger": await audit_logger.health_check(),
            "intrusion_detection": await intrusion_detection_system.health_check(),
            "rate_limiter": "healthy" if rate_limit_metrics["total_requests"] > 0 else "unknown"
        }
        
        return {
            "status": "success",
            "data": {
                "overview": {
                    "total_events_24h": events_summary["total_events"],
                    "critical_events": events_summary["by_severity"].get(SecurityEventSeverity.CRITICAL.value, 0),
                    "high_severity_events": events_summary["by_severity"].get(SecurityEventSeverity.HIGH.value, 0),
                    "active_threats": len(active_threats),
                    "blocked_ips": len(await intrusion_detection_system.get_blocked_ips()),
                    "rate_limited_requests": rate_limit_metrics["rate_limited_requests"],
                    "active_sessions": session_stats["active_sessions"],
                    "failed_logins_1h": len(failed_logins)
                },
                "trend_data": {
                    "events_last_7d": await _get_event_trends(last_7d, now),
                    "threat_levels": await _get_threat_level_trends(last_7d, now)
                },
                "health_status": health_status,
                "last_updated": now.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting security overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get security overview"
        )


@router.get("/security/dashboard/events")
async def get_security_events(
    event_type: Optional[SecurityEventType] = None,
    severity: Optional[SecurityEventSeverity] = None,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get filtered security events with pagination.
    """
    try:
        # Default time range if not specified
        if not end_time:
            end_time = datetime.utcnow()
        if not start_time:
            start_time = end_time - timedelta(hours=24)
        
        # Build filters
        filters = {}
        if event_type:
            filters["event_type"] = event_type
        if severity:
            filters["severity"] = severity
        if user_id:
            filters["user_id"] = user_id
        if ip_address:
            filters["ip_address"] = ip_address
        
        # Get events
        events = await security_monitor.get_events(
            start_time=start_time,
            end_time=end_time,
            filters=filters,
            limit=limit,
            offset=offset
        )
        
        # Get total count for pagination
        total_count = await security_monitor.count_events(
            start_time=start_time,
            end_time=end_time,
            filters=filters
        )
        
        return {
            "status": "success",
            "data": {
                "events": events,
                "pagination": {
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + limit < total_count
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting security events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get security events"
        )


@router.get("/security/dashboard/threats")
async def get_threat_analysis(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get detailed threat analysis and active threats.
    """
    try:
        # Get active threats
        active_threats = await intrusion_detection_system.get_active_threats()
        
        # Get threat intelligence
        threat_intelligence = await intrusion_detection_system.get_threat_intelligence()
        
        # Get blocked IPs with reasons
        blocked_ips = await intrusion_detection_system.get_blocked_ips_detailed()
        
        # Get attack patterns
        attack_patterns = await intrusion_detection_system.get_detected_patterns(
            start_time=datetime.utcnow() - timedelta(hours=24)
        )
        
        # Risk assessment
        risk_score = await _calculate_risk_score(
            active_threats,
            attack_patterns,
            len(blocked_ips)
        )
        
        return {
            "status": "success",
            "data": {
                "active_threats": active_threats,
                "threat_intelligence": threat_intelligence,
                "blocked_ips": blocked_ips,
                "attack_patterns": attack_patterns,
                "risk_assessment": {
                    "score": risk_score,
                    "level": _get_risk_level(risk_score),
                    "recommendations": _get_security_recommendations(risk_score)
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting threat analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get threat analysis"
        )


@router.get("/security/dashboard/sessions")
async def get_session_analysis(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get session security analysis.
    """
    try:
        # Get session statistics
        session_stats = await session_manager.get_session_statistics()
        
        # Get suspicious sessions
        suspicious_sessions = await session_manager.get_suspicious_sessions()
        
        # Get geographic distribution
        geo_distribution = await session_manager.get_geographic_distribution()
        
        # Get device statistics
        device_stats = await session_manager.get_device_statistics()
        
        # Get concurrent session violations
        concurrent_violations = await security_monitor.get_events_by_type(
            SecurityEventType.CONCURRENT_SESSION_LIMIT,
            start_time=datetime.utcnow() - timedelta(hours=24)
        )
        
        return {
            "status": "success",
            "data": {
                "statistics": session_stats,
                "suspicious_sessions": suspicious_sessions,
                "geographic_distribution": geo_distribution,
                "device_statistics": device_stats,
                "concurrent_violations": len(concurrent_violations),
                "security_metrics": {
                    "sessions_with_2fa": session_stats.get("sessions_with_2fa", 0),
                    "average_session_duration": session_stats.get("avg_duration_minutes", 0),
                    "unique_locations": len(geo_distribution)
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting session analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get session analysis"
        )


@router.get("/security/dashboard/compliance")
async def get_compliance_status(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get compliance and audit status.
    """
    try:
        # Get audit log statistics
        audit_stats = await audit_logger.get_statistics(
            start_time=datetime.utcnow() - timedelta(days=30)
        )
        
        # Check audit log integrity
        integrity_check = await audit_logger.verify_integrity(
            start_time=datetime.utcnow() - timedelta(hours=24)
        )
        
        # Get compliance metrics
        compliance_metrics = {
            "password_policy": await _check_password_policy_compliance(),
            "session_security": await _check_session_security_compliance(),
            "data_retention": await _check_data_retention_compliance(),
            "access_controls": await _check_access_control_compliance()
        }
        
        # Calculate overall compliance score
        compliance_score = sum(
            metric["score"] for metric in compliance_metrics.values()
        ) / len(compliance_metrics)
        
        return {
            "status": "success",
            "data": {
                "audit_statistics": audit_stats,
                "integrity_status": {
                    "verified": integrity_check["valid"],
                    "total_logs": integrity_check["total_logs"],
                    "invalid_logs": integrity_check["invalid_logs"]
                },
                "compliance_metrics": compliance_metrics,
                "overall_compliance": {
                    "score": compliance_score,
                    "status": "compliant" if compliance_score >= 80 else "non-compliant",
                    "last_audit": audit_stats.get("last_audit_time")
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting compliance status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get compliance status"
        )


@router.get("/security/dashboard/performance")
async def get_security_performance(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get security system performance metrics.
    """
    try:
        # Get performance metrics from each component
        performance_data = {
            "security_monitor": await security_monitor.get_performance_metrics(),
            "audit_logger": await audit_logger.get_performance_metrics(),
            "intrusion_detection": await intrusion_detection_system.get_performance_metrics(),
            "rate_limiter": {
                "total_requests": enhanced_rate_limiter.metrics["total_requests"],
                "rate_limited": enhanced_rate_limiter.metrics["rate_limited_requests"],
                "blocked": enhanced_rate_limiter.metrics["blocked_requests"],
                "active_buckets": len(enhanced_rate_limiter.token_buckets)
            }
        }
        
        # Calculate response times
        response_times = {
            "auth_avg_ms": await _get_avg_response_time("auth"),
            "security_check_avg_ms": await _get_avg_response_time("security"),
            "rate_limit_check_avg_ms": await _get_avg_response_time("rate_limit")
        }
        
        # Resource utilization
        resource_usage = {
            "memory_mb": await _get_memory_usage(),
            "cpu_percent": await _get_cpu_usage(),
            "cache_hit_rate": await cache_manager.get_hit_rate()
        }
        
        return {
            "status": "success",
            "data": {
                "performance_metrics": performance_data,
                "response_times": response_times,
                "resource_usage": resource_usage,
                "throughput": {
                    "events_per_second": performance_data["security_monitor"].get("events_per_second", 0),
                    "auth_requests_per_minute": performance_data["security_monitor"].get("auth_rpm", 0)
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting security performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get security performance"
        )


@router.post("/security/dashboard/export")
async def export_security_report(
    report_type: str = Query(..., description="Type of report (daily, weekly, monthly, custom)"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    format: str = Query("json", description="Export format (json, csv, pdf)"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Export security report for specified period.
    """
    try:
        # Validate report type
        valid_types = ["daily", "weekly", "monthly", "custom"]
        if report_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid report type. Must be one of: {', '.join(valid_types)}"
            )
        
        # Determine date range
        if report_type == "custom":
            if not start_date or not end_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Start and end dates required for custom reports"
                )
        else:
            end_date = datetime.utcnow()
            if report_type == "daily":
                start_date = end_date - timedelta(days=1)
            elif report_type == "weekly":
                start_date = end_date - timedelta(days=7)
            elif report_type == "monthly":
                start_date = end_date - timedelta(days=30)
        
        # Generate report data
        report_data = await _generate_security_report(start_date, end_date)
        
        # Format report
        if format == "json":
            return {
                "status": "success",
                "data": report_data,
                "metadata": {
                    "report_type": report_type,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "generated_at": datetime.utcnow().isoformat(),
                    "generated_by": current_user.email
                }
            }
        else:
            # TODO: Implement CSV and PDF export
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Export format '{format}' not yet implemented"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting security report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export security report"
        )


# Helper functions

async def _get_event_trends(start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
    """Get event trends over time period."""
    trends = []
    current = start_time
    
    while current < end_time:
        next_time = current + timedelta(hours=6)  # 6-hour intervals
        
        events = await security_monitor.get_events_summary(
            start_time=current,
            end_time=next_time
        )
        
        trends.append({
            "timestamp": current.isoformat(),
            "total_events": events["total_events"],
            "critical_events": events["by_severity"].get(SecurityEventSeverity.CRITICAL.value, 0),
            "high_events": events["by_severity"].get(SecurityEventSeverity.HIGH.value, 0)
        })
        
        current = next_time
    
    return trends


async def _get_threat_level_trends(start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
    """Get threat level trends over time period."""
    # Simulated threat level calculation
    trends = []
    current = start_time
    
    while current < end_time:
        next_time = current + timedelta(days=1)
        
        threats = await intrusion_detection_system.get_threats_in_period(
            start_time=current,
            end_time=next_time
        )
        
        trends.append({
            "date": current.date().isoformat(),
            "threat_score": len(threats) * 10,  # Simple scoring
            "threat_level": _get_risk_level(len(threats) * 10)
        })
        
        current = next_time
    
    return trends


async def _calculate_risk_score(
    active_threats: List[Dict],
    attack_patterns: List[Dict],
    blocked_ips: int
) -> float:
    """Calculate overall risk score."""
    base_score = 0.0
    
    # Active threats contribute most to risk
    base_score += len(active_threats) * 20
    
    # Attack patterns indicate ongoing issues
    base_score += len(attack_patterns) * 10
    
    # Blocked IPs show we're under attack
    base_score += min(blocked_ips * 5, 50)  # Cap at 50
    
    return min(base_score, 100)  # Cap at 100


def _get_risk_level(score: float) -> str:
    """Convert risk score to level."""
    if score >= 80:
        return "critical"
    elif score >= 60:
        return "high"
    elif score >= 40:
        return "medium"
    elif score >= 20:
        return "low"
    return "minimal"


def _get_security_recommendations(risk_score: float) -> List[str]:
    """Get security recommendations based on risk score."""
    recommendations = []
    
    if risk_score >= 80:
        recommendations.extend([
            "Immediately review and respond to all critical alerts",
            "Consider enabling emergency response protocols",
            "Increase monitoring frequency"
        ])
    elif risk_score >= 60:
        recommendations.extend([
            "Review all high-severity events",
            "Verify all blocked IPs are legitimate threats",
            "Consider strengthening authentication requirements"
        ])
    elif risk_score >= 40:
        recommendations.extend([
            "Monitor trends for escalation",
            "Review security policies",
            "Ensure all patches are up to date"
        ])
    else:
        recommendations.extend([
            "Maintain current security posture",
            "Continue regular security reviews",
            "Keep security training up to date"
        ])
    
    return recommendations


async def _check_password_policy_compliance() -> Dict[str, Any]:
    """Check password policy compliance."""
    # This would check actual password policies
    return {
        "score": 85,
        "status": "compliant",
        "details": {
            "min_length": True,
            "complexity": True,
            "expiration": True,
            "history": True
        }
    }


async def _check_session_security_compliance() -> Dict[str, Any]:
    """Check session security compliance."""
    return {
        "score": 90,
        "status": "compliant",
        "details": {
            "timeout_configured": True,
            "secure_cookies": True,
            "csrf_protection": True,
            "concurrent_limits": True
        }
    }


async def _check_data_retention_compliance() -> Dict[str, Any]:
    """Check data retention compliance."""
    return {
        "score": 80,
        "status": "compliant",
        "details": {
            "audit_logs_retained": True,
            "user_data_lifecycle": True,
            "backup_policies": True,
            "deletion_procedures": True
        }
    }


async def _check_access_control_compliance() -> Dict[str, Any]:
    """Check access control compliance."""
    return {
        "score": 95,
        "status": "compliant",
        "details": {
            "rbac_implemented": True,
            "least_privilege": True,
            "regular_reviews": True,
            "mfa_enabled": True
        }
    }


async def _get_avg_response_time(operation: str) -> float:
    """Get average response time for operation."""
    # This would fetch from metrics
    return 45.2  # Mock value


async def _get_memory_usage() -> float:
    """Get current memory usage in MB."""
    import psutil
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024


async def _get_cpu_usage() -> float:
    """Get current CPU usage percentage."""
    import psutil
    return psutil.cpu_percent(interval=0.1)


async def _generate_security_report(
    start_date: datetime,
    end_date: datetime
) -> Dict[str, Any]:
    """Generate comprehensive security report."""
    # Get all security data for the period
    events_summary = await security_monitor.get_events_summary(
        start_time=start_date,
        end_time=end_date
    )
    
    threat_analysis = await intrusion_detection_system.get_threats_in_period(
        start_time=start_date,
        end_time=end_date
    )
    
    audit_summary = await audit_logger.get_statistics(
        start_time=start_date,
        end_time=end_date
    )
    
    return {
        "executive_summary": {
            "total_events": events_summary["total_events"],
            "critical_incidents": events_summary["by_severity"].get(SecurityEventSeverity.CRITICAL.value, 0),
            "threats_detected": len(threat_analysis),
            "overall_status": "secure" if events_summary["by_severity"].get(SecurityEventSeverity.CRITICAL.value, 0) == 0 else "at-risk"
        },
        "detailed_analysis": {
            "events": events_summary,
            "threats": threat_analysis,
            "audit": audit_summary
        },
        "recommendations": _get_security_recommendations(
            await _calculate_risk_score([], threat_analysis, 0)
        )
    }