"""
Fixes for failing Spotify integration tests
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import aiohttp

logger = logging.getLogger(__name__)


class SpotifyRateLimitingFixes:
    """Fixes for Spotify API rate limiting"""
    
    # Rate limiting configuration
    MAX_RETRIES = 3
    BASE_BACKOFF_SECONDS = 1
    MAX_BACKOFF_SECONDS = 60
    
    @staticmethod
    async def handle_rate_limit_with_retry(api_call_func, *args, **kwargs):
        """
        Handle rate limiting with exponential backoff
        FIX: Implement proper retry logic with exponential backoff
        """
        last_exception = None
        
        for attempt in range(SpotifyRateLimitingFixes.MAX_RETRIES):
            try:
                return await api_call_func(*args, **kwargs)
            except Exception as e:
                error_message = str(e)
                
                # Check if it's a rate limit error
                if "429" in error_message or "Too Many Requests" in error_message:
                    # Calculate backoff time with exponential backoff
                    backoff_time = min(
                        SpotifyRateLimitingFixes.BASE_BACKOFF_SECONDS * (2 ** attempt),
                        SpotifyRateLimitingFixes.MAX_BACKOFF_SECONDS
                    )
                    
                    logger.warning(f"Rate limited. Retrying in {backoff_time} seconds (attempt {attempt + 1}/{SpotifyRateLimitingFixes.MAX_RETRIES})")
                    await asyncio.sleep(backoff_time)
                    last_exception = e
                else:
                    # Not a rate limit error, raise immediately
                    raise e
        
        # All retries exhausted
        raise last_exception or Exception("Rate limit retry failed")


class SpotifyPremiumFeaturesFixes:
    """Fixes for handling free vs premium users"""
    
    @staticmethod
    async def check_premium_features(spotify_service, user_id: str) -> bool:
        """
        Check if user has premium features available
        FIX: Add graceful handling for free users
        """
        try:
            # Get user profile to check subscription
            profile = await spotify_service.get_user_profile(user_id)
            
            if profile.get('product') == 'free':
                # Free user - return False and log
                logger.info(f"User {user_id} has free account, premium features disabled")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking premium status: {e}")
            # Default to free user behavior on error
            return False
    
    @staticmethod
    def get_free_user_alternatives() -> Dict[str, Any]:
        """
        Get alternative features for free users
        FIX: Provide graceful degradation options
        """
        return {
            "available_features": [
                "search_tracks",
                "get_recommendations",
                "view_playlists"
            ],
            "unavailable_features": [
                "playback_control",
                "skip_tracks",
                "seek_position",
                "repeat_mode",
                "shuffle_mode"
            ],
            "upgrade_prompt": "Upgrade to Spotify Premium to unlock playback controls and ad-free listening",
            "fallback_mode": "playlist_only"
        }


class SpotifyPlaylistBatchingFixes:
    """Fixes for handling large playlists"""
    
    # Spotify limits
    SPOTIFY_MAX_TRACKS_PER_PLAYLIST = 10000
    SPOTIFY_MAX_TRACKS_PER_REQUEST = 100
    
    @staticmethod
    def batch_tracks_for_playlist(track_uris: List[str]) -> List[List[str]]:
        """
        Batch tracks for playlist operations
        FIX: Implement proper batching for large playlists
        """
        if len(track_uris) <= SpotifyPlaylistBatchingFixes.SPOTIFY_MAX_TRACKS_PER_PLAYLIST:
            # Within single playlist limit, batch for API requests
            batches = []
            for i in range(0, len(track_uris), SpotifyPlaylistBatchingFixes.SPOTIFY_MAX_TRACKS_PER_REQUEST):
                batch = track_uris[i:i + SpotifyPlaylistBatchingFixes.SPOTIFY_MAX_TRACKS_PER_REQUEST]
                batches.append(batch)
            return batches
        else:
            # Exceeds playlist limit, need multiple playlists
            logger.warning(f"Track count ({len(track_uris)}) exceeds Spotify limit. Creating multiple playlists.")
            
            # Split into playlist-sized chunks
            playlist_chunks = []
            for i in range(0, len(track_uris), SpotifyPlaylistBatchingFixes.SPOTIFY_MAX_TRACKS_PER_PLAYLIST):
                chunk = track_uris[i:i + SpotifyPlaylistBatchingFixes.SPOTIFY_MAX_TRACKS_PER_PLAYLIST]
                playlist_chunks.append(chunk)
            
            return playlist_chunks
    
    @staticmethod
    async def add_tracks_in_batches(spotify_service, playlist_id: str, track_uris: List[str], user_id: str):
        """
        Add tracks to playlist in batches
        FIX: Handle large track lists properly
        """
        batches = SpotifyPlaylistBatchingFixes.batch_tracks_for_playlist(track_uris)
        
        if len(track_uris) <= SpotifyPlaylistBatchingFixes.SPOTIFY_MAX_TRACKS_PER_PLAYLIST:
            # Single playlist, multiple batches
            for i, batch in enumerate(batches):
                logger.info(f"Adding batch {i+1}/{len(batches)} ({len(batch)} tracks)")
                await spotify_service.add_tracks_to_playlist(user_id, playlist_id, batch)
                
                # Small delay between batches to avoid rate limiting
                if i < len(batches) - 1:
                    await asyncio.sleep(0.1)
        else:
            # Multiple playlists needed
            playlists_created = []
            
            for i, playlist_tracks in enumerate(batches):
                # Create additional playlist
                playlist_name = f"Journey Playlist Part {i+1}"
                new_playlist = await spotify_service.create_playlist(
                    user_id=user_id,
                    name=playlist_name,
                    description=f"Part {i+1} of your journey playlist"
                )
                playlists_created.append(new_playlist)
                
                # Add tracks in batches to this playlist
                track_batches = []
                for j in range(0, len(playlist_tracks), SpotifyPlaylistBatchingFixes.SPOTIFY_MAX_TRACKS_PER_REQUEST):
                    batch = playlist_tracks[j:j + SpotifyPlaylistBatchingFixes.SPOTIFY_MAX_TRACKS_PER_REQUEST]
                    track_batches.append(batch)
                
                for batch in track_batches:
                    await spotify_service.add_tracks_to_playlist(user_id, new_playlist['id'], batch)
                    await asyncio.sleep(0.1)
            
            return playlists_created


# Apply fixes to SpotifyService
def apply_spotify_fixes():
    """Apply all fixes to the Spotify service"""
    from backend.app.services.spotify_service import SpotifyService, JourneyPlaylistGenerator
    
    # Add retry method to SpotifyService
    async def search_tracks_with_retry(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search tracks with rate limit retry"""
        async def _search():
            return await self.search_tracks(query, limit)
        
        return await SpotifyRateLimitingFixes.handle_rate_limit_with_retry(_search)
    
    # Add premium check method
    SpotifyService.check_premium_features = lambda self, user_id: SpotifyPremiumFeaturesFixes.check_premium_features(self, user_id)
    SpotifyService.search_tracks_with_retry = search_tracks_with_retry
    
    # Add batching to JourneyPlaylistGenerator
    JourneyPlaylistGenerator._batch_tracks_for_playlist = SpotifyPlaylistBatchingFixes.batch_tracks_for_playlist
    
    # Wrap the original add_tracks method
    if hasattr(SpotifyService, 'add_tracks_to_playlist'):
        original_add_tracks = SpotifyService.add_tracks_to_playlist
        
        async def add_tracks_with_batching(self, user_id: str, playlist_id: str, track_uris: List[str]):
            """Add tracks with proper batching for large lists"""
            if len(track_uris) > SpotifyPlaylistBatchingFixes.SPOTIFY_MAX_TRACKS_PER_REQUEST:
                # Use batching
                batches = SpotifyPlaylistBatchingFixes.batch_tracks_for_playlist(track_uris)
                for batch in batches[0]:  # First playlist chunk
                    await original_add_tracks(self, user_id, playlist_id, batch)
                    await asyncio.sleep(0.1)  # Rate limit protection
            else:
                # Small enough for single request
                await original_add_tracks(self, user_id, playlist_id, track_uris)
        
        SpotifyService.add_tracks_to_playlist = add_tracks_with_batching