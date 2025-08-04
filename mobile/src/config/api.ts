/**
 * API Configuration for the mobile app
 * Updates automatically based on environment
 */

import { FEATURES } from './features';

import { logger } from '@/services/logger';
// Import secure configuration
import { SecureConfig, getAPIUrl } from './secure-config';

// Determine API URL based on environment
const getApiUrl = () => {
  return getAPIUrl();
};

const API_BASE_URL = getApiUrl();
const WS_BASE_URL = API_BASE_URL.replace('http', 'ws').replace('https', 'wss');

export const API_CONFIG = {
  BASE_URL: API_BASE_URL,
  WS_URL: WS_BASE_URL,
  TIMEOUT: 30000, // 30 seconds
  
  // API Endpoints
  ENDPOINTS: {
    // MVP Endpoints (always available)
    VOICE_INTERACT: '/api/voice-assistant/interact',
    GET_STORY: '/api/stories/generate',
    GET_ROUTE: '/api/navigation/route',
    HEALTH: '/health',
    
    // Phase 2 Endpoints (conditionally included)
    ...(FEATURES.BOOKING && {
      SEARCH_HOTELS: '/api/booking/hotels/search',
      BOOK_HOTEL: '/api/booking/hotels/book',
      SEARCH_RESTAURANTS: '/api/booking/restaurants/search',
    }),
    
    ...(FEATURES.GAMES && {
      START_GAME: '/api/games/start',
      SUBMIT_ANSWER: '/api/games/answer',
      GET_LEADERBOARD: '/api/games/leaderboard',
    }),
    
    ...(FEATURES.MUSIC && {
      GET_PLAYLIST: '/api/music/playlist',
      CONTROL_PLAYBACK: '/api/music/control',
    }),
    
    ...(FEATURES.EVENT_JOURNEYS && {
      DETECT_EVENT: '/api/events/detect',
      GET_EVENT_INFO: '/api/events/info',
    }),
  },
  
  // Default headers
  HEADERS: {
    'Content-Type': 'application/json',
    'X-App-Version': '1.0.0-mvp',
    'X-Platform': process.env.EXPO_PUBLIC_PLATFORM || 'unknown',
  },
};

// Helper function to build full URL
export const buildApiUrl = (endpoint: string): string => {
  return `${API_CONFIG.BASE_URL}${endpoint}`;
};

// Helper function for WebSocket URL
export const buildWsUrl = (endpoint: string): string => {
  return `${API_CONFIG.WS_URL}${endpoint}`;
};

// Log configuration in development
if (__DEV__) {
  logger.debug('📡 API Configuration:', {
    BASE_URL: API_CONFIG.BASE_URL,
    WS_URL: API_CONFIG.WS_URL,
    AVAILABLE_ENDPOINTS: Object.keys(API_CONFIG.ENDPOINTS).length,
  });
}