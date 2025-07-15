"""
Mobile Security Endpoints
Receives security telemetry from mobile devices
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from enum import Enum

from app.core.auth import get_current_user_optional
from app.models.user import User
from app.database import get_db
from app.core.logger import get_logger
from app.monitoring.security_monitor_v2 import security_monitor, SecurityEventType
from app.core.cache import cache_manager

logger = get_logger(__name__)

router = APIRouter(prefix="/api/mobile/security", tags=["Mobile Security"])


class SecurityRiskType(str, Enum):
    JAILBREAK = "JAILBREAK"
    ROOT = "ROOT"
    DEBUGGING = "DEBUGGING"
    EMULATOR = "EMULATOR"
    TAMPERING = "TAMPERING"
    VPN = "VPN"
    NETWORK = "NETWORK"
    OUTDATED_OS = "OUTDATED_OS"
    UNKNOWN_SOURCE = "UNKNOWN_SOURCE"


class RiskSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityRisk(BaseModel):
    type: SecurityRiskType
    severity: RiskSeverity
    description: str
    mitigation: str


class MobileSecurityStatus(BaseModel):
    device_id: str = Field(..., description="Unique device identifier")
    platform: str = Field(..., regex="^(ios|android)$")
    platform_version: str
    app_version: str
    is_jailbroken: bool = Field(False, description="iOS jailbreak status")
    is_rooted: bool = Field(False, description="Android root status")
    is_debugging_enabled: bool = Field(False)
    is_emulator: bool = Field(False)
    is_tampered: bool = Field(False)
    is_vpn_active: bool = Field(False)
    security_score: int = Field(..., ge=0, le=100)
    risks: List[SecurityRisk] = Field(default_factory=list)
    timestamp: datetime
    
    class Config:
        schema_extra = {
            "example": {
                "device_id": "device_123456",
                "platform": "ios",
                "platform_version": "15.5",
                "app_version": "1.0.0",
                "is_jailbroken": False,
                "is_rooted": False,
                "is_debugging_enabled": False,
                "is_emulator": False,
                "is_tampered": False,
                "is_vpn_active": False,
                "security_score": 95,
                "risks": [],
                "timestamp": "2025-07-11T10:00:00Z"
            }
        }


class SecurityAction(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    RESTRICT = "restrict"
    BLOCK = "block"


class SecurityPolicyResponse(BaseModel):
    action: SecurityAction
    message: Optional[str] = None
    restrictions: List[str] = Field(default_factory=list)
    require_update: bool = Field(False)
    min_app_version: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "action": "allow",
                "message": None,
                "restrictions": [],
                "require_update": False,
                "min_app_version": None
            }
        }


@router.post("/report", response_model=SecurityPolicyResponse)
async def report_security_status(
    status: MobileSecurityStatus,
    current_user: Optional[User] = Depends(get_current_user_optional),
    user_agent: Optional[str] = Header(None),
    x_real_ip: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> SecurityPolicyResponse:
    """
    Report mobile device security status and receive policy decision.
    
    The backend analyzes the security status and returns appropriate
    actions based on the risk level.
    """
    try:
        # Log security telemetry
        await security_monitor.log_event(
            event_type=SecurityEventType.MOBILE_SECURITY_CHECK,
            user_id=str(current_user.id) if current_user else None,
            ip_address=x_real_ip,
            details={
                "device_id": status.device_id,
                "platform": status.platform,
                "platform_version": status.platform_version,
                "app_version": status.app_version,
                "security_score": status.security_score,
                "risks": [risk.dict() for risk in status.risks],
                "flags": {
                    "jailbroken": status.is_jailbroken,
                    "rooted": status.is_rooted,
                    "debugging": status.is_debugging_enabled,
                    "emulator": status.is_emulator,
                    "tampered": status.is_tampered,
                    "vpn": status.is_vpn_active
                }
            },
            user_agent=user_agent
        )
        
        # Cache device security status
        cache_key = f"device_security:{status.device_id}"
        await cache_manager.set(
            cache_key,
            status.dict(),
            expire=3600  # 1 hour
        )
        
        # Determine policy action based on security score and risks
        action = SecurityAction.ALLOW
        message = None
        restrictions = []
        
        # Critical risks - block access
        critical_risks = [r for r in status.risks if r.severity == RiskSeverity.CRITICAL]
        if critical_risks or status.security_score < 30:
            action = SecurityAction.BLOCK
            message = "Device security requirements not met. Please use a secure device."
            
            # Log critical security event
            for risk in critical_risks:
                await security_monitor.log_event(
                    event_type=SecurityEventType.CRITICAL_RISK_DETECTED,
                    user_id=str(current_user.id) if current_user else None,
                    ip_address=x_real_ip,
                    details={
                        "device_id": status.device_id,
                        "risk_type": risk.type,
                        "description": risk.description
                    }
                )
        
        # High risks - restrict features
        elif status.security_score < 70:
            action = SecurityAction.RESTRICT
            message = "Some features are restricted due to security concerns."
            
            # Apply restrictions based on specific risks
            if status.is_jailbroken or status.is_rooted:
                restrictions.extend([
                    "no_payment_processing",
                    "no_sensitive_data_storage",
                    "limited_offline_access"
                ])
            
            if status.is_debugging_enabled:
                restrictions.append("no_production_data")
            
            if status.is_emulator:
                restrictions.extend([
                    "no_biometric_auth",
                    "no_location_services"
                ])
            
            if status.is_tampered:
                restrictions.extend([
                    "require_app_reinstall",
                    "no_cached_credentials"
                ])
        
        # Medium risks - warn user
        elif status.security_score < 90:
            action = SecurityAction.WARN
            message = "Minor security risks detected. Consider addressing them for optimal security."
        
        # Check app version requirements
        min_version = "1.0.0"  # Minimum required version
        if status.app_version < min_version:
            return SecurityPolicyResponse(
                action=SecurityAction.BLOCK,
                message="App version too old. Please update to continue.",
                restrictions=[],
                require_update=True,
                min_app_version=min_version
            )
        
        # Store user device mapping if authenticated
        if current_user:
            device_key = f"user_device:{current_user.id}:{status.device_id}"
            await cache_manager.set(
                device_key,
                {
                    "platform": status.platform,
                    "last_seen": datetime.utcnow().isoformat(),
                    "security_score": status.security_score
                },
                expire=86400  # 24 hours
            )
        
        return SecurityPolicyResponse(
            action=action,
            message=message,
            restrictions=restrictions,
            require_update=False,
            min_app_version=None
        )
        
    except Exception as e:
        logger.error(f"Error processing security report: {e}")
        raise HTTPException(status_code=500, detail="Failed to process security report")


@router.get("/policy")
async def get_security_policy(
    platform: str = "ios",
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    Get security policy for the platform.
    
    Returns security requirements and recommendations.
    """
    policies = {
        "ios": {
            "min_os_version": "14.0",
            "block_jailbroken": True,
            "allow_debugging": False,
            "allow_emulator": False,
            "min_security_score": 70,
            "features": {
                "certificate_pinning": True,
                "anti_debugging": True,
                "background_blur": True,
                "biometric_auth": True
            }
        },
        "android": {
            "min_os_version": "29",  # Android 10
            "min_sdk_version": 29,
            "block_rooted": True,
            "allow_debugging": False,
            "allow_emulator": False,
            "min_security_score": 70,
            "features": {
                "certificate_pinning": True,
                "anti_debugging": True,
                "screenshot_blocking": True,
                "biometric_auth": True,
                "safetynet_attestation": True
            }
        }
    }
    
    return {
        "platform": platform,
        "policy": policies.get(platform, policies["ios"]),
        "last_updated": "2025-07-11T10:00:00Z",
        "enforcement_level": "strict" if not current_user else "standard"
    }


@router.get("/device/{device_id}/history")
async def get_device_security_history(
    device_id: str,
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get security history for a specific device.
    
    Only accessible by the device owner.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Verify device ownership
    device_key = f"user_device:{current_user.id}:{device_id}"
    device_info = await cache_manager.get(device_key)
    
    if not device_info:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Get recent security reports
    cache_key = f"device_security:{device_id}"
    current_status = await cache_manager.get(cache_key)
    
    return {
        "device_id": device_id,
        "platform": device_info.get("platform"),
        "last_seen": device_info.get("last_seen"),
        "current_status": current_status,
        "history": []  # In production, this would query historical data
    }


@router.post("/incident")
async def report_security_incident(
    incident: Dict[str, Any],
    current_user: Optional[User] = Depends(get_current_user_optional),
    x_real_ip: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Report a security incident from mobile device.
    
    Used for reporting detected attacks, suspicious activity, etc.
    """
    try:
        # Log security incident
        await security_monitor.log_event(
            event_type=SecurityEventType.MOBILE_INCIDENT,
            user_id=str(current_user.id) if current_user else None,
            ip_address=x_real_ip,
            details=incident
        )
        
        # Analyze incident severity
        severity = incident.get("severity", "medium")
        
        # Take immediate action for critical incidents
        if severity == "critical":
            device_id = incident.get("device_id")
            if device_id:
                # Mark device as compromised
                await cache_manager.set(
                    f"compromised_device:{device_id}",
                    {
                        "incident": incident,
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    expire=86400  # 24 hours
                )
        
        return {
            "status": "reported",
            "incident_id": f"inc_{datetime.utcnow().timestamp()}",
            "message": "Security incident has been logged and will be investigated"
        }
        
    except Exception as e:
        logger.error(f"Error reporting security incident: {e}")
        raise HTTPException(status_code=500, detail="Failed to report incident")


@router.get("/stats")
async def get_mobile_security_stats(
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get mobile security statistics.
    
    Admin endpoint for monitoring overall mobile security health.
    """
    # This would typically require admin privileges
    # For now, return mock statistics
    
    return {
        "total_devices": 1000,
        "platforms": {
            "ios": 600,
            "android": 400
        },
        "security_scores": {
            "excellent": 450,  # 90-100
            "good": 300,       # 70-89
            "fair": 150,       # 50-69
            "poor": 100        # 0-49
        },
        "common_risks": [
            {
                "type": "OUTDATED_OS",
                "count": 180,
                "percentage": 18
            },
            {
                "type": "VPN",
                "count": 120,
                "percentage": 12
            },
            {
                "type": "DEBUGGING",
                "count": 50,
                "percentage": 5
            },
            {
                "type": "JAILBREAK",
                "count": 30,
                "percentage": 3
            },
            {
                "type": "ROOT",
                "count": 20,
                "percentage": 2
            }
        ],
        "blocked_devices": 50,
        "restricted_devices": 150,
        "incidents_24h": 5,
        "last_updated": datetime.utcnow().isoformat()
    }