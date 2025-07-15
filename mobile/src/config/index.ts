// API Configuration
export const API_URL = __DEV__
  ? 'http://localhost:8000'  // Development
  : 'https://api.roadtripstoryteller.com';  // Production

// Auth Configuration
export const ACCESS_TOKEN_KEY = 'access_token';
export const REFRESH_TOKEN_KEY = 'refresh_token';
export const TOKEN_EXPIRY_KEY = 'token_expiry';
export const AUTH_USER_KEY = 'auth_user';

// Map Configuration
export const MAPS_API_KEY = process.env.MAPS_API_KEY || 'your_google_maps_api_key';
export const DEFAULT_LATITUDE = 37.7749;  // San Francisco
export const DEFAULT_LONGITUDE = -122.4194;
export const DEFAULT_ZOOM = 12;

// Story Generation
export const STORY_TRIGGER_DISTANCE = 1000;  // meters
export const STORY_MIN_INTERVAL = 5 * 60;  // 5 minutes in seconds

// Spotify Configuration
export const SPOTIFY_CLIENT_ID = process.env.SPOTIFY_CLIENT_ID || 'your_spotify_client_id';
export const SPOTIFY_REDIRECT_URI = __DEV__ 
  ? 'exp://localhost:19000/--/spotify-auth-callback'
  : 'roadtripstoryteller://spotify-auth-callback';

// Cache Configuration
export const CACHE_TTL = 24 * 60 * 60;  // 24 hours in seconds
export const MAX_CACHED_STORIES = 100;
export const MAX_CACHED_TRIPS = 20;

// Security Configuration
export const SECURE_STORAGE_ENABLED = true;
export const TOKEN_REFRESH_BUFFER = 5 * 60 * 1000;  // 5 minutes in milliseconds
export const CSRF_TOKEN_KEY = 'csrf_token';
export const CSRF_HEADER_NAME = 'X-CSRF-Token';

// UI Configuration - Using new design system
import { lightTheme } from '../design/theme';
export const THEME = lightTheme;

// Animation Configuration
export const ANIMATION_DURATION = lightTheme.animation.duration.normal;
export const VOICE_PULSE_DURATION = lightTheme.animation.duration.voicePulse;

// Voice Interface Configuration
export const VOICE_BUTTON_SIZE = 80;
export const VOICE_LISTENING_TIMEOUT = 30000; // 30 seconds
export const VOICE_TRANSCRIPT_MAX_LENGTH = 200;

// Story Card Configuration
export const STORY_CARD_WIDTH_PERCENTAGE = 0.9;
export const STORY_CARD_HEIGHT = 200;
export const STORY_CARD_MARGIN = lightTheme.spacing.md;

// Navigation UI Configuration
export const NAVIGATION_STATUS_HEIGHT = 100;
export const NAVIGATION_UPDATE_INTERVAL = 1000; // 1 second

// Safety UI Configuration
export const SAFETY_MODE_SPEED_THRESHOLD = 55; // mph
export const DRIVING_MODE_SIMPLIFICATION = true;
export const LARGE_TOUCH_TARGET_SIZE = 64; // pixels