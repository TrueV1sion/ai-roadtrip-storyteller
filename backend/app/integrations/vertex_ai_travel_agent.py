"""
Vertex AI Travel Agent Integration
Provides travel booking capabilities through Google's pre-built agent
Completely invisible to the user - works through our unified voice interface
"""

import os
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, date
from google.cloud import aiplatform
from google.cloud.aiplatform_v1beta1 import (
    AgentServiceClient,
    SessionServiceClient,
    Content,
    Part,
    GenerateContentRequest,
)
import logging

logger = logging.getLogger(__name__)


class VertexAITravelAgent:
    """
    Integration with Google's Vertex AI Travel Concierge Agent
    Handles hotels, flights, restaurants, and activities
    """
    
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("VERTEX_AI_LOCATION", "us-central1")
        self.agent_id = os.getenv("VERTEX_TRAVEL_AGENT_ID")
        
        # Initialize clients
        self.agent_client = AgentServiceClient()
        self.session_client = SessionServiceClient()
        
        # Agent resource path
        self.agent_name = (
            f"projects/{self.project_id}/locations/{self.location}/"
            f"agents/{self.agent_id}"
        )
        
        # Session management
        self.sessions: Dict[str, str] = {}
        
        logger.info("Vertex AI Travel Agent initialized")
    
    async def search_hotels(
        self,
        latitude: float,
        longitude: float,
        check_in_date: date,
        nights: int = 1,
        preferences: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for hotels using the Travel Agent
        Returns results formatted for our voice interface
        """
        try:
            # Format query for the Travel Agent
            query = self._build_hotel_query(
                latitude, longitude, check_in_date, nights, preferences
            )
            
            # Send to Travel Agent
            response = await self._query_agent(
                query,
                tool_name="hotel_search"
            )
            
            # Parse and format results
            hotels = self._parse_hotel_results(response)
            
            # Sort by our criteria (rating, distance, price)
            hotels = self._rank_hotels(hotels, preferences)
            
            return hotels[:5]  # Top 5 options
            
        except Exception as e:
            logger.error(f"Hotel search failed: {e}")
            return []
    
    async def book_hotel(
        self,
        hotel_id: str,
        check_in_date: date,
        nights: int,
        guest_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Book a hotel through the Travel Agent
        Returns confirmation details
        """
        try:
            booking_request = {
                "hotel_id": hotel_id,
                "check_in": check_in_date.isoformat(),
                "nights": nights,
                "guests": guest_details
            }
            
            response = await self._query_agent(
                f"Book hotel {hotel_id} for {nights} nights starting {check_in_date}",
                tool_name="hotel_booking",
                parameters=booking_request
            )
            
            return self._parse_booking_confirmation(response)
            
        except Exception as e:
            logger.error(f"Hotel booking failed: {e}")
            raise
    
    async def search_restaurants(
        self,
        latitude: float,
        longitude: float,
        radius_miles: float = 10,
        preferences: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for restaurants using the Travel Agent
        """
        try:
            query = self._build_restaurant_query(
                latitude, longitude, radius_miles, preferences
            )
            
            response = await self._query_agent(
                query,
                tool_name="restaurant_search"
            )
            
            restaurants = self._parse_restaurant_results(response)
            
            # Enhance with distance and travel time
            for restaurant in restaurants:
                restaurant["distance_miles"] = self._calculate_distance(
                    latitude, longitude,
                    restaurant["latitude"], restaurant["longitude"]
                )
                restaurant["drive_time_minutes"] = int(restaurant["distance_miles"] * 2)
            
            return sorted(restaurants, key=lambda r: r["distance_miles"])
            
        except Exception as e:
            logger.error(f"Restaurant search failed: {e}")
            return []
    
    async def search_activities(
        self,
        latitude: float,
        longitude: float,
        interests: List[str],
        time_available_hours: float = 2
    ) -> List[Dict[str, Any]]:
        """
        Find activities and attractions
        """
        try:
            query = f"""Find activities near {latitude},{longitude} that match 
            interests: {', '.join(interests)} and can be done in {time_available_hours} hours"""
            
            response = await self._query_agent(
                query,
                tool_name="activity_search"
            )
            
            activities = self._parse_activity_results(response)
            
            # Filter by time available
            suitable_activities = [
                a for a in activities 
                if a.get("duration_hours", 1) <= time_available_hours
            ]
            
            return suitable_activities
            
        except Exception as e:
            logger.error(f"Activity search failed: {e}")
            return []
    
    async def get_flight_info(
        self,
        origin: str,
        destination: str,
        date: date
    ) -> List[Dict[str, Any]]:
        """
        Get flight options for airport trips
        """
        try:
            query = f"Find flights from {origin} to {destination} on {date}"
            
            response = await self._query_agent(
                query,
                tool_name="flight_search"
            )
            
            return self._parse_flight_results(response)
            
        except Exception as e:
            logger.error(f"Flight search failed: {e}")
            return []
    
    def _build_hotel_query(
        self,
        lat: float,
        lng: float,
        check_in: date,
        nights: int,
        preferences: Dict[str, Any]
    ) -> str:
        """Build natural language query for hotel search"""
        query_parts = [
            f"Find hotels near {lat},{lng}",
            f"for {nights} night(s) starting {check_in}"
        ]
        
        if preferences:
            if preferences.get("budget"):
                query_parts.append(f"under ${preferences['budget']} per night")
            if preferences.get("amenities"):
                query_parts.append(f"with {', '.join(preferences['amenities'])}")
            if preferences.get("rating_min"):
                query_parts.append(f"rated {preferences['rating_min']} stars or higher")
        
        return " ".join(query_parts)
    
    def _build_restaurant_query(
        self,
        lat: float,
        lng: float,
        radius: float,
        preferences: Dict[str, Any]
    ) -> str:
        """Build natural language query for restaurant search"""
        query_parts = [
            f"Find restaurants within {radius} miles of {lat},{lng}"
        ]
        
        if preferences:
            if preferences.get("cuisine"):
                query_parts.append(f"serving {preferences['cuisine']} cuisine")
            if preferences.get("price_range"):
                query_parts.append(f"with {'$' * preferences['price_range']} pricing")
            if preferences.get("dietary"):
                query_parts.append(f"with {preferences['dietary']} options")
        
        return " ".join(query_parts)
    
    async def _query_agent(
        self,
        query: str,
        tool_name: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send query to the Travel Agent and get response
        """
        # Get or create session
        if not session_id:
            session_id = f"session_{datetime.now().timestamp()}"
        
        session_path = f"{self.agent_name}/sessions/{session_id}"
        
        # Build the request
        text_input = Content(
            parts=[Part(text=query)],
            role="user"
        )
        
        # If specific tool requested, add tool use instructions
        if tool_name:
            query = f"Use the {tool_name} tool to: {query}"
        
        # Send to agent
        request = GenerateContentRequest(
            session=session_path,
            contents=[text_input]
        )
        
        # Get response (this would be async in production)
        response = await asyncio.to_thread(
            self.session_client.generate_content,
            request=request
        )
        
        # Parse response
        return self._parse_agent_response(response)
    
    def _parse_agent_response(self, response) -> Dict[str, Any]:
        """Extract structured data from agent response"""
        # The response format depends on Vertex AI Agent Builder
        # This is a simplified parser
        
        result = {
            "raw_response": response,
            "parsed_data": {},
            "tool_results": []
        }
        
        # Extract tool call results if present
        for candidate in response.candidates:
            for part in candidate.content.parts:
                if hasattr(part, 'function_response'):
                    result["tool_results"].append(part.function_response)
                elif hasattr(part, 'text'):
                    result["parsed_data"]["text"] = part.text
        
        return result
    
    def _parse_hotel_results(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse hotel search results into our format"""
        hotels = []
        
        # Extract from tool results
        for tool_result in response.get("tool_results", []):
            if "hotels" in tool_result:
                for hotel in tool_result["hotels"]:
                    hotels.append({
                        "hotel_id": hotel.get("id"),
                        "name": hotel.get("name"),
                        "rating": hotel.get("rating", 0),
                        "price_per_night": hotel.get("price", {}).get("amount", 0),
                        "amenities": hotel.get("amenities", []),
                        "latitude": hotel.get("location", {}).get("lat"),
                        "longitude": hotel.get("location", {}).get("lng"),
                        "description": hotel.get("description", ""),
                        "images": hotel.get("images", [])[:3],  # Top 3 images
                        "availability": True  # Assumed from search results
                    })
        
        return hotels
    
    def _parse_restaurant_results(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse restaurant search results"""
        restaurants = []
        
        for tool_result in response.get("tool_results", []):
            if "restaurants" in tool_result:
                for restaurant in tool_result["restaurants"]:
                    restaurants.append({
                        "place_id": restaurant.get("place_id"),
                        "name": restaurant.get("name"),
                        "cuisine": restaurant.get("cuisine_type"),
                        "rating": restaurant.get("rating", 0),
                        "price_level": restaurant.get("price_level", 2),
                        "latitude": restaurant.get("location", {}).get("lat"),
                        "longitude": restaurant.get("location", {}).get("lng"),
                        "specialty": restaurant.get("known_for", "their food"),
                        "wait_time": "20 minutes",  # Would come from integration
                        "phone": restaurant.get("phone")
                    })
        
        return restaurants
    
    def _parse_booking_confirmation(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse booking confirmation"""
        # Extract confirmation from tool results
        for tool_result in response.get("tool_results", []):
            if "confirmation" in tool_result:
                return {
                    "confirmation_number": tool_result["confirmation"]["number"],
                    "status": "confirmed",
                    "details": tool_result["confirmation"]["details"],
                    "cancellation_policy": tool_result["confirmation"].get("cancellation_policy")
                }
        
        raise Exception("No confirmation found in response")
    
    def _rank_hotels(
        self,
        hotels: List[Dict[str, Any]],
        preferences: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Rank hotels based on user preferences"""
        # Simple scoring algorithm
        for hotel in hotels:
            score = 0
            
            # Rating weight
            score += hotel.get("rating", 0) * 20
            
            # Price weight (inverse - cheaper is better unless luxury preferred)
            if preferences and preferences.get("luxury"):
                score += hotel.get("price_per_night", 0) * 0.1
            else:
                score += (500 - hotel.get("price_per_night", 200)) * 0.1
            
            # Amenity matches
            if preferences and preferences.get("amenities"):
                wanted_amenities = set(preferences["amenities"])
                hotel_amenities = set(hotel.get("amenities", []))
                matches = len(wanted_amenities & hotel_amenities)
                score += matches * 10
            
            hotel["relevance_score"] = score
        
        return sorted(hotels, key=lambda h: h["relevance_score"], reverse=True)
    
    def _calculate_distance(
        self,
        lat1: float, lng1: float,
        lat2: float, lng2: float
    ) -> float:
        """Calculate distance in miles between two points"""
        # Simplified haversine formula
        import math
        
        R = 3959  # Earth's radius in miles
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def _parse_activity_results(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse activity search results"""
        activities = []
        
        for tool_result in response.get("tool_results", []):
            if "activities" in tool_result:
                for activity in tool_result["activities"]:
                    activities.append({
                        "id": activity.get("id"),
                        "name": activity.get("name"),
                        "type": activity.get("type"),
                        "duration_hours": activity.get("duration", {}).get("hours", 1),
                        "price": activity.get("price", {}).get("amount", 0),
                        "description": activity.get("description"),
                        "rating": activity.get("rating", 0),
                        "suitable_for": activity.get("suitable_for", [])
                    })
        
        return activities
    
    def _parse_flight_results(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse flight search results"""
        flights = []
        
        for tool_result in response.get("tool_results", []):
            if "flights" in tool_result:
                for flight in tool_result["flights"]:
                    flights.append({
                        "flight_number": flight.get("flight_number"),
                        "airline": flight.get("airline"),
                        "departure_time": flight.get("departure"),
                        "arrival_time": flight.get("arrival"),
                        "duration_minutes": flight.get("duration"),
                        "price": flight.get("price", {}).get("amount", 0),
                        "seats_available": flight.get("availability", True)
                    })
        
        return sorted(flights, key=lambda f: f["price"])