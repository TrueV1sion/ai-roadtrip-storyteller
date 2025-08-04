"""
Comprehensive unit tests for the weather service.
Tests weather data fetching, forecasting, alerts, and narrative generation.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, List, Any
import json

from app.services.weather_service import (
    WeatherService,
    WeatherData,
    WeatherForecast,
    WeatherAlert,
    WeatherCondition,
    WeatherSeverity,
    WeatherNarrative,
    RoadCondition
)
from app.integrations.weather_client import WeatherClient


@pytest.fixture
def mock_weather_client():
    """Create a mock weather client."""
    client = Mock(spec=WeatherClient)
    client.get_current_weather = AsyncMock()
    client.get_forecast = AsyncMock()
    client.get_alerts = AsyncMock()
    client.get_historical_weather = AsyncMock()
    return client


@pytest.fixture
def sample_location():
    """Create a sample location for testing."""
    return {
        "lat": 37.7749,
        "lng": -122.4194,
        "city": "San Francisco",
        "state": "CA"
    }


@pytest.fixture
def sample_weather_data():
    """Create sample weather data."""
    return WeatherData(
        temperature=72.5,
        feels_like=70.0,
        humidity=65,
        pressure=1013.25,
        wind_speed=12.5,
        wind_direction=270,
        visibility=10.0,
        condition=WeatherCondition.PARTLY_CLOUDY,
        description="Partly cloudy skies",
        icon="02d",
        timestamp=datetime.now(),
        location={"lat": 37.7749, "lng": -122.4194}
    )


@pytest.fixture
async def weather_service(mock_weather_client):
    """Create a weather service with mocks."""
    with patch('backend.app.services.weather_service.WeatherClient', return_value=mock_weather_client):
        service = WeatherService()
        service.weather_client = mock_weather_client
        yield service


class TestWeatherDataFetching:
    """Test fetching weather data."""
    
    @pytest.mark.asyncio
    async def test_get_current_weather(self, weather_service, mock_weather_client, sample_location):
        """Test getting current weather conditions."""
        # Mock weather API response
        mock_weather_client.get_current_weather.return_value = {
            "main": {
                "temp": 72.5,
                "feels_like": 70.0,
                "humidity": 65,
                "pressure": 1013.25
            },
            "weather": [{
                "id": 801,
                "main": "Clouds",
                "description": "few clouds",
                "icon": "02d"
            }],
            "wind": {
                "speed": 12.5,
                "deg": 270
            },
            "visibility": 10000,
            "dt": 1234567890,
            "name": "San Francisco"
        }
        
        weather = await weather_service.get_current_weather(sample_location)
        
        assert isinstance(weather, WeatherData)
        assert weather.temperature == 72.5
        assert weather.condition == WeatherCondition.PARTLY_CLOUDY
        assert weather.wind_speed == 12.5
        assert weather.location["city"] == "San Francisco"
    
    @pytest.mark.asyncio
    async def test_get_forecast(self, weather_service, mock_weather_client, sample_location):
        """Test getting weather forecast."""
        # Mock forecast API response
        mock_weather_client.get_forecast.return_value = {
            "list": [
                {
                    "dt": int((datetime.now() + timedelta(hours=3)).timestamp()),
                    "main": {"temp": 75.0, "humidity": 60},
                    "weather": [{"id": 800, "main": "Clear", "description": "clear sky"}],
                    "wind": {"speed": 10.0},
                    "pop": 0.0
                },
                {
                    "dt": int((datetime.now() + timedelta(hours=6)).timestamp()),
                    "main": {"temp": 68.0, "humidity": 70},
                    "weather": [{"id": 500, "main": "Rain", "description": "light rain"}],
                    "wind": {"speed": 15.0},
                    "pop": 0.8
                }
            ]
        }
        
        forecast = await weather_service.get_forecast(sample_location, hours=12)
        
        assert isinstance(forecast, list)
        assert len(forecast) == 2
        assert all(isinstance(f, WeatherForecast) for f in forecast)
        assert forecast[0].temperature == 75.0
        assert forecast[1].condition == WeatherCondition.RAIN
        assert forecast[1].precipitation_probability == 0.8
    
    @pytest.mark.asyncio
    async def test_get_weather_along_route(self, weather_service, mock_weather_client):
        """Test getting weather along a route."""
        route_points = [
            {"lat": 37.7749, "lng": -122.4194, "time": datetime.now()},
            {"lat": 36.7783, "lng": -119.4179, "time": datetime.now() + timedelta(hours=2)},
            {"lat": 34.0522, "lng": -118.2437, "time": datetime.now() + timedelta(hours=5)}
        ]
        
        # Mock weather for each point
        mock_weather_client.get_current_weather.side_effect = [
            {"main": {"temp": 72}, "weather": [{"id": 800}]},
            {"main": {"temp": 85}, "weather": [{"id": 801}]},
            {"main": {"temp": 78}, "weather": [{"id": 803}]}
        ]
        
        weather_points = await weather_service.get_weather_along_route(route_points)
        
        assert len(weather_points) == 3
        assert weather_points[0]["weather"].temperature == 72
        assert weather_points[1]["weather"].temperature == 85
        assert weather_points[2]["weather"].temperature == 78


class TestWeatherAlerts:
    """Test weather alert functionality."""
    
    @pytest.mark.asyncio
    async def test_get_weather_alerts(self, weather_service, mock_weather_client, sample_location):
        """Test getting weather alerts."""
        # Mock weather alerts
        mock_weather_client.get_alerts.return_value = [
            {
                "sender_name": "NWS San Francisco",
                "event": "High Wind Warning",
                "start": int(datetime.now().timestamp()),
                "end": int((datetime.now() + timedelta(hours=12)).timestamp()),
                "description": "Strong winds expected. Gusts up to 60 mph.",
                "tags": ["wind"]
            },
            {
                "sender_name": "NWS San Francisco",
                "event": "Coastal Flood Advisory",
                "start": int((datetime.now() + timedelta(hours=6)).timestamp()),
                "end": int((datetime.now() + timedelta(hours=18)).timestamp()),
                "description": "Minor coastal flooding possible.",
                "tags": ["flood"]
            }
        ]
        
        alerts = await weather_service.get_weather_alerts(sample_location)
        
        assert len(alerts) == 2
        assert all(isinstance(a, WeatherAlert) for a in alerts)
        assert alerts[0].event == "High Wind Warning"
        assert alerts[0].severity == WeatherSeverity.WARNING
        assert alerts[1].event == "Coastal Flood Advisory"
        assert alerts[1].severity == WeatherSeverity.ADVISORY
    
    @pytest.mark.asyncio
    async def test_check_severe_weather(self, weather_service, mock_weather_client, sample_location):
        """Test checking for severe weather conditions."""
        # Mock severe weather conditions
        mock_weather_client.get_current_weather.return_value = {
            "main": {"temp": 72},
            "weather": [{"id": 211, "main": "Thunderstorm", "description": "thunderstorm"}],
            "wind": {"speed": 45}  # High wind speed
        }
        
        mock_weather_client.get_alerts.return_value = [{
            "event": "Severe Thunderstorm Warning",
            "severity": "warning"
        }]
        
        is_severe = await weather_service.check_severe_weather(sample_location)
        
        assert is_severe is True
    
    @pytest.mark.asyncio
    async def test_filter_relevant_alerts(self, weather_service):
        """Test filtering alerts relevant to driving."""
        alerts = [
            WeatherAlert(
                event="Winter Storm Warning",
                severity=WeatherSeverity.WARNING,
                description="Heavy snow expected",
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(hours=12)
            ),
            WeatherAlert(
                event="Air Quality Alert",
                severity=WeatherSeverity.ADVISORY,
                description="Unhealthy air quality",
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(hours=24)
            ),
            WeatherAlert(
                event="Tornado Warning",
                severity=WeatherSeverity.EXTREME,
                description="Tornado spotted",
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(hours=1)
            )
        ]
        
        relevant = weather_service.filter_driving_relevant_alerts(alerts)
        
        assert len(relevant) == 2  # Winter storm and tornado
        assert all(a.event in ["Winter Storm Warning", "Tornado Warning"] for a in relevant)


class TestWeatherNarratives:
    """Test weather narrative generation."""
    
    @pytest.mark.asyncio
    async def test_generate_weather_narrative(self, weather_service, sample_weather_data):
        """Test generating weather narrative for storytelling."""
        narrative = await weather_service.generate_weather_narrative(
            sample_weather_data,
            style="dramatic"
        )
        
        assert isinstance(narrative, WeatherNarrative)
        assert narrative.style == "dramatic"
        assert len(narrative.text) > 50  # Should have substantial content
        assert "partly cloudy" in narrative.text.lower()
        assert narrative.mood in ["peaceful", "mysterious", "contemplative"]
    
    @pytest.mark.asyncio
    async def test_generate_narrative_different_conditions(self, weather_service):
        """Test narrative generation for different weather conditions."""
        conditions = [
            (WeatherCondition.CLEAR, "sunny", ["bright", "clear", "blue"]),
            (WeatherCondition.RAIN, "rain", ["rain", "drops", "wet"]),
            (WeatherCondition.STORM, "storm", ["thunder", "lightning", "storm"]),
            (WeatherCondition.SNOW, "snow", ["snow", "white", "winter"]),
            (WeatherCondition.FOG, "fog", ["fog", "mist", "visibility"])
        ]
        
        for condition, desc, keywords in conditions:
            weather = WeatherData(
                temperature=60,
                condition=condition,
                description=desc,
                timestamp=datetime.now(),
                location={"lat": 0, "lng": 0}
            )
            
            narrative = await weather_service.generate_weather_narrative(weather)
            
            assert any(keyword in narrative.text.lower() for keyword in keywords)
            assert narrative.mood is not None
    
    @pytest.mark.asyncio
    async def test_generate_transition_narrative(self, weather_service):
        """Test generating narrative for weather transitions."""
        current_weather = WeatherData(
            temperature=75,
            condition=WeatherCondition.CLEAR,
            description="Clear skies",
            timestamp=datetime.now()
        )
        
        future_weather = WeatherData(
            temperature=65,
            condition=WeatherCondition.RAIN,
            description="Light rain",
            timestamp=datetime.now() + timedelta(hours=2)
        )
        
        narrative = await weather_service.generate_transition_narrative(
            current_weather,
            future_weather,
            duration_hours=2
        )
        
        assert "clear" in narrative.text.lower()
        assert "rain" in narrative.text.lower()
        assert any(word in narrative.text.lower() for word in ["change", "transition", "moving", "approaching"])


class TestRoadConditions:
    """Test road condition assessment."""
    
    @pytest.mark.asyncio
    async def test_assess_road_conditions_dry(self, weather_service):
        """Test assessing dry road conditions."""
        weather = WeatherData(
            temperature=75,
            condition=WeatherCondition.CLEAR,
            description="Clear",
            humidity=40,
            timestamp=datetime.now()
        )
        
        conditions = await weather_service.assess_road_conditions(weather)
        
        assert isinstance(conditions, RoadCondition)
        assert conditions.surface == "dry"
        assert conditions.visibility == "excellent"
        assert conditions.safety_rating >= 0.8
        assert len(conditions.warnings) == 0
    
    @pytest.mark.asyncio
    async def test_assess_road_conditions_wet(self, weather_service):
        """Test assessing wet road conditions."""
        weather = WeatherData(
            temperature=60,
            condition=WeatherCondition.RAIN,
            description="Moderate rain",
            humidity=90,
            visibility=5.0,
            timestamp=datetime.now()
        )
        
        conditions = await weather_service.assess_road_conditions(weather)
        
        assert conditions.surface == "wet"
        assert conditions.visibility == "reduced"
        assert conditions.safety_rating < 0.7
        assert len(conditions.warnings) > 0
        assert any("slippery" in w.lower() for w in conditions.warnings)
    
    @pytest.mark.asyncio
    async def test_assess_road_conditions_snow(self, weather_service):
        """Test assessing snowy road conditions."""
        weather = WeatherData(
            temperature=28,
            condition=WeatherCondition.SNOW,
            description="Heavy snow",
            humidity=85,
            visibility=0.5,
            wind_speed=25,
            timestamp=datetime.now()
        )
        
        conditions = await weather_service.assess_road_conditions(weather)
        
        assert conditions.surface in ["snow", "ice"]
        assert conditions.visibility == "poor"
        assert conditions.safety_rating < 0.5
        assert len(conditions.warnings) >= 2
        assert any("hazardous" in w.lower() for w in conditions.warnings)
        assert conditions.recommended_speed_reduction > 30  # Significant speed reduction
    
    @pytest.mark.asyncio
    async def test_assess_road_conditions_fog(self, weather_service):
        """Test assessing foggy conditions."""
        weather = WeatherData(
            temperature=55,
            condition=WeatherCondition.FOG,
            description="Dense fog",
            humidity=95,
            visibility=0.25,
            timestamp=datetime.now()
        )
        
        conditions = await weather_service.assess_road_conditions(weather)
        
        assert conditions.visibility == "very poor"
        assert conditions.safety_rating < 0.6
        assert any("visibility" in w.lower() for w in conditions.warnings)
        assert any("fog" in w.lower() for w in conditions.warnings)


class TestWeatherImpactAnalysis:
    """Test analyzing weather impact on journey."""
    
    @pytest.mark.asyncio
    async def test_analyze_journey_weather_impact(self, weather_service, mock_weather_client):
        """Test analyzing weather impact on entire journey."""
        route = {
            "segments": [
                {"location": {"lat": 37.7749, "lng": -122.4194}, "time": datetime.now()},
                {"location": {"lat": 36.7783, "lng": -119.4179}, "time": datetime.now() + timedelta(hours=2)},
                {"location": {"lat": 34.0522, "lng": -118.2437}, "time": datetime.now() + timedelta(hours=5)}
            ],
            "total_duration": timedelta(hours=5)
        }
        
        # Mock different weather conditions
        mock_weather_client.get_current_weather.side_effect = [
            {"main": {"temp": 72}, "weather": [{"id": 800}]},  # Clear
            {"main": {"temp": 85}, "weather": [{"id": 500}]},  # Rain
            {"main": {"temp": 78}, "weather": [{"id": 803}]}   # Cloudy
        ]
        
        impact = await weather_service.analyze_journey_weather_impact(route)
        
        assert impact["has_weather_changes"] is True
        assert impact["worst_condition"] == WeatherCondition.RAIN
        assert impact["estimated_delay_minutes"] > 0
        assert len(impact["recommendations"]) > 0
    
    @pytest.mark.asyncio
    async def test_calculate_weather_delay(self, weather_service):
        """Test calculating delays due to weather."""
        weather_conditions = [
            WeatherData(condition=WeatherCondition.CLEAR, temperature=70),
            WeatherData(condition=WeatherCondition.RAIN, temperature=60, visibility=5),
            WeatherData(condition=WeatherCondition.HEAVY_RAIN, temperature=55, visibility=2),
            WeatherData(condition=WeatherCondition.SNOW, temperature=30, visibility=1)
        ]
        
        base_duration = 3600  # 1 hour
        
        delays = []
        for weather in weather_conditions:
            delay = await weather_service.calculate_weather_delay(weather, base_duration)
            delays.append(delay)
        
        assert delays[0] == 0  # Clear weather, no delay
        assert delays[1] > 0   # Rain causes some delay
        assert delays[2] > delays[1]  # Heavy rain causes more delay
        assert delays[3] > delays[2]  # Snow causes most delay


class TestWeatherCaching:
    """Test weather data caching."""
    
    @pytest.mark.asyncio
    async def test_cache_weather_data(self, weather_service, mock_weather_client, sample_location):
        """Test that weather data is cached."""
        # Mock weather response
        mock_weather_client.get_current_weather.return_value = {
            "main": {"temp": 72},
            "weather": [{"id": 800}]
        }
        
        # First call - should hit API
        weather1 = await weather_service.get_current_weather(sample_location)
        assert mock_weather_client.get_current_weather.call_count == 1
        
        # Second call within cache period - should use cache
        weather2 = await weather_service.get_current_weather(sample_location)
        assert mock_weather_client.get_current_weather.call_count == 1  # No additional call
        assert weather1.temperature == weather2.temperature
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self, weather_service, mock_weather_client, sample_location):
        """Test that cache expires appropriately."""
        # Mock changing weather
        mock_weather_client.get_current_weather.side_effect = [
            {"main": {"temp": 72}, "weather": [{"id": 800}]},
            {"main": {"temp": 75}, "weather": [{"id": 801}]}
        ]
        
        # First call
        weather1 = await weather_service.get_current_weather(sample_location)
        assert weather1.temperature == 72
        
        # Simulate cache expiration
        with patch.object(weather_service, '_is_cache_valid', return_value=False):
            weather2 = await weather_service.get_current_weather(sample_location)
            assert weather2.temperature == 75
            assert mock_weather_client.get_current_weather.call_count == 2


class TestErrorHandling:
    """Test error handling in weather service."""
    
    @pytest.mark.asyncio
    async def test_handle_api_error(self, weather_service, mock_weather_client, sample_location):
        """Test handling weather API errors."""
        # Mock API error
        mock_weather_client.get_current_weather.side_effect = Exception("API key invalid")
        
        # Should return default/cached data or raise appropriate error
        with pytest.raises(Exception) as exc_info:
            await weather_service.get_current_weather(sample_location)
        
        assert "API key" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_handle_invalid_location(self, weather_service):
        """Test handling invalid location data."""
        invalid_location = {"latitude": 37.7749}  # Missing lng
        
        with pytest.raises(ValueError) as exc_info:
            await weather_service.get_current_weather(invalid_location)
        
        assert "invalid location" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_handle_missing_weather_data(self, weather_service, mock_weather_client, sample_location):
        """Test handling incomplete weather data."""
        # Mock incomplete response
        mock_weather_client.get_current_weather.return_value = {
            "main": {"temp": 72}
            # Missing weather array
        }
        
        weather = await weather_service.get_current_weather(sample_location)
        
        # Should handle gracefully with defaults
        assert weather.temperature == 72
        assert weather.condition == WeatherCondition.UNKNOWN
        assert weather.description == "Unknown conditions"