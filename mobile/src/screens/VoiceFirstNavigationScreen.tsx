import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View,
  StyleSheet,
  AppState,
  AppStateStatus,
  Alert,
  Platform,
} from 'react-native';
import MapView, { Marker, Polyline, PROVIDER_GOOGLE } from 'react-native-maps';
import * as Location from 'expo-location';
import { useNavigation, useRoute } from '@react-navigation/native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import KeepAwake from 'react-native-keep-awake';

import { VoiceFirstInterface } from '../components/voice/VoiceFirstInterface';
import voiceInteractionManager from '../services/voice/voiceInteractionManager';
import { navigationService } from '../services/navigation/navigationService';
import { storyService } from '../services/storyService';
import { drivingAssistantService } from '../services/drivingAssistantService';
import { OptimizedApiClient } from '../services/api/OptimizedApiClient';

interface RouteParams {
  destination?: string;
  theme?: string;
}

export const VoiceFirstNavigationScreen: React.FC = () => {
  const navigation = useNavigation();
  const route = useRoute();
  const routeParams = route.params as RouteParams;
  const insets = useSafeAreaInsets();
  const mapRef = useRef<MapView>(null);

  // State
  const [isListening, setIsListening] = useState(false);
  const [currentLocation, setCurrentLocation] = useState<Location.LocationObject | null>(null);
  const [destination, setDestination] = useState<string | null>(routeParams?.destination || null);
  const [routeCoordinates, setRouteCoordinates] = useState<any[]>([]);
  const [currentAction, setCurrentAction] = useState<string>('');
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [confirmationData, setConfirmationData] = useState<any>(null);
  const [voiceLevel, setVoiceLevel] = useState(0);
  const [isDriving, setIsDriving] = useState(true);
  const [appState, setAppState] = useState(AppState.currentState);

  const apiClient = useRef(new OptimizedApiClient()).current;

  // Initialize location tracking
  useEffect(() => {
    let locationSubscription: Location.LocationSubscription | null = null;

    const setupLocation = async () => {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert(
          'Permission Required',
          'Location permission is required for navigation.',
          [{ text: 'OK' }]
        );
        return;
      }

      // Get initial location
      const location = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.High,
      });
      setCurrentLocation(location);

      // Subscribe to location updates
      locationSubscription = await Location.watchPositionAsync(
        {
          accuracy: Location.Accuracy.High,
          timeInterval: 1000,
          distanceInterval: 10,
        },
        (location) => {
          setCurrentLocation(location);
          navigationService.updateCurrentLocation(location);
          
          // Check if moving (simple speed check)
          const speed = location.coords.speed || 0;
          setIsDriving(speed > 2); // > 2 m/s (~7 km/h)
        }
      );
    };

    setupLocation();

    return () => {
      if (locationSubscription) {
        locationSubscription.remove();
      }
    };
  }, []);

  // App state handling
  useEffect(() => {
    const handleAppStateChange = (nextAppState: AppStateStatus) => {
      if (appState.match(/inactive|background/) && nextAppState === 'active') {
        // App has come to foreground
        voiceInteractionManager.speak('Welcome back. Say a command when ready.');
      } else if (nextAppState.match(/inactive|background/)) {
        // App going to background
        voiceInteractionManager.pause();
      }
      setAppState(nextAppState);
    };

    const subscription = AppState.addEventListener('change', handleAppStateChange);
    return () => subscription.remove();
  }, [appState]);

  // Voice interaction setup
  useEffect(() => {
    // Voice state change listener
    const handleStateChange = (state: any) => {
      setIsListening(state.isListening);
      if (state.lastAction) {
        setCurrentAction(formatActionDisplay(state.lastAction));
      }
    };

    // Command listener
    const handleCommand = async ({ action, params }: any) => {
      await processCommand(action, params);
    };

    // Confirmation listener
    const handleConfirmation = ({ action, params, message }: any) => {
      setConfirmationData({ action, params });
      setCurrentAction(message);
      setShowConfirmation(true);
    };

    // Volume change listener
    const handleVolumeChange = (level: number) => {
      setVoiceLevel(level);
    };

    // Safety prompt listener
    const handleSafetyPrompt = ({ action, params }: any) => {
      Alert.alert(
        'Safety First',
        'This action requires your attention. Please pull over safely before proceeding.',
        [
          { text: 'Cancel', style: 'cancel' },
          {
            text: 'I\'m Stopped',
            onPress: () => processCommand(action, params),
          },
        ]
      );
    };

    voiceInteractionManager.on('stateChange', handleStateChange);
    voiceInteractionManager.on('command', handleCommand);
    voiceInteractionManager.on('confirmationNeeded', handleConfirmation);
    voiceInteractionManager.on('volumeChanged', handleVolumeChange);
    voiceInteractionManager.on('safetyPrompt', handleSafetyPrompt);

    // Initial greeting
    voiceInteractionManager.speak(
      'Voice navigation ready. Say "help" for available commands or tap the microphone to start.'
    );

    return () => {
      voiceInteractionManager.off('stateChange', handleStateChange);
      voiceInteractionManager.off('command', handleCommand);
      voiceInteractionManager.off('confirmationNeeded', handleConfirmation);
      voiceInteractionManager.off('volumeChanged', handleVolumeChange);
      voiceInteractionManager.off('safetyPrompt', handleSafetyPrompt);
    };
  }, []);

  // Process voice commands
  const processCommand = async (action: string, params: Record<string, string>) => {
    switch (action) {
      case 'NAVIGATE_TO':
        if (params.destination) {
          await startNavigation(params.destination);
        }
        break;

      case 'FIND_GAS_STATION':
        await findNearbyPlace('gas_station', 'gas stations');
        break;

      case 'FIND_REST_STOP':
        await findNearbyPlace('rest_area', 'rest stops');
        break;

      case 'SHOW_ALTERNATIVES':
        await showAlternativeRoutes();
        break;

      case 'STOP_NAVIGATION':
        stopNavigation();
        break;

      case 'PAUSE_NARRATION':
        storyService.pauseNarration();
        break;

      case 'RESUME_NARRATION':
        storyService.resumeNarration();
        break;

      case 'START_STORY':
        if (currentLocation) {
          await storyService.generateLocationStory(
            currentLocation.coords.latitude,
            currentLocation.coords.longitude
          );
        }
        break;

      case 'START_TRIVIA':
        navigation.navigate('TriviaGame' as never);
        break;

      case 'QUERY_LOCATION':
        announceCurrentLocation();
        break;

      case 'QUERY_TRAFFIC':
        await checkTrafficStatus();
        break;

      case 'SHOW_HELP':
        voiceInteractionManager.speak(
          'You can say: navigate to a destination, find gas station, find rest stop, ' +
          'tell me a story, play trivia, or ask about your current location.'
        );
        break;

      case 'EMERGENCY':
        handleEmergency();
        break;

      default:
        console.log('Unhandled command:', action, params);
    }
  };

  // Navigation functions
  const startNavigation = async (destination: string) => {
    if (!currentLocation) {
      voiceInteractionManager.speak('Waiting for current location. Please try again.');
      return;
    }

    try {
      setCurrentAction(`Starting navigation to ${destination}`);
      
      const route = await navigationService.getRoute(
        {
          latitude: currentLocation.coords.latitude,
          longitude: currentLocation.coords.longitude,
        },
        destination
      );

      if (route && route.coordinates) {
        setDestination(destination);
        setRouteCoordinates(route.coordinates);
        
        // Fit map to route
        if (mapRef.current) {
          mapRef.current.fitToCoordinates(route.coordinates, {
            edgePadding: { top: 100, right: 50, bottom: 200, left: 50 },
            animated: true,
          });
        }

        // Start turn-by-turn navigation
        navigationService.startNavigation(route);
        
        // Start contextual storytelling
        if (routeParams?.theme) {
          storyService.startThemedJourney(route, routeParams.theme);
        }
      }
    } catch (error) {
      console.error('Navigation error:', error);
      voiceInteractionManager.speak('Sorry, I couldn\'t find a route to that destination.');
    }
  };

  const findNearbyPlace = async (placeType: string, spokenType: string) => {
    if (!currentLocation) {
      voiceInteractionManager.speak('Waiting for current location. Please try again.');
      return;
    }

    try {
      setCurrentAction(`Finding nearby ${spokenType}`);
      
      const places = await navigationService.findNearbyPlaces(
        currentLocation.coords.latitude,
        currentLocation.coords.longitude,
        placeType
      );

      if (places && places.length > 0) {
        const nearest = places[0];
        voiceInteractionManager.speak(
          `Found ${nearest.name}, ${nearest.distance} away. Say "navigate there" to get directions.`
        );
        
        // Store for potential navigation
        setDestination(nearest.address);
      } else {
        voiceInteractionManager.speak(`No ${spokenType} found nearby.`);
      }
    } catch (error) {
      console.error('Place search error:', error);
      voiceInteractionManager.speak(`Sorry, I couldn't search for ${spokenType}.`);
    }
  };

  const showAlternativeRoutes = async () => {
    if (!currentLocation || !destination) {
      voiceInteractionManager.speak('Please set a destination first.');
      return;
    }

    navigation.navigate('AlternativeRoutes' as never, {
      origin: currentLocation.coords,
      destination,
    });
  };

  const stopNavigation = () => {
    navigationService.stopNavigation();
    storyService.stopNarration();
    setDestination(null);
    setRouteCoordinates([]);
    setCurrentAction('Navigation stopped');
  };

  const announceCurrentLocation = async () => {
    if (!currentLocation) {
      voiceInteractionManager.speak('Location not available yet.');
      return;
    }

    try {
      const address = await Location.reverseGeocodeAsync({
        latitude: currentLocation.coords.latitude,
        longitude: currentLocation.coords.longitude,
      });

      if (address && address.length > 0) {
        const loc = address[0];
        voiceInteractionManager.speak(
          `You are near ${loc.street || loc.name}, ${loc.city}, ${loc.region}`
        );
      }
    } catch (error) {
      voiceInteractionManager.speak('Could not determine current address.');
    }
  };

  const checkTrafficStatus = async () => {
    if (!destination) {
      voiceInteractionManager.speak('No active route to check traffic.');
      return;
    }

    const status = await drivingAssistantService.getTrafficStatus();
    voiceInteractionManager.speak(status.summary);
  };

  const handleEmergency = () => {
    Alert.alert(
      'Emergency',
      'Call 911?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Call',
          style: 'destructive',
          onPress: () => {
            if (Platform.OS === 'ios') {
              // Linking.openURL('tel:911');
            }
          },
        },
      ],
      { cancelable: false }
    );
  };

  // UI handlers
  const handleVoiceButtonPress = () => {
    if (isListening) {
      voiceInteractionManager.stopListening();
    } else {
      voiceInteractionManager.startListening();
    }
  };

  const handleConfirm = () => {
    setShowConfirmation(false);
    voiceInteractionManager.confirmAction();
  };

  const handleCancel = () => {
    setShowConfirmation(false);
    voiceInteractionManager.cancelAction();
  };

  const formatActionDisplay = (action: string): string => {
    const displays: Record<string, string> = {
      NAVIGATE_TO: 'Starting navigation',
      FIND_GAS_STATION: 'Finding gas stations',
      FIND_REST_STOP: 'Finding rest stops',
      STOP_NAVIGATION: 'Stopping navigation',
      PAUSE_NARRATION: 'Pausing',
      RESUME_NARRATION: 'Resuming',
      START_STORY: 'Starting story',
      START_TRIVIA: 'Starting trivia',
    };

    return displays[action] || action;
  };

  return (
    <View style={styles.container}>
      <KeepAwake />
      
      {/* Map View */}
      <MapView
        ref={mapRef}
        style={styles.map}
        provider={PROVIDER_GOOGLE}
        showsUserLocation
        showsMyLocationButton={false}
        showsCompass={false}
        initialRegion={
          currentLocation
            ? {
                latitude: currentLocation.coords.latitude,
                longitude: currentLocation.coords.longitude,
                latitudeDelta: 0.0922,
                longitudeDelta: 0.0421,
              }
            : undefined
        }
      >
        {/* Route polyline */}
        {routeCoordinates.length > 0 && (
          <Polyline
            coordinates={routeCoordinates}
            strokeColor="#007AFF"
            strokeWidth={4}
          />
        )}

        {/* Destination marker */}
        {destination && routeCoordinates.length > 0 && (
          <Marker
            coordinate={routeCoordinates[routeCoordinates.length - 1]}
            title="Destination"
            description={destination}
          />
        )}
      </MapView>

      {/* Voice-First Interface Overlay */}
      <View style={[styles.overlay, { paddingTop: insets.top }]}>
        <VoiceFirstInterface
          isListening={isListening}
          onVoiceButtonPress={handleVoiceButtonPress}
          currentAction={currentAction}
          showConfirmation={showConfirmation}
          onConfirm={handleConfirm}
          onCancel={handleCancel}
          voiceLevel={voiceLevel}
          isDriving={isDriving}
        />
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  map: {
    flex: 1,
  },
  overlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    pointerEvents: 'box-none',
  },
});