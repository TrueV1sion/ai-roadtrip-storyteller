import { APIClient } from '@utils/apiUtils';
import { Story } from '@/types/cultural';
import { memoizeAsync } from '@utils/cache';
import type { AxiosRequestConfig } from 'axios';
import { AZURE_TTS_KEY, AWS_POLLY_KEY, GOOGLE_TTS_KEY } from '@/config/env';
import { VoiceConfig, AudioSegment, ConversationState } from './voiceTypes';
import VoicePersonalityManager, { VoicePersonality, GuideTheme } from './voicePersonalities';
import StorageManager from '@utils/storage';
import SessionManager from './sessionManager';
import APIManager from '../api/apiManager';

interface Voice {
  id: string;
  name: string;
  gender: 'male' | 'female' | 'neutral';
  language: string;
  locale: string;
  neural: boolean;
  capabilities: Array<'emotion' | 'style' | 'rate' | 'pitch'>;
}

interface SpeakingStyle {
  type: 'narrative' | 'conversational' | 'newscast' | 'excited' | 'sad' | 'friendly';
  intensity: number;  // 0 to 1
  emotion?: {
    type: 'happiness' | 'sadness' | 'excitement' | 'fear' | 'anger' | 'surprise';
    level: number;  // 0 to 1
  };
}

class VoiceService {
  private currentState: ConversationState | null = null;
  private audioSegments: AudioSegment[] = [];
  private isPlaying: boolean = false;
  private currentPersonality: VoicePersonality | null = null;
  private currentTheme: GuideTheme | null = null;

  constructor() {
    void this.initialize();
  }

  private async initialize(): Promise<void> {
    await VoicePersonalityManager.initialize();
    await this.loadConversationState();
    await this.loadCurrentPersonalityAndTheme();
    if (this.currentPersonality) {
      await SessionManager.startSession(this.currentPersonality);
    }
  }

  private async loadCurrentPersonalityAndTheme(): Promise<void> {
    try {
      const personalityId = await StorageManager.getItem<string>('@selected_personality');
      const themeId = await StorageManager.getItem<string>('@selected_theme');

      if (personalityId) {
        const personality = VoicePersonalityManager.getPersonalityById(personalityId);
        this.currentPersonality = personality || VoicePersonalityManager.getPersonalityById('adventurous-explorer') || null;
      } else {
        // Default to adventurous explorer
        this.currentPersonality = VoicePersonalityManager.getPersonalityById('adventurous-explorer') || null;
      }

      if (themeId) {
        const theme = VoicePersonalityManager.getThemeById(themeId);
        this.currentTheme = theme || VoicePersonalityManager.getThemeById('adventure-explorer') || null;
      } else {
        // Default to adventure explorer theme
        this.currentTheme = VoicePersonalityManager.getThemeById('adventure-explorer') || null;
      }
    } catch (error) {
      console.error('Failed to load personality and theme:', error);
      // Set defaults on error
      this.currentPersonality = VoicePersonalityManager.getPersonalityById('adventurous-explorer') || null;
      this.currentTheme = VoicePersonalityManager.getThemeById('adventure-explorer') || null;
    }
  }

  async setPersonality(personalityId: string): Promise<void> {
    const personality = VoicePersonalityManager.getPersonalityById(personalityId);
    if (!personality) {
      throw new Error(`Personality not found: ${personalityId}`);
    }

    this.currentPersonality = personality;
    await StorageManager.setItem('@selected_personality', personalityId);
    await SessionManager.startSession(personality);
  }

  async setTheme(themeId: string): Promise<void> {
    const theme = VoicePersonalityManager.getThemeById(themeId);
    if (!theme) {
      throw new Error(`Theme not found: ${themeId}`);
    }

    this.currentTheme = theme;
    await StorageManager.setItem('@selected_theme', themeId);
  }

  async synthesizeSpeech(
    text: string,
    config: Partial<VoiceConfig> = {}
  ): Promise<string> {
    if (!this.currentPersonality) {
      throw new Error('No personality selected');
    }

    // Add topic to session context
    await SessionManager.addTopic({
      id: `speech-${Date.now()}`,
      type: 'story',
      content: text,
      confidence: 1,
      verificationStatus: 'verified',
      relatedTopics: [],
    });

    const ssml = this.generateSSML(text, {
      voice: this.currentPersonality.voice,
      style: this.currentPersonality.defaultStyle,
      ...config,
    });

    try {
      // Try primary TTS service (Azure)
      const response = await APIManager.makeRequest<ArrayBuffer>(
        'azure-tts',
        '/synthesize',
        'post',
        ssml
      );

      return this.saveAudioFile(response);
    } catch (error) {
      // APIManager will automatically try fallback services
      // If all fail, throw the error
      console.error('Failed to synthesize speech:', error);
      throw error;
    }
  }

  async startNarration(story: Story): Promise<void> {
    if (!this.currentPersonality || !this.currentTheme) {
      throw new Error('Personality or theme not selected');
    }

    // Add story to session context
    await SessionManager.addTopic({
      id: story.id,
      type: 'story',
      content: story.content,
      confidence: 1,
      verificationStatus: 'verified',
      relatedTopics: story.relatedStories || [],
    });

    this.currentState = {
      currentStory: story,
      lastPosition: 0,
      interruptions: [],
      userPreferences: {
        voice: this.currentPersonality.voice.id,
        style: this.currentPersonality.defaultStyle,
        musicVolume: 0.3,
        effectsVolume: 0.5,
      },
    };

    const segments = await this.prepareAudioSegments(story);
    this.audioSegments = segments;
    
    await this.playAudioSegments();
    await this.saveConversationState();
  }

  async pauseNarration(): Promise<void> {
    this.isPlaying = false;
    if (this.currentState) {
      this.currentState.interruptions.push({
        timestamp: Date.now(),
        type: 'user_question',
        context: 'manual_pause',
      });
      await this.saveConversationState();
    }
  }

  async resumeNarration(): Promise<void> {
    if (!this.currentState || !this.currentState.currentStory) {
      throw new Error('No story in progress');
    }

    const lastInterruption = this.currentState.interruptions[
      this.currentState.interruptions.length - 1
    ];

    // Generate a smooth transition phrase based on interruption context
    const transitionPhrase = this.generateTransitionPhrase(lastInterruption);
    const transitionAudio = await this.synthesizeSpeech(transitionPhrase);

    // Insert transition audio at current position
    this.audioSegments.splice(
      this.findCurrentSegmentIndex(),
      0,
      {
        id: `transition-${Date.now()}`,
        type: 'speech',
        url: transitionAudio,
        duration: await this.getAudioDuration(transitionAudio),
        startTime: 0,
        endTime: 0,
        volume: 1,
        fadeIn: 0.5,
        fadeOut: 0.5,
      }
    );

    this.isPlaying = true;
    await this.playAudioSegments();
  }

  async handleInterruption(type: 'user_question' | 'notification' | 'navigation', context: string): Promise<void> {
    await this.pauseNarration();
    
    // Add interruption to session
    await SessionManager.addTopic({
      id: `interruption-${Date.now()}`,
      type: 'question',
      content: context,
      confidence: 1,
      verificationStatus: 'verified',
      relatedTopics: this.currentState?.currentStory ? [this.currentState.currentStory.id] : [],
    });

    this.currentState?.interruptions.push({
      timestamp: Date.now(),
      type,
      context,
    });
    await this.saveConversationState();
  }

  async processUserFeedback(
    sentiment: number,
    engagement: number,
    confusion: number
  ): Promise<void> {
    // Add feedback to session and get adjusted speaking style
    const adjustedStyle = await SessionManager.addUserFeedback({
      sentiment,
      engagement,
      confusion,
    });

    // Update current speaking style
    if (this.currentState) {
      this.currentState.userPreferences.style = adjustedStyle;
    }

    await this.saveConversationState();
  }

  async handleUnverifiedContent(content: string, confidence: number): Promise<string> {
    // Add unverified topic to session
    await SessionManager.addTopic({
      id: `unverified-${Date.now()}`,
      type: 'fact',
      content,
      confidence,
      verificationStatus: 'unverified',
      relatedTopics: [],
    });

    // Get appropriate fallback response
    return SessionManager.getFallbackResponse({
      id: `unverified-${Date.now()}`,
      type: 'fact',
      content,
      confidence,
      verificationStatus: 'unverified',
      relatedTopics: [],
      lastDiscussed: Date.now(),
      userFeedback: [],
    });
  }

  private async prepareAudioSegments(story: Story): Promise<AudioSegment[]> {
    if (!this.currentPersonality || !this.currentTheme) {
      throw new Error('Personality or theme not selected');
    }

    const segments: AudioSegment[] = [];
    let currentTime = 0;

    try {
      // Add intro sound effect
      const introEffect = await APIManager.makeRequest<ArrayBuffer>(
        'azure-tts',
        '/effects/transition',
        'get'
      );
      segments.push({
        id: 'intro-effect',
        type: 'sound_effect',
        url: await this.saveAudioFile(introEffect),
        duration: 2,
        startTime: currentTime,
        endTime: currentTime + 2,
        volume: this.currentState?.userPreferences.effectsVolume || 0.5,
        fadeIn: 0.1,
        fadeOut: 0.1,
      });

      currentTime += 2;

      // Add background music
      const backgroundMusic = await APIManager.makeRequest<ArrayBuffer>(
        'azure-tts',
        '/music/background',
        'get'
      );
      segments.push({
        id: 'background-music',
        type: 'music',
        url: await this.saveAudioFile(backgroundMusic),
        duration: 300,
        startTime: currentTime,
        endTime: currentTime + 300,
        volume: this.currentState?.userPreferences.musicVolume || 0.3,
        fadeIn: 2,
        fadeOut: 2,
        loop: true,
      });

      // Synthesize and add intro catchphrase
      const catchphrase = this.currentPersonality.catchphrases[
        Math.floor(Math.random() * this.currentPersonality.catchphrases.length)
      ];
      const catchphraseAudio = await this.synthesizeSpeech(catchphrase, {
        style: {
          type: 'excited',
          intensity: 0.9,
          emotion: {
            type: 'happiness',
            level: 0.8,
          },
        },
      });

      segments.push({
        id: 'intro-catchphrase',
        type: 'speech',
        url: catchphraseAudio,
        duration: await this.getAudioDuration(catchphraseAudio),
        startTime: currentTime,
        endTime: currentTime + await this.getAudioDuration(catchphraseAudio),
        volume: 1,
        fadeIn: 0.2,
        fadeOut: 0.2,
      });

      currentTime += await this.getAudioDuration(catchphraseAudio) + 0.5;

      // Synthesize main narration with storytelling style
      const narrationAudio = await this.synthesizeSpeech(story.content, {
        style: this.currentPersonality.contextualStyles.storytelling,
      });

      segments.push({
        id: `narration-${story.id}`,
        type: 'speech',
        url: narrationAudio,
        duration: await this.getAudioDuration(narrationAudio),
        startTime: currentTime,
        endTime: currentTime + await this.getAudioDuration(narrationAudio),
        volume: 1,
        fadeIn: 0.5,
        fadeOut: 0.5,
      });

      return segments;
    } catch (error) {
      console.error('Failed to prepare audio segments:', error);
      throw error;
    }
  }

  private async playAudioSegments(): Promise<void> {
    if (!this.isPlaying || !this.audioSegments.length) return;

    const currentSegment = this.audioSegments[this.findCurrentSegmentIndex()];
    if (!currentSegment) return;

    // Apply audio processing
    await this.processAudioSegment(currentSegment);

    // Handle ducking for overlapping segments
    await this.handleAudioDucking(currentSegment);

    // Update state
    this.currentState!.lastPosition = currentSegment.endTime;
    await this.saveConversationState();

    // Schedule next segment
    const nextSegment = this.audioSegments[this.findCurrentSegmentIndex() + 1];
    if (nextSegment) {
      setTimeout(
        () => this.playAudioSegments(),
        (nextSegment.startTime - currentSegment.endTime) * 1000
      );
    }
  }

  private async processAudioSegment(segment: AudioSegment): Promise<void> {
    // Apply audio effects (fades, volume, etc.)
    if (segment.fadeIn) {
      // Implement fade in
    }
    if (segment.fadeOut) {
      // Implement fade out
    }
    // Set volume
    // Handle looping if needed
  }

  private async handleAudioDucking(currentSegment: AudioSegment): Promise<void> {
    const overlappingSegments = this.audioSegments.filter(
      segment =>
        segment.id !== currentSegment.id &&
        segment.startTime <= currentSegment.endTime &&
        segment.endTime >= currentSegment.startTime
    );

    for (const segment of overlappingSegments) {
      if (currentSegment.type === 'speech' && segment.type === 'music') {
        // Duck music volume during speech
        // Implement smooth volume transition
      }
    }
  }

  private findCurrentSegmentIndex(): number {
    if (!this.currentState) return 0;
    return this.audioSegments.findIndex(
      segment => segment.startTime <= this.currentState!.lastPosition &&
                 segment.endTime > this.currentState!.lastPosition
    );
  }

  private generateSSML(text: string, config: Partial<VoiceConfig>): string {
    const voice = config.voice || this.currentPersonality?.voice;
    const style = config.style || this.currentPersonality?.defaultStyle;

    return `
      <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"
             xmlns:mstts="http://www.w3.org/2001/mstts">
        <voice name="${voice?.id}">
          <mstts:express-as style="${style?.type}" styledegree="${style?.intensity || 1}">
            ${this.addProsody(text)}
          </mstts:express-as>
        </voice>
      </speak>
    `;
  }

  private addProsody(text: string): string {
    // Add SSML prosody tags for natural pauses and emphasis
    // Use NLP to analyze sentence structure and add appropriate breaks
    return text;
  }

  private generateTransitionPhrase(interruption: ConversationState['interruptions'][0]): string {
    if (!this.currentPersonality) {
      return "Let's continue...";
    }

    const phrases = this.currentPersonality.transitionPhrases[
      interruption.type === 'user_question' ? 'resumeStory' :
      interruption.type === 'navigation' ? 'changeLocation' : 'resumeStory'
    ];

    return phrases[Math.floor(Math.random() * phrases.length)];
  }

  private async loadConversationState(): Promise<void> {
    try {
      const state = await StorageManager.getItem<ConversationState>('@voice_state');
      if (state) {
        this.currentState = state;
      }
    } catch (error) {
      console.error('Failed to load conversation state:', error);
    }
  }

  private async saveConversationState(): Promise<void> {
    if (!this.currentState) return;
    await StorageManager.setItem('@voice_state', this.currentState);
  }

  private async getAudioDuration(url: string): Promise<number> {
    // Implement audio duration detection
    return 0;
  }

  private async saveAudioFile(data: ArrayBuffer): Promise<string> {
    // Implement file saving logic
    return '';
  }
}

export default new VoiceService(); 