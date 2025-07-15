"""
Terminal Navigation Service

Provides wayfinding and navigation assistance within airport terminals,
including walking time estimates, accessibility routes, and real-time updates.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import math

from backend.app.core.logger import get_logger
from backend.app.core.cache import get_cache

logger = get_logger(__name__)


class LocationType(str, Enum):
    GATE = "gate"
    LOUNGE = "lounge"
    RESTAURANT = "restaurant"
    RESTROOM = "restroom"
    SECURITY = "security"
    CUSTOMS = "customs"
    BAGGAGE = "baggage"
    CHECKIN = "check-in"
    SHOP = "shop"
    ATM = "atm"
    PHARMACY = "pharmacy"
    CHARGING = "charging_station"


class RouteType(str, Enum):
    FASTEST = "fastest"
    ACCESSIBLE = "accessible"
    SCENIC = "scenic"  # Routes with shops/restaurants
    QUIET = "quiet"    # Avoiding crowded areas


@dataclass
class TerminalLocation:
    """Represents a location in the terminal"""
    id: str
    type: LocationType
    name: str
    terminal: str
    level: int
    coordinates: Tuple[float, float]  # (x, y) in terminal grid
    amenities: List[str]
    accessibility_features: List[str]
    current_wait_time: Optional[int] = None


@dataclass
class NavigationSegment:
    """A segment of the navigation route"""
    from_location: str
    to_location: str
    direction: str
    distance_meters: int
    walking_time_minutes: int
    accessibility_time_minutes: Optional[int]
    landmarks: List[str]
    amenities_along_route: List[str]


@dataclass
class NavigationRoute:
    """Complete navigation route"""
    route_id: str
    type: RouteType
    segments: List[NavigationSegment]
    total_distance_meters: int
    total_walking_time_minutes: int
    accessibility_time_minutes: Optional[int]
    amenities_summary: Dict[str, int]
    congestion_level: str  # low, medium, high
    real_time_alerts: List[str]


class TerminalNavigationService:
    """Manages terminal navigation and wayfinding"""
    
    # Average walking speeds
    WALKING_SPEED_MPS = 1.4  # meters per second (normal)
    ACCESSIBLE_SPEED_MPS = 0.8  # with mobility assistance
    RUNNING_SPEED_MPS = 3.0  # if rushing
    
    def __init__(self):
        self.cache = get_cache()
        
    async def get_terminal_map(
        self,
        airport_code: str,
        terminal: str
    ) -> Dict[str, Any]:
        """Get terminal map data"""
        try:
            # Check cache
            cache_key = f"terminal_map:{airport_code}:{terminal}"
            cached = await self.cache.get(cache_key)
            if cached:
                return cached
            
            # In production, this would fetch from airport API
            # For now, return mock data
            map_data = self._get_mock_terminal_map(airport_code, terminal)
            
            # Cache for 24 hours
            await self.cache.set(cache_key, map_data, expire=86400)
            return map_data
            
        except Exception as e:
            logger.error(f"Failed to get terminal map: {e}")
            return {}
    
    def _get_mock_terminal_map(
        self,
        airport_code: str,
        terminal: str
    ) -> Dict[str, Any]:
        """Return mock terminal map data"""
        if airport_code == "LAX" and terminal == "4":
            return {
                "terminal": "4",
                "levels": 2,
                "total_area_sqm": 50000,
                "locations": [
                    {
                        "id": "gate_44",
                        "type": "gate",
                        "name": "Gate 44",
                        "level": 2,
                        "coordinates": [1000, 500],
                        "amenities": ["seating", "charging_stations"]
                    },
                    {
                        "id": "security_t4",
                        "type": "security",
                        "name": "Security Checkpoint",
                        "level": 1,
                        "coordinates": [500, 250],
                        "amenities": ["tsa_precheck", "clear"]
                    },
                    {
                        "id": "lounge_pp_t4",
                        "type": "lounge",
                        "name": "Priority Pass Lounge",
                        "level": 2,
                        "coordinates": [1100, 600],
                        "amenities": ["food", "bar", "showers", "wifi"]
                    }
                ],
                "connections": [
                    {"from": "security_t4", "to": "gate_44", "distance": 600},
                    {"from": "gate_44", "to": "lounge_pp_t4", "distance": 150}
                ]
            }
        
        # Default mock data
        return {
            "terminal": terminal,
            "levels": 2,
            "total_area_sqm": 30000,
            "locations": [],
            "connections": []
        }
    
    async def calculate_route(
        self,
        airport_code: str,
        from_location: str,
        to_location: str,
        route_type: RouteType = RouteType.FASTEST,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> Optional[NavigationRoute]:
        """Calculate optimal route between two locations"""
        try:
            # Get terminal map
            terminal = await self._determine_terminal(
                airport_code, from_location, to_location
            )
            map_data = await self.get_terminal_map(airport_code, terminal)
            
            if not map_data:
                return None
            
            # Calculate route based on type
            if route_type == RouteType.ACCESSIBLE:
                route = await self._calculate_accessible_route(
                    map_data, from_location, to_location
                )
            elif route_type == RouteType.SCENIC:
                route = await self._calculate_scenic_route(
                    map_data, from_location, to_location, user_preferences
                )
            else:
                route = await self._calculate_fastest_route(
                    map_data, from_location, to_location
                )
            
            # Add real-time information
            if route:
                route = await self._add_real_time_info(route, airport_code)
            
            return route
            
        except Exception as e:
            logger.error(f"Failed to calculate route: {e}")
            return None
    
    async def _determine_terminal(
        self,
        airport_code: str,
        from_location: str,
        to_location: str
    ) -> str:
        """Determine which terminal the locations are in"""
        # In production, this would look up location database
        # For mock, extract from location ID
        if "t4" in from_location.lower() or "t4" in to_location.lower():
            return "4"
        return "1"
    
    async def _calculate_fastest_route(
        self,
        map_data: Dict[str, Any],
        from_location: str,
        to_location: str
    ) -> NavigationRoute:
        """Calculate fastest walking route"""
        # Mock implementation
        route_id = f"route_{datetime.utcnow().timestamp()}"
        
        # Create mock segments
        segments = [
            NavigationSegment(
                from_location=from_location,
                to_location="central_corridor",
                direction="Head towards the central corridor",
                distance_meters=200,
                walking_time_minutes=3,
                accessibility_time_minutes=5,
                landmarks=["Starbucks on your right", "Gate 42 on your left"],
                amenities_along_route=["restroom", "water_fountain"]
            ),
            NavigationSegment(
                from_location="central_corridor",
                to_location=to_location,
                direction="Turn left and walk to the end",
                distance_meters=150,
                walking_time_minutes=2,
                accessibility_time_minutes=3,
                landmarks=["News stand", "Gate 44"],
                amenities_along_route=["atm", "charging_station"]
            )
        ]
        
        total_distance = sum(s.distance_meters for s in segments)
        total_time = sum(s.walking_time_minutes for s in segments)
        
        return NavigationRoute(
            route_id=route_id,
            type=RouteType.FASTEST,
            segments=segments,
            total_distance_meters=total_distance,
            total_walking_time_minutes=total_time,
            accessibility_time_minutes=8,
            amenities_summary={
                "restrooms": 1,
                "restaurants": 0,
                "shops": 1,
                "charging_stations": 1
            },
            congestion_level="medium",
            real_time_alerts=[]
        )
    
    async def _calculate_accessible_route(
        self,
        map_data: Dict[str, Any],
        from_location: str,
        to_location: str
    ) -> NavigationRoute:
        """Calculate accessible route avoiding stairs/escalators"""
        # Mock implementation focusing on elevators and ramps
        route_id = f"route_accessible_{datetime.utcnow().timestamp()}"
        
        segments = [
            NavigationSegment(
                from_location=from_location,
                to_location="elevator_bank_a",
                direction="Follow signs to elevators",
                distance_meters=250,
                walking_time_minutes=5,
                accessibility_time_minutes=6,
                landmarks=["Information desk", "Accessible restroom"],
                amenities_along_route=["accessible_restroom", "elevator"]
            ),
            NavigationSegment(
                from_location="elevator_bank_a",
                to_location=to_location,
                direction="Take elevator to Level 2, turn right",
                distance_meters=100,
                walking_time_minutes=3,
                accessibility_time_minutes=4,
                landmarks=["Level 2 food court"],
                amenities_along_route=["accessible_seating"]
            )
        ]
        
        total_distance = sum(s.distance_meters for s in segments)
        total_time = sum(s.accessibility_time_minutes for s in segments)
        
        return NavigationRoute(
            route_id=route_id,
            type=RouteType.ACCESSIBLE,
            segments=segments,
            total_distance_meters=total_distance,
            total_walking_time_minutes=8,
            accessibility_time_minutes=total_time,
            amenities_summary={
                "accessible_restrooms": 1,
                "elevators": 1,
                "accessible_seating": 2
            },
            congestion_level="low",
            real_time_alerts=["Elevator at Gate 45 temporarily out of service"]
        )
    
    async def _calculate_scenic_route(
        self,
        map_data: Dict[str, Any],
        from_location: str,
        to_location: str,
        user_preferences: Optional[Dict[str, Any]]
    ) -> NavigationRoute:
        """Calculate route passing by shops and restaurants"""
        route_id = f"route_scenic_{datetime.utcnow().timestamp()}"
        
        # Route through shopping/dining areas
        segments = [
            NavigationSegment(
                from_location=from_location,
                to_location="duty_free_plaza",
                direction="Head to Duty Free shopping area",
                distance_meters=300,
                walking_time_minutes=4,
                accessibility_time_minutes=6,
                landmarks=["Luxury boutiques", "Wine bar"],
                amenities_along_route=["shops", "cafe", "bar"]
            ),
            NavigationSegment(
                from_location="duty_free_plaza",
                to_location="restaurant_row",
                direction="Continue through dining concourse",
                distance_meters=200,
                walking_time_minutes=3,
                accessibility_time_minutes=4,
                landmarks=["Umami Burger", "Petrossian Bar"],
                amenities_along_route=["restaurants", "quick_service"]
            ),
            NavigationSegment(
                from_location="restaurant_row",
                to_location=to_location,
                direction="Exit dining area towards your destination",
                distance_meters=150,
                walking_time_minutes=2,
                accessibility_time_minutes=3,
                landmarks=["Gate 44 ahead"],
                amenities_along_route=["water_fountain"]
            )
        ]
        
        total_distance = sum(s.distance_meters for s in segments)
        total_time = sum(s.walking_time_minutes for s in segments)
        
        return NavigationRoute(
            route_id=route_id,
            type=RouteType.SCENIC,
            segments=segments,
            total_distance_meters=total_distance,
            total_walking_time_minutes=total_time,
            accessibility_time_minutes=13,
            amenities_summary={
                "shops": 8,
                "restaurants": 5,
                "bars": 2,
                "cafes": 3
            },
            congestion_level="high",
            real_time_alerts=["Restaurant Row busy - 15-20 min wait at most venues"]
        )
    
    async def _add_real_time_info(
        self,
        route: NavigationRoute,
        airport_code: str
    ) -> NavigationRoute:
        """Add real-time congestion and alerts"""
        # In production, this would fetch from airport systems
        # Mock implementation
        import random
        
        # Add random congestion updates
        hour = datetime.now().hour
        if 6 <= hour <= 9 or 17 <= hour <= 20:
            route.congestion_level = "high"
            route.real_time_alerts.append("Peak travel time - expect crowds")
        
        # Add random alerts
        if random.random() < 0.3:
            route.real_time_alerts.append(
                "Security wait time: 25 minutes at main checkpoint"
            )
        
        return route
    
    async def get_walking_time(
        self,
        from_location: str,
        to_location: str,
        walking_speed: str = "normal"
    ) -> Dict[str, int]:
        """Get estimated walking time between locations"""
        try:
            # In production, calculate actual distance
            # Mock implementation
            base_distance = 350  # meters
            
            speeds = {
                "slow": self.ACCESSIBLE_SPEED_MPS,
                "normal": self.WALKING_SPEED_MPS,
                "fast": self.RUNNING_SPEED_MPS
            }
            
            speed = speeds.get(walking_speed, self.WALKING_SPEED_MPS)
            time_seconds = base_distance / speed
            time_minutes = math.ceil(time_seconds / 60)
            
            return {
                "walking_time_minutes": time_minutes,
                "distance_meters": base_distance,
                "route_type": "direct"
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate walking time: {e}")
            return {"walking_time_minutes": 10}  # Default estimate
    
    async def find_nearest_amenity(
        self,
        current_location: str,
        amenity_type: str,
        max_results: int = 3
    ) -> List[Dict[str, Any]]:
        """Find nearest amenities of specified type"""
        try:
            # Mock implementation
            amenities = {
                "restroom": [
                    {"name": "Restroom A", "distance_meters": 50, "walking_time": 1},
                    {"name": "Family Restroom", "distance_meters": 120, "walking_time": 2}
                ],
                "restaurant": [
                    {"name": "Umami Burger", "distance_meters": 200, "walking_time": 3},
                    {"name": "Starbucks", "distance_meters": 80, "walking_time": 1}
                ],
                "atm": [
                    {"name": "Chase ATM", "distance_meters": 150, "walking_time": 2},
                    {"name": "Bank of America", "distance_meters": 300, "walking_time": 4}
                ],
                "charging_station": [
                    {"name": "Charging Hub A", "distance_meters": 100, "walking_time": 2},
                    {"name": "Gate 44 Charging", "distance_meters": 30, "walking_time": 1}
                ]
            }
            
            results = amenities.get(amenity_type, [])
            return sorted(results, key=lambda x: x["distance_meters"])[:max_results]
            
        except Exception as e:
            logger.error(f"Failed to find amenities: {e}")
            return []
    
    async def get_security_wait_times(
        self,
        airport_code: str,
        terminal: str
    ) -> Dict[str, Any]:
        """Get current security checkpoint wait times"""
        try:
            # In production, fetch from TSA API
            # Mock implementation
            import random
            
            current_hour = datetime.now().hour
            base_wait = 10
            
            # Peak hours
            if 6 <= current_hour <= 9 or 16 <= current_hour <= 19:
                base_wait = 25
            
            return {
                "main_checkpoint": {
                    "standard_lanes": base_wait + random.randint(-5, 10),
                    "tsa_precheck": max(5, base_wait // 3),
                    "clear": max(2, base_wait // 5)
                },
                "alternate_checkpoint": {
                    "standard_lanes": base_wait + random.randint(-3, 5),
                    "tsa_precheck": max(5, (base_wait + 5) // 3)
                },
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get security wait times: {e}")
            return {}
    
    async def get_gate_change_alerts(
        self,
        flight_number: str,
        current_gate: str
    ) -> Optional[Dict[str, Any]]:
        """Check for gate change alerts"""
        try:
            # In production, monitor flight information systems
            # Mock: 10% chance of gate change
            import random
            
            if random.random() < 0.1:
                new_gate = f"Gate {random.randint(40, 49)}"
                return {
                    "alert_type": "gate_change",
                    "flight_number": flight_number,
                    "old_gate": current_gate,
                    "new_gate": new_gate,
                    "walking_time_minutes": random.randint(3, 8),
                    "announcement_time": datetime.utcnow().isoformat()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to check gate changes: {e}")
            return None
    
    async def get_accessibility_services(
        self,
        airport_code: str,
        terminal: str
    ) -> Dict[str, Any]:
        """Get information about accessibility services"""
        return {
            "wheelchair_assistance": {
                "request_points": [
                    "Curbside check-in",
                    "Security checkpoint",
                    "Gate agents"
                ],
                "phone": "+1-555-0199"
            },
            "accessible_routes": {
                "elevators": 6,
                "ramps": 12,
                "accessible_restrooms": 8
            },
            "sensory_assistance": {
                "hearing_loops": ["Gates 40-49", "Customer Service"],
                "braille_signage": True,
                "visual_paging": True
            },
            "service_animals": {
                "relief_areas": [
                    "Post-security near Gate 45",
                    "Pre-security courtyard"
                ]
            }
        }