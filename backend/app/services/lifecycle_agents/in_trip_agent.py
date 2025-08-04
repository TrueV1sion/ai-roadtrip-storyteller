"""
In-Trip Agent - Manages real-time navigation, story generation, and dynamic adaptations.

This agent handles the active journey phase, focusing on:
- Real-time navigation assistance
- Dynamic story generation based on location
- Contextual adaptations to changing conditions
- Live interaction and engagement
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from app.core.unified_ai_client import UnifiedAIClient
from app.services.memory.trip_memory_system import TripMemorySystem, TripPhase
from app.services.lifecycle_agents.base_lifecycle_agent import (
    BaseLifecycleAgent, LifecycleContext, LifecycleResponse, LifecycleState
)
from app.services.navigation_agent import NavigationAgent
from app.services.contextual_awareness_agent import ContextualAwarenessAgent
from app.services.local_expert_agent import LocalExpertAgent
from app.services.weather_service import WeatherService
from app.services.location_service import LocationService

logger = logging.getLogger(__name__)


@dataclass
class JourneyState:
    """Current state of the journey."""
    current_location: Dict[str, float]
    heading: Optional[float]
    speed: Optional[float]
    next_waypoint: Optional[Dict[str, Any]]
    distance_to_destination: float
    estimated_arrival: Optional[datetime]
    road_conditions: Dict[str, Any]
    passenger_mood: Dict[str, float]
    last_story_time: Optional[datetime]
    last_interaction_time: Optional[datetime]


class InTripAgent(BaseLifecycleAgent):
    """
    Manages the active journey experience.
    
    This agent provides:
    - Real-time contextual storytelling
    - Dynamic route adaptations
    - Proactive suggestions and engagement
    - Safety-conscious interactions
    - Seamless companion experience
    """
    
    def __init__(self, ai_client: UnifiedAIClient, memory_system: TripMemorySystem):
        super().__init__(ai_client, memory_system)
        
        # Initialize supporting agents
        self.navigation_agent = NavigationAgent()
        self.context_agent = ContextualAwarenessAgent(ai_client)
        self.local_expert = LocalExpertAgent(ai_client)
        self.weather_service = WeatherService()
        self.location_service = LocationService()
        
        # In-trip specific configuration
        # Story timing now handled by master orchestration agent's dynamic timing system
        self.proactive_suggestion_interval = 30  # Minutes between proactive suggestions
        self.location_update_threshold = 1.0  # km before updating context
        self.max_concurrent_stories = 1  # Safety: one story at a time
        
        # Journey state tracking
        self.journey_states: Dict[str, JourneyState] = {}
        self.active_stories: Dict[str, Dict[str, Any]] = {}
        
        logger.info("In-Trip Agent initialized")
    
    def get_phase(self) -> TripPhase:
        """Return the in-trip phase."""
        return TripPhase.IN_TRIP
    
    async def initialize(self, context: LifecycleContext) -> LifecycleResponse:
        """Initialize the in-trip experience."""
        try:
            await self.transition_to_state(LifecycleState.INITIALIZING, context)
            
            # Initialize journey state
            journey_state = JourneyState(
                current_location=context.current_location or {"lat": 0.0, "lng": 0.0},
                heading=None,
                speed=None,
                next_waypoint=None,
                distance_to_destination=0.0,
                estimated_arrival=None,
                road_conditions={},
                passenger_mood={"excitement": 0.8, "curiosity": 0.7},
                last_story_time=None,
                last_interaction_time=datetime.utcnow()
            )
            
            self.journey_states[context.user.id] = journey_state
            
            # Create journey start memory
            memory_id = await self.create_memory(context, {
                "journey_started": True,
                "start_location": context.current_location,
                "trip_name": context.trip.name,
                "start_time": datetime.utcnow().isoformat(),
                "initial_mood": journey_state.passenger_mood
            })
            
            # Generate welcome message for the journey
            welcome_message = await self._generate_journey_welcome(context)
            
            # Check for immediate story opportunities
            story_opportunities = await self._check_immediate_story_opportunities(context)
            
            await self.transition_to_state(LifecycleState.ACTIVE, context)
            
            suggestions = ["Tell me about this area", "What's coming up next?", "Play some music"]
            if story_opportunities:
                suggestions.insert(0, "Tell me a story about this place")
            
            return self.create_success_response(
                message=welcome_message,
                data={
                    "journey_active": True,
                    "current_location": context.current_location,
                    "story_opportunities": story_opportunities[:3]
                },
                memories=[memory_id],
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"In-trip initialization failed: {e}")
            return self.create_error_response(
                message="I'm getting ready to guide your journey. Let me know when you're ready to start!",
                error_data={"error": str(e)}
            )
    
    async def process_request(self, request: str, context: LifecycleContext) -> LifecycleResponse:
        """Process user requests during the journey."""
        try:
            # Update location and journey state
            await self._update_journey_state(context)
            
            # Analyze request type and urgency
            request_analysis = await self._analyze_journey_request(request, context)
            
            # Handle based on request type
            if request_analysis["type"] == "navigation":
                return await self._handle_navigation_request(request, context)
            elif request_analysis["type"] == "story":
                return await self._handle_story_request(request, context)
            elif request_analysis["type"] == "local_info":
                return await self._handle_local_info_request(request, context)
            elif request_analysis["type"] == "route_change":
                return await self._handle_route_change_request(request, context)
            elif request_analysis["type"] == "emergency":
                return await self._handle_emergency_request(request, context)
            elif request_analysis["type"] == "entertainment":
                return await self._handle_entertainment_request(request, context)
            else:
                return await self._handle_general_journey_request(request, context)
                
        except Exception as e:
            logger.error(f"Journey request processing failed: {e}")
            return self.create_error_response(
                message="I'm here to help with your journey. Could you tell me what you need?",
                error_data={"error": str(e)}
            )
    
    async def finalize(self, context: LifecycleContext) -> LifecycleResponse:
        """Finalize the in-trip experience."""
        try:
            await self.transition_to_state(LifecycleState.TRANSITIONING, context)
            
            # Get journey state
            journey_state = self.journey_states.get(context.user.id)
            if not journey_state:
                return self.create_error_response("No active journey found to finalize.")
            
            # Generate journey summary
            journey_summary = await self._generate_journey_summary(context, journey_state)
            
            # Create completion memory
            memory_id = await self.create_memory(context, {
                "journey_completed": True,
                "end_location": context.current_location,
                "end_time": datetime.utcnow().isoformat(),
                "journey_summary": journey_summary,
                "memories_created": len(await self.get_relevant_memories(context))
            })
            
            # Generate completion message
            completion_message = await self._generate_journey_completion(context, journey_summary)
            
            # Clean up journey state
            if context.user.id in self.journey_states:
                del self.journey_states[context.user.id]
            if context.user.id in self.active_stories:
                del self.active_stories[context.user.id]
            
            await self.transition_to_state(LifecycleState.COMPLETED, context)
            
            return self.create_success_response(
                message=completion_message,
                data={
                    "journey_summary": journey_summary,
                    "ready_for_post_trip": True,
                    "phase_transition": "post_trip"
                },
                memories=[memory_id],
                suggestions=[
                    "Create a trip recap",
                    "Share highlights",
                    "Plan another adventure",
                    "Save favorite stories"
                ]
            )
            
        except Exception as e:
            logger.error(f"Journey finalization failed: {e}")
            return self.create_error_response(
                message="I'm wrapping up your journey experience. Thanks for traveling with me!",
                error_data={"error": str(e)}
            )
    
    async def update_location(self, context: LifecycleContext) -> LifecycleResponse:
        """Handle location updates during the journey."""
        try:
            # Update journey state
            await self._update_journey_state(context)
            
            # Note: Proactive story opportunities are now checked by the master orchestration agent
            # using its dynamic timing system. This agent focuses on location-based triggers
            # for immediate contextual responses (landmarks, POIs, etc.)
            
            # Check for location-based triggers
            triggers = await self._check_location_triggers(context)
            
            responses = []
            memories = []
            
            # Handle triggers
            for trigger in triggers:
                if trigger["type"] == "story_opportunity":
                    story_response = await self._handle_story_opportunity(trigger, context)
                    responses.append(story_response)
                elif trigger["type"] == "poi_nearby":
                    poi_response = await self._handle_poi_notification(trigger, context)
                    responses.append(poi_response)
                elif trigger["type"] == "route_update":
                    route_response = await self._handle_route_update(trigger, context)
                    responses.append(route_response)
            
            # Create location update memory
            memory_id = await self.create_memory(context, {
                "location_update": True,
                "new_location": context.current_location,
                "triggers": [t["type"] for t in triggers],
                "timestamp": datetime.utcnow().isoformat()
            })
            memories.append(memory_id)
            
            # Combine responses if multiple triggers
            if responses:
                combined_message = "\n\n".join([r.message for r in responses])
                combined_data = {}
                combined_suggestions = []
                
                for response in responses:
                    combined_data.update(response.data)
                    combined_suggestions.extend(response.next_suggestions)
                
                return self.create_success_response(
                    message=combined_message,
                    data=combined_data,
                    memories=memories,
                    suggestions=list(set(combined_suggestions))[:4]  # Unique suggestions, max 4
                )
            
            # No triggers, just acknowledge location update
            return self.create_success_response(
                message="",  # Silent update
                data={"location_updated": True},
                memories=memories
            )
            
        except Exception as e:
            logger.error(f"Location update failed: {e}")
            return self.create_error_response(
                message="I'm tracking your location to provide the best experience.",
                error_data={"error": str(e)}
            )
    
    async def _update_journey_state(self, context: LifecycleContext):
        """Update the journey state with current context."""
        user_id = context.user.id
        
        if user_id not in self.journey_states:
            # Initialize if not exists
            self.journey_states[user_id] = JourneyState(
                current_location=context.current_location or {"lat": 0.0, "lng": 0.0},
                heading=None,
                speed=None,
                next_waypoint=None,
                distance_to_destination=0.0,
                estimated_arrival=None,
                road_conditions={},
                passenger_mood={"excitement": 0.5, "curiosity": 0.5},
                last_story_time=None,
                last_interaction_time=datetime.utcnow()
            )
        
        journey_state = self.journey_states[user_id]
        
        # Update location
        if context.current_location:
            journey_state.current_location = context.current_location
        
        # Update weather-based road conditions
        if context.weather:
            journey_state.road_conditions = {
                "weather": context.weather.get("summary", "Unknown"),
                "temperature": context.weather.get("temperature", 0),
                "conditions": context.weather.get("conditions", "clear")
            }
        
        # Update interaction time
        journey_state.last_interaction_time = datetime.utcnow()
    
    async def _analyze_journey_request(self, request: str, context: LifecycleContext) -> Dict[str, Any]:
        """Analyze user request to determine type and urgency."""
        analysis_prompt = f"""
        Analyze this user request during an active road trip:
        "{request}"
        
        Current context:
        - Driving/traveling
        - Location: {context.current_location}
        - Weather: {context.weather.get('summary', 'Unknown') if context.weather else 'Unknown'}
        
        Classify the request type:
        - navigation: directions, route help, traffic
        - story: wants to hear a story or narrative
        - local_info: asking about local places, attractions
        - route_change: wants to modify route or add stops
        - emergency: urgent help needed
        - entertainment: music, games, general entertainment
        - general: other requests
        
        Also determine urgency (high/medium/low) and if it's safe to respond while driving.
        
        Return JSON with: type, urgency, driving_safe
        """
        
        try:
            response = await self.ai_generate_response(analysis_prompt, context, "json")
            return {
                "type": response.get("type", "general"),
                "urgency": response.get("urgency", "medium"),
                "driving_safe": response.get("driving_safe", True)
            }
        except Exception as e:
            logger.error(f"Request analysis failed: {e}")
            return {"type": "general", "urgency": "medium", "driving_safe": True}
    
    async def _handle_navigation_request(self, request: str, context: LifecycleContext) -> LifecycleResponse:
        """Handle navigation-related requests."""
        try:
            # Use navigation agent
            nav_response = await self.navigation_agent.route_assistance(
                current_location=context.current_location,
                route_info=context.trip.route_info if hasattr(context.trip, 'route_info') else {},
                assistance_type="general"
            )
            
            # Create memory
            memory_id = await self.create_memory(context, {
                "navigation_request": True,
                "request": request,
                "assistance_provided": True
            })
            
            # Generate conversational response
            response_message = await self._generate_navigation_response(nav_response, context)
            
            return self.create_success_response(
                message=response_message,
                data={"navigation_info": nav_response},
                memories=[memory_id],
                suggestions=[
                    "Update route",
                    "Find alternate path",
                    "Check traffic ahead",
                    "Find rest stops"
                ]
            )
            
        except Exception as e:
            logger.error(f"Navigation request failed: {e}")
            return self.create_error_response(
                message="I'm working on your navigation request. Could you be more specific about what you need?",
                error_data={"error": str(e)}
            )
    
    async def _handle_story_request(self, request: str, context: LifecycleContext) -> LifecycleResponse:
        """Handle story requests during the journey."""
        try:
            # Note: Story timing cooldown is now handled by the master orchestration agent's
            # dynamic timing system. This method now focuses only on story generation
            # when the orchestrator determines it's appropriate.
            user_id = context.user.id
            journey_state = self.journey_states.get(user_id)
            
            # Extract story preferences from request
            story_preferences = await self._extract_story_preferences_from_request(request)
            
            # Generate contextual story
            story_data = await self.generate_contextual_story(
                context,
                story_theme=story_preferences.get("theme", "general"),
                duration=story_preferences.get("duration", "medium")
            )
            
            # Update journey state
            if journey_state:
                journey_state.last_story_time = datetime.utcnow()
                journey_state.passenger_mood["entertainment"] = 0.8
            
            # Create memory
            memory_id = await self.create_memory(context, {
                "story_told": True,
                "story_theme": story_preferences.get("theme", "general"),
                "location": context.current_location,
                "passenger_response": "engaged"
            })
            
            # Generate response
            response_message = await self._generate_story_response(story_data, context)
            
            return self.create_success_response(
                message=response_message,
                data={"story": story_data},
                memories=[memory_id],
                suggestions=story_data.get("suggested_followups", [
                    "Tell me more about that",
                    "What else happened here?",
                    "Are there similar places nearby?"
                ])
            )
            
        except Exception as e:
            logger.error(f"Story request failed: {e}")
            return self.create_error_response(
                message="I'm preparing an interesting story for you. Give me just a moment.",
                error_data={"error": str(e)}
            )
    
    async def _handle_local_info_request(self, request: str, context: LifecycleContext) -> LifecycleResponse:
        """Handle requests for local information."""
        try:
            # Use local expert agent
            local_info = await self.local_expert.provide_insights(
                location=context.current_location,
                insight_type="general",
                user_interests=context.preferences.get("interests", [])
            )
            
            # Create memory
            memory_id = await self.create_memory(context, {
                "local_info_request": True,
                "request": request,
                "location": context.current_location
            })
            
            # Generate response
            response_message = await self._generate_local_info_response(local_info, context)
            
            return self.create_success_response(
                message=response_message,
                data={"local_info": local_info},
                memories=[memory_id],
                suggestions=[
                    "Tell me more about [specific place]",
                    "What's good to eat here?",
                    "Any hidden gems nearby?",
                    "Historical significance?"
                ]
            )
            
        except Exception as e:
            logger.error(f"Local info request failed: {e}")
            return self.create_error_response(
                message="I'm gathering information about this area. What specifically interests you?",
                error_data={"error": str(e)}
            )
    
    async def _handle_emergency_request(self, request: str, context: LifecycleContext) -> LifecycleResponse:
        """Handle emergency requests with priority."""
        try:
            # Emergency response with location
            emergency_response = await self._generate_emergency_response(request, context)
            
            # Create urgent memory
            memory_id = await self.create_memory(context, {
                "emergency_request": True,
                "request": request,
                "location": context.current_location,
                "timestamp": datetime.utcnow().isoformat(),
                "priority": "urgent"
            })
            
            return self.create_success_response(
                message=emergency_response,
                data={"emergency_handled": True, "location": context.current_location},
                memories=[memory_id],
                suggestions=[
                    "Call emergency services",
                    "Find nearest hospital",
                    "Get roadside assistance",
                    "Contact emergency contact"
                ]
            )
            
        except Exception as e:
            logger.error(f"Emergency request failed: {e}")
            return self.create_error_response(
                message="I'm here to help with your emergency. Please tell me what you need assistance with.",
                error_data={"error": str(e)}
            )
    
    async def _check_location_triggers(self, context: LifecycleContext) -> List[Dict[str, Any]]:
        """Check for location-based triggers."""
        triggers = []
        
        # Check for story opportunities
        if context.current_location:
            # Mock story opportunity check
            triggers.append({
                "type": "story_opportunity",
                "location": context.current_location,
                "theme": "historical",
                "confidence": 0.8
            })
        
        return triggers
    
    async def _generate_journey_welcome(self, context: LifecycleContext) -> str:
        """Generate welcome message for journey start."""
        prompt = f"""
        Create a warm, encouraging message to welcome someone starting their road trip journey.
        
        Trip: {context.trip.name}
        Current location: {context.current_location}
        
        The message should:
        1. Welcome them to the active journey
        2. Express excitement about the adventure ahead
        3. Offer assistance and engagement
        4. Keep it brief and driving-safe
        5. Maintain the friendly travel guide personality
        
        Style: Enthusiastic but calm, supportive companion.
        """
        
        return await self.ai_generate_response(prompt, context)
    
    async def _generate_journey_summary(self, context: LifecycleContext, 
                                       journey_state: JourneyState) -> Dict[str, Any]:
        """Generate summary of the journey."""
        memories = await self.get_relevant_memories(context)
        
        return {
            "duration": "N/A",  # Would calculate from start/end times
            "distance": "N/A",  # Would calculate from route
            "locations_visited": len(set(str(m.location) for m in memories if m.location)),
            "stories_told": len([m for m in memories if "story_told" in m.context]),
            "interactions": len([m for m in memories if "user_interactions" in m.context]),
            "highlights": [m.context for m in memories if m.context.get("highlight")],
            "mood_journey": journey_state.passenger_mood
        }
    
    # Additional helper methods would be implemented here for:
    # - Various response generation methods
    # - Emergency handling
    # - Route change processing
    # - Entertainment handling
    # - Proactive suggestion generation