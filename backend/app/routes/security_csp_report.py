"""
CSP Violation Reporting Endpoint
Receives and processes Content Security Policy violation reports
"""

from fastapi import APIRouter, Request, Response
from fastapi.responses import Response as FastAPIResponse
import logging
from typing import Dict, Any
from ..core.security_headers import CSPReportingEndpoint
from ..monitoring.security_metrics import security_metrics
from ..monitoring.audit_logger import audit_logger

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/api/v1/security/csp-report")
async def csp_violation_report(request: Request) -> FastAPIResponse:
    """
    Receive CSP violation reports from browsers
    
    Browsers automatically send violation reports to this endpoint
    when Content Security Policy rules are violated.
    """
    # Handle the CSP report
    response = await CSPReportingEndpoint.handle_csp_report(request)
    
    # Track metric
    await security_metrics.track_csp_violation()
    
    # Log to audit system
    try:
        report_data = await request.json()
        await audit_logger.log_security_event(
            event_type="csp_violation",
            severity="WARNING",
            details={
                "csp_report": report_data,
                "user_agent": request.headers.get("user-agent", "unknown"),
                "ip_address": request.client.host if request.client else "unknown"
            }
        )
    except Exception as e:
        logger.error(f"Failed to log CSP violation: {e}")
    
    return response


@router.get("/api/v1/security/csp-nonce")
async def get_csp_nonce(request: Request) -> Dict[str, str]:
    """
    Get the current CSP nonce for this request
    
    This endpoint is useful for JavaScript applications that need
    to dynamically create script or style elements.
    """
    nonce = getattr(request.state, "csp_nonce", None)
    
    if not nonce:
        logger.warning("CSP nonce requested but not found in request state")
        return {"error": "CSP nonce not available"}
    
    return {"nonce": nonce}


@router.get("/api/v1/security/headers-info")
async def security_headers_info() -> Dict[str, Any]:
    """
    Get information about security headers configuration
    
    This endpoint is for debugging and monitoring purposes only.
    Should be restricted to admin users in production.
    """
    return {
        "csp_enabled": True,
        "nonce_based_csp": True,
        "hsts_enabled": True,
        "cors_restricted": True,
        "request_body_limits": {
            "default": "10MB",
            "uploads": "50MB",
            "api_calls": "1MB"
        },
        "security_features": [
            "CSP with nonce support",
            "Strict CORS policy",
            "Request body size limits",
            "XSS protection via CSP",
            "Clickjacking protection",
            "MIME type sniffing prevention",
            "Comprehensive permissions policy",
            "HSTS with preload",
            "Cross-origin isolation"
        ]
    }