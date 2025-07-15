"""
Airport Amenities Routes - Stub Implementation
TODO: Implement airport amenities information
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.models.user import User
from app.core.auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/airport-amenities/{airport_code}")
async def get_airport_amenities(
    airport_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get airport amenities information."""
    # TODO: Implement actual airport amenities lookup
    return {
        "airport_code": airport_code,
        "amenities": {
            "restaurants": [],
            "shops": [],
            "lounges": [],
            "services": []
        },
        "message": "Airport amenities lookup not implemented",
        "status": "stub_implementation"
    }


@router.get("/airport-amenities/{airport_code}/restaurants")
async def get_airport_restaurants(
    airport_code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get airport restaurant information."""
    # TODO: Implement actual airport restaurant lookup
    return {
        "airport_code": airport_code,
        "restaurants": [],
        "message": "Airport restaurant lookup not implemented",
        "status": "stub_implementation"
    }
