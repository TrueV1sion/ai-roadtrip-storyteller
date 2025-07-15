import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react-native';
import { Provider } from 'react-redux';
import { NavigationContainer } from '@react-navigation/native';
import { configureStore } from '@reduxjs/toolkit';
import { AuthProvider } from '@/contexts/AuthContext';

// Create a mock store for testing
const createMockStore = (initialState = {}) => {
  return configureStore({
    reducer: {
      // Add your reducers here as you implement them
      auth: (state = { user: null, isAuthenticated: false }) => state,
      navigation: (state = { currentRoute: 'Home' }) => state,
      voice: (state = { isListening: false }) => state,
      booking: (state = { activeBooking: null }) => state,
    },
    preloadedState: initialState,
  });
};

// Mock auth context
const mockAuthContext = {
  user: null,
  isAuthenticated: false,
  login: jest.fn(),
  logout: jest.fn(),
  register: jest.fn(),
};

interface AllTheProvidersProps {
  children: React.ReactNode;
  initialState?: any;
}

// Wrapper component with all providers
const AllTheProviders: React.FC<AllTheProvidersProps> = ({ 
  children, 
  initialState = {} 
}) => {
  const store = createMockStore(initialState);

  return (
    <Provider store={store}>
      <AuthProvider value={mockAuthContext}>
        <NavigationContainer>
          {children}
        </NavigationContainer>
      </AuthProvider>
    </Provider>
  );
};

// Custom render method
const customRender = (
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'> & { initialState?: any }
) => {
  const { initialState, ...renderOptions } = options || {};
  
  return render(ui, {
    wrapper: ({ children }) => (
      <AllTheProviders initialState={initialState}>
        {children}
      </AllTheProviders>
    ),
    ...renderOptions,
  });
};

// Re-export everything
export * from '@testing-library/react-native';
export { customRender as render, createMockStore };

// Test data factories
export const createMockUser = (overrides = {}) => ({
  id: '1',
  email: 'test@example.com',
  name: 'Test User',
  preferences: {
    voiceEnabled: true,
    personality: 'friendly',
  },
  ...overrides,
});

export const createMockLocation = (overrides = {}) => ({
  latitude: 37.7749,
  longitude: -122.4194,
  altitude: 0,
  accuracy: 10,
  heading: 0,
  speed: 0,
  ...overrides,
});

export const createMockStory = (overrides = {}) => ({
  id: '1',
  title: 'Test Story',
  content: 'This is a test story content',
  location: createMockLocation(),
  timestamp: new Date().toISOString(),
  ...overrides,
});

export const createMockBooking = (overrides = {}) => ({
  id: '1',
  type: 'restaurant',
  name: 'Test Restaurant',
  dateTime: new Date().toISOString(),
  status: 'confirmed',
  confirmationCode: 'ABC123',
  ...overrides,
});