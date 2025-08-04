/**
 * Secure Configuration Service
 * Six Sigma DMAIC - IMPROVE Phase Implementation
 * 
 * This replaces hardcoded API keys with secure environment variable handling
 * All sensitive API calls should go through the backend proxy
 */

import Constants from 'expo-constants';
import { logger } from '@/services/logger';

/**
 * Get a required environment variable with validation
 */
const getRequiredEnvVar = (key: string): string => {
  const value = Constants.expoConfig?.extra?.[key] || process.env[key];
  
  if (!value && !__DEV__) {
    const error = new Error(`Missing required environment variable: ${key}`);
    logger.error('Environment variable missing', error, { key });
    throw error;
  }
  
  return value || '';
};

/**
 * Get an optional environment variable
 */
const getOptionalEnvVar = (key: string, defaultValue: string = ''): string => {
  return Constants.expoConfig?.extra?.[key] || process.env[key] || defaultValue;
};

/**
 * Validate environment on app startup
 */
export const validateEnvironment = (): void => {
  const requiredVars = [
    'EXPO_PUBLIC_API_URL',
    'EXPO_PUBLIC_ENVIRONMENT',
  ];
  
  const missingVars: string[] = [];
  
  requiredVars.forEach(varName => {
    try {
      getRequiredEnvVar(varName);
    } catch (error) {
      missingVars.push(varName);
    }
  });
  
  if (missingVars.length > 0 && !__DEV__) {
    throw new Error(`Missing required environment variables: ${missingVars.join(', ')}`);
  }
  
  if (missingVars.length > 0 && __DEV__) {
    logger.warn('Missing environment variables in development', { missingVars });
  }
};

/**
 * Secure configuration object
 * NO API KEYS should be stored here - all go through backend proxy
 */
export const SecureConfig = {
  // API Configuration
  API_URL: getRequiredEnvVar('EXPO_PUBLIC_API_URL'),
  ENVIRONMENT: getOptionalEnvVar('EXPO_PUBLIC_ENVIRONMENT', 'production'),
  
  // Feature Flags (safe to expose)
  MVP_MODE: getOptionalEnvVar('EXPO_PUBLIC_MVP_MODE', 'false') === 'true',
  ENABLE_BOOKING: getOptionalEnvVar('EXPO_PUBLIC_ENABLE_BOOKING', 'true') === 'true',
  ENABLE_VOICE: getOptionalEnvVar('EXPO_PUBLIC_ENABLE_VOICE', 'true') === 'true',
  ENABLE_AR: getOptionalEnvVar('EXPO_PUBLIC_ENABLE_AR', 'true') === 'true',
  
  // App Configuration (safe to expose)
  APP_NAME: getOptionalEnvVar('EXPO_PUBLIC_APP_NAME', 'AI Road Trip Storyteller'),
  APP_VERSION: Constants.expoConfig?.version || '1.0.0',
  BUILD_NUMBER: Constants.expoConfig?.ios?.buildNumber || Constants.expoConfig?.android?.versionCode || '1',
  
  // Development Configuration
  DEV_SETTINGS: __DEV__ ? {
    SHOW_DEBUG_INFO: true,
    ENABLE_NETWORK_LOGS: true,
    USE_MOCK_LOCATION: false,
  } : {
    SHOW_DEBUG_INFO: false,
    ENABLE_NETWORK_LOGS: false,
    USE_MOCK_LOCATION: false,
  },
  
  // Security Configuration
  SECURITY: {
    ENABLE_CERTIFICATE_PINNING: !__DEV__,
    ENABLE_JAILBREAK_DETECTION: !__DEV__,
    ENABLE_ROOT_DETECTION: !__DEV__,
    SECURE_STORAGE_REQUIRED: true,
    BIOMETRIC_AUTH_ENABLED: true,
  },
  
  // Performance Configuration
  PERFORMANCE: {
    API_TIMEOUT: 30000, // 30 seconds
    MAX_RETRY_ATTEMPTS: 3,
    CACHE_DURATION: 3600000, // 1 hour
    IMAGE_COMPRESSION_QUALITY: 0.8,
  },
};

/**
 * API Proxy Configuration
 * All sensitive API calls go through backend proxy endpoints
 */
export const APIProxyEndpoints = {
  // Maps - backend handles Google Maps API key
  MAPS: {
    GEOCODE: '/api/proxy/maps/geocode',
    DIRECTIONS: '/api/proxy/maps/directions',
    PLACES: '/api/proxy/maps/places',
    DISTANCE_MATRIX: '/api/proxy/maps/distance',
  },
  
  // Weather - backend handles API key
  WEATHER: {
    CURRENT: '/api/proxy/weather/current',
    FORECAST: '/api/proxy/weather/forecast',
  },
  
  // Third-party services - backend handles OAuth and API keys
  SPOTIFY: {
    AUTH: '/api/proxy/spotify/auth',
    SEARCH: '/api/proxy/spotify/search',
    PLAYLISTS: '/api/proxy/spotify/playlists',
  },
  
  // AI Services - backend handles API keys
  AI: {
    GENERATE_STORY: '/api/ai/generate-story',
    TEXT_TO_SPEECH: '/api/ai/text-to-speech',
    SPEECH_TO_TEXT: '/api/ai/speech-to-text',
  },
};

/**
 * Get the appropriate API URL based on platform and environment
 */
export const getAPIUrl = (): string => {
  // Production URL from environment
  if (SecureConfig.API_URL) {
    return SecureConfig.API_URL;
  }
  
  // Development defaults
  if (__DEV__) {
    // These are safe development defaults - no sensitive data
    if (Constants.expoConfig?.extra?.PLATFORM === 'ios') {
      return 'http://localhost:8000';
    } else if (Constants.expoConfig?.extra?.PLATFORM === 'android') {
      return 'http://10.0.2.2:8000';
    }
    // Physical device - must be configured
    logger.warn('No API URL configured for physical device development');
    return 'http://localhost:8000';
  }
  
  // Should never reach here if environment is properly configured
  throw new Error('API URL not configured');
};

// Validate environment on module load
if (!__DEV__) {
  validateEnvironment();
}

export default SecureConfig;