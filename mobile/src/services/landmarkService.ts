import { LocationData } from './locationService';
import { withRetry } from '@utils/async';
import { memoizeAsync } from '@utils/cache';

import { logger } from '@/services/logger';
export interface Landmark {
  name: string;
  distance: number;
  type: string;
  description?: string;
  coordinates: {
    latitude: number;
    longitude: number;
  };
  rating?: number;
  photos?: string[];
  openingHours?: {
    isOpen: boolean;
    periods: string[];
  };
  address?: string;
  website?: string;
  phoneNumber?: string;
  historicalSignificance?: string;
}

class LandmarkService {
  // No API keys needed - all calls go through backend proxy

  getNearbyLandmarks = memoizeAsync(
    async (
      location: LocationData,
      radius: number = 5000, // 5km default radius
      types: string[] = ['tourist_attraction', 'historic', 'museum']
    ): Promise<Landmark[]> => {
      return withRetry(async () => {
        // Fetch landmarks from multiple sources in parallel
        const [googlePlacesResults, mapboxResults] = await Promise.all([
          this.fetchGooglePlacesLandmarks(location, radius, types),
          this.fetchMapboxLandmarks(location, radius),
        ]);

        // Combine and deduplicate results
        const combinedLandmarks = this.combineLandmarkResults(
          googlePlacesResults,
          mapboxResults
        );

        // Enrich with additional details
        const enrichedLandmarks = await this.enrichLandmarkDetails(combinedLandmarks);

        // Sort by distance
        return this.sortLandmarksByDistance(enrichedLandmarks);
      });
    },
    100, // Cache size
    900  // TTL: 15 minutes
  );

  private async fetchGooglePlacesLandmarks(
    location: LocationData,
    radius: number,
    types: string[]
  ): Promise<Landmark[]> {
    // Import the maps proxy service
    const { mapsProxy } = await import('@/services/api/mapsProxy');
    
    // Use backend proxy instead of direct API call
    const response = await mapsProxy.searchPlaces({
      location,
      radius,
      types,
    });

    return response.data.results.map((place: any) => ({
      name: place.name,
      distance: this.calculateDistance(
        location,
        {
          latitude: place.geometry.location.lat,
          longitude: place.geometry.location.lng,
        }
      ),
      type: place.types[0],
      coordinates: {
        latitude: place.geometry.location.lat,
        longitude: place.geometry.location.lng,
      },
      rating: place.rating,
      photos: place.photos?.map((photo: any) => photo.photo_reference),
      // Photo URLs will be constructed by the frontend component using the backend proxy
    }));
  }

  private async fetchMapboxLandmarks(
    location: LocationData,
    radius: number
  ): Promise<Landmark[]> {
    // For now, return empty array - Mapbox integration should go through backend
    // TODO: Add Mapbox proxy endpoint to backend if needed
    return [];
  }

  private async enrichLandmarkDetails(landmarks: Landmark[]): Promise<Landmark[]> {
    return Promise.all(
      landmarks.map(async (landmark) => {
        try {
          // Fetch additional details from Google Places
          const details = await this.fetchPlaceDetails(landmark.name, landmark.coordinates);
          
          return {
            ...landmark,
            description: details.description,
            openingHours: details.openingHours,
            address: details.address,
            website: details.website,
            phoneNumber: details.phoneNumber,
            historicalSignificance: details.historicalSignificance,
          };
        } catch (error) {
          logger.error(`Error enriching landmark details for ${landmark.name}:`, error);
          return landmark;
        }
      })
    );
  }

  private async fetchPlaceDetails(name: string, coordinates: { latitude: number; longitude: number }): Promise<any> {
    // Implement place details fetching
    // This could use Google Places Details API or other sources
    return {};
  }

  private calculateDistance(
    point1: { latitude: number; longitude: number },
    point2: { latitude: number; longitude: number }
  ): number {
    const R = 6371e3; // Earth's radius in meters
    const φ1 = (point1.latitude * Math.PI) / 180;
    const φ2 = (point2.latitude * Math.PI) / 180;
    const Δφ = ((point2.latitude - point1.latitude) * Math.PI) / 180;
    const Δλ = ((point2.longitude - point1.longitude) * Math.PI) / 180;

    const a =
      Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
      Math.cos(φ1) * Math.cos(φ2) * Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

    return R * c; // Distance in meters
  }

  private combineLandmarkResults(...results: Landmark[][]): Landmark[] {
    const landmarkMap = new Map<string, Landmark>();

    results.flat().forEach((landmark) => {
      const key = `${landmark.coordinates.latitude},${landmark.coordinates.longitude}`;
      if (!landmarkMap.has(key) || landmark.description) {
        landmarkMap.set(key, landmark);
      }
    });

    return Array.from(landmarkMap.values());
  }

  private sortLandmarksByDistance(landmarks: Landmark[]): Landmark[] {
    return landmarks.sort((a, b) => a.distance - b.distance);
  }
}

export const landmarkService = new LandmarkService(); 