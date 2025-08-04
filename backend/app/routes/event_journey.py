from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from app.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.story import EventJourney
from app.schemas.story import (
    EventJourneyRequest,
    EventJourneyResponse,
    EventJourneyUpdate,
    EventSearchRequest
)
from app.services.event_journey_service import EventJourneyService
from app.integrations.ticketmaster_client import ticketmaster_client
from app.core.logger import logger

router = APIRouter(prefix="/api/event-journeys", tags=["event-journeys"])
event_journey_service = EventJourneyService()


@router.post("/create", response_model=EventJourneyResponse)
async def create_event_journey(
    request: EventJourneyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new event journey for a ticketed event."""
    try:
        # Create the event journey
        journey_data = await event_journey_service.create_event_journey(
            user_id=current_user.id,
            origin=request.origin,
            event_id=request.event_id,
            preferences=request.preferences
        )
        
        # Save to database
        event_journey = EventJourney(
            user_id=current_user.id,
            event_id=journey_data["event"]["id"],
            event_name=journey_data["event"]["name"],
            event_type=journey_data["event"]["classifications"][0]["segment"] if journey_data["event"]["classifications"] else None,
            event_date=journey_data["event"]["dates"]["start"]["dateTime"],
            venue_id=journey_data["event"]["venue"].get("id"),
            venue_name=journey_data["event"]["venue"]["name"],
            venue_address=journey_data["event"]["venue"]["address"],
            venue_lat=journey_data["event"]["venue"]["location"]["latitude"],
            venue_lon=journey_data["event"]["venue"]["location"]["longitude"],
            origin_address=request.origin,
            origin_lat=journey_data["route"]["start_location"]["lat"],
            origin_lon=journey_data["route"]["start_location"]["lng"],
            departure_time=journey_data["departure_time"],
            estimated_arrival=journey_data["estimated_arrival"],
            voice_personality=journey_data["voice_personality"],
            journey_content=journey_data["journey_content"],
            theme=journey_data["journey_content"]["theme"],
            preferences=request.preferences
        )
        
        db.add(event_journey)
        db.commit()
        db.refresh(event_journey)
        
        return event_journey
        
    except Exception as e:
        logger.error(f"Error creating event journey: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/search-events")
async def search_events(
    keyword: Optional[str] = Query(None),
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    radius: int = Query(50),
    event_type: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """Search for events near a location or by keyword."""
    try:
        events = await ticketmaster_client.search_events(
            keyword=keyword,
            lat=lat,
            lon=lon,
            radius=radius,
            start_datetime=start_date,
            end_datetime=end_date
        )
        
        # Extract and format event data
        event_list = []
        for event in events.get("_embedded", {}).get("events", []):
            event_data = await ticketmaster_client.extract_event_metadata(event)
            event_list.append(event_data)
        
        return {"events": event_list, "total": len(event_list)}
        
    except Exception as e:
        logger.error(f"Error searching events: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/my-journeys", response_model=List[EventJourneyResponse])
async def get_user_journeys(
    status: Optional[str] = Query(None),
    upcoming_only: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all event journeys for the current user."""
    query = db.query(EventJourney).filter(EventJourney.user_id == current_user.id)
    
    if status:
        query = query.filter(EventJourney.status == status)
    
    if upcoming_only:
        query = query.filter(EventJourney.event_date >= datetime.now())
    
    journeys = query.order_by(EventJourney.event_date).all()
    return journeys


@router.get("/{journey_id}", response_model=EventJourneyResponse)
async def get_journey_details(
    journey_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get details of a specific event journey."""
    journey = db.query(EventJourney).filter(
        EventJourney.id == journey_id,
        EventJourney.user_id == current_user.id
    ).first()
    
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")
    
    return journey


@router.patch("/{journey_id}", response_model=EventJourneyResponse)
async def update_journey(
    journey_id: str,
    update_data: EventJourneyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an event journey (status, rating, feedback, etc)."""
    journey = db.query(EventJourney).filter(
        EventJourney.id == journey_id,
        EventJourney.user_id == current_user.id
    ).first()
    
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")
    
    # Update fields
    update_dict = update_data.dict(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(journey, field, value)
    
    db.commit()
    db.refresh(journey)
    
    return journey


@router.post("/{journey_id}/start")
async def start_journey(
    journey_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a journey as started."""
    journey = db.query(EventJourney).filter(
        EventJourney.id == journey_id,
        EventJourney.user_id == current_user.id
    ).first()
    
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")
    
    journey.status = "in_progress"
    journey.actual_departure = datetime.now()
    
    db.commit()
    
    return {"message": "Journey started", "journey_id": journey_id}


@router.post("/{journey_id}/complete")
async def complete_journey(
    journey_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a journey as completed."""
    journey = db.query(EventJourney).filter(
        EventJourney.id == journey_id,
        EventJourney.user_id == current_user.id
    ).first()
    
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")
    
    journey.status = "completed"
    journey.actual_arrival = datetime.now()
    
    db.commit()
    
    return {"message": "Journey completed", "journey_id": journey_id}


@router.get("/{journey_id}/pregame-suggestions")
async def get_pregame_suggestions(
    journey_id: str,
    current_location_lat: float = Query(...),
    current_location_lon: float = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get pregame activity suggestions near the venue."""
    journey = db.query(EventJourney).filter(
        EventJourney.id == journey_id,
        EventJourney.user_id == current_user.id
    ).first()
    
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")
    
    # Calculate time until event
    time_until_event = (journey.event_date - datetime.now()).total_seconds() / 60  # minutes
    
    if time_until_event < 0:
        raise HTTPException(status_code=400, detail="Event has already started")
    
    suggestions = await event_journey_service.suggest_pregame_activities(
        event_id=journey.event_id,
        current_location=(current_location_lat, current_location_lon),
        time_available=int(time_until_event)
    )
    
    return {"suggestions": suggestions, "time_available_minutes": int(time_until_event)}


@router.delete("/{journey_id}")
async def delete_journey(
    journey_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an event journey."""
    journey = db.query(EventJourney).filter(
        EventJourney.id == journey_id,
        EventJourney.user_id == current_user.id
    ).first()
    
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")
    
    db.delete(journey)
    db.commit()
    
    return {"message": "Journey deleted", "journey_id": journey_id}