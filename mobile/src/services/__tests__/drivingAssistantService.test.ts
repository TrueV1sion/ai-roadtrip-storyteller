import { drivingAssistantService } from '../drivingAssistantService';
import { locationService } from '../locationService';
import { weatherService } from '../weatherService';
import { ApiClient } from '../api/ApiClient';

// Mock dependencies
jest.mock('../locationService');
jest.mock('../weatherService');
jest.mock('../api/ApiClient');

const mockLocationService = locationService as jest.Mocked<typeof locationService>;
const mockWeatherService = weatherService as jest.Mocked<typeof weatherService>;
const mockApiClient = ApiClient as jest.Mocked<typeof ApiClient>;

describe('DrivingAssistantService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Fuel/Charging Recommendations', () => {
    it('recommends fuel stops based on current level', async () => {
      mockLocationService.getCurrentLocation.mockResolvedValue({
        lat: 37.7749,
        lng: -122.4194,
      });

      mockApiClient.get.mockResolvedValue({
        stations: [
          {
            id: '1',
            name: 'Shell Station',
            distance: 2.5,
            price: 4.99,
            brand: 'Shell',
            address: '123 Main St',
          },
          {
            id: '2',
            name: 'Chevron',
            distance: 3.0,
            price: 5.09,
            brand: 'Chevron',
            address: '456 Oak Ave',
          },
        ],
      });

      const recommendations = await drivingAssistantService.getFuelRecommendations({
        fuelLevel: 15, // 15% remaining
        fuelType: 'regular',
        tankCapacity: 15,
        mpg: 30,
      });

      expect(recommendations).toHaveLength(2);
      expect(recommendations[0].urgency).toBe('high');
      expect(mockApiClient.get).toHaveBeenCalledWith(
        '/api/driving-assistant/fuel-stations',
        expect.any(Object)
      );
    });

    it('recommends EV charging stations', async () => {
      mockLocationService.getCurrentLocation.mockResolvedValue({
        lat: 37.7749,
        lng: -122.4194,
      });

      mockApiClient.get.mockResolvedValue({
        stations: [
          {
            id: '1',
            name: 'Tesla Supercharger',
            distance: 5.0,
            chargerType: 'DC Fast',
            power: 250,
            available: 4,
            total: 8,
            network: 'Tesla',
          },
        ],
      });

      const recommendations = await drivingAssistantService.getChargingRecommendations({
        batteryLevel: 20, // 20% remaining
        vehicleType: 'Tesla Model 3',
        range: 50, // 50 miles remaining
      });

      expect(recommendations).toHaveLength(1);
      expect(recommendations[0].chargerType).toBe('DC Fast');
    });
  });

  describe('Rest Break Suggestions', () => {
    it('suggests rest breaks after continuous driving', async () => {
      const startTime = new Date();
      startTime.setHours(startTime.getHours() - 2); // 2 hours ago

      const suggestions = await drivingAssistantService.getRestBreakSuggestions({
        drivingStartTime: startTime,
        lastBreakTime: null,
        currentSpeed: 65,
      });

      expect(suggestions).toHaveLength(1);
      expect(suggestions[0].reason).toContain('2 hours');
      expect(suggestions[0].urgency).toBe('medium');
    });

    it('increases urgency after 4 hours of driving', async () => {
      const startTime = new Date();
      startTime.setHours(startTime.getHours() - 4.5); // 4.5 hours ago

      const suggestions = await drivingAssistantService.getRestBreakSuggestions({
        drivingStartTime: startTime,
        lastBreakTime: null,
        currentSpeed: 70,
      });

      expect(suggestions[0].urgency).toBe('high');
    });

    it('suggests scenic rest stops when available', async () => {
      mockApiClient.get.mockResolvedValue({
        restStops: [
          {
            id: '1',
            name: 'Scenic Overlook',
            type: 'scenic',
            amenities: ['restrooms', 'picnic area', 'viewpoint'],
            distance: 10,
            rating: 4.5,
          },
        ],
      });

      const suggestions = await drivingAssistantService.getRestBreakSuggestions({
        drivingStartTime: new Date(),
        preferScenic: true,
      });

      expect(suggestions[0].location.type).toBe('scenic');
    });
  });

  describe('Weather-Based Alerts', () => {
    it('alerts for severe weather conditions', async () => {
      mockWeatherService.getCurrentWeather.mockResolvedValue({
        condition: 'heavy rain',
        visibility: 0.5, // miles
        windSpeed: 25,
        temperature: 45,
      });

      mockWeatherService.getWeatherAlerts.mockResolvedValue([
        {
          type: 'flood warning',
          severity: 'severe',
          description: 'Flash flood warning in effect',
          startTime: new Date(),
          endTime: new Date(Date.now() + 3600000),
        },
      ]);

      const alerts = await drivingAssistantService.getWeatherAlerts({
        lat: 37.7749,
        lng: -122.4194,
      });

      expect(alerts).toHaveLength(2); // Weather condition + alert
      expect(alerts[0].recommendation).toContain('reduce speed');
      expect(alerts[1].severity).toBe('severe');
    });

    it('provides ice warning for freezing conditions', async () => {
      mockWeatherService.getCurrentWeather.mockResolvedValue({
        condition: 'rain',
        temperature: 31, // Just below freezing
        humidity: 85,
      });

      const alerts = await drivingAssistantService.getWeatherAlerts({
        lat: 45.5152,
        lng: -122.6784,
      });

      expect(alerts[0].type).toBe('ice warning');
      expect(alerts[0].recommendation).toContain('bridges and overpasses');
    });
  });

  describe('Traffic Analysis', () => {
    it('analyzes traffic patterns and suggests alternatives', async () => {
      mockApiClient.get.mockResolvedValue({
        currentRoute: {
          trafficDelay: 25, // minutes
          congestionLevel: 'heavy',
          incidents: [
            {
              type: 'accident',
              location: 'I-5 at Exit 42',
              delay: 15,
            },
          ],
        },
        alternatives: [
          {
            routeName: 'US-101',
            timeSavings: 10,
            additionalDistance: 5,
          },
        ],
      });

      const analysis = await drivingAssistantService.analyzeTraffic({
        currentRoute: 'I-5',
        destination: { lat: 37.7749, lng: -122.4194 },
      });

      expect(analysis.recommendation).toBe('consider alternative');
      expect(analysis.alternatives[0].timeSavings).toBe(10);
    });
  });

  describe('Parking Assistance', () => {
    it('finds nearby parking with availability', async () => {
      mockApiClient.get.mockResolvedValue({
        parkingSpots: [
          {
            id: '1',
            name: 'Downtown Garage',
            distance: 0.2,
            available: 45,
            total: 200,
            price: { hourly: 5, daily: 25 },
            type: 'garage',
          },
          {
            id: '2',
            name: 'Street Parking',
            distance: 0.1,
            available: 3,
            total: 10,
            price: { hourly: 2 },
            type: 'street',
          },
        ],
      });

      const parking = await drivingAssistantService.findParking({
        destination: { lat: 37.7749, lng: -122.4194 },
        preferredType: 'garage',
        maxPrice: 30,
      });

      expect(parking).toHaveLength(2);
      expect(parking[0].name).toBe('Downtown Garage');
    });

    it('predicts parking availability based on time', async () => {
      const futureTime = new Date();
      futureTime.setHours(futureTime.getHours() + 2);

      mockApiClient.get.mockResolvedValue({
        predictions: [
          {
            time: futureTime.toISOString(),
            availabilityPercentage: 15,
            confidence: 0.85,
          },
        ],
      });

      const prediction = await drivingAssistantService.predictParkingAvailability({
        location: { lat: 37.7749, lng: -122.4194 },
        arrivalTime: futureTime,
      });

      expect(prediction.availabilityPercentage).toBe(15);
      expect(prediction.recommendation).toContain('limited availability');
    });
  });

  describe('Speed Management', () => {
    it('warns about speed limit changes', async () => {
      const speedData = {
        currentSpeed: 70,
        speedLimit: 65,
        upcomingSpeedLimit: 45,
        distanceToChange: 0.5, // miles
      };

      const warning = await drivingAssistantService.checkSpeedCompliance(speedData);

      expect(warning.type).toBe('speed_reduction_ahead');
      expect(warning.message).toContain('45 mph');
    });

    it('alerts for excessive speed', async () => {
      const speedData = {
        currentSpeed: 85,
        speedLimit: 65,
      };

      const warning = await drivingAssistantService.checkSpeedCompliance(speedData);

      expect(warning.type).toBe('excessive_speed');
      expect(warning.severity).toBe('high');
    });
  });

  describe('Maintenance Reminders', () => {
    it('reminds about upcoming maintenance', async () => {
      const vehicleData = {
        mileage: 29500,
        lastOilChange: 26000,
        lastTireRotation: 20000,
      };

      const reminders = await drivingAssistantService.getMaintenanceReminders(vehicleData);

      expect(reminders).toContainEqual(
        expect.objectContaining({
          type: 'oil_change',
          urgency: 'upcoming',
        })
      );
      expect(reminders).toContainEqual(
        expect.objectContaining({
          type: 'tire_rotation',
          urgency: 'overdue',
        })
      );
    });
  });

  describe('Emergency Assistance', () => {
    it('provides emergency contact information', async () => {
      mockLocationService.getCurrentLocation.mockResolvedValue({
        lat: 37.7749,
        lng: -122.4194,
      });

      const emergency = await drivingAssistantService.getEmergencyAssistance({
        type: 'breakdown',
        location: { lat: 37.7749, lng: -122.4194 },
      });

      expect(emergency.contacts).toContainEqual(
        expect.objectContaining({
          service: 'roadside_assistance',
        })
      );
      expect(emergency.nearestServices).toBeDefined();
    });
  });
});