"""End-to-end tests for voice interaction flows."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncio
from datetime import datetime, timedelta
import json
import websockets

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.stt_service import STTService
from backend.app.services.tts_service import TTSService
from backend.app.services.master_orchestration_agent import MasterOrchestrationAgent
from backend.app.core.auth import create_access_token


@pytest.fixture
def client():
    """Create test client with WebSocket support."""
    return TestClient(app)


@pytest.fixture
def auth_token():
    """Create authentication token."""
    return create_access_token(data={"sub": "test@example.com", "user_id": 1})


@pytest.fixture
def mock_audio_services():
    """Mock audio processing services."""
    with patch('backend.app.services.stt_service.STTService') as mock_stt, \
         patch('backend.app.services.tts_service.TTSService') as mock_tts:
        
        # Mock STT responses
        mock_stt.return_value.transcribe_audio = AsyncMock(side_effect=[
            "Navigate to San Francisco",
            "Find Italian restaurants along the way",
            "Book a table for 4 at 7pm",
            "Yes, confirm the booking",
            "Tell me about the Golden Gate Bridge"
        ])
        
        # Mock TTS responses
        mock_tts.return_value.synthesize_speech = AsyncMock(return_value=b"mock_audio_data")
        
        yield {"stt": mock_stt, "tts": mock_tts}


@pytest.fixture
def mock_location_updates():
    """Mock location updates for testing."""
    locations = [
        {"lat": 37.7749, "lng": -122.4194, "speed": 0},  # Start in SF
        {"lat": 37.7849, "lng": -122.4094, "speed": 30},  # Moving
        {"lat": 37.7949, "lng": -122.3994, "speed": 45},  # On highway
        {"lat": 37.8049, "lng": -122.3894, "speed": 40},  # Approaching destination
        {"lat": 37.8199, "lng": -122.4783, "speed": 0},  # At Golden Gate
    ]
    return locations


class TestVoiceInteractionsE2E:
    """End-to-end tests for voice interaction flows."""
    
    @pytest.mark.asyncio
    async def test_continuous_voice_conversation(self, client, auth_token, mock_audio_services):
        """Test continuous voice conversation flow."""
        with client.websocket_connect(
            f"/api/v1/voice/stream?token={auth_token}"
        ) as websocket:
            # Send initial audio stream
            audio_chunk = b"mock_audio_chunk_1"
            await websocket.send_bytes(audio_chunk)
            
            # Receive transcription
            response = await websocket.receive_json()
            assert response["type"] == "transcription"
            assert response["text"] == "Navigate to San Francisco"
            
            # Receive AI response
            response = await websocket.receive_json()
            assert response["type"] == "response"
            assert "San Francisco" in response["text"]
            
            # Receive audio response
            audio_response = await websocket.receive_bytes()
            assert len(audio_response) > 0
            
            # Continue conversation
            await websocket.send_bytes(b"mock_audio_chunk_2")
            response = await websocket.receive_json()
            assert response["type"] == "transcription"
            assert "Italian restaurants" in response["text"]
    
    @pytest.mark.asyncio
    async def test_voice_navigation_with_updates(self, client, auth_token, mock_audio_services, mock_location_updates):
        """Test voice-guided navigation with real-time updates."""
        with client.websocket_connect(
            f"/api/v1/realtime/connect?token={auth_token}"
        ) as websocket:
            # Start navigation via voice
            await websocket.send_json({
                "type": "voice_command",
                "audio": "base64_encoded_audio",
                "location": mock_location_updates[0]
            })
            
            # Receive navigation started confirmation
            response = await websocket.receive_json()
            assert response["type"] == "navigation_started"
            assert "route" in response
            
            # Simulate movement and location updates
            for i, location in enumerate(mock_location_updates[1:]):
                await asyncio.sleep(0.1)  # Simulate time passing
                
                await websocket.send_json({
                    "type": "location_update",
                    "location": location
                })
                
                # Receive navigation updates
                response = await websocket.receive_json()
                
                if response["type"] == "navigation_instruction":
                    assert "instruction" in response
                    assert "distance" in response
                elif response["type"] == "story_segment":
                    assert "content" in response
                    assert "audio" in response
                elif response["type"] == "point_of_interest":
                    assert "name" in response
                    assert "description" in response
            
            # Arrival notification
            response = await websocket.receive_json()
            assert response["type"] == "destination_reached"
    
    @pytest.mark.asyncio
    async def test_voice_booking_complete_flow(self, client, auth_token, mock_audio_services):
        """Test complete booking flow via voice commands."""
        with patch('backend.app.services.booking_service.BookingService') as mock_booking:
            mock_booking.return_value.search_restaurants = AsyncMock(return_value=[
                {"id": "r1", "name": "Bella Italia", "cuisine": "italian"},
                {"id": "r2", "name": "Roma Restaurant", "cuisine": "italian"}
            ])
            
            mock_booking.return_value.create_reservation = AsyncMock(return_value={
                "reservation_id": "RES123",
                "confirmation_code": "ABC123",
                "status": "confirmed"
            })
            
            with client.websocket_connect(
                f"/api/v1/voice/stream?token={auth_token}"
            ) as websocket:
                # User: "Find Italian restaurants along the way"
                await websocket.send_bytes(b"audio_find_restaurants")
                
                # System responds with options
                response = await websocket.receive_json()
                assert response["type"] == "options"
                assert len(response["restaurants"]) == 2
                
                # TTS audio for options
                audio = await websocket.receive_bytes()
                assert len(audio) > 0
                
                # User: "Book a table for 4 at 7pm"
                await websocket.send_bytes(b"audio_book_table")
                
                # System asks which restaurant
                response = await websocket.receive_json()
                assert response["type"] == "clarification"
                assert "which restaurant" in response["text"].lower()
                
                # User: "The first one" or "Bella Italia"
                await websocket.send_bytes(b"audio_select_first")
                
                # System confirms details
                response = await websocket.receive_json()
                assert response["type"] == "confirmation_request"
                assert "Bella Italia" in response["text"]
                assert "4 people" in response["text"]
                assert "7:00 PM" in response["text"]
                
                # User: "Yes, confirm the booking"
                await websocket.send_bytes(b"audio_confirm")
                
                # Booking confirmation
                response = await websocket.receive_json()
                assert response["type"] == "booking_confirmed"
                assert response["confirmation_code"] == "ABC123"
    
    @pytest.mark.asyncio
    async def test_voice_multi_agent_coordination(self, client, auth_token, mock_audio_services):
        """Test voice commands that require multiple agents."""
        with client.websocket_connect(
            f"/api/v1/voice/stream?token={auth_token}"
        ) as websocket:
            # Complex command requiring navigation + story + booking
            await websocket.send_json({
                "type": "voice_command",
                "text": "Take me to Napa Valley, tell me about the wineries, and book a wine tasting",
                "location": {"lat": 37.7749, "lng": -122.4194}
            })
            
            responses_received = {
                "navigation": False,
                "story": False,
                "booking_options": False
            }
            
            # Collect responses from different agents
            for _ in range(5):  # Expect multiple responses
                response = await websocket.receive_json()
                
                if response["type"] == "navigation_started":
                    responses_received["navigation"] = True
                    assert "Napa Valley" in response["destination"]
                    
                elif response["type"] == "story_segment":
                    responses_received["story"] = True
                    assert "winer" in response["content"].lower()
                    
                elif response["type"] == "booking_options":
                    responses_received["booking_options"] = True
                    assert len(response["wineries"]) > 0
            
            # All agents should have responded
            assert all(responses_received.values())
    
    @pytest.mark.asyncio
    async def test_voice_error_handling_and_recovery(self, client, auth_token, mock_audio_services):
        """Test voice interaction error handling and recovery."""
        with client.websocket_connect(
            f"/api/v1/voice/stream?token={auth_token}"
        ) as websocket:
            # Send invalid/unclear command
            mock_audio_services["stt"].return_value.transcribe_audio.return_value = "mumble mumble unclear"
            await websocket.send_bytes(b"unclear_audio")
            
            # System should ask for clarification
            response = await websocket.receive_json()
            assert response["type"] == "clarification_needed"
            assert "didn't understand" in response["text"].lower()
            
            # Send corrupted audio
            await websocket.send_bytes(b"corrupted")
            
            # System should handle gracefully
            response = await websocket.receive_json()
            assert response["type"] == "error"
            assert "audio" in response["text"].lower()
            
            # Recovery - send clear command
            mock_audio_services["stt"].return_value.transcribe_audio.return_value = "Navigate home"
            await websocket.send_bytes(b"clear_audio")
            
            # Should process normally
            response = await websocket.receive_json()
            assert response["type"] in ["response", "navigation_started"]
    
    @pytest.mark.asyncio
    async def test_voice_context_preservation(self, client, auth_token, mock_audio_services):
        """Test context preservation across voice interactions."""
        with client.websocket_connect(
            f"/api/v1/voice/stream?token={auth_token}"
        ) as websocket:
            # First command establishes context
            await websocket.send_json({
                "type": "voice_command",
                "text": "I'm traveling with my family including 2 kids"
            })
            
            response = await websocket.receive_json()
            assert response["type"] == "acknowledgment"
            
            # Subsequent command uses context
            await websocket.send_json({
                "type": "voice_command",
                "text": "Find attractions nearby"
            })
            
            response = await websocket.receive_json()
            assert response["type"] == "suggestions"
            # Should return family-friendly attractions
            assert all(a.get("family_friendly", False) for a in response["attractions"])
            
            # Another command using context
            await websocket.send_json({
                "type": "voice_command",
                "text": "Book tickets for all of us"
            })
            
            response = await websocket.receive_json()
            assert response["type"] == "ticket_options"
            # Should know party size from context
            assert response["suggested_tickets"]["adult"] == 2
            assert response["suggested_tickets"]["child"] == 2
    
    @pytest.mark.asyncio
    async def test_voice_interruption_handling(self, client, auth_token, mock_audio_services):
        """Test handling of voice interruptions."""
        with client.websocket_connect(
            f"/api/v1/voice/stream?token={auth_token}"
        ) as websocket:
            # Start a long story
            await websocket.send_json({
                "type": "voice_command",
                "text": "Tell me the complete history of San Francisco"
            })
            
            # Start receiving story
            response = await websocket.receive_json()
            assert response["type"] == "story_started"
            
            # Interrupt with new command
            await websocket.send_json({
                "type": "interrupt",
                "new_command": "Stop and navigate to the nearest gas station"
            })
            
            # Should acknowledge interruption
            response = await websocket.receive_json()
            assert response["type"] == "story_stopped"
            
            # Should process new command
            response = await websocket.receive_json()
            assert response["type"] == "navigation_started"
            assert "gas station" in response["destination"].lower()
    
    @pytest.mark.asyncio
    async def test_voice_language_switching(self, client, auth_token, mock_audio_services):
        """Test voice interaction in multiple languages."""
        with client.websocket_connect(
            f"/api/v1/voice/stream?token={auth_token}"
        ) as websocket:
            # Set language preference
            await websocket.send_json({
                "type": "set_language",
                "language": "es"  # Spanish
            })
            
            response = await websocket.receive_json()
            assert response["type"] == "language_changed"
            assert response["language"] == "es"
            
            # Send command (mocked as Spanish)
            mock_audio_services["stt"].return_value.transcribe_audio.return_value = "Navegar a San Francisco"
            await websocket.send_bytes(b"spanish_audio")
            
            # Response should be in Spanish
            response = await websocket.receive_json()
            assert response["type"] == "response"
            assert response["language"] == "es"
            
            # TTS should use Spanish voice
            mock_audio_services["tts"].return_value.synthesize_speech.assert_called_with(
                text=response["text"],
                language="es",
                voice_params={"language_code": "es-US"}
            )
    
    @pytest.mark.asyncio
    async def test_voice_offline_mode_transition(self, client, auth_token, mock_audio_services):
        """Test voice functionality during online/offline transitions."""
        with client.websocket_connect(
            f"/api/v1/voice/stream?token={auth_token}"
        ) as websocket:
            # Normal operation
            await websocket.send_json({
                "type": "voice_command",
                "text": "Navigate to downtown"
            })
            
            response = await websocket.receive_json()
            assert response["type"] == "navigation_started"
            
            # Simulate going offline
            await websocket.send_json({
                "type": "connection_status",
                "status": "offline"
            })
            
            # Try voice command while offline
            await websocket.send_json({
                "type": "voice_command",
                "text": "Tell me a story"
            })
            
            # Should use cached/offline content
            response = await websocket.receive_json()
            assert response["type"] == "offline_response"
            assert response["source"] == "cached"
            
            # Come back online
            await websocket.send_json({
                "type": "connection_status",
                "status": "online"
            })
            
            # Should resume normal operation
            await websocket.send_json({
                "type": "voice_command",
                "text": "Book a restaurant"
            })
            
            response = await websocket.receive_json()
            assert response["type"] in ["booking_options", "response"]
    
    @pytest.mark.asyncio
    async def test_voice_accessibility_features(self, client, auth_token, mock_audio_services):
        """Test voice accessibility features."""
        with client.websocket_connect(
            f"/api/v1/voice/stream?token={auth_token}"
        ) as websocket:
            # Enable accessibility mode
            await websocket.send_json({
                "type": "accessibility",
                "settings": {
                    "speech_rate": 0.8,  # Slower
                    "verbose_mode": True,
                    "repeat_enabled": True
                }
            })
            
            # Send command
            await websocket.send_json({
                "type": "voice_command",
                "text": "Navigate to the museum"
            })
            
            # Should receive verbose response
            response = await websocket.receive_json()
            assert response["type"] == "verbose_response"
            assert len(response["steps"]) > 0  # Detailed steps
            
            # Request repeat
            await websocket.send_json({
                "type": "voice_command",
                "text": "Repeat that please"
            })
            
            # Should repeat last response
            response = await websocket.receive_json()
            assert response["type"] == "repeated_response"
            assert response["text"] == response["original_text"]
            
            # Verify TTS uses accessibility settings
            mock_audio_services["tts"].return_value.synthesize_speech.assert_called_with(
                text=response["text"],
                speech_rate=0.8,
                voice_params={"speaking_rate": 0.8}
            )