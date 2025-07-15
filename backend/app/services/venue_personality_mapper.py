from typing import Dict, Any, Optional
import random

from backend.app.core.logger import logger


class VenuePersonalityMapper:
    """Maps event types and venues to appropriate voice personalities."""
    
    # Define voice personalities for different event types
    VOICE_PERSONALITIES = {
        "rock_concert": {
            "name": "Axel",
            "style": "energetic_rocker",
            "traits": ["enthusiastic", "rebellious", "knowledgeable about rock history"],
            "speech_patterns": ["Hey there, rock star!", "Let's crank it up!", "This is gonna be epic!"],
            "tone": "excited and edgy",
            "vocabulary": "music industry slang, rock references"
        },
        "classical_concert": {
            "name": "Sophia",
            "style": "cultured_guide",
            "traits": ["sophisticated", "knowledgeable", "passionate about arts"],
            "speech_patterns": ["Good evening", "A delightful performance awaits", "The maestro's interpretation"],
            "tone": "refined and informative",
            "vocabulary": "musical terminology, historical context"
        },
        "sports_game": {
            "name": "Coach Mike",
            "style": "sports_announcer",
            "traits": ["energetic", "stats-focused", "team spirit"],
            "speech_patterns": ["Game day, baby!", "Let's break it down", "Time to bring the heat!"],
            "tone": "pumped up and analytical",
            "vocabulary": "sports terminology, team history, player stats"
        },
        "theater": {
            "name": "Victoria",
            "style": "theater_enthusiast",
            "traits": ["dramatic", "articulate", "emotionally expressive"],
            "speech_patterns": ["The curtain rises on", "A performance to remember", "Bravo!"],
            "tone": "theatrical and elegant",
            "vocabulary": "theater terminology, Broadway references"
        },
        "comedy_show": {
            "name": "Chuck",
            "style": "comedy_buddy",
            "traits": ["humorous", "upbeat", "timing-conscious"],
            "speech_patterns": ["Ready for some laughs?", "This is gonna be hilarious", "Comedy gold!"],
            "tone": "light-hearted and fun",
            "vocabulary": "comedy references, playful language"
        },
        "family_show": {
            "name": "Jamie",
            "style": "family_friend",
            "traits": ["warm", "inclusive", "child-friendly"],
            "speech_patterns": ["Hi everyone!", "This is going to be so much fun", "Adventure time!"],
            "tone": "friendly and enthusiastic",
            "vocabulary": "simple, engaging, age-appropriate"
        },
        "jazz_club": {
            "name": "Miles",
            "style": "jazz_aficionado",
            "traits": ["smooth", "knowledgeable", "laid-back"],
            "speech_patterns": ["Let's groove", "Smooth as silk", "Feel that rhythm"],
            "tone": "cool and sophisticated",
            "vocabulary": "jazz terminology, music history"
        },
        "festival": {
            "name": "Luna",
            "style": "festival_guide",
            "traits": ["free-spirited", "informative", "community-focused"],
            "speech_patterns": ["Welcome to the vibe", "So many amazing artists", "Feel the energy!"],
            "tone": "excited and inclusive",
            "vocabulary": "festival culture, artist backgrounds"
        },
        "theme_park": {
            "name": "Max",
            "style": "adventure_guide",
            "traits": ["adventurous", "safety-conscious", "fun-loving"],
            "speech_patterns": ["Ready for adventure?", "Hold on tight!", "Magic awaits!"],
            "tone": "thrilling and reassuring",
            "vocabulary": "theme park lingo, attraction details"
        },
        "default": {
            "name": "Alex",
            "style": "friendly_companion",
            "traits": ["adaptable", "informative", "personable"],
            "speech_patterns": ["Let's go!", "This will be great", "Almost there!"],
            "tone": "warm and encouraging",
            "vocabulary": "conversational, context-aware"
        }
    }
    
    # Special venue overrides for iconic locations
    VENUE_OVERRIDES = {
        "madison square garden": "sports_game",  # Even for concerts, MSG has a special energy
        "hollywood bowl": "classical_concert",
        "red rocks amphitheatre": "rock_concert",
        "disney": "theme_park",
        "universal studios": "theme_park",
        "broadway": "theater",
        "carnegie hall": "classical_concert",
        "blue note": "jazz_club"
    }
    
    async def get_personality_for_event(
        self,
        event_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Select the best voice personality for an event."""
        # Check venue overrides first
        venue_name = event_metadata.get("venue", {}).get("name", "").lower()
        for venue_key, personality_type in self.VENUE_OVERRIDES.items():
            if venue_key in venue_name:
                return self.VOICE_PERSONALITIES.get(
                    personality_type,
                    self.VOICE_PERSONALITIES["default"]
                )
        
        # Determine personality based on event classification
        personality_type = self._classify_event(event_metadata)
        
        # Get base personality
        personality = self.VOICE_PERSONALITIES.get(
            personality_type,
            self.VOICE_PERSONALITIES["default"]
        ).copy()
        
        # Add event-specific context
        personality["event_context"] = self._build_event_context(event_metadata)
        
        # Add dynamic elements based on time of day, season, etc.
        personality["dynamic_elements"] = self._add_dynamic_elements(event_metadata)
        
        return personality
    
    def _classify_event(self, event_metadata: Dict[str, Any]) -> str:
        """Classify event into personality categories."""
        classifications = event_metadata.get("classifications", [])
        if not classifications:
            return "default"
        
        primary = classifications[0]
        segment = primary.get("segment", "").lower()
        genre = primary.get("genre", "").lower()
        subgenre = primary.get("subGenre", "").lower()
        
        # Music events
        if segment == "music":
            if any(term in genre for term in ["rock", "metal", "punk", "alternative"]):
                return "rock_concert"
            elif any(term in genre for term in ["classical", "symphony", "opera"]):
                return "classical_concert"
            elif "jazz" in genre or "blues" in genre:
                return "jazz_club"
            elif "comedy" in subgenre:
                return "comedy_show"
            else:
                return "festival"  # General music event
        
        # Sports events
        elif segment == "sports":
            return "sports_game"
        
        # Arts & Theatre
        elif segment == "arts & theatre":
            if "comedy" in genre:
                return "comedy_show"
            else:
                return "theater"
        
        # Family events
        elif segment == "family" or "family" in genre:
            attractions = event_metadata.get("attractions", [])
            if any("disney" in attr.get("name", "").lower() for attr in attractions):
                return "theme_park"
            return "family_show"
        
        # Film events
        elif segment == "film":
            return "theater"
        
        return "default"
    
    def _build_event_context(self, event_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Build context-specific information for the personality."""
        context = {
            "event_name": event_metadata.get("name"),
            "venue_name": event_metadata.get("venue", {}).get("name"),
            "performers": [attr.get("name") for attr in event_metadata.get("attractions", [])],
            "event_type": event_metadata.get("classifications", [{}])[0].get("segment"),
            "special_notes": event_metadata.get("pleaseNote", "")
        }
        
        # Add interesting facts based on event type
        if context["performers"]:
            context["focus_topics"] = [
                f"facts about {context['performers'][0]}",
                "venue history",
                "similar past performances"
            ]
        
        return context
    
    def _add_dynamic_elements(self, event_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Add dynamic elements based on context."""
        from datetime import datetime
        
        elements = {}
        
        # Time-based adjustments
        event_date = event_metadata.get("dates", {}).get("start", {}).get("dateTime")
        if event_date:
            try:
                event_time = datetime.fromisoformat(event_date.replace("Z", "+00:00"))
                hour = event_time.hour
                
                if hour < 12:
                    elements["time_greeting"] = "morning"
                elif hour < 17:
                    elements["time_greeting"] = "afternoon"
                else:
                    elements["time_greeting"] = "evening"
                
                # Weekend vs weekday
                if event_time.weekday() >= 5:
                    elements["day_type"] = "weekend"
                else:
                    elements["day_type"] = "weekday"
            except:
                pass
        
        # Weather considerations (would integrate with weather service)
        elements["weather_aware"] = True
        
        # Special event considerations
        if "sold out" in event_metadata.get("name", "").lower():
            elements["excitement_level"] = "maximum"
        
        return elements
    
    def get_personality_traits(self, personality_type: str) -> Dict[str, Any]:
        """Get detailed traits for a personality type."""
        return self.VOICE_PERSONALITIES.get(
            personality_type,
            self.VOICE_PERSONALITIES["default"]
        )
    
    def get_introduction_style(self, personality: Dict[str, Any]) -> str:
        """Get introduction style for a personality."""
        greetings = personality.get("speech_patterns", [])
        if greetings:
            return random.choice(greetings)
        return "Hello! Let's begin our journey."
    
    def adjust_for_user_preferences(
        self,
        base_personality: Dict[str, Any],
        user_preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Adjust personality based on user preferences."""
        adjusted = base_personality.copy()
        
        # Adjust formality
        if user_preferences.get("formality") == "casual":
            adjusted["tone"] = adjusted["tone"].replace("refined", "friendly")
            adjusted["tone"] = adjusted["tone"].replace("sophisticated", "relaxed")
        elif user_preferences.get("formality") == "formal":
            adjusted["tone"] = adjusted["tone"].replace("laid-back", "professional")
        
        # Adjust information density
        if user_preferences.get("detail_level") == "minimal":
            adjusted["traits"].append("concise")
        elif user_preferences.get("detail_level") == "detailed":
            adjusted["traits"].append("thorough")
        
        # Language preferences
        if user_preferences.get("language_complexity") == "simple":
            adjusted["vocabulary"] = "simple, clear language"
        
        return adjusted