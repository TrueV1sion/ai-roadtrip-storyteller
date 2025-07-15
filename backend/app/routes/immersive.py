from fastapi import APIRouter, HTTPException, Depends, Request, Query # Added Query
from typing import Dict, List, Optional
import base64
import hashlib
from pydantic import BaseModel, Field

from app.core.ai_client import ai_client
# from app.core.google_ai_client import google_ai_client # Removed - Using ai_client only
from app.services.music_service import music_service
from app.services.tts_service import tts_synthesizer
from app.core.logger import get_logger
from app.core.cache import cacheable, redis_client, generate_cache_key
from app.core.config import settings
from sqlalchemy.orm import Session # Added Session
from app.db.base import get_db # Or your actual path to get_db
from app.crud import user_saved_experience_crud
from app.schemas.experience import (
    ExperienceSavePayload, 
    SavedExperienceItem, 
    ExperienceHistoryResponse,
    UserSavedExperienceCreate # For constructing object for CRUD
)
from app.models.user import User # For current_user dependency
from app.core.auth import get_current_active_user # Assuming this is your auth dependency
from app.services.tts_service import tts_synthesizer # For permanent TTS storage
from app.schemas.experience import PlaylistSchema, LocationSchema, ImmersiveContextSchema # For manual Pydantic construction

logger = get_logger(__name__)
router = APIRouter()


class LocationData(BaseModel):
    latitude: float
    longitude: float


class ImmersiveContext(BaseModel):
    time_of_day: Optional[str] = None
    weather: Optional[str] = None
    mood: Optional[str] = None


class ImmersiveRequest(BaseModel):
    conversation_id: str
    location: LocationData
    interests: List[str]
    context: Optional[ImmersiveContext] = None


class Track(BaseModel):
    id: str
    title: str
    artist: str
    uri: str
    duration_ms: int


class Playlist(BaseModel):
    playlist_name: str
    tracks: List[Track]
    provider: str


class ImmersiveResponse(BaseModel):
    story: str
    playlist: Playlist
    # tts_audio: str # Changed from base64 bytes
    tts_audio_url: Optional[str] # Now returns a URL or None


@router.post("/immersive/save", response_model=SavedExperienceItem, tags=["Immersive History"])
async def save_immersive_experience(
    *,
    db: Session = Depends(get_db),
    experience_data: ExperienceSavePayload,
    current_user: User = Depends(get_current_active_user)
):
    """
    Save an immersive experience for the current user.
    """
    logger.info(f"User {current_user.id} attempting to save an immersive experience.")

    gcs_path_for_tts = None
    if experience_data.story:
        try:
            gcs_path_for_tts = tts_synthesizer.synthesize_and_store_permanently(
                text=experience_data.story
            )
            if gcs_path_for_tts:
                logger.info(f"Story TTS audio stored permanently at GCS path: {gcs_path_for_tts}")
            else:
                logger.warning(f"Failed to store story TTS audio permanently for user {current_user.id}.")
        except Exception as e:
            logger.error(f"Error during permanent TTS storage for user {current_user.id}: {str(e)}")

    saved_experience_create_data = UserSavedExperienceCreate(
        user_id=current_user.id,
        story=experience_data.story,
        playlist=experience_data.playlist, # This is PlaylistSchema from payload
        location=experience_data.location,
        interests=experience_data.interests,
        context=experience_data.context,
        tts_audio_identifier=gcs_path_for_tts
    )

    try:
        saved_item_orm = user_saved_experience_crud.create_saved_experience(
            db=db, obj_in=saved_experience_create_data
        )
        
        response_tts_url = None
        if saved_item_orm.tts_audio_identifier:
            response_tts_url = tts_synthesizer.get_signed_url_for_gcs_path(
                saved_item_orm.tts_audio_identifier
            )
            if not response_tts_url:
                 logger.warning(f"Could not generate signed URL for GCS path: {saved_item_orm.tts_audio_identifier} for immediate response.")

        # Construct Pydantic response model from ORM object
        response_item = SavedExperienceItem(
            id=str(saved_item_orm.id),
            story_text=saved_item_orm.story_text,
            playlist=PlaylistSchema(
                playlist_name=saved_item_orm.playlist_name,
                tracks=saved_item_orm.playlist_tracks, # Already list of dicts from model/CRUD
                provider=saved_item_orm.playlist_provider
            ),
            location=LocationSchema(latitude=saved_item_orm.location_latitude, longitude=saved_item_orm.location_longitude) if saved_item_orm.location_latitude is not None else None,
            interests=saved_item_orm.interests,
            context=ImmersiveContextSchema(
                time_of_day=saved_item_orm.context_time_of_day,
                weather=saved_item_orm.context_weather,
                mood=saved_item_orm.context_mood
            ),
            generated_at=saved_item_orm.generated_at,
            saved_at=saved_item_orm.saved_at,
            tts_audio_url=response_tts_url
        )
        return response_item
    except Exception as e:
        logger.error(f"Error saving experience for user {current_user.id}: {str(e)}")
        # Consider more specific error handling based on exception type
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Failed to save experience: {str(e)}")


@router.get("/immersive/history", response_model=ExperienceHistoryResponse, tags=["Immersive History"])
async def get_user_immersive_history(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size")
):
    """
    Retrieve a paginated list of saved immersive experiences for the current user.
    """
    logger.info(f"Fetching immersive history for user {current_user.id}, page={page}, size={size}")
    
    skip = (page - 1) * size
    saved_experiences = user_saved_experience_crud.get_saved_experiences_by_user(
        db=db, user_id=current_user.id, skip=skip, limit=size
    )
    db_items = user_saved_experience_crud.get_saved_experiences_by_user(
        db=db, user_id=current_user.id, skip=skip, limit=size
    )
    total_items = user_saved_experience_crud.count_saved_experiences_by_user(
        db=db, user_id=current_user.id
    )

    response_items: List[SavedExperienceItem] = []
    for item_orm in db_items:
        item_tts_url = None
        if item_orm.tts_audio_identifier:
            try:
                item_tts_url = tts_synthesizer.get_signed_url_for_gcs_path(
                    item_orm.tts_audio_identifier
                )
                if not item_tts_url:
                    logger.warning(f"Could not generate signed URL for GCS path: {item_orm.tts_audio_identifier} for history item ID: {item_orm.id}")
            except Exception as e:
                logger.error(f"Error generating signed URL for history item ID {item_orm.id}: {str(e)}")
        
        playlist_schema_tracks = [TrackSchema(**track) for track in item_orm.playlist_tracks] if item_orm.playlist_tracks else []

        pydantic_item = SavedExperienceItem(
            id=str(item_orm.id),
            story_text=item_orm.story_text,
            playlist=PlaylistSchema(
                playlist_name=item_orm.playlist_name,
                tracks=playlist_schema_tracks,
                provider=item_orm.playlist_provider
            ),
            location=LocationSchema(latitude=item_orm.location_latitude, longitude=item_orm.location_longitude) if item_orm.location_latitude is not None else None,
            interests=item_orm.interests,
            context=ImmersiveContextSchema(
                time_of_day=item_orm.context_time_of_day,
                weather=item_orm.context_weather,
                mood=item_orm.context_mood
            ) if item_orm.context_time_of_day or item_orm.context_weather or item_orm.context_mood else None, # Ensure context is None if all fields are None
            generated_at=item_orm.generated_at,
            saved_at=item_orm.saved_at,
            tts_audio_url=item_tts_url
        )
        response_items.append(pydantic_item)

    return ExperienceHistoryResponse(
        items=response_items,
        total=total_items,
        page=page,
        size=size
    )


def _get_immersive_cache_key(payload: ImmersiveRequest) -> str:
    """
    Generate a cache key for immersive experience requests.
    
    Args:
        payload: The immersive request payload
        
    Returns:
        str: Cache key
    """
    # Round coordinates to 4 decimal places for better cache hits
    lat = round(payload.location.latitude, 4)
    lng = round(payload.location.longitude, 4)
    
    # Sort interests for consistent key generation
    interests = sorted(payload.interests)
    
    # Extract context parameters if available
    time_of_day = payload.context.time_of_day if payload.context else None
    weather = payload.context.weather if payload.context else None
    mood = payload.context.mood if payload.context else None
    
    # Create a hash of the parameters
    params_dict = {
        "lat": lat,
        "lng": lng,
        "interests": ",".join(interests),
        "time_of_day": time_of_day,
        "weather": weather,
        "mood": mood
    }
    
    return generate_cache_key("immersive", None, params_dict)


@router.post("/immersive", tags=["Immersive"], response_model=ImmersiveResponse)
@cacheable(
    namespace="immersive",
    ttl=getattr(settings, "REDIS_CACHE_TTL_STORY", 86400),  # Default to 24 hours
    key_builder=lambda payload: _get_immersive_cache_key(payload) if isinstance(payload, ImmersiveRequest) else None,
    skip_cache_if=lambda request: request.headers.get("X-Skip-Cache") == "true"
)
async def get_immersive_experience(payload: ImmersiveRequest, request: Request = None):
    """
    Generate an immersive itinerary experience that integrates AI storytelling,
    music, and TTS synthesis.

    Expected payload:
    {
      "conversation_id": "abc123",
      "location": {
          "latitude": 12.34,
          "longitude": 56.78
      },
      "interests": ["history", "nature"],
      "context": {
          "time_of_day": "morning",
          "weather": "sunny",
          "mood": "happy"
      }
    }

    Returns:
    {
      "story": "AI generated story text",
      "playlist": { /* playlist object */ },
      "tts_audio_url": "URL to the generated audio file or null"
    }
    """
    # Generate story using the primary AI client (now Vertex AI)
    # The client itself handles fallbacks internally if needed.
    try:
        story = await ai_client.generate_story_with_session(
            conversation_id=payload.conversation_id,
            location=payload.location.dict(),
            interests=payload.interests,
            context=payload.context.dict() if payload.context else None
        )
    except Exception as e:
        # If the primary client (including its internal fallback) fails, raise HTTP error
        logger.error(f"Failed to generate story using AI client: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate story: {str(e)}"
        )

    try:
        # Generate playlist based on story and context
        context_dict = payload.context.dict() if payload.context else None
        
        # Try to get playlist from cache
        playlist_cache_key = generate_cache_key(
            "playlist", 
            None, 
            {
                "story_hash": hashlib.md5(story.encode()).hexdigest(),
                "context": str(context_dict)
            }
        )
        
        cached_playlist = redis_client.get(playlist_cache_key)
        if cached_playlist:
            logger.info(f"Cache hit for playlist: {playlist_cache_key}")
            playlist = cached_playlist # Assuming cached playlist is valid JSON/dict
        else:
            logger.info(f"Cache miss for playlist: {playlist_cache_key}")
            playlist = await music_service.generate_playlist(story, context_dict)
            playlist_ttl = getattr(settings, "REDIS_CACHE_TTL_PLAYLIST", 43200)
            # Ensure playlist is serializable (e.g., convert Pydantic model to dict if needed)
            redis_client.set(playlist_cache_key, json.dumps(playlist) if isinstance(playlist, BaseModel) else playlist, playlist_ttl)
        
        # Try to get TTS audio URL from cache
        # Cache key remains the same (based on story hash)
        tts_cache_key = generate_cache_key("tts_url", None, {"story_hash": hashlib.md5(story.encode()).hexdigest()}) # Changed namespace slightly
        cached_audio_url = redis_client.get(tts_cache_key)

        tts_audio_url: Optional[str] = None # Initialize URL variable

        if cached_audio_url:
            logger.info(f"Cache hit for TTS audio URL: {tts_cache_key}")
            tts_audio_url = cached_audio_url.decode('utf-8') # Decode bytes from Redis
        else:
            logger.info(f"Cache miss for TTS audio URL: {tts_cache_key}")
            # Synthesize speech and upload to GCS
            # Assuming tts_synthesizer now returns a URL or None
            tts_audio_url = tts_synthesizer.synthesize_and_upload(story)

            if not tts_audio_url:
                logger.error("Failed to synthesize speech or upload to GCS.")
                # Decide how to handle TTS failure: return null URL or raise error?
                # For now, we'll return null in the response.
                tts_audio_url = None
            else:
                 # Cache the Signed URL. The TTL should be less than the Signed URL's
                 # expiration time (currently 1 hour in tts_service.py).
                 # Set cache TTL to 55 minutes (3300 seconds).
                 signed_url_cache_ttl = 3300
                 redis_client.set(tts_cache_key, tts_audio_url, signed_url_cache_ttl)
        
        # Prepare final response
        response_payload = {
            "story": story,
            "playlist": playlist, # Ensure playlist is a dict/JSON serializable
            "tts_audio_url": tts_audio_url # Return the URL
        }

        return response_payload
        
    except Exception as e:
        # Log the specific error stage if possible (e.g., playlist generation vs TTS)
        raise HTTPException(
            status_code=500,
            detail=f"Error generating immersive experience: {str(e)}"
        )
