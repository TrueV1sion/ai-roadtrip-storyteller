import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { logger } from '@/services/logger';
import {
  View,
  StyleSheet,
  Animated,
  Dimensions,
  Platform,
  ScrollView,
  Image,
  TouchableOpacity,
} from 'react-native';
import {
  Surface,
  Text,
  IconButton,
  Portal,
  Modal,
  Button,
  Chip,
  Slider,
} from 'react-native-paper';
import { BlurView } from 'expo-blur';
import { MaterialIcons } from '@expo/vector-icons';
import MapView, { Marker, Polyline, PROVIDER_GOOGLE, MapStyleElement } from 'react-native-maps';
import { Audio } from 'expo-av';
import { MusicVisualizer } from '../immersive/MusicVisualizer';
import { StoryCard } from '../immersive/StoryCard';
import { Story } from '../../types/story';
import { Track } from '../../types/audio';
import { Location, Route, Region } from '../../types/location';
import { NavigationState, RouteMetrics } from '../../types/navigation';
import { formatDistance, formatDuration } from '../../utils/formatters';
import { COLORS, SPACING } from '../../theme';
import { useVoiceGuidance } from '../../hooks/useVoiceGuidance';
import OfflineManager from '../../services/OfflineManager';
import ErrorHandler from '../../services/ErrorHandler';
import { SharedValue, useSharedValue, withSpring } from 'react-native-reanimated';
import { PanGestureHandler } from 'react-native-gesture-handler';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { AudioMixConfig, AudioTransition } from '../../types/audio';
import { SoundSettingsModal } from './SoundSettingsModal';
import { FadeInUp, FadeOutDown } from 'react-native-reanimated';
import { Camera } from 'expo-camera';
import * as Location from 'expo-location';
import { Accelerometer, Magnetometer } from 'expo-sensors';
import { GLView } from 'expo-gl';
import { Renderer, TextureLoader, THREE } from 'expo-three';

interface ImmersiveNavigationViewProps {
  route: Route;
  onExit: () => void;
}

// Update map styles with more options
const MAP_STYLES: Record<'default' | 'night' | 'satellite' | 'nature' | 'transit' | 'terrain' | 'retro' | 'silver', MapStyleElement[]> = {
  default: [
    {
      featureType: 'all',
      elementType: 'geometry',
      stylers: [{ saturation: -20 }],
    },
    {
      featureType: 'road',
      elementType: 'geometry',
      stylers: [{ color: COLORS.primary + '80' }],
    },
    {
      featureType: 'poi',
      elementType: 'labels',
      stylers: [{ visibility: 'off' }],
    },
  ],
  night: [
    {
      featureType: 'all',
      elementType: 'geometry',
      stylers: [{ saturation: -100 }, { lightness: -40 }],
    },
    {
      featureType: 'road',
      elementType: 'geometry',
      stylers: [{ color: '#404040' }],
    },
    {
      featureType: 'water',
      elementType: 'geometry',
      stylers: [{ color: '#101020' }],
    },
  ],
  satellite: [],  // Default satellite view
  nature: [
    {
      featureType: 'landscape.natural',
      elementType: 'geometry',
      stylers: [{ saturation: 40 }, { lightness: 10 }],
    },
    {
      featureType: 'water',
      elementType: 'geometry',
      stylers: [{ color: '#a3d1ff' }],
    },
    {
      featureType: 'poi.park',
      elementType: 'geometry',
      stylers: [{ color: '#7ac97a' }],
    },
  ],
  transit: [
    {
      featureType: 'transit',
      elementType: 'geometry',
      stylers: [{ visibility: 'on' }, { color: '#3a4b78' }],
    },
    {
      featureType: 'transit.station',
      elementType: 'labels',
      stylers: [{ visibility: 'on' }, { color: '#3a4b78' }],
    },
    {
      featureType: 'road',
      elementType: 'geometry',
      stylers: [{ color: '#ffffff' }],
    },
  ],
  terrain: [
    {
      featureType: 'landscape.natural',
      elementType: 'geometry',
      stylers: [{ color: '#c9dd93' }],
    },
    {
      featureType: 'landscape.natural.terrain',
      elementType: 'geometry',
      stylers: [{ visibility: 'on' }, { color: '#93b771' }],
    },
    {
      featureType: 'administrative.country',
      elementType: 'geometry.stroke',
      stylers: [{ color: '#a3a3a3' }],
    },
  ],
  retro: [
    {
      featureType: 'all',
      elementType: 'geometry',
      stylers: [{ saturation: -60 }, { gamma: 0.8 }],
    },
    {
      featureType: 'water',
      elementType: 'geometry',
      stylers: [{ color: '#b0d3e5' }],
    },
    {
      featureType: 'poi.park',
      elementType: 'geometry',
      stylers: [{ color: '#a0c396' }],
    },
  ],
  silver: [
    {
      featureType: 'all',
      elementType: 'geometry',
      stylers: [{ saturation: -100 }, { lightness: 20 }],
    },
    {
      featureType: 'road',
      elementType: 'geometry',
      stylers: [{ lightness: 100 }],
    },
    {
      featureType: 'water',
      elementType: 'geometry',
      stylers: [{ lightness: -20 }],
    },
  ],
};

// Add AR-related interfaces
interface ARPoint {
  x: number;
  y: number;
  z: number;
  distance: number;
  bearing: number;
  elevation: number;
}

interface ARState {
  heading: number;
  pitch: number;
  roll: number;
  cameraPermission: boolean;
  points: ARPoint[];
  isCalibrating: boolean;
}

// Add AR path navigation interfaces
interface ARPathPoint extends ARPoint {
  type: 'path' | 'turn' | 'landmark';
  instruction?: string;
  turnAngle?: number;
  nextPoint?: ARPoint;
}

interface ARNavigationState {
  currentSegment: RouteSegment;
  nextTurn?: {
    distance: number;
    instruction: string;
    angle: number;
  };
  pathPoints: ARPathPoint[];
  visiblePoints: ARPathPoint[];
}

export const ImmersiveNavigationView: React.FC<ImmersiveNavigationViewProps> = ({
  route,
  onExit,
}) => {
  // Map and navigation state
  const mapRef = useRef<MapView>(null);
  const [currentLocation, setCurrentLocation] = useState<Location>();
  const [navigationState, setNavigationState] = useState<NavigationState>({
    currentRoute: route,
    isNavigating: true,
  });
  const [metrics, setMetrics] = useState<RouteMetrics>();

  // Immersive features state
  const [currentStory, setCurrentStory] = useState<Story>();
  const [upcomingStories, setUpcomingStories] = useState<Story[]>([]);
  const [currentTrack, setCurrentTrack] = useState<Track>();
  const [isPlaying, setIsPlaying] = useState(false);
  const [showStoryDetails, setShowStoryDetails] = useState(false);
  const [ambientVolume, setAmbientVolume] = useState(0.3);

  // Animation values
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(0)).current;
  const pulseAnim = useRef(new Animated.Value(1)).current;

  // Audio refs
  const musicPlayerRef = useRef<Audio.Sound>();
  const storyPlayerRef = useRef<Audio.Sound>();
  const { speak } = useVoiceGuidance();

  // Add new state variables
  const [showSoundSettings, setShowSoundSettings] = useState(false);
  const [audioConfig, setAudioConfig] = useState<AudioMixConfig>({
    storyVolume: 1,
    musicVolume: 0.3,
    ambientVolume: 0.2,
    crossfadeDuration: 2,
    musicFadeIn: 1,
    musicFadeOut: 1,
    duckingAmount: 0.5,
    duckingSpeed: 200,
    equalizerSettings: {
      bass: 0,
      mid: 0,
      treble: 0,
    },
  });
  const [interactionMode, setInteractionMode] = useState<'story' | 'explore'>('story');
  const [storyProgress, setStoryProgress] = useState(0);
  const [showLandmarkDetails, setShowLandmarkDetails] = useState(false);
  const [selectedLandmark, setSelectedLandmark] = useState<Story['landmarks'][0] | null>(null);
  const [nearbyContent, setNearbyContent] = useState<{
    stories: Story[];
    landmarks: Story['landmarks'];
    distance: number;
  }>();

  // Animation values
  const storyScale = useSharedValue(1);
  const cardRotation = useSharedValue(0);
  const mapBlur = useSharedValue(0);
  const insets = useSafeAreaInsets();

  // Add to component state
  const [mapType, setMapType] = useState<'standard' | 'satellite' | 'hybrid'>('standard');
  const [mapStyle, setMapStyle] = useState<'default' | 'night' | 'satellite' | 'nature' | 'transit' | 'terrain' | 'retro' | 'silver'>('default');
  const [showTraffic, setShowTraffic] = useState(true);
  const [showLandmarks, setShowLandmarks] = useState(true);
  const [isMapExpanded, setIsMapExpanded] = useState(false);
  const [routeProgress, setRouteProgress] = useState(0);

  // Add new state for landmark interactions
  const [landmarkInteractions, setLandmarkInteractions] = useState<{
    [key: string]: {
      visited: boolean;
      favorite: boolean;
      notes: string;
      photos: string[];
    };
  }>({});
  const [showLandmarkGallery, setShowLandmarkGallery] = useState(false);
  const [landmarkViewMode, setLandmarkViewMode] = useState<'list' | 'ar' | 'map'>('map');
  const [landmarkFilter, setLandmarkFilter] = useState<'all' | 'unvisited' | 'favorite'>('all');

  // Add to component state
  const [arState, setARState] = useState<ARState>({
    heading: 0,
    pitch: 0,
    roll: 0,
    cameraPermission: false,
    points: [],
    isCalibrating: false,
  });
  const [showARCalibration, setShowARCalibration] = useState(false);
  const cameraRef = useRef<Camera>(null);
  const glRef = useRef<GLView>(null);
  const rendererRef = useRef<Renderer>();
  const sceneRef = useRef<THREE.Scene>();
  const cameraARRef = useRef<THREE.PerspectiveCamera>();

  // Add to component state
  const [arNavigation, setARNavigation] = useState<ARNavigationState>({
    pathPoints: [],
    visiblePoints: [],
  });

  // Calculate visible region based on route
  const routeBounds = useMemo(() => {
    if (!navigationState.currentRoute?.steps.length) return null;

    const coordinates = navigationState.currentRoute.steps.map(step => ({
      latitude: step.startLocation.latitude,
      longitude: step.startLocation.longitude,
    }));

    const latitudes = coordinates.map(c => c.latitude);
    const longitudes = coordinates.map(c => c.longitude);

    return {
      latitude: (Math.min(...latitudes) + Math.max(...latitudes)) / 2,
      longitude: (Math.min(...longitudes) + Math.max(...longitudes)) / 2,
      latitudeDelta: (Math.max(...latitudes) - Math.min(...latitudes)) * 1.5,
      longitudeDelta: (Math.max(...longitudes) - Math.min(...longitudes)) * 1.5,
    };
  }, [navigationState.currentRoute]);

  // Initialize immersive features
  useEffect(() => {
    setupImmersiveMode();
    return () => cleanup();
  }, []);

  const setupImmersiveMode = async () => {
    try {
      // Load location-based stories and ambient music
      const response = await fetch('/api/immersive/navigation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          route: route,
          preferences: {
            includeStories: true,
            includeMusic: true,
            includeLandmarks: true,
          },
        }),
      });

      if (!response.ok) {
        throw ErrorHandler.createApiError(
          'Failed to load immersive content',
          response.status,
          '/api/immersive/navigation'
        );
      }

      const data = await response.json();
      setCurrentStory(data.currentStory);
      setUpcomingStories(data.upcomingStories);
      setCurrentTrack(data.currentTrack);

      // Setup audio players
      await setupAudioPlayers(data.currentTrack, data.currentStory);

      // Start animations
      Animated.parallel([
        Animated.timing(fadeAnim, {
          toValue: 1,
          duration: 1000,
          useNativeDriver: true,
        }),
        Animated.timing(slideAnim, {
          toValue: 1,
          duration: 1000,
          useNativeDriver: true,
        }),
      ]).start();

      // Start pulse animation
      startPulseAnimation();

    } catch (error) {
      await ErrorHandler.handleError(error, {
        title: 'Immersive Mode Error',
        message: 'Unable to load immersive features.',
        retry: setupImmersiveMode,
      });
    }
  };

  const setupAudioPlayers = async (track?: Track, story?: Story) => {
    try {
      if (track) {
        const musicSound = new Audio.Sound();
        await musicSound.loadAsync(
          { uri: await OfflineManager.getOfflineUrl(track.id) || track.url },
          { shouldPlay: false, volume: ambientVolume }
        );
        musicPlayerRef.current = musicSound;
      }

      if (story?.audio) {
        const storySound = new Audio.Sound();
        await storySound.loadAsync(
          { uri: await OfflineManager.getOfflineUrl(story.id) || story.audio.url }
        );
        storyPlayerRef.current = storySound;
      }
    } catch (error) {
      logger.error('Error setting up audio:', error);
    }
  };

  const startPulseAnimation = () => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1.1,
          duration: 1000,
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 1000,
          useNativeDriver: true,
        }),
      ])
    ).start();
  };

  const togglePlayback = async () => {
    try {
      if (isPlaying) {
        await musicPlayerRef.current?.pauseAsync();
        await storyPlayerRef.current?.pauseAsync();
      } else {
        await musicPlayerRef.current?.playAsync();
        if (currentStory) {
          await storyPlayerRef.current?.playAsync();
        }
      }
      setIsPlaying(!isPlaying);
    } catch (error) {
      logger.error('Error toggling playback:', error);
    }
  };

  const cleanup = async () => {
    try {
      await musicPlayerRef.current?.unloadAsync();
      await storyPlayerRef.current?.unloadAsync();
    } catch (error) {
      logger.error('Error cleaning up:', error);
    }
  };

  // Add new effects and functions
  useEffect(() => {
    // Monitor story progress and trigger events
    if (storyProgress > 0) {
      const landmark = currentStory?.landmarks?.find(
        l => l.distance / (currentStory.distance || 1) === storyProgress
      );
      if (landmark) {
        highlightLandmark(landmark);
      }
    }
  }, [storyProgress, currentStory]);

  useEffect(() => {
    // Setup location monitoring for nearby content
    const locationInterval = setInterval(checkNearbyContent, 10000);
    return () => clearInterval(locationInterval);
  }, [currentLocation]);

  const checkNearbyContent = async () => {
    if (!currentLocation) return;

    try {
      const response = await fetch('/api/immersive/nearby', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          location: currentLocation,
          radius: 1000, // 1km radius
        }),
      });

      if (!response.ok) throw new Error('Failed to fetch nearby content');

      const data = await response.json();
      setNearbyContent(data);

      // Trigger ambient sounds or stories based on proximity
      if (data.distance < 200) { // Within 200m
        triggerProximityContent(data);
      }
    } catch (error) {
      logger.error('Error checking nearby content:', error);
    }
  };

  const triggerProximityContent = async (content: typeof nearbyContent) => {
    if (!content) return;

    // Crossfade current audio if needed
    if (isPlaying) {
      await crossfadeAudio({
        type: 'fadeOut',
        duration: audioConfig.crossfadeDuration,
        curve: 'exponential',
        startVolume: audioConfig.musicVolume,
        endVolume: 0,
      });
    }

    // Play ambient sounds or story intro
    if (content.stories.length > 0) {
      speak(`Approaching ${content.stories[0].title}`);
    }
  };

  const crossfadeAudio = async (transition: AudioTransition) => {
    try {
      const { duration, startVolume, endVolume, curve } = transition;
      const steps = 20;
      const stepDuration = duration / steps;

      for (let i = 0; i <= steps; i++) {
        const progress = i / steps;
        let volume;

        if (curve === 'exponential') {
          volume = startVolume + (endVolume - startVolume) * (progress * progress);
        } else if (curve === 'logarithmic') {
          volume = startVolume + (endVolume - startVolume) * Math.sqrt(progress);
        } else {
          volume = startVolume + (endVolume - startVolume) * progress;
        }

        await musicPlayerRef.current?.setVolumeAsync(volume);
        await new Promise(resolve => setTimeout(resolve, stepDuration * 1000));
      }
    } catch (error) {
      logger.error('Error during audio crossfade:', error);
    }
  };

  const highlightLandmark = (landmark: Story['landmarks'][0]) => {
    setSelectedLandmark(landmark);
    mapRef.current?.animateCamera({
      center: landmark.location,
      pitch: 45,
      heading: 0,
      zoom: 18,
    });
    storyScale.value = withSpring(1.1);
    mapBlur.value = withSpring(5);
  };

  const handleStoryInteraction = (gesture: { x: number; y: number }) => {
    // Calculate rotation based on touch position
    const rotation = (gesture.x / Dimensions.get('window').width - 0.5) * 30;
    cardRotation.value = withSpring(rotation);
  };

  // Update the sound button click handler
  const handleSoundSettingsPress = () => {
    setShowSoundSettings(true);
  };

  const handleUpdateAudioConfig = (newConfig: AudioMixConfig) => {
    setAudioConfig(newConfig);
    // Apply new audio settings
    if (musicPlayerRef.current) {
      musicPlayerRef.current.setVolumeAsync(newConfig.musicVolume);
    }
    if (storyPlayerRef.current) {
      storyPlayerRef.current.setVolumeAsync(newConfig.storyVolume);
    }
  };

  // Add new render methods
  const renderSoundSettings = () => (
    <Portal>
      <Modal
        visible={showSoundSettings}
        onDismiss={() => setShowSoundSettings(false)}
        contentContainerStyle={styles.soundSettingsModal}
      >
        <Text style={styles.modalTitle}>Sound Settings</Text>
        
        <View style={styles.volumeControls}>
          <Text style={styles.settingLabel}>Story Volume</Text>
          <Slider
            value={audioConfig.storyVolume}
            onValueChange={value =>
              setAudioConfig(prev => ({ ...prev, storyVolume: value }))
            }
            style={styles.slider}
          />
          
          <Text style={styles.settingLabel}>Music Volume</Text>
          <Slider
            value={audioConfig.musicVolume}
            onValueChange={value =>
              setAudioConfig(prev => ({ ...prev, musicVolume: value }))
            }
            style={styles.slider}
          />
          
          <Text style={styles.settingLabel}>Ambient Volume</Text>
          <Slider
            value={audioConfig.ambientVolume}
            onValueChange={value =>
              setAudioConfig(prev => ({ ...prev, ambientVolume: value }))
            }
            style={styles.slider}
          />
        </View>

        <View style={styles.equalizerControls}>
          <Text style={styles.settingLabel}>Equalizer</Text>
          <View style={styles.eqSliders}>
            <View style={styles.eqSlider}>
              <Text style={styles.eqLabel}>Bass</Text>
              <Slider
                value={audioConfig.equalizerSettings.bass}
                minimumValue={-12}
                maximumValue={12}
                onValueChange={value =>
                  setAudioConfig(prev => ({
                    ...prev,
                    equalizerSettings: {
                      ...prev.equalizerSettings,
                      bass: value,
                    },
                  }))
                }
                style={[styles.slider, { height: 100 }]}
                vertical
              />
            </View>
            <View style={styles.eqSlider}>
              <Text style={styles.eqLabel}>Mid</Text>
              <Slider
                value={audioConfig.equalizerSettings.mid}
                minimumValue={-12}
                maximumValue={12}
                onValueChange={value =>
                  setAudioConfig(prev => ({
                    ...prev,
                    equalizerSettings: {
                      ...prev.equalizerSettings,
                      mid: value,
                    },
                  }))
                }
                style={[styles.slider, { height: 100 }]}
                vertical
              />
            </View>
            <View style={styles.eqSlider}>
              <Text style={styles.eqLabel}>Treble</Text>
              <Slider
                value={audioConfig.equalizerSettings.treble}
                minimumValue={-12}
                maximumValue={12}
                onValueChange={value =>
                  setAudioConfig(prev => ({
                    ...prev,
                    equalizerSettings: {
                      ...prev.equalizerSettings,
                      treble: value,
                    },
                  }))
                }
                style={[styles.slider, { height: 100 }]}
                vertical
              />
            </View>
          </View>
        </View>

        <View style={styles.audioSettings}>
          <Text style={styles.settingLabel}>Audio Settings</Text>
          <View style={styles.settingRow}>
            <Text>Ducking Amount</Text>
            <Slider
              value={audioConfig.duckingAmount}
              onValueChange={value =>
                setAudioConfig(prev => ({ ...prev, duckingAmount: value }))
              }
              style={[styles.slider, { width: 100 }]}
            />
          </View>
          <View style={styles.settingRow}>
            <Text>Crossfade Duration</Text>
            <Slider
              value={audioConfig.crossfadeDuration}
              minimumValue={0.5}
              maximumValue={5}
              onValueChange={value =>
                setAudioConfig(prev => ({ ...prev, crossfadeDuration: value }))
              }
              style={[styles.slider, { width: 100 }]}
            />
          </View>
        </View>

        <Button
          mode="contained"
          onPress={() => setShowSoundSettings(false)}
          style={styles.doneButton}
        >
          Done
        </Button>
      </Modal>
    </Portal>
  );

  // Add map interaction handlers
  const handleMapPress = (event: any) => {
    setSelectedLandmark(null);
  };

  const handleMarkerPress = (landmark: Story['landmarks'][0]) => {
    setSelectedLandmark(landmark);
    mapRef.current?.animateCamera({
      center: landmark.location,
      pitch: 45,
      heading: 0,
      zoom: 18,
    });
  };

  const toggleMapExpansion = () => {
    setIsMapExpanded(!isMapExpanded);
    if (!isMapExpanded && routeBounds) {
      mapRef.current?.animateToRegion(routeBounds, 1000);
    }
  };

  // Update map style based on time of day
  useEffect(() => {
    const hour = new Date().getHours();
    if (hour >= 20 || hour < 6) {
      setMapStyle('night');
    }
  }, []);

  // Update route progress
  useEffect(() => {
    if (currentLocation && navigationState.currentRoute) {
      const progress = calculateRouteProgress(
        currentLocation,
        navigationState.currentRoute
      );
      setRouteProgress(progress);
    }
  }, [currentLocation, navigationState.currentRoute]);

  // Add landmark interaction handlers
  const handleLandmarkInteraction = (landmark: Story['landmarks'][0], action: 'visit' | 'favorite' | 'note' | 'photo') => {
    setLandmarkInteractions(prev => ({
      ...prev,
      [landmark.name]: {
        ...prev[landmark.name],
        [action === 'visit' ? 'visited' : action === 'favorite' ? 'favorite' : '']: 
          action === 'visit' || action === 'favorite' 
            ? !(prev[landmark.name]?.[action === 'visit' ? 'visited' : 'favorite'])
            : prev[landmark.name]?.[action === 'visit' ? 'visited' : 'favorite'],
      },
    }));
  };

  // Update landmark info card
  const renderLandmarkInfo = (landmark: Story['landmarks'][0]) => (
    <Animated.View
      entering={FadeInUp}
      exiting={FadeOutDown}
      style={styles.landmarkInfo}
    >
      <Surface style={styles.landmarkCard}>
        <View style={styles.landmarkHeader}>
          <View>
            <Text style={styles.landmarkTitle}>{landmark.name}</Text>
            <Text style={styles.landmarkDistance}>
              {formatDistance(landmark.distance)} ahead
            </Text>
          </View>
          <View style={styles.landmarkActions}>
            <IconButton
              icon={landmarkInteractions[landmark.name]?.visited ? 'check-circle' : 'checkbox-blank-circle-outline'}
              color={landmarkInteractions[landmark.name]?.visited ? COLORS.success : COLORS.text}
              onPress={() => handleLandmarkInteraction(landmark, 'visit')}
            />
            <IconButton
              icon={landmarkInteractions[landmark.name]?.favorite ? 'heart' : 'heart-outline'}
              color={landmarkInteractions[landmark.name]?.favorite ? COLORS.error : COLORS.text}
              onPress={() => handleLandmarkInteraction(landmark, 'favorite')}
            />
            <IconButton
              icon="image-multiple"
              onPress={() => setShowLandmarkGallery(true)}
            />
          </View>
        </View>

        <Text style={styles.landmarkDescription}>
          {landmark.description}
        </Text>

        {/* Image Gallery */}
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={styles.landmarkGallery}
        >
          {landmark.images?.map((image, index) => (
            <TouchableOpacity
              key={index}
              onPress={() => setShowLandmarkGallery(true)}
            >
              <Image
                source={{ uri: image }}
                style={styles.landmarkThumbnail}
              />
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/* Quick Actions */}
        <View style={styles.landmarkQuickActions}>
          <Button
            mode="outlined"
            icon="navigation"
            onPress={() => {
              mapRef.current?.animateCamera({
                center: landmark.location,
                pitch: 45,
                heading: 0,
                zoom: 18,
              });
            }}
          >
            Navigate
          </Button>
          <Button
            mode="outlined"
            icon="share"
            onPress={() => {/* Share landmark */}}
          >
            Share
          </Button>
          <Button
            mode="outlined"
            icon={landmarkViewMode === 'ar' ? 'view-in-ar' : 'map'}
            onPress={() => handleLandmarkViewModeChange(landmarkViewMode === 'map' ? 'ar' : 'map')}
          >
            {landmarkViewMode === 'ar' ? 'AR View' : 'Map View'}
          </Button>
        </View>
      </Surface>
    </Animated.View>
  );

  // Add AR setup and cleanup
  useEffect(() => {
    let subscriptions: any[] = [];
    
    const setupAR = async () => {
      // Request permissions
      const { status: cameraStatus } = await Camera.requestCameraPermissionsAsync();
      const { status: locationStatus } = await Location.requestForegroundPermissionsAsync();
      
      if (cameraStatus === 'granted' && locationStatus === 'granted') {
        setARState(prev => ({ ...prev, cameraPermission: true }));
        
        // Setup sensor subscriptions
        subscriptions.push(
          Accelerometer.addListener(({ x, y, z }) => {
            // Calculate pitch and roll
            const pitch = Math.atan2(-x, Math.sqrt(y * y + z * z));
            const roll = Math.atan2(y, z);
            setARState(prev => ({ ...prev, pitch, roll }));
          })
        );
        
        subscriptions.push(
          Magnetometer.addListener(({ x, y, z }) => {
            // Calculate heading
            const heading = Math.atan2(y, x);
            setARState(prev => ({ ...prev, heading }));
          })
        );
        
        // Start sensors with high update frequency
        await Accelerometer.setUpdateInterval(100);
        await Magnetometer.setUpdateInterval(100);
      }
    };
    
    setupAR();
    return () => {
      subscriptions.forEach(sub => sub.remove());
    };
  }, []);

  // Add AR rendering setup
  const setupARScene = () => {
    if (!glRef.current) return;
    
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      75,
      Dimensions.get('window').width / Dimensions.get('window').height,
      0.1,
      1000
    );
    
    const renderer = new Renderer({ gl: glRef.current });
    renderer.setSize(
      Dimensions.get('window').width,
      Dimensions.get('window').height
    );
    
    sceneRef.current = scene;
    cameraARRef.current = camera;
    rendererRef.current = renderer;
    
    // Add ambient light
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);
    
    // Add directional light
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.5);
    directionalLight.position.set(5, 5, 5);
    scene.add(directionalLight);
  };

  // Add AR point calculation
  const calculateARPoints = useCallback((landmarks: Story['landmarks']) => {
    if (!currentLocation) return [];
    
    return landmarks.map(landmark => {
      const distance = calculateDistance(
        currentLocation.latitude,
        currentLocation.longitude,
        landmark.location.latitude,
        landmark.location.longitude
      );
      
      const bearing = calculateBearing(
        currentLocation.latitude,
        currentLocation.longitude,
        landmark.location.latitude,
        landmark.location.longitude
      );
      
      // Convert to 3D coordinates
      const x = distance * Math.sin(bearing);
      const z = distance * Math.cos(bearing);
      const y = 0; // Assuming flat ground for simplicity
      
      return {
        x,
        y,
        z,
        distance,
        bearing,
        elevation: 0,
      };
    });
  }, [currentLocation]);

  // Add AR rendering function
  const renderAR = useCallback(() => {
    if (!sceneRef.current || !cameraARRef.current || !rendererRef.current) return;
    
    const { heading, pitch, roll } = arState;
    
    // Update camera rotation based on device orientation
    cameraARRef.current.rotation.set(pitch, heading, roll);
    
    // Update AR points
    arState.points.forEach((point, index) => {
      const pointMesh = sceneRef.current?.getObjectByName(`point-${index}`);
      if (pointMesh) {
        pointMesh.position.set(point.x, point.y, point.z);
        
        // Update point visibility based on heading
        const pointBearing = Math.atan2(point.x, point.z);
        const bearingDiff = Math.abs(heading - pointBearing);
        pointMesh.visible = bearingDiff < Math.PI / 4; // Only show points in 90° FOV
      }
    });
    
    rendererRef.current.render(sceneRef.current, cameraARRef.current);
  }, [arState]);

  // Add AR calibration component
  const renderARCalibration = () => (
    <Portal>
      <Modal
        visible={showARCalibration}
        onDismiss={() => setShowARCalibration(false)}
        contentContainerStyle={styles.arCalibrationModal}
      >
        <View style={styles.arCalibrationContent}>
          <Text style={styles.arCalibrationTitle}>Calibrate AR View</Text>
          <MaterialIcons
            name="compass"
            size={48}
            color={COLORS.primary}
            style={[
              styles.arCompass,
              { transform: [{ rotate: `${arState.heading}rad` }] },
            ]}
          />
          <Text style={styles.arCalibrationInstructions}>
            Move your device in a figure-8 pattern to calibrate the compass
          </Text>
          <ProgressBar
            progress={arState.isCalibrating ? 0.5 : 1}
            style={styles.arCalibrationProgress}
            indeterminate={arState.isCalibrating}
          />
          <Button
            mode="contained"
            onPress={() => {
              setARState(prev => ({ ...prev, isCalibrating: true }));
              setTimeout(() => {
                setARState(prev => ({ ...prev, isCalibrating: false }));
                setShowARCalibration(false);
              }, 3000);
            }}
            loading={arState.isCalibrating}
            disabled={arState.isCalibrating}
          >
            Start Calibration
          </Button>
        </View>
      </Modal>
    </Portal>
  );

  // Update landmark view mode handler
  const handleLandmarkViewModeChange = (mode: 'list' | 'ar' | 'map') => {
    if (mode === 'ar' && !arState.cameraPermission) {
      // Request permissions if not granted
      Camera.requestCameraPermissionsAsync().then(({ status }) => {
        if (status === 'granted') {
          setARState(prev => ({ ...prev, cameraPermission: true }));
          setShowARCalibration(true);
        }
      });
    }
    setLandmarkViewMode(mode);
  };

  // Add AR view component
  const renderARView = () => (
    <View style={styles.arContainer}>
      <Camera
        ref={cameraRef}
        style={styles.arCamera}
        type={Camera.Constants.Type.back}
      >
        <GLView
          ref={glRef}
          style={styles.arOverlay}
          onContextCreate={setupARScene}
        />
        
        {/* AR UI Overlay */}
        <View style={styles.arUI}>
          <View style={styles.arHeader}>
            <IconButton
              icon="arrow-left"
              color={COLORS.white}
              onPress={() => setLandmarkViewMode('map')}
            />
            <Text style={styles.arTitle}>AR View</Text>
            <IconButton
              icon="compass"
              color={COLORS.white}
              onPress={() => setShowARCalibration(true)}
            />
          </View>
          
          {/* AR Points */}
          {arState.points.map((point, index) => {
            // Calculate screen position based on 3D coordinates
            const screenX = (point.x / point.z) * Dimensions.get('window').width / 2;
            const screenY = (point.y / point.z) * Dimensions.get('window').height / 2;
            
            return (
              <Animated.View
                key={index}
                style={[
                  styles.arPoint,
                  {
                    transform: [
                      { translateX: screenX },
                      { translateY: screenY },
                      { scale: 1 / (point.distance / 10) }, // Scale based on distance
                    ],
                  },
                ]}
              >
                <Surface style={styles.arPointCard}>
                  <MaterialIcons name="place" size={24} color={COLORS.primary} />
                  <Text style={styles.arPointTitle}>
                    {currentStory?.landmarks?.[index].name}
                  </Text>
                  <Text style={styles.arPointDistance}>
                    {formatDistance(point.distance)}
                  </Text>
                </Surface>
              </Animated.View>
            );
          })}
          
          {/* AR Compass */}
          <Animated.View
            style={[
              styles.arCompassContainer,
              {
                transform: [{ rotate: `${arState.heading}rad` }],
              },
            ]}
          >
            <MaterialIcons name="explore" size={32} color={COLORS.white} />
          </Animated.View>
        </View>
      </Camera>
    </View>
  );

  // Add AR path calculation
  const calculateARPath = useCallback(() => {
    if (!currentLocation || !navigationState.currentRoute) return;

    const pathPoints: ARPathPoint[] = [];
    let currentPoint = currentLocation;
    
    navigationState.currentRoute.steps.forEach((step, index) => {
      // Calculate points along the path
      const pointCount = Math.ceil(step.distance / 20); // Point every 20 meters
      for (let i = 0; i < pointCount; i++) {
        const progress = i / pointCount;
        const point = interpolatePoint(
          currentPoint,
          step.endLocation,
          progress
        );
        
        pathPoints.push({
          x: 0,
          y: 0,
          z: 0,
          distance: calculateDistance(
            currentLocation.latitude,
            currentLocation.longitude,
            point.latitude,
            point.longitude
          ),
          bearing: calculateBearing(
            currentLocation.latitude,
            currentLocation.longitude,
            point.latitude,
            point.longitude
          ),
          elevation: 0,
          type: 'path',
        });
      }

      // Add turn point if there's a next step
      if (index < navigationState.currentRoute.steps.length - 1) {
        const nextStep = navigationState.currentRoute.steps[index + 1];
        const turnAngle = calculateTurnAngle(
          step.startLocation,
          step.endLocation,
          nextStep.endLocation
        );

        pathPoints.push({
          x: 0,
          y: 0,
          z: 0,
          distance: calculateDistance(
            currentLocation.latitude,
            currentLocation.longitude,
            step.endLocation.latitude,
            step.endLocation.longitude
          ),
          bearing: calculateBearing(
            currentLocation.latitude,
            currentLocation.longitude,
            step.endLocation.latitude,
            step.endLocation.longitude
          ),
          elevation: 0,
          type: 'turn',
          instruction: step.instruction,
          turnAngle,
          nextPoint: {
            x: 0,
            y: 0,
            z: 0,
            distance: calculateDistance(
              currentLocation.latitude,
              currentLocation.longitude,
              nextStep.endLocation.latitude,
              nextStep.endLocation.longitude
            ),
            bearing: calculateBearing(
              currentLocation.latitude,
              currentLocation.longitude,
              nextStep.endLocation.latitude,
              nextStep.endLocation.longitude
            ),
            elevation: 0,
          },
        });
      }

      currentPoint = step.endLocation;
    });

    setARNavigation(prev => ({
      ...prev,
      pathPoints,
    }));
  }, [currentLocation, navigationState.currentRoute]);

  // Update AR rendering to include path visualization
  const renderARPath = useCallback(() => {
    if (!sceneRef.current || !arNavigation.pathPoints.length) return;

    // Create or update path points
    arNavigation.pathPoints.forEach((point, index) => {
      let mesh = sceneRef.current?.getObjectByName(`path-${index}`);
      
      if (!mesh) {
        // Create new point mesh based on type
        const geometry = point.type === 'turn' 
          ? new THREE.ConeGeometry(0.5, 1, 8)
          : new THREE.SphereGeometry(0.2);
        
        const material = new THREE.MeshPhongMaterial({
          color: point.type === 'turn' ? 0xff4444 : 0x4444ff,
          transparent: true,
          opacity: 0.8,
        });

        mesh = new THREE.Mesh(geometry, material);
        mesh.name = `path-${index}`;
        sceneRef.current?.add(mesh);
      }

      // Update position
      const worldPosition = calculateWorldPosition(point);
      mesh.position.set(worldPosition.x, worldPosition.y, worldPosition.z);

      // Update rotation for turn indicators
      if (point.type === 'turn' && point.turnAngle) {
        mesh.rotation.y = point.turnAngle;
      }

      // Add floating instruction text for turns
      if (point.type === 'turn' && point.instruction) {
        let textMesh = sceneRef.current?.getObjectByName(`text-${index}`);
        if (!textMesh) {
          const textGeometry = new THREE.TextGeometry(point.instruction, {
            size: 0.5,
            height: 0.1,
          });
          const textMaterial = new THREE.MeshPhongMaterial({ color: 0xffffff });
          textMesh = new THREE.Mesh(textGeometry, textMaterial);
          textMesh.name = `text-${index}`;
          sceneRef.current?.add(textMesh);
        }
        textMesh.position.set(
          worldPosition.x,
          worldPosition.y + 1.5,
          worldPosition.z
        );
        textMesh.rotation.y = -arState.heading;
      }
    });
  }, [arNavigation.pathPoints, arState.heading]);

  // Add AR UI for path navigation
  const renderARPathUI = () => (
    <View style={styles.arPathUI}>
      {/* Next Turn Indicator */}
      {arNavigation.nextTurn && (
        <Animated.View
          style={[
            styles.arNextTurn,
            {
              transform: [
                { scale: pulseAnim },
                { rotate: `${arNavigation.nextTurn.angle}deg` },
              ],
            },
          ]}
        >
          <MaterialIcons
            name={getTurnIcon(arNavigation.nextTurn.instruction)}
            size={32}
            color={COLORS.white}
          />
          <Text style={styles.arNextTurnDistance}>
            {formatDistance(arNavigation.nextTurn.distance)}
          </Text>
          <Text style={styles.arNextTurnInstruction}>
            {arNavigation.nextTurn.instruction}
          </Text>
        </Animated.View>
      )}

      {/* Path Progress */}
      <View style={styles.arProgress}>
        <View style={styles.arProgressBar}>
          <Animated.View
            style={[
              styles.arProgressFill,
              { width: `${routeProgress * 100}%` },
            ]}
          />
        </View>
        <Text style={styles.arProgressText}>
          {formatDistance(navigationState.currentRoute?.distance || 0)} remaining
        </Text>
      </View>
    </View>
  );

  return (
    <View style={styles.container}>
      {/* Main Map View */}
      <Animated.View
        style={[
          styles.mapContainer,
          isMapExpanded && styles.expandedMap,
          {
            transform: [{ scale: storyScale }],
            filter: `blur(${mapBlur.value}px)`,
          },
        ]}
      >
        <MapView
          ref={mapRef}
          style={styles.map}
          provider={PROVIDER_GOOGLE}
          mapType={mapType}
          customMapStyle={MAP_STYLES[mapStyle]}
          showsUserLocation
          showsMyLocationButton
          showsCompass
          showsTraffic={showTraffic}
          showsBuildings
          showsIndoors
          onPress={handleMapPress}
          initialRegion={routeBounds || undefined}
        >
          {navigationState.currentRoute && (
            <>
              <Polyline
                coordinates={navigationState.currentRoute.steps.map(
                  step => step.startLocation
                )}
                strokeWidth={5}
                strokeColor={COLORS.primary}
                lineDashPattern={[1]}
              />
              {/* Add progress indicator on the route */}
              <Polyline
                coordinates={navigationState.currentRoute.steps
                  .slice(0, Math.ceil(navigationState.currentRoute.steps.length * routeProgress))
                  .map(step => step.startLocation)
                }
                strokeWidth={5}
                strokeColor={COLORS.success}
              />
            </>
          )}

          {/* Landmarks */}
          {showLandmarks && currentStory?.landmarks?.map(landmark => (
            <Marker
              key={landmark.name}
              coordinate={landmark.location}
              title={landmark.name}
              description={`${formatDistance(landmark.distance)} ahead`}
              onPress={() => handleMarkerPress(landmark)}
            >
              <Animated.View
                style={[
                  styles.markerContainer,
                  selectedLandmark?.name === landmark.name && styles.selectedMarker,
                ]}
              >
                <MaterialIcons
                  name="place"
                  size={24}
                  color={selectedLandmark?.name === landmark.name ? COLORS.primary : COLORS.text}
                />
              </Animated.View>
            </Marker>
          ))}
        </MapView>

        {/* Map Controls */}
        <View style={styles.mapControls}>
          <IconButton
            icon={isMapExpanded ? 'fullscreen-exit' : 'fullscreen'}
            onPress={toggleMapExpansion}
          />
          <IconButton
            icon={showTraffic ? 'traffic' : 'traffic-off'}
            onPress={() => setShowTraffic(!showTraffic)}
          />
          <IconButton
            icon={showLandmarks ? 'place' : 'place-off'}
            onPress={() => setShowLandmarks(!showLandmarks)}
          />
          <IconButton
            icon={mapType === 'satellite' ? 'satellite' : 'map'}
            onPress={() => setMapType(mapType === 'standard' ? 'satellite' : 'standard')}
          />
        </View>

        {/* Selected Landmark Info */}
        {selectedLandmark && renderLandmarkInfo(selectedLandmark)}
      </Animated.View>

      {/* Immersive Overlay */}
      <Animated.View
        style={[
          styles.overlay,
          {
            opacity: fadeAnim,
            transform: [
              {
                translateY: slideAnim.interpolate({
                  inputRange: [0, 1],
                  outputRange: [100, 0],
                }),
              },
            ],
          },
        ]}
      >
        <BlurView intensity={80} style={styles.blurContainer}>
          {/* Current Story Preview */}
          {currentStory && (
            <Surface style={styles.storyPreview}>
              <StoryCard
                story={currentStory}
                relevanceScores={{}}
                onPress={() => setShowStoryDetails(true)}
              />
              <MusicVisualizer
                isPlaying={isPlaying}
                style={styles.visualizer}
              />
            </Surface>
          )}

          {/* Playback Controls */}
          <View style={styles.controls}>
            <IconButton
              icon="skip-previous"
              size={32}
              onPress={() => {/* Handle previous */}}
            />
            <IconButton
              icon={isPlaying ? 'pause' : 'play'}
              size={48}
              onPress={togglePlayback}
            />
            <IconButton
              icon="skip-next"
              size={32}
              onPress={() => {/* Handle next */}}
            />
          </View>

          {/* Upcoming Stories */}
          {upcomingStories.length > 0 && (
            <View style={styles.upcomingContainer}>
              <Text style={styles.sectionTitle}>Coming Up</Text>
              <ScrollView
                horizontal
                showsHorizontalScrollIndicator={false}
                style={styles.upcomingScroll}
              >
                {upcomingStories.map(story => (
                  <Surface
                    key={story.id}
                    style={styles.upcomingStory}
                  >
                    <StoryCard
                      story={story}
                      relevanceScores={{}}
                      style={styles.storyCard}
                    />
                    <Text style={styles.storyDistance}>
                      {story.distance && formatDistance(story.distance)}
                    </Text>
                  </Surface>
                ))}
              </ScrollView>
            </View>
          )}

          {/* Bottom Controls */}
          <Surface style={styles.bottomBar}>
            <Button
              mode="outlined"
              icon="map"
              onPress={() => {/* Toggle map mode */}}
            >
              Map
            </Button>
            <Button
              mode="outlined"
              icon="music-note"
              onPress={handleSoundSettingsPress}
            >
              Sound
            </Button>
            <Button
              mode="outlined"
              icon="exit-to-app"
              onPress={onExit}
            >
              Exit
            </Button>
          </Surface>
        </BlurView>
      </Animated.View>

      {/* Story Details Modal */}
      <Portal>
        <Modal
          visible={showStoryDetails}
          onDismiss={() => setShowStoryDetails(false)}
          contentContainerStyle={styles.modal}
        >
          {currentStory && (
            <ScrollView>
              <Text style={styles.modalTitle}>{currentStory.title}</Text>
              <Text style={styles.modalDescription}>
                {currentStory.description}
              </Text>
              {currentStory.landmarks?.map(landmark => (
                <Surface key={landmark.name} style={styles.landmarkCard}>
                  <Text style={styles.landmarkTitle}>{landmark.name}</Text>
                  <Text style={styles.landmarkDescription}>
                    {landmark.description}
                  </Text>
                  <Text style={styles.landmarkDistance}>
                    {formatDistance(landmark.distance)} ahead
                  </Text>
                </Surface>
              ))}
            </ScrollView>
          )}
        </Modal>
      </Portal>

      {/* Add the SoundSettingsModal */}
      <SoundSettingsModal
        visible={showSoundSettings}
        onDismiss={() => setShowSoundSettings(false)}
        audioConfig={audioConfig}
        onUpdateConfig={handleUpdateAudioConfig}
      />

      {/* Add AR view component */}
      {landmarkViewMode === 'ar' && renderARView()}

      {/* Add AR calibration component */}
      {renderARCalibration()}

      {/* Add AR path UI */}
      {renderARPathUI()}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  map: {
    ...StyleSheet.absoluteFillObject,
  },
  overlay: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    paddingBottom: Platform.OS === 'ios' ? 20 : 0,
  },
  blurContainer: {
    padding: SPACING.medium,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    overflow: 'hidden',
  },
  storyPreview: {
    borderRadius: 12,
    overflow: 'hidden',
    marginBottom: SPACING.medium,
  },
  visualizer: {
    height: 40,
    marginTop: SPACING.small,
  },
  controls: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: SPACING.medium,
  },
  upcomingContainer: {
    marginBottom: SPACING.medium,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: SPACING.small,
  },
  upcomingScroll: {
    marginHorizontal: -SPACING.medium,
    paddingHorizontal: SPACING.medium,
  },
  upcomingStory: {
    width: 280,
    marginRight: SPACING.medium,
    borderRadius: 12,
    overflow: 'hidden',
  },
  storyCard: {
    borderRadius: 12,
  },
  storyDistance: {
    position: 'absolute',
    bottom: SPACING.small,
    right: SPACING.small,
    backgroundColor: COLORS.primary + '80',
    paddingHorizontal: SPACING.small,
    paddingVertical: 2,
    borderRadius: 12,
    color: COLORS.white,
    fontSize: 12,
  },
  bottomBar: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    padding: SPACING.medium,
    borderRadius: 12,
  },
  modal: {
    backgroundColor: COLORS.background,
    margin: SPACING.medium,
    padding: SPACING.medium,
    borderRadius: 12,
    maxHeight: '80%',
  },
  modalTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: SPACING.small,
  },
  modalDescription: {
    fontSize: 16,
    color: COLORS.textSecondary,
    marginBottom: SPACING.medium,
  },
  landmarkCard: {
    padding: SPACING.medium,
    borderRadius: 12,
    marginBottom: SPACING.small,
  },
  landmarkTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: SPACING.xsmall,
  },
  landmarkDescription: {
    fontSize: 14,
    color: COLORS.textSecondary,
    marginBottom: SPACING.xsmall,
  },
  landmarkDistance: {
    fontSize: 12,
    color: COLORS.primary,
  },
  soundSettingsModal: {
    backgroundColor: COLORS.background,
    margin: SPACING.medium,
    padding: SPACING.medium,
    borderRadius: 12,
    maxHeight: '80%',
  },
  volumeControls: {
    marginBottom: SPACING.medium,
  },
  settingLabel: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: SPACING.xsmall,
  },
  slider: {
    width: '100%',
    height: 40,
  },
  equalizerControls: {
    marginBottom: SPACING.medium,
  },
  eqSliders: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  eqSlider: {
    width: '33.33%',
    height: 100,
  },
  eqLabel: {
    fontSize: 12,
    fontWeight: 'bold',
    marginBottom: SPACING.xsmall,
  },
  audioSettings: {
    marginBottom: SPACING.medium,
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SPACING.xsmall,
  },
  doneButton: {
    marginTop: SPACING.medium,
  },
  expandedMap: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 1000,
  },
  mapControls: {
    position: 'absolute',
    top: SPACING.medium,
    right: SPACING.medium,
    backgroundColor: COLORS.surface + '80',
    borderRadius: 12,
    padding: SPACING.xsmall,
  },
  markerContainer: {
    padding: SPACING.xsmall,
    backgroundColor: COLORS.surface,
    borderRadius: 12,
    elevation: 3,
  },
  selectedMarker: {
    backgroundColor: COLORS.primary + '20',
    transform: [{ scale: 1.2 }],
  },
  landmarkInfo: {
    position: 'absolute',
    bottom: SPACING.medium,
    left: SPACING.medium,
    right: SPACING.medium,
  },
  landmarkImage: {
    width: '100%',
    height: 120,
    borderRadius: 8,
    marginTop: SPACING.small,
  },
  landmarkHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: SPACING.small,
  },
  landmarkActions: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  landmarkGallery: {
    marginVertical: SPACING.small,
  },
  landmarkThumbnail: {
    width: 120,
    height: 80,
    borderRadius: 8,
    marginRight: SPACING.small,
  },
  landmarkQuickActions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: SPACING.small,
  },
  visitedMarker: {
    backgroundColor: COLORS.success + '20',
    borderColor: COLORS.success,
    borderWidth: 2,
  },
  favoriteMarker: {
    backgroundColor: COLORS.error + '20',
    borderColor: COLORS.error,
    borderWidth: 2,
  },
  arContainer: {
    flex: 1,
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
  },
  arCamera: {
    flex: 1,
  },
  arOverlay: {
    ...StyleSheet.absoluteFillObject,
  },
  arUI: {
    ...StyleSheet.absoluteFillObject,
    padding: SPACING.medium,
  },
  arHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: SPACING.medium,
  },
  arTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: COLORS.white,
    textShadowColor: 'rgba(0, 0, 0, 0.5)',
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 2,
  },
  arPoint: {
    position: 'absolute',
    alignItems: 'center',
  },
  arPointCard: {
    padding: SPACING.small,
    borderRadius: 12,
    alignItems: 'center',
    backgroundColor: COLORS.surface + 'E6',
  },
  arPointTitle: {
    fontSize: 12,
    fontWeight: 'bold',
    marginTop: SPACING.xsmall,
  },
  arPointDistance: {
    fontSize: 10,
    color: COLORS.textSecondary,
  },
  arCompassContainer: {
    position: 'absolute',
    top: SPACING.medium + 48,
    right: SPACING.medium,
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: COLORS.primary + '80',
    alignItems: 'center',
    justifyContent: 'center',
  },
  arCalibrationModal: {
    backgroundColor: COLORS.background,
    margin: SPACING.medium,
    padding: SPACING.medium,
    borderRadius: 12,
    alignItems: 'center',
  },
  arCalibrationContent: {
    alignItems: 'center',
  },
  arCalibrationTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: SPACING.medium,
  },
  arCompass: {
    marginVertical: SPACING.medium,
  },
  arCalibrationInstructions: {
    textAlign: 'center',
    marginBottom: SPACING.medium,
    color: COLORS.textSecondary,
  },
  arCalibrationProgress: {
    width: '100%',
    marginBottom: SPACING.medium,
  },
  arPathUI: {
    position: 'absolute',
    bottom: SPACING.large,
    left: SPACING.medium,
    right: SPACING.medium,
  },
  arNextTurn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: COLORS.primary + 'CC',
    padding: SPACING.small,
    borderRadius: 12,
    marginBottom: SPACING.medium,
  },
  arNextTurnDistance: {
    color: COLORS.white,
    fontSize: 16,
    fontWeight: 'bold',
    marginLeft: SPACING.small,
  },
  arNextTurnInstruction: {
    color: COLORS.white,
    fontSize: 14,
    marginLeft: SPACING.small,
    flex: 1,
  },
  arProgress: {
    backgroundColor: COLORS.surface + 'CC',
    padding: SPACING.small,
    borderRadius: 12,
  },
  arProgressBar: {
    height: 4,
    backgroundColor: COLORS.border,
    borderRadius: 2,
    marginBottom: SPACING.xsmall,
  },
  arProgressFill: {
    height: '100%',
    backgroundColor: COLORS.primary,
    borderRadius: 2,
  },
  arProgressText: {
    color: COLORS.white,
    fontSize: 12,
    textAlign: 'center',
  },
});

export default ImmersiveNavigationView; 