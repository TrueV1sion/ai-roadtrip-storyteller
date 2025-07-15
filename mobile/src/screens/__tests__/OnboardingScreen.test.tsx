import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { NavigationContainer } from '@react-navigation/native';
import OnboardingScreen from '../OnboardingScreen';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Mock navigation
const mockNavigate = jest.fn();
jest.mock('@react-navigation/native', () => ({
  ...jest.requireActual('@react-navigation/native'),
  useNavigation: () => ({
    navigate: mockNavigate,
    replace: mockNavigate,
  }),
}));

// Mock AsyncStorage
jest.mock('@react-native-async-storage/async-storage');

describe('OnboardingScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const renderScreen = () => {
    return render(
      <NavigationContainer>
        <OnboardingScreen />
      </NavigationContainer>
    );
  };

  it('renders welcome message', () => {
    const { getByText } = renderScreen();
    
    expect(getByText(/Welcome to AI Road Trip/i)).toBeTruthy();
  });

  it('shows all onboarding slides', () => {
    const { getByText } = renderScreen();
    
    // First slide
    expect(getByText(/Personalized Stories/i)).toBeTruthy();
    
    // Navigate to next slide
    const nextButton = getByText('Next');
    fireEvent.press(nextButton);
    
    // Second slide
    expect(getByText(/Smart Bookings/i)).toBeTruthy();
    
    // Navigate to next slide
    fireEvent.press(nextButton);
    
    // Third slide
    expect(getByText(/Voice Control/i)).toBeTruthy();
  });

  it('allows skipping onboarding', async () => {
    const { getByText } = renderScreen();
    
    const skipButton = getByText('Skip');
    fireEvent.press(skipButton);
    
    await waitFor(() => {
      expect(AsyncStorage.setItem).toHaveBeenCalledWith('hasSeenOnboarding', 'true');
      expect(mockNavigate).toHaveBeenCalledWith('Main');
    });
  });

  it('completes onboarding flow', async () => {
    const { getByText } = renderScreen();
    
    // Navigate through all slides
    const nextButton = getByText('Next');
    fireEvent.press(nextButton); // Slide 2
    fireEvent.press(nextButton); // Slide 3
    
    // Complete onboarding
    const getStartedButton = getByText('Get Started');
    fireEvent.press(getStartedButton);
    
    await waitFor(() => {
      expect(AsyncStorage.setItem).toHaveBeenCalledWith('hasSeenOnboarding', 'true');
      expect(mockNavigate).toHaveBeenCalledWith('Main');
    });
  });

  it('tracks current slide indicator', () => {
    const { getAllByTestId, getByText } = renderScreen();
    
    // Check initial state
    let indicators = getAllByTestId('slide-indicator');
    expect(indicators[0].props.style).toMatchObject({ opacity: 1 });
    expect(indicators[1].props.style).toMatchObject({ opacity: 0.3 });
    
    // Move to next slide
    fireEvent.press(getByText('Next'));
    
    // Check updated state
    indicators = getAllByTestId('slide-indicator');
    expect(indicators[0].props.style).toMatchObject({ opacity: 0.3 });
    expect(indicators[1].props.style).toMatchObject({ opacity: 1 });
  });

  it('disables back navigation on first slide', () => {
    const { queryByTestId } = renderScreen();
    
    const backButton = queryByTestId('back-button');
    expect(backButton).toBeFalsy();
  });

  it('enables back navigation on subsequent slides', () => {
    const { getByText, getByTestId } = renderScreen();
    
    // Navigate to second slide
    fireEvent.press(getByText('Next'));
    
    // Back button should be visible
    const backButton = getByTestId('back-button');
    expect(backButton).toBeTruthy();
    
    // Navigate back
    fireEvent.press(backButton);
    
    // Should be on first slide again
    expect(getByText(/Personalized Stories/i)).toBeTruthy();
  });

  it('handles permission requests', async () => {
    const { getByText } = renderScreen();
    
    // Navigate to permissions slide
    fireEvent.press(getByText('Next'));
    fireEvent.press(getByText('Next'));
    
    // Mock permission responses
    jest.spyOn(require('expo-location'), 'requestForegroundPermissionsAsync')
      .mockResolvedValueOnce({ status: 'granted' });
    
    const enableLocationButton = getByText('Enable Location');
    fireEvent.press(enableLocationButton);
    
    await waitFor(() => {
      expect(require('expo-location').requestForegroundPermissionsAsync).toHaveBeenCalled();
    });
  });

  it('handles swipe gestures', () => {
    const { getByTestId, getByText } = renderScreen();
    
    const scrollView = getByTestId('onboarding-scroll');
    
    // Simulate swipe to next slide
    fireEvent.scroll(scrollView, {
      nativeEvent: {
        contentOffset: { x: 375, y: 0 }, // Assuming screen width of 375
        layoutMeasurement: { width: 375 },
      },
    });
    
    // Should show second slide
    expect(getByText(/Smart Bookings/i)).toBeTruthy();
  });
});