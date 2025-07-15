/**
 * Feature flags for MVP mode
 * Set these based on environment variables or build configuration
 */

// Check if we're in MVP mode (default to true for now)
const MVP_MODE = process.env.EXPO_PUBLIC_MVP_MODE !== 'false';

export const FEATURES = {
  // Core MVP Features (always enabled)
  VOICE_NAVIGATION: true,
  STORIES: true,
  BASIC_PERSONALITIES: true,
  SAFETY_FEATURES: true,
  MAP_VIEW: true,
  
  // Phase 2 Features (disabled in MVP)
  AR: !MVP_MODE && process.env.EXPO_PUBLIC_ENABLE_AR === 'true',
  GAMES: !MVP_MODE && process.env.EXPO_PUBLIC_ENABLE_GAMES === 'true',
  MUSIC: !MVP_MODE && process.env.EXPO_PUBLIC_ENABLE_MUSIC === 'true',
  BOOKING: !MVP_MODE && process.env.EXPO_PUBLIC_ENABLE_BOOKING === 'true',
  SPATIAL_AUDIO: !MVP_MODE && process.env.EXPO_PUBLIC_ENABLE_SPATIAL === 'true',
  EVENT_JOURNEYS: !MVP_MODE && process.env.EXPO_PUBLIC_ENABLE_EVENTS === 'true',
  RIDESHARE: !MVP_MODE && process.env.EXPO_PUBLIC_ENABLE_RIDESHARE === 'true',
  AIRPORT: !MVP_MODE && process.env.EXPO_PUBLIC_ENABLE_AIRPORT === 'true',
  
  // Development features
  DEBUG_MODE: process.env.EXPO_PUBLIC_DEBUG === 'true',
  MOCK_LOCATION: process.env.EXPO_PUBLIC_MOCK_LOCATION === 'true'
};

// Log active features in development
if (__DEV__) {
  console.log('🚀 Active Features:', Object.entries(FEATURES)
    .filter(([_, enabled]) => enabled)
    .map(([feature]) => feature)
    .join(', '));
}