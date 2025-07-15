import AsyncStorage from '@react-native-async-storage/async-storage';
import { SPOTIFY_CLIENT_ID, SPOTIFY_REDIRECT_URI } from '@/config';
import { APIClient } from '@utils/apiUtils';

interface SpotifyTokens {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
}

class SpotifyService {
  private readonly apiClient: APIClient;
  private tokenExpirationTime: number = 0;

  constructor() {
    this.apiClient = new APIClient({
      baseURL: 'https://api.spotify.com/v1',
      timeout: 10000,
      rateLimit: {
        maxRequests: 100,
        windowMs: 30000, // 30 seconds
        retryAfterHeader: 'Retry-After',
      },
      retry: {
        maxAttempts: 3,
        baseDelay: 1000,
        maxDelay: 10000,
        retryableStatuses: [408, 429, 500, 502, 503, 504],
      },
    });
  }

  async initialize(): Promise<void> {
    const tokens = await this.loadTokens();
    if (tokens) {
      this.setTokens(tokens);
    }
  }

  private async loadTokens(): Promise<SpotifyTokens | null> {
    try {
      const tokensJson = await AsyncStorage.getItem('spotify_tokens');
      return tokensJson ? JSON.parse(tokensJson) : null;
    } catch (error) {
      console.error('Failed to load Spotify tokens:', error);
      return null;
    }
  }

  private async saveTokens(tokens: SpotifyTokens): Promise<void> {
    try {
      await AsyncStorage.setItem('spotify_tokens', JSON.stringify(tokens));
    } catch (error) {
      console.error('Failed to save Spotify tokens:', error);
    }
  }

  private setTokens(tokens: SpotifyTokens): void {
    this.apiClient.setAuthorizationHeader(`Bearer ${tokens.accessToken}`);
    this.tokenExpirationTime = Date.now() + tokens.expiresIn * 1000;
  }

  async isAuthenticated(): Promise<boolean> {
    try {
      const tokens = await this.loadTokens();
      return !!tokens && !!tokens.accessToken;
    } catch (error) {
      console.error('Error checking authentication:', error);
      return false;
    }
  }

  async exchangeCodeForToken(code: string): Promise<void> {
    try {
      const authClient = new APIClient({
        baseURL: 'https://accounts.spotify.com/api',
        timeout: 10000,
      });

      const params = new URLSearchParams();
      params.append('grant_type', 'authorization_code');
      params.append('code', code);
      params.append('redirect_uri', SPOTIFY_REDIRECT_URI);
      params.append('client_id', SPOTIFY_CLIENT_ID);

      const response = await authClient.post<SpotifyTokens>('/token', params.toString(), {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      await this.saveTokens(response);
      this.setTokens(response);
    } catch (error) {
      console.error('Error exchanging code for token:', error);
      throw new Error('Failed to exchange authorization code for token');
    }
  }

  getAuthConfig() {
    return {
      clientId: SPOTIFY_CLIENT_ID,
      redirectUri: SPOTIFY_REDIRECT_URI,
      scopes: [
        'user-read-private',
        'user-read-email',
        'user-modify-playback-state',
        'user-read-playback-state',
        'playlist-modify-private',
        'playlist-read-private',
      ],
    };
  }

  async refreshTokensIfNeeded(): Promise<void> {
    if (Date.now() >= this.tokenExpirationTime - 300000) { // Refresh 5 minutes before expiry
      const tokens = await this.loadTokens();
      if (tokens?.refreshToken) {
        const authClient = new APIClient({
          baseURL: 'https://accounts.spotify.com/api',
          timeout: 10000,
        });

        const response = await authClient.post<SpotifyTokens>('/token', {
          grant_type: 'refresh_token',
          refresh_token: tokens.refreshToken,
          client_id: SPOTIFY_CLIENT_ID,
        }, {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        });

        await this.saveTokens(response);
        this.setTokens(response);
      }
    }
  }

  async createTripPlaylist(
    tripName: string,
    duration: number,
    genres: string[] = []
  ): Promise<string> {
    await this.refreshTokensIfNeeded();

    interface CreatePlaylistResponse {
      id: string;
      external_urls: {
        spotify: string;
      };
    }

    // Create a new playlist
    const playlist = await this.apiClient.post<CreatePlaylistResponse>('/me/playlists', {
      name: `Road Trip: ${tripName}`,
      description: 'Auto-generated road trip playlist',
      public: false,
    });

    // Get recommendations based on genres
    interface RecommendationsResponse {
      tracks: Array<{
        id: string;
        duration_ms: number;
      }>;
    }

    const recommendations = await this.apiClient.get<RecommendationsResponse>('/recommendations', {
      params: {
        seed_genres: genres.join(','),
        limit: Math.ceil((duration * 60 * 1000) / 180000), // Average song length of 3 minutes
        min_popularity: 50,
      },
    });

    // Add tracks to playlist
    if (recommendations.tracks.length > 0) {
      await this.apiClient.post(`/playlists/${playlist.id}/tracks`, {
        uris: recommendations.tracks.map((track) => `spotify:track:${track.id}`),
      });
    }

    return playlist.external_urls.spotify;
  }

  async updatePlaylistMood(
    playlistId: string,
    mood: 'energetic' | 'calm' | 'focused'
  ): Promise<void> {
    await this.refreshTokensIfNeeded();

    interface PlaylistTracksResponse {
      items: Array<{
        track: {
          id: string;
        };
      }>;
    }

    // Get current tracks
    const currentTracks = await this.apiClient.get<PlaylistTracksResponse>(
      `/playlists/${playlistId}/tracks`
    );

    // Get audio features for all tracks
    interface AudioFeaturesResponse {
      audio_features: Array<{
        energy: number;
        valence: number;
        tempo: number;
      }>;
    }

    const audioFeatures = await this.apiClient.get<AudioFeaturesResponse>('/audio-features', {
      params: {
        ids: currentTracks.items.map((item) => item.track.id).join(','),
      },
    });

    // Calculate average features
    const avgFeatures = audioFeatures.audio_features.reduce(
      (acc, feat) => ({
        energy: acc.energy + feat.energy / audioFeatures.audio_features.length,
        valence: acc.valence + feat.valence / audioFeatures.audio_features.length,
        tempo: acc.tempo + feat.tempo / audioFeatures.audio_features.length,
      }),
      { energy: 0, valence: 0, tempo: 0 }
    );

    // Get recommendations based on mood
    const moodParams = {
      energetic: { min_energy: 0.7, min_tempo: avgFeatures.tempo },
      calm: { max_energy: 0.4, max_tempo: avgFeatures.tempo },
      focused: { target_energy: 0.5, target_valence: 0.5 },
    }[mood];

    interface RecommendationsResponse {
      tracks: Array<{
        id: string;
        uri: string;
      }>;
    }

    const recommendations = await this.apiClient.get<RecommendationsResponse>('/recommendations', {
      params: {
        seed_tracks: currentTracks.items
          .slice(0, 5)
          .map((item) => item.track.id)
          .join(','),
        ...moodParams,
        limit: currentTracks.items.length,
      },
    });

    // Replace tracks in playlist
    await this.apiClient.put(`/playlists/${playlistId}/tracks`, {
      uris: recommendations.tracks.map((track) => track.uri),
    });
  }

  async getCurrentPlayback(): Promise<SpotifyApi.CurrentPlaybackResponse | null> {
    await this.refreshTokensIfNeeded();
    return this.apiClient.get('/me/player');
  }

  async togglePlayPause(): Promise<void> {
    await this.refreshTokensIfNeeded();
    const playback = await this.getCurrentPlayback();
    
    if (playback?.is_playing) {
      await this.apiClient.put('/me/player/pause');
    } else {
      await this.apiClient.put('/me/player/play');
    }
  }

  async skipToNext(): Promise<void> {
    await this.refreshTokensIfNeeded();
    await this.apiClient.post('/me/player/next');
  }

  async skipToPrevious(): Promise<void> {
    await this.refreshTokensIfNeeded();
    await this.apiClient.post('/me/player/previous');
  }
}

export default new SpotifyService(); 