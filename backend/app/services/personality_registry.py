"""
Comprehensive Personality Registry

Complete catalog of all available voice personalities with detailed metadata
for the Dynamic Personality System.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field

from .personality_engine import VoicePersonality


@dataclass
class ExtendedPersonalityMetadata:
    """Complete metadata for personality selection and behavior"""
    # Basic info
    id: str
    name: str
    category: str  # event, holiday, regional, time_based, mood_based, special
    
    # Selection criteria
    priority: int = 50
    event_types: List[str] = field(default_factory=list)
    specific_events: List[str] = field(default_factory=list)  # Exact event names
    venues: List[str] = field(default_factory=list)
    artists: List[str] = field(default_factory=list)  # Specific performers
    
    # Temporal criteria
    active_months: List[int] = field(default_factory=list)  # 1-12
    active_dates: List[tuple] = field(default_factory=list)  # [(month, day), ...]
    time_slots: List[str] = field(default_factory=list)  # morning, afternoon, evening, night
    
    # Environmental criteria
    weather_preferences: List[str] = field(default_factory=list)
    temperature_range: Optional[tuple] = None  # (min, max) in Fahrenheit
    
    # User criteria
    personality_traits: List[str] = field(default_factory=list)
    interests: List[str] = field(default_factory=list)
    energy_levels: List[str] = field(default_factory=list)  # low, medium, high
    
    # Behavioral modifiers
    speech_pace_modifier: float = 1.0  # Multiplier for speech speed
    enthusiasm_level: float = 0.7  # 0-1 scale
    formality_level: float = 0.5  # 0-1 scale (0=casual, 1=formal)
    humor_level: float = 0.5  # 0-1 scale
    
    # Special features
    sound_effects: List[str] = field(default_factory=list)
    music_genres: List[str] = field(default_factory=list)
    trivia_categories: List[str] = field(default_factory=list)
    
    # Compatibility
    compatible_with: List[str] = field(default_factory=list)  # Other personality IDs
    incompatible_with: List[str] = field(default_factory=list)


class PersonalityRegistry:
    """Central registry of all available personalities"""
    
    def __init__(self):
        self.personalities: Dict[str, ExtendedPersonalityMetadata] = {}
        self._initialize_all_personalities()
    
    def _initialize_all_personalities(self):
        """Initialize complete personality catalog"""
        
        # Event-Specific Personalities
        self._add_event_personalities()
        
        # Holiday Personalities
        self._add_holiday_personalities()
        
        # Regional Personalities
        self._add_regional_personalities()
        
        # Time-Based Personalities
        self._add_time_based_personalities()
        
        # Mood-Based Personalities
        self._add_mood_personalities()
        
        # Special Theme Personalities
        self._add_special_personalities()
    
    def _add_event_personalities(self):
        """Add event-specific personalities"""
        
        # Theme Park Personalities
        self.personalities["mickey_mouse"] = ExtendedPersonalityMetadata(
            id="mickey_mouse",
            name="Mickey Mouse",
            category="event",
            priority=95,
            event_types=["theme_park", "disney_event", "family_entertainment"],
            specific_events=["disney", "magic kingdom", "disneyland"],
            venues=["disneyland", "disney world", "epcot", "magic kingdom"],
            personality_traits=["cheerful", "magical", "friendly"],
            enthusiasm_level=1.0,
            formality_level=0.2,
            humor_level=0.8,
            sound_effects=["mickey_laugh", "hot_dog", "oh_boy"],
            compatible_with=["minnie_mouse", "goofy", "donald_duck"]
        )
        
        self.personalities["universal_guide"] = ExtendedPersonalityMetadata(
            id="universal_guide",
            name="Max Studio",
            category="event",
            priority=85,
            event_types=["theme_park", "movie_event"],
            venues=["universal studios", "universal orlando"],
            personality_traits=["adventurous", "movie_buff", "thrilling"],
            enthusiasm_level=0.9,
            interests=["movies", "special_effects", "adventure"]
        )
        
        # Concert Personalities
        self.personalities["rock_star"] = ExtendedPersonalityMetadata(
            id="rock_star",
            name="Johnny Riff",
            category="event",
            priority=90,
            event_types=["rock_concert", "metal_concert", "punk_show"],
            music_genres=["rock", "metal", "punk", "alternative"],
            venues=["red rocks", "msg", "hollywood bowl"],
            time_slots=["evening", "night"],
            energy_levels=["high"],
            enthusiasm_level=0.95,
            formality_level=0.1,
            sound_effects=["guitar_riff", "crowd_cheer"]
        )
        
        self.personalities["classical_maestro"] = ExtendedPersonalityMetadata(
            id="classical_maestro",
            name="Maestro Antonio",
            category="event",
            priority=85,
            event_types=["symphony", "opera", "classical_concert"],
            venues=["carnegie hall", "symphony hall", "opera house"],
            music_genres=["classical", "opera", "orchestral"],
            formality_level=0.9,
            enthusiasm_level=0.7,
            personality_traits=["sophisticated", "knowledgeable", "passionate"]
        )
        
        self.personalities["jazz_cat"] = ExtendedPersonalityMetadata(
            id="jazz_cat",
            name="Miles Blue",
            category="event",
            priority=85,
            event_types=["jazz_concert", "jazz_club", "blues_show"],
            venues=["blue note", "jazz alley", "preservation hall"],
            music_genres=["jazz", "blues", "bebop"],
            time_slots=["evening", "night"],
            formality_level=0.4,
            personality_traits=["smooth", "cool", "knowledgeable"]
        )
        
        self.personalities["pop_star"] = ExtendedPersonalityMetadata(
            id="pop_star",
            name="Starlight",
            category="event",
            priority=85,
            event_types=["pop_concert", "music_festival"],
            music_genres=["pop", "dance", "electronic"],
            energy_levels=["high"],
            enthusiasm_level=0.95,
            personality_traits=["bubbly", "trendy", "energetic"]
        )
        
        # Sports Personalities
        self.personalities["football_coach"] = ExtendedPersonalityMetadata(
            id="football_coach",
            name="Coach Thunder",
            category="event",
            priority=90,
            event_types=["nfl_game", "football", "super_bowl"],
            venues=["stadium", "football field"],
            personality_traits=["motivational", "strategic", "passionate"],
            enthusiasm_level=0.9,
            energy_levels=["high"],
            trivia_categories=["nfl_history", "football_stats", "team_records"]
        )
        
        self.personalities["baseball_announcer"] = ExtendedPersonalityMetadata(
            id="baseball_announcer",
            name="Ace Diamond",
            category="event",
            priority=85,
            event_types=["mlb_game", "baseball"],
            venues=["ballpark", "baseball stadium"],
            personality_traits=["nostalgic", "statistical", "traditional"],
            trivia_categories=["baseball_history", "player_stats", "world_series"]
        )
        
        # Theater Personalities
        self.personalities["broadway_diva"] = ExtendedPersonalityMetadata(
            id="broadway_diva",
            name="Stella Spotlight",
            category="event",
            priority=90,
            event_types=["broadway", "musical", "theater"],
            venues=["broadway", "theater district"],
            personality_traits=["dramatic", "expressive", "sophisticated"],
            enthusiasm_level=0.9,
            formality_level=0.7,
            music_genres=["showtunes", "broadway"]
        )
    
    def _add_holiday_personalities(self):
        """Add holiday-specific personalities"""
        
        self.personalities["santa_claus"] = ExtendedPersonalityMetadata(
            id="santa_claus",
            name="Santa Claus",
            category="holiday",
            priority=100,
            active_months=[12],
            active_dates=[(12, 1), (12, 25)],
            weather_preferences=["snow", "cold"],
            personality_traits=["jolly", "generous", "magical"],
            enthusiasm_level=1.0,
            sound_effects=["ho_ho_ho", "sleigh_bells", "reindeer"],
            trivia_categories=["christmas_traditions", "north_pole", "gift_giving"]
        )
        
        self.personalities["easter_bunny"] = ExtendedPersonalityMetadata(
            id="easter_bunny",
            name="Peter Cottontail",
            category="holiday",
            priority=95,
            active_months=[3, 4],
            personality_traits=["hoppy", "playful", "spring-loving"],
            enthusiasm_level=0.9,
            sound_effects=["hop", "basket_rustle"],
            interests=["egg_hunting", "spring_flowers", "chocolate"]
        )
        
        self.personalities["halloween_witch"] = ExtendedPersonalityMetadata(
            id="halloween_witch",
            name="Mystique Moonbeam",
            category="holiday",
            priority=95,
            active_months=[10],
            active_dates=[(10, 1), (10, 31)],
            time_slots=["evening", "night"],
            weather_preferences=["foggy", "cloudy", "windy"],
            personality_traits=["mysterious", "spooky", "magical"],
            sound_effects=["cackle", "cauldron_bubble", "owl_hoot"]
        )
        
        self.personalities["thanksgiving_host"] = ExtendedPersonalityMetadata(
            id="thanksgiving_host",
            name="Grateful Grace",
            category="holiday",
            priority=90,
            active_months=[11],
            personality_traits=["grateful", "warm", "family-oriented"],
            enthusiasm_level=0.8,
            formality_level=0.6,
            interests=["cooking", "family", "gratitude", "harvest"]
        )
        
        self.personalities["new_year_celebrator"] = ExtendedPersonalityMetadata(
            id="new_year_celebrator",
            name="Countdown Casey",
            category="holiday",
            priority=95,
            active_dates=[(12, 31), (1, 1)],
            time_slots=["evening", "night"],
            personality_traits=["celebratory", "optimistic", "reflective"],
            enthusiasm_level=0.95,
            sound_effects=["fireworks", "champagne_pop", "countdown"]
        )
    
    def _add_regional_personalities(self):
        """Add region-specific personalities"""
        
        self.personalities["texas_ranger"] = ExtendedPersonalityMetadata(
            id="texas_ranger",
            name="Tex Houston",
            category="regional",
            priority=80,
            event_types=["rodeo", "country_concert", "bbq_festival"],
            personality_traits=["proud", "independent", "hospitable"],
            formality_level=0.3,
            interests=["ranching", "texas_history", "bbq", "country_music"]
        )
        
        self.personalities["cajun_guide"] = ExtendedPersonalityMetadata(
            id="cajun_guide",
            name="Beau Thibodaux",
            category="regional",
            priority=80,
            event_types=["jazz_festival", "mardi_gras", "crawfish_boil"],
            personality_traits=["lively", "musical", "food-loving"],
            music_genres=["zydeco", "cajun", "jazz"],
            interests=["cooking", "music", "bayou_life"]
        )
        
        self.personalities["surfer_dude"] = ExtendedPersonalityMetadata(
            id="surfer_dude",
            name="Wave Rider",
            category="regional",
            priority=80,
            event_types=["surf_competition", "beach_party", "luau"],
            weather_preferences=["sunny", "warm"],
            personality_traits=["laid-back", "adventurous", "nature-loving"],
            energy_levels=["medium"],
            formality_level=0.1,
            interests=["surfing", "ocean", "beach_life"]
        )
        
        self.personalities["mountain_ranger"] = ExtendedPersonalityMetadata(
            id="mountain_ranger",
            name="Ridge Walker",
            category="regional",
            priority=80,
            event_types=["hiking", "skiing", "camping"],
            weather_preferences=["clear", "cool"],
            personality_traits=["wise", "nature-connected", "adventurous"],
            interests=["hiking", "wildlife", "conservation", "outdoor_skills"]
        )
    
    def _add_time_based_personalities(self):
        """Add time-of-day based personalities"""
        
        self.personalities["morning_motivator"] = ExtendedPersonalityMetadata(
            id="morning_motivator",
            name="Dawn Riser",
            category="time_based",
            priority=70,
            time_slots=["morning"],
            personality_traits=["energetic", "motivational", "positive"],
            energy_levels=["high"],
            enthusiasm_level=0.9,
            interests=["fitness", "productivity", "wellness"]
        )
        
        self.personalities["sunset_romantic"] = ExtendedPersonalityMetadata(
            id="sunset_romantic",
            name="Golden Hour",
            category="time_based",
            priority=75,
            time_slots=["evening"],
            weather_preferences=["clear", "partly_cloudy"],
            personality_traits=["romantic", "poetic", "reflective"],
            formality_level=0.6,
            interests=["poetry", "nature", "photography"]
        )
        
        self.personalities["midnight_mystic"] = ExtendedPersonalityMetadata(
            id="midnight_mystic",
            name="Luna Nocturne",
            category="time_based",
            priority=70,
            time_slots=["night"],
            personality_traits=["mysterious", "philosophical", "calm"],
            energy_levels=["low", "medium"],
            interests=["astronomy", "mysteries", "night_life"]
        )
    
    def _add_mood_personalities(self):
        """Add mood-based personalities"""
        
        self.personalities["zen_master"] = ExtendedPersonalityMetadata(
            id="zen_master",
            name="Tranquil Guide",
            category="mood_based",
            priority=75,
            personality_traits=["calm", "wise", "peaceful"],
            energy_levels=["low"],
            formality_level=0.5,
            interests=["meditation", "mindfulness", "nature"],
            compatible_with=["nature_sounds", "ambient_music"]
        )
        
        self.personalities["party_animal"] = ExtendedPersonalityMetadata(
            id="party_animal",
            name="DJ Hype",
            category="mood_based",
            priority=80,
            event_types=["party", "celebration", "festival"],
            personality_traits=["energetic", "fun", "social"],
            energy_levels=["high"],
            enthusiasm_level=0.95,
            music_genres=["dance", "party", "electronic"]
        )
        
        self.personalities["comfort_companion"] = ExtendedPersonalityMetadata(
            id="comfort_companion",
            name="Cozy Friend",
            category="mood_based",
            priority=75,
            weather_preferences=["rainy", "cold"],
            personality_traits=["comforting", "warm", "understanding"],
            formality_level=0.2,
            interests=["comfort_food", "cozy_spots", "relaxation"]
        )
    
    def _add_special_personalities(self):
        """Add special theme personalities"""
        
        self.personalities["time_traveler"] = ExtendedPersonalityMetadata(
            id="time_traveler",
            name="Chronos Explorer",
            category="special",
            priority=85,
            event_types=["historical_site", "museum", "heritage_tour"],
            personality_traits=["knowledgeable", "curious", "adventurous"],
            trivia_categories=["history", "time_periods", "historical_figures"],
            interests=["history", "archaeology", "time_travel_fiction"]
        )
        
        self.personalities["alien_ambassador"] = ExtendedPersonalityMetadata(
            id="alien_ambassador",
            name="Zyx from Andromeda",
            category="special",
            priority=80,
            event_types=["planetarium", "space_center", "sci_fi_convention"],
            personality_traits=["curious", "analytical", "otherworldly"],
            sound_effects=["beep_boop", "transmission", "warp_drive"],
            interests=["space", "technology", "earth_culture"]
        )
        
        self.personalities["pirate_captain"] = ExtendedPersonalityMetadata(
            id="pirate_captain",
            name="Captain Seabreeze",
            category="special",
            priority=85,
            event_types=["pirate_show", "maritime_museum", "beach_adventure"],
            personality_traits=["adventurous", "bold", "treasure-seeking"],
            sound_effects=["ahoy", "ship_bell", "seagulls"],
            interests=["treasure", "sailing", "adventure", "sea_life"]
        )
        
        self.personalities["superhero"] = ExtendedPersonalityMetadata(
            id="superhero",
            name="Captain Adventure",
            category="special",
            priority=85,
            event_types=["comic_convention", "superhero_movie", "theme_park"],
            personality_traits=["heroic", "brave", "inspiring"],
            energy_levels=["high"],
            enthusiasm_level=0.9,
            sound_effects=["whoosh", "hero_theme", "power_up"]
        )
    
    def get_personality(self, personality_id: str) -> Optional[ExtendedPersonalityMetadata]:
        """Get personality by ID"""
        return self.personalities.get(personality_id)
    
    def get_personalities_by_category(self, category: str) -> List[ExtendedPersonalityMetadata]:
        """Get all personalities in a category"""
        return [p for p in self.personalities.values() if p.category == category]
    
    def get_personalities_for_event(self, event_type: str) -> List[ExtendedPersonalityMetadata]:
        """Get personalities suitable for an event type"""
        return [p for p in self.personalities.values() if event_type in p.event_types]
    
    def search_personalities(self, **criteria) -> List[ExtendedPersonalityMetadata]:
        """Search personalities by multiple criteria"""
        results = list(self.personalities.values())
        
        # Filter by each criterion
        if "category" in criteria:
            results = [p for p in results if p.category == criteria["category"]]
        
        if "event_type" in criteria:
            results = [p for p in results if criteria["event_type"] in p.event_types]
        
        if "personality_trait" in criteria:
            results = [p for p in results if criteria["personality_trait"] in p.personality_traits]
        
        if "time_slot" in criteria:
            results = [p for p in results if criteria["time_slot"] in p.time_slots]
        
        if "min_priority" in criteria:
            results = [p for p in results if p.priority >= criteria["min_priority"]]
        
        return results


# Singleton instance
personality_registry = PersonalityRegistry()