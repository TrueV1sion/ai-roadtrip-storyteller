import * as Speech from 'expo-speech';
import { Platform } from 'react-native';

import { logger } from '@/services/logger';
interface SpeechOptions {
  language?: string;
  pitch?: number;
  rate?: number;
  voice?: string;
}

class VoiceService {
  private isSpeaking: boolean = false;
  private queue: { text: string; options?: SpeechOptions }[] = [];
  private defaultOptions: SpeechOptions = {
    language: 'en-US',
    pitch: 1.0,
    rate: Platform.select({ ios: 0.5, android: 1.0 }),
    voice: 'com.apple.ttsbundle.Samantha-compact',  // Default iOS voice
  };

  async initialize(): Promise<void> {
    try {
      // Get available voices
      const voices = await Speech.getAvailableVoicesAsync();
      
      // Find a suitable voice for storytelling
      const storytellerVoice = voices.find(
        (voice) =>
          voice.identifier.includes('Samantha') ||  // iOS
          voice.identifier.includes('en-us-x-sfg')  // Android
      );

      if (storytellerVoice) {
        this.defaultOptions.voice = storytellerVoice.identifier;
      }
    } catch (error) {
      logger.error('Error initializing voice service:', error);
    }
  }

  async speak(text: string, options?: SpeechOptions): Promise<void> {
    const speechOptions = {
      ...this.defaultOptions,
      ...options,
    };

    // If already speaking, add to queue
    if (this.isSpeaking) {
      this.queue.push({ text, options: speechOptions });
      return;
    }

    try {
      this.isSpeaking = true;
      await Speech.speak(text, {
        ...speechOptions,
        onDone: () => this.handleSpeechComplete(),
        onError: (error) => this.handleSpeechError(error),
      });
    } catch (error) {
      logger.error('Error speaking:', error);
      this.isSpeaking = false;
      this.processQueue();
    }
  }

  private handleSpeechComplete(): void {
    this.isSpeaking = false;
    this.processQueue();
  }

  private handleSpeechError(error: any): void {
    logger.error('Speech error:', error);
    this.isSpeaking = false;
    this.processQueue();
  }

  private async processQueue(): Promise<void> {
    if (this.queue.length > 0 && !this.isSpeaking) {
      const next = this.queue.shift();
      if (next) {
        await this.speak(next.text, next.options);
      }
    }
  }

  async stop(): Promise<void> {
    try {
      await Speech.stop();
      this.isSpeaking = false;
      this.queue = [];  // Clear queue
    } catch (error) {
      logger.error('Error stopping speech:', error);
    }
  }

  async pause(): Promise<void> {
    try {
      await Speech.pause();
    } catch (error) {
      logger.error('Error pausing speech:', error);
    }
  }

  async resume(): Promise<void> {
    try {
      await Speech.resume();
    } catch (error) {
      logger.error('Error resuming speech:', error);
    }
  }

  async isSpeakingNow(): Promise<boolean> {
    try {
      return await Speech.isSpeakingAsync();
    } catch (error) {
      logger.error('Error checking speech status:', error);
      return false;
    }
  }

  // Helper method to speak a story with appropriate pacing and emphasis
  async tellStory(
    story: string,
    options?: SpeechOptions & { addPauses?: boolean }
  ): Promise<void> {
    if (options?.addPauses) {
      // Add pauses at punctuation for more natural storytelling
      const sentences = story.split(/([.!?]+)\s+/);
      for (let i = 0; i < sentences.length; i++) {
        const sentence = sentences[i].trim();
        if (sentence) {
          // Add longer pause between sentences
          if (i > 0) {
            await new Promise((resolve) => setTimeout(resolve, 800));
          }
          await this.speak(sentence, options);
        }
      }
    } else {
      await this.speak(story, options);
    }
  }
}

export const voiceService = new VoiceService(); 