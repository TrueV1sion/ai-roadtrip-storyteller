"""
Comprehensive Dynamic Personality System

This system automatically selects and manages voice personalities based on multiple contextual factors:
- Event type and venue
- Holiday and seasonal context
- Location and regional preferences
- Time of day and day of week
- User preferences and history
- Special occasions and themes
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, date, time
from enum import Enum
import json
import logging
from dataclasses import dataclass, field
import pytz
from collections import defaultdict

from ..core.cache import cache_manager
from ..models.user import UserPreferences
from .personality_engine import PersonalityEngine, VoicePersonality, PersonalityType
from .venue_personality_mapper import VenuePersonalityMapper
from .voice_personalities import load_extended_personalities

logger = logging.getLogger(__name__)


@dataclass
class PersonalityMetadata:
    """Extended metadata for dynamic personality selection"""
    id: str
    priority: int = 50  # 0-100, higher = more likely to be selected
    event_types: List[str] = field(default_factory=list)
    venues: List[str] = field(default_factory=list)
    weather_conditions: List[str] = field(default_factory=list)
    time_ranges: List[Tuple[int, int]] = field(default_factory=list)  # List of (start_hour, end_hour)
    days_of_week: List[int] = field(default_factory=list)  # 0=Monday, 6=Sunday
    seasons: List[str] = field(default_factory=list)
    holidays: List[str] = field(default_factory=list)
    regions: List[str] = field(default_factory=list)
    user_moods: List[str] = field(default_factory=list)
    age_groups: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    special_occasions: List[str] = field(default_factory=list)
    exclusion_rules: Dict[str, Any] = field(default_factory=dict)  # Conditions that prevent selection


class ContextFactor(str, Enum):
    """Factors that influence personality selection"""
    EVENT_TYPE = "event_type"
    VENUE = "venue"
    HOLIDAY = "holiday"
    SEASON = "season"
    LOCATION = "location"
    TIME_OF_DAY = "time_of_day"
    DAY_OF_WEEK = "day_of_week"
    WEATHER = "weather"
    USER_PREFERENCE = "user_preference"
    USER_MOOD = "user_mood"
    SPECIAL_OCCASION = "special_occasion"
    JOURNEY_TYPE = "journey_type"
    PASSENGER_COUNT = "passenger_count"
    AGE_GROUP = "age_group"


@dataclass
class PersonalityContext:
    """Current context for personality selection"""
    event_metadata: Optional[Dict[str, Any]] = None
    location: Optional[Dict[str, Any]] = None
    datetime: datetime = field(default_factory=datetime.now)
    weather: Optional[Dict[str, Any]] = None
    user_preferences: Optional[UserPreferences] = None
    journey_type: Optional[str] = None
    passenger_info: Optional[Dict[str, Any]] = None
    special_occasion: Optional[str] = None
    user_mood: Optional[str] = None
    timezone: str = "UTC"


class DynamicPersonalitySystem:
    """Comprehensive system for dynamic personality selection and management"""
    
    def __init__(self):
        self.personality_engine = PersonalityEngine()
        self.venue_mapper = VenuePersonalityMapper()
        self.personality_registry: Dict[str, PersonalityMetadata] = {}
        self.event_personality_map: Dict[str, List[str]] = {}
        self.selection_history: List[Dict[str, Any]] = []
        self._initialize_registry()
        self._load_event_mappings()
    
    def _initialize_registry(self):
        """Initialize the personality registry with metadata"""
        
        # Base personalities with enhanced metadata
        self.personality_registry = {
            # Event-specific personalities
            "mickey_mouse": PersonalityMetadata(
                id="mickey_mouse",
                priority=95,
                event_types=["theme_park", "disney", "family_entertainment"],
                venues=["disneyland", "disney world", "magic kingdom"],
                age_groups=["child", "family"],
                time_ranges=[(6, 22)],  # Active during park hours
                exclusion_rules={"user_age": "adult_only"}
            ),
            
            "rock_dj": PersonalityMetadata(
                id="rock_dj",
                priority=85,
                event_types=["rock_concert", "music_festival", "metal_show"],
                venues=["red rocks", "msg", "forum"],
                time_ranges=[(16, 23)],  # Evening/night events
                user_moods=["excited", "energetic", "rebellious"],
                age_groups=["teen", "adult"]
            ),
            
            "broadway_star": PersonalityMetadata(
                id="broadway_star",
                priority=90,
                event_types=["theater", "musical", "broadway"],
                venues=["broadway", "lincoln center", "pantages"],
                time_ranges=[(18, 22)],  # Show times
                regions=["new_york", "los_angeles"],
                user_moods=["sophisticated", "artistic"]
            ),
            
            "sports_announcer": PersonalityMetadata(
                id="sports_announcer",
                priority=85,
                event_types=["sports", "football", "basketball", "baseball"],
                venues=["stadium", "arena", "ballpark"],
                days_of_week=[0, 5, 6],  # More common on weekends
                user_moods=["competitive", "team_spirit"]
            ),
            
            # Holiday personalities with date ranges
            "santa_claus": PersonalityMetadata(
                id=PersonalityType.SANTA,
                priority=100,  # Highest priority during season
                holidays=["christmas"],
                seasons=["winter"],
                weather_conditions=["snow", "cold"],
                time_ranges=[(0, 23)],  # All day during season
                age_groups=["child", "family"],
                special_occasions=["christmas_shopping", "holiday_lights"]
            ),
            
            "spooky_narrator": PersonalityMetadata(
                id=PersonalityType.HALLOWEEN_NARRATOR,
                priority=95,
                holidays=["halloween"],
                seasons=["fall"],
                time_ranges=[(18, 23)],  # Evening only
                weather_conditions=["foggy", "cloudy"],
                event_types=["haunted_house", "ghost_tour"],
                exclusion_rules={"passenger_type": "young_children"}
            ),
            
            "cupid": PersonalityMetadata(
                id=PersonalityType.CUPID,
                priority=90,
                holidays=["valentines"],
                special_occasions=["date_night", "anniversary", "proposal"],
                event_types=["romantic_dinner", "couples_event"],
                user_moods=["romantic", "loving"]
            ),
            
            # Regional personalities with location awareness
            "southern_belle": PersonalityMetadata(
                id=PersonalityType.SOUTHERN_CHARM,
                priority=80,
                regions=["south", "georgia", "louisiana", "tennessee"],
                weather_conditions=["warm", "humid"],
                time_ranges=[(6, 22)],
                user_moods=["relaxed", "hospitable"]
            ),
            
            "beach_guru": PersonalityMetadata(
                id=PersonalityType.BEACH_VIBES,
                priority=85,
                regions=["california", "florida", "hawaii"],
                event_types=["beach_party", "surf_competition", "luau"],
                weather_conditions=["sunny", "warm"],
                seasons=["summer"],
                user_moods=["relaxed", "carefree"]
            ),
            
            "mountain_guide": PersonalityMetadata(
                id=PersonalityType.MOUNTAIN_SAGE,
                priority=80,
                regions=["colorado", "utah", "montana", "wyoming"],
                event_types=["hiking", "skiing", "outdoor_adventure"],
                weather_conditions=["clear", "snow"],
                user_moods=["adventurous", "peaceful"]
            ),
            
            # Time-based personalities
            "morning_motivator": PersonalityMetadata(
                id="morning_motivator",
                priority=70,
                time_ranges=[(5, 9)],  # Early morning
                user_moods=["energetic", "motivated"],
                special_occasions=["workout", "commute"]
            ),
            
            "sunset_poet": PersonalityMetadata(
                id="sunset_poet",
                priority=75,
                time_ranges=[(17, 20)],  # Golden hour
                weather_conditions=["clear", "partly_cloudy"],
                user_moods=["reflective", "peaceful"],
                event_types=["scenic_drive", "sunset_viewing"]
            ),
            
            "night_owl": PersonalityMetadata(
                id="night_owl",
                priority=70,
                time_ranges=[(22, 4)],  # Late night
                event_types=["nightclub", "late_show", "midnight_movie"],
                user_moods=["adventurous", "night_person"]
            )
        }
    
    def _load_event_mappings(self):
        """Load detailed event type to personality mappings"""
        self.event_personality_map = {
            # Theme Parks
            "disney": ["mickey_mouse", "fairy_godmother", "adventure_guide"],
            "universal": ["movie_director", "action_hero", "wizard_guide"],
            "six_flags": ["thrill_seeker", "adventure_guide", "safety_sam"],
            
            # Concerts
            "rock_concert": ["rock_dj", "music_historian", "concert_buddy"],
            "classical_concert": ["classical_maestro", "culture_curator", "symphony_guide"],
            "country_concert": ["country_cowboy", "honky_tonk_hero", "southern_charm"],
            "jazz_concert": ["jazz_cat", "smooth_talker", "bebop_buddy"],
            "pop_concert": ["pop_star", "fan_friend", "dance_commander"],
            
            # Sports
            "nfl_game": ["football_fanatic", "sports_announcer", "tailgate_champion"],
            "nba_game": ["basketball_analyst", "court_side_companion", "hoops_historian"],
            "mlb_game": ["baseball_buff", "stats_master", "diamond_guide"],
            "hockey_game": ["hockey_enthusiast", "ice_expert", "puck_pal"],
            
            # Special Events
            "wedding": ["wedding_planner", "romance_guide", "celebration_host"],
            "graduation": ["proud_mentor", "achievement_celebrator", "future_guide"],
            "birthday": ["party_host", "celebration_expert", "birthday_buddy"],
            "reunion": ["memory_keeper", "nostalgia_guide", "reunion_host"]
        }
    
    async def select_personality(self, context: PersonalityContext) -> VoicePersonality:
        """
        Select the most appropriate personality based on comprehensive context analysis
        """
        try:
            # Calculate scores for each personality
            personality_scores = await self._calculate_personality_scores(context)
            
            # Get the highest scoring personality
            if personality_scores:
                selected_id = max(personality_scores.items(), key=lambda x: x[1])[0]
                
                # Log selection for analytics
                self._log_selection(selected_id, context, personality_scores)
                
                # Get full personality object
                return await self._get_personality_by_id(selected_id)
            
            # Fallback to default
            return self.personality_engine.get_contextual_personality(
                location=context.location,
                user_preferences=context.user_preferences,
                current_datetime=context.datetime
            )
            
        except Exception as e:
            logger.error(f"Error selecting personality: {e}")
            return self.personality_engine.personalities[PersonalityType.FRIENDLY_GUIDE]
    
    async def _calculate_personality_scores(
        self, 
        context: PersonalityContext
    ) -> Dict[str, float]:
        """Calculate scores for each personality based on context"""
        scores = defaultdict(float)
        
        for personality_id, metadata in self.personality_registry.items():
            # Start with base priority
            score = metadata.priority
            
            # Event type matching (highest weight)
            if context.event_metadata:
                event_type = self._extract_event_type(context.event_metadata)
                if event_type in metadata.event_types:
                    score += 30
                
                # Venue matching
                venue_name = context.event_metadata.get("venue", {}).get("name", "").lower()
                for venue in metadata.venues:
                    if venue in venue_name:
                        score += 25
                        break
            
            # Holiday matching (very high weight during active periods)
            if metadata.holidays:
                active_holiday = self._check_active_holiday(context.datetime, metadata.holidays)
                if active_holiday:
                    score += 40
            
            # Time of day matching
            current_hour = context.datetime.hour
            for time_range in metadata.time_ranges:
                if time_range[0] <= current_hour <= time_range[1]:
                    score += 15
                    break
            
            # Day of week matching
            if metadata.days_of_week and context.datetime.weekday() in metadata.days_of_week:
                score += 10
            
            # Weather matching
            if context.weather and metadata.weather_conditions:
                weather_condition = context.weather.get("condition", "").lower()
                if any(cond in weather_condition for cond in metadata.weather_conditions):
                    score += 10
            
            # Regional matching
            if context.location and metadata.regions:
                location_region = self._extract_region(context.location)
                if location_region in metadata.regions:
                    score += 20
            
            # User mood matching
            if context.user_mood and context.user_mood in metadata.user_moods:
                score += 15
            
            # Special occasion matching
            if context.special_occasion and context.special_occasion in metadata.special_occasions:
                score += 25
            
            # Age group matching
            if context.passenger_info:
                age_group = self._determine_age_group(context.passenger_info)
                if age_group in metadata.age_groups:
                    score += 15
            
            # Apply exclusion rules
            if self._check_exclusions(metadata.exclusion_rules, context):
                score = 0  # Exclude this personality
            
            # User preference boost
            if (context.user_preferences and 
                context.user_preferences.preferred_voice_personality == personality_id):
                score += 20
            
            scores[personality_id] = score
        
        return dict(scores)
    
    def _extract_event_type(self, event_metadata: Dict[str, Any]) -> str:
        """Extract normalized event type from metadata"""
        # Check classifications
        classifications = event_metadata.get("classifications", [])
        if classifications:
            segment = classifications[0].get("segment", "").lower()
            genre = classifications[0].get("genre", "").lower()
            
            # Map to our event types
            if "disney" in event_metadata.get("name", "").lower():
                return "disney"
            elif segment == "sports":
                return f"{genre}_game" if genre else "sports"
            elif segment == "music":
                return f"{genre}_concert" if genre else "concert"
            elif segment == "arts & theatre":
                return "theater"
        
        # Check event name for clues
        name = event_metadata.get("name", "").lower()
        if "wedding" in name:
            return "wedding"
        elif "birthday" in name:
            return "birthday"
        elif "graduation" in name:
            return "graduation"
        
        return "general_event"
    
    def _check_active_holiday(self, current_datetime: datetime, holidays: List[str]) -> Optional[str]:
        """Check if any holidays are currently active"""
        current_date = current_datetime.date()
        
        # Get holiday calendar from personality engine
        holiday_calendar = self.personality_engine.holiday_calendar
        
        for holiday in holidays:
            if holiday in holiday_calendar:
                date_range = holiday_calendar[holiday]
                if len(date_range) >= 2 and date_range[0] <= current_date <= date_range[1]:
                    return holiday
        
        return None
    
    def _extract_region(self, location: Dict[str, Any]) -> str:
        """Extract region from location data"""
        state = location.get("state", "").lower()
        
        # Map states to regions
        region_map = {
            "south": ["georgia", "alabama", "mississippi", "louisiana", "tennessee", 
                     "kentucky", "north carolina", "south carolina", "virginia", "arkansas"],
            "california": ["california"],
            "florida": ["florida"],
            "hawaii": ["hawaii"],
            "colorado": ["colorado"],
            "utah": ["utah"],
            "montana": ["montana"],
            "wyoming": ["wyoming"],
            "texas": ["texas"],
            "new_york": ["new york"],
            "los_angeles": ["california"]  # Special case for LA
        }
        
        for region, states in region_map.items():
            if state in states:
                return region
        
        return "general"
    
    def _determine_age_group(self, passenger_info: Dict[str, Any]) -> str:
        """Determine primary age group from passenger info"""
        passengers = passenger_info.get("passengers", [])
        
        if any(p.get("age", 100) < 12 for p in passengers):
            return "family"
        elif all(p.get("age", 30) < 25 for p in passengers):
            return "teen"
        else:
            return "adult"
    
    def _check_exclusions(self, exclusion_rules: Dict[str, Any], context: PersonalityContext) -> bool:
        """Check if any exclusion rules apply"""
        if not exclusion_rules:
            return False
        
        # Check user age exclusions
        if "user_age" in exclusion_rules and context.passenger_info:
            age_group = self._determine_age_group(context.passenger_info)
            if exclusion_rules["user_age"] == "adult_only" and age_group == "family":
                return True
        
        # Check passenger type exclusions
        if "passenger_type" in exclusion_rules and context.passenger_info:
            if (exclusion_rules["passenger_type"] == "young_children" and 
                any(p.get("age", 100) < 8 for p in context.passenger_info.get("passengers", []))):
                return True
        
        return False
    
    async def _get_personality_by_id(self, personality_id: str) -> VoicePersonality:
        """Get full personality object by ID"""
        # Check base personalities
        if personality_id in self.personality_engine.personalities:
            return self.personality_engine.personalities[personality_id]
        
        # Check extended personalities
        extended = load_extended_personalities()
        if personality_id in extended:
            return extended[personality_id]
        
        # Create custom personality if needed
        return await self._create_custom_personality(personality_id)
    
    async def _create_custom_personality(self, personality_id: str) -> VoicePersonality:
        """Create a custom personality for special cases"""
        # Map custom IDs to personality configurations
        custom_map = {
            "mickey_mouse": VoicePersonality(
                id="mickey_mouse",
                name="Mickey Mouse",
                description="The one and only Mickey Mouse, here to make your Disney trip magical!",
                voice_id="en-US-Neural2-H",  # High-pitched, cheerful voice
                speaking_style={
                    "pitch": 3,
                    "speed": 1.1,
                    "emphasis": "cheerful",
                    "enthusiasm": 1.0
                },
                vocabulary_style="disney_magic",
                catchphrases=[
                    "Oh boy! Ha-ha!",
                    "Hot dog!",
                    "See ya real soon!",
                    "Welcome to the most magical place on Earth!"
                ],
                topics_of_expertise=["disney", "magic", "fun", "imagination"],
                emotion_range={"joy": 1.0, "excitement": 0.95, "wonder": 0.9},
                age_appropriate=["all"]
            ),
            
            "rock_dj": VoicePersonality(
                id="rock_dj",
                name="Axel Thunder",
                description="Your high-energy rock concert companion",
                voice_id="en-US-Neural2-F",
                speaking_style={
                    "pitch": 0,
                    "speed": 1.15,
                    "emphasis": "energetic",
                    "intensity": 0.9
                },
                vocabulary_style="rock_slang",
                catchphrases=[
                    "Let's rock and roll!",
                    "Crank it up to 11!",
                    "This is gonna be EPIC!",
                    "Rock on!"
                ],
                topics_of_expertise=["rock_music", "concerts", "bands", "music_history"],
                emotion_range={"excitement": 0.95, "energy": 1.0, "rebellion": 0.8},
                age_appropriate=["teen", "adult"]
            ),
            
            "broadway_star": VoicePersonality(
                id="broadway_star",
                name="Victoria Stage",
                description="Your theatrical guide to the Great White Way",
                voice_id="en-US-Neural2-G",
                speaking_style={
                    "pitch": 1,
                    "speed": 1.05,
                    "emphasis": "theatrical",
                    "drama": 0.9
                },
                vocabulary_style="theatrical",
                catchphrases=[
                    "The show must go on!",
                    "Break a leg!",
                    "It's showtime!",
                    "Bravo! Encore!"
                ],
                topics_of_expertise=["theater", "broadway", "musicals", "performances"],
                emotion_range={"drama": 0.9, "elegance": 0.85, "passion": 0.95},
                age_appropriate=["all"]
            )
        }
        
        if personality_id in custom_map:
            return custom_map[personality_id]
        
        # Default fallback
        return self.personality_engine.personalities[PersonalityType.FRIENDLY_GUIDE]
    
    def _log_selection(self, selected_id: str, context: PersonalityContext, scores: Dict[str, float]):
        """Log personality selection for analytics"""
        selection_record = {
            "timestamp": context.datetime.isoformat(),
            "selected_personality": selected_id,
            "scores": scores,
            "context": {
                "event_type": self._extract_event_type(context.event_metadata) if context.event_metadata else None,
                "location": context.location.get("state") if context.location else None,
                "time_of_day": context.datetime.hour,
                "day_of_week": context.datetime.weekday(),
                "user_mood": context.user_mood,
                "special_occasion": context.special_occasion
            }
        }
        
        self.selection_history.append(selection_record)
        
        # Keep only last 1000 selections
        if len(self.selection_history) > 1000:
            self.selection_history = self.selection_history[-1000:]
        
        logger.info(f"Selected personality: {selected_id} with score: {scores.get(selected_id, 0)}")
    
    async def get_personality_suggestions(
        self, 
        context: PersonalityContext, 
        count: int = 3
    ) -> List[Tuple[VoicePersonality, float]]:
        """Get top personality suggestions with scores"""
        scores = await self._calculate_personality_scores(context)
        
        # Sort by score
        sorted_personalities = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:count]
        
        # Get full personality objects
        suggestions = []
        for personality_id, score in sorted_personalities:
            personality = await self._get_personality_by_id(personality_id)
            suggestions.append((personality, score))
        
        return suggestions
    
    def get_analytics(self) -> Dict[str, Any]:
        """Get analytics on personality selection patterns"""
        if not self.selection_history:
            return {"message": "No selection history available"}
        
        # Analyze selection patterns
        personality_counts = defaultdict(int)
        time_distribution = defaultdict(int)
        context_patterns = defaultdict(lambda: defaultdict(int))
        
        for record in self.selection_history:
            personality_counts[record["selected_personality"]] += 1
            time_distribution[record["context"]["time_of_day"]] += 1
            
            if record["context"]["event_type"]:
                context_patterns["event_types"][record["context"]["event_type"]] += 1
            if record["context"]["user_mood"]:
                context_patterns["moods"][record["context"]["user_mood"]] += 1
        
        return {
            "total_selections": len(self.selection_history),
            "personality_distribution": dict(personality_counts),
            "time_distribution": dict(time_distribution),
            "context_patterns": dict(context_patterns),
            "most_popular": max(personality_counts.items(), key=lambda x: x[1])[0] if personality_counts else None
        }


# Singleton instance
dynamic_personality_system = DynamicPersonalitySystem()