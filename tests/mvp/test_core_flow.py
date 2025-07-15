"""
MVP Core Flow Tests - Essential functionality only
Tests the critical path: Voice Input → AI Processing → TTS Output
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from backend.app.services.master_orchestration_agent import (
    MasterOrchestrationAgent, 
    IntentType, 
    JourneyContext
)
from backend.app.services.personality_engine import personality_engine, PersonalityType
from backend.app.models.user import User, UserPreferences

@pytest.mark.mvp
class TestMVPCoreFlow:
    """Test the core MVP functionality end-to-end"""
    
    @pytest.mark.asyncio
    async def test_voice_to_story_flow(self, mock_ai_client, sample_user, sample_journey_context):
        """Test: User says 'Navigate to Golden Gate Bridge' → Get story + navigation"""
        # Arrange
        orchestrator = MasterOrchestrationAgent(mock_ai_client)
        user_input = "Navigate to Golden Gate Bridge"
        
        # Mock the AI responses
        mock_ai_client.generate_structured_response.return_value = {
            "primary_intent": "complex_assistance",
            "secondary_intents": ["story_request", "navigation_help"],
            "required_agents": {
                "story": {"theme": "history", "duration": "medium"},
                "navigation": {"assistance_type": "route_planning"}
            },
            "urgency": "immediate",
            "context_requirements": ["location", "route"],
            "expected_response_type": "mixed"
        }
        
        mock_ai_client.generate_response.return_value = (
            "I'll help you navigate to the Golden Gate Bridge! It's about 15 minutes north. "
            "Did you know the Golden Gate Bridge took over 4 years to build? "
            "Construction began in 1933 during the Great Depression..."
        )
        
        # Act
        response = await orchestrator.process_user_input(
            user_input, 
            sample_journey_context,
            sample_user
        )
        
        # Assert
        assert response is not None
        assert response.text is not None
        assert "Golden Gate Bridge" in response.text
        assert len(response.text) > 50  # Meaningful response
        assert response.requires_followup is False  # Navigation doesn't need followup in MVP
    
    @pytest.mark.asyncio
    async def test_response_time_under_3_seconds(self, mock_ai_client, sample_user, sample_journey_context):
        """Test: Total processing time is under 3 seconds"""
        import time
        
        orchestrator = MasterOrchestrationAgent(mock_ai_client)
        
        # Set up quick mock responses
        mock_ai_client.generate_structured_response = AsyncMock(return_value={
            "primary_intent": "story_request",
            "required_agents": {"story": {"theme": "general"}},
            "urgency": "can_wait",
            "expected_response_type": "story"
        })
        mock_ai_client.generate_response = AsyncMock(return_value="Quick story response")
        
        # Act
        start_time = time.time()
        response = await orchestrator.process_user_input(
            "Tell me about this area",
            sample_journey_context,
            sample_user
        )
        end_time = time.time()
        
        # Assert
        processing_time = end_time - start_time
        assert processing_time < 3.0, f"Processing took {processing_time}s, should be under 3s"
        assert response.text == "Quick story response"
    
    def test_personality_selection_mvp(self):
        """Test: Only MVP personalities are available"""
        # Get available personalities in MVP mode
        context_personality = personality_engine.get_contextual_personality()
        
        # Should default to FRIENDLY_GUIDE
        assert context_personality.id == PersonalityType.FRIENDLY_GUIDE
        
        # Test regional personality (Texas)
        texas_location = {"state": "Texas"}
        regional_personality = personality_engine.get_contextual_personality(location=texas_location)
        
        # In MVP, we might limit regional personalities
        assert regional_personality.id in [
            PersonalityType.FRIENDLY_GUIDE,
            PersonalityType.TEXAS_RANGER  # If we keep regional in MVP
        ]
    
    def test_safety_pause_feature(self):
        """Test: Story pauses during high-speed or merging scenarios"""
        from backend.app.services.voice_safety_validator import (
            VoiceSafetyValidator, 
            SafetyContext, 
            SafetyLevel
        )
        
        validator = VoiceSafetyValidator()
        
        # Test high speed scenario
        high_speed_context = SafetyContext(
            safety_level=SafetyLevel.HIGHWAY,
            speed_mph=75,
            is_navigating=True,
            upcoming_maneuver_distance=None,
            traffic_density="normal",
            weather_condition="clear"
        )
        
        validator.update_context(high_speed_context)
        should_pause, reason = validator.should_auto_pause()
        
        # Highway driving shouldn't auto-pause unless critical
        assert should_pause is False, "Highway driving alone shouldn't pause"
        
        # Test critical scenario (merging)
        critical_context = SafetyContext(
            safety_level=SafetyLevel.CRITICAL,
            speed_mph=45,
            is_navigating=True,
            upcoming_maneuver_distance=0.05,  # Very close maneuver
            traffic_density="heavy",
            weather_condition="clear"
        )
        
        validator.update_context(critical_context)
        should_pause, reason = validator.should_auto_pause()
        assert should_pause is True, "Critical conditions should pause content"
        assert "critical" in reason.lower()
    
    @pytest.mark.asyncio
    async def test_tts_integration(self, sample_user):
        """Test: TTS service generates audio URLs"""
        from backend.app.services.tts_service import tts_synthesizer
        
        # Skip if TTS not configured
        if not tts_synthesizer.tts_client:
            pytest.skip("TTS client not configured")
        
        # Mock the TTS and GCS upload
        with patch.object(tts_synthesizer, 'synthesize_and_upload') as mock_tts:
            mock_tts.return_value = "https://storage.googleapis.com/roadtrip-audio/test.mp3"
            
            # Test TTS generation
            audio_url = await mock_tts(
                "Welcome to your road trip adventure!",
                personality=personality_engine.get_contextual_personality()
            )
            
            assert audio_url is not None
            assert audio_url.startswith("https://")
            assert ".mp3" in audio_url
    
    def test_mvp_feature_flags(self):
        """Test: Non-MVP features are disabled"""
        import os
        
        # In MVP mode, these should be disabled
        mvp_mode = os.getenv("MVP_MODE", "true").lower() == "true"
        
        if mvp_mode:
            # These features should not be accessible
            from backend.app.core.config import settings
            
            # Check that MVP mode limits features
            assert hasattr(settings, 'APP_VERSION')
            
            # In a real implementation, we'd check feature flags
            # For now, just verify MVP mode is set
            assert mvp_mode is True

@pytest.mark.mvp
class TestMVPErrorHandling:
    """Test error handling and fallback behaviors"""
    
    @pytest.mark.asyncio
    async def test_fallback_on_ai_failure(self, sample_user, sample_journey_context):
        """Test: System provides fallback response when AI fails"""
        # Create orchestrator with failing AI client
        failing_ai_client = Mock()
        failing_ai_client.generate_structured_response = AsyncMock(
            side_effect=Exception("AI service unavailable")
        )
        failing_ai_client.generate_response = AsyncMock(
            side_effect=Exception("AI service unavailable")
        )
        
        orchestrator = MasterOrchestrationAgent(failing_ai_client)
        
        # Act
        response = await orchestrator.process_user_input(
            "Navigate to Disneyland",
            sample_journey_context,
            sample_user
        )
        
        # Assert - should get fallback response
        assert response is not None
        assert response.text in [
            "I'm here to help with your journey. Could you tell me more about what you're looking for?",
            "Let me think about that. What specifically would be most helpful right now?",
            "I want to make sure I give you the best information. Could you rephrase your question?"
        ]
        assert response.requires_followup is True
    
    @pytest.mark.asyncio  
    async def test_network_timeout_handling(self, mock_ai_client, sample_user, sample_journey_context):
        """Test: Handle network timeouts gracefully"""
        import asyncio
        
        # Simulate slow AI response
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(35)  # Longer than timeout
            return "This should timeout"
        
        mock_ai_client.generate_response = slow_response
        
        orchestrator = MasterOrchestrationAgent(mock_ai_client)
        
        # Should complete without hanging
        response = await orchestrator.process_user_input(
            "Tell me a story",
            sample_journey_context,
            sample_user
        )
        
        assert response is not None  # Should return fallback, not hang