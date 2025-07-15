"""
Spatial Audio Engine - State-of-the-art 3D audio processing for immersive storytelling
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import logging
from scipy import signal
from scipy.spatial import distance
import json

logger = logging.getLogger(__name__)


class AudioEnvironment(Enum):
    """Different acoustic environments for spatial processing"""
    FOREST = "forest"
    CITY = "city"
    HIGHWAY = "highway"
    MOUNTAIN = "mountain"
    DESERT = "desert"
    COASTAL = "coastal"
    TUNNEL = "tunnel"
    BRIDGE = "bridge"
    RURAL = "rural"
    URBAN_CANYON = "urban_canyon"


class SoundSource(Enum):
    """Types of sound sources in the 3D space"""
    NARRATOR = "narrator"
    CHARACTER = "character"
    AMBIENT = "ambient"
    VEHICLE = "vehicle"
    NATURE = "nature"
    MUSIC = "music"
    NAVIGATION = "navigation"
    EFFECT = "effect"


@dataclass
class AudioPosition:
    """3D position for audio source"""
    x: float  # Left(-1) to Right(1)
    y: float  # Down(-1) to Up(1)
    z: float  # Behind(-1) to Front(1)
    
    def distance_from_origin(self) -> float:
        """Calculate distance from listener at origin"""
        return np.sqrt(self.x**2 + self.y**2 + self.z**2)
    
    def azimuth(self) -> float:
        """Calculate horizontal angle from front"""
        return np.arctan2(self.x, self.z) * 180 / np.pi
    
    def elevation(self) -> float:
        """Calculate vertical angle from horizontal plane"""
        dist_horizontal = np.sqrt(self.x**2 + self.z**2)
        return np.arctan2(self.y, dist_horizontal) * 180 / np.pi


@dataclass
class SpatialAudioSource:
    """A sound source in 3D space"""
    source_id: str
    source_type: SoundSource
    position: AudioPosition
    volume: float = 1.0
    priority: int = 5  # 1-10, higher is more important
    movement_path: Optional[List[AudioPosition]] = None
    doppler_enabled: bool = True
    distance_attenuation: bool = True
    environment_reverb: bool = True
    
    
@dataclass
class HRTFProfile:
    """Head-Related Transfer Function profile for binaural audio"""
    name: str
    left_ear_impulse: np.ndarray = field(default_factory=lambda: np.array([]))
    right_ear_impulse: np.ndarray = field(default_factory=lambda: np.array([]))
    frequency_response: Dict[str, np.ndarray] = field(default_factory=dict)


@dataclass
class EnvironmentAcoustics:
    """Acoustic properties of an environment"""
    environment: AudioEnvironment
    reverb_time: float  # RT60 in seconds
    early_reflections: List[Tuple[float, float]]  # (delay_ms, gain)
    late_reverb_density: float  # 0-1
    high_frequency_damping: float  # 0-1
    diffusion: float  # 0-1
    pre_delay: float  # milliseconds
    
    
class SpatialAudioEngine:
    """
    Advanced spatial audio processing engine for immersive 3D soundscapes
    """
    
    def __init__(self):
        self.sample_rate = 48000  # High quality audio
        self.buffer_size = 2048
        self.active_sources: Dict[str, SpatialAudioSource] = {}
        self.environment = AudioEnvironment.RURAL
        self.listener_position = AudioPosition(0, 0, 0)
        self.listener_heading = 0  # degrees, 0 = north
        self.vehicle_speed = 0  # km/h
        
        # Load HRTF profiles
        self.hrtf_profiles = self._load_hrtf_profiles()
        self.current_hrtf = "generic"
        
        # Environment acoustics database
        self.environment_acoustics = self._initialize_acoustics()
        
        # Processing state
        self.processing_active = False
        self.audio_buffer = np.zeros((self.buffer_size, 2))  # Stereo
        
    def _load_hrtf_profiles(self) -> Dict[str, HRTFProfile]:
        """Load Head-Related Transfer Function profiles"""
        # In production, load from actual HRTF database
        # For now, create basic profiles
        profiles = {}
        
        # Generic HRTF using simple ITD/ILD model
        profiles["generic"] = self._create_generic_hrtf()
        
        # Could add more profiles: "small_head", "large_head", etc.
        
        return profiles
    
    def _create_generic_hrtf(self) -> HRTFProfile:
        """Create a basic generic HRTF profile"""
        # Simplified HRTF using Interaural Time Difference (ITD) and
        # Interaural Level Difference (ILD)
        profile = HRTFProfile(name="generic")
        
        # Create basic impulse responses
        # In reality, these would be measured responses
        profile.left_ear_impulse = np.array([1.0, 0.3, 0.1, 0.05])
        profile.right_ear_impulse = np.array([1.0, 0.3, 0.1, 0.05])
        
        return profile
    
    def _initialize_acoustics(self) -> Dict[AudioEnvironment, EnvironmentAcoustics]:
        """Initialize acoustic properties for each environment"""
        return {
            AudioEnvironment.FOREST: EnvironmentAcoustics(
                environment=AudioEnvironment.FOREST,
                reverb_time=0.8,
                early_reflections=[(20, 0.5), (40, 0.3), (60, 0.2)],
                late_reverb_density=0.6,
                high_frequency_damping=0.7,
                diffusion=0.8,
                pre_delay=10
            ),
            AudioEnvironment.CITY: EnvironmentAcoustics(
                environment=AudioEnvironment.CITY,
                reverb_time=1.2,
                early_reflections=[(10, 0.6), (25, 0.4), (40, 0.3), (55, 0.2)],
                late_reverb_density=0.8,
                high_frequency_damping=0.4,
                diffusion=0.6,
                pre_delay=5
            ),
            AudioEnvironment.HIGHWAY: EnvironmentAcoustics(
                environment=AudioEnvironment.HIGHWAY,
                reverb_time=0.3,
                early_reflections=[(5, 0.2), (15, 0.1)],
                late_reverb_density=0.2,
                high_frequency_damping=0.9,
                diffusion=0.3,
                pre_delay=2
            ),
            AudioEnvironment.MOUNTAIN: EnvironmentAcoustics(
                environment=AudioEnvironment.MOUNTAIN,
                reverb_time=2.5,
                early_reflections=[(100, 0.7), (200, 0.5), (350, 0.3), (500, 0.2)],
                late_reverb_density=0.4,
                high_frequency_damping=0.6,
                diffusion=0.9,
                pre_delay=50
            ),
            AudioEnvironment.TUNNEL: EnvironmentAcoustics(
                environment=AudioEnvironment.TUNNEL,
                reverb_time=3.0,
                early_reflections=[(5, 0.8), (15, 0.6), (30, 0.5), (45, 0.4)],
                late_reverb_density=0.9,
                high_frequency_damping=0.3,
                diffusion=0.4,
                pre_delay=2
            ),
            AudioEnvironment.COASTAL: EnvironmentAcoustics(
                environment=AudioEnvironment.COASTAL,
                reverb_time=0.6,
                early_reflections=[(30, 0.3), (60, 0.2)],
                late_reverb_density=0.3,
                high_frequency_damping=0.8,
                diffusion=0.7,
                pre_delay=15
            ),
        }
    
    async def add_source(self, source: SpatialAudioSource) -> None:
        """Add a sound source to the 3D space"""
        self.active_sources[source.source_id] = source
        logger.info(f"Added spatial audio source: {source.source_id} at position {source.position}")
    
    async def remove_source(self, source_id: str) -> None:
        """Remove a sound source"""
        if source_id in self.active_sources:
            del self.active_sources[source_id]
            logger.info(f"Removed spatial audio source: {source_id}")
    
    async def update_source_position(self, source_id: str, new_position: AudioPosition) -> None:
        """Update position of a sound source"""
        if source_id in self.active_sources:
            self.active_sources[source_id].position = new_position
    
    async def set_environment(self, environment: AudioEnvironment) -> None:
        """Change the acoustic environment"""
        self.environment = environment
        logger.info(f"Changed audio environment to: {environment.value}")
    
    async def update_listener(self, position: AudioPosition, heading: float, speed: float) -> None:
        """Update listener position and orientation"""
        self.listener_position = position
        self.listener_heading = heading
        self.vehicle_speed = speed
    
    def process_audio_frame(self, input_audio: np.ndarray) -> np.ndarray:
        """
        Process a frame of audio with spatial effects
        
        Args:
            input_audio: Mono or stereo audio frame
            
        Returns:
            Processed stereo audio with spatial effects
        """
        if input_audio.ndim == 1:
            # Convert mono to stereo
            input_audio = np.column_stack((input_audio, input_audio))
        
        # Initialize output
        output = np.zeros_like(input_audio)
        
        # Process each active source
        for source_id, source in self.active_sources.items():
            # Calculate relative position
            rel_position = self._calculate_relative_position(source.position)
            
            # Apply HRTF
            processed = self._apply_hrtf(input_audio, rel_position)
            
            # Apply distance attenuation
            if source.distance_attenuation:
                distance = rel_position.distance_from_origin()
                attenuation = 1.0 / max(1.0, distance)
                processed *= attenuation
            
            # Apply Doppler effect
            if source.doppler_enabled and self.vehicle_speed > 0:
                processed = self._apply_doppler(processed, source, rel_position)
            
            # Add to output with source volume
            output += processed * source.volume
        
        # Apply environmental reverb
        output = self._apply_environment_reverb(output)
        
        # Normalize to prevent clipping
        max_val = np.max(np.abs(output))
        if max_val > 1.0:
            output /= max_val
        
        return output
    
    def _calculate_relative_position(self, source_position: AudioPosition) -> AudioPosition:
        """Calculate position relative to listener"""
        # Account for listener position and heading
        # Simplified for now - full implementation would include rotation matrices
        rel_x = source_position.x - self.listener_position.x
        rel_y = source_position.y - self.listener_position.y
        rel_z = source_position.z - self.listener_position.z
        
        # Rotate by listener heading
        heading_rad = np.radians(self.listener_heading)
        rotated_x = rel_x * np.cos(heading_rad) - rel_z * np.sin(heading_rad)
        rotated_z = rel_x * np.sin(heading_rad) + rel_z * np.cos(heading_rad)
        
        return AudioPosition(rotated_x, rel_y, rotated_z)
    
    def _apply_hrtf(self, audio: np.ndarray, position: AudioPosition) -> np.ndarray:
        """Apply Head-Related Transfer Function for binaural spatialization"""
        # Calculate interaural time difference (ITD)
        # Head radius ~8.75cm, speed of sound ~343 m/s
        azimuth_rad = np.radians(position.azimuth())
        itd_seconds = 0.0875 * np.sin(azimuth_rad) / 343.0
        itd_samples = int(itd_seconds * self.sample_rate)
        
        # Calculate interaural level difference (ILD)
        # Simplified model: 20dB max difference
        ild_db = 20 * np.sin(azimuth_rad)
        ild_left = 10 ** (-max(0, ild_db) / 20)
        ild_right = 10 ** (-max(0, -ild_db) / 20)
        
        # Apply ITD and ILD
        left_channel = audio[:, 0] * ild_left
        right_channel = audio[:, 1] * ild_right
        
        # Apply delay for ITD
        if itd_samples > 0:
            # Delay right ear
            right_channel = np.pad(right_channel, (itd_samples, 0), mode='constant')[:-itd_samples]
        elif itd_samples < 0:
            # Delay left ear
            left_channel = np.pad(left_channel, (-itd_samples, 0), mode='constant')[:itd_samples]
        
        # Elevation filtering (simplified)
        elevation = position.elevation()
        if abs(elevation) > 30:
            # Apply high-frequency boost/cut for elevation
            nyquist = self.sample_rate / 2
            if elevation > 0:  # Above
                # Boost high frequencies
                b, a = signal.butter(2, 4000 / nyquist, 'high')
            else:  # Below
                # Cut high frequencies
                b, a = signal.butter(2, 4000 / nyquist, 'low')
            
            left_channel = signal.filtfilt(b, a, left_channel)
            right_channel = signal.filtfilt(b, a, right_channel)
        
        return np.column_stack((left_channel, right_channel))
    
    def _apply_doppler(self, audio: np.ndarray, source: SpatialAudioSource, 
                      rel_position: AudioPosition) -> np.ndarray:
        """Apply Doppler effect based on relative motion"""
        # Calculate relative velocity (simplified)
        # In full implementation, track source movement over time
        relative_speed = self.vehicle_speed * np.cos(np.radians(rel_position.azimuth()))
        
        # Doppler shift factor
        sound_speed = 343  # m/s
        speed_ms = relative_speed / 3.6  # km/h to m/s
        doppler_factor = sound_speed / (sound_speed + speed_ms)
        
        if abs(doppler_factor - 1.0) > 0.01:
            # Resample audio for pitch shift
            resampled_length = int(len(audio) * doppler_factor)
            left_resampled = signal.resample(audio[:, 0], resampled_length)
            right_resampled = signal.resample(audio[:, 1], resampled_length)
            
            # Pad or trim to original length
            if resampled_length > len(audio):
                left_resampled = left_resampled[:len(audio)]
                right_resampled = right_resampled[:len(audio)]
            else:
                pad_length = len(audio) - resampled_length
                left_resampled = np.pad(left_resampled, (0, pad_length), mode='constant')
                right_resampled = np.pad(right_resampled, (0, pad_length), mode='constant')
            
            audio = np.column_stack((left_resampled, right_resampled))
        
        return audio
    
    def _apply_environment_reverb(self, audio: np.ndarray) -> np.ndarray:
        """Apply environmental reverb based on current environment"""
        acoustics = self.environment_acoustics.get(
            self.environment,
            self.environment_acoustics[AudioEnvironment.RURAL]
        )
        
        output = audio.copy()
        
        # Apply early reflections
        for delay_ms, gain in acoustics.early_reflections:
            delay_samples = int(delay_ms * self.sample_rate / 1000)
            if delay_samples < len(audio):
                delayed = np.pad(audio, ((delay_samples, 0), (0, 0)), mode='constant')[:-delay_samples]
                output += delayed * gain
        
        # Simple late reverb using comb filters
        if acoustics.late_reverb_density > 0:
            # Create comb filter delays based on reverb time
            comb_delays = [
                int(0.03 * self.sample_rate),
                int(0.037 * self.sample_rate),
                int(0.041 * self.sample_rate),
                int(0.043 * self.sample_rate)
            ]
            
            reverb_signal = np.zeros_like(audio)
            for delay in comb_delays:
                if delay < len(audio):
                    comb_output = signal.lfilter(
                        [1], 
                        np.concatenate(([1], np.zeros(delay-1), [-0.8 * acoustics.late_reverb_density])),
                        audio, axis=0
                    )
                    reverb_signal += comb_output * 0.25
            
            # Apply high-frequency damping
            if acoustics.high_frequency_damping > 0:
                nyquist = self.sample_rate / 2
                cutoff = nyquist * (1 - acoustics.high_frequency_damping * 0.8)
                b, a = signal.butter(1, cutoff / nyquist, 'low')
                reverb_signal = signal.filtfilt(b, a, reverb_signal, axis=0)
            
            # Mix with dry signal
            wet_gain = 0.3 * acoustics.reverb_time / 3.0  # Scale by reverb time
            output = output * (1 - wet_gain) + reverb_signal * wet_gain
        
        return output
    
    async def create_soundscape(self, location: Dict[str, Any], 
                              time_of_day: str, weather: str) -> Dict[str, Any]:
        """
        Create an immersive soundscape based on location and conditions
        
        Args:
            location: Current location info (terrain, landmarks, etc.)
            time_of_day: morning, afternoon, evening, night
            weather: clear, rain, snow, fog, etc.
            
        Returns:
            Soundscape configuration with positioned audio sources
        """
        soundscape = {
            "environment": self._determine_environment(location),
            "sources": []
        }
        
        # Add ambient sounds based on environment
        if soundscape["environment"] == AudioEnvironment.FOREST:
            # Birds in different positions
            if time_of_day in ["morning", "afternoon"]:
                soundscape["sources"].extend([
                    {
                        "id": "birds_left",
                        "type": SoundSource.NATURE,
                        "position": AudioPosition(-0.8, 0.5, 0.3),
                        "volume": 0.4,
                        "sound": "forest_birds_1"
                    },
                    {
                        "id": "birds_right", 
                        "type": SoundSource.NATURE,
                        "position": AudioPosition(0.7, 0.6, -0.2),
                        "volume": 0.3,
                        "sound": "forest_birds_2"
                    }
                ])
            
            # Wind through trees
            soundscape["sources"].append({
                "id": "wind",
                "type": SoundSource.NATURE,
                "position": AudioPosition(0, 0.8, 0),
                "volume": 0.5,
                "sound": "wind_trees"
            })
            
        elif soundscape["environment"] == AudioEnvironment.COASTAL:
            # Ocean waves
            soundscape["sources"].append({
                "id": "waves",
                "type": SoundSource.NATURE,
                "position": AudioPosition(0, 0, 1),  # In front
                "volume": 0.7,
                "sound": "ocean_waves"
            })
            
            # Seagulls
            soundscape["sources"].append({
                "id": "seagulls",
                "type": SoundSource.NATURE,
                "position": AudioPosition(0.5, 0.7, 0.5),
                "volume": 0.3,
                "sound": "seagulls",
                "movement_path": [
                    AudioPosition(0.5, 0.7, 0.5),
                    AudioPosition(-0.5, 0.6, 0.3),
                    AudioPosition(-0.8, 0.5, -0.5)
                ]
            })
        
        # Add weather effects
        if weather == "rain":
            soundscape["sources"].append({
                "id": "rain",
                "type": SoundSource.NATURE,
                "position": AudioPosition(0, 1, 0),  # Above
                "volume": 0.8,
                "sound": "rain_medium"
            })
        
        # Position narrator optimally
        soundscape["sources"].append({
            "id": "narrator",
            "type": SoundSource.NARRATOR,
            "position": AudioPosition(0, 0, 0.3),  # Slightly in front
            "volume": 1.0,
            "priority": 10
        })
        
        return soundscape
    
    def _determine_environment(self, location: Dict[str, Any]) -> AudioEnvironment:
        """Determine audio environment from location data"""
        terrain = location.get("terrain", "").lower()
        landmarks = location.get("landmarks", [])
        road_type = location.get("road_type", "").lower()
        
        # Check specific conditions
        if "tunnel" in road_type or "tunnel" in terrain:
            return AudioEnvironment.TUNNEL
        elif "bridge" in road_type:
            return AudioEnvironment.BRIDGE
        elif "highway" in road_type or "interstate" in road_type:
            return AudioEnvironment.HIGHWAY
        elif "city" in terrain or "urban" in terrain:
            return AudioEnvironment.CITY
        elif "forest" in terrain or "woods" in terrain:
            return AudioEnvironment.FOREST
        elif "mountain" in terrain or "alpine" in terrain:
            return AudioEnvironment.MOUNTAIN
        elif "coast" in terrain or "beach" in terrain:
            return AudioEnvironment.COASTAL
        elif "desert" in terrain:
            return AudioEnvironment.DESERT
        else:
            return AudioEnvironment.RURAL
    
    async def generate_transition_effect(self, from_env: AudioEnvironment, 
                                       to_env: AudioEnvironment,
                                       duration_seconds: float) -> np.ndarray:
        """Generate smooth transition between environments"""
        samples = int(duration_seconds * self.sample_rate)
        
        # Create transition envelope
        envelope = np.linspace(0, 1, samples)
        
        # Generate characteristic sounds for each environment
        from_sound = self._generate_environment_signature(from_env, samples)
        to_sound = self._generate_environment_signature(to_env, samples)
        
        # Crossfade between environments
        transition = from_sound * (1 - envelope[:, np.newaxis]) + to_sound * envelope[:, np.newaxis]
        
        return transition
    
    def _generate_environment_signature(self, environment: AudioEnvironment, 
                                      samples: int) -> np.ndarray:
        """Generate characteristic sound for an environment"""
        # Simplified - in production would use actual recorded ambiences
        output = np.zeros((samples, 2))
        
        if environment == AudioEnvironment.CITY:
            # Urban rumble
            noise = np.random.normal(0, 0.1, (samples, 2))
            b, a = signal.butter(4, 200 / (self.sample_rate/2), 'low')
            output = signal.filtfilt(b, a, noise, axis=0)
        
        elif environment == AudioEnvironment.FOREST:
            # High-frequency nature sounds
            noise = np.random.normal(0, 0.05, (samples, 2))
            b, a = signal.butter(4, [2000 / (self.sample_rate/2), 
                                   8000 / (self.sample_rate/2)], 'band')
            output = signal.filtfilt(b, a, noise, axis=0)
        
        elif environment == AudioEnvironment.HIGHWAY:
            # Road noise
            noise = np.random.normal(0, 0.15, (samples, 2))
            b, a = signal.butter(4, [100 / (self.sample_rate/2), 
                                   1000 / (self.sample_rate/2)], 'band')
            output = signal.filtfilt(b, a, noise, axis=0)
        
        return output
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information about spatial audio state"""
        return {
            "environment": self.environment.value,
            "active_sources": len(self.active_sources),
            "sources": [
                {
                    "id": source.source_id,
                    "type": source.source_type.value,
                    "position": {
                        "x": source.position.x,
                        "y": source.position.y,
                        "z": source.position.z
                    },
                    "volume": source.volume
                }
                for source in self.active_sources.values()
            ],
            "listener": {
                "position": {
                    "x": self.listener_position.x,
                    "y": self.listener_position.y,
                    "z": self.listener_position.z
                },
                "heading": self.listener_heading,
                "speed": self.vehicle_speed
            },
            "hrtf_profile": self.current_hrtf
        }


# Global instance
spatial_audio_engine = SpatialAudioEngine()