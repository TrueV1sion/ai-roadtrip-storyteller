"""
Personality System Integration Module

Integrates the Dynamic Personality System with existing services and provides
a unified interface for personality selection and management.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging
from dataclasses import dataclass

from ..core.cache import cache_manager
from ..models.user import UserPreferences
from ..services.personality_engine import PersonalityEngine, VoicePersonality
from ..services.dynamic_personality_system import (
    DynamicPersonalitySystem, 
    PersonalityContext,
    ContextFactor
)
from ..services.personality_registry import personality_registry
from ..services.venue_personality_mapper import VenuePersonalityMapper
from ..services.event_journey_service import EventJourneyService
from ..services.weather_service import get_weather

logger = logging.getLogger(__name__)


@dataclass
class PersonalitySelectionResult:
    """Result of personality selection process"""
    selected_personality: VoicePersonality
    confidence_score: float
    selection_reason: str
    alternatives: List[Tuple[VoicePersonality, float]]
    context_analysis: Dict[str, Any]


class PersonalityIntegrationService:
    """
    Main integration point for the personality system.
    Coordinates between all personality-related services.
    """
    
    def __init__(self):
        self.dynamic_system = DynamicPersonalitySystem()
        self.personality_engine = PersonalityEngine()
        self.venue_mapper = VenuePersonalityMapper()
        self.selection_cache = {}
        
    async def select_personality_for_journey(
        self,
        user_id: str,
        journey_data: Dict[str, Any],
        user_preferences: Optional[UserPreferences] = None
    ) -> PersonalitySelectionResult:
        """
        Select the best personality for a complete journey context
        """
        try:
            # Build comprehensive context
            context = await self._build_journey_context(
                user_id, 
                journey_data, 
                user_preferences
            )
            
            # Check cache first
            cache_key = self._generate_cache_key(context)
            cached_result = await cache_manager.get(cache_key)
            if cached_result:
                return PersonalitySelectionResult(**cached_result)
            
            # Perform selection
            selected = await self.dynamic_system.select_personality(context)
            
            # Get alternatives for user choice
            alternatives = await self.dynamic_system.get_personality_suggestions(
                context, 
                count=3
            )
            
            # Analyze why this personality was selected
            selection_reason = self._generate_selection_reason(selected, context)
            
            # Calculate confidence score
            confidence_score = await self._calculate_confidence_score(
                selected, 
                context, 
                alternatives
            )
            
            # Build result
            result = PersonalitySelectionResult(
                selected_personality=selected,
                confidence_score=confidence_score,
                selection_reason=selection_reason,
                alternatives=alternatives,
                context_analysis=self._analyze_context(context)
            )
            
            # Cache result
            await cache_manager.set(
                cache_key, 
                result.__dict__, 
                ttl=3600  # 1 hour cache
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error selecting personality: {e}")
            # Fallback to default
            return PersonalitySelectionResult(
                selected_personality=self.personality_engine.personalities["friendly_guide"],
                confidence_score=0.5,
                selection_reason="Default selection due to error",
                alternatives=[],
                context_analysis={}
            )
    
    async def _build_journey_context(
        self,
        user_id: str,
        journey_data: Dict[str, Any],
        user_preferences: Optional[UserPreferences]
    ) -> PersonalityContext:
        """Build comprehensive context from journey data"""
        
        # Extract location info
        location = None
        if "destination" in journey_data:
            location = {
                "state": journey_data.get("destination_state"),
                "city": journey_data.get("destination_city"),
                "region": self._determine_region(journey_data.get("destination_state"))
            }
        
        # Get current weather
        weather = None
        if location:
            try:
                weather = await get_weather(
                    location.get("city"), 
                    location.get("state")
                )
            except Exception as e:
                pass
        
        # Extract event metadata if present
        event_metadata = journey_data.get("event_metadata")
        
        # Determine special occasions
        special_occasion = self._detect_special_occasion(journey_data)
        
        # Extract passenger info
        passenger_info = {
            "passengers": journey_data.get("passengers", []),
            "count": journey_data.get("passenger_count", 1)
        }
        
        # Build context
        return PersonalityContext(
            event_metadata=event_metadata,
            location=location,
            datetime=datetime.now(),
            weather=weather,
            user_preferences=user_preferences,
            journey_type=journey_data.get("journey_type"),
            passenger_info=passenger_info,
            special_occasion=special_occasion,
            user_mood=journey_data.get("user_mood"),
            timezone=journey_data.get("timezone", "UTC")
        )
    
    def _determine_region(self, state: Optional[str]) -> str:
        """Determine region from state"""
        if not state:
            return "unknown"
        
        state = state.lower()
        
        # Regional mappings
        regions = {
            "northeast": ["maine", "new hampshire", "vermont", "massachusetts", 
                         "rhode island", "connecticut", "new york", "new jersey", 
                         "pennsylvania"],
            "south": ["delaware", "maryland", "virginia", "west virginia", 
                     "kentucky", "tennessee", "north carolina", "south carolina", 
                     "georgia", "florida", "alabama", "mississippi", "louisiana", 
                     "arkansas"],
            "midwest": ["ohio", "indiana", "illinois", "michigan", "wisconsin", 
                       "minnesota", "iowa", "missouri", "north dakota", 
                       "south dakota", "nebraska", "kansas"],
            "southwest": ["texas", "oklahoma", "new mexico", "arizona"],
            "west": ["colorado", "wyoming", "montana", "idaho", "utah", "nevada", 
                    "california", "oregon", "washington", "alaska", "hawaii"]
        }
        
        for region, states in regions.items():
            if state in states:
                return region
        
        return "unknown"
    
    def _detect_special_occasion(self, journey_data: Dict[str, Any]) -> Optional[str]:
        """Detect special occasions from journey data"""
        
        # Check explicit occasion
        if "special_occasion" in journey_data:
            return journey_data["special_occasion"]
        
        # Check event name for clues
        event_name = journey_data.get("event_name", "").lower()
        
        occasion_keywords = {
            "wedding": ["wedding", "nuptials", "marriage"],
            "birthday": ["birthday", "bday", "birth day"],
            "anniversary": ["anniversary"],
            "graduation": ["graduation", "commencement"],
            "reunion": ["reunion"],
            "date_night": ["date", "romantic", "couples"],
            "proposal": ["proposal", "engagement"]
        }
        
        for occasion, keywords in occasion_keywords.items():
            if any(keyword in event_name for keyword in keywords):
                return occasion
        
        return None
    
    def _generate_cache_key(self, context: PersonalityContext) -> str:
        """Generate cache key for personality selection"""
        components = []
        
        if context.event_metadata:
            components.append(f"event_{context.event_metadata.get('id', 'unknown')}")
        
        if context.location:
            components.append(f"loc_{context.location.get('state', 'unknown')}")
        
        components.append(f"hour_{context.datetime.hour}")
        components.append(f"dow_{context.datetime.weekday()}")
        
        if context.special_occasion:
            components.append(f"occasion_{context.special_occasion}")
        
        if context.user_mood:
            components.append(f"mood_{context.user_mood}")
        
        return "personality_" + "_".join(components)
    
    def _generate_selection_reason(
        self, 
        personality: VoicePersonality, 
        context: PersonalityContext
    ) -> str:
        """Generate human-readable reason for personality selection"""
        reasons = []
        
        # Event-based selection
        if context.event_metadata:
            event_name = context.event_metadata.get("name", "your event")
            reasons.append(f"Perfect for {event_name}")
        
        # Holiday-based selection
        if hasattr(personality, 'active_holidays') and personality.active_holidays:
            holiday = personality.active_holidays[0]
            reasons.append(f"Celebrating {holiday.replace('_', ' ').title()}")
        
        # Location-based selection
        if hasattr(personality, 'regional_accent') and personality.regional_accent:
            reasons.append(f"Local {personality.regional_accent} personality")
        
        # Time-based selection
        if hasattr(personality, 'active_hours') and personality.active_hours:
            reasons.append(f"Perfect for this time of day")
        
        # Mood-based selection
        if context.user_mood:
            reasons.append(f"Matches your {context.user_mood} mood")
        
        # Special occasion
        if context.special_occasion:
            reasons.append(f"Ideal for your {context.special_occasion}")
        
        if reasons:
            return " | ".join(reasons)
        else:
            return "Best match for your journey"
    
    async def _calculate_confidence_score(
        self,
        selected: VoicePersonality,
        context: PersonalityContext,
        alternatives: List[Tuple[VoicePersonality, float]]
    ) -> float:
        """Calculate confidence score for the selection"""
        
        # Get all scores
        scores = await self.dynamic_system._calculate_personality_scores(context)
        
        if not scores:
            return 0.5
        
        selected_score = scores.get(selected.id, 0)
        max_score = max(scores.values()) if scores else 1
        
        # Normalize to 0-1 range
        if max_score > 0:
            base_confidence = selected_score / max_score
        else:
            base_confidence = 0.5
        
        # Adjust based on gap to next best
        if alternatives and len(alternatives) > 1:
            gap = selected_score - alternatives[1][1]
            gap_factor = min(gap / 20, 0.2)  # Max 0.2 bonus for large gaps
            base_confidence = min(base_confidence + gap_factor, 1.0)
        
        return round(base_confidence, 2)
    
    def _analyze_context(self, context: PersonalityContext) -> Dict[str, Any]:
        """Analyze context for insights"""
        analysis = {
            "primary_factors": [],
            "time_analysis": {},
            "environmental_factors": [],
            "user_factors": []
        }
        
        # Primary selection factors
        if context.event_metadata:
            analysis["primary_factors"].append("event-driven")
        if context.special_occasion:
            analysis["primary_factors"].append("special-occasion")
        if context.datetime.month == 12 and context.datetime.day >= 20:
            analysis["primary_factors"].append("holiday-season")
        
        # Time analysis
        hour = context.datetime.hour
        if 5 <= hour < 12:
            analysis["time_analysis"]["period"] = "morning"
        elif 12 <= hour < 17:
            analysis["time_analysis"]["period"] = "afternoon"
        elif 17 <= hour < 21:
            analysis["time_analysis"]["period"] = "evening"
        else:
            analysis["time_analysis"]["period"] = "night"
        
        analysis["time_analysis"]["day_type"] = (
            "weekend" if context.datetime.weekday() >= 5 else "weekday"
        )
        
        # Environmental factors
        if context.weather:
            analysis["environmental_factors"].append(
                f"weather: {context.weather.get('condition', 'unknown')}"
            )
        if context.location:
            analysis["environmental_factors"].append(
                f"region: {context.location.get('region', 'unknown')}"
            )
        
        # User factors
        if context.user_mood:
            analysis["user_factors"].append(f"mood: {context.user_mood}")
        if context.passenger_info:
            count = context.passenger_info.get("count", 1)
            analysis["user_factors"].append(f"passengers: {count}")
        
        return analysis
    
    async def update_personality_preferences(
        self,
        user_id: str,
        personality_id: str,
        rating: int,
        feedback: Optional[str] = None
    ):
        """Update user preferences based on personality feedback"""
        # This would integrate with user preference storage
        logger.info(
            f"User {user_id} rated personality {personality_id}: "
            f"{rating}/5 - {feedback or 'No feedback'}"
        )
        
        # Update user preferences in database
        # This would be implemented with actual database operations
        pass
    
    async def get_personality_recommendations(
        self,
        user_id: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get personality recommendations for user selection"""
        journey_context = await self._build_journey_context(
            user_id,
            context,
            None  # Will be fetched if needed
        )
        
        suggestions = await self.dynamic_system.get_personality_suggestions(
            journey_context,
            count=5
        )
        
        recommendations = []
        for personality, score in suggestions:
            # Get metadata from registry
            metadata = personality_registry.get_personality(personality.id)
            
            recommendations.append({
                "id": personality.id,
                "name": personality.name,
                "description": personality.description,
                "category": metadata.category if metadata else "general",
                "match_score": score,
                "preview_greeting": self.personality_engine.get_personality_greeting(
                    personality
                ),
                "traits": metadata.personality_traits if metadata else [],
                "why_recommended": self._generate_selection_reason(
                    personality, 
                    journey_context
                )
            })
        
        return recommendations
    
    def get_personality_analytics(self) -> Dict[str, Any]:
        """Get analytics on personality usage"""
        return self.dynamic_system.get_analytics()


# Singleton instance
personality_integration = PersonalityIntegrationService()