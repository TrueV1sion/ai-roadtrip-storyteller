"""
Lifecycle Orchestrator - Integration between lifecycle agents and master orchestration.

This module provides the integration layer between the lifecycle-based agents
and the existing master orchestration agent, enabling seamless transitions
between trip phases and coordinated state management.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

from app.core.unified_ai_client import UnifiedAIClient
from app.core.standardized_errors import handle_errors
from app.models.user import User
from app.models.trip import Trip
from app.services.memory.trip_memory_system import TripMemorySystem, TripPhase
from app.services.master_orchestration_agent import MasterOrchestrationAgent
from app.services.lifecycle_agents.base_lifecycle_agent import LifecycleContext, LifecycleResponse
from app.services.lifecycle_agents.pre_trip_agent import PreTripAgent
from app.services.lifecycle_agents.in_trip_agent import InTripAgent
from app.services.lifecycle_agents.post_trip_agent import PostTripAgent

logger = logging.getLogger(__name__)


class OrchestrationMode(Enum):
    """Orchestration modes for different interaction patterns."""
    LIFECYCLE_FOCUSED = "lifecycle_focused"  # Use lifecycle agents primarily
    MASTER_FOCUSED = "master_focused"       # Use master agent primarily
    HYBRID = "hybrid"                       # Intelligent routing between both


@dataclass
class OrchestrationRequest:
    """Request for orchestrated processing."""
    user_input: str
    user: User
    trip: Trip
    current_location: Optional[Dict[str, float]] = None
    context: Optional[Dict[str, Any]] = None
    mode: OrchestrationMode = OrchestrationMode.HYBRID
    force_phase: Optional[TripPhase] = None


@dataclass
class OrchestrationResponse:
    """Response from orchestrated processing."""
    response: str
    agent_used: str
    phase: TripPhase
    data: Dict[str, Any]
    memories_created: List[str]
    suggestions: List[str]
    phase_transition_suggested: Optional[TripPhase] = None


class LifecycleOrchestrator:
    """
    Orchestrates between lifecycle agents and master orchestration agent.
    
    This class provides intelligent routing between the lifecycle-based agents
    and the existing master orchestration agent, enabling seamless integration
    of Google's travel-concierge patterns with the AI Road Trip Storyteller's
    narrative capabilities.
    """
    
    def __init__(self, ai_client: UnifiedAIClient, memory_system: TripMemorySystem):
        self.ai_client = ai_client
        self.memory_system = memory_system
        
        # Initialize agents
        self.master_agent = MasterOrchestrationAgent(ai_client)
        self.pre_trip_agent = PreTripAgent(ai_client, memory_system)
        self.in_trip_agent = InTripAgent(ai_client, memory_system)
        self.post_trip_agent = PostTripAgent(ai_client, memory_system)
        
        # Agent mapping
        self.lifecycle_agents = {
            TripPhase.PRE_TRIP: self.pre_trip_agent,
            TripPhase.IN_TRIP: self.in_trip_agent,
            TripPhase.POST_TRIP: self.post_trip_agent
        }
        
        # State management
        self.active_sessions = {}  # user_id -> session_state
        self.default_mode = OrchestrationMode.HYBRID
        
        logger.info("Lifecycle Orchestrator initialized with all agents")
    
    @handle_errors(default_error_code="ORCHESTRATION_FAILED")
    async def process_request(self, request: OrchestrationRequest) -> OrchestrationResponse:
        """
        Process a request using intelligent agent routing.
        
        Args:
            request: The orchestration request containing user input and context
            
        Returns:
            OrchestrationResponse with the processed result
        """
        try:
            # Determine current trip phase
            current_phase = await self._determine_trip_phase(request)
            
            # Create lifecycle context
            context = self._create_lifecycle_context(request, current_phase)
            
            # Route to appropriate agent based on mode and phase
            if request.mode == OrchestrationMode.LIFECYCLE_FOCUSED:
                response = await self._process_with_lifecycle_agent(request, context, current_phase)
            elif request.mode == OrchestrationMode.MASTER_FOCUSED:
                response = await self._process_with_master_agent(request, context)
            else:  # HYBRID mode
                response = await self._process_with_hybrid_routing(request, context, current_phase)
            
            # Check for phase transitions
            transition_suggestion = await self._check_phase_transition(request, response, current_phase)
            if transition_suggestion:
                response.phase_transition_suggested = transition_suggestion
            
            # Update session state
            self._update_session_state(request.user.id, current_phase, response)
            
            logger.info(f"Orchestrated request for user {request.user.id} using {response.agent_used}")
            return response
            
        except Exception as e:
            logger.error(f"Orchestration failed: {e}")
            # Fallback to master agent
            return await self._create_fallback_response(request, str(e))
    
    async def transition_trip_phase(self, user: User, trip: Trip, 
                                   new_phase: TripPhase) -> OrchestrationResponse:
        """
        Transition a trip to a new phase.
        
        Args:
            user: The user whose trip is transitioning
            trip: The trip being transitioned
            new_phase: The new phase to transition to
            
        Returns:
            OrchestrationResponse with transition results
        """
        try:
            # Create context for transition
            context = LifecycleContext(
                user=user,
                trip=trip,
                current_location=None,
                preferences={}
            )
            
            # Get current phase agent
            current_phase = await self._determine_trip_phase(
                OrchestrationRequest(
                    user_input="",
                    user=user,
                    trip=trip
                )
            )
            
            # Finalize current phase
            if current_phase in self.lifecycle_agents:
                current_agent = self.lifecycle_agents[current_phase]
                await current_agent.finalize(context)
            
            # Initialize new phase
            if new_phase in self.lifecycle_agents:
                new_agent = self.lifecycle_agents[new_phase]
                lifecycle_response = await new_agent.initialize(context)
                
                # Update trip memory system
                await self.memory_system.transition_trip_phase(trip.id, new_phase)
                
                return OrchestrationResponse(
                    response=lifecycle_response.message,
                    agent_used=f"{new_phase.value}_agent",
                    phase=new_phase,
                    data=lifecycle_response.data,
                    memories_created=lifecycle_response.memories_created,
                    suggestions=lifecycle_response.next_suggestions
                )
            else:
                raise ValueError(f"No agent available for phase {new_phase}")
                
        except Exception as e:
            logger.error(f"Phase transition failed: {e}")
            return await self._create_fallback_response(
                OrchestrationRequest(
                    user_input=f"transition to {new_phase.value}",
                    user=user,
                    trip=trip
                ),
                str(e)
            )
    
    async def get_trip_status(self, user: User, trip: Trip) -> Dict[str, Any]:
        """
        Get comprehensive status of a trip across all phases.
        
        Args:
            user: The user requesting status
            trip: The trip to get status for
            
        Returns:
            Dictionary containing trip status across all phases
        """
        try:
            # Get current phase
            current_phase = await self._determine_trip_phase(
                OrchestrationRequest(
                    user_input="",
                    user=user,
                    trip=trip
                )
            )
            
            # Get memories from all phases
            all_memories = {}
            for phase in TripPhase:
                if phase != TripPhase.ARCHIVED:
                    memories = await self.memory_system.get_trip_memories(
                        trip.id,
                        phase=phase,
                        limit=10
                    )
                    all_memories[phase.value] = len(memories)
            
            # Get session state
            session_state = self.active_sessions.get(user.id, {})
            
            return {
                "trip_id": trip.id,
                "trip_name": trip.name,
                "current_phase": current_phase.value,
                "memory_counts": all_memories,
                "session_active": bool(session_state),
                "last_activity": session_state.get("last_activity"),
                "available_agents": [phase.value for phase in self.lifecycle_agents.keys()],
                "status": "active" if session_state else "inactive"
            }
            
        except Exception as e:
            logger.error(f"Status retrieval failed: {e}")
            return {
                "trip_id": trip.id,
                "error": str(e),
                "status": "error"
            }
    
    async def _determine_trip_phase(self, request: OrchestrationRequest) -> TripPhase:
        """Determine the current trip phase based on context."""
        # If forced phase is specified, use it
        if request.force_phase:
            return request.force_phase
        
        # Check session state first
        session_state = self.active_sessions.get(request.user.id)
        if session_state and "current_phase" in session_state:
            return TripPhase(session_state["current_phase"])
        
        # Get latest memories to determine phase
        try:
            recent_memories = await self.memory_system.get_trip_memories(
                request.trip.id,
                limit=5
            )
            
            if recent_memories:
                # Use the phase from the most recent memory
                return recent_memories[0].phase
            else:
                # No memories, assume pre-trip
                return TripPhase.PRE_TRIP
                
        except Exception as e:
            logger.error(f"Phase determination failed: {e}")
            return TripPhase.PRE_TRIP
    
    def _create_lifecycle_context(self, request: OrchestrationRequest, 
                                 phase: TripPhase) -> LifecycleContext:
        """Create lifecycle context from orchestration request."""
        return LifecycleContext(
            user=request.user,
            trip=request.trip,
            current_location=request.current_location,
            weather=request.context.get("weather") if request.context else None,
            time_of_day=request.context.get("time_of_day") if request.context else None,
            companions=request.context.get("companions", []) if request.context else [],
            preferences=request.context.get("preferences", {}) if request.context else {}
        )
    
    async def _process_with_lifecycle_agent(self, request: OrchestrationRequest,
                                          context: LifecycleContext, 
                                          phase: TripPhase) -> OrchestrationResponse:
        """Process request using lifecycle agent."""
        agent = self.lifecycle_agents.get(phase)
        if not agent:
            raise ValueError(f"No lifecycle agent available for phase {phase}")
        
        # Process with lifecycle agent
        lifecycle_response = await agent.process_request(request.user_input, context)
        
        return OrchestrationResponse(
            response=lifecycle_response.message,
            agent_used=f"{phase.value}_agent",
            phase=phase,
            data=lifecycle_response.data,
            memories_created=lifecycle_response.memories_created,
            suggestions=lifecycle_response.next_suggestions
        )
    
    async def _process_with_master_agent(self, request: OrchestrationRequest,
                                       context: LifecycleContext) -> OrchestrationResponse:
        """Process request using master orchestration agent."""
        # Convert to master agent context
        journey_context = self._create_master_agent_context(request, context)
        
        # Process with master agent
        master_response = await self.master_agent.process_user_input(
            request.user_input,
            journey_context,
            request.user
        )
        
        return OrchestrationResponse(
            response=master_response.text,
            agent_used="master_agent",
            phase=TripPhase.IN_TRIP,  # Master agent assumes in-trip
            data={"actions": master_response.actions},
            memories_created=[],
            suggestions=[]
        )
    
    async def _process_with_hybrid_routing(self, request: OrchestrationRequest,
                                         context: LifecycleContext,
                                         phase: TripPhase) -> OrchestrationResponse:
        """Process request using intelligent hybrid routing."""
        # Analyze request to determine best agent
        agent_choice = await self._analyze_agent_choice(request, context, phase)
        
        if agent_choice == "lifecycle":
            return await self._process_with_lifecycle_agent(request, context, phase)
        else:
            return await self._process_with_master_agent(request, context)
    
    async def _analyze_agent_choice(self, request: OrchestrationRequest,
                                   context: LifecycleContext, 
                                   phase: TripPhase) -> str:
        """Analyze which agent would best handle the request."""
        # Simple heuristics for agent choice
        user_input = request.user_input.lower()
        
        # Phase-specific routing
        if phase == TripPhase.PRE_TRIP:
            if any(word in user_input for word in ["plan", "route", "itinerary", "prepare"]):
                return "lifecycle"
        elif phase == TripPhase.POST_TRIP:
            if any(word in user_input for word in ["recap", "highlights", "memories", "share"]):
                return "lifecycle"
        
        # General story requests work well with lifecycle agents
        if any(word in user_input for word in ["story", "tell me about", "history"]):
            return "lifecycle"
        
        # Complex requests that need multiple agents - use master
        if any(word in user_input for word in ["book", "reserve", "find", "navigation"]):
            return "master"
        
        # Default to lifecycle agent for phase-specific requests
        return "lifecycle"
    
    def _create_master_agent_context(self, request: OrchestrationRequest,
                                    context: LifecycleContext):
        """Create master agent context from lifecycle context."""
        from app.services.master_orchestration_agent import JourneyContext
        
        return JourneyContext(
            current_location=context.current_location or {},
            current_time=datetime.utcnow(),
            journey_stage="active",
            passengers=[{"name": comp.get("name", "Unknown")} for comp in context.companions],
            vehicle_info={},
            weather=context.weather or {},
            route_info={}
        )
    
    async def _check_phase_transition(self, request: OrchestrationRequest,
                                    response: OrchestrationResponse,
                                    current_phase: TripPhase) -> Optional[TripPhase]:
        """Check if a phase transition should be suggested."""
        # Simple transition logic
        user_input = request.user_input.lower()
        
        if current_phase == TripPhase.PRE_TRIP:
            if any(word in user_input for word in ["start", "begin", "let's go", "ready"]):
                return TripPhase.IN_TRIP
        elif current_phase == TripPhase.IN_TRIP:
            if any(word in user_input for word in ["finished", "arrived", "done", "complete"]):
                return TripPhase.POST_TRIP
        
        return None
    
    def _update_session_state(self, user_id: str, phase: TripPhase, 
                             response: OrchestrationResponse):
        """Update session state with response information."""
        if user_id not in self.active_sessions:
            self.active_sessions[user_id] = {}
        
        self.active_sessions[user_id].update({
            "current_phase": phase.value,
            "last_activity": datetime.utcnow().isoformat(),
            "last_agent": response.agent_used,
            "memory_count": len(response.memories_created)
        })
    
    async def _create_fallback_response(self, request: OrchestrationRequest,
                                      error: str) -> OrchestrationResponse:
        """Create fallback response when orchestration fails."""
        return OrchestrationResponse(
            response="I'm here to help with your journey. Could you tell me more about what you need?",
            agent_used="fallback",
            phase=TripPhase.PRE_TRIP,
            data={"error": error},
            memories_created=[],
            suggestions=[
                "Tell me about your trip plans",
                "I need help with navigation",
                "Share a story about this place",
                "What's interesting around here?"
            ]
        )