"""
Rideshare mode service for drivers and passengers.
Provides optimized routes, entertainment, and convenience features.
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass
from enum import Enum

from backend.app.core.logger import get_logger
from backend.app.core.cache import get_cache
from backend.app.services.directions_service import DirectionsService
from backend.app.services.contextual_awareness import ContextualAwarenessService
from backend.app.services.entertainment.entertainmentService import EntertainmentService
from backend.app.services.food.foodService import FoodService
from backend.app.services.local_expert import LocalExpertService

logger = get_logger(__name__)


class RideshareMode(Enum):
    DRIVER = "driver"
    PASSENGER = "passenger"


@dataclass
class RideshareContext:
    mode: RideshareMode
    pickup_location: Optional[Dict[str, float]] = None
    dropoff_location: Optional[Dict[str, float]] = None
    current_location: Optional[Dict[str, float]] = None
    ride_duration: Optional[int] = None  # minutes
    driver_preferences: Optional[Dict[str, Any]] = None
    passenger_interests: Optional[List[str]] = None


@dataclass
class DriverOpportunity:
    type: str  # "restaurant", "charging", "rest_stop", "gas"
    name: str
    location: Dict[str, float]
    distance_from_route: float  # meters
    estimated_detour_time: int  # minutes
    details: Dict[str, Any]
    quick_action_available: bool = False


@dataclass
class SurgePricingArea:
    location: Dict[str, float]
    radius: float  # meters
    surge_multiplier: float
    estimated_end_time: Optional[datetime] = None


class RideshareService:
    def __init__(self):
        self.directions_service = DirectionsService()
        self.contextual_service = ContextualAwarenessService()
        self.entertainment_service = EntertainmentService()
        self.food_service = FoodService()
        self.local_expert = LocalExpertService()
        self.cache = get_cache()
        
    async def get_optimized_driver_route(
        self,
        pickup: Dict[str, float],
        dropoff: Dict[str, float],
        driver_preferences: Optional[Dict[str, Any]] = None,
        avoid_surge_areas: bool = True
    ) -> Dict[str, Any]:
        """Get optimized route for rideshare drivers with opportunities."""
        try:
            # Get base route
            route = await self.directions_service.get_directions(
                origin=f"{pickup['lat']},{pickup['lng']}",
                destination=f"{dropoff['lat']},{dropoff['lng']}",
                mode="driving"
            )
            
            if not route or not route.get("routes"):
                return {"error": "No route found"}
            
            primary_route = route["routes"][0]
            
            # Find opportunities along route
            opportunities = await self._find_driver_opportunities(
                primary_route,
                driver_preferences or {}
            )
            
            # Calculate earnings optimization
            earnings_tips = await self._calculate_earnings_optimization(
                primary_route,
                pickup,
                dropoff
            )
            
            # Find surge areas to avoid if requested
            surge_areas = []
            if avoid_surge_areas:
                surge_areas = await self._get_surge_areas(pickup, dropoff)
                
            return {
                "route": primary_route,
                "opportunities": opportunities,
                "earnings_tips": earnings_tips,
                "surge_areas": surge_areas,
                "estimated_fare": await self._estimate_fare(primary_route),
                "optimal_stops": await self._suggest_optimal_stops(
                    primary_route,
                    opportunities,
                    driver_preferences
                )
            }
            
        except Exception as e:
            logger.error(f"Error in driver route optimization: {e}")
            return {"error": str(e)}
    
    async def get_passenger_entertainment(
        self,
        pickup: Dict[str, float],
        dropoff: Dict[str, float],
        duration_minutes: int,
        interests: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get entertainment content for passengers during ride."""
        try:
            # Get route info for context
            route_info = await self.directions_service.get_directions(
                origin=f"{pickup['lat']},{pickup['lng']}",
                destination=f"{dropoff['lat']},{dropoff['lng']}",
                mode="driving"
            )
            
            # Generate entertainment based on ride duration
            entertainment_package = {
                "destination_insights": await self._get_destination_insights(
                    dropoff,
                    interests
                ),
                "route_highlights": await self._get_route_highlights(
                    route_info,
                    duration_minutes
                ),
                "conversation_starters": await self._generate_conversation_starters(
                    pickup,
                    dropoff,
                    interests
                ),
                "local_trivia": await self._get_local_trivia(
                    pickup,
                    dropoff,
                    duration_minutes
                )
            }
            
            # Add time-appropriate content
            if duration_minutes > 10:
                entertainment_package["mini_podcast"] = await self._get_mini_podcast(
                    interests,
                    duration_minutes
                )
            
            if duration_minutes > 20:
                entertainment_package["interactive_game"] = await self._get_rideshare_game(
                    route_info,
                    interests
                )
                
            return entertainment_package
            
        except Exception as e:
            logger.error(f"Error generating passenger entertainment: {e}")
            return {"error": str(e)}
    
    async def find_quick_actions(
        self,
        location: Dict[str, float],
        action_type: str = "all"
    ) -> List[Dict[str, Any]]:
        """Find quick action opportunities for drivers (food pickup, etc)."""
        try:
            actions = []
            
            if action_type in ["all", "food"]:
                # Find restaurants with quick pickup
                food_actions = await self._find_quick_food_pickups(location)
                actions.extend(food_actions)
            
            if action_type in ["all", "charging"]:
                # Find EV charging stations
                charging_actions = await self._find_ev_charging(location)
                actions.extend(charging_actions)
                
            if action_type in ["all", "rest"]:
                # Find rest stops
                rest_actions = await self._find_rest_stops(location)
                actions.extend(rest_actions)
                
            # Sort by distance
            actions.sort(key=lambda x: x.get("distance", float('inf')))
            
            return actions[:10]  # Return top 10 options
            
        except Exception as e:
            logger.error(f"Error finding quick actions: {e}")
            return []
    
    async def _find_driver_opportunities(
        self,
        route: Dict[str, Any],
        preferences: Dict[str, Any]
    ) -> List[DriverOpportunity]:
        """Find opportunities along the route for drivers."""
        opportunities = []
        
        # Extract route polyline points
        if "legs" not in route:
            return opportunities
            
        # Sample points along route
        sample_points = self._sample_route_points(route, interval_meters=5000)
        
        for point in sample_points:
            # Find restaurants if driver needs food
            if preferences.get("find_food", True):
                restaurants = await self.food_service.find_nearby_restaurants(
                    point,
                    radius_meters=1000,
                    quick_service=True
                )
                for restaurant in restaurants[:2]:  # Top 2 per point
                    opportunities.append(DriverOpportunity(
                        type="restaurant",
                        name=restaurant["name"],
                        location=restaurant["location"],
                        distance_from_route=restaurant.get("distance", 0),
                        estimated_detour_time=restaurant.get("detour_time", 5),
                        details=restaurant,
                        quick_action_available=restaurant.get("has_mobile_order", False)
                    ))
            
            # Find EV charging if needed
            if preferences.get("find_charging", False):
                charging = await self._find_ev_charging(point, radius=1500)
                for station in charging[:1]:  # Top 1 per point
                    opportunities.append(DriverOpportunity(
                        type="charging",
                        name=station["name"],
                        location=station["location"],
                        distance_from_route=station.get("distance", 0),
                        estimated_detour_time=station.get("detour_time", 15),
                        details=station,
                        quick_action_available=True
                    ))
                    
        return opportunities
    
    async def _calculate_earnings_optimization(
        self,
        route: Dict[str, Any],
        pickup: Dict[str, float],
        dropoff: Dict[str, float]
    ) -> Dict[str, Any]:
        """Calculate tips for optimizing driver earnings."""
        tips = {
            "optimal_speed": "Maintain steady speed for fuel efficiency",
            "best_times": [],
            "high_demand_areas": [],
            "efficiency_score": 0
        }
        
        # Calculate efficiency based on route
        if "legs" in route and route["legs"]:
            leg = route["legs"][0]
            distance = leg.get("distance", {}).get("value", 0) / 1000  # km
            duration = leg.get("duration", {}).get("value", 0) / 60  # minutes
            
            if distance > 0 and duration > 0:
                avg_speed = (distance / duration) * 60  # km/h
                tips["efficiency_score"] = min(100, int((avg_speed / 60) * 100))
                
        # Time-based recommendations
        current_hour = datetime.now().hour
        if 7 <= current_hour <= 9 or 17 <= current_hour <= 19:
            tips["best_times"].append("Currently in peak hours - higher demand")
        elif 22 <= current_hour or current_hour <= 5:
            tips["best_times"].append("Late night - check for surge pricing")
            
        return tips
    
    async def _get_surge_areas(
        self,
        pickup: Dict[str, float],
        dropoff: Dict[str, float]
    ) -> List[SurgePricingArea]:
        """Get current surge pricing areas to avoid."""
        # This would integrate with rideshare APIs in production
        # Simulated data for now
        surge_areas = []
        
        # Check cache for surge data
        cache_key = f"surge_areas_{pickup['lat']:.2f}_{pickup['lng']:.2f}"
        cached_data = await self.cache.get(cache_key)
        
        if cached_data:
            return cached_data
            
        # Simulate surge areas (would be real API data)
        # For demo, assume downtown areas have surge during peak times
        current_hour = datetime.now().hour
        if 7 <= current_hour <= 9 or 17 <= current_hour <= 19:
            surge_areas.append(SurgePricingArea(
                location={"lat": pickup["lat"], "lng": pickup["lng"]},
                radius=2000,
                surge_multiplier=1.5,
                estimated_end_time=datetime.now() + timedelta(hours=1)
            ))
            
        await self.cache.set(cache_key, surge_areas, expire=300)  # 5 min cache
        return surge_areas
    
    async def _get_destination_insights(
        self,
        destination: Dict[str, float],
        interests: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Get insights about the passenger's destination."""
        insights = await self.local_expert.get_local_insights(
            destination,
            interests or ["general"]
        )
        
        return {
            "arrival_tips": insights.get("tips", []),
            "nearby_attractions": insights.get("attractions", []),
            "local_favorites": insights.get("favorites", []),
            "weather_appropriate": insights.get("weather_tips", [])
        }
    
    async def _generate_conversation_starters(
        self,
        pickup: Dict[str, float],
        dropoff: Dict[str, float],
        interests: Optional[List[str]] = None
    ) -> List[str]:
        """Generate conversation starters for the ride."""
        starters = [
            "Did you know this area has some amazing hidden gems?",
            "The route we're taking passes by some interesting history.",
            "Have you tried any of the local restaurants around here?"
        ]
        
        # Add interest-specific starters
        if interests:
            if "food" in interests:
                starters.append("There's a famous local dish you should try!")
            if "history" in interests:
                starters.append("This neighborhood has fascinating historical significance.")
            if "art" in interests:
                starters.append("There's a vibrant art scene in this area.")
                
        return starters[:5]
    
    async def _find_quick_food_pickups(
        self,
        location: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Find restaurants with quick pickup options."""
        restaurants = await self.food_service.find_nearby_restaurants(
            location,
            radius_meters=2000,
            quick_service=True
        )
        
        # Filter for mobile ordering
        quick_options = [
            r for r in restaurants 
            if r.get("has_mobile_order") or r.get("drive_through")
        ]
        
        return quick_options
    
    async def _find_ev_charging(
        self,
        location: Dict[str, float],
        radius: int = 3000
    ) -> List[Dict[str, Any]]:
        """Find EV charging stations nearby."""
        # This would use a real EV charging API
        # Simulated for demo
        return [
            {
                "name": "FastCharge Station",
                "location": {
                    "lat": location["lat"] + 0.01,
                    "lng": location["lng"] + 0.01
                },
                "distance": 800,
                "available_ports": 3,
                "charging_speed": "150kW",
                "estimated_wait": 5
            }
        ]
    
    async def _find_rest_stops(
        self,
        location: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Find rest stops and facilities."""
        # Would integrate with maps API for real data
        return [
            {
                "name": "Highway Rest Area",
                "location": location,
                "distance": 500,
                "amenities": ["restrooms", "vending", "picnic_area"],
                "clean_rating": 4.2
            }
        ]
    
    def _sample_route_points(
        self,
        route: Dict[str, Any],
        interval_meters: int = 5000
    ) -> List[Dict[str, float]]:
        """Sample points along the route at regular intervals."""
        points = []
        
        if "legs" not in route:
            return points
            
        for leg in route["legs"]:
            if "steps" in leg:
                for step in leg["steps"]:
                    if "start_location" in step:
                        points.append({
                            "lat": step["start_location"]["lat"],
                            "lng": step["start_location"]["lng"]
                        })
                        
        # Sample every N points based on interval
        # Simplified - in production would decode polyline
        sampled = points[::max(1, len(points) // 10)]
        return sampled
    
    async def _estimate_fare(self, route: Dict[str, Any]) -> Dict[str, float]:
        """Estimate fare for the ride."""
        base_fare = 2.50
        per_km = 1.50
        per_minute = 0.25
        
        if "legs" in route and route["legs"]:
            leg = route["legs"][0]
            distance_km = leg.get("distance", {}).get("value", 0) / 1000
            duration_min = leg.get("duration", {}).get("value", 0) / 60
            
            estimated = base_fare + (distance_km * per_km) + (duration_min * per_minute)
            
            return {
                "base": base_fare,
                "distance": distance_km * per_km,
                "time": duration_min * per_minute,
                "total": round(estimated, 2)
            }
            
        return {"total": 0}
    
    async def _suggest_optimal_stops(
        self,
        route: Dict[str, Any],
        opportunities: List[DriverOpportunity],
        preferences: Dict[str, Any]
    ) -> List[DriverOpportunity]:
        """Suggest optimal stops based on route and preferences."""
        # Filter based on detour time tolerance
        max_detour = preferences.get("max_detour_minutes", 5)
        
        optimal = [
            opp for opp in opportunities
            if opp.estimated_detour_time <= max_detour
        ]
        
        # Prioritize based on preferences
        if preferences.get("prefer_quick_action"):
            optimal.sort(key=lambda x: (not x.quick_action_available, x.distance_from_route))
        else:
            optimal.sort(key=lambda x: x.distance_from_route)
            
        return optimal[:3]  # Top 3 suggestions
    
    async def _get_route_highlights(
        self,
        route_info: Dict[str, Any],
        duration: int
    ) -> List[Dict[str, str]]:
        """Get interesting highlights along the route."""
        highlights = []
        
        if route_info and "routes" in route_info and route_info["routes"]:
            route = route_info["routes"][0]
            
            # Extract notable waypoints
            if "legs" in route:
                for leg in route["legs"]:
                    if "steps" in leg:
                        for i, step in enumerate(leg["steps"]):
                            if i % max(1, len(leg["steps"]) // 5) == 0:  # Sample 5 points
                                highlights.append({
                                    "type": "waypoint",
                                    "description": f"Passing through {step.get('html_instructions', 'interesting area')}",
                                    "timing": f"{i * duration // len(leg['steps'])} minutes"
                                })
                                
        return highlights[:5]
    
    async def _get_local_trivia(
        self,
        pickup: Dict[str, float],
        dropoff: Dict[str, float],
        duration: int
    ) -> List[Dict[str, str]]:
        """Get trivia about the areas."""
        trivia = [
            {
                "question": "What year was this neighborhood established?",
                "answer": "1892",
                "fact": "Making it one of the oldest in the city!"
            },
            {
                "question": "What famous person lived near here?",
                "answer": "A renowned local artist",
                "fact": "Their studio is now a popular gallery."
            }
        ]
        
        # Adjust trivia count based on duration
        trivia_count = min(len(trivia), max(1, duration // 5))
        return trivia[:trivia_count]
    
    async def _get_mini_podcast(
        self,
        interests: List[str],
        duration: int
    ) -> Dict[str, Any]:
        """Get mini podcast content for longer rides."""
        topics = []
        
        if "technology" in interests:
            topics.append({
                "title": "Tech Innovation in Transportation",
                "duration": min(10, duration),
                "url": "podcast://tech-transport-ep1"
            })
            
        if "history" in interests:
            topics.append({
                "title": "Local History Spotlight",
                "duration": min(8, duration),
                "url": "podcast://local-history-ep1"
            })
            
        if not topics:
            topics.append({
                "title": "Daily News Digest",
                "duration": min(5, duration),
                "url": "podcast://news-digest"
            })
            
        return {
            "available_episodes": topics,
            "auto_play": duration > 15
        }
    
    async def _get_rideshare_game(
        self,
        route_info: Dict[str, Any],
        interests: List[str]
    ) -> Dict[str, Any]:
        """Get interactive game for passenger entertainment."""
        return {
            "type": "location_trivia",
            "title": "Spot the Landmark",
            "description": "Can you spot these landmarks as we pass by?",
            "challenges": [
                {
                    "landmark": "Historic Building",
                    "points": 10,
                    "hint": "Look for the red brick facade"
                },
                {
                    "landmark": "Famous Mural",
                    "points": 15,
                    "hint": "On the side of the blue building"
                }
            ],
            "total_possible_points": 25
        }