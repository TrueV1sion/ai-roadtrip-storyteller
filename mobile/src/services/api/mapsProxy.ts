/**
 * Maps Proxy Service
 * Routes all map-related API calls through backend to protect API keys
 * 
 * Security: All API keys are stored on backend only
 */

import { ApiClient } from './ApiClient';
import { APIProxyEndpoints } from '@/config/secure-config';
import { logger } from '@/services/logger';

interface LocationData {
  latitude: number;
  longitude: number;
}

interface PlaceSearchParams {
  location: LocationData;
  radius?: number;
  types?: string[];
  keyword?: string;
}

interface DirectionsParams {
  origin: LocationData;
  destination: LocationData;
  waypoints?: LocationData[];
  mode?: 'driving' | 'walking' | 'bicycling' | 'transit';
  alternatives?: boolean;
}

interface GeocodeParams {
  address?: string;
  location?: LocationData;
  placeId?: string;
}

interface TileRequestParams {
  z: number;
  x: number;
  y: number;
  style?: string;
  provider?: 'maptiler' | 'mapbox';
}

class MapsProxyService {
  private apiClient: ApiClient;

  constructor() {
    this.apiClient = new ApiClient({
      enableTokenRefresh: true,
      enableRetry: true,
    });
  }

  /**
   * Search for places near a location
   * Backend handles Google Places API key
   */
  async searchPlaces(params: PlaceSearchParams): Promise<any> {
    try {
      const response = await this.apiClient.post(APIProxyEndpoints.MAPS.PLACES, {
        location: `${params.location.latitude},${params.location.longitude}`,
        radius: params.radius || 5000,
        types: params.types?.join('|') || 'tourist_attraction|historic|museum',
        keyword: params.keyword,
      });

      return response.data;
    } catch (error) {
      logger.error('Failed to search places', error as Error);
      throw error;
    }
  }

  /**
   * Get directions between points
   * Backend handles Google Directions API key
   */
  async getDirections(params: DirectionsParams): Promise<any> {
    try {
      const response = await this.apiClient.post(APIProxyEndpoints.MAPS.DIRECTIONS, {
        origin: `${params.origin.latitude},${params.origin.longitude}`,
        destination: `${params.destination.latitude},${params.destination.longitude}`,
        waypoints: params.waypoints?.map(w => `${w.latitude},${w.longitude}`).join('|'),
        mode: params.mode || 'driving',
        alternatives: params.alternatives !== false,
      });

      return response.data;
    } catch (error) {
      logger.error('Failed to get directions', error as Error);
      throw error;
    }
  }

  /**
   * Geocode an address or reverse geocode coordinates
   * Backend handles Google Geocoding API key
   */
  async geocode(params: GeocodeParams): Promise<any> {
    try {
      const response = await this.apiClient.post(APIProxyEndpoints.MAPS.GEOCODE, {
        address: params.address,
        latlng: params.location ? `${params.location.latitude},${params.location.longitude}` : undefined,
        place_id: params.placeId,
      });

      return response.data;
    } catch (error) {
      logger.error('Failed to geocode', error as Error);
      throw error;
    }
  }

  /**
   * Get distance matrix between multiple points
   * Backend handles Google Distance Matrix API key
   */
  async getDistanceMatrix(origins: LocationData[], destinations: LocationData[]): Promise<any> {
    try {
      const response = await this.apiClient.post(APIProxyEndpoints.MAPS.DISTANCE_MATRIX, {
        origins: origins.map(o => `${o.latitude},${o.longitude}`).join('|'),
        destinations: destinations.map(d => `${d.latitude},${d.longitude}`).join('|'),
      });

      return response.data;
    } catch (error) {
      logger.error('Failed to get distance matrix', error as Error);
      throw error;
    }
  }

  /**
   * Download map tile through backend proxy
   * Backend handles MapTiler/Mapbox API keys
   */
  async downloadMapTile(params: TileRequestParams): Promise<ArrayBuffer> {
    try {
      const response = await this.apiClient.get('/api/proxy/maps/tile', {
        params: {
          z: params.z,
          x: params.x,
          y: params.y,
          style: params.style || 'v3',
          provider: params.provider || 'maptiler',
        },
        responseType: 'arraybuffer',
      });

      return response.data;
    } catch (error) {
      logger.error('Failed to download map tile', error as Error);
      throw error;
    }
  }

  /**
   * Get weather for a location
   * Backend handles OpenWeather API key
   */
  async getWeather(location: LocationData): Promise<any> {
    try {
      const response = await this.apiClient.get(APIProxyEndpoints.WEATHER.CURRENT, {
        params: {
          lat: location.latitude,
          lon: location.longitude,
        },
      });

      return response.data;
    } catch (error) {
      logger.error('Failed to get weather', error as Error);
      throw error;
    }
  }

  /**
   * Get weather forecast
   * Backend handles OpenWeather API key
   */
  async getWeatherForecast(location: LocationData, days: number = 5): Promise<any> {
    try {
      const response = await this.apiClient.get(APIProxyEndpoints.WEATHER.FORECAST, {
        params: {
          lat: location.latitude,
          lon: location.longitude,
          days,
        },
      });

      return response.data;
    } catch (error) {
      logger.error('Failed to get weather forecast', error as Error);
      throw error;
    }
  }
}

export const mapsProxy = new MapsProxyService();
export default mapsProxy;