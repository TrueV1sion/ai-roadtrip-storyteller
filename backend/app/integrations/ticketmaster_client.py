import httpx
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import hashlib
import hmac
from urllib.parse import urlencode, quote

from backend.app.core.config import settings
from backend.app.core.cache import cache_manager
from backend.app.core.logger import logger
from backend.app.core.circuit_breaker import with_circuit_breaker, CircuitOpenError


class TicketmasterClient:
    """Client for Ticketmaster Discovery API integration."""
    
    BASE_URL = "https://app.ticketmaster.com/discovery/v2"
    
    def __init__(self):
        self.api_key = settings.TICKETMASTER_API_KEY
        self.client = httpx.AsyncClient(timeout=30.0)
        
    @with_circuit_breaker("ticketmaster-api", failure_threshold=3, recovery_timeout=60, timeout=15.0)
    async def search_events(
        self,
        keyword: Optional[str] = None,
        venue_id: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radius: int = 50,
        start_datetime: Optional[datetime] = None,
        end_datetime: Optional[datetime] = None,
        size: int = 20
    ) -> Dict[str, Any]:
        """Search for events based on various criteria."""
        cache_key = f"ticketmaster:events:{keyword}:{venue_id}:{lat}:{lon}:{radius}"
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached
            
        params = {
            "apikey": self.api_key,
            "size": size,
            "radius": radius,
            "unit": "miles"
        }
        
        if keyword:
            params["keyword"] = keyword
        if venue_id:
            params["venueId"] = venue_id
        if lat and lon:
            params["latlong"] = f"{lat},{lon}"
        if start_datetime:
            params["startDateTime"] = start_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
        if end_datetime:
            params["endDateTime"] = end_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
            
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/events.json",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            # Cache for 1 hour
            await cache_manager.set(cache_key, data, ttl=3600)
            return data
            
        except Exception as e:
            logger.error(f"Error searching Ticketmaster events: {e}")
            return {"_embedded": {"events": []}}
    
    @with_circuit_breaker("ticketmaster-api", failure_threshold=3, recovery_timeout=60, timeout=15.0)
    async def get_event_details(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific event."""
        cache_key = f"ticketmaster:event:{event_id}"
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached
            
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/events/{event_id}.json",
                params={"apikey": self.api_key}
            )
            response.raise_for_status()
            data = response.json()
            
            # Cache for 2 hours
            await cache_manager.set(cache_key, data, ttl=7200)
            return data
            
        except Exception as e:
            logger.error(f"Error getting event details: {e}")
            return None
    
    @with_circuit_breaker("ticketmaster-api", failure_threshold=3, recovery_timeout=60, timeout=15.0)
    async def get_venue_details(self, venue_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific venue."""
        cache_key = f"ticketmaster:venue:{venue_id}"
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached
            
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/venues/{venue_id}.json",
                params={"apikey": self.api_key}
            )
            response.raise_for_status()
            data = response.json()
            
            # Cache for 24 hours (venues don't change often)
            await cache_manager.set(cache_key, data, ttl=86400)
            return data
            
        except Exception as e:
            logger.error(f"Error getting venue details: {e}")
            return None
    
    @with_circuit_breaker("ticketmaster-api", failure_threshold=3, recovery_timeout=60, timeout=15.0)
    async def get_attractions(self, attraction_id: str) -> Optional[Dict[str, Any]]:
        """Get information about an attraction (artist, team, etc)."""
        cache_key = f"ticketmaster:attraction:{attraction_id}"
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached
            
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/attractions/{attraction_id}.json",
                params={"apikey": self.api_key}
            )
            response.raise_for_status()
            data = response.json()
            
            # Cache for 12 hours
            await cache_manager.set(cache_key, data, ttl=43200)
            return data
            
        except Exception as e:
            logger.error(f"Error getting attraction details: {e}")
            return None
    
    @with_circuit_breaker("ticketmaster-api", failure_threshold=3, recovery_timeout=60, timeout=15.0)
    async def search_venues_near_location(
        self,
        lat: float,
        lon: float,
        radius: int = 25
    ) -> List[Dict[str, Any]]:
        """Find venues near a specific location."""
        cache_key = f"ticketmaster:venues:{lat}:{lon}:{radius}"
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached
            
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/venues.json",
                params={
                    "apikey": self.api_key,
                    "latlong": f"{lat},{lon}",
                    "radius": radius,
                    "unit": "miles",
                    "size": 50
                }
            )
            response.raise_for_status()
            data = response.json()
            
            venues = data.get("_embedded", {}).get("venues", [])
            
            # Cache for 6 hours
            await cache_manager.set(cache_key, venues, ttl=21600)
            return venues
            
        except Exception as e:
            logger.error(f"Error searching venues: {e}")
            return []
    
    async def get_event_images(self, event_id: str) -> List[Dict[str, Any]]:
        """Get images associated with an event."""
        event = await self.get_event_details(event_id)
        if not event:
            return []
            
        return event.get("images", [])
    
    async def extract_event_metadata(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant metadata from event data."""
        metadata = {
            "id": event.get("id"),
            "name": event.get("name"),
            "type": event.get("type"),
            "url": event.get("url"),
            "locale": event.get("locale"),
            "images": event.get("images", []),
            "dates": event.get("dates", {}),
            "classifications": [],
            "venue": None,
            "attractions": [],
            "price_ranges": event.get("priceRanges", []),
            "info": event.get("info"),
            "pleaseNote": event.get("pleaseNote")
        }
        
        # Extract classifications (genre, type, etc)
        for classification in event.get("classifications", []):
            metadata["classifications"].append({
                "primary": classification.get("primary", False),
                "segment": classification.get("segment", {}).get("name"),
                "genre": classification.get("genre", {}).get("name"),
                "subGenre": classification.get("subGenre", {}).get("name"),
                "type": classification.get("type", {}).get("name"),
                "subType": classification.get("subType", {}).get("name")
            })
        
        # Extract venue information
        embedded = event.get("_embedded", {})
        venues = embedded.get("venues", [])
        if venues:
            venue = venues[0]
            metadata["venue"] = {
                "id": venue.get("id"),
                "name": venue.get("name"),
                "location": venue.get("location"),
                "address": venue.get("address"),
                "city": venue.get("city"),
                "state": venue.get("state"),
                "postalCode": venue.get("postalCode"),
                "country": venue.get("country"),
                "timezone": venue.get("timezone")
            }
        
        # Extract attractions (performers)
        for attraction in embedded.get("attractions", []):
            metadata["attractions"].append({
                "id": attraction.get("id"),
                "name": attraction.get("name"),
                "type": attraction.get("type"),
                "url": attraction.get("url"),
                "images": attraction.get("images", [])
            })
        
        return metadata
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Singleton instance
ticketmaster_client = TicketmasterClient()