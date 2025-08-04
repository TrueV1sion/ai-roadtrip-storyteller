import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { API_URL, CACHE_TTL, MAX_CACHED_STORIES } from '@/config';
import { LocationData } from './locationService';
import { LRUCache, memoizeAsync } from '@utils/cache';
import { withRetry } from '@utils/async';
import { factVerificationService } from './factVerificationService';

import { logger } from '@/services/logger';
export interface StoryContext {
  time_of_day?: string;
  weather?: string;
  speed?: number;
  road_type?: string;
  landmarks?: {
    name: string;
    distance: number;
    type: string;
    description?: string;
  }[];
  historical_events?: {
    date: string;
    description: string;
    significance: string;
    verified: boolean;
  }[];
  local_culture?: {
    traditions?: string[];
    cuisine?: string[];
    music?: string[];
  };
  environmental_data?: {
    temperature?: number;
    weather_description?: string;
    air_quality?: string;
    sunrise?: string;
    sunset?: string;
  };
}

export interface Story {
  id: string;
  location: LocationData;
  story_text: string;
  interests: string[];
  context?: StoryContext;
  verified_facts?: {
    fact: string;
    confidence: number;
    source: string;
  }[];
  rating?: number;
  is_favorite: boolean;
  created_at: string;
}

interface StoryCache {
  story: Story;
  timestamp: number;
}

class StoryService {
  private api: ReturnType<typeof axios.create>;
  private cache: LRUCache<string, StoryCache>;

  constructor() {
    this.api = axios.create({
      baseURL: `${API_URL}/api/story`,
    });

    // Initialize cache
    this.cache = new LRUCache<string, StoryCache>(
      MAX_CACHED_STORIES,
      CACHE_TTL
    );

    // Add token to requests
    this.api.interceptors.request.use(async (config) => {
      const token = await AsyncStorage.getItem('token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Handle response errors
    this.api.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401) {
          // Handle token expiration
          await AsyncStorage.removeItem('token');
        }
        throw error;
      }
    );
  }

  private generateCacheKey(location: LocationData): string {
    // Round coordinates to reduce cache fragmentation
    const lat = Math.round(location.latitude * 1000) / 1000;
    const lng = Math.round(location.longitude * 1000) / 1000;
    return `${lat},${lng}`;
  }

  private async enrichContext(
    location: LocationData,
    context?: Partial<StoryContext>
  ): Promise<StoryContext> {
    try {
      // Fetch additional context data in parallel
      const [
        weatherData,
        landmarksData,
        historicalEvents,
        localCulture,
      ] = await Promise.all([
        this.fetchWeatherData(location),
        this.fetchNearbyLandmarks(location),
        this.fetchHistoricalEvents(location),
        this.fetchLocalCulture(location),
      ]);

      return {
        ...context,
        weather: weatherData.description,
        landmarks: landmarksData,
        historical_events: historicalEvents,
        local_culture: localCulture,
        environmental_data: {
          temperature: weatherData.temperature,
          weather_description: weatherData.description,
          air_quality: weatherData.airQuality,
          sunrise: weatherData.sunrise,
          sunset: weatherData.sunset,
        },
      };
    } catch (error) {
      logger.error('Error enriching context:', error);
      return context || {};
    }
  }

  private async verifyStoryFacts(story: string): Promise<Array<{ fact: string; confidence: number; source: string }>> {
    try {
      // Extract key facts from the story
      const facts = this.extractKeyFacts(story);
      
      // Verify each fact in parallel
      const verificationResults = await Promise.all(
        facts.map(fact => factVerificationService.verifyFact(fact))
      );

      return verificationResults.map((result, index) => ({
        fact: facts[index],
        confidence: result.confidence,
        source: result.source,
      }));
    } catch (error) {
      logger.error('Error verifying facts:', error);
      return [];
    }
  }

  private extractKeyFacts(story: string): string[] {
    // Implement fact extraction logic
    // This could use NLP techniques or pattern matching
    // For now, return a simple implementation
    return story
      .split('.')
      .filter(sentence => 
        sentence.includes('is') || 
        sentence.includes('was') || 
        sentence.includes('were')
      )
      .map(fact => fact.trim());
  }

  generateStory = memoizeAsync(
    async (
      location: LocationData,
      interests: string[],
      context?: Partial<StoryContext>
    ): Promise<Story> => {
      return withRetry(async () => {
        // Enrich context with additional data
        const enrichedContext = await this.enrichContext(location, context);

        // Generate the story
        const response = await this.api.post<Story>('/generate', {
          latitude: location.latitude,
          longitude: location.longitude,
          interests,
          context: enrichedContext,
        });

        // Verify facts in the generated story
        const verifiedFacts = await this.verifyStoryFacts(response.data.story_text);

        return {
          ...response.data,
          verified_facts: verifiedFacts,
          context: enrichedContext,
        };
      });
    },
    MAX_CACHED_STORIES,
    CACHE_TTL
  );

  getStory = memoizeAsync(
    async (storyId: string): Promise<Story> => {
      return withRetry(async () => {
        const response = await this.api.get<Story>(`/${storyId}`);
        return response.data;
      });
    }
  );

  async rateStory(storyId: string, rating: number): Promise<Story> {
    return withRetry(async () => {
      const response = await this.api.post<Story>(`/${storyId}/rate`, {
        rating,
      });
      return response.data;
    });
  }

  async toggleFavorite(storyId: string): Promise<Story> {
    return withRetry(async () => {
      const response = await this.api.post<Story>(`/${storyId}/favorite`);
      return response.data;
    });
  }

  getUserStories = memoizeAsync(
    async (): Promise<Story[]> => {
      return withRetry(async () => {
        const response = await this.api.get<Story[]>('/user/stories');
        return response.data;
      });
    },
    1,  // Only cache the latest result
    60  // Cache for 1 minute
  );

  getFavoriteStories = memoizeAsync(
    async (): Promise<Story[]> => {
      return withRetry(async () => {
        const response = await this.api.get<Story[]>('/user/favorites');
        return response.data;
      });
    },
    1,  // Only cache the latest result
    60  // Cache for 1 minute
  );

  async clearCache(): Promise<void> {
    this.cache.clear();
  }

  private async fetchWeatherData(location: LocationData) {
    // Implement weather data fetching
    return {
      temperature: 0,
      description: '',
      airQuality: '',
      sunrise: '',
      sunset: '',
    };
  }

  private async fetchNearbyLandmarks(location: LocationData) {
    // Implement landmark fetching
    return [];
  }

  private async fetchHistoricalEvents(location: LocationData) {
    // Implement historical events fetching
    return [];
  }

  private async fetchLocalCulture(location: LocationData) {
    // Implement local culture data fetching
    return {};
  }
}

export const storyService = new StoryService(); 