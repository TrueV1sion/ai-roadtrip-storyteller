"""
Weather service integration for contextual awareness and storytelling.
Uses the weather client with proper encoding support.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from app.integrations.weather_client import weather_client
from app.core.logger import logger


class WeatherService:
    """Service for weather-related functionality across the application."""
    
    @staticmethod
    async def get_weather_context(
        latitude: float,
        longitude: float,
        include_forecast: bool = False,
        forecast_hours: int = 6
    ) -> Dict[str, Any]:
        """
        Get weather context for a location.
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            include_forecast: Whether to include forecast data
            forecast_hours: Hours of forecast to include
            
        Returns:
            Weather context dictionary
        """
        try:
            # Get current weather
            current = await weather_client.get_current_weather(latitude, longitude)
            
            if not current:
                return WeatherService._get_default_weather_context()
            
            context = {
                "current": {
                    "temperature": current["current"]["temperature"],
                    "feels_like": current["current"]["feels_like"],
                    "conditions": current["current"]["weather"],
                    "description": current["current"]["description"],
                    "humidity": current["current"]["humidity"],
                    "wind_speed": current["current"]["wind_speed"],
                    "visibility": current["current"]["visibility"],
                    "rain": current["current"].get("rain_1h", 0),
                    "snow": current["current"].get("snow_1h", 0)
                },
                "location": current["location"]["name"],
                "timestamp": current["timestamp"]
            }
            
            # Add weather-based recommendations
            context["recommendations"] = WeatherService._get_weather_recommendations(
                current["current"]
            )
            
            # Add forecast if requested
            if include_forecast:
                forecast = await weather_client.get_weather_forecast(
                    latitude, longitude, forecast_hours
                )
                if forecast:
                    context["forecast"] = WeatherService._process_forecast(
                        forecast["forecast"]
                    )
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to get weather context: {e}")
            return WeatherService._get_default_weather_context()
    
    @staticmethod
    def _get_weather_recommendations(weather_data: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on weather conditions."""
        recommendations = []
        
        temp = weather_data["temperature"]
        conditions = weather_data["weather"].lower()
        wind_speed = weather_data["wind_speed"]
        visibility = weather_data["visibility"]
        rain = weather_data.get("rain_1h", 0)
        snow = weather_data.get("snow_1h", 0)
        
        # Temperature-based recommendations
        if temp < 0:
            recommendations.append("Watch for icy conditions on roads")
        elif temp > 30:
            recommendations.append("Stay hydrated and use air conditioning")
        
        # Condition-based recommendations
        if "rain" in conditions or rain > 0:
            recommendations.append("Drive carefully in wet conditions")
            if rain > 10:
                recommendations.append("Heavy rain - consider waiting for better conditions")
        
        if "snow" in conditions or snow > 0:
            recommendations.append("Snow conditions - reduce speed and increase following distance")
        
        if "fog" in conditions or visibility < 1000:
            recommendations.append("Limited visibility - use fog lights if available")
        
        if "storm" in conditions or "thunder" in conditions:
            recommendations.append("Storm conditions - avoid stopping under trees or overpasses")
        
        # Wind-based recommendations
        if wind_speed > 10:  # m/s
            recommendations.append("Strong winds - be cautious, especially on bridges")
        
        return recommendations
    
    @staticmethod
    def _process_forecast(forecast_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process forecast data for context."""
        processed = []
        
        for item in forecast_data:
            processed.append({
                "time": item["time"],
                "temperature": item["temperature"],
                "conditions": item["weather"],
                "description": item["description"],
                "rain_probability": item["pop"],
                "rain_amount": item.get("rain_3h", 0),
                "snow_amount": item.get("snow_3h", 0)
            })
        
        return processed
    
    @staticmethod
    def _get_default_weather_context() -> Dict[str, Any]:
        """Return default weather context when data unavailable."""
        return {
            "current": {
                "temperature": 20,
                "feels_like": 20,
                "conditions": "Clear",
                "description": "Weather data unavailable",
                "humidity": 50,
                "wind_speed": 0,
                "visibility": 10000,
                "rain": 0,
                "snow": 0
            },
            "location": "Unknown",
            "timestamp": datetime.utcnow().isoformat(),
            "recommendations": []
        }
    
    @staticmethod
    async def get_weather_summary(latitude: float, longitude: float) -> str:
        """Get a concise weather summary for voice output."""
        return await weather_client.get_weather_summary(latitude, longitude)
    
    @staticmethod
    def is_severe_weather(weather_context: Dict[str, Any]) -> bool:
        """Check if weather conditions are severe."""
        current = weather_context.get("current", {})
        conditions = current.get("conditions", "").lower()
        
        severe_keywords = [
            "storm", "thunder", "tornado", "hurricane", 
            "blizzard", "hail", "flood"
        ]
        
        # Check conditions
        if any(keyword in conditions for keyword in severe_keywords):
            return True
        
        # Check precipitation
        if current.get("rain", 0) > 20:  # Heavy rain
            return True
        
        if current.get("snow", 0) > 10:  # Heavy snow
            return True
        
        # Check visibility
        if current.get("visibility", 10000) < 500:  # Very poor visibility
            return True
        
        # Check wind speed
        if current.get("wind_speed", 0) > 20:  # Very strong winds
            return True
        
        return False
    
    @staticmethod
    def get_driving_condition_score(weather_context: Dict[str, Any]) -> float:
        """
        Calculate a driving condition score (0-100).
        Higher score = better conditions.
        """
        current = weather_context.get("current", {})
        score = 100.0
        
        # Temperature impact
        temp = current.get("temperature", 20)
        if temp < 0 or temp > 35:
            score -= 10
        
        # Precipitation impact
        rain = current.get("rain", 0)
        snow = current.get("snow", 0)
        
        if rain > 0:
            score -= min(rain * 2, 30)  # Up to -30 for heavy rain
        
        if snow > 0:
            score -= min(snow * 3, 40)  # Up to -40 for heavy snow
        
        # Visibility impact
        visibility = current.get("visibility", 10000)
        if visibility < 1000:
            score -= 20
        elif visibility < 5000:
            score -= 10
        
        # Wind impact
        wind = current.get("wind_speed", 0)
        if wind > 15:
            score -= 15
        elif wind > 10:
            score -= 10
        elif wind > 5:
            score -= 5
        
        # Condition keywords impact
        conditions = current.get("conditions", "").lower()
        if "storm" in conditions:
            score -= 20
        elif "fog" in conditions:
            score -= 15
        
        return max(score, 0)  # Don't go below 0


# Export service instance
weather_service = WeatherService()