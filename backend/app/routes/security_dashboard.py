"""
Security Dashboard Routes - Stub Implementation
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.models.user import User
from app.core.auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/security-dashboard")
async def get_security_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get security dashboard data."""
    return {
        "overview": {
            "threat_level": "low",
            "active_monitoring": True,
            "last_update": "2024-01-01T00:00:00Z"
        },
        "metrics": {
            "total_scans": 0,
            "threats_detected": 0,
            "threats_blocked": 0
        },
        "status": "stub_implementation"
    }
