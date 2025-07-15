"""
Automated threat response management endpoints.
"""

from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel

from app.core.auth import get_current_admin_user
from app.core.logger import get_logger
from app.models.user import User
from app.security.automated_threat_response import (
    automated_threat_response,
    ThreatResponseAction,
    ThreatLevel
)
from app.monitoring.security_monitor import SecurityEvent, SecurityEventType, SecurityEventSeverity

logger = get_logger(__name__)
router = APIRouter()


class TestEventRequest(BaseModel):
    """Request model for testing threat response rules."""
    event_type: SecurityEventType
    severity: SecurityEventSeverity
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    details: dict = {}


class RuleUpdateRequest(BaseModel):
    """Request model for updating response rules."""
    enabled: Optional[bool] = None
    cooldown_minutes: Optional[int] = None
    actions: Optional[List[ThreatResponseAction]] = None


@router.get("/threat-response/status")
async def get_threat_response_status(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get automated threat response system status.
    """
    try:
        stats = await automated_threat_response.get_statistics()
        
        return {
            "status": "success",
            "data": {
                "system_status": "active" if automated_threat_response._running else "inactive",
                "emergency_mode": automated_threat_response.emergency_mode,
                "statistics": stats,
                "rules": [
                    {
                        "name": rule.name,
                        "threat_level": rule.threat_level.value,
                        "actions": [action.value for action in rule.actions],
                        "cooldown_minutes": rule.cooldown_minutes,
                        "active_cooldowns": len(rule.last_triggered)
                    }
                    for rule in automated_threat_response.rules
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting threat response status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get threat response status"
        )


@router.get("/threat-response/history")
async def get_response_history(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get automated response history.
    """
    try:
        # Default time range if not specified
        if not end_time:
            end_time = datetime.utcnow()
        if not start_time:
            start_time = end_time - timedelta(hours=24)
        
        history = await automated_threat_response.get_response_history(
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        
        return {
            "status": "success",
            "data": {
                "responses": history,
                "total": len(history),
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting response history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get response history"
        )


@router.post("/threat-response/test-rule")
async def test_response_rule(
    rule_name: str,
    test_event: TestEventRequest,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Test a threat response rule with a simulated event.
    """
    try:
        # Create test security event
        event = SecurityEvent(
            id=f"test_{datetime.utcnow().timestamp()}",
            event_type=test_event.event_type,
            severity=test_event.severity,
            timestamp=datetime.utcnow(),
            user_id=test_event.user_id,
            ip_address=test_event.ip_address,
            details=test_event.details
        )
        
        # Test the rule
        result = await automated_threat_response.test_rule(rule_name, event)
        
        return {
            "status": "success",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Error testing rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to test rule"
        )


@router.post("/threat-response/emergency-mode")
async def toggle_emergency_mode(
    enable: bool = Query(..., description="Enable or disable emergency mode"),
    reason: str = Query(..., description="Reason for toggling emergency mode"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Toggle emergency security mode.
    """
    try:
        if enable:
            # Create emergency event
            event = SecurityEvent(
                id=f"emergency_{datetime.utcnow().timestamp()}",
                event_type=SecurityEventType.SECURITY_ALERT,
                severity=SecurityEventSeverity.CRITICAL,
                timestamp=datetime.utcnow(),
                user_id=str(current_user.id),
                details={
                    "reason": reason,
                    "triggered_by": "manual",
                    "admin_id": str(current_user.id)
                }
            )
            
            # Enable emergency mode
            result = await automated_threat_response._enable_emergency_mode(event)
            
            message = "Emergency mode enabled"
        else:
            # Disable emergency mode
            automated_threat_response.emergency_mode = False
            
            # Remove emergency mode adjustments
            from app.core.enhanced_rate_limiter import enhanced_rate_limiter
            enhanced_rate_limiter.remove_dynamic_adjustment("emergency_mode")
            
            # Clear emergency mode flag
            from app.core.cache import cache_manager
            await cache_manager.delete("security_emergency_mode")
            
            result = {"emergency_mode": False}
            message = "Emergency mode disabled"
        
        logger.warning(
            f"Emergency mode {'enabled' if enable else 'disabled'} "
            f"by {current_user.email}: {reason}"
        )
        
        return {
            "status": "success",
            "message": message,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Error toggling emergency mode: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to toggle emergency mode"
        )


@router.get("/threat-response/rules")
async def get_response_rules(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get all configured threat response rules.
    """
    try:
        rules = []
        
        for rule in automated_threat_response.rules:
            rules.append({
                "name": rule.name,
                "threat_level": rule.threat_level.value,
                "actions": [action.value for action in rule.actions],
                "cooldown_minutes": rule.cooldown_minutes,
                "active_cooldowns": [
                    {
                        "target": target,
                        "expires_at": (
                            rule.last_triggered[target] + 
                            timedelta(minutes=rule.cooldown_minutes)
                        ).isoformat()
                    }
                    for target in rule.last_triggered
                    if datetime.utcnow() - rule.last_triggered[target] < timedelta(minutes=rule.cooldown_minutes)
                ]
            })
        
        return {
            "status": "success",
            "data": {
                "rules": rules,
                "total": len(rules)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting response rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get response rules"
        )


@router.post("/threat-response/manual-action")
async def execute_manual_action(
    action: ThreatResponseAction = Query(..., description="Action to execute"),
    target: str = Query(..., description="Target (IP address or user ID)"),
    reason: str = Query(..., description="Reason for manual action"),
    duration_seconds: int = Query(3600, description="Duration for temporary actions"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Manually execute a threat response action.
    """
    try:
        # Create event for audit trail
        event = SecurityEvent(
            id=f"manual_{datetime.utcnow().timestamp()}",
            event_type=SecurityEventType.MANUAL_ACTION,
            severity=SecurityEventSeverity.HIGH,
            timestamp=datetime.utcnow(),
            user_id=target if not target.count('.') >= 3 else None,  # Simple IP check
            ip_address=target if target.count('.') >= 3 else None,
            details={
                "action": action.value,
                "reason": reason,
                "admin_id": str(current_user.id),
                "duration": duration_seconds
            }
        )
        
        # Execute the action
        result = await automated_threat_response._execute_action(action, event)
        
        logger.warning(
            f"Manual action {action.value} executed on {target} "
            f"by {current_user.email}: {reason}"
        )
        
        return {
            "status": "success",
            "message": f"Action {action.value} executed successfully",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Error executing manual action: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute action"
        )


@router.get("/threat-response/blocked-entities")
async def get_blocked_entities(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get currently blocked IPs and locked accounts.
    """
    try:
        from app.security.intrusion_detection import intrusion_detection_system
        from app.core.cache import cache_manager
        
        # Get blocked IPs
        blocked_ips = await intrusion_detection_system.get_blocked_ips_detailed()
        
        # Get locked accounts (scan cache keys)
        locked_accounts = []
        # This is a simplified version - in production, you'd have a proper index
        
        return {
            "status": "success",
            "data": {
                "blocked_ips": blocked_ips,
                "locked_accounts": locked_accounts,
                "total_blocked": len(blocked_ips) + len(locked_accounts)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting blocked entities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get blocked entities"
        )


@router.delete("/threat-response/unblock/{entity}")
async def unblock_entity(
    entity: str,
    reason: str = Query(..., description="Reason for unblocking"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Unblock an IP address or unlock an account.
    """
    try:
        from app.security.intrusion_detection import intrusion_detection_system
        from app.core.cache import cache_manager
        
        results = []
        
        # Check if it's an IP
        if entity.count('.') >= 3:  # Simple IP check
            # Unblock IP
            await intrusion_detection_system.unblock_ip(entity)
            results.append(f"Unblocked IP: {entity}")
            
            # Remove from rate limiter
            from app.core.enhanced_rate_limiter import enhanced_rate_limiter
            key = f"ip:{entity}"
            if key in enhanced_rate_limiter.blocked_keys:
                del enhanced_rate_limiter.blocked_keys[key]
            await cache_manager.delete(f"rate_limit_blocked:{key}")
            results.append(f"Removed rate limit block for IP: {entity}")
        else:
            # Unlock account
            await cache_manager.delete(f"account_locked:{entity}")
            results.append(f"Unlocked account: {entity}")
            
            # Remove password reset requirement
            await cache_manager.delete(f"force_password_reset:{entity}")
            results.append(f"Removed password reset requirement for: {entity}")
        
        logger.info(
            f"Entity {entity} unblocked by {current_user.email}: {reason}"
        )
        
        return {
            "status": "success",
            "message": f"Successfully unblocked {entity}",
            "actions": results
        }
        
    except Exception as e:
        logger.error(f"Error unblocking entity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unblock entity"
        )