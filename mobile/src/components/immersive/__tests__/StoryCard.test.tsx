import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';

import StoryCard from '../StoryCard';

const Stack = createNativeStackNavigator();

const mockStory = {
  id: '1',
  title: 'The Legend of Half Dome',
  description: 'Discover the ancient Native American legends surrounding this iconic Yosemite landmark.',
  duration: 300,
  distance: 2.5,
  thumbnail: 'https://example.com/half-dome.jpg',
  themes: ['nature', 'history', 'culture'],
  rating: 4.8,
  plays: 1523,
};

const renderWithNavigation = (component: React.ReactElement) => {
  return render(
    <NavigationContainer>
      <Stack.Navigator>
        <Stack.Screen name="Home" component={() => component} />
        <Stack.Screen name="StoryDetails" component={() => null} />
      </Stack.Navigator>
    </NavigationContainer>
  );
};

describe('StoryCard Component', () => {
  it('renders story information correctly', () => {
    const { getByText } = renderWithNavigation(
      <StoryCard story={mockStory} onPress={jest.fn()} />
    );
    
    expect(getByText('The Legend of Half Dome')).toBeTruthy();
    expect(getByText('Discover the ancient Native American legends surrounding this iconic Yosemite landmark.')).toBeTruthy();
    expect(getByText('5 min')).toBeTruthy(); // 300 seconds
    expect(getByText('2.5 mi away')).toBeTruthy();
    expect(getByText('4.8')).toBeTruthy();
    expect(getByText('1.5K plays')).toBeTruthy();
  });

  it('calls onPress when tapped', () => {
    const onPress = jest.fn();
    const { getByTestId } = renderWithNavigation(
      <StoryCard story={mockStory} onPress={onPress} />
    );
    
    fireEvent.press(getByTestId('story-card'));
    expect(onPress).toHaveBeenCalledWith(mockStory);
  });

  it('displays story themes as chips', () => {
    const { getByText } = renderWithNavigation(
      <StoryCard story={mockStory} onPress={jest.fn()} />
    );
    
    expect(getByText('Nature')).toBeTruthy();
    expect(getByText('History')).toBeTruthy();
    expect(getByText('Culture')).toBeTruthy();
  });

  it('shows loading state for thumbnail', () => {
    const { getByTestId } = renderWithNavigation(
      <StoryCard story={{ ...mockStory, thumbnail: null }} onPress={jest.fn()} />
    );
    
    expect(getByTestId('thumbnail-placeholder')).toBeTruthy();
  });

  it('handles long press for preview', async () => {
    const onLongPress = jest.fn();
    const { getByTestId } = renderWithNavigation(
      <StoryCard 
        story={mockStory} 
        onPress={jest.fn()} 
        onLongPress={onLongPress}
      />
    );
    
    fireEvent.longPress(getByTestId('story-card'));
    
    await waitFor(() => {
      expect(onLongPress).toHaveBeenCalledWith(mockStory);
    });
  });

  it('shows "New" badge for recent stories', () => {
    const recentStory = {
      ...mockStory,
      createdAt: new Date().toISOString(),
    };
    
    const { getByText } = renderWithNavigation(
      <StoryCard story={recentStory} onPress={jest.fn()} />
    );
    
    expect(getByText('NEW')).toBeTruthy();
  });

  it('shows download indicator if available offline', () => {
    const offlineStory = {
      ...mockStory,
      isDownloaded: true,
    };
    
    const { getByTestId } = renderWithNavigation(
      <StoryCard story={offlineStory} onPress={jest.fn()} />
    );
    
    expect(getByTestId('download-indicator')).toBeTruthy();
  });

  it('formats large play counts correctly', () => {
    const popularStory = {
      ...mockStory,
      plays: 1234567,
    };
    
    const { getByText } = renderWithNavigation(
      <StoryCard story={popularStory} onPress={jest.fn()} />
    );
    
    expect(getByText('1.2M plays')).toBeTruthy();
  });

  it('shows premium badge for premium content', () => {
    const premiumStory = {
      ...mockStory,
      isPremium: true,
    };
    
    const { getByTestId } = renderWithNavigation(
      <StoryCard story={premiumStory} onPress={jest.fn()} />
    );
    
    expect(getByTestId('premium-badge')).toBeTruthy();
  });

  it('displays estimated listening time based on distance', () => {
    const nearbyStory = {
      ...mockStory,
      distance: 0.5,
      estimatedArrival: 2, // 2 minutes
    };
    
    const { getByText } = renderWithNavigation(
      <StoryCard story={nearbyStory} onPress={jest.fn()} />
    );
    
    expect(getByText('Arrives in 2 min')).toBeTruthy();
  });

  it('applies disabled style when story is unavailable', () => {
    const unavailableStory = {
      ...mockStory,
      isAvailable: false,
    };
    
    const { getByTestId } = renderWithNavigation(
      <StoryCard story={unavailableStory} onPress={jest.fn()} />
    );
    
    const card = getByTestId('story-card');
    expect(card.props.style).toMatchObject({ opacity: 0.5 });
  });
});