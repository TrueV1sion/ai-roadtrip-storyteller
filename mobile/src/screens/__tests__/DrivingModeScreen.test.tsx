import React from 'react';
import { render, fireEvent, waitFor, act } from '@testing-library/react-native';
import { NavigationContainer } from '@react-navigation/native';
import { DrivingModeScreen } from '../DrivingModeScreen';
import { AppProvider } from '../../contexts/AppContext';
import * as Speech from 'expo-speech';
import * as Location from 'expo-location';

// Mock dependencies
jest.mock('expo-speech');
jest.mock('expo-location');
jest.mock('../../services/drivingAssistantService');
jest.mock('../../services/weatherService');
jest.mock('../../services/api/ApiClient');

const mockNavigation = {
  navigate: jest.fn(),
  goBack: jest.fn(),
  setOptions: jest.fn(),
};

const mockRoute = {
  params: {
    destination: { latitude: 34.0522, longitude: -118.2437, name: 'Los Angeles' },
  },
};

const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AppProvider>
    <NavigationContainer>{children}</NavigationContainer>
  </AppProvider>
);

describe('DrivingModeScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (Location.requestForegroundPermissionsAsync as jest.Mock).mockResolvedValue({
      status: 'granted',
    });
    (Location.getCurrentPositionAsync as jest.Mock).mockResolvedValue({
      coords: {
        latitude: 37.7749,
        longitude: -122.4194,
        speed: 25, // meters/second
      },
    });
    (Speech.speak as jest.Mock).mockImplementation(() => {});
  });

  it('renders correctly', () => {
    const { getByText, getByTestId } = render(
      <TestWrapper>
        <DrivingModeScreen navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    expect(getByText(/Driving Mode/)).toBeTruthy();
    expect(getByTestId('speed-display')).toBeTruthy();
    expect(getByTestId('voice-assistant-button')).toBeTruthy();
  });

  it('displays current speed', async () => {
    const { getByText } = render(
      <TestWrapper>
        <DrivingModeScreen navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    await waitFor(() => {
      // 25 m/s = 56 mph
      expect(getByText(/56 mph/)).toBeTruthy();
    });
  });

  it('handles voice commands toggle', () => {
    const { getByTestId } = render(
      <TestWrapper>
        <DrivingModeScreen navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    const voiceButton = getByTestId('voice-assistant-button');
    fireEvent.press(voiceButton);

    expect(getByTestId('voice-active-indicator')).toBeTruthy();

    fireEvent.press(voiceButton);
    expect(() => getByTestId('voice-active-indicator')).toThrow();
  });

  it('displays weather information', async () => {
    const mockWeatherService = require('../../services/weatherService');
    mockWeatherService.getWeatherForLocation.mockResolvedValue({
      temp: 72,
      condition: 'Sunny',
      icon: '01d',
    });

    const { getByText } = render(
      <TestWrapper>
        <DrivingModeScreen navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(getByText(/72°F/)).toBeTruthy();
      expect(getByText(/Sunny/)).toBeTruthy();
    });
  });

  it('displays driving alerts', async () => {
    const mockDrivingService = require('../../services/drivingAssistantService');
    mockDrivingService.getDrivingAlerts.mockResolvedValue([
      {
        id: '1',
        type: 'traffic',
        message: 'Heavy traffic ahead in 5 miles',
        severity: 'warning',
      },
    ]);

    const { getByText } = render(
      <TestWrapper>
        <DrivingModeScreen navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(getByText(/Heavy traffic ahead/)).toBeTruthy();
    });
  });

  it('announces alerts via speech', async () => {
    const mockDrivingService = require('../../services/drivingAssistantService');
    mockDrivingService.getDrivingAlerts.mockResolvedValue([
      {
        id: '1',
        type: 'fuel',
        message: 'Low fuel - gas station in 2 miles',
        severity: 'high',
      },
    ]);

    render(
      <TestWrapper>
        <DrivingModeScreen navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(Speech.speak).toHaveBeenCalledWith(
        expect.stringContaining('Low fuel'),
        expect.any(Object)
      );
    });
  });

  it('handles quick actions', () => {
    const { getByTestId } = render(
      <TestWrapper>
        <DrivingModeScreen navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    const fuelButton = getByTestId('quick-action-fuel');
    fireEvent.press(fuelButton);

    expect(mockNavigation.navigate).toHaveBeenCalledWith('FuelStations');
  });

  it('adapts UI based on speed', async () => {
    const { getByTestId, rerender } = render(
      <TestWrapper>
        <DrivingModeScreen navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    // Update to high speed
    (Location.getCurrentPositionAsync as jest.Mock).mockResolvedValue({
      coords: {
        latitude: 37.7749,
        longitude: -122.4194,
        speed: 35, // meters/second (~78 mph)
      },
    });

    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    // Should show simplified UI at high speed
    expect(getByTestId('simplified-ui')).toBeTruthy();
  });

  it('handles rest break suggestions', async () => {
    // Simulate 2 hours of driving
    jest.useFakeTimers();
    
    const { getByText } = render(
      <TestWrapper>
        <DrivingModeScreen navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    act(() => {
      jest.advanceTimersByTime(2 * 60 * 60 * 1000); // 2 hours
    });

    await waitFor(() => {
      expect(getByText(/Time for a break/)).toBeTruthy();
    });

    jest.useRealTimers();
  });

  it('handles navigation exit', () => {
    const { getByTestId } = render(
      <TestWrapper>
        <DrivingModeScreen navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    const exitButton = getByTestId('exit-driving-mode');
    fireEvent.press(exitButton);

    expect(mockNavigation.goBack).toHaveBeenCalled();
  });

  it('displays ETA and distance', async () => {
    const mockDrivingService = require('../../services/drivingAssistantService');
    mockDrivingService.getRouteInfo.mockResolvedValue({
      distance: 380, // miles
      duration: 360, // minutes
      eta: new Date(Date.now() + 360 * 60 * 1000),
    });

    const { getByText } = render(
      <TestWrapper>
        <DrivingModeScreen navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(getByText(/380 miles/)).toBeTruthy();
      expect(getByText(/6 hours/)).toBeTruthy();
    });
  });

  it('handles offline mode', async () => {
    const mockDrivingService = require('../../services/drivingAssistantService');
    mockDrivingService.getDrivingAlerts.mockRejectedValue(new Error('Network error'));

    const { getByText } = render(
      <TestWrapper>
        <DrivingModeScreen navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(getByText(/Offline Mode/)).toBeTruthy();
    });
  });
});