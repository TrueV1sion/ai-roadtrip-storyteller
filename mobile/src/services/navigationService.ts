/**
 * Navigation Service - Handles all navigation-related API calls and position updates
 */

import { LocationObject } from 'expo-location';
import { apiClient } from './apiClient';
import { logger } from '@/services/logger';
import { 
  NavigationStartRequest, 
  NavigationUpdateRequest,
  NavigationInstructionResponse,
  NavigationStateResponse 
} from '../types/navigation';

interface NavigationPosition {
  latitude: number;
  longitude: number;
  speed?: number;
  heading?: number;
  altitude?: number;
  timestamp: number;
}

class NavigationService {
  private isActive: boolean = false;
  private currentRouteId: string | null = null;
  private currentStepIndex: number = 0;
  private lastUpdateTime: number = 0;
  private updateInterval: number = 2000; // 2 seconds default
  
  /**
   * Start navigation for a route
   */
  async startNavigation(request: NavigationStartRequest): Promise<{
    status: string;
    route_id: string;
    total_instructions: number;
    coordination_rules: any;
  }> {
    try {
      const response = await apiClient.post('/api/navigation/start', request);
      
      if (response.data.status === 'success') {
        this.isActive = true;
        this.currentRouteId = response.data.route_id;
        this.currentStepIndex = 0;
      }
      
      return response.data;
    } catch (error) {
      logger.error('Failed to start navigation:', error);
      throw error;
    }
  }
  
  /**
   * Update navigation with current position and get instructions
   */
  async updateNavigation(location: LocationObject, context: {
    currentStepIndex: number;
    distanceToNextManeuver: number;
    timeToNextManeuver: number;
    isOnHighway: boolean;
    approachingComplexIntersection: boolean;
    storyPlaying: boolean;
    audioPriority?: string;
  }): Promise<NavigationInstructionResponse> {
    try {
      // Throttle updates
      const now = Date.now();
      if (now - this.lastUpdateTime < this.updateInterval) {
        return { has_instruction: false, next_check_seconds: 2 };
      }
      this.lastUpdateTime = now;
      
      const request: NavigationUpdateRequest = {
        current_location: {
          lat: location.coords.latitude,
          lng: location.coords.longitude
        },
        current_step_index: context.currentStepIndex,
        distance_to_next_maneuver: context.distanceToNextManeuver,
        time_to_next_maneuver: context.timeToNextManeuver,
        current_speed: location.coords.speed || 0,
        is_on_highway: context.isOnHighway,
        approaching_complex_intersection: context.approachingComplexIntersection,
        story_playing: context.storyPlaying,
        audio_priority: context.audioPriority || 'balanced',
        last_instruction_time: undefined // Will be managed by component
      };
      
      const response = await apiClient.post('/api/navigation/update', request);
      
      // Adjust update interval based on next check recommendation
      if (response.data.next_check_seconds) {
        this.updateInterval = response.data.next_check_seconds * 1000;
      }
      
      return response.data;
    } catch (error) {
      logger.error('Failed to update navigation:', error);
      // Return no instruction on error to avoid disruption
      return { has_instruction: false, next_check_seconds: 5 };
    }
  }
  
  /**
   * Get current navigation state
   */
  async getNavigationStatus(): Promise<NavigationStateResponse> {
    try {
      const response = await apiClient.get('/api/navigation/status');
      return response.data;
    } catch (error) {
      logger.error('Failed to get navigation status:', error);
      throw error;
    }
  }
  
  /**
   * Stop navigation
   */
  async stopNavigation(): Promise<void> {
    try {
      await apiClient.post('/api/navigation/stop');
      this.isActive = false;
      this.currentRouteId = null;
      this.currentStepIndex = 0;
      this.updateInterval = 2000;
    } catch (error) {
      logger.error('Failed to stop navigation:', error);
      throw error;
    }
  }
  
  /**
   * Update position in background
   */
  async updateBackgroundPosition(position: NavigationPosition): Promise<void> {
    try {
      if (!this.isActive) return;
      
      await apiClient.post('/api/navigation/background-update', {
        position,
        route_id: this.currentRouteId,
        timestamp: position.timestamp
      });
    } catch (error) {
      logger.error('Failed to update background position:', error);
    }
  }
  
  /**
   * Check if instruction is needed (for background)
   */
  async checkInstruction(location: LocationObject): Promise<NavigationInstructionResponse | null> {
    try {
      if (!this.isActive) return null;
      
      // Simplified check for background mode
      const response = await apiClient.post('/api/navigation/check-instruction', {
        current_location: {
          lat: location.coords.latitude,
          lng: location.coords.longitude
        },
        route_id: this.currentRouteId
      });
      
      return response.data;
    } catch (error) {
      logger.error('Failed to check instruction:', error);
      return null;
    }
  }
  
  /**
   * Calculate distance between two points
   */
  calculateDistance(lat1: number, lon1: number, lat2: number, lon2: number): number {
    const R = 6371e3; // Earth's radius in meters
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
   * Check if currently on highway based on road type
   */
  detectHighway(routeStep: any): boolean {
    const highwayKeywords = ['highway', 'freeway', 'interstate', 'i-', 'hwy', 'expressway'];
    const instruction = routeStep.html_instructions?.toLowerCase() || '';
    return highwayKeywords.some(keyword => instruction.includes(keyword));
  }
  
  /**
   * Get current navigation state for UI
   */
  getNavigationState() {
    return {
      isActive: this.isActive,
      routeId: this.currentRouteId,
      currentStepIndex: this.currentStepIndex
    };
  }
  
  /**
   * Set current step index (for UI sync)
   */
  setCurrentStepIndex(index: number) {
    this.currentStepIndex = index;
  }
}

export const navigationService = new NavigationService();