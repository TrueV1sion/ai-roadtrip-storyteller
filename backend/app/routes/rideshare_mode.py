"""
Rideshare Mode Routes - Stub Implementation
TODO: Implement rideshare-specific functionality
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.models.user import User
from app.core.auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/rideshare-mode/status")
async def get_rideshare_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current rideshare mode status."""
    # TODO: Implement actual rideshare status logic
    return {
        "rideshare_mode": False,
        "driver_mode": False,
        "passenger_mode": False,
        "status": "stub_implementation"
    }


@router.post("/rideshare-mode/enable")
async def enable_rideshare_mode(
    mode: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enable rideshare mode (driver or passenger)."""
    # TODO: Implement actual rideshare mode logic
    logger.info(f"Rideshare mode {mode} enabled for user {current_user.id} (stub)")
    return {"message": f"Rideshare mode {mode} enabled", "status": "stub_implementation"}


@router.post("/rideshare-mode/disable")
async def disable_rideshare_mode(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disable rideshare mode."""
    # TODO: Implement actual rideshare mode logic
    logger.info(f"Rideshare mode disabled for user {current_user.id} (stub)")
    return {"message": "Rideshare mode disabled", "status": "stub_implementation"}
