import { ApiClient } from './api/ApiClient';
import { logger } from '@/services/logger';
import {
  RestStopType,
  FuelStationType,
  DrivingStatusType,
  TrafficInfoType,
  RestBreakRequestType,
  FuelStationRequestType,
  TrafficInfoRequestType,
  DrivingStatusRequestType
} from '../types/driving';

class DrivingAssistantService {
  /**
   * Get recommended rest breaks based on route and driving time
   */
  async getRestBreaks(request: RestBreakRequestType): Promise<RestStopType[]> {
    try {
      return await ApiClient.post<RestStopType[]>('/driving-assistant/rest-breaks', request);
    } catch (error) {
      logger.error('Error getting rest breaks:', error);
      throw error;
    }
  }

  /**
   * Get nearby fuel stations, prioritizing if fuel is low
   */
  async getFuelStations(request: FuelStationRequestType): Promise<FuelStationType[]> {
    try {
      return await ApiClient.post<FuelStationType[]>('/driving-assistant/fuel-stations', request);
    } catch (error) {
      logger.error('Error getting fuel stations:', error);
      throw error;
    }
  }

  /**
   * Get traffic information for the current route
   */
  async getTrafficInfo(request: TrafficInfoRequestType): Promise<TrafficInfoType> {
    try {
      return await ApiClient.post<TrafficInfoType>('/driving-assistant/traffic-info', request);
    } catch (error) {
      logger.error('Error getting traffic information:', error);
      throw error;
    }
  }

  /**
   * Get the current driving status and recommendations
   */
  async getDrivingStatus(request: DrivingStatusRequestType): Promise<DrivingStatusType> {
    try {
      return await ApiClient.post<DrivingStatusType>('/driving-assistant/driving-status', request);
    } catch (error) {
      logger.error('Error getting driving status:', error);
      throw error;
    }
  }

  /**
   * Estimate fuel efficiency based on driving conditions
   */
  async estimateFuelEfficiency(
    vehicleType: string,
    speed: number,
    elevationChange: number = 0,
    hasClimateControl: boolean = false
  ): Promise<{ efficiency: number; units: string }> {
    try {
      const response = await ApiClient.get<{ efficiency: number; units: string }>(
        `/driving-assistant/fuel-efficiency?vehicle_type=${vehicleType}&speed=${speed}&elevation_change=${elevationChange}&has_climate_control=${hasClimateControl}`
      );
      return response;
    } catch (error) {
      logger.error('Error estimating fuel efficiency:', error);
      throw error;
    }
  }

  /**
   * Check if a rest break is due based on driving time
   */
  isRestBreakDue(drivingTimeMinutes: number, restIntervalMinutes: number = 120): boolean {
    return drivingTimeMinutes >= restIntervalMinutes;
  }

  /**
   * Get the recommended rest duration based on driving time
   */
  getRecommendedRestDuration(drivingTimeMinutes: number): number {
    if (drivingTimeMinutes < 180) {
      return 15; // 15 minutes for less than 3 hours
    } else if (drivingTimeMinutes < 360) {
      return 30; // 30 minutes for 3-6 hours
    } else {
      return 45; // 45 minutes for more than 6 hours
    }
  }

  /**
   * Get driver fatigue level based on driving time
   */
  getDriverFatigueLevel(drivingTimeMinutes: number, restIntervalMinutes: number = 120): string {
    if (drivingTimeMinutes < restIntervalMinutes * 0.5) {
      return 'low';
    } else if (drivingTimeMinutes < restIntervalMinutes * 0.8) {
      return 'moderate';
    } else {
      return 'high';
    }
  }

  /**
   * Check if a fuel warning is needed
   */
  isLowFuelWarning(fuelLevel: number, threshold: number = 20): boolean {
    return fuelLevel <= threshold;
  }

  /**
   * Estimate remaining range based on fuel level and efficiency
   */
  estimateRange(fuelLevel: number, efficiency: number, tankCapacity: number): number {
    return (fuelLevel / 100) * tankCapacity * efficiency;
  }
}

export const drivingAssistantService = new DrivingAssistantService();
export default drivingAssistantService;