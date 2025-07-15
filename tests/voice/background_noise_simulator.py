"""
Background Noise Simulation for Voice Testing
Simulates various driving conditions and noise environments
"""
import numpy as np
import random
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import scipy.signal as signal
import json


class NoiseType(Enum):
    WHITE = "white_noise"
    PINK = "pink_noise"
    BROWN = "brown_noise"
    TRAFFIC = "traffic"
    WIND = "wind"
    RAIN = "rain"
    ENGINE = "engine"
    MUSIC = "music"
    CONVERSATION = "conversation"
    EMERGENCY = "emergency_siren"


@dataclass
class NoiseProfile:
    """Defines a noise profile for testing"""
    name: str
    base_db: float
    noise_types: List[Tuple[NoiseType, float]]  # (type, weight)
    frequency_range: Tuple[int, int]  # Hz
    variability: float  # 0-1, how much the noise varies
    burst_probability: float  # Probability of sudden loud noises


class DrivingCondition(Enum):
    """Different driving conditions that affect noise"""
    CITY_QUIET = "city_quiet"
    CITY_BUSY = "city_busy"
    HIGHWAY_SMOOTH = "highway_smooth"
    HIGHWAY_ROUGH = "highway_rough"
    SUBURBAN = "suburban"
    RURAL = "rural"
    PARKING = "parking"
    TRAFFIC_JAM = "traffic_jam"
    RAIN_LIGHT = "rain_light"
    RAIN_HEAVY = "rain_heavy"
    WINDOWS_DOWN = "windows_down"
    EMERGENCY = "emergency_situation"


class BackgroundNoiseSimulator:
    """Simulates various background noise conditions for voice testing"""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.noise_profiles = self._create_noise_profiles()
        self.condition_profiles = self._create_driving_conditions()
    
    def _create_noise_profiles(self) -> Dict[str, NoiseProfile]:
        """Create standard noise profiles"""
        return {
            "quiet_car": NoiseProfile(
                name="Quiet Car",
                base_db=30,
                noise_types=[(NoiseType.ENGINE, 0.7), (NoiseType.WHITE, 0.3)],
                frequency_range=(100, 1000),
                variability=0.1,
                burst_probability=0.01
            ),
            "highway_cruise": NoiseProfile(
                name="Highway Cruise",
                base_db=55,
                noise_types=[
                    (NoiseType.ENGINE, 0.4),
                    (NoiseType.WIND, 0.4),
                    (NoiseType.TRAFFIC, 0.2)
                ],
                frequency_range=(100, 3000),
                variability=0.3,
                burst_probability=0.05
            ),
            "city_traffic": NoiseProfile(
                name="City Traffic",
                base_db=65,
                noise_types=[
                    (NoiseType.TRAFFIC, 0.5),
                    (NoiseType.ENGINE, 0.3),
                    (NoiseType.WHITE, 0.2)
                ],
                frequency_range=(200, 4000),
                variability=0.5,
                burst_probability=0.1
            ),
            "windows_down": NoiseProfile(
                name="Windows Down",
                base_db=75,
                noise_types=[
                    (NoiseType.WIND, 0.6),
                    (NoiseType.ENGINE, 0.2),
                    (NoiseType.TRAFFIC, 0.2)
                ],
                frequency_range=(100, 5000),
                variability=0.7,
                burst_probability=0.15
            ),
            "rain_driving": NoiseProfile(
                name="Rain Driving",
                base_db=70,
                noise_types=[
                    (NoiseType.RAIN, 0.5),
                    (NoiseType.ENGINE, 0.3),
                    (NoiseType.WIND, 0.2)
                ],
                frequency_range=(500, 6000),
                variability=0.4,
                burst_probability=0.08
            ),
            "music_playing": NoiseProfile(
                name="Music Playing",
                base_db=60,
                noise_types=[
                    (NoiseType.MUSIC, 0.6),
                    (NoiseType.ENGINE, 0.3),
                    (NoiseType.WHITE, 0.1)
                ],
                frequency_range=(100, 8000),
                variability=0.6,
                burst_probability=0.02
            ),
            "family_car": NoiseProfile(
                name="Family Car",
                base_db=68,
                noise_types=[
                    (NoiseType.CONVERSATION, 0.4),
                    (NoiseType.ENGINE, 0.3),
                    (NoiseType.MUSIC, 0.2),
                    (NoiseType.WHITE, 0.1)
                ],
                frequency_range=(200, 5000),
                variability=0.8,
                burst_probability=0.2
            ),
            "emergency": NoiseProfile(
                name="Emergency Situation",
                base_db=85,
                noise_types=[
                    (NoiseType.EMERGENCY, 0.4),
                    (NoiseType.TRAFFIC, 0.3),
                    (NoiseType.ENGINE, 0.3)
                ],
                frequency_range=(200, 8000),
                variability=0.9,
                burst_probability=0.3
            )
        }
    
    def _create_driving_conditions(self) -> Dict[DrivingCondition, str]:
        """Map driving conditions to noise profiles"""
        return {
            DrivingCondition.CITY_QUIET: "quiet_car",
            DrivingCondition.CITY_BUSY: "city_traffic",
            DrivingCondition.HIGHWAY_SMOOTH: "highway_cruise",
            DrivingCondition.HIGHWAY_ROUGH: "highway_cruise",
            DrivingCondition.SUBURBAN: "quiet_car",
            DrivingCondition.RURAL: "quiet_car",
            DrivingCondition.PARKING: "quiet_car",
            DrivingCondition.TRAFFIC_JAM: "city_traffic",
            DrivingCondition.RAIN_LIGHT: "rain_driving",
            DrivingCondition.RAIN_HEAVY: "rain_driving",
            DrivingCondition.WINDOWS_DOWN: "windows_down",
            DrivingCondition.EMERGENCY: "emergency"
        }
    
    def generate_noise(self, noise_type: NoiseType, duration: float, 
                      amplitude: float = 1.0) -> np.ndarray:
        """Generate specific type of noise"""
        samples = int(duration * self.sample_rate)
        
        if noise_type == NoiseType.WHITE:
            return np.random.normal(0, amplitude, samples)
        
        elif noise_type == NoiseType.PINK:
            # Pink noise has 1/f power spectral density
            white = np.random.normal(0, 1, samples)
            # Simple pink noise approximation
            b, a = signal.butter(1, 0.1)
            pink = signal.filtfilt(b, a, white)
            return pink * amplitude
        
        elif noise_type == NoiseType.BROWN:
            # Brown noise has 1/f^2 power spectral density
            white = np.random.normal(0, 1, samples)
            brown = np.cumsum(white) / np.sqrt(samples)
            return brown * amplitude
        
        elif noise_type == NoiseType.ENGINE:
            # Engine noise - low frequency rumble
            fundamental = 50  # Hz
            harmonics = [1, 2, 3, 4]
            engine = np.zeros(samples)
            t = np.linspace(0, duration, samples)
            for h in harmonics:
                engine += np.sin(2 * np.pi * fundamental * h * t) / h
            # Add some randomness
            engine += np.random.normal(0, 0.1, samples)
            return engine * amplitude
        
        elif noise_type == NoiseType.WIND:
            # Wind noise - filtered white noise
            white = np.random.normal(0, 1, samples)
            # Bandpass filter for wind-like sound
            b, a = signal.butter(4, [0.1, 0.5], btype='band')
            wind = signal.filtfilt(b, a, white)
            # Add gusts
            gusts = np.random.random(samples) > 0.95
            wind[gusts] *= 2
            return wind * amplitude
        
        elif noise_type == NoiseType.RAIN:
            # Rain noise - high frequency patter
            rain = np.random.normal(0, 1, samples)
            # High-pass filter
            b, a = signal.butter(4, 0.5, btype='high')
            rain = signal.filtfilt(b, a, rain)
            # Add random drops
            drops = np.random.random(samples) > 0.99
            rain[drops] *= 3
            return rain * amplitude
        
        elif noise_type == NoiseType.TRAFFIC:
            # Traffic noise - mix of engine and random events
            traffic = self.generate_noise(NoiseType.ENGINE, duration, 0.5)
            # Add random vehicle passes
            for _ in range(int(duration * 2)):  # ~2 vehicles per second
                start = random.randint(0, samples - self.sample_rate)
                duration_samples = random.randint(self.sample_rate // 2, self.sample_rate * 2)
                end = min(start + duration_samples, samples)
                # Doppler-like effect
                t = np.linspace(0, 1, end - start)
                doppler = np.sin(2 * np.pi * 200 * t * (1 + 0.2 * t))
                traffic[start:end] += doppler * 0.3
            return traffic * amplitude
        
        elif noise_type == NoiseType.MUSIC:
            # Simplified music - mix of frequencies
            music = np.zeros(samples)
            t = np.linspace(0, duration, samples)
            # Bass line
            music += 0.3 * np.sin(2 * np.pi * 100 * t)
            # Mid frequencies
            music += 0.2 * np.sin(2 * np.pi * 440 * t)
            music += 0.2 * np.sin(2 * np.pi * 554 * t)
            # Beat pattern
            beat = (t * 2 % 1) < 0.1
            music[beat] *= 1.5
            return music * amplitude
        
        elif noise_type == NoiseType.CONVERSATION:
            # Simulated conversation - modulated noise
            conversation = np.random.normal(0, 1, samples)
            # Bandpass for voice frequencies
            b, a = signal.butter(4, [0.05, 0.3], btype='band')
            conversation = signal.filtfilt(b, a, conversation)
            # Add pauses
            t = np.linspace(0, duration, samples)
            modulation = np.sin(2 * np.pi * 0.5 * t) > 0
            conversation *= modulation
            return conversation * amplitude
        
        elif noise_type == NoiseType.EMERGENCY:
            # Emergency siren
            t = np.linspace(0, duration, samples)
            # Two-tone siren
            freq1, freq2 = 700, 1000
            siren = np.zeros(samples)
            switch = (t * 2 % 1) < 0.5
            siren[switch] = np.sin(2 * np.pi * freq1 * t[switch])
            siren[~switch] = np.sin(2 * np.pi * freq2 * t[~switch])
            return siren * amplitude
        
        else:
            # Default to white noise
            return np.random.normal(0, amplitude, samples)
    
    def mix_noise_profile(self, profile: NoiseProfile, duration: float) -> np.ndarray:
        """Mix multiple noise types according to profile"""
        samples = int(duration * self.sample_rate)
        mixed = np.zeros(samples)
        
        for noise_type, weight in profile.noise_types:
            noise = self.generate_noise(noise_type, duration, weight)
            mixed += noise
        
        # Apply frequency filtering
        nyquist = self.sample_rate // 2
        low_freq = profile.frequency_range[0] / nyquist
        high_freq = min(profile.frequency_range[1] / nyquist, 0.99)
        
        if high_freq > low_freq:
            b, a = signal.butter(4, [low_freq, high_freq], btype='band')
            mixed = signal.filtfilt(b, a, mixed)
        
        # Add variability
        if profile.variability > 0:
            envelope = 1 + profile.variability * np.random.normal(0, 1, samples)
            envelope = np.clip(envelope, 0.5, 1.5)
            # Smooth the envelope
            b, a = signal.butter(2, 0.01)
            envelope = signal.filtfilt(b, a, envelope)
            mixed *= envelope
        
        # Add random bursts
        if profile.burst_probability > 0:
            bursts = np.random.random(samples) < profile.burst_probability / self.sample_rate
            mixed[bursts] *= random.uniform(1.5, 3)
        
        # Convert to dB scale
        target_amplitude = 10 ** (profile.base_db / 20)
        mixed = mixed / (np.max(np.abs(mixed)) + 1e-8) * target_amplitude
        
        return mixed
    
    def simulate_driving_condition(self, condition: DrivingCondition, 
                                 duration: float) -> np.ndarray:
        """Simulate noise for a specific driving condition"""
        profile_name = self.condition_profiles[condition]
        profile = self.noise_profiles[profile_name]
        
        # Adjust profile based on specific condition
        if condition == DrivingCondition.HIGHWAY_ROUGH:
            profile.base_db += 5
            profile.variability *= 1.5
        elif condition == DrivingCondition.RAIN_HEAVY:
            profile.base_db += 10
            profile.burst_probability *= 2
        
        return self.mix_noise_profile(profile, duration)
    
    def add_noise_to_audio(self, clean_audio: np.ndarray, 
                          noise_profile: str, 
                          snr_db: float = 10) -> np.ndarray:
        """Add noise to clean audio with specified SNR"""
        if noise_profile not in self.noise_profiles:
            raise ValueError(f"Unknown noise profile: {noise_profile}")
        
        profile = self.noise_profiles[noise_profile]
        duration = len(clean_audio) / self.sample_rate
        noise = self.mix_noise_profile(profile, duration)
        
        # Ensure same length
        noise = noise[:len(clean_audio)]
        
        # Calculate scaling for desired SNR
        signal_power = np.mean(clean_audio ** 2)
        noise_power = np.mean(noise ** 2)
        
        if noise_power > 0:
            noise_scale = np.sqrt(signal_power / (10 ** (snr_db / 10) * noise_power))
            noise *= noise_scale
        
        # Mix signal and noise
        noisy_audio = clean_audio + noise
        
        # Prevent clipping
        max_val = np.max(np.abs(noisy_audio))
        if max_val > 1.0:
            noisy_audio /= max_val
        
        return noisy_audio
    
    def generate_test_scenarios(self) -> List[Dict[str, any]]:
        """Generate comprehensive test scenarios"""
        scenarios = []
        
        # Test all driving conditions
        for condition in DrivingCondition:
            for snr in [20, 10, 5, 0]:  # Different signal-to-noise ratios
                scenarios.append({
                    "id": f"{condition.value}_snr{snr}",
                    "condition": condition.value,
                    "snr_db": snr,
                    "expected_accuracy": self._estimate_accuracy(condition, snr)
                })
        
        # Special test cases
        special_cases = [
            {
                "id": "sudden_siren",
                "description": "Sudden emergency vehicle",
                "profile": "quiet_car",
                "event": "emergency_siren",
                "event_time": 2.0,
                "expected_behavior": "pause_and_resume"
            },
            {
                "id": "loud_music_burst",
                "description": "Sudden loud music",
                "profile": "music_playing",
                "event": "volume_spike",
                "event_time": 1.5,
                "expected_behavior": "adaptive_gain"
            },
            {
                "id": "multiple_speakers",
                "description": "Multiple people talking",
                "profile": "family_car",
                "event": "crosstalk",
                "expected_behavior": "focus_primary_speaker"
            }
        ]
        
        scenarios.extend(special_cases)
        return scenarios
    
    def _estimate_accuracy(self, condition: DrivingCondition, snr_db: float) -> float:
        """Estimate expected accuracy for condition and SNR"""
        # Base accuracy at 20dB SNR
        base_accuracy = {
            DrivingCondition.CITY_QUIET: 0.95,
            DrivingCondition.CITY_BUSY: 0.85,
            DrivingCondition.HIGHWAY_SMOOTH: 0.88,
            DrivingCondition.HIGHWAY_ROUGH: 0.80,
            DrivingCondition.SUBURBAN: 0.93,
            DrivingCondition.RURAL: 0.94,
            DrivingCondition.PARKING: 0.96,
            DrivingCondition.TRAFFIC_JAM: 0.82,
            DrivingCondition.RAIN_LIGHT: 0.85,
            DrivingCondition.RAIN_HEAVY: 0.75,
            DrivingCondition.WINDOWS_DOWN: 0.70,
            DrivingCondition.EMERGENCY: 0.65
        }
        
        accuracy = base_accuracy.get(condition, 0.85)
        
        # Adjust for SNR
        snr_penalty = max(0, (20 - snr_db) * 0.03)  # 3% per dB below 20
        accuracy -= snr_penalty
        
        return max(0.5, accuracy)


class NoiseTestReport:
    """Generate comprehensive noise testing report"""
    
    def __init__(self, test_results: List[Dict[str, any]]):
        self.results = test_results
    
    def generate_report(self) -> Dict[str, any]:
        """Generate detailed test report"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.get("passed", False))
        
        # Group by condition
        condition_stats = {}
        for result in self.results:
            condition = result.get("condition", "unknown")
            if condition not in condition_stats:
                condition_stats[condition] = {
                    "total": 0,
                    "passed": 0,
                    "avg_accuracy": [],
                    "snr_performance": {}
                }
            
            stats = condition_stats[condition]
            stats["total"] += 1
            if result.get("passed", False):
                stats["passed"] += 1
            stats["avg_accuracy"].append(result.get("accuracy", 0))
            
            snr = result.get("snr_db", "unknown")
            if snr not in stats["snr_performance"]:
                stats["snr_performance"][snr] = []
            stats["snr_performance"][snr].append(result.get("accuracy", 0))
        
        # Calculate averages
        for condition, stats in condition_stats.items():
            stats["avg_accuracy"] = np.mean(stats["avg_accuracy"]) if stats["avg_accuracy"] else 0
            stats["pass_rate"] = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
            
            for snr, accuracies in stats["snr_performance"].items():
                stats["snr_performance"][snr] = np.mean(accuracies) if accuracies else 0
        
        # Identify problem areas
        problem_conditions = [
            condition for condition, stats in condition_stats.items()
            if stats["pass_rate"] < 80
        ]
        
        return {
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": total_tests - passed_tests,
                "pass_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0
            },
            "condition_breakdown": condition_stats,
            "problem_areas": problem_conditions,
            "recommendations": self._generate_recommendations(condition_stats)
        }
    
    def _generate_recommendations(self, condition_stats: Dict[str, any]) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        for condition, stats in condition_stats.items():
            if stats["pass_rate"] < 70:
                recommendations.append(
                    f"Critical: {condition} has very low pass rate ({stats['pass_rate']:.1f}%). "
                    f"Consider specialized noise cancellation for this condition."
                )
            elif stats["pass_rate"] < 85:
                recommendations.append(
                    f"Warning: {condition} needs improvement ({stats['pass_rate']:.1f}% pass rate)."
                )
            
            # Check SNR performance
            for snr, accuracy in stats["snr_performance"].items():
                if isinstance(snr, int) and snr <= 5 and accuracy < 0.7:
                    recommendations.append(
                        f"Low SNR performance: {condition} at {snr}dB SNR "
                        f"has {accuracy*100:.1f}% accuracy. Consider adaptive filtering."
                    )
        
        if not recommendations:
            recommendations.append("All conditions meet acceptable performance standards.")
        
        return recommendations


# Example usage
if __name__ == "__main__":
    # Create simulator
    simulator = BackgroundNoiseSimulator()
    
    # Generate test scenarios
    scenarios = simulator.generate_test_scenarios()
    print(f"Generated {len(scenarios)} test scenarios")
    
    # Simulate some conditions
    print("\nSimulating driving conditions:")
    for condition in [DrivingCondition.CITY_QUIET, DrivingCondition.HIGHWAY_SMOOTH, 
                     DrivingCondition.RAIN_HEAVY]:
        noise = simulator.simulate_driving_condition(condition, duration=3.0)
        print(f"{condition.value}: Generated {len(noise)} samples, "
              f"RMS level: {np.sqrt(np.mean(noise**2)):.3f}")
    
    # Test noise profiles
    print("\nNoise profiles:")
    for name, profile in simulator.noise_profiles.items():
        print(f"{name}: {profile.base_db}dB, "
              f"frequency range: {profile.frequency_range[0]}-{profile.frequency_range[1]}Hz")