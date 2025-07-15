/**
 * Enhanced Voice Service
 * Integrates Google Cloud TTS with personality system
 */

import googleCloudTTS from '../googleCloudTTS';
import audioPlaybackService from '../audioPlaybackService';
import { VoicePersonality } from './voicePersonalities';
import { Story } from '@/types/cultural';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface VoiceServiceConfig {
  defaultPersonalityId: string;
  autoPlayStories: boolean;
  musicVolume: number;
  effectsVolume: number;
  speechRate: number;
}

class EnhancedVoiceService {
  private config: VoiceServiceConfig = {
    defaultPersonalityId: 'navigator',
    autoPlayStories: true,
    musicVolume: 0.3,
    effectsVolume: 0.5,
    speechRate: 1.0,
  };

  private currentPersonalityId: string = 'navigator';
  private isNarrating: boolean = false;
  private currentStoryId: string | null = null;

  constructor() {
    this.loadConfig();
  }

  private async loadConfig(): Promise<void> {
    try {
      const savedConfig = await AsyncStorage.getItem('voice_service_config');
      if (savedConfig) {
        this.config = { ...this.config, ...JSON.parse(savedConfig) };
      }
      
      const savedPersonality = await AsyncStorage.getItem('current_personality');
      if (savedPersonality) {
        this.currentPersonalityId = savedPersonality;
      }
    } catch (error) {
      console.error('Failed to load voice config:', error);
    }
  }

  private async saveConfig(): Promise<void> {
    try {
      await AsyncStorage.setItem('voice_service_config', JSON.stringify(this.config));
      await AsyncStorage.setItem('current_personality', this.currentPersonalityId);
    } catch (error) {
      console.error('Failed to save voice config:', error);
    }
  }

  /**
   * Set the current voice personality
   */
  async setPersonality(personalityId: string): Promise<void> {
    this.currentPersonalityId = personalityId;
    await this.saveConfig();
  }

  /**
   * Get the current personality ID
   */
  getCurrentPersonality(): string {
    return this.currentPersonalityId;
  }

  /**
   * Synthesize speech with current personality
   */
  async synthesizeSpeech(
    text: string,
    options?: {
      immediate?: boolean;
      volume?: number;
      ssml?: boolean;
    }
  ): Promise<void> {
    try {
      // Synthesize audio using Google Cloud TTS
      const audioPath = await googleCloudTTS.synthesizeSpeech({
        text,
        personalityId: this.currentPersonalityId,
        ssml: options?.ssml || false,
      });

      // Play the audio
      const playbackOptions = {
        id: `speech-${Date.now()}`,
        uri: audioPath,
        type: 'story' as const,
        volume: options?.volume || 1.0,
        fadeIn: 0.2,
        fadeOut: 0.2,
      };

      if (options?.immediate) {
        await audioPlaybackService.playImmediate(playbackOptions);
      } else {
        await audioPlaybackService.play(playbackOptions);
      }
    } catch (error) {
      console.error('Failed to synthesize speech:', error);
      throw error;
    }
  }

  /**
   * Start narrating a story
   */
  async startStoryNarration(story: Story): Promise<void> {
    if (this.isNarrating) {
      await this.stopNarration();
    }

    this.isNarrating = true;
    this.currentStoryId = story.id;

    try {
      // Add introductory catchphrase based on personality
      const intro = this.getPersonalityIntro();
      if (intro) {
        await this.synthesizeSpeech(intro, { immediate: true, ssml: true });
      }

      // Narrate the main story content
      await this.synthesizeSpeech(story.content, { 
        immediate: false,
        ssml: true 
      });

      // Add concluding remark
      const outro = this.getPersonalityOutro();
      if (outro) {
        await this.synthesizeSpeech(outro, { immediate: false, ssml: true });
      }
    } catch (error) {
      console.error('Failed to start story narration:', error);
      this.isNarrating = false;
      this.currentStoryId = null;
      throw error;
    }
  }

  /**
   * Pause current narration
   */
  async pauseNarration(): Promise<void> {
    await audioPlaybackService.pause();
  }

  /**
   * Resume current narration
   */
  async resumeNarration(): Promise<void> {
    await audioPlaybackService.resume();
  }

  /**
   * Stop all narration
   */
  async stopNarration(): Promise<void> {
    await audioPlaybackService.stop();
    this.isNarrating = false;
    this.currentStoryId = null;
  }

  /**
   * Speak a navigation instruction
   */
  async speakNavigationInstruction(instruction: string): Promise<void> {
    // Navigation instructions should interrupt current playback
    const audioPath = await googleCloudTTS.synthesizeSpeech({
      text: instruction,
      personalityId: 'navigator', // Always use navigator for directions
      ssml: false,
    });

    await audioPlaybackService.playImmediate({
      id: `nav-${Date.now()}`,
      uri: audioPath,
      type: 'navigation',
      volume: 1.0,
      fadeIn: 0.1,
      fadeOut: 0.1,
    });
  }

  /**
   * Speak an alert or warning
   */
  async speakAlert(message: string): Promise<void> {
    const audioPath = await googleCloudTTS.synthesizeSpeech({
      text: message,
      personalityId: 'navigator',
      ssml: false,
      voiceConfig: {
        speakingRate: 1.2, // Slightly faster for urgency
        pitch: 2.0, // Slightly higher pitch
      },
    });

    await audioPlaybackService.playImmediate({
      id: `alert-${Date.now()}`,
      uri: audioPath,
      type: 'alert',
      volume: 1.0,
      fadeIn: 0,
      fadeOut: 0,
    });
  }

  /**
   * Preload common phrases for faster response
   */
  async preloadCommonPhrases(): Promise<void> {
    const personalities = ['navigator', 'friendly-guide', 'educational-expert'];
    await googleCloudTTS.preloadPersonalityVoices(personalities);
  }

  /**
   * Get personality-specific intro
   */
  private getPersonalityIntro(): string | null {
    const intros: Record<string, string> = {
      'mickey-mouse': '<speak><prosody rate="fast" pitch="+8st">Oh boy! Have I got a story for you!</prosody></speak>',
      'santa-claus': '<speak><prosody rate="slow" pitch="-4st">Ho ho ho! Gather round for a special tale!</prosody></speak>',
      'rock-dj': '<speak><prosody rate="fast">Alright road trippers, crank it up!</prosody></speak>',
      'southern-charm': '<speak><prosody rate="slow">Well, honey, let me tell you something fascinating!</prosody></speak>',
      'educational-expert': '<speak>Here\'s an interesting fact about this location.</speak>',
    };

    return intros[this.currentPersonalityId] || null;
  }

  /**
   * Get personality-specific outro
   */
  private getPersonalityOutro(): string | null {
    const outros: Record<string, string> = {
      'mickey-mouse': '<speak><prosody rate="fast" pitch="+8st">See ya real soon!</prosody></speak>',
      'santa-claus': '<speak><prosody rate="slow" pitch="-4st">Remember to stay on the nice list!</prosody></speak>',
      'rock-dj': '<speak><prosody rate="fast">Keep on rockin\' down the highway!</prosody></speak>',
      'southern-charm': '<speak><prosody rate="slow">Y\'all come back now, ya hear?</prosody></speak>',
      'educational-expert': '<speak>I hope you found that informative.</speak>',
    };

    return outros[this.currentPersonalityId] || null;
  }

  /**
   * Update voice configuration
   */
  async updateConfig(updates: Partial<VoiceServiceConfig>): Promise<void> {
    this.config = { ...this.config, ...updates };
    await this.saveConfig();
  }

  /**
   * Get current configuration
   */
  getConfig(): VoiceServiceConfig {
    return { ...this.config };
  }

  /**
   * Check if currently narrating
   */
  isCurrentlyNarrating(): boolean {
    return this.isNarrating;
  }

  /**
   * Get current story ID
   */
  getCurrentStoryId(): string | null {
    return this.currentStoryId;
  }

  /**
   * Clear TTS cache
   */
  async clearCache(): Promise<void> {
    await googleCloudTTS.clearCache();
  }

  /**
   * Get cache size
   */
  getCacheSize(): number {
    return googleCloudTTS.getCacheSize();
  }
}

export default new EnhancedVoiceService();