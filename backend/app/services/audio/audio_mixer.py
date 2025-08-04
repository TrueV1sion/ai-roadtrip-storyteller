"""
Audio mixing and processing engine.
Handles multi-track mixing, effects, and final audio rendering.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from scipy import signal
import asyncio

from app.core.logger import logger


class AudioMixer:
    """Handles mixing of multiple audio tracks with effects processing."""
    
    def __init__(self, sample_rate: int = 44100, channels: int = 2):
        self.sample_rate = sample_rate
        self.channels = channels
        self.master_volume = 0.8
        self.compressor_threshold = -20  # dB
        self.compressor_ratio = 4
    
    async def mix_tracks(
        self,
        tracks: List[Dict[str, Any]],
        duration: Optional[float] = None
    ) -> np.ndarray:
        """
        Mix multiple audio tracks into a single output.
        
        Args:
            tracks: List of track configurations with audio data and parameters
            duration: Optional output duration in seconds
            
        Returns:
            Mixed audio as numpy array
        """
        if not tracks:
            return np.zeros((int(self.sample_rate * (duration or 1)), self.channels))
        
        # Determine output length
        if duration:
            output_samples = int(duration * self.sample_rate)
        else:
            output_samples = max(len(track["audio"]) for track in tracks)
        
        # Initialize output buffer
        output = np.zeros((output_samples, self.channels))
        
        # Process each track
        for track in tracks:
            processed = await self._process_track(track, output_samples)
            output += processed
        
        # Apply master processing
        output = self._apply_master_chain(output)
        
        # Normalize to prevent clipping
        max_val = np.max(np.abs(output))
        if max_val > 0.95:
            output = output * (0.95 / max_val)
        
        return output
    
    async def _process_track(
        self,
        track: Dict[str, Any],
        output_length: int
    ) -> np.ndarray:
        """Process individual track with effects and positioning."""
        audio = track["audio"]
        
        # Ensure correct length
        if len(audio) < output_length:
            audio = np.pad(audio, (0, output_length - len(audio)), mode='constant')
        elif len(audio) > output_length:
            audio = audio[:output_length]
        
        # Apply volume
        volume = track.get("volume", 1.0)
        audio = audio * volume
        
        # Apply fade in/out
        fade_in = track.get("fade_in", 0)
        fade_out = track.get("fade_out", 0)
        
        if fade_in > 0:
            fade_samples = int(fade_in * self.sample_rate)
            fade_curve = np.linspace(0, 1, fade_samples)
            audio[:fade_samples] *= fade_curve
        
        if fade_out > 0:
            fade_samples = int(fade_out * self.sample_rate)
            fade_curve = np.linspace(1, 0, fade_samples)
            audio[-fade_samples:] *= fade_curve
        
        # Apply effects
        if track.get("reverb", 0) > 0:
            audio = self._apply_reverb(audio, track["reverb"])
        
        if track.get("delay", 0) > 0:
            audio = self._apply_delay(audio, track["delay"], track.get("delay_time", 0.5))
        
        if track.get("eq"):
            audio = self._apply_eq(audio, track["eq"])
        
        # Convert to stereo if needed
        if audio.ndim == 1:
            # Apply panning if specified
            pan = track.get("pan", 0)  # -1 to 1
            left_gain = np.sqrt((1 - pan) / 2)
            right_gain = np.sqrt((1 + pan) / 2)
            
            stereo = np.zeros((len(audio), 2))
            stereo[:, 0] = audio * left_gain
            stereo[:, 1] = audio * right_gain
            audio = stereo
        
        return audio
    
    def _apply_reverb(self, audio: np.ndarray, amount: float) -> np.ndarray:
        """Apply reverb effect to audio."""
        # Simple reverb using convolution with exponential decay
        reverb_time = 2.0  # seconds
        decay_samples = int(reverb_time * self.sample_rate)
        
        # Create impulse response
        impulse = np.random.randn(decay_samples) * 0.01
        decay = np.exp(-np.linspace(0, 4, decay_samples))
        impulse *= decay
        
        # Convolve with audio
        if audio.ndim == 1:
            wet = signal.convolve(audio, impulse, mode='same')
        else:
            wet = np.zeros_like(audio)
            for ch in range(audio.shape[1]):
                wet[:, ch] = signal.convolve(audio[:, ch], impulse, mode='same')
        
        # Mix wet and dry
        return (1 - amount) * audio + amount * wet * 0.3
    
    def _apply_delay(
        self,
        audio: np.ndarray,
        amount: float,
        delay_time: float
    ) -> np.ndarray:
        """Apply delay effect to audio."""
        delay_samples = int(delay_time * self.sample_rate)
        feedback = 0.4
        
        if audio.ndim == 1:
            # Mono delay
            output = np.copy(audio)
            delayed = np.zeros(len(audio) + delay_samples)
            delayed[delay_samples:] = audio
            
            # Add feedback
            for _ in range(3):
                delayed[delay_samples:] += delayed[:-delay_samples] * feedback
                feedback *= 0.7
            
            output += delayed[:len(audio)] * amount
        else:
            # Stereo ping-pong delay
            output = np.copy(audio)
            
            # Left channel delay
            delayed_l = np.zeros(len(audio) + delay_samples)
            delayed_l[delay_samples:] = audio[:, 0]
            
            # Right channel delay (different time)
            delay_samples_r = int(delay_time * self.sample_rate * 0.75)
            delayed_r = np.zeros(len(audio) + delay_samples_r)
            delayed_r[delay_samples_r:] = audio[:, 1]
            
            # Cross-feed delays
            output[:, 0] += delayed_r[:len(audio)] * amount * 0.7
            output[:, 1] += delayed_l[:len(audio)] * amount * 0.7
        
        return output
    
    def _apply_eq(self, audio: np.ndarray, eq_params: Dict[str, float]) -> np.ndarray:
        """Apply EQ to audio."""
        # Three-band EQ
        low_freq = 200
        mid_freq = 1000
        high_freq = 4000
        
        low_gain = eq_params.get("low", 0)
        mid_gain = eq_params.get("mid", 0)
        high_gain = eq_params.get("high", 0)
        
        # Design filters
        nyquist = self.sample_rate / 2
        
        # Low shelf
        if abs(low_gain) > 0.01:
            sos_low = signal.butter(2, low_freq / nyquist, 'low', output='sos')
            low_band = signal.sosfilt(sos_low, audio, axis=0)
            audio = audio + low_band * (10**(low_gain/20) - 1)
        
        # Mid peak
        if abs(mid_gain) > 0.01:
            sos_mid = signal.butter(
                2,
                [mid_freq * 0.7 / nyquist, mid_freq * 1.3 / nyquist],
                'band',
                output='sos'
            )
            mid_band = signal.sosfilt(sos_mid, audio, axis=0)
            audio = audio + mid_band * (10**(mid_gain/20) - 1)
        
        # High shelf
        if abs(high_gain) > 0.01:
            sos_high = signal.butter(2, high_freq / nyquist, 'high', output='sos')
            high_band = signal.sosfilt(sos_high, audio, axis=0)
            audio = audio + high_band * (10**(high_gain/20) - 1)
        
        return audio
    
    def _apply_master_chain(self, audio: np.ndarray) -> np.ndarray:
        """Apply master processing chain."""
        # Apply compression
        audio = self._apply_compression(audio)
        
        # Apply limiter
        audio = self._apply_limiter(audio)
        
        # Apply master volume
        audio *= self.master_volume
        
        return audio
    
    def _apply_compression(
        self,
        audio: np.ndarray,
        threshold: Optional[float] = None,
        ratio: Optional[float] = None
    ) -> np.ndarray:
        """Apply dynamic range compression."""
        if threshold is None:
            threshold = self.compressor_threshold
        if ratio is None:
            ratio = self.compressor_ratio
        
        # Convert to dB
        epsilon = 1e-10
        audio_db = 20 * np.log10(np.abs(audio) + epsilon)
        
        # Apply compression curve
        mask = audio_db > threshold
        compressed_db = np.where(
            mask,
            threshold + (audio_db - threshold) / ratio,
            audio_db
        )
        
        # Convert back to linear
        gain_db = compressed_db - audio_db
        gain_linear = 10 ** (gain_db / 20)
        
        # Apply makeup gain
        makeup_gain = 1.5
        
        return audio * gain_linear * makeup_gain
    
    def _apply_limiter(
        self,
        audio: np.ndarray,
        threshold: float = 0.95
    ) -> np.ndarray:
        """Apply brick-wall limiter to prevent clipping."""
        # Soft knee limiter
        knee_width = 0.1
        
        # Calculate gain reduction
        level = np.abs(audio)
        
        # Soft knee curve
        mask_hard = level > threshold
        mask_soft = (level > (threshold - knee_width)) & (level <= threshold)
        
        gain = np.ones_like(level)
        
        # Hard limiting
        gain[mask_hard] = threshold / level[mask_hard]
        
        # Soft knee
        if np.any(mask_soft):
            knee_factor = (level[mask_soft] - (threshold - knee_width)) / knee_width
            gain[mask_soft] = 1 - knee_factor * (1 - threshold / level[mask_soft])
        
        # Smooth gain changes
        gain = signal.medfilt(gain, kernel_size=5)
        
        return audio * gain
    
    async def create_crossfade(
        self,
        track_a: np.ndarray,
        track_b: np.ndarray,
        duration: float,
        curve: str = "linear"
    ) -> np.ndarray:
        """
        Create crossfade between two tracks.
        
        Args:
            track_a: First track (fading out)
            track_b: Second track (fading in)
            duration: Crossfade duration in seconds
            curve: Fade curve type ("linear", "exponential", "logarithmic")
            
        Returns:
            Crossfaded audio
        """
        fade_samples = int(duration * self.sample_rate)
        
        # Ensure tracks are long enough
        min_length = fade_samples
        if len(track_a) < min_length:
            track_a = np.pad(track_a, (0, min_length - len(track_a)), mode='constant')
        if len(track_b) < min_length:
            track_b = np.pad(track_b, (0, min_length - len(track_b)), mode='constant')
        
        # Generate fade curves
        if curve == "exponential":
            fade_out = np.exp(-np.linspace(0, 5, fade_samples))
            fade_in = 1 - fade_out
        elif curve == "logarithmic":
            fade_out = np.log10(np.linspace(10, 0.1, fade_samples) + 0.1) / np.log10(10.1)
            fade_in = 1 - fade_out
        else:  # linear
            fade_out = np.linspace(1, 0, fade_samples)
            fade_in = np.linspace(0, 1, fade_samples)
        
        # Apply fades
        output_length = max(len(track_a), len(track_b))
        output = np.zeros((output_length, self.channels))
        
        # Ensure correct shape
        if track_a.ndim == 1:
            track_a = track_a.reshape(-1, 1)
        if track_b.ndim == 1:
            track_b = track_b.reshape(-1, 1)
        
        # Apply crossfade
        if track_a.shape[1] == 1 and self.channels == 2:
            track_a = np.repeat(track_a, 2, axis=1)
        if track_b.shape[1] == 1 and self.channels == 2:
            track_b = np.repeat(track_b, 2, axis=1)
        
        # Fade out track A
        output[:len(track_a)] += track_a
        for ch in range(min(track_a.shape[1], self.channels)):
            output[:fade_samples, ch] *= fade_out
        
        # Fade in track B
        start_offset = max(0, len(track_a) - fade_samples)
        output[start_offset:start_offset + len(track_b)] += track_b
        for ch in range(min(track_b.shape[1], self.channels)):
            output[start_offset:start_offset + fade_samples, ch] *= fade_in
        
        return output