import { apiClient } from './ApiClient';
import { LocationData } from '../locationService';

// Types for API requests and responses
export interface ImmersiveRequest {
  conversation_id: string;
  location: LocationData;
  interests: string[];
  context?: {
    time_of_day?: string;
    weather?: string;
    mood?: string;
  };
}

export interface Track {
  title: string;
  artist: string;
}

export interface Playlist {
  playlist_name: string;
  tracks: Track[];
  provider: string;
}

export interface ImmersiveResponse {
  story: string;
  playlist: Playlist;
  tts_audio: string;
}

/**
 * Service for handling immersive experience API interactions
 */
export class ImmersiveService {
  /**
   * Get an immersive experience based on location, interests, and context
   * 
   * @param request The request parameters 
   * @returns Promise resolving to immersive experience data
   */
  async getImmersiveExperience(request: ImmersiveRequest): Promise<ImmersiveResponse> {
    try {
      const response = await apiClient.post<ImmersiveResponse>('/api/immersive', request);
      return response;
    } catch (error) {
      console.error('Error fetching immersive experience:', error);
      throw error;
    }
  }

  /**
   * Generates a story for a specific location
   * 
   * @param location Location coordinates
   * @param interests User interests
   * @param context Additional context
   * @returns Promise resolving to the generated story
   */
  async generateStory(
    location: LocationData,
    interests: string[],
    context?: { time_of_day?: string; weather?: string; mood?: string }
  ): Promise<string> {
    try {
      const response = await apiClient.post<{ status: string; story: string }>('/api/story/generate', {
        latitude: location.latitude,
        longitude: location.longitude,
        interests,
        context
      });
      
      return response.story;
    } catch (error) {
      console.error('Error generating story:', error);
      throw error;
    }
  }

  /**
   * Rate a story (for user feedback and personalization)
   * 
   * @param storyId The ID of the story to rate
   * @param rating Rating value (1-5)
   * @returns Promise resolving to the updated story
   */
  async rateStory(storyId: string, rating: number): Promise<{ success: boolean }> {
    try {
      const response = await apiClient.post<{ success: boolean }>(`/api/story/${storyId}/rate`, {
        rating
      });
      
      return response;
    } catch (error) {
      console.error('Error rating story:', error);
      throw error;
    }
  }

  /**
   * Toggle favorite status for a story
   * 
   * @param storyId The ID of the story
   * @returns Promise resolving to the updated story
   */
  async toggleFavorite(storyId: string): Promise<{ success: boolean; isFavorite: boolean }> {
    try {
      const response = await apiClient.post<{ success: boolean; isFavorite: boolean }>(
        `/api/story/${storyId}/favorite`
      );
      
      return response;
    } catch (error) {
      console.error('Error toggling favorite status:', error);
      throw error;
    }
  }
}

// Export a singleton instance for app-wide use
export const immersiveService = new ImmersiveService();

export default immersiveService;
