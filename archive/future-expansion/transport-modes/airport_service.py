"""
Airport Services for comprehensive air travel support.

This module provides:
- Airport detection and information
- Parking reservation and management
- Flight tracking and status
- TSA wait time monitoring
- Terminal navigation assistance
- Return journey automation
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json
import math

from sqlalchemy.orm import Session
from backend.app.core.logger import get_logger
from backend.app.core.cache import cache_manager
from backend.app.core.config import settings
from backend.app.services.booking_service import BookingService
from app.core.enums import BookingType
from backend.app.core.tracing import trace_method
from backend.app.core.event_store import EventStore, EventType

logger = get_logger(__name__)


class ParkingType(str, Enum):
    """Types of airport parking."""
    ECONOMY = "economy"
    DAILY = "daily"
    GARAGE = "garage"
    PREMIUM = "premium"
    VALET = "valet"
    CELL_PHONE_LOT = "cell_phone"


class AirportCode(str, Enum):
    """Major US airports with their codes."""
    # California
    LAX = "LAX"  # Los Angeles International
    SFO = "SFO"  # San Francisco International
    SJC = "SJC"  # San Jose International
    OAK = "OAK"  # Oakland International
    SAN = "SAN"  # San Diego International
    
    # New York Area
    JFK = "JFK"  # John F. Kennedy International
    LGA = "LGA"  # LaGuardia
    EWR = "EWR"  # Newark Liberty International
    
    # Major Hubs
    ORD = "ORD"  # Chicago O'Hare
    ATL = "ATL"  # Atlanta Hartsfield-Jackson
    DFW = "DFW"  # Dallas/Fort Worth
    DEN = "DEN"  # Denver International
    LAS = "LAS"  # Las Vegas McCarran
    PHX = "PHX"  # Phoenix Sky Harbor
    SEA = "SEA"  # Seattle-Tacoma
    BOS = "BOS"  # Boston Logan
    MCO = "MCO"  # Orlando International
    MIA = "MIA"  # Miami International


class AirportInfo:
    """Airport information and configuration."""
    
    AIRPORTS = {
        "LAX": {
            "name": "Los Angeles International Airport",
            "terminals": ["1", "2", "3", "4", "5", "6", "7", "8", "TBIT"],
            "parking": {
                ParkingType.ECONOMY: {
                    "name": "Economy Parking",
                    "lots": ["C", "E"],
                    "price_per_day": 12.00,
                    "shuttle_frequency": 10,  # minutes
                    "walk_time": 15  # minutes to terminal
                },
                ParkingType.DAILY: {
                    "name": "Central Terminal Area",
                    "lots": ["P1", "P2", "P3", "P4", "P5", "P6", "P7"],
                    "price_per_day": 30.00,
                    "shuttle_frequency": 0,  # Direct walk
                    "walk_time": 5
                },
                ParkingType.VALET: {
                    "name": "Valet Parking",
                    "lots": ["Terminal Valet"],
                    "price_per_day": 50.00,
                    "shuttle_frequency": 0,
                    "walk_time": 0
                }
            },
            "coordinates": {"lat": 33.9425, "lng": -118.4081}
        },
        "SFO": {
            "name": "San Francisco International Airport",
            "terminals": ["1", "2", "3", "International"],
            "parking": {
                ParkingType.ECONOMY: {
                    "name": "Long Term Parking",
                    "lots": ["Long Term"],
                    "price_per_day": 18.00,
                    "shuttle_frequency": 8,
                    "walk_time": 20
                },
                ParkingType.DAILY: {
                    "name": "Daily Parking",
                    "lots": ["Domestic", "International"],
                    "price_per_day": 36.00,
                    "shuttle_frequency": 0,
                    "walk_time": 8
                },
                ParkingType.GARAGE: {
                    "name": "Garage Parking",
                    "lots": ["A", "B", "C", "D", "E", "F", "G"],
                    "price_per_day": 36.00,
                    "shuttle_frequency": 0,
                    "walk_time": 5
                }
            },
            "coordinates": {"lat": 37.6213, "lng": -122.3790}
        }
        # Add more airports as needed
    }


class AirportService:
    """
    Main service for airport-related functionality.
    
    This service handles:
    - Airport detection from destinations
    - Parking availability and reservations
    - Flight status tracking
    - TSA wait times
    - Optimal departure time calculation
    """
    
    def __init__(self, booking_service: BookingService, event_store: EventStore):
        self.booking_service = booking_service
        self.event_store = event_store
        self._airport_cache = {}
    
    @trace_method(name="airport.detect")
    async def detect_airport_trip(self, destination: str) -> Optional[Dict[str, Any]]:
        """
        Detect if a destination is an airport.
        
        Args:
            destination: Destination string from user
            
        Returns:
            Airport info if detected, None otherwise
        """
        # Check cache first
        cache_key = f"airport_detection:{destination.lower()}"
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached
        
        # Check for airport codes in destination
        destination_upper = destination.upper()
        for code in AirportCode:
            if code.value in destination_upper:
                airport_info = AirportInfo.AIRPORTS.get(code.value)
                if airport_info:
                    result = {
                        "code": code.value,
                        "detected": True,
                        **airport_info
                    }
                    await cache_manager.set(cache_key, result, ttl=3600)
                    return result
        
        # Check for airport names
        destination_lower = destination.lower()
        for code, info in AirportInfo.AIRPORTS.items():
            if "airport" in destination_lower and any(
                term in destination_lower 
                for term in [code.lower(), info["name"].lower().split()[0]]
            ):
                result = {
                    "code": code,
                    "detected": True,
                    **info
                }
                await cache_manager.set(cache_key, result, ttl=3600)
                return result
        
        return None
    
    @trace_method(name="airport.check_parking")
    async def check_parking_availability(
        self,
        airport_code: str,
        start_date: datetime,
        end_date: datetime,
        parking_type: Optional[ParkingType] = None
    ) -> Dict[str, Any]:
        """
        Check parking availability at an airport.
        
        Args:
            airport_code: IATA airport code
            start_date: Parking start date/time
            end_date: Parking end date/time
            parking_type: Specific type or None for all
            
        Returns:
            Parking options with availability and pricing
        """
        airport_info = AirportInfo.AIRPORTS.get(airport_code)
        if not airport_info:
            raise ValueError(f"Unknown airport code: {airport_code}")
        
        duration_days = (end_date - start_date).days or 1
        parking_options = []
        
        for p_type, p_info in airport_info["parking"].items():
            if parking_type and p_type != parking_type:
                continue
            
            # Simulate availability (in production, call real APIs)
            availability = await self._check_parking_api(
                airport_code, p_type, start_date, end_date
            )
            
            option = {
                "type": p_type.value,
                "name": p_info["name"],
                "lots": p_info["lots"],
                "available_spots": availability.get("spots", 100),
                "price_per_day": p_info["price_per_day"],
                "total_price": p_info["price_per_day"] * duration_days,
                "shuttle_frequency": p_info["shuttle_frequency"],
                "walk_time": p_info["walk_time"],
                "features": self._get_parking_features(p_type)
            }
            parking_options.append(option)
        
        # Sort by price
        parking_options.sort(key=lambda x: x["total_price"])
        
        return {
            "airport_code": airport_code,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "duration_days": duration_days,
            "options": parking_options,
            "recommendation": self._recommend_parking(parking_options, duration_days)
        }
    
    @trace_method(name="airport.book_parking")
    async def book_parking(
        self,
        user_id: str,
        airport_code: str,
        parking_type: ParkingType,
        start_date: datetime,
        end_date: datetime,
        flight_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Book airport parking.
        
        Args:
            user_id: User making the booking
            airport_code: IATA airport code
            parking_type: Type of parking
            start_date: Parking start
            end_date: Parking end
            flight_info: Optional flight details
            
        Returns:
            Booking confirmation
        """
        # Check availability first
        availability = await self.check_parking_availability(
            airport_code, start_date, end_date, parking_type
        )
        
        parking_option = next(
            (opt for opt in availability["options"] if opt["type"] == parking_type.value),
            None
        )
        
        if not parking_option or parking_option["available_spots"] == 0:
            raise ValueError("Parking type not available")
        
        # Create booking through booking service
        booking_result = await self.booking_service.create_booking(
            partner="airport_parking",
            venue_id=f"{airport_code}_{parking_type.value}",
            date=start_date,
            party_size=1,  # One vehicle
            user_data={
                "user_id": user_id,
                "end_date": end_date.isoformat(),
                "flight_info": flight_info,
                "parking_type": parking_type.value,
                "total_price": parking_option["total_price"]
            }
        )
        
        if booking_result["success"]:
            # Emit event
            self.event_store.append(
                event_type=EventType.BOOKING_CREATED,
                aggregate_id=booking_result["booking_id"],
                aggregate_type="AirportParking",
                event_data={
                    "airport_code": airport_code,
                    "parking_type": parking_type.value,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "total_price": parking_option["total_price"],
                    "lot_assigned": parking_option["lots"][0] if parking_option["lots"] else None
                },
                user_id=user_id
            )
            
            # Return enhanced confirmation
            return {
                **booking_result,
                "parking_details": {
                    "lot": parking_option["lots"][0] if parking_option["lots"] else "Any available",
                    "instructions": self._get_parking_instructions(airport_code, parking_type),
                    "shuttle_info": f"Shuttles every {parking_option['shuttle_frequency']} minutes" 
                                   if parking_option["shuttle_frequency"] > 0 else "Direct terminal access",
                    "total_price": parking_option["total_price"]
                }
            }
        
        return booking_result
    
    @trace_method(name="airport.get_tsa_wait")
    async def get_tsa_wait_times(self, airport_code: str, terminal: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current TSA wait times.
        
        Args:
            airport_code: IATA airport code
            terminal: Specific terminal or None for all
            
        Returns:
            Wait times by checkpoint
        """
        # In production, this would call TSA API or scrape data
        # For now, return realistic estimates based on time of day
        current_hour = datetime.now().hour
        day_of_week = datetime.now().weekday()
        
        # Peak hours: 5-9 AM, 3-7 PM on weekdays
        is_peak = (
            (5 <= current_hour <= 9 or 15 <= current_hour <= 19) and 
            day_of_week < 5
        )
        
        base_wait = 15 if not is_peak else 35
        
        # Add randomness
        import random
        wait_variance = random.randint(-5, 10)
        
        checkpoints = {
            "main": base_wait + wait_variance,
            "precheck": max(5, (base_wait + wait_variance) // 3),
            "clear": 5
        }
        
        if terminal:
            checkpoints[f"terminal_{terminal}"] = base_wait + random.randint(-3, 7)
        
        return {
            "airport_code": airport_code,
            "timestamp": datetime.now().isoformat(),
            "is_peak_time": is_peak,
            "checkpoints": checkpoints,
            "recommendation": "Use PreCheck line" if checkpoints["precheck"] < checkpoints["main"] - 10 else "Any checkpoint is fine"
        }
    
    @trace_method(name="airport.calculate_departure")
    async def calculate_optimal_departure_time(
        self,
        flight_time: datetime,
        origin: str,
        airport_code: str,
        has_bags_to_check: bool = True,
        has_precheck: bool = False,
        international: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate when to leave for the airport.
        
        Args:
            flight_time: Scheduled flight departure
            origin: Starting location
            airport_code: Destination airport
            has_bags_to_check: Whether checking bags
            has_precheck: TSA PreCheck status
            international: International flight
            
        Returns:
            Optimal departure time and breakdown
        """
        # Get drive time to airport
        from backend.app.services.directions_service import DirectionsService
        directions_service = DirectionsService()
        
        route = await directions_service.get_directions(
            origin=origin,
            destination=f"{airport_code} Airport",
            departure_time=flight_time - timedelta(hours=2)  # Aim to arrive 2 hours early
        )
        
        drive_time_minutes = route.get("duration", 1800) // 60  # Convert to minutes
        
        # Get TSA wait time
        tsa_wait = await self.get_tsa_wait_times(airport_code)
        security_time = tsa_wait["checkpoints"]["precheck" if has_precheck else "main"]
        
        # Calculate buffer times
        parking_time = 15  # Time to park and get to terminal
        check_in_time = 20 if has_bags_to_check else 5
        terminal_navigation = 10
        boarding_buffer = 30  # Airlines close doors 10-15 min early, add buffer
        
        # Additional time for international
        if international:
            check_in_time += 20
            boarding_buffer += 30
        
        # Total time needed at airport
        airport_time = (
            security_time +
            check_in_time +
            terminal_navigation +
            boarding_buffer
        )
        
        # Add traffic buffer (20% of drive time)
        traffic_buffer = int(drive_time_minutes * 0.2)
        
        # Calculate departure time
        total_time_needed = drive_time_minutes + parking_time + airport_time + traffic_buffer
        optimal_departure = flight_time - timedelta(minutes=total_time_needed)
        
        # Create timeline
        timeline = [
            {
                "time": optimal_departure,
                "action": "Leave for airport",
                "duration": drive_time_minutes
            },
            {
                "time": optimal_departure + timedelta(minutes=drive_time_minutes),
                "action": "Park and walk to terminal",
                "duration": parking_time
            },
            {
                "time": optimal_departure + timedelta(minutes=drive_time_minutes + parking_time),
                "action": "Check in" if has_bags_to_check else "Head to security",
                "duration": check_in_time
            },
            {
                "time": optimal_departure + timedelta(minutes=drive_time_minutes + parking_time + check_in_time),
                "action": "Security checkpoint",
                "duration": security_time
            },
            {
                "time": flight_time - timedelta(minutes=boarding_buffer),
                "action": "Arrive at gate",
                "duration": boarding_buffer
            }
        ]
        
        return {
            "flight_time": flight_time.isoformat(),
            "recommended_departure": optimal_departure.isoformat(),
            "arrival_at_airport": (optimal_departure + timedelta(minutes=drive_time_minutes + parking_time)).isoformat(),
            "breakdown": {
                "drive_time": drive_time_minutes,
                "parking_time": parking_time,
                "check_in_time": check_in_time,
                "security_time": security_time,
                "terminal_navigation": terminal_navigation,
                "boarding_buffer": boarding_buffer,
                "traffic_buffer": traffic_buffer
            },
            "total_journey_time": total_time_needed,
            "timeline": timeline,
            "alerts": [
                {
                    "time": optimal_departure - timedelta(hours=1),
                    "message": "Start getting ready for your flight"
                },
                {
                    "time": optimal_departure - timedelta(minutes=15),
                    "message": "Time to leave in 15 minutes"
                },
                {
                    "time": optimal_departure,
                    "message": "Time to leave for the airport!"
                }
            ]
        }
    
    async def _check_parking_api(
        self,
        airport_code: str,
        parking_type: ParkingType,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Check parking availability with external API.
        
        In production, this would call:
        - SpotHero API
        - ParkWhiz API
        - Airport's own system
        """
        # Mock implementation
        import random
        
        # Simulate realistic availability
        if parking_type == ParkingType.ECONOMY:
            spots = random.randint(50, 500)
        elif parking_type == ParkingType.VALET:
            spots = random.randint(0, 20)
        else:
            spots = random.randint(20, 200)
        
        return {
            "spots": spots,
            "last_updated": datetime.now().isoformat()
        }
    
    def _get_parking_features(self, parking_type: ParkingType) -> List[str]:
        """Get features for parking type."""
        features = {
            ParkingType.ECONOMY: ["Shuttle Service", "24/7 Security", "Covered Areas Available"],
            ParkingType.DAILY: ["Close to Terminal", "Covered Parking", "EV Charging"],
            ParkingType.GARAGE: ["Covered Parking", "Direct Terminal Access", "EV Charging"],
            ParkingType.PREMIUM: ["Covered Parking", "Reserved Spots", "Valet Available"],
            ParkingType.VALET: ["Door-to-Door Service", "Car Wash Available", "Priority Access"]
        }
        return features.get(parking_type, [])
    
    def _recommend_parking(self, options: List[Dict[str, Any]], duration_days: int) -> str:
        """Recommend best parking option based on duration and price."""
        if duration_days <= 1:
            # Short trip - prioritize convenience
            garage_options = [opt for opt in options if opt["walk_time"] <= 10]
            if garage_options:
                return f"For a short trip, we recommend {garage_options[0]['name']} for quick terminal access"
        elif duration_days >= 7:
            # Long trip - prioritize price
            economy_options = [opt for opt in options if "economy" in opt["type"]]
            if economy_options:
                savings = options[-1]["total_price"] - economy_options[0]["total_price"]
                return f"For {duration_days} days, {economy_options[0]['name']} saves you ${savings:.0f}"
        
        # Medium trip - balance
        mid_price_options = options[len(options)//2:len(options)//2+1]
        if mid_price_options:
            return f"{mid_price_options[0]['name']} offers the best balance of price and convenience"
        
        return f"{options[0]['name']} is most economical"
    
    def _get_parking_instructions(self, airport_code: str, parking_type: ParkingType) -> str:
        """Get specific parking instructions for airport and type."""
        instructions = {
            "LAX": {
                ParkingType.ECONOMY: "Follow signs to Economy Parking Lot C or E. Free shuttles run every 10 minutes.",
                ParkingType.DAILY: "Enter Central Terminal Area and follow signs to parking structures P1-P7.",
                ParkingType.VALET: "Follow signs to your terminal. Valet is available at departure level."
            },
            "SFO": {
                ParkingType.ECONOMY: "Take the Long Term Parking exit. Shuttles to terminals every 8 minutes.",
                ParkingType.GARAGE: "Follow signs to Domestic or International Garages based on your terminal.",
                ParkingType.DAILY: "Enter via the main terminal road to daily parking areas."
            }
        }
        
        airport_instructions = instructions.get(airport_code, {})
        return airport_instructions.get(
            parking_type,
            f"Follow airport signs to {parking_type.value} parking"
        )