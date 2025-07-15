"""
Unified Voice Orchestrator
The single brain that makes everything appear as one seamless voice assistant
Hides all complexity from the user while orchestrating multiple agents
"""

import asyncio
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from ..services.master_orchestration_agent import MasterOrchestrationAgent
from ..services.voice_personality_service import voice_personality_service
from ..integrations.vertex_ai_travel_agent import VertexAITravelAgent
from ..services.voice_services import VoiceServices
from ..core.unified_ai_client import UnifiedAIClient

import logging
logger = logging.getLogger(__name__)


class ConversationState(Enum):
    """Tracks what phase of conversation we're in"""
    IDLE = "idle"
    GATHERING_INFO = "gathering_info"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    PROCESSING_REQUEST = "processing_request"
    TELLING_STORY = "telling_story"


@dataclass
class ConversationContext:
    """Maintains context across the entire journey"""
    current_state: ConversationState = ConversationState.IDLE
    current_topic: Optional[str] = None
    pending_action: Optional[Dict[str, Any]] = None
    recent_suggestions: List[Dict[str, Any]] = None
    user_preferences: Dict[str, Any] = None
    active_story: Optional[str] = None
    location_context: Dict[str, Any] = None
    personality: str = "wise_narrator"
    
    def __post_init__(self):
        if self.recent_suggestions is None:
            self.recent_suggestions = []
        if self.user_preferences is None:
            self.user_preferences = {}
        if self.location_context is None:
            self.location_context = {}


class UnifiedVoiceOrchestrator:
    """
    The maestro that conducts all services while maintaining a single voice
    """
    
    def __init__(self, master_agent: MasterOrchestrationAgent, ai_client: UnifiedAIClient):
        self.master_agent = master_agent
        self.ai_client = ai_client
        self.vertex_travel_agent = VertexAITravelAgent()
        self.voice_services = VoiceServices()
        
        # Conversation management
        self.conversations: Dict[str, ConversationContext] = {}
        
        # Response blending templates for each personality
        self.personality_templates = {
            "wise_narrator": {
                "greeting": "Welcome, traveler. Your journey awaits...",
                "suggestion": "I've discovered {option} ahead. {detail}",
                "confirmation": "It is done. {detail}",
                "error": "I'm afraid {issue}. Perhaps {alternative}?",
                "story_transition": "Speaking of {topic}, {story}"
            },
            "enthusiastic_buddy": {
                "greeting": "Hey there! Ready for an AMAZING adventure?!",
                "suggestion": "Oh wow, check this out - {option}! {detail}",
                "confirmation": "Boom! Got it! {detail}",
                "error": "Ah bummer, {issue}. But hey, how about {alternative}?",
                "story_transition": "Oh that reminds me! {story}"
            },
            "local_expert": {
                "greeting": "Well hey there, welcome to my neck of the woods.",
                "suggestion": "Now locals know about {option}. {detail}",
                "confirmation": "All set for you. {detail}",
                "error": "Well now, {issue}. Might I suggest {alternative}?",
                "story_transition": "You know, {topic} has quite a history here. {story}"
            }
        }
    
    async def process_voice_input(
        self,
        user_id: str,
        audio_input: bytes,
        location: Dict[str, float],
        context_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Main entry point for ALL voice interactions
        Returns both voice audio and any visual data (for when stopped)
        """
        try:
            # Get or create conversation context
            ctx = self.conversations.get(user_id, ConversationContext(
                personality=context_data.get("personality", "wise_narrator"),
                location_context=location
            ))
            
            # 1. Convert speech to text
            transcription = await self.voice_services.transcribe_audio(audio_input)
            logger.info(f"User said: {transcription}")
            
            # 2. Understand intent and required actions
            intent_analysis = await self._analyze_intent(transcription, ctx)
            
            # 3. Update conversation state
            ctx.current_topic = intent_analysis.get("topic")
            ctx.current_state = ConversationState(intent_analysis.get("next_state", "idle"))
            
            # 4. Orchestrate services based on intent
            response_data = await self._orchestrate_response(intent_analysis, ctx)
            
            # 5. Blend all responses into cohesive narrative
            unified_response = await self._blend_responses(response_data, ctx)
            
            # 6. Generate voice output
            voice_audio = await self._generate_voice_response(unified_response, ctx)
            
            # 7. Update context for next interaction
            self.conversations[user_id] = ctx
            
            return {
                "voice_audio": voice_audio,
                "transcript": unified_response,
                "visual_data": response_data.get("visual_elements"),
                "actions_taken": response_data.get("actions"),
                "state": ctx.current_state.value
            }
            
        except Exception as e:
            logger.error(f"Voice processing error: {e}")
            # Return graceful error in character
            return await self._handle_error(e, ctx)
    
    async def _analyze_intent(
        self,
        transcription: str,
        context: ConversationContext
    ) -> Dict[str, Any]:
        """
        Understand what the user wants without them knowing we're analyzing
        """
        # Use AI to understand intent in context
        prompt = f"""
        Analyze this user request in the context of a road trip:
        
        User said: "{transcription}"
        
        Current context:
        - Conversation state: {context.current_state.value}
        - Recent topic: {context.current_topic}
        - Pending action: {context.pending_action}
        
        Determine:
        1. Primary intent (hungry, tired, bored, curious, confirm, cancel, etc.)
        2. Required services (restaurants, hotels, stories, games, navigation)
        3. Urgency level (immediate, soon, planning ahead)
        4. Next conversation state
        
        Return as JSON.
        """
        
        intent = await self.ai_client.generate_json(prompt)
        return intent
    
    async def _orchestrate_response(
        self,
        intent: Dict[str, Any],
        context: ConversationContext
    ) -> Dict[str, Any]:
        """
        Secretly coordinate multiple services while maintaining the illusion
        """
        response_data = {
            "services_used": [],
            "results": {},
            "actions": [],
            "visual_elements": None
        }
        
        # Parallel service calls based on intent
        tasks = []
        
        if "restaurants" in intent.get("required_services", []):
            tasks.append(self._get_restaurant_data(context))
            response_data["services_used"].append("restaurants")
            
        if "hotels" in intent.get("required_services", []):
            tasks.append(self._get_hotel_data(context))
            response_data["services_used"].append("hotels")
            
        if "stories" in intent.get("required_services", []):
            tasks.append(self._get_relevant_story(context))
            response_data["services_used"].append("stories")
            
        if "navigation" in intent.get("required_services", []):
            tasks.append(self._get_navigation_update(context))
            response_data["services_used"].append("navigation")
        
        # Execute all tasks in parallel
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, service in enumerate(response_data["services_used"]):
                if not isinstance(results[i], Exception):
                    response_data["results"][service] = results[i]
        
        # Handle confirmations or actions
        if intent.get("primary_intent") == "confirm" and context.pending_action:
            action_result = await self._execute_pending_action(context)
            response_data["actions"].append(action_result)
            context.pending_action = None
        
        return response_data
    
    async def _blend_responses(
        self,
        response_data: Dict[str, Any],
        context: ConversationContext
    ) -> str:
        """
        The magic: blend all service responses into one natural narrative
        """
        personality = context.personality
        templates = self.personality_templates[personality]
        
        # Build narrative based on what services returned
        narrative_parts = []
        
        # Handle restaurant results
        if "restaurants" in response_data["results"]:
            restaurants = response_data["results"]["restaurants"]
            if restaurants:
                # Pick top option and create natural suggestion
                top_pick = restaurants[0]
                narrative = templates["suggestion"].format(
                    option=top_pick["name"],
                    detail=f"They're known for {top_pick['specialty']} and have availability in {top_pick['wait_time']}"
                )
                narrative_parts.append(narrative)
                
                # Store for potential confirmation
                context.pending_action = {
                    "type": "restaurant_booking",
                    "details": top_pick
                }
        
        # Weave in stories naturally
        if "stories" in response_data["results"]:
            story = response_data["results"]["stories"]
            if narrative_parts:
                # Transition from previous topic
                story_intro = templates["story_transition"].format(
                    topic=context.current_topic or "that",
                    story=story["snippet"]
                )
                narrative_parts.append(story_intro)
            else:
                narrative_parts.append(story["full_text"])
        
        # Add navigation updates conversationally
        if "navigation" in response_data["results"]:
            nav = response_data["results"]["navigation"]
            if nav.get("important_update"):
                narrative_parts.append(nav["natural_language_update"])
        
        # Handle confirmations
        if response_data["actions"]:
            action = response_data["actions"][0]
            if action["success"]:
                confirmation = templates["confirmation"].format(
                    detail=action["detail"]
                )
                narrative_parts.append(confirmation)
        
        # Join all parts naturally
        if len(narrative_parts) > 1:
            # Add natural connectors between parts
            connected_narrative = self._add_natural_transitions(narrative_parts, personality)
            return connected_narrative
        elif narrative_parts:
            return narrative_parts[0]
        else:
            # Fallback response
            return "I'm here whenever you need anything on your journey."
    
    def _add_natural_transitions(self, parts: List[str], personality: str) -> str:
        """
        Add personality-appropriate transitions between response parts
        """
        transitions = {
            "wise_narrator": [" Moreover, ", " In addition, ", " Furthermore, "],
            "enthusiastic_buddy": [" Oh, and get this - ", " Plus, ", " Also, "],
            "local_expert": [" Now, ", " And you know, ", " I should mention, "]
        }
        
        result = parts[0]
        for i in range(1, len(parts)):
            transition = transitions[personality][i % len(transitions[personality])]
            result += transition + parts[i]
        
        return result
    
    async def _generate_voice_response(
        self,
        text: str,
        context: ConversationContext
    ) -> bytes:
        """
        Generate voice audio maintaining personality consistency
        """
        # Get voice configuration for personality
        voice_config = voice_personality_service.get_personality_config(context.personality)
        
        # Add subtle audio cues based on context
        if context.current_state == ConversationState.AWAITING_CONFIRMATION:
            # Slightly higher pitch for questions
            voice_config["pitch"] = voice_config.get("pitch", 0) + 0.5
        
        # Generate audio
        audio = await self.voice_services.synthesize_speech(
            text=text,
            voice_config=voice_config
        )
        
        return audio
    
    async def _get_restaurant_data(self, context: ConversationContext) -> List[Dict[str, Any]]:
        """Fetch restaurant options through Vertex AI Travel Agent"""
        location = context.location_context
        
        results = await self.vertex_travel_agent.search_restaurants(
            latitude=location.get("lat"),
            longitude=location.get("lng"),
            radius_miles=20,
            preferences=context.user_preferences.get("food", {})
        )
        
        # Enhance with availability
        for restaurant in results[:3]:  # Top 3 only
            availability = await self.master_agent.booking_agent.check_restaurant_availability(
                restaurant["place_id"],
                party_size=context.user_preferences.get("party_size", 2)
            )
            restaurant.update(availability)
        
        return results[:3]
    
    async def _get_hotel_data(self, context: ConversationContext) -> List[Dict[str, Any]]:
        """Fetch hotel options through Vertex AI Travel Agent"""
        location = context.location_context
        
        # Calculate arrival time based on current pace
        arrival_estimate = await self._estimate_arrival_time(location, 50)  # 50 miles ahead
        
        results = await self.vertex_travel_agent.search_hotels(
            latitude=location.get("lat"),
            longitude=location.get("lng"),
            check_in_date=arrival_estimate.date(),
            nights=1,
            preferences=context.user_preferences.get("accommodation", {})
        )
        
        return results[:3]
    
    async def _get_relevant_story(self, context: ConversationContext) -> Dict[str, Any]:
        """Get a contextually relevant story"""
        # Use the story agent to get location-based narrative
        story = await self.master_agent.story_agent.generate_contextual_story(
            location=context.location_context,
            topic=context.current_topic,
            personality=context.personality,
            recent_context=context.active_story
        )
        
        return {
            "full_text": story.content,
            "snippet": story.content[:100] + "...",
            "duration": story.estimated_duration
        }
    
    async def _get_navigation_update(self, context: ConversationContext) -> Dict[str, Any]:
        """Get natural language navigation update"""
        nav_data = await self.master_agent.navigation_agent.get_current_status()
        
        # Convert to natural language based on personality
        if nav_data.get("upcoming_turn"):
            turn = nav_data["upcoming_turn"]
            templates = {
                "wise_narrator": f"In {turn['distance']}, you'll want to {turn['direction']}",
                "enthusiastic_buddy": f"Alright, {turn['direction']} coming up in {turn['distance']}!",
                "local_expert": f"You'll be taking a {turn['direction']} in about {turn['distance']}"
            }
            
            return {
                "important_update": True,
                "natural_language_update": templates[context.personality]
            }
        
        return {"important_update": False}
    
    async def _execute_pending_action(self, context: ConversationContext) -> Dict[str, Any]:
        """Execute whatever action was pending confirmation"""
        action = context.pending_action
        
        if action["type"] == "restaurant_booking":
            result = await self.master_agent.booking_agent.book_restaurant(
                action["details"]["place_id"],
                action["details"]["time_slot"],
                party_size=context.user_preferences.get("party_size", 2)
            )
            
            return {
                "success": result.success,
                "detail": f"Table for {result.party_size} at {result.time}",
                "confirmation_number": result.confirmation_number
            }
        
        elif action["type"] == "hotel_booking":
            result = await self.vertex_travel_agent.book_hotel(
                action["details"]["hotel_id"],
                action["details"]["check_in"],
                action["details"]["nights"]
            )
            
            return {
                "success": True,
                "detail": f"Room confirmed for {action['details']['check_in']}",
                "confirmation_number": result["confirmation"]
            }
        
        return {"success": False, "detail": "Unable to complete that action"}
    
    async def _handle_error(self, error: Exception, context: ConversationContext) -> Dict[str, Any]:
        """Handle errors gracefully in character"""
        templates = self.personality_templates[context.personality]
        
        error_messages = {
            "wise_narrator": "I sense a disturbance in our journey. Let me recalibrate...",
            "enthusiastic_buddy": "Whoops! Hit a little snag there. Give me a sec...",
            "local_expert": "Well now, seems we've hit a rough patch. Let me see here..."
        }
        
        audio = await self._generate_voice_response(
            error_messages[context.personality],
            context
        )
        
        return {
            "voice_audio": audio,
            "transcript": error_messages[context.personality],
            "visual_data": None,
            "actions_taken": [],
            "state": "error"
        }
    
    async def _estimate_arrival_time(self, current_location: Dict[str, float], miles_ahead: float) -> datetime:
        """Estimate arrival time based on current pace"""
        # Simplified - in production would use actual route data
        average_speed = 50  # mph
        hours = miles_ahead / average_speed
        return datetime.now() + timedelta(hours=hours)
    
    async def proactive_suggestion(
        self,
        user_id: str,
        trigger: str,
        context_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate proactive suggestions based on time, location, or context
        Without the user having to ask
        """
        ctx = self.conversations.get(user_id, ConversationContext())
        
        suggestions = {
            "meal_time": "I notice it's getting close to {meal}. There's a wonderful {cuisine} place in {distance} that locals love.",
            "low_fuel": "Your fuel's running low. There's a station in {distance} with good prices.",
            "scenic_ahead": "Beautiful vista point coming up in {distance}. Perfect for stretching your legs.",
            "weather_change": "Weather's changing ahead. {suggestion}",
            "kids_restless": "The little ones might enjoy a stop at {attraction} in {distance}."
        }
        
        # Generate contextual suggestion
        if trigger in suggestions:
            template = suggestions[trigger]
            filled = template.format(**context_data)
            
            audio = await self._generate_voice_response(filled, ctx)
            
            return {
                "voice_audio": audio,
                "transcript": filled,
                "trigger": trigger,
                "can_dismiss": True
            }
        
        return None