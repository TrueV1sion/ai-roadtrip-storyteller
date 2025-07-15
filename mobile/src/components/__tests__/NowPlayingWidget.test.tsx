import React from 'react';
import { fireEvent, waitFor } from '@testing-library/react-native';
import { render } from '../../__tests__/utils/test-utils';
import { NowPlayingWidget } from '../NowPlayingWidget';

// Mock the spotify service
jest.mock('../../services/spotifyService', () => ({
  spotifyService: {
    getCurrentTrack: jest.fn(() => Promise.resolve({
      name: 'Test Song',
      artist: 'Test Artist',
      album: 'Test Album',
      imageUrl: 'https://example.com/album.jpg',
      isPlaying: true,
      progress: 30000,
      duration: 180000,
    })),
    play: jest.fn(() => Promise.resolve()),
    pause: jest.fn(() => Promise.resolve()),
    next: jest.fn(() => Promise.resolve()),
    previous: jest.fn(() => Promise.resolve()),
  },
}));

const mockTrack = {
  name: 'Road Trip Anthem',
  artist: 'The Travelers',
  album: 'Highway Dreams',
  imageUrl: 'https://example.com/album-art.jpg',
  isPlaying: true,
  progress: 60000, // 1 minute
  duration: 240000, // 4 minutes
};

describe('NowPlayingWidget', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders correctly with track info', () => {
    const { getByText, getByTestId } = render(
      <NowPlayingWidget track={mockTrack} />
    );
    
    expect(getByText('Road Trip Anthem')).toBeTruthy();
    expect(getByText('The Travelers')).toBeTruthy();
    expect(getByTestId('album-artwork')).toBeTruthy();
  });

  it('shows placeholder when no track', () => {
    const { getByText } = render(<NowPlayingWidget track={null} />);
    
    expect(getByText('No music playing')).toBeTruthy();
    expect(getByText('Connect to Spotify to start listening')).toBeTruthy();
  });

  it('displays play button when paused', () => {
    const pausedTrack = { ...mockTrack, isPlaying: false };
    const { getByTestId } = render(<NowPlayingWidget track={pausedTrack} />);
    
    const playButton = getByTestId('play-pause-button');
    expect(playButton).toBeTruthy();
    expect(getByTestId('play-icon')).toBeTruthy();
  });

  it('displays pause button when playing', () => {
    const { getByTestId } = render(<NowPlayingWidget track={mockTrack} />);
    
    const pauseButton = getByTestId('play-pause-button');
    expect(pauseButton).toBeTruthy();
    expect(getByTestId('pause-icon')).toBeTruthy();
  });

  it('handles play/pause toggle', async () => {
    const onPlayPause = jest.fn();
    const { getByTestId } = render(
      <NowPlayingWidget track={mockTrack} onPlayPause={onPlayPause} />
    );
    
    const playPauseButton = getByTestId('play-pause-button');
    fireEvent.press(playPauseButton);
    
    await waitFor(() => {
      expect(onPlayPause).toHaveBeenCalled();
    });
  });

  it('handles skip to next track', async () => {
    const onNext = jest.fn();
    const { getByTestId } = render(
      <NowPlayingWidget track={mockTrack} onNext={onNext} />
    );
    
    const nextButton = getByTestId('next-button');
    fireEvent.press(nextButton);
    
    await waitFor(() => {
      expect(onNext).toHaveBeenCalled();
    });
  });

  it('handles skip to previous track', async () => {
    const onPrevious = jest.fn();
    const { getByTestId } = render(
      <NowPlayingWidget track={mockTrack} onPrevious={onPrevious} />
    );
    
    const previousButton = getByTestId('previous-button');
    fireEvent.press(previousButton);
    
    await waitFor(() => {
      expect(onPrevious).toHaveBeenCalled();
    });
  });

  it('displays progress bar correctly', () => {
    const { getByTestId } = render(<NowPlayingWidget track={mockTrack} />);
    
    const progressBar = getByTestId('progress-bar');
    const progressFill = getByTestId('progress-fill');
    
    expect(progressBar).toBeTruthy();
    // Progress is 60000/240000 = 25%
    expect(progressFill).toHaveStyle({ width: '25%' });
  });

  it('formats time correctly', () => {
    const { getByText } = render(<NowPlayingWidget track={mockTrack} />);
    
    // 60000ms = 1:00, 240000ms = 4:00
    expect(getByText('1:00')).toBeTruthy();
    expect(getByText('4:00')).toBeTruthy();
  });

  it('handles missing album artwork', () => {
    const trackWithoutArt = { ...mockTrack, imageUrl: null };
    const { getByTestId } = render(<NowPlayingWidget track={trackWithoutArt} />);
    
    const placeholder = getByTestId('album-placeholder');
    expect(placeholder).toBeTruthy();
  });

  it('truncates long song titles', () => {
    const longTitleTrack = { 
      ...mockTrack, 
      name: 'This Is An Extremely Long Song Title That Should Be Truncated' 
    };
    const { getByText } = render(<NowPlayingWidget track={longTitleTrack} />);
    
    const title = getByText(/This Is An Extremely Long/);
    expect(title.props.numberOfLines).toBe(1);
  });

  it('handles tap to expand', () => {
    const onExpand = jest.fn();
    const { getByTestId } = render(
      <NowPlayingWidget track={mockTrack} onExpand={onExpand} />
    );
    
    const container = getByTestId('now-playing-container');
    fireEvent.press(container);
    
    expect(onExpand).toHaveBeenCalled();
  });

  it('shows loading state during track change', () => {
    const { getByTestId, rerender } = render(
      <NowPlayingWidget track={mockTrack} isLoading />
    );
    
    expect(getByTestId('loading-overlay')).toBeTruthy();
    
    // Remove loading state
    rerender(<NowPlayingWidget track={mockTrack} isLoading={false} />);
    expect(() => getByTestId('loading-overlay')).toThrow();
  });

  it('is accessible', () => {
    const { getByTestId } = render(<NowPlayingWidget track={mockTrack} />);
    
    const container = getByTestId('now-playing-container');
    expect(container.props.accessible).toBe(true);
    expect(container.props.accessibilityLabel).toContain('Now playing: Road Trip Anthem by The Travelers');
    
    const playButton = getByTestId('play-pause-button');
    expect(playButton.props.accessibilityLabel).toBe('Pause');
  });

  it('handles swipe gestures', () => {
    const onNext = jest.fn();
    const onPrevious = jest.fn();
    const { getByTestId } = render(
      <NowPlayingWidget 
        track={mockTrack} 
        onNext={onNext} 
        onPrevious={onPrevious}
        enableGestures 
      />
    );
    
    const container = getByTestId('now-playing-container');
    
    // Simulate swipe left (next)
    fireEvent(container, 'swipeLeft');
    expect(onNext).toHaveBeenCalled();
    
    // Simulate swipe right (previous)
    fireEvent(container, 'swipeRight');
    expect(onPrevious).toHaveBeenCalled();
  });
});