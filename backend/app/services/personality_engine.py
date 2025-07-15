"""
Dynamic Voice Personality Engine

This service manages voice personalities that adapt based on:
- Location (regional accents, local experts)
- Season/holidays (Santa during Christmas, spooky during Halloween)
- User preferences (comedy, educational, adventurous)
- Special events (match event performer styles)
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, date
from enum import Enum
import logging
from dataclasses import dataclass
import json

from ..core.cache import cache_manager
from ..models.user import UserPreferences

logger = logging.getLogger(__name__)


class PersonalityType(str, Enum):
    FRIENDLY_GUIDE = "friendly_guide"
    LOCAL_EXPERT = "local_expert"
    HISTORIAN = "historian"
    ADVENTURER = "adventurer"
    COMEDIAN = "comedian"
    SANTA = "santa"
    HALLOWEEN_NARRATOR = "halloween_narrator"
    CUPID = "cupid"
    LEPRECHAUN = "leprechaun"
    PATRIOT = "patriot"
    HARVEST_GUIDE = "harvest_guide"
    INSPIRATIONAL = "inspirational"
    SOUTHERN_CHARM = "southern_charm"
    NEW_ENGLAND_SCHOLAR = "new_england_scholar"
    MIDWEST_NEIGHBOR = "midwest_neighbor"
    WEST_COAST_COOL = "west_coast_cool"
    MOUNTAIN_SAGE = "mountain_sage"
    TEXAS_RANGER = "texas_ranger"
    JAZZ_STORYTELLER = "jazz_storyteller"
    BEACH_VIBES = "beach_vibes"


@dataclass
class VoicePersonality:
    """Defines a voice personality with its characteristics"""
    id: str
    name: str
    description: str
    voice_id: str  # Google Cloud TTS voice ID
    speaking_style: Dict[str, any]  # pitch, speed, emphasis patterns
    vocabulary_style: str  # formal, casual, regional
    catchphrases: List[str]
    topics_of_expertise: List[str]
    emotion_range: Dict[str, float]  # happiness, excitement, mystery, etc.
    regional_accent: Optional[str] = None
    age_appropriate: List[str] = None  # kid, teen, adult, all
    active_seasons: Optional[List[str]] = None  # spring, summer, fall, winter
    active_holidays: Optional[List[str]] = None
    active_hours: Optional[Tuple[int, int]] = None  # (start_hour, end_hour)


class PersonalityEngine:
    """Manages dynamic voice personalities based on context"""
    
    def __init__(self):
        self.personalities = self._load_personalities()
        self.holiday_calendar = self._load_holiday_calendar()
        
    def _load_personalities(self) -> Dict[str, VoicePersonality]:
        """Load all voice personality definitions"""
        personalities = {
            PersonalityType.FRIENDLY_GUIDE: VoicePersonality(
                id=PersonalityType.FRIENDLY_GUIDE,
                name="Alex the Guide",
                description="Your friendly road trip companion with enthusiasm for discovery",
                voice_id="en-US-Neural2-J",  # Warm, friendly voice
                speaking_style={
                    "pitch": 0,
                    "speed": 1.0,
                    "emphasis": "moderate",
                    "warmth": 0.8
                },
                vocabulary_style="casual_friendly",
                catchphrases=[
                    "What an amazing view!",
                    "Did you know...",
                    "Let's explore!",
                    "This is one of my favorite spots"
                ],
                topics_of_expertise=["general", "travel", "fun_facts"],
                emotion_range={"happiness": 0.8, "excitement": 0.7, "calm": 0.6},
                age_appropriate=["all"]
            ),
            
            PersonalityType.LOCAL_EXPERT: VoicePersonality(
                id=PersonalityType.LOCAL_EXPERT,
                name="Local Guide",
                description="A knowledgeable local with insider tips and regional flavor",
                voice_id="en-US-Neural2-A",  # Will be dynamically selected based on region
                speaking_style={
                    "pitch": -0.5,
                    "speed": 0.95,
                    "emphasis": "conversational",
                    "authenticity": 0.9
                },
                vocabulary_style="regional_casual",
                catchphrases=[
                    "Folks around here say...",
                    "If you ask me...",
                    "The locals know...",
                    "Back in my day..."
                ],
                topics_of_expertise=["local_history", "hidden_gems", "regional_culture"],
                emotion_range={"pride": 0.8, "nostalgia": 0.7, "friendliness": 0.9},
                age_appropriate=["teen", "adult"]
            ),
            
            PersonalityType.HISTORIAN: VoicePersonality(
                id=PersonalityType.HISTORIAN,
                name="Professor History",
                description="A Ken Burns-style narrator bringing history to life",
                voice_id="en-US-Neural2-D",  # Deep, authoritative voice
                speaking_style={
                    "pitch": -2,
                    "speed": 0.9,
                    "emphasis": "dramatic_pauses",
                    "gravitas": 0.9
                },
                vocabulary_style="formal_educational",
                catchphrases=[
                    "In the annals of history...",
                    "Picture if you will...",
                    "The year was...",
                    "History remembers..."
                ],
                topics_of_expertise=["history", "culture", "significant_events"],
                emotion_range={"reverence": 0.8, "wonder": 0.7, "solemnity": 0.6},
                age_appropriate=["teen", "adult"]
            ),
            
            PersonalityType.ADVENTURER: VoicePersonality(
                id=PersonalityType.ADVENTURER,
                name="Max Adventure",
                description="High-energy explorer with Bear Grylls enthusiasm",
                voice_id="en-US-Neural2-F",  # Energetic, dynamic voice
                speaking_style={
                    "pitch": 1,
                    "speed": 1.15,
                    "emphasis": "high_energy",
                    "intensity": 0.9
                },
                vocabulary_style="action_packed",
                catchphrases=[
                    "Adventure awaits!",
                    "This is incredible!",
                    "Let's push forward!",
                    "Nature at its finest!"
                ],
                topics_of_expertise=["nature", "outdoor_activities", "challenges"],
                emotion_range={"excitement": 0.95, "courage": 0.9, "enthusiasm": 1.0},
                age_appropriate=["kid", "teen", "adult"]
            ),
            
            PersonalityType.COMEDIAN: VoicePersonality(
                id=PersonalityType.COMEDIAN,
                name="Chuckles McGee",
                description="Family-friendly comedian keeping spirits high",
                voice_id="en-US-Neural2-H",  # Playful, expressive voice
                speaking_style={
                    "pitch": 0.5,
                    "speed": 1.05,
                    "emphasis": "comedic_timing",
                    "playfulness": 0.9
                },
                vocabulary_style="humorous",
                catchphrases=[
                    "Here's a good one...",
                    "Why did the...",
                    "That reminds me of a joke...",
                    "Buckle up for this one!"
                ],
                topics_of_expertise=["jokes", "puns", "funny_observations"],
                emotion_range={"humor": 0.95, "playfulness": 0.9, "joy": 0.85},
                age_appropriate=["kid", "teen", "adult"]
            ),
            
            # Holiday Personalities
            PersonalityType.SANTA: VoicePersonality(
                id=PersonalityType.SANTA,
                name="Santa Claus",
                description="Jolly Santa spreading Christmas cheer",
                voice_id="en-US-Neural2-D",  # Deep, warm voice
                speaking_style={
                    "pitch": -3,
                    "speed": 0.9,
                    "emphasis": "jolly",
                    "warmth": 1.0
                },
                vocabulary_style="christmas_jolly",
                catchphrases=[
                    "Ho ho ho!",
                    "Merry Christmas!",
                    "Have you been good?",
                    "Christmas magic is in the air!"
                ],
                topics_of_expertise=["christmas", "gifts", "holiday_traditions"],
                emotion_range={"joy": 1.0, "warmth": 0.95, "magic": 0.9},
                age_appropriate=["kid", "teen", "adult"],
                active_seasons=["winter"],
                active_holidays=["christmas"]
            ),
            
            PersonalityType.HALLOWEEN_NARRATOR: VoicePersonality(
                id=PersonalityType.HALLOWEEN_NARRATOR,
                name="The Crypt Keeper",
                description="Spooky storyteller for Halloween thrills",
                voice_id="en-US-Neural2-C",  # Mysterious voice
                speaking_style={
                    "pitch": -1,
                    "speed": 0.85,
                    "emphasis": "mysterious",
                    "spookiness": 0.9
                },
                vocabulary_style="gothic_mysterious",
                catchphrases=[
                    "Listen... if you dare...",
                    "On a night like this...",
                    "The spirits are restless...",
                    "Beware..."
                ],
                topics_of_expertise=["ghost_stories", "haunted_places", "mysteries"],
                emotion_range={"mystery": 0.95, "suspense": 0.9, "thrill": 0.85},
                age_appropriate=["teen", "adult"],
                active_seasons=["fall"],
                active_holidays=["halloween"],
                active_hours=(18, 23)  # Evening only
            ),
            
            # Regional Personalities
            PersonalityType.SOUTHERN_CHARM: VoicePersonality(
                id=PersonalityType.SOUTHERN_CHARM,
                name="Belle Southern",
                description="Southern hospitality and charm",
                voice_id="en-US-Neural2-G",  # Southern accent
                speaking_style={
                    "pitch": 0.5,
                    "speed": 0.9,
                    "emphasis": "melodic",
                    "hospitality": 0.95
                },
                vocabulary_style="southern_gracious",
                catchphrases=[
                    "Well, bless your heart!",
                    "Y'all come see this!",
                    "Sweet as pecan pie!",
                    "Now, honey..."
                ],
                topics_of_expertise=["southern_culture", "hospitality", "regional_food"],
                emotion_range={"warmth": 0.95, "grace": 0.9, "friendliness": 1.0},
                regional_accent="southern",
                age_appropriate=["all"]
            ),
            
            PersonalityType.TEXAS_RANGER: VoicePersonality(
                id=PersonalityType.TEXAS_RANGER,
                name="Tex Walker",
                description="Rugged Texas personality with frontier spirit",
                voice_id="en-US-Neural2-B",  # Deep Texas drawl
                speaking_style={
                    "pitch": -2,
                    "speed": 0.85,
                    "emphasis": "strong",
                    "confidence": 0.95
                },
                vocabulary_style="texas_frontier",
                catchphrases=[
                    "Everything's bigger in Texas!",
                    "Yeehaw!",
                    "Now that's Texas-sized!",
                    "Remember the Alamo!"
                ],
                topics_of_expertise=["texas_history", "ranching", "frontier_life"],
                emotion_range={"pride": 0.95, "strength": 0.9, "independence": 0.9},
                regional_accent="texas",
                age_appropriate=["teen", "adult"]
            )
        }
        
        return personalities
    
    def _load_holiday_calendar(self) -> Dict[str, List[date]]:
        """Load holiday dates for personality activation"""
        current_year = datetime.now().year
        return {
            "christmas": [
                date(current_year, 12, 1),  # Start December 1
                date(current_year, 12, 25)   # Through Christmas
            ],
            "halloween": [
                date(current_year, 10, 15),  # Mid-October
                date(current_year, 10, 31)   # Through Halloween
            ],
            "valentines": [
                date(current_year, 2, 10),
                date(current_year, 2, 14)
            ],
            "st_patricks": [
                date(current_year, 3, 15),
                date(current_year, 3, 17)
            ],
            "independence_day": [
                date(current_year, 7, 1),
                date(current_year, 7, 4)
            ],
            "thanksgiving": [
                date(current_year, 11, 20),
                date(current_year, 11, 30)
            ]
        }
    
    def get_contextual_personality(
        self,
        location: Optional[Dict[str, any]] = None,
        user_preferences: Optional[UserPreferences] = None,
        current_datetime: Optional[datetime] = None
    ) -> VoicePersonality:
        """
        Select the best personality based on context
        
        Priority order:
        1. Active holiday personalities
        2. User preference override
        3. Regional personality for location
        4. Time-based personality
        5. Default personality
        """
        if not current_datetime:
            current_datetime = datetime.now()
            
        # Check for holiday personalities
        holiday_personality = self._check_holiday_personality(current_datetime)
        if holiday_personality:
            return holiday_personality
            
        # Check user preference
        if user_preferences and user_preferences.preferred_voice_personality:
            if user_preferences.preferred_voice_personality in self.personalities:
                return self.personalities[user_preferences.preferred_voice_personality]
                
        # Check regional personality
        if location:
            regional_personality = self._get_regional_personality(location)
            if regional_personality:
                return regional_personality
                
        # Default to friendly guide
        return self.personalities[PersonalityType.FRIENDLY_GUIDE]
    
    def _check_holiday_personality(self, current_datetime: datetime) -> Optional[VoicePersonality]:
        """Check if any holiday personalities should be active"""
        current_date = current_datetime.date()
        current_hour = current_datetime.hour
        
        for personality in self.personalities.values():
            if not personality.active_holidays:
                continue
                
            for holiday in personality.active_holidays:
                if holiday in self.holiday_calendar:
                    date_range = self.holiday_calendar[holiday]
                    if date_range[0] <= current_date <= date_range[1]:
                        # Check hour restrictions
                        if personality.active_hours:
                            if personality.active_hours[0] <= current_hour <= personality.active_hours[1]:
                                return personality
                        else:
                            return personality
                            
        return None
    
    def _get_regional_personality(self, location: Dict[str, any]) -> Optional[VoicePersonality]:
        """Get personality based on regional location"""
        # Extract state or region from location
        state = location.get("state", "").lower()
        region = location.get("region", "").lower()
        
        # Map regions to personalities
        regional_mapping = {
            "texas": PersonalityType.TEXAS_RANGER,
            "louisiana": PersonalityType.SOUTHERN_CHARM,
            "georgia": PersonalityType.SOUTHERN_CHARM,
            "alabama": PersonalityType.SOUTHERN_CHARM,
            "mississippi": PersonalityType.SOUTHERN_CHARM,
            "tennessee": PersonalityType.SOUTHERN_CHARM,
            "kentucky": PersonalityType.SOUTHERN_CHARM,
            "south carolina": PersonalityType.SOUTHERN_CHARM,
            "north carolina": PersonalityType.SOUTHERN_CHARM,
            "virginia": PersonalityType.SOUTHERN_CHARM,
            "massachusetts": PersonalityType.NEW_ENGLAND_SCHOLAR,
            "maine": PersonalityType.NEW_ENGLAND_SCHOLAR,
            "vermont": PersonalityType.NEW_ENGLAND_SCHOLAR,
            "new hampshire": PersonalityType.NEW_ENGLAND_SCHOLAR,
            "california": PersonalityType.WEST_COAST_COOL,
            "oregon": PersonalityType.WEST_COAST_COOL,
            "washington": PersonalityType.WEST_COAST_COOL,
            "colorado": PersonalityType.MOUNTAIN_SAGE,
            "utah": PersonalityType.MOUNTAIN_SAGE,
            "wyoming": PersonalityType.MOUNTAIN_SAGE,
            "montana": PersonalityType.MOUNTAIN_SAGE,
            "louisiana": PersonalityType.JAZZ_STORYTELLER,  # New Orleans area
            "florida": PersonalityType.BEACH_VIBES,
            "hawaii": PersonalityType.BEACH_VIBES
        }
        
        if state in regional_mapping:
            personality_type = regional_mapping[state]
            if personality_type in self.personalities:
                return self.personalities[personality_type]
                
        return None
    
    def get_personality_greeting(self, personality: VoicePersonality) -> str:
        """Get a contextual greeting from the personality"""
        import random
        
        greetings = {
            PersonalityType.FRIENDLY_GUIDE: [
                "Hey there, road trippers! Ready for an amazing journey?",
                "Welcome aboard! I'm so excited to explore with you today!",
                "Hi friends! Let's make some memories on this trip!"
            ],
            PersonalityType.SANTA: [
                "Ho ho ho! Welcome to our magical Christmas journey!",
                "Merry travelers! Santa's here to guide your festive adventure!",
                "Ho ho ho! Have you all been good this year?"
            ],
            PersonalityType.HALLOWEEN_NARRATOR: [
                "Welcome, brave souls, to a journey into the unknown...",
                "Ah, you dare to travel these haunted roads...",
                "The spirits have been expecting you..."
            ],
            PersonalityType.SOUTHERN_CHARM: [
                "Well hey there, y'all! Welcome to our little adventure!",
                "Bless your hearts for joining me today!",
                "Well now, aren't y'all a sight for sore eyes!"
            ],
            PersonalityType.ADVENTURER: [
                "Adventure seekers! Are you ready for the journey of a lifetime?",
                "Let's go! The open road is calling our names!",
                "Buckle up, explorers! Epic discoveries await!"
            ]
        }
        
        personality_greetings = greetings.get(personality.id, personality.catchphrases)
        return random.choice(personality_greetings)
    
    def adjust_text_for_personality(self, text: str, personality: VoicePersonality) -> str:
        """Adjust text to match personality's speaking style"""
        # This would contain more sophisticated text transformation
        # For now, simple personality-based modifications
        
        if personality.id == PersonalityType.SOUTHERN_CHARM:
            text = text.replace("you all", "y'all")
            text = text.replace("very", "mighty")
            
        elif personality.id == PersonalityType.COMEDIAN:
            # Add occasional joke setups
            if "interesting" in text.lower():
                text = text.replace("interesting", "interesting... like my cousin's haircut")
                
        elif personality.id == PersonalityType.ADVENTURER:
            text = text.replace("Let's go", "Let's GO!")
            text = text.replace("amazing", "INCREDIBLE")
            text = text.replace("beautiful", "absolutely STUNNING")
            
        return text
    
    def get_voice_settings(self, personality: VoicePersonality) -> Dict[str, any]:
        """Get TTS voice settings for the personality"""
        return {
            "voice_id": personality.voice_id,
            "pitch": personality.speaking_style.get("pitch", 0),
            "speed": personality.speaking_style.get("speed", 1.0),
            "emphasis_style": personality.speaking_style.get("emphasis", "moderate")
        }


# Singleton instance
personality_engine = PersonalityEngine()