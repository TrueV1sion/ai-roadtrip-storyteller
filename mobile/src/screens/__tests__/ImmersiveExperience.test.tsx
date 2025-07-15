import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { NavigationContainer } from '@react-navigation/native';
import { ImmersiveExperience } from '../ImmersiveExperience';
import * as Location from 'expo-location';
import { AppProvider } from '../../contexts/AppContext';

// Mock dependencies
jest.mock('expo-location');
jest.mock('../../services/storyService');
jest.mock('../../services/spotifyService');
jest.mock('../../services/api/immersiveApi');

const mockNavigation = {
  navigate: jest.fn(),
  goBack: jest.fn(),
};

const mockRoute = {
  params: {
    origin: { latitude: 37.7749, longitude: -122.4194, name: 'San Francisco' },
    destination: { latitude: 34.0522, longitude: -118.2437, name: 'Los Angeles' },
  },
};

const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AppProvider>
    <NavigationContainer>{children}</NavigationContainer>
  </AppProvider>
);

describe('ImmersiveExperience', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (Location.requestForegroundPermissionsAsync as jest.Mock).mockResolvedValue({
      status: 'granted',
    });
    (Location.getCurrentPositionAsync as jest.Mock).mockResolvedValue({
      coords: {
        latitude: 37.7749,
        longitude: -122.4194,
      },
    });
  });

  it('renders correctly', () => {
    const { getByText, getByTestId } = render(
      <TestWrapper>
        <ImmersiveExperience navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    expect(getByText(/San Francisco/)).toBeTruthy();
    expect(getByText(/Los Angeles/)).toBeTruthy();
  });

  it('requests location permissions on mount', async () => {
    render(
      <TestWrapper>
        <ImmersiveExperience navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(Location.requestForegroundPermissionsAsync).toHaveBeenCalled();
    });
  });

  it('handles location permission denial', async () => {
    (Location.requestForegroundPermissionsAsync as jest.Mock).mockResolvedValue({
      status: 'denied',
    });

    const { getByText } = render(
      <TestWrapper>
        <ImmersiveExperience navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(getByText(/Location access is required/)).toBeTruthy();
    });
  });

  it('toggles music player', () => {
    const { getByTestId, queryByTestId } = render(
      <TestWrapper>
        <ImmersiveExperience navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    const musicButton = getByTestId('music-toggle');
    expect(queryByTestId('music-player')).toBeNull();

    fireEvent.press(musicButton);
    expect(queryByTestId('music-player')).toBeTruthy();

    fireEvent.press(musicButton);
    expect(queryByTestId('music-player')).toBeNull();
  });

  it('toggles AR mode', () => {
    const { getByTestId, queryByTestId } = render(
      <TestWrapper>
        <ImmersiveExperience navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    const arButton = getByTestId('ar-toggle');
    expect(queryByTestId('ar-view')).toBeNull();

    fireEvent.press(arButton);
    expect(queryByTestId('ar-view')).toBeTruthy();

    fireEvent.press(arButton);
    expect(queryByTestId('ar-view')).toBeNull();
  });

  it('handles story loading', async () => {
    const mockStoryService = require('../../services/storyService');
    mockStoryService.getStoriesAlongRoute.mockResolvedValue([
      {
        id: '1',
        title: 'Test Story',
        content: 'Test content',
        audioUrl: 'test.mp3',
      },
    ]);

    const { getByText } = render(
      <TestWrapper>
        <ImmersiveExperience navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(getByText('Test Story')).toBeTruthy();
    });
  });

  it('handles navigation back', () => {
    const { getByTestId } = render(
      <TestWrapper>
        <ImmersiveExperience navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    const backButton = getByTestId('back-button');
    fireEvent.press(backButton);

    expect(mockNavigation.goBack).toHaveBeenCalled();
  });

  it('displays loading state initially', () => {
    const { getByTestId } = render(
      <TestWrapper>
        <ImmersiveExperience navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    expect(getByTestId('loading-indicator')).toBeTruthy();
  });

  it('updates when location changes', async () => {
    const { rerender } = render(
      <TestWrapper>
        <ImmersiveExperience navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    // Simulate location update
    (Location.getCurrentPositionAsync as jest.Mock).mockResolvedValue({
      coords: {
        latitude: 36.0,
        longitude: -120.0,
      },
    });

    await waitFor(() => {
      expect(Location.getCurrentPositionAsync).toHaveBeenCalledTimes(1);
    });
  });

  it('handles interest selection', () => {
    const { getByText, getByTestId } = render(
      <TestWrapper>
        <ImmersiveExperience navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    const interestButton = getByTestId('interest-history');
    fireEvent.press(interestButton);

    // Verify interest is selected (visual feedback)
    expect(interestButton).toHaveStyle({ backgroundColor: expect.any(String) });
  });

  it('handles trivia modal', async () => {
    const { getByTestId, queryByTestId } = render(
      <TestWrapper>
        <ImmersiveExperience navigation={mockNavigation} route={mockRoute} />
      </TestWrapper>
    );

    // Wait for stories to load
    await waitFor(() => {
      expect(getByTestId('story-card-0')).toBeTruthy();
    });

    const storyCard = getByTestId('story-card-0');
    fireEvent.press(storyCard);

    await waitFor(() => {
      expect(queryByTestId('trivia-modal')).toBeTruthy();
    });
  });
});