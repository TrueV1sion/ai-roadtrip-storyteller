/**
 * Voice Assistant Service
 * 
 * Provides unified interface for all voice interactions with the backend
 * MasterOrchestrationAgent. Handles voice recording, transcription, and
 * response processing including booking opportunities.
 */

import { Audio } from 'expo-av';
import * as Speech from 'expo-speech';
import { ApiClient } from './api/ApiClient';

import { logger } from '@/services/logger';
export interface VoiceAssistantResponse {
  text: string;
  audioUrl?: string;
  sessionId: string;
  actions: any[];
  bookingOpportunities: BookingOpportunity[];
  requiresFollowup: boolean;
  conversationId?: string;
}

export interface BookingOpportunity {
  id: string;
  type: string;
  name: string;
  description: string;
  location: {
    address: string;
    distanceMiles: number;
    travelTimeMinutes: number;
  };
  timing: {
    durationMinutes: number;
    availableTimes: string[];
  };
  pricing: {
    range: string;
    perPerson: boolean;
  };
  availability: string;
  rating: number;
}

export interface JourneyContext {
  currentLocation: {
    latitude: number;
    longitude: number;
    name?: string;
    address?: string;
  };
  destination?: {
    latitude: number;
    longitude: number;
    name?: string;
  };
  journeyStage: 'pre_trip' | 'traveling' | 'arrived';
  passengers: any[];
  vehicleInfo?: any;
  weather?: any;
  routeInfo?: any;
}

class VoiceAssistantService {
  private apiClient: ApiClient;
  private sessionId: string;
  private recording: Audio.Recording | null = null;
  private conversationHistory: VoiceAssistantResponse[] = [];

  constructor() {
    this.apiClient = new ApiClient();
    this.sessionId = this.generateSessionId();
  }

  /**
   * Send voice or text input to the assistant
   */
  async sendMessage(
    input: string | Audio.Recording,
    journeyContext: JourneyContext,
    preferences?: any
  ): Promise<VoiceAssistantResponse> {
    try {
      let voiceInput: any = {
        sessionId: this.sessionId
      };

      if (typeof input === 'string') {
        // Text input
        voiceInput.text = input;
      } else {
        // Audio input - convert to base64
        const uri = input.getURI();
        if (uri) {
          const audioData = await this.convertAudioToBase64(uri);
          voiceInput.audioData = audioData;
        }
      }

      const requestData = {
        voiceInput,
        journeyContext,
        preferences: preferences || this.getDefaultPreferences()
      };

      const response = await this.apiClient.post<VoiceAssistantResponse>(
        '/voice-assistant/interact',
        requestData
      );

      // Store in conversation history
      this.conversationHistory.push(response);

      // Play audio response if available
      if (response.audioUrl) {
        await this.playAudioResponse(response.audioUrl);
      } else {
        // Fallback to text-to-speech
        await this.speakText(response.text);
      }

      return response;
    } catch (error) {
      logger.error('Voice assistant error:', error);
      throw error;
    }
  }

  /**
   * Start recording voice input
   */
  async startRecording(): Promise<void> {
    try {
      await Audio.requestPermissionsAsync();
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      this.recording = new Audio.Recording();
      await this.recording.prepareToRecordAsync(
        Audio.RECORDING_OPTIONS_PRESET_HIGH_QUALITY
      );
      await this.recording.startAsync();
    } catch (error) {
      logger.error('Failed to start recording:', error);
      throw error;
    }
  }

  /**
   * Stop recording and return the recording
   */
  async stopRecording(): Promise<Audio.Recording | null> {
    if (!this.recording) return null;

    try {
      await this.recording.stopAndUnloadAsync();
      const recording = this.recording;
      this.recording = null;
      return recording;
    } catch (error) {
      logger.error('Failed to stop recording:', error);
      return null;
    }
  }

  /**
   * Process a booking action
   */
  async processBookingAction(
    bookingId: string,
    action: 'confirm' | 'modify' | 'cancel',
    additionalInfo?: any
  ): Promise<any> {
    try {
      const response = await this.apiClient.post('/voice-assistant/booking-action', {
        bookingId,
        action,
        sessionId: this.sessionId,
        additionalInfo
      });

      return response;
    } catch (error) {
      logger.error('Booking action error:', error);
      throw error;
    }
  }

  /**
   * Get conversation history for current session
   */
  async getSessionHistory(limit: number = 10): Promise<any> {
    try {
      const response = await this.apiClient.get(
        `/voice-assistant/session-history/${this.sessionId}?limit=${limit}`
      );
      return response;
    } catch (error) {
      logger.error('Failed to get session history:', error);
      throw error;
    }
  }

  /**
   * End the current session
   */
  async endSession(): Promise<void> {
    try {
      await this.apiClient.post(`/voice-assistant/end-session/${this.sessionId}`, {});
      this.conversationHistory = [];
      this.sessionId = this.generateSessionId(); // Generate new session ID
    } catch (error) {
      logger.error('Failed to end session:', error);
    }
  }

  /**
   * Quick action methods for common requests
   */
  async requestStory(location: any): Promise<VoiceAssistantResponse> {
    const context: JourneyContext = {
      currentLocation: location,
      journeyStage: 'traveling',
      passengers: []
    };

    return this.sendMessage(
      "Tell me an interesting story about this area",
      context
    );
  }

  async findRestaurant(
    location: any,
    cuisine?: string,
    passengers?: any[]
  ): Promise<VoiceAssistantResponse> {
    const context: JourneyContext = {
      currentLocation: location,
      journeyStage: 'traveling',
      passengers: passengers || []
    };

    const message = cuisine
      ? `Find a ${cuisine} restaurant nearby`
      : "I'm looking for a good place to eat";

    return this.sendMessage(message, context);
  }

  async getNavigationHelp(
    currentLocation: any,
    destination: any
  ): Promise<VoiceAssistantResponse> {
    const context: JourneyContext = {
      currentLocation,
      destination,
      journeyStage: 'traveling',
      passengers: []
    };

    return this.sendMessage(
      "What's the best route to my destination?",
      context
    );
  }

  /**
   * Helper methods
   */
  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private getDefaultPreferences(): any {
    return {
      voiceId: 'default',
      speakingRate: 1.0,
      pitch: 0,
      interests: [],
      dietaryRestrictions: [],
      budgetLevel: 'moderate'
    };
  }

  private async convertAudioToBase64(uri: string): Promise<string> {
    // Implementation would convert audio file to base64
    // This is a placeholder
    return '';
  }

  private async playAudioResponse(audioUrl: string): Promise<void> {
    try {
      const { sound } = await Audio.Sound.createAsync({ uri: audioUrl });
      await sound.playAsync();
    } catch (error) {
      logger.error('Failed to play audio:', error);
      // Fallback to text-to-speech handled by caller
    }
  }

  private async speakText(text: string): Promise<void> {
    try {
      await Speech.speak(text, {
        language: 'en-US',
        pitch: 1.0,
        rate: 1.0
      });
    } catch (error) {
      logger.error('Failed to speak text:', error);
    }
  }

  /**
   * Get current conversation history
   */
  getConversationHistory(): VoiceAssistantResponse[] {
    return this.conversationHistory;
  }

  /**
   * Get active booking opportunities from the last response
   */
  getActiveBookingOpportunities(): BookingOpportunity[] {
    if (this.conversationHistory.length === 0) return [];
    
    const lastResponse = this.conversationHistory[this.conversationHistory.length - 1];
    return lastResponse.bookingOpportunities || [];
  }
}

export default new VoiceAssistantService();