import { ApiClient } from '../api/ApiClient';
import { logger } from '@/services/logger';
import { 
  ARPointRequest, 
  ARPointResponse, 
  ARViewParameters, 
  ARRenderResponse,
  ARRenderSettings,
  ARRenderSettingsUpdate,
  HistoricalOverlayRequest,
  HistoricalOverlayResponse
} from '../../types/ar';
import { LocationObj } from '../../types/location';

class ARService {
  private settings: ARRenderSettings = {
    distance_scale: 1.0,
    opacity: 0.85,
    color_scheme: 'default',
    show_labels: true,
    show_distances: true,
    show_arrows: true,
    animation_speed: 1.0,
    detail_level: 2,
    accessibility_mode: false
  };

  constructor() {
    // Load saved settings from local storage if available
    this.loadSavedSettings();
  }

  /**
   * Load previously saved AR settings
   */
  private async loadSavedSettings(): Promise<void> {
    try {
      // This would typically use AsyncStorage or similar
      // const savedSettings = await AsyncStorage.getItem('ar_settings');
      // if (savedSettings) {
      //   this.settings = JSON.parse(savedSettings);
      // }
    } catch (error) {
      logger.error('Failed to load AR settings:', error);
    }
  }

  /**
   * Save AR settings to persistent storage
   */
  private async saveSettings(): Promise<void> {
    try {
      // This would typically use AsyncStorage or similar
      // await AsyncStorage.setItem('ar_settings', JSON.stringify(this.settings));
    } catch (error) {
      logger.error('Failed to save AR settings:', error);
    }
  }

  /**
   * Get AR points around a location
   */
  async getARPoints(
    location: LocationObj,
    radius: number = 500,
    types?: string[]
  ): Promise<ARPointResponse[]> {
    const request: ARPointRequest = {
      latitude: location.latitude,
      longitude: location.longitude,
      radius,
      types
    };

    try {
      return await ApiClient.post<ARPointResponse[]>('/ar/points', request);
    } catch (error) {
      logger.error('Failed to fetch AR points:', error);
      throw error;
    }
  }

  /**
   * Render AR points for display
   */
  async renderARView(
    location: LocationObj,
    viewParams: ARViewParameters,
    radius: number = 500,
    types?: string[]
  ): Promise<ARRenderResponse> {
    const request: ARPointRequest = {
      latitude: location.latitude,
      longitude: location.longitude,
      radius,
      types
    };

    try {
      return await ApiClient.post<ARRenderResponse>('/ar/render', request, viewParams);
    } catch (error) {
      logger.error('Failed to render AR view:', error);
      throw error;
    }
  }

  /**
   * Update AR rendering settings
   */
  async updateSettings(newSettings: ARRenderSettingsUpdate): Promise<ARRenderSettings> {
    try {
      const updatedSettings = await ApiClient.patch<ARRenderSettings>('/ar/render/settings', newSettings);
      this.settings = updatedSettings;
      await this.saveSettings();
      return updatedSettings;
    } catch (error) {
      logger.error('Failed to update AR settings:', error);
      throw error;
    }
  }

  /**
   * Get historical overlay for a location
   */
  async getHistoricalOverlay(
    location: LocationObj,
    year?: number
  ): Promise<HistoricalOverlayResponse> {
    const request: HistoricalOverlayRequest = {
      latitude: location.latitude,
      longitude: location.longitude,
      year
    };

    try {
      return await ApiClient.post<HistoricalOverlayResponse>('/ar/historical/overlay', request);
    } catch (error) {
      logger.error('Failed to fetch historical overlay:', error);
      throw error;
    }
  }

  /**
   * Check if device supports AR features
   */
  async isARSupported(): Promise<boolean> {
    // In a real implementation, this would check device capabilities
    // For now, return true if we're on a relatively modern device
    return true;
  }

  /**
   * Get current AR settings
   */
  getSettings(): ARRenderSettings {
    return { ...this.settings };
  }
}

export const arService = new ARService();
export default arService;