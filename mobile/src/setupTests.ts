// Jest setup for React Native testing

// Add Jest types to global scope
declare global {
  namespace jest {
    interface Matchers<R> {
      toHaveStyle: (style: object) => R;
      toBeEnabled: () => R;
      toBeDisabled: () => R;
      toBeVisible: () => R;
      toBeOnTheScreen: () => R;
      toHaveProp: (prop: string, value?: any) => R;
      toHaveTextContent: (text: string | RegExp) => R;
      toHaveProperty: (property: string) => R;
    }
  }

  // Add Jest itself to global scope
  const jest: typeof import('jest');
  const expect: typeof import('expect');
  const describe: typeof import('jest').Describe;
  const test: typeof import('jest').It;
  const beforeEach: typeof import('jest').Hook;
  const afterEach: typeof import('jest').Hook;
}

// Mock environment variables
process.env.APP_ENV = 'test';
process.env.API_URL = 'http://test-api.example.com';

// Enhanced Platform mock with dynamic OS switching
const Platform = require('react-native/Libraries/Utilities/Platform');
Platform.OS = 'ios';
Platform.select = jest.fn(obj => obj[Platform.OS]);
Platform.setOS = (os: 'ios' | 'android') => {
  Platform.OS = os;
};

// Enhanced Dimensions mock with dynamic screen size
const Dimensions = require('react-native/Libraries/Utilities/Dimensions');
let dimensionsData = { width: 375, height: 812 };
Dimensions.get = jest.fn().mockReturnValue(dimensionsData);
Dimensions.set = (dimensions: { width: number; height: number }) => {
  dimensionsData = dimensions;
  Dimensions.get.mockReturnValue(dimensionsData);
};

// Enhanced AsyncStorage mock with error simulation
jest.mock('@react-native-async-storage/async-storage', () => {
  const mockStorage: { [key: string]: string } = {};
  return {
    getItem: jest.fn((key: string) => Promise.resolve(mockStorage[key])),
    setItem: jest.fn((key: string, value: string) => {
      mockStorage[key] = value;
      return Promise.resolve();
    }),
    removeItem: jest.fn((key: string) => {
      delete mockStorage[key];
      return Promise.resolve();
    }),
    clear: jest.fn(() => {
      Object.keys(mockStorage).forEach(key => delete mockStorage[key]);
      return Promise.resolve();
    }),
    getAllKeys: jest.fn(() => Promise.resolve(Object.keys(mockStorage))),
    multiGet: jest.fn((keys: string[]) => 
      Promise.resolve(keys.map(key => [key, mockStorage[key]]))
    ),
    multiSet: jest.fn((keyValuePairs: string[][]) => {
      keyValuePairs.forEach(([key, value]) => {
        mockStorage[key] = value;
      });
      return Promise.resolve();
    }),
    multiRemove: jest.fn((keys: string[]) => {
      keys.forEach(key => delete mockStorage[key]);
      return Promise.resolve();
    }),
  };
});

// Enhanced Location mock with error simulation
jest.mock('expo-location', () => ({
  requestForegroundPermissionsAsync: jest.fn().mockResolvedValue({ status: 'granted' }),
  requestBackgroundPermissionsAsync: jest.fn().mockResolvedValue({ status: 'granted' }),
  getCurrentPositionAsync: jest.fn().mockResolvedValue({
    coords: {
      latitude: 40.7128,
      longitude: -74.0060,
      altitude: 0,
      accuracy: 5,
      altitudeAccuracy: 5,
      heading: 0,
      speed: 0,
    },
    timestamp: Date.now(),
  }),
  watchPositionAsync: jest.fn((options, callback) => ({
    remove: jest.fn(),
  })),
  setGoogleApiKey: jest.fn(),
  hasServicesEnabledAsync: jest.fn().mockResolvedValue(true),
  geocodeAsync: jest.fn().mockResolvedValue([{
    latitude: 40.7128,
    longitude: -74.0060,
    altitude: 0,
    accuracy: 5,
  }]),
}));

// Enhanced Speech mock with platform-specific voices
jest.mock('expo-speech', () => {
  const mockVoices = {
    ios: [
      { identifier: 'com.apple.ttsbundle.Samantha-compact', language: 'en-US' },
      { identifier: 'com.apple.ttsbundle.Karen-compact', language: 'en-AU' },
    ],
    android: [
      { identifier: 'en-us-x-sfg#female_1', language: 'en-US' },
      { identifier: 'en-us-x-sfg#male_1', language: 'en-US' },
    ],
  };

  return {
    speak: jest.fn(),
    stop: jest.fn(),
    pause: jest.fn(),
    resume: jest.fn(),
    isSpeakingAsync: jest.fn().mockResolvedValue(false),
    getAvailableVoicesAsync: jest.fn().mockImplementation(() => 
      Promise.resolve(mockVoices[Platform.OS])
    ),
  };
});

// Mock navigation with route params and deep linking
jest.mock('@react-navigation/native', () => {
  const actualNav = jest.requireActual('@react-navigation/native');
  return {
    ...actualNav,
    useNavigation: () => ({
      navigate: jest.fn(),
      goBack: jest.fn(),
      setParams: jest.fn(),
      addListener: jest.fn(),
      dispatch: jest.fn(),
    }),
    useRoute: () => ({
      params: {},
      name: 'TestScreen',
      key: 'test-screen',
    }),
    useLinking: () => ({
      getInitialState: jest.fn(),
    }),
  };
});

// Mock vector icons with custom icon sets
jest.mock('react-native-vector-icons/MaterialCommunityIcons', () => 'Icon');

// Mock StatusBar with system appearance
jest.mock('react-native/Libraries/Components/StatusBar/StatusBar', () => ({
  setBarStyle: jest.fn(),
  currentHeight: Platform.OS === 'ios' ? 44 : 24,
  setTranslucent: jest.fn(),
  setBackgroundColor: jest.fn(),
}));

// Silence console errors and warnings in tests
global.console.error = jest.fn();
global.console.warn = jest.fn();

// Add test utilities
global.waitForAnimation = () => new Promise(resolve => setTimeout(resolve, 0));
global.mockGeolocation = {
  getCurrentPosition: jest.fn(),
  watchPosition: jest.fn(),
  clearWatch: jest.fn(),
};

// Setup test environment flags
global.__TEST__ = true;
global.__DEV__ = true; 