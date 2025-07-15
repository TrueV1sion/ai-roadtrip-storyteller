from typing import Dict, List, Optional
# import openai # Removed
import vertexai
from vertexai.generative_models import GenerativeModel
from vertexai.generative_models import GenerationConfig, HarmCategory, HarmBlockThreshold
from vertexai.generative_models import Content, Part
from app.core.config import settings
from app.core.logger import get_logger
from app.core.circuit_breaker import get_ai_circuit_breaker, CircuitOpenError
import time
import random
import asyncio

logger = get_logger(__name__)

class AIStorytellingClient:
    def __init__(self):
        # openai.api_key = settings.OPENAI_API_KEY # Removed
        # self.model = settings.GPT_MODEL_NAME # Removed

        # Initialize Vertex AI
        try:
            vertexai.init(
                project=settings.GOOGLE_AI_PROJECT_ID,
                location=settings.GOOGLE_AI_LOCATION,
            )
            # Load the generative model
            self.model = GenerativeModel(settings.GOOGLE_AI_MODEL)
            logger.info(f"Vertex AI client initialized with model: {settings.GOOGLE_AI_MODEL}")
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI client: {str(e)}")
            # Depending on requirements, might want to raise or handle differently
            self.model = None # Indicate initialization failure

        # Keep session memory for now, might be replaced by ChatSession later
        self.session_memory: Dict[str, List[str]] = {}

    async def generate_location_story(
        self,
        location: Dict[str, float],
        interests: List[str],
        context: Optional[Dict] = None
    ) -> str:
        """
        Generate a story based on location and user interests using Vertex AI.

        Args:
            location: Dict containing 'latitude' and 'longitude'
            interests: List of user interests (e.g., ['history', 'nature'])
            context: Optional additional context (time of day, weather, etc.)

        Returns:
            str: Generated story text
        """
        if not self.model:
             logger.error("Vertex AI client not initialized.")
             return self._get_fallback_story(location, interests) # Use a fallback

        try:
            # Construct the prompt based on location and interests
            # Combine system message and user prompt for Gemini
            system_msg = (
                "You are an engaging storyteller for a road trip app, specializing "
                "in location-based narratives that capture the magic and wonder of "
                "each place, similar to Disney's Imagineering style."
            )
            user_prompt = self._build_storytelling_prompt(location, interests, context)
            full_prompt = f"{system_msg}\n\n{user_prompt}" # Combine prompts

            # Configure generation parameters
            generation_config = GenerationConfig(
                temperature=0.7,
                max_output_tokens=500, # Keep similar token limit
                # Add other relevant Gemini parameters if needed (top_p, top_k)
            )

            # Generate the story using Vertex AI with circuit breaker protection
            ai_circuit_breaker = get_ai_circuit_breaker()
            try:
                response = await ai_circuit_breaker.call_async(
                    self.model.generate_content_async,  # Use async version
                    [Part.from_text(full_prompt)],  # Pass prompt as Part
                    generation_config=generation_config,
                    # stream=False # Default is False
                )
                # Extract text - handle potential safety blocks later if needed
                return response.text
            except CircuitOpenError as e:
                logger.error(f"AI service circuit breaker is open: {e}")
                return self._get_fallback_story(location, interests)

        except Exception as e:
            logger.error(f"Error generating story with Vertex AI: {str(e)}")
            return self._get_fallback_story(location, interests) # Use a fallback

    def _build_storytelling_prompt(
        self,
        location: Dict[str, float],
        interests: List[str],
        context: Optional[Dict] = None
    ) -> str:
        """Build a prompt for the storytelling AI based on location and interests."""
        # This method remains largely the same, as it constructs the user-facing part
        # of the prompt based on input data.
        lat = location.get('latitude', 'N/A')
        lng = location.get('longitude', 'N/A')
        base_prompt = f"""
        Create an engaging, family-friendly story about the location at coordinates
        {lat}, {lng}.

        The audience is interested in: {', '.join(interests)}

        Make the story:
        1. Brief (2-3 minutes when read aloud)
        2. Educational yet entertaining
        3. Appropriate for all ages
        4. Include a touch of magic or wonder
        5. Relate to the visible surroundings when possible
        """

        if context:
            # Add time-of-day appropriate elements
            if 'time_of_day' in context:
                base_prompt += (
                    f"\nThe story should fit the current time: "
                    f"{context['time_of_day']}"
                )

            # Add weather-appropriate elements
            if 'weather' in context:
                base_prompt += (
                    f"\nIncorporate the current weather: "
                    f"{context['weather']}"
                )

            # Add session history if available
            # Note: Gemini's multi-turn chat might handle this better,
            # but we keep it for now to match existing logic.
            if 'session_history' in context:
                base_prompt += (
                    f"\n\nConversation history:\n"
                    f"{context['session_history']}"
                )

        return base_prompt

    def update_session(self, conversation_id: str, user_message: str, ai_response: str) -> None:
        """Update the session memory with the latest user message and AI response."""
        # Keep this logic for now, used by generate_story_with_session
        if conversation_id not in self.session_memory:
            self.session_memory[conversation_id] = []
        # Limit stored message length to avoid excessive memory use
        self.session_memory[conversation_id].append(f"User: {user_message[:500]}...")
        self.session_memory[conversation_id].append(f"AI: {ai_response[:500]}...")
        # Limit history length
        if len(self.session_memory[conversation_id]) > 10: # Keep last 5 turns (10 messages)
             self.session_memory[conversation_id] = self.session_memory[conversation_id][-10:]


    def get_conversation_history(self, conversation_id: str) -> Optional[str]:
        """Retrieve the conversation history for a given session."""
        # Keep this logic for now
        if conversation_id in self.session_memory:
            return "\n".join(self.session_memory[conversation_id])
        return None

    async def generate_story_with_session(
        self,
        conversation_id: str,
        location: Dict[str, float],
        interests: List[str],
        context: Optional[Dict] = None
    ) -> str:
        """Generate a story using Vertex AI while maintaining multi-turn conversation context."""
        if not self.model:
             logger.error("Vertex AI client not initialized.")
             return self._get_fallback_story(location, interests)

        if context is None:
            context = {}
        history = self.get_conversation_history(conversation_id)
        if history:
            context["session_history"] = history # Add history to context for prompt building

        # Construct the prompt using the shared builder
        system_msg = (
            "You are an engaging storyteller for a road trip app, specializing "
            "in location-based narratives that capture the magic and wonder of "
            "each place, similar to Disney's Imagineering style."
        )
        user_prompt = self._build_storytelling_prompt(location, interests, context)
        full_prompt = f"{system_msg}\n\n{user_prompt}" # Combine prompts

        try:
            # Configure generation parameters
            generation_config = GenerationConfig(
                temperature=0.7,
                max_output_tokens=500,
            )

            # Generate the story using Vertex AI with circuit breaker protection
            ai_circuit_breaker = get_ai_circuit_breaker()
            try:
                response = await ai_circuit_breaker.call_async(
                    self.model.generate_content_async,
                    [Part.from_text(full_prompt)],
                    generation_config=generation_config,
                )
                ai_response = response.text
            except CircuitOpenError as e:
                logger.error(f"AI service circuit breaker is open: {e}")
                return self._get_fallback_story(location, interests)
            # Update session memory with the actual prompt sent and the response
            self.update_session(conversation_id, user_prompt, ai_response)
            return ai_response

        except Exception as e:
            logger.error(f"Error generating story with session using Vertex AI: {str(e)}")
            return self._get_fallback_story(location, interests)

    def _get_fallback_story(
        self,
        location: Dict[str, float],
        interests: List[str]
    ) -> str:
        """Provide a generic fallback story when AI generation fails."""
        # This can be kept as a simple, static fallback
        lat = location.get("latitude", "an unknown latitude")
        lng = location.get("longitude", "an unknown longitude")
        interest_text = ", ".join(interests) if interests else "the journey"

        return f"""
        As we travel near coordinates {lat}, {lng}, let's imagine the tales this place could tell.
        Every location holds secrets and stories waiting to be discovered. While I'm unable
        to weave a specific narrative right now, think about the {interest_text} that draws you here.
        Perhaps you can spot something related to it nearby? The adventure often lies in
        observing and creating your own connections to the world around you. Keep exploring!
        """

# Remove unused function and dictionary
# DEFAULT_STORIES = { ... }
# def get_story(prompt: str) -> str: ...

# Create singleton instance
ai_client = AIStorytellingClient()