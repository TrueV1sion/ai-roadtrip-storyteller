/**
 * Background Navigation Service
 * Handles navigation updates and voice instructions when app is in background
 */

import * as TaskManager from 'expo-task-manager';
import * as Location from 'expo-location';
import * as BackgroundFetch from 'expo-background-fetch';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { navigationService } from './navigationService';
import { navigationVoiceService } from './navigationVoiceService';

import { logger } from '@/services/logger';
const LOCATION_TASK_NAME = 'background-location-task';
const NAVIGATION_STATE_KEY = '@navigation_state';
const NAVIGATION_ROUTE_KEY = '@navigation_route';

interface BackgroundNavigationState {
  isActive: boolean;
  routeId: string | null;
  currentStepIndex: number;
  lastInstructionTime: string | null;
  routeData: any;
}

class BackgroundNavigationService {
  private isInitialized: boolean = false;

  /**
   * Initialize background navigation tracking
   */
  async initialize(routeId: string, routeData: any): Promise<void> {
    try {
      // Store navigation state for background access
      const state: BackgroundNavigationState = {
        isActive: true,
        routeId,
        currentStepIndex: 0,
        lastInstructionTime: null,
        routeData
      };
      
      await AsyncStorage.setItem(NAVIGATION_STATE_KEY, JSON.stringify(state));
      await AsyncStorage.setItem(NAVIGATION_ROUTE_KEY, JSON.stringify(routeData));
      
      // Request background permissions
      const { status: backgroundStatus } = await Location.requestBackgroundPermissionsAsync();
      if (backgroundStatus !== 'granted') {
        logger.warn('Background location permission not granted');
        return;
      }
      
      // Start background location updates
      await Location.startLocationUpdatesAsync(LOCATION_TASK_NAME, {
        accuracy: Location.Accuracy.BestForNavigation,
        timeInterval: 5000, // Update every 5 seconds
        distanceInterval: 10, // Update every 10 meters
        foregroundService: {
          notificationTitle: 'Road Trip Navigation',
          notificationBody: 'Navigation is active in background',
          notificationColor: '#4A90E2',
        },
        pausesUpdatesAutomatically: false,
        activityType: Location.ActivityType.AutomotiveNavigation,
      });
      
      this.isInitialized = true;
      logger.debug('Background navigation initialized');
      
    } catch (error) {
      logger.error('Failed to initialize background navigation:', error);
      throw error;
    }
  }

  /**
   * Update navigation state from foreground
   */
  async updateState(currentStepIndex: number): Promise<void> {
    try {
      const stateStr = await AsyncStorage.getItem(NAVIGATION_STATE_KEY);
      if (stateStr) {
        const state: BackgroundNavigationState = JSON.parse(stateStr);
        state.currentStepIndex = currentStepIndex;
        await AsyncStorage.setItem(NAVIGATION_STATE_KEY, JSON.stringify(state));
      }
    } catch (error) {
      logger.error('Failed to update background navigation state:', error);
    }
  }

  /**
   * Stop background navigation
   */
  async stop(): Promise<void> {
    try {
      if (this.isInitialized) {
        await Location.stopLocationUpdatesAsync(LOCATION_TASK_NAME);
        await AsyncStorage.removeItem(NAVIGATION_STATE_KEY);
        await AsyncStorage.removeItem(NAVIGATION_ROUTE_KEY);
        this.isInitialized = false;
      }
    } catch (error) {
      logger.error('Failed to stop background navigation:', error);
    }
  }

  /**
   * Check if background navigation is active
   */
  async isActive(): Promise<boolean> {
    try {
      const stateStr = await AsyncStorage.getItem(NAVIGATION_STATE_KEY);
      if (stateStr) {
        const state: BackgroundNavigationState = JSON.parse(stateStr);
        return state.isActive;
      }
      return false;
    } catch (error) {
      return false;
    }
  }

  /**
   * Process location update in background
   */
  static async processBackgroundUpdate(location: Location.LocationObject): Promise<void> {
    try {
      // Get stored navigation state
      const stateStr = await AsyncStorage.getItem(NAVIGATION_STATE_KEY);
      const routeStr = await AsyncStorage.getItem(NAVIGATION_ROUTE_KEY);
      
      if (!stateStr || !routeStr) {
        return;
      }
      
      const state: BackgroundNavigationState = JSON.parse(stateStr);
      const routeData = JSON.parse(routeStr);
      
      if (!state.isActive) {
        return;
      }
      
      // Calculate navigation metrics
      const metrics = await this.calculateBackgroundMetrics(
        location,
        routeData,
        state.currentStepIndex
      );
      
      // Check if we need to advance step
      if (metrics.shouldAdvanceStep) {
        state.currentStepIndex++;
        await AsyncStorage.setItem(NAVIGATION_STATE_KEY, JSON.stringify(state));
      }
      
      // Send update to backend
      await navigationService.updateBackgroundPosition({
        latitude: location.coords.latitude,
        longitude: location.coords.longitude,
        speed: location.coords.speed,
        heading: location.coords.heading,
        altitude: location.coords.altitude,
        timestamp: location.timestamp,
      });
      
      // Check for navigation instruction
      const instructionCheck = await navigationService.checkInstruction(location);
      
      if (instructionCheck?.has_instruction) {
        // Calculate time since last instruction
        const lastInstructionTime = state.lastInstructionTime 
          ? new Date(state.lastInstructionTime) 
          : null;
        
        const timeSinceLastInstruction = lastInstructionTime
          ? (Date.now() - lastInstructionTime.getTime()) / 1000
          : Infinity;
        
        // Only play if enough time has passed (avoid spam)
        if (timeSinceLastInstruction > 15) {
          await navigationVoiceService.checkAndPlayInstruction(location, {
            currentStepIndex: state.currentStepIndex,
            distanceToNextManeuver: metrics.distanceToNextManeuver,
            timeToNextManeuver: metrics.timeToNextManeuver,
            currentSpeed: metrics.currentSpeed,
            isOnHighway: metrics.isOnHighway,
            approachingComplexIntersection: metrics.approachingComplexIntersection,
            storyPlaying: false,
            audioPriority: 'navigation'
          });
          
          // Update last instruction time
          state.lastInstructionTime = new Date().toISOString();
          await AsyncStorage.setItem(NAVIGATION_STATE_KEY, JSON.stringify(state));
        }
      }
      
    } catch (error) {
      logger.error('Failed to process background location update:', error);
    }
  }

  /**
   * Calculate navigation metrics in background
   */
  private static async calculateBackgroundMetrics(
    location: Location.LocationObject,
    routeData: any,
    currentStepIndex: number
  ): Promise<any> {
    const legs = routeData.legs || [];
    if (legs.length === 0) {
      return {
        distanceToNextManeuver: 0,
        timeToNextManeuver: 0,
        currentSpeed: 0,
        isOnHighway: false,
        approachingComplexIntersection: false,
        shouldAdvanceStep: false
      };
    }
    
    const currentLeg = legs[0];
    const steps = currentLeg.steps || [];
    
    if (currentStepIndex >= steps.length) {
      return {
        distanceToNextManeuver: 0,
        timeToNextManeuver: 0,
        currentSpeed: location.coords.speed || 0,
        isOnHighway: false,
        approachingComplexIntersection: false,
        shouldAdvanceStep: false
      };
    }
    
    const currentStep = steps[currentStepIndex];
    const nextLocation = currentStep.end_location || currentStep.start_location;
    
    // Calculate distance
    const distance = navigationService.calculateDistance(
      location.coords.latitude,
      location.coords.longitude,
      nextLocation.lat,
      nextLocation.lng
    );
    
    // Calculate time
    const speedMs = location.coords.speed || 13.4; // Default ~30mph
    const timeSeconds = distance / speedMs;
    
    // Detect highway
    const instructions = currentStep.html_instructions?.toLowerCase() || '';
    const isHighway = ['highway', 'freeway', 'interstate', 'i-'].some(
      keyword => instructions.includes(keyword)
    );
    
    // Detect complex maneuvers
    const maneuver = currentStep.maneuver || '';
    const isComplex = ['roundabout', 'fork', 'merge'].some(
      m => maneuver.includes(m)
    );
    
    return {
      distanceToNextManeuver: distance,
      timeToNextManeuver: timeSeconds,
      currentSpeed: speedMs,
      isOnHighway: isHighway,
      approachingComplexIntersection: isComplex && distance < 200,
      shouldAdvanceStep: distance < 30
    };
  }
}

// Define the background task
TaskManager.defineTask(LOCATION_TASK_NAME, async ({ data, error }) => {
  if (error) {
    logger.error('Background location task error:', error);
    return;
  }
  
  if (data) {
    const { locations } = data as any;
    const location = locations[0];
    
    // Process the location update
    await BackgroundNavigationService.processBackgroundUpdate(location);
  }
});

export const backgroundNavigationService = new BackgroundNavigationService();