"""
Session management endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session

from app.core.auth import get_current_active_user
from app.core.logger import get_logger
from app.database import get_db
from app.models.user import User
from app.services.session_manager import session_manager, DeviceInfo
from app.monitoring.audit_logger import audit_logger, AuditEventType
from app.core.cache import cache_manager

logger = get_logger(__name__)
router = APIRouter()


@router.get("/sessions")
async def get_user_sessions(
    current_user: User = Depends(get_current_active_user),
    request: Request = None
):
    """
    Get all active sessions for the current user.
    """
    try:
        session_info = await session_manager.get_session_info(str(current_user.id))
        
        # Mark current session
        current_session_id = request.cookies.get("session_id") if request else None
        if current_session_id:
            for session in session_info["active_sessions"]:
                if session["session_id"] == current_session_id:
                    session["is_current"] = True
        
        return {
            "status": "success",
            "data": session_info
        }
        
    except Exception as e:
        logger.error(f"Error fetching user sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch sessions"
        )


@router.post("/sessions/revoke/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    request: Request = None
):
    """
    Revoke a specific session.
    """
    try:
        # Get session to verify ownership
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Verify user owns this session
        if session.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot revoke another user's session"
            )
        
        # Don't allow revoking current session via this endpoint
        current_session_id = request.cookies.get("session_id") if request else None
        if session_id == current_session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot revoke current session. Use logout instead."
            )
        
        # Revoke session
        await session_manager.revoke_session(session_id, "User requested revocation")
        
        # Log action
        await audit_logger.log(
            event_type=AuditEventType.SECURITY_ALERT,
            user_id=str(current_user.id),
            details={
                "action": "session_revoked",
                "revoked_session_id": session_id
            }
        )
        
        return {
            "status": "success",
            "message": "Session revoked successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke session"
        )


@router.post("/sessions/revoke-all")
async def revoke_all_sessions(
    current_user: User = Depends(get_current_active_user),
    request: Request = None,
    keep_current: bool = True
):
    """
    Revoke all sessions for the current user.
    
    Args:
        keep_current: If True, keeps the current session active
    """
    try:
        current_session_id = request.cookies.get("session_id") if request else None
        
        if keep_current and current_session_id:
            # Revoke all except current
            await session_manager.revoke_all_sessions(
                str(current_user.id),
                except_current=current_session_id
            )
            message = "All sessions except current have been revoked"
        else:
            # Revoke all sessions
            await session_manager.revoke_all_sessions(str(current_user.id))
            message = "All sessions have been revoked"
        
        # Log action
        await audit_logger.log(
            event_type=AuditEventType.SECURITY_ALERT,
            user_id=str(current_user.id),
            details={
                "action": "all_sessions_revoked",
                "keep_current": keep_current
            }
        )
        
        return {
            "status": "success",
            "message": message
        }
        
    except Exception as e:
        logger.error(f"Error revoking all sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke sessions"
        )


@router.get("/sessions/{session_id}")
async def get_session_details(
    session_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get details for a specific session.
    """
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Verify user owns this session
        if session.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access another user's session"
            )
        
        return {
            "status": "success",
            "data": {
                "session_id": session.session_id,
                "device": session.device_info.to_dict(),
                "created_at": session.created_at.isoformat(),
                "expires_at": session.expires_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "is_persistent": session.is_persistent,
                "activity_count": session.activity_count,
                "status": session.status.value
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching session details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch session details"
        )


@router.post("/sessions/extend")
async def extend_session(
    hours: int = 1,
    current_user: User = Depends(get_current_active_user),
    request: Request = None
):
    """
    Extend current session expiry.
    """
    try:
        if hours < 1 or hours > 24:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hours must be between 1 and 24"
            )
        
        current_session_id = request.cookies.get("session_id") if request else None
        if not current_session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active session found"
            )
        
        # Get and extend session
        session = await session_manager.get_session(current_session_id)
        if not session or session.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid session"
            )
        
        session.extend_expiry(hours)
        await session_manager._store_session(session)
        
        return {
            "status": "success",
            "data": {
                "new_expiry": session.expires_at.isoformat(),
                "extended_by_hours": hours
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extending session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extend session"
        )


@router.get("/sessions/csrf-token")
async def get_csrf_token(
    current_user: User = Depends(get_current_active_user),
    request: Request = None
):
    """
    Get CSRF token for current session.
    """
    try:
        current_session_id = request.cookies.get("session_id") if request else None
        if not current_session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active session found"
            )
        
        session = await session_manager.get_session(current_session_id)
        if not session or session.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid session"
            )
        
        return {
            "status": "success",
            "data": {
                "csrf_token": session.csrf_token
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching CSRF token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch CSRF token"
        )


@router.get("/sessions/devices")
async def get_known_devices(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get list of known devices for the user.
    """
    try:
        # Get known devices from session manager
        devices = await session_manager._get_known_devices(str(current_user.id))
        
        # Get device details
        device_list = []
        device_key = f"user_devices:{current_user.id}"
        
        for device_id in devices:
            device_data = await cache_manager.hget(device_key, device_id)
            if device_data:
                import json
                device_info = json.loads(device_data)
                device_list.append(device_info)
        
        # Sort by last seen
        device_list.sort(key=lambda d: d.get("last_seen", ""), reverse=True)
        
        return {
            "status": "success",
            "data": {
                "devices": device_list,
                "total": len(device_list)
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching known devices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch devices"
        )


@router.post("/sessions/remove-device/{device_id}")
async def remove_device(
    device_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Remove a device from known devices and revoke its sessions.
    """
    try:
        # Remove device from cache
        device_key = f"user_devices:{current_user.id}"
        await cache_manager.hdel(device_key, device_id)
        
        # Revoke all sessions for this device
        device_sessions_key = f"device_sessions:{device_id}"
        session_ids = await cache_manager.smembers(device_sessions_key)
        
        for session_id in session_ids:
            session = await session_manager.get_session(session_id)
            if session and session.user_id == str(current_user.id):
                await session_manager.revoke_session(session_id, "Device removed")
        
        # Clear device sessions index
        await cache_manager.delete(device_sessions_key)
        
        # Log action
        await audit_logger.log(
            event_type=AuditEventType.SECURITY_ALERT,
            user_id=str(current_user.id),
            details={
                "action": "device_removed",
                "device_id": device_id
            }
        )
        
        return {
            "status": "success",
            "message": "Device removed successfully"
        }
        
    except Exception as e:
        logger.error(f"Error removing device: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove device"
        )