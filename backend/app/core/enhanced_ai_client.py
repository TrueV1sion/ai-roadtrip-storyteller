from typing import Dict, List, Optional, Any, Union
import json
import logging
import uuid
import re
import time
from datetime import datetime

# import openai # Removed
from vertexai.generative_models import GenerationConfig, Part # Added for type hints if needed

from app.core.config import settings
from app.core.logger import get_logger
from app.core.personalization import personalization_engine
from app.core.ai_client import AIStorytellingClient # Base class now uses Vertex AI
from app.core.circuit_breaker import get_ai_circuit_breaker, CircuitOpenError

logger = get_logger(__name__)


class EnhancedAIStorytellingClient(AIStorytellingClient):
    """
    Enhanced AI client for storytelling with personalization features.
    Extends the base AIStorytellingClient (now using Vertex AI) with advanced
    prompt engineering, content safety, and personalization capabilities.
    NOTE: This client is now stateless regarding story ratings and history.
          This data should be handled and stored via DB interactions in routes/services.
    """

    def __init__(self):
        """Initialize the enhanced AI client."""
        super().__init__() # Initializes base client with Vertex AI model
        self.personalization = personalization_engine

        # Removed in-memory storage for ratings and history
        # self.story_ratings = {}
        # self.content_history = {}

        # System message templates (Keep)
        self.system_templates = {
            "default": (
                "You are an engaging storyteller for a road trip app, specializing "
                "in location-based narratives that capture the magic and wonder of "
                "each place, similar to Disney's Imagineering style."
            ),
            "educational": (
                "You are an educational storyteller for a road trip app, specializing "
                "in location-based narratives that inform and educate travelers about "
                "the history, culture, and natural wonders of each place they visit. "
                "Your stories are factually accurate yet engaging, weaving educational "
                "content into compelling narratives."
            ),
            "entertaining": (
                "You are an entertaining storyteller for a road trip app, specializing "
                "in location-based narratives that delight and captivate travelers. "
                "Your stories bring places to life with humor, wonder, and imagination, "
                "creating memorable experiences that enhance the journey."
            ),
            "family": (
                "You are a family-friendly storyteller for a road trip app, creating "
                "narratives that appeal to travelers of all ages. Your stories spark "
                "curiosity, imagination, and conversation, while remaining appropriate "
                "for young listeners. You incorporate educational elements, humor, and "
                "wonder in a way that engages both children and adults."
            )
        }

    async def generate_personalized_story(
        self,
        user_id: str, # Keep user_id for potential future use (e.g., logging)
        location: Dict[str, float],
        interests: List[str],
        user_preferences: Optional[Dict[str, Any]] = None, # Pass preferences directly
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate a personalized story based on user preferences and context using Vertex AI.

        Args:
            user_id: User identifier (for logging/context, not fetching prefs here)
            location: Dict containing 'latitude' and 'longitude'
            interests: List of user interests (e.g., ['history', 'nature'])
            user_preferences: User preference data fetched from DB
            context: Optional additional context (time of day, weather, etc.)

        Returns:
            Dict[str, Any]: Generated story data with metadata (excluding story_id)
        """
        start_time = time.time()
        # story_id generation should happen when saving to DB in the route/service
        # story_id = str(uuid.uuid4())

        # Ensure base client (and model) is initialized
        if not self.model:
             logger.error("Vertex AI client not initialized in base class.")
             fallback_story = self._get_fallback_story(location, interests)
             return {
                 # "id": story_id, # No ID generated here anymore
                 "text": fallback_story, "model": "fallback",
                 "generation_time": time.time() - start_time, "is_fallback": True
             }

        try:
            # Preferences are now passed in directly, no need to fetch/process here

            # Build base prompt (using inherited method)
            base_user_prompt = self._build_storytelling_prompt(location, interests, context)

            # Enhance prompt with personalization using passed-in preferences
            enhanced_user_prompt = self.personalization.enhance_prompt(
                base_user_prompt,
                user_preferences=user_preferences, # Pass preferences dict
                location=location,
                context=context
            )

            # Select appropriate storytelling style from passed-in preferences
            style = "balanced"
            if user_preferences and "storytelling_style" in user_preferences:
                style = user_preferences["storytelling_style"]

            # Select system template based on style
            if style in ["educational", "entertaining", "family"]:
                system_template = self.system_templates.get(style, self.system_templates["default"])
            else:
                system_template = self.system_templates["default"]

            # Add location-specific information to system template
            location_info = self.personalization.extract_location_info(
                location["latitude"],
                location["longitude"]
            )
            historical_facts = self.personalization.get_nearby_historical_sites(location["latitude"], location["longitude"], count=1)
            cultural_elements = self.personalization.get_nearby_cultural_venues(location["latitude"], location["longitude"], count=1)

            # Add facts to system context if available
            system_context = system_template
            if historical_facts or cultural_elements:
                loc_name = location_info.get("locality") or location_info.get("formatted_address") or "this area"
                system_context += f"\n\nFor context about {loc_name}:"
                if historical_facts:
                    system_context += f"\n- Nearby historical site/museum: {historical_facts[0]}"
                if cultural_elements:
                    system_context += f"\n- Nearby cultural venue: {cultural_elements[0]}"

            # Combine system context and enhanced user prompt for Vertex AI
            full_prompt = f"{system_context}\n\n{enhanced_user_prompt}"

            vertex_model_name = settings.GOOGLE_AI_MODEL

            logger.info(f"Generating personalized story with model {vertex_model_name} for user {user_id}")
            generation_params = self._get_vertex_generation_parameters(style)

            # Call Vertex AI API via base class model with circuit breaker protection
            try:
                ai_circuit_breaker = get_ai_circuit_breaker()
                response = await ai_circuit_breaker.call_async(
                    self.model.generate_content_async,
                    [Part.from_text(full_prompt)],
                    generation_config=generation_params,
                )
                story_text = response.text
            except CircuitOpenError as e:
                logger.error(f"AI service circuit breaker is open: {e}")
                # Return a fallback story when circuit is open
                fallback_story = self._get_fallback_story(location, interests)
                return {
                    "text": fallback_story,
                    "model": "fallback",
                    "generation_time": time.time() - start_time,
                    "is_fallback": True,
                    "circuit_breaker_open": True
                }

            # Check content safety (using personalization engine)
            is_safe, safety_issues = self.personalization.analyze_content_safety(story_text)
            if not is_safe:
                logger.warning(f"Safety issues detected in story for user {user_id}: {safety_issues}")
                story_text = self._clean_content(story_text) or self._get_fallback_story(location, interests)

            # Analyze sentiment (using personalization engine)
            sentiment = self.personalization.analyze_sentiment(story_text)

            # Removed in-memory content history storage

            generation_time = time.time() - start_time
            logger.info(f"Personalized story generated for user {user_id} in {generation_time:.2f}s")

            # Return story with metadata (without ID)
            return {
                # "id": story_id, # ID will be assigned by DB on save
                "text": story_text,
                "model": vertex_model_name,
                "generation_time": generation_time,
                "sentiment": sentiment,
                "word_count": len(story_text.split())
            }

        except Exception as e:
            logger.error(f"Error generating personalized story for user {user_id} with Vertex AI: {str(e)}")
            fallback_story = self._get_fallback_story(location, interests)
            return {
                # "id": story_id,
                "text": fallback_story,
                "model": "fallback",
                "generation_time": time.time() - start_time,
                "is_fallback": True
            }

    # Vertex AI generation parameters method (remains the same)
    def _get_vertex_generation_parameters(self, style: str) -> GenerationConfig:
        """
        Get Vertex AI GenerationConfig based on storytelling style.
        """
        # Adjust parameters based on style
        if style == "educational":
            return GenerationConfig(
                max_output_tokens=600,
                temperature=0.5,
                top_p=0.9,
            )
        elif style == "entertaining":
            return GenerationConfig(
                max_output_tokens=600,
                temperature=0.8,
                top_p=0.95,
            )
        else:  # balanced or default
            return GenerationConfig(
                max_output_tokens=600,
                temperature=0.7,
                top_p=0.9,
            )

    # Content cleaning method (remains the same)
    def _clean_content(self, content: str) -> Optional[str]:
        """
        Attempt to clean potentially problematic content. (Keep placeholder)
        """
        # This is a simplified implementation
        terms_to_redact = ["inappropriate", "explicit", "violent"]
        cleaned_content = content
        for term in terms_to_redact:
            cleaned_content = re.sub(
                rf'\b{re.escape(term)}\b',
                "[suitable for all ages]",
                cleaned_content,
                flags=re.IGNORECASE
            )
        return cleaned_content

    # Removed in-memory feedback methods
    # def record_story_rating(...) -> None: ...
    # def get_story_feedback(...) -> List[Dict[str, Any]]: ...
    # def get_average_rating(...) -> Optional[float]: ...

    # Fallback story method is inherited from base class
    # def _get_fallback_story(...) -> str: ...


# Create singleton instance
enhanced_ai_client = EnhancedAIStorytellingClient()
