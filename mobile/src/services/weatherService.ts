import { LocationData } from './locationService';
import { memoizeAsync } from '@utils/cache';
import { APIClient } from '@utils/apiUtils';

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
  private readonly OPEN_WEATHER_API_KEY = process.env.EXPO_PUBLIC_OPEN_WEATHER_KEY;
  private readonly AIR_QUALITY_API_KEY = process.env.EXPO_PUBLIC_AIR_QUALITY_API_KEY;
  
  private readonly weatherClient: APIClient;
  private readonly airQualityClient: APIClient;

  constructor() {
    this.weatherClient = new APIClient({
      baseURL: 'https://api.openweathermap.org/data/3.0',
      timeout: 5000,
      rateLimit: {
        maxRequests: 60,
        windowMs: 60000, // 1 minute
      },
      retry: {
        maxAttempts: 3,
        baseDelay: 1000,
        maxDelay: 5000,
        retryableStatuses: [408, 429, 500, 502, 503, 504],
      },
    });

    this.airQualityClient = new APIClient({
      baseURL: 'https://api.airquality.com/v1',
      timeout: 5000,
      rateLimit: {
        maxRequests: 30,
        windowMs: 60000, // 1 minute
      },
      retry: {
        maxAttempts: 2,
        baseDelay: 1000,
        maxDelay: 3000,
        retryableStatuses: [408, 429, 500, 502, 503, 504],
      },
    });
  }

  getWeatherData = memoizeAsync(
    async (location: LocationData): Promise<WeatherData> => {
      // Fetch weather and air quality data in parallel
      const [weatherData, airQualityData] = await Promise.all([
        this.fetchWeatherData(location),
        this.fetchAirQualityData(location),
      ]);

      return {
        ...weatherData,
        airQuality: airQualityData.airQuality,
      };
    },
    100, // Cache size
    300  // TTL: 5 minutes
  );

  private async fetchWeatherData(location: LocationData): Promise<Omit<WeatherData, 'airQuality'>> {
    interface OpenWeatherResponse {
      current: {
        temp: number;
        weather: Array<{ description: string }>;
        sunrise: number;
        sunset: number;
        humidity: number;
        wind_speed: number;
        wind_deg: number;
        rain?: { '1h': number };
        uvi: number;
        visibility: number;
        pressure: number;
        feels_like: number;
      };
    }

    const response = await this.weatherClient.get<OpenWeatherResponse>('/onecall', {
      params: {
        lat: location.latitude,
        lon: location.longitude,
        appid: this.OPEN_WEATHER_API_KEY,
        units: 'metric',
        exclude: 'minutely,hourly,daily,alerts',
      },
    });

    return {
      temperature: response.current.temp,
      description: response.current.weather[0].description,
      sunrise: new Date(response.current.sunrise * 1000).toISOString(),
      sunset: new Date(response.current.sunset * 1000).toISOString(),
      humidity: response.current.humidity,
      windSpeed: response.current.wind_speed,
      windDirection: this.getWindDirection(response.current.wind_deg),
      precipitation: response.current.rain?.['1h'] || 0,
      uvIndex: response.current.uvi,
      visibility: response.current.visibility,
      pressure: response.current.pressure,
      feelsLike: response.current.feels_like,
    };
  }

  private async fetchAirQualityData(location: LocationData): Promise<{ airQuality: string }> {
    interface AirQualityResponse {
      data: {
        aqi: number;
      };
    }

    const response = await this.airQualityClient.get<AirQualityResponse>('/air-quality', {
      params: {
        lat: location.latitude,
        lon: location.longitude,
        token: this.AIR_QUALITY_API_KEY,
      },
    });

    return {
      airQuality: this.getAirQualityDescription(response.data.aqi),
    };
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