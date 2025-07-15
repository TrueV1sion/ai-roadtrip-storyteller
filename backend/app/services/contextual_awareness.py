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
from app.models.reservation import Reservation, ReservationStatus
from app.models.side_quest import SideQuest, UserSideQuest, SideQuestStatus

logger = get_logger(__name__)


class ContextType:
    """Types of context that can be detected."""
    MEAL_TIME = "meal_time"
    REST_BREAK = "rest_break"
    TRAFFIC_ALERT = "traffic_alert"
    SCENIC_SPOT = "scenic_spot"
    WEATHER_ALERT = "weather_alert"
    HISTORICAL_POI = "historical_poi"
    NEARBY_ATTRACTION = "nearby_attraction"
    LOCAL_EVENT = "local_event"
    FUEL_REMINDER = "fuel_reminder"
    LODGING = "lodging"
    ITINERARY_UPDATE = "itinerary_update"
    DRIVING_MILESTONE = "driving_milestone"


class ContextualAwareness:
    """
    Service for contextual awareness and proactive suggestions.
    
    This service analyzes the user's context (location, time, route, etc.)
    and generates proactive suggestions and notifications.
    """
    
    def __init__(self, db: Session):
        """Initialize the contextual awareness engine with database session."""
        self.db = db
        self.context_thresholds = {
            # Time between meal suggestions in hours
            ContextType.MEAL_TIME: 3.0,
            
            # Driving time before suggesting a rest break in hours
            ContextType.REST_BREAK: 2.0,
            
            # Distance in km before suggesting fuel
            ContextType.FUEL_REMINDER: 50.0,
            
            # Minimum uniqueness score for suggesting a scenic spot
            "scenic_spot_min_score": 70.0,
            
            # Minimum uniqueness score for suggesting a historical POI
            "historical_poi_min_score": 60.0,
            
            # Minimum uniqueness score for suggesting an attraction
            "attraction_min_score": 80.0,
            
            # Maximum detour time in minutes for suggestions
            "max_detour_time": 20,
            
            # Maximum distance in km for nearby suggestions
            "nearby_max_distance": 5.0,
        }
    
    async def analyze_context(
        self,
        user_id: str,
        current_location: Dict[str, float],
        current_time: Optional[datetime] = None,
        route_id: Optional[str] = None,
        trip_id: Optional[str] = None,
        vehicle_data: Optional[Dict[str, Any]] = None,
        weather_data: Optional[Dict[str, Any]] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
        recent_contexts: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Analyze the user's current context and generate relevant awareness items.
        
        Args:
            user_id: ID of the user
            current_location: Dict with latitude and longitude
            current_time: Current time (defaults to now)
            route_id: Optional ID of the active route
            trip_id: Optional ID of the current trip
            vehicle_data: Optional vehicle telemetry data
            weather_data: Optional weather conditions
            user_preferences: Optional user preferences
            recent_contexts: Optional list of recently detected contexts (to avoid duplicates)
            
        Returns:
            List of context awareness items with suggestions
        """
        try:
            if current_time is None:
                current_time = datetime.utcnow()
            
            # Get user data
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User with ID {user_id} not found")
            
            # Extract current coordinates
            latitude = current_location.get("latitude")
            longitude = current_location.get("longitude")
            if latitude is None or longitude is None:
                raise ValueError("Current location must include latitude and longitude")
            
            # Initialize context results
            context_results = []
            
            # Initialize set of recently detected context types to avoid duplicates
            recent_context_types = set()
            if recent_contexts:
                recent_context_types = {ctx.get("type") for ctx in recent_contexts if "type" in ctx}
            
            # 1. Check for meal time context
            if ContextType.MEAL_TIME not in recent_context_types:
                meal_context = await self._check_meal_time(
                    current_time=current_time,
                    latitude=latitude,
                    longitude=longitude,
                    user_id=user_id,
                    user_preferences=user_preferences
                )
                if meal_context:
                    context_results.append(meal_context)
            
            # 2. Check for rest break context
            if ContextType.REST_BREAK not in recent_context_types and vehicle_data:
                rest_context = await self._check_rest_break(
                    driving_duration=vehicle_data.get("continuous_driving_time", 0),
                    latitude=latitude,
                    longitude=longitude,
                    user_id=user_id
                )
                if rest_context:
                    context_results.append(rest_context)
            
            # 3. Check for nearby attractions
            if ContextType.NEARBY_ATTRACTION not in recent_context_types:
                attraction_context = await self._check_nearby_attractions(
                    latitude=latitude,
                    longitude=longitude,
                    route_id=route_id,
                    user_id=user_id,
                    user_preferences=user_preferences
                )
                if attraction_context:
                    context_results.append(attraction_context)
            
            # 4. Check for scenic spots
            if ContextType.SCENIC_SPOT not in recent_context_types:
                scenic_context = await self._check_scenic_spots(
                    latitude=latitude,
                    longitude=longitude,
                    route_id=route_id,
                    user_id=user_id
                )
                if scenic_context:
                    context_results.append(scenic_context)
            
            # 5. Check for historical points of interest
            if ContextType.HISTORICAL_POI not in recent_context_types:
                historical_context = await self._check_historical_poi(
                    latitude=latitude,
                    longitude=longitude,
                    route_id=route_id,
                    user_id=user_id,
                    user_preferences=user_preferences
                )
                if historical_context:
                    context_results.append(historical_context)
            
            # 6. Check for upcoming reservations
            if ContextType.ITINERARY_UPDATE not in recent_context_types:
                reservation_context = await self._check_upcoming_reservations(
                    current_time=current_time,
                    user_id=user_id,
                    latitude=latitude,
                    longitude=longitude,
                    route_id=route_id
                )
                if reservation_context:
                    context_results.append(reservation_context)
            
            # 7. Check for weather alerts
            if ContextType.WEATHER_ALERT not in recent_context_types and weather_data:
                weather_context = await self._check_weather_alerts(
                    weather_data=weather_data,
                    latitude=latitude,
                    longitude=longitude,
                    route_id=route_id
                )
                if weather_context:
                    context_results.append(weather_context)
            
            # 8. Check for fuel/charging reminders
            if ContextType.FUEL_REMINDER not in recent_context_types and vehicle_data:
                fuel_context = await self._check_fuel_reminder(
                    vehicle_data=vehicle_data,
                    latitude=latitude,
                    longitude=longitude,
                    route_id=route_id
                )
                if fuel_context:
                    context_results.append(fuel_context)
            
            # 9. Check for local events
            if ContextType.LOCAL_EVENT not in recent_context_types:
                events_context = await self._check_local_events(
                    current_time=current_time,
                    latitude=latitude,
                    longitude=longitude,
                    user_preferences=user_preferences
                )
                if events_context:
                    context_results.append(events_context)
            
            # 10. Check for lodging suggestions as day ends
            if ContextType.LODGING not in recent_context_types:
                lodging_context = await self._check_lodging_suggestions(
                    current_time=current_time,
                    latitude=latitude,
                    longitude=longitude,
                    route_id=route_id,
                    user_id=user_id
                )
                if lodging_context:
                    context_results.append(lodging_context)
            
            # Sort contexts by priority
            context_results.sort(key=lambda x: x.get("priority", 5), reverse=True)
            
            return context_results
        except Exception as e:
            logger.error(f"Error analyzing context: {str(e)}")
            return []
    
    async def _check_meal_time(
        self,
        current_time: datetime,
        latitude: float,
        longitude: float,
        user_id: str,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Check if it's near a meal time and suggest restaurants.
        
        Args:
            current_time: Current time
            latitude: Current latitude
            longitude: Current longitude
            user_id: User ID
            user_preferences: Optional user preferences
            
        Returns:
            Meal time context if relevant, None otherwise
        """
        try:
            local_time = current_time.time()
            
            # Define meal time ranges
            breakfast_start = time(6, 30)
            breakfast_end = time(10, 30)
            lunch_start = time(11, 30)
            lunch_end = time(14, 30)
            dinner_start = time(17, 0)
            dinner_end = time(21, 0)
            
            # Check if current time is within meal times
            is_breakfast_time = breakfast_start <= local_time <= breakfast_end
            is_lunch_time = lunch_start <= local_time <= lunch_end
            is_dinner_time = dinner_start <= local_time <= dinner_end
            
            meal_time = None
            if is_breakfast_time:
                meal_time = "breakfast"
            elif is_lunch_time:
                meal_time = "lunch"
            elif is_dinner_time:
                meal_time = "dinner"
            else:
                return None  # Not a meal time
            
            # Check if we recently suggested a meal (would be in recent_contexts)
            # This is handled by the calling function's recent_context_types check
            
            # Get cuisine preferences if available
            cuisine_preferences = []
            if user_preferences and "cuisine" in user_preferences:
                cuisine_preferences = user_preferences["cuisine"]
            
            # In a real implementation, this would query nearby restaurants
            # using a service like Google Places API. For now, we'll simulate it.
            suggested_restaurants = [
                {
                    "name": f"Sample {cuisine if cuisine_preferences else 'Local'} Restaurant",
                    "cuisine": cuisine if cuisine_preferences else "Local",
                    "distance": random.uniform(0.5, 3.0),
                    "rating": random.uniform(3.5, 4.8),
                    "price_level": random.randint(1, 3),
                    "is_open": True,
                    "address": "123 Sample St.",
                    "latitude": latitude + random.uniform(-0.01, 0.01),
                    "longitude": longitude + random.uniform(-0.01, 0.01)
                }
                for cuisine in (cuisine_preferences[:3] if cuisine_preferences else ["Local"])
            ]
            
            if not suggested_restaurants:
                return None
            
            # Create the meal time context
            context = {
                "id": str(uuid.uuid4()),
                "type": ContextType.MEAL_TIME,
                "detected_at": current_time.isoformat(),
                "user_id": user_id,
                "priority": 8 if meal_time in ["lunch", "dinner"] else 6,  # Lunch/dinner higher priority than breakfast
                "title": f"Time for {meal_time.capitalize()}",
                "description": f"It's {meal_time} time! Here are some restaurants near you.",
                "category": "food",
                "icon": "food",
                "action_type": "restaurants",
                "expires_in_minutes": 90,
                "location": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "data": {
                    "meal_type": meal_time,
                    "restaurants": suggested_restaurants,
                    "cuisine_preferences": cuisine_preferences
                }
            }
            
            return context
        except Exception as e:
            logger.error(f"Error checking meal time context: {str(e)}")
            return None
    
    async def _check_rest_break(
        self,
        driving_duration: float,  # In minutes
        latitude: float,
        longitude: float,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Check if the user needs a rest break based on driving duration.
        
        Args:
            driving_duration: Continuous driving time in minutes
            latitude: Current latitude
            longitude: Current longitude
            user_id: User ID
            
        Returns:
            Rest break context if relevant, None otherwise
        """
        try:
            # Convert to hours for clearer comparison
            driving_hours = driving_duration / 60.0
            
            # Check if driving duration exceeds threshold
            threshold_hours = self.context_thresholds[ContextType.REST_BREAK]
            if driving_hours < threshold_hours:
                return None
            
            # Calculate how much the threshold is exceeded
            excess_hours = driving_hours - threshold_hours
            
            # Higher priority as excess increases
            priority = min(9, 5 + int(excess_hours * 2))
            
            # In a real implementation, this would query nearby rest areas, parks, etc.
            # using a service like Google Places API
            suggested_rest_areas = [
                {
                    "name": "Sample Rest Area",
                    "type": "rest_area",
                    "distance": random.uniform(1.0, 15.0),
                    "amenities": ["restrooms", "parking", "picnic tables"],
                    "latitude": latitude + random.uniform(-0.05, 0.05),
                    "longitude": longitude + random.uniform(-0.05, 0.05)
                },
                {
                    "name": "Sample Park",
                    "type": "park",
                    "distance": random.uniform(2.0, 10.0),
                    "amenities": ["restrooms", "walking trails", "picnic area"],
                    "latitude": latitude + random.uniform(-0.05, 0.05),
                    "longitude": longitude + random.uniform(-0.05, 0.05)
                }
            ]
            
            # Create the rest break context
            context = {
                "id": str(uuid.uuid4()),
                "type": ContextType.REST_BREAK,
                "detected_at": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "priority": priority,
                "title": "Time for a Break",
                "description": f"You've been driving for {int(driving_duration)} minutes. Consider taking a short break.",
                "category": "safety",
                "icon": "break",
                "action_type": "rest_areas",
                "expires_in_minutes": 60,
                "location": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "data": {
                    "driving_duration": driving_duration,
                    "rest_areas": suggested_rest_areas,
                    "safety_tip": "Taking regular breaks every 2 hours helps maintain alertness and reduces fatigue."
                }
            }
            
            return context
        except Exception as e:
            logger.error(f"Error checking rest break context: {str(e)}")
            return None
    
    async def _check_nearby_attractions(
        self,
        latitude: float,
        longitude: float,
        route_id: Optional[str],
        user_id: str,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Check for interesting attractions near the current location.
        
        Args:
            latitude: Current latitude
            longitude: Current longitude
            route_id: Optional active route ID
            user_id: User ID
            user_preferences: Optional user preferences
            
        Returns:
            Nearby attraction context if relevant, None otherwise
        """
        try:
            # In a real implementation, this would use the SideQuest service to find
            # nearby attractions based on the user's preferences and route
            
            # Get SideQuest table dynamically since it was just created
            # and might not be directly importable yet
            SideQuest = self.db.get_bind().table_names()
            if "side_quests" not in SideQuest:
                # Side quests table doesn't exist yet
                return None
            
            # Get user interests from preferences
            interests = []
            if user_preferences and "interests" in user_preferences:
                interests = user_preferences["interests"]
            
            # Simulate finding a nearby attraction
            # In a real implementation, this would query the side_quests table
            attraction = {
                "id": str(uuid.uuid4()),
                "title": "Sample Local Attraction",
                "description": "A unique local attraction worth checking out.",
                "category": random.choice(["cultural", "natural", "historical", "entertainment"]),
                "distance": random.uniform(0.5, self.context_thresholds["nearby_max_distance"]),
                "detour_time": random.randint(5, self.context_thresholds["max_detour_time"]),
                "uniqueness_score": random.uniform(80, 95),
                "latitude": latitude + random.uniform(-0.01, 0.01),
                "longitude": longitude + random.uniform(-0.01, 0.01),
                "image_url": "https://example.com/sample_attraction.jpg"
            }
            
            if attraction["uniqueness_score"] < self.context_thresholds["attraction_min_score"]:
                return None
            
            # Create the nearby attraction context
            context = {
                "id": str(uuid.uuid4()),
                "type": ContextType.NEARBY_ATTRACTION,
                "detected_at": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "priority": 7,
                "title": "Interesting Attraction Nearby",
                "description": f"{attraction['title']} is just {attraction['distance']:.1f} km away!",
                "category": attraction["category"],
                "icon": "attraction",
                "action_type": "show_attraction",
                "expires_in_minutes": 30,
                "location": {
                    "latitude": attraction["latitude"],
                    "longitude": attraction["longitude"]
                },
                "data": {
                    "attraction": attraction,
                    "user_interests_match": True if interests and any(i in attraction["category"] for i in interests) else False
                }
            }
            
            return context
        except Exception as e:
            logger.error(f"Error checking nearby attractions: {str(e)}")
            return None
    
    async def _check_scenic_spots(
        self,
        latitude: float,
        longitude: float,
        route_id: Optional[str],
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Check for scenic spots along the route or near the current location.
        
        Args:
            latitude: Current latitude
            longitude: Current longitude
            route_id: Optional active route ID
            user_id: User ID
            
        Returns:
            Scenic spot context if relevant, None otherwise
        """
        try:
            # Simulate finding a scenic spot
            # In a real implementation, this would query a database or API
            scenic_spot = {
                "id": str(uuid.uuid4()),
                "name": "Sample Scenic Viewpoint",
                "description": "A beautiful overlook with panoramic views.",
                "type": "viewpoint",
                "distance": random.uniform(0.5, 10.0),
                "detour_time": random.randint(5, 15),
                "uniqueness_score": random.uniform(60, 90),
                "best_time_of_day": random.choice(["morning", "afternoon", "sunset"]),
                "photo_worthy": True,
                "latitude": latitude + random.uniform(-0.05, 0.05),
                "longitude": longitude + random.uniform(-0.05, 0.05),
                "image_url": "https://example.com/sample_viewpoint.jpg"
            }
            
            if scenic_spot["uniqueness_score"] < self.context_thresholds["scenic_spot_min_score"]:
                return None
            
            # Check if the detour time is reasonable
            if scenic_spot["detour_time"] > self.context_thresholds["max_detour_time"]:
                return None
            
            # Create the scenic spot context
            context = {
                "id": str(uuid.uuid4()),
                "type": ContextType.SCENIC_SPOT,
                "detected_at": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "priority": 6,
                "title": "Scenic Spot Ahead",
                "description": f"Don't miss {scenic_spot['name']} just {scenic_spot['distance']:.1f} km away!",
                "category": "scenic",
                "icon": "scenic",
                "action_type": "show_scenic_spot",
                "expires_in_minutes": 60,
                "location": {
                    "latitude": scenic_spot["latitude"],
                    "longitude": scenic_spot["longitude"]
                },
                "data": {
                    "scenic_spot": scenic_spot,
                    "photo_tip": "This spot is perfect for panoramic photos."
                }
            }
            
            return context
        except Exception as e:
            logger.error(f"Error checking scenic spots: {str(e)}")
            return None
    
    async def _check_historical_poi(
        self,
        latitude: float,
        longitude: float,
        route_id: Optional[str],
        user_id: str,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Check for historical points of interest near the route.
        
        Args:
            latitude: Current latitude
            longitude: Current longitude
            route_id: Optional active route ID
            user_id: User ID
            user_preferences: Optional user preferences
            
        Returns:
            Historical POI context if relevant, None otherwise
        """
        try:
            # Check if user has interest in history
            has_history_interest = False
            if user_preferences and "interests" in user_preferences:
                has_history_interest = any(i in ["history", "historical", "heritage", "culture"] for i in user_preferences["interests"])
            
            # Adjust threshold based on interest
            threshold = self.context_thresholds["historical_poi_min_score"]
            if has_history_interest:
                threshold -= 10  # Lower threshold if user is interested in history
            
            # Simulate finding a historical point of interest
            historical_poi = {
                "id": str(uuid.uuid4()),
                "name": "Sample Historical Site",
                "description": "A significant historical location with an interesting past.",
                "historical_period": random.choice(["colonial", "civil_war", "roaring_twenties", "ancient", "medieval"]),
                "significance": random.choice(["local", "regional", "national"]),
                "distance": random.uniform(0.5, 8.0),
                "detour_time": random.randint(5, 20),
                "uniqueness_score": random.uniform(50, 85),
                "latitude": latitude + random.uniform(-0.03, 0.03),
                "longitude": longitude + random.uniform(-0.03, 0.03),
                "year_established": random.randint(1700, 1950),
                "image_url": "https://example.com/sample_historical_site.jpg"
            }
            
            if historical_poi["uniqueness_score"] < threshold:
                return None
            
            # Check if the detour time is reasonable
            if historical_poi["detour_time"] > self.context_thresholds["max_detour_time"]:
                return None
            
            # Create the historical POI context
            context = {
                "id": str(uuid.uuid4()),
                "type": ContextType.HISTORICAL_POI,
                "detected_at": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "priority": 5 if has_history_interest else 4,
                "title": "Historical Site Nearby",
                "description": f"Discover {historical_poi['name']}, est. {historical_poi['year_established']}, just {historical_poi['distance']:.1f} km away.",
                "category": "historical",
                "icon": "historical",
                "action_type": "show_historical_poi",
                "expires_in_minutes": 90,
                "location": {
                    "latitude": historical_poi["latitude"],
                    "longitude": historical_poi["longitude"]
                },
                "data": {
                    "historical_poi": historical_poi,
                    "matches_user_interest": has_history_interest
                }
            }
            
            return context
        except Exception as e:
            logger.error(f"Error checking historical POIs: {str(e)}")
            return None
    
    async def _check_upcoming_reservations(
        self,
        current_time: datetime,
        user_id: str,
        latitude: float,
        longitude: float,
        route_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Check for upcoming reservations and provide reminders.
        
        Args:
            current_time: Current time
            user_id: User ID
            latitude: Current latitude
            longitude: Current longitude
            route_id: Optional active route ID
            
        Returns:
            Reservation context if relevant, None otherwise
        """
        try:
            # Check for reservations in the next 2 hours
            time_threshold = current_time + timedelta(hours=2)
            
            # Query the database for upcoming reservations
            reservations = self.db.query(Reservation).filter(
                Reservation.user_id == user_id,
                Reservation.status == ReservationStatus.CONFIRMED.value,
                Reservation.reservation_time <= time_threshold,
                Reservation.reservation_time >= current_time
            ).order_by(Reservation.reservation_time).all()
            
            if not reservations:
                return None
            
            # Get the nearest upcoming reservation
            nearest_reservation = reservations[0]
            
            # Calculate time until reservation
            time_until = (nearest_reservation.reservation_time - current_time).total_seconds() / 60  # in minutes
            
            # In a real implementation, we would calculate the travel time to the venue
            # using a routing service. For now, we'll simulate it.
            estimated_travel_time = random.uniform(10, 60)  # in minutes
            
            # Determine if we need to alert the user
            needs_alert = time_until <= estimated_travel_time * 1.5  # Alert if reservation is within 1.5x travel time
            
            if not needs_alert:
                return None
            
            # Calculate priority based on urgency
            priority = 10 if time_until <= estimated_travel_time else 8
            
            # Create the reservation context
            context = {
                "id": str(uuid.uuid4()),
                "type": ContextType.ITINERARY_UPDATE,
                "detected_at": current_time.isoformat(),
                "user_id": user_id,
                "priority": priority,
                "title": f"Upcoming {nearest_reservation.type.capitalize()} Reservation",
                "description": f"Your reservation at {nearest_reservation.venue_name} is in {int(time_until)} minutes.",
                "category": "reservation",
                "icon": "calendar",
                "action_type": "show_reservation",
                "expires_in_minutes": min(60, int(time_until)),
                "location": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "data": {
                    "reservation": {
                        "id": nearest_reservation.id,
                        "type": nearest_reservation.type,
                        "venue_name": nearest_reservation.venue_name,
                        "venue_address": nearest_reservation.venue_address,
                        "reservation_time": nearest_reservation.reservation_time.isoformat(),
                        "confirmation_number": nearest_reservation.confirmation_number,
                        "status": nearest_reservation.status
                    },
                    "time_until_minutes": time_until,
                    "estimated_travel_time_minutes": estimated_travel_time,
                    "needs_to_leave_now": time_until <= estimated_travel_time,
                    "directions_available": True
                }
            }
            
            return context
        except Exception as e:
            logger.error(f"Error checking upcoming reservations: {str(e)}")
            return None
    
    async def _check_weather_alerts(
        self,
        weather_data: Dict[str, Any],
        latitude: float,
        longitude: float,
        route_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Check for weather alerts that could affect travel.
        
        Args:
            weather_data: Weather data
            latitude: Current latitude
            longitude: Current longitude
            route_id: Optional active route ID
            
        Returns:
            Weather alert context if relevant, None otherwise
        """
        try:
            # Check for severe weather conditions
            alerts = weather_data.get("alerts", [])
            current_condition = weather_data.get("current", {}).get("condition")
            
            if not alerts and not current_condition:
                return None
            
            # Process weather alerts
            relevant_alerts = []
            for alert in alerts:
                # In a real implementation, filter for relevant alerts based on severity, etc.
                if alert.get("severity") in ["severe", "extreme"]:
                    relevant_alerts.append(alert)
            
            # Check current conditions even if no alerts
            severe_conditions = ["thunderstorm", "snow", "sleet", "hail", "tornado", "hurricane", "blizzard", "flood"]
            caution_conditions = ["rain", "fog", "wind", "dust"]
            
            alert_level = None
            if any(condition in current_condition.lower() for condition in severe_conditions):
                alert_level = "severe"
            elif any(condition in current_condition.lower() for condition in caution_conditions):
                alert_level = "caution"
            
            if not relevant_alerts and not alert_level:
                return None
            
            # Determine priority based on severity
            priority = 10 if alert_level == "severe" or any(a.get("severity") == "extreme" for a in relevant_alerts) else 7
            
            # Create the weather alert context
            context = {
                "id": str(uuid.uuid4()),
                "type": ContextType.WEATHER_ALERT,
                "detected_at": datetime.utcnow().isoformat(),
                "user_id": "system",  # Weather alerts are system-wide
                "priority": priority,
                "title": "Weather Alert",
                "description": f"Weather conditions may affect your trip: {current_condition or relevant_alerts[0].get('title')}",
                "category": "weather",
                "icon": "weather_alert",
                "action_type": "show_weather",
                "expires_in_minutes": 120,
                "location": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "data": {
                    "alerts": relevant_alerts,
                    "current_condition": current_condition,
                    "alert_level": alert_level,
                    "driving_tips": "Reduce speed and increase following distance in adverse weather."
                }
            }
            
            return context
        except Exception as e:
            logger.error(f"Error checking weather alerts: {str(e)}")
            return None
    
    async def _check_fuel_reminder(
        self,
        vehicle_data: Dict[str, Any],
        latitude: float,
        longitude: float,
        route_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Check if the vehicle needs fuel/charging soon.
        
        Args:
            vehicle_data: Vehicle telemetry data
            latitude: Current latitude
            longitude: Current longitude
            route_id: Optional active route ID
            
        Returns:
            Fuel reminder context if relevant, None otherwise
        """
        try:
            # Get vehicle fuel/charge data
            fuel_level = vehicle_data.get("fuel_level_percent")
            battery_level = vehicle_data.get("battery_level_percent")
            range_remaining = vehicle_data.get("range_remaining_km")
            is_electric = vehicle_data.get("is_electric", False)
            
            # Determine if we need to alert based on either fuel or battery
            needs_alert = False
            low_threshold = 15  # Percentage
            critical_threshold = 10  # Percentage
            
            if is_electric and battery_level is not None:
                needs_alert = battery_level <= low_threshold
                is_critical = battery_level <= critical_threshold
            elif fuel_level is not None:
                needs_alert = fuel_level <= low_threshold
                is_critical = fuel_level <= critical_threshold
            elif range_remaining is not None:
                needs_alert = range_remaining <= self.context_thresholds[ContextType.FUEL_REMINDER]
                is_critical = range_remaining <= self.context_thresholds[ContextType.FUEL_REMINDER] * 0.5
            
            if not needs_alert:
                return None
            
            # Determine priority based on criticality
            priority = 10 if is_critical else 8
            
            # In a real implementation, we would search for nearby gas stations or charging stations
            # using a service like Google Places API
            nearby_stations = [
                {
                    "name": f"Sample {'Charging' if is_electric else 'Gas'} Station",
                    "distance": random.uniform(0.5, 10.0),
                    "price": random.uniform(2.5, 4.5) if not is_electric else None,
                    "rating": random.uniform(3.0, 4.5),
                    "is_open": True,
                    "has_amenities": random.choice([True, False]),
                    "latitude": latitude + random.uniform(-0.02, 0.02),
                    "longitude": longitude + random.uniform(-0.02, 0.02)
                }
                for _ in range(3)
            ]
            
            # Create the fuel reminder context
            context = {
                "id": str(uuid.uuid4()),
                "type": ContextType.FUEL_REMINDER,
                "detected_at": datetime.utcnow().isoformat(),
                "user_id": "vehicle",  # Fuel alerts are vehicle-specific
                "priority": priority,
                "title": f"{'Battery' if is_electric else 'Fuel'} Running Low",
                "description": f"{'Battery' if is_electric else 'Fuel'} level at {battery_level if is_electric else fuel_level}%. Finding nearby {'charging stations' if is_electric else 'gas stations'}.",
                "category": "vehicle",
                "icon": "fuel_alert",
                "action_type": "show_stations",
                "expires_in_minutes": 60,
                "location": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "data": {
                    "vehicle_type": "electric" if is_electric else "gas",
                    "level_percent": battery_level if is_electric else fuel_level,
                    "range_remaining_km": range_remaining,
                    "is_critical": is_critical,
                    "nearby_stations": nearby_stations
                }
            }
            
            return context
        except Exception as e:
            logger.error(f"Error checking fuel reminder: {str(e)}")
            return None
    
    async def _check_local_events(
        self,
        current_time: datetime,
        latitude: float,
        longitude: float,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Check for interesting local events happening soon.
        
        Args:
            current_time: Current time
            latitude: Current latitude
            longitude: Current longitude
            user_preferences: Optional user preferences
            
        Returns:
            Local event context if relevant, None otherwise
        """
        try:
            # In a real implementation, this would query event APIs like Eventbrite, Ticketmaster, etc.
            # For now, we'll simulate it
            
            # Get user interests
            interests = []
            if user_preferences and "interests" in user_preferences:
                interests = user_preferences["interests"]
            
            # Generate a random local event with 20% probability
            if random.random() > 0.2:
                return None
            
            # Create a simulated event that matches user interests if possible
            event_types = ["concert", "festival", "market", "sports", "art_exhibition", "food_fair"]
            matching_types = [et for et in event_types if any(i in et for i in interests)] if interests else event_types
            event_type = random.choice(matching_types if matching_types else event_types)
            
            # Time for the event (within next 6 hours)
            event_time = current_time + timedelta(hours=random.uniform(1, 6))
            
            local_event = {
                "id": str(uuid.uuid4()),
                "name": f"Sample {event_type.replace('_', ' ').title()}",
                "type": event_type,
                "description": f"A local {event_type.replace('_', ' ')} happening soon.",
                "start_time": event_time.isoformat(),
                "end_time": (event_time + timedelta(hours=random.uniform(1, 3))).isoformat(),
                "distance": random.uniform(0.5, 15.0),
                "venue_name": "Sample Venue",
                "venue_address": "123 Local St.",
                "ticket_required": random.choice([True, False]),
                "price": random.uniform(0, 50) if random.choice([True, False]) else 0,
                "latitude": latitude + random.uniform(-0.05, 0.05),
                "longitude": longitude + random.uniform(-0.05, 0.05),
                "popularity": random.uniform(3, 5)
            }
            
            # Calculate priority based on match to interests and timing
            base_priority = 5
            if interests and any(i in event_type for i in interests):
                base_priority += 1
            
            # Higher priority for events happening soon
            hours_until = (event_time - current_time).total_seconds() / 3600
            if hours_until < 2:
                base_priority += 1
            
            # Adjust for popularity
            if local_event["popularity"] > 4.5:
                base_priority += 1
            
            # Create the local event context
            context = {
                "id": str(uuid.uuid4()),
                "type": ContextType.LOCAL_EVENT,
                "detected_at": current_time.isoformat(),
                "user_id": "system",  # Local events are system-wide
                "priority": min(9, base_priority),
                "title": "Local Event Discovered",
                "description": f"{local_event['name']} at {local_event['venue_name']} starting at {event_time.strftime('%I:%M %p')}.",
                "category": "event",
                "icon": "event",
                "action_type": "show_event",
                "expires_in_minutes": int(hours_until * 60),
                "location": {
                    "latitude": local_event["latitude"],
                    "longitude": local_event["longitude"]
                },
                "data": {
                    "event": local_event,
                    "matches_user_interest": interests and any(i in event_type for i in interests),
                    "time_until_hours": hours_until
                }
            }
            
            return context
        except Exception as e:
            logger.error(f"Error checking local events: {str(e)}")
            return None
    
    async def _check_lodging_suggestions(
        self,
        current_time: datetime,
        latitude: float,
        longitude: float,
        route_id: Optional[str],
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Check if it's time to suggest lodging options for the night.
        
        Args:
            current_time: Current time
            latitude: Current latitude
            longitude: Current longitude
            route_id: Optional active route ID
            user_id: User ID
            
        Returns:
            Lodging suggestion context if relevant, None otherwise
        """
        try:
            # Check if it's evening (after 3 PM)
            local_time = current_time.time()
            if local_time.hour < 15:  # Before 3 PM
                return None
            
            # Higher priority as it gets later
            priority = 5
            if local_time.hour >= 18:  # After 6 PM
                priority = 8
            if local_time.hour >= 20:  # After 8 PM
                priority = 9
            
            # In a real implementation, this would query hotel APIs, Airbnb, etc.
            # For now, we'll simulate it
            lodging_options = [
                {
                    "name": "Sample Hotel",
                    "type": "hotel",
                    "price_range": f"${random.randint(70, 200)} - ${random.randint(200, 300)}",
                    "rating": random.uniform(3.0, 4.8),
                    "distance": random.uniform(0.5, 10.0),
                    "amenities": ["parking", "wifi", "breakfast", "pool"],
                    "availability": "available",
                    "latitude": latitude + random.uniform(-0.05, 0.05),
                    "longitude": longitude + random.uniform(-0.05, 0.05),
                    "image_url": "https://example.com/sample_hotel.jpg"
                },
                {
                    "name": "Sample Motel",
                    "type": "motel",
                    "price_range": f"${random.randint(40, 100)} - ${random.randint(100, 150)}",
                    "rating": random.uniform(2.5, 4.0),
                    "distance": random.uniform(0.5, 8.0),
                    "amenities": ["parking", "wifi"],
                    "availability": "available",
                    "latitude": latitude + random.uniform(-0.05, 0.05),
                    "longitude": longitude + random.uniform(-0.05, 0.05),
                    "image_url": "https://example.com/sample_motel.jpg"
                }
            ]
            
            # Create the lodging suggestion context
            context = {
                "id": str(uuid.uuid4()),
                "type": ContextType.LODGING,
                "detected_at": current_time.isoformat(),
                "user_id": user_id,
                "priority": priority,
                "title": "Time to Find Lodging?",
                "description": "It's getting late. Here are some nearby places to stay for the night.",
                "category": "lodging",
                "icon": "hotel",
                "action_type": "show_lodging",
                "expires_in_minutes": 180,
                "location": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "data": {
                    "lodging_options": lodging_options,
                    "current_time": current_time.isoformat(),
                    "booking_available": True
                }
            }
            
            return context
        except Exception as e:
            logger.error(f"Error checking lodging suggestions: {str(e)}")
            return None


def get_contextual_awareness(db: Session = Depends(get_db)) -> ContextualAwareness:
    """
    Dependency to get the contextual awareness service.
    
    Args:
        db: Database session dependency
        
    Returns:
        ContextualAwareness instance
    """
    return ContextualAwareness(db)