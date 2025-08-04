import { LocationData } from './locationService';
import { memoizeAsync } from '@utils/cache';
import { mapsProxy } from '@/services/api/mapsProxy';
import { logger } from '@/services/logger';

export interface WeatherData {
  temperature: number;
  description: string;
  airQuality: string;
  sunrise: string;
  sunset: string;
  humidity: number;
  windSpeed: number;
  windDirection: string;
  precipitation: number;
  uvIndex: number;
  visibility: number;
  pressure: number;
  feelsLike: number;
}

class WeatherService {
  // No API keys needed - all calls go through backend proxy
  
  constructor() {
    // Weather API calls are handled through the backend proxy
  }

  getWeatherData = memoizeAsync(
    async (location: LocationData): Promise<WeatherData> => {
      try {
        // Use backend proxy to get weather data - API key is handled server-side
        const weatherData = await mapsProxy.getWeather(location);
        
        // Convert the backend response to our expected format
        return {
          temperature: weatherData.main.temp,
          description: weatherData.weather[0].description,
          sunrise: new Date(weatherData.sys.sunrise * 1000).toISOString(),
          sunset: new Date(weatherData.sys.sunset * 1000).toISOString(),
          humidity: weatherData.main.humidity,
          windSpeed: weatherData.wind.speed,
          windDirection: this.getWindDirection(weatherData.wind.deg),
          precipitation: weatherData.rain?.['1h'] || 0,
          uvIndex: weatherData.uvi || 0,
          visibility: weatherData.visibility,
          pressure: weatherData.main.pressure,
          feelsLike: weatherData.main.feels_like,
          airQuality: 'Good', // Backend can implement air quality API later
        };
      } catch (error) {
        logger.error('Failed to fetch weather data', error as Error);
        throw error;
      }
    },
    100, // Cache size
    300  // TTL: 5 minutes
  );

  // Weather forecast method using backend proxy
  async getWeatherForecast(location: LocationData, days: number = 5): Promise<any> {
    try {
      const forecast = await mapsProxy.getWeatherForecast(location, days);
      return forecast;
    } catch (error) {
      logger.error('Failed to fetch weather forecast', error as Error);
      throw error;
    }
  }

  private getWindDirection(degrees: number): string {
    const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
    const index = Math.round(degrees / 45) % 8;
    return directions[index];
  }

  private getAirQualityDescription(aqi: number): string {
    if (aqi <= 50) return 'Good';
    if (aqi <= 100) return 'Moderate';
    if (aqi <= 150) return 'Unhealthy for Sensitive Groups';
    if (aqi <= 200) return 'Unhealthy';
    if (aqi <= 300) return 'Very Unhealthy';
    return 'Hazardous';
  }
}

export default new WeatherService(); 