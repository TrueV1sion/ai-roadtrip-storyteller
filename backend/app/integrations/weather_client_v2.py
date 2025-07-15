"""
Enhanced OpenWeatherMap API client with circuit breaker protection.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlencode

import aiohttp
from aiohttp import ClientError, ClientResponseError

from backend.app.core.logger import logger
from backend.app.core.cache import cache_manager
from backend.app.core.config import settings
from backend.app.core.circuit_breaker import (
    get_weather_circuit_breaker, 
    CircuitOpenError,
    with_circuit_breaker
)


class WeatherClientV2:
    """Enhanced weather client with circuit breaker protection."""
    
    def __init__(self):
        """Initialize weather client with configuration."""
        self.api_key = settings.OPENWEATHERMAP_API_KEY
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.timeout = aiohttp.ClientTimeout(total=5)  # Reduced timeout for circuit breaker
        
        # Rate limiting
        self.rate_limit_delay = 0.1  # 100ms between requests
        self._last_request_time = 0
        
        # Mock mode for testing
        self.mock_mode = not self.api_key or settings.ENVIRONMENT == "test"
        
        # Get circuit breaker instance
        self.circuit_breaker = get_weather_circuit_breaker()
        
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
    
    async def _make_api_call(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make the actual API call - wrapped by circuit breaker."""
        await self._enforce_rate_limit()
        
        # Add API key to params
        params["appid"] = self.api_key
        params["units"] = params.get("units", "metric")
        
        # Build URL
        url = f"{self.base_url}/{endpoint}"
        
        logger.info(f"Making weather API request to {endpoint}")
        
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
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request with circuit breaker protection."""
        if self.mock_mode:
            return self._get_mock_weather_data(params)
        
        # Check cache first
        cache_key = f"weather:{endpoint}:{json.dumps(params, sort_keys=True)}"
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            logger.debug(f"Weather cache hit for {endpoint}")
            return json.loads(cached_result)
        
        try:
            # Make request through circuit breaker
            data = await self.circuit_breaker.call_async(
                self._make_api_call,
                endpoint,
                params
            )
            
            if data:
                # Cache for 10 minutes
                await cache_manager.setex(
                    cache_key,
                    600,
                    json.dumps(data, ensure_ascii=False)
                )
            
            return data
            
        except CircuitOpenError as e:
            logger.warning(f"Weather API circuit breaker is open: {e}")
            # Return cached data if available, even if expired
            expired_data = await cache_manager.get(cache_key)
            if expired_data:
                logger.info("Returning expired cache data due to circuit breaker")
                return json.loads(expired_data)
            return self._get_fallback_weather_data()
            
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            logger.error(f"Encoding error in weather API: {e}")
            return self._get_fallback_weather_data()
            
        except Exception as e:
            logger.error(f"Weather API error: {e}")
            # For unexpected errors, still return fallback
            return self._get_fallback_weather_data()
    
    async def get_current_weather(
        self,
        latitude: float,
        longitude: float,
        lang: str = "en"
    ) -> Optional[Dict[str, Any]]:
        """
        Get current weather for coordinates with circuit breaker protection.
        
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
        Get weather forecast with circuit breaker protection.
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            hours: Number of hours to forecast (max 120)
            lang: Language code for descriptions
            
        Returns:
            Forecast data with UTF-8 encoded strings
        """
        params = {
            "lat": latitude,
            "lon": longitude,
            "lang": lang,
            "cnt": min(hours // 3, 40)  # API returns 3-hour intervals
        }
        
        try:
            data = await self._make_request("forecast", params)
            
            if not data:
                return None
            
            # Process forecast data
            return self._process_forecast_data(data, hours)
            
        except Exception as e:
            logger.error(f"Failed to get weather forecast: {e}")
            return self._get_fallback_forecast_data(hours)
    
    def _process_weather_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and sanitize weather data."""
        try:
            # Extract and sanitize relevant fields
            processed = {
                "temperature": data.get("main", {}).get("temp", 20),
                "feels_like": data.get("main", {}).get("feels_like", 20),
                "humidity": data.get("main", {}).get("humidity", 50),
                "pressure": data.get("main", {}).get("pressure", 1013),
                "wind_speed": data.get("wind", {}).get("speed", 0),
                "wind_direction": data.get("wind", {}).get("deg", 0),
                "clouds": data.get("clouds", {}).get("all", 0),
                "visibility": data.get("visibility", 10000),
                "weather": [],
                "timestamp": datetime.now().isoformat(),
                "location": {
                    "lat": data.get("coord", {}).get("lat"),
                    "lon": data.get("coord", {}).get("lon"),
                    "name": data.get("name", "Unknown")
                }
            }
            
            # Process weather conditions
            for condition in data.get("weather", []):
                processed["weather"].append({
                    "id": condition.get("id"),
                    "main": condition.get("main", "Clear"),
                    "description": condition.get("description", "clear sky"),
                    "icon": condition.get("icon", "01d")
                })
            
            # Add sunrise/sunset if available
            if "sys" in data:
                if "sunrise" in data["sys"]:
                    processed["sunrise"] = datetime.fromtimestamp(
                        data["sys"]["sunrise"]
                    ).isoformat()
                if "sunset" in data["sys"]:
                    processed["sunset"] = datetime.fromtimestamp(
                        data["sys"]["sunset"]
                    ).isoformat()
            
            return processed
            
        except Exception as e:
            logger.error(f"Error processing weather data: {e}")
            return self._get_fallback_weather_data()
    
    def _process_forecast_data(self, data: Dict[str, Any], hours: int) -> Dict[str, Any]:
        """Process and sanitize forecast data."""
        try:
            forecasts = []
            
            for item in data.get("list", [])[:hours // 3]:
                forecast_item = {
                    "timestamp": datetime.fromtimestamp(item.get("dt", 0)).isoformat(),
                    "temperature": item.get("main", {}).get("temp", 20),
                    "feels_like": item.get("main", {}).get("feels_like", 20),
                    "humidity": item.get("main", {}).get("humidity", 50),
                    "wind_speed": item.get("wind", {}).get("speed", 0),
                    "clouds": item.get("clouds", {}).get("all", 0),
                    "precipitation": item.get("rain", {}).get("3h", 0) + 
                                   item.get("snow", {}).get("3h", 0),
                    "weather": []
                }
                
                # Process weather conditions
                for condition in item.get("weather", []):
                    forecast_item["weather"].append({
                        "main": condition.get("main", "Clear"),
                        "description": condition.get("description", "clear sky"),
                        "icon": condition.get("icon", "01d")
                    })
                
                forecasts.append(forecast_item)
            
            return {
                "forecasts": forecasts,
                "location": {
                    "lat": data.get("city", {}).get("coord", {}).get("lat"),
                    "lon": data.get("city", {}).get("coord", {}).get("lon"),
                    "name": data.get("city", {}).get("name", "Unknown"),
                    "country": data.get("city", {}).get("country", "")
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing forecast data: {e}")
            return self._get_fallback_forecast_data(hours)
    
    def _get_mock_weather_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Return mock weather data for testing."""
        return {
            "coord": {"lon": params.get("lon", -122.08), "lat": params.get("lat", 37.39)},
            "weather": [{
                "id": 800,
                "main": "Clear",
                "description": "clear sky",
                "icon": "01d"
            }],
            "main": {
                "temp": 22.5,
                "feels_like": 21.8,
                "pressure": 1013,
                "humidity": 55
            },
            "wind": {"speed": 3.5, "deg": 180},
            "clouds": {"all": 0},
            "visibility": 10000,
            "sys": {
                "sunrise": int((datetime.now().replace(hour=6, minute=30)).timestamp()),
                "sunset": int((datetime.now().replace(hour=19, minute=30)).timestamp())
            },
            "name": "Mock Location"
        }
    
    def _get_fallback_weather_data(self) -> Dict[str, Any]:
        """Return fallback weather data when API fails."""
        return {
            "temperature": 20,
            "feels_like": 20,
            "humidity": 50,
            "pressure": 1013,
            "wind_speed": 2,
            "wind_direction": 0,
            "clouds": 25,
            "visibility": 10000,
            "weather": [{
                "id": 800,
                "main": "Clear",
                "description": "Weather data temporarily unavailable",
                "icon": "01d"
            }],
            "timestamp": datetime.now().isoformat(),
            "location": {
                "name": "Unknown"
            },
            "_fallback": True
        }
    
    def _get_fallback_forecast_data(self, hours: int) -> Dict[str, Any]:
        """Return fallback forecast data when API fails."""
        base_time = datetime.now()
        forecasts = []
        
        for i in range(0, hours, 3):
            forecasts.append({
                "timestamp": (base_time + timedelta(hours=i)).isoformat(),
                "temperature": 20,
                "feels_like": 20,
                "humidity": 50,
                "wind_speed": 2,
                "clouds": 25,
                "precipitation": 0,
                "weather": [{
                    "main": "Clear",
                    "description": "Forecast temporarily unavailable",
                    "icon": "01d"
                }]
            })
        
        return {
            "forecasts": forecasts,
            "location": {"name": "Unknown"},
            "_fallback": True
        }
    
    async def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get circuit breaker status for monitoring."""
        return self.circuit_breaker.get_stats()


# Create singleton instance
weather_client_v2 = WeatherClientV2()