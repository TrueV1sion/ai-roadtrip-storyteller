/**
 * Types for the voice character system
 */

// Enum types
export type VoiceGender = 'male' | 'female' | 'neutral';
export type VoiceAge = 'child' | 'young' | 'adult' | 'senior';
export type VoiceAccent = 
  | 'american' 
  | 'british' 
  | 'australian' 
  | 'indian' 
  | 'french' 
  | 'german' 
  | 'spanish' 
  | 'italian' 
  | 'japanese' 
  | 'korean' 
  | 'chinese' 
  | 'russian' 
  | 'arabic' 
  | 'other'
  | 'none';

export type EmotionType = 
  | 'neutral' 
  | 'happy' 
  | 'sad' 
  | 'angry' 
  | 'excited' 
  | 'calm' 
  | 'fearful' 
  | 'surprised';

// Voice Character types
export interface VoiceCharacterBase {
  name: string;
  description: string;
  voice_id: string;
  gender: VoiceGender;
  age: VoiceAge;
  accent: VoiceAccent;
  speaking_style: string;
  pitch: number;
  rate: number;
  base_emotion: EmotionType;
}

export interface VoiceCharacterType extends VoiceCharacterBase {
  id: string;
  personality_traits: string[];
  speech_patterns: Record<string, string>;
  filler_words: string[];
  vocabulary_level: string;
  backstory?: string;
  theme_affinity: string[];
  character_image_url?: string;
}

// Speech types
export interface SpeechPromptType {
  text: string;
  character_id: string;
  context?: Record<string, any>;
  emotion?: EmotionType;
  emphasis_words?: string[];
}

export interface SpeechResultType {
  original_text: string;
  transformed_text: string;
  audio_url: string;
  duration: number;
  character_id: string;
  emotion: EmotionType;
}

// Request types
export interface ThemeRequestType {
  theme: string;
}

export interface ContextualCharacterRequestType {
  theme: string;
  context: Record<string, any>;
}

// Voice playback state
export interface VoicePlaybackState {
  isPlaying: boolean;
  isPaused: boolean;
  isLoading: boolean;
  progress: number;
  duration: number;
  currentCharacterId?: string;
  currentEmotion: EmotionType;
  speakingText?: string;
}

// Dynamic Voice Personality System
export interface VoicePersonality {
  id: string;
  name: string;
  description: string;
  voice_id: string;
  speaking_style: {
    pitch: number;
    speed: number;
    emphasis: string;
    [key: string]: any;
  };
  vocabulary_style: string;
  catchphrases: string[];
  topics_of_expertise: string[];
  emotion_range: Record<string, number>;
  regional_accent?: string;
  age_appropriate?: string[];
  active_seasons?: string[];
  active_holidays?: string[];
  active_hours?: [number, number];
}

export interface UserPreferences {
  preferred_voice_personality?: string;
  age_group?: string;
  interests?: string[];
  language?: string;
  accessibility?: {
    slow_speech?: boolean;
    high_contrast?: boolean;
  };
}

export interface VoiceSettings {
  character: VoiceCharacterType;
  personality?: VoicePersonality;
  volume: number;
  speed: number;
  pitch: number;
  language: string;
}

export interface VoiceCommand {
  command: string;
  action: string;
  parameters?: Record<string, any>;
}

export interface VoiceResponse {
  text: string;
  audio?: string;
  emotion?: string;
  actions?: VoiceCommand[];
}