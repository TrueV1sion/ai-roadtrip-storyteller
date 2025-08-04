"""
Airport Dining Integration Client

Handles integration with airport restaurant reservation systems and
dining directories. Supports multiple restaurant booking platforms.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import aiohttp
from urllib.parse import urljoin

from app.core.config import settings
from app.core.logger import get_logger
from app.core.cache import get_cache

logger = get_logger(__name__)


class AirportDiningClient:
    """Client for airport dining integrations"""
    
    def __init__(self):
        self.base_url = "https://api.airportdining.com/v1/"
        self.api_key = settings.AIRPORT_DINING_API_KEY
        self.cache = get_cache()
        self.session = None
        self._mock_mode = not self.api_key or self.api_key == "mock"
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json"
                }
            )
        return self.session
    
    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def get_restaurants(
        self,
        airport_code: str,
        terminal: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get restaurants at an airport"""
        if self._mock_mode:
            return self._get_mock_restaurants(airport_code, terminal)
        
        try:
            # Check cache
            cache_key = f"airport_dining:{airport_code}:{terminal}"
            cached = await self.cache.get(cache_key)
            if cached:
                return cached
            
            session = await self._get_session()
            params = {
                "airport": airport_code,
                "status": "open"
            }
            if terminal:
                params["terminal"] = terminal
            
            async with session.get(
                urljoin(self.base_url, "restaurants"),
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    restaurants = data.get("restaurants", [])
                    
                    # Cache for 30 minutes
                    await self.cache.set(cache_key, restaurants, expire=1800)
                    return restaurants
                else:
                    logger.error(f"Airport dining API error: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Failed to get restaurants: {e}")
            return self._get_mock_restaurants(airport_code, terminal)
    
    def _get_mock_restaurants(
        self,
        airport_code: str,
        terminal: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return mock restaurant data"""
        mock_restaurants = {
            "LAX": [
                {
                    "id": "lax_rest_001",
                    "name": "The Proud Bird",
                    "description": "Upscale dining with runway views",
                    "terminal": "4",
                    "gate_area": "Gates 40-49",
                    "location": "Near Gate 42, Upper Level",
                    "hours": {
                        "monday": "06:00-22:00",
                        "tuesday": "06:00-22:00",
                        "wednesday": "06:00-22:00",
                        "thursday": "06:00-22:00",
                        "friday": "06:00-23:00",
                        "saturday": "06:00-23:00",
                        "sunday": "06:00-22:00"
                    },
                    "cuisine_types": ["American", "Steakhouse"],
                    "price_range": "$$$",
                    "rating": 4.3,
                    "reviews_count": 892,
                    "features": [
                        "Full Bar",
                        "Runway Views",
                        "Table Service",
                        "Vegetarian Options",
                        "Gluten-Free Menu"
                    ],
                    "accepts_reservations": True,
                    "average_wait": 15,
                    "reservation_url": "https://reservations.proudbird.com",
                    "images": [
                        "https://example.com/proudbird1.jpg",
                        "https://example.com/proudbird2.jpg"
                    ]
                },
                {
                    "id": "lax_rest_002",
                    "name": "Umami Burger",
                    "description": "Gourmet burgers and craft beer",
                    "terminal": "4",
                    "gate_area": "Gates 40-49",
                    "location": "Food Court, Lower Level",
                    "hours": {
                        "monday": "05:00-23:00",
                        "tuesday": "05:00-23:00",
                        "wednesday": "05:00-23:00",
                        "thursday": "05:00-23:00",
                        "friday": "05:00-23:00",
                        "saturday": "05:00-23:00",
                        "sunday": "05:00-23:00"
                    },
                    "cuisine_types": ["American", "Burgers"],
                    "price_range": "$$",
                    "rating": 4.1,
                    "reviews_count": 1567,
                    "features": [
                        "Quick Service",
                        "Craft Beer",
                        "Vegetarian Options",
                        "To-Go Available"
                    ],
                    "accepts_reservations": False,
                    "average_wait": 10,
                    "images": []
                },
                {
                    "id": "lax_rest_003",
                    "name": "Petrossian Bar",
                    "description": "Champagne bar with caviar service",
                    "terminal": "B",
                    "gate_area": "International Terminal",
                    "location": "Great Hall, Upper Level",
                    "hours": {
                        "monday": "11:00-23:00",
                        "tuesday": "11:00-23:00",
                        "wednesday": "11:00-23:00",
                        "thursday": "11:00-23:00",
                        "friday": "11:00-23:00",
                        "saturday": "11:00-23:00",
                        "sunday": "11:00-23:00"
                    },
                    "cuisine_types": ["French", "Seafood", "Bar"],
                    "price_range": "$$$$",
                    "rating": 4.7,
                    "reviews_count": 432,
                    "features": [
                        "Champagne Bar",
                        "Caviar Service",
                        "Small Plates",
                        "Premium Spirits"
                    ],
                    "accepts_reservations": True,
                    "average_wait": 5,
                    "reservation_url": "https://petrossian.com/reserve",
                    "images": []
                }
            ],
            "JFK": [
                {
                    "id": "jfk_rest_001",
                    "name": "Deep Blue Sushi",
                    "description": "Fresh sushi and Japanese cuisine",
                    "terminal": "4",
                    "gate_area": "Concourse B",
                    "location": "Near Gate B20",
                    "hours": {
                        "monday": "10:00-22:00",
                        "tuesday": "10:00-22:00",
                        "wednesday": "10:00-22:00",
                        "thursday": "10:00-22:00",
                        "friday": "10:00-22:00",
                        "saturday": "10:00-22:00",
                        "sunday": "10:00-22:00"
                    },
                    "cuisine_types": ["Japanese", "Sushi"],
                    "price_range": "$$$",
                    "rating": 4.4,
                    "reviews_count": 656,
                    "features": [
                        "Sushi Bar",
                        "Hot Entrees",
                        "Sake Selection",
                        "Gluten-Free Options"
                    ],
                    "accepts_reservations": True,
                    "average_wait": 20,
                    "images": []
                },
                {
                    "id": "jfk_rest_002",
                    "name": "Shake Shack",
                    "description": "Classic burgers and shakes",
                    "terminal": "4",
                    "gate_area": "Concourse B",
                    "location": "Food Court Area",
                    "hours": {
                        "monday": "05:00-23:00",
                        "tuesday": "05:00-23:00",
                        "wednesday": "05:00-23:00",
                        "thursday": "05:00-23:00",
                        "friday": "05:00-23:00",
                        "saturday": "05:00-23:00",
                        "sunday": "05:00-23:00"
                    },
                    "cuisine_types": ["American", "Fast Food"],
                    "price_range": "$",
                    "rating": 4.0,
                    "reviews_count": 2341,
                    "features": [
                        "Quick Service",
                        "Milkshakes",
                        "Mobile Ordering"
                    ],
                    "accepts_reservations": False,
                    "average_wait": 15,
                    "images": []
                }
            ]
        }
        
        restaurants = mock_restaurants.get(airport_code, [])
        if terminal:
            restaurants = [r for r in restaurants if r["terminal"] == terminal]
        
        return restaurants
    
    async def check_availability(
        self,
        restaurant_id: str,
        party_size: int,
        preferred_time: datetime,
        duration_minutes: int = 60
    ) -> Optional[Dict[str, Any]]:
        """Check restaurant availability"""
        if self._mock_mode:
            return self._get_mock_availability(
                restaurant_id, party_size, preferred_time, duration_minutes
            )
        
        try:
            session = await self._get_session()
            
            data = {
                "restaurant_id": restaurant_id,
                "party_size": party_size,
                "date": preferred_time.date().isoformat(),
                "time": preferred_time.time().isoformat(),
                "duration_minutes": duration_minutes
            }
            
            async with session.post(
                urljoin(self.base_url, "availability"),
                json=data
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Availability check error: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to check availability: {e}")
            return None
    
    def _get_mock_availability(
        self,
        restaurant_id: str,
        party_size: int,
        preferred_time: datetime,
        duration_minutes: int
    ) -> Dict[str, Any]:
        """Return mock availability data"""
        # Generate available times around preferred time
        available_times = []
        base_time = preferred_time.replace(minute=0, second=0, microsecond=0)
        
        for offset in [-60, -30, 0, 30, 60]:
            time_slot = base_time + timedelta(minutes=offset)
            if time_slot >= datetime.now():
                available_times.append(time_slot)
        
        # Mock cuisine based on restaurant ID
        cuisines = {
            "lax_rest_001": "American",
            "lax_rest_002": "American",
            "lax_rest_003": "French",
            "jfk_rest_001": "Japanese",
            "jfk_rest_002": "American"
        }
        
        prices = {
            "lax_rest_001": 45,
            "lax_rest_002": 25,
            "lax_rest_003": 85,
            "jfk_rest_001": 55,
            "jfk_rest_002": 15
        }
        
        return {
            "restaurant_id": restaurant_id,
            "times": available_times[:3],  # Return up to 3 slots
            "party_sizes": list(range(max(1, party_size - 1), min(8, party_size + 2))),
            "cuisine": cuisines.get(restaurant_id, "International"),
            "dietary_options": ["Vegetarian", "Gluten-Free", "Vegan Available"],
            "avg_duration": 45,
            "avg_price": prices.get(restaurant_id, 35)
        }
    
    async def book_restaurant(
        self,
        restaurant_id: str,
        user_id: str,
        booking_details: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Book restaurant reservation"""
        if self._mock_mode:
            return self._mock_book_restaurant(restaurant_id, user_id, booking_details)
        
        try:
            session = await self._get_session()
            
            booking_data = {
                "restaurant_id": restaurant_id,
                "user_id": user_id,
                "party_size": booking_details["party_size"],
                "reservation_time": booking_details["reservation_time"].isoformat(),
                "special_requests": booking_details.get("special_requests", ""),
                "contact_info": {
                    "name": booking_details.get("name"),
                    "phone": booking_details.get("phone"),
                    "email": booking_details.get("email")
                },
                "flight_info": {
                    "airline": booking_details.get("airline"),
                    "flight_number": booking_details.get("flight_number"),
                    "departure_time": booking_details.get("departure_time")
                }
            }
            
            async with session.post(
                urljoin(self.base_url, "reservations"),
                json=booking_data
            ) as response:
                if response.status == 201:
                    return await response.json()
                else:
                    error_data = await response.json()
                    logger.error(f"Restaurant booking failed: {error_data}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to book restaurant: {e}")
            return None
    
    def _mock_book_restaurant(
        self,
        restaurant_id: str,
        user_id: str,
        booking_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mock restaurant booking"""
        booking_id = f"ARD{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Get restaurant info
        restaurant_names = {
            "lax_rest_001": "The Proud Bird",
            "lax_rest_002": "Umami Burger",
            "lax_rest_003": "Petrossian Bar",
            "jfk_rest_001": "Deep Blue Sushi",
            "jfk_rest_002": "Shake Shack"
        }
        
        return {
            "booking_id": booking_id,
            "confirmation_number": booking_id,
            "restaurant_id": restaurant_id,
            "restaurant_name": restaurant_names.get(restaurant_id, "Airport Restaurant"),
            "status": "confirmed",
            "reservation_time": booking_details["reservation_time"].isoformat(),
            "party_size": booking_details["party_size"],
            "table_number": None,  # Assigned on arrival
            "special_requests": booking_details.get("special_requests", ""),
            "cancellation_policy": "Free cancellation up to 1 hour before reservation",
            "modification_url": f"https://airportdining.com/modify/{booking_id}",
            "restaurant_phone": "+1-555-0123",
            "estimated_duration": 60,
            "qr_code": f"https://airportdining.com/qr/{booking_id}"
        }
    
    async def get_wait_times(
        self,
        airport_code: str,
        terminal: Optional[str] = None
    ) -> Dict[str, int]:
        """Get current wait times for restaurants"""
        if self._mock_mode:
            # Mock wait times
            import random
            restaurants = await self.get_restaurants(airport_code, terminal)
            wait_times = {}
            for restaurant in restaurants:
                if not restaurant.get("accepts_reservations"):
                    wait_times[restaurant["id"]] = random.randint(5, 45)
            return wait_times
        
        try:
            session = await self._get_session()
            params = {"airport": airport_code}
            if terminal:
                params["terminal"] = terminal
            
            async with session.get(
                urljoin(self.base_url, "wait-times"),
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("wait_times", {})
                else:
                    logger.error(f"Wait times query error: {response.status}")
                    return {}
                    
        except Exception as e:
            logger.error(f"Failed to get wait times: {e}")
            return {}
    
    async def search_by_cuisine(
        self,
        airport_code: str,
        cuisine_types: List[str],
        terminal: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search restaurants by cuisine type"""
        restaurants = await self.get_restaurants(airport_code, terminal)
        
        # Filter by cuisine
        filtered = []
        for restaurant in restaurants:
            restaurant_cuisines = [c.lower() for c in restaurant.get("cuisine_types", [])]
            if any(cuisine.lower() in restaurant_cuisines for cuisine in cuisine_types):
                filtered.append(restaurant)
        
        return filtered
    
    async def get_dietary_options(
        self,
        restaurant_id: str
    ) -> Dict[str, List[str]]:
        """Get detailed dietary options for a restaurant"""
        if self._mock_mode:
            return {
                "vegetarian": ["Veggie Burger", "Garden Salad", "Pasta Primavera"],
                "vegan": ["Beyond Burger", "Quinoa Bowl"],
                "gluten_free": ["Grilled Chicken", "Salmon", "GF Pizza"],
                "halal": ["Chicken Shawarma", "Lamb Kebab"],
                "kosher": ["Bagel & Lox", "Hummus Plate"]
            }
        
        try:
            session = await self._get_session()
            async with session.get(
                urljoin(self.base_url, f"restaurants/{restaurant_id}/dietary")
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Dietary options query error: {response.status}")
                    return {}
                    
        except Exception as e:
            logger.error(f"Failed to get dietary options: {e}")
            return {}