import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { NavigationContainer } from '@react-navigation/native';
import { RideshareScreen } from '../RideshareScreen';
import { AppProvider } from '../../contexts/AppContext';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Mock dependencies
jest.mock('@react-native-async-storage/async-storage');
jest.mock('../../services/rideshareService');
jest.mock('../../services/voiceService');

const mockNavigation = {
  navigate: jest.fn(),
  goBack: jest.fn(),
};

const mockRoute = {
  params: {},
};

const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AppProvider>
    <NavigationContainer>{children}</NavigationContainer>
  </AppProvider>
);

describe('RideshareScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (AsyncStorage.getItem as jest.Mock).mockResolvedValue(null);
  });

  it('renders mode selection initially', () => {
    const { getByText, getByTestId } = render(
      <TestWrapper>
        <RideshareScreen navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    expect(getByText(/Choose Your Mode/)).toBeTruthy();
    expect(getByTestId('driver-mode-button')).toBeTruthy();
    expect(getByTestId('passenger-mode-button')).toBeTruthy();
  });

  it('handles driver mode selection', () => {
    const { getByTestId } = render(
      <TestWrapper>
        <RideshareScreen navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    const driverButton = getByTestId('driver-mode-button');
    fireEvent.press(driverButton);

    expect(mockNavigation.navigate).toHaveBeenCalledWith('RideshareDriverMode', {
      mode: 'driver',
    });
  });

  it('handles passenger mode selection', () => {
    const { getByTestId } = render(
      <TestWrapper>
        <RideshareScreen navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    const passengerButton = getByTestId('passenger-mode-button');
    fireEvent.press(passengerButton);

    expect(mockNavigation.navigate).toHaveBeenCalledWith('RidesharePassengerMode', {
      mode: 'passenger',
    });
  });

  it('remembers last mode selection', async () => {
    (AsyncStorage.getItem as jest.Mock).mockResolvedValue('driver');

    const { queryByText } = render(
      <TestWrapper>
        <RideshareScreen navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(mockNavigation.navigate).toHaveBeenCalledWith('RideshareDriverMode', {
        mode: 'driver',
      });
    });

    // Should not show mode selection
    expect(queryByText(/Choose Your Mode/)).toBeNull();
  });

  it('displays feature highlights', () => {
    const { getByText } = render(
      <TestWrapper>
        <RideshareScreen navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    // Driver features
    expect(getByText(/Voice Navigation/)).toBeTruthy();
    expect(getByText(/Earnings Tracker/)).toBeTruthy();
    expect(getByText(/Passenger Info/)).toBeTruthy();

    // Passenger features
    expect(getByText(/Entertainment Options/)).toBeTruthy();
    expect(getByText(/Trip Stories/)).toBeTruthy();
    expect(getByText(/Journey Games/)).toBeTruthy();
  });

  it('handles back navigation', () => {
    const { getByTestId } = render(
      <TestWrapper>
        <RideshareScreen navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    const backButton = getByTestId('back-button');
    fireEvent.press(backButton);

    expect(mockNavigation.goBack).toHaveBeenCalled();
  });

  it('saves mode preference', async () => {
    const { getByTestId } = render(
      <TestWrapper>
        <RideshareScreen navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    const driverButton = getByTestId('driver-mode-button');
    fireEvent.press(driverButton);

    await waitFor(() => {
      expect(AsyncStorage.setItem).toHaveBeenCalledWith('rideshare_mode', 'driver');
    });
  });

  it('displays tutorial for first-time users', async () => {
    (AsyncStorage.getItem as jest.Mock)
      .mockResolvedValueOnce(null) // No saved mode
      .mockResolvedValueOnce(null); // No tutorial seen

    const { getByText } = render(
      <TestWrapper>
        <RideshareScreen navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(getByText(/Welcome to Rideshare Mode/)).toBeTruthy();
    });
  });

  it('handles quick start with voice command', () => {
    const { getByTestId } = render(
      <TestWrapper>
        <RideshareScreen navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    const voiceButton = getByTestId('voice-quick-start');
    fireEvent.press(voiceButton);

    const mockVoiceService = require('../../services/voiceService');
    expect(mockVoiceService.startListening).toHaveBeenCalled();
  });

  it('shows accessibility options', () => {
    const { getByTestId } = render(
      <TestWrapper>
        <RideshareScreen navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    const accessibilityButton = getByTestId('accessibility-toggle');
    fireEvent.press(accessibilityButton);

    expect(getByTestId('large-button-mode')).toBeTruthy();
    expect(getByTestId('voice-only-mode')).toBeTruthy();
  });
});