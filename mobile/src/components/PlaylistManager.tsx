import React, { useState, useEffect } from 'react';
import { logger } from '@/services/logger';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { apiManager } from '../services/api/apiManager';
import { Card } from './Card';
import { Button } from './Button';

interface Track {
  id: string;
  title: string;
  artist: string;
  duration: number;
  uri: string;
  energy?: number;
  valence?: number;
}

interface Playlist {
  id: string;
  name: string;
  description?: string;
  tracks: Track[];
  duration_minutes: number;
  collaborative?: boolean;
}

interface PlaylistManagerProps {
  routePoints?: any[];
  journeyDuration?: number;
  onPlaylistCreated?: (playlist: Playlist) => void;
}

export const PlaylistManager: React.FC<PlaylistManagerProps> = ({
  routePoints = [],
  journeyDuration = 120,
  onPlaylistCreated,
}) => {
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [selectedMood, setSelectedMood] = useState('balanced');
  const [expandedPlaylist, setExpandedPlaylist] = useState<string | null>(null);

  const moods = [
    { id: 'energetic', label: 'Energetic', icon: 'flash', color: '#FF6B6B' },
    { id: 'relaxed', label: 'Relaxed', icon: 'water', color: '#4ECDC4' },
    { id: 'happy', label: 'Happy', icon: 'sunny', color: '#FFD93D' },
    { id: 'focused', label: 'Focused', icon: 'eye', color: '#6C63FF' },
    { id: 'balanced', label: 'Balanced', icon: 'scale', color: '#95A5A6' },
  ];

  useEffect(() => {
    loadPlaylists();
  }, []);

  const loadPlaylists = async () => {
    try {
      setIsRefreshing(true);
      // Load existing journey playlists
      // This would fetch user's journey playlists from the backend
      setPlaylists([]);
    } catch (error) {
      logger.error('Failed to load playlists:', error);
    } finally {
      setIsRefreshing(false);
    }
  };

  const createJourneyPlaylist = async () => {
    try {
      setIsLoading(true);
      
      const locations = routePoints
        .filter(p => p.name)
        .map(p => p.name)
        .slice(0, 5);

      const response = await apiManager.post('/spotify/playlist/journey', {
        journey_name: locations.length > 0 
          ? `${locations[0]} to ${locations[locations.length - 1]}`
          : 'Road Trip Adventure',
        duration_minutes: journeyDuration,
        mood: selectedMood,
        locations: locations,
      });

      const newPlaylist: Playlist = {
        id: response.data.playlist_id,
        name: response.data.playlist_name,
        description: response.data.description,
        tracks: [],
        duration_minutes: response.data.duration_minutes,
        collaborative: response.data.collaborative,
      };

      setPlaylists([newPlaylist, ...playlists]);
      
      if (onPlaylistCreated) {
        onPlaylistCreated(newPlaylist);
      }
    } catch (error) {
      logger.error('Failed to create playlist:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const createLocationPlaylist = async (location: string) => {
    try {
      setIsLoading(true);
      
      const response = await apiManager.get('/spotify/music/location', {
        params: {
          location: location,
          limit: 20,
        },
      });

      const tracks = response.data.tracks.map((track: any) => ({
        id: track.id,
        title: track.name,
        artist: track.artist,
        duration: track.duration_seconds,
        uri: track.uri,
      }));

      const locationPlaylist: Playlist = {
        id: `location-${Date.now()}`,
        name: `${location} Vibes`,
        description: `Music inspired by ${location}`,
        tracks: tracks,
        duration_minutes: Math.round(
          tracks.reduce((sum: number, t: Track) => sum + t.duration, 0) / 60
        ),
      };

      setPlaylists([locationPlaylist, ...playlists]);
    } catch (error) {
      logger.error('Failed to create location playlist:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const renderMoodSelector = () => (
    <View style={styles.moodContainer}>
      <Text style={styles.sectionTitle}>Journey Mood</Text>
      <FlatList
        horizontal
        showsHorizontalScrollIndicator={false}
        data={moods}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={[
              styles.moodButton,
              selectedMood === item.id && styles.moodButtonSelected,
              { borderColor: item.color },
            ]}
            onPress={() => setSelectedMood(item.id)}
          >
            <Ionicons
              name={item.icon as any}
              size={24}
              color={selectedMood === item.id ? 'white' : item.color}
            />
            <Text
              style={[
                styles.moodLabel,
                selectedMood === item.id && styles.moodLabelSelected,
              ]}
            >
              {item.label}
            </Text>
          </TouchableOpacity>
        )}
      />
    </View>
  );

  const renderTrack = ({ item }: { item: Track }) => (
    <View style={styles.trackItem}>
      <View style={styles.trackInfo}>
        <Text style={styles.trackTitle} numberOfLines={1}>
          {item.title}
        </Text>
        <Text style={styles.trackArtist} numberOfLines={1}>
          {item.artist}
        </Text>
      </View>
      <Text style={styles.trackDuration}>
        {Math.floor(item.duration / 60)}:{(item.duration % 60).toString().padStart(2, '0')}
      </Text>
    </View>
  );

  const renderPlaylist = ({ item }: { item: Playlist }) => {
    const isExpanded = expandedPlaylist === item.id;

    return (
      <Card style={styles.playlistCard}>
        <TouchableOpacity
          onPress={() => setExpandedPlaylist(isExpanded ? null : item.id)}
          style={styles.playlistHeader}
        >
          <View style={styles.playlistInfo}>
            <Text style={styles.playlistName}>{item.name}</Text>
            {item.description && (
              <Text style={styles.playlistDescription} numberOfLines={1}>
                {item.description}
              </Text>
            )}
            <View style={styles.playlistMeta}>
              <Ionicons name="time-outline" size={14} color="#666" />
              <Text style={styles.playlistDuration}>
                {item.duration_minutes} min
              </Text>
              {item.collaborative && (
                <>
                  <Ionicons name="people-outline" size={14} color="#666" />
                  <Text style={styles.playlistCollaborative}>Collaborative</Text>
                </>
              )}
            </View>
          </View>
          <Ionicons
            name={isExpanded ? 'chevron-up' : 'chevron-down'}
            size={20}
            color="#666"
          />
        </TouchableOpacity>

        {isExpanded && item.tracks.length > 0 && (
          <View style={styles.trackList}>
            <FlatList
              data={item.tracks.slice(0, 5)}
              keyExtractor={(track) => track.id}
              renderItem={renderTrack}
              ItemSeparatorComponent={() => <View style={styles.trackSeparator} />}
            />
            {item.tracks.length > 5 && (
              <Text style={styles.moreTracksText}>
                +{item.tracks.length - 5} more tracks
              </Text>
            )}
          </View>
        )}

        <View style={styles.playlistActions}>
          <TouchableOpacity style={styles.actionButton}>
            <Ionicons name="play-circle" size={24} color="#1DB954" />
            <Text style={styles.actionText}>Play</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.actionButton}>
            <Ionicons name="shuffle" size={24} color="#666" />
            <Text style={styles.actionText}>Shuffle</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.actionButton}>
            <Ionicons name="share-outline" size={24} color="#666" />
            <Text style={styles.actionText}>Share</Text>
          </TouchableOpacity>
        </View>
      </Card>
    );
  };

  const renderLocationSuggestions = () => {
    if (!routePoints || routePoints.length === 0) return null;

    return (
      <View style={styles.locationSection}>
        <Text style={styles.sectionTitle}>Location Playlists</Text>
        <FlatList
          horizontal
          showsHorizontalScrollIndicator={false}
          data={routePoints.filter(p => p.name).slice(0, 5)}
          keyExtractor={(item, index) => `location-${index}`}
          renderItem={({ item }) => (
            <TouchableOpacity
              style={styles.locationCard}
              onPress={() => createLocationPlaylist(item.name)}
            >
              <Ionicons name="location" size={20} color="#1DB954" />
              <Text style={styles.locationName} numberOfLines={1}>
                {item.name}
              </Text>
              <Text style={styles.locationAction}>Create Playlist</Text>
            </TouchableOpacity>
          )}
        />
      </View>
    );
  };

  return (
    <View style={styles.container}>
      {renderMoodSelector()}
      
      <Button
        title="Create Journey Playlist"
        onPress={createJourneyPlaylist}
        disabled={isLoading}
        style={styles.createButton}
        icon={
          isLoading ? (
            <ActivityIndicator size="small" color="white" />
          ) : (
            <Ionicons name="add-circle-outline" size={20} color="white" />
          )
        }
      />

      {renderLocationSuggestions()}

      <Text style={styles.sectionTitle}>Your Playlists</Text>
      
      <FlatList
        testID="playlist-list"
        data={playlists}
        keyExtractor={(item) => item.id}
        renderItem={renderPlaylist}
        refreshControl={
          <RefreshControl refreshing={isRefreshing} onRefresh={loadPlaylists} />
        }
        ListEmptyComponent={
          <Card style={styles.emptyState}>
            <Ionicons name="musical-notes-outline" size={48} color="#999" />
            <Text style={styles.emptyText}>No playlists yet</Text>
            <Text style={styles.emptySubtext}>
              Create your first journey playlist above
            </Text>
          </Card>
        }
        contentContainerStyle={styles.listContent}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  moodContainer: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 12,
    paddingHorizontal: 16,
  },
  moodButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 2,
    marginHorizontal: 8,
  },
  moodButtonSelected: {
    backgroundColor: '#1DB954',
    borderColor: '#1DB954',
  },
  moodLabel: {
    marginLeft: 8,
    fontSize: 14,
    fontWeight: '600',
    color: '#666',
  },
  moodLabelSelected: {
    color: 'white',
  },
  createButton: {
    marginHorizontal: 16,
    marginBottom: 20,
    backgroundColor: '#1DB954',
  },
  locationSection: {
    marginBottom: 20,
  },
  locationCard: {
    backgroundColor: '#F0F9F4',
    padding: 12,
    borderRadius: 12,
    marginHorizontal: 8,
    alignItems: 'center',
    minWidth: 120,
  },
  locationName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginTop: 4,
    marginBottom: 8,
  },
  locationAction: {
    fontSize: 12,
    color: '#1DB954',
    fontWeight: '600',
  },
  listContent: {
    paddingHorizontal: 16,
    paddingBottom: 100,
  },
  playlistCard: {
    marginBottom: 16,
  },
  playlistHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  playlistInfo: {
    flex: 1,
  },
  playlistName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  playlistDescription: {
    fontSize: 14,
    color: '#666',
    marginTop: 2,
  },
  playlistMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 6,
  },
  playlistDuration: {
    fontSize: 12,
    color: '#666',
    marginLeft: 4,
    marginRight: 12,
  },
  playlistCollaborative: {
    fontSize: 12,
    color: '#666',
    marginLeft: 4,
  },
  trackList: {
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0',
    paddingTop: 12,
    marginBottom: 12,
  },
  trackItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
  },
  trackInfo: {
    flex: 1,
  },
  trackTitle: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
  },
  trackArtist: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  trackDuration: {
    fontSize: 12,
    color: '#999',
  },
  trackSeparator: {
    height: 1,
    backgroundColor: '#F0F0F0',
  },
  moreTracksText: {
    fontSize: 12,
    color: '#666',
    fontStyle: 'italic',
    marginTop: 8,
    textAlign: 'center',
  },
  playlistActions: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0',
    paddingTop: 12,
  },
  actionButton: {
    alignItems: 'center',
  },
  actionText: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  emptyState: {
    alignItems: 'center',
    padding: 40,
  },
  emptyText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#666',
    marginTop: 16,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#999',
    marginTop: 8,
    textAlign: 'center',
  },
});