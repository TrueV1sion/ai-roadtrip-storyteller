"""Shell Recharge EV charging station booking integration client with production-ready features."""

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


class ShellRechargeClient:
    """Production-ready client for Shell Recharge EV charging station API integration."""
    
    # API Error codes mapping
    ERROR_CODES = {
        "STATION_NOT_FOUND": "The requested charging station could not be found",
        "CONNECTOR_UNAVAILABLE": "The selected connector is not available",
        "INVALID_SESSION": "Invalid or expired charging session",
        "PAYMENT_REQUIRED": "Payment method required for this transaction",
        "VEHICLE_INCOMPATIBLE": "Vehicle not compatible with connector type",
        "RESERVATION_CONFLICT": "Time slot already reserved",
        "MAX_DURATION_EXCEEDED": "Requested duration exceeds maximum allowed",
        "AUTHENTICATION_FAILED": "User authentication failed"
    }
    
    def __init__(self):
        """Initialize Shell Recharge client with production configuration."""
        # API Credentials
        self.api_key = os.getenv("SHELL_RECHARGE_API_KEY", "")
        self.api_secret = os.getenv("SHELL_RECHARGE_API_SECRET", "")
        self.client_id = os.getenv("SHELL_RECHARGE_CLIENT_ID", "")
        
        # OAuth2 tokens
        self.oauth_token = os.getenv("SHELL_RECHARGE_OAUTH_TOKEN", "")
        self.oauth_refresh_token = os.getenv("SHELL_RECHARGE_OAUTH_REFRESH_TOKEN", "")
        self._token_expires_at = 0
        
        # API Configuration
        self.base_url = os.getenv(
            "SHELL_RECHARGE_API_URL",
            "https://api.shellrecharge.com/v2"
        )
        self.auth_url = os.getenv(
            "SHELL_RECHARGE_AUTH_URL",
            "https://auth.shellrecharge.com/oauth/token"
        )
        self.websocket_url = os.getenv(
            "SHELL_RECHARGE_WS_URL",
            "wss://ws.shellrecharge.com/v2"
        )
        
        # Request configuration
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.user_agent = "RoadTripStorytellerAPI/1.0"
        
        # Rate limiting
        self.rate_limit_delay = 0.15  # 150ms between requests
        self._last_request_time = 0
        self._request_count = 0
        self._rate_limit_window_start = time.time()
        self._max_requests_per_minute = 40
        
        # Circuit breaker settings
        self._circuit_breaker_failures = 0
        self._circuit_breaker_threshold = 5
        self._circuit_breaker_timeout = 60  # seconds
        self._circuit_breaker_opened_at = 0
        
        # Mock mode for testing
        self.mock_mode = os.getenv("SHELL_RECHARGE_MOCK_MODE", "false").lower() == "true"
        
        # Request signing
        self.sign_requests = os.getenv("SHELL_RECHARGE_SIGN_REQUESTS", "true").lower() == "true"
        
        # WebSocket connections for real-time updates
        self._websocket_sessions = {}
        
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
            "recoverable": error_code not in ["STATION_NOT_FOUND", "VEHICLE_INCOMPATIBLE"]
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
            cache_key = f"shellrecharge:{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
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
            "User-Agent": self.user_agent
        }
        
        # Add authentication
        if self.oauth_token:
            token = await self._get_oauth_token()
            headers["Authorization"] = f"Bearer {token}"
        elif self.api_key:
            headers["X-API-Key"] = self.api_key
            
        # Add request signature if enabled
        if self.sign_requests:
            body_str = json.dumps(json_data) if json_data else ""
            signature = self._sign_request(method, url, timestamp, body_str)
            if signature:
                headers["X-Signature"] = signature
                headers["X-Client-ID"] = self.client_id
        
        # Log request details
        logger.info(f"Shell Recharge API Request: {method} {endpoint}")
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
                    if response.status in [200, 201, 202]:
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
                        error_code = error_data.get("error_code", "BAD_REQUEST")
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
                            message="Shell Recharge API server error"
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
            logger.error(f"Shell Recharge API client error: {str(e)}")
            raise
        except Exception as e:
            self._record_failure()
            logger.error(f"Unexpected error calling Shell Recharge API: {str(e)}")
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
        if "locations/nearby" in endpoint:
            return await self._get_mock_stations(params)
        elif "connectors" in endpoint and "availability" in endpoint:
            return await self._get_mock_availability(endpoint, params)
        elif "sessions" in endpoint and method == "POST":
            return await self._get_mock_session(json_data)
        elif "reservations" in endpoint and method == "POST":
            return await self._get_mock_reservation(json_data)
        else:
            return {"mock": True, "endpoint": endpoint}
            
    async def search_charging_stations(
        self,
        latitude: float,
        longitude: float,
        radius_miles: float = 25,
        connector_type: Optional[str] = None,
        min_power_kw: Optional[int] = None,
        available_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search for EV charging stations near a location.
        
        Args:
            latitude: Latitude of search location
            longitude: Longitude of search location
            radius_miles: Search radius in miles
            connector_type: Optional connector type filter (CCS, CHAdeMO, Type2)
            min_power_kw: Minimum charging power in kW
            available_only: Only show currently available stations
            
        Returns:
            List of charging station data with availability
        """
        # Build search parameters
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "radius": int(radius_miles * 1.60934),  # Convert to km
            "limit": 50,
            "include": "connectors,pricing,amenities"
        }
        
        # Add filters
        filters = []
        if connector_type:
            filters.append(f"connector_type:{connector_type}")
        if min_power_kw:
            filters.append(f"min_power:{min_power_kw}")
        if available_only:
            filters.append("status:available")
            
        if filters:
            params["filter"] = ",".join(filters)
        
        try:
            # Make API request with caching
            response = await self._make_request(
                "GET",
                "locations/nearby",
                params=params,
                use_cache=True,
                cache_ttl=300  # Cache for 5 minutes
            )
            
            # Process station data
            stations = []
            for location in response.get("data", []):
                # Get real-time availability for each station
                availability = await self._get_station_availability(location["id"])
                
                processed = {
                    "id": location["id"],
                    "name": location["name"],
                    "operator": location.get("operator", "Shell Recharge"),
                    "address": location["address"]["street"],
                    "city": location["address"]["city"],
                    "latitude": location["coordinates"]["latitude"],
                    "longitude": location["coordinates"]["longitude"],
                    "distance_miles": round(location["distance"] / 1.60934, 1),
                    "connectors": self._process_connectors(location.get("connectors", []), availability),
                    "amenities": location.get("amenities", []),
                    "access_hours": location.get("access_info", {}).get("hours", "24/7"),
                    "access_restrictions": location.get("access_info", {}).get("restrictions", []),
                    "payment_methods": location.get("payment_methods", []),
                    "network": "Shell Recharge",
                    "rating": location.get("rating", {}).get("average", 0),
                    "review_count": location.get("rating", {}).get("count", 0),
                    "last_updated": location.get("last_updated", "")
                }
                stations.append(processed)
            
            # Sort by distance
            stations.sort(key=lambda x: x["distance_miles"])
            
            logger.info(
                f"Searched charging stations near ({latitude}, {longitude}) "
                f"within {radius_miles} miles, found {len(stations)} results"
            )
            
            return stations
            
        except Exception as e:
            logger.error(f"Failed to search charging stations: {str(e)}")
            return []
    
    def _process_connectors(self, connectors: List[Dict], availability: Dict) -> List[Dict]:
        """Process connector data with real-time availability."""
        processed = []
        
        for connector in connectors:
            conn_id = connector["id"]
            status = availability.get(conn_id, {}).get("status", "unknown")
            
            processed.append({
                "id": conn_id,
                "type": connector["type"],
                "power_kw": connector["max_power_kw"],
                "status": status,
                "current_session": availability.get(conn_id, {}).get("session_id"),
                "price_per_kwh": connector.get("pricing", {}).get("per_kwh", 0),
                "price_per_minute": connector.get("pricing", {}).get("per_minute", 0),
                "session_fee": connector.get("pricing", {}).get("session_fee", 0),
                "supported_vehicles": connector.get("compatibility", [])
            })
            
        return processed
    
    async def _get_station_availability(self, station_id: str) -> Dict[str, Any]:
        """Get real-time availability for a station's connectors."""
        try:
            response = await self._make_request(
                "GET",
                f"locations/{station_id}/availability",
                use_cache=True,
                cache_ttl=60  # Cache for 1 minute
            )
            
            # Map connector availability
            availability = {}
            for connector in response.get("connectors", []):
                availability[connector["id"]] = {
                    "status": connector["status"],
                    "session_id": connector.get("active_session_id"),
                    "estimated_available": connector.get("estimated_available_time")
                }
                
            return availability
            
        except Exception:
            # Return empty availability on error
            return {}
            
    async def check_availability(
        self,
        station_id: str,
        connector_id: str,
        duration_minutes: int = 30
    ) -> Dict[str, Any]:
        """
        Check real-time availability of a specific connector.
        
        Args:
            station_id: Charging station identifier
            connector_id: Specific connector identifier
            duration_minutes: Desired charging duration
            
        Returns:
            Current status and reservation options
        """
        try:
            # Get connector details and status
            response = await self._make_request(
                "GET",
                f"locations/{station_id}/connectors/{connector_id}",
                params={"include": "status,pricing,reservations"}
            )
            
            connector = response.get("data", {})
            status = connector.get("status", "unknown")
            
            # Calculate pricing estimate
            pricing = connector.get("pricing", {})
            estimated_kwh = duration_minutes * (connector.get("max_power_kw", 50) / 60) * 0.85  # 85% efficiency
            
            price_estimate = {
                "duration_minutes": duration_minutes,
                "estimated_kwh": round(estimated_kwh, 1),
                "price_per_kwh": pricing.get("per_kwh", 0),
                "price_per_minute": pricing.get("per_minute", 0),
                "session_fee": pricing.get("session_fee", 0),
                "total_cost": self._calculate_total_cost(pricing, duration_minutes, estimated_kwh),
                "currency": pricing.get("currency", "USD")
            }
            
            # Get upcoming reservations
            reservations = []
            if status == "available":
                upcoming = connector.get("upcoming_reservations", [])
                for res in upcoming[:3]:  # Show next 3 reservations
                    reservations.append({
                        "start_time": res["start_time"],
                        "duration_minutes": res["duration_minutes"],
                        "buffer_minutes": 15  # Buffer between sessions
                    })
            
            result = {
                "station_id": station_id,
                "connector_id": connector_id,
                "connector_type": connector.get("type", ""),
                "max_power_kw": connector.get("max_power_kw", 0),
                "current_status": status,
                "current_session": connector.get("active_session", {}),
                "estimated_wait_minutes": self._estimate_wait_time(connector),
                "reservation_available": status == "available" or status == "reserved",
                "max_reservation_duration": 240,  # 4 hours max
                "min_reservation_duration": 15,   # 15 minutes min
                "price_estimate": price_estimate,
                "upcoming_reservations": reservations,
                "operating_status": connector.get("operating_status", "operational"),
                "last_maintenance": connector.get("last_maintenance_date", ""),
                "supported_payment": connector.get("payment_methods", [])
            }
            
            logger.info(
                f"Checked availability for connector {connector_id} "
                f"at station {station_id}: {status}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to check availability: {str(e)}")
            raise
    
    def _calculate_total_cost(self, pricing: Dict, duration_minutes: int, kwh: float) -> float:
        """Calculate total charging cost."""
        total = pricing.get("session_fee", 0)
        total += pricing.get("per_kwh", 0) * kwh
        total += pricing.get("per_minute", 0) * duration_minutes
        
        # Apply time-of-use pricing if applicable
        if "time_of_use" in pricing:
            current_hour = datetime.now().hour
            for period in pricing["time_of_use"]:
                if period["start_hour"] <= current_hour < period["end_hour"]:
                    total *= period.get("multiplier", 1.0)
                    break
                    
        return round(total, 2)
    
    def _estimate_wait_time(self, connector: Dict) -> int:
        """Estimate wait time based on current session."""
        if connector.get("status") != "occupied":
            return 0
            
        session = connector.get("active_session", {})
        if not session:
            return 15  # Default estimate
            
        # Calculate based on current charge level and target
        start_time = datetime.fromisoformat(session.get("start_time", "").replace("Z", "+00:00"))
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() / 60
        
        current_soc = session.get("vehicle_soc", 50)
        target_soc = session.get("target_soc", 80)
        
        if current_soc >= target_soc:
            return 5  # Should be done soon
            
        # Estimate remaining time based on charge rate
        charge_rate = session.get("current_power_kw", connector.get("max_power_kw", 50))
        battery_capacity = session.get("vehicle_battery_kwh", 60)
        
        remaining_kwh = (target_soc - current_soc) / 100 * battery_capacity
        remaining_minutes = (remaining_kwh / charge_rate) * 60
        
        return int(min(remaining_minutes, 120))  # Cap at 2 hours
        
    async def create_reservation(
        self,
        station_id: str,
        connector_id: str,
        start_time: str,
        duration_minutes: int,
        vehicle_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a charging session reservation.
        
        Args:
            station_id: Charging station identifier
            connector_id: Specific connector identifier
            start_time: Reservation start time in ISO format
            duration_minutes: Charging duration in minutes
            vehicle_info: Vehicle and driver information
            
        Returns:
            Reservation confirmation details
        """
        # Validate start time
        start_datetime = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        if start_datetime < datetime.now(timezone.utc):
            raise ValueError("Cannot create reservation for past time")
            
        if start_datetime > datetime.now(timezone.utc) + timedelta(days=14):
            raise ValueError("Cannot create reservation more than 14 days in advance")
        
        # Build reservation request
        reservation_data = {
            "station_id": station_id,
            "connector_id": connector_id,
            "start_time": start_time,
            "duration_minutes": duration_minutes,
            "vehicle": {
                "make": vehicle_info.get("make", "Unknown"),
                "model": vehicle_info.get("model", "Unknown"),
                "year": vehicle_info.get("year"),
                "battery_capacity_kwh": vehicle_info.get("battery_capacity", 60),
                "connector_type": vehicle_info.get("connector_type", "CCS"),
                "license_plate": vehicle_info.get("license_plate", "")
            },
            "driver": {
                "name": vehicle_info.get("driver_name", ""),
                "phone": vehicle_info.get("driver_phone", ""),
                "email": vehicle_info.get("driver_email", ""),
                "member_id": vehicle_info.get("member_id", "")
            },
            "preferences": {
                "target_soc": vehicle_info.get("target_soc", 80),
                "notifications": vehicle_info.get("notifications", {
                    "sms": True,
                    "email": True,
                    "push": True
                })
            },
            "payment_method_id": vehicle_info.get("payment_method_id")
        }
        
        try:
            # Create reservation
            response = await self._make_request(
                "POST",
                "reservations",
                json_data=reservation_data
            )
            
            # Process confirmation
            confirmation = {
                "reservation_id": response["id"],
                "confirmation_code": response["confirmation_code"],
                "station_id": station_id,
                "station_name": response.get("station_name", ""),
                "station_address": response.get("station_address", ""),
                "connector_id": connector_id,
                "connector_type": response.get("connector_type", ""),
                "power_kw": response.get("max_power_kw", 0),
                "start_time": start_datetime.isoformat(),
                "end_time": (start_datetime + timedelta(minutes=duration_minutes)).isoformat(),
                "duration_minutes": duration_minutes,
                "vehicle_make": vehicle_info.get("make", "Unknown"),
                "vehicle_model": vehicle_info.get("model", "Unknown"),
                "estimated_cost": response.get("estimated_cost", {}),
                "grace_period_minutes": response.get("grace_period", 10),
                "late_fee_per_minute": response.get("late_fee", 0.50),
                "status": "confirmed",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "qr_code": response.get("qr_code_url", ""),
                "activation_code": response.get("activation_code", ""),
                "instructions": response.get("instructions", "Scan QR code or enter activation code at station"),
                "cancellation_policy": response.get("cancellation_policy", {
                    "free_cancellation_minutes": 60,
                    "cancellation_fee": 5.00
                }),
                "modification_allowed": response.get("modification_allowed", True),
                "reminders_scheduled": response.get("reminders", {
                    "email": True,
                    "sms": vehicle_info.get("driver_phone") is not None,
                    "push": True
                })
            }
            
            logger.info(
                f"Created reservation {confirmation['reservation_id']} for connector {connector_id} "
                f"at station {station_id} from {start_time} for {duration_minutes} minutes"
            )
            
            # Start monitoring for the reservation
            asyncio.create_task(self._monitor_reservation(confirmation["reservation_id"]))
            
            return confirmation
            
        except ClientResponseError as e:
            if e.status == 409:
                raise ValueError("Time slot is no longer available")
            elif e.status == 400:
                raise ValueError("Invalid reservation details")
            raise
        except Exception as e:
            logger.error(f"Failed to create reservation: {str(e)}")
            raise
            
    async def _monitor_reservation(self, reservation_id: str):
        """Monitor reservation for updates via WebSocket."""
        try:
            # This would establish WebSocket connection for real-time updates
            logger.info(f"Started monitoring reservation {reservation_id}")
        except Exception as e:
            logger.error(f"Failed to monitor reservation: {str(e)}")
            
    async def start_charging_session(
        self,
        reservation_id: str,
        connector_id: str
    ) -> Dict[str, Any]:
        """
        Start a charging session (with or without reservation).
        
        Args:
            reservation_id: Optional reservation ID
            connector_id: Connector to start charging on
            
        Returns:
            Active session details
        """
        # Build session request
        session_data = {
            "connector_id": connector_id,
            "reservation_id": reservation_id,
            "start_method": "app",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Start charging session
            response = await self._make_request(
                "POST",
                "sessions",
                json_data=session_data
            )
            
            # Process session data
            session = {
                "session_id": response["id"],
                "reservation_id": reservation_id,
                "connector_id": connector_id,
                "connector_type": response.get("connector_type", ""),
                "start_time": response["start_time"],
                "status": "active",
                "current_kwh": 0,
                "current_cost": 0,
                "current_duration_minutes": 0,
                "charging_speed_kw": response.get("initial_power_kw", 0),
                "max_power_kw": response.get("max_power_kw", 0),
                "vehicle_connected": True,
                "vehicle_battery_level": response.get("initial_soc", 0),
                "target_battery_level": response.get("target_soc", 80),
                "estimated_completion": response.get("estimated_completion_time", ""),
                "energy_meter_start": response.get("meter_reading_kwh", 0),
                "pricing": response.get("pricing", {}),
                "updates_url": f"{self.websocket_url}/sessions/{response['id']}/updates",
                "emergency_stop_code": response.get("emergency_stop_code", ""),
                "support_phone": response.get("support_phone", "+1-800-SHELL-EV")
            }
            
            logger.info(f"Started charging session {session['session_id']} on connector {connector_id}")
            
            # Start real-time monitoring
            asyncio.create_task(self._monitor_session(session["session_id"]))
            
            return session
            
        except Exception as e:
            logger.error(f"Failed to start charging session: {str(e)}")
            raise
            
    async def _monitor_session(self, session_id: str):
        """Monitor active session for updates via WebSocket."""
        try:
            # This would establish WebSocket connection for real-time updates
            ws_url = f"{self.websocket_url}/sessions/{session_id}/updates"
            
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(ws_url) as ws:
                    self._websocket_sessions[session_id] = ws
                    
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            update = json.loads(msg.data)
                            logger.debug(f"Session {session_id} update: {update}")
                            # Process updates (power changes, cost updates, etc.)
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logger.error(f"WebSocket error for session {session_id}")
                            break
                            
        except Exception as e:
            logger.error(f"Failed to monitor session: {str(e)}")
        finally:
            self._websocket_sessions.pop(session_id, None)
            
    async def get_session_status(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """Get current status of a charging session."""
        try:
            response = await self._make_request(
                "GET",
                f"sessions/{session_id}"
            )
            
            # Add calculated fields
            start_time = datetime.fromisoformat(response["start_time"].replace("Z", "+00:00"))
            duration = (datetime.now(timezone.utc) - start_time).total_seconds() / 60
            
            response["current_duration_minutes"] = int(duration)
            response["estimated_completion_minutes"] = self._estimate_completion_time(response)
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to get session status: {str(e)}")
            raise
            
    def _estimate_completion_time(self, session: Dict) -> int:
        """Estimate remaining charging time."""
        current_soc = session.get("current_soc", 0)
        target_soc = session.get("target_soc", 80)
        
        if current_soc >= target_soc:
            return 0
            
        current_power = session.get("current_power_kw", 0)
        if current_power == 0:
            return -1  # Cannot estimate
            
        battery_capacity = session.get("vehicle_battery_kwh", 60)
        remaining_kwh = (target_soc - current_soc) / 100 * battery_capacity
        
        # Account for charging curve (slower at higher SOC)
        if current_soc > 80:
            current_power *= 0.5
        elif current_soc > 60:
            current_power *= 0.8
            
        return int((remaining_kwh / current_power) * 60)
        
    async def stop_charging_session(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Stop an active charging session.
        
        Args:
            session_id: Active session identifier
            
        Returns:
            Final session details and receipt
        """
        try:
            # Stop the session
            response = await self._make_request(
                "POST",
                f"sessions/{session_id}/stop"
            )
            
            # Close WebSocket if monitoring
            if session_id in self._websocket_sessions:
                await self._websocket_sessions[session_id].close()
                del self._websocket_sessions[session_id]
            
            # Process final receipt
            receipt = {
                "session_id": session_id,
                "status": "completed",
                "start_time": response["start_time"],
                "end_time": response["end_time"],
                "duration_minutes": response["duration_minutes"],
                "energy_delivered_kwh": response["total_energy_kwh"],
                "peak_power_kw": response.get("peak_power_kw", 0),
                "average_power_kw": response.get("average_power_kw", 0),
                "final_cost": {
                    "energy_cost": response["costs"]["energy_cost"],
                    "time_cost": response["costs"].get("time_cost", 0),
                    "session_fee": response["costs"].get("session_fee", 0),
                    "taxes": response["costs"].get("taxes", 0),
                    "total": response["costs"]["total"],
                    "currency": response["costs"]["currency"]
                },
                "payment_status": response.get("payment_status", "completed"),
                "payment_method": response.get("payment_method", {}),
                "receipt_url": response.get("receipt_url", ""),
                "invoice_available": response.get("invoice_available", True),
                "vehicle_battery_level_start": response.get("initial_soc", 0),
                "vehicle_battery_level_end": response.get("final_soc", 0),
                "co2_saved_kg": response.get("environmental_impact", {}).get("co2_saved", 0),
                "green_energy_percentage": response.get("environmental_impact", {}).get("renewable_percentage", 0),
                "loyalty_points_earned": response.get("loyalty_points", 0),
                "feedback_requested": True
            }
            
            logger.info(
                f"Stopped charging session {session_id}. "
                f"Duration: {receipt['duration_minutes']} min, "
                f"Energy: {receipt['energy_delivered_kwh']} kWh, "
                f"Cost: {receipt['final_cost']['total']} {receipt['final_cost']['currency']}"
            )
            
            return receipt
            
        except Exception as e:
            logger.error(f"Failed to stop charging session: {str(e)}")
            raise
            
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
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Cancel reservation
            response = await self._make_request(
                "DELETE",
                f"reservations/{reservation_id}",
                json_data=cancellation_data
            )
            
            result = {
                "reservation_id": reservation_id,
                "status": "cancelled",
                "cancelled_at": response.get("cancelled_at", datetime.now(timezone.utc).isoformat()),
                "reason": reason or "Customer requested",
                "cancellation_number": response.get("cancellation_number", ""),
                "refund_status": response.get("refund_status", "No charge applied"),
                "cancellation_fee": response.get("cancellation_fee", 0),
                "fee_waived": response.get("fee_waived", False),
                "email_confirmation_sent": response.get("notifications_sent", {}).get("email", True),
                "sms_confirmation_sent": response.get("notifications_sent", {}).get("sms", False)
            }
            
            logger.info(f"Cancelled reservation {reservation_id}")
            
            return result
            
        except ClientResponseError as e:
            if e.status == 404:
                raise ValueError(f"Reservation {reservation_id} not found")
            elif e.status == 400:
                raise ValueError("Reservation cannot be cancelled")
            raise
        except Exception as e:
            logger.error(f"Failed to cancel reservation: {str(e)}")
            raise
            
    async def get_station_details(
        self,
        station_id: str
    ) -> Dict[str, Any]:
        """
        Get detailed information about a charging station.
        
        Args:
            station_id: Charging station identifier
            
        Returns:
            Detailed station information
        """
        try:
            # Get station details with all related data
            response = await self._make_request(
                "GET",
                f"locations/{station_id}",
                params={"include": "connectors,amenities,ratings,media,pricing"},
                use_cache=True,
                cache_ttl=3600  # Cache for 1 hour
            )
            
            location = response.get("data", {})
            
            # Get current availability
            availability = await self._get_station_availability(station_id)
            
            # Process station details
            details = {
                "id": station_id,
                "name": location["name"],
                "operator": location.get("operator", "Shell Recharge Solutions"),
                "network": "Shell Recharge",
                "address": {
                    "street": location["address"]["street"],
                    "city": location["address"]["city"],
                    "state": location["address"]["state"],
                    "zip": location["address"]["postal_code"],
                    "country": location["address"]["country"]
                },
                "coordinates": {
                    "latitude": location["coordinates"]["latitude"],
                    "longitude": location["coordinates"]["longitude"]
                },
                "connectors": self._process_connectors(location.get("connectors", []), availability),
                "total_connectors": len(location.get("connectors", [])),
                "available_connectors": sum(1 for c in availability.values() if c.get("status") == "available"),
                "amenities": location.get("amenities", []),
                "dining_options": location.get("nearby_dining", []),
                "shopping_options": location.get("nearby_shopping", []),
                "access_info": {
                    "hours": location.get("access_info", {}).get("hours", "24/7"),
                    "restricted": location.get("access_info", {}).get("restricted", False),
                    "membership_required": location.get("access_info", {}).get("membership_required", False),
                    "parking_fee": location.get("access_info", {}).get("parking_fee", False),
                    "parking_time_limit": location.get("access_info", {}).get("parking_time_limit"),
                    "security": location.get("access_info", {}).get("security_features", [])
                },
                "payment_methods": location.get("payment_methods", []),
                "pricing_summary": location.get("pricing_summary", {}),
                "sustainability": {
                    "renewable_energy": location.get("renewable_energy_percentage", 0),
                    "carbon_offset": location.get("carbon_offset_available", False),
                    "green_certified": location.get("green_certification", False)
                },
                "ratings": {
                    "overall": location.get("rating", {}).get("average", 0),
                    "reliability": location.get("rating", {}).get("reliability", 0),
                    "accessibility": location.get("rating", {}).get("accessibility", 0),
                    "value": location.get("rating", {}).get("value", 0),
                    "total_reviews": location.get("rating", {}).get("count", 0)
                },
                "recent_reviews": location.get("recent_reviews", [])[:5],
                "images": location.get("media", {}).get("images", []),
                "contact": {
                    "support_phone": location.get("support_phone", "+1-800-SHELL-EV"),
                    "email": location.get("support_email", ""),
                    "website": location.get("website", "")
                },
                "features": location.get("special_features", []),
                "partner_benefits": location.get("partner_benefits", []),
                "upcoming_maintenance": location.get("maintenance_schedule", []),
                "statistics": {
                    "average_session_duration": location.get("stats", {}).get("avg_duration_minutes", 0),
                    "peak_hours": location.get("stats", {}).get("peak_hours", []),
                    "utilization_rate": location.get("stats", {}).get("utilization_percentage", 0)
                }
            }
            
            logger.info(f"Retrieved details for charging station {station_id}")
            
            return details
            
        except Exception as e:
            logger.error(f"Failed to get station details: {str(e)}")
            raise
            
    async def get_charging_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get user's charging session history.
        
        Args:
            user_id: User identifier
            limit: Maximum number of sessions to return
            
        Returns:
            List of past charging sessions
        """
        try:
            # Get user's charging history
            response = await self._make_request(
                "GET",
                "users/me/sessions",
                params={
                    "limit": limit,
                    "sort": "start_time:desc",
                    "include": "location,costs,environmental_impact"
                },
                use_cache=True,
                cache_ttl=300  # Cache for 5 minutes
            )
            
            # Process session history
            sessions = []
            for session in response.get("data", []):
                processed = {
                    "session_id": session["id"],
                    "station_name": session["location"]["name"],
                    "station_address": session["location"]["address"]["city"],
                    "connector_type": session["connector_type"],
                    "date": session["start_time"][:10],
                    "start_time": session["start_time"],
                    "duration_minutes": session["duration_minutes"],
                    "energy_kwh": session["energy_delivered_kwh"],
                    "peak_power_kw": session.get("peak_power_kw", 0),
                    "cost": session["total_cost"],
                    "currency": session["currency"],
                    "payment_method": session.get("payment_method", ""),
                    "vehicle": f"{session.get('vehicle_make', '')} {session.get('vehicle_model', '')}".strip(),
                    "battery_start": session.get("initial_soc", 0),
                    "battery_end": session.get("final_soc", 0),
                    "co2_saved": session.get("environmental_impact", {}).get("co2_saved_kg", 0),
                    "renewable_energy": session.get("environmental_impact", {}).get("renewable_percentage", 0),
                    "rating": session.get("user_rating"),
                    "receipt_url": session.get("receipt_url", "")
                }
                sessions.append(processed)
            
            logger.info(f"Retrieved {len(sessions)} charging sessions for user {user_id}")
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get charging history: {str(e)}")
            return []
            
    async def get_charging_statistics(
        self,
        user_id: str,
        period: str = "month"
    ) -> Dict[str, Any]:
        """Get user's charging statistics and insights."""
        try:
            response = await self._make_request(
                "GET",
                f"users/me/statistics",
                params={"period": period},
                use_cache=True,
                cache_ttl=3600  # Cache for 1 hour
            )
            
            return response.get("data", {})
            
        except Exception as e:
            logger.error(f"Failed to get charging statistics: {str(e)}")
            return {}
            
    async def _get_mock_stations(self, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Get mock station data for testing."""
        return {
            "data": [{
                "id": "shell_ev_001",
                "name": "Shell Recharge Highway Plaza",
                "address": {
                    "street": "Highway 101 Service Area",
                    "city": "San Francisco"
                },
                "coordinates": {
                    "latitude": params.get("latitude", 0) + 0.02,
                    "longitude": params.get("longitude", 0) + 0.01
                },
                "distance": 8366,  # meters
                "connectors": [
                    {
                        "id": "conn_001",
                        "type": "CCS",
                        "max_power_kw": 150,
                        "pricing": {"per_kwh": 0.35}
                    }
                ],
                "amenities": ["Restrooms", "Coffee Shop"],
                "rating": {"average": 4.5, "count": 128}
            }]
        }
        
    async def _get_mock_availability(self, endpoint: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Get mock availability data for testing."""
        return {
            "data": {
                "status": "available",
                "connector_type": "CCS",
                "max_power_kw": 150,
                "pricing": {
                    "per_kwh": 0.35,
                    "session_fee": 0,
                    "currency": "USD"
                }
            }
        }
        
    async def _get_mock_session(self, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Get mock session data for testing."""
        return {
            "id": f"SESS{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "initial_power_kw": 145,
            "max_power_kw": 150,
            "initial_soc": 35,
            "target_soc": 80,
            "pricing": {
                "per_kwh": 0.35,
                "currency": "USD"
            }
        }
        
    async def _get_mock_reservation(self, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Get mock reservation data for testing."""
        return {
            "id": f"SR{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "confirmation_code": "MOCK123",
            "station_name": "Shell Recharge Highway Plaza",
            "connector_type": "CCS",
            "max_power_kw": 150,
            "estimated_cost": {
                "total": 10.50,
                "currency": "USD"
            },
            "qr_code_url": "https://shellrecharge.com/qr/mock123"
        }