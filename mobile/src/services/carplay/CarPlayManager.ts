/**
 * CarPlay Manager
 * Handles Apple CarPlay integration for the AI Road Trip app
 */

import { NativeModules, NativeEventEmitter } from 'react-native';
import { Location, Route } from '../../types/location';
import { voiceOrchestrator } from '../voice/VoiceOrchestrator';
import { navigationService } from '../navigation/NavigationService';
import { offlineManager } from '../OfflineManager';
import { performanceMonitor } from '../performanceMonitor';

import { logger } from '@/services/logger';
const { RNCarPlay } = NativeModules;
const carPlayEventEmitter = new NativeEventEmitter(RNCarPlay);

export interface CarPlayTemplate {
  id: string;
  type: 'map' | 'list' | 'grid' | 'nowPlaying' | 'alert';
  title?: string;
  content?: any;
}

export interface CarPlayMapTemplate extends CarPlayTemplate {
  type: 'map';
  guidanceBackgroundColor?: string;
  tripEstimates?: {
    distanceRemaining: number;
    timeRemaining: number;
  };
  mapButtons?: CarPlayMapButton[];
  navigationAlert?: CarPlayNavigationAlert;
}

export interface CarPlayMapButton {
  id: string;
  image: string;
  focusedImage?: string;
  handler: () => void;
}

export interface CarPlayNavigationAlert {
  titleVariants: string[];
  subtitleVariants?: string[];
  image?: string;
  primaryAction: {
    title: string;
    handler: () => void;
  };
  secondaryAction?: {
    title: string;
    handler: () => void;
  };
  duration?: number;
}

export interface CarPlayListTemplate extends CarPlayTemplate {
  type: 'list';
  sections: CarPlayListSection[];
  emptyViewTitle?: string;
  emptyViewSubtitle?: string;
}

export interface CarPlayListSection {
  header?: string;
  items: CarPlayListItem[];
}

export interface CarPlayListItem {
  text: string;
  detailText?: string;
  image?: string;
  playbackProgress?: number;
  isPlaying?: boolean;
  isExplicitContent?: boolean;
  handler: () => void;
}

export interface CarPlayNowPlayingTemplate extends CarPlayTemplate {
  type: 'nowPlaying';
  albumArtistButtonEnabled: boolean;
  upNextButtonTitle?: string;
  upNextButtonEnabled: boolean;
  playbackRateButtonEnabled: boolean;
  repeatButtonEnabled: boolean;
  shuffleButtonEnabled: boolean;
}

export interface CarPlayConnection {
  isConnected: boolean;
  templateId: string | null;
  maneuverInfo?: {
    symbolImage: string;
    instruction: string;
    distanceRemaining: number;
  };
}

class CarPlayManager {
  private static instance: CarPlayManager;
  private isConnected: boolean = false;
  private currentTemplate: CarPlayTemplate | null = null;
  private navigationSession: any = null;
  private voiceGuidanceEnabled: boolean = true;
  private templates: Map<string, CarPlayTemplate> = new Map();
  private eventListeners: Map<string, any> = new Map();
  
  private constructor() {
    this.setupEventListeners();
  }
  
  static getInstance(): CarPlayManager {
    if (!CarPlayManager.instance) {
      CarPlayManager.instance = new CarPlayManager();
    }
    return CarPlayManager.instance;
  }
  
  /**
   * Setup CarPlay event listeners
   */
  private setupEventListeners(): void {
    // Connection events
    this.addEventListener('didConnect', this.handleDidConnect.bind(this));
    this.addEventListener('didDisconnect', this.handleDidDisconnect.bind(this));
    
    // Template events
    this.addEventListener('didSelectListItem', this.handleListItemSelection.bind(this));
    this.addEventListener('didSelectMapButton', this.handleMapButtonPress.bind(this));
    this.addEventListener('didUpdateManeuvers', this.handleManeuverUpdate.bind(this));
    
    // Navigation events
    this.addEventListener('didCancelNavigation', this.handleNavigationCancel.bind(this));
    this.addEventListener('didArrive', this.handleArrival.bind(this));
    
    // Voice control events
    this.addEventListener('didSelectVoiceControl', this.handleVoiceControl.bind(this));
  }
  
  /**
   * Initialize CarPlay
   */
  async initialize(): Promise<void> {
    try {
      if (!RNCarPlay) {
        logger.debug('CarPlay not available on this device');
        return;
      }
      
      // Set up interface controller
      await RNCarPlay.setRootTemplate(this.createRootTemplate());
      
      // Check if already connected
      const connectionStatus = await RNCarPlay.checkConnection();
      if (connectionStatus.isConnected) {
        this.isConnected = true;
        this.onCarPlayConnected();
      }
      
      performanceMonitor.logEvent('carplay_initialized');
      
    } catch (error) {
      logger.error('Failed to initialize CarPlay:', error);
    }
  }
  
  /**
   * Create root template
   */
  private createRootTemplate(): CarPlayTemplate {
    const mapTemplate: CarPlayMapTemplate = {
      id: 'root_map',
      type: 'map',
      guidanceBackgroundColor: '#1E3A8A', // Brand blue
      mapButtons: [
        {
          id: 'voice_control',
          image: 'carplay_mic',
          handler: () => this.toggleVoiceControl()
        },
        {
          id: 'story_mode',
          image: 'carplay_book',
          handler: () => this.toggleStoryMode()
        },
        {
          id: 'games',
          image: 'carplay_game',
          handler: () => this.showGamesMenu()
        },
        {
          id: 'settings',
          image: 'carplay_settings',
          handler: () => this.showSettings()
        }
      ]
    };
    
    this.templates.set(mapTemplate.id, mapTemplate);
    return mapTemplate;
  }
  
  /**
   * Handle CarPlay connection
   */
  private handleDidConnect(): void {
    this.isConnected = true;
    this.onCarPlayConnected();
  }
  
  /**
   * Handle CarPlay disconnection
   */
  private handleDidDisconnect(): void {
    this.isConnected = false;
    this.onCarPlayDisconnected();
  }
  
  /**
   * CarPlay connected callback
   */
  private async onCarPlayConnected(): Promise<void> {
    logger.debug('CarPlay connected');
    
    // Initialize voice for CarPlay
    await voiceOrchestrator.initializeForCarPlay();
    
    // Check for active navigation
    const activeRoute = navigationService.getActiveRoute();
    if (activeRoute) {
      await this.startCarPlayNavigation(activeRoute);
    }
    
    // Enable voice guidance by default
    this.voiceGuidanceEnabled = true;
    
    performanceMonitor.logEvent('carplay_connected');
  }
  
  /**
   * CarPlay disconnected callback
   */
  private onCarPlayDisconnected(): void {
    logger.debug('CarPlay disconnected');
    
    // Clean up navigation session
    if (this.navigationSession) {
      this.navigationSession = null;
    }
    
    // Clear templates
    this.currentTemplate = null;
    
    performanceMonitor.logEvent('carplay_disconnected');
  }
  
  /**
   * Start CarPlay navigation
   */
  async startCarPlayNavigation(route: Route): Promise<void> {
    if (!this.isConnected || !RNCarPlay) return;
    
    try {
      // Create navigation session
      this.navigationSession = await RNCarPlay.startNavigationSession({
        routeId: route.id,
        tripEstimates: {
          distanceRemaining: route.distanceMeters,
          timeRemaining: route.durationSeconds
        }
      });
      
      // Update map template with navigation info
      await this.updateNavigationDisplay(route);
      
      // Start voice guidance
      if (this.voiceGuidanceEnabled) {
        await voiceOrchestrator.startCarPlayGuidance(route);
      }
      
      performanceMonitor.logEvent('carplay_navigation_started', {
        routeId: route.id,
        distance: route.distanceMeters
      });
      
    } catch (error) {
      logger.error('Failed to start CarPlay navigation:', error);
    }
  }
  
  /**
   * Update navigation display
   */
  private async updateNavigationDisplay(route: Route): Promise<void> {
    if (!RNCarPlay) return;
    
    const mapTemplate = this.templates.get('root_map') as CarPlayMapTemplate;
    if (!mapTemplate) return;
    
    // Update trip estimates
    mapTemplate.tripEstimates = {
      distanceRemaining: route.distanceMeters,
      timeRemaining: route.durationSeconds
    };
    
    // Add navigation-specific buttons
    mapTemplate.mapButtons = [
      {
        id: 'end_navigation',
        image: 'carplay_close',
        handler: () => this.endNavigation()
      },
      {
        id: 'voice_toggle',
        image: this.voiceGuidanceEnabled ? 'carplay_speaker_on' : 'carplay_speaker_off',
        handler: () => this.toggleVoiceGuidance()
      },
      {
        id: 'story_mode',
        image: 'carplay_book',
        handler: () => this.toggleStoryMode()
      },
      {
        id: 'overview',
        image: 'carplay_overview',
        handler: () => this.showRouteOverview()
      }
    ];
    
    await RNCarPlay.updateTemplate(mapTemplate);
  }
  
  /**
   * Handle maneuver updates
   */
  private async handleManeuverUpdate(maneuver: any): Promise<void> {
    if (!this.navigationSession) return;
    
    // Update current maneuver
    await RNCarPlay.updateManeuver({
      symbolImage: maneuver.type, // e.g., 'turn_left', 'turn_right', 'straight'
      instruction: maneuver.instruction,
      distanceRemaining: maneuver.distanceRemaining,
      junctionImage: maneuver.junctionImage
    });
    
    // Voice announcement
    if (this.voiceGuidanceEnabled) {
      await voiceOrchestrator.announceManeuver(maneuver);
    }
  }
  
  /**
   * Show games menu
   */
  private async showGamesMenu(): Promise<void> {
    const gamesTemplate: CarPlayListTemplate = {
      id: 'games_menu',
      type: 'list',
      title: 'Road Trip Games',
      sections: [
        {
          header: 'Voice Games',
          items: [
            {
              text: 'Road Trip Trivia',
              detailText: 'Test your knowledge',
              image: 'carplay_trivia',
              handler: () => this.startGame('trivia')
            },
            {
              text: '20 Questions',
              detailText: 'I\'ll guess what you\'re thinking',
              image: 'carplay_questions',
              handler: () => this.startGame('twenty_questions')
            },
            {
              text: 'Travel Bingo',
              detailText: 'Spot items along the way',
              image: 'carplay_bingo',
              handler: () => this.startGame('bingo')
            }
          ]
        },
        {
          header: 'Story Modes',
          items: [
            {
              text: 'Historical Journey',
              detailText: 'Learn about places you pass',
              image: 'carplay_history',
              handler: () => this.setStoryMode('historical')
            },
            {
              text: 'Nature Explorer',
              detailText: 'Discover the natural world',
              image: 'carplay_nature',
              handler: () => this.setStoryMode('nature')
            },
            {
              text: 'Kids Adventure',
              detailText: 'Fun stories for young travelers',
              image: 'carplay_kids',
              handler: () => this.setStoryMode('kids')
            }
          ]
        }
      ]
    };
    
    await this.pushTemplate(gamesTemplate);
  }
  
  /**
   * Show settings
   */
  private async showSettings(): Promise<void> {
    const settingsTemplate: CarPlayListTemplate = {
      id: 'settings',
      type: 'list',
      title: 'Settings',
      sections: [
        {
          header: 'Voice',
          items: [
            {
              text: 'Voice Personality',
              detailText: await this.getCurrentVoicePersonality(),
              image: 'carplay_voice',
              handler: () => this.showVoicePersonalities()
            },
            {
              text: 'Voice Guidance',
              detailText: this.voiceGuidanceEnabled ? 'On' : 'Off',
              image: 'carplay_speaker',
              handler: () => this.toggleVoiceGuidance()
            },
            {
              text: 'Story Frequency',
              detailText: 'Every 5 miles',
              image: 'carplay_frequency',
              handler: () => this.showStoryFrequencyOptions()
            }
          ]
        },
        {
          header: 'Display',
          items: [
            {
              text: 'Day/Night Mode',
              detailText: 'Automatic',
              image: 'carplay_brightness',
              handler: () => this.showDisplayModeOptions()
            },
            {
              text: 'Map Style',
              detailText: 'Standard',
              image: 'carplay_map_style',
              handler: () => this.showMapStyleOptions()
            }
          ]
        },
        {
          header: 'Data',
          items: [
            {
              text: 'Offline Maps',
              detailText: await this.getOfflineMapStatus(),
              image: 'carplay_download',
              handler: () => this.showOfflineMapOptions()
            },
            {
              text: 'Data Usage',
              detailText: 'Wi-Fi Only',
              image: 'carplay_data',
              handler: () => this.showDataUsageOptions()
            }
          ]
        }
      ]
    };
    
    await this.pushTemplate(settingsTemplate);
  }
  
  /**
   * Handle voice control
   */
  private async handleVoiceControl(command: any): Promise<void> {
    // Process voice command through voice orchestrator
    const response = await voiceOrchestrator.processCarPlayVoiceCommand(command);
    
    // Handle response
    if (response.action) {
      switch (response.action) {
        case 'navigate':
          await this.startCarPlayNavigation(response.route);
          break;
        case 'play_game':
          await this.startGame(response.gameType);
          break;
        case 'change_voice':
          await this.setVoicePersonality(response.personality);
          break;
        case 'tell_story':
          await voiceOrchestrator.playStory(response.story);
          break;
      }
    }
  }
  
  /**
   * Toggle voice control
   */
  private async toggleVoiceControl(): Promise<void> {
    await voiceOrchestrator.toggleCarPlayListening();
    
    // Show visual feedback
    const alert: CarPlayNavigationAlert = {
      titleVariants: ['Listening...'],
      subtitleVariants: ['Say a command'],
      image: 'carplay_mic_active',
      primaryAction: {
        title: 'Cancel',
        handler: () => voiceOrchestrator.stopListening()
      },
      duration: 10
    };
    
    await this.showNavigationAlert(alert);
  }
  
  /**
   * Toggle story mode
   */
  private async toggleStoryMode(): Promise<void> {
    const isEnabled = await voiceOrchestrator.toggleStoryMode();
    
    const alert: CarPlayNavigationAlert = {
      titleVariants: [isEnabled ? 'Story Mode On' : 'Story Mode Off'],
      subtitleVariants: [isEnabled ? 'I\'ll tell you stories along the way' : 'Stories paused'],
      image: 'carplay_book',
      primaryAction: {
        title: 'OK',
        handler: () => {}
      },
      duration: 3
    };
    
    await this.showNavigationAlert(alert);
  }
  
  /**
   * Toggle voice guidance
   */
  private async toggleVoiceGuidance(): Promise<void> {
    this.voiceGuidanceEnabled = !this.voiceGuidanceEnabled;
    await this.updateNavigationDisplay(navigationService.getActiveRoute()!);
    
    if (!this.voiceGuidanceEnabled) {
      await voiceOrchestrator.pauseCarPlayGuidance();
    } else {
      await voiceOrchestrator.resumeCarPlayGuidance();
    }
  }
  
  /**
   * Start a game
   */
  private async startGame(gameType: string): Promise<void> {
    await voiceOrchestrator.startCarPlayGame(gameType);
    
    // Show now playing template for game
    const nowPlayingTemplate: CarPlayNowPlayingTemplate = {
      id: 'game_now_playing',
      type: 'nowPlaying',
      albumArtistButtonEnabled: false,
      upNextButtonTitle: 'Skip Question',
      upNextButtonEnabled: true,
      playbackRateButtonEnabled: false,
      repeatButtonEnabled: false,
      shuffleButtonEnabled: false
    };
    
    await this.pushTemplate(nowPlayingTemplate);
  }
  
  /**
   * End navigation
   */
  private async endNavigation(): Promise<void> {
    if (!this.navigationSession || !RNCarPlay) return;
    
    await RNCarPlay.endNavigationSession();
    this.navigationSession = null;
    
    // Stop voice guidance
    await voiceOrchestrator.stopCarPlayGuidance();
    
    // Return to root template
    await this.popToRootTemplate();
  }
  
  /**
   * Handle navigation cancel
   */
  private async handleNavigationCancel(): Promise<void> {
    await this.endNavigation();
  }
  
  /**
   * Handle arrival
   */
  private async handleArrival(): Promise<void> {
    // Play arrival message
    await voiceOrchestrator.announceArrival();
    
    // Show arrival alert
    const alert: CarPlayNavigationAlert = {
      titleVariants: ['You\'ve Arrived!'],
      subtitleVariants: ['Thanks for traveling with me'],
      image: 'carplay_arrive',
      primaryAction: {
        title: 'End',
        handler: () => this.endNavigation()
      },
      secondaryAction: {
        title: 'Save Trip',
        handler: () => this.saveTrip()
      }
    };
    
    await this.showNavigationAlert(alert);
  }
  
  /**
   * Helper methods
   */
  
  private async pushTemplate(template: CarPlayTemplate): Promise<void> {
    if (!RNCarPlay) return;
    
    this.templates.set(template.id, template);
    await RNCarPlay.pushTemplate(template);
    this.currentTemplate = template;
  }
  
  private async popTemplate(): Promise<void> {
    if (!RNCarPlay) return;
    
    await RNCarPlay.popTemplate();
    // Update current template reference
  }
  
  private async popToRootTemplate(): Promise<void> {
    if (!RNCarPlay) return;
    
    await RNCarPlay.popToRootTemplate();
    this.currentTemplate = this.templates.get('root_map') || null;
  }
  
  private async showNavigationAlert(alert: CarPlayNavigationAlert): Promise<void> {
    if (!RNCarPlay || !this.navigationSession) return;
    
    await RNCarPlay.presentNavigationAlert(alert);
  }
  
  private async getCurrentVoicePersonality(): Promise<string> {
    const personality = await voiceOrchestrator.getCurrentPersonality();
    return personality.displayName;
  }
  
  private async getOfflineMapStatus(): Promise<string> {
    const hasOfflineMaps = await offlineManager.hasOfflineMaps();
    return hasOfflineMaps ? 'Available' : 'Not Downloaded';
  }
  
  private async showVoicePersonalities(): Promise<void> {
    // Would show voice personality selection
  }
  
  private async showStoryFrequencyOptions(): Promise<void> {
    // Would show story frequency options
  }
  
  private async showDisplayModeOptions(): Promise<void> {
    // Would show display mode options
  }
  
  private async showMapStyleOptions(): Promise<void> {
    // Would show map style options
  }
  
  private async showOfflineMapOptions(): Promise<void> {
    // Would show offline map options
  }
  
  private async showDataUsageOptions(): Promise<void> {
    // Would show data usage options
  }
  
  private async setVoicePersonality(personality: string): Promise<void> {
    await voiceOrchestrator.setPersonality(personality);
  }
  
  private async setStoryMode(mode: string): Promise<void> {
    await voiceOrchestrator.setStoryMode(mode);
  }
  
  private async showRouteOverview(): Promise<void> {
    // Would show route overview
  }
  
  private async saveTrip(): Promise<void> {
    // Would save trip to history
  }
  
  private async handleListItemSelection(item: any): Promise<void> {
    const template = this.currentTemplate as CarPlayListTemplate;
    if (!template) return;
    
    // Find and execute handler
    for (const section of template.sections) {
      const listItem = section.items.find(i => i.text === item.text);
      if (listItem) {
        listItem.handler();
        break;
      }
    }
  }
  
  private async handleMapButtonPress(buttonId: string): Promise<void> {
    const template = this.currentTemplate as CarPlayMapTemplate;
    if (!template) return;
    
    const button = template.mapButtons?.find(b => b.id === buttonId);
    if (button) {
      button.handler();
    }
  }
  
  private addEventListener(event: string, handler: any): void {
    const listener = carPlayEventEmitter.addListener(event, handler);
    this.eventListeners.set(event, listener);
  }
  
  /**
   * Get connection status
   */
  getConnectionStatus(): CarPlayConnection {
    return {
      isConnected: this.isConnected,
      templateId: this.currentTemplate?.id || null
    };
  }
  
  /**
   * Clean up
   */
  cleanup(): void {
    // Remove event listeners
    this.eventListeners.forEach(listener => listener.remove());
    this.eventListeners.clear();
    
    // End any active navigation
    if (this.navigationSession) {
      this.endNavigation();
    }
  }
}

// Export singleton instance
export const carPlayManager = CarPlayManager.getInstance();
