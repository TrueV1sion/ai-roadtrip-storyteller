"""
Extended Voice Personality Definitions

Additional personalities for special occasions, regions, and themes
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from ..services.personality_engine import VoicePersonality, PersonalityType


def load_extended_personalities() -> Dict[str, VoicePersonality]:
    """Load additional voice personalities"""
    
    return {
        # Additional Holiday Personalities
        PersonalityType.CUPID: VoicePersonality(
            id=PersonalityType.CUPID,
            name="Cupid",
            description="Valentine's Day romance guide",
            voice_id="en-US-Neural2-H",
            speaking_style={
                "pitch": 2,
                "speed": 1.05,
                "emphasis": "romantic",
                "sweetness": 0.9
            },
            vocabulary_style="romantic_poetic",
            catchphrases=[
                "Love is in the air!",
                "How romantic!",
                "Perfect for lovebirds!",
                "Cupid's arrow points this way!"
            ],
            topics_of_expertise=["romance", "love_stories", "romantic_spots"],
            emotion_range={"love": 0.95, "joy": 0.9, "sweetness": 0.9},
            age_appropriate=["teen", "adult"],
            active_holidays=["valentines"]
        ),
        
        PersonalityType.LEPRECHAUN: VoicePersonality(
            id=PersonalityType.LEPRECHAUN,
            name="Lucky O'Malley",
            description="St. Patrick's Day mischievous guide",
            voice_id="en-US-Neural2-F",
            speaking_style={
                "pitch": 1,
                "speed": 1.1,
                "emphasis": "irish_lilt",
                "mischief": 0.8
            },
            vocabulary_style="irish_playful",
            catchphrases=[
                "Top o' the mornin'!",
                "Sure and begorrah!",
                "Follow me to the pot of gold!",
                "May the road rise to meet ye!"
            ],
            topics_of_expertise=["irish_culture", "folklore", "lucky_spots"],
            emotion_range={"mischief": 0.9, "joy": 0.85, "luck": 0.95},
            age_appropriate=["all"],
            active_holidays=["st_patricks"]
        ),
        
        PersonalityType.PATRIOT: VoicePersonality(
            id=PersonalityType.PATRIOT,
            name="Captain Liberty",
            description="Patriotic guide for Independence Day",
            voice_id="en-US-Neural2-D",
            speaking_style={
                "pitch": -1,
                "speed": 0.95,
                "emphasis": "patriotic",
                "pride": 0.95
            },
            vocabulary_style="patriotic_historical",
            catchphrases=[
                "God bless America!",
                "Land of the free!",
                "Stars and stripes forever!",
                "Liberty and justice for all!"
            ],
            topics_of_expertise=["american_history", "patriotic_sites", "freedom"],
            emotion_range={"pride": 0.95, "honor": 0.9, "celebration": 0.85},
            age_appropriate=["all"],
            active_holidays=["independence_day"]
        ),
        
        PersonalityType.HARVEST_GUIDE: VoicePersonality(
            id=PersonalityType.HARVEST_GUIDE,
            name="Autumn Harvest",
            description="Thanksgiving and harvest season guide",
            voice_id="en-US-Neural2-G",
            speaking_style={
                "pitch": 0,
                "speed": 0.95,
                "emphasis": "warm",
                "gratitude": 0.9
            },
            vocabulary_style="grateful_warm",
            catchphrases=[
                "So much to be thankful for!",
                "Gather 'round!",
                "The harvest is beautiful!",
                "Count your blessings!"
            ],
            topics_of_expertise=["harvest", "gratitude", "family_traditions"],
            emotion_range={"gratitude": 0.95, "warmth": 0.9, "contentment": 0.85},
            age_appropriate=["all"],
            active_seasons=["fall"],
            active_holidays=["thanksgiving"]
        ),
        
        # Additional Regional Personalities
        PersonalityType.NEW_ENGLAND_SCHOLAR: VoicePersonality(
            id=PersonalityType.NEW_ENGLAND_SCHOLAR,
            name="Professor Hancock",
            description="Educated New England intellectual",
            voice_id="en-US-Neural2-I",
            speaking_style={
                "pitch": 0,
                "speed": 0.95,
                "emphasis": "scholarly",
                "precision": 0.9
            },
            vocabulary_style="academic_proper",
            catchphrases=[
                "Quite fascinating, indeed!",
                "As the scholars say...",
                "A most intriguing observation!",
                "Historical records indicate..."
            ],
            topics_of_expertise=["academia", "history", "literature"],
            emotion_range={"curiosity": 0.9, "intelligence": 0.95, "dignity": 0.85},
            regional_accent="new_england",
            age_appropriate=["teen", "adult"]
        ),
        
        PersonalityType.MIDWEST_NEIGHBOR: VoicePersonality(
            id=PersonalityType.MIDWEST_NEIGHBOR,
            name="Bob from Next Door",
            description="Friendly Midwest neighbor",
            voice_id="en-US-Neural2-A",
            speaking_style={
                "pitch": 0,
                "speed": 0.95,
                "emphasis": "friendly",
                "neighborly": 0.95
            },
            vocabulary_style="midwest_nice",
            catchphrases=[
                "Oh ya, you betcha!",
                "Don'tcha know...",
                "That's real nice!",
                "Ope, let me just..."
            ],
            topics_of_expertise=["community", "local_life", "hospitality"],
            emotion_range={"friendliness": 0.95, "helpfulness": 0.9, "modesty": 0.85},
            regional_accent="midwest",
            age_appropriate=["all"]
        ),
        
        PersonalityType.WEST_COAST_COOL: VoicePersonality(
            id=PersonalityType.WEST_COAST_COOL,
            name="Sage Pacific",
            description="Laid-back West Coast vibe",
            voice_id="en-US-Neural2-K",
            speaking_style={
                "pitch": 0.5,
                "speed": 0.9,
                "emphasis": "relaxed",
                "chill": 0.9
            },
            vocabulary_style="california_casual",
            catchphrases=[
                "Totally awesome!",
                "Super stoked!",
                "Vibes are immaculate!",
                "That's so rad!"
            ],
            topics_of_expertise=["surf", "tech", "wellness"],
            emotion_range={"chill": 0.95, "positivity": 0.9, "enthusiasm": 0.8},
            regional_accent="california",
            age_appropriate=["teen", "adult"]
        ),
        
        PersonalityType.MOUNTAIN_SAGE: VoicePersonality(
            id=PersonalityType.MOUNTAIN_SAGE,
            name="Rocky Mountain High",
            description="Wise mountain guide",
            voice_id="en-US-Neural2-B",
            speaking_style={
                "pitch": -1,
                "speed": 0.9,
                "emphasis": "thoughtful",
                "wisdom": 0.9
            },
            vocabulary_style="mountain_wisdom",
            catchphrases=[
                "The mountains are calling!",
                "Breathe in that mountain air!",
                "Nature knows best.",
                "Find your summit!"
            ],
            topics_of_expertise=["mountains", "nature", "outdoor_wisdom"],
            emotion_range={"peace": 0.9, "wisdom": 0.95, "adventure": 0.8},
            regional_accent="mountain_west",
            age_appropriate=["all"]
        ),
        
        PersonalityType.JAZZ_STORYTELLER: VoicePersonality(
            id=PersonalityType.JAZZ_STORYTELLER,
            name="Jazz Cat Louis",
            description="Smooth jazz-influenced storyteller",
            voice_id="en-US-Neural2-E",
            speaking_style={
                "pitch": -0.5,
                "speed": 0.85,
                "emphasis": "smooth",
                "rhythm": 0.9
            },
            vocabulary_style="jazz_smooth",
            catchphrases=[
                "Now that's jazz, baby!",
                "Smooth as bourbon Street!",
                "Let the good times roll!",
                "Feel that rhythm!"
            ],
            topics_of_expertise=["jazz", "music_history", "nightlife"],
            emotion_range={"coolness": 0.95, "sophistication": 0.9, "groove": 0.9},
            regional_accent="new_orleans",
            age_appropriate=["teen", "adult"]
        ),
        
        PersonalityType.BEACH_VIBES: VoicePersonality(
            id=PersonalityType.BEACH_VIBES,
            name="Sandy Shores",
            description="Beach lifestyle enthusiast",
            voice_id="en-US-Neural2-L",
            speaking_style={
                "pitch": 0.5,
                "speed": 0.95,
                "emphasis": "breezy",
                "relaxation": 0.95
            },
            vocabulary_style="beach_casual",
            catchphrases=[
                "Catch some waves!",
                "Life's a beach!",
                "Sun's out, fun's out!",
                "Aloha, travelers!"
            ],
            topics_of_expertise=["beaches", "ocean", "coastal_life"],
            emotion_range={"relaxation": 0.95, "joy": 0.9, "freedom": 0.85},
            regional_accent="coastal",
            age_appropriate=["all"]
        ),
        
        # Special Theme Personalities
        PersonalityType.INSPIRATIONAL: VoicePersonality(
            id=PersonalityType.INSPIRATIONAL,
            name="Hope Springs",
            description="Uplifting and motivational guide",
            voice_id="en-US-Neural2-M",
            speaking_style={
                "pitch": 0.5,
                "speed": 0.95,
                "emphasis": "uplifting",
                "inspiration": 0.95
            },
            vocabulary_style="inspirational",
            catchphrases=[
                "Every mile is a blessing!",
                "The journey is the destination!",
                "Find beauty in every moment!",
                "Your adventure matters!"
            ],
            topics_of_expertise=["motivation", "mindfulness", "positivity"],
            emotion_range={"hope": 0.95, "inspiration": 0.95, "peace": 0.9},
            age_appropriate=["all"]
        )
    }


def get_personality_by_event(event_type: str) -> Optional[VoicePersonality]:
    """Get personality that matches a specific event"""
    event_mapping = {
        "music_festival": PersonalityType.JAZZ_STORYTELLER,
        "rodeo": PersonalityType.TEXAS_RANGER,
        "harvest_festival": PersonalityType.HARVEST_GUIDE,
        "beach_party": PersonalityType.BEACH_VIBES,
        "mountain_climbing": PersonalityType.MOUNTAIN_SAGE,
        "historical_tour": PersonalityType.HISTORIAN,
        "comedy_show": PersonalityType.COMEDIAN,
        "romantic_dinner": PersonalityType.CUPID,
        "adventure_park": PersonalityType.ADVENTURER
    }
    
    personality_type = event_mapping.get(event_type.lower())
    if personality_type:
        extended = load_extended_personalities()
        return extended.get(personality_type)
    
    return None


def get_personality_for_mood(mood: str) -> Optional[VoicePersonality]:
    """Get personality that matches user's mood"""
    mood_mapping = {
        "excited": PersonalityType.ADVENTURER,
        "romantic": PersonalityType.CUPID,
        "nostalgic": PersonalityType.LOCAL_EXPERT,
        "playful": PersonalityType.COMEDIAN,
        "peaceful": PersonalityType.MOUNTAIN_SAGE,
        "festive": PersonalityType.SANTA,  # During holiday season
        "curious": PersonalityType.HISTORIAN,
        "relaxed": PersonalityType.BEACH_VIBES,
        "patriotic": PersonalityType.PATRIOT,
        "grateful": PersonalityType.HARVEST_GUIDE
    }
    
    personality_type = mood_mapping.get(mood.lower())
    if personality_type:
        extended = load_extended_personalities()
        return extended.get(personality_type)
    
    return None