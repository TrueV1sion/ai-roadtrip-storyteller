import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { MusicPlayerInterface } from '../MusicPlayerInterface';
import { apiManager } from '../../services/api/apiManager';

// Mock dependencies
jest.mock('../../services/api/apiManager');
jest.mock('@react-native-community/slider', () => 'Slider');

const mockGet = apiManager.get as jest.MockedFunction<typeof apiManager.get>;
const mockPost = apiManager.post as jest.MockedFunction<typeof apiManager.post>;

describe('MusicPlayerInterface', () => {
  const mockOnToggleExpand = jest.fn();

  const defaultProps = {
    isExpanded: false,
    onToggleExpand: mockOnToggleExpand,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('renders empty state when no track is playing', async () => {
    mockGet.mockResolvedValue({
      data: { is_playing: false, track: null }
    });

    const { getByText } = render(<MusicPlayerInterface {...defaultProps} />);

    await waitFor(() => {
      expect(getByText('No music playing')).toBeTruthy();
      expect(getByText('Browse Music')).toBeTruthy();
    });
  });

  it('renders compact player with track info', async () => {
    const mockTrack = {
      is_playing: true,
      track: {
        name: 'Test Song',
        artist: 'Test Artist',
        album: 'Test Album',
      },
      duration_ms: 180000,
      progress_ms: 60000,
    };

    mockGet.mockResolvedValue({ data: mockTrack });

    const { getByText, getByTestId } = render(
      <MusicPlayerInterface {...defaultProps} />
    );

    await waitFor(() => {
      expect(getByText('Test Song')).toBeTruthy();
      expect(getByText('Test Artist')).toBeTruthy();
      expect(getByTestId('play-pause-button')).toBeTruthy();
      expect(getByTestId('next-button')).toBeTruthy();
    });
  });

  it('handles play/pause toggle', async () => {
    const mockTrack = {
      is_playing: true,
      track: {
        name: 'Test Song',
        artist: 'Test Artist',
        album: 'Test Album',
      },
      duration_ms: 180000,
      progress_ms: 60000,
    };

    mockGet.mockResolvedValue({ data: mockTrack });
    mockPost.mockResolvedValue({ data: { success: true } });

    const { getByTestId } = render(<MusicPlayerInterface {...defaultProps} />);

    await waitFor(() => {
      expect(getByTestId('play-pause-button')).toBeTruthy();
    });

    const playPauseButton = getByTestId('play-pause-button');
    fireEvent.press(playPauseButton);

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/spotify/playback/control/pause');
    });
  });

  it('handles next track', async () => {
    const mockTrack = {
      is_playing: true,
      track: {
        name: 'Test Song',
        artist: 'Test Artist',
        album: 'Test Album',
      },
      duration_ms: 180000,
      progress_ms: 60000,
    };

    mockGet.mockResolvedValue({ data: mockTrack });
    mockPost.mockResolvedValue({ data: { success: true } });

    const { getByTestId } = render(<MusicPlayerInterface {...defaultProps} />);

    await waitFor(() => {
      expect(getByTestId('next-button')).toBeTruthy();
    });

    const nextButton = getByTestId('next-button');
    fireEvent.press(nextButton);

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/spotify/playback/control/next');
    });

    // Check that it refreshes playback state after 1 second
    jest.advanceTimersByTime(1000);
    expect(mockGet).toHaveBeenCalledWith('/spotify/playback/current');
  });

  it('expands to show full player', async () => {
    const mockTrack = {
      is_playing: true,
      track: {
        name: 'Test Song',
        artist: 'Test Artist',
        album: 'Test Album',
      },
      duration_ms: 180000,
      progress_ms: 60000,
    };

    mockGet.mockResolvedValue({ data: mockTrack });

    const { getByTestId, rerender } = render(
      <MusicPlayerInterface {...defaultProps} />
    );

    await waitFor(() => {
      expect(getByTestId('compact-player')).toBeTruthy();
    });

    // Simulate expansion
    rerender(<MusicPlayerInterface {...defaultProps} isExpanded={true} />);

    await waitFor(() => {
      expect(getByTestId('collapse-button')).toBeTruthy();
      expect(getByTestId('previous-button')).toBeTruthy();
      expect(getByTestId('volume-slider')).toBeTruthy();
      expect(getByTestId('progress-slider')).toBeTruthy();
    });
  });

  it('handles volume changes', async () => {
    const mockTrack = {
      is_playing: true,
      track: {
        name: 'Test Song',
        artist: 'Test Artist',
        album: 'Test Album',
      },
      duration_ms: 180000,
      progress_ms: 60000,
    };

    mockGet.mockResolvedValue({ data: mockTrack });
    mockPost.mockResolvedValue({ data: { success: true } });

    const { getByTestId } = render(
      <MusicPlayerInterface {...defaultProps} isExpanded={true} />
    );

    await waitFor(() => {
      expect(getByTestId('volume-slider')).toBeTruthy();
    });

    const volumeSlider = getByTestId('volume-slider');
    fireEvent(volumeSlider, 'onValueChange', 50);

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/spotify/playback/volume', {
        volume_percent: 50,
      });
    });
  });

  it('handles previous track in expanded view', async () => {
    const mockTrack = {
      is_playing: true,
      track: {
        name: 'Test Song',
        artist: 'Test Artist',
        album: 'Test Album',
      },
      duration_ms: 180000,
      progress_ms: 60000,
    };

    mockGet.mockResolvedValue({ data: mockTrack });
    mockPost.mockResolvedValue({ data: { success: true } });

    const { getByTestId } = render(
      <MusicPlayerInterface {...defaultProps} isExpanded={true} />
    );

    await waitFor(() => {
      expect(getByTestId('previous-button')).toBeTruthy();
    });

    const previousButton = getByTestId('previous-button');
    fireEvent.press(previousButton);

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/spotify/playback/control/previous');
    });
  });

  it('formats time correctly', async () => {
    const mockTrack = {
      is_playing: true,
      track: {
        name: 'Test Song',
        artist: 'Test Artist',
        album: 'Test Album',
      },
      duration_ms: 195000, // 3:15
      progress_ms: 65000,  // 1:05
    };

    mockGet.mockResolvedValue({ data: mockTrack });

    const { getByTestId } = render(
      <MusicPlayerInterface {...defaultProps} isExpanded={true} />
    );

    await waitFor(() => {
      expect(getByTestId('progress-time')).toBeTruthy();
      expect(getByTestId('progress-time').props.children).toBe('1:05');
    });
  });

  it('shows loading state during actions', async () => {
    const mockTrack = {
      is_playing: true,
      track: {
        name: 'Test Song',
        artist: 'Test Artist',
        album: 'Test Album',
      },
      duration_ms: 180000,
      progress_ms: 60000,
    };

    mockGet.mockResolvedValue({ data: mockTrack });
    mockPost.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 1000)));

    const { getByTestId } = render(<MusicPlayerInterface {...defaultProps} />);

    await waitFor(() => {
      expect(getByTestId('play-pause-button')).toBeTruthy();
    });

    const playPauseButton = getByTestId('play-pause-button');
    fireEvent.press(playPauseButton);

    // Should show loading indicator
    expect(getByTestId('loading-indicator')).toBeTruthy();
  });

  it('handles API errors gracefully', async () => {
    mockGet.mockRejectedValue(new Error('Network error'));

    const consoleError = jest.spyOn(console, 'error').mockImplementation();

    render(<MusicPlayerInterface {...defaultProps} />);

    await waitFor(() => {
      expect(consoleError).toHaveBeenCalledWith(
        'Failed to get playback state:',
        expect.any(Error)
      );
    });

    consoleError.mockRestore();
  });

  it('refreshes playback state periodically', async () => {
    const mockTrack = {
      is_playing: true,
      track: {
        name: 'Test Song',
        artist: 'Test Artist',
        album: 'Test Album',
      },
      duration_ms: 180000,
      progress_ms: 60000,
    };

    mockGet.mockResolvedValue({ data: mockTrack });

    render(<MusicPlayerInterface {...defaultProps} />);

    // Initial call
    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledTimes(1);
    });

    // Advance timer by 5 seconds
    jest.advanceTimersByTime(5000);

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledTimes(2);
    });

    // Advance timer by another 5 seconds
    jest.advanceTimersByTime(5000);

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledTimes(3);
    });
  });

  it('toggles between compact and expanded views', async () => {
    const mockTrack = {
      is_playing: true,
      track: {
        name: 'Test Song',
        artist: 'Test Artist',
        album: 'Test Album',
      },
      duration_ms: 180000,
      progress_ms: 60000,
    };

    mockGet.mockResolvedValue({ data: mockTrack });

    const { getByTestId } = render(<MusicPlayerInterface {...defaultProps} />);

    await waitFor(() => {
      expect(getByTestId('compact-player')).toBeTruthy();
    });

    // Click to expand
    fireEvent.press(getByTestId('compact-player'));
    expect(mockOnToggleExpand).toHaveBeenCalled();
  });
});