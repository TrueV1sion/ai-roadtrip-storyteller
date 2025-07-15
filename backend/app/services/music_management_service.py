"""
Music Service - Intelligent background music management
"""

import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import random
import logging

from ..core.cache import cache_manager
from .audio_orchestration_service import get_audio_orchestrator

logger = logging.getLogger(__name__)


class MusicMood(Enum):
    """Music moods for different journey moments"""
    ADVENTUROUS = "adventurous"
    PEACEFUL = "peaceful"
    ENERGETIC = "energetic"
    MYSTERIOUS = "mysterious"
    UPLIFTING = "uplifting"
    CONTEMPLATIVE = "contemplative"
    DRAMATIC = "dramatic"
    WHIMSICAL = "whimsical"


class TimeOfDay(Enum):
    """Time periods for music selection"""
    DAWN = "dawn"           # 5am - 7am
    MORNING = "morning"     # 7am - 12pm
    AFTERNOON = "afternoon" # 12pm - 5pm
    EVENING = "evening"     # 5pm - 8pm
    NIGHT = "night"         # 8pm - 11pm
    LATE_NIGHT = "late_night"  # 11pm - 5am


@dataclass
class MusicTrack:
    """Represents a music track"""
    track_id: str
    title: str
    artist: str
    mood: MusicMood
    duration: int  # seconds
    energy_level: float  # 0.0 - 1.0
    tempo: int  # BPM
    tags: List[str]
    file_url: str


@dataclass
class MusicContext:
    """Context for music selection"""
    location_type: str  # city, highway, rural, scenic
    weather: str       # clear, rain, cloudy, etc.
    time_of_day: TimeOfDay
    speed: float
    story_mood: Optional[str] = None
    user_energy: float = 0.5  # 0.0 - 1.0
    recent_tracks: List[str] = None


class MusicService:
    """
    Intelligent music service that selects and manages background music
    based on journey context, time, location, and narrative
    """
    
    def __init__(self):
        self.audio_orchestrator = get_audio_orchestrator()
        self.current_track_id: Optional[str] = None
        self.current_stream_id: Optional[str] = None
        self.music_library = self._initialize_music_library()
        self.playback_history: List[str] = []
        self.max_history = 20
        
        # Music selection weights
        self.mood_transitions = self._initialize_mood_transitions()
        self.context_mood_mapping = self._initialize_context_mapping()
        
        logger.info("Music Service initialized")
    
    async def select_and_play_music(
        self,
        context: MusicContext,
        crossfade: bool = True
    ) -> Optional[str]:
        """
        Select and play appropriate music based on context
        """
        # Select appropriate mood
        target_mood = await self._determine_mood(context)
        
        # Filter available tracks
        candidates = self._filter_tracks(target_mood, context)
        
        if not candidates:
            logger.warning(f"No suitable tracks found for mood {target_mood}")
            return None
        
        # Select track using intelligent algorithm
        selected_track = self._select_track(candidates, context)
        
        # Play the track
        stream_id = await self._play_track(selected_track, crossfade)
        
        # Update state
        self.current_track_id = selected_track.track_id
        self.current_stream_id = stream_id
        self.playback_history.append(selected_track.track_id)
        
        # Trim history
        if len(self.playback_history) > self.max_history:
            self.playback_history = self.playback_history[-self.max_history:]
        
        logger.info(f"Playing music: {selected_track.title} - {selected_track.artist} ({selected_track.mood.value})")
        
        return selected_track.track_id
    
    async def adjust_for_narrative(self, story_mood: str, intensity: float = 0.5):
        """
        Adjust music selection based on story narrative
        """
        # Map story mood to music mood
        mood_mapping = {
            "suspenseful": MusicMood.MYSTERIOUS,
            "joyful": MusicMood.UPLIFTING,
            "intense": MusicMood.DRAMATIC,
            "relaxed": MusicMood.PEACEFUL,
            "funny": MusicMood.WHIMSICAL,
            "epic": MusicMood.ADVENTUROUS
        }
        
        target_mood = mood_mapping.get(story_mood, MusicMood.CONTEMPLATIVE)
        
        # Check if we need to change music
        current_track = self._get_current_track()
        if current_track and current_track.mood == target_mood:
            # Just adjust volume based on intensity
            volume = 0.2 + (intensity * 0.3)  # 0.2 to 0.5 range
            await self.set_music_volume(volume)
        else:
            # Transition to new mood
            context = MusicContext(
                location_type="scenic",
                weather="clear",
                time_of_day=self._get_time_of_day(),
                speed=50,
                story_mood=story_mood
            )
            await self.select_and_play_music(context, crossfade=True)
    
    async def pause_for_voice(self, duration: float = 0):
        """
        Pause or duck music for voice narration
        """
        if self.current_stream_id:
            # Audio orchestrator handles ducking automatically
            # This is for explicit pause if needed
            if duration > 10:  # Long narration, pause instead of duck
                await self.pause_music()
                await asyncio.sleep(duration)
                await self.resume_music()
    
    async def pause_music(self):
        """Pause current music"""
        if self.current_stream_id:
            # Implementation would pause the actual audio
            logger.info("Music paused")
    
    async def resume_music(self):
        """Resume music playback"""
        if self.current_stream_id:
            # Implementation would resume the actual audio
            logger.info("Music resumed")
    
    async def set_music_volume(self, volume: float):
        """Set music volume (0.0 - 1.0)"""
        # This would integrate with audio orchestrator
        logger.info(f"Music volume set to {volume}")
    
    async def skip_track(self):
        """Skip to next track"""
        if self.current_stream_id:
            await self.audio_orchestrator.stop_stream(self.current_stream_id, fade_out=1.0)
            
            # Select new track with current context
            context = MusicContext(
                location_type="scenic",
                weather="clear",
                time_of_day=self._get_time_of_day(),
                speed=50
            )
            await self.select_and_play_music(context)
    
    # Private methods
    
    async def _determine_mood(self, context: MusicContext) -> MusicMood:
        """Determine appropriate music mood from context"""
        # Priority: story mood > time of day > location > weather
        
        if context.story_mood:
            # Map story mood to music mood
            story_mood_map = {
                "suspenseful": MusicMood.MYSTERIOUS,
                "joyful": MusicMood.UPLIFTING,
                "intense": MusicMood.DRAMATIC,
                "relaxed": MusicMood.PEACEFUL
            }
            return story_mood_map.get(context.story_mood, MusicMood.CONTEMPLATIVE)
        
        # Use context mapping
        base_mood = self.context_mood_mapping.get(
            (context.time_of_day, context.location_type),
            MusicMood.PEACEFUL
        )
        
        # Adjust for weather
        if context.weather == "rain":
            if base_mood == MusicMood.ENERGETIC:
                return MusicMood.CONTEMPLATIVE
            elif base_mood == MusicMood.ADVENTUROUS:
                return MusicMood.MYSTERIOUS
        
        # Adjust for speed
        if context.speed > 70 and base_mood == MusicMood.PEACEFUL:
            return MusicMood.ENERGETIC
        
        return base_mood
    
    def _filter_tracks(
        self,
        mood: MusicMood,
        context: MusicContext
    ) -> List[MusicTrack]:
        """Filter tracks based on mood and context"""
        candidates = []
        
        for track in self.music_library:
            # Match mood
            if track.mood != mood:
                continue
            
            # Filter by energy level
            if context.speed > 60 and track.energy_level < 0.4:
                continue
            elif context.speed < 30 and track.energy_level > 0.7:
                continue
            
            # Avoid recent tracks
            if track.track_id in self.playback_history[-5:]:
                continue
            
            candidates.append(track)
        
        return candidates
    
    def _select_track(
        self,
        candidates: List[MusicTrack],
        context: MusicContext
    ) -> MusicTrack:
        """Select best track from candidates"""
        if not candidates:
            return None
        
        # Score each track
        scores = []
        for track in candidates:
            score = 1.0
            
            # Prefer appropriate energy level
            energy_diff = abs(track.energy_level - context.user_energy)
            score *= (1.0 - energy_diff * 0.5)
            
            # Prefer tracks not played recently
            if track.track_id in self.playback_history:
                recency = self.playback_history.index(track.track_id)
                score *= (recency / len(self.playback_history))
            
            # Time of day preference
            if context.time_of_day in [TimeOfDay.NIGHT, TimeOfDay.LATE_NIGHT]:
                if track.energy_level < 0.5:
                    score *= 1.2
            
            scores.append((score, track))
        
        # Sort by score and add some randomness
        scores.sort(key=lambda x: x[0], reverse=True)
        
        # Pick from top 3 with weighted randomness
        top_tracks = scores[:3]
        if len(top_tracks) > 1:
            weights = [s[0] for s in top_tracks]
            selected = random.choices(top_tracks, weights=weights)[0][1]
        else:
            selected = top_tracks[0][1]
        
        return selected
    
    async def _play_track(self, track: MusicTrack, crossfade: bool) -> str:
        """Play a music track through audio orchestrator"""
        # Stop current track with crossfade
        if self.current_stream_id and crossfade:
            asyncio.create_task(
                self.audio_orchestrator.stop_stream(
                    self.current_stream_id,
                    fade_out=2.0
                )
            )
        
        # Play new track
        stream_id = await self.audio_orchestrator.play_music(
            track.track_id,
            volume=0.3,
            crossfade=crossfade
        )
        
        # Schedule next track before this one ends
        asyncio.create_task(self._schedule_next_track(track.duration))
        
        return stream_id
    
    async def _schedule_next_track(self, duration: int):
        """Schedule the next track to play"""
        # Wait for track to near completion
        await asyncio.sleep(duration - 5)  # 5 seconds before end
        
        # Select and queue next track
        context = MusicContext(
            location_type="scenic",
            weather="clear",
            time_of_day=self._get_time_of_day(),
            speed=50
        )
        await self.select_and_play_music(context, crossfade=True)
    
    def _get_current_track(self) -> Optional[MusicTrack]:
        """Get currently playing track"""
        if not self.current_track_id:
            return None
        
        for track in self.music_library:
            if track.track_id == self.current_track_id:
                return track
        return None
    
    def _get_time_of_day(self) -> TimeOfDay:
        """Get current time of day period"""
        hour = datetime.now().hour
        
        if 5 <= hour < 7:
            return TimeOfDay.DAWN
        elif 7 <= hour < 12:
            return TimeOfDay.MORNING
        elif 12 <= hour < 17:
            return TimeOfDay.AFTERNOON
        elif 17 <= hour < 20:
            return TimeOfDay.EVENING
        elif 20 <= hour < 23:
            return TimeOfDay.NIGHT
        else:
            return TimeOfDay.LATE_NIGHT
    
    def _initialize_music_library(self) -> List[MusicTrack]:
        """Initialize the music library"""
        # This would load from a database or music service
        # For now, returning sample tracks
        return [
            MusicTrack(
                track_id="track_001",
                title="Highway Dreams",
                artist="Journey Sounds",
                mood=MusicMood.ADVENTUROUS,
                duration=240,
                energy_level=0.7,
                tempo=120,
                tags=["road", "upbeat", "adventure"],
                file_url="https://example.com/tracks/highway_dreams.mp3"
            ),
            MusicTrack(
                track_id="track_002",
                title="Sunset Drive",
                artist="Ambient Roads",
                mood=MusicMood.PEACEFUL,
                duration=300,
                energy_level=0.3,
                tempo=80,
                tags=["calm", "sunset", "relaxing"],
                file_url="https://example.com/tracks/sunset_drive.mp3"
            ),
            # Add more tracks...
        ]
    
    def _initialize_mood_transitions(self) -> Dict[MusicMood, List[MusicMood]]:
        """Define natural mood transitions"""
        return {
            MusicMood.PEACEFUL: [MusicMood.CONTEMPLATIVE, MusicMood.UPLIFTING],
            MusicMood.ENERGETIC: [MusicMood.ADVENTUROUS, MusicMood.UPLIFTING],
            MusicMood.MYSTERIOUS: [MusicMood.DRAMATIC, MusicMood.CONTEMPLATIVE],
            MusicMood.ADVENTUROUS: [MusicMood.ENERGETIC, MusicMood.DRAMATIC],
            MusicMood.UPLIFTING: [MusicMood.ENERGETIC, MusicMood.PEACEFUL],
            MusicMood.CONTEMPLATIVE: [MusicMood.PEACEFUL, MusicMood.MYSTERIOUS],
            MusicMood.DRAMATIC: [MusicMood.ADVENTUROUS, MusicMood.MYSTERIOUS],
            MusicMood.WHIMSICAL: [MusicMood.UPLIFTING, MusicMood.PEACEFUL]
        }
    
    def _initialize_context_mapping(self) -> Dict[tuple, MusicMood]:
        """Map context to appropriate moods"""
        return {
            # (TimeOfDay, LocationType) -> MusicMood
            (TimeOfDay.DAWN, "highway"): MusicMood.PEACEFUL,
            (TimeOfDay.DAWN, "rural"): MusicMood.CONTEMPLATIVE,
            (TimeOfDay.MORNING, "highway"): MusicMood.ADVENTUROUS,
            (TimeOfDay.MORNING, "city"): MusicMood.ENERGETIC,
            (TimeOfDay.AFTERNOON, "scenic"): MusicMood.UPLIFTING,
            (TimeOfDay.EVENING, "highway"): MusicMood.CONTEMPLATIVE,
            (TimeOfDay.EVENING, "rural"): MusicMood.PEACEFUL,
            (TimeOfDay.NIGHT, "highway"): MusicMood.MYSTERIOUS,
            (TimeOfDay.LATE_NIGHT, "any"): MusicMood.CONTEMPLATIVE,
        }


# Global instance
music_service = MusicService()