from typing import Dict, List, Optional, Any
import os
import json
from vertexai.generative_models import GenerativeModel, GenerationConfig
import vertexai

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class GoogleAIStorytellingClient:
    """Client for Google's Vertex AI (Gemini) for story generation."""
    
    def __init__(self):
        try:
            # Initialize Vertex AI with project and location
            vertexai.init(
                project=settings.GOOGLE_AI_PROJECT_ID,
                location=settings.GOOGLE_AI_LOCATION,
            )
            
            # Load the model
            self.model = GenerativeModel(settings.GOOGLE_AI_MODEL)
            
            # Session memory for conversation context
            self.session_memory = {}
            
            logger.info(f"Google AI client initialized with model: {settings.GOOGLE_AI_MODEL}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google AI client: {str(e)}")
            raise
    
    async def generate_story_with_session(
        self,
        conversation_id: str,
        location: Dict[str, float],
        interests: List[str],
        context: Optional[Dict] = None
    ) -> str:
        """
        Generate a story using Google's Vertex AI with session context.
        
        Args:
            conversation_id: Unique identifier for the conversation session
            location: Location data with 'latitude' and 'longitude'
            interests: List of user interests
            context: Optional additional context
        
        Returns:
            str: Generated story text
        """
        try:
            # Get conversation history
            history = self.get_conversation_history(conversation_id)
            
            # Format prompt
            prompt = self._format_story_prompt(location, interests, context, history)
            
            # Configure generation parameters
            generation_config = GenerationConfig(
                temperature=0.7,
                max_output_tokens=1024,
                top_p=0.8,
                top_k=40
            )
            
            # Generate content
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Extract story text
            story = response.text
            
            # Update session memory
            self.update_session(conversation_id, prompt, story)
            
            return story
            
        except Exception as e:
            logger.error(f"Error generating story with Google AI: {str(e)}")
            return self._get_fallback_story(location, interests)
    
    def _format_story_prompt(
        self,
        location: Dict[str, float],
        interests: List[str],
        context: Optional[Dict] = None,
        history: Optional[str] = None
    ) -> str:
        """Format prompt for story generation."""
        lat = location.get("latitude")
        lng = location.get("longitude")
        
        base_prompt = f"""
        Create an engaging, family-friendly story about the location at coordinates {lat}, {lng}.
        
        The audience is interested in: {', '.join(interests)}
        
        Make the story:
        1. Brief (2-3 minutes when read aloud)
        2. Educational yet entertaining
        3. Appropriate for all ages
        4. Include a touch of magic or wonder
        5. Relate to the visible surroundings when possible
        """
        
        if context:
            if 'time_of_day' in context:
                base_prompt += f"\nThe current time is: {context['time_of_day']}"
                
            if 'weather' in context:
                base_prompt += f"\nThe current weather is: {context['weather']}"
                
            if 'mood' in context:
                base_prompt += f"\nThe desired mood for the story is: {context['mood']}"
        
        if history:
            base_prompt += f"\n\nPrevious conversation context:\n{history}"
        
        return base_prompt
    
    def update_session(
        self,
        conversation_id: str,
        user_message: str,
        ai_response: str
    ) -> None:
        """Update session memory with conversation history."""
        if conversation_id not in self.session_memory:
            self.session_memory[conversation_id] = []
            
        # Keep context concise to avoid exceeding token limits
        self.session_memory[conversation_id].append(f"User request: {user_message[:100]}...")
        self.session_memory[conversation_id].append(f"AI response: {ai_response[:100]}...")
        
        # Limit history length
        if len(self.session_memory[conversation_id]) > 10:
            self.session_memory[conversation_id] = self.session_memory[conversation_id][-10:]
    
    def get_conversation_history(self, conversation_id: str) -> Optional[str]:
        """Retrieve conversation history for a given session."""
        if conversation_id in self.session_memory:
            return "\n".join(self.session_memory[conversation_id])
        return None
    
    def _get_fallback_story(
        self,
        location: Dict[str, float],
        interests: List[str]
    ) -> str:
        """Provide a fallback story when AI generation fails."""
        lat = location.get("latitude", 0)
        lng = location.get("longitude", 0)
        interest_text = ", ".join(interests) if interests else "travel"
        
        return f"""
        As we travel along this stretch of road at coordinates {lat}, {lng}, 
        let's take a moment to appreciate the journey itself. Every road trip 
        has its own story - the changing landscapes outside your window, the 
        conversations with fellow travelers, and the anticipation of what lies ahead.
        
        While I don't have a specific story about this exact location right now, 
        I encourage you to look around and create your own narrative. What do you see? 
        What makes this place unique? If you're interested in {interest_text}, 
        keep your eyes open for signs and landmarks that might connect to those interests.
        
        The magic of road trips often lies in the unexpected discoveries. Perhaps 
        around the next bend, you'll find something truly remarkable that becomes 
        part of your own travel story – one that you'll share for years to come.
        
        Safe travels, and enjoy the continuing adventure!
        """


# Create singleton instance
google_ai_client = GoogleAIStorytellingClient()
