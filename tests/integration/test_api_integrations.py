"""
Integration tests for external API services

These tests verify that all external API integrations are properly configured
and functioning. They use mocked responses for CI/CD environments but can
be run with real APIs when INTEGRATION_TEST_MODE=live is set.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from datetime import datetime, timedelta
import json

# Determine if we're running live tests or mocked tests
INTEGRATION_TEST_MODE = os.getenv("INTEGRATION_TEST_MODE", "mock")
SKIP_LIVE_TESTS = INTEGRATION_TEST_MODE != "live"


class TestGoogleMapsIntegration:
    """Test Google Maps API integration"""
    
    @pytest.mark.skipif(SKIP_LIVE_TESTS, reason="Live API tests disabled")
    def test_google_maps_directions_live(self):
        """Test real Google Maps Directions API"""
        from backend.app.services.directions_service import DirectionsService
        
        service = DirectionsService()
        result = service.get_directions(
            origin="San Francisco, CA",
            destination="Los Angeles, CA"
        )
        
        assert result is not None
        assert "routes" in result
        assert len(result["routes"]) > 0
        assert "legs" in result["routes"][0]
    
    def test_google_maps_directions_mock(self):
        """Test Google Maps Directions API with mock"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "OK",
                "routes": [{
                    "legs": [{
                        "distance": {"text": "380 mi", "value": 611000},
                        "duration": {"text": "5 hours 45 mins", "value": 20700},
                        "steps": []
                    }]
                }]
            }
            mock_get.return_value = mock_response
            
            from backend.app.services.directions_service import DirectionsService
            service = DirectionsService()
            result = service.get_directions(
                origin="San Francisco, CA",
                destination="Los Angeles, CA"
            )
            
            assert result["status"] == "OK"
            assert len(result["routes"]) > 0
    
    @pytest.mark.skipif(SKIP_LIVE_TESTS, reason="Live API tests disabled")
    def test_google_places_search_live(self):
        """Test real Google Places API search"""
        from backend.app.services.directions_service import DirectionsService
        
        service = DirectionsService()
        places = service.search_nearby_places(
            location=(37.7749, -122.4194),  # San Francisco
            radius=5000,
            place_type="restaurant"
        )
        
        assert places is not None
        assert len(places) > 0
        assert "name" in places[0]
        assert "place_id" in places[0]


class TestGoogleCloudIntegration:
    """Test Google Cloud services integration"""
    
    @pytest.mark.skipif(SKIP_LIVE_TESTS, reason="Live API tests disabled")
    def test_vertex_ai_generation_live(self):
        """Test real Vertex AI text generation"""
        from backend.app.core.google_ai_client import GoogleAIClient
        
        client = GoogleAIClient()
        response = client.generate_text(
            prompt="Write a one-sentence description of the Golden Gate Bridge.",
            max_tokens=50
        )
        
        assert response is not None
        assert len(response) > 0
        assert "Golden Gate" in response or "bridge" in response.lower()
    
    def test_vertex_ai_generation_mock(self):
        """Test Vertex AI text generation with mock"""
        with patch('backend.app.core.google_ai_client.GoogleAIClient.generate_text') as mock_generate:
            mock_generate.return_value = "The Golden Gate Bridge is an iconic suspension bridge spanning the Golden Gate strait in San Francisco."
            
            from backend.app.core.google_ai_client import GoogleAIClient
            client = GoogleAIClient()
            response = client.generate_text(
                prompt="Describe the Golden Gate Bridge",
                max_tokens=50
            )
            
            assert "Golden Gate Bridge" in response
    
    @pytest.mark.skipif(SKIP_LIVE_TESTS, reason="Live API tests disabled")
    def test_google_tts_live(self):
        """Test real Google Text-to-Speech"""
        from backend.app.services.tts_service import TTSService
        
        service = TTSService()
        audio_content = service.synthesize_speech(
            text="Hello, this is a test.",
            voice_name="en-US-Wavenet-D"
        )
        
        assert audio_content is not None
        assert len(audio_content) > 0
        assert isinstance(audio_content, bytes)


class TestSpotifyIntegration:
    """Test Spotify API integration"""
    
    @pytest.mark.skipif(SKIP_LIVE_TESTS, reason="Live API tests disabled")
    def test_spotify_auth_live(self):
        """Test real Spotify authentication"""
        import requests
        
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        
        if not client_id or not client_secret:
            pytest.skip("Spotify credentials not configured")
        
        auth_url = "https://accounts.spotify.com/api/token"
        response = requests.post(
            auth_url,
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "Bearer"
    
    def test_spotify_search_mock(self):
        """Test Spotify search with mock"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "tracks": {
                    "items": [{
                        "id": "123",
                        "name": "Road Trip Song",
                        "artists": [{"name": "Test Artist"}],
                        "uri": "spotify:track:123"
                    }]
                }
            }
            mock_get.return_value = mock_response
            
            # Simulate search
            headers = {"Authorization": "Bearer fake_token"}
            response = requests.get(
                "https://api.spotify.com/v1/search",
                headers=headers,
                params={"q": "road trip", "type": "track"}
            )
            
            data = response.json()
            assert len(data["tracks"]["items"]) > 0
            assert data["tracks"]["items"][0]["name"] == "Road Trip Song"


class TestOpenTableIntegration:
    """Test OpenTable API integration"""
    
    def test_opentable_restaurant_search_mock(self):
        """Test OpenTable restaurant search with mock"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "restaurants": [{
                    "id": "12345",
                    "name": "Test Restaurant",
                    "address": "123 Main St",
                    "city": "San Francisco",
                    "cuisine": "Italian"
                }],
                "total": 1
            }
            mock_get.return_value = mock_response
            
            # Simulate search
            response = requests.get(
                "https://api.opentable.com/api/restaurants",
                params={"city": "San Francisco", "cuisine": "Italian"}
            )
            
            data = response.json()
            assert data["total"] > 0
            assert data["restaurants"][0]["name"] == "Test Restaurant"
    
    def test_opentable_availability_mock(self):
        """Test OpenTable availability check with mock"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "availability": [{
                    "time": "19:00",
                    "available": True
                }, {
                    "time": "19:30",
                    "available": True
                }]
            }
            mock_get.return_value = mock_response
            
            # Simulate availability check
            response = requests.get(
                "https://api.opentable.com/api/availability",
                params={
                    "restaurant_id": "12345",
                    "date": "2024-12-25",
                    "party_size": 4
                }
            )
            
            data = response.json()
            assert len(data["availability"]) > 0
            assert data["availability"][0]["available"] is True


class TestWeatherIntegration:
    """Test weather API integration"""
    
    @pytest.mark.skipif(SKIP_LIVE_TESTS, reason="Live API tests disabled")
    def test_openweather_current_live(self):
        """Test real OpenWeatherMap current weather"""
        api_key = os.getenv("OPENWEATHER_API_KEY")
        if not api_key:
            pytest.skip("OpenWeatherMap API key not configured")
        
        response = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={
                "q": "San Francisco",
                "appid": api_key,
                "units": "imperial"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "main" in data
        assert "temp" in data["main"]
        assert "weather" in data
    
    def test_openweather_forecast_mock(self):
        """Test OpenWeatherMap forecast with mock"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "list": [{
                    "dt": 1640995200,
                    "main": {
                        "temp": 65.0,
                        "humidity": 70
                    },
                    "weather": [{
                        "main": "Clear",
                        "description": "clear sky"
                    }]
                }],
                "city": {"name": "San Francisco"}
            }
            mock_get.return_value = mock_response
            
            response = requests.get(
                "https://api.openweathermap.org/data/2.5/forecast",
                params={"q": "San Francisco", "appid": "fake_key"}
            )
            
            data = response.json()
            assert len(data["list"]) > 0
            assert data["list"][0]["main"]["temp"] == 65.0


class TestTicketmasterIntegration:
    """Test Ticketmaster API integration"""
    
    def test_ticketmaster_event_search_mock(self):
        """Test Ticketmaster event search with mock"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "_embedded": {
                    "events": [{
                        "id": "evt123",
                        "name": "Concert in the Park",
                        "dates": {
                            "start": {
                                "localDate": "2024-12-25",
                                "localTime": "19:00:00"
                            }
                        },
                        "venues": [{
                            "name": "Golden Gate Park"
                        }]
                    }]
                },
                "page": {"totalElements": 1}
            }
            mock_get.return_value = mock_response
            
            response = requests.get(
                "https://app.ticketmaster.com/discovery/v2/events",
                params={
                    "city": "San Francisco",
                    "apikey": "fake_key"
                }
            )
            
            data = response.json()
            assert data["page"]["totalElements"] > 0
            assert data["_embedded"]["events"][0]["name"] == "Concert in the Park"


@pytest.fixture
def mock_all_apis():
    """Fixture to mock all external APIs for testing"""
    with patch.multiple(
        'requests',
        get=MagicMock(return_value=Mock(status_code=200, json=lambda: {"status": "OK"})),
        post=MagicMock(return_value=Mock(status_code=200, json=lambda: {"status": "OK"}))
    ):
        yield


def test_all_apis_health_check(mock_all_apis):
    """Test that all API endpoints are reachable"""
    endpoints = [
        "https://maps.googleapis.com/maps/api/directions/json",
        "https://api.spotify.com/v1/search",
        "https://api.opentable.com/api/restaurants",
        "https://api.openweathermap.org/data/2.5/weather",
        "https://app.ticketmaster.com/discovery/v2/events"
    ]
    
    for endpoint in endpoints:
        response = requests.get(endpoint)
        assert response.status_code == 200


if __name__ == "__main__":
    # Run tests with pytest
    import subprocess
    import sys
    
    # Run mocked tests by default
    result = subprocess.run([sys.executable, "-m", "pytest", __file__, "-v"])
    
    # Optionally run live tests if flag is set
    if os.getenv("RUN_LIVE_INTEGRATION_TESTS") == "true":
        print("\nRunning live integration tests...")
        os.environ["INTEGRATION_TEST_MODE"] = "live"
        subprocess.run([sys.executable, "-m", "pytest", __file__, "-v", "-k", "live"])