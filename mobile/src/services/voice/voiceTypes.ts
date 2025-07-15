import { Story } from '@/types/cultural';

export interface Voice {
  id: string;
  name: string;
  gender: 'male' | 'female' | 'neutral';
  language: string;
  locale: string;
  neural: boolean;
  capabilities: Array<'emotion' | 'style' | 'rate' | 'pitch'>;
}

export interface SpeakingStyle {
  type: 'narrative' | 'conversational' | 'newscast' | 'excited' | 'sad' | 'friendly';
  intensity: number;  // 0 to 1
  emotion?: {
    type: 'happiness' | 'sadness' | 'excitement' | 'fear' | 'anger' | 'surprise';
    level: number;  // 0 to 1
  };
}

export interface VoiceConfig {
  voice: Voice;
  style: SpeakingStyle;
  rate: number;  // 0.5 to 2.0
  pitch: number;  // 0.5 to 2.0
  volume: number;  // 0 to 1
}

export interface AudioSegment {
  id: string;
  type: 'speech' | 'music' | 'sound_effect';
  url: string;
  duration: number;
  startTime: number;
  endTime: number;
  volume: number;
  fadeIn?: number;
  fadeOut?: number;
  loop?: boolean;
}

export interface ConversationState {
  currentStory?: Story;
  lastPosition: number;
  interruptions: Array<{
    timestamp: number;
    type: 'user_question' | 'notification' | 'navigation';
    context: string;
  }>;
  userPreferences: {
    voice: string;
    style: SpeakingStyle;
    musicVolume: number;
    effectsVolume: number;
  };
} 