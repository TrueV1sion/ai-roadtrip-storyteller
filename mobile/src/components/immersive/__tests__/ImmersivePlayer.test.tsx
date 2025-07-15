import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';

import ImmersivePlayer from '../ImmersivePlayer';
import { ImmersiveService } from '../../../services/api/immersiveApi';

// Mock dependencies
jest.mock('../../../services/api/immersiveApi');
jest.mock('expo-av', () => ({
  Audio: {
    Sound: {
      createAsync: jest.fn(() => Promise.resolve({
        sound: {
          playAsync: jest.fn(),
          pauseAsync: jest.fn(),
          stopAsync: jest.fn(),
          unloadAsync: jest.fn(),
          setPositionAsync: jest.fn(),
          getStatusAsync: jest.fn(() => Promise.resolve({
            isPlaying: false,
            positionMillis: 0,
            durationMillis: 180000,
          })),
        },
      })),
    },
  },
}));

const mockStore = configureStore({
  reducer: {
    immersive: (state = { 
      currentStory: null,
      isPlaying: false,
      volume: 1.0,
    }) => state,
    location: (state = { current: { lat: 37.7749, lng: -122.4194 } }) => state,
  },
});

const mockStory = {
  id: '1',
  title: 'Golden Gate Bridge History',
  audioUrl: 'https://example.com/audio.mp3',
  duration: 180,
  location: { lat: 37.8199, lng: -122.4783 },
  themes: ['history', 'architecture'],
};

const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <Provider store={mockStore}>
      {component}
    </Provider>
  );
};

describe('ImmersivePlayer Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders player interface correctly', () => {
    const { getByText, getByTestId } = renderWithProviders(
      <ImmersivePlayer story={mockStory} />
    );
    
    expect(getByText('Golden Gate Bridge History')).toBeTruthy();
    expect(getByTestId('play-button')).toBeTruthy();
    expect(getByTestId('progress-bar')).toBeTruthy();
    expect(getByTestId('volume-slider')).toBeTruthy();
  });

  it('plays audio when play button pressed', async () => {
    const { getByTestId } = renderWithProviders(
      <ImmersivePlayer story={mockStory} />
    );
    
    const playButton = getByTestId('play-button');
    fireEvent.press(playButton);
    
    await waitFor(() => {
      expect(Audio.Sound.createAsync).toHaveBeenCalledWith(
        { uri: mockStory.audioUrl },
        { shouldPlay: true }
      );
    });
  });

  it('pauses audio when pause pressed', async () => {
    const { getByTestId } = renderWithProviders(
      <ImmersivePlayer story={mockStory} autoPlay={true} />
    );
    
    // Wait for auto play
    await waitFor(() => {
      expect(Audio.Sound.createAsync).toHaveBeenCalled();
    });
    
    const pauseButton = getByTestId('pause-button');
    fireEvent.press(pauseButton);
    
    const { sound } = await Audio.Sound.createAsync();
    expect(sound.pauseAsync).toHaveBeenCalled();
  });

  it('shows progress during playback', async () => {
    const { getByTestId } = renderWithProviders(
      <ImmersivePlayer story={mockStory} />
    );
    
    const progressBar = getByTestId('progress-bar');
    expect(progressBar.props.value).toBe(0);
    
    // Start playback
    fireEvent.press(getByTestId('play-button'));
    
    // Simulate progress update
    await waitFor(() => {
      const updatedProgress = getByTestId('progress-bar');
      expect(updatedProgress.props.max).toBe(180);
    });
  });

  it('allows seeking to position', async () => {
    const { getByTestId } = renderWithProviders(
      <ImmersivePlayer story={mockStory} />
    );
    
    fireEvent.press(getByTestId('play-button'));
    
    await waitFor(() => {
      expect(Audio.Sound.createAsync).toHaveBeenCalled();
    });
    
    const progressBar = getByTestId('progress-bar');
    fireEvent(progressBar, 'slidingComplete', 60);
    
    const { sound } = await Audio.Sound.createAsync();
    expect(sound.setPositionAsync).toHaveBeenCalledWith(60000);
  });

  it('adjusts volume with slider', async () => {
    const { getByTestId } = renderWithProviders(
      <ImmersivePlayer story={mockStory} />
    );
    
    const volumeSlider = getByTestId('volume-slider');
    fireEvent(volumeSlider, 'valueChange', 0.5);
    
    await waitFor(() => {
      const sound = mockStore.getState().immersive.sound;
      if (sound) {
        expect(sound.setVolumeAsync).toHaveBeenCalledWith(0.5);
      }
    });
  });

  it('shows loading state while fetching audio', () => {
    const { getByTestId } = renderWithProviders(
      <ImmersivePlayer story={{ ...mockStory, audioUrl: null }} />
    );
    
    expect(getByTestId('loading-indicator')).toBeTruthy();
  });

  it('handles playback errors gracefully', async () => {
    Audio.Sound.createAsync.mockRejectedValueOnce(new Error('Network error'));
    
    const { getByTestId, getByText } = renderWithProviders(
      <ImmersivePlayer story={mockStory} />
    );
    
    fireEvent.press(getByTestId('play-button'));
    
    await waitFor(() => {
      expect(getByText('Unable to play audio. Please try again.')).toBeTruthy();
    });
  });

  it('displays time remaining', () => {
    const { getByText } = renderWithProviders(
      <ImmersivePlayer story={mockStory} />
    );
    
    expect(getByText('3:00')).toBeTruthy(); // 180 seconds
  });

  it('cleans up audio on unmount', async () => {
    const { unmount } = renderWithProviders(
      <ImmersivePlayer story={mockStory} autoPlay={true} />
    );
    
    await waitFor(() => {
      expect(Audio.Sound.createAsync).toHaveBeenCalled();
    });
    
    const { sound } = await Audio.Sound.createAsync();
    
    unmount();
    
    expect(sound.unloadAsync).toHaveBeenCalled();
  });

  it('shows visual indicator for story themes', () => {
    const { getByText } = renderWithProviders(
      <ImmersivePlayer story={mockStory} />
    );
    
    expect(getByText('History')).toBeTruthy();
    expect(getByText('Architecture')).toBeTruthy();
  });
});