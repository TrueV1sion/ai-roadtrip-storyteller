/**
 * Development Mode Configuration
 * Provides fallback values and mock data for local development
 */

export const DevelopmentConfig = {
  // Enable development features
  ENABLE_MOCK_DATA: true,
  ENABLE_OFFLINE_MODE: true,
  SKIP_PERMISSIONS: false, // Still ask for permissions but handle gracefully
  DISABLE_SECURITY: true, // Disable certificate pinning etc for local dev
  
  // Mock user for testing
  MOCK_USER: {
    id: 'dev-user-123',
    email: 'dev@roadtrip.local',
    name: 'Development User',
    preferences: {
      voicePersonality: 'morgan-freeman',
      language: 'en',
      theme: 'light'
    }
  },
  
  // Mock location for testing (San Francisco)
  MOCK_LOCATION: {
    latitude: 37.7749,
    longitude: -122.4194,
    speed: 0,
    heading: 0,
    accuracy: 10
  },
  
  // Development API endpoints that return mock data
  MOCK_ENDPOINTS: {
    '/api/mvp/voice': {
      response: {
        text: "Welcome to AI Road Trip! I'm your development assistant. Since we're in development mode, I'll provide mock responses.",
        audio_url: null,
        personality: 'morgan-freeman'
      }
    },
    '/api/stories/generate': {
      response: {
        story: {
          id: 'mock-story-1',
          title: 'The Golden Gate Bridge',
          content: 'As you approach the iconic Golden Gate Bridge, let me tell you about its fascinating history. This engineering marvel was completed in 1937...',
          location: {
            latitude: 37.8199,
            longitude: -122.4783
          },
          audio_url: null
        }
      }
    },
    '/api/navigation/route': {
      response: {
        route: {
          distance: '5.2 miles',
          duration: '12 minutes',
          steps: [
            'Head north on Market St',
            'Turn left onto Van Ness Ave',
            'Continue to destination'
          ]
        }
      }
    }
  }
};

// Helper function to check if we should use mock data
export const shouldUseMockData = (): boolean => {
  return __DEV__ && DevelopmentConfig.ENABLE_MOCK_DATA;
};

// Helper function to get mock response for an endpoint
export const getMockResponse = (endpoint: string): any => {
  const mockEndpoint = Object.keys(DevelopmentConfig.MOCK_ENDPOINTS).find(
    key => endpoint.includes(key)
  );
  
  if (mockEndpoint) {
    return DevelopmentConfig.MOCK_ENDPOINTS[mockEndpoint as keyof typeof DevelopmentConfig.MOCK_ENDPOINTS].response;
  }
  
  return null;
};