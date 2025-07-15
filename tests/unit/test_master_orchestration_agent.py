"""Unit tests for the Master Orchestration Agent."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import json

from backend.app.services.master_orchestration_agent import (
    MasterOrchestrationAgent,
    AgentCommand,
    AgentResponse,
    ConversationContext,
    ExecutionPlan
)
from backend.app.models.user import User
from backend.app.core.config import get_settings


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = Mock(spec=User)
    user.id = 1
    user.email = "test@example.com"
    user.preferences = {
        "interests": ["history", "nature"],
        "travel_style": "adventurous",
        "dietary_restrictions": ["vegetarian"]
    }
    return user


@pytest.fixture
def mock_context():
    """Create a mock conversation context."""
    return ConversationContext(
        user_id=1,
        session_id="test-session-123",
        location={"lat": 37.7749, "lng": -122.4194},
        current_route=None,
        active_agents=[],
        conversation_history=[]
    )


@pytest.fixture
def mock_agents():
    """Create mock agent instances."""
    navigation_agent = AsyncMock()
    navigation_agent.name = "navigation"
    navigation_agent.process_command = AsyncMock(return_value={
        "route": {"distance": "50 miles", "duration": "1 hour"},
        "alternatives": []
    })
    
    booking_agent = AsyncMock()
    booking_agent.name = "booking"
    booking_agent.process_command = AsyncMock(return_value={
        "reservation_id": "RES123",
        "status": "confirmed",
        "details": {"restaurant": "Test Restaurant", "time": "7:00 PM"}
    })
    
    story_agent = AsyncMock()
    story_agent.name = "story"
    story_agent.process_command = AsyncMock(return_value={
        "story": "Once upon a time...",
        "theme": "historical"
    })
    
    contextual_agent = AsyncMock()
    contextual_agent.name = "contextual"
    contextual_agent.process_command = AsyncMock(return_value={
        "suggestions": ["Visit the local museum", "Try the famous bakery"],
        "weather": {"temp": 72, "conditions": "sunny"}
    })
    
    local_expert_agent = AsyncMock()
    local_expert_agent.name = "local_expert"
    local_expert_agent.process_command = AsyncMock(return_value={
        "recommendations": ["Hidden waterfall trail", "Best sunset spot"],
        "insights": "This area is known for..."
    })
    
    return {
        "navigation": navigation_agent,
        "booking": booking_agent,
        "story": story_agent,
        "contextual": contextual_agent,
        "local_expert": local_expert_agent
    }


@pytest.fixture
def orchestration_agent(mock_agents):
    """Create a master orchestration agent with mocked dependencies."""
    with patch('backend.app.services.master_orchestration_agent.NavigationAgent', return_value=mock_agents["navigation"]), \
         patch('backend.app.services.master_orchestration_agent.BookingAgent', return_value=mock_agents["booking"]), \
         patch('backend.app.services.master_orchestration_agent.StoryGenerationAgent', return_value=mock_agents["story"]), \
         patch('backend.app.services.master_orchestration_agent.ContextualAwarenessAgent', return_value=mock_agents["contextual"]), \
         patch('backend.app.services.master_orchestration_agent.LocalExpertAgent', return_value=mock_agents["local_expert"]):
        
        agent = MasterOrchestrationAgent()
        agent.agents = mock_agents
        return agent


class TestMasterOrchestrationAgent:
    """Test suite for Master Orchestration Agent."""
    
    @pytest.mark.asyncio
    async def test_intent_classification_navigation(self, orchestration_agent):
        """Test intent classification for navigation commands."""
        commands = [
            "Take me to San Francisco",
            "Navigate to the Golden Gate Bridge",
            "Find the fastest route to downtown",
            "Show me alternative routes",
            "How long to get to the airport?"
        ]
        
        for command in commands:
            intent = await orchestration_agent.classify_intent(command)
            assert intent["primary"] == "navigation"
            assert intent["confidence"] > 0.7
    
    @pytest.mark.asyncio
    async def test_intent_classification_booking(self, orchestration_agent):
        """Test intent classification for booking commands."""
        commands = [
            "Book a table for 4 at 7pm",
            "Make a reservation at Italian restaurant",
            "Reserve tickets for the museum",
            "I need a hotel for tonight",
            "Cancel my dinner reservation"
        ]
        
        for command in commands:
            intent = await orchestration_agent.classify_intent(command)
            assert intent["primary"] == "booking"
            assert intent["confidence"] > 0.7
    
    @pytest.mark.asyncio
    async def test_intent_classification_story(self, orchestration_agent):
        """Test intent classification for story commands."""
        commands = [
            "Tell me about this place",
            "What's the history here?",
            "Share a ghost story",
            "Give me interesting facts about this area",
            "Tell me a story about the Civil War"
        ]
        
        for command in commands:
            intent = await orchestration_agent.classify_intent(command)
            assert intent["primary"] == "story"
            assert intent["confidence"] > 0.7
    
    @pytest.mark.asyncio
    async def test_intent_classification_contextual(self, orchestration_agent):
        """Test intent classification for contextual awareness."""
        commands = [
            "What's the weather like?",
            "Any good coffee shops nearby?",
            "What should I do here?",
            "Are there any events today?",
            "What time does the sun set?"
        ]
        
        for command in commands:
            intent = await orchestration_agent.classify_intent(command)
            assert intent["primary"] in ["contextual", "local_expert"]
            assert intent["confidence"] > 0.6
    
    @pytest.mark.asyncio
    async def test_multi_intent_detection(self, orchestration_agent):
        """Test detection of multiple intents in complex commands."""
        command = "Navigate to San Francisco and book a table for dinner at 7pm"
        intent = await orchestration_agent.classify_intent(command)
        
        assert intent["primary"] in ["navigation", "booking"]
        assert len(intent.get("secondary", [])) > 0
        assert "navigation" in [intent["primary"]] + intent.get("secondary", [])
        assert "booking" in [intent["primary"]] + intent.get("secondary", [])
    
    @pytest.mark.asyncio
    async def test_execution_plan_creation(self, orchestration_agent, mock_context):
        """Test creation of execution plans for commands."""
        command = AgentCommand(
            text="Take me to Golden Gate Bridge and tell me its history",
            user_id=1,
            context=mock_context
        )
        
        plan = await orchestration_agent.create_execution_plan(command)
        
        assert isinstance(plan, ExecutionPlan)
        assert len(plan.steps) >= 2
        assert any(step.agent == "navigation" for step in plan.steps)
        assert any(step.agent == "story" for step in plan.steps)
        assert plan.parallel_execution is not None
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self, orchestration_agent, mock_context, mock_agents):
        """Test parallel execution of independent tasks."""
        command = AgentCommand(
            text="What's the weather and tell me about local restaurants",
            user_id=1,
            context=mock_context
        )
        
        response = await orchestration_agent.process_command(command)
        
        # Both agents should be called
        mock_agents["contextual"].process_command.assert_called()
        mock_agents["local_expert"].process_command.assert_called()
        
        assert response.success
        assert len(response.results) >= 2
    
    @pytest.mark.asyncio
    async def test_sequential_execution(self, orchestration_agent, mock_context, mock_agents):
        """Test sequential execution of dependent tasks."""
        # Mock navigation to return a route
        mock_agents["navigation"].process_command.return_value = {
            "route": {
                "waypoints": [
                    {"name": "Start", "lat": 37.7749, "lng": -122.4194},
                    {"name": "End", "lat": 37.8199, "lng": -122.4783}
                ],
                "duration": "30 minutes"
            }
        }
        
        command = AgentCommand(
            text="Navigate to Golden Gate Bridge then find restaurants near there",
            user_id=1,
            context=mock_context
        )
        
        response = await orchestration_agent.process_command(command)
        
        # Navigation should be called first
        assert mock_agents["navigation"].process_command.call_count >= 1
        # Then booking/local expert for restaurants
        assert mock_agents["booking"].process_command.call_count >= 1 or \
               mock_agents["local_expert"].process_command.call_count >= 1
        
        assert response.success
    
    @pytest.mark.asyncio
    async def test_error_handling_single_agent_failure(self, orchestration_agent, mock_context, mock_agents):
        """Test handling when one agent fails."""
        # Make navigation fail
        mock_agents["navigation"].process_command.side_effect = Exception("Navigation service unavailable")
        
        command = AgentCommand(
            text="Navigate to downtown and tell me about it",
            user_id=1,
            context=mock_context
        )
        
        response = await orchestration_agent.process_command(command)
        
        # Should still get story response even if navigation fails
        assert mock_agents["story"].process_command.called
        assert response.success  # Partial success
        assert any("error" in str(r).lower() for r in response.results)
    
    @pytest.mark.asyncio
    async def test_error_handling_all_agents_fail(self, orchestration_agent, mock_context, mock_agents):
        """Test handling when all agents fail."""
        # Make all agents fail
        for agent in mock_agents.values():
            agent.process_command.side_effect = Exception("Service unavailable")
        
        command = AgentCommand(
            text="Do something",
            user_id=1,
            context=mock_context
        )
        
        response = await orchestration_agent.process_command(command)
        
        assert not response.success
        assert response.error is not None
        assert "failed" in response.error.lower()
    
    @pytest.mark.asyncio
    async def test_context_preservation(self, orchestration_agent, mock_context):
        """Test that context is preserved across agent calls."""
        mock_context.conversation_history = [
            {"role": "user", "content": "I'm vegetarian"},
            {"role": "assistant", "content": "I'll keep that in mind for restaurant recommendations."}
        ]
        
        command = AgentCommand(
            text="Find me a good restaurant",
            user_id=1,
            context=mock_context
        )
        
        response = await orchestration_agent.process_command(command)
        
        # Verify context was passed to agents
        assert response.success
        # The context should include dietary preferences
    
    @pytest.mark.asyncio
    async def test_response_aggregation(self, orchestration_agent, mock_context, mock_agents):
        """Test aggregation of responses from multiple agents."""
        command = AgentCommand(
            text="Plan my evening with dinner and entertainment",
            user_id=1,
            context=mock_context
        )
        
        response = await orchestration_agent.process_command(command)
        
        assert response.success
        assert isinstance(response.aggregated_response, str)
        assert len(response.aggregated_response) > 0
        assert response.metadata is not None
        assert "agents_used" in response.metadata
    
    @pytest.mark.asyncio
    async def test_conversation_state_management(self, orchestration_agent, mock_context):
        """Test conversation state updates."""
        initial_history_len = len(mock_context.conversation_history)
        
        command = AgentCommand(
            text="Navigate to the museum",
            user_id=1,
            context=mock_context
        )
        
        response = await orchestration_agent.process_command(command)
        
        # Conversation history should be updated
        assert len(response.context.conversation_history) > initial_history_len
        assert response.context.active_agents == ["navigation"]
    
    @pytest.mark.asyncio
    async def test_agent_coordination(self, orchestration_agent, mock_context, mock_agents):
        """Test coordination between multiple agents."""
        # Setup mock to simulate route with specific location
        mock_agents["navigation"].process_command.return_value = {
            "route": {
                "destination": {"lat": 37.8199, "lng": -122.4783, "name": "Golden Gate Bridge"},
                "duration": "30 minutes"
            }
        }
        
        command = AgentCommand(
            text="Take me to Golden Gate Bridge and book a restaurant nearby for dinner",
            user_id=1,
            context=mock_context
        )
        
        response = await orchestration_agent.process_command(command)
        
        # Both agents should be called
        assert mock_agents["navigation"].process_command.called
        assert mock_agents["booking"].process_command.called
        
        # Booking should receive location context from navigation
        booking_call_args = mock_agents["booking"].process_command.call_args[0][0]
        assert booking_call_args.context.location is not None
    
    @pytest.mark.asyncio
    async def test_performance_monitoring(self, orchestration_agent, mock_context):
        """Test performance metrics collection."""
        command = AgentCommand(
            text="Simple navigation request",
            user_id=1,
            context=mock_context
        )
        
        response = await orchestration_agent.process_command(command)
        
        assert response.metadata is not None
        assert "execution_time" in response.metadata
        assert "agent_timings" in response.metadata
        assert isinstance(response.metadata["execution_time"], float)
    
    @pytest.mark.asyncio
    async def test_fallback_behavior(self, orchestration_agent, mock_context):
        """Test fallback behavior for unclear commands."""
        command = AgentCommand(
            text="Xyz abc 123",  # Nonsense command
            user_id=1,
            context=mock_context
        )
        
        response = await orchestration_agent.process_command(command)
        
        # Should fall back to contextual awareness or return helpful message
        assert response.success
        assert len(response.aggregated_response) > 0
        assert "understand" in response.aggregated_response.lower() or \
               "help" in response.aggregated_response.lower()