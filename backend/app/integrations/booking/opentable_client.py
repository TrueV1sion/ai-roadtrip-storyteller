"""
OpenTable Integration Client

Handles restaurant search, availability checking, and reservation management
through OpenTable's API. Supports both mock and live modes.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlencode
import hashlib
import hmac

import aiohttp
from aiohttp import ClientError, ClientResponseError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from app.core.logger import logger
from app.core.cache import cache_manager
from app.core.config import settings
from app.schemas.booking import (
    RestaurantSearchRequest,
    RestaurantAvailabilityRequest,
    RestaurantReservationRequest,
    BookingResponse,
    BookingStatus
)


class OpenTableClient:
    """Client for OpenTable restaurant reservations."""
    
    def __init__(self, api_key: Optional[str] = None, partner_id: Optional[str] = None):
        """Initialize OpenTable client."""
        self.api_key = api_key or settings.OPENTABLE_API_KEY
        self.partner_id = partner_id or settings.OPENTABLE_PARTNER_ID
        self.base_url = "https://platform.opentable.com/api/v2"
        self.timeout = aiohttp.ClientTimeout(total=15)
        
        # Rate limiting
        self.rate_limit_delay = 0.1  # 100ms between requests
        self._last_request_time = 0
        
        # Mock mode for testing
        self.mock_mode = not self.api_key or settings.ENVIRONMENT == "test"
        
        # Commission rates per diner
        self.commission_rates = {
            "standard": 2.50,  # $2.50 per diner
            "premium": 5.00,   # Premium time slots
            "special_event": 7.50  # Special events
        }
        
        if not self.api_key and not self.mock_mode:
            logger.warning("OpenTable API key not configured")
    
    async def _enforce_rate_limit(self):
        """Enforce rate limiting between requests."""
        import time
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)
        
        self._last_request_time = time.time()
    
    def _generate_auth_headers(self, method: str, endpoint: str, body: str = "") -> Dict[str, str]:
        """Generate authentication headers for OpenTable API."""
        timestamp = str(int(datetime.utcnow().timestamp()))
        
        # Create signature
        message = f"{method}\n{endpoint}\n{timestamp}\n{body}"
        signature = hmac.new(
            self.api_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return {
            "Authorization": f"Bearer {self.api_key}",
            "X-Partner-ID": self.partner_id,
            "X-Timestamp": timestamp,
            "X-Signature": signature,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ClientError, asyncio.TimeoutError)),
        before_sleep=before_sleep_log(logger, "WARNING")
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic."""
        if self.mock_mode:
            return self._get_mock_response(method, endpoint, params, json_data)
        
        await self._enforce_rate_limit()
        
        # Build full URL
        url = f"{self.base_url}/{endpoint}"
        
        # Generate cache key for GET requests
        if method == "GET":
            cache_key = f"opentable:{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
            cached_result = await cache_manager.get(cache_key)
            if cached_result:
                logger.debug(f"OpenTable cache hit for {endpoint}")
                return json.loads(cached_result)
        
        # Prepare request
        headers = self._generate_auth_headers(
            method,
            endpoint,
            json.dumps(json_data) if json_data else ""
        )
        
        logger.info(f"OpenTable API request: {method} {endpoint}")
        
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=json_data
                ) as response:
                    response_text = await response.text()
                    
                    if response.status == 200:
                        data = json.loads(response_text)
                        
                        # Cache successful GET responses for 5 minutes
                        if method == "GET":
                            await cache_manager.setex(
                                cache_key,
                                300,
                                json.dumps(data)
                            )
                        
                        return data
                    
                    elif response.status == 401:
                        raise ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message="Authentication failed"
                        )
                    
                    elif response.status == 404:
                        return None
                    
                    else:
                        raise ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message=f"API error: {response_text}"
                        )
                        
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in OpenTable API: {e}")
            raise
            
        except Exception as e:
            logger.error(f"OpenTable API error: {e}")
            raise
    
    async def search_restaurants(
        self,
        location: Dict[str, Any],
        cuisine: Optional[str] = None,
        party_size: int = 2,
        date: Optional[str] = None,
        time: Optional[str] = None,
        price_range: Optional[str] = None,
        radius_miles: float = 5.0
    ) -> Dict[str, Any]:
        """
        Search for restaurants.
        
        Args:
            location: Dict with latitude/longitude or city/state
            cuisine: Cuisine type filter
            party_size: Number of diners
            date: Date in YYYY-MM-DD format
            time: Time in HH:MM format
            price_range: Price range filter ($, $$, $$$, $$$$)
            radius_miles: Search radius in miles
            
        Returns:
            Dictionary with restaurants list and metadata
        """
        params = {
            "party_size": party_size,
            "radius": radius_miles
        }
        
        # Handle location
        if "latitude" in location and "longitude" in location:
            params["latitude"] = location["latitude"]
            params["longitude"] = location["longitude"]
        elif "city" in location:
            params["city"] = location["city"]
            if "state" in location:
                params["state"] = location["state"]
        else:
            raise ValueError("Location must include either lat/lon or city")
        
        # Add optional filters
        if cuisine:
            params["cuisine"] = cuisine
        if date:
            params["date"] = date
        if time:
            params["time"] = time
        if price_range:
            params["price_range"] = price_range
        
        try:
            response = await self._make_request("GET", "restaurants/search", params=params)
            
            if not response:
                return {"restaurants": [], "total": 0}
            
            # Process and enhance restaurant data
            restaurants = []
            for restaurant in response.get("restaurants", []):
                enhanced = self._enhance_restaurant_data(restaurant)
                restaurants.append(enhanced)
            
            return {
                "restaurants": restaurants,
                "total": len(restaurants),
                "search_params": params
            }
            
        except Exception as e:
            logger.error(f"Restaurant search failed: {e}")
            raise
    
    async def get_availability(
        self,
        restaurant_id: str,
        date: str,
        time: str,
        party_size: int
    ) -> Dict[str, Any]:
        """
        Check availability for a specific restaurant.
        
        Args:
            restaurant_id: Restaurant identifier
            date: Date in YYYY-MM-DD format
            time: Preferred time in HH:MM format
            party_size: Number of diners
            
        Returns:
            Dictionary with available time slots
        """
        params = {
            "date": date,
            "party_size": party_size,
            "time_preference": time
        }
        
        try:
            response = await self._make_request(
                "GET",
                f"restaurants/{restaurant_id}/availability",
                params=params
            )
            
            if not response:
                return {
                    "restaurant_id": restaurant_id,
                    "available_times": [],
                    "date": date
                }
            
            # Process availability slots
            available_times = []
            for slot in response.get("time_slots", []):
                if slot.get("available", False):
                    available_times.append(slot["time"])
            
            return {
                "restaurant_id": restaurant_id,
                "available_times": available_times,
                "date": date,
                "party_size": party_size
            }
            
        except Exception as e:
            logger.error(f"Availability check failed: {e}")
            raise
    
    async def create_reservation(
        self,
        restaurant_id: str,
        date: str,
        time: str,
        party_size: int,
        guest_info: Dict[str, str],
        special_requests: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a restaurant reservation.
        
        Args:
            restaurant_id: Restaurant identifier
            date: Date in YYYY-MM-DD format
            time: Time in HH:MM format
            party_size: Number of diners
            guest_info: Guest information (first_name, last_name, email, phone)
            special_requests: Optional special requests
            
        Returns:
            Reservation confirmation details
        """
        # Validate guest info
        required_fields = ["first_name", "last_name", "email", "phone"]
        for field in required_fields:
            if field not in guest_info:
                raise ValueError(f"Missing required guest info: {field}")
        
        # Build reservation request
        reservation_data = {
            "restaurant_id": restaurant_id,
            "date": date,
            "time": time,
            "party_size": party_size,
            "guest": {
                "first_name": guest_info["first_name"],
                "last_name": guest_info["last_name"],
                "email": guest_info["email"],
                "phone": guest_info["phone"]
            }
        }
        
        if special_requests:
            reservation_data["special_requests"] = special_requests
        
        try:
            response = await self._make_request(
                "POST",
                "reservations",
                json_data=reservation_data
            )
            
            if not response:
                raise Exception("Failed to create reservation")
            
            # Calculate commission
            commission = self._calculate_commission(
                party_size,
                date,
                time,
                response.get("restaurant_type", "standard")
            )
            
            # Format response
            return {
                "confirmation_number": response.get("confirmation_number"),
                "restaurant_name": response.get("restaurant_name"),
                "restaurant_id": restaurant_id,
                "date": date,
                "time": time,
                "party_size": party_size,
                "status": "confirmed",
                "guest_name": f"{guest_info['first_name']} {guest_info['last_name']}",
                "commission_amount": commission,
                "cancellation_policy": response.get("cancellation_policy", "24 hours notice required"),
                "reservation_url": response.get("reservation_url")
            }
            
        except Exception as e:
            logger.error(f"Reservation creation failed: {e}")
            raise
    
    async def get_reservation(
        self,
        confirmation_number: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get reservation details.
        
        Args:
            confirmation_number: Reservation confirmation number
            
        Returns:
            Reservation details or None if not found
        """
        try:
            response = await self._make_request(
                "GET",
                f"reservations/{confirmation_number}"
            )
            
            if not response:
                return None
            
            return {
                "confirmation_number": confirmation_number,
                "restaurant_name": response.get("restaurant_name"),
                "date": response.get("date"),
                "time": response.get("time"),
                "party_size": response.get("party_size"),
                "status": response.get("status", "confirmed"),
                "guest_name": response.get("guest_name"),
                "special_requests": response.get("special_requests")
            }
            
        except Exception as e:
            logger.error(f"Failed to get reservation: {e}")
            return None
    
    async def cancel_reservation(
        self,
        confirmation_number: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancel a reservation.
        
        Args:
            confirmation_number: Reservation confirmation number
            reason: Optional cancellation reason
            
        Returns:
            Cancellation confirmation
        """
        cancel_data = {}
        if reason:
            cancel_data["cancellation_reason"] = reason
        
        try:
            response = await self._make_request(
                "DELETE",
                f"reservations/{confirmation_number}",
                json_data=cancel_data
            )
            
            return {
                "status": "cancelled",
                "confirmation_number": confirmation_number,
                "cancelled_at": datetime.utcnow().isoformat(),
                "refund_amount": response.get("refund_amount", 0)
            }
            
        except Exception as e:
            logger.error(f"Reservation cancellation failed: {e}")
            raise
    
    def _enhance_restaurant_data(self, restaurant: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance restaurant data with additional information."""
        return {
            "id": restaurant.get("id"),
            "name": restaurant.get("name"),
            "cuisine": restaurant.get("cuisine_type", "American"),
            "price_range": restaurant.get("price_range", "$$"),
            "rating": restaurant.get("rating", 4.0),
            "review_count": restaurant.get("review_count", 0),
            "location": {
                "address": restaurant.get("address"),
                "city": restaurant.get("city"),
                "state": restaurant.get("state"),
                "zip_code": restaurant.get("zip_code"),
                "latitude": restaurant.get("latitude"),
                "longitude": restaurant.get("longitude")
            },
            "phone": restaurant.get("phone"),
            "website": restaurant.get("website"),
            "hours": restaurant.get("hours", {}),
            "features": restaurant.get("features", []),
            "description": restaurant.get("description", ""),
            "photos": restaurant.get("photos", []),
            "booking_fee": restaurant.get("booking_fee", 0),
            "cancellation_policy": restaurant.get("cancellation_policy", "24 hours notice")
        }
    
    def _calculate_commission(
        self,
        party_size: int,
        date: str,
        time: str,
        restaurant_type: str = "standard"
    ) -> float:
        """Calculate commission for a reservation."""
        # Parse time to check if it's premium
        hour = int(time.split(":")[0])
        is_premium_time = 18 <= hour <= 21  # 6 PM - 9 PM
        
        # Parse date to check if weekend
        reservation_date = datetime.strptime(date, "%Y-%m-%d")
        is_weekend = reservation_date.weekday() >= 5
        
        # Determine rate
        if restaurant_type == "special_event":
            rate = self.commission_rates["special_event"]
        elif is_premium_time and is_weekend:
            rate = self.commission_rates["premium"]
        else:
            rate = self.commission_rates["standard"]
        
        # Calculate total commission
        return rate * party_size
    
    def _get_mock_response(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Return mock responses for testing."""
        if "search" in endpoint:
            return {
                "restaurants": [
                    {
                        "id": "mock_restaurant_1",
                        "name": "Mock Italian Bistro",
                        "cuisine_type": "Italian",
                        "price_range": "$$",
                        "rating": 4.5,
                        "review_count": 324,
                        "address": "123 Mock St",
                        "city": params.get("city", "San Francisco"),
                        "state": params.get("state", "CA"),
                        "latitude": params.get("latitude", 37.7749),
                        "longitude": params.get("longitude", -122.4194)
                    },
                    {
                        "id": "mock_restaurant_2",
                        "name": "Mock Steakhouse",
                        "cuisine_type": "Steakhouse",
                        "price_range": "$$$",
                        "rating": 4.7,
                        "review_count": 567,
                        "address": "456 Test Ave",
                        "city": params.get("city", "San Francisco"),
                        "state": params.get("state", "CA")
                    }
                ]
            }
        
        elif "availability" in endpoint:
            # Generate mock time slots
            base_time = datetime.strptime(params.get("time_preference", "19:00"), "%H:%M")
            time_slots = []
            
            for i in range(-2, 3):  # 5 slots, 30 min apart
                slot_time = base_time + timedelta(minutes=30 * i)
                time_slots.append({
                    "time": slot_time.strftime("%H:%M"),
                    "available": i != 0  # Make preferred time unavailable for testing
                })
            
            return {"time_slots": time_slots}
        
        elif method == "POST" and "reservations" in endpoint:
            return {
                "confirmation_number": f"OT{int(datetime.utcnow().timestamp())}",
                "restaurant_name": "Mock Italian Bistro",
                "restaurant_type": "standard",
                "cancellation_policy": "Free cancellation up to 24 hours before",
                "reservation_url": "https://opentable.com/mock-reservation"
            }
        
        elif method == "GET" and "reservations/" in endpoint:
            return {
                "restaurant_name": "Mock Italian Bistro",
                "date": "2024-02-20",
                "time": "19:00",
                "party_size": 2,
                "status": "confirmed",
                "guest_name": "Test User"
            }
        
        elif method == "DELETE":
            return {"refund_amount": 0}
        
        return {}


# Global instance
opentable_client = OpenTableClient()