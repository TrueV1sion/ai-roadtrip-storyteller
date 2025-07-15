import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Animated,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import Slider from '@react-native-community/slider';

import { apiManager } from '../services/api/apiManager';
import { Card } from './Card';

interface Track {
  id: string;
  name: string;
  artist: string;
  album: string;
  duration_ms: number;
  uri: string;
}

interface MusicPlayerInterfaceProps {
  isExpanded?: boolean;
  onToggleExpand?: () => void;
}

export const MusicPlayerInterface: React.FC<MusicPlayerInterfaceProps> = ({
  isExpanded = false,
  onToggleExpand,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTrack, setCurrentTrack] = useState<Track | null>(null);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(70);
  const [isLoading, setIsLoading] = useState(false);
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    checkCurrentPlayback();
    const interval = setInterval(checkCurrentPlayback, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    Animated.timing(fadeAnim, {
      toValue: isExpanded ? 1 : 0,
      duration: 300,
      useNativeDriver: true,
    }).start();
  }, [isExpanded]);

  const checkCurrentPlayback = async () => {
    try {
      const response = await apiManager.get('/spotify/playback/current');
      const data = response.data;
      
      if (data.is_playing && data.track) {
        setIsPlaying(true);
        setCurrentTrack({
          id: data.track.name,
          name: data.track.name,
          artist: data.track.artist,
          album: data.track.album,
          duration_ms: data.duration_ms || 0,
          uri: '',
        });
        setProgress(data.progress_ms || 0);
        setDuration(data.duration_ms || 0);
      } else {
        setIsPlaying(false);
      }
    } catch (error) {
      console.error('Failed to get playback state:', error);
    }
  };

  const handlePlayPause = async () => {
    try {
      setIsLoading(true);
      const action = isPlaying ? 'pause' : 'play';
      await apiManager.post(`/spotify/playback/control/${action}`);
      setIsPlaying(!isPlaying);
    } catch (error) {
      console.error('Failed to control playback:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleNext = async () => {
    try {
      setIsLoading(true);
      await apiManager.post('/spotify/playback/control/next');
      setTimeout(checkCurrentPlayback, 1000);
    } catch (error) {
      console.error('Failed to skip track:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePrevious = async () => {
    try {
      setIsLoading(true);
      await apiManager.post('/spotify/playback/control/previous');
      setTimeout(checkCurrentPlayback, 1000);
    } catch (error) {
      console.error('Failed to go to previous track:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleVolumeChange = async (value: number) => {
    setVolume(value);
    try {
      await apiManager.post('/spotify/playback/volume', {
        volume_percent: Math.round(value),
      });
    } catch (error) {
      console.error('Failed to set volume:', error);
    }
  };

  const formatTime = (ms: number) => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  if (!currentTrack) {
    return (
      <Card style={styles.emptyContainer}>
        <Ionicons name="musical-notes-outline" size={32} color="#999" />
        <Text style={styles.emptyText}>No music playing</Text>
        <TouchableOpacity style={styles.browseButton}>
          <Text style={styles.browseButtonText}>Browse Music</Text>
        </TouchableOpacity>
      </Card>
    );
  }

  const renderCompactPlayer = () => (
    <TouchableOpacity testID="compact-player" onPress={onToggleExpand} activeOpacity={0.9}>
      <Card style={styles.compactContainer}>
        <View style={styles.compactLeft}>
          <Text style={styles.compactTrackName} numberOfLines={1}>
            {currentTrack.name}
          </Text>
          <Text style={styles.compactArtist} numberOfLines={1}>
            {currentTrack.artist}
          </Text>
        </View>
        <View style={styles.compactControls}>
          <TouchableOpacity
            testID="play-pause-button"
            onPress={handlePlayPause}
            disabled={isLoading}
            style={styles.compactButton}
          >
            {isLoading ? (
              <ActivityIndicator testID="loading-indicator" size="small" color="#1DB954" />
            ) : (
              <Ionicons
                testID="play-pause-icon"
                name={isPlaying ? 'pause' : 'play'}
                size={24}
                color="#333"
              />
            )}
          </TouchableOpacity>
          <TouchableOpacity
            testID="next-button"
            onPress={handleNext}
            disabled={isLoading}
            style={styles.compactButton}
          >
            <Ionicons name="play-skip-forward" size={20} color="#333" />
          </TouchableOpacity>
        </View>
      </Card>
    </TouchableOpacity>
  );

  const renderExpandedPlayer = () => (
    <Animated.View
      style={[
        styles.expandedContainer,
        {
          opacity: fadeAnim,
          transform: [
            {
              translateY: fadeAnim.interpolate({
                inputRange: [0, 1],
                outputRange: [50, 0],
              }),
            },
          ],
        },
      ]}
    >
      <Card style={styles.expandedCard}>
        <TouchableOpacity
          testID="collapse-button"
          onPress={onToggleExpand}
          style={styles.collapseButton}
        >
          <Ionicons name="chevron-down" size={24} color="#666" />
        </TouchableOpacity>

        <View style={styles.trackInfo}>
          <Text style={styles.trackName}>{currentTrack.name}</Text>
          <Text style={styles.artistName}>{currentTrack.artist}</Text>
          <Text style={styles.albumName}>{currentTrack.album}</Text>
        </View>

        <View style={styles.progressContainer}>
          <Text testID="progress-time" style={styles.timeText}>{formatTime(progress)}</Text>
          <Slider
            testID="progress-slider"
            style={styles.progressSlider}
            minimumValue={0}
            maximumValue={duration}
            value={progress}
            minimumTrackTintColor="#1DB954"
            maximumTrackTintColor="#E0E0E0"
            thumbTintColor="#1DB954"
            onSlidingComplete={(value) => {
              // Seek functionality would go here
              setProgress(value);
            }}
          />
          <Text style={styles.timeText}>{formatTime(duration)}</Text>
        </View>

        <View style={styles.controls}>
          <TouchableOpacity onPress={() => {}}>
            <Ionicons name="shuffle" size={24} color="#666" />
          </TouchableOpacity>

          <TouchableOpacity
            testID="previous-button"
            onPress={handlePrevious}
            disabled={isLoading}
            style={styles.controlButton}
          >
            <Ionicons name="play-skip-back" size={30} color="#333" />
          </TouchableOpacity>

          <TouchableOpacity
            onPress={handlePlayPause}
            disabled={isLoading}
            style={styles.playButton}
          >
            {isLoading ? (
              <ActivityIndicator size="large" color="#1DB954" />
            ) : (
              <Ionicons
                name={isPlaying ? 'pause' : 'play'}
                size={40}
                color="#1DB954"
              />
            )}
          </TouchableOpacity>

          <TouchableOpacity
            onPress={handleNext}
            disabled={isLoading}
            style={styles.controlButton}
          >
            <Ionicons name="play-skip-forward" size={30} color="#333" />
          </TouchableOpacity>

          <TouchableOpacity onPress={() => {}}>
            <Ionicons name="repeat" size={24} color="#666" />
          </TouchableOpacity>
        </View>

        <View style={styles.volumeContainer}>
          <Ionicons name="volume-low" size={20} color="#666" />
          <Slider
            testID="volume-slider"
            style={styles.volumeSlider}
            minimumValue={0}
            maximumValue={100}
            value={volume}
            minimumTrackTintColor="#1DB954"
            maximumTrackTintColor="#E0E0E0"
            thumbTintColor="#1DB954"
            onValueChange={handleVolumeChange}
          />
          <Ionicons name="volume-high" size={20} color="#666" />
        </View>

        <View style={styles.additionalControls}>
          <TouchableOpacity style={styles.additionalButton}>
            <Ionicons name="heart-outline" size={24} color="#666" />
          </TouchableOpacity>
          <TouchableOpacity style={styles.additionalButton}>
            <Ionicons name="list" size={24} color="#666" />
          </TouchableOpacity>
          <TouchableOpacity style={styles.additionalButton}>
            <Ionicons name="share-outline" size={24} color="#666" />
          </TouchableOpacity>
        </View>
      </Card>
    </Animated.View>
  );

  return isExpanded ? renderExpandedPlayer() : renderCompactPlayer();
};

const styles = StyleSheet.create({
  emptyContainer: {
    padding: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyText: {
    fontSize: 16,
    color: '#666',
    marginTop: 12,
    marginBottom: 16,
  },
  browseButton: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 20,
    backgroundColor: '#1DB954',
  },
  browseButtonText: {
    color: 'white',
    fontWeight: '600',
  },
  compactContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 12,
  },
  compactLeft: {
    flex: 1,
    marginRight: 12,
  },
  compactTrackName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  compactArtist: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  compactControls: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  compactButton: {
    padding: 8,
    marginLeft: 8,
  },
  expandedContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    padding: 20,
  },
  expandedCard: {
    padding: 24,
    backgroundColor: 'white',
    maxHeight: '90%',
  },
  collapseButton: {
    alignSelf: 'center',
    marginBottom: 20,
  },
  trackInfo: {
    alignItems: 'center',
    marginBottom: 30,
  },
  trackName: {
    fontSize: 22,
    fontWeight: '700',
    color: '#333',
    textAlign: 'center',
  },
  artistName: {
    fontSize: 18,
    color: '#666',
    marginTop: 8,
  },
  albumName: {
    fontSize: 14,
    color: '#999',
    marginTop: 4,
  },
  progressContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 30,
  },
  progressSlider: {
    flex: 1,
    height: 40,
    marginHorizontal: 10,
  },
  timeText: {
    fontSize: 12,
    color: '#666',
    minWidth: 40,
  },
  controls: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-around',
    marginBottom: 30,
  },
  controlButton: {
    padding: 10,
  },
  playButton: {
    width: 70,
    height: 70,
    borderRadius: 35,
    backgroundColor: '#F0F9F4',
    justifyContent: 'center',
    alignItems: 'center',
  },
  volumeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
  },
  volumeSlider: {
    flex: 1,
    height: 40,
    marginHorizontal: 10,
  },
  additionalControls: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingTop: 20,
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0',
  },
  additionalButton: {
    padding: 10,
  },
});