"""
Integration Example - Shows how to use lifecycle agents with the AI Road Trip Storyteller.

This module provides examples of how to integrate the lifecycle-based agents
with the existing AI Road Trip Storyteller infrastructure.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

from backend.app.core.unified_ai_client import UnifiedAIClient
from backend.app.models.user import User
from backend.app.models.trip import Trip
from backend.app.services.memory.trip_memory_system import TripMemorySystem, TripPhase
from backend.app.services.lifecycle_agents import (
    LifecycleOrchestrator,
    OrchestrationRequest,
    OrchestrationMode,
    LifecycleContext
)

logger = logging.getLogger(__name__)


class LifecycleIntegrationExample:
    """
    Example class showing lifecycle agent integration patterns.
    
    This demonstrates how to:
    1. Initialize the lifecycle orchestrator
    2. Handle different trip phases
    3. Process user requests across phases
    4. Manage phase transitions
    5. Integrate with existing storytelling features
    """
    
    def __init__(self, ai_client: UnifiedAIClient, db_session):
        self.ai_client = ai_client
        self.db_session = db_session
        
        # Initialize memory system
        self.memory_system = TripMemorySystem(
            db=db_session,
            orchestrator=None  # Will be set after orchestrator init
        )
        
        # Initialize lifecycle orchestrator
        self.orchestrator = LifecycleOrchestrator(ai_client, self.memory_system)
        
        # Update memory system with orchestrator reference
        self.memory_system.orchestrator = self.orchestrator.master_agent
        
        logger.info("Lifecycle integration example initialized")
    
    async def example_full_trip_lifecycle(self, user: User, trip: Trip) -> Dict[str, Any]:
        """
        Example of a complete trip lifecycle using the agents.
        
        This demonstrates the full flow from pre-trip planning through
        post-trip memory consolidation.
        """
        results = {}
        
        try:
            # Phase 1: Pre-Trip Planning
            logger.info("Starting pre-trip phase")
            
            # Initialize pre-trip
            pre_trip_request = OrchestrationRequest(
                user_input="I'm planning a road trip and need help",
                user=user,
                trip=trip,
                mode=OrchestrationMode.LIFECYCLE_FOCUSED,
                force_phase=TripPhase.PRE_TRIP
            )
            
            pre_trip_response = await self.orchestrator.process_request(pre_trip_request)
            results["pre_trip_init"] = pre_trip_response
            
            # Plan the route
            route_request = OrchestrationRequest(
                user_input="Help me plan a route from San Francisco to Los Angeles with interesting stops",
                user=user,
                trip=trip,
                mode=OrchestrationMode.LIFECYCLE_FOCUSED
            )
            
            route_response = await self.orchestrator.process_request(route_request)
            results["route_planning"] = route_response
            
            # Discover stories
            story_request = OrchestrationRequest(
                user_input="What stories can you tell me along this route?",
                user=user,
                trip=trip,
                mode=OrchestrationMode.LIFECYCLE_FOCUSED
            )
            
            story_response = await self.orchestrator.process_request(story_request)
            results["story_discovery"] = story_response
            
            # Transition to in-trip
            logger.info("Transitioning to in-trip phase")
            transition_response = await self.orchestrator.transition_trip_phase(
                user, trip, TripPhase.IN_TRIP
            )
            results["transition_to_in_trip"] = transition_response
            
            # Phase 2: In-Trip Experience
            logger.info("Starting in-trip phase")
            
            # Simulate journey with location updates
            locations = [
                {"lat": 37.7749, "lng": -122.4194, "name": "San Francisco"},
                {"lat": 37.5665, "lng": -122.3756, "name": "San Mateo"},
                {"lat": 37.4419, "lng": -122.1430, "name": "Palo Alto"},
                {"lat": 37.3382, "lng": -121.8863, "name": "San Jose"}
            ]
            
            in_trip_responses = []
            for i, location in enumerate(locations):
                # Story request at location
                location_request = OrchestrationRequest(
                    user_input=f"Tell me a story about {location['name']}",
                    user=user,
                    trip=trip,
                    current_location=location,
                    context={
                        "weather": {"summary": "Clear", "temperature": 72},
                        "time_of_day": "afternoon"
                    },
                    mode=OrchestrationMode.LIFECYCLE_FOCUSED
                )
                
                location_response = await self.orchestrator.process_request(location_request)
                in_trip_responses.append(location_response)
                
                # Simulate some travel time
                await asyncio.sleep(0.1)  # Small delay for demo
            
            results["in_trip_stories"] = in_trip_responses
            
            # Navigation request
            nav_request = OrchestrationRequest(
                user_input="What's the best route to avoid traffic?",
                user=user,
                trip=trip,
                current_location=locations[-1],
                mode=OrchestrationMode.LIFECYCLE_FOCUSED
            )
            
            nav_response = await self.orchestrator.process_request(nav_request)
            results["navigation_help"] = nav_response
            
            # Transition to post-trip
            logger.info("Transitioning to post-trip phase")
            transition_response = await self.orchestrator.transition_trip_phase(
                user, trip, TripPhase.POST_TRIP
            )
            results["transition_to_post_trip"] = transition_response
            
            # Phase 3: Post-Trip Memories
            logger.info("Starting post-trip phase")
            
            # Generate highlights
            highlights_request = OrchestrationRequest(
                user_input="Generate highlights from my trip",
                user=user,
                trip=trip,
                mode=OrchestrationMode.LIFECYCLE_FOCUSED
            )
            
            highlights_response = await self.orchestrator.process_request(highlights_request)
            results["trip_highlights"] = highlights_response
            
            # Create trip recap
            recap_request = OrchestrationRequest(
                user_input="Create a trip recap for sharing",
                user=user,
                trip=trip,
                mode=OrchestrationMode.LIFECYCLE_FOCUSED
            )
            
            recap_response = await self.orchestrator.process_request(recap_request)
            results["trip_recap"] = recap_response
            
            # Compile stories
            compilation_request = OrchestrationRequest(
                user_input="Compile all the stories from my trip",
                user=user,
                trip=trip,
                mode=OrchestrationMode.LIFECYCLE_FOCUSED
            )
            
            compilation_response = await self.orchestrator.process_request(compilation_request)
            results["story_compilation"] = compilation_response
            
            logger.info("Full trip lifecycle example completed successfully")
            
        except Exception as e:
            logger.error(f"Trip lifecycle example failed: {e}")
            results["error"] = str(e)
        
        return results
    
    async def example_hybrid_mode_usage(self, user: User, trip: Trip) -> Dict[str, Any]:
        """
        Example of using hybrid mode for intelligent agent routing.
        
        This shows how the orchestrator can intelligently route between
        lifecycle agents and the master orchestration agent.
        """
        results = {}
        
        try:
            # Various requests that will be routed intelligently
            requests = [
                {
                    "input": "Tell me a story about this place",
                    "expected_agent": "lifecycle",
                    "description": "Story request - should go to lifecycle agent"
                },
                {
                    "input": "Find me a restaurant and book a table",
                    "expected_agent": "master",
                    "description": "Complex booking - should go to master agent"
                },
                {
                    "input": "Plan my route for tomorrow",
                    "expected_agent": "lifecycle", 
                    "description": "Planning request - should go to lifecycle agent"
                },
                {
                    "input": "What's the weather like ahead?",
                    "expected_agent": "master",
                    "description": "Multi-service request - should go to master agent"
                },
                {
                    "input": "Show me my trip highlights",
                    "expected_agent": "lifecycle",
                    "description": "Memory request - should go to lifecycle agent"
                }
            ]
            
            for i, req in enumerate(requests):
                orchestration_request = OrchestrationRequest(
                    user_input=req["input"],
                    user=user,
                    trip=trip,
                    current_location={"lat": 37.7749, "lng": -122.4194},
                    mode=OrchestrationMode.HYBRID
                )
                
                response = await self.orchestrator.process_request(orchestration_request)
                
                results[f"request_{i}"] = {
                    "input": req["input"],
                    "description": req["description"],
                    "expected_agent": req["expected_agent"],
                    "actual_agent": response.agent_used,
                    "response": response.response[:100] + "..." if len(response.response) > 100 else response.response
                }
                
                logger.info(f"Request {i}: '{req['input']}' -> {response.agent_used}")
            
        except Exception as e:
            logger.error(f"Hybrid mode example failed: {e}")
            results["error"] = str(e)
        
        return results
    
    async def example_memory_integration(self, user: User, trip: Trip) -> Dict[str, Any]:
        """
        Example of how lifecycle agents integrate with the trip memory system.
        
        This demonstrates memory creation, retrieval, and consolidation
        across different trip phases.
        """
        results = {}
        
        try:
            # Create some memories across different phases
            phases = [TripPhase.PRE_TRIP, TripPhase.IN_TRIP, TripPhase.POST_TRIP]
            memory_counts = {}
            
            for phase in phases:
                # Create context for the phase
                context = LifecycleContext(
                    user=user,
                    trip=trip,
                    current_location={"lat": 37.7749, "lng": -122.4194},
                    preferences={"interests": ["history", "nature"]}
                )
                
                # Create sample memory
                memory_id = await self.memory_system.create_trip_memory(
                    trip_id=trip.id,
                    phase=phase,
                    context={
                        "phase_example": True,
                        "demo_memory": f"Sample memory for {phase.value}",
                        "location": context.current_location,
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    location=context.current_location
                )
                
                # Get memories for this phase
                phase_memories = await self.memory_system.get_trip_memories(
                    trip.id,
                    phase=phase
                )
                
                memory_counts[phase.value] = len(phase_memories)
                logger.info(f"Phase {phase.value}: {len(phase_memories)} memories")
            
            results["memory_counts"] = memory_counts
            
            # Test memory consolidation
            transition_result = await self.memory_system.transition_trip_phase(
                trip.id,
                TripPhase.POST_TRIP
            )
            results["phase_transition"] = transition_result
            
            # Generate narrative from memories
            narrative = await self.memory_system.generate_memory_narrative(
                trip.id,
                narrative_style="adventure"
            )
            results["memory_narrative"] = narrative
            
        except Exception as e:
            logger.error(f"Memory integration example failed: {e}")
            results["error"] = str(e)
        
        return results
    
    async def get_trip_status_example(self, user: User, trip: Trip) -> Dict[str, Any]:
        """
        Example of getting comprehensive trip status.
        
        This shows how to get status information across all phases
        and active agents.
        """
        try:
            status = await self.orchestrator.get_trip_status(user, trip)
            logger.info(f"Trip status: {status}")
            return status
            
        except Exception as e:
            logger.error(f"Status example failed: {e}")
            return {"error": str(e)}


# Usage example function
async def run_lifecycle_examples():
    """
    Run all lifecycle integration examples.
    
    This function demonstrates how to use the lifecycle agents in practice.
    """
    # Note: In practice, these would be real instances from your application
    # ai_client = UnifiedAIClient()
    # db_session = get_db_session()
    # user = get_user_by_id(user_id)
    # trip = get_trip_by_id(trip_id)
    
    # For demo purposes, we'll create mock objects
    class MockUser:
        def __init__(self):
            self.id = "user_123"
            self.email = "traveler@example.com"
            self.preferences = {"interests": ["history", "nature"]}
    
    class MockTrip:
        def __init__(self):
            self.id = "trip_456"
            self.name = "Pacific Coast Adventure"
            self.route_info = {}
    
    # Mock implementations would be created here
    # example = LifecycleIntegrationExample(ai_client, db_session)
    # user = MockUser()
    # trip = MockTrip()
    
    print("Lifecycle Agents Integration Examples")
    print("=====================================")
    print()
    print("This module demonstrates how to integrate the lifecycle agents")
    print("with the AI Road Trip Storyteller. The examples show:")
    print()
    print("1. Full trip lifecycle (pre-trip -> in-trip -> post-trip)")
    print("2. Hybrid mode routing between agents")
    print("3. Memory system integration")
    print("4. Trip status monitoring")
    print()
    print("To run these examples with real data, initialize the")
    print("LifecycleIntegrationExample class with your AI client")
    print("and database session, then call the example methods.")
    
    # Uncomment these lines when you have real instances:
    # results = await example.example_full_trip_lifecycle(user, trip)
    # hybrid_results = await example.example_hybrid_mode_usage(user, trip)
    # memory_results = await example.example_memory_integration(user, trip)
    # status_results = await example.get_trip_status_example(user, trip)


if __name__ == "__main__":
    asyncio.run(run_lifecycle_examples())