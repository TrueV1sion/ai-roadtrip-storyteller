from typing import Dict, List, Optional, Any, Union
import json
import logging
import uuid
import re
import time
from datetime import datetime
from enum import Enum

import vertexai
from vertexai.generative_models import (
    GenerativeModel, 
    GenerationConfig, 
    Part,
    GenerationResponse,
    Content
)

from app.core.config import settings
from app.core.logger import get_logger
from app.core.personalization import personalization_engine
from app.core.google_cloud_auth import google_cloud_auth

logger = get_logger(__name__)


class StoryStyle(str, Enum):
    """Enumeration of storytelling styles."""
    DEFAULT = "default"
    EDUCATIONAL = "educational"
    ENTERTAINING = "entertaining"
    FAMILY = "family"
    HISTORIC = "historic"
    ADVENTURE = "adventure"
    MYSTERY = "mystery"


class AIModelProvider(str, Enum):
    """Enumeration of AI model providers."""
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    MISTRAL = "mistral"
    CUSTOM = "custom"
    FALLBACK = "fallback"


class UnifiedAIClient:
    """
    Unified AI client that provides a consistent interface for all AI operations
    in the application, focusing on Google's Vertex AI (Gemini) by default but
    designed to support multiple providers.
    """
    
    def __init__(self, initialize_now: bool = True):
        """
        Initialize the unified AI client.

        Args:
            initialize_now: Whether to initialize the AI models immediately
        """
        self.provider = settings.DEFAULT_AI_PROVIDER if hasattr(settings, 'DEFAULT_AI_PROVIDER') else AIModelProvider.GOOGLE
        self.model = None
        self.personalization = personalization_engine
        self.initialized = False
        
        # Session memory for maintaining conversation context
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
        # System prompt templates for different storytelling styles
        self.system_templates = {
            StoryStyle.DEFAULT: (
                "You are an engaging storyteller for a road trip app, specializing "
                "in location-based narratives that capture the magic and wonder of "
                "each place, similar to Disney's Imagineering style."
            ),
            StoryStyle.EDUCATIONAL: (
                "You are an educational storyteller for a road trip app, specializing "
                "in location-based narratives that inform and educate travelers about "
                "the history, culture, and natural wonders of each place they visit. "
                "Your stories are factually accurate yet engaging, weaving educational "
                "content into compelling narratives."
            ),
            StoryStyle.ENTERTAINING: (
                "You are an entertaining storyteller for a road trip app, specializing "
                "in location-based narratives that delight and captivate travelers. "
                "Your stories bring places to life with humor, wonder, and imagination, "
                "creating memorable experiences that enhance the journey."
            ),
            StoryStyle.FAMILY: (
                "You are a family-friendly storyteller for a road trip app, creating "
                "narratives that appeal to travelers of all ages. Your stories spark "
                "curiosity, imagination, and conversation, while remaining appropriate "
                "for young listeners. You incorporate educational elements, humor, and "
                "wonder in a way that engages both children and adults."
            ),
            StoryStyle.HISTORIC: (
                "You are a historically-minded storyteller for a road trip app, weaving "
                "narratives that connect travelers to the rich past of each location. "
                "You highlight significant historical events, figures, and landmarks, "
                "bringing history to life in a way that's engaging and meaningful to modern "
                "travelers. Your stories are thoroughly researched and accurate while remaining "
                "engaging and accessible."
            ),
            StoryStyle.ADVENTURE: (
                "You are an adventure-focused storyteller for a road trip app, creating "
                "narratives that emphasize the thrill of exploration and discovery. "
                "Your stories highlight the unique adventures possible at each location, "
                "from hidden hiking trails to exhilarating viewpoints. You instill a sense "
                "of excitement and possibility while encouraging travelers to safely step "
                "outside their comfort zones."
            ),
            StoryStyle.MYSTERY: (
                "You are a mystery-weaving storyteller for a road trip app, crafting "
                "intriguing narratives that hint at the secrets and mysteries of each location. "
                "You incorporate legends, unsolved historical questions, and fascinating local "
                "lore into your stories, creating an air of intrigue that encourages travelers "
                "to look deeper and ask questions about the places they visit."
            )
        }
        
        # Initialize Vertex AI if requested
        if initialize_now:
            self.initialize()
        
    def initialize(self) -> bool:
        """
        Initialize the AI provider and models.
        
        Returns:
            bool: Whether initialization was successful
        """
        if self.initialized:
            return True
            
        try:
            if self.provider == AIModelProvider.GOOGLE:
                self._initialize_vertex_ai()
            else:
                logger.warning(f"Provider {self.provider} not currently supported, falling back to Google AI")
                self.provider = AIModelProvider.GOOGLE
                self._initialize_vertex_ai()
                
            self.initialized = True
            logger.info(f"Unified AI client initialized with provider: {self.provider}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize AI client: {str(e)}")
            self.initialized = False
            return False
    
    def _initialize_vertex_ai(self) -> None:
        """Initialize Google's Vertex AI (Gemini) model."""
        try:
            # Ensure Google Cloud authentication is set up
            if not google_cloud_auth.initialize():
                raise Exception("Google Cloud authentication failed")
            
            # Get credentials and project ID
            credentials = google_cloud_auth.get_credentials()
            project_id = google_cloud_auth.get_project_id() or settings.GOOGLE_AI_PROJECT_ID
            
            if not project_id:
                raise Exception("Google Cloud project ID not configured")
            
            # Initialize Vertex AI with project, location, and credentials
            vertexai.init(
                project=project_id,
                location=settings.GOOGLE_AI_LOCATION,
                credentials=credentials
            )
            
            # Load the model
            model_name = settings.GOOGLE_AI_MODEL
            self.model = GenerativeModel(model_name)
            
            logger.info(f"Vertex AI initialized with model: {model_name} in project: {project_id}")
            
            # Validate permissions
            permissions = google_cloud_auth.validate_permissions()
            if not permissions.get('vertex_ai', False):
                logger.warning("Vertex AI permissions may be insufficient")
            
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {str(e)}")
            logger.error("Please check your Google Cloud service account configuration")
            self.model = None
            raise
    
    async def generate_story(
        self,
        location: Dict[str, float],
        interests: List[str],
        context: Optional[Dict[str, Any]] = None,
        style: StoryStyle = StoryStyle.DEFAULT,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a location-based story.
        
        Args:
            location: Dictionary with 'latitude' and 'longitude'
            interests: List of user interests
            context: Optional context information (weather, time, etc.)
            style: Storytelling style
            conversation_id: Optional ID for maintaining conversation context
            
        Returns:
            Dict with story text and metadata
        """
        start_time = time.time()
        
        # Make sure we're initialized
        if not self.initialized:
            success = self.initialize()
            if not success:
                return self._create_fallback_response(
                    location, interests, start_time,
                    "AI client initialization failed"
                )
        
        # Get the appropriate system template for the style
        system_template = self.system_templates.get(style, self.system_templates[StoryStyle.DEFAULT])
        
        try:
            # Build the user prompt
            user_prompt = self._build_storytelling_prompt(location, interests, context)
            
            # Enhance with personalization if context is provided
            if context:
                user_prompt = self.personalization.enhance_prompt(
                    user_prompt,
                    user_preferences=context.get("user_preferences"),
                    location=location,
                    context=context
                )
            
            # Get conversation history if provided
            history = None
            if conversation_id:
                history = self._get_session_history(conversation_id)
                if history:
                    user_prompt += f"\n\nPrevious conversation context:\n{history}"
            
            # Add location context to system prompt
            enhanced_system = self._enhance_system_prompt_with_location(system_template, location)
            
            # Generate the story based on provider
            story_text = await self._generate_with_provider(enhanced_system, user_prompt, style)
            
            if not story_text:
                return self._create_fallback_response(
                    location, interests, start_time,
                    "No story generated by AI provider"
                )
            
            # Update session if conversation ID provided
            if conversation_id:
                self._update_session(conversation_id, user_prompt, story_text)
            
            # Check for content safety
            is_safe, safety_issues = self.personalization.analyze_content_safety(story_text)
            if not is_safe:
                logger.warning(f"Safety issues detected in story: {safety_issues}")
                story_text = self._clean_content(story_text)
                if not story_text:
                    return self._create_fallback_response(
                        location, interests, start_time,
                        f"Content safety issues: {safety_issues}"
                    )
            
            # Analyze sentiment
            sentiment = self.personalization.analyze_sentiment(story_text)
            
            # Calculate generation time
            generation_time = time.time() - start_time
            
            # Return story with metadata
            return {
                "text": story_text,
                "provider": self.provider,
                "model": self._get_model_name(),
                "style": style,
                "generation_time": generation_time,
                "word_count": len(story_text.split()),
                "sentiment": sentiment,
                "is_fallback": False
            }
            
        except Exception as e:
            logger.error(f"Error generating story: {str(e)}")
            return self._create_fallback_response(
                location, interests, start_time,
                f"Exception: {str(e)}"
            )
    
    async def generate_personalized_story(
        self,
        user_id: Optional[str],
        location: Dict[str, float],
        interests: List[str],
        user_preferences: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        style: Optional[StoryStyle] = None
    ) -> Dict[str, Any]:
        """
        Generate a personalized story based on user preferences.
        
        Args:
            user_id: Optional user identifier for logging and context
            location: Dictionary with 'latitude' and 'longitude'
            interests: List of user interests
            user_preferences: User preferences for personalization
            context: Optional additional context
            style: Optional storytelling style (will be derived from preferences if not provided)
            
        Returns:
            Dict with story text and metadata
        """
        start_time = time.time()
        
        # Determine style from preferences if not provided
        if not style and user_preferences and "storytelling_style" in user_preferences:
            pref_style = user_preferences["storytelling_style"]
            try:
                style = StoryStyle(pref_style)
            except ValueError:
                style = StoryStyle.DEFAULT
                logger.warning(f"Unknown storytelling style: {pref_style}, using default")
        
        if not style:
            style = StoryStyle.DEFAULT
        
        # Make sure we're initialized
        if not self.initialized:
            success = self.initialize()
            if not success:
                return self._create_fallback_response(
                    location, interests, start_time,
                    "AI client initialization failed"
                )
        
        try:
            # Combine context with user preferences
            enhanced_context = context or {}
            if user_preferences:
                enhanced_context["user_preferences"] = user_preferences
            
            # Call the base story generation method with enhanced context
            story_result = await self.generate_story(
                location=location,
                interests=interests,
                context=enhanced_context,
                style=style
            )
            
            # Add user ID to the result if provided
            if user_id:
                story_result["user_id"] = user_id
            
            return story_result
            
        except Exception as e:
            logger.error(f"Error generating personalized story for user {user_id}: {str(e)}")
            return self._create_fallback_response(
                location, interests, start_time,
                f"Exception in personalization: {str(e)}"
            )
    
    async def _generate_with_provider(
        self,
        system_prompt: str,
        user_prompt: str,
        style: StoryStyle
    ) -> Optional[str]:
        """
        Generate content using the configured AI provider.
        
        Args:
            system_prompt: System instructions
            user_prompt: User query or prompt
            style: Storytelling style for parameter tuning
            
        Returns:
            Generated text or None if generation failed
        """
        if self.provider == AIModelProvider.GOOGLE:
            return await self._generate_with_vertex(system_prompt, user_prompt, style)
        else:
            logger.warning(f"Provider {self.provider} not implemented, falling back to Vertex AI")
            return await self._generate_with_vertex(system_prompt, user_prompt, style)
    
    async def _generate_with_vertex(
        self,
        system_prompt: str,
        user_prompt: str,
        style: StoryStyle
    ) -> Optional[str]:
        """
        Generate content using Google's Vertex AI (Gemini).
        
        Args:
            system_prompt: System instructions
            user_prompt: User query or prompt
            style: Storytelling style for parameter tuning
            
        Returns:
            Generated text or None on failure
        """
        if not self.model:
            logger.error("Vertex AI model not initialized")
            return None
        
        try:
            # Combine prompts (Gemini doesn't have separate system prompts)
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            # Get generation parameters based on style
            generation_config = self._get_generation_config(style)
            
            # Call Gemini API
            response = await self.model.generate_content_async(
                [Part.from_text(full_prompt)],
                generation_config=generation_config
            )
            
            # Check if response has text
            if hasattr(response, 'text') and response.text:
                return response.text
            else:
                logger.warning("Empty response from Vertex AI")
                return None
                
        except Exception as e:
            logger.error(f"Error in Vertex AI generation: {str(e)}")
            return None
    
    def _get_generation_config(self, style: StoryStyle) -> GenerationConfig:
        """
        Get generation parameters tuned for the specified storytelling style.
        
        Args:
            style: Storytelling style
            
        Returns:
            GenerationConfig with appropriate parameters
        """
        # Base parameters
        max_tokens = 600
        temperature = 0.7
        top_p = 0.9
        top_k = 40
        
        # Adjust parameters based on style
        if style == StoryStyle.EDUCATIONAL:
            temperature = 0.5  # More factual
            top_p = 0.85
        elif style == StoryStyle.ENTERTAINING:
            temperature = 0.8  # More creative
            top_p = 0.95
        elif style == StoryStyle.FAMILY:
            max_tokens = 500  # Shorter for kids
            temperature = 0.65
        elif style == StoryStyle.HISTORIC:
            temperature = 0.45  # More factual
            top_p = 0.8
            max_tokens = 700  # More detail for historical context
        elif style == StoryStyle.ADVENTURE:
            temperature = 0.85  # More creative
            top_p = 0.95
        elif style == StoryStyle.MYSTERY:
            temperature = 0.75  # Balance of creativity and coherence
            top_p = 0.9
            
        return GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k
        )
    
    def _build_storytelling_prompt(
        self,
        location: Dict[str, float],
        interests: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build a user prompt for storytelling.
        
        Args:
            location: Dictionary with 'latitude' and 'longitude'
            interests: List of user interests
            context: Optional additional context
            
        Returns:
            Formatted user prompt
        """
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
                
            # Add mood if specified
            if 'mood' in context:
                base_prompt += (
                    f"\nThe desired mood for the story is: "
                    f"{context['mood']}"
                )
                
            # Add specific requests
            if 'special_requests' in context:
                base_prompt += (
                    f"\nSpecial requests: "
                    f"{context['special_requests']}"
                )

        return base_prompt
    
    def _enhance_system_prompt_with_location(
        self,
        system_prompt: str,
        location: Dict[str, float]
    ) -> str:
        """
        Enhance the system prompt with location-specific information.
        
        Args:
            system_prompt: Base system prompt
            location: Dictionary with 'latitude' and 'longitude'
            
        Returns:
            Enhanced system prompt with location context
        """
        try:
            # Get location information
            location_info = self.personalization.extract_location_info(
                location["latitude"],
                location["longitude"]
            )
            
            # Get nearby points of interest
            historical_facts = self.personalization.get_nearby_historical_sites(
                location["latitude"], 
                location["longitude"], 
                count=1
            )
            
            cultural_elements = self.personalization.get_nearby_cultural_venues(
                location["latitude"], 
                location["longitude"], 
                count=1
            )
            
            # If we have location info, add it to the system prompt
            enhanced_prompt = system_prompt
            if location_info or historical_facts or cultural_elements:
                loc_name = (
                    location_info.get("locality") or 
                    location_info.get("formatted_address") or 
                    "this area"
                )
                
                enhanced_prompt += f"\n\nFor context about {loc_name}:"
                
                # Add formatted address if available
                if location_info and "formatted_address" in location_info:
                    enhanced_prompt += f"\n- Location: {location_info['formatted_address']}"
                
                # Add place details if available
                if location_info and "place_type" in location_info:
                    enhanced_prompt += f"\n- Place type: {location_info['place_type']}"
                
                # Add historical sites if available
                if historical_facts:
                    enhanced_prompt += f"\n- Nearby historical site: {historical_facts[0]}"
                
                # Add cultural venues if available
                if cultural_elements:
                    enhanced_prompt += f"\n- Nearby cultural venue: {cultural_elements[0]}"
            
            return enhanced_prompt
            
        except Exception as e:
            logger.warning(f"Error enhancing system prompt with location: {e}")
            return system_prompt
    
    def _update_session(
        self,
        conversation_id: str,
        user_message: str,
        ai_response: str
    ) -> None:
        """
        Update session memory with the latest exchange.
        
        Args:
            conversation_id: Unique session identifier
            user_message: User's message or prompt
            ai_response: AI's response
        """
        if conversation_id not in self.sessions:
            self.sessions[conversation_id] = {
                "messages": [],
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            }
        
        # Update messages array
        self.sessions[conversation_id]["messages"].append(
            {"role": "user", "content": user_message[:500]}  # Truncate for brevity
        )
        self.sessions[conversation_id]["messages"].append(
            {"role": "assistant", "content": ai_response[:500]}  # Truncate for brevity
        )
        
        # Update last_updated timestamp
        self.sessions[conversation_id]["last_updated"] = datetime.now().isoformat()
        
        # Limit session history length
        if len(self.sessions[conversation_id]["messages"]) > 10:
            self.sessions[conversation_id]["messages"] = self.sessions[conversation_id]["messages"][-10:]
    
    def _get_session_history(self, conversation_id: str) -> Optional[str]:
        """
        Get formatted session history for a conversation.
        
        Args:
            conversation_id: Unique session identifier
            
        Returns:
            Formatted history string or None if no history
        """
        if conversation_id not in self.sessions or not self.sessions[conversation_id]["messages"]:
            return None
        
        # Format messages into a string
        messages = self.sessions[conversation_id]["messages"]
        formatted_history = []
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            formatted_history.append(f"{role.capitalize()}: {content}")
        
        return "\n".join(formatted_history)
    
    def _clean_content(self, content: str) -> Optional[str]:
        """
        Attempt to clean potentially problematic content.
        
        Args:
            content: Content to clean
            
        Returns:
            Cleaned content or None if cleaning failed
        """
        if not content:
            return None
            
        try:
            # Words to look for and redact
            terms_to_redact = ["inappropriate", "explicit", "violent", "offensive", "disturbing"]
            
            # Check if any terms are present
            has_problematic_content = any(re.search(rf'\b{re.escape(term)}\b', content, re.IGNORECASE) for term in terms_to_redact)
            
            if has_problematic_content:
                # If problematic content is detected, redact those terms
                cleaned_content = content
                for term in terms_to_redact:
                    cleaned_content = re.sub(
                        rf'\b{re.escape(term)}\b',
                        "[suitable for all ages]",
                        cleaned_content,
                        flags=re.IGNORECASE
                    )
                logger.info("Content cleaned: Potentially problematic terms redacted")
                return cleaned_content
            else:
                # If no problematic terms found, return the original content
                return content
                
        except Exception as e:
            logger.error(f"Error cleaning content: {str(e)}")
            return None
    
    def _create_fallback_response(
        self,
        location: Dict[str, float],
        interests: List[str],
        start_time: float,
        error_msg: str
    ) -> Dict[str, Any]:
        """
        Create a response with fallback content when generation fails.
        
        Args:
            location: Dictionary with 'latitude' and 'longitude'
            interests: List of user interests
            start_time: Time when generation started
            error_msg: Error message for logging
            
        Returns:
            Response dictionary with fallback content
        """
        fallback_text = self._get_fallback_story(location, interests)
        
        logger.warning(f"Using fallback story due to error: {error_msg}")
        
        return {
            "text": fallback_text,
            "provider": AIModelProvider.FALLBACK,
            "model": "fallback",
            "generation_time": time.time() - start_time,
            "word_count": len(fallback_text.split()),
            "is_fallback": True,
            "error": error_msg
        }
    
    def _get_fallback_story(
        self,
        location: Dict[str, float],
        interests: List[str]
    ) -> str:
        """
        Provide a generic fallback story when AI generation fails.
        
        Args:
            location: Dictionary with 'latitude' and 'longitude'
            interests: List of user interests
            
        Returns:
            Fallback story text
        """
        lat = location.get("latitude", "an unknown latitude")
        lng = location.get("longitude", "an unknown longitude")
        interest_text = ", ".join(interests) if interests else "the journey"

        return f"""
        As we travel near coordinates {lat}, {lng}, let's take a moment to appreciate 
        the journey itself. Every road trip has its own story to tell - the changing 
        landscapes outside your window, the conversations with fellow travelers, and 
        the anticipation of what lies ahead.
        
        While I don't have a specific story about this exact location right now, 
        I encourage you to look around and create your own narrative. What do you see? 
        What makes this place unique? If you're interested in {interest_text}, 
        keep your eyes open for signs and landmarks that might connect to those interests.
        
        The magic of road trips often lies in the unexpected discoveries. Perhaps 
        around the next bend, you'll find something truly remarkable that becomes 
        part of your own travel story – one that you'll share for years to come.
        
        Safe travels, and enjoy the continuing adventure!
        """
    
    def _get_model_name(self) -> str:
        """Get the name of the currently loaded model."""
        if self.provider == AIModelProvider.GOOGLE:
            return settings.GOOGLE_AI_MODEL
        elif self.provider == AIModelProvider.OPENAI:
            return "openai_model"  # Would come from settings
        elif self.provider == AIModelProvider.ANTHROPIC:
            return "anthropic_model"  # Would come from settings
        else:
            return "unknown_model"


# Create a singleton instance
unified_ai_client = UnifiedAIClient()


def get_unified_ai_client() -> UnifiedAIClient:
    """
    Get the singleton instance of the unified AI client.
    
    Returns:
        UnifiedAIClient: The singleton instance
    """
    return unified_ai_client