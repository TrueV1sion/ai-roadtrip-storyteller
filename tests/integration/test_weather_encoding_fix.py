"""
Test OpenWeatherMap API encoding fixes
Verifies UTF-8 handling and special character processing
"""

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import aiohttp

from backend.app.integrations.weather_client import WeatherClient


class TestWeatherEncoding:
    """Test weather client encoding fixes."""
    
    @pytest.fixture
    def client(self):
        """Create a weather client instance."""
        with patch.dict('os.environ', {'OPENWEATHERMAP_API_KEY': 'test_key'}):
            return WeatherClient()
    
    @pytest.mark.asyncio
    async def test_utf8_encoding_in_response(self, client):
        """Test that UTF-8 encoded responses are handled correctly."""
        # Mock response with UTF-8 characters
        mock_response_data = {
            "coord": {"lon": 2.3522, "lat": 48.8566},
            "weather": [{
                "id": 800,
                "main": "Clear",
                "description": "ciel dégagé",  # French with accent
                "icon": "01d"
            }],
            "main": {
                "temp": 22.5,
                "feels_like": 21.8,
                "humidity": 65
            },
            "name": "Île-de-France",  # French with special characters
            "sys": {"country": "FR"},
            "dt": 1234567890
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            # Setup mock response
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.text = AsyncMock(return_value=json.dumps(mock_response_data))
            
            # Setup session
            mock_session_instance = AsyncMock()
            mock_session_instance.get = AsyncMock(return_value=mock_resp)
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock()
            mock_session.return_value = mock_session_instance
            
            # Get weather
            result = await client.get_current_weather(48.8566, 2.3522, lang="fr")
            
            # Verify encoding was handled correctly
            assert result["location"]["name"] == "Île-de-France"
            assert result["current"]["description"] == "ciel dégagé"
    
    @pytest.mark.asyncio
    async def test_special_character_sanitization(self, client):
        """Test that special characters are properly sanitized."""
        # Mock response with problematic characters
        mock_response_data = {
            "weather": [{
                "main": "Rain",
                "description": "It's raining — heavily",  # Em dash and curly apostrophe
                "icon": "09d"
            }],
            "main": {"temp": 15.0},
            "name": "Test City",
            "dt": 1234567890
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            # Setup mock response
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.text = AsyncMock(return_value=json.dumps(mock_response_data))
            
            # Setup session
            mock_session_instance = AsyncMock()
            mock_session_instance.get = AsyncMock(return_value=mock_resp)
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock()
            mock_session.return_value = mock_session_instance
            
            # Get weather
            result = await client.get_current_weather(0, 0)
            
            # Verify special characters were sanitized
            assert result["current"]["description"] == "It's raining -- heavily"
    
    @pytest.mark.asyncio
    async def test_unicode_decode_error_handling(self, client):
        """Test handling of Unicode decode errors."""
        with patch('aiohttp.ClientSession') as mock_session:
            # Setup mock response that will cause decode error
            mock_resp = AsyncMock()
            mock_resp.status = 200
            # Simulate a decode error
            mock_resp.text = AsyncMock(side_effect=UnicodeDecodeError(
                'utf-8', b'\xff\xfe', 0, 1, 'invalid start byte'
            ))
            
            # Setup session
            mock_session_instance = AsyncMock()
            mock_session_instance.get = AsyncMock(return_value=mock_resp)
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock()
            mock_session.return_value = mock_session_instance
            
            # Get weather - should return fallback data
            result = await client.get_current_weather(0, 0)
            
            # Verify fallback data was returned
            assert result["current"]["description"] == "Weather data unavailable"
            assert result["location"]["name"] == "Unknown"
    
    @pytest.mark.asyncio
    async def test_json_decode_error_handling(self, client):
        """Test handling of JSON decode errors."""
        with patch('aiohttp.ClientSession') as mock_session:
            # Setup mock response with invalid JSON
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.text = AsyncMock(return_value="Invalid JSON {")
            
            # Setup session
            mock_session_instance = AsyncMock()
            mock_session_instance.get = AsyncMock(return_value=mock_resp)
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock()
            mock_session.return_value = mock_session_instance
            
            # Get weather - should return fallback data
            result = await client.get_current_weather(0, 0)
            
            # Verify fallback data was returned
            assert result["current"]["description"] == "Weather data unavailable"
    
    @pytest.mark.asyncio
    async def test_city_name_encoding(self, client):
        """Test various city name encodings."""
        test_cases = [
            ("São Paulo", "São Paulo"),  # Portuguese
            ("Zürich", "Zürich"),        # German
            ("Москва", "Москва"),        # Russian
            ("北京", "北京"),            # Chinese
            ("København", "København"),   # Danish
        ]
        
        for original, expected in test_cases:
            mock_response_data = {
                "weather": [{"main": "Clear", "description": "clear", "icon": "01d"}],
                "main": {"temp": 20.0},
                "name": original,
                "dt": 1234567890
            }
            
            with patch('aiohttp.ClientSession') as mock_session:
                # Setup mock response
                mock_resp = AsyncMock()
                mock_resp.status = 200
                mock_resp.text = AsyncMock(return_value=json.dumps(mock_response_data))
                
                # Setup session
                mock_session_instance = AsyncMock()
                mock_session_instance.get = AsyncMock(return_value=mock_resp)
                mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
                mock_session_instance.__aexit__ = AsyncMock()
                mock_session.return_value = mock_session_instance
                
                # Get weather
                result = await client.get_current_weather(0, 0)
                
                # Verify city name encoding
                assert result["location"]["name"] == expected
    
    @pytest.mark.asyncio
    async def test_weather_summary_formatting(self, client):
        """Test weather summary generation with various conditions."""
        mock_response_data = {
            "weather": [{"main": "Rain", "description": "light rain", "icon": "09d"}],
            "main": {"temp": 18.5, "feels_like": 17.2},
            "rain": {"1h": 2.5},
            "name": "Test City",
            "dt": 1234567890
        }
        
        with patch.object(client, 'get_current_weather') as mock_get_weather:
            mock_get_weather.return_value = client._process_weather_data(mock_response_data)
            
            summary = await client.get_weather_summary(0, 0)
            
            assert "18.5°C" in summary
            assert "light rain" in summary
            assert "feels like 17.2°C" in summary
            assert "2.5mm rain" in summary
    
    @pytest.mark.asyncio
    async def test_forecast_encoding(self, client):
        """Test forecast data encoding."""
        mock_response_data = {
            "city": {
                "name": "München",  # German city name
                "country": "DE",
                "coord": {"lat": 48.1351, "lon": 11.5820}
            },
            "list": [{
                "dt": 1234567890,
                "main": {"temp": 15.0, "feels_like": 14.0, "humidity": 70},
                "weather": [{
                    "main": "Clouds",
                    "description": "überwiegend bewölkt",  # German description
                    "icon": "04d"
                }],
                "wind": {"speed": 3.5},
                "clouds": {"all": 75},
                "pop": 0.2
            }]
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            # Setup mock response
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.text = AsyncMock(return_value=json.dumps(mock_response_data))
            
            # Setup session
            mock_session_instance = AsyncMock()
            mock_session_instance.get = AsyncMock(return_value=mock_resp)
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock()
            mock_session.return_value = mock_session_instance
            
            # Get forecast
            result = await client.get_weather_forecast(48.1351, 11.5820, lang="de")
            
            # Verify encoding
            assert result["location"]["name"] == "München"
            assert result["forecast"][0]["description"] == "überwiegend bewölkt"
    
    def test_sanitize_text_method(self, client):
        """Test the text sanitization method directly."""
        test_cases = [
            ("It's sunny", "It's sunny"),  # Curly apostrophe
            (""Quoted text"", '"Quoted text"'),  # Curly quotes
            ("Em—dash", "Em--dash"),  # Em dash
            ("En–dash", "En-dash"),  # En dash
            ("Ellipsis…", "Ellipsis..."),  # Horizontal ellipsis
            ("Non\u00a0breaking", "Non breaking"),  # Non-breaking space
            (b"Byte string", "Byte string"),  # Bytes input
        ]
        
        for input_text, expected in test_cases:
            result = client._sanitize_text(input_text)
            assert result == expected
    
    def test_mock_mode(self):
        """Test that mock mode works without API key."""
        # Create client without API key
        with patch.dict('os.environ', {'OPENWEATHERMAP_API_KEY': ''}):
            client = WeatherClient()
            assert client.mock_mode == True
            
            # Should return mock data
            mock_data = client._get_mock_weather_data({"lat": 0, "lon": 0})
            assert mock_data["weather"][0]["main"] == "Clear"
            assert mock_data["main"]["temp"] == 22.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])