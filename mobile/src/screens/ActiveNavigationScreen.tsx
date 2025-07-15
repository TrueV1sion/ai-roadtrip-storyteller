import React, { useState, useEffect, useCallback, useRef } from 'react';
import { View, StyleSheet, Alert, AppState, Platform } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Audio } from 'expo-av';
import * as TaskManager from 'expo-task-manager';
import * as Location from 'expo-location';
import * as BackgroundFetch from 'expo-background-fetch';

import { NavigationMap } from '../components/NavigationMap';
import { NavigationVoiceController } from '../components/NavigationVoiceController';
import { navigationService } from '../services/navigationService';
import { navigationVoiceService } from '../services/navigationVoiceService';
import { backgroundNavigationService } from '../services/backgroundNavigationService';
import { audioOrchestrationService } from '../services/audio/audioOrchestrationService';
import audioPlaybackService from '../services/audioPlaybackService';
import { useNavigation } from '../hooks/useNavigation';
import { useStory } from '../hooks/useStory';

const LOCATION_TASK_NAME = 'background-location-task';
const NAVIGATION_UPDATE_TASK = 'navigation-update-task';

interface ActiveNavigationScreenProps {
  route: {
    params: {
      directions: any; // Google Directions response
      destination: any;
      tripId: string;
    };
  };
}

export const ActiveNavigationScreen: React.FC<ActiveNavigationScreenProps> = ({ route }) => {
  const { directions, destination, tripId } = route.params;
  const insets = useSafeAreaInsets();
  const navigation = useNavigation();
  const { currentStory, isPlaying } = useStory();
  
  // Navigation state
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [distanceToNextManeuver, setDistanceToNextManeuver] = useState(0);
  const [timeToNextManeuver, setTimeToNextManeuver] = useState(0);
  const [currentSpeed, setCurrentSpeed] = useState(0);
  const [isOnHighway, setIsOnHighway] = useState(false);
  const [lastInstructionTime, setLastInstructionTime] = useState<Date | null>(null);
  
  // Audio state
  const [audioFocus, setAudioFocus] = useState<'navigation' | 'story'>('navigation');
  const [navigationVolume, setNavigationVolume] = useState(1.0);
  const [storyVolume, setStoryVolume] = useState(0.3); // Ducked by default
  
  // Refs
  const updateIntervalRef = useRef<NodeJS.Timeout>();
  const appStateRef = useRef(AppState.currentState);

  useEffect(() => {
    initializeNavigation();
    
    // Handle app state changes
    const appStateSubscription = AppState.addEventListener('change', handleAppStateChange);
    
    return () => {
      cleanup();
      appStateSubscription.remove();
    };
  }, []);

  const initializeNavigation = async () => {
    try {
      // Start navigation on backend
      const result = await navigationService.startNavigation({
        route: directions.routes[0],
        currentLocation: await getCurrentLocation(),
        destination,
        navigationPreferences: {
          voice_personality: 'professional',
          verbosity: 'detailed',
          audio_priority: 'safety_first'
        }
      });

      if (result.status === 'success') {
        // Initialize navigation voice service
        await navigationVoiceService.initializeForRoute(
          result.route_id,
          directions.routes[0]
        );
        
        // Configure audio orchestration
        audioOrchestrationService.updateConfig({
          audioPriority: 'navigation',
          duckingEnabled: true,
          crossfadeEnabled: true
        });
        
        // Initialize background navigation
        await backgroundNavigationService.initialize(
          result.route_id,
          directions.routes[0]
        );
        
        // Start position updates
        startPositionUpdates();
        
        // Configure audio session for navigation
        await configureAudioForNavigation();
      }
    } catch (error) {
      console.error('Failed to initialize navigation:', error);
      Alert.alert('Navigation Error', 'Failed to start navigation');
    }
  };

  const configureAudioForNavigation = async () => {
    try {
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: false,
        staysActiveInBackground: true,
        interruptionModeIOS: Audio.INTERRUPTION_MODE_IOS_DO_NOT_MIX,
        playsInSilentModeIOS: true,
        shouldDuckAndroid: true,
        interruptionModeAndroid: Audio.INTERRUPTION_MODE_ANDROID_DO_NOT_MIX,
        playThroughEarpieceAndroid: false,
      });
    } catch (error) {
      console.error('Failed to configure audio:', error);
    }
  };

  const startPositionUpdates = () => {
    // Update every 2 seconds when app is active
    updateIntervalRef.current = setInterval(async () => {
      await updateNavigationState();
    }, 2000);
  };

  const updateNavigationState = async () => {
    try {
      const location = await getCurrentLocation();
      
      // Calculate navigation metrics
      const metrics = calculateNavigationMetrics(location);
      
      // Update local state
      setDistanceToNextManeuver(metrics.distanceToNextManeuver);
      setTimeToNextManeuver(metrics.timeToNextManeuver);
      setCurrentSpeed(metrics.currentSpeed);
      setIsOnHighway(metrics.isOnHighway);
      
      // Check if we need to advance to next step
      if (metrics.shouldAdvanceStep) {
        const nextStepIndex = currentStepIndex + 1;
        setCurrentStepIndex(nextStepIndex);
        navigationService.setCurrentStepIndex(nextStepIndex);
        
        // Update background navigation state
        await backgroundNavigationService.updateState(nextStepIndex);
      }
      
      // Request navigation instruction from backend
      const instructionResponse = await navigationService.updateNavigation(location, {
        currentStepIndex,
        distanceToNextManeuver: metrics.distanceToNextManeuver,
        timeToNextManeuver: metrics.timeToNextManeuver,
        isOnHighway: metrics.isOnHighway,
        approachingComplexIntersection: metrics.approachingComplexIntersection,
        storyPlaying: isPlaying,
        audioPriority: 'safety_first'
      });
      
      // Handle navigation instruction for UI updates
      if (instructionResponse.has_instruction) {
        await handleNavigationInstruction(instructionResponse);
        setLastInstructionTime(new Date());
      }
    } catch (error) {
      console.error('Failed to update navigation:', error);
    }
  };

  const handleNavigationInstruction = async (instruction: any) => {
    // Update last instruction time
    setLastInstructionTime(new Date());
    
    // Use the enhanced audio orchestration
    await audioPlaybackService.handleNavigationInstruction(
      instruction.audio_url,
      instruction.orchestration_action,
      instruction.audio_duration || 5
    );
  };


  const handleAppStateChange = (nextAppState: any) => {
    if (appStateRef.current.match(/inactive|background/) && nextAppState === 'active') {
      // App came to foreground
      startPositionUpdates();
    } else if (appStateRef.current === 'active' && nextAppState.match(/inactive|background/)) {
      // App went to background
      if (updateIntervalRef.current) {
        clearInterval(updateIntervalRef.current);
      }
    }
    appStateRef.current = nextAppState;
  };


  const cleanup = async () => {
    // Stop position updates
    if (updateIntervalRef.current) {
      clearInterval(updateIntervalRef.current);
    }
    
    // Stop navigation voice
    await navigationVoiceService.stop();
    
    // Clean up audio orchestration
    await audioOrchestrationService.cleanup();
    
    // Stop background navigation
    await backgroundNavigationService.stop();
    
    // Stop navigation
    await navigationService.stopNavigation();
  };

  const getCurrentLocation = async () => {
    return await Location.getCurrentPositionAsync({
      accuracy: Location.Accuracy.BestForNavigation,
    });
  };

  const calculateNavigationMetrics = (location: any) => {
    const route = directions.routes[0];
    const currentLeg = route.legs[0];
    
    if (currentStepIndex >= currentLeg.steps.length) {
      // Reached destination
      return {
        distanceToNextManeuver: 0,
        timeToNextManeuver: 0,
        currentSpeed: location.coords.speed || 0,
        isOnHighway: false,
        approachingComplexIntersection: false,
        shouldAdvanceStep: false,
      };
    }
    
    const currentStep = currentLeg.steps[currentStepIndex];
    const nextManeuverLocation = currentStep.end_location || currentStep.start_location;
    
    // Calculate distance to next maneuver
    const distance = navigationService.calculateDistance(
      location.coords.latitude,
      location.coords.longitude,
      nextManeuverLocation.lat,
      nextManeuverLocation.lng
    );
    
    // Calculate time based on current speed (m/s to minutes)
    const speedMs = location.coords.speed || 13.4; // Default ~30mph if no speed
    const timeSeconds = distance / speedMs;
    
    // Check if we should advance to next step (within 30 meters of maneuver)
    const shouldAdvance = distance < 30;
    
    // Detect highway
    const isHighway = navigationService.detectHighway(currentStep);
    
    // Detect complex intersection (roundabouts, multi-lane turns)
    const complexManeuvers = ['roundabout', 'fork', 'merge', 'keep'];
    const isComplex = currentStep.maneuver && 
      complexManeuvers.some(m => currentStep.maneuver.includes(m));
    
    return {
      distanceToNextManeuver: distance,
      timeToNextManeuver: timeSeconds,
      currentSpeed: speedMs,
      isOnHighway: isHighway,
      approachingComplexIntersection: isComplex && distance < 200,
      shouldAdvanceStep: shouldAdvance,
    };
  };

  const handleNavigationUpdate = useCallback((update: any) => {
    // Handle updates from the map component
    console.log('Navigation update:', update);
  }, []);

  return (
    <View style={styles.container}>
      <NavigationMap
        route={directions.routes[0]}
        currentStepIndex={currentStepIndex}
        distanceToNextManeuver={distanceToNextManeuver}
        timeToNextManeuver={timeToNextManeuver}
        currentSpeed={currentSpeed}
        onNavigationUpdate={handleNavigationUpdate}
      />
      
      <NavigationVoiceController
        navigationVolume={navigationVolume}
        storyVolume={storyVolume}
        audioFocus={audioFocus}
        onVolumeChange={(nav, story) => {
          setNavigationVolume(nav);
          setStoryVolume(story);
        }}
        onFocusChange={setAudioFocus}
      />
    </View>
  );
};

// Background task is now defined in backgroundNavigationService.ts

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
});