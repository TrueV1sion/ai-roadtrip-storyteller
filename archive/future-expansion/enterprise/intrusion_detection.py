"""
Intrusion Detection System management endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_admin_user
from app.core.logger import get_logger
from app.db.base import get_db
from app.models.user import User
from app.security.intrusion_detection import intrusion_detection_system

logger = get_logger(__name__)
router = APIRouter()


@router.get("/ids/status")
async def get_ids_status(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get IDS system status and threat summary.
    Admin access required.
    """
    try:
        summary = await intrusion_detection_system.get_threat_summary()
        
        return {
            "status": "success",
            "data": summary
        }
        
    except Exception as e:
        logger.error(f"Error getting IDS status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get IDS status"
        )


@router.get("/ids/active-threats")
async def get_active_threats(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get list of currently active threats.
    Admin access required.
    """
    try:
        active_threats = []
        
        for threat_id, threat_data in intrusion_detection_system.active_threats.items():
            active_threats.append({
                "threat_id": threat_id,
                "threats": [
                    {
                        "type": t["type"].value,
                        "level": t["level"].value,
                        "details": t["details"]
                    }
                    for t in threat_data["threats"]
                ],
                "source_ip": threat_data["source_ip"],
                "user_id": threat_data.get("user_id"),
                "first_seen": threat_data["first_seen"].isoformat(),
                "last_seen": threat_data["last_seen"].isoformat(),
                "occurrence_count": threat_data["count"]
            })
        
        return {
            "status": "success",
            "data": {
                "active_threats": active_threats,
                "total": len(active_threats)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting active threats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get active threats"
        )


@router.get("/ids/threat-intelligence")
async def get_threat_intelligence(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get current threat intelligence data.
    Admin access required.
    """
    try:
        threat_intel = intrusion_detection_system.threat_intel
        
        return {
            "status": "success",
            "data": {
                "known_bad_ips": list(threat_intel.known_bad_ips),
                "known_bad_domains": list(threat_intel.known_bad_domains),
                "threat_signatures": [
                    {
                        "name": sig["name"],
                        "threat_type": sig["threat_type"].value,
                        "level": sig["level"].value
                    }
                    for sig in threat_intel.threat_signatures
                ],
                "last_update": threat_intel.last_update.isoformat() if threat_intel.last_update else None
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting threat intelligence: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get threat intelligence"
        )


@router.post("/ids/threat-intelligence/update")
async def update_threat_intelligence(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Force update of threat intelligence feeds.
    Admin access required.
    """
    try:
        await intrusion_detection_system.threat_intel.update_feeds()
        
        return {
            "status": "success",
            "message": "Threat intelligence feeds updated successfully"
        }
        
    except Exception as e:
        logger.error(f"Error updating threat intelligence: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update threat intelligence"
        )


@router.get("/ids/threat-timeline")
async def get_threat_timeline(
    hours: int = 24,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get threat timeline for specified hours.
    Admin access required.
    """
    try:
        if hours < 1 or hours > 168:  # Max 7 days
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hours must be between 1 and 168"
            )
        
        timeline = intrusion_detection_system._get_threat_timeline(hours)
        
        return {
            "status": "success",
            "data": {
                "timeline": timeline,
                "period_hours": hours
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting threat timeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get threat timeline"
        )


@router.get("/ids/threat-sources")
async def get_threat_sources(
    limit: int = 10,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get top threat sources.
    Admin access required.
    """
    try:
        sources = intrusion_detection_system._get_top_threat_sources(limit)
        
        return {
            "status": "success",
            "data": {
                "threat_sources": sources,
                "limit": limit
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting threat sources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get threat sources"
        )


@router.post("/ids/whitelist/ip/{ip_address}")
async def whitelist_ip(
    ip_address: str,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Add IP to whitelist.
    Admin access required.
    """
    try:
        # Remove from known bad IPs if present
        intrusion_detection_system.threat_intel.known_bad_ips.discard(ip_address)
        
        # TODO: Implement persistent whitelist storage
        
        return {
            "status": "success",
            "message": f"IP {ip_address} added to whitelist"
        }
        
    except Exception as e:
        logger.error(f"Error whitelisting IP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to whitelist IP"
        )


@router.delete("/ids/threat/{threat_id}")
async def dismiss_threat(
    threat_id: str,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Dismiss an active threat.
    Admin access required.
    """
    try:
        if threat_id in intrusion_detection_system.active_threats:
            del intrusion_detection_system.active_threats[threat_id]
            
            return {
                "status": "success",
                "message": f"Threat {threat_id} dismissed"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Threat not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error dismissing threat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to dismiss threat"
        )


@router.get("/ids/config")
async def get_ids_config(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get IDS configuration.
    Admin access required.
    """
    try:
        return {
            "status": "success",
            "data": intrusion_detection_system.config
        }
        
    except Exception as e:
        logger.error(f"Error getting IDS config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get IDS configuration"
        )


@router.patch("/ids/config")
async def update_ids_config(
    config_updates: dict,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Update IDS configuration.
    Admin access required.
    """
    try:
        # Validate config keys
        valid_keys = set(intrusion_detection_system.config.keys())
        update_keys = set(config_updates.keys())
        
        invalid_keys = update_keys - valid_keys
        if invalid_keys:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid configuration keys: {', '.join(invalid_keys)}"
            )
        
        # Update configuration
        for key, value in config_updates.items():
            intrusion_detection_system.config[key] = value
        
        return {
            "status": "success",
            "message": "IDS configuration updated",
            "updated_config": intrusion_detection_system.config
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating IDS config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update IDS configuration"
        )