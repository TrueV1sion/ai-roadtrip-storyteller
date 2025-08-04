"""
Airline Lounge Integration Client

Handles integration with various airline lounge APIs for access validation
and day pass purchases. Supports multiple airline partners.
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


class AirlineLoungeClient:
    """Client for airline lounge integrations"""
    
    # Airline API endpoints mapping
    AIRLINE_APIS = {
        "united": {
            "base_url": "https://api.united.com/lounges/v1/",
            "api_key_setting": "UNITED_API_KEY"
        },
        "delta": {
            "base_url": "https://api.delta.com/lounges/v1/",
            "api_key_setting": "DELTA_API_KEY"
        },
        "american": {
            "base_url": "https://api.aa.com/lounges/v1/",
            "api_key_setting": "AA_API_KEY"
        }
    }
    
    def __init__(self):
        self.cache = get_cache()
        self.sessions = {}
        self._mock_mode = True  # Default to mock until partnerships secured
        
    async def _get_session(self, airline: str) -> Optional[aiohttp.ClientSession]:
        """Get or create aiohttp session for specific airline"""
        if airline not in self.sessions:
            if airline in self.AIRLINE_APIS:
                api_config = self.AIRLINE_APIS[airline]
                api_key = getattr(settings, api_config["api_key_setting"], None)
                
                if api_key and api_key != "mock":
                    self.sessions[airline] = aiohttp.ClientSession(
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json"
                        }
                    )
                    self._mock_mode = False
        
        return self.sessions.get(airline)
    
    async def close(self):
        """Close all sessions"""
        for session in self.sessions.values():
            await session.close()
        self.sessions.clear()
    
    async def get_lounges(
        self,
        airport_code: str,
        terminal: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get airline lounges across all partners"""
        if self._mock_mode:
            return self._get_mock_lounges(airport_code, terminal)
        
        all_lounges = []
        
        # Query each airline partner
        tasks = []
        for airline in self.AIRLINE_APIS.keys():
            tasks.append(self._get_airline_lounges(airline, airport_code, terminal))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_lounges.extend(result)
            else:
                logger.error(f"Failed to get lounges: {result}")
        
        return all_lounges
    
    async def _get_airline_lounges(
        self,
        airline: str,
        airport_code: str,
        terminal: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Get lounges for specific airline"""
        try:
            # Check cache
            cache_key = f"airline_lounges:{airline}:{airport_code}:{terminal}"
            cached = await self.cache.get(cache_key)
            if cached:
                return cached
            
            session = await self._get_session(airline)
            if not session:
                return []
            
            api_config = self.AIRLINE_APIS[airline]
            params = {"airport": airport_code}
            if terminal:
                params["terminal"] = terminal
            
            async with session.get(
                urljoin(api_config["base_url"], "lounges"),
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    lounges = data.get("lounges", [])
                    
                    # Add airline tag
                    for lounge in lounges:
                        lounge["airline"] = airline
                    
                    # Cache for 1 hour
                    await self.cache.set(cache_key, lounges, expire=3600)
                    return lounges
                else:
                    logger.error(f"{airline} API error: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Failed to get {airline} lounges: {e}")
            return []
    
    def _get_mock_lounges(
        self,
        airport_code: str,
        terminal: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return mock airline lounge data"""
        mock_lounges = {
            "LAX": [
                {
                    "id": "ua_lax_001",
                    "airline": "united",
                    "name": "United Club",
                    "description": "United's premium lounge with full amenities",
                    "terminal": "7",
                    "gate_area": "Gates 70-77",
                    "location": "Near Gate 71B, Level 2",
                    "hours": {
                        "monday": "05:00-23:00",
                        "tuesday": "05:00-23:00",
                        "wednesday": "05:00-23:00",
                        "thursday": "05:00-23:00",
                        "friday": "05:00-23:00",
                        "saturday": "05:00-23:00",
                        "sunday": "05:00-23:00"
                    },
                    "amenities": [
                        "Hot Meals",
                        "Premium Bar",
                        "Showers",
                        "WiFi",
                        "Business Center",
                        "TV Lounges"
                    ],
                    "rating": 4.4,
                    "reviews_count": 1203,
                    "images": [],
                    "access_rules": {
                        "united_club_member": True,
                        "star_alliance_gold": True,
                        "business_class": True,
                        "day_pass": True
                    }
                },
                {
                    "id": "dl_lax_001",
                    "airline": "delta",
                    "name": "Delta Sky Club",
                    "description": "Delta's flagship lounge at LAX",
                    "terminal": "2",
                    "gate_area": "Gates 20-29",
                    "location": "Concourse Level, near Gate 24",
                    "hours": {
                        "monday": "05:30-22:30",
                        "tuesday": "05:30-22:30",
                        "wednesday": "05:30-22:30",
                        "thursday": "05:30-22:30",
                        "friday": "05:30-22:30",
                        "saturday": "05:30-22:30",
                        "sunday": "05:30-22:30"
                    },
                    "amenities": [
                        "Made-to-order meals",
                        "Full Bar",
                        "Spa Showers",
                        "WiFi",
                        "Outdoor Sky Deck",
                        "Quiet Rooms"
                    ],
                    "rating": 4.6,
                    "reviews_count": 2341,
                    "images": [],
                    "access_rules": {
                        "sky_club_member": True,
                        "delta_one": True,
                        "skyteam_elite_plus": True,
                        "day_pass": True
                    }
                }
            ],
            "JFK": [
                {
                    "id": "aa_jfk_001",
                    "airline": "american",
                    "name": "Admirals Club",
                    "description": "American Airlines premium lounge",
                    "terminal": "8",
                    "gate_area": "Concourse B",
                    "location": "Near Gate B31",
                    "hours": {
                        "monday": "04:30-23:00",
                        "tuesday": "04:30-23:00",
                        "wednesday": "04:30-23:00",
                        "thursday": "04:30-23:00",
                        "friday": "04:30-23:00",
                        "saturday": "04:30-23:00",
                        "sunday": "04:30-23:00"
                    },
                    "amenities": [
                        "Flagship Dining",
                        "Premium Wine Bar",
                        "Shower Suites",
                        "High-Speed WiFi",
                        "Conference Rooms",
                        "Kids Zone"
                    ],
                    "rating": 4.5,
                    "reviews_count": 1876,
                    "images": [],
                    "access_rules": {
                        "admirals_club_member": True,
                        "oneworld_emerald": True,
                        "flagship_first": True,
                        "day_pass": True
                    }
                }
            ]
        }
        
        lounges = mock_lounges.get(airport_code, [])
        if terminal:
            lounges = [l for l in lounges if l["terminal"] == terminal]
        
        return lounges
    
    async def check_status(
        self,
        user_id: str,
        airline: str
    ) -> Optional[Dict[str, Any]]:
        """Check user's airline status for lounge access"""
        if self._mock_mode:
            return self._get_mock_status(user_id, airline)
        
        try:
            session = await self._get_session(airline)
            if not session:
                return None
            
            api_config = self.AIRLINE_APIS[airline]
            async with session.get(
                urljoin(api_config["base_url"], f"members/{user_id}/status")
            ) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    return None
                else:
                    logger.error(f"Status check error: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to check {airline} status: {e}")
            return None
    
    def _get_mock_status(self, user_id: str, airline: str) -> Optional[Dict[str, Any]]:
        """Return mock airline status"""
        # Mock: 20% have elite status
        if hash(f"{user_id}{airline}") % 10 < 2:
            status_tiers = {
                "united": ["Premier Silver", "Premier Gold", "Premier Platinum", "Premier 1K"],
                "delta": ["Silver Medallion", "Gold Medallion", "Platinum Medallion", "Diamond Medallion"],
                "american": ["Gold", "Platinum", "Platinum Pro", "Executive Platinum"]
            }
            
            tier_index = hash(user_id) % 4
            return {
                "member_id": f"{airline.upper()}{user_id[:8]}",
                "airline": airline,
                "tier": status_tiers[airline][tier_index],
                "has_access": tier_index >= 1,  # Gold and above get access
                "guest_policy": "One guest" if tier_index >= 2 else "No guests",
                "expiry_date": "2025-12-31"
            }
        return None
    
    async def get_day_pass(self, lounge_id: str) -> Optional[Dict[str, Any]]:
        """Get day pass pricing for a lounge"""
        if self._mock_mode:
            return self._get_mock_day_pass(lounge_id)
        
        # Extract airline from lounge_id
        airline = lounge_id.split('_')[0]
        if airline not in self.AIRLINE_APIS:
            return None
        
        try:
            session = await self._get_session(airline)
            if not session:
                return None
            
            api_config = self.AIRLINE_APIS[airline]
            async with session.get(
                urljoin(api_config["base_url"], f"lounges/{lounge_id}/day-pass")
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Day pass query error: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to get day pass info: {e}")
            return None
    
    def _get_mock_day_pass(self, lounge_id: str) -> Dict[str, Any]:
        """Return mock day pass data"""
        airline = lounge_id.split('_')[0]
        
        prices = {
            "ua": 59.00,
            "dl": 59.00,
            "aa": 59.00
        }
        
        return {
            "lounge_id": lounge_id,
            "airline": airline,
            "price": prices.get(airline, 59.00),
            "currency": "USD",
            "duration_hours": None,  # Valid until departure
            "included_amenities": [
                "All lounge amenities",
                "Food & beverages",
                "WiFi & workspace",
                "Shower facilities (where available)"
            ],
            "guest_price": prices.get(airline, 59.00),
            "purchase_restrictions": [
                "Same-day ticketed passenger only",
                "Subject to capacity"
            ]
        }
    
    async def book_lounge(
        self,
        lounge_id: str,
        user_id: str,
        booking_details: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Book airline lounge access"""
        if self._mock_mode:
            return self._mock_book_lounge(lounge_id, user_id, booking_details)
        
        # Extract airline from lounge_id
        airline = lounge_id.split('_')[0]
        if airline not in self.AIRLINE_APIS:
            return None
        
        try:
            session = await self._get_session(airline)
            if not session:
                return None
            
            api_config = self.AIRLINE_APIS[airline]
            
            booking_data = {
                "lounge_id": lounge_id,
                "user_id": user_id,
                "access_type": booking_details.get("access_type", "day_pass"),
                "flight_details": {
                    "confirmation_number": booking_details.get("confirmation_number"),
                    "flight_number": booking_details.get("flight_number"),
                    "departure_time": booking_details.get("departure_time")
                },
                "party_size": booking_details.get("party_size", 1),
                "payment_method": booking_details.get("payment_method")
            }
            
            async with session.post(
                urljoin(api_config["base_url"], "bookings"),
                json=booking_data
            ) as response:
                if response.status == 201:
                    return await response.json()
                else:
                    error_data = await response.json()
                    logger.error(f"Lounge booking failed: {error_data}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to book airline lounge: {e}")
            return None
    
    def _mock_book_lounge(
        self,
        lounge_id: str,
        user_id: str,
        booking_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mock airline lounge booking"""
        airline = lounge_id.split('_')[0]
        booking_id = f"{airline.upper()}B{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Calculate price
        base_price = 59.00
        party_size = booking_details.get("party_size", 1)
        
        # Check if free with status
        total_amount = 0.0
        if booking_details.get("access_type") == "day_pass":
            total_amount = base_price * party_size
        
        return {
            "booking_id": booking_id,
            "confirmation_number": booking_id,
            "airline": airline,
            "lounge_id": lounge_id,
            "status": "confirmed",
            "access_type": booking_details.get("access_type", "day_pass"),
            "valid_from": datetime.utcnow().isoformat(),
            "valid_until": booking_details.get("departure_time", 
                (datetime.utcnow() + timedelta(hours=8)).isoformat()),
            "party_size": party_size,
            "total_amount": total_amount,
            "currency": "USD",
            "qr_code": f"https://{airline}.com/lounge-pass/{booking_id}",
            "lounge_details": {
                "name": f"{airline.title()} Lounge",
                "terminal": "2",
                "location": "After security, Concourse Level"
            }
        }
    
    async def check_capacity(
        self,
        lounge_id: str,
        datetime: datetime
    ) -> Dict[str, Any]:
        """Check real-time lounge capacity"""
        if self._mock_mode:
            import random
            occupancy = random.randint(40, 95)
            return {
                "lounge_id": lounge_id,
                "timestamp": datetime.isoformat(),
                "occupancy_percent": occupancy,
                "status": "available" if occupancy < 85 else "busy",
                "estimated_wait": 0 if occupancy < 85 else (occupancy - 85) * 2
            }
        
        # Real API implementation would go here
        return {"status": "available"}