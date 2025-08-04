"""
Comprehensive unit tests for voice services.
Tests TTS, STT, voice personalities, and voice safety features.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
import base64
from typing import Dict, Any

from app.services.voice_services import (
    VoiceService,
    VoicePersonality,
    VoiceSafetyChecker,
    PersonalityManager,
    VoiceInteractionContext,
    SafetyViolationType,
    VoiceMetrics
)
from app.models.user import User
from app.core.config import settings


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = Mock(spec=User)
    user.id = "test-user-123"
    user.email = "driver@example.com"
    user.preferences = {
        "voice_personality": "friendly_guide",
        "voice_speed": 1.0,
        "voice_language": "en-US"
    }
    return user


@pytest.fixture
def mock_tts_client():
    """Create a mock TTS client."""
    client = Mock()
    client.synthesize_speech = AsyncMock()
    return client


@pytest.fixture
def mock_stt_client():
    """Create a mock STT client."""
    client = Mock()
    client.recognize = AsyncMock()
    return client


@pytest.fixture
def voice_context():
    """Create a sample voice interaction context."""
    return VoiceInteractionContext(
        is_driving=True,
        speed_mph=65,
        traffic_condition="moderate",
        time_of_day="afternoon",
        weather_condition="clear",
        passenger_count=2,
        conversation_duration_minutes=5
    )


@pytest.fixture
async def voice_service(mock_tts_client, mock_stt_client):
    """Create a voice service with mocks."""
    with patch('backend.app.services.voice_services.texttospeech.TextToSpeechClient', return_value=mock_tts_client):
        with patch('backend.app.services.voice_services.speech.SpeechClient', return_value=mock_stt_client):
            service = VoiceService()
            yield service


class TestVoicePersonalities:
    """Test voice personality management."""
    
    def test_personality_initialization(self):
        """Test initializing voice personalities."""
        personality = VoicePersonality(
            id="friendly_guide",
            name="Friendly Guide",
            voice_name="en-US-Neural2-F",
            pitch=0.0,
            speaking_rate=1.0,
            style_attributes={
                "friendliness": 0.9,
                "formality": 0.3,
                "enthusiasm": 0.8
            }
        )
        
        assert personality.id == "friendly_guide"
        assert personality.voice_name == "en-US-Neural2-F"
        assert personality.style_attributes["friendliness"] == 0.9
    
    def test_personality_manager_get_personality(self):
        """Test getting personalities from manager."""
        manager = PersonalityManager()
        
        # Test getting default personality
        personality = manager.get_personality("friendly_guide")
        assert personality is not None
        assert personality.name == "Friendly Guide"
        
        # Test getting seasonal personality
        winter_personality = manager.get_personality("santa_claus")
        assert winter_personality is not None
        assert "ho ho ho" in winter_personality.style_attributes.get("catchphrase", "").lower()
    
    def test_personality_manager_list_available(self):
        """Test listing available personalities."""
        manager = PersonalityManager()
        
        # List all personalities
        all_personalities = manager.list_available_personalities()
        assert len(all_personalities) > 10  # Should have many personalities
        assert any(p["id"] == "friendly_guide" for p in all_personalities)
        
        # List by category
        regional_personalities = manager.list_available_personalities(category="regional")
        assert all(p.get("category") == "regional" for p in regional_personalities)
    
    def test_personality_selection_by_context(self):
        """Test automatic personality selection based on context."""
        manager = PersonalityManager()
        
        # Test location-based selection
        sf_context = {"location": {"city": "San Francisco"}}
        personality = manager.select_personality_by_context(sf_context)
        assert personality.id in ["san_francisco_local", "california_surfer", "friendly_guide"]
        
        # Test time-based selection (Christmas)
        christmas_context = {"date": datetime(2024, 12, 25)}
        personality = manager.select_personality_by_context(christmas_context)
        assert personality.id == "santa_claus"


class TestTextToSpeech:
    """Test text-to-speech functionality."""
    
    @pytest.mark.asyncio
    async def test_synthesize_speech_basic(self, voice_service, mock_tts_client):
        """Test basic speech synthesis."""
        text = "Hello, welcome to your road trip!"
        personality = VoicePersonality(
            id="test",
            name="Test Voice",
            voice_name="en-US-Neural2-A",
            pitch=0.0,
            speaking_rate=1.0
        )
        
        # Mock TTS response
        mock_audio_content = b"fake_audio_data"
        mock_tts_client.synthesize_speech.return_value = Mock(audio_content=mock_audio_content)
        
        result = await voice_service.synthesize_speech(text, personality)
        
        assert result["audio_content"] == base64.b64encode(mock_audio_content).decode()
        assert result["format"] == "mp3"
        assert result["personality_id"] == "test"
        mock_tts_client.synthesize_speech.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_synthesize_speech_with_ssml(self, voice_service, mock_tts_client):
        """Test speech synthesis with SSML markup."""
        text = "Welcome to <emphasis>San Francisco</emphasis>!"
        personality = VoicePersonality(
            id="guide",
            name="Guide",
            voice_name="en-US-Neural2-F",
            pitch=0.5,
            speaking_rate=0.9
        )
        
        mock_tts_client.synthesize_speech.return_value = Mock(audio_content=b"audio_with_emphasis")
        
        result = await voice_service.synthesize_speech(text, personality, use_ssml=True)
        
        # Verify SSML was processed
        call_args = mock_tts_client.synthesize_speech.call_args
        assert "<speak>" in str(call_args)
        assert "<emphasis>" in str(call_args)
        assert result["personality_id"] == "guide"
    
    @pytest.mark.asyncio
    async def test_synthesize_speech_with_caching(self, voice_service, mock_tts_client):
        """Test that speech synthesis results are cached."""
        text = "Cached message"
        personality = VoicePersonality(id="test", name="Test", voice_name="en-US-Neural2-A")
        
        mock_tts_client.synthesize_speech.return_value = Mock(audio_content=b"cached_audio")
        
        # First call - should hit TTS service
        result1 = await voice_service.synthesize_speech(text, personality)
        assert mock_tts_client.synthesize_speech.call_count == 1
        
        # Second call - should use cache
        result2 = await voice_service.synthesize_speech(text, personality)
        assert mock_tts_client.synthesize_speech.call_count == 1  # No additional call
        assert result1["audio_content"] == result2["audio_content"]
    
    @pytest.mark.asyncio
    async def test_synthesize_speech_error_handling(self, voice_service, mock_tts_client):
        """Test error handling in speech synthesis."""
        text = "Error test"
        personality = VoicePersonality(id="test", name="Test", voice_name="en-US-Neural2-A")
        
        # Mock TTS error
        mock_tts_client.synthesize_speech.side_effect = Exception("TTS service unavailable")
        
        result = await voice_service.synthesize_speech(text, personality)
        
        assert result["error"] == "TTS service unavailable"
        assert result["audio_content"] is None


class TestSpeechToText:
    """Test speech-to-text functionality."""
    
    @pytest.mark.asyncio
    async def test_recognize_speech_basic(self, voice_service, mock_stt_client):
        """Test basic speech recognition."""
        audio_content = b"fake_audio_data"
        
        # Mock STT response
        mock_result = Mock()
        mock_result.alternatives = [Mock(transcript="Hello, take me to San Francisco", confidence=0.95)]
        mock_stt_client.recognize.return_value = Mock(results=[mock_result])
        
        result = await voice_service.recognize_speech(audio_content)
        
        assert result["transcript"] == "Hello, take me to San Francisco"
        assert result["confidence"] == 0.95
        assert result["language"] == "en-US"
        mock_stt_client.recognize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_recognize_speech_with_alternatives(self, voice_service, mock_stt_client):
        """Test speech recognition with multiple alternatives."""
        audio_content = b"ambiguous_audio"
        
        # Mock multiple alternatives
        mock_alternatives = [
            Mock(transcript="Turn left here", confidence=0.8),
            Mock(transcript="Turn left hear", confidence=0.7),
            Mock(transcript="Turn left ear", confidence=0.5)
        ]
        mock_result = Mock(alternatives=mock_alternatives)
        mock_stt_client.recognize.return_value = Mock(results=[mock_result])
        
        result = await voice_service.recognize_speech(
            audio_content,
            return_alternatives=True
        )
        
        assert result["transcript"] == "Turn left here"
        assert len(result["alternatives"]) == 3
        assert result["alternatives"][0]["confidence"] == 0.8
    
    @pytest.mark.asyncio
    async def test_recognize_speech_no_results(self, voice_service, mock_stt_client):
        """Test handling when no speech is recognized."""
        audio_content = b"silence"
        
        # Mock empty results
        mock_stt_client.recognize.return_value = Mock(results=[])
        
        result = await voice_service.recognize_speech(audio_content)
        
        assert result["transcript"] == ""
        assert result["confidence"] == 0.0
        assert result["error"] == "No speech detected"
    
    @pytest.mark.asyncio
    async def test_recognize_speech_error_handling(self, voice_service, mock_stt_client):
        """Test error handling in speech recognition."""
        audio_content = b"error_audio"
        
        # Mock STT error
        mock_stt_client.recognize.side_effect = Exception("STT service error")
        
        result = await voice_service.recognize_speech(audio_content)
        
        assert result["error"] == "STT service error"
        assert result["transcript"] == ""


class TestVoiceSafety:
    """Test voice safety features for driving."""
    
    def test_safety_checker_initialization(self):
        """Test initializing voice safety checker."""
        checker = VoiceSafetyChecker()
        
        assert checker.max_interaction_length_driving == 30  # seconds
        assert checker.cooldown_period_driving == 5  # seconds
        assert checker.warning_threshold == 3
    
    @pytest.mark.asyncio
    async def test_check_interaction_safe(self):
        """Test checking safe voice interaction."""
        checker = VoiceSafetyChecker()
        context = VoiceInteractionContext(
            is_driving=True,
            speed_mph=30,  # Low speed
            traffic_condition="light",
            time_of_day="afternoon",
            weather_condition="clear"
        )
        
        result = await checker.check_interaction_safety("Play some music", context)
        
        assert result["safe"] is True
        assert result["reason"] is None
        assert len(result["warnings"]) == 0
    
    @pytest.mark.asyncio
    async def test_check_interaction_unsafe_high_speed(self):
        """Test unsafe interaction due to high speed."""
        checker = VoiceSafetyChecker()
        context = VoiceInteractionContext(
            is_driving=True,
            speed_mph=85,  # Very high speed
            traffic_condition="heavy",
            time_of_day="night",
            weather_condition="rain"
        )
        
        result = await checker.check_interaction_safety(
            "Show me the detailed restaurant menu",
            context
        )
        
        assert result["safe"] is False
        assert result["violation_type"] == SafetyViolationType.HIGH_SPEED_COMPLEXITY
        assert "high speed" in result["reason"].lower()
    
    @pytest.mark.asyncio
    async def test_check_interaction_warning_long_interaction(self):
        """Test warning for long interaction while driving."""
        checker = VoiceSafetyChecker()
        context = VoiceInteractionContext(
            is_driving=True,
            speed_mph=65,
            traffic_condition="moderate",
            conversation_duration_minutes=2  # Getting long
        )
        
        result = await checker.check_interaction_safety(
            "Tell me more about that story",
            context
        )
        
        assert result["safe"] is True  # Still safe but with warning
        assert len(result["warnings"]) > 0
        assert any("long conversation" in w.lower() for w in result["warnings"])
    
    @pytest.mark.asyncio
    async def test_cooldown_enforcement(self):
        """Test cooldown period enforcement."""
        checker = VoiceSafetyChecker()
        context = VoiceInteractionContext(is_driving=True, speed_mph=70)
        
        # First interaction
        result1 = await checker.check_interaction_safety("First command", context)
        assert result1["safe"] is True
        
        # Immediate second interaction - should require cooldown
        result2 = await checker.check_interaction_safety("Second command", context)
        assert result2["safe"] is False
        assert result2["violation_type"] == SafetyViolationType.COOLDOWN_REQUIRED
        assert result2["cooldown_seconds"] > 0
    
    def test_calculate_safe_response_length(self):
        """Test calculating safe response length based on context."""
        checker = VoiceSafetyChecker()
        
        # Stationary - can have long response
        stationary_context = VoiceInteractionContext(is_driving=False)
        length = checker.calculate_safe_response_length(stationary_context)
        assert length > 100  # Can have long responses
        
        # Highway driving - short response
        highway_context = VoiceInteractionContext(
            is_driving=True,
            speed_mph=75,
            traffic_condition="moderate"
        )
        length = checker.calculate_safe_response_length(highway_context)
        assert length < 50  # Must be brief
        
        # Complex conditions - very short
        complex_context = VoiceInteractionContext(
            is_driving=True,
            speed_mph=65,
            traffic_condition="heavy",
            weather_condition="storm"
        )
        length = checker.calculate_safe_response_length(complex_context)
        assert length < 30  # Very brief


class TestVoiceMetrics:
    """Test voice interaction metrics tracking."""
    
    def test_metrics_initialization(self):
        """Test initializing voice metrics."""
        metrics = VoiceMetrics()
        
        assert metrics.total_interactions == 0
        assert metrics.total_duration_seconds == 0
        assert metrics.safety_violations == 0
        assert metrics.successful_recognitions == 0
    
    def test_record_interaction(self):
        """Test recording voice interactions."""
        metrics = VoiceMetrics()
        
        # Record successful interaction
        metrics.record_interaction(
            duration_seconds=15,
            successful=True,
            personality_id="friendly_guide",
            safety_violation=False
        )
        
        assert metrics.total_interactions == 1
        assert metrics.total_duration_seconds == 15
        assert metrics.successful_recognitions == 1
        assert metrics.safety_violations == 0
        assert metrics.personality_usage["friendly_guide"] == 1
    
    def test_record_safety_violation(self):
        """Test recording safety violations."""
        metrics = VoiceMetrics()
        
        # Record interaction with safety violation
        metrics.record_interaction(
            duration_seconds=5,
            successful=False,
            safety_violation=True,
            violation_type=SafetyViolationType.HIGH_SPEED_COMPLEXITY
        )
        
        assert metrics.safety_violations == 1
        assert metrics.violation_types[SafetyViolationType.HIGH_SPEED_COMPLEXITY] == 1
    
    def test_calculate_metrics_summary(self):
        """Test calculating metrics summary."""
        metrics = VoiceMetrics()
        
        # Record several interactions
        for i in range(10):
            metrics.record_interaction(
                duration_seconds=10 + i,
                successful=i < 8,  # 80% success rate
                personality_id="guide" if i < 5 else "casual",
                safety_violation=i >= 9  # 10% violations
            )
        
        summary = metrics.get_summary()
        
        assert summary["total_interactions"] == 10
        assert summary["success_rate"] == 0.8
        assert summary["average_duration"] == 14.5  # (10+11+...+19)/10
        assert summary["safety_violation_rate"] == 0.1
        assert summary["most_used_personality"] == "guide"


class TestVoiceServiceIntegration:
    """Test full voice service integration."""
    
    @pytest.mark.asyncio
    async def test_process_voice_command(self, voice_service, mock_stt_client, mock_user):
        """Test processing a complete voice command."""
        audio_data = b"command_audio"
        context = VoiceInteractionContext(
            is_driving=True,
            speed_mph=55,
            traffic_condition="light"
        )
        
        # Mock STT result
        mock_stt_client.recognize.return_value = Mock(
            results=[Mock(alternatives=[
                Mock(transcript="Navigate to the nearest gas station", confidence=0.92)
            ])]
        )
        
        with patch.object(voice_service, 'safety_checker') as mock_safety:
            mock_safety.check_interaction_safety = AsyncMock(return_value={
                "safe": True,
                "warnings": []
            })
            
            result = await voice_service.process_voice_command(
                audio_data,
                mock_user,
                context
            )
        
        assert result["success"] is True
        assert result["transcript"] == "Navigate to the nearest gas station"
        assert result["safe"] is True
        assert "command_type" in result  # Should analyze command type
    
    @pytest.mark.asyncio
    async def test_generate_voice_response(self, voice_service, mock_tts_client, mock_user):
        """Test generating a complete voice response."""
        text = "Your next turn is in 2 miles"
        context = VoiceInteractionContext(
            is_driving=True,
            speed_mph=60,
            traffic_condition="moderate"
        )
        
        # Mock TTS result
        mock_tts_client.synthesize_speech.return_value = Mock(
            audio_content=b"response_audio"
        )
        
        with patch.object(voice_service, 'personality_manager') as mock_pm:
            mock_pm.get_personality.return_value = VoicePersonality(
                id="guide",
                name="Guide",
                voice_name="en-US-Neural2-F"
            )
            
            result = await voice_service.generate_voice_response(
                text,
                mock_user,
                context,
                check_safety=True
            )
        
        assert result["success"] is True
        assert result["audio_content"] is not None
        assert result["personality_used"] == "guide"
        assert result["duration_estimate"] > 0
    
    @pytest.mark.asyncio
    async def test_voice_conversation_flow(self, voice_service, mock_user):
        """Test a complete voice conversation flow."""
        # Start conversation
        session = await voice_service.start_voice_session(mock_user)
        assert session["session_id"] is not None
        assert session["status"] == "active"
        
        # Process multiple interactions
        for i in range(3):
            context = VoiceInteractionContext(
                is_driving=True,
                speed_mph=60,
                conversation_duration_minutes=i
            )
            
            # Simulate processing (would normally include STT/TTS)
            await voice_service.update_session_context(
                session["session_id"],
                context
            )
        
        # End conversation
        summary = await voice_service.end_voice_session(session["session_id"])
        assert summary["total_interactions"] >= 0
        assert summary["total_duration"] >= 0
        assert "safety_summary" in summary