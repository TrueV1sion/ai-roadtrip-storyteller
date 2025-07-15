import * as Location from 'expo-location';
import { locationService } from '../locationService';

// Mock expo-location
jest.mock('expo-location', () => ({
  requestForegroundPermissionsAsync: jest.fn(),
  requestBackgroundPermissionsAsync: jest.fn(),
  getCurrentPositionAsync: jest.fn(),
  watchPositionAsync: jest.fn(),
  setGoogleApiKey: jest.fn(),
}));

describe('LocationService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('requestPermissions', () => {
    test('returns true when both permissions are granted', async () => {
      (Location.requestForegroundPermissionsAsync as jest.Mock).mockResolvedValue({ status: 'granted' });
      (Location.requestBackgroundPermissionsAsync as jest.Mock).mockResolvedValue({ status: 'granted' });

      const result = await locationService.requestPermissions();
      expect(result).toBe(true);
    });

    test('returns false when foreground permission is denied', async () => {
      (Location.requestForegroundPermissionsAsync as jest.Mock).mockResolvedValue({ status: 'denied' });

      const result = await locationService.requestPermissions();
      expect(result).toBe(false);
    });

    test('returns false when background permission is denied', async () => {
      (Location.requestForegroundPermissionsAsync as jest.Mock).mockResolvedValue({ status: 'granted' });
      (Location.requestBackgroundPermissionsAsync as jest.Mock).mockResolvedValue({ status: 'denied' });

      const result = await locationService.requestPermissions();
      expect(result).toBe(false);
    });

    test('handles errors gracefully', async () => {
      (Location.requestForegroundPermissionsAsync as jest.Mock).mockRejectedValue(new Error('Permission error'));

      const result = await locationService.requestPermissions();
      expect(result).toBe(false);
    });
  });

  describe('startTracking', () => {
    const mockLocation = {
      coords: {
        latitude: 40.7128,
        longitude: -74.0060,
        heading: 90,
        speed: 5,
        altitude: 10,
        accuracy: 5,
      },
    };

    beforeEach(() => {
      (Location.requestForegroundPermissionsAsync as jest.Mock).mockResolvedValue({ status: 'granted' });
      (Location.requestBackgroundPermissionsAsync as jest.Mock).mockResolvedValue({ status: 'granted' });
      (Location.watchPositionAsync as jest.Mock).mockImplementation((options, callback) => {
        callback(mockLocation);
        return { remove: jest.fn() };
      });
    });

    test('starts tracking location successfully', async () => {
      const listener = jest.fn();
      locationService.addLocationListener(listener);

      await locationService.startTracking();

      expect(Location.setGoogleApiKey).toHaveBeenCalled();
      expect(Location.watchPositionAsync).toHaveBeenCalled();
      expect(listener).toHaveBeenCalledWith({
        latitude: mockLocation.coords.latitude,
        longitude: mockLocation.coords.longitude,
        heading: mockLocation.coords.heading,
        speed: mockLocation.coords.speed,
        altitude: mockLocation.coords.altitude,
        accuracy: mockLocation.coords.accuracy,
      });
    });

    test('throws error when permissions are denied', async () => {
      (Location.requestForegroundPermissionsAsync as jest.Mock).mockResolvedValue({ status: 'denied' });

      await expect(locationService.startTracking()).rejects.toThrow('Location permission not granted');
    });

    test('handles multiple listeners', async () => {
      const listener1 = jest.fn();
      const listener2 = jest.fn();

      locationService.addLocationListener(listener1);
      locationService.addLocationListener(listener2);

      await locationService.startTracking();

      expect(listener1).toHaveBeenCalled();
      expect(listener2).toHaveBeenCalled();
    });
  });

  describe('getCurrentLocation', () => {
    test('returns current location successfully', async () => {
      const mockLocation = {
        coords: {
          latitude: 40.7128,
          longitude: -74.0060,
          heading: 90,
          speed: 5,
          altitude: 10,
          accuracy: 5,
        },
      };

      (Location.getCurrentPositionAsync as jest.Mock).mockResolvedValue(mockLocation);

      const result = await locationService.getCurrentLocation();

      expect(result).toEqual({
        latitude: mockLocation.coords.latitude,
        longitude: mockLocation.coords.longitude,
        heading: mockLocation.coords.heading,
        speed: mockLocation.coords.speed,
        altitude: mockLocation.coords.altitude,
        accuracy: mockLocation.coords.accuracy,
      });
    });

    test('handles errors gracefully', async () => {
      (Location.getCurrentPositionAsync as jest.Mock).mockRejectedValue(new Error('Location error'));

      await expect(locationService.getCurrentLocation()).rejects.toThrow('Location error');
    });
  });

  describe('distance calculations', () => {
    test('calculates distance between two points correctly', () => {
      // New York to Los Angeles (approximate coordinates)
      const distance = locationService.calculateDistance(
        40.7128, // NY latitude
        -74.0060, // NY longitude
        34.0522, // LA latitude
        -118.2437 // LA longitude
      );

      // Approximate distance should be around 3935 km (or 3,935,000 meters)
      expect(Math.round(distance / 1000)).toBeCloseTo(3935, -2); // Within 100km
    });

    test('determines if location is near another location', () => {
      const location1 = { latitude: 40.7128, longitude: -74.0060 };
      const location2 = { latitude: 40.7129, longitude: -74.0061 }; // Very close
      const location3 = { latitude: 41.7128, longitude: -75.0060 }; // Far

      expect(locationService.isNearLocation(location1, location2, 1000)).toBe(true);
      expect(locationService.isNearLocation(location1, location3, 1000)).toBe(false);
    });
  });

  describe('listener management', () => {
    test('manages listeners correctly', async () => {
      const listener1 = jest.fn();
      const listener2 = jest.fn();

      locationService.addLocationListener(listener1);
      locationService.addLocationListener(listener2);
      locationService.removeLocationListener(listener1);

      const mockLocation = {
        coords: {
          latitude: 40.7128,
          longitude: -74.0060,
          heading: 90,
          speed: 5,
          altitude: 10,
          accuracy: 5,
        },
      };

      (Location.watchPositionAsync as jest.Mock).mockImplementation((options, callback) => {
        callback(mockLocation);
        return { remove: jest.fn() };
      });

      await locationService.startTracking();

      expect(listener1).not.toHaveBeenCalled();
      expect(listener2).toHaveBeenCalled();
    });
  });
}); 