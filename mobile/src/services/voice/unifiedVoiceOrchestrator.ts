/**
 * Unified Voice Orchestrator for Mobile App
 * 
 * This service connects to the backend's UnifiedVoiceOrchestrator to provide
 * a seamless "one agent" experience. It manages all voice interactions,
 * making complex backend operations invisible to the user.
 */

import { EventEmitter } from 'events';
import apiClient from '../apiClient';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Audio } from 'expo-av';
import * as Speech from 'expo-speech';
import * as Location from 'expo-location';
import * as Permissions from 'expo-permissions';
import { Platform } from 'react-native';
import { voicePerformanceOptimizer } from './voicePerformanceOptimizer';

interface VoiceResponse {
  voice_audio: string; // Base64 encoded audio
  transcript: string;
  visual_data?: any;
  actions_taken?: any[];
  state: ConversationState;
}

interface ProactiveSuggestion {
  voice_audio: string;
  transcript: string;
  trigger: string;
  can_dismiss: boolean;
}

type ConversationState = 'idle' | 'gathering_info' | 'awaiting_confirmation' | 'processing_request' | 'telling_story';

interface LocationData {
  lat: number;
  lng: number;
  heading?: number;
  speed?: number;
}

interface ContextData {
  personality?: string;
  story_playing?: boolean;
  audio_priority?: 'balanced' | 'navigation' | 'story';
  emergency_mode?: boolean;
  party_size?: number;
  user_preferences?: any;
}

class UnifiedVoiceOrchestrator extends EventEmitter {
  private recording?: Audio.Recording;
  private playback?: Audio.Sound;
  private isRecording: boolean = false;
  private isPlaying: boolean = false;
  private currentLocation?: LocationData;
  private locationSubscription?: Location.LocationSubscription;
  private conversationContext: ContextData = {
    personality: 'wise_narrator',
    audio_priority: 'balanced',
    party_size: 2
  };
  private proactiveSuggestionInterval?: NodeJS.Timeout;
  private lastProactiveSuggestion: number = 0;

  constructor() {
    super();
    this.initialize();
  }

  private async initialize() {
    // Setup audio session for iOS
    if (Platform.OS === 'ios') {
      await Audio.setAudioModeAsync({
        playsInSilentModeIOS: true,
        staysActiveInBackground: true,
        interruptionModeIOS: Audio.INTERRUPTION_MODE_IOS_DUCK_OTHERS,
        shouldDuckAndroid: true,
        interruptionModeAndroid: Audio.INTERRUPTION_MODE_ANDROID_DUCK_OTHERS,
        playThroughEarpieceAndroid: false,
      });
    }

    // Load saved preferences
    await this.loadPreferences();
    
    // Start location tracking
    await this.startLocationTracking();
    
    // Start proactive suggestion monitoring
    this.startProactiveSuggestions();
    
    // Initialize performance optimizer
    await voicePerformanceOptimizer.optimizeForNetwork();
    
    // Listen for performance events
    voicePerformanceOptimizer.on('performanceThresholdExceeded', (data) => {
      console.warn('Performance threshold exceeded:', data);
      this.emit('performanceWarning', data);
    });
    
    // Process offline queue when back online
    voicePerformanceOptimizer.on('networkOptimization', (mode) => {
      if (mode === 'wifi' || mode === 'cellular') {
        voicePerformanceOptimizer.processOfflineQueue();
      }
    });
  }

  /**
   * Main entry point for voice interactions
   * This is the ONLY method the UI needs to call for voice
   */
  async startVoiceInteraction(): Promise<void> {
    if (this.isRecording) {
      await this.stopRecording();
    } else {
      await this.startRecording();
    }
  }

  private async startRecording(): Promise<void> {
    try {
      // Request permissions
      const { status } = await Audio.requestPermissionsAsync();
      if (status !== 'granted') {
        this.emit('error', 'Microphone permission not granted');
        return;
      }

      // Prepare recording
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      // Start recording
      this.recording = new Audio.Recording();
      await this.recording.prepareToRecordAsync(Audio.RECORDING_OPTIONS_PRESET_HIGH_QUALITY);
      await this.recording.startAsync();
      
      this.isRecording = true;
      this.emit('recordingStarted');
      
      // Auto-stop after 10 seconds max
      setTimeout(() => {
        if (this.isRecording) {
          this.stopRecording();
        }
      }, 10000);
      
    } catch (error) {
      console.error('Failed to start recording:', error);
      this.emit('error', 'Failed to start recording');
    }
  }

  private async stopRecording(): Promise<void> {
    if (!this.recording || !this.isRecording) return;

    try {
      this.isRecording = false;
      this.emit('recordingStopped');
      
      // Stop and unload recording
      await this.recording.stopAndUnloadAsync();
      const uri = this.recording.getURI();
      
      if (!uri) {
        this.emit('error', 'No recording found');
        return;
      }

      // Convert to base64 for sending to backend
      const audioData = await this.getAudioBase64(uri);
      
      // Send to backend unified orchestrator
      await this.processVoiceInput(audioData);
      
      // Clean up
      this.recording = undefined;
      
    } catch (error) {
      console.error('Failed to stop recording:', error);
      this.emit('error', 'Failed to process recording');
    }
  }

  /**
   * Process voice input through the backend's unified orchestrator
   */
  private async processVoiceInput(audioBase64: string): Promise<void> {
    try {
      this.emit('processing');
      
      // Get current location
      const location = this.currentLocation || { lat: 0, lng: 0 };
      
      // Measure performance
      const response = await voicePerformanceOptimizer.measurePerformance(
        'voice_processing',
        async () => {
          // Try cache first for intent analysis
          const cacheKey = `voice_intent:${audioBase64.substring(0, 100)}`;
          
          return await voicePerformanceOptimizer.withCache(
            cacheKey,
            async () => {
              // Call backend unified voice orchestrator
              return await apiClient.post<VoiceResponse>('/api/voice/process', {
                audio_input: audioBase64,
                location,
                context_data: this.conversationContext
              });
            },
            300 // 5 minute cache for voice responses
          );
        }
      );

      const data = response.data;
      
      // Emit the transcript immediately for UI feedback
      this.emit('transcriptReceived', data.transcript);
      
      // Play the voice response
      if (data.voice_audio) {
        await this.playVoiceResponse(data.voice_audio);
      }
      
      // Emit visual data if any (for when stopped)
      if (data.visual_data) {
        this.emit('visualDataReceived', data.visual_data);
      }
      
      // Update conversation state
      this.emit('stateChanged', data.state);
      
      // Handle any actions taken
      if (data.actions_taken && data.actions_taken.length > 0) {
        this.emit('actionsCompleted', data.actions_taken);
      }
      
    } catch (error) {
      console.error('Failed to process voice input:', error);
      
      // Check if we can handle offline
      const isOffline = error.message?.includes('Network') || error.code === 'NETWORK_ERROR';
      
      if (isOffline) {
        // Queue for offline processing
        await voicePerformanceOptimizer.queueForOffline('voice_process', {
          audioBase64,
          location: this.currentLocation,
          context: this.conversationContext
        });
        
        this.emit('offlineMode');
        await this.speakLocally("I'm offline right now, but I'll process this when we reconnect.");
      } else {
        this.emit('error', 'Failed to process your request');
        await this.speakLocally("I'm having trouble understanding that. Could you try again?");
      }
    }
  }

  /**
   * Play voice response from backend
   */
  private async playVoiceResponse(audioBase64: string): Promise<void> {
    try {
      this.isPlaying = true;
      this.emit('playbackStarted');
      
      // Create temporary file URI for the audio
      const fileUri = `${Audio.RecordingOptionsPresets.HIGH_QUALITY.android.outputFormat}`;
      
      // Create and load sound object
      const { sound } = await Audio.Sound.createAsync(
        { uri: `data:audio/mp3;base64,${audioBase64}` },
        { shouldPlay: true }
      );
      
      this.playback = sound;
      
      // Set up playback status update
      sound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded && status.didJustFinish) {
          this.onPlaybackFinished();
        }
      });
      
    } catch (error) {
      console.error('Failed to play audio:', error);
      // Fallback to text-to-speech
      await this.speakLocally(audioBase64);
    }
  }

  /**
   * Fallback local TTS
   */
  private async speakLocally(text: string): Promise<void> {
    const options = {
      language: 'en-US',
      pitch: 1.0,
      rate: 0.9,
    };
    
    await Speech.speak(text, options);
  }

  private onPlaybackFinished(): void {
    this.isPlaying = false;
    this.emit('playbackFinished');
    
    if (this.playback) {
      this.playback.unloadAsync();
      this.playback = undefined;
    }
  }

  /**
   * Start location tracking for context
   */
  private async startLocationTracking(): Promise<void> {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        console.log('Location permission not granted');
        return;
      }

      // Get initial location
      const location = await Location.getCurrentPositionAsync({});
      this.currentLocation = {
        lat: location.coords.latitude,
        lng: location.coords.longitude,
        heading: location.coords.heading || undefined,
        speed: location.coords.speed || undefined,
      };

      // Subscribe to location updates
      this.locationSubscription = await Location.watchPositionAsync(
        {
          accuracy: Location.Accuracy.BestForNavigation,
          timeInterval: 5000,
          distanceInterval: 10,
        },
        (location) => {
          this.currentLocation = {
            lat: location.coords.latitude,
            lng: location.coords.longitude,
            heading: location.coords.heading || undefined,
            speed: location.coords.speed || undefined,
          };
          
          this.emit('locationUpdated', this.currentLocation);
        }
      );
    } catch (error) {
      console.error('Failed to start location tracking:', error);
    }
  }

  /**
   * Monitor for proactive suggestions
   */
  private startProactiveSuggestions(): void {
    // Check every 30 seconds for proactive suggestions
    this.proactiveSuggestionInterval = setInterval(async () => {
      // Don't suggest if actively in conversation
      if (this.isRecording || this.isPlaying) return;
      
      // Rate limit suggestions (at least 5 minutes apart)
      const now = Date.now();
      if (now - this.lastProactiveSuggestion < 300000) return;
      
      try {
        // Determine trigger based on context
        const trigger = this.determineProactiveTrigger();
        if (!trigger) return;
        
        const response = await apiClient.post<ProactiveSuggestion>('/api/voice/proactive', {
          user_id: await this.getUserId(),
          trigger,
          context_data: {
            ...this.conversationContext,
            location: this.currentLocation,
            time_of_day: new Date().getHours(),
          }
        });
        
        if (response.data) {
          this.lastProactiveSuggestion = now;
          this.emit('proactiveSuggestion', response.data);
          
          // Play the suggestion
          await this.playVoiceResponse(response.data.voice_audio);
        }
      } catch (error) {
        console.error('Failed to get proactive suggestion:', error);
      }
    }, 30000);
  }

  private determineProactiveTrigger(): string | null {
    const hour = new Date().getHours();
    
    // Meal time triggers
    if (hour === 12 || hour === 18) return 'meal_time';
    
    // Check speed for rest suggestions
    if (this.currentLocation?.speed && this.currentLocation.speed < 5) {
      return 'scenic_ahead';
    }
    
    // Random chance for interesting facts
    if (Math.random() < 0.1) return 'scenic_ahead';
    
    return null;
  }

  /**
   * Update user preferences
   */
  async updatePreferences(preferences: Partial<ContextData>): Promise<void> {
    this.conversationContext = {
      ...this.conversationContext,
      ...preferences
    };
    
    await AsyncStorage.setItem('@voice_preferences', JSON.stringify(this.conversationContext));
    this.emit('preferencesUpdated', this.conversationContext);
  }

  /**
   * Load saved preferences
   */
  private async loadPreferences(): Promise<void> {
    try {
      const saved = await AsyncStorage.getItem('@voice_preferences');
      if (saved) {
        this.conversationContext = JSON.parse(saved);
      }
    } catch (error) {
      console.error('Failed to load preferences:', error);
    }
  }

  /**
   * Get or create user ID
   */
  private async getUserId(): Promise<string> {
    let userId = await AsyncStorage.getItem('@user_id');
    if (!userId) {
      userId = `mobile_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      await AsyncStorage.setItem('@user_id', userId);
    }
    return userId;
  }

  /**
   * Convert audio file to base64
   */
  private async getAudioBase64(uri: string): Promise<string> {
    // In a real implementation, you'd use react-native-fs or similar
    // For now, return placeholder
    return 'audio_base64_placeholder';
  }

  /**
   * Clean up resources
   */
  async cleanup(): Promise<void> {
    if (this.recording) {
      await this.recording.stopAndUnloadAsync();
    }
    
    if (this.playback) {
      await this.playback.unloadAsync();
    }
    
    if (this.locationSubscription) {
      this.locationSubscription.remove();
    }
    
    if (this.proactiveSuggestionInterval) {
      clearInterval(this.proactiveSuggestionInterval);
    }
  }
}

// Export singleton instance
export const unifiedVoiceOrchestrator = new UnifiedVoiceOrchestrator();
export default unifiedVoiceOrchestrator;