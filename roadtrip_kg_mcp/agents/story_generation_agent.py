"""
Story Generation Agent - Generates location-based stories and narratives

This agent specializes in creating engaging, factually accurate stories about
locations, historical events, and cultural significance along the journey.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum

from ..core.unified_ai_client import UnifiedAIClient
from ..core.cache import get_cache
from ..models.story import Story

logger = logging.getLogger(__name__)


class StoryLength(Enum):
    SHORT = "short"  # 1-2 minutes
    MEDIUM = "medium"  # 3-5 minutes
    LONG = "long"  # 5-10 minutes


class StoryTheme(Enum):
    HISTORICAL = "historical"
    CULTURAL = "cultural"
    NATURAL = "natural"
    HAUNTED = "haunted"
    SCIENTIFIC = "scientific"
    LOCAL_LEGENDS = "local_legends"
    GENERAL = "general"


class StoryGenerationAgent:
    """
    Specialized agent for generating engaging location-based stories.
    
    This agent creates narratives that are:
    - Factually accurate and verified
    - Tailored to user preferences
    - Appropriate for the journey context
    - Engaging and educational
    """
    
    def __init__(self, ai_client: UnifiedAIClient):
        self.ai_client = ai_client
        self.cache = get_cache()
        self.fact_check_enabled = True
        logger.info("Story Generation Agent initialized")
    
    async def generate_story(self, location: Dict[str, Any], user_preferences: Dict[str, Any],
                           story_theme: str = "general", duration: str = "medium") -> Dict[str, Any]:
        """
        Generate a story for a specific location.
        
        Args:
            location: Current location information
            user_preferences: User's content preferences
            story_theme: Theme for the story
            duration: Desired story length
            
        Returns:
            Dictionary containing the story narrative and metadata
        """
        try:
            # Check cache first
            cache_key = self._generate_cache_key(location, story_theme, duration)
            cached_story = await self._get_cached_story(cache_key)
            if cached_story:
                logger.info("Returning cached story")
                return cached_story
            
            # Generate fresh story
            story_prompt = self._create_story_prompt(location, user_preferences, story_theme, duration)
            
            # Generate story content
            story_content = await self.ai_client.generate_response(story_prompt)
            
            # Fact-check if enabled
            if self.fact_check_enabled and story_theme in ["historical", "cultural", "scientific"]:
                verified_content = await self._verify_facts(story_content, location)
                if verified_content:
                    story_content = verified_content
            
            # Structure the response
            story_data = {
                "narrative": story_content,
                "theme": story_theme,
                "duration": duration,
                "location": {
                    "name": location.get("name", "Unknown Location"),
                    "coordinates": location.get("coordinates", {}),
                    "type": location.get("type", "general")
                },
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "fact_checked": self.fact_check_enabled,
                    "user_preferences_applied": True
                },
                "suggested_followups": await self._generate_followup_topics(story_content, location)
            }
            
            # Cache the story
            await self._cache_story(cache_key, story_data)
            
            logger.info(f"Generated {story_theme} story for {location.get('name', 'location')}")
            return story_data
            
        except Exception as e:
            logger.error(f"Story generation failed: {e}")
            return self._create_fallback_story(location, story_theme)
    
    def _create_story_prompt(self, location: Dict[str, Any], user_preferences: Dict[str, Any],
                           story_theme: str, duration: str) -> str:
        """Create prompt for story generation"""
        
        # Duration guidelines
        duration_guide = {
            "short": "Tell a brief, engaging story (1-2 minutes of narration)",
            "medium": "Tell a compelling story with detail (3-5 minutes of narration)",
            "long": "Tell a rich, detailed story with multiple elements (5-10 minutes of narration)"
        }
        
        # Theme-specific instructions
        theme_instructions = {
            "historical": "Focus on historical events, figures, and significance. Include dates and verified facts.",
            "cultural": "Explore cultural traditions, local customs, and community heritage.",
            "natural": "Describe natural features, geological history, and ecological significance.",
            "haunted": "Share ghost stories, mysterious events, and local legends (clearly mark as legends).",
            "scientific": "Explain scientific discoveries, research, or natural phenomena related to this location.",
            "local_legends": "Share folklore, myths, and traditional stories from the area.",
            "general": "Create an engaging narrative that captures the essence of this location."
        }
        
        # Build user preference context
        preference_context = []
        if user_preferences.get("interests"):
            preference_context.append(f"User interests: {', '.join(user_preferences['interests'])}")
        if user_preferences.get("age_group"):
            preference_context.append(f"Audience age group: {user_preferences['age_group']}")
        if user_preferences.get("avoid_topics"):
            preference_context.append(f"Avoid these topics: {', '.join(user_preferences['avoid_topics'])}")
        
        prompt = f"""
        Create an engaging story about this location for a road trip traveler.
        
        Location: {location.get('name', 'Unknown Location')}
        Type: {location.get('type', 'general location')}
        Region: {location.get('region', 'Unknown region')}
        
        Story Requirements:
        - Theme: {story_theme} - {theme_instructions.get(story_theme, theme_instructions['general'])}
        - Length: {duration_guide.get(duration, duration_guide['medium'])}
        - Style: Conversational, engaging, and appropriate for listening while driving
        
        {' '.join(preference_context)}
        
        Important Guidelines:
        1. Start with a hook that captures attention
        2. Use vivid descriptions that paint mental pictures
        3. Include specific details that make the story memorable
        4. For historical/cultural content, ensure accuracy
        5. For legends/ghost stories, clearly indicate they are stories/legends
        6. End with an interesting fact or thought-provoking element
        7. Maintain a warm, friendly narrative voice
        8. Avoid graphic violence or inappropriate content
        9. Consider the driver is listening - no complex visual references
        
        The story should feel like a knowledgeable local friend sharing fascinating information.
        """
        
        return prompt
    
    async def _verify_facts(self, story_content: str, location: Dict[str, Any]) -> Optional[str]:
        """Verify facts in the generated story"""
        
        verification_prompt = f"""
        Review this story for factual accuracy. If any facts are incorrect, provide a corrected version.
        If all facts are accurate, return the original story unchanged.
        
        Story to verify:
        {story_content}
        
        Location context:
        - Name: {location.get('name')}
        - Type: {location.get('type')}
        - Region: {location.get('region')}
        
        Focus on:
        1. Historical dates and events
        2. Names of people and places
        3. Scientific facts
        4. Cultural practices
        5. Geographic information
        
        If corrections are needed, rewrite the story with accurate information.
        Maintain the engaging narrative style.
        """
        
        try:
            verified_content = await self.ai_client.generate_response(verification_prompt)
            return verified_content
        except Exception as e:
            logger.error(f"Fact verification failed: {e}")
            return None
    
    async def _generate_followup_topics(self, story_content: str, location: Dict[str, Any]) -> List[str]:
        """Generate potential follow-up topics based on the story"""
        
        try:
            followup_prompt = f"""
            Based on this story, suggest 3 brief follow-up topics the listener might be curious about.
            
            Story: {story_content[:500]}...
            
            Create 3 short, intriguing questions or topics (max 10 words each) that:
            1. Relate directly to elements mentioned in the story
            2. Would lead to interesting additional information
            3. Are phrased as natural curiosities
            
            Return as a simple list.
            """
            
            response = await self.ai_client.generate_response(followup_prompt)
            
            # Parse response into list
            topics = [line.strip() for line in response.split('\n') if line.strip()][:3]
            return topics
            
        except Exception as e:
            logger.error(f"Failed to generate follow-up topics: {e}")
            return [
                "Tell me more about the history",
                "What else is interesting here?",
                "Are there similar places nearby?"
            ]
    
    def _generate_cache_key(self, location: Dict[str, Any], theme: str, duration: str) -> str:
        """Generate cache key for story"""
        location_id = location.get('place_id', location.get('name', 'unknown'))
        return f"story:{location_id}:{theme}:{duration}"
    
    async def _get_cached_story(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached story if available"""
        try:
            cached = await self.cache.get(cache_key)
            if cached:
                logger.info(f"Found cached story: {cache_key}")
                return cached
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
        return None
    
    async def _cache_story(self, cache_key: str, story_data: Dict[str, Any]):
        """Cache generated story"""
        try:
            # Cache for 7 days
            await self.cache.set(cache_key, story_data, expire=604800)
            logger.info(f"Cached story: {cache_key}")
        except Exception as e:
            logger.error(f"Cache storage error: {e}")
    
    def _create_fallback_story(self, location: Dict[str, Any], theme: str) -> Dict[str, Any]:
        """Create a generic fallback story if generation fails"""
        
        location_name = location.get('name', 'this location')
        
        fallback_narratives = {
            "general": f"We're passing through {location_name}, a place with its own unique character and stories. "
                      f"Every location along our journey has something special to discover.",
            "historical": f"{location_name} has witnessed many events throughout history. "
                         f"Like many places, it holds stories of the people who lived, worked, and passed through here.",
            "natural": f"The natural landscape around {location_name} tells its own story through the land itself. "
                      f"Nature has shaped this area in fascinating ways over time."
        }
        
        return {
            "narrative": fallback_narratives.get(theme, fallback_narratives["general"]),
            "theme": theme,
            "duration": "short",
            "location": {
                "name": location_name,
                "coordinates": location.get("coordinates", {}),
                "type": location.get("type", "general")
            },
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "fact_checked": False,
                "fallback": True
            },
            "suggested_followups": []
        }