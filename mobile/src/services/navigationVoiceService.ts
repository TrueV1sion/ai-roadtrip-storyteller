/**
 * Navigation Voice Service
 * Integrates with backend NavigationVoiceService for turn-by-turn voice guidance
 * Coordinates with spatial audio for immersive directional instructions
 */

import { Audio } from 'expo-av';
import { LocationObject } from 'expo-location';
import { apiClient } from './apiClient';
import { spatialAudioService } from './audio/spatialAudioService';
import { audioOrchestrationService } from './audio/audioOrchestrationService';

import { logger } from '@/services/logger';
interface NavigationInstruction {
  text: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  timing: string;
  maneuver_type?: string;
  street_name?: string;
  exit_number?: string;
  audio_cues: {
    tone?: string;
    volume_boost?: number;
    spatial_position?: 'left' | 'right' | 'center';
    speaking_rate?: number;
    pre_announcement?: string;
    post_announcement?: string;
  };
  requires_story_pause: boolean;
  estimated_duration: number;
}

interface NavigationVoiceResponse {
  has_instruction: boolean;
  instruction?: NavigationInstruction;
  audio_url?: string;
  next_check_seconds: number;
  spatial_audio_config?: {
    position: { x: number; y: number; z: number };
    environment?: string;
  };
}

interface NavigationContext {
  currentStepIndex: number;
  distanceToNextManeuver: number;
  timeToNextManeuver: number;
  currentSpeed: number;
  isOnHighway: boolean;
  approachingComplexIntersection: boolean;
  storyPlaying: boolean;
  audioPriority: 'navigation' | 'story' | 'balanced';
  lastInstructionTime?: Date;
}

class NavigationVoiceService {
  private isActive: boolean = false;
  private currentSound: Audio.Sound | null = null;
  private lastInstructionTime: Date | null = null;
  private audioMixer: any = null;
  private currentRouteId: string | null = null;
  
  // Audio settings for navigation voice
  private navigationVoiceSettings = {
    volume: 1.0,
    shouldCorrectPitch: true,
    pitchCorrectionQuality: Audio.PitchCorrectionQuality.High,
  };

  /**
   * Initialize navigation voice for a route
   */
  async initializeForRoute(routeId: string, routeData: any): Promise<void> {
    try {
      this.currentRouteId = routeId;
      this.isActive = true;
      
      // Process route for voice navigation
      const response = await apiClient.post('/api/navigation/voice/initialize', {
        route_data: routeData,
        current_location: {
          lat: routeData.start_location.lat,
          lng: routeData.start_location.lng
        },
        journey_context: {
          navigation_preferences: {
            verbosity: 'normal',
            spatial_audio_enabled: true
          }
        }
      });
      
      logger.debug('Navigation voice initialized:', response.data);
      
      // Initialize spatial audio for navigation
      await spatialAudioService.setEnvironment('car_interior');
      
    } catch (error) {
      logger.error('Failed to initialize navigation voice:', error);
      throw error;
    }
  }

  /**
   * Get and play navigation instruction based on current context
   */
  async checkAndPlayInstruction(
    location: LocationObject,
    navigationContext: NavigationContext
  ): Promise<void> {
    try {
      if (!this.isActive) return;
      
      // Check if we should get an instruction
      const response = await apiClient.post('/api/navigation/voice/instruction', {
        route_id: this.currentRouteId,
        navigation_context: {
          current_step_index: navigationContext.currentStepIndex,
          distance_to_next_maneuver: navigationContext.distanceToNextManeuver,
          time_to_next_maneuver: navigationContext.timeToNextManeuver,
          current_speed: navigationContext.currentSpeed,
          is_on_highway: navigationContext.isOnHighway,
          approaching_complex_intersection: navigationContext.approachingComplexIntersection,
          story_playing: navigationContext.storyPlaying,
          last_instruction_time: this.lastInstructionTime?.toISOString()
        },
        orchestration_state: {
          route_id: this.currentRouteId,
          audio_priority: navigationContext.audioPriority
        }
      });
      
      const voiceResponse: NavigationVoiceResponse = response.data;
      
      if (voiceResponse.has_instruction && voiceResponse.instruction && voiceResponse.audio_url) {
        await this.playNavigationInstruction(
          voiceResponse.instruction,
          voiceResponse.audio_url,
          voiceResponse.spatial_audio_config
        );
      }
      
    } catch (error) {
      logger.error('Failed to check/play navigation instruction:', error);
    }
  }

  /**
   * Play a navigation instruction with spatial audio
   */
  private async playNavigationInstruction(
    instruction: NavigationInstruction,
    audioUrl: string,
    spatialConfig?: any
  ): Promise<void> {
    try {
      // Stop any current instruction
      if (this.currentSound) {
        await this.currentSound.unloadAsync();
        this.currentSound = null;
      }
      
      // Handle audio orchestration based on priority
      if (instruction.requires_story_pause) {
        await audioOrchestrationService.pauseStory();
      }
      
      // Create and load the sound
      const { sound } = await Audio.Sound.createAsync(
        { uri: audioUrl },
        this.navigationVoiceSettings
      );
      
      this.currentSound = sound;
      
      // Apply spatial positioning if available
      if (spatialConfig && instruction.audio_cues.spatial_position) {
        // Get distance from spatial config if available
        const distanceToManeuver = spatialConfig.distanceToManeuver;
        const position = this.getPositionForDirection(
          instruction.audio_cues.spatial_position,
          distanceToManeuver
        );
        
        // Configure spatial audio for navigation voice
        await spatialAudioService.setSourcePosition(sound, position);
        
        // Add distance attenuation for depth perception
        const distanceModel = {
          type: 'linear' as const,
          maxDistance: 10,
          refDistance: 1,
          rolloffFactor: 1
        };
        await spatialAudioService.setDistanceModel(sound, distanceModel);
        
        // Apply directional cone for focused audio
        if (instruction.audio_cues.spatial_position !== 'center') {
          const coneConfig = {
            innerAngle: 60,
            outerAngle: 120,
            outerGain: 0.4
          };
          await spatialAudioService.setConeParameters(sound, coneConfig);
        }
      }
      
      // Apply volume boost if specified
      if (instruction.audio_cues.volume_boost) {
        const boostedVolume = Math.min(1.0, this.navigationVoiceSettings.volume + (instruction.audio_cues.volume_boost * 0.1));
        await sound.setVolumeAsync(boostedVolume);
      }
      
      // Apply speaking rate if specified
      if (instruction.audio_cues.speaking_rate) {
        await sound.setRateAsync(instruction.audio_cues.speaking_rate, this.navigationVoiceSettings.shouldCorrectPitch);
      }
      
      // Set up completion handler
      sound.setOnPlaybackStatusUpdate(async (status) => {
        if (status.isLoaded && status.didJustFinish) {
          await this.handleInstructionComplete(instruction);
        }
      });
      
      // Play the instruction
      await sound.playAsync();
      this.lastInstructionTime = new Date();
      
      // Log for debugging
      logger.debug(`Playing navigation instruction: ${instruction.text}`);
      
    } catch (error) {
      logger.error('Failed to play navigation instruction:', error);
    }
  }

  /**
   * Get 3D position for directional audio based on turn direction and distance
   */
  private getPositionForDirection(
    direction: 'left' | 'right' | 'center',
    distanceToManeuver?: number
  ): { x: number; y: number; z: number } {
    // Calculate z position based on distance (closer = more forward)
    let zPosition = 2.0; // Default forward position
    if (distanceToManeuver) {
      // Map distance to z position (0-100m = 0.5-3.0 z)
      zPosition = Math.max(0.5, Math.min(3.0, distanceToManeuver / 33));
    }
    
    switch (direction) {
      case 'left':
        return { 
          x: -2.5, // Further left for clarity
          y: 0, 
          z: zPosition 
        };
      case 'right':
        return { 
          x: 2.5, // Further right for clarity
          y: 0, 
          z: zPosition 
        };
      case 'center':
      default:
        return { 
          x: 0, 
          y: 0, 
          z: zPosition 
        };
    }
  }

  /**
   * Handle instruction completion
   */
  private async handleInstructionComplete(instruction: NavigationInstruction): Promise<void> {
    // Clean up sound
    if (this.currentSound) {
      await this.currentSound.unloadAsync();
      this.currentSound = null;
    }
    
    // Resume story if it was paused
    if (instruction.requires_story_pause && instruction.audio_cues.post_announcement === 'gentle_resume') {
      await audioOrchestrationService.resumeStory();
    }
  }

  /**
   * Play a navigation alert tone
   */
  async playNavigationTone(toneType: string): Promise<void> {
    try {
      const toneUrl = await this.getToneUrl(toneType);
      const { sound } = await Audio.Sound.createAsync(
        { uri: toneUrl },
        { volume: 0.5 }
      );
      
      await sound.playAsync();
      
      // Auto-unload after playing
      sound.setOnPlaybackStatusUpdate(async (status) => {
        if (status.isLoaded && status.didJustFinish) {
          await sound.unloadAsync();
        }
      });
      
    } catch (error) {
      logger.error('Failed to play navigation tone:', error);
    }
  }

  /**
   * Get URL for navigation tone
   */
  private async getToneUrl(toneType: string): Promise<string> {
    // In production, these would be fetched from backend or stored locally
    const toneMap: { [key: string]: string } = {
      'navigation_chime': 'https://storage.googleapis.com/roadtrip-audio/tones/nav_chime.mp3',
      'navigation_alert': 'https://storage.googleapis.com/roadtrip-audio/tones/nav_alert.mp3',
      'navigation_urgent': 'https://storage.googleapis.com/roadtrip-audio/tones/nav_urgent.mp3',
      'navigation_confirm': 'https://storage.googleapis.com/roadtrip-audio/tones/nav_confirm.mp3'
    };
    
    return toneMap[toneType] || toneMap['navigation_chime'];
  }

  /**
   * Update navigation voice settings
   */
  async updateSettings(settings: Partial<typeof this.navigationVoiceSettings>): Promise<void> {
    this.navigationVoiceSettings = {
      ...this.navigationVoiceSettings,
      ...settings
    };
  }

  /**
   * Stop navigation voice
   */
  async stop(): Promise<void> {
    this.isActive = false;
    
    if (this.currentSound) {
      await this.currentSound.stopAsync();
      await this.currentSound.unloadAsync();
      this.currentSound = null;
    }
    
    this.lastInstructionTime = null;
    this.currentRouteId = null;
  }

  /**
   * Mute/unmute navigation voice
   */
  async setMuted(muted: boolean): Promise<void> {
    if (this.currentSound) {
      await this.currentSound.setVolumeAsync(muted ? 0 : this.navigationVoiceSettings.volume);
    }
  }

  /**
   * Check if navigation voice is active
   */
  isNavigationActive(): boolean {
    return this.isActive;
  }

  /**
   * Get last instruction time
   */
  getLastInstructionTime(): Date | null {
    return this.lastInstructionTime;
  }
}

export const navigationVoiceService = new NavigationVoiceService();