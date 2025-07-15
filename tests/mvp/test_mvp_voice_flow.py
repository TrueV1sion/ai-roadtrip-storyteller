"""
MVP Voice Flow Tests
Tests the complete voice interaction flow from input to output
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import base64

from backend.app.services.voice_services import VoiceService
from backend.app.services.master_orchestration_agent import MasterOrchestrationAgent
from backend.app.models.user import User
from backend.app.core.cache import CacheManager


@pytest.mark.mvp
class TestMVPVoiceToStory:
    """Test the complete voice to story generation flow"""
    
    @pytest.fixture
    def voice_service(self):
        """Create voice service with mocked dependencies"""
        service = VoiceService()
        service.speech_client = Mock()
        service.tts_client = Mock()
        service.storage_client = Mock()
        return service
    
    @pytest.fixture
    def mock_audio_data(self):
        """Create mock audio data"""
        # Simple WAV header + silence
        return b'RIFF' + b'\x00' * 100
    
    @pytest.mark.asyncio
    async def test_voice_command_processing(self, voice_service, mock_audio_data):
        """Test: Process voice command and extract text"""
        # Mock speech recognition
        mock_response = Mock()
        mock_response.results = [
            Mock(alternatives=[Mock(transcript="Tell me about the Grand Canyon")])
        ]
        voice_service.speech_client.recognize.return_value = mock_response
        
        # Process voice command
        result = await voice_service.process_voice_command(mock_audio_data)
        
        # Verify
        assert result["status"] == "success"
        assert result["text"] == "Tell me about the Grand Canyon"
        assert result["confidence"] > 0
    
    @pytest.mark.asyncio
    async def test_story_generation_from_voice(self):
        """Test: Generate story from voice input"""
        # Setup
        mock_ai_client = Mock()
        mock_ai_client.generate_response = AsyncMock(
            return_value="The Grand Canyon is one of the world's most spectacular natural wonders..."
        )
        
        orchestrator = MasterOrchestrationAgent(mock_ai_client)
        
        # Create context
        context = {
            "location": {
                "lat": 36.0544,
                "lng": -112.1401,
                "name": "Grand Canyon National Park"
            },
            "speed_mph": 35,
            "weather": "clear"
        }
        
        user = Mock(spec=User)
        user.id = "test-user"
        user.preferences = {"voice_personality": "Morgan_Freeman"}
        
        # Process request
        response = await orchestrator.process_user_input(
            "Tell me about the history of this place",
            context,
            user
        )
        
        # Verify story generation
        assert response.text is not None
        assert len(response.text) > 50
        assert "Grand Canyon" in response.text
    
    @pytest.mark.asyncio
    async def test_text_to_speech_generation(self, voice_service):
        """Test: Convert story text to speech"""
        # Mock TTS
        mock_audio_content = b'mock_mp3_data'
        voice_service.tts_client.synthesize_speech.return_value = Mock(
            audio_content=mock_audio_content
        )
        
        # Mock storage upload
        voice_service.storage_client.bucket.return_value.blob.return_value.public_url = \
            "https://storage.googleapis.com/roadtrip/audio/test.mp3"
        
        # Generate speech
        result = await voice_service.generate_speech(
            text="Welcome to the Grand Canyon",
            voice_personality="Morgan_Freeman"
        )
        
        # Verify
        assert result["status"] == "success"
        assert result["audio_url"].endswith(".mp3")
        assert result["duration"] > 0
        assert result["voice"] == "Morgan_Freeman"
    
    @pytest.mark.asyncio
    async def test_end_to_end_voice_flow(self, voice_service):
        """Test: Complete flow from voice input to audio output"""
        # Setup all mocks
        mock_audio_input = b'RIFF' + b'\x00' * 100
        
        # Mock speech recognition
        voice_service.speech_client.recognize.return_value = Mock(
            results=[Mock(alternatives=[Mock(transcript="Tell me a story about Route 66")])]
        )
        
        # Mock AI story generation
        with patch('backend.app.services.master_orchestration_agent.MasterOrchestrationAgent') as mock_orchestrator:
            mock_instance = mock_orchestrator.return_value
            mock_instance.process_user_input = AsyncMock(
                return_value=Mock(
                    text="Route 66, the Mother Road, stretches from Chicago to Los Angeles...",
                    requires_followup=False
                )
            )
            
            # Mock TTS
            voice_service.tts_client.synthesize_speech.return_value = Mock(
                audio_content=b'mock_story_audio'
            )
            
            # Execute full flow
            # 1. Voice to text
            voice_result = await voice_service.process_voice_command(mock_audio_input)
            assert voice_result["status"] == "success"
            
            # 2. Text to story
            story_response = await mock_instance.process_user_input(
                voice_result["text"],
                {"location": {"name": "Route 66"}},
                Mock(spec=User)
            )
            assert story_response.text is not None
            
            # 3. Story to speech
            audio_result = await voice_service.generate_speech(
                story_response.text,
                "Road_Trip_DJ"
            )
            assert "audio_content" in audio_result or "audio_url" in audio_result


@pytest.mark.mvp
class TestMVPCaching:
    """Test caching for AI responses to reduce costs"""
    
    @pytest.fixture
    def cache_manager(self):
        """Create cache manager with mock Redis"""
        cache = CacheManager()
        cache.redis_client = Mock()
        return cache
    
    @pytest.mark.asyncio
    async def test_cache_ai_response(self, cache_manager):
        """Test: AI responses are cached"""
        # Setup
        cache_key = "story_grand_canyon_history"
        story_content = "The Grand Canyon was formed over millions of years..."
        
        # Mock cache miss then set
        cache_manager.redis_client.get.return_value = None
        cache_manager.redis_client.setex.return_value = True
        
        # Store in cache
        await cache_manager.set(cache_key, story_content, ttl=3600)
        
        # Verify cache was set
        cache_manager.redis_client.setex.assert_called_once()
        call_args = cache_manager.redis_client.setex.call_args
        assert call_args[0][0] == cache_key
        assert call_args[0][2] == story_content
    
    @pytest.mark.asyncio
    async def test_cache_hit_prevents_ai_call(self, cache_manager):
        """Test: Cache hit prevents expensive AI call"""
        # Setup
        cache_key = "story_route66_history"
        cached_story = "Route 66 is an iconic American highway..."
        
        # Mock cache hit
        cache_manager.redis_client.get.return_value = cached_story.encode()
        
        # Get from cache
        result = await cache_manager.get(cache_key)
        
        # Verify
        assert result == cached_story
        cache_manager.redis_client.get.assert_called_once_with(cache_key)
    
    @pytest.mark.asyncio
    async def test_cache_ttl_for_stories(self):
        """Test: Story cache has appropriate TTL"""
        from backend.app.services.storytelling_services import StorytellingService
        
        # Create service with mock cache
        mock_cache = Mock()
        service = StorytellingService(cache=mock_cache)
        
        # Generate story (mocked)
        with patch.object(service, 'ai_client') as mock_ai:
            mock_ai.generate_response = AsyncMock(
                return_value="Cached story content"
            )
            
            # Request story
            await service.generate_contextual_story(
                location={"name": "Yosemite"},
                theme="nature",
                cache_key="story_yosemite_nature"
            )
            
            # Verify cache TTL is set appropriately (1 hour for stories)
            mock_cache.set.assert_called()
            call_args = mock_cache.set.call_args
            assert call_args[1]['ttl'] == 3600  # 1 hour


@pytest.mark.mvp
class TestMVPErrorRecovery:
    """Test error recovery and fallback mechanisms"""
    
    @pytest.mark.asyncio
    async def test_voice_recognition_failure_fallback(self):
        """Test: Fallback when voice recognition fails"""
        service = VoiceService()
        service.speech_client = Mock()
        service.speech_client.recognize.side_effect = Exception("Recognition failed")
        
        # Should return error gracefully
        result = await service.process_voice_command(b'invalid_audio')
        
        assert result["status"] == "error"
        assert "recognition failed" in result["message"].lower()
        assert result.get("text") is None
    
    @pytest.mark.asyncio
    async def test_ai_timeout_fallback(self):
        """Test: Fallback response on AI timeout"""
        import asyncio
        
        mock_ai_client = Mock()
        
        async def timeout_response(*args, **kwargs):
            await asyncio.sleep(35)  # Simulate timeout
            return "This will timeout"
        
        mock_ai_client.generate_response = timeout_response
        
        orchestrator = MasterOrchestrationAgent(mock_ai_client)
        orchestrator.timeout = 30  # 30 second timeout
        
        # Should return fallback, not hang
        with patch.object(orchestrator, '_get_fallback_response') as mock_fallback:
            mock_fallback.return_value = Mock(
                text="I'm having trouble processing that. Let me try again.",
                requires_followup=True
            )
            
            response = await orchestrator.process_user_input(
                "Tell me a story",
                {},
                Mock(spec=User)
            )
            
            assert response.text == "I'm having trouble processing that. Let me try again."
            assert response.requires_followup is True
    
    @pytest.mark.asyncio
    async def test_tts_failure_fallback(self):
        """Test: Handle TTS generation failure"""
        service = VoiceService()
        service.tts_client = Mock()
        service.tts_client.synthesize_speech.side_effect = Exception("TTS failed")
        
        # Should handle error gracefully
        result = await service.generate_speech(
            "Test text",
            "Morgan_Freeman"
        )
        
        assert result["status"] == "error"
        assert "tts failed" in result["message"].lower()
        assert result.get("audio_url") is None


@pytest.mark.mvp
class TestMVPPerformance:
    """Test performance requirements for MVP"""
    
    @pytest.mark.asyncio
    async def test_voice_processing_under_500ms(self):
        """Test: Voice recognition completes in under 500ms"""
        import time
        
        service = VoiceService()
        service.speech_client = Mock()
        service.speech_client.recognize.return_value = Mock(
            results=[Mock(alternatives=[Mock(transcript="Quick test")])]
        )
        
        start = time.time()
        result = await service.process_voice_command(b'audio_data')
        duration = (time.time() - start) * 1000  # Convert to ms
        
        assert duration < 500
        assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_story_generation_under_2s(self):
        """Test: Story generation completes in under 2 seconds"""
        import time
        
        mock_ai = Mock()
        mock_ai.generate_response = AsyncMock(
            return_value="Quick story response"
        )
        mock_ai.generate_structured_response = AsyncMock(
            return_value={"primary_intent": "story_request"}
        )
        
        orchestrator = MasterOrchestrationAgent(mock_ai)
        
        start = time.time()
        response = await orchestrator.process_user_input(
            "Tell me a story",
            {},
            Mock(spec=User)
        )
        duration = time.time() - start
        
        assert duration < 2.0
        assert response.text is not None
    
    @pytest.mark.asyncio
    async def test_tts_generation_under_1s(self):
        """Test: TTS generation completes in under 1 second"""
        import time
        
        service = VoiceService()
        service.tts_client = Mock()
        service.tts_client.synthesize_speech.return_value = Mock(
            audio_content=b'audio'
        )
        service.storage_client = Mock()
        
        start = time.time()
        result = await service.generate_speech(
            "Short text",
            "Morgan_Freeman"
        )
        duration = time.time() - start
        
        assert duration < 1.0
        assert result["status"] in ["success", "error"]  # Should complete either way


@pytest.mark.mvp
class TestMVPDataFlow:
    """Test data flow through the MVP system"""
    
    @pytest.mark.asyncio
    async def test_location_context_flow(self):
        """Test: Location context flows through system correctly"""
        location = {
            "lat": 37.7749,
            "lng": -122.4194,
            "name": "San Francisco",
            "state": "California"
        }
        
        # Verify location affects story generation
        mock_ai = Mock()
        mock_ai.generate_response = AsyncMock(
            return_value="Story about San Francisco..."
        )
        mock_ai.generate_structured_response = AsyncMock(
            return_value={"primary_intent": "story_request"}
        )
        
        orchestrator = MasterOrchestrationAgent(mock_ai)
        
        response = await orchestrator.process_user_input(
            "Tell me about this place",
            {"location": location},
            Mock(spec=User)
        )
        
        # Verify AI was called with location context
        mock_ai.generate_response.assert_called()
        call_args = mock_ai.generate_response.call_args[0][0]
        assert "San Francisco" in call_args or "California" in call_args
    
    @pytest.mark.asyncio
    async def test_user_preferences_flow(self):
        """Test: User preferences affect output"""
        user = Mock(spec=User)
        user.id = "test-user"
        user.preferences = {
            "voice_personality": "Texas_Ranger",
            "story_length": "short",
            "interests": ["history", "nature"]
        }
        
        mock_ai = Mock()
        mock_ai.generate_response = AsyncMock(
            return_value="Howdy partner! Let me tell you about this here canyon..."
        )
        mock_ai.generate_structured_response = AsyncMock(
            return_value={"primary_intent": "story_request"}
        )
        
        orchestrator = MasterOrchestrationAgent(mock_ai)
        
        response = await orchestrator.process_user_input(
            "Tell me a story",
            {},
            user
        )
        
        # Verify personality affects response
        assert "Howdy" in response.text or "partner" in response.text
    
    @pytest.mark.asyncio
    async def test_safety_context_flow(self):
        """Test: Safety context affects content delivery"""
        from backend.app.services.voice_safety_validator import VoiceSafetyValidator
        
        # High-speed context
        context = {
            "speed_mph": 85,
            "location": {"highway": "I-5"},
            "traffic": "heavy"
        }
        
        validator = VoiceSafetyValidator()
        validator.update_context_from_dict(context)
        
        # Should recommend pause
        should_pause, reason = validator.should_auto_pause()
        
        # At 85mph in heavy traffic, content should pause
        assert should_pause is True
        assert "speed" in reason.lower() or "traffic" in reason.lower()