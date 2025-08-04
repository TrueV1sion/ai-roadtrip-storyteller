"""
Flight tracking API client for real-time flight status.

Supports multiple providers with automatic fallback:
- FlightStats (enterprise-grade, requires paid subscription)
- FlightAware (comprehensive, requires paid API key)
- AviationStack (free tier available, limited requests)
- FlightLabs (affordable alternative)
"""

import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta, date
from enum import Enum
import httpx
from urllib.parse import quote

from app.core.logger import get_logger
from app.core.config import settings
from app.core.cache import cache_manager
from app.core.resilience import CircuitBreaker, with_circuit_breaker

logger = get_logger(__name__)


class FlightProvider(Enum):
    """Available flight tracking providers."""
    FLIGHTSTATS = "flightstats"
    FLIGHTAWARE = "flightaware"
    AVIATIONSTACK = "aviationstack"
    FLIGHTLABS = "flightlabs"


class FlightTrackerClient:
    """
    Multi-provider flight tracking client with automatic fallback.
    
    Providers are tried in order of preference based on availability and reliability.
    Caching is used to reduce API calls and improve performance.
    """
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.circuit_breakers = {
            provider: CircuitBreaker(
                failure_threshold=3,
                recovery_timeout=300,  # 5 minutes
                expected_exception=httpx.HTTPError
            )
            for provider in FlightProvider
        }
        
        # Determine available providers based on configured API keys
        self.available_providers = self._get_available_providers()
        
        if not self.available_providers:
            logger.warning("No flight tracking API keys configured. Will return mock data.")
    
    def _get_available_providers(self) -> List[FlightProvider]:
        """Get list of providers with configured API keys."""
        providers = []
        
        if settings.FLIGHTSTATS_API_KEY and settings.FLIGHTSTATS_APP_ID:
            providers.append(FlightProvider.FLIGHTSTATS)
        
        if settings.FLIGHTAWARE_API_KEY:
            providers.append(FlightProvider.FLIGHTAWARE)
        
        if settings.AVIATIONSTACK_API_KEY:
            providers.append(FlightProvider.AVIATIONSTACK)
        
        if settings.FLIGHTLABS_API_KEY:
            providers.append(FlightProvider.FLIGHTLABS)
        
        logger.info(f"Available flight tracking providers: {[p.value for p in providers]}")
        return providers
    
    async def track_flight(
        self,
        flight_number: str,
        departure_date: Union[datetime, date],
        airline_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Track a specific flight with automatic provider fallback.
        
        Args:
            flight_number: Flight number (e.g., "AA100" or just "100")
            departure_date: Scheduled departure date
            airline_code: Optional airline IATA code if not in flight number
            
        Returns:
            Flight status and details
        """
        # Normalize date to datetime if needed
        if isinstance(departure_date, date) and not isinstance(departure_date, datetime):
            departure_date = datetime.combine(departure_date, datetime.min.time())
        
        # Extract airline code if not provided
        if not airline_code and len(flight_number) >= 3:
            # Check if first 2-3 chars are letters (airline code)
            if flight_number[:2].isalpha():
                airline_code = flight_number[:2].upper()
                flight_num = flight_number[2:]
            elif flight_number[:3].isalpha():
                airline_code = flight_number[:3].upper()
                flight_num = flight_number[3:]
            else:
                flight_num = flight_number
        else:
            flight_num = flight_number.upper() if not airline_code else flight_number
            if airline_code:
                airline_code = airline_code.upper()
        
        # Check cache first
        cache_key = f"flight:{airline_code}:{flight_num}:{departure_date.date()}"
        cached = await cache_manager.get(cache_key)
        if cached:
            logger.info(f"Returning cached flight data for {airline_code}{flight_num}")
            return cached
        
        # Try each provider in order with circuit breaker protection
        errors = []
        for provider in self.available_providers:
            try:
                circuit_breaker = self.circuit_breakers[provider]
                
                with with_circuit_breaker(circuit_breaker):
                    logger.info(f"Trying {provider.value} for flight {airline_code}{flight_num}")
                    
                    if provider == FlightProvider.FLIGHTSTATS:
                        result = await self._track_flightstats(airline_code, flight_num, departure_date)
                    elif provider == FlightProvider.FLIGHTAWARE:
                        result = await self._track_flightaware(airline_code, flight_num, departure_date)
                    elif provider == FlightProvider.AVIATIONSTACK:
                        result = await self._track_aviationstack(airline_code, flight_num, departure_date)
                    elif provider == FlightProvider.FLIGHTLABS:
                        result = await self._track_flightlabs(airline_code, flight_num, departure_date)
                    else:
                        continue
                    
                    # Cache successful result for 5 minutes
                    await cache_manager.set(cache_key, result, ttl=300)
                    return result
                    
            except Exception as e:
                errors.append(f"{provider.value}: {str(e)}")
                logger.warning(f"Provider {provider.value} failed: {str(e)}")
                continue
        
        # All providers failed, return mock data
        logger.error(f"All providers failed for flight {airline_code}{flight_num}. Errors: {errors}")
        return self._get_mock_flight_data(f"{airline_code}{flight_num}", departure_date)
    
    async def search_flights_by_route(
        self,
        departure_airport: str,
        arrival_airport: str,
        departure_date: Union[datetime, date]
    ) -> List[Dict[str, Any]]:
        """
        Search for flights between airports on a specific date.
        
        Args:
            departure_airport: IATA code of departure airport
            arrival_airport: IATA code of arrival airport
            departure_date: Date of travel
            
        Returns:
            List of available flights
        """
        # Normalize date
        if isinstance(departure_date, date) and not isinstance(departure_date, datetime):
            departure_date = datetime.combine(departure_date, datetime.min.time())
        
        cache_key = f"routes:{departure_airport.upper()}:{arrival_airport.upper()}:{departure_date.date()}"
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached
        
        # Try each provider
        for provider in self.available_providers:
            try:
                circuit_breaker = self.circuit_breakers[provider]
                
                with with_circuit_breaker(circuit_breaker):
                    logger.info(f"Searching flights with {provider.value}")
                    
                    if provider == FlightProvider.FLIGHTSTATS:
                        flights = await self._search_flightstats(
                            departure_airport, arrival_airport, departure_date
                        )
                    elif provider == FlightProvider.FLIGHTAWARE:
                        flights = await self._search_flightaware(
                            departure_airport, arrival_airport, departure_date
                        )
                    elif provider == FlightProvider.AVIATIONSTACK:
                        flights = await self._search_aviationstack(
                            departure_airport, arrival_airport, departure_date
                        )
                    elif provider == FlightProvider.FLIGHTLABS:
                        flights = await self._search_flightlabs(
                            departure_airport, arrival_airport, departure_date
                        )
                    else:
                        continue
                    
                    # Cache for 1 hour
                    await cache_manager.set(cache_key, flights, ttl=3600)
                    return flights
                    
            except Exception as e:
                logger.warning(f"Provider {provider.value} failed for route search: {str(e)}")
                continue
        
        logger.error("All providers failed for route search")
        return []
    
    async def get_flight_delays(
        self,
        airport_code: str,
        departure: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get current delays at an airport.
        
        Args:
            airport_code: IATA airport code
            departure: True for departures, False for arrivals
            
        Returns:
            List of delayed flights
        """
        cache_key = f"delays:{airport_code}:{'dep' if departure else 'arr'}"
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached
        
        # This would be implemented per provider
        # For now, return empty list
        return []
    
    # FlightStats Implementation
    async def _track_flightstats(
        self,
        airline_code: str,
        flight_number: str,
        departure_date: datetime
    ) -> Dict[str, Any]:
        """Track flight using FlightStats API v2."""
        base_url = "https://api.flightstats.com/flex/flightstatus/rest/v2/json"
        
        # FlightStats uses year/month/day in URL path
        year = departure_date.year
        month = departure_date.month
        day = departure_date.day
        
        url = f"{base_url}/flight/status/{airline_code}/{flight_number}/dep/{year}/{month}/{day}"
        
        params = {
            "appId": settings.FLIGHTSTATS_APP_ID,
            "appKey": settings.FLIGHTSTATS_API_KEY,
            "utc": "false",
            "airport": "true",
            "weather": "true"
        }
        
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get("flightStatuses"):
            raise ValueError("Flight not found")
        
        # Get first flight status (usually only one for specific flight/date)
        flight = data["flightStatuses"][0]
        
        # Get additional data from appendix
        airlines = {a["iata"]: a for a in data.get("appendix", {}).get("airlines", [])}
        airports = {a["iata"]: a for a in data.get("appendix", {}).get("airports", [])}
        
        return self._normalize_flightstats_response(flight, airlines, airports)
    
    async def _search_flightstats(
        self,
        departure_airport: str,
        arrival_airport: str,
        departure_date: datetime
    ) -> List[Dict[str, Any]]:
        """Search flights using FlightStats API."""
        base_url = "https://api.flightstats.com/flex/schedules/rest/v1/json"
        
        year = departure_date.year
        month = departure_date.month
        day = departure_date.day
        
        url = f"{base_url}/from/{departure_airport}/to/{arrival_airport}/departing/{year}/{month}/{day}"
        
        params = {
            "appId": settings.FLIGHTSTATS_APP_ID,
            "appKey": settings.FLIGHTSTATS_API_KEY
        }
        
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        flights = []
        
        airlines = {a["iata"]: a for a in data.get("appendix", {}).get("airlines", [])}
        airports = {a["iata"]: a for a in data.get("appendix", {}).get("airports", [])}
        
        for flight in data.get("scheduledFlights", []):
            normalized = self._normalize_flightstats_response(flight, airlines, airports)
            flights.append(normalized)
        
        return flights
    
    def _normalize_flightstats_response(
        self,
        flight_data: Dict[str, Any],
        airlines: Dict[str, Any],
        airports: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Normalize FlightStats response to standard format."""
        airline_code = flight_data.get("carrierFsCode", "")
        airline_info = airlines.get(airline_code, {})
        
        departure_airport = flight_data.get("departureAirportFsCode", "")
        arrival_airport = flight_data.get("arrivalAirportFsCode", "")
        
        # Parse times
        dep_times = flight_data.get("departureDate", {})
        arr_times = flight_data.get("arrivalDate", {})
        
        return {
            "flight_number": f"{airline_code}{flight_data.get('flightNumber', '')}",
            "airline": {
                "code": airline_code,
                "name": airline_info.get("name", "Unknown Airline")
            },
            "status": self._map_flightstats_status(flight_data.get("status", "")),
            "departure": {
                "airport": departure_airport,
                "airport_name": airports.get(departure_airport, {}).get("name", ""),
                "terminal": flight_data.get("departureTerminal"),
                "gate": flight_data.get("departureGate"),
                "scheduled": dep_times.get("dateLocal"),
                "estimated": flight_data.get("operationalTimes", {}).get("estimatedGateDeparture", {}).get("dateLocal"),
                "actual": flight_data.get("operationalTimes", {}).get("actualGateDeparture", {}).get("dateLocal"),
                "delay_minutes": flight_data.get("delays", {}).get("departureGateDelayMinutes", 0)
            },
            "arrival": {
                "airport": arrival_airport,
                "airport_name": airports.get(arrival_airport, {}).get("name", ""),
                "terminal": flight_data.get("arrivalTerminal"),
                "gate": flight_data.get("arrivalGate"),
                "scheduled": arr_times.get("dateLocal"),
                "estimated": flight_data.get("operationalTimes", {}).get("estimatedGateArrival", {}).get("dateLocal"),
                "actual": flight_data.get("operationalTimes", {}).get("actualGateArrival", {}).get("dateLocal"),
                "delay_minutes": flight_data.get("delays", {}).get("arrivalGateDelayMinutes", 0)
            },
            "aircraft": {
                "type": flight_data.get("flightEquipment", {}).get("scheduledEquipmentIataCode"),
                "tail_number": flight_data.get("flightEquipment", {}).get("tailNumber")
            },
            "duration_minutes": flight_data.get("flightDurations", {}).get("scheduledBlockMinutes"),
            "distance_miles": flight_data.get("distances", {}).get("miles")
        }
    
    def _map_flightstats_status(self, status: str) -> str:
        """Map FlightStats status codes to standard status."""
        status_map = {
            "A": "active",
            "C": "cancelled",
            "D": "diverted",
            "DN": "data_not_available",
            "L": "landed",
            "NO": "not_operational",
            "R": "redirected",
            "S": "scheduled",
            "U": "unknown"
        }
        return status_map.get(status, "unknown")
    
    # FlightAware Implementation
    async def _track_flightaware(
        self,
        airline_code: str,
        flight_number: str,
        departure_date: datetime
    ) -> Dict[str, Any]:
        """Track flight using FlightAware AeroAPI v4."""
        base_url = "https://aeroapi.flightaware.com/aeroapi"
        
        # FlightAware uses ident format: AAL100 (airline code + flight number)
        ident = f"{airline_code}{flight_number}"
        
        # Format date for API
        start_date = departure_date.replace(hour=0, minute=0, second=0)
        end_date = start_date + timedelta(days=1)
        
        url = f"{base_url}/flights/{ident}"
        
        params = {
            "start": start_date.isoformat() + "Z",
            "end": end_date.isoformat() + "Z",
            "max_pages": 1
        }
        
        headers = {
            "x-apikey": settings.FLIGHTAWARE_API_KEY
        }
        
        response = await self.client.get(url, params=params, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get("flights"):
            raise ValueError("Flight not found")
        
        # Find the best matching flight for the date
        flights = data["flights"]
        best_match = flights[0]  # Usually sorted by relevance
        
        return self._normalize_flightaware_response(best_match)
    
    async def _search_flightaware(
        self,
        departure_airport: str,
        arrival_airport: str,
        departure_date: datetime
    ) -> List[Dict[str, Any]]:
        """Search flights using FlightAware API."""
        base_url = "https://aeroapi.flightaware.com/aeroapi"
        
        url = f"{base_url}/flights/search"
        
        # FlightAware search query format
        query = f'-origin {departure_airport} -destination {arrival_airport}'
        
        params = {
            "query": query,
            "start": departure_date.isoformat() + "Z",
            "end": (departure_date + timedelta(days=1)).isoformat() + "Z",
            "max_pages": 1
        }
        
        headers = {
            "x-apikey": settings.FLIGHTAWARE_API_KEY
        }
        
        response = await self.client.get(url, params=params, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        flights = []
        
        for flight in data.get("flights", []):
            normalized = self._normalize_flightaware_response(flight)
            flights.append(normalized)
        
        return flights
    
    def _normalize_flightaware_response(self, flight_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize FlightAware response to standard format."""
        return {
            "flight_number": flight_data.get("ident", ""),
            "airline": {
                "code": flight_data.get("operator_iata", ""),
                "name": flight_data.get("operator", "")
            },
            "status": self._map_flightaware_status(flight_data.get("status", "")),
            "departure": {
                "airport": flight_data.get("origin", {}).get("code_iata", ""),
                "airport_name": flight_data.get("origin", {}).get("name", ""),
                "terminal": flight_data.get("terminal_origin"),
                "gate": flight_data.get("gate_origin"),
                "scheduled": flight_data.get("scheduled_out"),
                "estimated": flight_data.get("estimated_out"),
                "actual": flight_data.get("actual_out"),
                "delay_minutes": self._calculate_delay(
                    flight_data.get("scheduled_out"),
                    flight_data.get("estimated_out") or flight_data.get("actual_out")
                )
            },
            "arrival": {
                "airport": flight_data.get("destination", {}).get("code_iata", ""),
                "airport_name": flight_data.get("destination", {}).get("name", ""),
                "terminal": flight_data.get("terminal_destination"),
                "gate": flight_data.get("gate_destination"),
                "scheduled": flight_data.get("scheduled_in"),
                "estimated": flight_data.get("estimated_in"),
                "actual": flight_data.get("actual_in"),
                "delay_minutes": self._calculate_delay(
                    flight_data.get("scheduled_in"),
                    flight_data.get("estimated_in") or flight_data.get("actual_in")
                )
            },
            "aircraft": {
                "type": flight_data.get("aircraft_type", ""),
                "tail_number": flight_data.get("registration")
            },
            "progress_percent": flight_data.get("progress_percent", 0),
            "route": flight_data.get("route", ""),
            "baggage_claim": flight_data.get("baggage_claim")
        }
    
    def _map_flightaware_status(self, status: str) -> str:
        """Map FlightAware status to standard status."""
        status = status.lower()
        if "cancelled" in status:
            return "cancelled"
        elif "landed" in status:
            return "landed"
        elif "airborne" in status or "enroute" in status:
            return "in_air"
        elif "scheduled" in status:
            return "scheduled"
        elif "delayed" in status:
            return "delayed"
        else:
            return "unknown"
    
    # AviationStack Implementation (already exists, just updating)
    async def _track_aviationstack(
        self,
        airline_code: str,
        flight_number: str,
        departure_date: datetime
    ) -> Dict[str, Any]:
        """Track flight using AviationStack API (free tier)."""
        url = "http://api.aviationstack.com/v1/flights"
        
        params = {
            "access_key": settings.AVIATIONSTACK_API_KEY,
            "airline_iata": airline_code,
            "flight_number": flight_number,
            "dep_date": departure_date.date().isoformat(),
            "limit": 1
        }
        
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get("data"):
            raise ValueError("Flight not found")
        
        flight = data["data"][0]
        return self._normalize_aviationstack_response(flight)
    
    async def _search_aviationstack(
        self,
        departure_airport: str,
        arrival_airport: str,
        departure_date: datetime
    ) -> List[Dict[str, Any]]:
        """Search flights using AviationStack API."""
        url = "http://api.aviationstack.com/v1/flights"
        
        params = {
            "access_key": settings.AVIATIONSTACK_API_KEY,
            "dep_iata": departure_airport,
            "arr_iata": arrival_airport,
            "dep_date": departure_date.date().isoformat(),
            "limit": 100
        }
        
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        flights = []
        
        for flight in data.get("data", []):
            flights.append(self._normalize_aviationstack_response(flight))
        
        return flights
    
    def _normalize_aviationstack_response(self, flight_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize AviationStack response to standard format."""
        departure = flight_data.get("departure", {})
        arrival = flight_data.get("arrival", {})
        
        return {
            "flight_number": flight_data.get("flight", {}).get("iata", ""),
            "airline": {
                "code": flight_data.get("airline", {}).get("iata", ""),
                "name": flight_data.get("airline", {}).get("name", "")
            },
            "status": self._map_aviationstack_status(flight_data.get("flight_status", "")),
            "departure": {
                "airport": departure.get("iata", ""),
                "airport_name": departure.get("airport", ""),
                "terminal": departure.get("terminal"),
                "gate": departure.get("gate"),
                "scheduled": departure.get("scheduled"),
                "estimated": departure.get("estimated"),
                "actual": departure.get("actual"),
                "delay_minutes": departure.get("delay", 0)
            },
            "arrival": {
                "airport": arrival.get("iata", ""),
                "airport_name": arrival.get("airport", ""),
                "terminal": arrival.get("terminal"),
                "gate": arrival.get("gate"),
                "scheduled": arrival.get("scheduled"),
                "estimated": arrival.get("estimated"),
                "actual": arrival.get("actual"),
                "delay_minutes": arrival.get("delay", 0)
            },
            "aircraft": {
                "type": flight_data.get("aircraft", {}).get("iata"),
                "registration": flight_data.get("aircraft", {}).get("registration")
            },
            "live": flight_data.get("live", {})
        }
    
    def _map_aviationstack_status(self, status: str) -> str:
        """Map AviationStack status to standard status."""
        status_map = {
            "scheduled": "scheduled",
            "active": "in_air",
            "landed": "landed",
            "cancelled": "cancelled",
            "incident": "delayed",
            "diverted": "diverted"
        }
        return status_map.get(status.lower(), "unknown")
    
    # FlightLabs Implementation
    async def _track_flightlabs(
        self,
        airline_code: str,
        flight_number: str,
        departure_date: datetime
    ) -> Dict[str, Any]:
        """Track flight using FlightLabs API."""
        url = "https://app.goflightlabs.com/flights"
        
        params = {
            "access_key": settings.FLIGHTLABS_API_KEY,
            "airline_iata": airline_code,
            "flight_number": flight_number,
            "dep_date": departure_date.date().isoformat()
        }
        
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get("data"):
            raise ValueError("Flight not found")
        
        flight = data["data"][0]
        return self._normalize_flightlabs_response(flight)
    
    async def _search_flightlabs(
        self,
        departure_airport: str,
        arrival_airport: str,
        departure_date: datetime
    ) -> List[Dict[str, Any]]:
        """Search flights using FlightLabs API."""
        url = "https://app.goflightlabs.com/flights"
        
        params = {
            "access_key": settings.FLIGHTLABS_API_KEY,
            "dep_iata": departure_airport,
            "arr_iata": arrival_airport,
            "dep_date": departure_date.date().isoformat()
        }
        
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        flights = []
        
        for flight in data.get("data", []):
            flights.append(self._normalize_flightlabs_response(flight))
        
        return flights
    
    def _normalize_flightlabs_response(self, flight_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize FlightLabs response to standard format."""
        # FlightLabs has similar structure to AviationStack
        return self._normalize_aviationstack_response(flight_data)
    
    def _calculate_delay(self, scheduled: Optional[str], actual: Optional[str]) -> int:
        """Calculate delay in minutes between scheduled and actual times."""
        if not scheduled or not actual:
            return 0
        
        try:
            scheduled_dt = datetime.fromisoformat(scheduled.replace('Z', '+00:00'))
            actual_dt = datetime.fromisoformat(actual.replace('Z', '+00:00'))
            delay = (actual_dt - scheduled_dt).total_seconds() / 60
            return max(0, int(delay))  # Only positive delays
        except Exception:
            return 0
    
    def _get_mock_flight_data(self, flight_number: str, departure_date: datetime) -> Dict[str, Any]:
        """Return mock flight data for development."""
        return {
            "flight_number": flight_number,
            "airline": {
                "code": flight_number[:2] if len(flight_number) >= 2 else "AA",
                "name": "Mock Airlines"
            },
            "status": "scheduled",
            "departure": {
                "airport": "LAX",
                "airport_name": "Los Angeles International Airport",
                "terminal": "4",
                "gate": "42B",
                "scheduled": departure_date.isoformat(),
                "estimated": departure_date.isoformat(),
                "actual": None,
                "delay_minutes": 0
            },
            "arrival": {
                "airport": "JFK",
                "airport_name": "John F. Kennedy International Airport",
                "terminal": "4",
                "gate": "B22",
                "scheduled": (departure_date + timedelta(hours=5)).isoformat(),
                "estimated": (departure_date + timedelta(hours=5)).isoformat(),
                "actual": None,
                "delay_minutes": 0
            },
            "aircraft": {
                "type": "B738",
                "tail_number": "N12345"
            },
            "duration_minutes": 300,
            "distance_miles": 2475
        }
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Singleton instance
flight_tracker = FlightTrackerClient()