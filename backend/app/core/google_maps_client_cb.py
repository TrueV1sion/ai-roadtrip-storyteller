"""
Google Maps client wrapper with circuit breaker protection.
Wraps the googlemaps library to add resilience patterns.
"""
import googlemaps
from typing import Any, Dict, List, Optional
import asyncio
from functools import partial

from app.core.config import settings
from app.core.circuit_breaker import get_maps_circuit_breaker, CircuitOpenError
from app.core.logger import get_logger

logger = get_logger(__name__)


class GoogleMapsClientWithCB:
    """Google Maps client with circuit breaker protection."""
    
    def __init__(self, api_key: str):
        """Initialize the client with API key."""
        self._client = googlemaps.Client(key=api_key)
        self._circuit_breaker = get_maps_circuit_breaker()
    
    async def directions(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Get directions with circuit breaker protection.
        
        Args:
            **kwargs: Arguments for googlemaps.directions()
            
        Returns:
            Directions response from Google Maps API
            
        Raises:
            CircuitOpenError: If circuit breaker is open
        """
        try:
            # googlemaps library is synchronous, so we use run_in_executor
            loop = asyncio.get_event_loop()
            func = partial(self._client.directions, **kwargs)
            
            # Wrap the sync call in circuit breaker
            result = await self._circuit_breaker.call_async(
                loop.run_in_executor,
                None,
                func
            )
            return result
        except CircuitOpenError:
            logger.error(f"Google Maps circuit breaker is open for directions request")
            raise
        except Exception as e:
            logger.error(f"Google Maps directions error: {e}")
            raise
    
    async def geocode(self, address: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Geocode address with circuit breaker protection.
        
        Args:
            address: Address to geocode
            **kwargs: Additional arguments for googlemaps.geocode()
            
        Returns:
            Geocoding response from Google Maps API
            
        Raises:
            CircuitOpenError: If circuit breaker is open
        """
        try:
            loop = asyncio.get_event_loop()
            func = partial(self._client.geocode, address, **kwargs)
            
            result = await self._circuit_breaker.call_async(
                loop.run_in_executor,
                None,
                func
            )
            return result
        except CircuitOpenError:
            logger.error(f"Google Maps circuit breaker is open for geocode request")
            raise
        except Exception as e:
            logger.error(f"Google Maps geocode error: {e}")
            raise
    
    async def places_nearby(self, **kwargs) -> Dict[str, Any]:
        """
        Search nearby places with circuit breaker protection.
        
        Args:
            **kwargs: Arguments for googlemaps.places_nearby()
            
        Returns:
            Places response from Google Maps API
            
        Raises:
            CircuitOpenError: If circuit breaker is open
        """
        try:
            loop = asyncio.get_event_loop()
            func = partial(self._client.places_nearby, **kwargs)
            
            result = await self._circuit_breaker.call_async(
                loop.run_in_executor,
                None,
                func
            )
            return result
        except CircuitOpenError:
            logger.error(f"Google Maps circuit breaker is open for places request")
            raise
        except Exception as e:
            logger.error(f"Google Maps places error: {e}")
            raise
    
    async def distance_matrix(self, origins: List[str], destinations: List[str], **kwargs) -> Dict[str, Any]:
        """
        Calculate distance matrix with circuit breaker protection.
        
        Args:
            origins: List of origin locations
            destinations: List of destination locations
            **kwargs: Additional arguments for googlemaps.distance_matrix()
            
        Returns:
            Distance matrix response from Google Maps API
            
        Raises:
            CircuitOpenError: If circuit breaker is open
        """
        try:
            loop = asyncio.get_event_loop()
            func = partial(self._client.distance_matrix, origins, destinations, **kwargs)
            
            result = await self._circuit_breaker.call_async(
                loop.run_in_executor,
                None,
                func
            )
            return result
        except CircuitOpenError:
            logger.error(f"Google Maps circuit breaker is open for distance matrix request")
            raise
        except Exception as e:
            logger.error(f"Google Maps distance matrix error: {e}")
            raise


def get_maps_client_with_cb() -> GoogleMapsClientWithCB:
    """Get Google Maps client with circuit breaker protection."""
    if not settings.GOOGLE_MAPS_API_KEY:
        raise ValueError("Google Maps API key not configured")
    
    return GoogleMapsClientWithCB(settings.GOOGLE_MAPS_API_KEY)