"""
Pre-Trip Agent - Handles trip planning, itinerary creation, and narrative preparation.

This agent manages the pre-trip phase, focusing on:
- Trip planning and route optimization
- Itinerary creation with storytelling elements
- Narrative preparation and context building
- Expectation setting and excitement building
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
from app.services.booking_agent import BookingAgent
from app.services.location_service import LocationService
from app.services.weather_service import WeatherService

logger = logging.getLogger(__name__)


@dataclass
class TripPlan:
    """Structured trip plan with narrative elements."""
    origin: Dict[str, Any]
    destination: Dict[str, Any]
    waypoints: List[Dict[str, Any]]
    estimated_duration: float  # hours
    estimated_distance: float  # km
    narrative_themes: List[str]
    story_opportunities: List[Dict[str, Any]]
    booking_suggestions: List[Dict[str, Any]]
    weather_considerations: Dict[str, Any]
    preparation_checklist: List[str]


class PreTripAgent(BaseLifecycleAgent):
    """
    Specializes in pre-trip planning and preparation.
    
    This agent helps users:
    - Plan their route with storytelling in mind
    - Discover narrative opportunities along the way
    - Prepare for an engaging journey
    - Set expectations for the adventure ahead
    """
    
    def __init__(self, ai_client: UnifiedAIClient, memory_system: TripMemorySystem):
        super().__init__(ai_client, memory_system)
        
        # Initialize supporting services
        self.booking_agent = BookingAgent(ai_client)
        self.location_service = LocationService()
        self.weather_service = WeatherService()
        
        # Pre-trip specific configuration
        self.max_waypoints = 20
        self.story_discovery_radius = 50  # km
        self.planning_session_ttl = 86400  # 24 hours
        
        logger.info("Pre-Trip Agent initialized")
    
    def get_phase(self) -> TripPhase:
        """Return the pre-trip phase."""
        return TripPhase.PRE_TRIP
    
    async def initialize(self, context: LifecycleContext) -> LifecycleResponse:
        """Initialize pre-trip planning session."""
        try:
            await self.transition_to_state(LifecycleState.INITIALIZING, context)
            
            # Create initial planning memory
            memory_id = await self.create_memory(context, {
                "initialization": True,
                "trip_name": context.trip.name,
                "planning_started": datetime.utcnow().isoformat(),
                "user_preferences": context.preferences
            })
            
            # Initialize session
            self.update_session_info(context.user.id, {
                "trip_id": context.trip.id,
                "planning_started": datetime.utcnow(),
                "current_step": "initial_planning",
                "plan_data": {}
            })
            
            await self.transition_to_state(LifecycleState.ACTIVE, context)
            
            welcome_message = await self._generate_welcome_message(context)
            
            return self.create_success_response(
                message=welcome_message,
                data={"session_initialized": True, "planning_mode": "active"},
                memories=[memory_id],
                suggestions=[
                    "Let's start planning your route",
                    "Tell me about your interests",
                    "What kind of stories do you enjoy?",
                    "Are there specific places you want to visit?"
                ]
            )
            
        except Exception as e:
            logger.error(f"Pre-trip initialization failed: {e}")
            return self.create_error_response(
                message="I'm having trouble starting your trip planning. Let me try again.",
                error_data={"error": str(e)}
            )
    
    async def process_request(self, request: str, context: LifecycleContext) -> LifecycleResponse:
        """Process user requests during pre-trip planning."""
        try:
            # Analyze the request type
            request_type = await self._analyze_request_type(request, context)
            
            # Route to appropriate handler
            if request_type == "route_planning":
                return await self._handle_route_planning(request, context)
            elif request_type == "story_discovery":
                return await self._handle_story_discovery(request, context)
            elif request_type == "itinerary_creation":
                return await self._handle_itinerary_creation(request, context)
            elif request_type == "booking_inquiry":
                return await self._handle_booking_inquiry(request, context)
            elif request_type == "preparation_help":
                return await self._handle_preparation_help(request, context)
            else:
                return await self._handle_general_planning(request, context)
                
        except Exception as e:
            logger.error(f"Request processing failed: {e}")
            return self.create_error_response(
                message="I encountered an issue while helping with your planning. Could you try rephrasing your request?",
                error_data={"error": str(e)}
            )
    
    async def finalize(self, context: LifecycleContext) -> LifecycleResponse:
        """Finalize pre-trip planning and prepare for transition."""
        try:
            await self.transition_to_state(LifecycleState.TRANSITIONING, context)
            
            # Get current planning data
            session_info = self.get_session_info(context.user.id)
            plan_data = session_info.get("plan_data", {})
            
            # Generate final trip plan
            final_plan = await self._generate_final_plan(context, plan_data)
            
            # Create completion memory
            memory_id = await self.create_memory(context, {
                "planning_completed": True,
                "final_plan": final_plan,
                "completion_time": datetime.utcnow().isoformat(),
                "ready_for_journey": True
            })
            
            # Generate excitement-building message
            completion_message = await self._generate_completion_message(context, final_plan)
            
            await self.transition_to_state(LifecycleState.COMPLETED, context)
            
            return self.create_success_response(
                message=completion_message,
                data={
                    "trip_plan": final_plan,
                    "ready_for_journey": True,
                    "phase_transition": "in_trip"
                },
                memories=[memory_id],
                suggestions=[
                    "Start the journey",
                    "Review the plan once more",
                    "Adjust any preferences",
                    "Set departure time"
                ]
            )
            
        except Exception as e:
            logger.error(f"Pre-trip finalization failed: {e}")
            return self.create_error_response(
                message="I'm having trouble finalizing your trip plan. Let me gather everything together.",
                error_data={"error": str(e)}
            )
    
    async def _generate_welcome_message(self, context: LifecycleContext) -> str:
        """Generate personalized welcome message."""
        prompt = f"""
        Create a warm, engaging welcome message for a user starting to plan their road trip.
        
        Trip Name: {context.trip.name}
        User Background: {context.user.email}
        
        The message should:
        1. Welcome them to the AI Road Trip Storyteller
        2. Express excitement about their upcoming journey
        3. Briefly explain how you'll help with planning
        4. Invite them to share their initial thoughts
        5. Keep it conversational and enthusiastic
        
        Style: Friendly travel guide who's genuinely excited to help plan an amazing journey.
        """
        
        return await self.ai_generate_response(prompt, context)
    
    async def _analyze_request_type(self, request: str, context: LifecycleContext) -> str:
        """Analyze user request to determine handling approach."""
        analysis_prompt = f"""
        Analyze this user request during pre-trip planning:
        "{request}"
        
        Classify it as one of:
        - route_planning: wants to plan or modify the route
        - story_discovery: interested in stories/narratives along the way
        - itinerary_creation: wants to create detailed itinerary
        - booking_inquiry: asking about reservations or bookings
        - preparation_help: needs help preparing for the trip
        - general_planning: general planning questions
        
        Return only the classification.
        """
        
        try:
            response = await self.ai_generate_response(analysis_prompt, context)
            return response.strip().lower()
        except Exception as e:
            logger.error(f"Request analysis failed: {e}")
            return "general_planning"
    
    async def _handle_route_planning(self, request: str, context: LifecycleContext) -> LifecycleResponse:
        """Handle route planning requests."""
        try:
            # Extract locations from request
            locations = await self._extract_locations_from_request(request)
            
            if not locations:
                return self.create_success_response(
                    message="I'd love to help plan your route! Could you tell me your starting point and destination?",
                    data={"needs_locations": True},
                    suggestions=[
                        "I'm starting from [city] and going to [destination]",
                        "Plan a route from my current location",
                        "I want to visit [specific places]"
                    ]
                )
            
            # Generate route options
            route_options = await self._generate_route_options(locations, context)
            
            # Find story opportunities along routes
            story_opportunities = await self._find_story_opportunities(route_options, context)
            
            # Update session with route data
            session_info = self.get_session_info(context.user.id)
            session_info["plan_data"]["route_options"] = route_options
            session_info["plan_data"]["story_opportunities"] = story_opportunities
            self.update_session_info(context.user.id, session_info)
            
            # Create memory
            memory_id = await self.create_memory(context, {
                "route_planning": True,
                "locations": locations,
                "route_options": len(route_options),
                "story_opportunities": len(story_opportunities)
            })
            
            # Generate response
            response_message = await self._generate_route_response(route_options, story_opportunities, context)
            
            return self.create_success_response(
                message=response_message,
                data={
                    "route_options": route_options,
                    "story_opportunities": story_opportunities[:5]  # Top 5
                },
                memories=[memory_id],
                suggestions=[
                    "Tell me more about route option 1",
                    "What stories are available along the way?",
                    "Optimize for scenic routes",
                    "Add more waypoints"
                ]
            )
            
        except Exception as e:
            logger.error(f"Route planning failed: {e}")
            return self.create_error_response(
                message="I'm having trouble planning your route. Could you provide more details about where you'd like to go?",
                error_data={"error": str(e)}
            )
    
    async def _handle_story_discovery(self, request: str, context: LifecycleContext) -> LifecycleResponse:
        """Handle story discovery and narrative preparation."""
        try:
            # Get current route data
            session_info = self.get_session_info(context.user.id)
            route_data = session_info.get("plan_data", {}).get("route_options", [])
            
            if not route_data:
                return self.create_success_response(
                    message="I'd love to help you discover stories! First, let's plan your route so I can find the best narratives along your journey.",
                    data={"needs_route_first": True},
                    suggestions=[
                        "Plan my route first",
                        "I'm going from [origin] to [destination]",
                        "Show me story themes available"
                    ]
                )
            
            # Extract story preferences from request
            story_preferences = await self._extract_story_preferences(request, context)
            
            # Find stories along the planned route
            stories = await self._discover_stories_along_route(route_data, story_preferences, context)
            
            # Create memory
            memory_id = await self.create_memory(context, {
                "story_discovery": True,
                "preferences": story_preferences,
                "stories_found": len(stories)
            })
            
            # Generate response
            response_message = await self._generate_story_discovery_response(stories, context)
            
            return self.create_success_response(
                message=response_message,
                data={"stories": stories[:10]},  # Top 10 stories
                memories=[memory_id],
                suggestions=[
                    "Tell me more about [specific story]",
                    "Find historical stories",
                    "Show me local legends",
                    "What about ghost stories?"
                ]
            )
            
        except Exception as e:
            logger.error(f"Story discovery failed: {e}")
            return self.create_error_response(
                message="I'm having trouble finding stories for your journey. Let me try a different approach.",
                error_data={"error": str(e)}
            )
    
    async def _handle_itinerary_creation(self, request: str, context: LifecycleContext) -> LifecycleResponse:
        """Handle detailed itinerary creation."""
        try:
            # Get current planning data
            session_info = self.get_session_info(context.user.id)
            plan_data = session_info.get("plan_data", {})
            
            # Extract itinerary preferences
            itinerary_prefs = await self._extract_itinerary_preferences(request, context)
            
            # Create detailed itinerary
            itinerary = await self._create_detailed_itinerary(plan_data, itinerary_prefs, context)
            
            # Update session
            plan_data["itinerary"] = itinerary
            self.update_session_info(context.user.id, session_info)
            
            # Create memory
            memory_id = await self.create_memory(context, {
                "itinerary_creation": True,
                "itinerary_items": len(itinerary.get("items", [])),
                "preferences": itinerary_prefs
            })
            
            # Generate response
            response_message = await self._generate_itinerary_response(itinerary, context)
            
            return self.create_success_response(
                message=response_message,
                data={"itinerary": itinerary},
                memories=[memory_id],
                suggestions=[
                    "Adjust timing for specific stops",
                    "Add more dining options",
                    "Include rest stops",
                    "Optimize for storytelling"
                ]
            )
            
        except Exception as e:
            logger.error(f"Itinerary creation failed: {e}")
            return self.create_error_response(
                message="I'm working on your itinerary. Could you tell me more about your preferences?",
                error_data={"error": str(e)}
            )
    
    async def _handle_booking_inquiry(self, request: str, context: LifecycleContext) -> LifecycleResponse:
        """Handle booking-related inquiries."""
        try:
            # Use booking agent for specialized handling
            booking_task = {
                "task": "find_opportunities",
                "location": context.current_location,
                "context": context,
                "user_request": request
            }
            
            booking_response = await self.booking_agent.find_opportunities(**booking_task)
            
            # Create memory
            memory_id = await self.create_memory(context, {
                "booking_inquiry": True,
                "request": request,
                "opportunities_found": len(booking_response.get("opportunities", []))
            })
            
            # Generate response
            response_message = await self._generate_booking_response(booking_response, context)
            
            return self.create_success_response(
                message=response_message,
                data=booking_response,
                memories=[memory_id],
                suggestions=[
                    "Book this option",
                    "Find more alternatives",
                    "Check availability",
                    "Compare prices"
                ]
            )
            
        except Exception as e:
            logger.error(f"Booking inquiry failed: {e}")
            return self.create_error_response(
                message="I'm having trouble finding booking options. Could you be more specific about what you're looking for?",
                error_data={"error": str(e)}
            )
    
    async def _handle_preparation_help(self, request: str, context: LifecycleContext) -> LifecycleResponse:
        """Handle trip preparation assistance."""
        try:
            # Generate preparation checklist
            checklist = await self._generate_preparation_checklist(context)
            
            # Get weather forecast for the route
            weather_info = await self._get_route_weather_forecast(context)
            
            # Create memory
            memory_id = await self.create_memory(context, {
                "preparation_help": True,
                "checklist_items": len(checklist),
                "weather_checked": bool(weather_info)
            })
            
            # Generate response
            response_message = await self._generate_preparation_response(checklist, weather_info, context)
            
            return self.create_success_response(
                message=response_message,
                data={
                    "checklist": checklist,
                    "weather_forecast": weather_info
                },
                memories=[memory_id],
                suggestions=[
                    "Add custom checklist items",
                    "Check weather updates",
                    "Vehicle preparation tips",
                    "Emergency preparedness"
                ]
            )
            
        except Exception as e:
            logger.error(f"Preparation help failed: {e}")
            return self.create_error_response(
                message="I'm working on your preparation guide. Let me gather the essential information.",
                error_data={"error": str(e)}
            )
    
    async def _handle_general_planning(self, request: str, context: LifecycleContext) -> LifecycleResponse:
        """Handle general planning requests."""
        try:
            # Generate helpful response
            response_message = await self.ai_generate_response(
                f"Help the user with their pre-trip planning request: {request}",
                context
            )
            
            # Create memory
            memory_id = await self.create_memory(context, {
                "general_planning": True,
                "request": request
            })
            
            return self.create_success_response(
                message=response_message,
                data={"request_handled": True},
                memories=[memory_id],
                suggestions=[
                    "Plan the route",
                    "Discover stories",
                    "Create itinerary",
                    "Check preparations"
                ]
            )
            
        except Exception as e:
            logger.error(f"General planning failed: {e}")
            return self.create_error_response(
                message="I want to help with your planning. Could you tell me more about what you'd like to do?",
                error_data={"error": str(e)}
            )
    
    # Helper methods for complex operations
    async def _extract_locations_from_request(self, request: str) -> List[Dict[str, Any]]:
        """Extract location information from user request."""
        # In production, this would use NLP to extract locations
        # For now, return empty list - would need location service integration
        return []
    
    async def _generate_route_options(self, locations: List[Dict[str, Any]], 
                                    context: LifecycleContext) -> List[Dict[str, Any]]:
        """Generate route options based on locations."""
        # In production, integrate with mapping service
        return [{
            "id": "route_1",
            "name": "Scenic Route",
            "distance": 500,
            "duration": 8,
            "highlights": ["Mountain views", "Historic towns", "Natural landmarks"]
        }]
    
    async def _find_story_opportunities(self, routes: List[Dict[str, Any]], 
                                       context: LifecycleContext) -> List[Dict[str, Any]]:
        """Find story opportunities along routes."""
        # In production, query story database
        return [{
            "location": "Sample Location",
            "theme": "historical",
            "title": "The Great Adventure",
            "description": "A fascinating historical tale",
            "duration": "5 minutes"
        }]
    
    async def _generate_final_plan(self, context: LifecycleContext, 
                                  plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate final comprehensive trip plan."""
        return {
            "status": "ready",
            "route": plan_data.get("route_options", []),
            "stories": plan_data.get("story_opportunities", []),
            "itinerary": plan_data.get("itinerary", {}),
            "preparations": plan_data.get("checklist", [])
        }
    
    async def _generate_completion_message(self, context: LifecycleContext, 
                                         final_plan: Dict[str, Any]) -> str:
        """Generate exciting completion message."""
        prompt = f"""
        Create an exciting, motivational message for a user who has just completed
        their pre-trip planning. The message should:
        
        1. Congratulate them on completing the planning
        2. Build excitement for the journey ahead
        3. Briefly highlight what they have prepared
        4. Encourage them to begin their adventure
        
        Keep it warm, enthusiastic, and inspiring.
        """
        
        return await self.ai_generate_response(prompt, context)
    
    # Additional helper methods would be implemented here for:
    # - _extract_story_preferences
    # - _discover_stories_along_route
    # - _extract_itinerary_preferences
    # - _create_detailed_itinerary
    # - _generate_preparation_checklist
    # - _get_route_weather_forecast
    # - Various response generation methods