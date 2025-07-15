from typing import Dict, List, Optional, Any, Tuple
import json
import random
from datetime import datetime
import logging
import re

# Google Cloud Language API
from google.cloud import language_v1
from google.api_core import exceptions as google_exceptions

# Google Maps API
import googlemaps
from app.core.config import settings # Import settings for API key

from app.core.logger import get_logger

logger = get_logger(__name__)


class PersonalizationEngine:
    """
    Engine for personalizing content based on user preferences and context.
    Provides tools for context-aware prompt engineering and content enhancement.
    NOTE: This engine is now stateless regarding user preferences.
          Preferences should be fetched from the DB and passed into methods.
    """

    def __init__(self):
        """Initialize the personalization engine."""
        # Initialize Google Cloud Language Client
        try:
            self.language_client = language_v1.LanguageServiceClient()
            logger.info("Google Cloud Language client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Google Cloud Language client: {e}")
            self.language_client = None

        # Initialize Google Maps Client
        try:
            if settings.GOOGLE_MAPS_API_KEY:
                self.gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
                logger.info("Google Maps client initialized successfully.")
            else:
                logger.warning("GOOGLE_MAPS_API_KEY not set. Location features will be limited.")
                self.gmaps = None
        except Exception as e:
            logger.error(f"Failed to initialize Google Maps client: {e}")
            self.gmaps = None

        # --- Interest Categories, Storytelling Styles, Content Themes remain the same ---
        self.interest_categories = {
            "history": ["history", "historical", "heritage", "ancient", "vintage", "classical", "traditional", "civilization", "ruins", "monuments", "landmarks"],
            "nature": ["nature", "outdoors", "wildlife", "hiking", "mountains", "beaches", "forests", "lakes", "oceans", "camping", "parks", "scenic", "landscape"],
            "culture": ["culture", "arts", "museums", "galleries", "music", "dance", "theater", "cuisine", "food", "festivals", "customs", "traditions", "local"],
            "adventure": ["adventure", "activities", "sports", "adrenaline", "thrills", "exploration", "discovery", "excitement", "challenges"],
            "family": ["family", "kids", "children", "educational", "interactive", "fun", "playgrounds", "amusement", "entertainment"],
            "relaxation": ["relaxation", "wellness", "spa", "peaceful", "tranquil", "quiet", "retreat", "meditation", "mindfulness"]
        }
        self.storytelling_styles = {
             "educational": { "description": "...", "prompt_modifiers": ["Include 3 interesting educational facts about this location.","Highlight historical significance and educational value.","Explain the cultural or natural importance of this area."], "weight": 1.0 },
             "entertaining": { "description": "...", "prompt_modifiers": ["Create an exciting narrative with elements of wonder.","Incorporate humor and engaging anecdotes.","Use vivid imagery and sensory descriptions."], "weight": 1.0 },
             "balanced": { "description": "...", "prompt_modifiers": ["Balance factual information with engaging storytelling.","Weave educational facts into an entertaining narrative.","Create a story that both teaches and entertains."], "weight": 1.0 },
             "adventure": { "description": "...", "prompt_modifiers": ["Create a sense of adventure and discovery.","Include elements of exploration and the unknown.","Highlight the exciting aspects of the journey."], "weight": 1.0 },
             "cultural": { "description": "...", "prompt_modifiers": ["Highlight local customs, traditions, and way of life.","Include elements of cultural significance.","Explore the cultural heritage and identity of the location."], "weight": 1.0 }
        }
        self.content_themes = {
             "time_of_day": { "morning": ["morning mist and dew", "sunrise and new beginnings", "early bird activities", "fresh starts and energy"], "afternoon": ["bright daylight and clear views", "bustling activity and exploration", "warmth and vibrant colors", "peak experiences and adventures"], "evening": ["golden hour and sunset", "reflection on the day", "twilight and transition", "winding down and peaceful moments"], "night": ["stars and moonlight", "mystery and wonder", "nocturnal creatures and activities", "tranquility and darkness"] },
             "weather": { "sunny": ["bright sunshine and blue skies", "warm rays and natural beauty", "vibrant colors and clear views", "perfect outdoor experiences"], "cloudy": ["moody atmosphere and soft light", "changing patterns in the sky", "subdued colors and gentle transitions", "contemplative and calm moods"], "rainy": ["refreshing raindrops and petrichor", "glistening surfaces and reflections", "cozy indoor experiences and stories", "cleansing renewal and growth"], "snowy": ["pristine white landscapes", "serene quiet and transformation", "winter wonderland and magic", "crisp air and seasonal beauty"], "foggy": ["mysterious atmosphere and limited visibility", "dreamlike quality and soft edges", "focus on sounds and other senses", "hidden revelations and surprises"] },
             "mood": { "happy": ["joyful experiences and memories", "positive outlooks and discoveries", "uplifting elements and celebration", "delight and wonder"], "reflective": ["thoughtful connections to the past", "meaningful insights and perspective", "personal growth and understanding", "contemplative questions and wisdom"], "curious": ["intriguing facts and mysteries", "questions and exploration", "discovery and learning", "fascinating details and insights"], "adventurous": ["bold journeys and challenges", "exciting discoveries and risks", "exploration and the unexpected", "achievement and conquest"], "peaceful": ["tranquil moments and settings", "harmony with surroundings", "gentle experiences and calm", "mindfulness and presence"] }
        }

        # Removed static cultural database
        # self.cultural_database = { ... }

        # Removed in-memory user preference storage
        # self.user_preferences = {}

    # --- analyze_preferences, get_user_preference_model remain the same ---
    def analyze_preferences(self, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze provided user preferences to create a weighted interest model.
        Does not store the result internally.

        Args:
            preferences: User preference data (e.g., from DB or request)

        Returns:
            Dict[str, Any]: Analyzed preference model (interests, categories, style)
        """
        if not preferences:
            return {} # Return empty model if no preferences provided

        # Extract interests and assign weights
        interests = preferences.get("interests", [])
        interest_weights = {}
        if interests:
            base_weight = 1.0 / len(interests) if interests else 0 # Avoid division by zero
            for interest in interests:
                interest_weights[interest] = base_weight

        # Apply category mapping
        categorized_interests = {}
        for category, keywords in self.interest_categories.items():
            category_weight = 0.0
            for interest, weight in interest_weights.items():
                if interest.lower() == category.lower():
                    category_weight += weight
                    continue
                for keyword in keywords:
                    if keyword.lower() in interest.lower():
                        category_weight += weight * 0.8
                        break
            if category_weight > 0:
                categorized_interests[category] = category_weight

        # Get storytelling style preference
        storytelling_style = preferences.get("storytelling_style", "balanced")

        # Return the analyzed model without storing it in the instance
        analyzed_model = {
            "interests": interest_weights,
            "categories": categorized_interests,
            "storytelling_style": storytelling_style,
        }
        return analyzed_model

    # Removed get_user_preference_model as engine is stateless regarding preferences
    # def get_user_preference_model(self, user_id: str) -> Dict[str, Any]: ...

    # --- Refactored Location Info Methods ---
    def extract_location_info(self, latitude: float, longitude: float) -> Dict[str, Optional[str]]:
        """
        Extract location information using Google Maps Reverse Geocoding.
        """
        if not self.gmaps:
            logger.warning("Google Maps client not initialized. Cannot extract location info.")
            return {"country": None, "region": None, "locality": None, "formatted_address": None}

        try:
            reverse_geocode_result = self.gmaps.reverse_geocode((latitude, longitude))
            if not reverse_geocode_result:
                return {"country": None, "region": None, "locality": None, "formatted_address": None}

            # Extract components
            address_components = reverse_geocode_result[0].get('address_components', [])
            locality = next((c['long_name'] for c in address_components if 'locality' in c['types']), None)
            region = next((c['short_name'] for c in address_components if 'administrative_area_level_1' in c['types']), None) # State/Province code
            country = next((c['short_name'] for c in address_components if 'country' in c['types']), None)
            formatted_address = reverse_geocode_result[0].get('formatted_address')

            logger.info(f"Reverse geocode result for ({latitude},{longitude}): {formatted_address}")
            return {
                "country": country,
                "region": region,
                "locality": locality,
                "formatted_address": formatted_address
            }
        except Exception as e:
            logger.error(f"Error during reverse geocoding for ({latitude},{longitude}): {e}")
            return {"country": None, "region": None, "locality": None, "formatted_address": None}

    def _find_nearby_places(self, latitude: float, longitude: float, place_type: str, radius: int = 5000) -> List[Dict]:
        """Helper to find nearby places of a specific type."""
        if not self.gmaps:
            return []
        try:
            places_result = self.gmaps.places_nearby(
                location=(latitude, longitude),
                radius=radius, # Search within 5km
                type=place_type
            )
            return places_result.get('results', [])
        except Exception as e:
            logger.error(f"Error finding nearby places ({place_type}) for ({latitude},{longitude}): {e}")
            return []

    def get_nearby_landmarks(self, latitude: float, longitude: float, count: int = 3) -> List[str]:
        """Get names of nearby landmarks using Google Places API."""
        landmarks = self._find_nearby_places(latitude, longitude, 'tourist_attraction')
        # Could also search for 'landmark' type if needed
        landmark_names = [place.get('name') for place in landmarks if place.get('name')]
        return random.sample(landmark_names, min(count, len(landmark_names)))

    def get_nearby_historical_sites(self, latitude: float, longitude: float, count: int = 2) -> List[str]:
        """Get names of nearby historical sites using Google Places API."""
        sites = self._find_nearby_places(latitude, longitude, 'museum') # Museums often cover history
        # Could add 'historical_landmark' if available or broaden search
        site_names = [place.get('name') for place in sites if place.get('name')]
        return random.sample(site_names, min(count, len(site_names)))

    def get_nearby_cultural_venues(self, latitude: float, longitude: float, count: int = 2) -> List[str]:
        """Get names of nearby cultural venues using Google Places API."""
        venues = self._find_nearby_places(latitude, longitude, 'art_gallery')
        venues.extend(self._find_nearby_places(latitude, longitude, 'performing_arts_theater'))
        venue_names = [place.get('name') for place in venues if place.get('name')]
        return random.sample(venue_names, min(count, len(venue_names)))


    # --- enhance_prompt updated to use passed-in preferences ---
    def enhance_prompt(
        self,
        base_prompt: str,
        user_preferences: Optional[Dict[str, Any]] = None, # Now takes raw preferences
        location: Optional[Dict[str, float]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Enhance a prompt with personalization based on provided user preferences and context.
        """
        enhanced_prompt = base_prompt

        # Apply user preference enhancements if available
        if user_preferences:
            # Analyze the provided preferences on the fly
            analyzed_prefs = self.analyze_preferences(user_preferences) # Use the method to get structured data

            # Add storytelling style modifiers
            style = analyzed_prefs.get("storytelling_style", "balanced")
            style_info = self.storytelling_styles.get(style, self.storytelling_styles["balanced"])
            modifiers = style_info.get("prompt_modifiers", [])
            if modifiers:
                modifier = random.choice(modifiers)
                enhanced_prompt += f"\n\nStorytelling style: {modifier}"

            # Emphasize user's interests based on analyzed categories
            categories = analyzed_prefs.get("categories", {})
            if categories:
                sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3]
                category_emphasis = "\n\nEmphasize these elements based on user interests:"
                for category, weight in sorted_categories:
                    category_emphasis += f"\n- {category.capitalize()}: {int(weight * 100)}% emphasis"
                enhanced_prompt += category_emphasis


        # Apply context-specific enhancements (same as before)
        if context:
            # ... (time, weather, mood theme logic remains the same) ...
            time_of_day = context.get("time_of_day")
            if time_of_day and time_of_day in self.content_themes["time_of_day"]:
                themes = self.content_themes["time_of_day"][time_of_day]
                if themes: enhanced_prompt += f"\n\nIncorporate the {time_of_day} theme: {random.choice(themes)}"
            weather = context.get("weather")
            if weather and weather in self.content_themes["weather"]:
                 themes = self.content_themes["weather"][weather]
                 if themes: enhanced_prompt += f"\n\nCapture the {weather} weather atmosphere: {random.choice(themes)}"
            mood = context.get("mood")
            if mood and mood in self.content_themes["mood"]:
                 themes = self.content_themes["mood"][mood]
                 if themes: enhanced_prompt += f"\n\nReflect the {mood} mood: {random.choice(themes)}"


        # Add dynamic cultural and historical enhancements if location is available
        if location and self.gmaps: # Check if location and gmaps client are available
            lat = location.get("latitude")
            lon = location.get("longitude")
            if lat is not None and lon is not None:
                location_info = self.extract_location_info(lat, lon)
                loc_name = location_info.get("locality") or location_info.get("formatted_address") or "this area"

                nearby_landmarks = self.get_nearby_landmarks(lat, lon, count=1)
                nearby_historical = self.get_nearby_historical_sites(lat, lon, count=1)
                nearby_cultural = self.get_nearby_cultural_venues(lat, lon, count=1)

                enhancement_text = f"\n\nContext for {loc_name}:"
                added_context = False
                if nearby_landmarks:
                    enhancement_text += f"\n- Nearby landmark: {nearby_landmarks[0]}"
                    added_context = True
                if nearby_historical:
                    enhancement_text += f"\n- Nearby historical site/museum: {nearby_historical[0]}"
                    added_context = True
                if nearby_cultural:
                    enhancement_text += f"\n- Nearby cultural venue: {nearby_cultural[0]}"
                    added_context = True

                if added_context:
                    enhanced_prompt += enhancement_text
                else:
                    # Fallback if no specific places found
                    enhanced_prompt += f"\n\nBriefly mention something interesting about {loc_name} if possible."

        logger.debug(f"Enhanced prompt: {enhanced_prompt}")
        return enhanced_prompt


    # --- Refactored Content Analysis Methods (remain the same) ---
    def analyze_content_safety(self, content: str, threshold: float = 0.6) -> Tuple[bool, List[str]]:
        # ... (implementation remains the same) ...
        if not self.language_client: logger.warning("Language client not initialized..."); return True, []
        if not content: return True, []
        try:
            document = language_v1.Document(content=content, type_=language_v1.Document.Type.PLAIN_TEXT)
            request = language_v1.ModerateTextRequest(document=document)
            response = self.language_client.moderate_text(request=request)
            harmful_categories = [cat.name for cat in response.moderation_categories if cat.confidence >= threshold]
            is_safe = len(harmful_categories) == 0
            if not is_safe: logger.info(f"Content safety check flagged categories: {harmful_categories}")
            return is_safe, harmful_categories
        except google_exceptions.InvalidArgument as e: logger.warning(f"Content safety check failed (InvalidArgument): {e}. Assuming safe."); return True, []
        except Exception as e: logger.error(f"Error during content safety analysis: {e}"); return True, []


    def analyze_sentiment(self, content: str) -> Dict[str, float]:
        # ... (implementation remains the same) ...
        default_sentiment = {"score": 0.0, "magnitude": 0.0}
        if not self.language_client: logger.warning("Language client not initialized..."); return default_sentiment
        if not content: return default_sentiment
        try:
            document = language_v1.Document(content=content, type_=language_v1.Document.Type.PLAIN_TEXT)
            response = self.language_client.analyze_sentiment(request={"document": document, "encoding_type": language_v1.EncodingType.UTF8})
            sentiment = response.document_sentiment
            logger.info(f"Sentiment analysis: Score={sentiment.score:.2f}, Magnitude={sentiment.magnitude:.2f}")
            return {"score": sentiment.score, "magnitude": sentiment.magnitude}
        except google_exceptions.InvalidArgument as e: logger.warning(f"Sentiment analysis failed (InvalidArgument): {e}. Returning default."); return default_sentiment
        except Exception as e: logger.error(f"Error during sentiment analysis: {e}"); return default_sentiment


# Create singleton instance
personalization_engine = PersonalizationEngine()

# Removed duplicate instance creation
# personalization_engine = PersonalizationEngine()
