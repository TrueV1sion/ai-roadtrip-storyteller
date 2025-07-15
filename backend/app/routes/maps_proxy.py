"""
Google Maps API proxy endpoints to protect API keys from client exposure.
All Maps API calls should go through these endpoints instead of direct client calls.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, Dict, Any, List
import googlemaps
from datetime import datetime
import logging

from app.core.config import settings
from app.core.auth import get_current_user
from app.models.user import User
from app.core.cache import cache_manager
from app.core.google_maps_client_cb import get_maps_client_with_cb
from app.core.circuit_breaker import CircuitOpenError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/maps", tags=["Maps Proxy"])

# Initialize Google Maps client with circuit breaker protection
def get_maps_client():
    """Get Google Maps client with circuit breaker protection."""
    try:
        return get_maps_client_with_cb()
    except ValueError as e:
        raise HTTPException(
            status_code=503,
            detail="Google Maps service is not configured"
        )


@router.get("/directions")
async def get_directions(
    origin: str = Query(..., description="Origin location"),
    destination: str = Query(..., description="Destination location"),
    waypoints: Optional[str] = Query(None, description="Pipe-separated waypoints"),
    mode: str = Query("driving", description="Travel mode"),
    departure_time: Optional[str] = Query(None, description="ISO format departure time"),
    traffic_model: str = Query("best_guess", description="Traffic model"),
    current_user: User = Depends(get_current_user)
):
    """
    Get directions between locations (proxy for Google Maps Directions API).
    
    This endpoint protects the Google Maps API key by handling the request server-side.
    """
    try:
        gmaps = get_maps_client()
        
        # Build request parameters
        params = {
            "origin": origin,
            "destination": destination,
            "mode": mode,
            "traffic_model": traffic_model
        }
        
        # Add optional parameters
        if waypoints:
            params["waypoints"] = waypoints.split("|")
            
        if departure_time:
            params["departure_time"] = datetime.fromisoformat(departure_time)
        else:
            params["departure_time"] = "now"
        
        # Check cache first
        cache_key = f"directions:{origin}:{destination}:{mode}:{waypoints or ''}"
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            logger.info(f"Returning cached directions for user {current_user.id}")
            return cached_result
        
        # Make API call with circuit breaker protection
        try:
            result = await gmaps.directions(**params)
            
            # Cache for 5 minutes (traffic data changes frequently)
            await cache_manager.set(cache_key, result, expire=300)
            
            # Log usage for monitoring
            logger.info(f"Directions API called by user {current_user.id}: {origin} to {destination}")
            
            return result
        except CircuitOpenError:
            logger.error("Google Maps circuit breaker is open")
            raise HTTPException(
                status_code=503,
                detail="Maps service temporarily unavailable. Please try again later."
            )
        
    except googlemaps.exceptions.ApiError as e:
        logger.error(f"Google Maps API error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Maps proxy error: {e}")
        raise HTTPException(status_code=500, detail="Maps service error")


@router.get("/geocode")
async def geocode_address(
    address: str = Query(..., description="Address to geocode"),
    current_user: User = Depends(get_current_user)
):
    """
    Geocode an address to coordinates (proxy for Google Maps Geocoding API).
    """
    try:
        gmaps = get_maps_client()
        
        # Check cache
        cache_key = f"geocode:{address}"
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            return cached_result
        
        # Make API call with circuit breaker protection
        try:
            result = await gmaps.geocode(address)
            
            # Cache for 24 hours (geocoding results don't change often)
            await cache_manager.set(cache_key, result, expire=86400)
            
            logger.info(f"Geocoding API called by user {current_user.id}: {address}")
            
            return result
        except CircuitOpenError:
            logger.error("Google Maps circuit breaker is open")
            raise HTTPException(
                status_code=503,
                detail="Maps service temporarily unavailable. Please try again later."
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Geocoding error: {e}")
        raise HTTPException(status_code=500, detail="Geocoding service error")


@router.get("/places/nearby")
async def search_places_nearby(
    location: str = Query(..., description="Lat,lng format"),
    radius: int = Query(5000, description="Search radius in meters"),
    type: Optional[str] = Query(None, description="Place type filter"),
    keyword: Optional[str] = Query(None, description="Search keyword"),
    current_user: User = Depends(get_current_user)
):
    """
    Search for places near a location (proxy for Google Maps Places API).
    """
    try:
        gmaps = get_maps_client()
        
        # Parse location
        lat, lng = map(float, location.split(","))
        location_tuple = (lat, lng)
        
        # Build request
        params = {
            "location": location_tuple,
            "radius": radius
        }
        
        if type:
            params["type"] = type
        if keyword:
            params["keyword"] = keyword
        
        # Check cache
        cache_key = f"places:{location}:{radius}:{type or ''}:{keyword or ''}"
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            return cached_result
        
        # Make API call
        result = gmaps.places_nearby(**params)
        
        # Cache for 1 hour
        await cache_manager.set(cache_key, result, expire=3600)
        
        logger.info(f"Places API called by user {current_user.id}: {location}")
        
        return result
        
    except Exception as e:
        logger.error(f"Places search error: {e}")
        raise HTTPException(status_code=500, detail="Places service error")


@router.get("/places/details/{place_id}")
async def get_place_details(
    place_id: str,
    fields: Optional[str] = Query(None, description="Comma-separated fields"),
    current_user: User = Depends(get_current_user)
):
    """
    Get details for a specific place (proxy for Google Maps Place Details API).
    """
    try:
        gmaps = get_maps_client()
        
        # Default fields if not specified
        if not fields:
            fields = ["name", "formatted_address", "geometry", "rating", "opening_hours"]
        else:
            fields = fields.split(",")
        
        # Check cache
        cache_key = f"place_details:{place_id}:{','.join(sorted(fields))}"
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            return cached_result
        
        # Make API call
        result = gmaps.place(place_id, fields=fields)
        
        # Cache for 6 hours
        await cache_manager.set(cache_key, result, expire=21600)
        
        logger.info(f"Place Details API called by user {current_user.id}: {place_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"Place details error: {e}")
        raise HTTPException(status_code=500, detail="Place details service error")


@router.get("/staticmap")
async def get_static_map(
    center: Optional[str] = Query(None, description="Center of map (lat,lng)"),
    zoom: int = Query(13, description="Zoom level"),
    size: str = Query("600x400", description="Image size"),
    markers: Optional[str] = Query(None, description="Map markers"),
    path: Optional[str] = Query(None, description="Path to draw"),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a static map URL (proxy for Google Maps Static API).
    
    Note: This returns a URL that the client can use directly, but the URL
    includes the API key, so we should consider server-side image proxying
    for production.
    """
    try:
        gmaps = get_maps_client()
        
        # Build parameters
        params = {
            "size": size,
            "zoom": zoom
        }
        
        if center:
            params["center"] = center
        if markers:
            params["markers"] = markers
        if path:
            params["path"] = path
        
        # For now, return the URL (consider proxying the image in production)
        base_url = "https://maps.googleapis.com/maps/api/staticmap"
        params["key"] = settings.GOOGLE_MAPS_API_KEY
        
        # Build query string
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        url = f"{base_url}?{query_string}"
        
        logger.info(f"Static Map API URL generated for user {current_user.id}")
        
        return {"url": url}
        
    except Exception as e:
        logger.error(f"Static map error: {e}")
        raise HTTPException(status_code=500, detail="Static map service error")