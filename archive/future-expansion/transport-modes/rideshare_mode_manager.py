"""
Rideshare Mode Manager
Handles mode detection, switching, and management for rideshare drivers and passengers
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
import asyncio
from sqlalchemy.orm import Session

from ..core.logger import get_logger
from ..core.cache import cache_manager
from ..models.user import User
from ..schemas.rideshare import RideshareMode, DriverStats, PassengerPreferences

logger = get_logger(__name__)


class RideshareUserType(Enum):
    DRIVER = "driver"
    PASSENGER = "passenger"
    NONE = "none"


class RideshareModeManager:
    """Manages rideshare mode detection and features"""
    
    def __init__(self):
        self.active_sessions: Dict[int, Dict[str, Any]] = {}
        self.driver_stats_cache = {}
        
    async def detect_mode(
        self,
        user_id: int,
        location_data: Dict[str, Any],
        motion_data: Optional[Dict[str, Any]] = None
    ) -> RideshareUserType:
        """Detect if user is in rideshare mode based on patterns"""
        try:
            # Check manual mode setting first
            cached_mode = await cache_manager.get(f"rideshare_mode:{user_id}")
            if cached_mode:
                return RideshareUserType(cached_mode)
            
            # Analyze motion patterns for automatic detection
            if motion_data:
                # Driver patterns: frequent stops, consistent routes
                if self._detect_driver_patterns(motion_data):
                    return RideshareUserType.DRIVER
                    
                # Passenger patterns: single trip, no control of route
                if self._detect_passenger_patterns(motion_data):
                    return RideshareUserType.PASSENGER
                    
            return RideshareUserType.NONE
            
        except Exception as e:
            logger.error(f"Error detecting rideshare mode: {e}")
            return RideshareUserType.NONE
    
    async def set_mode(
        self,
        user_id: int,
        mode: RideshareUserType,
        preferences: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Manually set rideshare mode"""
        try:
            # Cache mode for 8 hours
            await cache_manager.set(
                f"rideshare_mode:{user_id}",
                mode.value,
                ttl=28800
            )
            
            # Initialize session
            self.active_sessions[user_id] = {
                "mode": mode,
                "started_at": datetime.utcnow(),
                "preferences": preferences or {},
                "stats": self._initialize_stats(mode)
            }
            
            logger.info(f"Set rideshare mode for user {user_id}: {mode.value}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting rideshare mode: {e}")
            return False
    
    async def get_driver_quick_actions(
        self,
        location: Dict[str, float],
        current_state: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get contextual quick actions for drivers"""
        actions = []
        
        # Always available actions
        actions.extend([
            {
                "id": "find_gas",
                "label": "Find Gas",
                "icon": "gas-pump",
                "voice_command": "find gas station",
                "priority": 1
            },
            {
                "id": "quick_food",
                "label": "Quick Food",
                "icon": "food",
                "voice_command": "find quick food",
                "priority": 2
            },
            {
                "id": "take_break",
                "label": "Take Break",
                "icon": "coffee",
                "voice_command": "take a break",
                "priority": 3
            }
        ])
        
        # Contextual actions based on time/state
        if current_state == "waiting_pickup":
            actions.append({
                "id": "optimal_waiting",
                "label": "Best Waiting Spot",
                "icon": "location",
                "voice_command": "where should I wait",
                "priority": 0
            })
        
        # Sort by priority
        actions.sort(key=lambda x: x["priority"])
        return actions
    
    async def get_passenger_entertainment(
        self,
        user_id: int,
        trip_duration: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get entertainment options for passengers"""
        options = {
            "quick_games": [
                {
                    "id": "trivia",
                    "name": "Quick Trivia",
                    "duration": "5-10 min",
                    "description": "Test your knowledge"
                },
                {
                    "id": "20_questions",
                    "name": "20 Questions",
                    "duration": "10-15 min",
                    "description": "AI guesses what you're thinking"
                }
            ],
            "stories": [
                {
                    "id": "short_mystery",
                    "name": "5-Minute Mystery",
                    "duration": "5 min",
                    "description": "Quick whodunit"
                },
                {
                    "id": "local_legend",
                    "name": "Local Legend",
                    "duration": "7-10 min",
                    "description": "Story about your area"
                }
            ],
            "music": {
                "mood_playlists": [
                    "Energizing Morning",
                    "Chill Commute",
                    "Friday Vibes"
                ],
                "quick_mixes": [
                    "Top Hits - 15 min",
                    "Throwback Mix - 20 min"
                ]
            }
        }
        
        # Filter based on trip duration if provided
        if trip_duration and trip_duration < 10:
            # Only show very quick options
            options["quick_games"] = [g for g in options["quick_games"] 
                                     if "5" in g["duration"]]
            options["stories"] = [s for s in options["stories"] 
                                 if "5" in s["duration"]]
                                 
        return options
    
    async def track_driver_earnings(
        self,
        user_id: int,
        trip_data: Dict[str, Any]
    ) -> Dict[str, float]:
        """Track and calculate driver earnings"""
        try:
            session = self.active_sessions.get(user_id, {})
            stats = session.get("stats", {})
            
            # Update earnings
            earnings = trip_data.get("earnings", 0)
            stats["total_earnings"] = stats.get("total_earnings", 0) + earnings
            stats["trips_completed"] = stats.get("trips_completed", 0) + 1
            stats["total_distance"] = stats.get("total_distance", 0) + \
                                     trip_data.get("distance", 0)
            
            # Calculate hourly rate
            session_duration = (datetime.utcnow() - 
                               session.get("started_at", datetime.utcnow()))
            hours_worked = max(session_duration.total_seconds() / 3600, 0.1)
            stats["hourly_rate"] = stats["total_earnings"] / hours_worked
            
            # Cache stats
            await cache_manager.set(
                f"driver_stats:{user_id}",
                stats,
                ttl=3600
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Error tracking earnings: {e}")
            return {}
    
    def _detect_driver_patterns(self, motion_data: Dict[str, Any]) -> bool:
        """Detect driver-specific motion patterns"""
        # Look for:
        # - Frequent stops (pickups/dropoffs)
        # - Circular routes (returning to high-demand areas)
        # - Extended active periods
        stops_per_hour = motion_data.get("stops_per_hour", 0)
        route_efficiency = motion_data.get("route_efficiency", 1.0)
        active_hours = motion_data.get("active_hours", 0)
        
        return (stops_per_hour > 4 and 
                route_efficiency < 0.7 and 
                active_hours > 2)
    
    def _detect_passenger_patterns(self, motion_data: Dict[str, Any]) -> bool:
        """Detect passenger-specific motion patterns"""
        # Look for:
        # - Single destination
        # - No control inputs
        # - Passive motion
        num_destinations = motion_data.get("num_destinations", 0)
        user_inputs = motion_data.get("user_inputs", 0)
        
        return num_destinations == 1 and user_inputs < 2
    
    def _initialize_stats(self, mode: RideshareUserType) -> Dict[str, Any]:
        """Initialize stats based on mode"""
        if mode == RideshareUserType.DRIVER:
            return {
                "total_earnings": 0,
                "trips_completed": 0,
                "total_distance": 0,
                "hourly_rate": 0,
                "peak_hours": [],
                "preferred_areas": []
            }
        elif mode == RideshareUserType.PASSENGER:
            return {
                "trips_taken": 0,
                "favorite_games": [],
                "entertainment_time": 0,
                "mood_preferences": []
            }
        return {}
    
    async def get_optimal_driver_routes(
        self,
        location: Dict[str, float],
        time_of_day: str
    ) -> List[Dict[str, Any]]:
        """Get optimal routes for drivers based on demand"""
        # This would integrate with real-time demand data
        # For now, return mock suggestions
        suggestions = [
            {
                "area": "Downtown",
                "demand_level": "high",
                "estimated_wait": "5-10 min",
                "surge_multiplier": 1.5
            },
            {
                "area": "Airport",
                "demand_level": "medium",
                "estimated_wait": "10-15 min",
                "surge_multiplier": 1.2
            }
        ]
        
        return suggestions
    
    async def suggest_break_locations(
        self,
        location: Dict[str, float],
        preferences: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Suggest good break locations for drivers"""
        # Would integrate with maps API
        # Return mock suggestions for now
        return [
            {
                "name": "Rest Stop Plaza",
                "distance": "2 miles",
                "amenities": ["restrooms", "food", "gas"],
                "rating": 4.2
            },
            {
                "name": "Park & Stretch",
                "distance": "0.5 miles",
                "amenities": ["restrooms", "walking path"],
                "rating": 4.5
            }
        ]


# Global instance
rideshare_mode_manager = RideshareModeManager()