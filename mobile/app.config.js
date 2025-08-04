// Build-time validation for required environment variables
const requiredEnvVars = [
  'EXPO_PUBLIC_API_URL',
];

// Validate in production builds
if (process.env.NODE_ENV === 'production') {
  const missingVars = requiredEnvVars.filter(varName => !process.env[varName]);
  if (missingVars.length > 0) {
    throw new Error(`Missing required environment variables for production build: ${missingVars.join(', ')}`);
  }
}

export default {
  name: 'RoadTrip',
  slug: 'roadtrip',
  version: '1.0.0',
  orientation: 'portrait',
  icon: './assets/icon.png',
  userInterfaceStyle: 'light',
  splash: {
    image: './assets/splash.png',
    resizeMode: 'contain',
    backgroundColor: '#ffffff'
  },
  assetBundlePatterns: [
    '**/*'
  ],
  web: {
    favicon: './assets/favicon.png'
  },
  extra: {
    // SECURITY: NO API KEYS should be exposed to the client
    // All API calls go through backend proxy endpoints
    
    // Safe configuration values only
    EXPO_PUBLIC_API_URL: process.env.EXPO_PUBLIC_API_URL,
    EXPO_PUBLIC_ENVIRONMENT: process.env.EXPO_PUBLIC_ENVIRONMENT || 'production',
    EXPO_PUBLIC_PLATFORM: process.env.EXPO_PUBLIC_PLATFORM,
    
    // Feature flags (safe to expose)
    EXPO_PUBLIC_MVP_MODE: process.env.EXPO_PUBLIC_MVP_MODE || 'false',
    EXPO_PUBLIC_ENABLE_BOOKING: process.env.EXPO_PUBLIC_ENABLE_BOOKING || 'true',
    EXPO_PUBLIC_ENABLE_VOICE: process.env.EXPO_PUBLIC_ENABLE_VOICE || 'true',
    EXPO_PUBLIC_ENABLE_AR: process.env.EXPO_PUBLIC_ENABLE_AR || 'true',
    
    // App configuration (safe to expose)
    EXPO_PUBLIC_APP_NAME: process.env.EXPO_PUBLIC_APP_NAME || 'AI Road Trip Storyteller',
    
    // Monitoring (client-safe)
    EXPO_PUBLIC_SENTRY_DSN: process.env.EXPO_PUBLIC_SENTRY_DSN,
  },
  plugins: [
    'expo-constants',
    // Voice recognition plugin with permissions
    ['@react-native-voice/voice', {
      microphonePermission: 'AI Road Trip needs microphone access for voice commands while driving',
      speechRecognitionPermission: 'AI Road Trip uses speech recognition for hands-free navigation'
    }]
  ],
  // Enable Hermes for better performance and bytecode compilation
  expo: {
    jsEngine: 'hermes'
  },
  // iOS specific Hermes configuration
  ios: {
    supportsTablet: true,
    bundleIdentifier: 'com.roadtrip.app',
    jsEngine: 'hermes',
    infoPlist: {
      NSLocationWhenInUseUsageDescription: 'AI Road Trip needs location to provide stories about places you\'re driving past',
      NSLocationAlwaysUsageDescription: 'AI Road Trip uses location to track your journey and provide continuous stories',
      NSMicrophoneUsageDescription: 'AI Road Trip needs microphone access for voice commands',
      NSSpeechRecognitionUsageDescription: 'AI Road Trip uses speech recognition for hands-free operation',
      UIBackgroundModes: ['location', 'audio']
    }
  },
  // Android specific Hermes configuration
  android: {
    adaptiveIcon: {
      foregroundImage: './assets/adaptive-icon.png',
      backgroundColor: '#ffffff'
    },
    package: 'com.roadtrip.app',
    jsEngine: 'hermes',
    permissions: [
      'ACCESS_FINE_LOCATION',
      'ACCESS_COARSE_LOCATION',
      'ACCESS_BACKGROUND_LOCATION',
      'RECORD_AUDIO',
      'FOREGROUND_SERVICE'
    ]
  }
}; 