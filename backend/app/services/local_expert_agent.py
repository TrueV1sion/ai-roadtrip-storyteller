"""
Local Expert Agent - Provides authentic local insights and recommendations

This agent specializes in delivering local knowledge, hidden gems, cultural insights,
and insider tips that make travelers feel like they have a knowledgeable local guide.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum
import random

from ..core.unified_ai_client import UnifiedAIClient
from ..core.cache import get_cache

logger = logging.getLogger(__name__)


class InsightType(Enum):
    HISTORICAL = "historical"
    CULTURAL = "cultural"
    CULINARY = "culinary"
    HIDDEN_GEM = "hidden_gem"
    LOCAL_FAVORITE = "local_favorite"
    SEASONAL = "seasonal"
    INSIDER_TIP = "insider_tip"
    GENERAL = "general"


class LocalPerspective(Enum):
    LONGTIME_RESIDENT = "longtime_resident"
    LOCAL_HISTORIAN = "local_historian"
    FOOD_ENTHUSIAST = "food_enthusiast"
    OUTDOOR_EXPERT = "outdoor_expert"
    CULTURAL_INSIDER = "cultural_insider"
    YOUNG_LOCAL = "young_local"


class LocalExpertAgent:
    """
    Agent that provides authentic local insights and recommendations.
    
    This agent:
    - Shares hidden gems and off-the-beaten-path locations
    - Provides cultural context and local customs
    - Recommends authentic local experiences
    - Offers insider tips for better experiences
    - Shares local stories and folklore
    """
    
    def __init__(self, ai_client: UnifiedAIClient):
        self.ai_client = ai_client
        self.cache = get_cache()
        logger.info("Local Expert Agent initialized")
    
    async def provide_insights(self, location: Dict[str, Any],
                             insight_type: str = "general",
                             user_interests: List[str] = None) -> Dict[str, Any]:
        """
        Provide local expert insights for a location.
        
        Args:
            location: Current location information
            insight_type: Type of insights to provide
            user_interests: User's interests for personalization
            
        Returns:
            Dictionary containing local insights and recommendations
        """
        try:
            # Check cache for existing insights
            cache_key = self._generate_cache_key(location, insight_type)
            cached_insights = await self._get_cached_insights(cache_key)
            if cached_insights:
                return self._personalize_insights(cached_insights, user_interests)
            
            # Determine local perspective to use
            perspective = self._select_perspective(insight_type, user_interests)
            
            # Generate location context
            location_context = await self._gather_location_context(location)
            
            # Generate insights based on type
            if insight_type == "hidden_gem":
                insights = await self._generate_hidden_gem_insights(location, location_context, perspective)
            elif insight_type == "culinary":
                insights = await self._generate_culinary_insights(location, location_context, perspective)
            elif insight_type == "cultural":
                insights = await self._generate_cultural_insights(location, location_context, perspective)
            elif insight_type == "historical":
                insights = await self._generate_historical_insights(location, location_context, perspective)
            else:
                insights = await self._generate_general_insights(location, location_context, perspective, user_interests)
            
            # Add local tips
            insights['local_tips'] = await self._generate_local_tips(location, insight_type)
            
            # Add authenticity markers
            insights['authenticity_notes'] = self._add_authenticity_markers(insights)
            
            # Cache the insights
            await self._cache_insights(cache_key, insights)
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to provide local insights: {e}")
            return self._create_fallback_insights(location, insight_type)
    
    def _select_perspective(self, insight_type: str, user_interests: List[str]) -> LocalPerspective:
        """Select appropriate local perspective based on context"""
        
        if insight_type == "culinary" or (user_interests and "food" in user_interests):
            return LocalPerspective.FOOD_ENTHUSIAST
        elif insight_type == "historical":
            return LocalPerspective.LOCAL_HISTORIAN
        elif insight_type == "cultural":
            return LocalPerspective.CULTURAL_INSIDER
        elif user_interests and any(interest in ["hiking", "outdoors", "nature"] for interest in user_interests):
            return LocalPerspective.OUTDOOR_EXPERT
        elif user_interests and any(interest in ["nightlife", "music", "arts"] for interest in user_interests):
            return LocalPerspective.YOUNG_LOCAL
        else:
            return LocalPerspective.LONGTIME_RESIDENT
    
    async def _gather_location_context(self, location: Dict[str, Any]) -> Dict[str, Any]:
        """Gather contextual information about the location"""
        
        context_prompt = f"""
        Provide context about {location.get('name', 'this location')} including:
        1. Type of area (urban, rural, historic district, etc.)
        2. Known for (what makes this place special)
        3. Local character and atmosphere
        4. Demographics and culture
        5. Economic focus (tourism, industry, agriculture, etc.)
        6. Regional identity
        
        Be specific and authentic.
        """
        
        try:
            context_response = await self.ai_client.generate_structured_response(
                context_prompt, expected_format="location_context"
            )
            
            return {
                "area_type": context_response.get("area_type", "general"),
                "known_for": context_response.get("known_for", []),
                "local_character": context_response.get("character", ""),
                "demographics": context_response.get("demographics", ""),
                "economic_focus": context_response.get("economic_focus", ""),
                "regional_identity": context_response.get("regional_identity", "")
            }
            
        except Exception as e:
            logger.error(f"Failed to gather location context: {e}")
            return {
                "area_type": "general",
                "known_for": [],
                "local_character": "friendly",
                "demographics": "diverse",
                "economic_focus": "mixed",
                "regional_identity": "American"
            }
    
    async def _generate_hidden_gem_insights(self, location: Dict[str, Any],
                                          context: Dict[str, Any],
                                          perspective: LocalPerspective) -> Dict[str, Any]:
        """Generate insights about hidden gems and secret spots"""
        
        prompt = f"""
        As a {perspective.value.replace('_', ' ')} in {location.get('name', 'this area')}, share 3-4 hidden gems 
        that most tourists don't know about.
        
        Location context: {context['known_for']}
        Area type: {context['area_type']}
        
        For each hidden gem, provide:
        1. Name and what it is
        2. Why locals love it
        3. Best time to visit
        4. How to find it (but keep some mystery)
        5. What makes it special
        
        Make it feel like you're sharing secrets with a friend. Include phrases like:
        - "Most people don't know about..."
        - "Locals call it..."
        - "You didn't hear this from me, but..."
        - "My favorite spot that tourists miss..."
        
        Be authentic and specific. These should feel like real insider knowledge.
        """
        
        try:
            response = await self.ai_client.generate_response(prompt)
            
            # Parse response into structured format
            hidden_gems = self._parse_hidden_gems(response)
            
            return {
                "insights": response,
                "insight_type": "hidden_gem",
                "perspective": perspective.value,
                "hidden_gems": hidden_gems,
                "local_saying": self._generate_local_saying(context),
                "best_kept_secret": hidden_gems[0] if hidden_gems else None
            }
            
        except Exception as e:
            logger.error(f"Failed to generate hidden gem insights: {e}")
            return self._create_fallback_insights(location, "hidden_gem")
    
    async def _generate_culinary_insights(self, location: Dict[str, Any],
                                        context: Dict[str, Any],
                                        perspective: LocalPerspective) -> Dict[str, Any]:
        """Generate insights about local food and dining"""
        
        prompt = f"""
        As a {perspective.value.replace('_', ' ')} in {location.get('name', 'this area')}, share authentic 
        culinary insights about the local food scene.
        
        Include:
        1. The dish/food locals actually eat (not tourist versions)
        2. Where locals go for the best version
        3. A family-owned place that's been here forever
        4. Local food tradition or custom visitors should know
        5. Something unique you can only get here
        6. Best time/way to experience local food culture
        
        Use natural, conversational language like:
        - "If you want to eat like a local..."
        - "My grandmother always said..."
        - "The real [dish name] is nothing like..."
        - "On Sunday mornings, everyone goes to..."
        
        Make it personal and authentic. Share real local food culture.
        """
        
        try:
            response = await self.ai_client.generate_response(prompt)
            
            # Extract specific recommendations
            food_spots = self._extract_food_recommendations(response)
            
            return {
                "insights": response,
                "insight_type": "culinary",
                "perspective": perspective.value,
                "local_favorites": food_spots,
                "food_traditions": self._extract_food_traditions(response),
                "must_try": food_spots[0] if food_spots else None,
                "local_tip": "Ask for it 'the local way' - they'll know what you mean"
            }
            
        except Exception as e:
            logger.error(f"Failed to generate culinary insights: {e}")
            return self._create_fallback_insights(location, "culinary")
    
    async def _generate_cultural_insights(self, location: Dict[str, Any],
                                        context: Dict[str, Any],
                                        perspective: LocalPerspective) -> Dict[str, Any]:
        """Generate insights about local culture and customs"""
        
        prompt = f"""
        As a {perspective.value.replace('_', ' ')} in {location.get('name', 'this area')}, share cultural 
        insights that help visitors understand and respect our community.
        
        Share:
        1. An important local tradition or festival
        2. Social customs visitors should know
        3. What makes locals proud of this place
        4. Common misconception outsiders have
        5. How to show respect for local culture
        6. A story that captures the local spirit
        
        Use warm, welcoming language like:
        - "Something visitors often don't realize..."
        - "We have a saying here..."
        - "The thing that makes us different..."
        - "If you really want to connect with locals..."
        
        Be genuine and help visitors feel welcomed into the community.
        """
        
        try:
            response = await self.ai_client.generate_response(prompt)
            
            return {
                "insights": response,
                "insight_type": "cultural",
                "perspective": perspective.value,
                "cultural_notes": self._extract_cultural_notes(response),
                "local_customs": self._extract_customs(response),
                "community_spirit": context.get('local_character', ''),
                "welcome_phrase": self._generate_welcome_phrase(context)
            }
            
        except Exception as e:
            logger.error(f"Failed to generate cultural insights: {e}")
            return self._create_fallback_insights(location, "cultural")
    
    async def _generate_historical_insights(self, location: Dict[str, Any],
                                          context: Dict[str, Any],
                                          perspective: LocalPerspective) -> Dict[str, Any]:
        """Generate historical insights with local perspective"""
        
        prompt = f"""
        As a {perspective.value.replace('_', ' ')} in {location.get('name', 'this area')}, share historical 
        insights that bring our local history to life.
        
        Include:
        1. A fascinating historical event locals still talk about
        2. How history shaped what this place is today
        3. A local legend or story passed down
        4. Historical spot with a story tourists don't know
        5. How locals remember and honor their history
        
        Use engaging, story-telling language like:
        - "My grandfather used to tell me..."
        - "You can still see where..."
        - "Locals know the real story..."
        - "Every year we remember when..."
        
        Make history feel alive and relevant, not like a textbook.
        """
        
        try:
            response = await self.ai_client.generate_response(prompt)
            
            return {
                "insights": response,
                "insight_type": "historical",
                "perspective": perspective.value,
                "historical_tales": self._extract_historical_tales(response),
                "living_history": self._identify_living_history(response, context),
                "local_memory": "This story has been passed down for generations"
            }
            
        except Exception as e:
            logger.error(f"Failed to generate historical insights: {e}")
            return self._create_fallback_insights(location, "historical")
    
    async def _generate_general_insights(self, location: Dict[str, Any],
                                       context: Dict[str, Any],
                                       perspective: LocalPerspective,
                                       user_interests: List[str]) -> Dict[str, Any]:
        """Generate general local insights based on interests"""
        
        interest_context = ""
        if user_interests:
            interest_context = f"The visitor is interested in: {', '.join(user_interests)}"
        
        prompt = f"""
        As a {perspective.value.replace('_', ' ')} in {location.get('name', 'this area')}, share insider 
        knowledge that would enhance a visitor's experience.
        
        {interest_context}
        
        Share a mix of:
        1. Something only locals know about
        2. Best local experience for their interests
        3. Common tourist mistake to avoid
        4. Local recommendation off the beaten path
        5. What makes this place special to you personally
        
        Be conversational and authentic. Make them feel like they're getting advice from a local friend.
        Use phrases like:
        - "Between you and me..."
        - "Locals know to..."
        - "Skip the tourist trap at..."
        - "My personal favorite..."
        
        Keep it genuine and helpful.
        """
        
        try:
            response = await self.ai_client.generate_response(prompt)
            
            return {
                "insights": response,
                "insight_type": "general",
                "perspective": perspective.value,
                "personalized_for": user_interests,
                "local_recommendations": self._extract_recommendations(response),
                "insider_advice": self._extract_insider_advice(response),
                "authenticity_score": "high"
            }
            
        except Exception as e:
            logger.error(f"Failed to generate general insights: {e}")
            return self._create_fallback_insights(location, "general")
    
    async def _generate_local_tips(self, location: Dict[str, Any],
                                 insight_type: str) -> List[str]:
        """Generate practical local tips"""
        
        tips = []
        
        # General tips applicable everywhere
        general_tips = [
            "Chat with shop owners - they love sharing local stories",
            "Check community boards for local events",
            "The best experiences often aren't advertised",
            "Local newspapers highlight authentic community happenings"
        ]
        
        # Type-specific tips
        if insight_type == "culinary":
            tips.extend([
                "If locals are lining up, it's worth the wait",
                "Family restaurants often have unlisted daily specials",
                "Ask servers for their personal favorite - not the popular item"
            ])
        elif insight_type == "hidden_gem":
            tips.extend([
                "Early morning or late afternoon for peaceful visits",
                "Respect these special places - take only photos",
                "Some spots are better discovered than directed to"
            ])
        elif insight_type == "cultural":
            tips.extend([
                "Observe first, participate when invited",
                "A smile and 'hello' goes a long way here",
                "Support local artisans and family businesses"
            ])
        
        # Select relevant tips
        tips.extend(random.sample(general_tips, 2))
        
        return tips[:5]  # Return top 5 tips
    
    def _add_authenticity_markers(self, insights: Dict[str, Any]) -> List[str]:
        """Add markers that indicate authentic local knowledge"""
        
        markers = []
        
        # Add credibility markers based on content
        if "family" in insights.get('insights', '').lower():
            markers.append("Shared by multi-generation locals")
        if "grandfather" in insights.get('insights', '').lower() or "grandmother" in insights.get('insights', '').lower():
            markers.append("Passed down through local families")
        if "locals know" in insights.get('insights', '').lower():
            markers.append("Common local knowledge")
        if "hidden" in insights.get('insights', '').lower():
            markers.append("Not in guidebooks")
        
        return markers
    
    def _personalize_insights(self, insights: Dict[str, Any],
                            user_interests: List[str]) -> Dict[str, Any]:
        """Personalize cached insights based on user interests"""
        
        if not user_interests:
            return insights
        
        # Add personalization layer
        insights['personalized'] = True
        insights['tailored_to'] = user_interests
        
        # Filter recommendations based on interests
        if 'local_recommendations' in insights:
            insights['local_recommendations'] = [
                rec for rec in insights['local_recommendations']
                if any(interest.lower() in str(rec).lower() for interest in user_interests)
            ]
        
        return insights
    
    # Parsing helper methods
    
    def _parse_hidden_gems(self, response: str) -> List[Dict[str, Any]]:
        """Parse hidden gems from response text"""
        # Simplified parsing - in production would use more sophisticated NLP
        gems = []
        lines = response.split('\n')
        current_gem = {}
        
        for line in lines:
            if any(marker in line.lower() for marker in ['most people don\'t know', 'locals call it', 'favorite spot']):
                if current_gem:
                    gems.append(current_gem)
                current_gem = {'description': line}
            elif current_gem:
                current_gem['details'] = current_gem.get('details', '') + ' ' + line
        
        if current_gem:
            gems.append(current_gem)
        
        return gems[:4]  # Return top 4
    
    def _extract_food_recommendations(self, response: str) -> List[Dict[str, Any]]:
        """Extract food recommendations from response"""
        # Placeholder extraction
        return [
            {
                "name": "Local favorite spot",
                "type": "restaurant",
                "why_special": "Authentic local cuisine"
            }
        ]
    
    def _extract_food_traditions(self, response: str) -> List[str]:
        """Extract food traditions from response"""
        # Placeholder extraction
        traditions = []
        if "tradition" in response.lower():
            traditions.append("Local food tradition mentioned in insights")
        return traditions
    
    def _extract_cultural_notes(self, response: str) -> List[str]:
        """Extract cultural notes from response"""
        # Placeholder extraction
        return ["Cultural insight from response"]
    
    def _extract_customs(self, response: str) -> List[str]:
        """Extract local customs from response"""
        # Placeholder extraction
        return ["Local custom to observe"]
    
    def _extract_historical_tales(self, response: str) -> List[Dict[str, Any]]:
        """Extract historical tales from response"""
        # Placeholder extraction
        return [{"tale": "Historical story", "era": "Past"}]
    
    def _identify_living_history(self, response: str, context: Dict[str, Any]) -> List[str]:
        """Identify living history elements"""
        # Placeholder identification
        return ["Historical element still visible today"]
    
    def _extract_recommendations(self, response: str) -> List[Dict[str, Any]]:
        """Extract general recommendations from response"""
        # Placeholder extraction
        return [{"recommendation": "Local suggestion", "type": "experience"}]
    
    def _extract_insider_advice(self, response: str) -> List[str]:
        """Extract insider advice from response"""
        # Placeholder extraction
        advice = []
        if "avoid" in response.lower():
            advice.append("Tourist trap to avoid mentioned")
        if "best time" in response.lower():
            advice.append("Optimal timing advice given")
        return advice
    
    # Helper methods
    
    def _generate_local_saying(self, context: Dict[str, Any]) -> str:
        """Generate a local saying based on context"""
        sayings = [
            "As we say around here, 'The best stories are found off the map'",
            "Local saying: 'If you want to know a place, walk its hidden paths'",
            "We have a phrase: 'Tourists see sights, travelers find stories'"
        ]
        return random.choice(sayings)
    
    def _generate_welcome_phrase(self, context: Dict[str, Any]) -> str:
        """Generate a welcoming phrase"""
        phrases = [
            "Welcome to our community - we're glad you're here",
            "Make yourself at home in our little corner of the world",
            "You're not a tourist here, you're a temporary local"
        ]
        return random.choice(phrases)
    
    def _generate_cache_key(self, location: Dict[str, Any], insight_type: str) -> str:
        """Generate cache key for insights"""
        location_id = location.get('place_id', location.get('name', 'unknown'))
        return f"local_insights:{location_id}:{insight_type}"
    
    async def _get_cached_insights(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached insights"""
        try:
            cached = await self.cache.get(cache_key)
            if cached:
                logger.info(f"Found cached insights: {cache_key}")
                return cached
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
        return None
    
    async def _cache_insights(self, cache_key: str, insights: Dict[str, Any]):
        """Cache insights for future use"""
        try:
            # Cache for 30 days - local insights don't change frequently
            await self.cache.set(cache_key, insights, expire=2592000)
            logger.info(f"Cached insights: {cache_key}")
        except Exception as e:
            logger.error(f"Cache storage error: {e}")
    
    def _create_fallback_insights(self, location: Dict[str, Any], insight_type: str) -> Dict[str, Any]:
        """Create fallback insights when generation fails"""
        
        location_name = location.get('name', 'this area')
        
        fallback_insights = {
            "general": f"Welcome to {location_name}! This area has its own unique character and hidden treasures. "
                      f"Take time to explore beyond the main attractions - the best discoveries often happen by chance.",
            "hidden_gem": f"Every place has its secrets, and {location_name} is no exception. "
                         f"Wander the side streets, chat with locals, and you'll find your own hidden gems.",
            "culinary": f"The food scene in {location_name} reflects the local culture. "
                       f"Look for busy local restaurants - they're popular for a reason.",
            "cultural": f"{location_name} has its own traditions and customs. "
                       f"Approach with respect and curiosity, and locals will warmly welcome you.",
            "historical": f"{location_name} has stories etched into every corner. "
                         f"Look closely and you'll see history all around you."
        }
        
        return {
            "insights": fallback_insights.get(insight_type, fallback_insights["general"]),
            "insight_type": insight_type,
            "perspective": "local",
            "fallback": True,
            "local_tips": [
                "Take time to explore",
                "Chat with locals",
                "Try something new"
            ]
        }