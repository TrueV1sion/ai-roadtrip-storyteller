import googlemaps
from typing import Optional, Dict, List, Any
from datetime import datetime

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

class DirectionsService:
    """Service for fetching directions using Google Maps Directions API."""

    def __init__(self):
        try:
            if settings.GOOGLE_MAPS_API_KEY:
                self.gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
                logger.info("Google Maps client initialized for DirectionsService.")
            else:
                logger.warning("GOOGLE_MAPS_API_KEY not set. Directions service will not function.")
                self.gmaps = None
        except Exception as e:
            logger.error(f"Failed to initialize Google Maps client for DirectionsService: {e}")
            self.gmaps = None

    def get_directions(
        self,
        origin: str, # Can be address, lat/lng string, or place ID
        destination: str,
        mode: str = "driving", # driving, walking, bicycling, transit
        departure_time: Optional[datetime] = None, # For traffic prediction
        waypoints: Optional[List[str]] = None, # Intermediate points
        optimize_waypoints: bool = False
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Fetches directions between an origin and destination.

        Args:
            origin: The starting point.
            destination: The ending point.
            mode: Travel mode.
            departure_time: Time of departure (for traffic).
            waypoints: List of intermediate waypoints.
            optimize_waypoints: Allow rearranging waypoints for shortest route.

        Returns:
            A list of direction results (usually one), or None on failure.
            See Google Maps Directions API documentation for result structure.
        """
        if not self.gmaps:
            logger.error("DirectionsService cannot function: Google Maps client not initialized.")
            return None

        try:
            logger.info(f"Requesting directions from '{origin}' to '{destination}' (mode: {mode})")
            directions_result = self.gmaps.directions(
                origin=origin,
                destination=destination,
                mode=mode,
                departure_time=departure_time,
                waypoints=waypoints,
                optimize_waypoints=optimize_waypoints
            )
            logger.info(f"Received directions result (legs: {len(directions_result[0]['legs']) if directions_result else 0})")
            return directions_result # Returns a list of routes

        except googlemaps.exceptions.ApiError as e:
            logger.error(f"Google Maps Directions API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching directions: {e}")
            return None

# Create singleton instance
directions_service = DirectionsService()