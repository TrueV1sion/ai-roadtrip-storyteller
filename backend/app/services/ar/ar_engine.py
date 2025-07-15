from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime
from pydantic import BaseModel

from ...core.config import settings
from ...core.enhanced_ai_client import EnhancedAIClient
from ...models.user import User
from ...services.locationService import LocationService
from ...services.historical_service import HistoricalService

logger = logging.getLogger(__name__)

class ARPoint(BaseModel):
    """Base model for an AR point of interest"""
    id: str
    title: str
    description: str
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    type: str  # historical, navigation, nature, etc.
    metadata: Dict[str, Any] = {}
    
class HistoricalARPoint(ARPoint):
    """AR point for historical overlays"""
    year: int
    historical_context: str
    image_url: Optional[str] = None
    
class NavigationARPoint(ARPoint):
    """AR point for navigation aids"""
    distance: float  # in meters
    eta: Optional[int] = None  # in seconds
    direction: str  # "left", "right", "ahead", etc.
    
class NatureARPoint(ARPoint):
    """AR point for nature landmarks"""
    species: Optional[str] = None
    ecosystem_info: Optional[str] = None
    conservation_status: Optional[str] = None

class AREngine:
    """Main engine for Augmented Reality features"""
    
    def __init__(
        self,
        location_service: LocationService,
        historical_service: HistoricalService,
        ai_client: EnhancedAIClient
    ):
        self.location_service = location_service
        self.historical_service = historical_service
        self.ai_client = ai_client
        self.max_points = settings.AR_MAX_POINTS
        self.point_distance_threshold = settings.AR_POINT_DISTANCE_THRESHOLD  # meters
        logger.info("AR Engine initialized")
        
    async def get_ar_points(
        self, 
        user: User,
        latitude: float, 
        longitude: float, 
        radius: float = 500,
        types: List[str] = None
    ) -> List[ARPoint]:
        """Get AR points around the user's location"""
        if types is None:
            types = ["historical", "navigation", "nature"]
            
        ar_points = []
        
        if "historical" in types:
            historical_points = await self._get_historical_points(
                user, latitude, longitude, radius
            )
            ar_points.extend(historical_points)
            
        if "navigation" in types:
            navigation_points = await self._get_navigation_points(
                user, latitude, longitude, radius
            )
            ar_points.extend(navigation_points)
            
        if "nature" in types:
            nature_points = await self._get_nature_points(
                user, latitude, longitude, radius
            )
            ar_points.extend(nature_points)
            
        # Sort by distance from user and limit to max points
        ar_points = self._filter_by_proximity(ar_points, latitude, longitude)
        return ar_points[:self.max_points]
    
    async def _get_historical_points(
        self, user: User, latitude: float, longitude: float, radius: float
    ) -> List[HistoricalARPoint]:
        """Get historical points for AR display"""
        historical_data = await self.historical_service.get_historical_context(
            latitude, longitude, radius
        )
        
        points = []
        for item in historical_data:
            point = HistoricalARPoint(
                id=f"hist_{item['id']}",
                title=item["title"],
                description=item["description"],
                latitude=item["latitude"],
                longitude=item["longitude"],
                type="historical",
                year=item["year"],
                historical_context=item["context"],
                image_url=item.get("image_url")
            )
            points.append(point)
            
        return points
    
    async def _get_navigation_points(
        self, user: User, latitude: float, longitude: float, radius: float
    ) -> List[NavigationARPoint]:
        """Get navigation points for AR display"""
        # Get current navigation route if any
        route_data = await self.location_service.get_active_route(user.id)
        if not route_data:
            return []
            
        # Extract upcoming maneuvers
        upcoming_maneuvers = route_data.get("upcoming_maneuvers", [])
        
        points = []
        for maneuver in upcoming_maneuvers:
            if self._is_in_radius(maneuver["latitude"], maneuver["longitude"], 
                                latitude, longitude, radius):
                point = NavigationARPoint(
                    id=f"nav_{maneuver['id']}",
                    title=maneuver["instruction"],
                    description=maneuver["detailed_instruction"],
                    latitude=maneuver["latitude"],
                    longitude=maneuver["longitude"],
                    type="navigation",
                    distance=maneuver["distance"],
                    eta=maneuver.get("eta"),
                    direction=maneuver["direction"]
                )
                points.append(point)
                
        return points
    
    async def _get_nature_points(
        self, user: User, latitude: float, longitude: float, radius: float
    ) -> List[NatureARPoint]:
        """Get nature points for AR display"""
        # This would typically connect to a nature database or service
        # For now, we'll generate some sample data
        nearby_features = await self.location_service.get_natural_features(
            latitude, longitude, radius
        )
        
        points = []
        for feature in nearby_features:
            point = NatureARPoint(
                id=f"nat_{feature['id']}",
                title=feature["name"],
                description=feature["description"],
                latitude=feature["latitude"],
                longitude=feature["longitude"],
                type="nature",
                species=feature.get("species"),
                ecosystem_info=feature.get("ecosystem_info"),
                conservation_status=feature.get("conservation_status")
            )
            points.append(point)
            
        return points
    
    def _filter_by_proximity(
        self, points: List[ARPoint], latitude: float, longitude: float
    ) -> List[ARPoint]:
        """Filter and sort AR points by proximity to user"""
        points_with_distance = []
        for point in points:
            distance = self._calculate_distance(
                latitude, longitude, point.latitude, point.longitude
            )
            points_with_distance.append((point, distance))
            
        # Sort by distance
        points_with_distance.sort(key=lambda x: x[1])
        
        # Remove points that are too close to each other
        filtered_points = []
        for point, _ in points_with_distance:
            if not self._is_too_close_to_existing_points(
                point, filtered_points
            ):
                filtered_points.append(point)
                
        return filtered_points
    
    def _is_too_close_to_existing_points(
        self, point: ARPoint, existing_points: List[ARPoint]
    ) -> bool:
        """Check if a point is too close to existing points"""
        for existing in existing_points:
            distance = self._calculate_distance(
                point.latitude, point.longitude, 
                existing.latitude, existing.longitude
            )
            if distance < self.point_distance_threshold:
                return True
        return False
    
    def _calculate_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points in meters"""
        # Simplified for brevity - would use haversine formula in production
        from math import radians, cos, sin, asin, sqrt
        
        # Convert decimal degrees to radians
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        
        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371000  # Radius of earth in meters
        
        return c * r
    
    def _is_in_radius(
        self, lat1: float, lon1: float, lat2: float, lon2: float, radius: float
    ) -> bool:
        """Check if a point is within a radius of another point"""
        distance = self._calculate_distance(lat1, lon1, lat2, lon2)
        return distance <= radius
    
    async def generate_historical_overlay(
        self, 
        user: User,
        latitude: float, 
        longitude: float,
        year: int = None
    ) -> Dict[str, Any]:
        """Generate a historical overlay for a location"""
        historical_data = await self.historical_service.get_historical_context(
            latitude, longitude, 200
        )
        
        if not historical_data:
            # Use AI to generate plausible historical context
            prompt = f"""
            Generate a brief historical description of the location at coordinates 
            {latitude}, {longitude} for the year {year if year else 'in the past'}.
            Include key events, architectural features, and daily life aspects.
            Format as a JSON object with:
            - title: Short title for this historical view
            - year: The year being depicted
            - description: 2-3 sentence overview
            - key_features: List of 3-5 notable elements visible in this area historically
            - daily_life: Brief description of what daily life was like here
            """
            
            response = await self.ai_client.generate_content(prompt)
            try:
                overlay_data = response.get("data", {})
                # Add coordinates
                overlay_data["latitude"] = latitude
                overlay_data["longitude"] = longitude
                return overlay_data
            except Exception as e:
                logger.error(f"Error parsing historical overlay response: {e}")
                return {
                    "title": "Historical View",
                    "year": year if year else 1900,
                    "description": "Historical data unavailable for this location.",
                    "key_features": [],
                    "daily_life": "Information not available.",
                    "latitude": latitude,
                    "longitude": longitude
                }
        else:
            # Process historical data into overlay format
            most_relevant = historical_data[0]
            
            if year:
                # Find the closest matching year if specified
                for item in historical_data:
                    if abs(item["year"] - year) < abs(most_relevant["year"] - year):
                        most_relevant = item
            
            return {
                "title": most_relevant["title"],
                "year": most_relevant["year"],
                "description": most_relevant["description"],
                "key_features": most_relevant.get("key_features", []),
                "daily_life": most_relevant.get("daily_life", "Information not available."),
                "image_url": most_relevant.get("image_url"),
                "latitude": most_relevant["latitude"],
                "longitude": most_relevant["longitude"]
            }