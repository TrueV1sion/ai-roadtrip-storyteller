"""
Viator API client for activity and tour bookings.
Viator is a leading marketplace for tours, activities, and experiences.
"""

import httpx
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from decimal import Decimal
import hashlib
import hmac
import json

from backend.app.core.config import settings
from backend.app.core.cache import cache_manager
from backend.app.core.logger import logger
from backend.app.core.resilience import CircuitBreaker, circuit_breaker_factory


class ViatorClient:
    """Client for Viator Partner API integration."""
    
    BASE_URL = "https://api.viator.com/partner"
    SANDBOX_URL = "https://api.sandbox.viator.com/partner"
    
    def __init__(self):
        self.api_key = settings.VIATOR_API_KEY
        self.partner_id = settings.VIATOR_PARTNER_ID
        self.use_sandbox = settings.ENVIRONMENT != "production"
        self.base_url = self.SANDBOX_URL if self.use_sandbox else self.BASE_URL
        
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "exp-api-key": self.api_key,
                "Accept": "application/json;version=2.0",
                "Content-Type": "application/json"
            }
        )
        
        # Circuit breaker for fault tolerance
        self.circuit_breaker = circuit_breaker_factory.create("viator_api")
        
    async def search_products(
        self,
        destination_id: Optional[int] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_id: Optional[int] = None,
        subcategory_id: Optional[int] = None,
        max_price: Optional[float] = None,
        currency: str = "USD",
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Search for activities and tours.
        
        Args:
            destination_id: Viator destination ID
            lat/lon: Geographic coordinates
            start_date: Availability start date
            end_date: Availability end date
            category_id: Activity category
            subcategory_id: Activity subcategory
            max_price: Maximum price filter
            currency: Currency code
            limit: Number of results
            
        Returns:
            Search results with products
        """
        # Cache key based on search parameters
        cache_params = f"{destination_id}:{lat}:{lon}:{start_date}:{category_id}"
        cache_key = f"viator:search:{cache_params}"
        
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached
            
        try:
            # Build search request
            search_request = {
                "currency": currency,
                "limit": limit
            }
            
            # Add filters
            filters = []
            if destination_id:
                filters.append({
                    "type": "destination",
                    "value": destination_id
                })
            
            if lat and lon:
                filters.append({
                    "type": "location",
                    "value": {
                        "latitude": lat,
                        "longitude": lon,
                        "radius": 50  # 50km radius
                    }
                })
            
            if start_date and end_date:
                filters.append({
                    "type": "dateRange",
                    "value": {
                        "from": start_date.isoformat(),
                        "to": end_date.isoformat()
                    }
                })
            
            if category_id:
                filters.append({
                    "type": "category",
                    "value": category_id
                })
            
            if max_price:
                filters.append({
                    "type": "priceRange",
                    "value": {
                        "max": max_price,
                        "currency": currency
                    }
                })
            
            if filters:
                search_request["filters"] = filters
            
            # Execute search
            response = await self.circuit_breaker.call(
                self._make_request,
                "POST",
                "/search/products",
                json=search_request
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Cache for 1 hour
                await cache_manager.set(cache_key, result, ttl=3600)
                
                logger.info(f"Viator search returned {len(result.get('products', []))} products")
                return result
            else:
                logger.error(f"Viator search failed: {response.status_code}")
                return {"products": [], "error": "Search failed"}
                
        except Exception as e:
            logger.error(f"Viator search error: {str(e)}")
            return {"products": [], "error": str(e)}
    
    async def get_product_details(
        self,
        product_code: str,
        currency: str = "USD"
    ) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific product."""
        cache_key = f"viator:product:{product_code}:{currency}"
        
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached
            
        try:
            response = await self.circuit_breaker.call(
                self._make_request,
                "GET",
                f"/products/{product_code}",
                params={"currency": currency}
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Cache for 2 hours
                await cache_manager.set(cache_key, result, ttl=7200)
                
                return result
            else:
                logger.error(f"Failed to get product details: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting product details: {str(e)}")
            return None
    
    async def check_availability(
        self,
        product_code: str,
        travel_date: date,
        currency: str = "USD"
    ) -> Dict[str, Any]:
        """Check availability for a specific product and date."""
        try:
            request_data = {
                "productCode": product_code,
                "travelDate": travel_date.isoformat(),
                "currency": currency
            }
            
            response = await self.circuit_breaker.call(
                self._make_request,
                "POST",
                "/availability/check",
                json=request_data
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Availability check failed: {response.status_code}")
                return {"available": False, "error": "Availability check failed"}
                
        except Exception as e:
            logger.error(f"Error checking availability: {str(e)}")
            return {"available": False, "error": str(e)}
    
    async def create_booking(
        self,
        product_code: str,
        travel_date: date,
        product_option_code: str,
        travelers: List[Dict[str, Any]],
        booking_reference: str,
        language: str = "en",
        currency: str = "USD"
    ) -> Dict[str, Any]:
        """
        Create a booking for an activity.
        
        Args:
            product_code: Viator product code
            travel_date: Date of activity
            product_option_code: Selected option code
            travelers: List of traveler information
            booking_reference: Your reference ID
            language: Language code
            currency: Currency code
            
        Returns:
            Booking confirmation or error
        """
        try:
            # Build booking request
            booking_request = {
                "productCode": product_code,
                "travelDate": travel_date.isoformat(),
                "productOptionCode": product_option_code,
                "currency": currency,
                "language": language,
                "partnerReference": booking_reference,
                "travelers": travelers,
                "communication": {
                    "email": travelers[0].get("email", ""),
                    "phone": travelers[0].get("phone", "")
                }
            }
            
            response = await self.circuit_breaker.call(
                self._make_request,
                "POST",
                "/bookings/create",
                json=booking_request
            )
            
            if response.status_code in (200, 201):
                result = response.json()
                
                logger.info(f"Viator booking created: {result.get('bookingId')}")
                
                # Calculate commission (Viator typically offers 8-20%)
                total_price = float(result.get("totalPrice", {}).get("amount", 0))
                commission_rate = 0.12  # 12% average commission
                commission = total_price * commission_rate
                
                result["commission"] = {
                    "amount": commission,
                    "rate": commission_rate,
                    "currency": currency
                }
                
                return result
            else:
                logger.error(f"Booking creation failed: {response.status_code}")
                return {
                    "success": False,
                    "error": f"Booking failed: {response.status_code}",
                    "details": response.text
                }
                
        except Exception as e:
            logger.error(f"Error creating booking: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_booking_status(
        self,
        booking_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get the status of a booking."""
        try:
            response = await self.circuit_breaker.call(
                self._make_request,
                "GET",
                f"/bookings/{booking_id}"
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get booking status: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting booking status: {str(e)}")
            return None
    
    async def cancel_booking(
        self,
        booking_id: str,
        reason: str = "Customer requested cancellation"
    ) -> Dict[str, Any]:
        """Cancel a booking."""
        try:
            request_data = {
                "reasonCode": "CUSTOMER_REQUEST",
                "reason": reason
            }
            
            response = await self.circuit_breaker.call(
                self._make_request,
                "POST",
                f"/bookings/{booking_id}/cancel",
                json=request_data
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Viator booking cancelled: {booking_id}")
                return result
            else:
                logger.error(f"Cancellation failed: {response.status_code}")
                return {
                    "success": False,
                    "error": f"Cancellation failed: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Error cancelling booking: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_destinations(
        self,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get list of destinations for search."""
        cache_key = f"viator:destinations:{query or 'all'}"
        
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached
            
        try:
            params = {}
            if query:
                params["query"] = query
            
            response = await self.circuit_breaker.call(
                self._make_request,
                "GET",
                "/destinations",
                params=params
            )
            
            if response.status_code == 200:
                result = response.json()
                destinations = result.get("destinations", [])
                
                # Cache for 24 hours
                await cache_manager.set(cache_key, destinations, ttl=86400)
                
                return destinations
            else:
                logger.error(f"Failed to get destinations: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting destinations: {str(e)}")
            return []
    
    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get list of activity categories."""
        cache_key = "viator:categories"
        
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached
            
        try:
            response = await self.circuit_breaker.call(
                self._make_request,
                "GET",
                "/categories"
            )
            
            if response.status_code == 200:
                result = response.json()
                categories = result.get("categories", [])
                
                # Cache for 24 hours
                await cache_manager.set(cache_key, categories, ttl=86400)
                
                return categories
            else:
                logger.error(f"Failed to get categories: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting categories: {str(e)}")
            return []
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request to Viator API."""
        url = f"{self.base_url}{endpoint}"
        
        response = await self.client.request(
            method,
            url,
            **kwargs
        )
        
        return response
    
    def __del__(self):
        """Cleanup when client is destroyed."""
        if hasattr(self, 'client'):
            asyncio.create_task(self.client.aclose())


# Singleton instance
viator_client = ViatorClient()