"""
Refactored Spatial Audio Engine using modular components.
Main orchestrator for spatial audio experiences.
"""

from typing import Any, Dict, List, Optional, Tuple
import asyncio
import numpy as np
from sqlalchemy.orm import Session

from backend.app.services.audio.sound_library import SoundLibrary
from backend.app.services.audio.binaural_processor import BinauralProcessor
from backend.app.services.audio.ambient_generator import AmbientGenerator
from backend.app.services.audio.audio_mixer import AudioMixer
from backend.app.core.logger import logger
from backend.app.core.cache import cache_manager
from backend.app.core.standardized_errors import (
    handle_errors,
    ExternalServiceError,
    ValidationError
)


class SpatialAudioEngineV2:
    """
    Refactored spatial audio engine with modular architecture.
    Orchestrates sound library, binaural processing, ambient generation, and mixing.
    """
    
    def __init__(self, db: Session):
        """Initialize spatial audio engine with components."""
        self.db = db
        self.sound_library = SoundLibrary()
        self.binaural_processor = BinauralProcessor()
        self.ambient_generator = AmbientGenerator(self.sound_library)
        self.audio_mixer = AudioMixer()
        
        # Configuration
        self.sample_rate = 44100
        self.default_duration = 30.0  # seconds
        
        logger.info("Spatial Audio Engine V2 initialized")
    
    @handle_errors(default_error_code="AUDIO_GENERATION_FAILED")
    async def generate_spatial_scene(
        self,
        environment: str,
        narration: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        duration: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Generate a complete spatial audio scene.
        
        Args:
            environment: Environment type
            narration: Optional narration configuration
            context: Scene context (weather, time, location, etc.)
            duration: Scene duration in seconds
            
        Returns:
            Spatial audio scene configuration
        """
        duration = duration or self.default_duration
        
        # Validate inputs
        if not environment:
            raise ValidationError("Environment type is required")
        
        # Extract context parameters
        weather = context.get("weather") if context else None
        time_of_day = context.get("time_of_day") if context else None
        activity_level = context.get("activity_level", 0.5) if context else 0.5
        listener_position = context.get("listener_position") if context else None
        
        # Check cache
        cache_key = f"spatial_scene:{environment}:{weather}:{time_of_day}:{duration}"
        cached_scene = await cache_manager.get(cache_key)
        if cached_scene:
            logger.info(f"Returning cached spatial scene for {environment}")
            return cached_scene
        
        # Generate ambient soundscape
        soundscape = await self.ambient_generator.generate_soundscape(
            environment=environment,
            weather=weather,
            time_of_day=time_of_day,
            activity_level=activity_level
        )
        
        # Process layers with binaural audio
        processed_layers = await self._process_spatial_layers(
            soundscape["layers"],
            duration,
            listener_position
        )
        
        # Mix all layers
        mixed_audio = await self.audio_mixer.mix_tracks(processed_layers, duration)
        
        # Add narration if provided
        if narration:
            narration_track = await self._process_narration(narration, duration)
            final_mix = await self._mix_with_ducking(
                mixed_audio,
                narration_track,
                duck_amount=0.5
            )
        else:
            final_mix = mixed_audio
        
        # Create scene configuration
        scene = {
            "environment": environment,
            "duration": duration,
            "soundscape": soundscape,
            "audio_format": {
                "sample_rate": self.sample_rate,
                "channels": 2,
                "bit_depth": 16
            },
            "context": context,
            "processing_info": {
                "total_layers": len(processed_layers),
                "has_narration": narration is not None,
                "binaural": True
            }
        }
        
        # Cache the scene configuration (not the audio data)
        await cache_manager.setex(cache_key, 3600, scene)  # 1 hour cache
        
        return scene
    
    @handle_errors(default_error_code="TRANSITION_GENERATION_FAILED")
    async def generate_environment_transition(
        self,
        from_env: str,
        to_env: str,
        duration: float = 5.0,
        context_change: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate smooth transition between environments.
        
        Args:
            from_env: Starting environment
            to_env: Target environment
            duration: Transition duration
            context_change: Optional context changes during transition
            
        Returns:
            Transition configuration
        """
        # Validate environments
        if not from_env or not to_env:
            raise ValidationError("Both source and target environments are required")
        
        # Generate transition
        transition = await self.ambient_generator.generate_transition(
            from_env=from_env,
            to_env=to_env,
            duration=duration,
            weather_change=context_change.get("weather") if context_change else None
        )
        
        # Process transition layers
        processed_layers = []
        for layer in transition["layers"]:
            # Mock audio data for now - in production, load actual audio files
            mock_audio = self._generate_mock_audio(duration)
            
            processed_layer = {
                "audio": mock_audio,
                "volume": layer.get("start_volume", 0.5),
                "action": layer["action"],
                "duration": layer.get("duration", duration)
            }
            
            processed_layers.append(processed_layer)
        
        return {
            "transition": transition,
            "duration": duration,
            "processed_layers": len(processed_layers)
        }
    
    async def _process_spatial_layers(
        self,
        layers: List[Dict[str, Any]],
        duration: float,
        listener_position: Optional[Tuple[float, float, float]]
    ) -> List[Dict[str, Any]]:
        """Process soundscape layers with spatial positioning."""
        processed = []
        
        for layer in layers:
            # In production, load actual audio file
            # For now, generate mock audio
            mono_audio = self._generate_mock_audio(duration)
            
            # Apply binaural processing
            position = layer.get("position", {})
            left, right = self.binaural_processor.apply_hrtf(
                mono_audio,
                azimuth=position.get("azimuth", 0),
                elevation=position.get("elevation", 0),
                distance=position.get("distance", 5)
            )
            
            # Create stereo track
            stereo_audio = np.stack([left, right], axis=1)
            
            processed.append({
                "audio": stereo_audio,
                "volume": layer.get("volume", 0.5),
                "fade_in": layer.get("fade_in", 0),
                "loop": layer.get("loop", True)
            })
        
        return processed
    
    async def _process_narration(
        self,
        narration: Dict[str, Any],
        duration: float
    ) -> np.ndarray:
        """Process narration with spatial effects."""
        # In production, use actual TTS or pre-recorded narration
        # For now, generate mock narration
        narration_audio = self._generate_mock_audio(duration, frequency=440)
        
        # Apply room acoustics if specified
        if narration.get("reverb"):
            left, right = np.split(narration_audio, 2)
            left, right = self.binaural_processor.add_room_acoustics(
                left, right,
                room_size=narration.get("room_size", "medium"),
                reverb_amount=narration.get("reverb", 0.2)
            )
            narration_audio = np.stack([left, right], axis=1)
        
        return narration_audio
    
    async def _mix_with_ducking(
        self,
        background: np.ndarray,
        foreground: np.ndarray,
        duck_amount: float = 0.5
    ) -> np.ndarray:
        """Mix tracks with ducking for narration clarity."""
        # Simple ducking - reduce background when foreground is present
        # In production, use envelope follower for smooth ducking
        
        output = np.copy(background)
        
        # Detect foreground presence (simple energy detection)
        window_size = int(0.1 * self.sample_rate)  # 100ms windows
        
        for i in range(0, len(foreground), window_size):
            window_end = min(i + window_size, len(foreground))
            
            # Check if foreground has content
            fg_energy = np.mean(np.abs(foreground[i:window_end]))
            
            if fg_energy > 0.01:  # Threshold for voice detection
                # Duck background
                output[i:window_end] *= (1 - duck_amount)
        
        # Add foreground
        output[:len(foreground)] += foreground
        
        return output
    
    def _generate_mock_audio(
        self,
        duration: float,
        frequency: float = 220
    ) -> np.ndarray:
        """Generate mock audio for testing (sine wave with envelope)."""
        samples = int(duration * self.sample_rate)
        t = np.linspace(0, duration, samples)
        
        # Generate tone with slight variation
        audio = np.sin(2 * np.pi * frequency * t)
        
        # Add envelope
        envelope = np.exp(-t / (duration * 0.7))
        audio *= envelope
        
        # Add some noise for realism
        audio += np.random.normal(0, 0.01, samples)
        
        return audio
    
    @handle_errors(default_error_code="ADAPTIVE_SCENE_FAILED")
    async def create_adaptive_scene(
        self,
        trip_id: str,
        checkpoints: List[Dict[str, Any]],
        total_duration: float
    ) -> Dict[str, Any]:
        """
        Create an adaptive audio scene that changes based on trip checkpoints.
        
        Args:
            trip_id: Trip identifier
            checkpoints: List of trip checkpoints with timestamps and contexts
            total_duration: Total trip duration
            
        Returns:
            Adaptive scene configuration
        """
        if not checkpoints:
            raise ValidationError("At least one checkpoint is required")
        
        # Sort checkpoints by time
        sorted_checkpoints = sorted(checkpoints, key=lambda x: x.get("time", 0))
        
        # Create variation points for adaptive soundscape
        variation_points = []
        
        for i, checkpoint in enumerate(sorted_checkpoints):
            time = checkpoint.get("time", i * 60)  # Default 1 minute intervals
            
            # Determine action based on checkpoint type
            if checkpoint.get("weather_change"):
                variation_points.append({
                    "time": time,
                    "action": "change_weather",
                    "weather": checkpoint["weather_change"],
                    "duration": 5.0
                })
            
            if checkpoint.get("activity_change"):
                variation_points.append({
                    "time": time,
                    "action": "change_activity",
                    "activity_level": checkpoint["activity_change"],
                    "duration": 3.0
                })
            
            if checkpoint.get("special_event"):
                variation_points.append({
                    "time": time,
                    "action": "add_event",
                    "event": checkpoint["special_event"],
                    "duration": 2.0
                })
        
        # Create adaptive soundscape
        base_environment = sorted_checkpoints[0].get("environment", "city")
        adaptive_scene = await self.ambient_generator.create_adaptive_soundscape(
            base_environment=base_environment,
            duration=total_duration,
            variation_points=variation_points
        )
        
        return {
            "trip_id": trip_id,
            "adaptive_scene": adaptive_scene,
            "checkpoint_count": len(checkpoints),
            "total_duration": total_duration
        }
    
    async def get_scene_analytics(self, scene_id: str) -> Dict[str, Any]:
        """Get analytics for a generated scene."""
        # In production, retrieve from database
        # For now, return mock analytics
        return {
            "scene_id": scene_id,
            "play_count": 42,
            "average_listen_duration": 180.5,
            "user_rating": 4.5,
            "generation_time": 1.2,
            "cache_hits": 15,
            "layer_complexity": 8
        }


# Dependency injection helper
def get_spatial_audio_engine(db: Session) -> SpatialAudioEngineV2:
    """Get spatial audio engine instance."""
    return SpatialAudioEngineV2(db)