"""
Comprehensive unit tests for the Master Orchestration Agent.
Tests intent analysis, agent coordination, response generation, and error handling.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any

from backend.app.services.master_orchestration_agent import (
    MasterOrchestrationAgent,
    IntentType,
    UrgencyLevel,
    IntentAnalysis,
    AgentTask,
    AgentResponse,
    JourneyContext,
    ConversationState
)
from backend.app.models.user import User
from backend.app.core.unified_ai_client import UnifiedAIClient


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = Mock(spec=User)
    user.id = "test-user-123"
    user.email = "test@example.com"
    user.preferences = {
        "interests": ["history", "nature"],
        "voice_personality": "friendly_guide"
    }
    return user


@pytest.fixture
def mock_ai_client():
    """Create a mock AI client."""
    client = Mock(spec=UnifiedAIClient)
    client.generate_response = AsyncMock()
    return client


@pytest.fixture
def mock_sub_agents():
    """Create mock sub-agents."""
    return {
        "story_agent": AsyncMock(),
        "booking_agent": AsyncMock(),
        "navigation_agent": AsyncMock(),
        "context_agent": AsyncMock(),
        "local_expert_agent": AsyncMock()
    }


@pytest.fixture
def journey_context():
    """Create a sample journey context."""
    return JourneyContext(
        current_location={"lat": 37.7749, "lng": -122.4194, "city": "San Francisco"},
        current_time=datetime.now(),
        journey_stage="en_route",
        passengers=[{"type": "adult", "count": 2}],
        vehicle_info={"type": "sedan", "fuel": "electric"},
        weather={"condition": "sunny", "temp": 72},
        route_info={"destination": "Los Angeles", "distance": 380, "duration": 360}
    )


@pytest.fixture
async def orchestrator(mock_ai_client, mock_sub_agents):
    """Create a master orchestration agent with mocks."""
    with patch.multiple(
        'backend.app.services.master_orchestration_agent',
        StoryGenerationAgent=mock_sub_agents["story_agent"],
        BookingAgent=mock_sub_agents["booking_agent"],
        NavigationAgent=mock_sub_agents["navigation_agent"],
        ContextualAwarenessAgent=mock_sub_agents["context_agent"],
        LocalExpertAgent=mock_sub_agents["local_expert_agent"]
    ):
        agent = MasterOrchestrationAgent(mock_ai_client)
        yield agent


class TestIntentAnalysis:
    """Test intent analysis functionality."""
    
    @pytest.mark.asyncio
    async def test_analyze_story_request_intent(self, orchestrator, mock_user, journey_context):
        """Test analyzing a story request intent."""
        message = "Tell me an interesting story about this area"
        
        # Mock AI response for intent analysis
        orchestrator.ai_client.generate_response.return_value = {
            "primary_intent": "story_request",
            "secondary_intents": ["local_interest"],
            "urgency": "immediate",
            "context_needed": ["location", "interests"]
        }
        
        result = await orchestrator._analyze_intent(message, journey_context, mock_user)
        
        assert result.primary_intent == IntentType.STORY_REQUEST
        assert result.urgency == UrgencyLevel.IMMEDIATE
        assert "story_generation" in result.required_agents
        assert "contextual_awareness" in result.required_agents
    
    @pytest.mark.asyncio
    async def test_analyze_booking_intent(self, orchestrator, mock_user, journey_context):
        """Test analyzing a booking inquiry intent."""
        message = "Are there any good restaurants nearby?"
        
        orchestrator.ai_client.generate_response.return_value = {
            "primary_intent": "booking_inquiry",
            "secondary_intents": ["dining", "location_based"],
            "urgency": "can_wait",
            "context_needed": ["location", "time", "preferences"]
        }
        
        result = await orchestrator._analyze_intent(message, journey_context, mock_user)
        
        assert result.primary_intent == IntentType.BOOKING_INQUIRY
        assert result.urgency == UrgencyLevel.CAN_WAIT
        assert "booking" in result.required_agents
    
    @pytest.mark.asyncio
    async def test_analyze_navigation_intent(self, orchestrator, mock_user, journey_context):
        """Test analyzing a navigation help intent."""
        message = "How long until we reach the next rest stop?"
        
        orchestrator.ai_client.generate_response.return_value = {
            "primary_intent": "navigation_help",
            "secondary_intents": ["route_info", "timing"],
            "urgency": "immediate",
            "context_needed": ["route", "current_location"]
        }
        
        result = await orchestrator._analyze_intent(message, journey_context, mock_user)
        
        assert result.primary_intent == IntentType.NAVIGATION_HELP
        assert result.urgency == UrgencyLevel.IMMEDIATE
        assert "navigation" in result.required_agents
    
    @pytest.mark.asyncio
    async def test_analyze_complex_intent(self, orchestrator, mock_user, journey_context):
        """Test analyzing a complex multi-intent request."""
        message = "Find a restaurant with a view and tell me about the history while we drive there"
        
        orchestrator.ai_client.generate_response.return_value = {
            "primary_intent": "complex_assistance",
            "secondary_intents": ["booking_inquiry", "story_request", "navigation_help"],
            "urgency": "immediate",
            "context_needed": ["location", "route", "preferences", "interests"]
        }
        
        result = await orchestrator._analyze_intent(message, journey_context, mock_user)
        
        assert result.primary_intent == IntentType.COMPLEX_ASSISTANCE
        assert len(result.secondary_intents) >= 2
        assert len(result.required_agents) >= 3


class TestAgentCoordination:
    """Test coordination between sub-agents."""
    
    @pytest.mark.asyncio
    async def test_single_agent_task(self, orchestrator, mock_sub_agents):
        """Test executing a single agent task."""
        task = AgentTask(
            task_type="generate_story",
            parameters={"theme": "history", "location": "San Francisco"},
            priority=1,
            timeout_seconds=10
        )
        
        # Mock story agent response
        mock_sub_agents["story_agent"].return_value.execute_task.return_value = {
            "story": "Once upon a time in San Francisco...",
            "audio_url": "https://example.com/story.mp3"
        }
        
        results = await orchestrator._execute_agent_tasks([task])
        
        assert len(results) == 1
        assert "story" in results[0]
        assert results[0]["story"].startswith("Once upon a time")
    
    @pytest.mark.asyncio
    async def test_parallel_agent_tasks(self, orchestrator, mock_sub_agents):
        """Test executing multiple agent tasks in parallel."""
        tasks = [
            AgentTask(
                task_type="generate_story",
                parameters={"theme": "history"},
                priority=1,
                timeout_seconds=10
            ),
            AgentTask(
                task_type="find_restaurants",
                parameters={"cuisine": "italian"},
                priority=2,
                timeout_seconds=10
            ),
            AgentTask(
                task_type="get_route_info",
                parameters={"destination": "LA"},
                priority=1,
                timeout_seconds=10
            )
        ]
        
        # Mock agent responses
        mock_sub_agents["story_agent"].return_value.execute_task.return_value = {
            "story": "Historical tale..."
        }
        mock_sub_agents["booking_agent"].return_value.execute_task.return_value = {
            "restaurants": [{"name": "Luigi's", "rating": 4.5}]
        }
        mock_sub_agents["navigation_agent"].return_value.execute_task.return_value = {
            "distance": 380, "duration": 360
        }
        
        results = await orchestrator._execute_agent_tasks(tasks)
        
        assert len(results) == 3
        # Verify tasks were executed based on priority
        assert any("story" in r for r in results)
        assert any("restaurants" in r for r in results)
        assert any("distance" in r for r in results)
    
    @pytest.mark.asyncio
    async def test_agent_task_timeout(self, orchestrator, mock_sub_agents):
        """Test handling of agent task timeout."""
        task = AgentTask(
            task_type="slow_task",
            parameters={},
            priority=1,
            timeout_seconds=0.1  # Very short timeout
        )
        
        # Mock slow agent response
        async def slow_response():
            await asyncio.sleep(1)  # Longer than timeout
            return {"data": "too late"}
        
        mock_sub_agents["story_agent"].return_value.execute_task.side_effect = slow_response
        
        results = await orchestrator._execute_agent_tasks([task])
        
        assert len(results) == 1
        assert "error" in results[0]
        assert "timeout" in results[0]["error"].lower()
    
    @pytest.mark.asyncio
    async def test_agent_task_error_handling(self, orchestrator, mock_sub_agents):
        """Test handling of agent task errors."""
        task = AgentTask(
            task_type="failing_task",
            parameters={},
            priority=1,
            timeout_seconds=10
        )
        
        # Mock agent error
        mock_sub_agents["story_agent"].return_value.execute_task.side_effect = Exception("Agent failed")
        
        results = await orchestrator._execute_agent_tasks([task])
        
        assert len(results) == 1
        assert "error" in results[0]
        assert "Agent failed" in results[0]["error"]


class TestResponseGeneration:
    """Test response generation and synthesis."""
    
    @pytest.mark.asyncio
    async def test_synthesize_simple_response(self, orchestrator):
        """Test synthesizing a simple response from single agent."""
        agent_results = [
            {"story": "A fascinating tale about the Golden Gate Bridge...", "audio_url": "story.mp3"}
        ]
        intent = IntentAnalysis(
            primary_intent=IntentType.STORY_REQUEST,
            secondary_intents=[],
            required_agents={"story_generation": {}},
            urgency=UrgencyLevel.IMMEDIATE,
            context_requirements=["location"],
            expected_response_type="narrative"
        )
        
        orchestrator.ai_client.generate_response.return_value = {
            "response": "Here's an interesting story about the Golden Gate Bridge...",
            "actions": [],
            "booking_opportunities": []
        }
        
        response = await orchestrator._synthesize_response(agent_results, intent)
        
        assert isinstance(response, AgentResponse)
        assert "Golden Gate Bridge" in response.text
        assert response.audio_url == "story.mp3"
        assert not response.requires_followup
    
    @pytest.mark.asyncio
    async def test_synthesize_complex_response(self, orchestrator):
        """Test synthesizing a complex response from multiple agents."""
        agent_results = [
            {"story": "Historical context..."},
            {"restaurants": [
                {"name": "Vista Restaurant", "rating": 4.8, "booking_url": "https://book.example.com"}
            ]},
            {"route": {"distance": 5, "duration": 10, "directions": ["Turn right", "Continue 5 miles"]}}
        ]
        intent = IntentAnalysis(
            primary_intent=IntentType.COMPLEX_ASSISTANCE,
            secondary_intents=[IntentType.BOOKING_INQUIRY, IntentType.STORY_REQUEST],
            required_agents={"story_generation": {}, "booking": {}, "navigation": {}},
            urgency=UrgencyLevel.IMMEDIATE,
            context_requirements=["all"],
            expected_response_type="mixed"
        )
        
        orchestrator.ai_client.generate_response.return_value = {
            "response": "I found Vista Restaurant 5 miles ahead with great views. While we drive there, let me tell you about the history...",
            "actions": [{"type": "show_restaurant", "data": {"name": "Vista Restaurant"}}],
            "booking_opportunities": [{"type": "restaurant", "name": "Vista Restaurant", "url": "https://book.example.com"}]
        }
        
        response = await orchestrator._synthesize_response(agent_results, intent)
        
        assert isinstance(response, AgentResponse)
        assert "Vista Restaurant" in response.text
        assert len(response.actions) > 0
        assert len(response.booking_opportunities) > 0
    
    @pytest.mark.asyncio
    async def test_synthesize_error_response(self, orchestrator):
        """Test synthesizing response when some agents fail."""
        agent_results = [
            {"error": "Story generation failed"},
            {"restaurants": [{"name": "Backup Restaurant"}]}
        ]
        intent = IntentAnalysis(
            primary_intent=IntentType.COMPLEX_ASSISTANCE,
            secondary_intents=[],
            required_agents={"story_generation": {}, "booking": {}},
            urgency=UrgencyLevel.CAN_WAIT,
            context_requirements=["all"],
            expected_response_type="mixed"
        )
        
        orchestrator.ai_client.generate_response.return_value = {
            "response": "I found a restaurant for you, though I'm having trouble with the story feature right now.",
            "actions": [{"type": "show_restaurant"}],
            "booking_opportunities": []
        }
        
        response = await orchestrator._synthesize_response(agent_results, intent)
        
        assert isinstance(response, AgentResponse)
        assert "restaurant" in response.text.lower()
        assert response.requires_followup  # Should follow up due to partial failure


class TestConversationManagement:
    """Test conversation state management."""
    
    def test_conversation_state_initialization(self):
        """Test initializing conversation state."""
        state = ConversationState()
        
        assert len(state.message_history) == 0
        assert len(state.active_topics) == 0
        assert len(state.pending_actions) == 0
    
    def test_add_user_message(self):
        """Test adding user messages to conversation history."""
        state = ConversationState()
        
        state.add_user_message("Hello", {"location": "SF"})
        state.add_user_message("Tell me a story")
        
        assert len(state.message_history) == 2
        assert state.message_history[0]["speaker"] == "user"
        assert state.message_history[0]["content"] == "Hello"
        assert state.message_history[0]["context"]["location"] == "SF"
    
    def test_add_assistant_message(self):
        """Test adding assistant messages to conversation history."""
        state = ConversationState()
        
        response = AgentResponse(
            text="Here's your story...",
            audio_url="story.mp3",
            actions=[],
            booking_opportunities=[],
            conversation_state_updates={"topic": "story"}
        )
        
        state.add_assistant_message(response)
        
        assert len(state.message_history) == 1
        assert state.message_history[0]["speaker"] == "assistant"
        assert state.message_history[0]["content"] == "Here's your story..."
    
    def test_conversation_history_limit(self):
        """Test that conversation history is limited to prevent memory issues."""
        state = ConversationState()
        
        # Add many messages
        for i in range(150):
            state.add_user_message(f"Message {i}")
        
        # Should keep only recent messages (default 100)
        assert len(state.message_history) <= 100
        assert state.message_history[-1]["content"] == "Message 149"
    
    def test_update_active_topics(self):
        """Test updating active conversation topics."""
        state = ConversationState()
        
        state.update_active_topics({
            "restaurant_search": {"status": "active", "cuisine": "italian"},
            "story": {"status": "completed", "theme": "history"}
        })
        
        assert "restaurant_search" in state.active_topics
        assert state.active_topics["restaurant_search"]["cuisine"] == "italian"


class TestProcessMessage:
    """Test the main message processing flow."""
    
    @pytest.mark.asyncio
    async def test_process_simple_message(self, orchestrator, mock_user, journey_context):
        """Test processing a simple user message."""
        message = "Tell me about this area"
        
        # Mock intent analysis
        orchestrator.ai_client.generate_response.side_effect = [
            # Intent analysis response
            {
                "primary_intent": "story_request",
                "secondary_intents": [],
                "urgency": "immediate",
                "context_needed": ["location"]
            },
            # Response synthesis
            {
                "response": "Let me tell you about San Francisco...",
                "actions": [],
                "booking_opportunities": []
            }
        ]
        
        # Mock story agent
        with patch.object(orchestrator, 'story_agent') as mock_story:
            mock_story.execute_task = AsyncMock(return_value={
                "story": "San Francisco has a rich history...",
                "audio_url": "sf_story.mp3"
            })
            
            response = await orchestrator.process_message(
                message=message,
                user=mock_user,
                journey_context=journey_context
            )
        
        assert isinstance(response, AgentResponse)
        assert "San Francisco" in response.text
        assert response.audio_url == "sf_story.mp3"
    
    @pytest.mark.asyncio
    async def test_process_message_with_conversation_history(self, orchestrator, mock_user, journey_context):
        """Test processing message with conversation context."""
        # Set up conversation history
        orchestrator.conversation_states[mock_user.id] = ConversationState()
        orchestrator.conversation_states[mock_user.id].add_user_message("What restaurants are nearby?")
        orchestrator.conversation_states[mock_user.id].update_active_topics({
            "restaurant_search": {"status": "active"}
        })
        
        message = "Something with outdoor seating"
        
        orchestrator.ai_client.generate_response.side_effect = [
            # Intent analysis (should recognize context)
            {
                "primary_intent": "booking_inquiry",
                "secondary_intents": [],
                "urgency": "immediate",
                "context_needed": ["preferences"]
            },
            # Response synthesis
            {
                "response": "I found several restaurants with outdoor seating...",
                "actions": [{"type": "show_restaurants"}],
                "booking_opportunities": [{"type": "restaurant", "name": "Patio Cafe"}]
            }
        ]
        
        with patch.object(orchestrator, 'booking_agent') as mock_booking:
            mock_booking.execute_task = AsyncMock(return_value={
                "restaurants": [{"name": "Patio Cafe", "outdoor_seating": True}]
            })
            
            response = await orchestrator.process_message(
                message=message,
                user=mock_user,
                journey_context=journey_context
            )
        
        assert "outdoor seating" in response.text
        assert len(response.booking_opportunities) > 0
    
    @pytest.mark.asyncio
    async def test_process_message_error_handling(self, orchestrator, mock_user, journey_context):
        """Test error handling in message processing."""
        message = "Test error handling"
        
        # Mock AI client to raise an error
        orchestrator.ai_client.generate_response.side_effect = Exception("AI service unavailable")
        
        response = await orchestrator.process_message(
            message=message,
            user=mock_user,
            journey_context=journey_context
        )
        
        assert isinstance(response, AgentResponse)
        assert "trouble understanding" in response.text.lower() or "error" in response.text.lower()
        assert response.requires_followup


class TestEdgeCases:
    """Test edge cases and error scenarios."""
    
    @pytest.mark.asyncio
    async def test_empty_message(self, orchestrator, mock_user, journey_context):
        """Test handling empty message."""
        response = await orchestrator.process_message(
            message="",
            user=mock_user,
            journey_context=journey_context
        )
        
        assert isinstance(response, AgentResponse)
        assert "didn't catch that" in response.text.lower() or "say that again" in response.text.lower()
    
    @pytest.mark.asyncio
    async def test_null_journey_context(self, orchestrator, mock_user):
        """Test handling null journey context."""
        message = "Hello"
        
        orchestrator.ai_client.generate_response.return_value = {
            "primary_intent": "general_chat",
            "secondary_intents": [],
            "urgency": "can_wait",
            "context_needed": []
        }
        
        # Should handle gracefully without journey context
        response = await orchestrator.process_message(
            message=message,
            user=mock_user,
            journey_context=None
        )
        
        assert isinstance(response, AgentResponse)
    
    @pytest.mark.asyncio
    async def test_concurrent_messages(self, orchestrator, mock_user, journey_context):
        """Test handling concurrent messages from same user."""
        messages = ["First message", "Second message", "Third message"]
        
        orchestrator.ai_client.generate_response.return_value = {
            "primary_intent": "general_chat",
            "secondary_intents": [],
            "urgency": "can_wait",
            "context_needed": []
        }
        
        # Process messages concurrently
        tasks = [
            orchestrator.process_message(msg, mock_user, journey_context)
            for msg in messages
        ]
        
        responses = await asyncio.gather(*tasks)
        
        assert len(responses) == 3
        assert all(isinstance(r, AgentResponse) for r in responses)
        
        # Check conversation history maintained order
        history = orchestrator.conversation_states[mock_user.id].message_history
        user_messages = [m for m in history if m["speaker"] == "user"]
        assert len(user_messages) == 3


class TestPerformance:
    """Test performance-related aspects."""
    
    @pytest.mark.asyncio
    async def test_response_time_under_limit(self, orchestrator, mock_user, journey_context):
        """Test that responses are generated within acceptable time."""
        import time
        
        message = "Quick test"
        
        orchestrator.ai_client.generate_response.return_value = {
            "primary_intent": "general_chat",
            "secondary_intents": [],
            "urgency": "immediate",
            "context_needed": []
        }
        
        start_time = time.time()
        response = await orchestrator.process_message(
            message=message,
            user=mock_user,
            journey_context=journey_context
        )
        end_time = time.time()
        
        # Response should be generated within 5 seconds
        assert (end_time - start_time) < 5.0
        assert isinstance(response, AgentResponse)
    
    @pytest.mark.asyncio
    async def test_memory_cleanup(self, orchestrator, mock_user, journey_context):
        """Test that memory is properly cleaned up."""
        # Process many messages
        for i in range(10):
            await orchestrator.process_message(
                message=f"Message {i}",
                user=mock_user,
                journey_context=journey_context
            )
        
        # Check conversation state is maintained
        assert mock_user.id in orchestrator.conversation_states
        
        # Simulate user inactivity
        orchestrator._cleanup_inactive_conversations()
        
        # Long-inactive conversations should be cleaned up
        # (Would need to mock time for proper testing)