import { useState, useEffect, useCallback } from 'react';
import * as Location from 'expo-location';
import { Alert } from 'react-native';

import { logger } from '@/services/logger';
interface LocationData {
  lat: number;
  lng: number;
  name?: string;
  address?: string;
  timestamp: number;
}

interface UseLocationResult {
  currentLocation: LocationData | null;
  loading: boolean;
  error: string | null;
  requestPermission: () => Promise<boolean>;
  refreshLocation: () => Promise<void>;
  watchLocation: (callback: (location: LocationData) => void) => () => void;
}

export const useLocation = (): UseLocationResult => {
  const [currentLocation, setCurrentLocation] = useState<LocationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const requestPermission = useCallback(async (): Promise<boolean> => {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      
      if (status !== 'granted') {
        setError('Permission to access location was denied');
        Alert.alert(
          'Location Permission Required',
          'This app needs location access to provide location-based games and stories.',
          [{ text: 'OK' }]
        );
        return false;
      }
      
      return true;
    } catch (err) {
      setError('Failed to request location permission');
      logger.error('Permission error:', err);
      return false;
    }
  }, []);

  const getLocationDetails = useCallback(async (coords: Location.LocationObject) => {
    try {
      const reverseGeocode = await Location.reverseGeocodeAsync({
        latitude: coords.coords.latitude,
        longitude: coords.coords.longitude,
      });

      if (reverseGeocode.length > 0) {
        const place = reverseGeocode[0];
        return {
          name: place.name || place.street || 'Unknown Location',
          address: [
            place.street,
            place.city,
            place.region,
            place.postalCode,
          ].filter(Boolean).join(', '),
        };
      }
    } catch (err) {
      logger.error('Reverse geocoding error:', err);
    }
    return { name: 'Unknown Location', address: '' };
  }, []);

  const refreshLocation = useCallback(async () => {
    setLoading(true);
    setError(null);

    const hasPermission = await requestPermission();
    if (!hasPermission) {
      setLoading(false);
      return;
    }

    try {
      const location = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      });

      const details = await getLocationDetails(location);

      const locationData: LocationData = {
        lat: location.coords.latitude,
        lng: location.coords.longitude,
        name: details.name,
        address: details.address,
        timestamp: location.timestamp,
      };

      setCurrentLocation(locationData);
    } catch (err) {
      setError('Failed to get current location');
      logger.error('Location error:', err);
    } finally {
      setLoading(false);
    }
  }, [requestPermission, getLocationDetails]);

  const watchLocation = useCallback((callback: (location: LocationData) => void) => {
    let subscription: Location.LocationSubscription | null = null;

    const startWatching = async () => {
      const hasPermission = await requestPermission();
      if (!hasPermission) return;

      subscription = await Location.watchPositionAsync(
        {
          accuracy: Location.Accuracy.Balanced,
          timeInterval: 5000, // Update every 5 seconds
          distanceInterval: 10, // Or when moved 10 meters
        },
        async (location) => {
          const details = await getLocationDetails(location);
          
          const locationData: LocationData = {
            lat: location.coords.latitude,
            lng: location.coords.longitude,
            name: details.name,
            address: details.address,
            timestamp: location.timestamp,
          };

          setCurrentLocation(locationData);
          callback(locationData);
        }
      );
    };

    startWatching();

    // Return cleanup function
    return () => {
      if (subscription) {
        subscription.remove();
      }
    };
  }, [requestPermission, getLocationDetails]);

  useEffect(() => {
    refreshLocation();
  }, []);

  return {
    currentLocation,
    loading,
    error,
    requestPermission,
    refreshLocation,
    watchLocation,
  };
};