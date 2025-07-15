import React from 'react';
import { render, fireEvent, waitFor } from '@/utils/test-utils';
import { PlaylistManager } from '../PlaylistManager';
import { apiManager } from '@/services/api/apiManager';

// Mock dependencies
jest.mock('@/services/api/apiManager');
jest.mock('@expo/vector-icons', () => ({
  Ionicons: 'Icon',
}));

describe('PlaylistManager', () => {
  const mockApiManager = apiManager as jest.Mocked<typeof apiManager>;
  const mockOnPlaylistCreated = jest.fn();

  const mockRoutePoints = [
    { name: 'San Francisco' },
    { name: 'Los Angeles' },
    { name: 'San Diego' },
  ];

  const mockPlaylistResponse = {
    data: {
      playlist_id: 'test-playlist-id',
      playlist_name: 'Road Trip Adventure',
      description: 'Your journey playlist',
      duration_minutes: 120,
      collaborative: false,
    },
  };

  const mockLocationTracksResponse = {
    data: {
      tracks: [
        {
          id: 'track1',
          name: 'California Love',
          artist: '2Pac',
          duration_seconds: 240,
          uri: 'spotify:track:1',
        },
        {
          id: 'track2',
          name: 'Hotel California',
          artist: 'Eagles',
          duration_seconds: 390,
          uri: 'spotify:track:2',
        },
      ],
    },
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders mood selector', () => {
    const { getByText } = render(<PlaylistManager />);
    
    expect(getByText('Journey Mood')).toBeTruthy();
    expect(getByText('Energetic')).toBeTruthy();
    expect(getByText('Relaxed')).toBeTruthy();
    expect(getByText('Happy')).toBeTruthy();
    expect(getByText('Focused')).toBeTruthy();
    expect(getByText('Balanced')).toBeTruthy();
  });

  it('selects mood when mood button is pressed', async () => {
    const { getByText, getByTestId } = render(<PlaylistManager />);
    
    const energeticButton = getByText('Energetic').parent;
    fireEvent.press(energeticButton);
    
    await waitFor(() => {
      // Check if the button has selected styles
      expect(energeticButton.props.style).toContainEqual(
        expect.objectContaining({ backgroundColor: '#1DB954' })
      );
    });
  });

  it('creates journey playlist when button is pressed', async () => {
    mockApiManager.post.mockResolvedValue(mockPlaylistResponse);
    
    const { getByText } = render(
      <PlaylistManager
        routePoints={mockRoutePoints}
        journeyDuration={120}
        onPlaylistCreated={mockOnPlaylistCreated}
      />
    );
    
    const createButton = getByText('Create Journey Playlist');
    fireEvent.press(createButton);
    
    await waitFor(() => {
      expect(mockApiManager.post).toHaveBeenCalledWith('/spotify/playlist/journey', {
        journey_name: 'San Francisco to San Diego',
        duration_minutes: 120,
        mood: 'balanced',
        locations: ['San Francisco', 'Los Angeles', 'San Diego'],
      });
    });
    
    await waitFor(() => {
      expect(mockOnPlaylistCreated).toHaveBeenCalledWith(
        expect.objectContaining({
          id: 'test-playlist-id',
          name: 'Road Trip Adventure',
        })
      );
    });
  });

  it('disables create button while loading', async () => {
    let resolvePost: (value: any) => void;
    const postPromise = new Promise(resolve => {
      resolvePost = resolve;
    });
    
    mockApiManager.post.mockReturnValue(postPromise);
    
    const { getByText } = render(<PlaylistManager />);
    
    const createButton = getByText('Create Journey Playlist');
    fireEvent.press(createButton);
    
    // Button should be disabled
    expect(createButton.parent.props.disabled).toBe(true);
    
    // Resolve the promise
    resolvePost!(mockPlaylistResponse);
    
    await waitFor(() => {
      expect(createButton.parent.props.disabled).toBe(false);
    });
  });

  it('renders location playlist suggestions', () => {
    const { getByText } = render(
      <PlaylistManager routePoints={mockRoutePoints} />
    );
    
    expect(getByText('Location Playlists')).toBeTruthy();
    expect(getByText('San Francisco')).toBeTruthy();
    expect(getByText('Los Angeles')).toBeTruthy();
    expect(getByText('San Diego')).toBeTruthy();
  });

  it('creates location playlist when location is pressed', async () => {
    mockApiManager.get.mockResolvedValue(mockLocationTracksResponse);
    
    const { getByText, getAllByText } = render(
      <PlaylistManager routePoints={mockRoutePoints} />
    );
    
    const sanFranciscoButton = getByText('San Francisco').parent;
    fireEvent.press(sanFranciscoButton);
    
    await waitFor(() => {
      expect(mockApiManager.get).toHaveBeenCalledWith('/spotify/music/location', {
        params: {
          location: 'San Francisco',
          limit: 20,
        },
      });
    });
    
    // Should create a new playlist with the location name
    await waitFor(() => {
      expect(getByText('San Francisco Vibes')).toBeTruthy();
    });
  });

  it('expands playlist to show tracks', async () => {
    mockApiManager.get.mockResolvedValue(mockLocationTracksResponse);
    
    const { getByText } = render(
      <PlaylistManager routePoints={mockRoutePoints} />
    );
    
    // Create a location playlist first
    const sanFranciscoButton = getByText('San Francisco').parent;
    fireEvent.press(sanFranciscoButton);
    
    await waitFor(() => {
      expect(getByText('San Francisco Vibes')).toBeTruthy();
    });
    
    // Expand the playlist
    const playlistHeader = getByText('San Francisco Vibes').parent.parent;
    fireEvent.press(playlistHeader);
    
    await waitFor(() => {
      expect(getByText('California Love')).toBeTruthy();
      expect(getByText('2Pac')).toBeTruthy();
      expect(getByText('Hotel California')).toBeTruthy();
      expect(getByText('Eagles')).toBeTruthy();
    });
  });

  it('shows empty state when no playlists', () => {
    const { getByText } = render(<PlaylistManager />);
    
    expect(getByText('No playlists yet')).toBeTruthy();
    expect(getByText('Create your first journey playlist above')).toBeTruthy();
  });

  it('formats track duration correctly', async () => {
    mockApiManager.get.mockResolvedValue(mockLocationTracksResponse);
    
    const { getByText } = render(
      <PlaylistManager routePoints={mockRoutePoints} />
    );
    
    // Create and expand a playlist
    fireEvent.press(getByText('San Francisco').parent);
    
    await waitFor(() => {
      const playlistHeader = getByText('San Francisco Vibes').parent.parent;
      fireEvent.press(playlistHeader);
    });
    
    await waitFor(() => {
      expect(getByText('4:00')).toBeTruthy(); // 240 seconds
      expect(getByText('6:30')).toBeTruthy(); // 390 seconds
    });
  });

  it('shows playlist actions', async () => {
    mockApiManager.post.mockResolvedValue(mockPlaylistResponse);
    
    const { getByText, getAllByText } = render(<PlaylistManager />);
    
    // Create a playlist
    fireEvent.press(getByText('Create Journey Playlist'));
    
    await waitFor(() => {
      expect(getByText('Play')).toBeTruthy();
      expect(getByText('Shuffle')).toBeTruthy();
      expect(getByText('Share')).toBeTruthy();
    });
  });

  it('shows collaborative indicator', async () => {
    mockApiManager.post.mockResolvedValue({
      data: {
        ...mockPlaylistResponse.data,
        collaborative: true,
      },
    });
    
    const { getByText } = render(<PlaylistManager />);
    
    fireEvent.press(getByText('Create Journey Playlist'));
    
    await waitFor(() => {
      expect(getByText('Collaborative')).toBeTruthy();
    });
  });

  it('handles API errors gracefully', async () => {
    mockApiManager.post.mockRejectedValue(new Error('Network error'));
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
    
    const { getByText } = render(<PlaylistManager />);
    
    fireEvent.press(getByText('Create Journey Playlist'));
    
    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith(
        'Failed to create playlist:',
        expect.any(Error)
      );
    });
    
    consoleSpy.mockRestore();
  });

  it('refreshes playlists when pulled down', async () => {
    const { getByTestId } = render(<PlaylistManager />);
    
    const flatList = getByTestId('playlist-list');
    const { onRefresh } = flatList.props.refreshControl.props;
    
    onRefresh();
    
    // Should trigger loadPlaylists
    await waitFor(() => {
      expect(flatList.props.refreshControl.props.refreshing).toBe(false);
    });
  });

  it('shows more tracks indicator when playlist has many tracks', async () => {
    const manyTracksResponse = {
      data: {
        tracks: Array(10).fill(null).map((_, i) => ({
          id: `track${i}`,
          name: `Track ${i}`,
          artist: `Artist ${i}`,
          duration_seconds: 180,
          uri: `spotify:track:${i}`,
        })),
      },
    };
    
    mockApiManager.get.mockResolvedValue(manyTracksResponse);
    
    const { getByText } = render(
      <PlaylistManager routePoints={mockRoutePoints} />
    );
    
    // Create and expand a playlist
    fireEvent.press(getByText('San Francisco').parent);
    
    await waitFor(() => {
      const playlistHeader = getByText('San Francisco Vibes').parent.parent;
      fireEvent.press(playlistHeader);
    });
    
    await waitFor(() => {
      expect(getByText('+5 more tracks')).toBeTruthy();
    });
  });
});