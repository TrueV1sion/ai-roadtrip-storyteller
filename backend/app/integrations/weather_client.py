"""
OpenWeatherMap API client with proper UTF-8 encoding support.
Handles weather data fetching with encoding fixes and caching.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlencode

import aiohttp
from aiohttp import ClientError, ClientResponseError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from backend.app.core.logger import logger
from backend.app.core.cache import cache_manager
from backend.app.core.config import settings
from backend.app.core.circuit_breaker import get_weather_circuit_breaker, CircuitOpenError


class WeatherClient:
    """Client for OpenWeatherMap API with encoding fixes and production features."""
    
    def __init__(self):
        """Initialize weather client with configuration."""
        self.api_key = settings.OPENWEATHERMAP_API_KEY
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.timeout = aiohttp.ClientTimeout(total=10)
        
        # Rate limiting
        self.rate_limit_delay = 0.1  # 100ms between requests
        self._last_request_time = 0
        
        # Mock mode for testing
        self.mock_mode = not self.api_key or settings.ENVIRONMENT == "test"
        
        if not self.api_key and not self.mock_mode:
            logger.warning("OpenWeatherMap API key not configured")
    
    async def _enforce_rate_limit(self):
        """Enforce rate limiting between requests."""
        import time
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)
        
        self._last_request_time = time.time()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ClientError, asyncio.TimeoutError)),
        before_sleep=before_sleep_log(logger, "WARNING")
    )
    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request with retry logic and proper encoding."""
        if self.mock_mode:
            return self._get_mock_weather_data(params)
        
        await self._enforce_rate_limit()
        
        # Add API key to params
        params["appid"] = self.api_key
        params["units"] = params.get("units", "metric")  # Default to metric
        
        # Build URL with proper encoding
        url = f"{self.base_url}/{endpoint}"
        
        # Check cache
        cache_key = f"weather:{endpoint}:{json.dumps(params, sort_keys=True)}"
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            logger.debug(f"Weather cache hit for {endpoint}")
            return json.loads(cached_result)
        
        logger.info(f"Fetching weather data from {endpoint}")
        
        try:
            # Create session with UTF-8 encoding support
            connector = aiohttp.TCPConnector(force_close=True)
            async with aiohttp.ClientSession(
                timeout=self.timeout,
                connector=connector,
                headers={"Accept": "application/json; charset=utf-8"}
            ) as session:
                async with session.get(url, params=params) as response:
                    # Force UTF-8 encoding on response
                    response_text = await response.text(encoding='utf-8')
                    
                    if response.status == 200:
                        # Parse JSON with UTF-8 support
                        data = json.loads(response_text)
                        
                        # Cache for 10 minutes
                        await cache_manager.setex(
                            cache_key,
                            600,
                            json.dumps(data, ensure_ascii=False)
                        )
                        
                        return data
                    
                    elif response.status == 401:
                        raise ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message="Invalid API key"
                        )
                    
                    elif response.status == 404:
                        # Location not found
                        return None
                    
                    else:
                        raise ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message=f"API error: {response_text}"
                        )
                        
        except UnicodeDecodeError as e:
            logger.error(f"Unicode decode error in weather API: {e}")
            # Return a safe fallback
            return self._get_fallback_weather_data()
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in weather API: {e}")
            return self._get_fallback_weather_data()
            
        except Exception as e:
            logger.error(f"Weather API error: {e}")
            raise
    
    async def get_current_weather(
        self,
        latitude: float,
        longitude: float,
        lang: str = "en"
    ) -> Optional[Dict[str, Any]]:
        """
        Get current weather for coordinates.
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            lang: Language code for descriptions
            
        Returns:
            Weather data with UTF-8 encoded strings
        """
        params = {
            "lat": latitude,
            "lon": longitude,
            "lang": lang
        }
        
        try:
            data = await self._make_request("weather", params)
            
            if not data:
                return None
            
            # Process and sanitize the response
            return self._process_weather_data(data)
            
        except Exception as e:
            logger.error(f"Failed to get current weather: {e}")
            return self._get_fallback_weather_data()
    
    async def get_weather_forecast(
        self,
        latitude: float,
        longitude: float,
        hours: int = 24,
        lang: str = "en"
    ) -> Optional[Dict[str, Any]]:
        """
        Get weather forecast for coordinates.
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            hours: Number of hours to forecast (max 120)
            lang: Language code for descriptions
            
        Returns:
            Forecast data with UTF-8 encoded strings
        """
        # Calculate number of 3-hour periods needed
        periods = min(hours // 3, 40)  # API returns max 40 periods
        
        params = {
            "lat": latitude,
            "lon": longitude,
            "cnt": periods,
            "lang": lang
        }
        
        try:
            data = await self._make_request("forecast", params)
            
            if not data:
                return None
            
            # Process forecast data
            return self._process_forecast_data(data, hours)
            
        except Exception as e:
            logger.error(f"Failed to get weather forecast: {e}")
            return None
    
    def _process_weather_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and sanitize weather data."""
        # Ensure all text fields are properly encoded
        weather_desc = data.get("weather", [{}])[0].get("description", "")
        weather_main = data.get("weather", [{}])[0].get("main", "")
        
        # Handle potential encoding issues in city names
        city_name = data.get("name", "")
        if isinstance(city_name, bytes):
            city_name = city_name.decode('utf-8', errors='replace')
        
        processed = {
            "location": {
                "name": city_name,
                "country": data.get("sys", {}).get("country", ""),
                "latitude": data.get("coord", {}).get("lat"),
                "longitude": data.get("coord", {}).get("lon")
            },
            "current": {
                "temperature": data.get("main", {}).get("temp"),
                "feels_like": data.get("main", {}).get("feels_like"),
                "humidity": data.get("main", {}).get("humidity"),
                "pressure": data.get("main", {}).get("pressure"),
                "visibility": data.get("visibility"),
                "wind_speed": data.get("wind", {}).get("speed"),
                "wind_direction": data.get("wind", {}).get("deg"),
                "clouds": data.get("clouds", {}).get("all"),
                "weather": weather_main,
                "description": self._sanitize_text(weather_desc),
                "icon": data.get("weather", [{}])[0].get("icon", "")
            },
            "timestamp": datetime.fromtimestamp(data.get("dt", 0)).isoformat(),
            "timezone_offset": data.get("timezone", 0)
        }
        
        # Add rain/snow data if present
        if "rain" in data:
            processed["current"]["rain_1h"] = data["rain"].get("1h", 0)
        if "snow" in data:
            processed["current"]["snow_1h"] = data["snow"].get("1h", 0)
        
        return processed
    
    def _process_forecast_data(self, data: Dict[str, Any], hours: int) -> Dict[str, Any]:
        """Process forecast data."""
        forecasts = []
        
        for item in data.get("list", [])[:hours // 3]:
            weather_desc = item.get("weather", [{}])[0].get("description", "")
            weather_main = item.get("weather", [{}])[0].get("main", "")
            
            forecast = {
                "time": datetime.fromtimestamp(item.get("dt", 0)).isoformat(),
                "temperature": item.get("main", {}).get("temp"),
                "feels_like": item.get("main", {}).get("feels_like"),
                "humidity": item.get("main", {}).get("humidity"),
                "weather": weather_main,
                "description": self._sanitize_text(weather_desc),
                "icon": item.get("weather", [{}])[0].get("icon", ""),
                "wind_speed": item.get("wind", {}).get("speed"),
                "clouds": item.get("clouds", {}).get("all"),
                "pop": item.get("pop", 0)  # Probability of precipitation
            }
            
            # Add rain/snow data if present
            if "rain" in item:
                forecast["rain_3h"] = item["rain"].get("3h", 0)
            if "snow" in item:
                forecast["snow_3h"] = item["snow"].get("3h", 0)
            
            forecasts.append(forecast)
        
        return {
            "location": {
                "name": data.get("city", {}).get("name", ""),
                "country": data.get("city", {}).get("country", ""),
                "latitude": data.get("city", {}).get("coord", {}).get("lat"),
                "longitude": data.get("city", {}).get("coord", {}).get("lon")
            },
            "forecast": forecasts,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def _sanitize_text(self, text: str) -> str:
        """Sanitize text to handle encoding issues."""
        if not text:
            return ""
        
        # Handle bytes
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='replace')
        
        # Replace common problematic characters
        replacements = {
            '\u2019': "'",  # Right single quotation mark
            '\u2018': "'",  # Left single quotation mark
            '\u201c': '"',  # Left double quotation mark
            '\u201d': '"',  # Right double quotation mark
            '\u2013': '-',  # En dash
            '\u2014': '--', # Em dash
            '\u2026': '...', # Horizontal ellipsis
            '\u00a0': ' ',  # Non-breaking space
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Remove any remaining non-ASCII characters if needed
        # text = text.encode('ascii', 'ignore').decode('ascii')
        
        return text.strip()
    
    def _get_mock_weather_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Return mock weather data for testing."""
        return {
            "coord": {"lon": params.get("lon", -122.4194), "lat": params.get("lat", 37.7749)},
            "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
            "main": {
                "temp": 22.5,
                "feels_like": 21.8,
                "temp_min": 20.0,
                "temp_max": 25.0,
                "pressure": 1013,
                "humidity": 65
            },
            "visibility": 10000,
            "wind": {"speed": 3.5, "deg": 250},
            "clouds": {"all": 0},
            "dt": int(datetime.utcnow().timestamp()),
            "sys": {"country": "US"},
            "timezone": -28800,
            "name": "San Francisco"
        }
    
    def _get_fallback_weather_data(self) -> Dict[str, Any]:
        """Return safe fallback weather data."""
        return {
            "location": {
                "name": "Unknown",
                "country": "",
                "latitude": 0,
                "longitude": 0
            },
            "current": {
                "temperature": 20,
                "feels_like": 20,
                "humidity": 50,
                "pressure": 1013,
                "visibility": 10000,
                "wind_speed": 0,
                "wind_direction": 0,
                "clouds": 50,
                "weather": "Unknown",
                "description": "Weather data unavailable",
                "icon": "01d"
            },
            "timestamp": datetime.utcnow().isoformat(),
            "timezone_offset": 0
        }
    
    async def get_weather_summary(
        self,
        latitude: float,
        longitude: float,
        lang: str = "en"
    ) -> str:
        """
        Get a human-readable weather summary.
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            lang: Language code
            
        Returns:
            Weather summary text
        """
        weather = await self.get_current_weather(latitude, longitude, lang)
        
        if not weather:
            return "Weather information unavailable"
        
        current = weather["current"]
        temp = current["temperature"]
        desc = current["description"]
        feels_like = current["feels_like"]
        
        summary = f"Currently {temp}°C ({desc}), feels like {feels_like}°C"
        
        # Add rain/snow info if present
        if current.get("rain_1h", 0) > 0:
            summary += f", {current['rain_1h']}mm rain in last hour"
        if current.get("snow_1h", 0) > 0:
            summary += f", {current['snow_1h']}mm snow in last hour"
        
        return summary


# Global instance
weather_client = WeatherClient()