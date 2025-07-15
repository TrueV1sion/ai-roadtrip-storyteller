from typing import Any, Dict, List, Optional, Tuple
import json
import math
import random
import uuid
from datetime import datetime, timedelta
from collections import deque

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.database import get_db
from app.services.spatial_audio_engine import SpatialAudioEngine, get_spatial_audio_engine
from app.core.cache import get_cache

logger = get_logger(__name__)


class AudioSceneService:
    """
    Service for managing comprehensive audio scenes that adapt to journey context.
    
    This service handles:
    1. Location-based soundscapes with real-time adaptation
    2. Weather-responsive audio generation
    3. Time-of-day audio variations
    4. Smooth scene transitions during travel
    5. Journey-aware audio narrative enhancement
    """
    
    def __init__(self, db: Session, spatial_audio_engine: SpatialAudioEngine):
        """Initialize the audio scene service."""
        self.db = db
        self.spatial_engine = spatial_audio_engine
        self.cache = get_cache()
        self.scene_history = deque(maxlen=10)  # Keep last 10 scenes for smooth transitions
        self.current_scene = None
        self.transition_in_progress = False
        
        # Scene templates for different journey contexts
        self.scene_templates = {
            "highway": {
                "base_environment": "highway",
                "characteristics": {
                    "wind_factor": 0.8,
                    "detail_reduction": 0.6,
                    "engine_prominence": 0.7,
                    "music_preference": "energetic"
                }
            },
            "scenic_route": {
                "base_environment": "rural",
                "characteristics": {
                    "nature_emphasis": 0.9,
                    "detail_enhancement": 1.2,
                    "music_preference": "reflective",
                    "narrative_spacing": "relaxed"
                }
            },
            "urban_exploration": {
                "base_environment": "city",
                "characteristics": {
                    "urban_density": 0.8,
                    "cultural_sounds": 0.7,
                    "music_preference": "contemporary",
                    "poi_awareness": "high"
                }
            },
            "coastal_drive": {
                "base_environment": "beach",
                "characteristics": {
                    "ocean_prominence": 0.9,
                    "wind_variation": 0.7,
                    "music_preference": "atmospheric",
                    "seasonal_variation": "high"
                }
            },
            "mountain_pass": {
                "base_environment": "mountain",
                "characteristics": {
                    "elevation_effects": 0.8,
                    "echo_modeling": 0.6,
                    "music_preference": "adventurous",
                    "weather_sensitivity": "high"
                }
            },
            "night_drive": {
                "base_environment": "night",
                "characteristics": {
                    "ambient_reduction": 0.7,
                    "focus_enhancement": 0.8,
                    "music_preference": "calm",
                    "safety_alerts": "enhanced"
                }
            }
        }
    
    async def create_journey_scene(
        self,
        location: Dict[str, Any],
        weather: Dict[str, Any],
        journey_context: Dict[str, Any],
        user_preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a comprehensive audio scene for the current journey context.
        
        Args:
            location: Current location data (lat, lon, type, terrain)
            weather: Weather conditions
            journey_context: Journey information (speed, route type, duration)
            user_preferences: User's audio preferences
            
        Returns:
            Dictionary with complete audio scene configuration
        """
        try:
            # Determine scene template based on journey context
            route_type = journey_context.get("route_type", "highway")
            template = self.scene_templates.get(route_type, self.scene_templates["highway"])
            
            # Get current time data
            current_time = datetime.now()
            time_data = {
                "hour": current_time.hour,
                "season": self._get_season(current_time),
                "day_phase": self._get_day_phase(current_time.hour)
            }
            
            # Enhance location data with terrain and population info
            enhanced_location = {
                "type": location.get("type", template["base_environment"]),
                "terrain": location.get("terrain", "flat"),
                "population_density": location.get("population_density", "medium"),
                "elevation": location.get("elevation", 0),
                "nearby_features": location.get("nearby_features", [])
            }
            
            # Generate environmental audio base
            environmental_audio = await self.spatial_engine.generate_environmental_audio(
                location_data=enhanced_location,
                weather_data=weather,
                time_data=time_data,
                speed=journey_context.get("speed", 0)
            )
            
            # Apply template characteristics
            scene_layers = environmental_audio["scene_layers"]
            characteristics = template["characteristics"]
            
            # Adjust layers based on template
            for layer in scene_layers:
                if layer["category"] == "wind" and "wind_factor" in characteristics:
                    layer["volume"] *= characteristics["wind_factor"]
                elif layer["category"] == "biological" and "detail_reduction" in characteristics:
                    layer["volume"] *= (2 - characteristics["detail_reduction"])
                elif layer["category"] == "urban" and "urban_density" in characteristics:
                    layer["volume"] *= characteristics["urban_density"]
            
            # Add journey-specific elements
            if journey_context.get("approaching_poi"):
                # Add anticipation sounds for approaching points of interest
                scene_layers.append({
                    "sound": "anticipation_swell",
                    "category": "narrative",
                    "volume": 0.6,
                    "start_time": 0,
                    "duration": 10,
                    "spatial_spread": 0.8
                })
            
            # Weather-specific adaptations
            if weather.get("type") == "rain":
                # Enhance rain sounds based on intensity
                rain_intensity = weather.get("intensity", 0.5)
                scene_layers.append({
                    "sound": "windshield_wipers",
                    "category": "vehicle",
                    "volume": 0.4 * rain_intensity,
                    "loop": True,
                    "rhythm": 60 / (1 + rain_intensity * 2)  # Wiper speed
                })
            
            # Time-based adaptations
            if time_data["day_phase"] == "night":
                # Reduce overall ambient volume at night
                for layer in scene_layers:
                    if layer["category"] in ["ambient", "biological"]:
                        layer["volume"] *= 0.7
            
            # Create adaptive music layer
            music_mood = characteristics.get("music_preference", "adventurous")
            if user_preferences.get("enable_music", True):
                music_transitions = self._plan_music_transitions(
                    journey_context, location, music_mood
                )
                
                adaptive_music = await self.spatial_engine.create_adaptive_music_track(
                    base_mood=music_mood,
                    transition_points=music_transitions,
                    duration=300,  # 5 minutes chunks
                    intensity_curve=self._calculate_intensity_curve(journey_context)
                )
                
                scene_layers.append({
                    "sound": "adaptive_music",
                    "source": adaptive_music["id"],
                    "category": "music",
                    "volume": user_preferences.get("music_volume", 0.5),
                    "loop": False,
                    "spatial_spread": 0.9
                })
            
            # Generate binaural positioning for key sounds
            listener_position = {"x": 0, "y": 0, "z": 0}
            listener_orientation = {
                "yaw": journey_context.get("heading", 0),
                "pitch": 0,
                "roll": 0
            }
            
            # Position sounds spatially
            for i, layer in enumerate(scene_layers):
                if layer.get("random_positioning"):
                    # Randomly position nature sounds around the listener
                    angle = random.uniform(0, 2 * math.pi)
                    distance = random.uniform(5, 20)
                    sound_source = {
                        "position": {
                            "x": distance * math.cos(angle),
                            "y": distance * math.sin(angle),
                            "z": random.uniform(-2, 5)
                        },
                        "environment": "outdoor"
                    }
                    
                    binaural_params = await self.spatial_engine.generate_binaural_audio(
                        sound_source=sound_source,
                        listener_position=listener_position,
                        listener_orientation=listener_orientation
                    )
                    
                    layer["binaural"] = binaural_params
            
            # Create the complete scene
            scene_id = str(uuid.uuid4())
            scene = {
                "id": scene_id,
                "timestamp": datetime.utcnow().isoformat(),
                "location": enhanced_location,
                "weather": weather,
                "time": time_data,
                "journey_context": journey_context,
                "template": route_type,
                "layers": scene_layers,
                "duration": 300,  # 5 minute scenes
                "fade_in": 3.0,  # 3 second fade in
                "fade_out": 3.0,  # 3 second fade out
                "next_transition": self._predict_next_transition(journey_context)
            }
            
            # Cache the scene
            cache_key = f"audio_scene:{scene_id}"
            await self.cache.set(cache_key, json.dumps(scene), ttl=3600)
            
            # Update scene history
            self.scene_history.append(scene)
            self.current_scene = scene
            
            return scene
            
        except Exception as e:
            logger.error(f"Error creating journey scene: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create journey scene: {str(e)}"
            )
    
    async def transition_to_scene(
        self,
        new_scene: Dict[str, Any],
        transition_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Smoothly transition from current scene to a new scene.
        
        Args:
            new_scene: Target scene configuration
            transition_type: Optional transition type override
            
        Returns:
            Dictionary with transition instructions
        """
        try:
            if not self.current_scene:
                # No current scene, just start the new one
                return {
                    "type": "immediate",
                    "scene": new_scene,
                    "duration": 0
                }
            
            # Determine transition type if not specified
            if not transition_type:
                transition_type = self._determine_transition_type(
                    self.current_scene, new_scene
                )
            
            # Generate smooth transition
            transition = await self.spatial_engine.generate_smooth_transition(
                from_scene=self.current_scene,
                to_scene=new_scene,
                transition_duration=5.0,
                transition_type=transition_type
            )
            
            # Mark transition in progress
            self.transition_in_progress = True
            
            # Schedule transition completion
            transition["completion_callback"] = self._complete_transition
            transition["new_scene"] = new_scene
            
            return transition
            
        except Exception as e:
            logger.error(f"Error creating scene transition: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create scene transition: {str(e)}"
            )
    
    async def update_scene_parameters(
        self,
        scene_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update parameters of the current scene in real-time.
        
        Args:
            scene_id: Current scene ID
            updates: Parameters to update
            
        Returns:
            Updated scene configuration
        """
        try:
            if not self.current_scene or self.current_scene["id"] != scene_id:
                raise ValueError("Scene ID does not match current scene")
            
            # Apply updates to scene layers
            if "volume_adjustments" in updates:
                for adjustment in updates["volume_adjustments"]:
                    category = adjustment["category"]
                    factor = adjustment["factor"]
                    
                    for layer in self.current_scene["layers"]:
                        if layer["category"] == category:
                            layer["volume"] *= factor
            
            if "add_layers" in updates:
                for new_layer in updates["add_layers"]:
                    self.current_scene["layers"].append(new_layer)
            
            if "remove_categories" in updates:
                self.current_scene["layers"] = [
                    layer for layer in self.current_scene["layers"]
                    if layer["category"] not in updates["remove_categories"]
                ]
            
            # Update cache
            cache_key = f"audio_scene:{scene_id}"
            await self.cache.set(
                cache_key,
                json.dumps(self.current_scene),
                ttl=3600
            )
            
            return {
                "scene_id": scene_id,
                "updates_applied": updates,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error updating scene parameters: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update scene parameters: {str(e)}"
            )
    
    async def get_scene_analytics(self, scene_id: str) -> Dict[str, Any]:
        """
        Get analytics and performance metrics for a scene.
        
        Args:
            scene_id: Scene ID to analyze
            
        Returns:
            Dictionary with scene analytics
        """
        try:
            # Retrieve scene from cache
            cache_key = f"audio_scene:{scene_id}"
            cached_data = await self.cache.get(cache_key)
            
            if not cached_data:
                raise ValueError("Scene not found in cache")
            
            scene = json.loads(cached_data)
            
            # Analyze scene composition
            layer_analysis = {}
            total_layers = len(scene["layers"])
            
            for layer in scene["layers"]:
                category = layer["category"]
                if category not in layer_analysis:
                    layer_analysis[category] = {
                        "count": 0,
                        "total_volume": 0,
                        "spatial_coverage": 0
                    }
                
                layer_analysis[category]["count"] += 1
                layer_analysis[category]["total_volume"] += layer.get("volume", 0)
                layer_analysis[category]["spatial_coverage"] += layer.get("spatial_spread", 0)
            
            # Calculate averages
            for category, data in layer_analysis.items():
                count = data["count"]
                data["average_volume"] = data["total_volume"] / count
                data["average_spatial_coverage"] = data["spatial_coverage"] / count
            
            # Estimate cognitive load
            cognitive_load = self._estimate_cognitive_load(scene)
            
            # Check for potential issues
            issues = []
            if total_layers > 15:
                issues.append("High layer count may cause audio clutter")
            
            total_volume = sum(layer.get("volume", 0) for layer in scene["layers"])
            if total_volume > total_layers * 0.8:
                issues.append("Overall volume may be too high")
            
            return {
                "scene_id": scene_id,
                "total_layers": total_layers,
                "layer_analysis": layer_analysis,
                "cognitive_load": cognitive_load,
                "estimated_bandwidth": self._estimate_bandwidth(scene),
                "issues": issues,
                "recommendations": self._generate_recommendations(scene, layer_analysis)
            }
            
        except Exception as e:
            logger.error(f"Error getting scene analytics: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get scene analytics: {str(e)}"
            )
    
    def _get_season(self, date: datetime) -> str:
        """Determine season based on date."""
        month = date.month
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "fall"
    
    def _get_day_phase(self, hour: int) -> str:
        """Determine day phase based on hour."""
        if 5 <= hour < 9:
            return "dawn"
        elif 9 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 20:
            return "dusk"
        else:
            return "night"
    
    def _plan_music_transitions(
        self,
        journey_context: Dict[str, Any],
        location: Dict[str, Any],
        base_mood: str
    ) -> List[Dict[str, Any]]:
        """Plan music transitions based on journey progression."""
        transitions = []
        
        # Add transitions for upcoming POIs
        if "upcoming_pois" in journey_context:
            for i, poi in enumerate(journey_context["upcoming_pois"][:3]):
                eta_seconds = poi.get("eta_seconds", (i + 1) * 60)
                poi_type = poi.get("type", "landmark")
                
                mood_map = {
                    "historical": "reflective",
                    "natural": "natural",
                    "cultural": "cultural",
                    "scenic": "atmospheric"
                }
                
                transitions.append({
                    "time": eta_seconds,
                    "mood": mood_map.get(poi_type, base_mood),
                    "intensity": 0.8,
                    "description": f"Approaching {poi.get('name', 'point of interest')}",
                    "fade_in_duration": 5,
                    "section_duration": 30
                })
        
        # Add transitions for elevation changes
        if "elevation_profile" in journey_context:
            for change in journey_context["elevation_profile"]:
                if abs(change["gradient"]) > 0.05:  # Significant grade
                    transitions.append({
                        "time": change["time"],
                        "mood": "adventurous" if change["gradient"] > 0 else "reflective",
                        "intensity": min(1.0, 0.5 + abs(change["gradient"]) * 5),
                        "description": "Elevation change"
                    })
        
        return transitions
    
    def _calculate_intensity_curve(
        self,
        journey_context: Dict[str, Any]
    ) -> List[Tuple[float, float]]:
        """Calculate music intensity curve based on journey dynamics."""
        curve = [(0, 0.6)]  # Start at moderate intensity
        
        # Add intensity variations based on speed changes
        if "speed_profile" in journey_context:
            for point in journey_context["speed_profile"]:
                time = point["time"]
                speed = point["speed"]
                # Higher speed = higher intensity
                intensity = min(1.0, 0.4 + (speed / 100) * 0.6)
                curve.append((time, intensity))
        
        # Add intensity drops for scenic moments
        if "scenic_points" in journey_context:
            for scenic in journey_context["scenic_points"]:
                curve.append((scenic["time"] - 5, 0.7))
                curve.append((scenic["time"], 0.4))  # Drop for scenic view
                curve.append((scenic["time"] + 20, 0.6))  # Return to normal
        
        return curve
    
    def _predict_next_transition(
        self,
        journey_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Predict when the next scene transition will be needed."""
        # Default to 5 minutes
        next_transition = {
            "estimated_time": 300,
            "reason": "scheduled",
            "confidence": 0.8
        }
        
        # Check for upcoming environment changes
        if "route_segments" in journey_context:
            for segment in journey_context["route_segments"]:
                if segment["start_time"] > 0 and segment["environment_change"]:
                    next_transition = {
                        "estimated_time": segment["start_time"],
                        "reason": "environment_change",
                        "confidence": 0.9,
                        "new_environment": segment["environment"]
                    }
                    break
        
        # Check for weather changes
        if "weather_forecast" in journey_context:
            for forecast in journey_context["weather_forecast"]:
                if forecast["change_time"] > 0 and forecast["significant_change"]:
                    if forecast["change_time"] < next_transition["estimated_time"]:
                        next_transition = {
                            "estimated_time": forecast["change_time"],
                            "reason": "weather_change",
                            "confidence": 0.85,
                            "new_weather": forecast["conditions"]
                        }
        
        return next_transition
    
    def _complete_transition(self, new_scene: Dict[str, Any]):
        """Mark transition as complete and update current scene."""
        self.transition_in_progress = False
        self.current_scene = new_scene
        logger.info(f"Completed transition to scene {new_scene['id']}")
    
    def _determine_transition_type(
        self,
        from_scene: Dict[str, Any],
        to_scene: Dict[str, Any]
    ) -> str:
        """Determine the best transition type between scenes."""
        from_type = from_scene.get("location", {}).get("type", "unknown")
        to_type = to_scene.get("location", {}).get("type", "unknown")
        
        # Environmental transitions for location changes
        if from_type != to_type:
            return "environmental"
        
        # Musical transitions for mood changes
        from_mood = from_scene.get("template", "")
        to_mood = to_scene.get("template", "")
        if from_mood != to_mood:
            return "musical"
        
        # Dramatic transitions for significant weather changes
        from_weather = from_scene.get("weather", {}).get("type", "clear")
        to_weather = to_scene.get("weather", {}).get("type", "clear")
        if from_weather != to_weather and to_weather in ["storm", "heavy_rain"]:
            return "dramatic"
        
        # Default to crossfade
        return "crossfade"
    
    def _estimate_cognitive_load(self, scene: Dict[str, Any]) -> float:
        """Estimate the cognitive load of a scene (0-1)."""
        load = 0.0
        
        # Factor in number of layers
        layer_count = len(scene["layers"])
        load += min(0.3, layer_count * 0.02)
        
        # Factor in volume levels
        total_volume = sum(layer.get("volume", 0) for layer in scene["layers"])
        avg_volume = total_volume / max(1, layer_count)
        load += avg_volume * 0.2
        
        # Factor in spatial complexity
        spatial_layers = sum(
            1 for layer in scene["layers"]
            if layer.get("binaural") or layer.get("random_positioning")
        )
        load += min(0.3, spatial_layers * 0.05)
        
        # Factor in category diversity
        categories = set(layer["category"] for layer in scene["layers"])
        load += min(0.2, len(categories) * 0.03)
        
        return min(1.0, load)
    
    def _estimate_bandwidth(self, scene: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate bandwidth requirements for the scene."""
        # Rough estimates based on audio quality
        bitrates = {
            "narration": 128,  # kbps for voice
            "music": 256,  # kbps for music
            "ambient": 192,  # kbps for ambient
            "effect": 128,  # kbps for effects
            "default": 160  # kbps default
        }
        
        total_bitrate = 0
        active_streams = 0
        
        for layer in scene["layers"]:
            if layer.get("volume", 0) > 0:
                category = layer["category"]
                bitrate = bitrates.get(category, bitrates["default"])
                
                # Apply compression factor for quieter sounds
                volume_factor = layer.get("volume", 1.0)
                effective_bitrate = bitrate * (0.5 + 0.5 * volume_factor)
                
                total_bitrate += effective_bitrate
                active_streams += 1
        
        return {
            "total_bitrate_kbps": round(total_bitrate),
            "active_streams": active_streams,
            "bandwidth_mbps": round(total_bitrate / 1000, 2),
            "quality_recommendation": "high" if total_bitrate < 1000 else "adaptive"
        }
    
    def _generate_recommendations(
        self,
        scene: Dict[str, Any],
        layer_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations for scene optimization."""
        recommendations = []
        
        # Check for layer balance
        if "narration" in layer_analysis and layer_analysis["narration"]["average_volume"] < 0.7:
            recommendations.append("Consider increasing narration volume for better clarity")
        
        # Check for excessive ambient
        if "ambient" in layer_analysis and layer_analysis["ambient"]["count"] > 5:
            recommendations.append("Reduce ambient layer count to prevent audio clutter")
        
        # Check for missing elements
        if "music" not in layer_analysis and scene.get("journey_context", {}).get("duration", 0) > 600:
            recommendations.append("Consider adding music for longer journeys")
        
        # Check for cognitive load
        cognitive_load = self._estimate_cognitive_load(scene)
        if cognitive_load > 0.7:
            recommendations.append("Simplify audio scene to reduce driver distraction")
        
        return recommendations


def get_audio_scene_service(
    db: Session = Depends(get_db),
    spatial_audio_engine: SpatialAudioEngine = Depends(get_spatial_audio_engine)
) -> AudioSceneService:
    """
    Dependency to get the audio scene service.
    
    Args:
        db: Database session dependency
        spatial_audio_engine: Spatial audio engine dependency
        
    Returns:
        AudioSceneService instance
    """
    return AudioSceneService(db, spatial_audio_engine)