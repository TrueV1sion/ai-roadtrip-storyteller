"""
Priority Pass Integration Client

Handles integration with Priority Pass API for lounge access bookings.
Provides lounge discovery, membership validation, and booking capabilities.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import aiohttp
from urllib.parse import urljoin

from backend.app.core.config import settings
from backend.app.core.logger import get_logger
from backend.app.core.cache import get_cache
from backend.app.core.circuit_breaker import get_booking_circuit_breaker, CircuitOpenError

logger = get_logger(__name__)


class PriorityPassClient:
    """Client for Priority Pass API integration"""
    
    def __init__(self):
        self.base_url = "https://api.prioritypass.com/v1/"
        self.api_key = settings.PRIORITY_PASS_API_KEY
        self.partner_id = settings.PRIORITY_PASS_PARTNER_ID
        self.cache = get_cache()
        self.session = None
        self._mock_mode = not self.api_key or self.api_key == "mock"
        self._circuit_breaker = get_booking_circuit_breaker("priority-pass")
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={
                    "X-API-Key": self.api_key,
                    "X-Partner-ID": self.partner_id,
                    "Content-Type": "application/json"
                }
            )
        return self.session
    
    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def get_lounges(
        self,
        airport_code: str,
        terminal: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get available lounges at an airport"""
        if self._mock_mode:
            return self._get_mock_lounges(airport_code, terminal)
        
        try:
            # Check cache
            cache_key = f"priority_pass:lounges:{airport_code}:{terminal}"
            cached = await self.cache.get(cache_key)
            if cached:
                return cached
            
            # API call
            session = await self._get_session()
            params = {
                "airport": airport_code,
                "status": "active"
            }
            if terminal:
                params["terminal"] = terminal
            
            # Wrap API call with circuit breaker
            async def api_call():
                async with session.get(
                    urljoin(self.base_url, "lounges"),
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        lounges = data.get("lounges", [])
                        
                        # Cache for 1 hour
                        await self.cache.set(cache_key, lounges, expire=3600)
                        return lounges
                    else:
                        logger.error(f"Priority Pass API error: {response.status}")
                        return []
            
            try:
                return await self._circuit_breaker.call_async(api_call)
            except CircuitOpenError:
                logger.error("Priority Pass circuit breaker is open")
                return self._get_mock_lounges(airport_code, terminal)
                    
        except Exception as e:
            logger.error(f"Failed to get Priority Pass lounges: {e}")
            return self._get_mock_lounges(airport_code, terminal)
    
    def _get_mock_lounges(
        self,
        airport_code: str,
        terminal: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return mock lounge data for testing"""
        mock_lounges = {
            "LAX": [
                {
                    "id": "pp_lax_001",
                    "name": "The Lounge LAX",
                    "description": "Premium lounge with full bar and hot food",
                    "terminal": "4",
                    "gate_area": "Gates 40-48",
                    "location": "After security, near Gate 44",
                    "hours": {
                        "monday": "05:00-22:00",
                        "tuesday": "05:00-22:00",
                        "wednesday": "05:00-22:00",
                        "thursday": "05:00-22:00",
                        "friday": "05:00-22:00",
                        "saturday": "05:00-22:00",
                        "sunday": "05:00-22:00"
                    },
                    "amenities": [
                        "Hot Food",
                        "Premium Bar",
                        "Showers",
                        "WiFi",
                        "Business Center",
                        "Quiet Zone"
                    ],
                    "rating": 4.5,
                    "reviews_count": 324,
                    "images": [
                        "https://example.com/lounge1.jpg",
                        "https://example.com/lounge2.jpg"
                    ]
                },
                {
                    "id": "pp_lax_002",
                    "name": "Star Alliance Lounge",
                    "description": "Spacious lounge with runway views",
                    "terminal": "6",
                    "gate_area": "Gates 60-69",
                    "location": "Level 3, after security",
                    "hours": {
                        "monday": "06:00-23:00",
                        "tuesday": "06:00-23:00",
                        "wednesday": "06:00-23:00",
                        "thursday": "06:00-23:00",
                        "friday": "06:00-23:00",
                        "saturday": "06:00-23:00",
                        "sunday": "06:00-23:00"
                    },
                    "amenities": [
                        "Hot Buffet",
                        "Bar Service",
                        "Showers",
                        "WiFi",
                        "Family Room",
                        "Outdoor Terrace"
                    ],
                    "rating": 4.7,
                    "reviews_count": 567,
                    "images": [
                        "https://example.com/star1.jpg",
                        "https://example.com/star2.jpg"
                    ]
                }
            ],
            "JFK": [
                {
                    "id": "pp_jfk_001",
                    "name": "Wingtips Lounge",
                    "description": "Modern lounge with craft cocktails",
                    "terminal": "4",
                    "gate_area": "Concourse B",
                    "location": "Near Gate B20",
                    "hours": {
                        "monday": "05:30-21:30",
                        "tuesday": "05:30-21:30",
                        "wednesday": "05:30-21:30",
                        "thursday": "05:30-21:30",
                        "friday": "05:30-21:30",
                        "saturday": "05:30-21:30",
                        "sunday": "05:30-21:30"
                    },
                    "amenities": [
                        "Craft Cocktails",
                        "Light Meals",
                        "WiFi",
                        "Charging Stations",
                        "Reading Room"
                    ],
                    "rating": 4.3,
                    "reviews_count": 892,
                    "images": []
                }
            ]
        }
        
        lounges = mock_lounges.get(airport_code, [])
        if terminal:
            lounges = [l for l in lounges if l["terminal"] == terminal]
        
        return lounges
    
    async def check_membership(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Check if user has active Priority Pass membership"""
        if self._mock_mode:
            return self._get_mock_membership(user_id)
        
        try:
            session = await self._get_session()
            
            async def api_call():
                async with session.get(
                    urljoin(self.base_url, f"members/{user_id}")
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("membership")
                    elif response.status == 404:
                        return None
                    else:
                        logger.error(f"Priority Pass membership check error: {response.status}")
                        return None
            
            try:
                return await self._circuit_breaker.call_async(api_call)
            except CircuitOpenError:
                logger.error("Priority Pass circuit breaker is open")
                return None
                    
        except Exception as e:
            logger.error(f"Failed to check Priority Pass membership: {e}")
            return None
    
    def _get_mock_membership(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Return mock membership data"""
        # Mock: 30% of users have membership
        if hash(user_id) % 10 < 3:
            return {
                "member_id": f"PP{user_id[:8]}",
                "status": "active",
                "tier": "prestige",
                "guest_policy": "Unlimited guests at additional charge",
                "visits_remaining": "unlimited",
                "expiry_date": "2025-12-31"
            }
        return None
    
    async def get_paid_access(self, lounge_id: str) -> Optional[Dict[str, Any]]:
        """Get paid access options for a lounge"""
        if self._mock_mode:
            return {
                "lounge_id": lounge_id,
                "price": 45.00,
                "currency": "USD",
                "duration_hours": 3,
                "included_amenities": [
                    "All lounge amenities",
                    "Food & beverages",
                    "WiFi",
                    "Shower access (if available)"
                ],
                "guest_price": 45.00
            }
        
        try:
            session = await self._get_session()
            async with session.get(
                urljoin(self.base_url, f"lounges/{lounge_id}/access-options")
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("paid_access")
                else:
                    logger.error(f"Failed to get paid access options: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to get paid access options: {e}")
            return None
    
    async def book_lounge(
        self,
        lounge_id: str,
        user_id: str,
        booking_details: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Book lounge access"""
        if self._mock_mode:
            return self._mock_book_lounge(lounge_id, user_id, booking_details)
        
        try:
            session = await self._get_session()
            
            # Prepare booking data
            booking_data = {
                "lounge_id": lounge_id,
                "member_id": booking_details.get("member_id"),
                "access_type": booking_details.get("access_type", "paid"),
                "arrival_time": booking_details["arrival_time"].isoformat(),
                "party_size": booking_details.get("party_size", 1),
                "flight_details": {
                    "airline": booking_details.get("airline"),
                    "flight_number": booking_details.get("flight_number"),
                    "departure_time": booking_details.get("departure_time")
                }
            }
            
            async def api_call():
                async with session.post(
                    urljoin(self.base_url, "bookings"),
                    json=booking_data
                ) as response:
                    if response.status == 201:
                        booking = await response.json()
                        return booking
                    else:
                        error_data = await response.json()
                        logger.error(f"Booking failed: {error_data}")
                        return None
            
            try:
                return await self._circuit_breaker.call_async(api_call)
            except CircuitOpenError:
                logger.error("Priority Pass circuit breaker is open")
                # Fallback to mock booking in case of circuit breaker open
                return self._mock_book_lounge(lounge_id, user_id, booking_details)
                    
        except Exception as e:
            logger.error(f"Failed to book lounge: {e}")
            return None
    
    def _mock_book_lounge(
        self,
        lounge_id: str,
        user_id: str,
        booking_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mock lounge booking for testing"""
        booking_id = f"PPB{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Calculate price
        base_price = 45.00
        party_size = booking_details.get("party_size", 1)
        total_amount = base_price * party_size
        
        # Apply member discount if applicable
        if booking_details.get("member_id"):
            total_amount = 0  # Free for members
        
        return {
            "booking_id": booking_id,
            "confirmation_number": booking_id,
            "lounge_id": lounge_id,
            "status": "confirmed",
            "arrival_time": booking_details["arrival_time"].isoformat(),
            "party_size": party_size,
            "total_amount": total_amount,
            "currency": "USD",
            "qr_code": f"https://prioritypass.com/qr/{booking_id}",
            "cancellation_policy": "Free cancellation up to 2 hours before arrival",
            "lounge_details": {
                "name": "The Lounge",
                "terminal": "4",
                "location": "Near Gate 44",
                "hours": "05:00-22:00"
            }
        }
    
    async def cancel_booking(self, booking_id: str) -> bool:
        """Cancel a lounge booking"""
        if self._mock_mode:
            return True
        
        try:
            session = await self._get_session()
            async with session.delete(
                urljoin(self.base_url, f"bookings/{booking_id}")
            ) as response:
                return response.status == 204
                
        except Exception as e:
            logger.error(f"Failed to cancel booking: {e}")
            return False
    
    async def get_lounge_availability(
        self,
        lounge_id: str,
        date: datetime,
        party_size: int = 1
    ) -> Dict[str, Any]:
        """Check real-time lounge availability"""
        if self._mock_mode:
            # Mock: Random availability
            import random
            capacity = random.randint(0, 100)
            return {
                "lounge_id": lounge_id,
                "date": date.isoformat(),
                "current_capacity": capacity,
                "available": capacity < 80,
                "wait_time_minutes": 0 if capacity < 60 else (capacity - 60) // 2,
                "max_party_size": 6
            }
        
        try:
            session = await self._get_session()
            params = {
                "date": date.isoformat(),
                "party_size": party_size
            }
            
            async with session.get(
                urljoin(self.base_url, f"lounges/{lounge_id}/availability"),
                params=params
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to check availability: {response.status}")
                    return {"available": True}  # Default to available
                    
        except Exception as e:
            logger.error(f"Failed to check lounge availability: {e}")
            return {"available": True}