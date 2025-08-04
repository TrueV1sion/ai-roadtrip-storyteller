from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import asyncio
from geopy.distance import geodesic

from app.integrations.ticketmaster_client import ticketmaster_client
from app.services.venue_personality_mapper import VenuePersonalityMapper
from app.core.enhanced_ai_client import enhanced_ai_client
from app.core.cache import cache_manager
from app.core.logger import logger
from app.services.theme_engine import ThemeEngine
from app.services.directions_service import DirectionsService
from app.models.story import EventJourney
from app.schemas.story import EventJourneyCreate


class EventJourneyService:
    """Service for creating immersive journeys to ticketed events."""
    
    def __init__(self):
        self.personality_mapper = VenuePersonalityMapper()
        self.theme_engine = ThemeEngine()
        self.directions_service = DirectionsService()
        
    async def detect_event_destination(
        self,
        destination: str,
        departure_time: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """Detect if a destination is a ticketed event venue."""
        # Try to parse destination for venue names or addresses
        venues = await ticketmaster_client.search_venues_near_location(
            lat=0, lon=0, radius=100  # Will be replaced with geocoded location
        )
        
        # Match destination with known venues
        for venue in venues:
            venue_name = venue.get("name", "").lower()
            if venue_name in destination.lower():
                # Check for events at this venue
                events = await ticketmaster_client.search_events(
                    venue_id=venue.get("id"),
                    start_datetime=departure_time or datetime.now(),
                    end_datetime=(departure_time or datetime.now()) + timedelta(days=1)
                )
                
                if events.get("_embedded", {}).get("events"):
                    return {
                        "venue": venue,
                        "events": events["_embedded"]["events"]
                    }
        
        return None
    
    async def create_event_journey(
        self,
        user_id: str,
        origin: str,
        event_id: str,
        preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a complete event journey experience."""
        # Get event details
        event = await ticketmaster_client.get_event_details(event_id)
        if not event:
            raise ValueError(f"Event {event_id} not found")
        
        # Extract event metadata
        event_metadata = await ticketmaster_client.extract_event_metadata(event)
        
        # Get venue details
        venue_id = event_metadata.get("venue", {}).get("id")
        venue = await ticketmaster_client.get_venue_details(venue_id) if venue_id else None
        
        # Select appropriate voice personality
        voice_personality = await self.personality_mapper.get_personality_for_event(
            event_metadata
        )
        
        # Generate route to venue
        destination = self._format_venue_address(event_metadata.get("venue", {}))
        route = await self.directions_service.get_directions(
            origin=origin,
            destination=destination,
            departure_time=self._get_optimal_departure_time(event)
        )
        
        # Generate themed journey content
        journey_content = await self._generate_journey_content(
            event_metadata,
            route,
            voice_personality,
            preferences
        )
        
        return {
            "event": event_metadata,
            "venue": venue,
            "route": route,
            "voice_personality": voice_personality,
            "journey_content": journey_content,
            "departure_time": self._get_optimal_departure_time(event),
            "estimated_arrival": self._calculate_arrival_time(route, event)
        }
    
    async def _generate_journey_content(
        self,
        event: Dict[str, Any],
        route: Dict[str, Any],
        voice_personality: Dict[str, Any],
        preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate AI-powered content for the journey."""
        # Build context for AI generation
        context = {
            "event_name": event.get("name"),
            "event_type": event.get("classifications", [{}])[0].get("segment"),
            "genre": event.get("classifications", [{}])[0].get("genre"),
            "attractions": [a.get("name") for a in event.get("attractions", [])],
            "venue_name": event.get("venue", {}).get("name"),
            "route_duration": route.get("duration"),
            "route_distance": route.get("distance"),
            "voice_style": voice_personality.get("style"),
            "user_preferences": preferences or {}
        }
        
        # Generate anticipation-building content
        intro_prompt = f"""
        Create an engaging introduction for a journey to {context['event_name']}.
        Event type: {context['event_type']}
        Performers: {', '.join(context['attractions'])}
        Venue: {context['venue_name']}
        Voice personality: {context['voice_style']}
        
        Build anticipation and excitement while providing interesting facts about
        the performers, venue history, or event significance. Keep it under 200 words.
        """
        
        intro_content = await enhanced_ai_client.generate_content(
            prompt=intro_prompt,
            temperature=0.8
        )
        
        # Generate milestone content for the journey
        milestones = await self._generate_journey_milestones(
            context, route, event
        )
        
        # Generate trivia about the event/performers
        trivia = await self._generate_event_trivia(context)
        
        return {
            "introduction": intro_content,
            "milestones": milestones,
            "trivia": trivia,
            "voice_personality": voice_personality,
            "theme": self._determine_journey_theme(event)
        }
    
    async def _generate_journey_milestones(
        self,
        context: Dict[str, Any],
        route: Dict[str, Any],
        event: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate content for journey milestones."""
        milestones = []
        
        # Departure milestone
        departure_prompt = f"""
        Create a brief, exciting departure message for someone heading to see {context['attractions'][0] if context['attractions'] else context['event_name']}.
        Make it personal and build anticipation. Voice style: {context['voice_style']}. Keep it under 50 words.
        """
        
        departure_content = await enhanced_ai_client.generate_content(
            prompt=departure_prompt,
            temperature=0.8
        )
        
        milestones.append({
            "type": "departure",
            "content": departure_content,
            "trigger": "journey_start"
        })
        
        # Halfway point milestone
        halfway_prompt = f"""
        Create an engaging halfway point message for the journey to {context['event_name']}.
        Include a fun fact about {context['attractions'][0] if context['attractions'] else 'the venue'}.
        Voice style: {context['voice_style']}. Keep it under 75 words.
        """
        
        halfway_content = await enhanced_ai_client.generate_content(
            prompt=halfway_prompt,
            temperature=0.8
        )
        
        milestones.append({
            "type": "halfway",
            "content": halfway_content,
            "trigger": "distance_percentage",
            "trigger_value": 0.5
        })
        
        # Near venue milestone
        arrival_prompt = f"""
        Create an arrival message as someone approaches {context['venue_name']} for {context['event_name']}.
        Include practical tips (parking, entry, etc). Voice style: {context['voice_style']}. Keep it under 100 words.
        """
        
        arrival_content = await enhanced_ai_client.generate_content(
            prompt=arrival_prompt,
            temperature=0.7
        )
        
        milestones.append({
            "type": "arrival",
            "content": arrival_content,
            "trigger": "distance_remaining",
            "trigger_value": 1.0  # 1 mile from venue
        })
        
        return milestones
    
    async def _generate_event_trivia(
        self,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate trivia questions about the event/performers."""
        trivia_prompt = f"""
        Generate 5 interesting trivia questions about {context['attractions'][0] if context['attractions'] else context['event_name']}.
        Include questions about career highlights, achievements, famous songs/plays/games, and fun facts.
        Format as JSON array with 'question', 'answer', and 'difficulty' (easy/medium/hard) fields.
        """
        
        trivia_response = await enhanced_ai_client.generate_content(
            prompt=trivia_prompt,
            temperature=0.7,
            response_format="json"
        )
        
        try:
            import json
            trivia = json.loads(trivia_response)
            return trivia
        except Exception as e:
            return []
    
    def _determine_journey_theme(self, event: Dict[str, Any]) -> str:
        """Determine the appropriate theme for the journey."""
        classifications = event.get("classifications", [{}])[0]
        segment = classifications.get("segment", "").lower()
        genre = classifications.get("genre", "").lower()
        
        # Map event types to journey themes
        if segment == "music":
            if "rock" in genre:
                return "rock_concert"
            elif "classical" in genre:
                return "symphony"
            elif "jazz" in genre:
                return "jazz_club"
            else:
                return "concert"
        elif segment == "sports":
            return "game_day"
        elif segment == "arts & theatre":
            return "theater"
        elif segment == "family":
            return "family_fun"
        else:
            return "special_event"
    
    def _format_venue_address(self, venue: Dict[str, Any]) -> str:
        """Format venue information into a proper address."""
        parts = []
        
        if venue.get("name"):
            parts.append(venue["name"])
        if venue.get("address", {}).get("line1"):
            parts.append(venue["address"]["line1"])
        if venue.get("city", {}).get("name"):
            parts.append(venue["city"]["name"])
        if venue.get("state", {}).get("stateCode"):
            parts.append(venue["state"]["stateCode"])
        if venue.get("postalCode"):
            parts.append(venue["postalCode"])
            
        return ", ".join(parts)
    
    def _get_optimal_departure_time(self, event: Dict[str, Any]) -> datetime:
        """Calculate optimal departure time based on event start."""
        dates = event.get("dates", {})
        start = dates.get("start", {})
        
        if start.get("dateTime"):
            event_time = datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00"))
            # Suggest arriving 30 minutes early
            return event_time - timedelta(minutes=30)
        
        return datetime.now()
    
    def _calculate_arrival_time(self, route: Dict[str, Any], event: Dict[str, Any]) -> datetime:
        """Calculate estimated arrival time at venue."""
        departure_time = self._get_optimal_departure_time(event)
        duration_seconds = route.get("duration", {}).get("value", 0)
        
        return departure_time + timedelta(seconds=duration_seconds)
    
    async def get_user_events(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get upcoming events for a user based on their saved events."""
        # This would integrate with a user's saved events database
        # For now, return empty list
        return []
    
    async def suggest_pregame_activities(
        self,
        event_id: str,
        current_location: Tuple[float, float],
        time_available: int  # minutes
    ) -> List[Dict[str, Any]]:
        """Suggest activities near the venue before the event."""
        event = await ticketmaster_client.get_event_details(event_id)
        if not event:
            return []
        
        event_metadata = await ticketmaster_client.extract_event_metadata(event)
        venue = event_metadata.get("venue", {})
        
        # Generate suggestions based on event type and time available
        suggestions_prompt = f"""
        Suggest 3-5 activities near {venue.get('name')} that someone could do 
        with {time_available} minutes before attending {event_metadata.get('name')}.
        Event type: {event_metadata.get('classifications', [{}])[0].get('segment')}
        
        Consider restaurants, bars, parking tips, and nearby attractions.
        Format as JSON array with 'name', 'type', 'duration_minutes', and 'description'.
        """
        
        suggestions_response = await enhanced_ai_client.generate_content(
            prompt=suggestions_prompt,
            temperature=0.7,
            response_format="json"
        )
        
        try:
            import json
            suggestions = json.loads(suggestions_response)
            return suggestions
        except Exception as e:
            return []