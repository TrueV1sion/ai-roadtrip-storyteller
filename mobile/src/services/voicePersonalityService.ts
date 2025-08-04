import { Audio } from 'expo-av';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { ApiClient } from './api/ApiClient';
import { VoicePersonality, UserPreferences } from '../types/voice';

import { logger } from '@/services/logger';
const PERSONALITY_CACHE_KEY = 'voice_personalities_cache';
const SELECTED_PERSONALITY_KEY = 'selected_voice_personality';

interface PersonalityContext {
  location?: {
    lat: number;
    lng: number;
    state?: string;
  };
  userPreferences?: UserPreferences;
  userId?: string;
}

class VoicePersonalityService {
  private apiClient: ApiClient;
  private cachedPersonalities: VoicePersonality[] = [];
  private currentSound: Audio.Sound | null = null;

  constructor() {
    this.apiClient = new ApiClient();
    this.loadCachedPersonalities();
  }

  private async loadCachedPersonalities() {
    try {
      const cached = await AsyncStorage.getItem(PERSONALITY_CACHE_KEY);
      if (cached) {
        this.cachedPersonalities = JSON.parse(cached);
      }
    } catch (error) {
      logger.error('Failed to load cached personalities:', error);
    }
  }

  async getAvailablePersonalities(context: PersonalityContext): Promise<VoicePersonality[]> {
    try {
      const response = await this.apiClient.post('/api/voice/personalities', context);
      const personalities = response.data.personalities;
      
      // Cache the personalities
      this.cachedPersonalities = personalities;
      await AsyncStorage.setItem(PERSONALITY_CACHE_KEY, JSON.stringify(personalities));
      
      return personalities;
    } catch (error) {
      logger.error('Failed to fetch personalities:', error);
      // Return cached personalities as fallback
      return this.cachedPersonalities;
    }
  }

  async getContextualPersonality(context: PersonalityContext): Promise<VoicePersonality | null> {
    try {
      const response = await this.apiClient.post('/api/voice/contextual-personality', context);
      return response.data.personality;
    } catch (error) {
      logger.error('Failed to get contextual personality:', error);
      // Return default personality from cache
      return this.cachedPersonalities.find(p => p.id === 'friendly_guide') || null;
    }
  }

  async saveSelectedPersonality(personalityId: string): Promise<void> {
    try {
      await AsyncStorage.setItem(SELECTED_PERSONALITY_KEY, personalityId);
    } catch (error) {
      logger.error('Failed to save selected personality:', error);
    }
  }

  async getSelectedPersonality(): Promise<string | null> {
    try {
      return await AsyncStorage.getItem(SELECTED_PERSONALITY_KEY);
    } catch (error) {
      logger.error('Failed to get selected personality:', error);
      return null;
    }
  }

  async playGreetingSample(personalityId: string): Promise<void> {
    try {
      // Stop any currently playing sound
      if (this.currentSound) {
        await this.currentSound.unloadAsync();
      }

      // Fetch greeting sample URL from API
      const response = await this.apiClient.get(`/api/voice/personality/${personalityId}/greeting`);
      const greetingUrl = response.data.audio_url;

      if (!greetingUrl) {
        logger.error('No greeting URL returned');
        return;
      }

      // Load and play the greeting
      const { sound } = await Audio.Sound.createAsync(
        { uri: greetingUrl },
        { shouldPlay: true }
      );

      this.currentSound = sound;

      // Cleanup when playback finishes
      sound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded && status.didJustFinish) {
          sound.unloadAsync();
          if (this.currentSound === sound) {
            this.currentSound = null;
          }
        }
      });
    } catch (error) {
      logger.error('Failed to play greeting sample:', error);
    }
  }

  isHolidayActive(holiday: string): boolean {
    const today = new Date();
    const currentYear = today.getFullYear();
    
    const holidayDates: Record<string, [Date, Date]> = {
      christmas: [
        new Date(currentYear, 11, 1), // December 1
        new Date(currentYear, 11, 25), // December 25
      ],
      halloween: [
        new Date(currentYear, 9, 15), // October 15
        new Date(currentYear, 9, 31), // October 31
      ],
      valentines: [
        new Date(currentYear, 1, 10), // February 10
        new Date(currentYear, 1, 14), // February 14
      ],
      st_patricks: [
        new Date(currentYear, 2, 15), // March 15
        new Date(currentYear, 2, 17), // March 17
      ],
      independence_day: [
        new Date(currentYear, 6, 1), // July 1
        new Date(currentYear, 6, 4), // July 4
      ],
      thanksgiving: [
        new Date(currentYear, 10, 20), // November 20
        new Date(currentYear, 10, 30), // November 30
      ],
    };

    const range = holidayDates[holiday];
    if (!range) return false;

    return today >= range[0] && today <= range[1];
  }

  getPersonalityByEvent(eventType: string): string | null {
    const eventMapping: Record<string, string> = {
      music_festival: 'jazz_storyteller',
      rodeo: 'texas_ranger',
      harvest_festival: 'harvest_guide',
      beach_party: 'beach_vibes',
      mountain_climbing: 'mountain_sage',
      historical_tour: 'historian',
      comedy_show: 'comedian',
      romantic_dinner: 'cupid',
      adventure_park: 'adventurer',
    };

    return eventMapping[eventType.toLowerCase()] || null;
  }

  getPersonalityByMood(mood: string): string | null {
    const moodMapping: Record<string, string> = {
      excited: 'adventurer',
      romantic: 'cupid',
      nostalgic: 'local_expert',
      playful: 'comedian',
      peaceful: 'mountain_sage',
      festive: 'santa', // During holiday season
      curious: 'historian',
      relaxed: 'beach_vibes',
      patriotic: 'patriot',
      grateful: 'harvest_guide',
    };

    return moodMapping[mood.toLowerCase()] || null;
  }

  async updatePersonalityForContext(context: {
    event?: string;
    mood?: string;
    location?: PersonalityContext['location'];
  }): Promise<VoicePersonality | null> {
    try {
      // Check for event-based personality
      if (context.event) {
        const eventPersonalityId = this.getPersonalityByEvent(context.event);
        if (eventPersonalityId) {
          const personality = this.cachedPersonalities.find(p => p.id === eventPersonalityId);
          if (personality) return personality;
        }
      }

      // Check for mood-based personality
      if (context.mood) {
        const moodPersonalityId = this.getPersonalityByMood(context.mood);
        if (moodPersonalityId) {
          const personality = this.cachedPersonalities.find(p => p.id === moodPersonalityId);
          if (personality) return personality;
        }
      }

      // Default to contextual personality
      return await this.getContextualPersonality({ location: context.location });
    } catch (error) {
      logger.error('Failed to update personality for context:', error);
      return null;
    }
  }

  async stopCurrentPlayback(): Promise<void> {
    if (this.currentSound) {
      await this.currentSound.stopAsync();
      await this.currentSound.unloadAsync();
      this.currentSound = null;
    }
  }
}

export const voicePersonalityService = new VoicePersonalityService();