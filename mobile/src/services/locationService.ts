/**
 * Location service for handling real device GPS tracking.
 * Uses expo-location for native GPS functionality.
 */
import * as Location from 'expo-location';
import { Alert } from 'react-native';

import { logger } from '@/services/logger';
// Define our internal LocationData interface
export interface LocationData {
  latitude: number;
  longitude: number;
  altitude?: number | null;
  accuracy?: number | null;
  altitudeAccuracy?: number | null;
  heading?: number | null;
  speed?: number | null;
  timestamp?: number;
}

// Define location options
export interface ExpoLocationOptions {
  accuracy?: Location.LocationAccuracy;
  timeInterval?: number;
  distanceInterval?: number;
  mayShowUserSettingsDialog?: boolean;
  timeout?: number;
  maximumAge?: number;
}

class LocationService {
  private initialized: boolean = false;
  private locationPermissionGranted: boolean = false;
  private watchSubscription: Location.LocationSubscription | null = null;
  private currentLocation: LocationData | null = null;
  private locationUpdateCallbacks: Array<(location: LocationData) => void> = [];

  /**
   * Initialize the location service and request permissions.
   */
  async initialize(): Promise<boolean> {
    if (this.initialized) {
      return this.locationPermissionGranted;
    }

    logger.debug('Initializing Location Service...');
    try {
      // Request foreground location permission
      const { status } = await Location.requestForegroundPermissionsAsync();
      
      if (status !== 'granted') {
        logger.warn('Location permission denied');
        Alert.alert(
          'Location Permission Required',
          'This app needs location access to provide navigation and location-based stories.',
          [{ text: 'OK' }]
        );
        this.locationPermissionGranted = false;
        this.initialized = true;
        return false;
      }

      logger.debug('Location permission granted');
      this.locationPermissionGranted = true;
      
      // Get initial location
      await this.updateCurrentLocation();
      
      this.initialized = true;
      return true;
    } catch (error: any) {
      logger.error('Error initializing location service:', error);
      this.initialized = true;
      this.locationPermissionGranted = false;
      return false;
    }
  }

  /**
   * Helper to get and store the current location.
   */
  private async updateCurrentLocation(options?: ExpoLocationOptions): Promise<void> {
    try {
      const locationOptions: Location.LocationOptions = {
        accuracy: options?.accuracy || Location.LocationAccuracy.High,
        timeout: options?.timeout || 5000,
        maximumAge: options?.maximumAge || 1000,
      };

      const location = await Location.getCurrentPositionAsync(locationOptions);
      this.currentLocation = this.mapExpoLocation(location);
      logger.debug('Updated current location:', this.currentLocation?.latitude, this.currentLocation?.longitude);
    } catch (error) {
      logger.error('Error updating current location:', error);
    }
  }

  /**
   * Get the current location.
   */
  async getCurrentLocation(options?: ExpoLocationOptions): Promise<LocationData | null> {
    if (!this.initialized) {
      await this.initialize();
    }

    if (!this.locationPermissionGranted) {
      logger.warn('Location permission not granted');
      return null;
    }

    try {
      const locationOptions: Location.LocationOptions = {
        accuracy: options?.accuracy || Location.LocationAccuracy.High,
        timeout: options?.timeout || 5000,
        maximumAge: options?.maximumAge || 1000,
      };

      const location = await Location.getCurrentPositionAsync(locationOptions);
      this.currentLocation = this.mapExpoLocation(location);
      return this.currentLocation;
    } catch (error) {
      logger.error('Error getting current location:', error);
      return null;
    }
  }

  /**
   * Watch for location changes.
   */
  async watchLocation(
    callback: (location: LocationData) => void,
    options?: ExpoLocationOptions
  ): Promise<number> {
    if (!this.initialized) {
      await this.initialize();
    }
    
    if (!this.locationPermissionGranted) {
      logger.warn('Cannot watch location: permission not granted.');
      return -1;
    }

    const callbackIndex = this.locationUpdateCallbacks.push(callback) - 1;

    // If this is the first callback, start watching location
    if (this.locationUpdateCallbacks.filter(cb => cb !== null).length === 1 && !this.watchSubscription) {
      logger.debug('Starting location watch...');
      
      const watchOptions: Location.LocationTaskOptions = {
        accuracy: options?.accuracy || Location.LocationAccuracy.High,
        timeInterval: options?.timeInterval || 5000,
        distanceInterval: options?.distanceInterval || 10,
        mayShowUserSettingsDialog: options?.mayShowUserSettingsDialog ?? true,
      };

      this.watchSubscription = await Location.watchPositionAsync(
        watchOptions,
        (location) => {
          const mappedLocation = this.mapExpoLocation(location);
          this.currentLocation = mappedLocation;

          // Call all registered callbacks
          this.locationUpdateCallbacks.forEach((cb, index) => {
            if (cb) {
              try {
                cb(mappedLocation);
              } catch (error) {
                logger.error(`Error in location update callback ${index}:`, error);
              }
            }
          });
        }
      );
      
      logger.debug('Location watch started.');
    }

    return callbackIndex;
  }

  /**
   * Stop watching for location changes.
   */
  clearWatch(watchId: number): void {
    if (watchId >= 0 && watchId < this.locationUpdateCallbacks.length) {
      this.locationUpdateCallbacks[watchId] = null as any;
      logger.debug(`Cleared location watch for ID: ${watchId}`);

      const activeCallbacks = this.locationUpdateCallbacks.filter(cb => cb !== null);

      // If no more active callbacks, stop the location watch
      if (activeCallbacks.length === 0 && this.watchSubscription) {
        logger.debug('Stopping location watch...');
        this.watchSubscription.remove();
        this.watchSubscription = null;
        this.locationUpdateCallbacks = [];
      }
    } else {
      logger.warn(`Attempted to clear invalid watchId: ${watchId}`);
    }
  }

  /**
   * Maps the expo-location object to our LocationData interface.
   */
  private mapExpoLocation(location: Location.LocationObject): LocationData {
    return {
      latitude: location.coords.latitude,
      longitude: location.coords.longitude,
      altitude: location.coords.altitude,
      accuracy: location.coords.accuracy,
      altitudeAccuracy: location.coords.altitudeAccuracy,
      heading: location.coords.heading,
      speed: location.coords.speed,
      timestamp: location.timestamp,
    };
  }

  /**
   * Calculate distance between two locations in meters.
   */
  calculateDistance(
    lat1: number,
    lon1: number,
    lat2: number,
    lon2: number
  ): number {
    const R = 6371e3; // Earth radius in meters
    const φ1 = lat1 * Math.PI / 180;
    const φ2 = lat2 * Math.PI / 180;
    const Δφ = (lat2 - lat1) * Math.PI / 180;
    const Δλ = (lon2 - lon1) * Math.PI / 180;

    const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
              Math.cos(φ1) * Math.cos(φ2) *
              Math.sin(Δλ/2) * Math.sin(Δλ/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));

    return R * c;
  }

  /**
   * Get a formatted address for a location using reverse geocoding.
   */
  async getAddressForLocation(location: LocationData): Promise<string | null> {
    try {
      const [result] = await Location.reverseGeocodeAsync({
        latitude: location.latitude,
        longitude: location.longitude,
      });

      if (result) {
        const addressParts = [];
        if (result.name) addressParts.push(result.name);
        if (result.street) addressParts.push(result.street);
        if (result.city) addressParts.push(result.city);
        if (result.region) addressParts.push(result.region);
        if (result.country) addressParts.push(result.country);
        
        return addressParts.join(', ');
      }
      
      return null;
    } catch (error) {
      logger.error('Error getting address for location:', error);
      return null;
    }
  }

  /**
   * Check if location permission has been granted.
   */
  public hasPermission(): boolean {
    return this.locationPermissionGranted;
  }

  /**
   * Get the last known location (cached).
   */
  public getLastKnownLocation(): LocationData | null {
    return this.currentLocation;
  }

  /**
   * Request background location permission (for future use).
   */
  async requestBackgroundPermission(): Promise<boolean> {
    try {
      const { status } = await Location.requestBackgroundPermissionsAsync();
      return status === 'granted';
    } catch (error) {
      logger.error('Error requesting background location permission:', error);
      return false;
    }
  }
}

// Singleton instance
export const locationService = new LocationService();
export default locationService;