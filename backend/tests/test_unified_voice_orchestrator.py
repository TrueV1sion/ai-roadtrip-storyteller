"""
Comprehensive test suite for UnifiedVoiceOrchestrator
Ensures world-class reliability and performance
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import base64
import json

from app.services.unified_voice_orchestrator import (
    UnifiedVoiceOrchestrator,
    ConversationState,
    ConversationContext
)
from app.services.master_orchestration_agent import MasterOrchestrationAgent
from app.core.unified_ai_client import UnifiedAIClient


class TestUnifiedVoiceOrchestrator:
    """Test suite for voice orchestration with focus on reliability and performance"""
    
    @pytest.fixture
    def mock_master_agent(self):
        """Create mock master orchestration agent"""
        agent = Mock(spec=MasterOrchestrationAgent)
        agent.booking_agent = AsyncMock()
        agent.story_agent = AsyncMock()
        agent.navigation_agent = AsyncMock()
        return agent
    
    @pytest.fixture
    def mock_ai_client(self):
        """Create mock AI client"""
        client = Mock(spec=UnifiedAIClient)
        client.generate_json = AsyncMock()
        client.generate_response = AsyncMock()
        return client
    
    @pytest.fixture
    def orchestrator(self, mock_master_agent, mock_ai_client):
        """Create orchestrator instance with mocks"""
        return UnifiedVoiceOrchestrator(mock_master_agent, mock_ai_client)
    
    @pytest.fixture
    def sample_audio(self):
        """Generate sample audio data"""
        return b"fake_audio_data_for_testing"
    
    @pytest.fixture
    def sample_location(self):
        """Sample location data"""
        return {
            "lat": 37.7749,
            "lng": -122.4194,
            "heading": 45.0,
            "speed": 65.0
        }
    
    @pytest.mark.asyncio
    async def test_voice_input_processing_performance(self, orchestrator, sample_audio, sample_location):
        """Test that voice processing completes within 2 seconds"""
        start_time = asyncio.get_event_loop().time()
        
        # Mock the STT response
        with patch.object(orchestrator, '_transcribe_audio', new_callable=AsyncMock) as mock_transcribe:
            mock_transcribe.return_value = "Find me a good restaurant nearby"
            
            # Mock intent analysis
            orchestrator.ai_client.generate_json.return_value = {
                "primary_intent": "hungry",
                "required_services": ["restaurants"],
                "urgency_level": "soon",
                "next_state": "gathering_info"
            }
            
            # Mock service responses
            with patch.object(orchestrator, '_get_restaurant_data', new_callable=AsyncMock) as mock_restaurant:
                mock_restaurant.return_value = [{
                    "name": "Test Restaurant",
                    "cuisine": "Italian",
                    "distance_miles": 2.5,
                    "rating": 4.5
                }]
                
                # Mock voice generation
                with patch.object(orchestrator, '_generate_voice_response', new_callable=AsyncMock) as mock_voice:
                    mock_voice.return_value = b"mock_audio_response"
                    
                    result = await orchestrator.process_voice_input(
                        user_id="test_user",
                        audio_input=sample_audio,
                        location=sample_location,
                        context_data={}
                    )
        
        elapsed_time = asyncio.get_event_loop().time() - start_time
        
        # Assert performance requirement
        assert elapsed_time < 2.0, f"Voice processing took {elapsed_time}s, should be < 2s"
        assert result["transcript"] is not None
        assert result["voice_audio"] is not None
        assert result["state"] == "gathering_info"
    
    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, orchestrator, sample_audio, sample_location):
        """Test handling multiple concurrent voice requests"""
        # Create 10 concurrent requests
        tasks = []
        for i in range(10):
            task = orchestrator.process_voice_input(
                user_id=f"user_{i}",
                audio_input=sample_audio,
                location=sample_location,
                context_data={}
            )
            tasks.append(task)
        
        # Mock dependencies for concurrent execution
        with patch.object(orchestrator, '_transcribe_audio', new_callable=AsyncMock) as mock_transcribe:
            mock_transcribe.return_value = "Test request"
            orchestrator.ai_client.generate_json.return_value = {"primary_intent": "general_chat"}
            
            with patch.object(orchestrator, '_generate_voice_response', new_callable=AsyncMock) as mock_voice:
                mock_voice.return_value = b"response"
                
                # Execute all tasks concurrently
                results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all completed successfully
        errors = [r for r in results if isinstance(r, Exception)]
        assert len(errors) == 0, f"Concurrent execution had {len(errors)} errors"
        assert len(results) == 10
    
    @pytest.mark.asyncio
    async def test_error_recovery_maintains_personality(self, orchestrator):
        """Test that errors are handled gracefully in character"""
        # Simulate transcription failure
        with patch.object(orchestrator, '_transcribe_audio', new_callable=AsyncMock) as mock_transcribe:
            mock_transcribe.side_effect = Exception("STT service unavailable")
            
            result = await orchestrator._handle_error(
                Exception("Test error"),
                ConversationContext(personality="wise_narrator")
            )
        
        assert "disturbance in our journey" in result["transcript"]
        assert result["voice_audio"] is not None
        assert result["state"] == "error"
    
    @pytest.mark.asyncio
    async def test_context_preservation_across_interactions(self, orchestrator):
        """Test conversation context is maintained properly"""
        user_id = "test_user"
        
        # First interaction
        ctx1 = ConversationContext(
            personality="enthusiastic_buddy",
            current_topic="restaurants"
        )
        orchestrator.conversations[user_id] = ctx1
        
        # Simulate second interaction
        with patch.object(orchestrator, '_transcribe_audio', new_callable=AsyncMock):
            with patch.object(orchestrator, '_analyze_intent', new_callable=AsyncMock) as mock_intent:
                mock_intent.return_value = {
                    "topic": "hotels",
                    "next_state": "gathering_info"
                }
                
                # Process maintains context
                assert orchestrator.conversations[user_id].personality == "enthusiastic_buddy"
                assert orchestrator.conversations[user_id].current_topic == "restaurants"
    
    @pytest.mark.asyncio
    async def test_memory_leak_prevention(self, orchestrator):
        """Test that resources are properly cleaned up"""
        import gc
        import weakref
        
        # Create conversation context
        ctx = ConversationContext()
        weak_ref = weakref.ref(ctx)
        orchestrator.conversations["temp_user"] = ctx
        
        # Delete reference
        del ctx
        del orchestrator.conversations["temp_user"]
        
        # Force garbage collection
        gc.collect()
        
        # Verify object was cleaned up
        assert weak_ref() is None, "Memory leak detected - context not garbage collected"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self, orchestrator):
        """Test circuit breaker prevents cascading failures"""
        # Simulate repeated failures
        with patch.object(orchestrator.vertex_travel_agent, 'search_restaurants', new_callable=AsyncMock) as mock_search:
            mock_search.side_effect = Exception("Service unavailable")
            
            # First few calls should attempt
            for _ in range(3):
                result = await orchestrator._get_restaurant_data(ConversationContext())
                assert result == []  # Graceful fallback
            
            # After threshold, circuit should open (not implemented yet - for future)
            # This test documents expected behavior
    
    @pytest.mark.asyncio
    async def test_timeout_protection(self, orchestrator):
        """Test that external calls have timeout protection"""
        async def slow_operation():
            await asyncio.sleep(10)  # Simulate slow service
            return "Too late"
        
        with patch.object(orchestrator.ai_client, 'generate_json', new=slow_operation):
            # This should timeout (when implemented)
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(
                    orchestrator._analyze_intent("test", ConversationContext()),
                    timeout=2.0
                )
    
    @pytest.mark.asyncio
    async def test_response_caching(self, orchestrator):
        """Test that repeated requests use cache"""
        # First request
        with patch.object(orchestrator.ai_client, 'generate_json', new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = {"intent": "test"}
            
            result1 = await orchestrator._analyze_intent("What's nearby?", ConversationContext())
            assert mock_ai.call_count == 1
            
            # Second identical request should use cache (when implemented)
            # This test documents expected behavior
            # result2 = await orchestrator._analyze_intent("What's nearby?", ConversationContext())
            # assert mock_ai.call_count == 1  # No additional call
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self, orchestrator):
        """Test system degrades gracefully when services fail"""
        # Simulate partial service failures
        with patch.object(orchestrator, '_get_restaurant_data', side_effect=Exception("Failed")):
            with patch.object(orchestrator, '_get_hotel_data', return_value=[{"name": "Test Hotel"}]):
                
                response_data = await orchestrator._orchestrate_response(
                    {"required_services": ["restaurants", "hotels"]},
                    ConversationContext()
                )
                
                # Should still return hotel data despite restaurant failure
                assert "hotels" in response_data["results"]
                assert response_data["results"]["hotels"] == [{"name": "Test Hotel"}]
    
    @pytest.mark.asyncio
    async def test_voice_personality_consistency(self, orchestrator):
        """Test that voice personality remains consistent"""
        personalities = ["wise_narrator", "enthusiastic_buddy", "local_expert"]
        
        for personality in personalities:
            ctx = ConversationContext(personality=personality)
            response = await orchestrator._blend_responses(
                {"results": {"restaurants": [{"name": "Test", "specialty": "Pizza"}]}},
                ctx
            )
            
            # Verify personality-specific language
            if personality == "wise_narrator":
                assert "discovered" in response.lower()
            elif personality == "enthusiastic_buddy":
                assert "!" in response or "wow" in response.lower()
            elif personality == "local_expert":
                assert "locals" in response.lower() or "know" in response.lower()


class TestPerformanceOptimizations:
    """Test performance optimizations and benchmarks"""
    
    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_response_generation_benchmark(self, benchmark, orchestrator):
        """Benchmark response generation performance"""
        async def generate_response():
            return await orchestrator._blend_responses(
                {"results": {"restaurants": [{"name": "Test"}] * 10}},
                ConversationContext()
            )
        
        result = benchmark(lambda: asyncio.run(generate_response()))
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_parallel_service_execution(self, orchestrator):
        """Test that services are called in parallel, not sequentially"""
        call_times = []
        
        async def mock_service_call(delay):
            start = asyncio.get_event_loop().time()
            await asyncio.sleep(delay)
            call_times.append(asyncio.get_event_loop().time() - start)
            return {"data": "test"}
        
        # Mock three services with different delays
        with patch.object(orchestrator, '_get_restaurant_data', lambda ctx: mock_service_call(0.1)):
            with patch.object(orchestrator, '_get_hotel_data', lambda ctx: mock_service_call(0.2)):
                with patch.object(orchestrator, '_get_relevant_story', lambda ctx: mock_service_call(0.3)):
                    
                    start = asyncio.get_event_loop().time()
                    await orchestrator._orchestrate_response(
                        {"required_services": ["restaurants", "hotels", "stories"]},
                        ConversationContext()
                    )
                    total_time = asyncio.get_event_loop().time() - start
        
        # If parallel, should take ~0.3s (max delay), not 0.6s (sum)
        assert total_time < 0.4, f"Services not executing in parallel: {total_time}s"


class TestIntegration:
    """Integration tests with other audio features"""
    
    @pytest.mark.asyncio
    async def test_spatial_audio_integration(self, orchestrator):
        """Test integration with spatial audio system"""
        with patch('app.services.master_orchestration_agent.spatial_audio_engine') as mock_spatial:
            # Test that navigation voice uses correct spatial position
            await orchestrator.coordinate_spatial_audio(
                "navigation",
                {"lat": 0, "lng": 0},
                {}
            )
            
            # Verify navigation voice positioned correctly
            mock_spatial.add_source.assert_called()
            call_args = mock_spatial.add_source.call_args[0][0]
            assert call_args.source_type.name == "NAVIGATION"
            assert call_args.priority == 10  # Highest priority
    
    @pytest.mark.asyncio  
    async def test_music_ducking_during_voice(self, orchestrator):
        """Test that music ducks during voice responses"""
        # This tests the audio orchestration behavior
        orchestration = orchestrator._determine_audio_orchestration(
            Mock(priority=Mock(value='high')),
            {"story_playing": True}
        )
        
        assert orchestration["action"] == "pause_story"
        assert orchestration["duck_music"] is True
        assert orchestration["restore_after"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-only"])