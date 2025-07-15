"""
Spatial Audio Schemas - Request/response models for 3D audio
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from enum import Enum


class AudioEnvironment(str, Enum):
    """Different acoustic environments"""
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


class AudioPosition(BaseModel):
    """3D position for audio sources"""
    x: float = Field(..., ge=-1, le=1, description="Left(-1) to Right(1)")
    y: float = Field(..., ge=-1, le=1, description="Down(-1) to Up(1)")
    z: float = Field(..., ge=-1, le=1, description="Behind(-1) to Front(1)")


class SpatialAudioRequest(BaseModel):
    """Request for spatial audio coordination"""
    audio_type: str = Field(..., description="Type of audio: story, navigation, ambient")
    location_context: Dict[str, Any] = Field(..., description="Current location and environment info")
    audio_metadata: Dict[str, Any] = Field(default_factory=dict, description="Details about the audio content")


class SoundscapeSource(BaseModel):
    """Individual sound source in a soundscape"""
    id: str
    type: str
    position: AudioPosition
    volume: float = Field(0.5, ge=0, le=1)
    sound: str
    priority: Optional[int] = Field(3, ge=1, le=10)
    movement_path: Optional[List[AudioPosition]] = None


class SoundscapeConfig(BaseModel):
    """Complete soundscape configuration"""
    environment: AudioEnvironment
    sources: List[SoundscapeSource]


class ProcessingConfig(BaseModel):
    """Audio processing configuration"""
    sample_rate: int = 48000
    hrtf_profile: str = "generic"


class SpatialAudioResponse(BaseModel):
    """Response from spatial audio coordination"""
    status: str
    environment: str
    active_sources: int
    soundscape: SoundscapeConfig
    processing_config: ProcessingConfig


class EnvironmentUpdateRequest(BaseModel):
    """Request to update audio environment"""
    environment: AudioEnvironment
    from_environment: Optional[AudioEnvironment] = None
    generate_transition: bool = False
    transition_duration: Optional[float] = Field(2.0, ge=0.5, le=5.0)


class AudioSourceUpdate(BaseModel):
    """Update for an audio source"""
    source_id: str
    position: Optional[AudioPosition] = None
    volume: Optional[float] = Field(None, ge=0, le=1)
    priority: Optional[int] = Field(None, ge=1, le=10)