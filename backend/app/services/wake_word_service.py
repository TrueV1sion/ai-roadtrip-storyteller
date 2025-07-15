"""
Wake Word Detection Service
Enables hands-free voice activation with custom wake words
"""

import asyncio
import numpy as np
from typing import Optional, List, Callable, Dict, Any
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime, timedelta
import wave
import struct

from ..core.cache import cache_manager
from ..monitoring.metrics import metrics

logger = logging.getLogger(__name__)


class WakeWordModel(Enum):
    """Available wake word models"""
    HEY_ROADTRIP = "hey_roadtrip"
    OK_JOURNEY = "ok_journey"
    HELLO_ADVENTURE = "hello_adventure"
    CUSTOM = "custom"


@dataclass
class WakeWordConfig:
    """Configuration for wake word detection"""
    model: WakeWordModel
    sensitivity: float = 0.5  # 0.0 - 1.0
    timeout_seconds: int = 10  # Time to listen after activation
    cooldown_seconds: int = 2  # Minimum time between activations
    audio_threshold: float = 0.02  # Minimum audio level to process
    pre_roll_ms: int = 500  # Audio to include before wake word
    
    
@dataclass
class DetectionResult:
    """Result of wake word detection"""
    detected: bool
    confidence: float
    timestamp: datetime
    audio_segment: Optional[bytes] = None
    wake_word: Optional[str] = None


class WakeWordService:
    """
    Advanced wake word detection service with:
    - Multiple wake word support
    - Confidence scoring
    - False positive reduction
    - Energy-based activation
    - Customizable sensitivity
    """
    
    def __init__(self, config: WakeWordConfig):
        self.config = config
        self.is_listening = False
        self.last_detection_time: Optional[datetime] = None
        self.detection_callbacks: List[Callable] = []
        self.audio_buffer = bytearray()
        self.buffer_duration_ms = 2000  # Keep 2 seconds of audio
        
        # Wake word models (simplified - real implementation would use ML models)
        self.wake_word_patterns = self._initialize_wake_words()
        
        # Performance tracking
        self.detection_stats = {
            "total_processed": 0,
            "true_positives": 0,
            "false_positives": 0,
            "missed_detections": 0
        }
        
        logger.info(f"Wake Word Service initialized with model: {config.model.value}")
    
    async def start_listening(self):
        """Start listening for wake words"""
        if self.is_listening:
            logger.warning("Wake word detection already active")
            return
        
        self.is_listening = True
        logger.info("Started listening for wake words")
        
        # Start the detection loop
        asyncio.create_task(self._detection_loop())
    
    async def stop_listening(self):
        """Stop listening for wake words"""
        self.is_listening = False
        logger.info("Stopped listening for wake words")
    
    def add_detection_callback(self, callback: Callable):
        """Add a callback for wake word detection"""
        self.detection_callbacks.append(callback)
    
    async def process_audio_chunk(self, audio_chunk: bytes) -> Optional[DetectionResult]:
        """
        Process an audio chunk for wake word detection
        
        Args:
            audio_chunk: Raw audio bytes (16kHz, 16-bit, mono)
            
        Returns:
            DetectionResult if wake word detected, None otherwise
        """
        if not self.is_listening:
            return None
        
        # Check cooldown
        if not self._check_cooldown():
            return None
        
        # Add to rolling buffer
        self._update_audio_buffer(audio_chunk)
        
        # Check audio energy level
        if not self._has_sufficient_energy(audio_chunk):
            return None
        
        # Perform detection
        result = await self._detect_wake_word(audio_chunk)
        
        if result.detected:
            self.last_detection_time = datetime.now()
            await self._trigger_callbacks(result)
            
            # Record metrics
            metrics.increment_counter("wake_word_detections", {
                "model": self.config.model.value,
                "confidence": str(round(result.confidence, 1))
            })
        
        self.detection_stats["total_processed"] += 1
        
        return result
    
    async def train_custom_wake_word(
        self,
        audio_samples: List[bytes],
        wake_word_text: str
    ) -> bool:
        """
        Train a custom wake word from user samples
        
        Args:
            audio_samples: List of audio recordings of the wake word
            wake_word_text: Text representation of the wake word
            
        Returns:
            True if training successful
        """
        if len(audio_samples) < 3:
            logger.error("Need at least 3 samples for custom wake word")
            return False
        
        try:
            # Extract features from samples
            features = []
            for sample in audio_samples:
                feature = self._extract_audio_features(sample)
                features.append(feature)
            
            # Create custom model (simplified - real implementation would use ML)
            custom_model = {
                "text": wake_word_text,
                "features": features,
                "threshold": 0.7
            }
            
            # Store custom model
            await cache_manager.set(
                f"custom_wake_word_{wake_word_text}",
                custom_model,
                ttl=86400 * 30  # 30 days
            )
            
            # Update patterns
            self.wake_word_patterns[WakeWordModel.CUSTOM] = custom_model
            
            logger.info(f"Trained custom wake word: {wake_word_text}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to train custom wake word: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get wake word detection statistics"""
        total = self.detection_stats["total_processed"]
        if total == 0:
            return self.detection_stats
        
        return {
            **self.detection_stats,
            "detection_rate": self.detection_stats["true_positives"] / total,
            "false_positive_rate": self.detection_stats["false_positives"] / total,
            "sensitivity": self.config.sensitivity,
            "model": self.config.model.value
        }
    
    async def adjust_sensitivity(self, new_sensitivity: float):
        """Dynamically adjust detection sensitivity"""
        self.config.sensitivity = max(0.0, min(1.0, new_sensitivity))
        logger.info(f"Wake word sensitivity adjusted to: {self.config.sensitivity}")
    
    # Private methods
    
    async def _detection_loop(self):
        """Main detection loop"""
        while self.is_listening:
            try:
                # In a real implementation, this would get audio from microphone
                # For now, we'll simulate with a sleep
                await asyncio.sleep(0.1)
                
                # Process any queued audio
                # This would be replaced with actual audio capture
                
            except Exception as e:
                logger.error(f"Error in detection loop: {e}")
                await asyncio.sleep(1)
    
    def _check_cooldown(self) -> bool:
        """Check if enough time has passed since last detection"""
        if self.last_detection_time is None:
            return True
        
        elapsed = (datetime.now() - self.last_detection_time).total_seconds()
        return elapsed >= self.config.cooldown_seconds
    
    def _update_audio_buffer(self, audio_chunk: bytes):
        """Update rolling audio buffer"""
        self.audio_buffer.extend(audio_chunk)
        
        # Trim buffer to maximum duration
        max_bytes = int(16000 * 2 * self.buffer_duration_ms / 1000)  # 16kHz, 16-bit
        if len(self.audio_buffer) > max_bytes:
            self.audio_buffer = self.audio_buffer[-max_bytes:]
    
    def _has_sufficient_energy(self, audio_chunk: bytes) -> bool:
        """Check if audio has sufficient energy for processing"""
        # Convert bytes to numpy array
        audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
        
        # Calculate RMS energy
        rms = np.sqrt(np.mean(audio_array.astype(float) ** 2)) / 32768.0
        
        return rms > self.config.audio_threshold
    
    async def _detect_wake_word(self, audio_chunk: bytes) -> DetectionResult:
        """Perform wake word detection on audio chunk"""
        # Extract features
        features = self._extract_audio_features(audio_chunk)
        
        # Get model for current wake word
        model = self.wake_word_patterns.get(self.config.model, {})
        
        # Calculate similarity (simplified - real implementation would use neural networks)
        confidence = self._calculate_confidence(features, model)
        
        # Apply sensitivity threshold
        threshold = 0.7 - (self.config.sensitivity * 0.4)  # 0.3 to 0.7 range
        detected = confidence > threshold
        
        # Get pre-roll audio if detected
        audio_segment = None
        if detected:
            pre_roll_bytes = int(16000 * 2 * self.config.pre_roll_ms / 1000)
            start_idx = max(0, len(self.audio_buffer) - pre_roll_bytes)
            audio_segment = bytes(self.audio_buffer[start_idx:])
        
        return DetectionResult(
            detected=detected,
            confidence=confidence,
            timestamp=datetime.now(),
            audio_segment=audio_segment,
            wake_word=self.config.model.value if detected else None
        )
    
    def _extract_audio_features(self, audio_chunk: bytes) -> Dict[str, float]:
        """Extract audio features for wake word detection"""
        audio_array = np.frombuffer(audio_chunk, dtype=np.int16).astype(float) / 32768.0
        
        # Simple feature extraction (real implementation would use MFCC, etc.)
        features = {
            "energy": np.sqrt(np.mean(audio_array ** 2)),
            "zero_crossings": np.sum(np.diff(np.sign(audio_array)) != 0) / len(audio_array),
            "spectral_centroid": self._calculate_spectral_centroid(audio_array),
            "duration": len(audio_array) / 16000.0
        }
        
        return features
    
    def _calculate_spectral_centroid(self, audio_array: np.ndarray) -> float:
        """Calculate spectral centroid of audio"""
        fft = np.fft.rfft(audio_array)
        magnitude = np.abs(fft)
        frequencies = np.fft.rfftfreq(len(audio_array), 1/16000)
        
        if np.sum(magnitude) == 0:
            return 0
        
        return np.sum(frequencies * magnitude) / np.sum(magnitude)
    
    def _calculate_confidence(
        self,
        features: Dict[str, float],
        model: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for wake word detection"""
        if not model:
            return 0.0
        
        # Simplified confidence calculation
        # Real implementation would use trained ML model
        base_confidence = 0.5
        
        # Check energy similarity
        if "features" in model:
            model_energy = np.mean([f["energy"] for f in model["features"]])
            energy_diff = abs(features["energy"] - model_energy) / model_energy
            base_confidence += (1 - energy_diff) * 0.3
        
        # Add some randomness for simulation
        import random
        base_confidence += random.uniform(-0.1, 0.1)
        
        return max(0.0, min(1.0, base_confidence))
    
    async def _trigger_callbacks(self, result: DetectionResult):
        """Trigger all registered callbacks"""
        for callback in self.detection_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(result)
                else:
                    callback(result)
            except Exception as e:
                logger.error(f"Error in wake word callback: {e}")
    
    def _initialize_wake_words(self) -> Dict[WakeWordModel, Dict[str, Any]]:
        """Initialize wake word models"""
        return {
            WakeWordModel.HEY_ROADTRIP: {
                "phonemes": ["HH", "EY", "R", "OW", "D", "T", "R", "IH", "P"],
                "duration_range": (0.8, 1.5),
                "energy_profile": "rising"
            },
            WakeWordModel.OK_JOURNEY: {
                "phonemes": ["OW", "K", "EY", "JH", "ER", "N", "IY"],
                "duration_range": (0.7, 1.3),
                "energy_profile": "steady"
            },
            WakeWordModel.HELLO_ADVENTURE: {
                "phonemes": ["HH", "AH", "L", "OW", "AE", "D", "V", "EH", "N", "CH", "ER"],
                "duration_range": (1.0, 1.8),
                "energy_profile": "falling"
            }
        }


# Global instance
wake_word_service = None

def get_wake_word_service(config: Optional[WakeWordConfig] = None) -> WakeWordService:
    """Get or create wake word service instance"""
    global wake_word_service
    if wake_word_service is None:
        if config is None:
            config = WakeWordConfig(model=WakeWordModel.HEY_ROADTRIP)
        wake_word_service = WakeWordService(config)
    return wake_word_service