"""
Binaural audio processing for 3D spatial audio.
Handles HRTF calculations and spatial positioning.
"""

import math
import numpy as np
from typing import Dict, Tuple, Optional
from scipy import signal
from scipy.spatial.transform import Rotation

from backend.app.core.logger import logger


class BinauralProcessor:
    """Processes audio for binaural 3D spatial positioning."""
    
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.speed_of_sound = 343  # m/s at 20°C
        self.head_radius = 0.0875  # Average human head radius in meters
        
        # HRTF (Head-Related Transfer Function) parameters
        self.hrtf_params = {
            "itd_max": 0.00074,  # Max interaural time difference in seconds
            "ild_max": 20,  # Max interaural level difference in dB
        }
    
    def calculate_itd(self, azimuth: float, elevation: float = 0) -> float:
        """
        Calculate Interaural Time Difference based on sound source position.
        
        Args:
            azimuth: Horizontal angle in degrees (-180 to 180)
            elevation: Vertical angle in degrees (-90 to 90)
            
        Returns:
            ITD in seconds
        """
        # Convert to radians
        azimuth_rad = math.radians(azimuth)
        elevation_rad = math.radians(elevation)
        
        # Woodworth formula for ITD
        if abs(azimuth) < 90:
            # Sound source in front hemisphere
            itd = (self.head_radius / self.speed_of_sound) * (
                azimuth_rad + math.sin(azimuth_rad)
            ) * math.cos(elevation_rad)
        else:
            # Sound source in rear hemisphere
            itd = (self.head_radius / self.speed_of_sound) * (
                math.pi - abs(azimuth_rad) + math.sin(math.pi - abs(azimuth_rad))
            ) * math.cos(elevation_rad)
            itd = -itd if azimuth < 0 else itd
        
        return np.clip(itd, -self.hrtf_params["itd_max"], self.hrtf_params["itd_max"])
    
    def calculate_ild(self, azimuth: float, elevation: float = 0, frequency: float = 1000) -> float:
        """
        Calculate Interaural Level Difference based on sound source position.
        
        Args:
            azimuth: Horizontal angle in degrees
            elevation: Vertical angle in degrees
            frequency: Sound frequency in Hz
            
        Returns:
            ILD in dB
        """
        # Simplified ILD model based on spherical head
        azimuth_rad = math.radians(azimuth)
        elevation_rad = math.radians(elevation)
        
        # Frequency-dependent ILD
        freq_factor = min(frequency / 1000, 2.0)  # Normalize to 1kHz
        
        # ILD increases with azimuth and frequency
        ild = self.hrtf_params["ild_max"] * math.sin(azimuth_rad) * math.cos(elevation_rad) * freq_factor
        
        return np.clip(ild, -self.hrtf_params["ild_max"], self.hrtf_params["ild_max"])
    
    def apply_hrtf(
        self,
        audio_data: np.ndarray,
        azimuth: float,
        elevation: float = 0,
        distance: float = 1.0
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Apply Head-Related Transfer Function to create binaural audio.
        
        Args:
            audio_data: Mono audio signal
            azimuth: Horizontal angle in degrees
            elevation: Vertical angle in degrees
            distance: Distance in meters
            
        Returns:
            Tuple of (left_channel, right_channel)
        """
        # Calculate ITD and ILD
        itd = self.calculate_itd(azimuth, elevation)
        ild = self.calculate_ild(azimuth, elevation)
        
        # Convert ITD to samples
        itd_samples = int(abs(itd) * self.sample_rate)
        
        # Apply distance attenuation (inverse square law)
        distance_gain = 1.0 / max(distance, 0.1)
        audio_data = audio_data * distance_gain
        
        # Create stereo channels
        if azimuth >= 0:  # Sound source on the right
            # Right ear receives sound first
            right_channel = audio_data
            left_channel = np.pad(audio_data, (itd_samples, 0), mode='constant')[:-itd_samples]
            
            # Apply ILD (right ear louder)
            left_gain = 10 ** (-abs(ild) / 20)
            left_channel *= left_gain
        else:  # Sound source on the left
            # Left ear receives sound first
            left_channel = audio_data
            right_channel = np.pad(audio_data, (itd_samples, 0), mode='constant')[:-itd_samples]
            
            # Apply ILD (left ear louder)
            right_gain = 10 ** (-abs(ild) / 20)
            right_channel *= right_gain
        
        # Apply elevation filtering (simplified)
        if abs(elevation) > 30:
            # High-frequency attenuation for elevated sources
            cutoff_freq = 8000 - abs(elevation) * 50
            left_channel = self._apply_lowpass(left_channel, cutoff_freq)
            right_channel = self._apply_lowpass(right_channel, cutoff_freq)
        
        return left_channel, right_channel
    
    def _apply_lowpass(self, audio: np.ndarray, cutoff_freq: float) -> np.ndarray:
        """Apply lowpass filter to audio signal."""
        nyquist = self.sample_rate / 2
        normalized_cutoff = cutoff_freq / nyquist
        
        # Design Butterworth filter
        b, a = signal.butter(4, normalized_cutoff, btype='low')
        
        # Apply filter
        return signal.filtfilt(b, a, audio)
    
    def create_moving_source(
        self,
        audio_data: np.ndarray,
        trajectory: Dict[str, np.ndarray],
        listener_position: Optional[Tuple[float, float, float]] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create binaural audio for a moving sound source.
        
        Args:
            audio_data: Mono audio signal
            trajectory: Dict with 'positions' and 'timestamps' arrays
            listener_position: Optional listener position (x, y, z)
            
        Returns:
            Tuple of (left_channel, right_channel)
        """
        if listener_position is None:
            listener_position = (0, 0, 0)
        
        positions = trajectory['positions']
        timestamps = trajectory['timestamps']
        
        # Calculate samples per position
        total_samples = len(audio_data)
        samples_per_segment = total_samples // len(positions)
        
        left_output = np.zeros(total_samples)
        right_output = np.zeros(total_samples)
        
        for i, pos in enumerate(positions):
            # Calculate relative position
            rel_x = pos[0] - listener_position[0]
            rel_y = pos[1] - listener_position[1]
            rel_z = pos[2] - listener_position[2]
            
            # Convert to spherical coordinates
            distance = np.sqrt(rel_x**2 + rel_y**2 + rel_z**2)
            azimuth = np.degrees(np.arctan2(rel_y, rel_x))
            elevation = np.degrees(np.arcsin(rel_z / max(distance, 0.001)))
            
            # Extract audio segment
            start_idx = i * samples_per_segment
            end_idx = min((i + 1) * samples_per_segment, total_samples)
            segment = audio_data[start_idx:end_idx]
            
            # Apply HRTF
            left_seg, right_seg = self.apply_hrtf(segment, azimuth, elevation, distance)
            
            # Add to output with crossfade
            if i > 0:
                # Simple linear crossfade
                fade_samples = min(int(0.01 * self.sample_rate), len(left_seg) // 4)
                fade_in = np.linspace(0, 1, fade_samples)
                fade_out = np.linspace(1, 0, fade_samples)
                
                left_seg[:fade_samples] *= fade_in
                right_seg[:fade_samples] *= fade_in
                
                if start_idx >= fade_samples:
                    left_output[start_idx-fade_samples:start_idx] *= fade_out
                    right_output[start_idx-fade_samples:start_idx] *= fade_out
            
            # Add to output
            seg_len = len(left_seg)
            left_output[start_idx:start_idx+seg_len] += left_seg
            right_output[start_idx:start_idx+seg_len] += right_seg
        
        return left_output, right_output
    
    def add_room_acoustics(
        self,
        left_channel: np.ndarray,
        right_channel: np.ndarray,
        room_size: str = "medium",
        reverb_amount: float = 0.3
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Add room acoustics and reverb to binaural audio.
        
        Args:
            left_channel: Left audio channel
            right_channel: Right audio channel
            room_size: "small", "medium", "large", or "cathedral"
            reverb_amount: Amount of reverb (0-1)
            
        Returns:
            Tuple of processed (left_channel, right_channel)
        """
        # Room impulse response parameters
        room_params = {
            "small": {"delay": 0.01, "decay": 0.3, "diffusion": 0.5},
            "medium": {"delay": 0.03, "decay": 0.5, "diffusion": 0.7},
            "large": {"delay": 0.05, "decay": 0.7, "diffusion": 0.8},
            "cathedral": {"delay": 0.08, "decay": 0.9, "diffusion": 0.95}
        }
        
        params = room_params.get(room_size, room_params["medium"])
        
        # Simple reverb using comb filters
        reverb_left = self._apply_reverb(left_channel, **params)
        reverb_right = self._apply_reverb(right_channel, **params)
        
        # Mix dry and wet signals
        left_output = (1 - reverb_amount) * left_channel + reverb_amount * reverb_left
        right_output = (1 - reverb_amount) * right_channel + reverb_amount * reverb_right
        
        return left_output, right_output
    
    def _apply_reverb(
        self,
        audio: np.ndarray,
        delay: float,
        decay: float,
        diffusion: float
    ) -> np.ndarray:
        """Apply simple reverb effect using comb filters."""
        # Convert parameters to samples
        delay_samples = int(delay * self.sample_rate)
        
        # Create multiple comb filters with different delays
        delays = [delay_samples, int(delay_samples * 1.5), int(delay_samples * 2.1)]
        gains = [decay * 0.7, decay * 0.5, decay * 0.3]
        
        output = np.zeros_like(audio)
        
        for d, g in zip(delays, gains):
            # Simple feedback comb filter
            delayed = np.zeros(len(audio) + d)
            delayed[d:] = audio * g
            
            # Add diffusion through allpass filter
            if diffusion > 0:
                delayed = self._allpass_filter(delayed, diffusion)
            
            output += delayed[:len(audio)]
        
        return output
    
    def _allpass_filter(self, audio: np.ndarray, diffusion: float) -> np.ndarray:
        """Apply allpass filter for diffusion."""
        # Simple allpass filter implementation
        delay_samples = int(0.005 * self.sample_rate)  # 5ms delay
        gain = diffusion * 0.7
        
        output = np.zeros_like(audio)
        delayed = np.zeros(delay_samples)
        
        for i in range(len(audio)):
            delayed_sample = delayed[0] if delay_samples > 0 else 0
            output[i] = -audio[i] + delayed_sample
            
            # Update delay line
            if delay_samples > 0:
                delayed = np.roll(delayed, -1)
                delayed[-1] = audio[i] + gain * delayed_sample
        
        return output