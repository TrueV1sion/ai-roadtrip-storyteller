from typing import List, Dict, Any, Optional, Union
import logging
import json
from datetime import datetime, timedelta
import math
from pydantic import BaseModel, Field

from ..core.config import settings
from ..core.enhanced_ai_client import EnhancedAIClient
from ..models.user import User

logger = logging.getLogger(__name__)

class RestStop(BaseModel):
    """Model for a rest stop recommendation"""
    id: str
    name: str
    location: Dict[str, float]  # latitude, longitude
    distance_from_current: float  # in meters
    distance_from_route: float  # in meters
    facilities: List[str]
    rating: Optional[float] = None
    estimated_duration: int  # in minutes
    arrival_time: datetime
    category: str  # "rest_area", "service_station", "restaurant", etc.
    amenities: Dict[str, bool] = Field(default_factory=dict)
    
class FuelStation(BaseModel):
    """Model for a fuel station"""
    id: str
    name: str
    location: Dict[str, float]
    distance_from_current: float  # in meters
    distance_from_route: float  # in meters
    fuel_types: List[str]
    prices: Optional[Dict[str, float]] = None
    brand: Optional[str] = None
    rating: Optional[float] = None
    amenities: Dict[str, bool] = Field(default_factory=dict)
    busy_level: Optional[str] = None  # "low", "medium", "high"

class TrafficIncident(BaseModel):
    """Model for a traffic incident"""
    id: str
    type: str  # "accident", "construction", "road_closure", etc.
    severity: int  # 1-5, with 5 being most severe
    description: str
    location: Dict[str, float]
    start_time: datetime
    end_time: Optional[datetime] = None
    affected_roads: List[str]
    delay_minutes: Optional[int] = None

class RouteSegment(BaseModel):
    """Model for a segment of a route with traffic info"""
    segment_id: str
    start_location: Dict[str, float]
    end_location: Dict[str, float]
    distance: float  # in meters
    normal_duration: int  # in seconds
    current_duration: int  # in seconds with traffic
    traffic_level: str  # "low", "moderate", "heavy", "severe"
    speed_limit: Optional[float] = None  # km/h
    incidents: List[TrafficIncident] = Field(default_factory=list)

class DrivingStatus(BaseModel):
    """Model for the current driving status"""
    driving_time: int  # in minutes since last substantial break
    distance_covered: float  # in km since start
    fuel_level: float  # percentage (0-100)
    estimated_range: float  # in km
    rest_break_due: bool
    next_rest_recommended_in: Optional[int] = None  # minutes
    alerts: List[str] = Field(default_factory=list)
    driver_fatigue_level: str  # "low", "moderate", "high"

class DrivingAssistant:
    """Service for driving assistance features"""
    
    def __init__(self, ai_client: EnhancedAIClient = None):
        self.ai_client = ai_client
        self.rest_interval_minutes = 120  # Default rest interval (2 hours)
        self.low_fuel_threshold = 20.0  # Percentage to trigger low fuel warning
        logger.info("Driving Assistant service initialized")
    
    async def get_rest_breaks(
        self,
        user: User,
        current_location: Dict[str, float],
        destination: Dict[str, float],
        route_polyline: str,
        driving_time_minutes: int,
        vehicle_type: str = "car",
        preferences: Dict[str, Any] = None
    ) -> List[RestStop]:
        """Get recommended rest breaks based on route and driving time"""
        
        if preferences is None:
            preferences = {}
        
        # Determine if rest break is needed based on driving time
        rest_needed = driving_time_minutes >= self.rest_interval_minutes
        
        if not rest_needed:
            logger.info(f"No rest break needed yet. Driving time: {driving_time_minutes} minutes")
            return []
        
        # Calculate approximately how many kilometers have been driven
        # Assuming average speed of 80 km/h
        average_speed_kmh = 80
        distance_covered_km = (driving_time_minutes / 60) * average_speed_kmh
        
        # Calculate recommended rest duration based on driving time
        if driving_time_minutes < 180:  # Less than 3 hours
            recommended_duration = 15  # 15 minutes
        elif driving_time_minutes < 360:  # 3-6 hours
            recommended_duration = 30  # 30 minutes
        else:  # More than 6 hours
            recommended_duration = 45  # 45 minutes
        
        # Adjust for preferences
        if preferences.get("rest_frequency") == "frequent":
            recommended_duration += 10
        elif preferences.get("rest_frequency") == "minimal":
            recommended_duration -= 5
        
        # Enforce minimum duration
        recommended_duration = max(recommended_duration, 10)
        
        # Determine facilities preference
        preferred_facilities = preferences.get("preferred_facilities", [])
        if not preferred_facilities:
            preferred_facilities = ["restrooms", "food"]
        
        # Calculate arrival time at potential rest stops
        # Simple estimate: current time + a fraction of remaining driving time
        now = datetime.now()
        
        # Search for actual rest stops using Google Places API
        try:
            from ..integrations.google_places_client import GooglePlacesClient
            places_client = GooglePlacesClient()
            
            # Search for rest stops along the route
            rest_stops = await places_client.search_rest_stops(
                current_location=current_location,
                destination=destination,
                radius=50000  # 50km radius
            )
            
            if not rest_stops:
                # Fallback to generic rest area if no results
                rest_stops = [
                    RestStop(
                        id="fallback_rest1",
                        name="Highway Rest Area",
                        location={"latitude": current_location["latitude"] + 0.02, "longitude": current_location["longitude"] + 0.02},
                        distance_from_current=2000,
                        distance_from_route=100,
                        facilities=["restrooms", "picnic_area"],
                        rating=4.0,
                        estimated_duration=recommended_duration,
                        arrival_time=now + timedelta(minutes=15),
                        category="rest_area",
                        amenities={
                            "restrooms": True,
                            "food": False,
                            "fuel": False,
                            "wifi": False,
                            "charging": False
                        }
                    )
                ]
            
            await places_client.close()
            
        except Exception as e:
            logger.error(f"Failed to fetch real rest stop data: {e}")
            # Fallback to sample data if API fails
            rest_stops = [
                RestStop(
                    id="fallback_rest1",
                    name="Highway Rest Area",
                    location={"latitude": current_location["latitude"] + 0.02, "longitude": current_location["longitude"] + 0.02},
                    distance_from_current=2000,
                    distance_from_route=100,
                    facilities=["restrooms", "picnic_area"],
                    rating=4.0,
                    estimated_duration=recommended_duration,
                    arrival_time=now + timedelta(minutes=15),
                    category="rest_area",
                    amenities={
                        "restrooms": True,
                        "food": False,
                    "fuel": False,
                    "wifi": False,
                    "charging": False
                }
            ),
            RestStop(
                id="rest2",
                name="Roadside Cafe",
                location={"latitude": current_location["latitude"] + 0.03, "longitude": current_location["longitude"] + 0.03},
                distance_from_current=3500,  # 3.5 km
                distance_from_route=200,  # 200 meters
                facilities=["restrooms", "restaurant", "wifi"],
                rating=4.2,
                estimated_duration=recommended_duration,
                arrival_time=now + timedelta(minutes=25),
                category="restaurant",
                amenities={
                    "restrooms": True,
                    "food": True,
                    "fuel": False,
                    "wifi": True,
                    "charging": False
                }
            ),
            RestStop(
                id="rest3",
                name="Mountain View Service Station",
                location={"latitude": current_location["latitude"] + 0.04, "longitude": current_location["longitude"] + 0.04},
                distance_from_current=5000,  # 5 km
                distance_from_route=50,  # 50 meters
                facilities=["restrooms", "food", "fuel", "convenience_store"],
                rating=3.8,
                estimated_duration=recommended_duration,
                arrival_time=now + timedelta(minutes=35),
                category="service_station",
                amenities={
                    "restrooms": True,
                    "food": True,
                    "fuel": True,
                    "wifi": False,
                    "charging": True
                }
            )
        ]
        
        # Filter and rank rest stops based on preferences
        filtered_stops = []
        for stop in rest_stops:
            # Check if the stop has at least one of the preferred facilities
            has_preferred_facility = any(facility in preferred_facilities for facility in stop.facilities)
            
            if has_preferred_facility:
                # Calculate a score based on preferences
                score = 0
                
                # Distance from route (closer is better)
                score -= stop.distance_from_route / 100
                
                # Rating (higher is better)
                if stop.rating:
                    score += stop.rating * 10
                
                # Preferred facilities
                for facility in preferred_facilities:
                    if facility in stop.facilities:
                        score += 5
                
                # Preferred categories
                preferred_categories = preferences.get("preferred_categories", [])
                if stop.category in preferred_categories:
                    score += 10
                
                # Store the score for sorting
                stop_dict = stop.dict()
                stop_dict["score"] = score
                filtered_stops.append((stop, score))
        
        # Sort by score (descending)
        filtered_stops.sort(key=lambda x: x[1], reverse=True)
        
        # Return the top stops
        return [stop for stop, _ in filtered_stops[:3]]
    
    async def get_fuel_stations(
        self,
        current_location: Dict[str, float],
        route_polyline: str,
        fuel_level: float,
        fuel_type: str = "regular",
        range_km: Optional[float] = None,
        preferences: Dict[str, Any] = None
    ) -> List[FuelStation]:
        """Get nearby fuel stations, prioritizing if fuel is low"""
        
        if preferences is None:
            preferences = {}
        
        # Determine if fuel warning is needed
        fuel_warning = fuel_level <= self.low_fuel_threshold
        
        estimated_range = range_km if range_km is not None else fuel_level * 0.8  # Simple estimation
        
        # If fuel is not low and not explicitly requested, return empty list
        if not fuel_warning and not preferences.get("show_fuel_stations", False):
            logger.info(f"No fuel warning needed. Current level: {fuel_level}%")
            return []
        
        # TODO: Replace with actual fuel station data from a service or API
        # For now, generate sample fuel stations
        fuel_stations = [
            FuelStation(
                id="fuel1",
                name="QuickFuel",
                location={"latitude": current_location["latitude"] + 0.01, "longitude": current_location["longitude"] + 0.01},
                distance_from_current=1500,  # 1.5 km
                distance_from_route=50,  # 50 meters
                fuel_types=["regular", "premium", "diesel"],
                prices={"regular": 3.45, "premium": 3.85, "diesel": 3.65},
                brand="QuickFuel",
                rating=4.1,
                amenities={
                    "restrooms": True,
                    "food": True,
                    "convenience_store": True,
                    "car_wash": True
                },
                busy_level="low"
            ),
            FuelStation(
                id="fuel2",
                name="EcoGas",
                location={"latitude": current_location["latitude"] + 0.015, "longitude": current_location["longitude"] + 0.015},
                distance_from_current=2000,  # 2 km
                distance_from_route=150,  # 150 meters
                fuel_types=["regular", "premium", "diesel", "electric"],
                prices={"regular": 3.40, "premium": 3.80, "diesel": 3.60},
                brand="EcoGas",
                rating=4.3,
                amenities={
                    "restrooms": True,
                    "food": True,
                    "convenience_store": True,
                    "car_wash": False,
                    "ev_charging": True
                },
                busy_level="medium"
            ),
            FuelStation(
                id="fuel3",
                name="Value Petroleum",
                location={"latitude": current_location["latitude"] + 0.02, "longitude": current_location["longitude"] + 0.02},
                distance_from_current=2500,  # 2.5 km
                distance_from_route=250,  # 250 meters
                fuel_types=["regular", "diesel"],
                prices={"regular": 3.35, "diesel": 3.55},
                brand="Value Petroleum",
                rating=3.8,
                amenities={
                    "restrooms": True,
                    "food": False,
                    "convenience_store": True,
                    "car_wash": False
                },
                busy_level="high"
            )
        ]
        
        # Filter and rank fuel stations based on preferences and needed fuel type
        filtered_stations = []
        for station in fuel_stations:
            # Check if the station has the needed fuel type
            if fuel_type in station.fuel_types:
                # Calculate a score
                score = 0
                
                # Distance from route (closer is better)
                score -= station.distance_from_route / 100
                
                # Price (lower is better)
                if station.prices and fuel_type in station.prices:
                    # Lower price is better, normalize around $3.50
                    price_score = 10 - ((station.prices[fuel_type] - 3.00) * 20)
                    score += price_score
                
                # Rating (higher is better)
                if station.rating:
                    score += station.rating * 5
                
                # Preferred brand
                preferred_brand = preferences.get("preferred_fuel_brand")
                if preferred_brand and station.brand == preferred_brand:
                    score += 15
                
                # Busy level
                if station.busy_level == "low":
                    score += 5
                elif station.busy_level == "high":
                    score -= 5
                
                # Additional amenities
                if preferences.get("want_food") and station.amenities.get("food", False):
                    score += 8
                if preferences.get("want_restrooms") and station.amenities.get("restrooms", False):
                    score += 8
                if preferences.get("want_car_wash") and station.amenities.get("car_wash", False):
                    score += 5
                
                filtered_stations.append((station, score))
        
        # Sort by score (descending)
        filtered_stations.sort(key=lambda x: x[1], reverse=True)
        
        # If fuel warning, return all matches, otherwise limit to top 2
        if fuel_warning:
            return [station for station, _ in filtered_stations]
        else:
            return [station for station, _ in filtered_stations[:2]]
    
    async def get_traffic_info(
        self,
        route_id: str,
        route_polyline: str,
        current_location: Dict[str, float],
        destination: Dict[str, float]
    ) -> Dict[str, Any]:
        """Get traffic information for the current route"""
        
        # Get real traffic data from Google Maps API
        try:
            from ..integrations.google_traffic_client import GoogleTrafficClient
            traffic_client = GoogleTrafficClient()
            
            incidents = await traffic_client.get_traffic_incidents(
                current_location=current_location,
                destination=destination,
                route_polyline=route_polyline
            )
            
            if not incidents:
                # No traffic incidents found
                incidents = []
            
            await traffic_client.close()
            
        except Exception as e:
            logger.error(f"Failed to fetch real traffic data: {e}")
            # Fallback to sample data if API fails
            now = datetime.now()
            incidents = [
                TrafficIncident(
                    id="fallback_incident1",
                    type="unknown",
                    severity=1,
                    description="Unable to fetch current traffic data",
                    location={"latitude": current_location["latitude"], "longitude": current_location["longitude"]},
                    start_time=now,
                    end_time=None,
                    affected_roads=["Current Route"],
                    delay_minutes=0
                )
            ]
        
        # Sample route segments with traffic
        segments = [
            RouteSegment(
                segment_id="segment1",
                start_location={"latitude": current_location["latitude"], "longitude": current_location["longitude"]},
                end_location={"latitude": current_location["latitude"] + 0.05, "longitude": current_location["longitude"] + 0.05},
                distance=5000,  # 5 km
                normal_duration=300,  # 5 minutes
                current_duration=450,  # 7.5 minutes with traffic
                traffic_level="moderate",
                speed_limit=100,  # 100 km/h
                incidents=[]
            ),
            RouteSegment(
                segment_id="segment2",
                start_location={"latitude": current_location["latitude"] + 0.05, "longitude": current_location["longitude"] + 0.05},
                end_location={"latitude": current_location["latitude"] + 0.1, "longitude": current_location["longitude"] + 0.1},
                distance=6000,  # 6 km
                normal_duration=360,  # 6 minutes
                current_duration=720,  # 12 minutes with traffic
                traffic_level="heavy",
                speed_limit=100,  # 100 km/h
                incidents=[incidents[0]]  # First incident affects this segment
            ),
            RouteSegment(
                segment_id="segment3",
                start_location={"latitude": current_location["latitude"] + 0.1, "longitude": current_location["longitude"] + 0.1},
                end_location={"latitude": current_location["latitude"] + 0.15, "longitude": current_location["longitude"] + 0.15},
                distance=5500,  # 5.5 km
                normal_duration=330,  # 5.5 minutes
                current_duration=480,  # 8 minutes with traffic
                traffic_level="moderate",
                speed_limit=100,  # 100 km/h
                incidents=[incidents[1]]  # Second incident affects this segment
            ),
            RouteSegment(
                segment_id="segment4",
                start_location={"latitude": current_location["latitude"] + 0.15, "longitude": current_location["longitude"] + 0.15},
                end_location={"latitude": destination["latitude"], "longitude": destination["longitude"]},
                distance=7000,  # 7 km
                normal_duration=420,  # 7 minutes
                current_duration=450,  # 7.5 minutes with traffic
                traffic_level="low",
                speed_limit=100,  # 100 km/h
                incidents=[]
            )
        ]
        
        # Calculate overall metrics
        total_distance = sum(segment.distance for segment in segments)
        total_normal_duration = sum(segment.normal_duration for segment in segments)
        total_current_duration = sum(segment.current_duration for segment in segments)
        
        delay = total_current_duration - total_normal_duration
        delay_percentage = (delay / total_normal_duration) * 100 if total_normal_duration > 0 else 0
        
        # Determine overall traffic status
        if delay_percentage < 10:
            traffic_status = "minimal"
        elif delay_percentage < 25:
            traffic_status = "light"
        elif delay_percentage < 50:
            traffic_status = "moderate"
        elif delay_percentage < 100:
            traffic_status = "heavy"
        else:
            traffic_status = "severe"
        
        # Prepare alternate routes if traffic is bad
        alternate_routes = []
        if traffic_status in ["heavy", "severe"]:
            # In a real implementation, this would come from a routing service
            alternate_routes = [
                {
                    "route_id": "alt1",
                    "description": "Alternate route via side streets",
                    "distance": total_distance * 1.1,  # 10% longer
                    "duration": total_normal_duration * 0.9,  # 10% faster than current route with traffic
                    "traffic_level": "light"
                },
                {
                    "route_id": "alt2",
                    "description": "Scenic route",
                    "distance": total_distance * 1.2,  # 20% longer
                    "duration": total_normal_duration * 0.85,  # 15% faster than current route with traffic
                    "traffic_level": "minimal"
                }
            ]
        
        return {
            "route_id": route_id,
            "overall_traffic": traffic_status,
            "total_distance": total_distance,
            "normal_duration": total_normal_duration,
            "current_duration": total_current_duration,
            "delay_seconds": delay,
            "delay_percentage": delay_percentage,
            "incidents": [incident.dict() for incident in incidents],
            "segments": [segment.dict() for segment in segments],
            "alternate_routes": alternate_routes
        }
    
    async def get_driving_status(
        self,
        user: User,
        driving_time_minutes: int,
        distance_covered: float,
        fuel_level: float,
        estimated_range: float,
        last_break_time: datetime = None
    ) -> DrivingStatus:
        """Get the current driving status and recommendations"""
        
        # Determine if a rest break is needed
        if last_break_time is None:
            last_break_time = datetime.now() - timedelta(minutes=driving_time_minutes)
        
        minutes_since_break = (datetime.now() - last_break_time).total_seconds() / 60
        rest_break_due = minutes_since_break >= self.rest_interval_minutes
        
        # Calculate when the next rest break is recommended
        next_rest_recommended_in = max(0, self.rest_interval_minutes - minutes_since_break)
        
        # Determine driver fatigue level
        if minutes_since_break < self.rest_interval_minutes * 0.5:
            fatigue_level = "low"
        elif minutes_since_break < self.rest_interval_minutes * 0.8:
            fatigue_level = "moderate"
        else:
            fatigue_level = "high"
        
        # Generate alerts
        alerts = []
        
        if rest_break_due:
            alerts.append("Rest break recommended for driver safety")
        
        if fuel_level <= self.low_fuel_threshold:
            range_message = f" Estimated range: {estimated_range:.1f} km"
            alerts.append(f"Low fuel warning ({fuel_level:.1f}%).{range_message}")
        
        # Create the driving status
        status = DrivingStatus(
            driving_time=driving_time_minutes,
            distance_covered=distance_covered,
            fuel_level=fuel_level,
            estimated_range=estimated_range,
            rest_break_due=rest_break_due,
            next_rest_recommended_in=int(next_rest_recommended_in) if not rest_break_due else 0,
            alerts=alerts,
            driver_fatigue_level=fatigue_level
        )
        
        return status
    
    def estimate_fuel_efficiency(
        self,
        vehicle_type: str,
        speed: float,
        elevation_change: float,
        has_climate_control: bool
    ) -> float:
        """Estimate fuel efficiency based on driving conditions"""
        
        # Base efficiency values in km/L
        base_efficiency = {
            "sedan": 12.0,
            "suv": 9.0,
            "truck": 7.0,
            "hybrid": 18.0,
            "electric": 25.0,  # For electric, this is actually kWh/100km converted to a comparable number
        }
        
        if vehicle_type not in base_efficiency:
            vehicle_type = "sedan"  # Default
        
        efficiency = base_efficiency[vehicle_type]
        
        # Speed adjustment - most efficient around 80-90 km/h
        if speed < 60:
            efficiency *= 0.85  # Less efficient at low speeds
        elif speed > 100:
            # Efficiency drops as speed increases above 100 km/h
            efficiency *= 0.95 - ((speed - 100) * 0.005)
        
        # Elevation adjustment
        if elevation_change > 0:  # Driving uphill
            efficiency *= max(0.7, 1 - (elevation_change / 1000))  # Max 30% reduction for steep hills
        elif elevation_change < 0:  # Driving downhill
            efficiency *= min(1.2, 1 + (abs(elevation_change) / 2000))  # Max 20% increase for downhill
        
        # Climate control
        if has_climate_control:
            efficiency *= 0.9  # 10% reduction when using climate control
        
        return efficiency