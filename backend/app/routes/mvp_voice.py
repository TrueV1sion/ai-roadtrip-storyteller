"""
MVP Voice Routes - Basic Voice Processing
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.models.user import User
from app.core.auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/mvp-voice/process")
async def process_voice_mvp(
    audio_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Process voice input (MVP version)."""
    # TODO: Implement actual voice processing
    logger.info(f"Voice processing requested for user {current_user.id} (MVP stub)")
    return {
        "message": "Voice processed",
        "transcript": "Sample transcript",
        "status": "mvp_stub_implementation"
    }


@router.get("/mvp-voice/status")
async def get_voice_status_mvp(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get voice processing status (MVP version)."""
    return {
        "voice_enabled": True,
        "processing_available": True,
        "status": "mvp_stub_implementation"
    }
