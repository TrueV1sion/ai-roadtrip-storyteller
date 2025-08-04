import { logger } from '@/services/logger';

/**
 * Production Environment Configuration
 * These values should be injected during the build process
 */

export const ENV = {
  // API Configuration
  API_URL: process.env.EXPO_PUBLIC_API_URL || 'https://api.roadtripai.com',
  API_VERSION: 'v1',
  API_TIMEOUT: 30000, // 30 seconds
  
  // App Configuration
  APP_NAME: 'AI Road Trip Storyteller',
  APP_VERSION: process.env.EXPO_PUBLIC_APP_VERSION || '1.0.0',
  APP_ENV: 'production',
  
  // Feature Flags
  FEATURES: {
    VOICE_COMMANDS: true,
    OFFLINE_MODE: true,
    BOOKINGS: true,
    JOURNEY_VIDEO: true,
    AR_FEATURES: false,
    SOCIAL_SHARING: true,
    TWO_FACTOR_AUTH: true,
    PREMIUM_VOICES: true,
  },
  
  // Google Services - API keys are handled by backend proxy
  // No API keys should be stored in the mobile app
  
  // Voice Services (keys should be on backend only)
  VOICE_RECOGNITION_ENABLED: true,
  TTS_ENABLED: true,
  DEFAULT_VOICE_PERSONALITY: 'Friendly_Guide',
  
  // Analytics
  ANALYTICS_ENABLED: true,
  // Analytics key is handled by backend proxy
  
  // Sentry Error Tracking
  SENTRY_DSN: process.env.EXPO_PUBLIC_SENTRY_DSN || '',
  SENTRY_ENVIRONMENT: 'production',
  
  // Cache Configuration
  CACHE_ENABLED: true,
  CACHE_DURATION: 3600000, // 1 hour
  OFFLINE_CACHE_SIZE: 104857600, // 100MB
  
  // Map Configuration
  MAP_DEFAULT_ZOOM: 13,
  MAP_MAX_ZOOM: 20,
  MAP_MIN_ZOOM: 3,
  MAP_STYLE: 'roadtrip_custom',
  
  // Performance
  IMAGE_QUALITY: 0.8,
  VIDEO_MAX_DURATION: 600, // 10 minutes
  AUDIO_SAMPLE_RATE: 44100,
  
  // Security
  SESSION_TIMEOUT: 3600000, // 1 hour
  REFRESH_TOKEN_EXPIRY: 604800000, // 7 days
  BIOMETRIC_AUTH_ENABLED: true,
  
  // Rate Limiting (enforced on backend, but good to know on frontend)
  RATE_LIMITS: {
    VOICE_COMMANDS: 100, // per hour
    STORY_GENERATION: 200, // per hour
    BOOKINGS: 500, // per hour
  },
  
  // URLs
  TERMS_URL: 'https://roadtripai.com/terms',
  PRIVACY_URL: 'https://roadtripai.com/privacy',
  SUPPORT_URL: 'https://roadtripai.com/support',
  WEBSITE_URL: 'https://roadtripai.com',
  
  // Social Media - OAuth handled by backend
  // No social media API keys should be stored in the mobile app
  
  // Deep Linking
  DEEP_LINK_SCHEME: 'roadtripai',
  UNIVERSAL_LINK_DOMAIN: 'roadtripai.com',
  
  // Update Configuration
  UPDATE_CHECK_INTERVAL: 86400000, // 24 hours
  FORCE_UPDATE_VERSION: '0.9.0', // Force update if below this version
  
  // A/B Testing
  AB_TESTING_ENABLED: true,
  AB_TEST_ENDPOINT: '/api/v1/experiments',
  
  // Debug (always false in production)
  DEBUG: false,
  SHOW_DEV_MENU: false,
  LOG_LEVEL: 'error',
};

// Type checking
export type Environment = typeof ENV;

// Validate required environment variables
const requiredVars = [
  'EXPO_PUBLIC_API_URL',
];

// Check required variables in production
if (ENV.APP_ENV === 'production') {
  const missing = requiredVars.filter(
    varName => !process.env[varName]
  );
  
  if (missing.length > 0) {
    logger.error('Missing required environment variables:', missing);
    // In production, this should fail the build
    if (process.env.CI) {
      throw new Error(`Missing required environment variables: ${missing.join(', ')}`);
    }
  }
}

export default ENV;