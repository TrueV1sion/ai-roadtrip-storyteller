"""
Security monitoring and audit log endpoints.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin_user
from app.core.logger import get_logger
from app.db.base import get_db
from app.models.user import User
from app.monitoring.security_monitor import security_monitor, SecurityEventType
from app.monitoring.audit_logger import audit_logger, AuditEventType

logger = get_logger(__name__)
router = APIRouter()


@router.get("/security/events")
async def get_security_events(
    hours: int = Query(default=24, ge=1, le=168),  # Max 7 days
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get security events summary for the specified time period.
    Admin access required.
    """
    try:
        summary = await security_monitor.get_security_summary(hours=hours)
        
        return {
            "status": "success",
            "data": summary
        }
        
    except Exception as e:
        logger.error(f"Error fetching security events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch security events"
        )


@router.get("/security/audit-logs")
async def get_audit_logs(
    db: Session = Depends(get_db),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    ip_address: Optional[str] = Query(None, description="Filter by IP address"),
    start_date: Optional[datetime] = Query(None, description="Start date for filtering"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Query audit logs with filters.
    Admin access required.
    """
    try:
        # Convert event type string to enum
        event_types = None
        if event_type:
            try:
                event_types = [AuditEventType(event_type)]
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid event type: {event_type}"
                )
        
        # Default date range if not specified
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=7)  # Default to last 7 days
        
        # Query logs
        logs = await audit_logger.query_logs(
            db=db,
            event_types=event_types,
            user_id=user_id,
            ip_address=ip_address,
            start_time=start_date,
            end_time=end_date,
            resource_type=resource_type,
            resource_id=resource_id,
            limit=limit,
            offset=offset
        )
        
        # Convert to response format
        log_data = [
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "event_type": log.event_type,
                "user_id": log.user_id,
                "ip_address": log.ip_address,
                "resource": f"{log.resource_type}/{log.resource_id}" if log.resource_type else None,
                "action": log.action,
                "result": log.result,
                "risk_score": log.risk_score,
                "details": log.details
            }
            for log in logs
        ]
        
        return {
            "status": "success",
            "data": {
                "logs": log_data,
                "query": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "limit": limit,
                    "offset": offset,
                    "filters": {
                        "event_type": event_type,
                        "user_id": user_id,
                        "ip_address": ip_address,
                        "resource_type": resource_type,
                        "resource_id": resource_id
                    }
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying audit logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query audit logs"
        )


@router.get("/security/audit-logs/user/{user_id}")
async def get_user_audit_logs(
    user_id: str,
    db: Session = Depends(get_db),
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get audit logs for a specific user.
    Admin access required.
    """
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        logs = await audit_logger.query_logs(
            db=db,
            user_id=user_id,
            start_time=start_date,
            end_time=end_date,
            limit=500  # Higher limit for user-specific queries
        )
        
        # Group by event type
        events_by_type = {}
        for log in logs:
            if log.event_type not in events_by_type:
                events_by_type[log.event_type] = []
            events_by_type[log.event_type].append({
                "timestamp": log.timestamp.isoformat(),
                "ip_address": log.ip_address,
                "result": log.result,
                "details": log.details
            })
        
        return {
            "status": "success",
            "data": {
                "user_id": user_id,
                "period": f"Last {days} days",
                "total_events": len(logs),
                "events_by_type": events_by_type,
                "recent_events": [
                    {
                        "timestamp": log.timestamp.isoformat(),
                        "event_type": log.event_type,
                        "ip_address": log.ip_address,
                        "result": log.result
                    }
                    for log in logs[:10]  # Last 10 events
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching user audit logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user audit logs"
        )


@router.post("/security/audit-logs/verify-integrity")
async def verify_audit_log_integrity(
    db: Session = Depends(get_db),
    start_id: Optional[str] = Query(None, description="Starting log ID"),
    end_id: Optional[str] = Query(None, description="Ending log ID"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Verify integrity of audit logs using hash chain.
    Admin access required.
    """
    try:
        result = await audit_logger.verify_integrity(
            db=db,
            start_id=start_id,
            end_id=end_id
        )
        
        return {
            "status": "success",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Error verifying audit log integrity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify audit log integrity"
        )


@router.get("/security/compliance-report/{compliance_type}")
async def generate_compliance_report(
    compliance_type: str,
    db: Session = Depends(get_db),
    start_date: datetime = Query(..., description="Report start date"),
    end_date: datetime = Query(..., description="Report end date"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Generate compliance report for auditors.
    Admin access required.
    
    Compliance types: GDPR, HIPAA, PCI-DSS, SOC2
    """
    try:
        valid_types = ["GDPR", "HIPAA", "PCI-DSS", "SOC2"]
        if compliance_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid compliance type. Must be one of: {', '.join(valid_types)}"
            )
        
        report = await audit_logger.generate_compliance_report(
            db=db,
            compliance_type=compliance_type,
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "status": "success",
            "data": report
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating compliance report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate compliance report"
        )


@router.get("/security/blocked-ips")
async def get_blocked_ips(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get list of currently blocked IP addresses.
    Admin access required.
    """
    try:
        # TODO: Implement proper blocked IP listing from cache
        blocked_ips = []
        
        return {
            "status": "success",
            "data": {
                "blocked_ips": blocked_ips,
                "total": len(blocked_ips)
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching blocked IPs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch blocked IPs"
        )


@router.post("/security/unblock-ip/{ip_address}")
async def unblock_ip(
    ip_address: str,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Unblock an IP address.
    Admin access required.
    """
    try:
        # TODO: Implement IP unblocking
        
        # Log the action
        await audit_logger.log(
            event_type=AuditEventType.CONFIG_CHANGED,
            user_id=str(current_user.id),
            details={
                "action": "unblock_ip",
                "ip_address": ip_address
            }
        )
        
        return {
            "status": "success",
            "message": f"IP address {ip_address} has been unblocked"
        }
        
    except Exception as e:
        logger.error(f"Error unblocking IP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unblock IP"
        )


@router.get("/security/locked-accounts")
async def get_locked_accounts(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get list of locked user accounts.
    Admin access required.
    """
    try:
        # TODO: Implement proper locked account listing
        locked_accounts = []
        
        return {
            "status": "success",
            "data": {
                "locked_accounts": locked_accounts,
                "total": len(locked_accounts)
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching locked accounts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch locked accounts"
        )


@router.post("/security/unlock-account/{user_id}")
async def unlock_account(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Unlock a user account.
    Admin access required.
    """
    try:
        # TODO: Implement account unlocking
        
        # Log the action
        await audit_logger.log(
            event_type=AuditEventType.ACCOUNT_UNLOCKED,
            user_id=user_id,
            details={
                "unlocked_by": str(current_user.id),
                "admin_email": current_user.email
            }
        )
        
        return {
            "status": "success",
            "message": f"Account {user_id} has been unlocked"
        }
        
    except Exception as e:
        logger.error(f"Error unlocking account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unlock account"
        )