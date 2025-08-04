/**
 * Test Drive Configuration
 * Optimized settings for testing the app while driving
 */

export const TestDriveConfig = {
  // Aggressive caching for poor connectivity
  CACHE_DURATION: 7200000, // 2 hours
  PREFETCH_RADIUS: 5000, // Prefetch content within 5km
  
  // Pre-cache common responses
  PRELOAD_ROUTES: [
    "Navigate to Golden Gate Bridge",
    "Take me to downtown",
    "Find interesting places nearby",
    "What's ahead on this route",
    "Tell me about this area"
  ],
  
  // Simplified voice commands for testing
  QUICK_COMMANDS: {
    start: "Hey Roadtrip, start navigation",
    story: "Tell me about this place",
    next: "What's coming up ahead",
    stop: "Stop navigation",
    pause: "Pause stories",
    resume: "Resume stories",
    louder: "Increase volume",
    quieter: "Decrease volume",
    personality: "Change voice to",
    help: "What can you do"
  },
  
  // Safety features
  SAFETY: {
    AUTO_LOCK_PREVENTION: true,
    LARGE_UI_MODE: true,
    VOICE_ONLY_FEEDBACK: true,
    MIN_BUTTON_SIZE: 60, // Minimum touch target size
    DRIVING_MODE_SPEED_THRESHOLD: 10, // mph
    AUTO_PAUSE_ON_CALL: true,
    EMERGENCY_COMMAND: "Hey Roadtrip, emergency"
  },
  
  // Voice configuration
  VOICE: {
    WAKE_WORD: "Hey Roadtrip",
    CONFIDENCE_THRESHOLD: 0.6, // Lower for noisy car environment
    NOISE_CANCELLATION: true,
    CONTINUOUS_LISTENING: true,
    TIMEOUT: 10000, // 10 seconds
    RETRY_ATTEMPTS: 3
  },
  
  // Story configuration
  STORIES: {
    MIN_DISTANCE_BETWEEN_STORIES: 1000, // meters
    STORY_TRIGGER_RADIUS: 500, // meters from POI
    MAX_STORY_LENGTH: 90, // seconds
    BUFFER_NEXT_STORIES: 3,
    CATEGORIES: [
      'history',
      'nature',
      'culture',
      'local_legends',
      'fun_facts'
    ]
  },
  
  // Navigation configuration
  NAVIGATION: {
    UPDATE_FREQUENCY: 5000, // Update every 5 seconds
    REROUTE_THRESHOLD: 100, // meters off route
    VOICE_GUIDANCE_TIMING: {
      highway: 2000, // 2km advance notice
      city: 500, // 500m advance notice
      turn: 100 // 100m for immediate turns
    }
  },
  
  // Performance optimizations
  PERFORMANCE: {
    BATTERY_SAVER_MODE: true,
    REDUCE_ANIMATIONS: true,
    OFFLINE_FIRST: true,
    MAX_CONCURRENT_REQUESTS: 2,
    REQUEST_TIMEOUT: 30000 // 30 seconds
  },
  
  // Debug features
  DEBUG: {
    SHOW_SPEED: true,
    SHOW_COORDINATES: true,
    SHOW_API_STATUS: true,
    LOG_VOICE_COMMANDS: true,
    MOCK_LOCATION_ENABLED: false
  }
};

// Helper functions for test drive

export const isDrivingMode = (speed: number): boolean => {
  return speed >= TestDriveConfig.SAFETY.DRIVING_MODE_SPEED_THRESHOLD;
};

export const shouldTriggerStory = (
  distanceFromLastStory: number,
  proximityToPOI: number
): boolean => {
  return (
    distanceFromLastStory >= TestDriveConfig.STORIES.MIN_DISTANCE_BETWEEN_STORIES &&
    proximityToPOI <= TestDriveConfig.STORIES.STORY_TRIGGER_RADIUS
  );
};

export const getVoiceGuidanceDistance = (roadType: 'highway' | 'city' | 'turn'): number => {
  return TestDriveConfig.NAVIGATION.VOICE_GUIDANCE_TIMING[roadType];
};

export const formatQuickCommand = (command: keyof typeof TestDriveConfig.QUICK_COMMANDS): string => {
  return TestDriveConfig.QUICK_COMMANDS[command];
};

// Safety check for emergency
export const isEmergencyCommand = (transcript: string): boolean => {
  const normalized = transcript.toLowerCase().trim();
  return normalized.includes('emergency') || normalized.includes('help') || normalized.includes('stop');
};

// Export mock data for offline testing
export const OFFLINE_TEST_DATA = {
  mockStories: [
    {
      id: 'test-1',
      title: 'Welcome to Your Test Drive',
      content: 'This is a test story that will play when you start driving. The AI Road Trip app is working correctly.',
      duration: 30
    },
    {
      id: 'test-2',
      title: 'Location Services Working',
      content: 'Great! Your location services are working. The app can now provide location-based stories.',
      duration: 25
    },
    {
      id: 'test-3',
      title: 'Voice Commands Active',
      content: 'Voice commands are active. Try saying "Hey Roadtrip" followed by a command.',
      duration: 20
    }
  ],
  mockRoute: {
    distance: '10 miles',
    duration: '20 minutes',
    steps: [
      'Continue straight for 2 miles',
      'Turn right at the light',
      'Your destination is on the left'
    ]
  }
};