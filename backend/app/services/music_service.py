"""
Enhanced music service with Spotify integration and journey-based playlist generation.
"""

from typing import Dict, Optional, List, Any
import asyncio
import random
from datetime import datetime

from backend.app.core.logger import get_logger
from backend.app.core.cache import get_cache
from backend.app.core.config import get_settings
from backend.app.services.spotify_service import spotify_service, SpotifyPlaylist, SpotifyTrack

settings = get_settings()
logger = get_logger(__name__)
cache = get_cache()


class MusicService:
    """Service for music generation and management."""

    def __init__(self):
        self.mood_mappings = {
            "happy": {"energy": 0.7, "valence": 0.8},
            "energetic": {"energy": 0.9, "valence": 0.7},
            "relaxed": {"energy": 0.3, "valence": 0.6},
            "melancholic": {"energy": 0.4, "valence": 0.3},
            "neutral": {"energy": 0.5, "valence": 0.5}
        }

    async def get_music_for_location(
        self,
        location: str,
        mood: Optional[str] = None,
        genre_preferences: List[str] = None,
        access_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get music recommendations for a specific location."""
        try:
            if not access_token:
                return self._get_fallback_music(mood)
            
            # Get location-based tracks from Spotify
            tracks = await spotify_service.get_location_based_tracks(
                access_token,
                location,
                limit=20
            )
            
            # Filter by mood if specified
            if mood:
                mood_energy = {
                    "energetic": 0.7,
                    "relaxed": 0.3,
                    "happy": 0.8,
                    "melancholic": 0.4,
                    "neutral": 0.5
                }.get(mood, 0.5)
                
                # Sort tracks by how close they match the mood
                tracks.sort(key=lambda t: abs(t.energy - mood_energy))
                tracks = tracks[:10]
            
            return {
                "playlist_name": f"{location} Vibes",
                "tracks": [
                    {
                        "id": track.id,
                        "title": track.name,
                        "artist": track.artist,
                        "duration": track.duration_ms // 1000,
                        "mood": mood or "neutral",
                        "uri": track.uri,
                        "preview_url": track.preview_url
                    }
                    for track in tracks
                ],
                "duration_minutes": sum(t.duration_ms for t in tracks) // 60000,
                "mood": mood
            }
        except Exception as e:
            logger.error(f"Error getting music for location: {e}")
            return self._get_fallback_music(mood)

    async def create_journey_soundtrack(
        self,
        route_points: List[Dict[str, Any]],
        duration_hours: float,
        preferences: Dict[str, Any],
        access_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a dynamic soundtrack for the entire journey."""
        try:
            if access_token:
                # Create a Spotify journey playlist
                locations = [p.get("name", "") for p in route_points if p.get("name")]
                playlist = await spotify_service.create_journey_playlist(
                    access_token,
                    journey_name=locations[0] + " to " + locations[-1] if locations else "Road Trip",
                    duration_minutes=int(duration_hours * 60),
                    mood=preferences.get("mood", "balanced"),
                    locations=locations[:3]
                )
                
                # Divide playlist into segments based on route points
                tracks_per_segment = len(playlist.tracks) // max(1, len(route_points))
                segments = []
                
                for i, point in enumerate(route_points):
                    start_idx = i * tracks_per_segment
                    end_idx = start_idx + tracks_per_segment
                    segment_tracks = playlist.tracks[start_idx:end_idx]
                    
                    if segment_tracks:
                        segments.append({
                            "location": point.get("name", "Unknown Location"),
                            "start_time": i * (duration_hours / len(route_points)) * 60,
                            "music": {
                                "playlist_name": f"{point.get('name', 'Location')} Mix",
                                "tracks": [
                                    {
                                        "id": track.id,
                                        "title": track.name,
                                        "artist": track.artist,
                                        "duration": track.duration_ms // 1000,
                                        "uri": track.uri,
                                        "energy": track.energy,
                                        "valence": track.valence
                                    }
                                    for track in segment_tracks
                                ],
                                "duration_minutes": sum(t.duration_ms for t in segment_tracks) // 60000
                            }
                        })
                
                return {
                    "journey_playlist": playlist.name,
                    "playlist_id": playlist.id,
                    "total_duration_hours": duration_hours,
                    "segments": segments,
                    "adaptive": True,
                    "collaborative": playlist.collaborative
                }
            else:
                # Fallback without Spotify
                segments = []
                
                for i, point in enumerate(route_points):
                    segment_music = await self.get_music_for_location(
                        point.get("name", "Unknown Location"),
                        mood=preferences.get("mood"),
                        genre_preferences=preferences.get("genres", [])
                    )
                    
                    segments.append({
                        "location": point.get("name"),
                        "start_time": i * (duration_hours / len(route_points)) * 60,
                        "music": segment_music
                    })
                
                return {
                    "journey_playlist": "Road Trip Soundtrack",
                    "total_duration_hours": duration_hours,
                    "segments": segments,
                    "adaptive": True
                }
        except Exception as e:
            logger.error(f"Error creating journey soundtrack: {e}")
            return {
                "journey_playlist": "Default Road Trip Mix",
                "total_duration_hours": duration_hours,
                "segments": [],
                "adaptive": False
            }

    async def adjust_music_for_context(
        self,
        current_context: Dict[str, Any],
        current_music: Dict[str, Any],
        access_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Adjust music based on current context (traffic, weather, time)."""
        try:
            adjusted_mood = current_music.get("mood", "neutral")
            target_energy = 0.5
            target_valence = 0.6
            
            # Adjust based on traffic
            if current_context.get("traffic_level") == "heavy":
                adjusted_mood = "relaxed"
                target_energy = 0.3
                target_valence = 0.5
            elif current_context.get("driving_speed", 0) > 70:
                adjusted_mood = "energetic"
                target_energy = 0.8
                target_valence = 0.7
            
            # Adjust based on weather
            weather = current_context.get("weather", {})
            if weather.get("condition") == "rainy":
                adjusted_mood = "melancholic"
                target_energy = 0.4
                target_valence = 0.3
            elif weather.get("condition") == "sunny":
                adjusted_mood = "happy"
                target_energy = 0.7
                target_valence = 0.9
            
            # Adjust based on time of day
            hour = current_context.get("hour", 12)
            if hour < 8:
                adjusted_mood = "energetic"  # Morning energy
                target_energy = 0.7
                target_valence = 0.8
            elif hour > 20:
                adjusted_mood = "relaxed"  # Evening wind-down
                target_energy = 0.3
                target_valence = 0.5
            
            if adjusted_mood != current_music.get("mood"):
                if access_token:
                    # Get new recommendations based on adjusted mood
                    tracks = await spotify_service.get_recommendations(
                        access_token,
                        target_energy=target_energy,
                        target_valence=target_valence,
                        limit=10
                    )
                    
                    return {
                        "playlist_name": f"{adjusted_mood.title()} Driving Mix",
                        "tracks": [
                            {
                                "id": track.id,
                                "title": track.name,
                                "artist": track.artist,
                                "duration": track.duration_ms // 1000,
                                "mood": adjusted_mood,
                                "uri": track.uri,
                                "energy": track.energy,
                                "valence": track.valence
                            }
                            for track in tracks
                        ],
                        "duration_minutes": sum(t.duration_ms for t in tracks) // 60000,
                        "mood": adjusted_mood,
                        "context_adjusted": True
                    }
                else:
                    return await self.get_music_for_location(
                        current_context.get("location", "Current Location"),
                        mood=adjusted_mood
                    )
            
            return current_music
        except Exception as e:
            logger.error(f"Error adjusting music for context: {e}")
            return current_music

    async def sync_music_with_narration(
        self,
        story_timeline: List[Dict[str, Any]],
        music_playlist: Dict[str, Any],
        access_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Synchronize music with story narration timeline."""
        try:
            synced_timeline = []
            
            for segment in story_timeline:
                # Determine music mood based on story content
                story_mood = segment.get("mood", "neutral")
                music_volume = 0.7  # Default volume
                
                # Lower volume during narration
                if segment.get("type") == "narration":
                    music_volume = 0.3
                elif segment.get("type") == "dialogue":
                    music_volume = 0.4
                elif segment.get("type") == "action":
                    music_volume = 0.8
                
                # Find matching music from playlist
                matching_tracks = []
                for track in music_playlist.get("tracks", []):
                    if track.get("mood") == story_mood:
                        matching_tracks.append(track)
                
                if not matching_tracks and music_playlist.get("tracks"):
                    matching_tracks = music_playlist["tracks"][:3]
                
                synced_timeline.append({
                    "start_time": segment.get("start_time", 0),
                    "duration": segment.get("duration", 60),
                    "story_content": segment.get("content", ""),
                    "music_tracks": matching_tracks,
                    "music_volume": music_volume,
                    "fade_in": segment.get("type") == "chapter_start",
                    "fade_out": segment.get("type") == "chapter_end"
                })
            
            return {
                "synced_timeline": synced_timeline,
                "total_duration": sum(s["duration"] for s in synced_timeline),
                "adaptive_volume": True,
                "seamless_transitions": True
            }
        except Exception as e:
            logger.error(f"Error syncing music with narration: {e}")
            return {
                "synced_timeline": [],
                "total_duration": 0,
                "adaptive_volume": False,
                "seamless_transitions": False
            }

    def _get_music_transition_points(
        self,
        story_segment: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify points where music should transition."""
        transitions = []
        
        # Transition at story emotional beats
        if "emotional_arc" in story_segment:
            for point in story_segment["emotional_arc"]:
                transitions.append({
                    "time": point["time"],
                    "type": "emotional",
                    "target_mood": point["mood"]
                })
        
        # Transition at location changes
        if "location_changes" in story_segment:
            for change in story_segment["location_changes"]:
                transitions.append({
                    "time": change["time"],
                    "type": "location",
                    "target_mood": "neutral"
                })
        
        return sorted(transitions, key=lambda x: x["time"])

    def _get_fallback_music(self, mood: Optional[str]) -> Dict[str, Any]:
        """Get fallback music when Spotify is not available."""
        return {
            "playlist_name": f"Road Trip {mood.title() if mood else 'Mix'}",
            "tracks": [
                {
                    "title": "Highway Song",
                    "artist": "Road Trip Band",
                    "duration": 240,
                    "mood": mood or "neutral"
                }
            ],
            "duration_minutes": 30,
            "mood": mood
        }


# Singleton instance
music_service = MusicService()