"""
Cache Warming Service
Intelligently preloads cache with predicted content based on usage patterns
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

from app.core.multi_tier_cache import multi_tier_cache, ContentType
from app.core.logger import get_logger
from app.services.location_service import LocationService
from app.services.story_generation_agent import StoryGenerationAgent
from app.services.booking_services import BookingOrchestrator
from app.db.session import get_db
from app.models.user import User
from app.models.trip import Trip

logger = get_logger(__name__)


@dataclass
class WarmingPattern:
    """Pattern for cache warming."""
    pattern_id: str
    pattern_type: str
    generator: Callable
    content_type: ContentType
    priority: int  # 1-10, higher is more important
    conditions: Dict[str, Any]
    tags: List[str]


class CacheWarmingService:
    """Service for intelligent cache warming based on patterns and predictions."""
    
    def __init__(self):
        self.cache = multi_tier_cache
        self.location_service = LocationService()
        self.story_agent = StoryGenerationAgent()
        self.booking_orchestrator = BookingOrchestrator()
        
        # Warming configurations
        self.warming_enabled = True
        self.max_concurrent_warmings = 5
        self.warming_interval = 300  # 5 minutes
        
        # Pattern registry
        self.warming_patterns: List[WarmingPattern] = []
        
        # Initialize default patterns
        self._initialize_default_patterns()
        
        # Start warming loop
        self._warming_task = asyncio.create_task(self._warming_loop())
    
    def _initialize_default_patterns(self):
        """Initialize default warming patterns."""
        
        # Popular routes pattern
        self.warming_patterns.append(WarmingPattern(
            pattern_id="popular_routes",
            pattern_type="route",
            generator=self._warm_popular_routes,
            content_type=ContentType.ROUTE_INFO,
            priority=8,
            conditions={"time_window": "peak_hours"},
            tags=["route", "navigation"]
        ))
        
        # Story locations pattern
        self.warming_patterns.append(WarmingPattern(
            pattern_id="story_locations",
            pattern_type="story",
            generator=self._warm_story_locations,
            content_type=ContentType.STORY_CONTENT,
            priority=7,
            conditions={"radius_miles": 50},
            tags=["story", "location"]
        ))
        
        # Booking searches pattern
        self.warming_patterns.append(WarmingPattern(
            pattern_id="booking_searches",
            pattern_type="booking",
            generator=self._warm_booking_searches,
            content_type=ContentType.BOOKING_SEARCH,
            priority=6,
            conditions={"categories": ["gas", "restaurant", "hotel"]},
            tags=["booking", "search"]
        ))
        
        # Voice personalities pattern
        self.warming_patterns.append(WarmingPattern(
            pattern_id="voice_personalities",
            pattern_type="voice",
            generator=self._warm_voice_greetings,
            content_type=ContentType.VOICE_AUDIO,
            priority=5,
            conditions={"personalities": ["captain", "tour_guide", "comedian"]},
            tags=["voice", "audio"]
        ))
        
        # User preferences pattern
        self.warming_patterns.append(WarmingPattern(
            pattern_id="user_preferences",
            pattern_type="user",
            generator=self._warm_user_preferences,
            content_type=ContentType.USER_PREFERENCE,
            priority=9,
            conditions={"active_users": True},
            tags=["user", "preferences"]
        ))
    
    async def _warming_loop(self):
        """Main loop for cache warming."""
        while self.warming_enabled:
            try:
                await asyncio.sleep(self.warming_interval)
                
                # Get patterns to warm
                patterns_to_warm = await self._select_patterns_to_warm()
                
                # Warm cache with selected patterns
                if patterns_to_warm:
                    await self._execute_warming(patterns_to_warm)
                
                # Log warming stats
                self._log_warming_stats()
                
            except Exception as e:
                logger.error(f"Cache warming loop error: {e}")
    
    async def _select_patterns_to_warm(self) -> List[WarmingPattern]:
        """Select patterns to warm based on conditions and priority."""
        selected = []
        
        for pattern in self.warming_patterns:
            if await self._should_warm_pattern(pattern):
                selected.append(pattern)
        
        # Sort by priority and limit
        selected.sort(key=lambda p: p.priority, reverse=True)
        return selected[:self.max_concurrent_warmings]
    
    async def _should_warm_pattern(self, pattern: WarmingPattern) -> bool:
        """Determine if a pattern should be warmed."""
        conditions = pattern.conditions
        
        # Check time-based conditions
        if "time_window" in conditions:
            if conditions["time_window"] == "peak_hours":
                hour = datetime.now().hour
                if hour not in [7, 8, 9, 16, 17, 18, 19]:  # Peak hours
                    return False
        
        # Check active users condition
        if conditions.get("active_users"):
            # Check if there are active users
            active_count = await self._get_active_user_count()
            if active_count == 0:
                return False
        
        return True
    
    async def _execute_warming(self, patterns: List[WarmingPattern]):
        """Execute cache warming for selected patterns."""
        tasks = []
        
        for pattern in patterns:
            task = asyncio.create_task(self._warm_single_pattern(pattern))
            tasks.append(task)
        
        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log results
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        logger.info(f"Cache warming completed: {success_count}/{len(patterns)} patterns warmed")
    
    async def _warm_single_pattern(self, pattern: WarmingPattern):
        """Warm cache for a single pattern."""
        try:
            logger.debug(f"Warming cache for pattern: {pattern.pattern_id}")
            
            # Execute pattern generator
            cache_entries = await pattern.generator()
            
            # Store in cache
            for entry in cache_entries:
                await self.cache.set(
                    key=entry['key'],
                    value=entry['value'],
                    content_type=pattern.content_type,
                    tags=pattern.tags + [pattern.pattern_id]
                )
            
            logger.debug(f"Warmed {len(cache_entries)} entries for {pattern.pattern_id}")
            
        except Exception as e:
            logger.error(f"Error warming pattern {pattern.pattern_id}: {e}")
            raise
    
    async def _warm_popular_routes(self) -> List[Dict[str, Any]]:
        """Warm cache with popular routes."""
        cache_entries = []
        
        # Get popular routes from database
        popular_routes = await self._get_popular_routes()
        
        for route in popular_routes:
            # Generate cache key
            cache_key = f"route:{route['origin_lat']},{route['origin_lng']}:" \
                       f"{route['dest_lat']},{route['dest_lng']}"
            
            # Get route info
            route_info = await self.location_service.get_route_info(
                origin=(route['origin_lat'], route['origin_lng']),
                destination=(route['dest_lat'], route['dest_lng'])
            )
            
            if route_info:
                cache_entries.append({
                    'key': cache_key,
                    'value': route_info
                })
        
        return cache_entries
    
    async def _warm_story_locations(self) -> List[Dict[str, Any]]:
        """Warm cache with stories for popular locations."""
        cache_entries = []
        
        # Get popular story locations
        locations = await self._get_popular_story_locations()
        
        for location in locations:
            for theme in ['adventure', 'history', 'mystery']:
                # Generate cache key
                cache_key = f"story:{location['lat']:.3f},{location['lng']:.3f}:{theme}"
                
                # Generate story
                story = await self.story_agent.generate_story(
                    location={
                        'lat': location['lat'],
                        'lng': location['lng'],
                        'name': location.get('name', 'Unknown Location')
                    },
                    story_theme=theme,
                    duration='medium'
                )
                
                if story:
                    cache_entries.append({
                        'key': cache_key,
                        'value': story
                    })
        
        return cache_entries
    
    async def _warm_booking_searches(self) -> List[Dict[str, Any]]:
        """Warm cache with common booking searches."""
        cache_entries = []
        
        # Get popular destinations
        destinations = await self._get_popular_destinations()
        
        for dest in destinations:
            for category in ['gas_station', 'restaurant', 'hotel']:
                # Generate cache key
                cache_key = f"booking:{category}:{dest['lat']:.3f},{dest['lng']:.3f}"
                
                # Search bookings
                results = await self.booking_orchestrator.search_unified(
                    query=category,
                    location=(dest['lat'], dest['lng']),
                    radius_miles=10
                )
                
                if results:
                    cache_entries.append({
                        'key': cache_key,
                        'value': results
                    })
        
        return cache_entries
    
    async def _warm_voice_greetings(self) -> List[Dict[str, Any]]:
        """Warm cache with common voice greetings."""
        cache_entries = []
        
        # Common greetings by personality
        greetings = {
            'captain': [
                "Welcome aboard! Ready for an adventure?",
                "Good morning, traveler! Where shall we explore today?",
                "Ahoy there! Let's set sail on the open road!"
            ],
            'tour_guide': [
                "Welcome! I'm excited to show you around today.",
                "Hello! Did you know this area has fascinating history?",
                "Greetings! Let me share some interesting facts about our route."
            ],
            'comedian': [
                "Well hello there! Ready for some laughs on the road?",
                "Welcome! I promise this trip will be wheely good!",
                "Hey there! Buckle up for fun - and safety, of course!"
            ]
        }
        
        # This would actually generate TTS audio
        # For now, we'll create placeholder entries
        for personality, texts in greetings.items():
            for text in texts:
                cache_key = f"voice:{personality}:{hashlib.md5(text.encode()).hexdigest()[:8]}"
                
                cache_entries.append({
                    'key': cache_key,
                    'value': {
                        'text': text,
                        'personality': personality,
                        'audio_url': f"cached_audio/{cache_key}.mp3"
                    }
                })
        
        return cache_entries
    
    async def _warm_user_preferences(self) -> List[Dict[str, Any]]:
        """Warm cache with active user preferences."""
        cache_entries = []
        
        # Get recently active users
        async with get_db() as db:
            active_users = db.query(User).filter(
                User.last_active > datetime.now() - timedelta(hours=24)
            ).limit(100).all()
        
        for user in active_users:
            cache_key = f"user_pref:{user.id}"
            
            preferences = {
                'user_id': user.id,
                'preferred_voice': user.preferences.get('voice_personality', 'captain'),
                'preferred_themes': user.preferences.get('story_themes', ['adventure']),
                'language': user.preferences.get('language', 'en'),
                'accessibility': user.preferences.get('accessibility', {})
            }
            
            cache_entries.append({
                'key': cache_key,
                'value': preferences
            })
        
        return cache_entries
    
    async def _get_popular_routes(self) -> List[Dict[str, Any]]:
        """Get popular routes from trip history."""
        # This would query actual trip data
        # For now, return common routes
        return [
            {
                'origin_lat': 37.7749, 'origin_lng': -122.4194,  # SF
                'dest_lat': 34.0522, 'dest_lng': -118.2437      # LA
            },
            {
                'origin_lat': 40.7128, 'origin_lng': -74.0060,   # NYC
                'dest_lat': 38.9072, 'dest_lng': -77.0369       # DC
            }
        ]
    
    async def _get_popular_story_locations(self) -> List[Dict[str, Any]]:
        """Get popular locations for stories."""
        # This would analyze actual story request data
        # For now, return major landmarks
        return [
            {'lat': 37.8199, 'lng': -122.4783, 'name': 'Golden Gate Bridge'},
            {'lat': 36.1069, 'lng': -112.1129, 'name': 'Grand Canyon'},
            {'lat': 40.7484, 'lng': -73.9857, 'name': 'Empire State Building'}
        ]
    
    async def _get_popular_destinations(self) -> List[Dict[str, Any]]:
        """Get popular destinations for bookings."""
        # This would analyze booking search patterns
        # For now, return major cities
        return [
            {'lat': 37.7749, 'lng': -122.4194, 'name': 'San Francisco'},
            {'lat': 34.0522, 'lng': -118.2437, 'name': 'Los Angeles'},
            {'lat': 40.7128, 'lng': -74.0060, 'name': 'New York'}
        ]
    
    async def _get_active_user_count(self) -> int:
        """Get count of currently active users."""
        # This would check active sessions
        # For now, return a placeholder
        return 10
    
    def _log_warming_stats(self):
        """Log cache warming statistics."""
        # This would track actual warming metrics
        logger.info("Cache warming cycle completed")
    
    async def warm_for_trip(self, trip_id: str):
        """Warm cache for a specific trip."""
        try:
            # Get trip details
            async with get_db() as db:
                trip = db.query(Trip).filter(Trip.id == trip_id).first()
                
                if not trip:
                    return
            
            # Warm route information
            route_key = f"route:{trip.origin_lat},{trip.origin_lng}:" \
                       f"{trip.destination_lat},{trip.destination_lng}"
            
            route_info = await self.location_service.get_route_info(
                origin=(trip.origin_lat, trip.origin_lng),
                destination=(trip.destination_lat, trip.destination_lng)
            )
            
            if route_info:
                await self.cache.set(
                    key=route_key,
                    value=route_info,
                    content_type=ContentType.ROUTE_INFO,
                    user_id=trip.user_id,
                    tags=['route', 'trip', trip_id]
                )
            
            # Warm stories along route
            if route_info and 'waypoints' in route_info:
                for waypoint in route_info['waypoints'][:5]:  # First 5 waypoints
                    story_key = f"story:{waypoint['lat']:.3f},{waypoint['lng']:.3f}:adventure"
                    
                    story = await self.story_agent.generate_story(
                        location=waypoint,
                        story_theme='adventure',
                        duration='short'
                    )
                    
                    if story:
                        await self.cache.set(
                            key=story_key,
                            value=story,
                            content_type=ContentType.STORY_CONTENT,
                            user_id=trip.user_id,
                            tags=['story', 'trip', trip_id]
                        )
            
            logger.info(f"Cache warmed for trip {trip_id}")
            
        except Exception as e:
            logger.error(f"Error warming cache for trip {trip_id}: {e}")
    
    async def warm_for_user(self, user_id: str):
        """Warm cache based on user's history and preferences."""
        try:
            # Get user preferences
            async with get_db() as db:
                user = db.query(User).filter(User.id == user_id).first()
                
                if not user:
                    return
            
            # Warm based on favorite locations
            if 'favorite_locations' in user.preferences:
                for location in user.preferences['favorite_locations']:
                    # Warm stories for favorite locations
                    for theme in user.preferences.get('story_themes', ['adventure']):
                        story_key = f"story:{location['lat']:.3f},{location['lng']:.3f}:{theme}"
                        
                        story = await self.story_agent.generate_story(
                            location=location,
                            story_theme=theme,
                            duration='medium'
                        )
                        
                        if story:
                            await self.cache.set(
                                key=story_key,
                                value=story,
                                content_type=ContentType.STORY_CONTENT,
                                user_id=user_id,
                                tags=['story', 'user', user_id]
                            )
            
            logger.info(f"Cache warmed for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error warming cache for user {user_id}: {e}")
    
    def add_warming_pattern(self, pattern: WarmingPattern):
        """Add a custom warming pattern."""
        self.warming_patterns.append(pattern)
        logger.info(f"Added warming pattern: {pattern.pattern_id}")
    
    def remove_warming_pattern(self, pattern_id: str):
        """Remove a warming pattern."""
        self.warming_patterns = [
            p for p in self.warming_patterns 
            if p.pattern_id != pattern_id
        ]
        logger.info(f"Removed warming pattern: {pattern_id}")
    
    def set_warming_enabled(self, enabled: bool):
        """Enable or disable cache warming."""
        self.warming_enabled = enabled
        logger.info(f"Cache warming {'enabled' if enabled else 'disabled'}")


# Global cache warming service
cache_warming_service = CacheWarmingService()


# Export components
__all__ = [
    'cache_warming_service',
    'CacheWarmingService',
    'WarmingPattern'
]