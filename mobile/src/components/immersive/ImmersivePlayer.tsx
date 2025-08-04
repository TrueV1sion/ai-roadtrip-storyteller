import React, { useState, useEffect, useCallback, useRef } from 'react';
import { logger } from '@/services/logger';
import {
  View,
  StyleSheet,
  Animated,
  PanResponder,
  Image,
  TouchableOpacity,
} from 'react-native';
import {
  Text,
  Surface,
  IconButton,
  ProgressBar,
  Chip,
  Portal,
  Modal,
  Button,
  ActivityIndicator,
} from 'react-native-paper';
import { Audio } from 'expo-av';
import { BlurView } from 'expo-blur';
import { MaterialIcons } from '@expo/vector-icons';
import { Story, Media } from '../../types/story';
import { Track } from '../../types/audio';
import { useVoiceGuidance } from '../../hooks/useVoiceGuidance';
import { useUserPreferences } from '../../hooks/useUserPreferences';
import { COLORS, SPACING } from '../../theme';
import { InterestSelector } from './InterestSelector';
import { StoryCard } from './StoryCard';
import { MusicVisualizer } from './MusicVisualizer';
import OfflineManager from '../../services/OfflineManager';
import VoiceInteractionManager from '../../services/VoiceInteractionManager';
import ErrorHandler from '../../services/ErrorHandler';

interface ImmersivePlayerProps {
  currentLocation: Location;
  onClose: () => void;
}

interface AudioState {
  isPlaying: boolean;
  duration: number;
  position: number;
  isLoading: boolean;
}

export const ImmersivePlayer: React.FC<ImmersivePlayerProps> = ({
  currentLocation,
  onClose,
}) => {
  // Refs for audio players
  const storyPlayerRef = useRef<Audio.Sound>();
  const musicPlayerRef = useRef<Audio.Sound>();
  
  // Animation and gesture state
  const translateY = useRef(new Animated.Value(0)).current;
  const lastGesture = useRef(0);
  
  // Player state
  const [audioState, setAudioState] = useState<AudioState>({
    isPlaying: false,
    duration: 0,
    position: 0,
    isLoading: true,
  });
  const [currentStory, setCurrentStory] = useState<Story>();
  const [currentTrack, setCurrentTrack] = useState<Track>();
  const [showInterests, setShowInterests] = useState(false);
  const [upcomingStories, setUpcomingStories] = useState<Story[]>([]);
  const [relevanceScores, setRelevanceScores] = useState<Record<string, number>>({});
  const [isOffline, setIsOffline] = useState(false);
  const [isVoiceEnabled, setIsVoiceEnabled] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState<number | null>(null);
  
  const { speak, stop: stopSpeech } = useVoiceGuidance();
  const { preferences, updateInterests } = useUserPreferences();

  // Pan responder for swipe gestures
  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onPanResponderMove: (_, gesture) => {
        const newValue = lastGesture.current + gesture.dy;
        if (newValue >= 0 && newValue <= 300) {
          translateY.setValue(newValue);
        }
      },
      onPanResponderRelease: (_, gesture) => {
        if (gesture.dy > 100) {
          // Swipe down - minimize
          Animated.spring(translateY, {
            toValue: 300,
            useNativeDriver: true,
          }).start();
        } else if (gesture.dy < -100) {
          // Swipe up - maximize
          Animated.spring(translateY, {
            toValue: 0,
            useNativeDriver: true,
          }).start();
        } else {
          // Return to last position
          Animated.spring(translateY, {
            toValue: lastGesture.current,
            useNativeDriver: true,
          }).start();
        }
      },
    })
  ).current;

  // Initialize voice commands
  useEffect(() => {
    VoiceInteractionManager.registerDefaultCommands(
      togglePlayback,
      togglePlayback,
      () => {/* Handle next */},
      () => {/* Handle previous */},
      onClose
    );
  }, []);

  // Load initial content
  useEffect(() => {
    loadImmersiveContent();
    return () => {
      cleanup();
    };
  }, [currentLocation]);

  // Load content with offline support and error handling
  const loadImmersiveContent = async () => {
    try {
      setAudioState(prev => ({ ...prev, isLoading: true }));

      // Check offline availability first
      const offlineContent = await OfflineManager.getOfflineContent();
      if (!navigator.onLine && offlineContent) {
        setIsOffline(true);
        handleOfflineContent(offlineContent);
        return;
      }

      // Fetch online content
      const response = await fetch('/api/immersive', {
        method: 'POST',
        body: JSON.stringify({
          location: currentLocation,
          interests: preferences.interests,
          lastStories: upcomingStories.map(s => s.id),
        }),
      });
      
      if (!response.ok) {
        throw ErrorHandler.createApiError(
          'Failed to load content',
          response.status,
          '/api/immersive'
        );
      }

      const data = await response.json();
      setCurrentStory(data.currentStory);
      setCurrentTrack(data.currentTrack);
      setUpcomingStories(data.upcomingStories);
      setRelevanceScores(data.relevanceScores);

      // Download content for offline use
      downloadContentForOffline(data);

      // Initialize audio players
      await setupAudioPlayers(data.currentStory, data.currentTrack);
      
    } catch (error) {
      await ErrorHandler.handleError(error, {
        title: 'Content Loading Error',
        message: 'Unable to load immersive content.',
        retry: loadImmersiveContent,
        fallback: async () => {
          const offlineContent = await OfflineManager.getOfflineContent();
          if (offlineContent) {
            setIsOffline(true);
            handleOfflineContent(offlineContent);
          }
        },
      });
    } finally {
      setAudioState(prev => ({ ...prev, isLoading: false }));
    }
  };

  // Handle offline content
  const handleOfflineContent = (content: any) => {
    const { stories, tracks } = content;
    // Find nearest story based on location
    const nearestStory = findNearestStory(stories, currentLocation);
    setCurrentStory(nearestStory);
    setCurrentTrack(tracks[0]); // Use first available track
    setUpcomingStories(
      stories
        .filter(s => s.id !== nearestStory.id)
        .slice(0, 5)
    );
  };

  // Download content for offline use
  const downloadContentForOffline = async (data: any) => {
    try {
      await OfflineManager.downloadContent(
        [data.currentStory, ...data.upcomingStories],
        [data.currentTrack],
        [{ // Current region
          latitude: currentLocation.latitude,
          longitude: currentLocation.longitude,
          latitudeDelta: 0.02,
          longitudeDelta: 0.02,
        }],
        (progress) => {
          setDownloadProgress(
            (progress.progress / progress.total) * 100
          );
        }
      );
    } catch (error) {
      logger.error('Error downloading content:', error);
    } finally {
      setDownloadProgress(null);
    }
  };

  // Setup audio players with offline support
  const setupAudioPlayers = async (story: Story, track: Track) => {
    try {
      // Get audio URLs (offline or online)
      const storyAudioUrl = await OfflineManager.getOfflineUrl(story.id) || story.audio.url;
      const trackAudioUrl = await OfflineManager.getOfflineUrl(track.id) || track.url;

      // Load story audio
      const storySound = new Audio.Sound();
      await storySound.loadAsync({ uri: storyAudioUrl });
      storyPlayerRef.current = storySound;

      // Load background music
      const musicSound = new Audio.Sound();
      await musicSound.loadAsync({ uri: trackAudioUrl });
      await musicSound.setVolumeAsync(0.3);
      musicPlayerRef.current = musicSound;

      // Setup audio state monitoring
      storySound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded) {
          setAudioState({
            isPlaying: status.isPlaying,
            duration: status.durationMillis || 0,
            position: status.positionMillis,
            isLoading: false,
          });
        }
      });

    } catch (error) {
      await ErrorHandler.handleError(error, {
        title: 'Audio Setup Error',
        message: 'Unable to setup audio playback.',
        retry: () => setupAudioPlayers(story, track),
      });
    }
  };

  // Playback controls
  const togglePlayback = async () => {
    try {
      if (audioState.isPlaying) {
        await storyPlayerRef.current?.pauseAsync();
        await musicPlayerRef.current?.pauseAsync();
      } else {
        await storyPlayerRef.current?.playAsync();
        await musicPlayerRef.current?.playAsync();
      }
    } catch (error) {
      logger.error('Error toggling playback:', error);
    }
  };

  const seekTo = async (position: number) => {
    try {
      await storyPlayerRef.current?.setPositionAsync(position);
    } catch (error) {
      logger.error('Error seeking:', error);
    }
  };

  // Toggle voice commands
  const toggleVoiceCommands = async () => {
    try {
      if (isVoiceEnabled) {
        await VoiceInteractionManager.stopListening();
      } else {
        await VoiceInteractionManager.startListening();
      }
      setIsVoiceEnabled(!isVoiceEnabled);
    } catch (error) {
      await ErrorHandler.handleError(error, {
        title: 'Voice Command Error',
        message: 'Unable to toggle voice commands.',
      });
    }
  };

  // Cleanup function
  const cleanup = async () => {
    try {
      await storyPlayerRef.current?.unloadAsync();
      await musicPlayerRef.current?.unloadAsync();
      stopSpeech();
    } catch (error) {
      logger.error('Error cleaning up:', error);
    }
  };

  return (
    <Animated.View
      style={[
        styles.container,
        {
          transform: [{ translateY }],
        },
      ]}
      {...panResponder.panHandlers}
    >
      <BlurView intensity={80} style={StyleSheet.absoluteFill}>
        {/* Header */}
        <Surface style={styles.header}>
          <View style={styles.headerContent}>
            <Text style={styles.title}>
              {currentStory?.title || 'Loading...'}
            </Text>
            {isOffline && (
              <Chip
                icon="cloud-off"
                style={styles.offlineChip}
              >
                Offline Mode
              </Chip>
            )}
            <View style={styles.interestTags}>
              {currentStory?.categories.map(category => (
                <Chip
                  key={category}
                  style={[
                    styles.interestChip,
                    {
                      backgroundColor: `rgba(${COLORS.primary_rgb}, ${
                        relevanceScores[category] || 0.5
                      })`,
                    },
                  ]}
                >
                  {category}
                </Chip>
              ))}
            </View>
          </View>
          <IconButton
            icon="close"
            size={24}
            onPress={onClose}
          />
        </Surface>

        {/* Download Progress */}
        {downloadProgress !== null && (
          <View style={styles.downloadProgress}>
            <ActivityIndicator size="small" />
            <Text style={styles.downloadText}>
              Downloading for offline use ({Math.round(downloadProgress)}%)
            </Text>
          </View>
        )}

        {/* Main Content */}
        <View style={styles.content}>
          {/* Story Image */}
          {currentStory?.media[0] && (
            <Image
              source={{ uri: currentStory.media[0].url }}
              style={styles.storyImage}
            />
          )}

          {/* Music Visualizer */}
          <MusicVisualizer
            isPlaying={audioState.isPlaying}
            style={styles.visualizer}
          />

          {/* Playback Controls */}
          <View style={styles.controls}>
            <IconButton
              icon="skip-previous"
              size={32}
              onPress={() => {/* Handle previous */}}
            />
            <IconButton
              icon={audioState.isPlaying ? 'pause' : 'play'}
              size={48}
              onPress={togglePlayback}
            />
            <IconButton
              icon="skip-next"
              size={32}
              onPress={() => {/* Handle next */}}
            />
          </View>

          {/* Progress Bar */}
          <View style={styles.progressContainer}>
            <Text style={styles.timeText}>
              {formatTime(audioState.position)}
            </Text>
            <ProgressBar
              progress={audioState.position / audioState.duration}
              style={styles.progressBar}
            />
            <Text style={styles.timeText}>
              {formatTime(audioState.duration)}
            </Text>
          </View>

          {/* Upcoming Stories */}
          <View style={styles.upcomingContainer}>
            <Text style={styles.sectionTitle}>Coming Up</Text>
            {upcomingStories.map((story, index) => (
              <StoryCard
                key={story.id}
                story={story}
                relevanceScores={relevanceScores}
                style={[
                  styles.upcomingStory,
                  { marginTop: index === 0 ? 0 : SPACING.small },
                ]}
              />
            ))}
          </View>
        </View>

        {/* Bottom Bar */}
        <Surface style={styles.bottomBar}>
          <Button
            mode="outlined"
            icon="tune"
            onPress={() => setShowInterests(true)}
          >
            Customize
          </Button>
          <Button
            mode="outlined"
            icon={isVoiceEnabled ? 'microphone' : 'microphone-off'}
            onPress={toggleVoiceCommands}
          >
            Voice
          </Button>
          <Button
            mode="outlined"
            icon="playlist-music"
            onPress={() => {/* Show playlist */}}
          >
            Playlist
          </Button>
        </Surface>
      </BlurView>

      {/* Interests Modal */}
      <Portal>
        <Modal
          visible={showInterests}
          onDismiss={() => setShowInterests(false)}
          contentContainerStyle={styles.modal}
        >
          <InterestSelector
            currentInterests={preferences.interests}
            onUpdateInterests={async (interests) => {
              await updateInterests(interests);
              setShowInterests(false);
              loadImmersiveContent(); // Reload with new preferences
            }}
          />
        </Modal>
      </Portal>
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'transparent',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: SPACING.medium,
  },
  headerContent: {
    flex: 1,
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
  },
  interestTags: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: SPACING.small,
  },
  interestChip: {
    marginRight: SPACING.xsmall,
    marginBottom: SPACING.xsmall,
  },
  content: {
    flex: 1,
    padding: SPACING.medium,
  },
  storyImage: {
    width: '100%',
    height: 200,
    borderRadius: 8,
    marginBottom: SPACING.medium,
  },
  visualizer: {
    height: 100,
    marginBottom: SPACING.medium,
  },
  controls: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: SPACING.medium,
  },
  progressContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: SPACING.medium,
  },
  progressBar: {
    flex: 1,
    marginHorizontal: SPACING.small,
  },
  timeText: {
    fontSize: 12,
    color: COLORS.textSecondary,
  },
  upcomingContainer: {
    flex: 1,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: SPACING.small,
  },
  upcomingStory: {
    marginBottom: SPACING.small,
  },
  bottomBar: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    padding: SPACING.medium,
  },
  modal: {
    backgroundColor: COLORS.background,
    margin: SPACING.medium,
    padding: SPACING.medium,
    borderRadius: 8,
  },
  offlineChip: {
    marginTop: SPACING.xsmall,
    backgroundColor: COLORS.warning,
  },
  downloadProgress: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: SPACING.small,
    backgroundColor: COLORS.surface,
  },
  downloadText: {
    marginLeft: SPACING.small,
    color: COLORS.textSecondary,
  },
});

// Helper function to format time
const formatTime = (ms: number) => {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
};

// Helper function to find nearest story
const findNearestStory = (stories: Story[], location: Location): Story => {
  return stories.reduce((nearest, story) => {
    const distance = calculateDistance(
      location.latitude,
      location.longitude,
      story.location.latitude,
      story.location.longitude
    );
    return distance < (nearest.distance || Infinity) ? { ...story, distance } : nearest;
  });
};

// Helper function to calculate distance between coordinates
const calculateDistance = (
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number => {
  const R = 6371; // Earth's radius in km
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = 
    Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
    Math.sin(dLon/2) * Math.sin(dLon/2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  return R * c;
};

export default ImmersivePlayer; 