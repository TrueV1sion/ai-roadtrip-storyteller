"""
Barge-In Detection Service
Allows users to interrupt ongoing voice responses naturally
"""

import asyncio
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import numpy as np
import logging

from ..core.cache import cache_manager
from .audio_orchestration_service import get_audio_orchestrator

logger = logging.getLogger(__name__)


class BargeInState(Enum):
    """States of barge-in detection"""
    IDLE = "idle"
    LISTENING = "listening"
    DETECTED = "detected"
    PROCESSING = "processing"
    COOLDOWN = "cooldown"


@dataclass
class BargeInConfig:
    """Configuration for barge-in detection"""
    enabled: bool = True
    sensitivity: float = 0.6  # 0.0 - 1.0
    min_speech_duration_ms: int = 300  # Minimum speech to trigger
    max_latency_ms: int = 150  # Maximum detection latency
    echo_cancellation: bool = True
    noise_threshold: float = 0.1
    confidence_threshold: float = 0.7


@dataclass
class BargeInEvent:
    """Barge-in detection event"""
    timestamp: datetime
    confidence: float
    speech_duration_ms: int
    interrupted_stream_id: Optional[str]
    audio_segment: Optional[bytes] = None
    intent_hint: Optional[str] = None  # Quick intent detection


class BargeInService:
    """
    Advanced barge-in detection service featuring:
    - Real-time speech detection during playback
    - Echo cancellation for system audio
    - Intent pre-classification
    - Adaptive sensitivity
    - False positive reduction
    """
    
    def __init__(self, config: BargeInConfig):
        self.config = config
        self.state = BargeInState.IDLE
        self.audio_orchestrator = get_audio_orchestrator()
        
        # Tracking
        self.active_playback_id: Optional[str] = None
        self.detection_callbacks: List[Callable] = []
        self.speech_buffer = bytearray()
        self.speech_start_time: Optional[datetime] = None
        
        # Echo cancellation
        self.reference_audio: Optional[np.ndarray] = None
        self.echo_estimator = self._initialize_echo_cancellation()
        
        # Performance metrics
        self.metrics = {
            "total_detections": 0,
            "successful_interruptions": 0,
            "false_positives": 0,
            "average_latency_ms": 0
        }
        
        logger.info("Barge-In Service initialized")
    
    async def start_monitoring(self, playback_stream_id: str):
        """
        Start monitoring for barge-in during playback
        
        Args:
            playback_stream_id: ID of the audio stream being played
        """
        if not self.config.enabled:
            return
        
        self.active_playback_id = playback_stream_id
        self.state = BargeInState.LISTENING
        self.speech_buffer.clear()
        self.speech_start_time = None
        
        logger.info(f"Started barge-in monitoring for stream: {playback_stream_id}")
        
        # Start detection loop
        asyncio.create_task(self._detection_loop())
    
    async def stop_monitoring(self):
        """Stop barge-in monitoring"""
        self.state = BargeInState.IDLE
        self.active_playback_id = None
        logger.info("Stopped barge-in monitoring")
    
    def add_detection_callback(self, callback: Callable):
        """Add callback for barge-in detection"""
        self.detection_callbacks.append(callback)
    
    async def process_audio_frame(
        self,
        audio_frame: bytes,
        reference_audio: Optional[bytes] = None
    ) -> Optional[BargeInEvent]:
        """
        Process audio frame for barge-in detection
        
        Args:
            audio_frame: Microphone audio (16kHz, 16-bit, mono)
            reference_audio: Currently playing audio for echo cancellation
            
        Returns:
            BargeInEvent if barge-in detected
        """
        if self.state != BargeInState.LISTENING:
            return None
        
        # Convert to numpy arrays
        mic_audio = np.frombuffer(audio_frame, dtype=np.int16).astype(float) / 32768.0
        
        # Apply echo cancellation if available
        if self.config.echo_cancellation and reference_audio:
            ref_audio = np.frombuffer(reference_audio, dtype=np.int16).astype(float) / 32768.0
            mic_audio = self._cancel_echo(mic_audio, ref_audio)
        
        # Check for speech
        is_speech = await self._detect_speech(mic_audio)
        
        if is_speech:
            # Add to speech buffer
            self._update_speech_buffer(audio_frame)
            
            # Check if we have enough speech
            if self._has_sufficient_speech():
                # Detect barge-in intent
                event = await self._create_barge_in_event()
                
                if event and event.confidence >= self.config.confidence_threshold:
                    await self._handle_barge_in(event)
                    return event
        else:
            # Reset if silence detected
            if self.speech_start_time:
                silence_duration = (datetime.now() - self.speech_start_time).total_seconds() * 1000
                if silence_duration > 500:  # 500ms silence resets
                    self._reset_speech_detection()
        
        return None
    
    async def adjust_sensitivity(self, sensitivity: float):
        """
        Dynamically adjust barge-in sensitivity
        
        Args:
            sensitivity: New sensitivity (0.0 - 1.0)
        """
        self.config.sensitivity = max(0.0, min(1.0, sensitivity))
        logger.info(f"Barge-in sensitivity adjusted to: {self.config.sensitivity}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get barge-in detection metrics"""
        total = self.metrics["total_detections"]
        if total == 0:
            return self.metrics
        
        success_rate = self.metrics["successful_interruptions"] / total
        false_positive_rate = self.metrics["false_positives"] / total
        
        return {
            **self.metrics,
            "success_rate": success_rate,
            "false_positive_rate": false_positive_rate,
            "sensitivity": self.config.sensitivity
        }
    
    # Private methods
    
    async def _detection_loop(self):
        """Main detection loop"""
        while self.state == BargeInState.LISTENING:
            try:
                # Check if playback is still active
                audio_state = await self.audio_orchestrator.get_audio_state()
                
                if self.active_playback_id not in [s["id"] for s in audio_state["streams"]]:
                    # Playback ended
                    await self.stop_monitoring()
                    break
                
                await asyncio.sleep(0.05)  # 50ms loop
                
            except Exception as e:
                logger.error(f"Error in barge-in detection loop: {e}")
                await asyncio.sleep(0.1)
    
    async def _detect_speech(self, audio: np.ndarray) -> bool:
        """
        Detect if audio contains speech
        
        Args:
            audio: Audio signal as numpy array
            
        Returns:
            True if speech detected
        """
        # Calculate energy
        energy = np.sqrt(np.mean(audio ** 2))
        
        if energy < self.config.noise_threshold:
            return False
        
        # Simple VAD (Voice Activity Detection)
        # Real implementation would use more sophisticated methods
        
        # Check zero crossing rate
        zcr = np.sum(np.diff(np.sign(audio)) != 0) / len(audio)
        
        # Speech typically has specific ZCR range
        is_speech_zcr = 0.02 < zcr < 0.1
        
        # Check spectral properties
        fft = np.fft.rfft(audio)
        magnitude = np.abs(fft)
        frequencies = np.fft.rfftfreq(len(audio), 1/16000)
        
        # Speech has energy concentrated in 300-3000 Hz
        speech_band = (frequencies > 300) & (frequencies < 3000)
        speech_energy_ratio = np.sum(magnitude[speech_band]) / np.sum(magnitude)
        
        is_speech_spectrum = speech_energy_ratio > 0.6
        
        # Combine detections with sensitivity
        threshold = 1.0 - self.config.sensitivity
        score = (is_speech_zcr * 0.4 + is_speech_spectrum * 0.6)
        
        return score > threshold
    
    def _update_speech_buffer(self, audio_frame: bytes):
        """Update speech buffer with new audio"""
        if self.speech_start_time is None:
            self.speech_start_time = datetime.now()
        
        self.speech_buffer.extend(audio_frame)
        
        # Limit buffer size (5 seconds max)
        max_bytes = 16000 * 2 * 5  # 16kHz, 16-bit, 5 seconds
        if len(self.speech_buffer) > max_bytes:
            self.speech_buffer = self.speech_buffer[-max_bytes:]
    
    def _has_sufficient_speech(self) -> bool:
        """Check if we have enough speech to trigger barge-in"""
        if self.speech_start_time is None:
            return False
        
        duration_ms = (datetime.now() - self.speech_start_time).total_seconds() * 1000
        return duration_ms >= self.config.min_speech_duration_ms
    
    async def _create_barge_in_event(self) -> Optional[BargeInEvent]:
        """Create barge-in event from detected speech"""
        if not self.speech_buffer:
            return None
        
        duration_ms = (datetime.now() - self.speech_start_time).total_seconds() * 1000
        
        # Quick intent detection from speech buffer
        intent_hint = await self._detect_intent_hint(bytes(self.speech_buffer))
        
        # Calculate confidence based on various factors
        confidence = self._calculate_confidence(duration_ms, intent_hint)
        
        return BargeInEvent(
            timestamp=datetime.now(),
            confidence=confidence,
            speech_duration_ms=int(duration_ms),
            interrupted_stream_id=self.active_playback_id,
            audio_segment=bytes(self.speech_buffer),
            intent_hint=intent_hint
        )
    
    async def _detect_intent_hint(self, audio_segment: bytes) -> Optional[str]:
        """
        Quick intent detection for barge-in
        Returns hint about user intent
        """
        # In real implementation, this would use a lightweight intent classifier
        # For now, return common interrupt intents
        
        # Check audio properties to guess intent
        audio_array = np.frombuffer(audio_segment, dtype=np.int16).astype(float) / 32768.0
        
        # High energy might indicate urgency
        energy = np.sqrt(np.mean(audio_array ** 2))
        
        if energy > 0.5:
            return "urgent_interruption"
        elif len(audio_segment) < 16000:  # Less than 1 second
            return "quick_command"
        else:
            return "normal_interruption"
    
    def _calculate_confidence(
        self,
        duration_ms: float,
        intent_hint: Optional[str]
    ) -> float:
        """Calculate confidence score for barge-in detection"""
        base_confidence = 0.5
        
        # Duration factor
        if duration_ms > 500:
            base_confidence += 0.2
        if duration_ms > 1000:
            base_confidence += 0.1
        
        # Intent factor
        if intent_hint == "urgent_interruption":
            base_confidence += 0.2
        elif intent_hint == "quick_command":
            base_confidence += 0.1
        
        # Apply sensitivity
        base_confidence *= (0.5 + self.config.sensitivity * 0.5)
        
        return min(1.0, base_confidence)
    
    async def _handle_barge_in(self, event: BargeInEvent):
        """Handle detected barge-in"""
        self.state = BargeInState.PROCESSING
        self.metrics["total_detections"] += 1
        
        # Stop current playback
        if event.interrupted_stream_id:
            try:
                await self.audio_orchestrator.stop_stream(
                    event.interrupted_stream_id,
                    fade_out=0.1  # Quick fade
                )
                self.metrics["successful_interruptions"] += 1
            except Exception as e:
                logger.error(f"Failed to stop playback on barge-in: {e}")
        
        # Trigger callbacks
        await self._trigger_callbacks(event)
        
        # Enter cooldown
        self.state = BargeInState.COOLDOWN
        await asyncio.sleep(0.5)  # 500ms cooldown
        
        # Reset
        self._reset_speech_detection()
        self.state = BargeInState.IDLE
    
    async def _trigger_callbacks(self, event: BargeInEvent):
        """Trigger all registered callbacks"""
        for callback in self.detection_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in barge-in callback: {e}")
    
    def _reset_speech_detection(self):
        """Reset speech detection state"""
        self.speech_buffer.clear()
        self.speech_start_time = None
    
    def _initialize_echo_cancellation(self):
        """Initialize echo cancellation system"""
        # Simplified echo cancellation
        # Real implementation would use adaptive filters
        return {
            "filter_length": 512,
            "adaptation_rate": 0.01,
            "coefficients": np.zeros(512)
        }
    
    def _cancel_echo(self, mic_audio: np.ndarray, ref_audio: np.ndarray) -> np.ndarray:
        """
        Cancel echo from microphone audio
        
        Args:
            mic_audio: Microphone signal
            ref_audio: Reference (playing) audio
            
        Returns:
            Echo-cancelled audio
        """
        # Simplified echo cancellation
        # Real implementation would use NLMS or similar algorithms
        
        # Ensure same length
        min_len = min(len(mic_audio), len(ref_audio))
        mic_audio = mic_audio[:min_len]
        ref_audio = ref_audio[:min_len]
        
        # Simple spectral subtraction
        mic_fft = np.fft.rfft(mic_audio)
        ref_fft = np.fft.rfft(ref_audio)
        
        # Estimate echo spectrum
        echo_estimate = ref_fft * 0.3  # Simple scaling
        
        # Subtract echo
        cleaned_fft = mic_fft - echo_estimate
        
        # Prevent over-subtraction
        cleaned_fft = np.maximum(cleaned_fft, mic_fft * 0.1)
        
        # Convert back to time domain
        cleaned_audio = np.fft.irfft(cleaned_fft, len(mic_audio))
        
        return cleaned_audio


# Global instance
barge_in_service = None

def get_barge_in_service(config: Optional[BargeInConfig] = None) -> BargeInService:
    """Get or create barge-in service instance"""
    global barge_in_service
    if barge_in_service is None:
        if config is None:
            config = BargeInConfig()
        barge_in_service = BargeInService(config)
    return barge_in_service