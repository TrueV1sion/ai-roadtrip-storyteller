import axios from 'axios';
import { LocationData } from './locationService';
import { withRetry } from '@utils/async';
import { memoizeAsync } from '@utils/cache';

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
  private readonly GOOGLE_PLACES_API_KEY = process.env.EXPO_PUBLIC_GOOGLE_PLACES_KEY;
  private readonly MAPBOX_API_KEY = process.env.EXPO_PUBLIC_MAPBOX_KEY;

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
    const response = await axios.get(
      'https://maps.googleapis.com/maps/api/place/nearbysearch/json',
      {
        params: {
          location: `${location.latitude},${location.longitude}`,
          radius,
          types: types.join('|'),
          key: this.GOOGLE_PLACES_API_KEY,
        },
      }
    );

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
      photos: place.photos?.map((photo: any) =>
        `https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference=${photo.photo_reference}&key=${this.GOOGLE_PLACES_API_KEY}`
      ),
    }));
  }

  private async fetchMapboxLandmarks(
    location: LocationData,
    radius: number
  ): Promise<Landmark[]> {
    const response = await axios.get(
      `https://api.mapbox.com/geocoding/v5/mapbox.places/${location.longitude},${location.latitude}.json`,
      {
        params: {
          access_token: this.MAPBOX_API_KEY,
          types: 'poi',
          limit: 10,
          radius,
        },
      }
    );

    return response.data.features.map((feature: any) => ({
      name: feature.text,
      distance: this.calculateDistance(
        location,
        {
          latitude: feature.center[1],
          longitude: feature.center[0],
        }
      ),
      type: feature.properties.category,
      coordinates: {
        latitude: feature.center[1],
        longitude: feature.center[0],
      },
    }));
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
          console.error(`Error enriching landmark details for ${landmark.name}:`, error);
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