"""
Google Maps Traffic API Client for real-time traffic information
"""

import logging
from typing import Dict, List, Any, Optional
import httpx
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..core.config import settings
from ..core.circuit_breaker import get_maps_circuit_breaker, CircuitOpenError

logger = logging.getLogger(__name__)


@dataclass
class TrafficIncident:
    id: str
    type: str
    severity: int
    description: str
    location: Dict[str, float]
    start_time: datetime
    end_time: Optional[datetime]
    affected_roads: List[str]
    delay_minutes: int


class GoogleTrafficClient:
    """Client for Google Maps traffic data."""
    
    def __init__(self):
        self.api_key = settings.GOOGLE_MAPS_API_KEY
        self.base_url = "https://maps.googleapis.com/maps/api"
        self.session = None
    
    async def _get_session(self):
        """Get or create HTTP session."""
        if not self.session:
            self.session = httpx.AsyncClient()
        return self.session
    
    async def get_traffic_incidents(
        self,
        current_location: Dict[str, float],
        destination: Dict[str, float],
        route_polyline: str
    ) -> List[TrafficIncident]:
        """Get traffic incidents along the route."""
        
        if not self.api_key:
            logger.warning("Google Maps API key not configured")
            return []
        
        try:
            session = await self._get_session()
            
            # Use Google Directions API with traffic model
            url = f"{self.base_url}/directions/json"
            params = {
                "origin": f"{current_location['latitude']},{current_location['longitude']}",
                "destination": f"{destination['latitude']},{destination['longitude']}",
                "departure_time": "now",
                "traffic_model": "best_guess",
                "alternatives": "true",
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
                    incidents = self._extract_traffic_incidents(data)
                    return incidents
            except CircuitOpenError as e:
                logger.error(f"Google Maps circuit breaker is open: {e}")
                return []
            
            return []
            
        except Exception as e:
            logger.error(f"Error fetching traffic data: {e}")
            return []
    
    def _extract_traffic_incidents(self, directions_data: Dict[str, Any]) -> List[TrafficIncident]:
        """Extract traffic incidents from directions response."""
        
        incidents = []
        
        try:
            routes = directions_data.get("routes", [])
            
            for route_idx, route in enumerate(routes):
                legs = route.get("legs", [])
                
                for leg_idx, leg in enumerate(legs):
                    # Check for traffic delays
                    duration = leg.get("duration", {}).get("value", 0)
                    duration_in_traffic = leg.get("duration_in_traffic", {}).get("value", 0)
                    
                    if duration_in_traffic > duration * 1.2:  # 20% longer than normal
                        delay_minutes = (duration_in_traffic - duration) // 60
                        
                        # Create a traffic incident for significant delays
                        incident = TrafficIncident(
                            id=f"traffic_delay_{route_idx}_{leg_idx}",
                            type="traffic_congestion",
                            severity=min(3, max(1, delay_minutes // 10)),  # 1-3 based on delay
                            description=f"Heavy traffic causing {delay_minutes} minute delay",
                            location={
                                "latitude": leg.get("start_location", {}).get("lat", 0),
                                "longitude": leg.get("start_location", {}).get("lng", 0)
                            },
                            start_time=datetime.now() - timedelta(minutes=30),  # Estimate
                            end_time=None,
                            affected_roads=[route.get("summary", "Current Route")],
                            delay_minutes=delay_minutes
                        )
                        incidents.append(incident)
                    
                    # Check for warnings (construction, accidents, etc.)
                    warnings = route.get("warnings", [])
                    for warning in warnings:
                        incident = TrafficIncident(
                            id=f"warning_{route_idx}_{len(incidents)}",
                            type="warning",
                            severity=2,
                            description=warning,
                            location={
                                "latitude": leg.get("start_location", {}).get("lat", 0),
                                "longitude": leg.get("start_location", {}).get("lng", 0)
                            },
                            start_time=datetime.now(),
                            end_time=None,
                            affected_roads=[route.get("summary", "Current Route")],
                            delay_minutes=5  # Estimate for warnings
                        )
                        incidents.append(incident)
        
        except Exception as e:
            logger.error(f"Error extracting traffic incidents: {e}")
        
        return incidents
    
    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.aclose()
