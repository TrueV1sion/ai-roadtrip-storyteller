/**
 * Simple API Service for MVP
 * Handles communication with the backend
 */
import axios, { AxiosInstance } from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { setupCSRFInterceptor } from '../utils/csrf';
import { DevelopmentConfig, shouldUseMockData, getMockResponse } from '../config/development';

import { logger } from '@/services/logger';
class ApiService {
  private client: AxiosInstance;
  private baseURL: string;

  constructor() {
    // Use environment variable if available, otherwise use defaults
    this.baseURL = process.env.EXPO_PUBLIC_API_URL || (
      __DEV__ 
        ? 'http://localhost:8000' 
        : 'https://roadtrip-mvp-792001900150.us-central1.run.app'
    );

    this.client = axios.create({
      baseURL: this.baseURL,
      timeout: 30000, // 30 seconds
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add request interceptor for auth token
    this.client.interceptors.request.use(
      async (config) => {
        const token = await AsyncStorage.getItem('authToken');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Setup CSRF protection
    setupCSRFInterceptor(this.client);

    // Add response interceptor for error handling and mock data
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        // In development, return mock data if backend is unavailable
        if (__DEV__ && shouldUseMockData() && error.code === 'ECONNREFUSED') {
          const mockData = getMockResponse(error.config.url);
          if (mockData) {
            logger.warn('Backend unavailable, using mock data for:', error.config.url);
            return { data: mockData, status: 200, config: error.config };
          }
        }
        
        if (error.response) {
          // Server responded with error
          logger.error('API Error:', error.response.data);
        } else if (error.request) {
          // Request made but no response
          logger.error('Network Error:', error.message);
        } else {
          // Something else happened
          logger.error('Error:', error.message);
        }
        return Promise.reject(error);
      }
    );
  }

  // Voice assistant interaction
  async interactWithVoiceAssistant(input: string, context: any) {
    // Use MVP endpoint for now
    return this.post('/api/mvp/voice', {
      user_input: input,
      context,
    });
  }

  // Get navigation route
  async getNavigationRoute(origin: any, destination: string) {
    return this.post('/api/navigation/route', {
      origin,
      destination,
    });
  }

  // Get story for location
  async getLocationStory(location: any, theme?: string) {
    return this.post('/api/stories/generate', {
      location,
      theme,
    });
  }

  // Generic HTTP methods
  async get(endpoint: string, params?: any) {
    return this.client.get(endpoint, { params });
  }

  async post(endpoint: string, data?: any) {
    return this.client.post(endpoint, data);
  }

  async put(endpoint: string, data?: any) {
    return this.client.put(endpoint, data);
  }

  async delete(endpoint: string) {
    return this.client.delete(endpoint);
  }

  // Update base URL (for switching environments)
  setBaseURL(url: string) {
    this.baseURL = url;
    this.client.defaults.baseURL = url;
  }

  // Get current base URL
  getBaseURL() {
    return this.baseURL;
  }
}

// Singleton instance
export const apiService = new ApiService();
export default apiService;