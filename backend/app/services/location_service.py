"""
Location Service
Handles location-based queries and nearby place lookups
"""

from typing import Dict, List, Optional, Any, Tuple
import asyncio
from datetime import datetime
import googlemaps

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.core.cache import cache_manager


class LocationService:
    """Service for location-based operations"""
    
    def __init__(self):
        self.gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
    
    async def get_nearby_places(
        self,
        latitude: float,
        longitude: float,
        radius: int = 5000,
        place_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get nearby places of interest"""
        cache_key = f"nearby_places:{latitude}:{longitude}:{radius}"
        
        # Check cache
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached
        
        try:
            # Default place types if not specified
            if not place_types:
                place_types = [
                    'tourist_attraction',
                    'museum',
                    'park',
                    'point_of_interest',
                    'establishment'
                ]
            
            all_places = []
            
            # Query each place type
            for place_type in place_types:
                result = self.gmaps.places_nearby(
                    location=(latitude, longitude),
                    radius=radius,
                    type=place_type
                )
                
                places = result.get('results', [])
                
                # Process and add places
                for place in places:
                    all_places.append({
                        'place_id': place.get('place_id'),
                        'name': place.get('name'),
                        'lat': place['geometry']['location']['lat'],
                        'lng': place['geometry']['location']['lng'],
                        'types': place.get('types', []),
                        'rating': place.get('rating'),
                        'user_ratings_total': place.get('user_ratings_total', 0),
                        'vicinity': place.get('vicinity'),
                        'photos': place.get('photos', [])
                    })
            
            # Remove duplicates based on place_id
            unique_places = []
            seen_ids = set()
            for place in all_places:
                if place['place_id'] not in seen_ids:
                    seen_ids.add(place['place_id'])
                    unique_places.append(place)
            
            # Sort by rating and number of ratings
            unique_places.sort(
                key=lambda x: (x.get('rating', 0) * x.get('user_ratings_total', 0)),
                reverse=True
            )
            
            # Cache for 1 hour
            await cache_manager.set(cache_key, unique_places[:50], ttl=3600)
            
            return unique_places[:50]  # Return top 50 places
            
        except Exception as e:
            logger.error(f"Error getting nearby places: {e}")
            return []
    
    async def get_place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a place"""
        cache_key = f"place_details:{place_id}"
        
        # Check cache
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached
        
        try:
            result = self.gmaps.place(
                place_id=place_id,
                fields=[
                    'name', 'formatted_address', 'formatted_phone_number',
                    'opening_hours', 'website', 'rating', 'reviews',
                    'photos', 'types', 'geometry', 'url', 'vicinity',
                    'editorial_summary', 'price_level'
                ]
            )
            
            place = result.get('result')
            if not place:
                return None
            
            # Process place details
            details = {
                'place_id': place_id,
                'name': place.get('name'),
                'address': place.get('formatted_address'),
                'phone': place.get('formatted_phone_number'),
                'website': place.get('website'),
                'google_url': place.get('url'),
                'rating': place.get('rating'),
                'price_level': place.get('price_level'),
                'types': place.get('types', []),
                'location': {
                    'lat': place['geometry']['location']['lat'],
                    'lng': place['geometry']['location']['lng']
                },
                'opening_hours': place.get('opening_hours', {}),
                'reviews': place.get('reviews', [])[:5],  # Top 5 reviews
                'photos': place.get('photos', [])[:10],  # First 10 photos
                'editorial_summary': place.get('editorial_summary', {}).get('overview')
            }
            
            # Cache for 1 day
            await cache_manager.set(cache_key, details, ttl=86400)
            
            return details
            
        except Exception as e:
            logger.error(f"Error getting place details: {e}")
            return None
    
    async def search_places(
        self,
        query: str,
        location: Optional[Tuple[float, float]] = None,
        radius: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Search for places by query"""
        try:
            params = {'query': query}
            
            if location:
                params['location'] = location
            
            if radius:
                params['radius'] = radius
            
            result = self.gmaps.places(**params)
            
            places = []
            for place in result.get('results', []):
                places.append({
                    'place_id': place.get('place_id'),
                    'name': place.get('name'),
                    'address': place.get('formatted_address'),
                    'lat': place['geometry']['location']['lat'],
                    'lng': place['geometry']['location']['lng'],
                    'types': place.get('types', []),
                    'rating': place.get('rating'),
                    'price_level': place.get('price_level'),
                    'opening_now': place.get('opening_hours', {}).get('open_now')
                })
            
            return places
            
        except Exception as e:
            logger.error(f"Error searching places: {e}")
            return []
    
    async def get_distance_matrix(
        self,
        origins: List[Tuple[float, float]],
        destinations: List[Tuple[float, float]],
        mode: str = "driving"
    ) -> Dict[str, Any]:
        """Get distance and duration between multiple points"""
        try:
            result = self.gmaps.distance_matrix(
                origins=origins,
                destinations=destinations,
                mode=mode,
                units="metric"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting distance matrix: {e}")
            return {}
    
    async def reverse_geocode(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[Dict[str, Any]]:
        """Get address from coordinates"""
        cache_key = f"reverse_geocode:{latitude}:{longitude}"
        
        # Check cache
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached
        
        try:
            result = self.gmaps.reverse_geocode((latitude, longitude))
            
            if result:
                location_info = {
                    'formatted_address': result[0].get('formatted_address'),
                    'components': {}
                }
                
                # Extract address components
                for component in result[0].get('address_components', []):
                    types = component.get('types', [])
                    if 'locality' in types:
                        location_info['components']['city'] = component.get('long_name')
                    elif 'administrative_area_level_1' in types:
                        location_info['components']['state'] = component.get('long_name')
                    elif 'country' in types:
                        location_info['components']['country'] = component.get('long_name')
                    elif 'postal_code' in types:
                        location_info['components']['postal_code'] = component.get('long_name')
                
                # Cache for 1 day
                await cache_manager.set(cache_key, location_info, ttl=86400)
                
                return location_info
            
            return None
            
        except Exception as e:
            logger.error(f"Error reverse geocoding: {e}")
            return None


# Create singleton instance
location_service = LocationService()

# Export convenience functions
async def get_nearby_places(
    latitude: float,
    longitude: float,
    radius: int = 5000,
    place_types: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """Convenience function for getting nearby places"""
    return await location_service.get_nearby_places(
        latitude, longitude, radius, place_types
    )

async def get_place_details(place_id: str) -> Optional[Dict[str, Any]]:
    """Convenience function for getting place details"""
    return await location_service.get_place_details(place_id)

async def search_places(
    query: str,
    location: Optional[Tuple[float, float]] = None,
    radius: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Convenience function for searching places"""
    return await location_service.search_places(query, location, radius)

async def reverse_geocode(
    latitude: float,
    longitude: float
) -> Optional[Dict[str, Any]]:
    """Convenience function for reverse geocoding"""
    return await location_service.reverse_geocode(latitude, longitude)