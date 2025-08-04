"""
Resy API client for restaurant reservations.
Resy focuses on trendy, upscale restaurants in major cities.
"""

import httpx
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date, time
from decimal import Decimal
import jwt
from urllib.parse import urlencode

from app.core.config import settings
from app.core.cache import cache_manager
from app.core.logger import logger
from app.core.resilience import CircuitBreaker, circuit_breaker_factory
from app.core.http_client import AsyncHTTPClient, TimeoutProfile, TimeoutError


class ResyClient:
    """Client for Resy API integration."""
    
    BASE_URL = "https://api.resy.com"
    AUTH_URL = "https://auth.resy.com"
    
    def __init__(self):
        self.client_id = settings.RESY_CLIENT_ID
        self.client_secret = settings.RESY_CLIENT_SECRET
        self.api_key = settings.RESY_API_KEY
        
        # Use standard timeout profile for Resy API
        self.client = AsyncHTTPClient(timeout_profile=TimeoutProfile.STANDARD)
        self.default_headers = {
            "Authorization": f"ResyAPI api_key={self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # Circuit breaker for fault tolerance
        self.circuit_breaker = circuit_breaker_factory.create("resy_api")
        
        # Token management
        self._access_token = None
        self._token_expires_at = None
    
    async def search_restaurants(
        self,
        lat: float,
        lon: float,
        query: Optional[str] = None,
        cuisine_type: Optional[str] = None,
        price_range: Optional[List[int]] = None,
        radius_miles: float = 5.0,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Search for restaurants.
        
        Args:
            lat/lon: Geographic coordinates
            query: Search query
            cuisine_type: Type of cuisine
            price_range: List of price levels (1-4)
            radius_miles: Search radius
            limit: Number of results
            
        Returns:
            Search results with restaurants
        """
        cache_params = f"{lat}:{lon}:{query}:{cuisine_type}:{radius_miles}"
        cache_key = f"resy:search:{cache_params}"
        
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached
            
        try:
            params = {
                "lat": lat,
                "lng": lon,
                "radius": radius_miles,
                "limit": limit
            }
            
            if query:
                params["query"] = query
            
            if cuisine_type:
                params["cuisine"] = cuisine_type
                
            if price_range:
                params["price_range"] = ",".join(map(str, price_range))
            
            response = await self.circuit_breaker.call(
                self._make_request,
                "GET",
                "/3/venues",
                params=params
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Enhance results with availability hint
                venues = result.get("venues", [])
                for venue in venues:
                    venue["reservation_available"] = venue.get("available_slots", 0) > 0
                    venue["commission_eligible"] = True
                
                # Cache for 30 minutes
                await cache_manager.set(cache_key, result, ttl=1800)
                
                logger.info(f"Resy search returned {len(venues)} restaurants")
                return result
            else:
                logger.error(f"Resy search failed: {response.status_code}")
                return {"venues": [], "error": "Search failed"}
                
        except Exception as e:
            logger.error(f"Resy search error: {str(e)}")
            return {"venues": [], "error": str(e)}
    
    async def get_venue_details(
        self,
        venue_id: str,
        date: Optional[date] = None
    ) -> Optional[Dict[str, Any]]:
        """Get detailed information about a restaurant."""
        cache_key = f"resy:venue:{venue_id}:{date}"
        
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached
            
        try:
            params = {}
            if date:
                params["date"] = date.isoformat()
            
            response = await self.circuit_breaker.call(
                self._make_request,
                "GET",
                f"/3/venues/{venue_id}",
                params=params
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Cache for 1 hour
                await cache_manager.set(cache_key, result, ttl=3600)
                
                return result
            else:
                logger.error(f"Failed to get venue details: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting venue details: {str(e)}")
            return None
    
    async def find_available_slots(
        self,
        venue_id: str,
        date: date,
        party_size: int,
        time_preference: Optional[time] = None
    ) -> List[Dict[str, Any]]:
        """
        Find available reservation slots.
        
        Args:
            venue_id: Restaurant ID
            date: Reservation date
            party_size: Number of guests
            time_preference: Preferred time (will search +/- 2 hours)
            
        Returns:
            List of available time slots
        """
        try:
            params = {
                "venue_id": venue_id,
                "date": date.isoformat(),
                "party_size": party_size
            }
            
            if time_preference:
                params["time"] = time_preference.strftime("%H:%M")
            
            response = await self.circuit_breaker.call(
                self._make_request,
                "GET",
                "/3/find",
                params=params
            )
            
            if response.status_code == 200:
                result = response.json()
                slots = result.get("results", {}).get("venues", [])
                
                # Extract and format available slots
                available_slots = []
                for venue_data in slots:
                    for slot in venue_data.get("slots", []):
                        available_slots.append({
                            "time": slot.get("time"),
                            "date": slot.get("date"),
                            "config_id": slot.get("config", {}).get("id"),
                            "table_type": slot.get("config", {}).get("type"),
                            "pricing": slot.get("pricing"),
                            "availability": slot.get("availability", {})
                        })
                
                logger.info(f"Found {len(available_slots)} available slots")
                return available_slots
            else:
                logger.error(f"Failed to find slots: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error finding slots: {str(e)}")
            return []
    
    async def create_reservation(
        self,
        venue_id: str,
        config_id: str,
        date: date,
        party_size: int,
        guest_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a reservation.
        
        Args:
            venue_id: Restaurant ID
            config_id: Slot configuration ID
            date: Reservation date
            party_size: Number of guests
            guest_info: Guest details (name, email, phone)
            
        Returns:
            Reservation confirmation or error
        """
        try:
            # Ensure we have a valid token
            await self._ensure_authenticated()
            
            reservation_data = {
                "venue_id": venue_id,
                "config_id": config_id,
                "date": date.isoformat(),
                "party_size": party_size,
                "first_name": guest_info.get("first_name"),
                "last_name": guest_info.get("last_name"),
                "email": guest_info.get("email"),
                "phone_number": guest_info.get("phone"),
                "notes": guest_info.get("special_requests", "")
            }
            
            response = await self.circuit_breaker.call(
                self._make_request,
                "POST",
                "/3/reservations",
                json=reservation_data
            )
            
            if response.status_code in (200, 201):
                result = response.json()
                
                logger.info(f"Resy reservation created: {result.get('reservation_id')}")
                
                # Calculate commission (Resy typically offers 10-15% for upscale venues)
                # Note: Actual commission would come from partnership agreement
                commission_rate = 0.12  # 12% commission
                estimated_spend = party_size * 75  # Estimate $75 per person
                commission = estimated_spend * commission_rate
                
                result["commission"] = {
                    "amount": commission,
                    "rate": commission_rate,
                    "currency": "USD",
                    "estimated_spend": estimated_spend
                }
                
                return result
            else:
                logger.error(f"Reservation creation failed: {response.status_code}")
                error_data = response.json()
                return {
                    "success": False,
                    "error": error_data.get("message", "Reservation failed"),
                    "details": error_data
                }
                
        except Exception as e:
            logger.error(f"Error creating reservation: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_reservation(
        self,
        reservation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get reservation details."""
        try:
            await self._ensure_authenticated()
            
            response = await self.circuit_breaker.call(
                self._make_request,
                "GET",
                f"/3/reservations/{reservation_id}"
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get reservation: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting reservation: {str(e)}")
            return None
    
    async def cancel_reservation(
        self,
        reservation_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cancel a reservation."""
        try:
            await self._ensure_authenticated()
            
            cancel_data = {}
            if reason:
                cancel_data["cancellation_reason"] = reason
            
            response = await self.circuit_breaker.call(
                self._make_request,
                "DELETE",
                f"/3/reservations/{reservation_id}",
                json=cancel_data
            )
            
            if response.status_code in (200, 204):
                logger.info(f"Resy reservation cancelled: {reservation_id}")
                return {
                    "success": True,
                    "reservation_id": reservation_id,
                    "cancelled_at": datetime.utcnow().isoformat()
                }
            else:
                logger.error(f"Cancellation failed: {response.status_code}")
                return {
                    "success": False,
                    "error": f"Cancellation failed: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Error cancelling reservation: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_venue_availability_calendar(
        self,
        venue_id: str,
        start_date: date,
        end_date: date,
        party_size: int = 2
    ) -> Dict[str, List[str]]:
        """Get availability calendar for a venue."""
        try:
            params = {
                "venue_id": venue_id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "party_size": party_size
            }
            
            response = await self.circuit_breaker.call(
                self._make_request,
                "GET",
                "/3/venues/calendar",
                params=params
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("availability", {})
            else:
                logger.error(f"Failed to get calendar: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting calendar: {str(e)}")
            return {}
    
    async def _ensure_authenticated(self):
        """Ensure we have a valid access token."""
        if self._access_token and self._token_expires_at:
            if datetime.utcnow() < self._token_expires_at:
                return
        
        # Get new token
        await self._authenticate()
    
    async def _authenticate(self):
        """Authenticate and get access token."""
        try:
            auth_data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials"
            }
            
            response = await self.client.post(
                f"{self.AUTH_URL}/oauth/token",
                json=auth_data,
                headers=self.default_headers
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self._access_token = token_data["access_token"]
                
                # Calculate expiration (usually 3600 seconds)
                expires_in = token_data.get("expires_in", 3600)
                self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 60)
                
                # Update default headers with new token
                self.default_headers["Authorization"] = f"Bearer {self._access_token}"
                
                logger.info("Resy authentication successful")
            else:
                logger.error(f"Resy authentication failed: {response.status_code}")
                raise Exception("Authentication failed")
                
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
            raise
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request to Resy API with proper timeout handling."""
        url = f"{self.BASE_URL}{endpoint}"
        
        # Merge default headers with any provided headers
        headers = kwargs.get('headers', {})
        headers.update(self.default_headers)
        kwargs['headers'] = headers
        
        try:
            response = await self.client.request(
                method,
                url,
                **kwargs
            )
            return response
            
        except TimeoutError as e:
            logger.error(f"Resy API timeout for {method} {endpoint}: {e}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Resy API HTTP error {e.response.status_code} for {method} {endpoint}: {e}")
            raise
        except Exception as e:
            logger.error(f"Resy API error for {method} {endpoint}: {e}")
            raise
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.close()


# Singleton instance
resy_client = ResyClient()