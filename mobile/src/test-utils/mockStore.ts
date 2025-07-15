import configureStore from 'redux-mock-store';
import thunk from 'redux-thunk';

const middlewares = [thunk];
const mockStoreCreator = configureStore(middlewares);

export const mockStore = (initialState = {}) => {
  return mockStoreCreator({
    user: {
      isAuthenticated: false,
      profile: null,
      preferences: {
        voicePersonality: 'morgan-freeman',
        autoPlayStories: true,
        offlineMode: false,
      },
      ...initialState.user,
    },
    app: {
      isLoading: false,
      error: null,
      isOnline: true,
      currentVersion: '1.0.0',
      ...initialState.app,
    },
    story: {
      currentStory: null,
      isPlaying: false,
      history: [],
      favorites: [],
      ...initialState.story,
    },
    voice: {
      personality: 'morgan-freeman',
      isListening: false,
      isProcessing: false,
      lastTranscript: null,
      ...initialState.voice,
    },
    navigation: {
      currentRoute: null,
      destination: null,
      waypoints: [],
      isDrivingMode: false,
      ...initialState.navigation,
    },
    booking: {
      currentBooking: null,
      bookingHistory: [],
      savedSearches: [],
      ...initialState.booking,
    },
    location: {
      currentLocation: null,
      permissionStatus: 'granted',
      trackingEnabled: true,
      ...initialState.location,
    },
    offline: {
      downloadedMaps: [],
      cachedStories: [],
      pendingSync: [],
      ...initialState.offline,
    },
    ...initialState,
  });
};