/**
 * Android Auto Manager
 * Handles Android Auto integration for the AI Road Trip app
 */

import { NativeModules, NativeEventEmitter, Platform } from 'react-native';
import { Location, Route } from '../../types/location';
import { voiceOrchestrator } from '../voice/VoiceOrchestrator';
import { navigationService } from '../navigation/NavigationService';
import { storyService } from '../story/StoryService';
import { performanceMonitor } from '../performanceMonitor';

import { logger } from '@/services/logger';
const { RNAndroidAuto } = NativeModules;
const androidAutoEventEmitter = RNAndroidAuto ? new NativeEventEmitter(RNAndroidAuto) : null;

export interface AndroidAutoStatus {
  available: boolean;
  connected: boolean;
}

export interface AndroidAutoManeuver {
  instruction: string;
  distance: number;
  type: 'turn_left' | 'turn_right' | 'straight' | 'u_turn' | 'roundabout' | 'merge' | 'exit';
  roundaboutExit?: number;
  lanes?: AndroidAutoLane[];
}

export interface AndroidAutoLane {
  directions: ('left' | 'straight' | 'right')[];
  isRecommended: boolean;
}

export interface AndroidAutoNavigationOptions {
  destination: string;
  waypoints?: Location[];
  avoidHighways?: boolean;
  avoidTolls?: boolean;
  preferScenic?: boolean;
}

export interface AndroidAutoStory {
  title: string;
  content: string;
  voiceUrl?: string;
  duration: number;
  location: Location;
}

class AndroidAutoManager {
  private static instance: AndroidAutoManager;
  private isInitialized: boolean = false;
  private isConnected: boolean = false;
  private currentRoute: Route | null = null;
  private voicePersonality: string = 'friendly_guide';
  private storyModeEnabled: boolean = true;
  private eventListeners: Map<string, any> = new Map();
  
  private constructor() {
    if (Platform.OS === 'android') {
      this.setupEventListeners();
    }
  }
  
  static getInstance(): AndroidAutoManager {
    if (!AndroidAutoManager.instance) {
      AndroidAutoManager.instance = new AndroidAutoManager();
    }
    return AndroidAutoManager.instance;
  }
  
  /**
   * Setup event listeners
   */
  private setupEventListeners(): void {
    if (!androidAutoEventEmitter) return;
    
    // Connection events
    this.addEventListener('androidAutoConnected', this.handleConnected.bind(this));
    this.addEventListener('androidAutoDisconnected', this.handleDisconnected.bind(this));
    
    // Navigation events
    this.addEventListener('navigationStarted', this.handleNavigationStarted.bind(this));
    this.addEventListener('navigationEnded', this.handleNavigationEnded.bind(this));
    
    // Voice events
    this.addEventListener('voiceCommand', this.handleVoiceCommand.bind(this));
  }
  
  /**
   * Initialize Android Auto
   */
  async initialize(): Promise<AndroidAutoStatus> {
    if (Platform.OS !== 'android' || !RNAndroidAuto) {
      return { available: false, connected: false };
    }
    
    try {
      const status = await RNAndroidAuto.initialize();
      this.isInitialized = true;
      this.isConnected = status.connected;
      
      // Initialize voice system for Android Auto
      if (status.connected) {
        await voiceOrchestrator.initializeForAndroidAuto();
      }
      
      performanceMonitor.logEvent('android_auto_initialized', status);
      
      return status;
      
    } catch (error) {
      logger.error('Failed to initialize Android Auto:', error);
      return { available: false, connected: false };
    }
  }
  
  /**
   * Start navigation
   */
  async startNavigation(options: AndroidAutoNavigationOptions): Promise<void> {
    if (!this.isConnected || !RNAndroidAuto) {
      throw new Error('Android Auto not connected');
    }
    
    try {
      // Get route from navigation service
      const route = await navigationService.calculateRoute({
        destination: options.destination,
        waypoints: options.waypoints,
        avoidHighways: options.avoidHighways,
        avoidTolls: options.avoidTolls,
        preferScenic: options.preferScenic
      });
      
      this.currentRoute = route;
      
      // Start navigation in Android Auto
      await RNAndroidAuto.startNavigation({
        destination: options.destination,
        waypoints: options.waypoints
      });
      
      // Start voice guidance
      await voiceOrchestrator.startAndroidAutoGuidance(route);
      
      // Start story mode if enabled
      if (this.storyModeEnabled) {
        await storyService.startJourney(route);
      }
      
      performanceMonitor.logEvent('android_auto_navigation_started', {
        destination: options.destination,
        routeDistance: route.distanceMeters
      });
      
    } catch (error) {
      logger.error('Failed to start Android Auto navigation:', error);
      throw error;
    }
  }
  
  /**
   * End navigation
   */
  async endNavigation(): Promise<void> {
    if (!RNAndroidAuto) return;
    
    try {
      await RNAndroidAuto.endNavigation();
      
      // Stop voice guidance
      await voiceOrchestrator.stopAndroidAutoGuidance();
      
      // Stop stories
      await storyService.endJourney();
      
      this.currentRoute = null;
      
      performanceMonitor.logEvent('android_auto_navigation_ended');
      
    } catch (error) {
      logger.error('Failed to end Android Auto navigation:', error);
    }
  }
  
  /**
   * Update navigation maneuver
   */
  async updateManeuver(maneuver: AndroidAutoManeuver): Promise<void> {
    if (!this.isConnected || !RNAndroidAuto) return;
    
    try {
      await RNAndroidAuto.updateManeuver(maneuver);
      
      // Voice announcement
      await voiceOrchestrator.announceManeuver({
        instruction: maneuver.instruction,
        distanceRemaining: maneuver.distance,
        type: maneuver.type
      });
      
    } catch (error) {
      logger.error('Failed to update maneuver:', error);
    }
  }
  
  /**
   * Set voice personality
   */
  async setVoicePersonality(personality: string): Promise<void> {
    this.voicePersonality = personality;
    
    if (RNAndroidAuto) {
      await RNAndroidAuto.setVoicePersonality(personality);
    }
    
    await voiceOrchestrator.setPersonality(personality);
  }
  
  /**
   * Toggle story mode
   */
  toggleStoryMode(): boolean {
    this.storyModeEnabled = !this.storyModeEnabled;
    
    if (this.storyModeEnabled && this.currentRoute) {
      storyService.startJourney(this.currentRoute);
    } else {
      storyService.pauseStories();
    }
    
    return this.storyModeEnabled;
  }
  
  /**
   * Start voice recognition
   */
  async startVoiceRecognition(): Promise<void> {
    if (!this.isConnected || !RNAndroidAuto) return;
    
    try {
      await RNAndroidAuto.startVoiceRecognition();
    } catch (error) {
      logger.error('Failed to start voice recognition:', error);
    }
  }
  
  /**
   * Play story
   */
  async playStory(story: AndroidAutoStory): Promise<void> {
    if (!this.isConnected || !RNAndroidAuto) return;
    
    try {
      await RNAndroidAuto.playStory(story);
      
      performanceMonitor.logEvent('android_auto_story_played', {
        title: story.title,
        duration: story.duration
      });
      
    } catch (error) {
      logger.error('Failed to play story:', error);
    }
  }
  
  /**
   * Start game
   */
  async startGame(gameType: 'trivia' | 'twenty_questions' | 'bingo'): Promise<void> {
    if (!this.isConnected || !RNAndroidAuto) return;
    
    try {
      await RNAndroidAuto.startGame(gameType);
      
      // Initialize game through voice orchestrator
      await voiceOrchestrator.startAndroidAutoGame(gameType);
      
      performanceMonitor.logEvent('android_auto_game_started', { gameType });
      
    } catch (error) {
      logger.error('Failed to start game:', error);
    }
  }
  
  /**
   * Get connection status
   */
  async getConnectionStatus(): Promise<AndroidAutoStatus> {
    if (!RNAndroidAuto) {
      return { available: false, connected: false };
    }
    
    try {
      return await RNAndroidAuto.getConnectionStatus();
    } catch (error) {
      logger.error('Failed to get connection status:', error);
      return { available: false, connected: false };
    }
  }
  
  /**
   * Handle connected event
   */
  private async handleConnected(): Promise<void> {
    logger.debug('Android Auto connected');
    this.isConnected = true;
    
    // Initialize voice for Android Auto
    await voiceOrchestrator.initializeForAndroidAuto();
    
    // Check for active navigation
    const activeRoute = navigationService.getActiveRoute();
    if (activeRoute) {
      // Resume navigation in Android Auto
      await this.startNavigation({
        destination: activeRoute.destination
      });
    }
    
    performanceMonitor.logEvent('android_auto_connected');
  }
  
  /**
   * Handle disconnected event
   */
  private handleDisconnected(): void {
    logger.debug('Android Auto disconnected');
    this.isConnected = false;
    this.currentRoute = null;
    
    performanceMonitor.logEvent('android_auto_disconnected');
  }
  
  /**
   * Handle navigation started event
   */
  private handleNavigationStarted(): void {
    // Navigation started from Android Auto
  }
  
  /**
   * Handle navigation ended event
   */
  private handleNavigationEnded(): void {
    this.currentRoute = null;
  }
  
  /**
   * Handle voice command event
   */
  private async handleVoiceCommand(event: { command: string }): Promise<void> {
    const response = await voiceOrchestrator.processAndroidAutoVoiceCommand(event.command);
    
    // Handle response
    if (response.action) {
      switch (response.action) {
        case 'navigate':
          await this.startNavigation({
            destination: response.destination
          });
          break;
          
        case 'play_game':
          await this.startGame(response.gameType);
          break;
          
        case 'change_voice':
          await this.setVoicePersonality(response.personality);
          break;
          
        case 'tell_story':
          await this.playStory(response.story);
          break;
      }
    }
  }
  
  /**
   * Add event listener
   */
  private addEventListener(event: string, handler: any): void {
    if (androidAutoEventEmitter) {
      const listener = androidAutoEventEmitter.addListener(event, handler);
      this.eventListeners.set(event, listener);
    }
  }
  
  /**
   * Is Android Auto available
   */
  isAvailable(): boolean {
    return Platform.OS === 'android' && RNAndroidAuto !== undefined;
  }
  
  /**
   * Is connected to Android Auto
   */
  isAndroidAutoConnected(): boolean {
    return this.isConnected;
  }
  
  /**
   * Get current route
   */
  getCurrentRoute(): Route | null {
    return this.currentRoute;
  }
  
  /**
   * Cleanup
   */
  cleanup(): void {
    // Remove event listeners
    this.eventListeners.forEach(listener => listener.remove());
    this.eventListeners.clear();
    
    // End any active navigation
    if (this.currentRoute) {
      this.endNavigation();
    }
  }
}

// Export singleton instance
export const androidAutoManager = AndroidAutoManager.getInstance();
