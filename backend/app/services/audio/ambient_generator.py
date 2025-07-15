"""
Ambient soundscape generator for environmental audio.
Creates layered, context-aware ambient sounds.
"""

import random
from typing import Dict, List, Optional, Any
from datetime import datetime
import numpy as np

from backend.app.services.audio.sound_library import SoundLibrary
from backend.app.core.logger import logger


class AmbientGenerator:
    """Generates ambient soundscapes based on environment and context."""
    
    def __init__(self, sound_library: SoundLibrary):
        self.sound_library = sound_library
        self.current_layers = {}
        self.transition_duration = 3.0  # seconds
    
    async def generate_soundscape(
        self,
        environment: str,
        weather: Optional[str] = None,
        time_of_day: Optional[str] = None,
        activity_level: float = 0.5,
        special_events: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate a multi-layered ambient soundscape.
        
        Args:
            environment: Primary environment type
            weather: Current weather conditions
            time_of_day: Current time period
            activity_level: Activity intensity (0-1)
            special_events: List of special events to include
            
        Returns:
            Soundscape configuration with layers and parameters
        """
        layers = []
        
        # Base environment layer
        env_sounds = self.sound_library.get_environment_sounds(environment)
        if env_sounds:
            # Select sounds based on activity level
            num_sounds = max(1, int(len(env_sounds) * activity_level))
            selected_sounds = random.sample(env_sounds, min(num_sounds, len(env_sounds)))
            
            for sound in selected_sounds:
                layers.append({
                    "sound": sound,
                    "volume": 0.6 + (random.random() * 0.2),
                    "loop": True,
                    "fade_in": 2.0,
                    "position": self._generate_sound_position(sound),
                    "layer_type": "environment"
                })
        
        # Weather layer
        if weather:
            weather_sounds = self.sound_library.get_weather_sounds(weather)
            for sound in weather_sounds[:2]:  # Limit weather sounds
                layers.append({
                    "sound": sound,
                    "volume": 0.4 + (random.random() * 0.3),
                    "loop": True,
                    "fade_in": 3.0,
                    "position": {"azimuth": 0, "elevation": 45, "distance": 10},
                    "layer_type": "weather"
                })
        
        # Time of day layer
        if time_of_day:
            time_sounds = self.sound_library.get_time_sounds(time_of_day)
            for sound in time_sounds[:2]:
                layers.append({
                    "sound": sound,
                    "volume": 0.3 + (random.random() * 0.2),
                    "loop": True,
                    "fade_in": 2.5,
                    "position": self._generate_sound_position(sound),
                    "layer_type": "time"
                })
        
        # Special events
        if special_events:
            for event in special_events:
                effect_sounds = self.sound_library.get_special_effect(event)
                if effect_sounds:
                    layers.append({
                        "sound": effect_sounds[0],
                        "volume": 0.7,
                        "loop": False,
                        "fade_in": 0.5,
                        "position": {"azimuth": 0, "elevation": 0, "distance": 2},
                        "layer_type": "event"
                    })
        
        # Calculate overall mix parameters
        mix_params = self._calculate_mix_parameters(layers, environment, activity_level)
        
        return {
            "environment": environment,
            "layers": layers,
            "mix_params": mix_params,
            "total_layers": len(layers),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def generate_transition(
        self,
        from_env: str,
        to_env: str,
        duration: float = 5.0,
        weather_change: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Generate a smooth transition between environments.
        
        Args:
            from_env: Starting environment
            to_env: Target environment
            duration: Transition duration in seconds
            weather_change: Optional weather transition
            
        Returns:
            Transition configuration
        """
        # Get transition sounds if available
        transition_sounds = self.sound_library.get_transition_sounds(from_env, to_env)
        
        transition_layers = []
        
        # Fade out layers
        from_sounds = self.sound_library.get_environment_sounds(from_env)
        for sound in from_sounds[:3]:
            transition_layers.append({
                "sound": sound,
                "action": "fade_out",
                "duration": duration * 0.7,
                "start_volume": 0.6,
                "end_volume": 0.0
            })
        
        # Transition sounds
        for sound in transition_sounds:
            transition_layers.append({
                "sound": sound,
                "action": "crossfade",
                "duration": duration,
                "peak_time": duration * 0.5,
                "peak_volume": 0.5
            })
        
        # Fade in layers
        to_sounds = self.sound_library.get_environment_sounds(to_env)
        for sound in to_sounds[:3]:
            transition_layers.append({
                "sound": sound,
                "action": "fade_in",
                "duration": duration * 0.7,
                "start_time": duration * 0.3,
                "start_volume": 0.0,
                "end_volume": 0.6
            })
        
        # Weather transition if applicable
        if weather_change:
            from_weather = weather_change.get("from")
            to_weather = weather_change.get("to")
            
            if from_weather:
                weather_sounds = self.sound_library.get_weather_sounds(from_weather)
                for sound in weather_sounds[:1]:
                    transition_layers.append({
                        "sound": sound,
                        "action": "fade_out",
                        "duration": duration * 0.8,
                        "start_volume": 0.4,
                        "end_volume": 0.0
                    })
            
            if to_weather:
                weather_sounds = self.sound_library.get_weather_sounds(to_weather)
                for sound in weather_sounds[:1]:
                    transition_layers.append({
                        "sound": sound,
                        "action": "fade_in",
                        "duration": duration * 0.8,
                        "start_time": duration * 0.2,
                        "start_volume": 0.0,
                        "end_volume": 0.4
                    })
        
        return {
            "from_environment": from_env,
            "to_environment": to_env,
            "duration": duration,
            "layers": transition_layers,
            "weather_change": weather_change,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _generate_sound_position(self, sound_name: str) -> Dict[str, float]:
        """Generate spatial position for a sound based on its type."""
        # Position sounds naturally based on type
        if "bird" in sound_name or "wind" in sound_name:
            # Birds and wind from above
            return {
                "azimuth": random.uniform(-180, 180),
                "elevation": random.uniform(20, 60),
                "distance": random.uniform(5, 20)
            }
        elif "traffic" in sound_name or "car" in sound_name:
            # Traffic at ground level, various directions
            return {
                "azimuth": random.uniform(-90, 90),
                "elevation": random.uniform(-5, 5),
                "distance": random.uniform(10, 50)
            }
        elif "people" in sound_name or "conversation" in sound_name:
            # People nearby at ground level
            return {
                "azimuth": random.uniform(-120, 120),
                "elevation": random.uniform(-10, 10),
                "distance": random.uniform(2, 10)
            }
        else:
            # Default random position
            return {
                "azimuth": random.uniform(-180, 180),
                "elevation": random.uniform(-30, 30),
                "distance": random.uniform(5, 30)
            }
    
    def _calculate_mix_parameters(
        self,
        layers: List[Dict[str, Any]],
        environment: str,
        activity_level: float
    ) -> Dict[str, Any]:
        """Calculate overall mix parameters for the soundscape."""
        # Base parameters on environment type
        env_params = {
            "forest": {"reverb": 0.4, "eq_profile": "natural", "compression": 0.2},
            "city": {"reverb": 0.2, "eq_profile": "urban", "compression": 0.4},
            "beach": {"reverb": 0.1, "eq_profile": "open", "compression": 0.1},
            "mountain": {"reverb": 0.6, "eq_profile": "distant", "compression": 0.1},
            "indoor": {"reverb": 0.3, "eq_profile": "warm", "compression": 0.3}
        }
        
        base_params = env_params.get(environment, env_params["city"])
        
        # Adjust based on activity level
        base_params["overall_volume"] = 0.3 + (activity_level * 0.4)
        base_params["dynamics_range"] = 0.6 - (activity_level * 0.2)
        
        # EQ settings based on environment
        eq_profiles = {
            "natural": {"low": 0.0, "mid": 0.2, "high": -0.1},
            "urban": {"low": 0.2, "mid": 0.0, "high": 0.1},
            "open": {"low": -0.2, "mid": 0.0, "high": 0.3},
            "distant": {"low": -0.3, "mid": -0.1, "high": -0.4},
            "warm": {"low": 0.3, "mid": 0.1, "high": -0.2}
        }
        
        base_params["eq"] = eq_profiles.get(base_params["eq_profile"], eq_profiles["natural"])
        
        # Layer balancing
        layer_counts = {}
        for layer in layers:
            layer_type = layer.get("layer_type", "unknown")
            layer_counts[layer_type] = layer_counts.get(layer_type, 0) + 1
        
        base_params["layer_balance"] = layer_counts
        
        return base_params
    
    async def create_adaptive_soundscape(
        self,
        base_environment: str,
        duration: float,
        variation_points: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create an adaptive soundscape that changes over time.
        
        Args:
            base_environment: Primary environment
            duration: Total duration in seconds
            variation_points: List of time-based variations
            
        Returns:
            Adaptive soundscape configuration
        """
        timeline = []
        current_time = 0.0
        
        # Start with base soundscape
        base_soundscape = await self.generate_soundscape(base_environment)
        timeline.append({
            "time": 0.0,
            "soundscape": base_soundscape,
            "action": "start"
        })
        
        # Process variation points
        for point in sorted(variation_points, key=lambda x: x.get("time", 0)):
            point_time = point.get("time", current_time)
            
            if point_time > duration:
                break
            
            action = point.get("action")
            
            if action == "change_weather":
                new_soundscape = await self.generate_soundscape(
                    base_environment,
                    weather=point.get("weather"),
                    activity_level=point.get("activity_level", 0.5)
                )
                timeline.append({
                    "time": point_time,
                    "soundscape": new_soundscape,
                    "action": "crossfade",
                    "duration": point.get("duration", 3.0)
                })
            
            elif action == "add_event":
                timeline.append({
                    "time": point_time,
                    "event": point.get("event"),
                    "action": "add_layer",
                    "duration": point.get("duration", 1.0)
                })
            
            elif action == "change_activity":
                new_soundscape = await self.generate_soundscape(
                    base_environment,
                    activity_level=point.get("activity_level", 0.5)
                )
                timeline.append({
                    "time": point_time,
                    "soundscape": new_soundscape,
                    "action": "adjust_mix",
                    "duration": point.get("duration", 2.0)
                })
            
            current_time = point_time
        
        return {
            "base_environment": base_environment,
            "duration": duration,
            "timeline": timeline,
            "variation_count": len(variation_points),
            "timestamp": datetime.utcnow().isoformat()
        }