import React, { useState, useEffect, useRef } from 'react';
import { logger } from '@/services/logger';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Platform,
  Animated,
  SafeAreaView,
} from 'react-native';
import MapView, { Marker, Polyline, PROVIDER_GOOGLE } from 'react-native-maps';
import { Audio } from 'expo-av';
import { Ionicons } from '@expo/vector-icons';

// Services
import { locationService } from '../services/locationService';
import { voiceRecognitionService } from '../services/voiceRecognitionService';
import { voiceAssistantService } from '../services/voiceAssistantService';

// Types
interface Location {
  latitude: number;
  longitude: number;
}

interface RouteInfo {
  origin: Location;
  destination: Location;
  polylinePoints: Location[];
  duration: number;
  distance: number;
}

const SimpleMVPNavigationScreen: React.FC = () => {
  // State
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentLocation, setCurrentLocation] = useState<Location | null>(null);
  const [routeInfo, setRouteInfo] = useState<RouteInfo | null>(null);
  const [storyText, setStoryText] = useState<string>('');
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  
  // Refs
  const mapRef = useRef<MapView>(null);
  const soundRef = useRef<Audio.Sound | null>(null);
  const fadeAnim = useRef(new Animated.Value(0)).current;
  
  // Initialize location tracking
  useEffect(() => {
    let watchId: number;
    
    const startLocationTracking = async () => {
      const hasPermission = await locationService.initialize();
      if (!hasPermission) {
        Alert.alert(
          'Location Required',
          'This app needs location access to provide navigation and stories.'
        );
        return;
      }
      
      // Get initial location
      const location = await locationService.getCurrentLocation();
      if (location) {
        setCurrentLocation({
          latitude: location.latitude,
          longitude: location.longitude,
        });
      }
      
      // Watch location changes
      watchId = await locationService.watchLocation((location) => {
        setCurrentLocation({
          latitude: location.latitude,
          longitude: location.longitude,
        });
      });
    };
    
    startLocationTracking();
    
    // Cleanup
    return () => {
      if (watchId !== undefined) {
        locationService.clearWatch(watchId);
      }
    };
  }, []);
  
  // Initialize voice recognition
  useEffect(() => {
    voiceRecognitionService.initialize();
    
    return () => {
      voiceRecognitionService.destroy();
    };
  }, []);
  
  // Handle voice input
  const handleVoiceInput = async (input: string) => {
    setIsListening(false);
    setIsProcessing(true);
    setStoryText('Processing your request...');
    
    // Fade in the story text
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 300,
      useNativeDriver: true,
    }).start();
    
    try {
      // Send to backend
      const response = await voiceAssistantService.processVoiceCommand(input, {
        location: currentLocation,
        routeInfo: routeInfo,
      });
      
      if (response.success) {
        // Update story text
        setStoryText(response.text || '');
        
        // Play audio if available
        if (response.audioUrl) {
          setAudioUrl(response.audioUrl);
          await playAudio(response.audioUrl);
        }
        
        // Update route if navigation response
        if (response.routeInfo) {
          setRouteInfo(response.routeInfo);
          fitMapToRoute(response.routeInfo);
        }
      } else {
        Alert.alert('Error', 'Failed to process your request. Please try again.');
      }
    } catch (error) {
      logger.error('Error processing voice input:', error);
      Alert.alert('Error', 'Something went wrong. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };
  
  // Play audio from URL
  const playAudio = async (url: string) => {
    try {
      // Stop previous audio if playing
      if (soundRef.current) {
        await soundRef.current.unloadAsync();
      }
      
      // Load and play new audio
      const { sound } = await Audio.Sound.createAsync(
        { uri: url },
        { shouldPlay: true }
      );
      soundRef.current = sound;
      
      // Clean up when finished
      sound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded && status.didJustFinish) {
          sound.unloadAsync();
        }
      });
    } catch (error) {
      logger.error('Error playing audio:', error);
    }
  };
  
  // Fit map to show route
  const fitMapToRoute = (route: RouteInfo) => {
    if (mapRef.current) {
      const coordinates = [route.origin, route.destination];
      mapRef.current.fitToCoordinates(coordinates, {
        edgePadding: { top: 100, right: 50, bottom: 200, left: 50 },
        animated: true,
      });
    }
  };
  
  // Toggle voice listening
  const toggleListening = async () => {
    if (isListening) {
      await voiceRecognitionService.stopListening();
      setIsListening(false);
    } else {
      setIsListening(true);
      try {
        await voiceRecognitionService.startListening(
          {
            language: 'en-US',
            showPartialResults: true,
          },
          {
            onResults: (results) => {
              if (results && results.length > 0) {
                handleVoiceInput(results[0]);
              }
            },
            onError: (error) => {
              logger.error('Voice recognition error:', error);
              setIsListening(false);
              Alert.alert('Error', 'Voice recognition failed. Please try again.');
            },
            onEnd: () => {
              setIsListening(false);
            },
          }
        );
      } catch (error) {
        logger.error('Error starting voice recognition:', error);
        setIsListening(false);
        Alert.alert('Error', 'Failed to start voice recognition.');
      }
    }
  };
  
  // Stop audio playback
  const stopAudio = async () => {
    if (soundRef.current) {
      await soundRef.current.stopAsync();
      await soundRef.current.unloadAsync();
      soundRef.current = null;
    }
  };
  
  return (
    <SafeAreaView style={styles.container}>
      {/* Map View */}
      <MapView
        ref={mapRef}
        style={styles.map}
        provider={PROVIDER_GOOGLE}
        showsUserLocation
        followsUserLocation
        showsMyLocationButton={false}
        initialRegion={
          currentLocation
            ? {
                ...currentLocation,
                latitudeDelta: 0.0922,
                longitudeDelta: 0.0421,
              }
            : undefined
        }
      >
        {/* Route polyline */}
        {routeInfo && (
          <>
            <Polyline
              coordinates={routeInfo.polylinePoints}
              strokeColor="#007AFF"
              strokeWidth={4}
            />
            <Marker coordinate={routeInfo.destination} />
          </>
        )}
      </MapView>
      
      {/* Story/Response Panel */}
      {storyText !== '' && (
        <Animated.View
          style={[
            styles.storyPanel,
            {
              opacity: fadeAnim,
              transform: [{
                translateY: fadeAnim.interpolate({
                  inputRange: [0, 1],
                  outputRange: [20, 0],
                }),
              }],
            },
          ]}
        >
          <Text style={styles.storyText}>{storyText}</Text>
          {audioUrl && (
            <TouchableOpacity
              style={styles.audioButton}
              onPress={stopAudio}
            >
              <Ionicons name="stop-circle" size={24} color="#007AFF" />
            </TouchableOpacity>
          )}
        </Animated.View>
      )}
      
      {/* Voice Control Button */}
      <View style={styles.controlsContainer}>
        <TouchableOpacity
          style={[
            styles.voiceButton,
            isListening && styles.voiceButtonActive,
            isProcessing && styles.voiceButtonProcessing,
          ]}
          onPress={toggleListening}
          disabled={isProcessing}
        >
          {isProcessing ? (
            <ActivityIndicator size="large" color="#FFFFFF" />
          ) : (
            <Ionicons
              name={isListening ? 'mic' : 'mic-outline'}
              size={32}
              color="#FFFFFF"
            />
          )}
        </TouchableOpacity>
        
        {isListening && (
          <Text style={styles.listeningText}>Listening...</Text>
        )}
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  map: {
    flex: 1,
  },
  storyPanel: {
    position: 'absolute',
    top: Platform.OS === 'ios' ? 60 : 40,
    left: 20,
    right: 20,
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    borderRadius: 16,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 5,
    maxHeight: '30%',
  },
  storyText: {
    fontSize: 16,
    lineHeight: 24,
    color: '#333333',
  },
  audioButton: {
    position: 'absolute',
    top: 12,
    right: 12,
  },
  controlsContainer: {
    position: 'absolute',
    bottom: 40,
    alignSelf: 'center',
    alignItems: 'center',
  },
  voiceButton: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: '#007AFF',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 5,
  },
  voiceButtonActive: {
    backgroundColor: '#FF3B30',
    transform: [{ scale: 1.1 }],
  },
  voiceButtonProcessing: {
    backgroundColor: '#8E8E93',
  },
  listeningText: {
    marginTop: 8,
    fontSize: 14,
    color: '#666666',
    fontWeight: '500',
  },
});

export default SimpleMVPNavigationScreen;