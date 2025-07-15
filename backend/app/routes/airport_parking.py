"""
Airport Parking Routes - Stub Implementation
TODO: Implement airport parking booking functionality
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.models.user import User
from app.core.auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/airport-parking/search")
async def search_airport_parking(
    airport_code: str,
    start_date: str,
    end_date: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search for airport parking options."""
    # TODO: Implement actual airport parking search
    return {
        "airport_code": airport_code,
        "parking_options": [],
        "message": "Airport parking search not implemented",
        "status": "stub_implementation"
    }


@router.post("/airport-parking/book")
async def book_airport_parking(
    parking_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Book airport parking."""
    # TODO: Implement actual airport parking booking
    logger.info(f"Airport parking booking attempted for user {current_user.id} (stub)")
    return {"message": "Airport parking booking not implemented", "status": "stub_implementation"}
