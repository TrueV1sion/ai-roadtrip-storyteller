import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import * as Location from 'expo-location';

import NavigationView from '../NavigationView';
import { navigationService } from '../../../services/navigation/navigationService';

// Mock dependencies
jest.mock('expo-location');
jest.mock('../../../services/navigation/navigationService');
jest.mock('react-native-maps', () => ({
  default: 'MapView',
  Marker: 'Marker',
  Polyline: 'Polyline',
  PROVIDER_GOOGLE: 'google',
}));

const mockLocation = Location as jest.Mocked<typeof Location>;
const mockNavigationService = navigationService as jest.Mocked<typeof navigationService>;

const mockStore = configureStore({
  reducer: {
    navigation: (state = {
      currentRoute: null,
      destination: null,
      isNavigating: false,
      currentLocation: { lat: 37.7749, lng: -122.4194 },
    }) => state,
    settings: (state = {
      navigationPreferences: {
        avoidTolls: false,
        avoidHighways: false,
        preferScenic: true,
      },
    }) => state,
  },
});

const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <Provider store={mockStore}>
      {component}
    </Provider>
  );
};

describe('NavigationView Component', () => {
  const mockRoute = {
    distance: 50.5,
    duration: 3600,
    polyline: 'encodedPolylineString',
    steps: [
      {
        instruction: 'Head north on Market St',
        distance: 0.5,
        duration: 120,
        maneuver: 'turn-left',
      },
      {
        instruction: 'Turn right onto Van Ness Ave',
        distance: 2.0,
        duration: 300,
        maneuver: 'turn-right',
      },
    ],
    bounds: {
      northeast: { lat: 37.8, lng: -122.4 },
      southwest: { lat: 37.7, lng: -122.5 },
    },
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockLocation.getCurrentPositionAsync.mockResolvedValue({
      coords: {
        latitude: 37.7749,
        longitude: -122.4194,
        altitude: 0,
        accuracy: 5,
        altitudeAccuracy: 5,
        heading: 0,
        speed: 0,
      },
      timestamp: Date.now(),
    });
  });

  it('renders navigation interface', () => {
    const { getByTestId, getByText } = renderWithProviders(
      <NavigationView route={mockRoute} destination="Golden Gate Bridge" />
    );
    
    expect(getByTestId('navigation-map')).toBeTruthy();
    expect(getByText('50.5 km')).toBeTruthy();
    expect(getByText('1 hr')).toBeTruthy();
  });

  it('displays turn-by-turn instructions', () => {
    const { getByText } = renderWithProviders(
      <NavigationView route={mockRoute} destination="Golden Gate Bridge" />
    );
    
    expect(getByText('Head north on Market St')).toBeTruthy();
    expect(getByText('Turn right onto Van Ness Ave')).toBeTruthy();
  });

  it('updates current location during navigation', async () => {
    const { getByTestId } = renderWithProviders(
      <NavigationView 
        route={mockRoute} 
        destination="Golden Gate Bridge"
        isNavigating={true}
      />
    );
    
    // Simulate location update
    const newLocation = {
      coords: {
        latitude: 37.7759,
        longitude: -122.4184,
        altitude: 0,
        accuracy: 5,
        altitudeAccuracy: 5,
        heading: 45,
        speed: 10,
      },
      timestamp: Date.now(),
    };
    
    mockLocation.watchPositionAsync.mockImplementation(async (options, callback) => {
      callback(newLocation);
      return { remove: jest.fn() };
    });
    
    await waitFor(() => {
      expect(mockLocation.watchPositionAsync).toHaveBeenCalled();
    });
  });

  it('shows next turn indicator', () => {
    const { getByTestId, getByText } = renderWithProviders(
      <NavigationView 
        route={mockRoute} 
        destination="Golden Gate Bridge"
        isNavigating={true}
      />
    );
    
    expect(getByTestId('next-turn-indicator')).toBeTruthy();
    expect(getByText('500 m')).toBeTruthy(); // Distance to next turn
  });

  it('handles route recalculation', async () => {
    const { getByText } = renderWithProviders(
      <NavigationView 
        route={mockRoute} 
        destination="Golden Gate Bridge"
        isNavigating={true}
      />
    );
    
    // Simulate going off route
    mockNavigationService.checkIfOnRoute.mockReturnValue(false);
    mockNavigationService.recalculateRoute.mockResolvedValue({
      ...mockRoute,
      distance: 52.0,
      duration: 3700,
    });
    
    await waitFor(() => {
      expect(getByText('Recalculating route...')).toBeTruthy();
    });
    
    await waitFor(() => {
      expect(mockNavigationService.recalculateRoute).toHaveBeenCalled();
      expect(getByText('52 km')).toBeTruthy();
    });
  });

  it('provides voice guidance toggle', async () => {
    const { getByTestId } = renderWithProviders(
      <NavigationView 
        route={mockRoute} 
        destination="Golden Gate Bridge"
        isNavigating={true}
      />
    );
    
    const voiceToggle = getByTestId('voice-guidance-toggle');
    expect(voiceToggle).toBeTruthy();
    
    fireEvent.press(voiceToggle);
    
    await waitFor(() => {
      expect(mockNavigationService.setVoiceGuidance).toHaveBeenCalledWith(false);
    });
  });

  it('shows arrival notification', async () => {
    const { getByText } = renderWithProviders(
      <NavigationView 
        route={mockRoute} 
        destination="Golden Gate Bridge"
        isNavigating={true}
      />
    );
    
    // Simulate approaching destination
    mockNavigationService.getDistanceToDestination.mockReturnValue(0.05); // 50 meters
    
    await waitFor(() => {
      expect(getByText('Arriving at Golden Gate Bridge')).toBeTruthy();
    });
  });

  it('displays traffic conditions', () => {
    const routeWithTraffic = {
      ...mockRoute,
      trafficConditions: [
        {
          severity: 'heavy',
          description: 'Heavy traffic on US-101',
          delay: 600, // 10 minutes
          start: 10,
          end: 20,
        },
      ],
    };
    
    const { getByText, getByTestId } = renderWithProviders(
      <NavigationView route={routeWithTraffic} destination="Golden Gate Bridge" />
    );
    
    expect(getByTestId('traffic-warning')).toBeTruthy();
    expect(getByText('Heavy traffic ahead')).toBeTruthy();
    expect(getByText('+10 min')).toBeTruthy();
  });

  it('allows route customization', async () => {
    const onRouteOptionsChange = jest.fn();
    const { getByTestId } = renderWithProviders(
      <NavigationView 
        route={mockRoute} 
        destination="Golden Gate Bridge"
        onRouteOptionsChange={onRouteOptionsChange}
      />
    );
    
    const optionsButton = getByTestId('route-options-button');
    fireEvent.press(optionsButton);
    
    await waitFor(() => {
      expect(getByTestId('avoid-tolls-toggle')).toBeTruthy();
      expect(getByTestId('avoid-highways-toggle')).toBeTruthy();
    });
    
    fireEvent.press(getByTestId('avoid-tolls-toggle'));
    
    expect(onRouteOptionsChange).toHaveBeenCalledWith({
      avoidTolls: true,
      avoidHighways: false,
      preferScenic: true,
    });
  });

  it('shows alternate routes', async () => {
    const alternateRoutes = [
      mockRoute,
      { ...mockRoute, distance: 48, duration: 3300, via: 'US-101' },
      { ...mockRoute, distance: 55, duration: 3200, via: 'I-280' },
    ];
    
    const { getByText, getAllByTestId } = renderWithProviders(
      <NavigationView 
        route={mockRoute} 
        alternateRoutes={alternateRoutes}
        destination="Golden Gate Bridge"
      />
    );
    
    const routeCards = getAllByTestId(/route-option-/);
    expect(routeCards).toHaveLength(3);
    
    expect(getByText('via US-101')).toBeTruthy();
    expect(getByText('via I-280')).toBeTruthy();
  });

  it('handles navigation cancellation', async () => {
    const onCancel = jest.fn();
    const { getByTestId } = renderWithProviders(
      <NavigationView 
        route={mockRoute} 
        destination="Golden Gate Bridge"
        isNavigating={true}
        onCancel={onCancel}
      />
    );
    
    const cancelButton = getByTestId('cancel-navigation');
    fireEvent.press(cancelButton);
    
    await waitFor(() => {
      expect(getByText('End navigation?')).toBeTruthy();
    });
    
    fireEvent.press(getByText('Yes'));
    expect(onCancel).toHaveBeenCalled();
  });

  it('displays speed limit warnings', async () => {
    const { getByTestId } = renderWithProviders(
      <NavigationView 
        route={mockRoute} 
        destination="Golden Gate Bridge"
        isNavigating={true}
      />
    );
    
    // Simulate speeding
    mockNavigationService.getCurrentSpeed.mockReturnValue(75); // mph
    mockNavigationService.getSpeedLimit.mockReturnValue(65); // mph
    
    await waitFor(() => {
      const speedWarning = getByTestId('speed-warning');
      expect(speedWarning).toBeTruthy();
      expect(speedWarning).toHaveStyle({ backgroundColor: '#ff0000' });
    });
  });

  it('shows offline mode indicator', () => {
    const { getByTestId } = renderWithProviders(
      <NavigationView 
        route={mockRoute} 
        destination="Golden Gate Bridge"
        isOffline={true}
      />
    );
    
    expect(getByTestId('offline-indicator')).toBeTruthy();
    expect(getByText('Offline Navigation')).toBeTruthy();
  });
});