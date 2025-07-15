"""
Google Places API Client for finding rest stops, gas stations, and amenities
"""

import logging
from typing import Dict, List, Any, Optional
import httpx
import asyncio
from dataclasses import dataclass

from ..core.config import settings
from ..core.circuit_breaker import get_maps_circuit_breaker, CircuitOpenError

logger = logging.getLogger(__name__)


@dataclass
class RestStop:
    id: str
    name: str
    location: Dict[str, float]
    distance_from_current: float
    distance_from_route: float
    facilities: List[str]
    rating: float
    estimated_duration: int
    arrival_time: str
    category: str
    amenities: Dict[str, bool]


class GooglePlacesClient:
    """Client for Google Places API integration."""
    
    def __init__(self):
        self.api_key = settings.GOOGLE_MAPS_API_KEY
        self.base_url = "https://maps.googleapis.com/maps/api/place"
        self.session = None
    
    async def _get_session(self):
        """Get or create HTTP session."""
        if not self.session:
            self.session = httpx.AsyncClient()
        return self.session
    
    async def search_rest_stops(
        self,
        current_location: Dict[str, float],
        destination: Dict[str, float],
        radius: int = 50000
    ) -> List[RestStop]:
        """Search for rest stops along the route."""
        
        if not self.api_key:
            logger.warning("Google Maps API key not configured")
            return []
        
        try:
            session = await self._get_session()
            
            # Search for rest areas, gas stations, and convenience stores
            search_types = ["rest_stop", "gas_station", "convenience_store"]
            all_places = []
            
            for place_type in search_types:
                url = f"{self.base_url}/nearbysearch/json"
                params = {
                    "location": f"{current_location['latitude']},{current_location['longitude']}",
                    "radius": radius,
                    "type": place_type,
                    "key": self.api_key
                }
                
                # Use circuit breaker for Google Maps API calls
                maps_circuit_breaker = get_maps_circuit_breaker()
                try:
                    response = await maps_circuit_breaker.call_async(
                        session.get,
                        url,
                        params=params
                    )
                    if response.status_code == 200:
                        data = response.json()
                        all_places.extend(data.get("results", []))
                except CircuitOpenError as e:
                    logger.error(f"Google Maps circuit breaker is open: {e}")
                    # Continue with partial results if some calls succeed
            
            # Convert to RestStop objects
            rest_stops = []
            for place in all_places[:10]:  # Limit to 10 results
                rest_stop = self._convert_place_to_rest_stop(place, current_location)
                if rest_stop:
                    rest_stops.append(rest_stop)
            
            return rest_stops
            
        except Exception as e:
            logger.error(f"Error searching rest stops: {e}")
            return []
    
    def _convert_place_to_rest_stop(
        self, 
        place: Dict[str, Any], 
        current_location: Dict[str, float]
    ) -> Optional[RestStop]:
        """Convert Google Places result to RestStop object."""
        
        try:
            location = place.get("geometry", {}).get("location", {})
            if not location:
                return None
            
            # Calculate rough distance (simplified)
            lat_diff = abs(location["lat"] - current_location["latitude"])
            lng_diff = abs(location["lng"] - current_location["longitude"])
            distance_km = ((lat_diff ** 2 + lng_diff ** 2) ** 0.5) * 111  # Rough conversion
            
            # Determine facilities based on place types
            types = place.get("types", [])
            facilities = []
            amenities = {"restrooms": False, "food": False, "fuel": False}
            
            if "gas_station" in types:
                facilities.extend(["fuel", "restrooms"])
                amenities["fuel"] = True
                amenities["restrooms"] = True
            
            if "convenience_store" in types:
                facilities.extend(["food", "restrooms"])
                amenities["food"] = True
                amenities["restrooms"] = True
            
            if "rest_stop" in types:
                facilities.extend(["restrooms", "picnic_area"])
                amenities["restrooms"] = True
            
            return RestStop(
                id=place.get("place_id", "unknown"),
                name=place.get("name", "Rest Stop"),
                location={"latitude": location["lat"], "longitude": location["lng"]},
                distance_from_current=distance_km * 1000,  # Convert to meters
                distance_from_route=0,  # Would need route calculation
                facilities=list(set(facilities)),  # Remove duplicates
                rating=place.get("rating", 0.0),
                estimated_duration=15,  # Default 15 minutes
                arrival_time="",  # Would need route calculation
                category="rest_area",
                amenities=amenities
            )
            
        except Exception as e:
            logger.error(f"Error converting place to rest stop: {e}")
            return None
    
    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.aclose()
