"""
Route Simulator for AI Road Trip Storyteller
Generates realistic routes and journey scenarios
"""

import random
import math
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta, time
from dataclasses import dataclass, field
from enum import Enum
import json
import requests
from geopy.distance import geodesic


class RouteType(Enum):
    HIGHWAY = "highway"
    SCENIC = "scenic"
    COASTAL = "coastal"
    MOUNTAIN = "mountain"
    DESERT = "desert"
    RURAL = "rural"
    URBAN = "urban"
    HISTORIC = "historic"


class PointOfInterest:
    """Represents a point of interest along a route"""
    
    def __init__(self, name: str, lat: float, lng: float, category: str, 
                 description: str, visit_duration: int = 30):
        self.name = name
        self.lat = lat
        self.lng = lng
        self.category = category
        self.description = description
        self.visit_duration = visit_duration  # minutes
        
        
@dataclass
class RouteSegment:
    """Represents a segment of a route"""
    start_point: Dict[str, Any]
    end_point: Dict[str, Any]
    distance: float  # km
    duration: int  # minutes
    route_type: RouteType
    points_of_interest: List[PointOfInterest] = field(default_factory=list)
    scenic_rating: float = 0.5  # 0-1
    difficulty: float = 0.5  # 0-1
    elevation_change: int = 0  # meters
    

@dataclass
class SimulatedRoute:
    """Complete simulated route"""
    id: str
    name: str
    origin: Dict[str, Any]
    destination: Dict[str, Any]
    segments: List[RouteSegment]
    total_distance: float  # km
    total_duration: int  # minutes
    route_types: List[RouteType]
    waypoints: List[Dict[str, Any]]
    points_of_interest: List[PointOfInterest]
    best_travel_time: str
    seasonal_considerations: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class RouteSimulator:
    """Generates realistic routes with various characteristics"""
    
    # Popular route templates
    ROUTE_TEMPLATES = {
        "pacific_coast_highway": {
            "name": "Pacific Coast Highway",
            "origin": {"lat": 37.7749, "lng": -122.4194, "name": "San Francisco, CA"},
            "destination": {"lat": 34.0522, "lng": -118.2437, "name": "Los Angeles, CA"},
            "waypoints": [
                {"lat": 36.5816, "lng": -121.8988, "name": "Monterey, CA"},
                {"lat": 36.2704, "lng": -121.8081, "name": "Big Sur, CA"},
                {"lat": 35.2828, "lng": -120.6596, "name": "San Luis Obispo, CA"},
                {"lat": 34.4208, "lng": -119.6982, "name": "Santa Barbara, CA"}
            ],
            "route_type": RouteType.COASTAL,
            "scenic_rating": 0.95
        },
        "route_66": {
            "name": "Historic Route 66",
            "origin": {"lat": 41.8781, "lng": -87.6298, "name": "Chicago, IL"},
            "destination": {"lat": 34.0522, "lng": -118.2437, "name": "Los Angeles, CA"},
            "waypoints": [
                {"lat": 38.6270, "lng": -90.1994, "name": "St. Louis, MO"},
                {"lat": 35.4676, "lng": -97.5164, "name": "Oklahoma City, OK"},
                {"lat": 35.0844, "lng": -106.6504, "name": "Albuquerque, NM"},
                {"lat": 35.1983, "lng": -114.0530, "name": "Kingman, AZ"}
            ],
            "route_type": RouteType.HISTORIC,
            "scenic_rating": 0.7
        },
        "blue_ridge_parkway": {
            "name": "Blue Ridge Parkway",
            "origin": {"lat": 36.1627, "lng": -81.6748, "name": "Boone, NC"},
            "destination": {"lat": 38.0293, "lng": -78.4767, "name": "Charlottesville, VA"},
            "waypoints": [
                {"lat": 35.7596, "lng": -82.2651, "name": "Asheville, NC"},
                {"lat": 37.2296, "lng": -80.4139, "name": "Roanoke, VA"}
            ],
            "route_type": RouteType.MOUNTAIN,
            "scenic_rating": 0.9
        },
        "florida_keys": {
            "name": "Florida Keys Scenic Highway",
            "origin": {"lat": 25.7617, "lng": -80.1918, "name": "Miami, FL"},
            "destination": {"lat": 24.5551, "lng": -81.7800, "name": "Key West, FL"},
            "waypoints": [
                {"lat": 25.0343, "lng": -80.4549, "name": "Key Largo, FL"},
                {"lat": 24.7829, "lng": -80.9101, "name": "Marathon, FL"}
            ],
            "route_type": RouteType.COASTAL,
            "scenic_rating": 0.85
        },
        "great_river_road": {
            "name": "Great River Road",
            "origin": {"lat": 44.9778, "lng": -93.2650, "name": "Minneapolis, MN"},
            "destination": {"lat": 38.6270, "lng": -90.1994, "name": "St. Louis, MO"},
            "waypoints": [
                {"lat": 43.0389, "lng": -91.1551, "name": "La Crosse, WI"},
                {"lat": 41.5868, "lng": -90.5958, "name": "Davenport, IA"}
            ],
            "route_type": RouteType.SCENIC,
            "scenic_rating": 0.75
        },
        "desert_southwest": {
            "name": "Desert Southwest Circuit",
            "origin": {"lat": 36.1699, "lng": -115.1398, "name": "Las Vegas, NV"},
            "destination": {"lat": 33.4484, "lng": -112.0740, "name": "Phoenix, AZ"},
            "waypoints": [
                {"lat": 36.1069, "lng": -112.1129, "name": "Grand Canyon South Rim, AZ"},
                {"lat": 35.0844, "lng": -114.5534, "name": "Flagstaff, AZ"},
                {"lat": 34.8697, "lng": -111.7610, "name": "Sedona, AZ"}
            ],
            "route_type": RouteType.DESERT,
            "scenic_rating": 0.88
        }
    }
    
    # Points of Interest database
    POI_DATABASE = {
        "natural": [
            {"name": "Yosemite Falls", "lat": 37.7569, "lng": -119.5966, "description": "Spectacular waterfall"},
            {"name": "Redwood National Park", "lat": 41.2132, "lng": -124.0046, "description": "Ancient giant trees"},
            {"name": "Grand Canyon Skywalk", "lat": 36.0120, "lng": -113.8107, "description": "Glass bridge viewpoint"},
            {"name": "Yellowstone Geysers", "lat": 44.4605, "lng": -110.8281, "description": "Geothermal wonders"},
            {"name": "Niagara Falls", "lat": 43.0962, "lng": -79.0377, "description": "Iconic waterfalls"},
            {"name": "Rocky Mountain National Park", "lat": 40.3428, "lng": -105.6836, "description": "Alpine wilderness"}
        ],
        "historical": [
            {"name": "Mount Rushmore", "lat": 43.8791, "lng": -103.4591, "description": "Presidential monument"},
            {"name": "Gettysburg Battlefield", "lat": 39.8157, "lng": -77.2309, "description": "Civil War site"},
            {"name": "Independence Hall", "lat": 39.9496, "lng": -75.1503, "description": "Birthplace of America"},
            {"name": "Alamo Mission", "lat": 29.4260, "lng": -98.4861, "description": "Historic battle site"},
            {"name": "Liberty Bell", "lat": 39.9496, "lng": -75.1503, "description": "Symbol of freedom"}
        ],
        "cultural": [
            {"name": "French Quarter", "lat": 29.9584, "lng": -90.0644, "description": "Historic New Orleans"},
            {"name": "Nashville Music Row", "lat": 36.1510, "lng": -86.7915, "description": "Country music capital"},
            {"name": "Hollywood Sign", "lat": 34.1341, "lng": -118.3215, "description": "Entertainment icon"},
            {"name": "Space Needle", "lat": 47.6205, "lng": -122.3493, "description": "Seattle landmark"},
            {"name": "Gateway Arch", "lat": 38.6247, "lng": -90.1848, "description": "St. Louis monument"}
        ],
        "quirky": [
            {"name": "Cadillac Ranch", "lat": 35.1872, "lng": -101.9873, "description": "Buried cars art"},
            {"name": "World's Largest Ball of Twine", "lat": 39.5089, "lng": -98.9196, "description": "Roadside oddity"},
            {"name": "Corn Palace", "lat": 43.7194, "lng": -98.0298, "description": "Decorated with corn"},
            {"name": "Carhenge", "lat": 42.1420, "lng": -102.8585, "description": "Car sculpture"},
            {"name": "Mystery Spot", "lat": 37.0176, "lng": -122.0024, "description": "Gravity anomaly"}
        ],
        "dining": [
            {"name": "Bern's Steak House", "lat": 27.9378, "lng": -82.4690, "description": "Famous steakhouse"},
            {"name": "Katz's Delicatessen", "lat": 40.7223, "lng": -73.9873, "description": "NYC institution"},
            {"name": "Lou Malnati's", "lat": 41.8904, "lng": -87.6332, "description": "Chicago deep dish"},
            {"name": "Franklin BBQ", "lat": 30.2702, "lng": -97.7314, "description": "Texas BBQ legend"},
            {"name": "In-N-Out Burger", "lat": 34.0522, "lng": -118.2437, "description": "California classic"}
        ]
    }
    
    def __init__(self):
        self.route_counter = 0
        
    def generate_route(self, origin: Optional[Dict] = None, destination: Optional[Dict] = None,
                      route_preferences: Optional[Dict] = None) -> SimulatedRoute:
        """Generate a complete simulated route"""
        self.route_counter += 1
        
        # Use template or custom route
        if origin is None or destination is None:
            template = random.choice(list(self.ROUTE_TEMPLATES.values()))
            origin = template["origin"]
            destination = template["destination"]
            waypoints = template.get("waypoints", [])
            route_type = template["route_type"]
            scenic_rating = template["scenic_rating"]
            name = template["name"]
        else:
            waypoints = self._generate_waypoints(origin, destination, route_preferences)
            route_type = self._determine_route_type(origin, destination, route_preferences)
            scenic_rating = self._calculate_scenic_rating(route_type, waypoints)
            name = f"{origin['name']} to {destination['name']}"
            
        # Generate route segments
        segments = self._generate_segments(origin, destination, waypoints, route_type)
        
        # Add points of interest
        pois = self._generate_points_of_interest(segments, route_preferences)
        
        # Calculate totals
        total_distance = sum(segment.distance for segment in segments)
        total_duration = sum(segment.duration for segment in segments)
        
        # Determine best travel time
        best_time = self._determine_best_travel_time(route_type, origin, destination)
        
        # Get seasonal considerations
        seasonal = self._get_seasonal_considerations(route_type, origin, destination)
        
        route = SimulatedRoute(
            id=f"route_{self.route_counter}_{int(datetime.now().timestamp())}",
            name=name,
            origin=origin,
            destination=destination,
            segments=segments,
            total_distance=total_distance,
            total_duration=total_duration,
            route_types=list(set(segment.route_type for segment in segments)),
            waypoints=waypoints,
            points_of_interest=pois,
            best_travel_time=best_time,
            seasonal_considerations=seasonal,
            metadata={
                "generated_at": datetime.now().isoformat(),
                "scenic_rating": scenic_rating,
                "difficulty": self._calculate_difficulty(segments),
                "family_friendly": self._is_family_friendly(segments, pois)
            }
        )
        
        return route
        
    def _generate_waypoints(self, origin: Dict, destination: Dict, 
                           preferences: Optional[Dict]) -> List[Dict]:
        """Generate waypoints between origin and destination"""
        # Calculate direct distance
        distance = geodesic(
            (origin["lat"], origin["lng"]),
            (destination["lat"], destination["lng"])
        ).kilometers
        
        # Determine number of waypoints based on distance
        if distance < 200:
            num_waypoints = random.randint(0, 2)
        elif distance < 500:
            num_waypoints = random.randint(1, 3)
        elif distance < 1000:
            num_waypoints = random.randint(2, 4)
        else:
            num_waypoints = random.randint(3, 6)
            
        waypoints = []
        
        # Generate waypoints along the route
        for i in range(num_waypoints):
            # Interpolate position
            ratio = (i + 1) / (num_waypoints + 1)
            
            # Add some randomness for more interesting routes
            lat_offset = random.uniform(-0.5, 0.5)
            lng_offset = random.uniform(-0.5, 0.5)
            
            waypoint_lat = origin["lat"] + (destination["lat"] - origin["lat"]) * ratio + lat_offset
            waypoint_lng = origin["lng"] + (destination["lng"] - origin["lng"]) * ratio + lng_offset
            
            # Find nearest city/town (simplified)
            waypoint = {
                "lat": waypoint_lat,
                "lng": waypoint_lng,
                "name": f"Waypoint {i+1}"
            }
            
            waypoints.append(waypoint)
            
        return waypoints
        
    def _determine_route_type(self, origin: Dict, destination: Dict,
                             preferences: Optional[Dict]) -> RouteType:
        """Determine route type based on geography and preferences"""
        if preferences and "route_type" in preferences:
            return RouteType(preferences["route_type"])
            
        # Simple heuristics based on coordinates
        lat_avg = (origin["lat"] + destination["lat"]) / 2
        lng_avg = (origin["lng"] + destination["lng"]) / 2
        
        # Coastal detection (simplified)
        if abs(lng_avg) > 120 or (abs(lng_avg) < 80 and lat_avg < 40):
            return RouteType.COASTAL
        # Mountain detection
        elif 105 < abs(lng_avg) < 115 and 35 < lat_avg < 45:
            return RouteType.MOUNTAIN
        # Desert detection
        elif 110 < abs(lng_avg) < 120 and 30 < lat_avg < 40:
            return RouteType.DESERT
        # Urban areas
        elif any(city in str(origin) + str(destination) for city in ["New York", "Los Angeles", "Chicago"]):
            return RouteType.URBAN
        else:
            return random.choice([RouteType.HIGHWAY, RouteType.SCENIC, RouteType.RURAL])
            
    def _generate_segments(self, origin: Dict, destination: Dict,
                          waypoints: List[Dict], route_type: RouteType) -> List[RouteSegment]:
        """Generate route segments"""
        segments = []
        
        # Create points list
        points = [origin] + waypoints + [destination]
        
        # Generate segments between consecutive points
        for i in range(len(points) - 1):
            start = points[i]
            end = points[i + 1]
            
            # Calculate distance
            distance = geodesic(
                (start["lat"], start["lng"]),
                (end["lat"], end["lng"])
            ).kilometers
            
            # Estimate duration (average 80 km/h with variations)
            speed = self._get_average_speed(route_type)
            duration = int((distance / speed) * 60)  # minutes
            
            # Generate segment characteristics
            segment = RouteSegment(
                start_point=start,
                end_point=end,
                distance=distance,
                duration=duration,
                route_type=route_type,
                scenic_rating=self._generate_scenic_rating(route_type),
                difficulty=self._generate_difficulty(route_type),
                elevation_change=self._generate_elevation_change(route_type)
            )
            
            segments.append(segment)
            
        return segments
        
    def _get_average_speed(self, route_type: RouteType) -> float:
        """Get average speed for route type in km/h"""
        speeds = {
            RouteType.HIGHWAY: random.uniform(100, 120),
            RouteType.SCENIC: random.uniform(60, 80),
            RouteType.COASTAL: random.uniform(50, 70),
            RouteType.MOUNTAIN: random.uniform(40, 60),
            RouteType.DESERT: random.uniform(90, 110),
            RouteType.RURAL: random.uniform(70, 90),
            RouteType.URBAN: random.uniform(40, 60),
            RouteType.HISTORIC: random.uniform(60, 80)
        }
        return speeds.get(route_type, 80)
        
    def _generate_scenic_rating(self, route_type: RouteType) -> float:
        """Generate scenic rating based on route type"""
        base_ratings = {
            RouteType.HIGHWAY: 0.3,
            RouteType.SCENIC: 0.8,
            RouteType.COASTAL: 0.9,
            RouteType.MOUNTAIN: 0.85,
            RouteType.DESERT: 0.7,
            RouteType.RURAL: 0.6,
            RouteType.URBAN: 0.4,
            RouteType.HISTORIC: 0.7
        }
        base = base_ratings.get(route_type, 0.5)
        return max(0, min(1, base + random.uniform(-0.1, 0.1)))
        
    def _generate_difficulty(self, route_type: RouteType) -> float:
        """Generate difficulty rating based on route type"""
        base_difficulties = {
            RouteType.HIGHWAY: 0.2,
            RouteType.SCENIC: 0.5,
            RouteType.COASTAL: 0.4,
            RouteType.MOUNTAIN: 0.8,
            RouteType.DESERT: 0.3,
            RouteType.RURAL: 0.4,
            RouteType.URBAN: 0.6,
            RouteType.HISTORIC: 0.3
        }
        base = base_difficulties.get(route_type, 0.5)
        return max(0, min(1, base + random.uniform(-0.1, 0.1)))
        
    def _generate_elevation_change(self, route_type: RouteType) -> int:
        """Generate elevation change in meters"""
        if route_type == RouteType.MOUNTAIN:
            return random.randint(500, 2000)
        elif route_type == RouteType.COASTAL:
            return random.randint(0, 200)
        elif route_type == RouteType.DESERT:
            return random.randint(100, 500)
        else:
            return random.randint(0, 300)
            
    def _generate_points_of_interest(self, segments: List[RouteSegment],
                                   preferences: Optional[Dict]) -> List[PointOfInterest]:
        """Generate points of interest along the route"""
        pois = []
        
        # Determine POI categories based on preferences
        if preferences:
            preferred_categories = preferences.get("interests", ["natural", "cultural"])
        else:
            preferred_categories = ["natural", "cultural", "historical", "quirky", "dining"]
            
        # Add POIs to segments
        for i, segment in enumerate(segments):
            # Number of POIs based on segment distance
            num_pois = int(segment.distance / 50)  # Roughly 1 POI per 50km
            num_pois = min(num_pois, 3)  # Max 3 per segment
            
            for _ in range(num_pois):
                category = random.choice(preferred_categories)
                if category in self.POI_DATABASE:
                    poi_data = random.choice(self.POI_DATABASE[category])
                    
                    # Place POI along segment (simplified)
                    ratio = random.random()
                    poi_lat = segment.start_point["lat"] + \
                             (segment.end_point["lat"] - segment.start_point["lat"]) * ratio
                    poi_lng = segment.start_point["lng"] + \
                             (segment.end_point["lng"] - segment.start_point["lng"]) * ratio
                    
                    # Add slight offset
                    poi_lat += random.uniform(-0.1, 0.1)
                    poi_lng += random.uniform(-0.1, 0.1)
                    
                    poi = PointOfInterest(
                        name=poi_data["name"],
                        lat=poi_lat,
                        lng=poi_lng,
                        category=category,
                        description=poi_data["description"],
                        visit_duration=random.randint(15, 60)
                    )
                    
                    pois.append(poi)
                    segment.points_of_interest.append(poi)
                    
        return pois
        
    def _calculate_scenic_rating(self, route_type: RouteType, waypoints: List[Dict]) -> float:
        """Calculate overall scenic rating"""
        base = self._generate_scenic_rating(route_type)
        
        # Bonus for more waypoints (more diverse route)
        waypoint_bonus = min(len(waypoints) * 0.05, 0.2)
        
        return min(base + waypoint_bonus, 1.0)
        
    def _calculate_difficulty(self, segments: List[RouteSegment]) -> float:
        """Calculate overall route difficulty"""
        if not segments:
            return 0.5
            
        difficulties = [segment.difficulty for segment in segments]
        elevation_factor = sum(segment.elevation_change for segment in segments) / 10000
        
        return min(sum(difficulties) / len(difficulties) + elevation_factor, 1.0)
        
    def _is_family_friendly(self, segments: List[RouteSegment], 
                           pois: List[PointOfInterest]) -> bool:
        """Determine if route is family-friendly"""
        # Check difficulty
        avg_difficulty = sum(s.difficulty for s in segments) / len(segments)
        if avg_difficulty > 0.7:
            return False
            
        # Check for family-friendly POIs
        family_categories = ["natural", "cultural", "quirky"]
        family_pois = sum(1 for poi in pois if poi.category in family_categories)
        
        return family_pois >= len(pois) * 0.5
        
    def _determine_best_travel_time(self, route_type: RouteType,
                                   origin: Dict, destination: Dict) -> str:
        """Determine best time to travel this route"""
        if route_type == RouteType.COASTAL:
            return "Late spring through early fall (May-September)"
        elif route_type == RouteType.MOUNTAIN:
            return "Summer and early fall (June-October)"
        elif route_type == RouteType.DESERT:
            return "Fall through spring (October-April)"
        elif route_type == RouteType.SCENIC:
            return "Spring and fall for best foliage"
        else:
            return "Year-round with weather considerations"
            
    def _get_seasonal_considerations(self, route_type: RouteType,
                                   origin: Dict, destination: Dict) -> List[str]:
        """Get seasonal considerations for route"""
        considerations = []
        
        if route_type == RouteType.MOUNTAIN:
            considerations.extend([
                "Snow possible October-May",
                "Chain requirements in winter",
                "Higher elevation roads may close"
            ])
        elif route_type == RouteType.COASTAL:
            considerations.extend([
                "Fog common in summer mornings",
                "Hurricane season June-November (Atlantic)",
                "Best weather in fall"
            ])
        elif route_type == RouteType.DESERT:
            considerations.extend([
                "Extreme heat in summer (100°F+)",
                "Flash flood risk during monsoons",
                "Ideal conditions in winter"
            ])
        elif route_type == RouteType.SCENIC:
            considerations.extend([
                "Fall foliage peak varies by region",
                "Spring wildflowers March-May",
                "Summer can be crowded"
            ])
            
        return considerations
        
    def generate_alternative_routes(self, origin: Dict, destination: Dict,
                                  num_alternatives: int = 3) -> List[SimulatedRoute]:
        """Generate alternative routes between same points"""
        routes = []
        
        # Generate different route preferences
        preferences_options = [
            {"route_type": "highway", "optimize": "time"},
            {"route_type": "scenic", "optimize": "scenery"},
            {"route_type": "historic", "optimize": "attractions"},
            {"interests": ["natural", "cultural"], "optimize": "balanced"}
        ]
        
        for i in range(min(num_alternatives, len(preferences_options))):
            route = self.generate_route(origin, destination, preferences_options[i])
            routes.append(route)
            
        return routes
        
    def generate_multi_day_journey(self, stops: List[Dict], 
                                 daily_limit_hours: int = 8) -> List[SimulatedRoute]:
        """Generate a multi-day journey with overnight stops"""
        journey_routes = []
        
        for i in range(len(stops) - 1):
            route = self.generate_route(stops[i], stops[i + 1])
            
            # Check if route exceeds daily limit
            if route.total_duration > daily_limit_hours * 60:
                # Split into multiple days
                # This is simplified - in reality would find actual overnight stops
                route.metadata["requires_overnight"] = True
                route.metadata["suggested_stops"] = self._suggest_overnight_stops(route)
                
            journey_routes.append(route)
            
        return journey_routes
        
    def _suggest_overnight_stops(self, route: SimulatedRoute) -> List[Dict]:
        """Suggest overnight stops for long routes"""
        stops = []
        
        # Find stops roughly every 8 hours of driving
        cumulative_duration = 0
        
        for segment in route.segments:
            cumulative_duration += segment.duration
            
            if cumulative_duration >= 480:  # 8 hours
                stops.append({
                    "location": segment.end_point,
                    "hotels_nearby": random.randint(5, 20),
                    "avg_price": random.randint(80, 200)
                })
                cumulative_duration = 0
                
        return stops
        
    def export_route(self, route: SimulatedRoute, filename: str = "simulated_route.json"):
        """Export route to JSON file"""
        # Convert route to dictionary
        route_dict = {
            "id": route.id,
            "name": route.name,
            "origin": route.origin,
            "destination": route.destination,
            "total_distance_km": route.total_distance,
            "total_duration_minutes": route.total_duration,
            "total_duration_formatted": f"{route.total_duration // 60}h {route.total_duration % 60}m",
            "route_types": [rt.value for rt in route.route_types],
            "waypoints": route.waypoints,
            "best_travel_time": route.best_travel_time,
            "seasonal_considerations": route.seasonal_considerations,
            "metadata": route.metadata,
            "segments": [],
            "points_of_interest": []
        }
        
        # Add segments
        for segment in route.segments:
            seg_dict = {
                "start": segment.start_point,
                "end": segment.end_point,
                "distance_km": segment.distance,
                "duration_minutes": segment.duration,
                "route_type": segment.route_type.value,
                "scenic_rating": segment.scenic_rating,
                "difficulty": segment.difficulty,
                "elevation_change_m": segment.elevation_change,
                "points_of_interest": [
                    {
                        "name": poi.name,
                        "location": {"lat": poi.lat, "lng": poi.lng},
                        "category": poi.category,
                        "description": poi.description,
                        "visit_duration": poi.visit_duration
                    } for poi in segment.points_of_interest
                ]
            }
            route_dict["segments"].append(seg_dict)
            
        # Add all POIs
        for poi in route.points_of_interest:
            poi_dict = {
                "name": poi.name,
                "location": {"lat": poi.lat, "lng": poi.lng},
                "category": poi.category,
                "description": poi.description,
                "suggested_visit_duration": poi.visit_duration
            }
            route_dict["points_of_interest"].append(poi_dict)
            
        with open(filename, 'w') as f:
            json.dump(route_dict, f, indent=2)
            
        print(f"Route exported to {filename}")
        

def main():
    """Example usage"""
    simulator = RouteSimulator()
    
    # Generate a random route from templates
    print("Generating route from template...")
    route1 = simulator.generate_route()
    print(f"\nRoute: {route1.name}")
    print(f"Distance: {route1.total_distance:.1f} km")
    print(f"Duration: {route1.total_duration // 60}h {route1.total_duration % 60}m")
    print(f"Route Types: {[rt.value for rt in route1.route_types]}")
    print(f"Points of Interest: {len(route1.points_of_interest)}")
    print(f"Best Travel Time: {route1.best_travel_time}")
    
    # Generate custom route
    print("\n\nGenerating custom route...")
    origin = {"lat": 40.7128, "lng": -74.0060, "name": "New York, NY"}
    destination = {"lat": 38.9072, "lng": -77.0369, "name": "Washington, DC"}
    
    route2 = simulator.generate_route(origin, destination, {"route_type": "scenic"})
    print(f"\nRoute: {route2.name}")
    print(f"Distance: {route2.total_distance:.1f} km")
    print(f"Waypoints: {len(route2.waypoints)}")
    
    # Generate alternatives
    print("\n\nGenerating alternative routes...")
    alternatives = simulator.generate_alternative_routes(origin, destination)
    
    for i, alt in enumerate(alternatives):
        print(f"\nAlternative {i+1}: {alt.metadata.get('optimize', 'balanced')}")
        print(f"  Distance: {alt.total_distance:.1f} km")
        print(f"  Duration: {alt.total_duration // 60}h {alt.total_duration % 60}m")
        print(f"  Scenic Rating: {alt.metadata.get('scenic_rating', 0):.2f}")
        
    # Generate multi-day journey
    print("\n\nGenerating multi-day journey...")
    stops = [
        {"lat": 34.0522, "lng": -118.2437, "name": "Los Angeles, CA"},
        {"lat": 36.1699, "lng": -115.1398, "name": "Las Vegas, NV"},
        {"lat": 40.7608, "lng": -111.8910, "name": "Salt Lake City, UT"},
        {"lat": 39.7392, "lng": -104.9903, "name": "Denver, CO"}
    ]
    
    journey = simulator.generate_multi_day_journey(stops)
    print(f"\nMulti-day journey with {len(journey)} legs:")
    
    for i, leg in enumerate(journey):
        print(f"\nDay {i+1}: {leg.name}")
        print(f"  Distance: {leg.total_distance:.1f} km")
        print(f"  Duration: {leg.total_duration // 60}h {leg.total_duration % 60}m")
        if leg.metadata.get("requires_overnight"):
            print(f"  Overnight stops suggested: {len(leg.metadata.get('suggested_stops', []))}")
            
    # Export example route
    simulator.export_route(route1)


if __name__ == "__main__":
    main()