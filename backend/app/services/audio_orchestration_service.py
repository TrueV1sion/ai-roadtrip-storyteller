"""
Advanced Audio Orchestration Service
Manages all audio streams for world-class immersive experience
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import numpy as np
import logging

from .spatial_audio_engine import (
    SpatialAudioEngine, 
    AudioPosition, 
    SoundSource,
    AudioEnvironment,
    SpatialAudioSource
)
from .voice_personality_service import voice_personality_service
from ..core.cache import cache_manager

logger = logging.getLogger(__name__)


class AudioPriority(Enum):
    """Priority levels for audio mixing"""
    CRITICAL = 5    # Emergency alerts, navigation warnings
    HIGH = 4        # Voice narration, navigation instructions
    MEDIUM = 3      # Story dialogue, important effects
    LOW = 2         # Background music, ambient sounds
    MINIMAL = 1     # Subtle effects


@dataclass
class AudioStream:
    """Represents an active audio stream"""
    stream_id: str
    source_type: SoundSource
    priority: AudioPriority
    volume: float = 1.0
    position: Optional[AudioPosition] = None
    is_playing: bool = True
    fade_duration: float = 0.5
    duck_others: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DuckingProfile:
    """Audio ducking configuration"""
    target_volume: float  # Volume to duck to (0.0 - 1.0)
    fade_time: float     # Time to fade down (seconds)
    hold_time: float     # Time to hold at ducked volume
    restore_time: float  # Time to fade back up


class AudioOrchestrationService:
    """
    World-class audio orchestration managing multiple audio streams
    with intelligent mixing, ducking, and spatial positioning
    """
    
    def __init__(self, spatial_engine: SpatialAudioEngine):
        self.spatial_engine = spatial_engine
        self.active_streams: Dict[str, AudioStream] = {}
        self.volume_targets: Dict[str, float] = {}
        self.ducking_states: Dict[str, DuckingProfile] = {}
        
        # Audio mixing configuration
        self.master_volume = 1.0
        self.category_volumes = {
            SoundSource.NARRATOR: 1.0,
            SoundSource.CHARACTER: 0.9,
            SoundSource.NAVIGATION: 1.0,
            SoundSource.MUSIC: 0.3,
            SoundSource.AMBIENT: 0.4,
            SoundSource.EFFECT: 0.7,
            SoundSource.NATURE: 0.5,
            SoundSource.VEHICLE: 0.6
        }
        
        # Ducking profiles for different scenarios
        self.ducking_profiles = {
            "navigation": DuckingProfile(0.2, 0.3, 2.0, 0.5),
            "voice": DuckingProfile(0.3, 0.5, 0.0, 0.8),
            "emergency": DuckingProfile(0.1, 0.1, 3.0, 1.0),
            "story": DuckingProfile(0.4, 0.8, 0.0, 1.0)
        }
        
        # Intelligent mixing rules
        self.mixing_rules = self._initialize_mixing_rules()
        
        logger.info("Audio Orchestration Service initialized")
    
    async def play_voice(
        self,
        audio_data: bytes,
        personality: str,
        context: Dict[str, Any],
        priority: AudioPriority = AudioPriority.HIGH
    ) -> str:
        """
        Play voice audio with spatial positioning and mixing
        """
        stream_id = f"voice_{datetime.now().timestamp()}"
        
        # Determine spatial position based on personality and context
        position = self._get_voice_position(personality, context)
        
        # Create audio stream
        stream = AudioStream(
            stream_id=stream_id,
            source_type=SoundSource.NARRATOR,
            priority=priority,
            position=position,
            duck_others=True,
            metadata={
                "personality": personality,
                "context": context
            }
        )
        
        # Apply ducking to other streams
        await self._apply_ducking(stream_id, "voice")
        
        # Add to spatial engine
        spatial_source = SpatialAudioSource(
            source_id=stream_id,
            source_type=SoundSource.NARRATOR,
            position=position,
            volume=self.category_volumes[SoundSource.NARRATOR],
            priority=priority.value
        )
        await self.spatial_engine.add_source(spatial_source)
        
        # Track active stream
        self.active_streams[stream_id] = stream
        
        logger.info(f"Playing voice stream {stream_id} with personality {personality}")
        
        return stream_id
    
    async def play_music(
        self,
        track_id: str,
        volume: float = 0.3,
        crossfade: bool = True
    ) -> str:
        """
        Play background music with intelligent volume management
        """
        stream_id = f"music_{track_id}_{datetime.now().timestamp()}"
        
        # Stop existing music with crossfade if requested
        if crossfade:
            await self._crossfade_music(stream_id)
        
        # Create music stream
        stream = AudioStream(
            stream_id=stream_id,
            source_type=SoundSource.MUSIC,
            priority=AudioPriority.LOW,
            volume=volume,
            metadata={"track_id": track_id}
        )
        
        # Add as ambient source (no specific position)
        spatial_source = SpatialAudioSource(
            source_id=stream_id,
            source_type=SoundSource.MUSIC,
            position=AudioPosition(0, 0, 0),
            volume=volume * self.category_volumes[SoundSource.MUSIC],
            priority=AudioPriority.LOW.value,
            distance_attenuation=False
        )
        await self.spatial_engine.add_source(spatial_source)
        
        self.active_streams[stream_id] = stream
        
        return stream_id
    
    async def play_navigation_alert(
        self,
        alert_type: str,
        audio_data: bytes,
        position: Optional[AudioPosition] = None
    ) -> str:
        """
        Play navigation alerts with highest priority
        """
        stream_id = f"nav_{alert_type}_{datetime.now().timestamp()}"
        
        # Navigation always comes from front-center unless specified
        if position is None:
            position = AudioPosition(0, 0.2, 0.8)  # Slightly up and forward
        
        stream = AudioStream(
            stream_id=stream_id,
            source_type=SoundSource.NAVIGATION,
            priority=AudioPriority.CRITICAL,
            position=position,
            duck_others=True,
            metadata={"alert_type": alert_type}
        )
        
        # Apply emergency ducking
        await self._apply_ducking(stream_id, "emergency")
        
        # Add to spatial engine with high priority
        spatial_source = SpatialAudioSource(
            source_id=stream_id,
            source_type=SoundSource.NAVIGATION,
            position=position,
            volume=self.category_volumes[SoundSource.NAVIGATION],
            priority=AudioPriority.CRITICAL.value
        )
        await self.spatial_engine.add_source(spatial_source)
        
        self.active_streams[stream_id] = stream
        
        logger.warning(f"Playing navigation alert: {alert_type}")
        
        return stream_id
    
    async def play_ambient_sound(
        self,
        sound_type: str,
        position: AudioPosition,
        volume: float = 0.5,
        loop: bool = True
    ) -> str:
        """
        Play ambient environmental sounds
        """
        stream_id = f"ambient_{sound_type}_{datetime.now().timestamp()}"
        
        stream = AudioStream(
            stream_id=stream_id,
            source_type=SoundSource.AMBIENT,
            priority=AudioPriority.MINIMAL,
            position=position,
            volume=volume,
            metadata={
                "sound_type": sound_type,
                "loop": loop
            }
        )
        
        # Add to spatial engine
        spatial_source = SpatialAudioSource(
            source_id=stream_id,
            source_type=SoundSource.AMBIENT,
            position=position,
            volume=volume * self.category_volumes[SoundSource.AMBIENT],
            priority=AudioPriority.MINIMAL.value,
            distance_attenuation=True
        )
        await self.spatial_engine.add_source(spatial_source)
        
        self.active_streams[stream_id] = stream
        
        return stream_id
    
    async def update_environment(
        self,
        environment: AudioEnvironment,
        location_data: Dict[str, Any]
    ):
        """
        Update audio environment based on location
        """
        await self.spatial_engine.set_environment(environment)
        
        # Adjust category volumes based on environment
        if environment in [AudioEnvironment.HIGHWAY, AudioEnvironment.TUNNEL]:
            # Boost voice volume in noisy environments
            self.category_volumes[SoundSource.NARRATOR] = 1.2
            self.category_volumes[SoundSource.NAVIGATION] = 1.2
            self.category_volumes[SoundSource.AMBIENT] = 0.2
        elif environment in [AudioEnvironment.FOREST, AudioEnvironment.RURAL]:
            # Normal volumes in quiet environments
            self.category_volumes[SoundSource.NARRATOR] = 1.0
            self.category_volumes[SoundSource.NAVIGATION] = 1.0
            self.category_volumes[SoundSource.AMBIENT] = 0.6
        
        logger.info(f"Updated audio environment to {environment.value}")
    
    async def handle_speed_change(self, speed: float):
        """
        Adjust audio mix based on vehicle speed
        """
        if speed > 70:  # Highway speeds
            # Reduce ambient sounds, boost voice
            await self._adjust_category_volume(SoundSource.AMBIENT, 0.2)
            await self._adjust_category_volume(SoundSource.NATURE, 0.3)
            await self._adjust_category_volume(SoundSource.NARRATOR, 1.1)
        elif speed < 30:  # City/slow speeds
            # Restore normal ambient levels
            await self._adjust_category_volume(SoundSource.AMBIENT, 0.5)
            await self._adjust_category_volume(SoundSource.NATURE, 0.5)
            await self._adjust_category_volume(SoundSource.NARRATOR, 1.0)
    
    async def stop_stream(self, stream_id: str, fade_out: float = 0.5):
        """
        Stop an audio stream with optional fade out
        """
        if stream_id not in self.active_streams:
            return
        
        stream = self.active_streams[stream_id]
        
        if fade_out > 0:
            # Fade out over specified duration
            await self._fade_stream(stream_id, 0.0, fade_out)
        
        # Remove from spatial engine
        await self.spatial_engine.remove_source(stream_id)
        
        # Remove from active streams
        del self.active_streams[stream_id]
        
        # Restore ducked streams if this was ducking others
        if stream.duck_others:
            await self._restore_ducked_streams(stream_id)
        
        logger.info(f"Stopped audio stream: {stream_id}")
    
    async def get_audio_state(self) -> Dict[str, Any]:
        """
        Get current audio orchestration state
        """
        return {
            "master_volume": self.master_volume,
            "active_streams": len(self.active_streams),
            "streams": [
                {
                    "id": stream_id,
                    "type": stream.source_type.value,
                    "priority": stream.priority.value,
                    "volume": stream.volume,
                    "position": stream.position.__dict__ if stream.position else None
                }
                for stream_id, stream in self.active_streams.items()
            ],
            "environment": self.spatial_engine.environment.value,
            "category_volumes": {
                cat.value: vol 
                for cat, vol in self.category_volumes.items()
            }
        }
    
    # Private helper methods
    
    def _get_voice_position(self, personality: str, context: Dict[str, Any]) -> AudioPosition:
        """
        Determine spatial position for voice based on personality
        """
        positions = {
            "wise_narrator": AudioPosition(0, 0.3, 0.5),      # Centered, slightly elevated
            "enthusiastic_buddy": AudioPosition(0.3, 0, 0.4),  # Slightly right, passenger seat
            "local_expert": AudioPosition(-0.2, 0.1, 0.3),    # Slightly left, knowledgeable
            "mystical_shaman": AudioPosition(0, 0.5, 0.6),    # Elevated, ethereal
            "comedic_relief": AudioPosition(0.4, -0.1, 0.3),  # Right side, playful
        }
        
        return positions.get(personality, AudioPosition(0, 0, 0.5))
    
    async def _apply_ducking(self, trigger_stream_id: str, profile_name: str):
        """
        Apply ducking to other streams when high priority audio plays
        """
        profile = self.ducking_profiles[profile_name]
        trigger_stream = self.active_streams.get(trigger_stream_id)
        
        if not trigger_stream:
            return
        
        for stream_id, stream in self.active_streams.items():
            if stream_id == trigger_stream_id:
                continue
            
            # Duck lower priority streams
            if stream.priority.value < trigger_stream.priority.value:
                current_volume = stream.volume
                self.ducking_states[stream_id] = profile
                
                # Fade to ducked volume
                await self._fade_stream(
                    stream_id, 
                    current_volume * profile.target_volume,
                    profile.fade_time
                )
    
    async def _restore_ducked_streams(self, trigger_stream_id: str):
        """
        Restore volume of ducked streams
        """
        streams_to_restore = []
        
        for stream_id, profile in self.ducking_states.items():
            if stream_id in self.active_streams:
                streams_to_restore.append((stream_id, profile))
        
        # Clear ducking states
        self.ducking_states.clear()
        
        # Restore volumes
        for stream_id, profile in streams_to_restore:
            stream = self.active_streams[stream_id]
            await self._fade_stream(
                stream_id,
                stream.metadata.get("original_volume", stream.volume),
                profile.restore_time
            )
    
    async def _fade_stream(self, stream_id: str, target_volume: float, duration: float):
        """
        Fade stream volume over duration
        """
        if stream_id not in self.active_streams:
            return
        
        stream = self.active_streams[stream_id]
        start_volume = stream.volume
        start_time = asyncio.get_event_loop().time()
        
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= duration:
                stream.volume = target_volume
                break
            
            # Linear fade
            progress = elapsed / duration
            stream.volume = start_volume + (target_volume - start_volume) * progress
            
            # Update spatial engine volume
            if stream_id in self.spatial_engine.active_sources:
                self.spatial_engine.active_sources[stream_id].volume = stream.volume
            
            await asyncio.sleep(0.05)  # 50ms updates
    
    async def _crossfade_music(self, new_stream_id: str, duration: float = 2.0):
        """
        Crossfade between music tracks
        """
        # Find current music stream
        current_music = None
        for stream_id, stream in self.active_streams.items():
            if stream.source_type == SoundSource.MUSIC:
                current_music = stream_id
                break
        
        if current_music:
            # Fade out old music
            asyncio.create_task(self.stop_stream(current_music, fade_out=duration))
    
    async def _adjust_category_volume(self, category: SoundSource, volume: float):
        """
        Adjust volume for all streams in a category
        """
        self.category_volumes[category] = volume
        
        for stream_id, stream in self.active_streams.items():
            if stream.source_type == category:
                # Update stream volume
                stream.volume = stream.metadata.get("base_volume", 1.0) * volume
                
                # Update spatial engine
                if stream_id in self.spatial_engine.active_sources:
                    self.spatial_engine.active_sources[stream_id].volume = stream.volume
    
    def _initialize_mixing_rules(self) -> Dict[str, Any]:
        """
        Initialize intelligent mixing rules
        """
        return {
            "auto_duck": {
                SoundSource.NAVIGATION: [SoundSource.MUSIC, SoundSource.AMBIENT],
                SoundSource.NARRATOR: [SoundSource.MUSIC, SoundSource.AMBIENT, SoundSource.NATURE],
                SoundSource.CHARACTER: [SoundSource.MUSIC, SoundSource.AMBIENT]
            },
            "exclusive_categories": [
                [SoundSource.NAVIGATION, SoundSource.CHARACTER]  # Don't play simultaneously
            ],
            "volume_limits": {
                "total_max": 1.5,  # Maximum combined volume
                "category_max": {
                    SoundSource.MUSIC: 0.5,
                    SoundSource.AMBIENT: 0.6,
                    SoundSource.EFFECT: 0.8
                }
            }
        }


# Global instance
audio_orchestrator = None

def get_audio_orchestrator() -> AudioOrchestrationService:
    """Get or create audio orchestrator instance"""
    global audio_orchestrator
    if audio_orchestrator is None:
        from .spatial_audio_engine import spatial_audio_engine
        audio_orchestrator = AudioOrchestrationService(spatial_audio_engine)
    return audio_orchestrator