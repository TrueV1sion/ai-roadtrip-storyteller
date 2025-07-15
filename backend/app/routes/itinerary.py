from fastapi import APIRouter, HTTPException
from backend.app.services.itinerary_service import generate_itinerary

router = APIRouter()


@router.get(
    "/itinerary",
    tags=["Itinerary"]
)
async def get_itinerary():
    """
    Fetch the consolidated itinerary including reservations and pit stops.
    """
    try:
        itinerary = generate_itinerary()
        return itinerary
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Error generating itinerary"
        ) from e 