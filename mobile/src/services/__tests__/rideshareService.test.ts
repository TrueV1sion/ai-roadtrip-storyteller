import { rideshareService } from '../rideshareService';
import { apiManager } from '../api/apiManager';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Location from 'expo-location';

// Mock dependencies
jest.mock('../api/apiManager');
jest.mock('@react-native-async-storage/async-storage');
jest.mock('expo-location');

describe('RideshareService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Driver Mode', () => {
    it('starts driver mode successfully', async () => {
      const mockDriverData = {
        driver_id: 'DRIVER123',
        status: 'active',
        vehicle: {
          make: 'Toyota',
          model: 'Camry',
          year: 2020,
          plate: 'ABC123',
        },
      };

      (apiManager.post as jest.Mock).mockResolvedValue({
        data: mockDriverData,
      });

      const result = await rideshareService.startDriverMode({
        vehicleInfo: {
          make: 'Toyota',
          model: 'Camry',
          year: 2020,
          plate: 'ABC123',
        },
      });

      expect(apiManager.post).toHaveBeenCalledWith('/rideshare/driver/start', {
        vehicle: {
          make: 'Toyota',
          model: 'Camry',
          year: 2020,
          plate: 'ABC123',
        },
      });

      expect(result).toEqual(mockDriverData);
      expect(AsyncStorage.setItem).toHaveBeenCalledWith(
        'driver_mode_active',
        'true'
      );
    });

    it('handles driver mode start failure', async () => {
      (apiManager.post as jest.Mock).mockRejectedValue(
        new Error('Vehicle verification failed')
      );

      await expect(
        rideshareService.startDriverMode({
          vehicleInfo: {
            make: 'Toyota',
            model: 'Camry',
            year: 2020,
            plate: 'ABC123',
          },
        })
      ).rejects.toThrow('Vehicle verification failed');

      expect(AsyncStorage.setItem).not.toHaveBeenCalled();
    });

    it('updates driver location', async () => {
      const mockLocation = {
        latitude: 37.7749,
        longitude: -122.4194,
        heading: 45,
        speed: 30,
      };

      (apiManager.put as jest.Mock).mockResolvedValue({
        data: { success: true },
      });

      await rideshareService.updateDriverLocation(mockLocation);

      expect(apiManager.put).toHaveBeenCalledWith(
        '/rideshare/driver/location',
        mockLocation
      );
    });

    it('gets nearby passengers', async () => {
      const mockPassengers = [
        {
          id: 'PASS1',
          location: { latitude: 37.7749, longitude: -122.4194 },
          destination: 'San Francisco Airport',
          distance: 0.5,
          fare_estimate: 25.50,
        },
        {
          id: 'PASS2',
          location: { latitude: 37.7751, longitude: -122.4180 },
          destination: 'Downtown',
          distance: 0.8,
          fare_estimate: 15.00,
        },
      ];

      (apiManager.get as jest.Mock).mockResolvedValue({
        data: { passengers: mockPassengers },
      });

      const result = await rideshareService.getNearbyPassengers({
        latitude: 37.7749,
        longitude: -122.4194,
        radius: 5,
      });

      expect(apiManager.get).toHaveBeenCalledWith('/rideshare/driver/nearby', {
        params: {
          latitude: 37.7749,
          longitude: -122.4194,
          radius: 5,
        },
      });

      expect(result).toEqual(mockPassengers);
    });

    it('accepts ride request', async () => {
      const mockRide = {
        ride_id: 'RIDE123',
        passenger: {
          id: 'PASS1',
          name: 'John Doe',
          rating: 4.8,
        },
        pickup: { latitude: 37.7749, longitude: -122.4194 },
        destination: { latitude: 37.7739, longitude: -122.4312 },
        fare: 25.50,
        estimated_duration: 15,
      };

      (apiManager.post as jest.Mock).mockResolvedValue({
        data: mockRide,
      });

      const result = await rideshareService.acceptRideRequest('PASS1');

      expect(apiManager.post).toHaveBeenCalledWith(
        '/rideshare/driver/accept',
        { passenger_id: 'PASS1' }
      );

      expect(result).toEqual(mockRide);
    });

    it('completes ride', async () => {
      const mockCompletion = {
        ride_id: 'RIDE123',
        fare: 25.50,
        duration: 18,
        distance: 5.2,
        tip: 5.00,
        total: 30.50,
      };

      (apiManager.post as jest.Mock).mockResolvedValue({
        data: mockCompletion,
      });

      const result = await rideshareService.completeRide('RIDE123');

      expect(apiManager.post).toHaveBeenCalledWith(
        '/rideshare/driver/complete',
        { ride_id: 'RIDE123' }
      );

      expect(result).toEqual(mockCompletion);
    });

    it('ends driver mode', async () => {
      (apiManager.post as jest.Mock).mockResolvedValue({
        data: { success: true },
      });

      await rideshareService.endDriverMode();

      expect(apiManager.post).toHaveBeenCalledWith('/rideshare/driver/end');
      expect(AsyncStorage.removeItem).toHaveBeenCalledWith(
        'driver_mode_active'
      );
    });
  });

  describe('Passenger Mode', () => {
    it('requests a ride', async () => {
      const mockRideRequest = {
        request_id: 'REQ123',
        estimated_wait: 5,
        estimated_fare: 25.50,
        drivers_nearby: 3,
      };

      (apiManager.post as jest.Mock).mockResolvedValue({
        data: mockRideRequest,
      });

      const result = await rideshareService.requestRide({
        pickup: { latitude: 37.7749, longitude: -122.4194 },
        destination: { latitude: 37.7739, longitude: -122.4312 },
        rideType: 'standard',
      });

      expect(apiManager.post).toHaveBeenCalledWith('/rideshare/passenger/request', {
        pickup: { latitude: 37.7749, longitude: -122.4194 },
        destination: { latitude: 37.7739, longitude: -122.4312 },
        ride_type: 'standard',
      });

      expect(result).toEqual(mockRideRequest);
    });

    it('cancels ride request', async () => {
      (apiManager.delete as jest.Mock).mockResolvedValue({
        data: { success: true, cancellation_fee: 0 },
      });

      const result = await rideshareService.cancelRideRequest('REQ123');

      expect(apiManager.delete).toHaveBeenCalledWith(
        '/rideshare/passenger/request/REQ123'
      );

      expect(result).toEqual({ success: true, cancellation_fee: 0 });
    });

    it('tracks ride status', async () => {
      const mockStatus = {
        status: 'driver_en_route',
        driver: {
          name: 'Jane Smith',
          rating: 4.9,
          vehicle: 'Toyota Camry',
          plate: 'XYZ789',
          location: { latitude: 37.7750, longitude: -122.4190 },
        },
        eta: 3,
      };

      (apiManager.get as jest.Mock).mockResolvedValue({
        data: mockStatus,
      });

      const result = await rideshareService.getRideStatus('RIDE123');

      expect(apiManager.get).toHaveBeenCalledWith(
        '/rideshare/passenger/ride/RIDE123/status'
      );

      expect(result).toEqual(mockStatus);
    });

    it('rates driver', async () => {
      (apiManager.post as jest.Mock).mockResolvedValue({
        data: { success: true },
      });

      await rideshareService.rateDriver('RIDE123', {
        rating: 5,
        tip: 5.00,
        comment: 'Great ride!',
      });

      expect(apiManager.post).toHaveBeenCalledWith(
        '/rideshare/passenger/ride/RIDE123/rate',
        {
          rating: 5,
          tip: 5.00,
          comment: 'Great ride!',
        }
      );
    });

    it('gets ride history', async () => {
      const mockHistory = [
        {
          ride_id: 'RIDE1',
          date: '2024-01-15T10:30:00Z',
          driver: 'John Doe',
          fare: 15.50,
          distance: 3.2,
          rating: 5,
        },
        {
          ride_id: 'RIDE2',
          date: '2024-01-14T14:20:00Z',
          driver: 'Jane Smith',
          fare: 22.00,
          distance: 5.8,
          rating: 4,
        },
      ];

      (apiManager.get as jest.Mock).mockResolvedValue({
        data: { rides: mockHistory },
      });

      const result = await rideshareService.getRideHistory();

      expect(apiManager.get).toHaveBeenCalledWith('/rideshare/history');
      expect(result).toEqual(mockHistory);
    });
  });

  describe('Location Services', () => {
    it('starts location tracking', async () => {
      const mockLocationSubscription = { remove: jest.fn() };
      
      (Location.requestForegroundPermissionsAsync as jest.Mock).mockResolvedValue({
        status: 'granted',
      });

      (Location.watchPositionAsync as jest.Mock).mockResolvedValue(
        mockLocationSubscription
      );

      await rideshareService.startLocationTracking((location) => {
        console.log('Location updated:', location);
      });

      expect(Location.requestForegroundPermissionsAsync).toHaveBeenCalled();
      expect(Location.watchPositionAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          accuracy: Location.Accuracy.High,
          timeInterval: 5000,
          distanceInterval: 10,
        }),
        expect.any(Function)
      );
    });

    it('handles location permission denied', async () => {
      (Location.requestForegroundPermissionsAsync as jest.Mock).mockResolvedValue({
        status: 'denied',
      });

      await expect(
        rideshareService.startLocationTracking(() => {})
      ).rejects.toThrow('Location permission denied');

      expect(Location.watchPositionAsync).not.toHaveBeenCalled();
    });

    it('stops location tracking', async () => {
      const mockSubscription = { remove: jest.fn() };
      
      // Start tracking first
      (Location.requestForegroundPermissionsAsync as jest.Mock).mockResolvedValue({
        status: 'granted',
      });
      (Location.watchPositionAsync as jest.Mock).mockResolvedValue(
        mockSubscription
      );

      await rideshareService.startLocationTracking(() => {});
      
      // Stop tracking
      await rideshareService.stopLocationTracking();

      expect(mockSubscription.remove).toHaveBeenCalled();
    });
  });

  describe('Entertainment Features', () => {
    it('gets passenger entertainment options', async () => {
      const mockOptions = {
        stories: [
          { id: 'STORY1', title: 'Local History', duration: 10 },
          { id: 'STORY2', title: 'Fun Facts', duration: 5 },
        ],
        music: {
          connected: true,
          current_playlist: 'Road Trip Mix',
        },
        games: [
          { id: 'GAME1', name: 'Trivia Challenge', players: 1 },
        ],
      };

      (apiManager.get as jest.Mock).mockResolvedValue({
        data: mockOptions,
      });

      const result = await rideshareService.getEntertainmentOptions();

      expect(apiManager.get).toHaveBeenCalledWith(
        '/rideshare/entertainment/options'
      );
      expect(result).toEqual(mockOptions);
    });

    it('starts entertainment content', async () => {
      (apiManager.post as jest.Mock).mockResolvedValue({
        data: { 
          success: true,
          content_id: 'STORY1',
          started_at: '2024-01-15T10:30:00Z',
        },
      });

      const result = await rideshareService.startEntertainment('STORY1');

      expect(apiManager.post).toHaveBeenCalledWith(
        '/rideshare/entertainment/start',
        { content_id: 'STORY1' }
      );

      expect(result.success).toBe(true);
    });
  });

  describe('Driver Analytics', () => {
    it('gets driver earnings', async () => {
      const mockEarnings = {
        today: 125.50,
        this_week: 650.00,
        this_month: 2800.00,
        trips_today: 8,
        average_rating: 4.85,
      };

      (apiManager.get as jest.Mock).mockResolvedValue({
        data: mockEarnings,
      });

      const result = await rideshareService.getDriverEarnings();

      expect(apiManager.get).toHaveBeenCalledWith('/rideshare/driver/earnings');
      expect(result).toEqual(mockEarnings);
    });

    it('gets driver performance metrics', async () => {
      const mockMetrics = {
        acceptance_rate: 92,
        completion_rate: 98,
        average_rating: 4.85,
        total_trips: 156,
        online_hours: 45.5,
      };

      (apiManager.get as jest.Mock).mockResolvedValue({
        data: mockMetrics,
      });

      const result = await rideshareService.getDriverMetrics();

      expect(apiManager.get).toHaveBeenCalledWith('/rideshare/driver/metrics');
      expect(result).toEqual(mockMetrics);
    });
  });

  describe('Safety Features', () => {
    it('shares ride status with contacts', async () => {
      (apiManager.post as jest.Mock).mockResolvedValue({
        data: { success: true, shared_with: 2 },
      });

      const result = await rideshareService.shareRideStatus('RIDE123', [
        { name: 'Mom', phone: '+1234567890' },
        { name: 'Friend', phone: '+0987654321' },
      ]);

      expect(apiManager.post).toHaveBeenCalledWith(
        '/rideshare/safety/share',
        {
          ride_id: 'RIDE123',
          contacts: [
            { name: 'Mom', phone: '+1234567890' },
            { name: 'Friend', phone: '+0987654321' },
          ],
        }
      );

      expect(result.shared_with).toBe(2);
    });

    it('reports safety issue', async () => {
      (apiManager.post as jest.Mock).mockResolvedValue({
        data: { 
          success: true,
          incident_id: 'INC123',
          support_contacted: true,
        },
      });

      const result = await rideshareService.reportSafetyIssue('RIDE123', {
        type: 'unsafe_driving',
        description: 'Driver was speeding',
      });

      expect(apiManager.post).toHaveBeenCalledWith(
        '/rideshare/safety/report',
        {
          ride_id: 'RIDE123',
          issue: {
            type: 'unsafe_driving',
            description: 'Driver was speeding',
          },
        }
      );

      expect(result.incident_id).toBe('INC123');
    });
  });
});