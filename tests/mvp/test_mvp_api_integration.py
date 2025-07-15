"""
MVP API Integration Tests
Tests the REST API endpoints for MVP functionality
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import json
import base64

from backend.app.main import app
from backend.app.models.user import User
from backend.app.core.auth import create_access_token


@pytest.mark.mvp
class TestMVPAPIEndpoints:
    """Test core API endpoints for MVP"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Create authenticated headers"""
        token = create_access_token(data={"sub": "test-user-123"})
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.mark.asyncio
    async def test_voice_input_endpoint(self, client, auth_headers):
        """Test: POST /api/v1/voice/process"""
        # Mock audio data
        audio_data = base64.b64encode(b'RIFF' + b'\x00' * 100).decode()
        
        with patch('backend.app.services.voice_services.VoiceService.process_voice_command') as mock_voice:
            mock_voice.return_value = {
                "status": "success",
                "text": "Navigate to Golden Gate Bridge",
                "confidence": 0.95
            }
            
            response = client.post(
                "/api/v1/voice/process",
                json={"audio_data": audio_data},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["text"] == "Navigate to Golden Gate Bridge"
    
    @pytest.mark.asyncio
    async def test_story_generation_endpoint(self, client, auth_headers):
        """Test: POST /api/v1/stories/generate"""
        request_data = {
            "prompt": "Tell me about this area",
            "context": {
                "location": {
                    "lat": 37.7749,
                    "lng": -122.4194,
                    "name": "San Francisco"
                },
                "theme": "history"
            }
        }
        
        with patch('backend.app.services.storytelling_services.StorytellingService.generate_contextual_story') as mock_story:
            mock_story.return_value = {
                "story": "San Francisco, originally called Yerba Buena...",
                "duration": 45,
                "voice_url": "https://storage.googleapis.com/roadtrip/stories/sf-history.mp3"
            }
            
            response = client.post(
                "/api/v1/stories/generate",
                json=request_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "story" in data
            assert len(data["story"]) > 20
            assert "voice_url" in data
    
    @pytest.mark.asyncio
    async def test_navigation_endpoint(self, client, auth_headers):
        """Test: POST /api/v1/navigation/route"""
        request_data = {
            "origin": "San Francisco, CA",
            "destination": "Los Angeles, CA",
            "preferences": {
                "avoid": ["tolls"],
                "optimize": "time"
            }
        }
        
        with patch('backend.app.services.navigation_agent.NavigationAgent.plan_route') as mock_nav:
            mock_nav.return_value = {
                "distance_miles": 382,
                "duration_hours": 6.25,
                "route_id": "route-123",
                "steps": [
                    {"instruction": "Head south on US-101"},
                    {"instruction": "Merge onto I-5 South"}
                ]
            }
            
            response = client.post(
                "/api/v1/navigation/route",
                json=request_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["distance_miles"] == 382
            assert len(data["steps"]) >= 2
    
    @pytest.mark.asyncio
    async def test_booking_search_endpoint(self, client, auth_headers):
        """Test: GET /api/v1/bookings/restaurants/search"""
        params = {
            "lat": 37.7749,
            "lng": -122.4194,
            "cuisine": "italian",
            "price_range": 2,
            "party_size": 2
        }
        
        with patch('backend.app.services.booking_agent.BookingAgent.search_restaurants') as mock_search:
            mock_search.return_value = [
                {
                    "id": "rest1",
                    "name": "Luigi's Italian",
                    "cuisine": "Italian",
                    "rating": 4.5,
                    "price_range": 2,
                    "available_times": ["6:00 PM", "7:00 PM"]
                }
            ]
            
            response = client.get(
                "/api/v1/bookings/restaurants/search",
                params=params,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) >= 1
            assert data[0]["name"] == "Luigi's Italian"


@pytest.mark.mvp
class TestMVPWebSocket:
    """Test WebSocket connections for real-time features"""
    
    @pytest.mark.asyncio
    async def test_voice_stream_websocket(self):
        """Test: WebSocket for streaming voice"""
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        with client.websocket_connect("/ws/voice-stream") as websocket:
            # Send audio chunk
            audio_chunk = base64.b64encode(b'audio_data').decode()
            websocket.send_json({
                "type": "audio_chunk",
                "data": audio_chunk
            })
            
            # Should receive acknowledgment
            response = websocket.receive_json()
            assert response["type"] == "ack"
            assert response["status"] == "received"
    
    @pytest.mark.asyncio
    async def test_navigation_updates_websocket(self):
        """Test: WebSocket for navigation updates"""
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        with client.websocket_connect("/ws/navigation") as websocket:
            # Send location update
            websocket.send_json({
                "type": "location_update",
                "data": {
                    "lat": 37.7749,
                    "lng": -122.4194,
                    "speed_mph": 45,
                    "heading": 180
                }
            })
            
            # Should receive navigation update
            response = websocket.receive_json()
            assert response["type"] in ["navigation_instruction", "route_update"]


@pytest.mark.mvp
class TestMVPAuthentication:
    """Test authentication and authorization"""
    
    def test_unauthenticated_request(self, client):
        """Test: Unauthenticated requests are rejected"""
        response = client.get("/api/v1/stories/generate")
        assert response.status_code == 401
        assert "detail" in response.json()
    
    def test_token_generation(self, client):
        """Test: Generate access token on login"""
        login_data = {
            "username": "testuser@example.com",
            "password": "testpass123"
        }
        
        with patch('backend.app.core.auth.authenticate_user') as mock_auth:
            mock_auth.return_value = Mock(
                id="user-123",
                email="testuser@example.com"
            )
            
            response = client.post(
                "/api/v1/auth/login",
                data=login_data
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
    
    def test_token_refresh(self, client):
        """Test: Refresh access token"""
        # Create refresh token
        refresh_token = create_access_token(
            data={"sub": "user-123", "type": "refresh"},
            expires_delta=timedelta(days=7)
        )
        
        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {refresh_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data


@pytest.mark.mvp
class TestMVPRateLimiting:
    """Test rate limiting for API endpoints"""
    
    def test_rate_limit_voice_api(self, client, auth_headers):
        """Test: Rate limit on voice processing"""
        # Make multiple rapid requests
        for i in range(15):  # Assuming limit is 10/minute
            response = client.post(
                "/api/v1/voice/process",
                json={"audio_data": "test"},
                headers=auth_headers
            )
            
            if i < 10:
                assert response.status_code in [200, 422]
            else:
                # Should hit rate limit
                assert response.status_code == 429
                assert "rate limit" in response.json()["detail"].lower()
    
    def test_rate_limit_ai_endpoints(self, client, auth_headers):
        """Test: Rate limit on AI-heavy endpoints"""
        # Story generation should have stricter limits
        for i in range(7):  # Assuming limit is 5/minute
            response = client.post(
                "/api/v1/stories/generate",
                json={"prompt": "test", "context": {}},
                headers=auth_headers
            )
            
            if i < 5:
                assert response.status_code in [200, 422]
            else:
                assert response.status_code == 429


@pytest.mark.mvp
class TestMVPHealthMonitoring:
    """Test health check and monitoring endpoints"""
    
    def test_health_check(self, client):
        """Test: GET /health"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_readiness_check(self, client):
        """Test: GET /ready"""
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True
        assert "services" in data
        assert data["services"]["database"] == "connected"
        assert data["services"]["redis"] == "connected"
    
    def test_metrics_endpoint(self, client):
        """Test: GET /metrics (Prometheus format)"""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain"
        
        # Check for standard metrics
        metrics_text = response.text
        assert "http_requests_total" in metrics_text
        assert "http_request_duration_seconds" in metrics_text
        assert "python_info" in metrics_text


@pytest.mark.mvp 
class TestMVPErrorHandling:
    """Test API error handling"""
    
    def test_validation_error(self, client, auth_headers):
        """Test: Invalid request data returns 422"""
        # Missing required fields
        response = client.post(
            "/api/v1/stories/generate",
            json={"invalid": "data"},
            headers=auth_headers
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert any("field required" in str(err).lower() for err in data["detail"])
    
    def test_internal_error_handling(self, client, auth_headers):
        """Test: Internal errors return 500 with safe message"""
        with patch('backend.app.services.storytelling_services.StorytellingService.generate_contextual_story') as mock:
            mock.side_effect = Exception("Database connection failed")
            
            response = client.post(
                "/api/v1/stories/generate",
                json={"prompt": "test", "context": {}},
                headers=auth_headers
            )
            
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            # Should not expose internal error details
            assert "database" not in data["detail"].lower()
            assert "internal server error" in data["detail"].lower()
    
    def test_timeout_handling(self, client, auth_headers):
        """Test: Long requests timeout appropriately"""
        import asyncio
        
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(35)
            return {"story": "This took too long"}
        
        with patch('backend.app.services.storytelling_services.StorytellingService.generate_contextual_story', slow_response):
            response = client.post(
                "/api/v1/stories/generate",
                json={"prompt": "test", "context": {}},
                headers=auth_headers,
                timeout=30
            )
            
            # Should timeout
            assert response.status_code in [504, 500]  # Gateway timeout or server error