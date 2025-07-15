"""OpenTable restaurant booking integration client with production-ready features."""

import asyncio
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import aiohttp
from aiohttp import ClientError, ClientResponseError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from backend.app.core.logger import logger
from backend.app.core.cache import cache_manager


class OpenTableClient:
    """Production-ready client for OpenTable restaurant booking API integration."""
    
    # API Error codes mapping
    ERROR_CODES = {
        "RESTAURANT_NOT_FOUND": "The requested restaurant could not be found",
        "NO_AVAILABILITY": "No tables available for the requested time",
        "INVALID_PARTY_SIZE": "Party size exceeds restaurant capacity",
        "BOOKING_WINDOW_EXCEEDED": "Booking too far in advance",
        "DUPLICATE_RESERVATION": "A reservation already exists for this time",
        "PAYMENT_REQUIRED": "Payment information required for this reservation",
        "RESTAURANT_CLOSED": "Restaurant is closed on the selected date"
    }
    
    def __init__(self):
        """Initialize OpenTable client with production configuration."""
        # API Credentials
        self.api_key = os.getenv("OPENTABLE_API_KEY", "")
        self.api_secret = os.getenv("OPENTABLE_API_SECRET", "")
        self.client_id = os.getenv("OPENTABLE_CLIENT_ID", "")
        
        # OAuth2 tokens (if using OAuth flow)
        self.oauth_token = os.getenv("OPENTABLE_OAUTH_TOKEN", "")
        self.oauth_refresh_token = os.getenv("OPENTABLE_OAUTH_REFRESH_TOKEN", "")
        self._token_expires_at = 0
        
        # API Configuration
        self.base_url = os.getenv("OPENTABLE_API_URL", "https://api.opentable.com/v2")
        self.auth_url = os.getenv("OPENTABLE_AUTH_URL", "https://oauth.opentable.com/v2/token")
        self.timeout = aiohttp.ClientTimeout(total=30)
        
        # Rate limiting
        self.rate_limit_delay = 0.1  # 100ms between requests
        self._last_request_time = 0
        self._request_count = 0
        self._rate_limit_window_start = time.time()
        self._max_requests_per_minute = 60
        
        # Circuit breaker settings
        self._circuit_breaker_failures = 0
        self._circuit_breaker_threshold = 5
        self._circuit_breaker_timeout = 60  # seconds
        self._circuit_breaker_opened_at = 0
        
        # Mock mode for testing
        self.mock_mode = os.getenv("OPENTABLE_MOCK_MODE", "false").lower() == "true"
        
        # Request signing
        self.sign_requests = os.getenv("OPENTABLE_SIGN_REQUESTS", "true").lower() == "true"
        
    async def _get_oauth_token(self) -> str:
        """Get valid OAuth token, refreshing if necessary."""
        if self._token_expires_at > time.time() + 300:  # 5 min buffer
            return self.oauth_token
            
        # Refresh token
        async with aiohttp.ClientSession() as session:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.oauth_refresh_token,
                "client_id": self.client_id,
                "client_secret": self.api_secret
            }
            
            async with session.post(self.auth_url, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    self.oauth_token = token_data["access_token"]
                    self._token_expires_at = time.time() + token_data.get("expires_in", 3600)
                    if "refresh_token" in token_data:
                        self.oauth_refresh_token = token_data["refresh_token"]
                    return self.oauth_token
                else:
                    logger.error(f"Failed to refresh OAuth token: {response.status}")
                    raise Exception("OAuth token refresh failed")
    
    def _sign_request(self, method: str, url: str, timestamp: str, body: str = "") -> str:
        """Generate request signature for API authentication."""
        if not self.sign_requests or not self.api_secret:
            return ""
            
        # Create signing string
        signing_string = f"{method.upper()}\n{url}\n{timestamp}\n{body}"
        
        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            signing_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    async def _enforce_rate_limit(self):
        """Enforce rate limiting with sliding window."""
        current_time = time.time()
        
        # Reset window if needed
        if current_time - self._rate_limit_window_start > 60:
            self._rate_limit_window_start = current_time
            self._request_count = 0
            
        # Check if we've hit the limit
        if self._request_count >= self._max_requests_per_minute:
            sleep_time = 60 - (current_time - self._rate_limit_window_start)
            if sleep_time > 0:
                logger.warning(f"Rate limit reached, sleeping for {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)
                self._rate_limit_window_start = time.time()
                self._request_count = 0
        
        # Enforce minimum delay between requests
        time_since_last = current_time - self._last_request_time
        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)
            
        self._last_request_time = time.time()
        self._request_count += 1
    
    def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker is open."""
        if self._circuit_breaker_failures >= self._circuit_breaker_threshold:
            if time.time() - self._circuit_breaker_opened_at < self._circuit_breaker_timeout:
                return True  # Circuit is open
            else:
                # Reset circuit breaker
                self._circuit_breaker_failures = 0
                logger.info("Circuit breaker reset")
        return False
    
    def _record_success(self):
        """Record successful request for circuit breaker."""
        self._circuit_breaker_failures = 0
    
    def _record_failure(self):
        """Record failed request for circuit breaker."""
        self._circuit_breaker_failures += 1
        if self._circuit_breaker_failures >= self._circuit_breaker_threshold:
            self._circuit_breaker_opened_at = time.time()
            logger.error(f"Circuit breaker opened after {self._circuit_breaker_failures} failures")
    
    def _map_api_error(self, error_code: str, message: str) -> Dict[str, Any]:
        """Map API error codes to user-friendly messages."""
        return {
            "error_code": error_code,
            "message": self.ERROR_CODES.get(error_code, message),
            "original_message": message,
            "recoverable": error_code not in ["RESTAURANT_NOT_FOUND", "INVALID_PARTY_SIZE"]
        }
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ClientError, asyncio.TimeoutError)),
        before_sleep=before_sleep_log(logger, "WARNING")
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        use_cache: bool = False,
        cache_ttl: int = 300
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic, caching, and comprehensive error handling."""
        # Check circuit breaker
        if self._check_circuit_breaker():
            raise Exception("Circuit breaker is open - API temporarily unavailable")
            
        # Return mock data if in mock mode
        if self.mock_mode:
            return await self._get_mock_response(method, endpoint, params, json_data)
            
        await self._enforce_rate_limit()
        
        url = f"{self.base_url}/{endpoint}"
        
        # Check cache for GET requests
        if use_cache and method.upper() == "GET":
            cache_key = f"opentable:{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
            cached_result = await cache_manager.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for {endpoint}")
                return json.loads(cached_result)
        
        # Prepare headers
        timestamp = datetime.now(timezone.utc).isoformat()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Request-ID": f"rt-{int(time.time() * 1000)}",
            "X-Timestamp": timestamp,
            "User-Agent": "RoadTripStorytellerAPI/1.0"
        }
        
        # Add authentication
        if self.oauth_token:
            token = await self._get_oauth_token()
            headers["Authorization"] = f"Bearer {token}"
        elif self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        # Add request signature if enabled
        if self.sign_requests:
            body_str = json.dumps(json_data) if json_data else ""
            signature = self._sign_request(method, url, timestamp, body_str)
            if signature:
                headers["X-Signature"] = signature
        
        # Log request details
        logger.info(f"OpenTable API Request: {method} {endpoint}")
        logger.debug(f"Request params: {params}")
        logger.debug(f"Request body: {json_data}")
        
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
                    
                    # Log response
                    logger.debug(f"Response status: {response.status}")
                    logger.debug(f"Response body: {response_text}")
                    
                    # Handle successful responses
                    if response.status in [200, 201]:
                        self._record_success()
                        result = json.loads(response_text) if response_text else {}
                        
                        # Cache successful GET responses
                        if use_cache and method.upper() == "GET" and 'cache_key' in locals():
                            await cache_manager.setex(
                                cache_key,
                                cache_ttl,
                                json.dumps(result)
                            )
                            
                        return result
                    
                    # Handle API errors
                    elif response.status == 400:
                        error_data = json.loads(response_text) if response_text else {}
                        error_code = error_data.get("code", "BAD_REQUEST")
                        error_msg = error_data.get("message", "Invalid request")
                        mapped_error = self._map_api_error(error_code, error_msg)
                        raise ValueError(f"Bad Request: {mapped_error['message']}")
                        
                    elif response.status == 401:
                        # Try to refresh token if using OAuth
                        if self.oauth_token and not endpoint.endswith("/token"):
                            self.oauth_token = ""
                            self._token_expires_at = 0
                            # Retry will use refreshed token
                        raise ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message="Authentication failed"
                        )
                        
                    elif response.status == 403:
                        raise ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message="Access forbidden - check API permissions"
                        )
                        
                    elif response.status == 404:
                        raise ValueError(f"Resource not found: {endpoint}")
                        
                    elif response.status == 429:
                        retry_after = response.headers.get("Retry-After", "60")
                        raise ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message=f"Rate limit exceeded. Retry after {retry_after}s"
                        )
                        
                    elif response.status >= 500:
                        self._record_failure()
                        raise ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message="OpenTable API server error"
                        )
                        
                    else:
                        raise ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message=f"Unexpected status code: {response.status}"
                        )
                        
        except ClientError as e:
            self._record_failure()
            logger.error(f"OpenTable API client error: {str(e)}")
            raise
        except Exception as e:
            self._record_failure()
            logger.error(f"Unexpected error calling OpenTable API: {str(e)}")
            raise
    
    async def _get_mock_response(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Return mock responses for testing."""
        logger.info(f"Mock mode: {method} {endpoint}")
        
        # Add mock responses based on endpoint
        if "restaurants/search" in endpoint:
            return await self._get_mock_restaurants(params)
        elif "availability" in endpoint:
            return await self._get_mock_availability(endpoint, params)
        elif "reservations" in endpoint and method == "POST":
            return await self._get_mock_reservation(json_data)
        else:
            return {"mock": True, "endpoint": endpoint}
            
    async def _get_mock_restaurants(self, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Get mock restaurant data for testing."""
        return {
            "restaurants": [
                {
                    "id": "rest_001",
                    "name": "The Roadside Grill",
                    "cuisine": "American",
                    "rating": 4.5,
                    "price_range": "$$",
                    "address": "123 Highway St",
                    "distance_miles": 2.5,
                    "phone": "+1-555-0123",
                    "image_url": "https://example.com/restaurant1.jpg"
                },
                {
                    "id": "rest_002", 
                    "name": "Bella Vista Italian",
                    "cuisine": "Italian",
                    "rating": 4.7,
                    "price_range": "$$$",
                    "address": "456 Main Ave",
                    "distance_miles": 5.1,
                    "phone": "+1-555-0124",
                    "image_url": "https://example.com/restaurant2.jpg"
                }
            ],
            "total_count": 2
        }
    
    async def _get_mock_availability(self, endpoint: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Get mock availability data for testing."""
        return {
            "available_slots": [
                {"time": "18:30", "availability": "available"},
                {"time": "19:00", "availability": "limited"},
                {"time": "19:30", "availability": "available"},
                {"time": "20:00", "availability": "available"}
            ]
        }
    
    async def _get_mock_reservation(self, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Get mock reservation confirmation for testing."""
        return {
            "reservation_id": f"OT{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "status": "confirmed",
            "confirmation_code": "MOCK123"
        }
    
    async def search_restaurants(
        self,
        latitude: float,
        longitude: float,
        radius_miles: float = 10,
        cuisine_type: Optional[str] = None,
        party_size: int = 2,
        datetime_str: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for restaurants near a location.
        
        Args:
            latitude: Latitude of search location
            longitude: Longitude of search location
            radius_miles: Search radius in miles
            cuisine_type: Optional cuisine filter
            party_size: Number of diners
            datetime_str: Optional datetime for availability check
            
        Returns:
            List of restaurant data with basic information
        """
        # Build search parameters
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "radius": radius_miles,
            "party_size": party_size,
            "per_page": 50,
            "sort_by": "distance"
        }
        
        if cuisine_type:
            params["cuisine"] = cuisine_type
            
        if datetime_str:
            # Parse datetime and format for API
            dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            params["date"] = dt.strftime("%Y-%m-%d")
            params["time"] = dt.strftime("%H:%M")
        
        try:
            # Make API request with caching
            response = await self._make_request(
                "GET",
                "restaurants/search",
                params=params,
                use_cache=True,
                cache_ttl=600  # Cache for 10 minutes
            )
            
            # Extract restaurant data
            restaurants = response.get("restaurants", [])
            
            # Process and enrich restaurant data
            processed_restaurants = []
            for restaurant in restaurants:
                processed = {
                    "id": restaurant.get("id"),
                    "name": restaurant.get("name"),
                    "cuisine": restaurant.get("cuisine_type", ""),
                    "rating": restaurant.get("rating", 0),
                    "review_count": restaurant.get("review_count", 0),
                    "price_range": restaurant.get("price_range", "$$"),
                    "address": restaurant.get("address", {}).get("street", ""),
                    "city": restaurant.get("address", {}).get("city", ""),
                    "distance_miles": restaurant.get("distance", 0),
                    "phone": restaurant.get("phone", ""),
                    "image_url": restaurant.get("image_url", ""),
                    "reservation_available": restaurant.get("reservation_available", False),
                    "instant_booking": restaurant.get("instant_booking", False),
                    "special_offers": restaurant.get("promotions", [])
                }
                processed_restaurants.append(processed)
            
            logger.info(
                f"Searched restaurants near ({latitude}, {longitude}) "
                f"within {radius_miles} miles, found {len(processed_restaurants)} results"
            )
            
            return processed_restaurants
            
        except Exception as e:
            logger.error(f"Failed to search restaurants: {str(e)}")
            # Return empty list on error rather than crashing
            return []
        
    async def check_availability(
        self,
        restaurant_id: str,
        party_size: int,
        date: str,
        time_preference: str = "19:00"
    ) -> Dict[str, Any]:
        """
        Check availability for a specific restaurant.
        
        Args:
            restaurant_id: Restaurant identifier
            party_size: Number of diners
            date: Date in YYYY-MM-DD format
            time_preference: Preferred time in HH:MM format
            
        Returns:
            Dictionary with available time slots and booking information
        """
        # Validate date format
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            if date_obj.date() < datetime.now().date():
                raise ValueError("Cannot check availability for past dates")
        except ValueError as e:
            raise ValueError(f"Invalid date format: {str(e)}")
        
        # Build availability request
        params = {
            "date": date,
            "party_size": party_size,
            "time": time_preference,
            "range_minutes": 120  # Search 2 hours around preference
        }
        
        try:
            # Make API request
            response = await self._make_request(
                "GET",
                f"restaurants/{restaurant_id}/availability",
                params=params,
                use_cache=True,
                cache_ttl=180  # Cache for 3 minutes
            )
            
            # Process availability data
            available_slots = []
            for slot in response.get("time_slots", []):
                processed_slot = {
                    "time": slot.get("time"),
                    "availability": slot.get("availability_type", "available"),
                    "table_types": slot.get("table_types", []),
                    "special_offers": slot.get("offers", []),
                    "points_eligible": slot.get("points_eligible", False),
                    "estimated_duration": slot.get("estimated_duration_minutes", 90)
                }
                
                # Add pricing info if available
                if "pricing" in slot:
                    processed_slot["pricing"] = {
                        "reservation_fee": slot["pricing"].get("reservation_fee", 0),
                        "per_person_minimum": slot["pricing"].get("per_person_minimum", 0),
                        "currency": slot["pricing"].get("currency", "USD")
                    }
                    
                available_slots.append(processed_slot)
            
            result = {
                "restaurant_id": restaurant_id,
                "restaurant_name": response.get("restaurant_name", ""),
                "date": date,
                "party_size": party_size,
                "available_slots": available_slots,
                "booking_fee": response.get("default_booking_fee", 0),
                "cancellation_policy": response.get("cancellation_policy", {
                    "description": "Free cancellation up to 2 hours before",
                    "fee": 0,
                    "cutoff_hours": 2
                }),
                "special_requirements_available": response.get("special_requirements", []),
                "loyalty_program": response.get("loyalty_program", {})
            }
            
            logger.info(
                f"Checked availability for restaurant {restaurant_id} on {date}, "
                f"found {len(available_slots)} time slots"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to check availability: {str(e)}")
            raise
        
    async def create_reservation(
        self,
        restaurant_id: str,
        party_size: int,
        date: str,
        time: str,
        customer_info: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Create a restaurant reservation.
        
        Args:
            restaurant_id: Restaurant identifier
            party_size: Number of diners
            date: Date in YYYY-MM-DD format
            time: Time in HH:MM format
            customer_info: Customer details (name, email, phone)
            
        Returns:
            Confirmation details including reservation ID
        """
        # Validate required customer info
        required_fields = ["name", "email", "phone"]
        for field in required_fields:
            if field not in customer_info or not customer_info[field]:
                raise ValueError(f"Missing required customer field: {field}")
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, customer_info["email"]):
            raise ValueError("Invalid email format")
        
        # Build reservation request
        reservation_data = {
            "restaurant_id": restaurant_id,
            "date": date,
            "time": time,
            "party_size": party_size,
            "customer": {
                "first_name": customer_info.get("first_name") or customer_info["name"].split()[0],
                "last_name": customer_info.get("last_name") or customer_info["name"].split()[-1],
                "email": customer_info["email"],
                "phone": customer_info["phone"],
                "country_code": customer_info.get("country_code", "+1")
            },
            "special_requests": customer_info.get("special_requests", ""),
            "dietary_restrictions": customer_info.get("dietary_restrictions", []),
            "occasion": customer_info.get("occasion", ""),
            "marketing_opt_in": customer_info.get("marketing_opt_in", False),
            "source": "road_trip_storyteller_api"
        }
        
        # Add loyalty program info if available
        if "loyalty_number" in customer_info:
            reservation_data["loyalty_number"] = customer_info["loyalty_number"]
        
        try:
            # Make API request
            response = await self._make_request(
                "POST",
                "reservations",
                json_data=reservation_data
            )
            
            # Process confirmation
            confirmation = {
                "reservation_id": response["reservation_id"],
                "confirmation_code": response["confirmation_code"],
                "restaurant_id": restaurant_id,
                "restaurant_name": response.get("restaurant_name", ""),
                "restaurant_phone": response.get("restaurant_phone", ""),
                "date": date,
                "time": time,
                "party_size": party_size,
                "customer_name": customer_info["name"],
                "customer_email": customer_info["email"],
                "status": response.get("status", "confirmed"),
                "special_requests": customer_info.get("special_requests", ""),
                "table_preferences": response.get("table_preferences", {}),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "cancellation_link": response.get("cancellation_link", ""),
                "modification_link": response.get("modification_link", ""),
                "points_earned": response.get("points_earned", 0),
                "estimated_duration_minutes": response.get("estimated_duration", 90),
                "reminders": response.get("reminders", {
                    "email": True,
                    "sms": customer_info.get("sms_reminders", True)
                })
            }
            
            # Add any fees if applicable
            if "fees" in response:
                confirmation["fees"] = response["fees"]
            
            # Log successful reservation
            logger.info(
                f"Created reservation {confirmation['reservation_id']} for {party_size} people "
                f"at restaurant {restaurant_id} on {date} {time}"
            )
            
            # Send confirmation event for tracking
            await self._track_reservation_event("created", confirmation)
            
            return confirmation
            
        except ClientResponseError as e:
            if e.status == 409:
                raise ValueError("A reservation already exists for this time")
            raise
        except Exception as e:
            logger.error(f"Failed to create reservation: {str(e)}")
            raise
    
    async def _track_reservation_event(self, event_type: str, reservation_data: Dict[str, Any]):
        """Track reservation events for analytics."""
        # This would send to analytics service
        logger.info(f"Reservation event: {event_type} - {reservation_data['reservation_id']}")
        
    async def cancel_reservation(
        self,
        reservation_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancel an existing reservation.
        
        Args:
            reservation_id: Reservation identifier
            reason: Optional cancellation reason
            
        Returns:
            Cancellation confirmation
        """
        # Build cancellation request
        cancellation_data = {
            "reason": reason or "Customer requested",
            "source": "road_trip_storyteller_api"
        }
        
        try:
            # Make API request
            response = await self._make_request(
                "DELETE",
                f"reservations/{reservation_id}",
                json_data=cancellation_data
            )
            
            # Process cancellation response
            result = {
                "reservation_id": reservation_id,
                "status": "cancelled",
                "cancelled_at": response.get("cancelled_at", datetime.now(timezone.utc).isoformat()),
                "reason": reason or "Customer requested",
                "cancellation_number": response.get("cancellation_number", ""),
                "refund_status": response.get("refund_status", "No charges applied"),
                "refund_amount": response.get("refund_amount", 0),
                "cancellation_fee": response.get("cancellation_fee", 0),
                "email_confirmation_sent": response.get("email_sent", True)
            }
            
            logger.info(f"Cancelled reservation {reservation_id}")
            
            # Track cancellation event
            await self._track_reservation_event("cancelled", result)
            
            return result
            
        except ClientResponseError as e:
            if e.status == 404:
                raise ValueError(f"Reservation {reservation_id} not found")
            elif e.status == 400:
                raise ValueError("Reservation cannot be cancelled - check cancellation policy")
            raise
        except Exception as e:
            logger.error(f"Failed to cancel reservation: {str(e)}")
            raise
        
    async def get_restaurant_details(
        self,
        restaurant_id: str
    ) -> Dict[str, Any]:
        """
        Get detailed information about a restaurant.
        
        Args:
            restaurant_id: Restaurant identifier
            
        Returns:
            Detailed restaurant information
        """
        try:
            # Make API request with caching
            response = await self._make_request(
                "GET",
                f"restaurants/{restaurant_id}",
                use_cache=True,
                cache_ttl=3600  # Cache for 1 hour
            )
            
            # Process restaurant details
            details = {
                "id": restaurant_id,
                "name": response.get("name", ""),
                "description": response.get("description", ""),
                "cuisine": response.get("cuisine_type", ""),
                "cuisines": response.get("cuisine_types", []),  # Multiple cuisines
                "rating": response.get("rating", 0),
                "review_count": response.get("review_count", 0),
                "price_range": response.get("price_range", "$$"),
                "address": {
                    "street": response.get("address", {}).get("street", ""),
                    "city": response.get("address", {}).get("city", ""),
                    "state": response.get("address", {}).get("state", ""),
                    "zip": response.get("address", {}).get("postal_code", ""),
                    "country": response.get("address", {}).get("country", "US")
                },
                "coordinates": {
                    "latitude": response.get("latitude", 0),
                    "longitude": response.get("longitude", 0)
                },
                "phone": response.get("phone", ""),
                "hours": response.get("operating_hours", {}),
                "timezone": response.get("timezone", "America/Los_Angeles"),
                "amenities": response.get("amenities", []),
                "dining_style": response.get("dining_style", ""),
                "dress_code": response.get("dress_code", "Casual"),
                "parking": response.get("parking_details", {}),
                "payment_options": response.get("payment_options", []),
                "images": response.get("photos", []),
                "menu_url": response.get("menu_url", ""),
                "website": response.get("website", ""),
                "reservation_policy": response.get("reservation_policy", {}),
                "safety_precautions": response.get("safety_precautions", []),
                "sustainability": response.get("sustainability_practices", []),
                "awards": response.get("awards", []),
                "special_diets": response.get("special_diets_accommodated", []),
                "private_dining": response.get("private_dining_available", False),
                "catering": response.get("catering_available", False)
            }
            
            # Add real-time info if available
            if "real_time" in response:
                details["real_time"] = {
                    "wait_time_minutes": response["real_time"].get("current_wait", 0),
                    "busy_level": response["real_time"].get("busy_level", "moderate"),
                    "tables_available": response["real_time"].get("tables_available", False)
                }
            
            logger.info(f"Retrieved details for restaurant {restaurant_id}")
            
            return details
            
        except Exception as e:
            logger.error(f"Failed to get restaurant details: {str(e)}")
            raise
    
    async def get_reservation_details(
        self,
        reservation_id: str
    ) -> Dict[str, Any]:
        """Get details of an existing reservation."""
        try:
            response = await self._make_request(
                "GET",
                f"reservations/{reservation_id}"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to get reservation details: {str(e)}")
            raise
    
    async def modify_reservation(
        self,
        reservation_id: str,
        modifications: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Modify an existing reservation."""
        try:
            response = await self._make_request(
                "PATCH",
                f"reservations/{reservation_id}",
                json_data=modifications
            )
            
            logger.info(f"Modified reservation {reservation_id}")
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to modify reservation: {str(e)}")
            raise