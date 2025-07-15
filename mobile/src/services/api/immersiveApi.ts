import axios from 'axios';
import env from '@/config/env';

export interface Location {
  latitude: number;
  longitude: number;
}

export interface Context {
  time_of_day: string;
  weather: string;
  mood: string;
}

export interface Track {
  id: string | undefined;
  title: string;
  artist: string;
  uri: string | undefined;
  duration_ms: number | undefined;
}

export interface Playlist {
  playlist_name: string;
  tracks: Track[];
  provider: string;
}

export interface Experience {
  id?: string;
  story: string;
  playlist: Playlist;
  tts_audio_url: string | null;
  created_at?: string;
  location?: Location;
  context?: Context;
}

export interface ExperienceRequest {
  conversation_id: string;
  location: Location;
  interests: string[];
  context: Context;
}

const api = axios.create({
  baseURL: env.API_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  }
});

export const immersiveApi = {
  getExperience: async (request: ExperienceRequest): Promise<Experience> => {
    try {
      const response = await api.post<Experience>('/immersive', request);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(
          error.response?.data?.message || 
          'Failed to fetch experience. Please check your connection.'
        );
      }
      throw error;
    }
  },

  getExperienceHistory: async (): Promise<Experience[]> => {
    try {
      const response = await api.get<Experience[]>('/immersive/history');
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(
          error.response?.data?.message || 
          'Failed to fetch experience history.'
        );
      }
      throw error;
    }
  },

  saveExperience: async (experience: Experience): Promise<void> => {
    try {
      await api.post('/immersive/save', experience);
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(
          error.response?.data?.message || 
          'Failed to save experience.'
        );
      }
      throw error;
    }
  }
}; 