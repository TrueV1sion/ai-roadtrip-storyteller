"""
Spotify integration routes for authentication and music management.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Response, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import secrets
from datetime import datetime, timedelta

from app.database import get_db
from app.core.auth import get_current_user
from app.core.cache import get_cache
from app.core.logger import get_logger
from app.services.spotify_service import spotify_service
from app.services.music_service import music_service
from app.models.user import User
from app.schemas.user import User as UserSchema

logger = get_logger(__name__)
cache = get_cache()
router = APIRouter(prefix="/spotify", tags=["spotify"])


# In-memory state storage (in production, use Redis or database)
auth_states = {}


@router.get("/auth")
async def spotify_auth(
    request: Request,
    current_user: UserSchema = Depends(get_current_user)
):
    """Initiate Spotify OAuth flow."""
    try:
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        auth_states[state] = {
            "user_id": current_user.id,
            "timestamp": datetime.now()
        }
        
        # Clean up old states
        cutoff = datetime.now() - timedelta(minutes=10)
        auth_states = {k: v for k, v in auth_states.items() 
                      if v["timestamp"] > cutoff}
        
        # Get request scheme for proper redirect URI
        request_scheme = request.url.scheme
        auth_url = spotify_service.get_auth_url(state, request_scheme)
        return {"auth_url": auth_url}
    except Exception as e:
        logger.error(f"Failed to initiate Spotify auth: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate authentication")


@router.get("/callback")
async def spotify_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db)
):
    """Handle Spotify OAuth callback."""
    try:
        # Verify state
        if state not in auth_states:
            raise HTTPException(status_code=400, detail="Invalid state parameter")
        
        user_id = auth_states[state]["user_id"]
        del auth_states[state]  # Use state only once
        
        # Get request scheme for proper redirect URI
        request_scheme = request.url.scheme
        
        # Exchange code for token
        auth_response = await spotify_service.exchange_code_for_token(code, request_scheme)
        
        # Store tokens in database (encrypted in production)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Store tokens in user preferences
        if not user.preferences:
            user.preferences = {}
        
        user.preferences["spotify_access_token"] = auth_response.access_token
        user.preferences["spotify_refresh_token"] = auth_response.refresh_token
        user.preferences["spotify_token_expires"] = (
            datetime.now() + timedelta(seconds=auth_response.expires_in)
        ).isoformat()
        
        db.commit()
        
        # Redirect to success page
        return RedirectResponse(url="/spotify/success", status_code=302)
    except Exception as e:
        logger.error(f"Failed to handle Spotify callback: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed")


@router.get("/success")
async def spotify_success():
    """Success page after Spotify authentication."""
    return {
        "message": "Spotify connected successfully!",
        "status": "authenticated"
    }


@router.get("/profile")
async def get_spotify_profile(
    current_user: UserSchema = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's Spotify profile."""
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        access_token = user.preferences.get("spotify_access_token") if user.preferences else None
        
        if not access_token:
            raise HTTPException(status_code=401, detail="Spotify not connected")
        
        profile = await spotify_service.get_user_profile(access_token)
        return profile
    except Exception as e:
        logger.error(f"Failed to get Spotify profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to get profile")


@router.post("/playlist/journey")
async def create_journey_playlist(
    journey_name: str,
    duration_minutes: int,
    mood: str = "balanced",
    locations: List[str] = None,
    current_user: UserSchema = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a journey-specific playlist."""
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        access_token = user.preferences.get("spotify_access_token") if user.preferences else None
        
        if not access_token:
            raise HTTPException(status_code=401, detail="Spotify not connected")
        
        # Check if token needs refresh
        token_expires = user.preferences.get("spotify_token_expires")
        if token_expires and datetime.fromisoformat(token_expires) < datetime.now():
            refresh_token = user.preferences.get("spotify_refresh_token")
            if refresh_token:
                auth_response = await spotify_service.refresh_access_token(refresh_token)
                user.preferences["spotify_access_token"] = auth_response.access_token
                user.preferences["spotify_token_expires"] = (
                    datetime.now() + timedelta(seconds=auth_response.expires_in)
                ).isoformat()
                db.commit()
                access_token = auth_response.access_token
        
        playlist = await spotify_service.create_journey_playlist(
            access_token,
            journey_name,
            duration_minutes,
            mood,
            locations
        )
        
        return {
            "playlist_id": playlist.id,
            "playlist_name": playlist.name,
            "description": playlist.description,
            "tracks_count": len(playlist.tracks),
            "duration_minutes": sum(t.duration_ms for t in playlist.tracks) // 60000,
            "collaborative": playlist.collaborative
        }
    except Exception as e:
        logger.error(f"Failed to create journey playlist: {e}")
        raise HTTPException(status_code=500, detail="Failed to create playlist")


@router.get("/music/location")
async def get_location_music(
    location: str,
    limit: int = 10,
    current_user: UserSchema = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get music recommendations for a specific location."""
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        access_token = user.preferences.get("spotify_access_token") if user.preferences else None
        
        if not access_token:
            raise HTTPException(status_code=401, detail="Spotify not connected")
        
        tracks = await spotify_service.get_location_based_tracks(
            access_token,
            location,
            limit
        )
        
        return {
            "location": location,
            "tracks": [
                {
                    "id": track.id,
                    "name": track.name,
                    "artist": track.artist,
                    "album": track.album,
                    "duration_seconds": track.duration_ms // 1000,
                    "uri": track.uri,
                    "preview_url": track.preview_url
                }
                for track in tracks
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get location music: {e}")
        raise HTTPException(status_code=500, detail="Failed to get music")


@router.get("/playback/current")
async def get_current_playback(
    current_user: UserSchema = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current playback state."""
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        access_token = user.preferences.get("spotify_access_token") if user.preferences else None
        
        if not access_token:
            raise HTTPException(status_code=401, detail="Spotify not connected")
        
        playback = await spotify_service.get_current_playback(access_token)
        
        if not playback:
            return {"is_playing": False}
        
        return {
            "is_playing": playback.get("is_playing", False),
            "device": playback.get("device", {}).get("name"),
            "track": {
                "name": playback.get("item", {}).get("name"),
                "artist": playback.get("item", {}).get("artists", [{}])[0].get("name"),
                "album": playback.get("item", {}).get("album", {}).get("name")
            } if playback.get("item") else None,
            "progress_ms": playback.get("progress_ms"),
            "duration_ms": playback.get("item", {}).get("duration_ms")
        }
    except Exception as e:
        logger.error(f"Failed to get current playback: {e}")
        raise HTTPException(status_code=500, detail="Failed to get playback state")


@router.post("/playback/control/{action}")
async def control_playback(
    action: str,
    device_id: Optional[str] = None,
    current_user: UserSchema = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Control playback (play, pause, next, previous)."""
    try:
        if action not in ["play", "pause", "next", "previous"]:
            raise HTTPException(status_code=400, detail="Invalid action")
        
        user = db.query(User).filter(User.id == current_user.id).first()
        access_token = user.preferences.get("spotify_access_token") if user.preferences else None
        
        if not access_token:
            raise HTTPException(status_code=401, detail="Spotify not connected")
        
        success = await spotify_service.control_playback(
            access_token,
            action,
            device_id
        )
        
        return {"success": success, "action": action}
    except Exception as e:
        logger.error(f"Failed to control playback: {e}")
        raise HTTPException(status_code=500, detail="Failed to control playback")


@router.post("/playback/volume")
async def set_volume(
    volume_percent: int,
    device_id: Optional[str] = None,
    current_user: UserSchema = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Set playback volume (0-100)."""
    try:
        if not 0 <= volume_percent <= 100:
            raise HTTPException(status_code=400, detail="Volume must be between 0 and 100")
        
        user = db.query(User).filter(User.id == current_user.id).first()
        access_token = user.preferences.get("spotify_access_token") if user.preferences else None
        
        if not access_token:
            raise HTTPException(status_code=401, detail="Spotify not connected")
        
        success = await spotify_service.set_volume(
            access_token,
            volume_percent,
            device_id
        )
        
        return {"success": success, "volume": volume_percent}
    except Exception as e:
        logger.error(f"Failed to set volume: {e}")
        raise HTTPException(status_code=500, detail="Failed to set volume")


@router.post("/journey/soundtrack")
async def create_journey_soundtrack(
    route_points: List[dict],
    duration_hours: float,
    preferences: dict,
    current_user: UserSchema = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a complete journey soundtrack with music adapted to route."""
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        access_token = user.preferences.get("spotify_access_token") if user.preferences else None
        
        soundtrack = await music_service.create_journey_soundtrack(
            route_points,
            duration_hours,
            preferences,
            access_token
        )
        
        return soundtrack
    except Exception as e:
        logger.error(f"Failed to create journey soundtrack: {e}")
        raise HTTPException(status_code=500, detail="Failed to create soundtrack")


# Add missing imports
from datetime import datetime, timedelta