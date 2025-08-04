/**
 * Voice Recognition Service for handling speech-to-text functionality.
 * Uses @react-native-voice/voice for native voice recognition.
 */
import Voice, {
  SpeechRecognizedEvent,
  SpeechResultsEvent,
  SpeechErrorEvent,
  SpeechEndEvent,
  SpeechStartEvent,
  SpeechVolumeChangeEvent,
} from '@react-native-voice/voice';
import { Platform } from 'react-native';

import { logger } from '@/services/logger';
export interface VoiceRecognitionOptions {
  language?: string;
  showPartialResults?: boolean;
  maxAlternatives?: number;
  continuous?: boolean;
}

export interface VoiceRecognitionCallbacks {
  onStart?: () => void;
  onEnd?: () => void;
  onError?: (error: any) => void;
  onResults?: (results: string[]) => void;
  onPartialResults?: (results: string[]) => void;
  onVolumeChanged?: (volume: number) => void;
}

class VoiceRecognitionService {
  private isListening: boolean = false;
  private callbacks: VoiceRecognitionCallbacks = {};
  private defaultOptions: VoiceRecognitionOptions = {
    language: 'en-US',
    showPartialResults: true,
    maxAlternatives: 1,
    continuous: false,
  };

  constructor() {
    // Set up event listeners
    Voice.onSpeechStart = this.onSpeechStart.bind(this);
    Voice.onSpeechEnd = this.onSpeechEnd.bind(this);
    Voice.onSpeechError = this.onSpeechError.bind(this);
    Voice.onSpeechResults = this.onSpeechResults.bind(this);
    Voice.onSpeechPartialResults = this.onSpeechPartialResults.bind(this);
    Voice.onSpeechVolumeChanged = this.onSpeechVolumeChanged.bind(this);
  }

  /**
   * Initialize voice recognition service.
   */
  async initialize(): Promise<boolean> {
    try {
      const isAvailable = await Voice.isAvailable();
      if (!isAvailable) {
        logger.warn('Voice recognition is not available on this device');
        return false;
      }
      
      logger.debug('Voice recognition service initialized');
      return true;
    } catch (error) {
      logger.error('Error initializing voice recognition:', error);
      return false;
    }
  }

  /**
   * Start listening for voice input.
   */
  async startListening(
    options?: VoiceRecognitionOptions,
    callbacks?: VoiceRecognitionCallbacks
  ): Promise<void> {
    if (this.isListening) {
      logger.warn('Already listening');
      return;
    }

    try {
      // Store callbacks
      this.callbacks = callbacks || {};
      
      // Merge options with defaults
      const recognitionOptions = {
        ...this.defaultOptions,
        ...options,
      };

      // Configure voice recognition
      const voiceOptions: any = {
        language: recognitionOptions.language,
      };

      if (Platform.OS === 'ios') {
        voiceOptions.partialResults = recognitionOptions.showPartialResults;
      }

      // Start recognition
      await Voice.start(recognitionOptions.language || 'en-US');
      this.isListening = true;
      
      logger.debug('Started voice recognition');
    } catch (error) {
      logger.error('Error starting voice recognition:', error);
      this.callbacks.onError?.(error);
      throw error;
    }
  }

  /**
   * Stop listening for voice input.
   */
  async stopListening(): Promise<void> {
    if (!this.isListening) {
      return;
    }

    try {
      await Voice.stop();
      this.isListening = false;
      logger.debug('Stopped voice recognition');
    } catch (error) {
      logger.error('Error stopping voice recognition:', error);
      throw error;
    }
  }

  /**
   * Cancel voice recognition (no results will be returned).
   */
  async cancelListening(): Promise<void> {
    if (!this.isListening) {
      return;
    }

    try {
      await Voice.cancel();
      this.isListening = false;
      logger.debug('Cancelled voice recognition');
    } catch (error) {
      logger.error('Error cancelling voice recognition:', error);
      throw error;
    }
  }

  /**
   * Destroy voice recognition instance and clean up.
   */
  async destroy(): Promise<void> {
    try {
      await Voice.destroy();
      this.isListening = false;
      this.callbacks = {};
      logger.debug('Voice recognition service destroyed');
    } catch (error) {
      logger.error('Error destroying voice recognition:', error);
    }
  }

  /**
   * Check if currently listening.
   */
  public isCurrentlyListening(): boolean {
    return this.isListening;
  }

  /**
   * Get supported languages.
   */
  async getSupportedLanguages(): Promise<string[]> {
    try {
      const languages = await Voice.getSpeechRecognitionServices();
      return languages || ['en-US'];
    } catch (error) {
      logger.error('Error getting supported languages:', error);
      return ['en-US'];
    }
  }

  /**
   * Process voice command for navigation.
   */
  parseNavigationCommand(text: string): { isNavigation: boolean; destination?: string } {
    const navigationPatterns = [
      /^navigate to (.+)$/i,
      /^take me to (.+)$/i,
      /^go to (.+)$/i,
      /^drive to (.+)$/i,
      /^directions to (.+)$/i,
      /^find (.+)$/i,
      /^where is (.+)$/i,
      /^show me (.+)$/i,
    ];

    const lowerText = text.toLowerCase().trim();
    
    for (const pattern of navigationPatterns) {
      const match = lowerText.match(pattern);
      if (match && match[1]) {
        return {
          isNavigation: true,
          destination: match[1].trim(),
        };
      }
    }

    // Check for simple destination without command prefix
    if (lowerText.includes('starbucks') || 
        lowerText.includes('gas station') || 
        lowerText.includes('restaurant') ||
        lowerText.includes('hotel') ||
        lowerText.includes('airport')) {
      return {
        isNavigation: true,
        destination: lowerText,
      };
    }

    return { isNavigation: false };
  }

  /**
   * Process voice command for story control.
   */
  parseStoryCommand(text: string): { command?: string; recognized: boolean } {
    const lowerText = text.toLowerCase().trim();
    
    const commands = {
      'stop': ['stop', 'stop story', 'stop talking', 'be quiet'],
      'pause': ['pause', 'pause story', 'hold on', 'wait'],
      'resume': ['resume', 'continue', 'keep going', 'go on'],
      'repeat': ['repeat', 'say that again', 'what did you say'],
      'skip': ['skip', 'next', 'skip story'],
      'louder': ['louder', 'volume up', 'speak up'],
      'quieter': ['quieter', 'volume down', 'softer'],
    };

    for (const [command, phrases] of Object.entries(commands)) {
      if (phrases.some(phrase => lowerText.includes(phrase))) {
        return { command, recognized: true };
      }
    }

    return { recognized: false };
  }

  // Event handlers
  private onSpeechStart(e: SpeechStartEvent): void {
    logger.debug('Speech recognition started');
    this.callbacks.onStart?.();
  }

  private onSpeechEnd(e: SpeechEndEvent): void {
    logger.debug('Speech recognition ended');
    this.isListening = false;
    this.callbacks.onEnd?.();
  }

  private onSpeechError(e: SpeechErrorEvent): void {
    logger.error('Speech recognition error:', e.error);
    this.isListening = false;
    this.callbacks.onError?.(e.error);
  }

  private onSpeechResults(e: SpeechResultsEvent): void {
    if (e.value) {
      logger.debug('Speech recognition results:', e.value);
      this.callbacks.onResults?.(e.value);
    }
  }

  private onSpeechPartialResults(e: SpeechResultsEvent): void {
    if (e.value) {
      logger.debug('Speech recognition partial results:', e.value);
      this.callbacks.onPartialResults?.(e.value);
    }
  }

  private onSpeechVolumeChanged(e: SpeechVolumeChangeEvent): void {
    if (Platform.OS === 'ios' && e.value !== undefined) {
      this.callbacks.onVolumeChanged?.(e.value);
    }
  }
}

// Singleton instance
export const voiceRecognitionService = new VoiceRecognitionService();
export default voiceRecognitionService;