from datetime import datetime, time, timedelta
import json
import math
import random
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union, Set

from fastapi import Depends, HTTPException, status
from sqlalchemy import and_, or_, func, desc, text
from sqlalchemy.orm import Session, joinedload

from app.core.logger import get_logger
from app.database import get_db
from app.models.user import User
from app.models.directions import Route, RouteLeg, RouteStep, Location

logger = get_logger(__name__)


class SerendipityType:
    """Types of serendipitous discoveries."""
    HIDDEN_GEM = "hidden_gem"
    LOCAL_SECRET = "local_secret"
    UNUSUAL_SIGHT = "unusual_sight"
    VIEWPOINT = "viewpoint"
    PHOTO_OPPORTUNITY = "photo_opportunity"
    QUIRKY_ATTRACTION = "quirky_attraction"
    UNEXPECTED_DELIGHT = "unexpected_delight"
    HISTORIC_DISCOVERY = "historic_discovery"
    NATURAL_WONDER = "natural_wonder"
    CULTURAL_EXPERIENCE = "cultural_experience"


class SerendipityEngine:
    """
    Service for generating unexpected discoveries and surprise moments.
    
    This service creates serendipitous experiences based on user location,
    preferences, and contextual factors, aiming to create memorable
    unplanned moments during the journey.
    """
    
    def __init__(self, db: Session):
        """Initialize the serendipity engine with database session."""
        self.db = db
        
        # Serendipity database (in a production version, this would be stored in the database)
        self.serendipity_db = {
            SerendipityType.HIDDEN_GEM: [
                {
                    "id": "hg1",
                    "title": "Secret Local Cafe",
                    "description": "A charming cafe known only to locals, with amazing pastries and coffee.",
                    "minimum_detour_minutes": 5,
                    "maximum_detour_minutes": 15,
                    "usual_duration_minutes": 30,
                    "tags": ["food", "local", "coffee", "relaxing"],
                    "environment_types": ["urban", "small_town"],
                    "time_ranges": ["morning", "afternoon"],
                    "uniqueness_score": 85,
                    "discovery_factor": 0.9
                },
                {
                    "id": "hg2",
                    "title": "Hidden Waterfall",
                    "description": "A serene waterfall tucked away from the main trails, perfect for a peaceful break.",
                    "minimum_detour_minutes": 15,
                    "maximum_detour_minutes": 45,
                    "usual_duration_minutes": 60,
                    "tags": ["nature", "water", "hiking", "peaceful"],
                    "environment_types": ["forest", "mountain"],
                    "time_ranges": ["morning", "afternoon"],
                    "uniqueness_score": 90,
                    "discovery_factor": 0.85
                }
            ],
            SerendipityType.LOCAL_SECRET: [
                {
                    "id": "ls1",
                    "title": "Locals-Only Swimming Hole",
                    "description": "A perfect natural swimming spot that only locals know about.",
                    "minimum_detour_minutes": 20,
                    "maximum_detour_minutes": 40,
                    "usual_duration_minutes": 90,
                    "tags": ["swimming", "nature", "water", "summer"],
                    "environment_types": ["forest", "rural"],
                    "time_ranges": ["morning", "afternoon"],
                    "uniqueness_score": 88,
                    "discovery_factor": 0.92
                },
                {
                    "id": "ls2",
                    "title": "Underground Art Gallery",
                    "description": "A tiny, unmarked gallery featuring incredible works by local artists.",
                    "minimum_detour_minutes": 10,
                    "maximum_detour_minutes": 25,
                    "usual_duration_minutes": 45,
                    "tags": ["art", "culture", "local", "indoor"],
                    "environment_types": ["urban", "small_town"],
                    "time_ranges": ["afternoon", "evening"],
                    "uniqueness_score": 82,
                    "discovery_factor": 0.8
                }
            ],
            SerendipityType.UNUSUAL_SIGHT: [
                {
                    "id": "us1",
                    "title": "Giant Roadside Sculpture",
                    "description": "An enormous, quirky sculpture that makes for a great photo opportunity.",
                    "minimum_detour_minutes": 5,
                    "maximum_detour_minutes": 15,
                    "usual_duration_minutes": 15,
                    "tags": ["quirky", "photo", "art", "roadside"],
                    "environment_types": ["rural", "highway"],
                    "time_ranges": ["any"],
                    "uniqueness_score": 75,
                    "discovery_factor": 0.7
                },
                {
                    "id": "us2",
                    "title": "Abandoned Ghost Town",
                    "description": "Remnants of a once-thriving town, now eerily deserted.",
                    "minimum_detour_minutes": 30,
                    "maximum_detour_minutes": 60,
                    "usual_duration_minutes": 90,
                    "tags": ["historical", "abandoned", "ghost_town", "photo"],
                    "environment_types": ["desert", "rural"],
                    "time_ranges": ["morning", "afternoon"],
                    "uniqueness_score": 92,
                    "discovery_factor": 0.88
                }
            ],
            SerendipityType.VIEWPOINT: [
                {
                    "id": "vp1",
                    "title": "Secret Panoramic Overlook",
                    "description": "A little-known viewpoint offering stunning vistas not visible from the main road.",
                    "minimum_detour_minutes": 15,
                    "maximum_detour_minutes": 30,
                    "usual_duration_minutes": 20,
                    "tags": ["scenic", "photo", "nature", "viewpoint"],
                    "environment_types": ["mountain", "rural", "coastal"],
                    "time_ranges": ["morning", "afternoon", "sunset"],
                    "uniqueness_score": 80,
                    "discovery_factor": 0.75
                },
                {
                    "id": "vp2",
                    "title": "Urban Skyline Viewpoint",
                    "description": "An unexpected spot to view the city skyline from a different angle.",
                    "minimum_detour_minutes": 10,
                    "maximum_detour_minutes": 25,
                    "usual_duration_minutes": 30,
                    "tags": ["urban", "skyline", "photo", "viewpoint"],
                    "environment_types": ["urban", "small_town"],
                    "time_ranges": ["afternoon", "sunset", "night"],
                    "uniqueness_score": 78,
                    "discovery_factor": 0.72
                }
            ],
            SerendipityType.PHOTO_OPPORTUNITY: [
                {
                    "id": "po1",
                    "title": "Stunning Wildflower Field",
                    "description": "A meadow filled with vibrant wildflowers, perfect for memorable photos.",
                    "minimum_detour_minutes": 10,
                    "maximum_detour_minutes": 20,
                    "usual_duration_minutes": 25,
                    "tags": ["flowers", "nature", "photo", "colorful"],
                    "environment_types": ["rural", "meadow", "forest"],
                    "time_ranges": ["morning", "afternoon"],
                    "uniqueness_score": 76,
                    "discovery_factor": 0.68
                },
                {
                    "id": "po2",
                    "title": "Vintage Neon Sign Collection",
                    "description": "A surprising collection of restored vintage neon signs illuminating the night.",
                    "minimum_detour_minutes": 5,
                    "maximum_detour_minutes": 20,
                    "usual_duration_minutes": 30,
                    "tags": ["vintage", "neon", "photo", "night"],
                    "environment_types": ["urban", "small_town"],
                    "time_ranges": ["evening", "night"],
                    "uniqueness_score": 80,
                    "discovery_factor": 0.78
                }
            ],
            # Other serendipity types would follow with their own entries
        }
    
    async def generate_surprise(
        self,
        user_id: str,
        current_location: Dict[str, float],
        environment_type: str,
        available_time: int,  # minutes
        current_time: Optional[datetime] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
        route_id: Optional[str] = None,
        past_discoveries: Optional[List[str]] = None,
        weather: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a serendipitous discovery based on user context.
        
        Args:
            user_id: ID of the user
            current_location: Dict with latitude and longitude
            environment_type: Current environment type (urban, rural, forest, etc.)
            available_time: Available time in minutes for a detour
            current_time: Current time (defaults to now)
            user_preferences: Optional user preferences
            route_id: Optional ID of the active route
            past_discoveries: Optional list of past discovery IDs to avoid duplicates
            weather: Optional current weather conditions
            
        Returns:
            Serendipitous discovery if found, None otherwise
        """
        try:
            # Use current time if not provided
            if current_time is None:
                current_time = datetime.utcnow()
            
            # Determine time of day category
            hour = current_time.hour
            time_of_day = "night"
            if 5 <= hour < 12:
                time_of_day = "morning"
            elif 12 <= hour < 17:
                time_of_day = "afternoon"
            elif 17 <= hour < 20:
                time_of_day = "evening"
            
            # Extract past discovery IDs to avoid
            past_ids = set()
            if past_discoveries:
                past_ids = set(past_discoveries)
            
            # Extract user interests
            interests = []
            if user_preferences and "interests" in user_preferences:
                interests = user_preferences["interests"]
            
            # Determine whether to generate a serendipitous discovery
            # Higher chance with more available time
            base_chance = 0.3  # 30% base chance
            time_factor = min(1.0, available_time / 60)  # Scale with available time (up to 60 min)
            serendipity_chance = base_chance + (time_factor * 0.4)  # 30-70% chance
            
            # Random roll - if we fail the check, don't generate serendipity
            if random.random() > serendipity_chance:
                return None
            
            # Gather all possible discoveries that match our criteria
            candidates = []
            for s_type, discoveries in self.serendipity_db.items():
                for discovery in discoveries:
                    # Skip discoveries that are too long for available time
                    total_time = discovery["usual_duration_minutes"] + discovery["minimum_detour_minutes"]
                    if total_time > available_time:
                        continue
                    
                    # Skip past discoveries
                    if discovery["id"] in past_ids:
                        continue
                    
                    # Check environment compatibility
                    if "any" not in discovery["environment_types"] and environment_type not in discovery["environment_types"]:
                        continue
                    
                    # Check time compatibility
                    if "any" not in discovery["time_ranges"] and time_of_day not in discovery["time_ranges"]:
                        continue
                    
                    # Weather compatibility (if specified)
                    if weather and "weather" in discovery and weather not in discovery["weather"]:
                        continue
                    
                    # Add to candidates with scoring
                    score = discovery["uniqueness_score"] * discovery["discovery_factor"]
                    
                    # Boost score for matching interests
                    if interests and any(tag in interests for tag in discovery["tags"]):
                        score *= 1.3
                    
                    candidates.append((discovery, s_type, score))
            
            if not candidates:
                return None
            
            # Sort by score and pick one of the top options (with some randomness)
            candidates.sort(key=lambda x: x[2], reverse=True)
            top_candidates = candidates[:min(3, len(candidates))]
            weighted_candidates = [(c, s, score) for c, s, score in top_candidates]
            
            # Select based on weighted probabilities
            total_score = sum(score for _, _, score in weighted_candidates)
            selection_probs = [score / total_score for _, _, score in weighted_candidates]
            
            # Choose a discovery
            selected_idx = random.choices(range(len(weighted_candidates)), weights=selection_probs, k=1)[0]
            discovery, s_type, _ = weighted_candidates[selected_idx]
            
            # Generate location near current position (simulated; in a real app, this would use map data)
            detour_distance_km = random.uniform(1, 5)
            bearing = random.uniform(0, 360)
            
            # Calculate new coordinates based on bearing and distance
            lat1 = math.radians(current_location["latitude"])
            lon1 = math.radians(current_location["longitude"])
            
            # Earth radius in km
            R = 6371
            
            # Calculate new point
            bearing_rad = math.radians(bearing)
            angular_distance = detour_distance_km / R
            
            lat2 = math.asin(math.sin(lat1) * math.cos(angular_distance) + 
                             math.cos(lat1) * math.sin(angular_distance) * math.cos(bearing_rad))
            
            lon2 = lon1 + math.atan2(math.sin(bearing_rad) * math.sin(angular_distance) * math.cos(lat1),
                                     math.cos(angular_distance) - math.sin(lat1) * math.sin(lat2))
            
            discovery_latitude = math.degrees(lat2)
            discovery_longitude = math.degrees(lon2)
            
            # Create the serendipitous discovery object
            now = datetime.utcnow()
            serendipity = {
                "id": str(uuid.uuid4()),
                "discovery_id": discovery["id"],
                "type": s_type,
                "title": discovery["title"],
                "description": discovery["description"],
                "detected_at": now.isoformat(),
                "user_id": user_id,
                "latitude": discovery_latitude,
                "longitude": discovery_longitude,
                "environment_type": environment_type,
                "detour_distance_km": detour_distance_km,
                "detour_time_minutes": discovery["minimum_detour_minutes"],
                "duration_minutes": discovery["usual_duration_minutes"],
                "total_time_required": discovery["minimum_detour_minutes"] + discovery["usual_duration_minutes"],
                "tags": discovery["tags"],
                "uniqueness_score": discovery["uniqueness_score"],
                "matches_interests": interests and any(tag in interests for tag in discovery["tags"]),
                "expires_at": (now + timedelta(minutes=90)).isoformat()
            }
            
            return serendipity
        except Exception as e:
            logger.error(f"Error generating surprise: {str(e)}")
            return None
    
    async def batch_generate_surprises(
        self,
        user_id: str,
        route: Dict[str, Any],
        total_trip_duration: int,  # minutes
        user_preferences: Optional[Dict[str, Any]] = None,
        count: int = 3,
        past_discoveries: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple serendipitous discoveries along a route.
        
        Args:
            user_id: ID of the user
            route: Route dict with waypoints
            total_trip_duration: Expected duration of the trip in minutes
            user_preferences: Optional user preferences
            count: Number of discoveries to generate
            past_discoveries: Optional list of past discovery IDs to avoid duplicates
            
        Returns:
            List of serendipitous discoveries
        """
        try:
            # Extract route waypoints
            waypoints = route.get("waypoints", [])
            if not waypoints:
                return []
            
            # Determine reasonable spacing between discoveries
            # We want them to be somewhat evenly distributed
            min_spacing = total_trip_duration / (count * 3)  # At least 1/3 of even spacing
            max_spacing = total_trip_duration / (count * 0.8)  # At most 1.25x even spacing
            
            # Generate discoveries
            discoveries = []
            cumulative_time = random.uniform(total_trip_duration * 0.15, total_trip_duration * 0.25)  # Start after 15-25% of the trip
            
            for i in range(count):
                # Determine point along route
                progress_ratio = cumulative_time / total_trip_duration
                waypoint_index = min(int(progress_ratio * len(waypoints)), len(waypoints) - 1)
                waypoint = waypoints[waypoint_index]
                
                # Determine environment type based on waypoint (simplified)
                # In a real implementation, this would use map data
                environment_types = ["urban", "rural", "forest", "mountain", "coastal", "desert", "small_town"]
                environment_type = random.choice(environment_types)
                
                # Available time for this discovery (10-20% of total gap to next one)
                next_discovery_time = total_trip_duration if i == count - 1 else cumulative_time + random.uniform(min_spacing, max_spacing)
                gap_to_next = next_discovery_time - cumulative_time
                available_time = random.uniform(gap_to_next * 0.1, gap_to_next * 0.2)
                
                # Generate a surprise at this location
                discovery = await self.generate_surprise(
                    user_id=user_id,
                    current_location={"latitude": waypoint["lat"], "longitude": waypoint["lng"]},
                    environment_type=environment_type,
                    available_time=available_time,
                    user_preferences=user_preferences,
                    past_discoveries=past_discoveries
                )
                
                if discovery:
                    # Add route context
                    discovery["route_progress_percent"] = progress_ratio * 100
                    discovery["estimated_arrival_time"] = (datetime.utcnow() + timedelta(minutes=cumulative_time)).isoformat()
                    
                    discoveries.append(discovery)
                    
                    # Add this discovery to past_discoveries to avoid duplicates
                    if past_discoveries is None:
                        past_discoveries = []
                    past_discoveries.append(discovery["discovery_id"])
                
                # Move to next potential discovery point
                cumulative_time = next_discovery_time
            
            return discoveries
        except Exception as e:
            logger.error(f"Error batch generating surprises: {str(e)}")
            return []
    
    async def suggest_detour(
        self,
        user_id: str,
        current_location: Dict[str, float],
        destination: Dict[str, float],
        max_detour_time: int,  # minutes
        max_detour_distance: float,  # km
        user_preferences: Optional[Dict[str, Any]] = None,
        past_discoveries: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Suggest a serendipitous detour between current location and destination.
        
        Args:
            user_id: ID of the user
            current_location: Dict with latitude and longitude of current position
            destination: Dict with latitude and longitude of destination
            max_detour_time: Maximum acceptable detour time in minutes
            max_detour_distance: Maximum acceptable detour distance in km
            user_preferences: Optional user preferences
            past_discoveries: Optional list of past discovery IDs to avoid duplicates
            
        Returns:
            Detour suggestion if found, None otherwise
        """
        try:
            # Calculate direct distance between current location and destination
            direct_distance = self._haversine_distance(
                lat1=current_location["latitude"],
                lon1=current_location["longitude"],
                lat2=destination["latitude"],
                lon2=destination["longitude"]
            )
            
            # Determine reasonable detour area
            # We'll look for points that are within a certain distance but not on the direct path
            
            # Determine environment type (simplified)
            # In a real implementation, this would use map data
            environment_types = ["urban", "rural", "forest", "mountain", "coastal", "desert", "small_town"]
            environment_type = random.choice(environment_types)
            
            # Find a viable serendipitous discovery
            discovery = await self.generate_surprise(
                user_id=user_id,
                current_location=current_location,
                environment_type=environment_type,
                available_time=max_detour_time,
                user_preferences=user_preferences,
                past_discoveries=past_discoveries
            )
            
            if not discovery:
                return None
            
            # Calculate distances
            discovery_location = {
                "latitude": discovery["latitude"],
                "longitude": discovery["longitude"]
            }
            
            distance_to_discovery = self._haversine_distance(
                lat1=current_location["latitude"],
                lon1=current_location["longitude"],
                lat2=discovery_location["latitude"],
                lon2=discovery_location["longitude"]
            )
            
            distance_from_discovery_to_dest = self._haversine_distance(
                lat1=discovery_location["latitude"],
                lon1=discovery_location["longitude"],
                lat2=destination["latitude"],
                lon2=destination["longitude"]
            )
            
            total_detour_distance = distance_to_discovery + distance_from_discovery_to_dest
            added_distance = total_detour_distance - direct_distance
            
            # Check if the detour is acceptable
            if added_distance > max_detour_distance:
                return None
            
            # Estimate travel time (simplified, assuming 60 km/h average speed)
            detour_travel_time = (added_distance / 60) * 60  # Convert to minutes
            
            if detour_travel_time > max_detour_time:
                return None
            
            # Create detour suggestion
            detour = {
                "id": str(uuid.uuid4()),
                "discovery": discovery,
                "direct_distance_km": direct_distance,
                "detour_distance_km": total_detour_distance,
                "added_distance_km": added_distance,
                "estimated_detour_travel_time_minutes": detour_travel_time,
                "total_detour_time_minutes": detour_travel_time + discovery["duration_minutes"],
                "waypoints": [
                    {"latitude": current_location["latitude"], "longitude": current_location["longitude"]},
                    {"latitude": discovery_location["latitude"], "longitude": discovery_location["longitude"]},
                    {"latitude": destination["latitude"], "longitude": destination["longitude"]}
                ]
            }
            
            return detour
        except Exception as e:
            logger.error(f"Error suggesting detour: {str(e)}")
            return None
    
    def _haversine_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calculate the great-circle distance between two points on Earth.
        
        Args:
            lat1: Latitude of the first point in degrees
            lon1: Longitude of the first point in degrees
            lat2: Latitude of the second point in degrees
            lon2: Longitude of the second point in degrees
            
        Returns:
            Distance between the points in kilometers
        """
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371  # Earth radius in kilometers
        
        return c * r


def get_serendipity_engine(db: Session = Depends(get_db)) -> SerendipityEngine:
    """
    Dependency to get the serendipity engine.
    
    Args:
        db: Database session dependency
        
    Returns:
        SerendipityEngine instance
    """
    return SerendipityEngine(db)