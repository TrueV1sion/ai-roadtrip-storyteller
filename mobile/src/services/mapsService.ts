/**
 * Google Maps service that uses backend proxy endpoints
 * to protect API keys from client exposure
 */
import { apiService } from './apiService';

export interface DirectionsOptions {
  origin: string;
  destination: string;
  waypoints?: string[];
  mode?: 'driving' | 'walking' | 'bicycling' | 'transit';
  departureTime?: Date;
  trafficModel?: 'best_guess' | 'optimistic' | 'pessimistic';
}

export interface PlacesSearchOptions {
  location: { latitude: number; longitude: number };
  radius: number;
  type?: string;
  keyword?: string;
}

class MapsService {
  /**
   * Get directions between locations using backend proxy
   */
  async getDirections(options: DirectionsOptions) {
    try {
      const params = new URLSearchParams({
        origin: options.origin,
        destination: options.destination,
        mode: options.mode || 'driving',
        traffic_model: options.trafficModel || 'best_guess',
      });

      if (options.waypoints && options.waypoints.length > 0) {
        params.append('waypoints', options.waypoints.join('|'));
      }

      if (options.departureTime) {
        params.append('departure_time', options.departureTime.toISOString());
      }

      const response = await apiService.get(`/maps/directions?${params}`);
      return response.data;
    } catch (error) {
      console.error('Error getting directions:', error);
      throw error;
    }
  }

  /**
   * Geocode an address to coordinates
   */
  async geocodeAddress(address: string) {
    try {
      const params = new URLSearchParams({ address });
      const response = await apiService.get(`/maps/geocode?${params}`);
      return response.data;
    } catch (error) {
      console.error('Error geocoding address:', error);
      throw error;
    }
  }

  /**
   * Search for places near a location
   */
  async searchPlacesNearby(options: PlacesSearchOptions) {
    try {
      const params = new URLSearchParams({
        location: `${options.location.latitude},${options.location.longitude}`,
        radius: options.radius.toString(),
      });

      if (options.type) {
        params.append('type', options.type);
      }

      if (options.keyword) {
        params.append('keyword', options.keyword);
      }

      const response = await apiService.get(`/maps/places/nearby?${params}`);
      return response.data;
    } catch (error) {
      console.error('Error searching places:', error);
      throw error;
    }
  }

  /**
   * Get details for a specific place
   */
  async getPlaceDetails(placeId: string, fields?: string[]) {
    try {
      const params = new URLSearchParams();
      if (fields && fields.length > 0) {
        params.append('fields', fields.join(','));
      }

      const response = await apiService.get(`/maps/places/details/${placeId}?${params}`);
      return response.data;
    } catch (error) {
      console.error('Error getting place details:', error);
      throw error;
    }
  }

  /**
   * Get static map URL
   */
  async getStaticMapUrl(options: {
    center?: { latitude: number; longitude: number };
    zoom?: number;
    size?: string;
    markers?: string;
    path?: string;
  }) {
    try {
      const params = new URLSearchParams({
        zoom: (options.zoom || 13).toString(),
        size: options.size || '600x400',
      });

      if (options.center) {
        params.append('center', `${options.center.latitude},${options.center.longitude}`);
      }

      if (options.markers) {
        params.append('markers', options.markers);
      }

      if (options.path) {
        params.append('path', options.path);
      }

      const response = await apiService.get(`/maps/staticmap?${params}`);
      return response.data.url;
    } catch (error) {
      console.error('Error getting static map:', error);
      throw error;
    }
  }

  /**
   * Calculate distance between two points (client-side calculation)
   */
  calculateDistance(
    point1: { latitude: number; longitude: number },
    point2: { latitude: number; longitude: number }
  ): number {
    const R = 6371; // Earth's radius in kilometers
    const dLat = this.toRad(point2.latitude - point1.latitude);
    const dLon = this.toRad(point2.longitude - point1.longitude);
    const lat1 = this.toRad(point1.latitude);
    const lat2 = this.toRad(point2.latitude);

    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.sin(dLon / 2) * Math.sin(dLon / 2) * Math.cos(lat1) * Math.cos(lat2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    const distance = R * c;

    return distance;
  }

  private toRad(value: number): number {
    return (value * Math.PI) / 180;
  }
}

export const mapsService = new MapsService();