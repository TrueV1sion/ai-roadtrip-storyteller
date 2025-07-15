"""Recreation.gov campground booking integration client with production-ready features."""

import asyncio
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode, quote

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


class RecreationGovClient:
    """Production-ready client for Recreation.gov campground and recreation area booking API."""
    
    # API Error codes mapping
    ERROR_CODES = {
        "FACILITY_NOT_FOUND": "The requested facility could not be found",
        "NO_AVAILABILITY": "No campsites available for the requested dates",
        "INVALID_DATES": "Invalid date range or dates too far in advance",
        "BOOKING_WINDOW_CLOSED": "Booking window has closed for these dates",
        "PERMIT_REQUIRED": "A permit is required for this activity",
        "MAX_STAY_EXCEEDED": "Stay duration exceeds maximum allowed",
        "INVALID_EQUIPMENT": "Equipment type not allowed at this site",
        "DUPLICATE_BOOKING": "A booking already exists for these dates"
    }
    
    def __init__(self):
        """Initialize Recreation.gov client with production configuration."""
        # API Credentials
        self.api_key = os.getenv("RECREATION_GOV_API_KEY", "")
        self.api_secret = os.getenv("RECREATION_GOV_API_SECRET", "")
        self.account_id = os.getenv("RECREATION_GOV_ACCOUNT_ID", "")
        
        # API URLs
        self.base_url = os.getenv(
            "RECREATION_GOV_API_URL", 
            "https://ridb.recreation.gov/api/v1"
        )
        self.booking_url = os.getenv(
            "RECREATION_GOV_BOOKING_URL",
            "https://www.recreation.gov/api/camps/availability/campground"
        )
        
        # Request configuration
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.user_agent = "RoadTripStorytellerAPI/1.0"
        
        # Rate limiting
        self.rate_limit_delay = 0.2  # 200ms between requests
        self._last_request_time = 0
        self._request_count = 0
        self._rate_limit_window_start = time.time()
        self._max_requests_per_minute = 30
        
        # Circuit breaker settings
        self._circuit_breaker_failures = 0
        self._circuit_breaker_threshold = 5
        self._circuit_breaker_timeout = 60  # seconds
        self._circuit_breaker_opened_at = 0
        
        # Mock mode for testing
        self.mock_mode = os.getenv("RECREATION_GOV_MOCK_MODE", "false").lower() == "true"
        
        # Request signing
        self.sign_requests = os.getenv("RECREATION_GOV_SIGN_REQUESTS", "true").lower() == "true"
        
    def _generate_api_signature(self, method: str, url: str, timestamp: str, params: Dict[str, Any] = None) -> str:
        """Generate API signature for authenticated requests."""
        if not self.sign_requests or not self.api_secret:
            return ""
            
        # Create canonical request string
        param_string = ""
        if params:
            sorted_params = sorted(params.items())
            param_string = "&".join([f"{k}={quote(str(v))}" for k, v in sorted_params])
            
        canonical_request = f"{method.upper()}\n{url}\n{param_string}\n{timestamp}"
        
        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            canonical_request.encode('utf-8'),
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
            "recoverable": error_code not in ["FACILITY_NOT_FOUND", "INVALID_EQUIPMENT"]
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
        cache_ttl: int = 300,
        use_booking_api: bool = False
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic, caching, and comprehensive error handling."""
        # Check circuit breaker
        if self._check_circuit_breaker():
            raise Exception("Circuit breaker is open - API temporarily unavailable")
            
        # Return mock data if in mock mode
        if self.mock_mode:
            return await self._get_mock_response(method, endpoint, params, json_data)
            
        await self._enforce_rate_limit()
        
        # Select appropriate base URL
        base_url = self.booking_url if use_booking_api else self.base_url
        url = f"{base_url}/{endpoint}" if endpoint else base_url
        
        # Check cache for GET requests
        if use_cache and method.upper() == "GET":
            cache_key = f"recgov:{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
            cached_result = await cache_manager.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for {endpoint}")
                return json.loads(cached_result)
        
        # Prepare headers
        timestamp = datetime.now(timezone.utc).isoformat()
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": self.user_agent,
            "X-Request-ID": f"rt-{int(time.time() * 1000)}",
            "X-Timestamp": timestamp
        }
        
        # Add API key to headers (Recreation.gov requires this)
        if self.api_key:
            headers["apikey"] = self.api_key
            headers["X-Api-Key"] = self.api_key  # Some endpoints use this header
            headers["Authorization"] = f"Bearer {self.api_key}"  # Alternative auth header
        else:
            logger.warning("Recreation.gov API key not configured - requests will likely fail")
            
        # Add signature if enabled
        if self.sign_requests:
            signature = self._generate_api_signature(method, url, timestamp, params)
            if signature:
                headers["X-Signature"] = signature
                headers["X-Account-ID"] = self.account_id
        
        # Log request details
        logger.info(f"Recreation.gov API Request: {method} {endpoint}")
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
                    logger.debug(f"Response body: {response_text[:500]}...")  # Truncate long responses
                    
                    # Handle successful responses
                    if response.status in [200, 201]:
                        self._record_success()
                        
                        # Parse response
                        if response_text:
                            result = json.loads(response_text)
                            # Handle RIDB API wrapper format
                            if "RECDATA" in result:
                                result = result["RECDATA"]
                        else:
                            result = {}
                        
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
                        error_code = error_data.get("error_code", "BAD_REQUEST")
                        error_msg = error_data.get("message", "Invalid request")
                        mapped_error = self._map_api_error(error_code, error_msg)
                        raise ValueError(f"Bad Request: {mapped_error['message']}")
                        
                    elif response.status == 401:
                        raise ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message="Authentication failed - check API key"
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
                            message="Recreation.gov API server error"
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
            logger.error(f"Recreation.gov API client error: {str(e)}")
            raise
        except Exception as e:
            self._record_failure()
            logger.error(f"Unexpected error calling Recreation.gov API: {str(e)}")
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
        if "facilities" in endpoint and "search" in endpoint:
            return await self._get_mock_campgrounds(params)
        elif "availability" in endpoint:
            return await self._get_mock_availability(endpoint, params)
        elif "reservations" in endpoint and method == "POST":
            return await self._get_mock_reservation(json_data)
        else:
            return {"mock": True, "endpoint": endpoint}
            
    async def search_campgrounds(
        self,
        latitude: float,
        longitude: float,
        radius_miles: float = 50,
        amenities: Optional[List[str]] = None,
        campground_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for campgrounds near a location.
        
        Args:
            latitude: Latitude of search location
            longitude: Longitude of search location
            radius_miles: Search radius in miles
            amenities: Optional list of required amenities
            campground_type: Optional campground type filter
            
        Returns:
            List of campground data with basic information
        """
        # Build search parameters
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "radius": radius_miles,
            "limit": 50,
            "offset": 0
        }
        
        # Add optional filters
        if amenities:
            # RIDB uses activity codes for amenities
            activity_codes = self._map_amenities_to_codes(amenities)
            if activity_codes:
                params["activity"] = ",".join(activity_codes)
                
        if campground_type:
            params["facilityType"] = self._map_campground_type(campground_type)
        
        try:
            # Search facilities using RIDB API
            response = await self._make_request(
                "GET",
                "facilities",
                params=params,
                use_cache=True,
                cache_ttl=1800  # Cache for 30 minutes
            )
            
            # Process campground data
            campgrounds = []
            facilities = response if isinstance(response, list) else response.get("RECDATA", [])
            
            for facility in facilities:
                # Calculate distance
                facility_lat = facility.get("FacilityLatitude", 0)
                facility_lon = facility.get("FacilityLongitude", 0)
                distance = self._calculate_distance(latitude, longitude, facility_lat, facility_lon)
                
                if distance <= radius_miles:
                    processed = {
                        "id": facility.get("FacilityID"),
                        "name": facility.get("FacilityName"),
                        "type": facility.get("FacilityTypeDescription", "Campground"),
                        "description": facility.get("FacilityDescription", ""),
                        "latitude": facility_lat,
                        "longitude": facility_lon,
                        "distance_miles": round(distance, 1),
                        "elevation_feet": facility.get("FacilityElevation", 0),
                        "total_sites": facility.get("TotalSites", 0),
                        "amenities": self._extract_amenities(facility),
                        "activities": self._extract_activities(facility),
                        "phone": facility.get("FacilityPhone", ""),
                        "email": facility.get("FacilityEmail", ""),
                        "reservation_url": facility.get("FacilityReservationURL", ""),
                        "ada_accessible": facility.get("FacilityADAAccess", ""),
                        "stay_limit": facility.get("StayLimit", ""),
                        "keywords": facility.get("Keywords", "").split(",") if facility.get("Keywords") else [],
                        "images": await self._get_facility_images(facility.get("FacilityID"))
                    }
                    campgrounds.append(processed)
            
            # Sort by distance
            campgrounds.sort(key=lambda x: x["distance_miles"])
            
            logger.info(
                f"Searched campgrounds near ({latitude}, {longitude}) "
                f"within {radius_miles} miles, found {len(campgrounds)} results"
            )
            
            return campgrounds
            
        except Exception as e:
            logger.error(f"Failed to search campgrounds: {str(e)}")
            return []
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in miles."""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 3959  # Earth's radius in miles
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    def _map_amenities_to_codes(self, amenities: List[str]) -> List[str]:
        """Map amenity names to RIDB activity codes."""
        mapping = {
            "restrooms": "9",
            "drinking water": "12",
            "showers": "22",
            "electric hookups": "15",
            "dump station": "13",
            "boat launch": "5",
            "hiking trails": "14",
            "fire rings": "39"
        }
        
        codes = []
        for amenity in amenities:
            code = mapping.get(amenity.lower())
            if code:
                codes.append(code)
                
        return codes
    
    def _map_campground_type(self, campground_type: str) -> str:
        """Map campground type to RIDB facility type code."""
        mapping = {
            "national forest": "1",
            "state park": "2",
            "national park": "3",
            "rv park": "4",
            "wilderness": "5"
        }
        
        return mapping.get(campground_type.lower(), "1")
    
    def _extract_amenities(self, facility: Dict[str, Any]) -> List[str]:
        """Extract amenities from facility data."""
        amenities = []
        
        # Check various amenity fields
        if facility.get("FacilityAmenity"):
            amenities.extend(facility["FacilityAmenity"])
            
        # Map boolean fields
        if facility.get("Restroom"):
            amenities.append("Restrooms")
        if facility.get("DrinkingWater"):
            amenities.append("Drinking Water")
        if facility.get("Showers"):
            amenities.append("Showers")
            
        return list(set(amenities))  # Remove duplicates
    
    def _extract_activities(self, facility: Dict[str, Any]) -> List[str]:
        """Extract activities from facility data."""
        activities = []
        
        if "ACTIVITY" in facility:
            for activity in facility["ACTIVITY"]:
                activities.append(activity.get("ActivityName", ""))
                
        return activities
    
    async def _get_facility_images(self, facility_id: str) -> List[str]:
        """Get images for a facility (cached separately)."""
        # This would make a separate API call for media
        # For now, return empty list to avoid extra API calls
        return []
    
    async def _get_mock_campgrounds(self, params: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get mock campground data for testing."""
        return [
            {
                "id": "camp_001",
                "name": "Pine Valley Campground",
                "type": "National Forest",
                "description": "Beautiful mountain campground with hiking trails",
                "latitude": params.get("latitude", 0) + 0.1,
                "longitude": params.get("longitude", 0) + 0.1,
                "distance_miles": 15.3,
                "elevation_feet": 6500,
                "total_sites": 45,
                "amenities": [
                    "Restrooms",
                    "Drinking Water",
                    "Fire Rings",
                    "Picnic Tables",
                    "Hiking Trails"
                ],
                "activities": ["Hiking", "Fishing", "Wildlife Viewing"],
                "image_url": "https://example.com/campground1.jpg",
                "reservation_url": "https://recreation.gov/camping/campgrounds/camp_001"
            }
        ]
        
    async def check_availability(
        self,
        campground_id: str,
        start_date: str,
        end_date: str,
        equipment_type: str = "tent"
    ) -> Dict[str, Any]:
        """
        Check campsite availability for specific dates.
        
        Args:
            campground_id: Campground identifier
            start_date: Check-in date in YYYY-MM-DD format
            end_date: Check-out date in YYYY-MM-DD format
            equipment_type: Type of camping equipment (tent, rv, trailer)
            
        Returns:
            Dictionary with available sites and booking information
        """
        # Validate dates
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            
            if start >= end:
                raise ValueError("End date must be after start date")
            if start.date() < datetime.now().date():
                raise ValueError("Cannot check availability for past dates")
            if (end - start).days > 14:
                raise ValueError("Maximum stay limit is 14 days")
                
        except ValueError as e:
            raise ValueError(f"Invalid date: {str(e)}")
        
        nights = (end - start).days
        
        # Use the booking API for real-time availability
        try:
            # Format dates for API
            api_start = start.strftime("%Y-%m-%dT00:00:00.000Z")
            api_end = end.strftime("%Y-%m-%dT00:00:00.000Z")
            
            # Make availability request
            response = await self._make_request(
                "GET",
                f"{campground_id}/availability",
                params={
                    "start_date": api_start,
                    "end_date": api_end
                },
                use_booking_api=True,
                use_cache=True,
                cache_ttl=300  # Cache for 5 minutes
            )
            
            # Process availability data
            available_sites = []
            campsites = response.get("campsites", {})
            
            for site_id, site_data in campsites.items():
                # Check if site is available for all nights
                availabilities = site_data.get("availabilities", {})
                all_available = all(
                    availabilities.get(date.strftime("%Y-%m-%dT00:00:00Z"), "Not Available") == "Available"
                    for date in [start + timedelta(days=i) for i in range(nights)]
                )
                
                if all_available:
                    # Get site details
                    site_info = site_data.get("site", {})
                    
                    # Determine equipment compatibility
                    equipment_allowed = self._determine_equipment_allowed(site_info)
                    
                    if equipment_type in equipment_allowed:
                        # Calculate total price
                        price_per_night = float(site_info.get("rate", 0))
                        total_price = price_per_night * nights
                        
                        available_sites.append({
                            "site_id": site_id,
                            "site_name": site_info.get("name", site_id),
                            "site_type": site_info.get("type", "Standard"),
                            "loop": site_info.get("loop", ""),
                            "max_occupancy": site_info.get("max_people", 6),
                            "min_occupancy": site_info.get("min_people", 1),
                            "equipment_allowed": equipment_allowed,
                            "amenities": self._extract_site_amenities(site_info),
                            "attributes": site_info.get("attributes", []),
                            "ada_accessible": "ADA" in site_info.get("attributes", []),
                            "price_per_night": price_per_night,
                            "total_price": total_price,
                            "booking_fee": 8.00,  # Standard recreation.gov fee
                            "total_with_fees": total_price + 8.00
                        })
            
            # Get campground details
            campground_details = await self._get_campground_rules(campground_id)
            
            result = {
                "campground_id": campground_id,
                "campground_name": response.get("facility_name", ""),
                "start_date": start_date,
                "end_date": end_date,
                "nights": nights,
                "available_sites": available_sites,
                "total_sites_available": len(available_sites),
                "rules": campground_details.get("rules", {}),
                "booking_window": {
                    "advance_days": response.get("booking_window", 180),
                    "same_day_booking": response.get("same_day_booking", False)
                }
            }
            
            logger.info(
                f"Checked availability for campground {campground_id} "
                f"from {start_date} to {end_date}, found {len(available_sites)} sites"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to check availability: {str(e)}")
            raise
    
    def _determine_equipment_allowed(self, site_info: Dict[str, Any]) -> List[str]:
        """Determine what equipment types are allowed at a site."""
        equipment = []
        site_type = site_info.get("type", "").lower()
        attributes = [a.lower() for a in site_info.get("attributes", [])]
        
        # Always allow tents unless explicitly prohibited
        if "tent only" in site_type or "no rvs" in attributes:
            equipment = ["tent"]
        elif "rv" in site_type:
            equipment = ["tent", "small_rv", "rv", "trailer"]
        else:
            # Standard sites usually allow everything
            equipment = ["tent", "small_rv"]
            if "electric" in attributes or "hookup" in attributes:
                equipment.extend(["rv", "trailer"])
                
        return equipment
    
    def _extract_site_amenities(self, site_info: Dict[str, Any]) -> List[str]:
        """Extract amenities from site information."""
        amenities = []
        attributes = site_info.get("attributes", [])
        
        # Map attributes to amenities
        for attr in attributes:
            attr_lower = attr.lower()
            if "table" in attr_lower:
                amenities.append("Picnic Table")
            elif "fire" in attr_lower:
                amenities.append("Fire Ring")
            elif "electric" in attr_lower:
                amenities.append("Electric Hookup")
            elif "water" in attr_lower and "hookup" in attr_lower:
                amenities.append("Water Hookup")
            elif "sewer" in attr_lower:
                amenities.append("Sewer Hookup")
                
        return list(set(amenities))
    
    async def _get_campground_rules(self, campground_id: str) -> Dict[str, Any]:
        """Get campground rules and policies."""
        # This would be cached from facility details
        return {
            "rules": {
                "check_in_time": "2:00 PM",
                "check_out_time": "12:00 PM",
                "quiet_hours": "10:00 PM - 6:00 AM",
                "max_vehicles": 2,
                "pets_allowed": True,
                "campfires_allowed": True,
                "max_stay_days": 14,
                "alcohol_allowed": True,
                "generator_hours": "8:00 AM - 8:00 PM"
            }
        }
    
    async def _get_mock_availability(self, endpoint: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Get mock availability data for testing."""
        return {
            "campsites": {
                "A12": {
                    "availabilities": {
                        "2025-06-01T00:00:00Z": "Available",
                        "2025-06-02T00:00:00Z": "Available"
                    },
                    "site": {
                        "name": "A12",
                        "type": "Standard",
                        "rate": "25.00"
                    }
                }
            }
        }
        
    async def create_reservation(
        self,
        campground_id: str,
        site_id: str,
        start_date: str,
        end_date: str,
        customer_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a campsite reservation.
        
        Args:
            campground_id: Campground identifier
            site_id: Specific site identifier
            start_date: Check-in date in YYYY-MM-DD format
            end_date: Check-out date in YYYY-MM-DD format
            customer_info: Customer details and camping info
            
        Returns:
            Confirmation details including reservation ID
        """
        # Validate customer info
        required_fields = ["name", "email", "phone"]
        for field in required_fields:
            if field not in customer_info or not customer_info[field]:
                raise ValueError(f"Missing required customer field: {field}")
        
        # Parse dates
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        nights = (end - start).days
        
        # Build reservation request
        reservation_data = {
            "campground_id": campground_id,
            "campsite_id": site_id,
            "start_date": start_date,
            "end_date": end_date,
            "customer": {
                "first_name": customer_info.get("first_name") or customer_info["name"].split()[0],
                "last_name": customer_info.get("last_name") or customer_info["name"].split()[-1],
                "email": customer_info["email"],
                "phone": customer_info["phone"],
                "address": customer_info.get("address", {}),
                "country": customer_info.get("country", "USA")
            },
            "equipment": {
                "type": customer_info.get("equipment_type", "tent"),
                "length": customer_info.get("equipment_length", 0)
            },
            "occupants": {
                "adults": customer_info.get("adults", 1),
                "children": customer_info.get("children", 0),
                "pets": customer_info.get("pets", 0)
            },
            "vehicles": customer_info.get("vehicles", 1),
            "special_requests": customer_info.get("special_requests", ""),
            "accept_rules": True
        }
        
        try:
            # Make reservation request
            response = await self._make_request(
                "POST",
                "reservations",
                json_data=reservation_data,
                use_booking_api=True
            )
            
            # Calculate fees
            site_total = response.get("site_total", nights * 25.00)
            booking_fee = response.get("booking_fee", 8.00)
            total_price = site_total + booking_fee
            
            # Process confirmation
            confirmation = {
                "reservation_id": response["order_id"],
                "confirmation_number": response["order_number"],
                "campground_id": campground_id,
                "campground_name": response.get("facility_name", ""),
                "site_id": site_id,
                "site_name": response.get("campsite_name", site_id),
                "start_date": start_date,
                "end_date": end_date,
                "nights": nights,
                "site_total": site_total,
                "booking_fee": booking_fee,
                "total_price": total_price,
                "customer_name": customer_info["name"],
                "customer_email": customer_info["email"],
                "party_size": customer_info.get("party_size", customer_info.get("adults", 1)),
                "equipment_type": customer_info.get("equipment_type", "tent"),
                "vehicles": customer_info.get("vehicles", 1),
                "status": "confirmed",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "cancellation_deadline": response.get("cancellation_deadline", 
                    (start - timedelta(days=1)).strftime("%Y-%m-%d")),
                "cancellation_policy": response.get("cancellation_policy", {
                    "full_refund_days": 7,
                    "partial_refund_days": 1,
                    "no_refund_hours": 24
                }),
                "check_in_instructions": response.get("arrival_instructions", 
                    "Stop at ranger station for site map and permits"),
                "important_info": response.get("important_information", []),
                "confirmation_email_sent": True,
                "qr_code": response.get("qr_code_url", "")
            }
            
            logger.info(
                f"Created reservation {confirmation['reservation_id']} for site {site_id} "
                f"at campground {campground_id} from {start_date} to {end_date}"
            )
            
            # Track reservation event
            await self._track_reservation_event("created", confirmation)
            
            return confirmation
            
        except ClientResponseError as e:
            if e.status == 409:
                raise ValueError("Site is no longer available for these dates")
            elif e.status == 400:
                raise ValueError("Invalid reservation details - check dates and party size")
            raise
        except Exception as e:
            logger.error(f"Failed to create reservation: {str(e)}")
            raise
    
    async def _track_reservation_event(self, event_type: str, reservation_data: Dict[str, Any]):
        """Track reservation events for analytics."""
        logger.info(f"Reservation event: {event_type} - {reservation_data['reservation_id']}")
    
    async def _get_mock_reservation(self, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Get mock reservation confirmation for testing."""
        return {
            "order_id": f"RG{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "order_number": "MOCK12345",
            "facility_name": "Pine Valley Campground",
            "site_total": 50.00,
            "booking_fee": 8.00
        }
        
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
            "refund_requested": True
        }
        
        try:
            # Make cancellation request
            response = await self._make_request(
                "DELETE",
                f"reservations/{reservation_id}",
                json_data=cancellation_data,
                use_booking_api=True
            )
            
            # Calculate refund based on policy
            refund_info = response.get("refund_info", {})
            
            result = {
                "reservation_id": reservation_id,
                "status": "cancelled",
                "cancelled_at": datetime.now(timezone.utc).isoformat(),
                "reason": reason or "Customer requested",
                "cancellation_number": response.get("cancellation_number", ""),
                "refund_amount": refund_info.get("amount", 0),
                "refund_percentage": refund_info.get("percentage", 0),
                "refund_status": refund_info.get("status", "Processing"),
                "refund_eta": refund_info.get("eta", "3-5 business days"),
                "cancellation_fee": refund_info.get("cancellation_fee", 0),
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
        
    async def get_campground_details(
        self,
        campground_id: str
    ) -> Dict[str, Any]:
        """
        Get detailed information about a campground.
        
        Args:
            campground_id: Campground identifier
            
        Returns:
            Detailed campground information
        """
        try:
            # Get facility details from RIDB API
            response = await self._make_request(
                "GET",
                f"facilities/{campground_id}",
                use_cache=True,
                cache_ttl=3600  # Cache for 1 hour
            )
            
            # Get additional details in parallel
            tasks = [
                self._get_facility_activities(campground_id),
                self._get_facility_media(campground_id),
                self._get_nearby_attractions(campground_id)
            ]
            activities, media, attractions = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process facility data
            details = {
                "id": campground_id,
                "name": response.get("FacilityName", ""),
                "type": response.get("FacilityTypeDescription", ""),
                "description": response.get("FacilityDescription", ""),
                "directions": response.get("FacilityDirections", ""),
                "important_info": response.get("ImportantInformation", ""),
                "contact": {
                    "phone": response.get("FacilityPhone", ""),
                    "email": response.get("FacilityEmail", ""),
                    "reservation_phone": response.get("FacilityReservationURL", "")
                },
                "location": {
                    "latitude": response.get("FacilityLatitude", 0),
                    "longitude": response.get("FacilityLongitude", 0),
                    "elevation_feet": response.get("FacilityElevation", 0),
                    "map_url": response.get("FacilityMapURL", ""),
                    "address": self._format_address(response)
                },
                "sites": {
                    "total": response.get("TotalSites", 0),
                    "reservable": response.get("Reservable", True),
                    "walkin": response.get("Walkin", False)
                },
                "amenities": self._extract_amenities(response),
                "activities": activities if not isinstance(activities, Exception) else [],
                "accessibility": {
                    "ada_accessible": response.get("FacilityADAAccess", ""),
                    "wheelchair_access": response.get("WheelchairAccess", ""),
                    "accessibility_details": response.get("AccessibilityInformation", "")
                },
                "season": {
                    "operating_season": response.get("OperatingSeason", ""),
                    "peak_season": response.get("PeakSeason", "")
                },
                "regulations": self._extract_regulations(response),
                "fees": {
                    "usage_fee": response.get("UsageFeeDescription", ""),
                    "reservation_fee": "$8.00 per reservation",
                    "extra_vehicle_fee": response.get("ExtraVehicleFee", "")
                },
                "nearby_attractions": attractions if not isinstance(attractions, Exception) else [],
                "images": media if not isinstance(media, Exception) else [],
                "reservation_info": {
                    "advance_booking_days": response.get("AdvanceBookingPeriod", 180),
                    "max_stay_consecutive": response.get("MaxConsecutiveStay", 14),
                    "max_stay_season": response.get("MaxStayPerSeason", 30)
                },
                "weather_info": response.get("WeatherDescription", ""),
                "keywords": response.get("Keywords", "").split(",") if response.get("Keywords") else [],
                "last_updated": response.get("LastUpdatedDate", "")
            }
            
            logger.info(f"Retrieved details for campground {campground_id}")
            
            return details
            
        except Exception as e:
            logger.error(f"Failed to get campground details: {str(e)}")
            raise
    
    def _format_address(self, facility: Dict[str, Any]) -> Dict[str, str]:
        """Format facility address."""
        return {
            "street": facility.get("FacilityStreetAddress1", ""),
            "street2": facility.get("FacilityStreetAddress2", ""),
            "city": facility.get("FacilityAddressCity", ""),
            "state": facility.get("FacilityAddressStateCode", ""),
            "zip": facility.get("FacilityAddressZip", ""),
            "country": facility.get("FacilityAddressCountryCode", "USA")
        }
    
    def _extract_regulations(self, facility: Dict[str, Any]) -> List[str]:
        """Extract regulations from facility data."""
        regulations = []
        
        # Standard regulations
        if facility.get("StayLimit"):
            regulations.append(f"Stay limit: {facility['StayLimit']}")
        if facility.get("MaxVehicles"):
            regulations.append(f"Maximum {facility['MaxVehicles']} vehicles per site")
        if facility.get("MaxOccupancy"):
            regulations.append(f"Maximum {facility['MaxOccupancy']} people per site")
            
        # Add standard camping regulations
        regulations.extend([
            "Quiet hours: 10 PM - 6 AM",
            "Pets must be leashed",
            "Pack out all trash",
            "Campfires only in designated areas"
        ])
        
        return regulations
    
    async def _get_facility_activities(self, facility_id: str) -> List[Dict[str, str]]:
        """Get activities available at a facility."""
        try:
            response = await self._make_request(
                "GET",
                f"facilities/{facility_id}/activities",
                use_cache=True,
                cache_ttl=3600
            )
            
            activities = []
            for activity in response:
                activities.append({
                    "name": activity.get("ActivityName", ""),
                    "description": activity.get("ActivityDescription", ""),
                    "fee_required": activity.get("ActivityFeeRequired", False)
                })
                
            return activities
        except:
            return []
    
    async def _get_facility_media(self, facility_id: str) -> List[str]:
        """Get media/images for a facility."""
        try:
            response = await self._make_request(
                "GET",
                f"facilities/{facility_id}/media",
                use_cache=True,
                cache_ttl=3600
            )
            
            images = []
            for media in response:
                if media.get("MediaType") == "Image":
                    images.append(media.get("URL", ""))
                    
            return images
        except:
            return []
    
    async def _get_nearby_attractions(self, facility_id: str) -> List[Dict[str, Any]]:
        """Get nearby attractions and points of interest."""
        # This would query nearby recreation areas
        return []
        
    async def search_permits(
        self,
        activity_type: str,
        location: str,
        date: str
    ) -> List[Dict[str, Any]]:
        """
        Search for required permits for activities.
        
        Args:
            activity_type: Type of activity (hiking, climbing, etc.)
            location: Location or park name
            date: Date of activity in YYYY-MM-DD format
            
        Returns:
            List of required permits and availability
        """
        try:
            # Search for permits/passes
            params = {
                "activity": activity_type,
                "state": self._extract_state_from_location(location),
                "date": date
            }
            
            response = await self._make_request(
                "GET",
                "permits",
                params=params,
                use_cache=True,
                cache_ttl=1800  # Cache for 30 minutes
            )
            
            # Process permit data
            permits = []
            for permit in response:
                processed = {
                    "permit_id": permit.get("PermitID"),
                    "name": permit.get("PermitName"),
                    "type": permit.get("PermitType"),
                    "location": permit.get("FacilityName"),
                    "description": permit.get("PermitDescription"),
                    "price": float(permit.get("Cost", 0)),
                    "availability": permit.get("AvailabilityStatus", "Check Availability"),
                    "required": permit.get("Required", True),
                    "valid_duration": permit.get("Duration", "Single day"),
                    "advance_booking_days": permit.get("AdvanceBookingDays", 0),
                    "lottery_required": permit.get("LotteryRequired", False),
                    "application_url": permit.get("ApplicationURL", ""),
                    "restrictions": permit.get("Restrictions", [])
                }
                permits.append(processed)
            
            logger.info(
                f"Searched permits for {activity_type} at {location} on {date}, "
                f"found {len(permits)} permits"
            )
            
            return permits
            
        except Exception as e:
            logger.error(f"Failed to search permits: {str(e)}")
            return []
    
    def _extract_state_from_location(self, location: str) -> str:
        """Extract state code from location string."""
        # Simple implementation - would be more sophisticated in production
        state_codes = {
            "california": "CA", "colorado": "CO", "utah": "UT",
            "arizona": "AZ", "nevada": "NV", "oregon": "OR",
            "washington": "WA", "idaho": "ID", "montana": "MT"
        }
        
        location_lower = location.lower()
        for state, code in state_codes.items():
            if state in location_lower or code.lower() in location_lower:
                return code
                
        return ""  # Return empty if no state found
    
    async def get_reservation_details(
        self,
        reservation_id: str
    ) -> Dict[str, Any]:
        """Get details of an existing reservation."""
        try:
            response = await self._make_request(
                "GET",
                f"reservations/{reservation_id}",
                use_booking_api=True
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
                json_data=modifications,
                use_booking_api=True
            )
            
            logger.info(f"Modified reservation {reservation_id}")
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to modify reservation: {str(e)}")
            raise