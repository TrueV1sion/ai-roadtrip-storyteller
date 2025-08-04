"""
Spotify integration service for AI Road Trip Storyteller.
Handles authentication, playlist creation, and music recommendations.
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException
from pydantic import BaseModel

from app.core.cache import get_cache
from app.core.config import get_settings
from app.core.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)
cache = get_cache()


class SpotifyTrack(BaseModel):
    id: str
    name: str
    artist: str
    album: str
    duration_ms: int
    preview_url: Optional[str]
    uri: str
    popularity: int
    energy: float
    valence: float
    tempo: float


class SpotifyPlaylist(BaseModel):
    id: str
    name: str
    description: Optional[str]
    tracks: List[SpotifyTrack]
    collaborative: bool = False
    public: bool = True


class SpotifyAuthResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str]
    scope: str


class SpotifyService:
    """Service for Spotify integration."""

    def __init__(self):
        self.client_id = settings.SPOTIFY_CLIENT_ID
        self.client_secret = settings.SPOTIFY_CLIENT_SECRET
        self.redirect_uri = settings.SPOTIFY_REDIRECT_URI
        self.base_url = "https://api.spotify.com/v1"
        self.auth_url = "https://accounts.spotify.com/authorize"
        self.token_url = "https://accounts.spotify.com/api/token"
        self.scopes = [
            "user-read-private",
            "user-read-email",
            "playlist-read-private",
            "playlist-modify-public",
            "playlist-modify-private",
            "user-library-read",
            "user-top-read",
            "user-read-playback-state",
            "user-modify-playback-state",
            "streaming"
        ]

    def get_auth_url(self, state: str, request_scheme: str = None) -> str:
        """Generate Spotify OAuth authorization URL."""
        # Use dynamic redirect URI based on environment and request scheme
        redirect_uri = settings.get_spotify_redirect_uri(request_scheme)
        
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": " ".join(self.scopes),
            "show_dialog": "true"
        }
        return f"{self.auth_url}?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str, request_scheme: str = None) -> SpotifyAuthResponse:
        """Exchange authorization code for access token."""
        # Use dynamic redirect URI based on environment and request scheme
        redirect_uri = settings.get_spotify_redirect_uri(request_scheme)
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.token_url,
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": redirect_uri,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret
                    }
                )
                response.raise_for_status()
                data = response.json()
                return SpotifyAuthResponse(**data)
            except httpx.HTTPError as e:
                logger.error(f"Failed to exchange code for token: {e}")
                raise HTTPException(status_code=400, detail="Failed to authenticate with Spotify")

    async def refresh_access_token(self, refresh_token: str) -> SpotifyAuthResponse:
        """Refresh expired access token."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.token_url,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret
                    }
                )
                response.raise_for_status()
                data = response.json()
                return SpotifyAuthResponse(**data)
            except httpx.HTTPError as e:
                logger.error(f"Failed to refresh token: {e}")
                raise HTTPException(status_code=401, detail="Failed to refresh Spotify token")

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        access_token: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make authenticated request to Spotify API with rate limiting."""
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            url = f"{self.base_url}/{endpoint}"
            
            # Implement exponential backoff for rate limiting
            max_retries = 3
            base_delay = 1  # seconds
            
            for attempt in range(max_retries):
                try:
                    response = await client.request(
                        method,
                        url,
                        headers=headers,
                        **kwargs
                    )
                    
                    # Handle rate limiting (429 status)
                    if response.status_code == 429:
                        retry_after = int(response.headers.get('Retry-After', base_delay * (2 ** attempt)))
                        logger.warning(f"Rate limited by Spotify. Waiting {retry_after} seconds...")
                        await asyncio.sleep(retry_after)
                        continue
                    
                    response.raise_for_status()
                    return response.json() if response.content else {}
                    
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429 and attempt < max_retries - 1:
                        # Exponential backoff
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Rate limited. Retrying in {delay} seconds...")
                        await asyncio.sleep(delay)
                        continue
                    elif e.response.status_code == 403:
                        # Check if it's a premium-only feature
                        error_data = e.response.json() if e.response.content else {}
                        if "PREMIUM_REQUIRED" in str(error_data.get("error", {}).get("reason", "")):
                            raise HTTPException(
                                status_code=403,
                                detail="This feature requires Spotify Premium"
                            )
                    raise
                except httpx.HTTPError as e:
                    logger.error(f"Spotify API request failed: {e}")
                    raise HTTPException(status_code=500, detail="Spotify API request failed")

    async def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """Get user's Spotify profile."""
        return await self._make_request("GET", "me", access_token)
    
    async def is_premium_user(self, access_token: str) -> bool:
        """Check if user has Spotify Premium."""
        try:
            profile = await self.get_user_profile(access_token)
            return profile.get("product") == "premium"
        except Exception as e:
            logger.error(f"Failed to check premium status: {e}")
            return False

    async def get_user_top_tracks(
        self,
        access_token: str,
        time_range: str = "medium_term",
        limit: int = 50
    ) -> List[SpotifyTrack]:
        """Get user's top tracks."""
        cache_key = f"spotify:top_tracks:{access_token[:10]}:{time_range}"
        cached = await cache.get(cache_key)
        if cached:
            return [SpotifyTrack(**track) for track in cached]

        data = await self._make_request(
            "GET",
            f"me/top/tracks?time_range={time_range}&limit={limit}",
            access_token
        )
        
        tracks = []
        for item in data.get("items", []):
            track = SpotifyTrack(
                id=item["id"],
                name=item["name"],
                artist=item["artists"][0]["name"],
                album=item["album"]["name"],
                duration_ms=item["duration_ms"],
                preview_url=item.get("preview_url"),
                uri=item["uri"],
                popularity=item["popularity"],
                energy=0.5,  # Will be populated by audio features
                valence=0.5,
                tempo=120.0
            )
            tracks.append(track)

        # Get audio features for tracks
        if tracks:
            track_ids = ",".join([t.id for t in tracks])
            features = await self._make_request(
                "GET",
                f"audio-features?ids={track_ids}",
                access_token
            )
            
            for i, feature in enumerate(features.get("audio_features", [])):
                if feature:
                    tracks[i].energy = feature.get("energy", 0.5)
                    tracks[i].valence = feature.get("valence", 0.5)
                    tracks[i].tempo = feature.get("tempo", 120.0)

        await cache.set(cache_key, [t.dict() for t in tracks], expire=3600)
        return tracks

    async def search_tracks(
        self,
        access_token: str,
        query: str,
        limit: int = 20
    ) -> List[SpotifyTrack]:
        """Search for tracks on Spotify."""
        data = await self._make_request(
            "GET",
            f"search?q={query}&type=track&limit={limit}",
            access_token
        )
        
        tracks = []
        for item in data.get("tracks", {}).get("items", []):
            track = SpotifyTrack(
                id=item["id"],
                name=item["name"],
                artist=item["artists"][0]["name"],
                album=item["album"]["name"],
                duration_ms=item["duration_ms"],
                preview_url=item.get("preview_url"),
                uri=item["uri"],
                popularity=item["popularity"],
                energy=0.5,
                valence=0.5,
                tempo=120.0
            )
            tracks.append(track)
        
        return tracks

    async def get_recommendations(
        self,
        access_token: str,
        seed_tracks: List[str] = None,
        seed_artists: List[str] = None,
        seed_genres: List[str] = None,
        target_energy: float = None,
        target_valence: float = None,
        target_tempo: float = None,
        limit: int = 20
    ) -> List[SpotifyTrack]:
        """Get track recommendations based on seeds and audio features."""
        params = {"limit": limit}
        
        if seed_tracks:
            params["seed_tracks"] = ",".join(seed_tracks[:5])
        if seed_artists:
            params["seed_artists"] = ",".join(seed_artists[:5])
        if seed_genres:
            params["seed_genres"] = ",".join(seed_genres[:5])
        
        if target_energy is not None:
            params["target_energy"] = target_energy
        if target_valence is not None:
            params["target_valence"] = target_valence
        if target_tempo is not None:
            params["target_tempo"] = target_tempo
        
        data = await self._make_request(
            "GET",
            f"recommendations?{urlencode(params)}",
            access_token
        )
        
        tracks = []
        for item in data.get("tracks", []):
            track = SpotifyTrack(
                id=item["id"],
                name=item["name"],
                artist=item["artists"][0]["name"],
                album=item["album"]["name"],
                duration_ms=item["duration_ms"],
                preview_url=item.get("preview_url"),
                uri=item["uri"],
                popularity=item["popularity"],
                energy=target_energy or 0.5,
                valence=target_valence or 0.5,
                tempo=target_tempo or 120.0
            )
            tracks.append(track)
        
        return tracks

    async def create_playlist(
        self,
        access_token: str,
        name: str,
        description: str = "",
        public: bool = True,
        collaborative: bool = False
    ) -> SpotifyPlaylist:
        """Create a new playlist."""
        user = await self.get_user_profile(access_token)
        user_id = user["id"]
        
        data = await self._make_request(
            "POST",
            f"users/{user_id}/playlists",
            access_token,
            json={
                "name": name,
                "description": description,
                "public": public,
                "collaborative": collaborative
            }
        )
        
        return SpotifyPlaylist(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            tracks=[],
            collaborative=collaborative,
            public=public
        )

    async def add_tracks_to_playlist(
        self,
        access_token: str,
        playlist_id: str,
        track_uris: List[str]
    ) -> bool:
        """Add tracks to a playlist."""
        # Spotify limits to 100 tracks per request
        for i in range(0, len(track_uris), 100):
            batch = track_uris[i:i+100]
            await self._make_request(
                "POST",
                f"playlists/{playlist_id}/tracks",
                access_token,
                json={"uris": batch}
            )
        return True

    async def get_playlist(
        self,
        access_token: str,
        playlist_id: str
    ) -> SpotifyPlaylist:
        """Get playlist details."""
        data = await self._make_request(
            "GET",
            f"playlists/{playlist_id}",
            access_token
        )
        
        tracks = []
        for item in data.get("tracks", {}).get("items", []):
            if item.get("track"):
                track = item["track"]
                tracks.append(SpotifyTrack(
                    id=track["id"],
                    name=track["name"],
                    artist=track["artists"][0]["name"],
                    album=track["album"]["name"],
                    duration_ms=track["duration_ms"],
                    preview_url=track.get("preview_url"),
                    uri=track["uri"],
                    popularity=track["popularity"],
                    energy=0.5,
                    valence=0.5,
                    tempo=120.0
                ))
        
        return SpotifyPlaylist(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            tracks=tracks,
            collaborative=data.get("collaborative", False),
            public=data.get("public", True)
        )

    async def get_current_playback(
        self,
        access_token: str
    ) -> Optional[Dict[str, Any]]:
        """Get current playback state."""
        try:
            return await self._make_request("GET", "me/player", access_token)
        except Exception as e:
            return None

    async def control_playback(
        self,
        access_token: str,
        action: str,
        device_id: Optional[str] = None
    ) -> bool:
        """Control playback (play, pause, next, previous) - requires Premium."""
        # Check if user has premium
        if not await self.is_premium_user(access_token):
            raise HTTPException(
                status_code=403,
                detail="Playback control requires Spotify Premium"
            )
        
        params = {}
        if device_id:
            params["device_id"] = device_id
        
        if action == "play":
            await self._make_request("PUT", "me/player/play", access_token, params=params)
        elif action == "pause":
            await self._make_request("PUT", "me/player/pause", access_token, params=params)
        elif action == "next":
            await self._make_request("POST", "me/player/next", access_token, params=params)
        elif action == "previous":
            await self._make_request("POST", "me/player/previous", access_token, params=params)
        else:
            raise ValueError(f"Invalid playback action: {action}")
        
        return True

    async def set_volume(
        self,
        access_token: str,
        volume_percent: int,
        device_id: Optional[str] = None
    ) -> bool:
        """Set playback volume."""
        params = {"volume_percent": max(0, min(100, volume_percent))}
        if device_id:
            params["device_id"] = device_id
        
        await self._make_request(
            "PUT",
            "me/player/volume",
            access_token,
            params=params
        )
        return True

    async def create_journey_playlist(
        self,
        access_token: str,
        journey_name: str,
        duration_minutes: int,
        mood: str = "balanced",
        locations: List[str] = None
    ) -> SpotifyPlaylist:
        """Create a playlist optimized for a journey."""
        # Limit playlist size to avoid performance issues
        max_tracks = 500  # Reasonable limit for journey playlists
        
        # Get user's top tracks as seeds
        top_tracks = await self.get_user_top_tracks(access_token, limit=10)
        seed_tracks = [t.id for t in top_tracks[:5]]
        
        # Determine audio features based on mood
        mood_features = {
            "energetic": {"energy": 0.8, "valence": 0.7, "tempo": 130},
            "relaxed": {"energy": 0.3, "valence": 0.6, "tempo": 90},
            "focused": {"energy": 0.5, "valence": 0.5, "tempo": 110},
            "happy": {"energy": 0.7, "valence": 0.9, "tempo": 120},
            "balanced": {"energy": 0.5, "valence": 0.6, "tempo": 115}
        }
        
        features = mood_features.get(mood, mood_features["balanced"])
        
        # Calculate how many batches we need for long journeys
        avg_track_duration = 3.5 * 60 * 1000  # 3.5 minutes in ms
        estimated_tracks_needed = int((duration_minutes * 60 * 1000) / avg_track_duration)
        
        # Limit to reasonable amount
        tracks_to_fetch = min(estimated_tracks_needed * 2, max_tracks)  # Fetch 2x needed for variety
        
        all_tracks = []
        
        # Get recommendations in batches if needed
        while len(all_tracks) < tracks_to_fetch:
            # Vary the seeds for each batch to get diversity
            batch_seeds = seed_tracks if not all_tracks else [t.id for t in random.sample(all_tracks[-10:], min(5, len(all_tracks)))]
            
            batch_tracks = await self.get_recommendations(
                access_token,
                seed_tracks=batch_seeds,
                target_energy=features["energy"] + random.uniform(-0.1, 0.1),  # Add variation
                target_valence=features["valence"] + random.uniform(-0.1, 0.1),
                target_tempo=features["tempo"] + random.uniform(-10, 10),
                limit=50
            )
            
            # Filter out duplicates
            existing_ids = {t.id for t in all_tracks}
            new_tracks = [t for t in batch_tracks if t.id not in existing_ids]
            all_tracks.extend(new_tracks)
            
            # Break if we're not getting new tracks
            if not new_tracks:
                break
        
        # Select tracks for the journey duration
        total_duration_ms = duration_minutes * 60 * 1000
        selected_tracks = []
        current_duration = 0
        
        # Shuffle for variety
        random.shuffle(all_tracks)
        
        for track in all_tracks:
            if current_duration + track.duration_ms <= total_duration_ms * 1.1:  # Allow 10% overflow
                selected_tracks.append(track)
                current_duration += track.duration_ms
            if current_duration >= total_duration_ms * 0.9:  # 90% of journey time
                break
        
        # Create playlist
        playlist_name = f"Road Trip: {journey_name}"
        description = f"AI-curated {mood} playlist for your {duration_minutes} minute journey"
        if locations:
            description += f" through {', '.join(locations[:3])}"
        
        playlist = await self.create_playlist(
            access_token,
            playlist_name,
            description,
            public=True,
            collaborative=True
        )
        
        # Add tracks in batches
        track_uris = [t.uri for t in selected_tracks]
        await self.add_tracks_to_playlist(access_token, playlist.id, track_uris)
        
        playlist.tracks = selected_tracks
        
        logger.info(f"Created journey playlist with {len(selected_tracks)} tracks for {duration_minutes} minute journey")
        
        return playlist

    async def get_location_based_tracks(
        self,
        access_token: str,
        location: str,
        limit: int = 10
    ) -> List[SpotifyTrack]:
        """Get tracks related to a specific location."""
        # Search for tracks mentioning the location
        location_tracks = await self.search_tracks(
            access_token,
            f'"{location}"',
            limit=limit
        )
        
        # Also search for genre-based tracks if it's a known music city
        music_cities = {
            "Nashville": ["country", "americana"],
            "New Orleans": ["jazz", "blues"],
            "Seattle": ["grunge", "indie"],
            "Detroit": ["motown", "techno"],
            "Memphis": ["soul", "blues"],
            "Austin": ["indie", "country"],
            "Los Angeles": ["pop", "rock"],
            "New York": ["hip-hop", "jazz"]
        }
        
        for city, genres in music_cities.items():
            if city.lower() in location.lower():
                genre_tracks = await self.get_recommendations(
                    access_token,
                    seed_genres=genres[:2],
                    limit=limit
                )
                location_tracks.extend(genre_tracks)
                break
        
        # Remove duplicates
        seen = set()
        unique_tracks = []
        for track in location_tracks:
            if track.id not in seen:
                seen.add(track.id)
                unique_tracks.append(track)
        
        return unique_tracks[:limit]


# Singleton instance
spotify_service = SpotifyService()