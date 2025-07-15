/**
 * AR Camera View Component
 * Main AR interface with safety features for automotive use
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  Alert,
  Platform,
  Dimensions,
} from 'react-native';
import {
  Camera,
  useCameraDevice,
  useCameraPermission,
  useFrameProcessor,
  Frame,
} from 'react-native-vision-camera';
import {
  Canvas,
  useCanvasRef,
  Picture,
  Skia,
} from '@shopify/react-native-skia';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withTiming,
  withSpring,
  runOnJS,
} from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';

// Services
import { arCameraService } from '../../services/ar/ARCameraService';
import { arLandmarkService } from '../../services/ar/ARLandmarkService';
import { arOverlayRenderer } from '../../services/ar/AROverlayRenderer';
import { voiceOrchestrationService } from '../../services/voiceOrchestrationService';
import { locationService } from '../../services/locationService';
import { vehicleMonitoringService } from '../../services/vehicleMonitoringService';

// Components
import { ARSafetyOverlay } from './ARSafetyOverlay';
import { ARLandmarkOverlay } from './ARLandmarkOverlay';
import { ARControlPanel } from './ARControlPanel';
import { LoadingView } from '../common/LoadingView';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

interface ARCameraViewProps {
  onClose?: () => void;
  initialMode?: 'landmark' | 'navigation' | 'game' | 'photo';
  voiceEnabled?: boolean;
}

export const ARCameraView: React.FC<ARCameraViewProps> = ({
  onClose,
  initialMode = 'landmark',
  voiceEnabled = true,
}) => {
  const navigation = useNavigation();
  const insets = useSafeAreaInsets();
  const canvasRef = useCanvasRef();
  
  // Camera setup
  const device = useCameraDevice('back');
  const { hasPermission, requestPermission } = useCameraPermission();
  const cameraRef = useRef<Camera>(null);
  
  // State
  const [isInitialized, setIsInitialized] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [arMode, setArMode] = useState(initialMode);
  const [isProcessing, setIsProcessing] = useState(false);
  const [vehicleSpeed, setVehicleSpeed] = useState(0);
  const [landmarks, setLandmarks] = useState([]);
  const [safetyWarning, setSafetyWarning] = useState<string | null>(null);
  
  // Shared values for animations
  const overlayOpacity = useSharedValue(1);
  const controlsVisible = useSharedValue(1);
  const safetyMode = useSharedValue(false);
  
  // Initialize AR system
  useEffect(() => {
    initializeAR();
    
    return () => {
      cleanup();
    };
  }, []);
  
  // Monitor vehicle speed for safety
  useEffect(() => {
    const speedSubscription = vehicleMonitoringService.subscribeToSpeed((speed) => {
      setVehicleSpeed(speed);
      
      // Safety thresholds
      if (speed > 80) {
        // Disable AR above 80 mph
        setSafetyWarning('AR disabled at high speed');
        safetyMode.value = true;
      } else if (speed > 50) {
        // Simplify AR above 50 mph
        setSafetyWarning('AR simplified for safety');
        safetyMode.value = true;
      } else {
        setSafetyWarning(null);
        safetyMode.value = false;
      }
    });
    
    return () => {
      speedSubscription.unsubscribe();
    };
  }, []);
  
  /**
   * Initialize AR system
   */
  const initializeAR = async () => {
    try {
      // Check permissions
      if (!hasPermission) {
        const granted = await requestPermission();
        if (granted !== 'granted') {
          Alert.alert(
            'Camera Permission Required',
            'AR features require camera access.',
            [{ text: 'OK', onPress: () => navigation.goBack() }]
          );
          return;
        }
      }
      
      // Initialize AR services
      const initialized = await arCameraService.initialize();
      if (!initialized) {
        Alert.alert(
          'AR Not Supported',
          'Your device does not support AR features.',
          [{ text: 'OK', onPress: () => navigation.goBack() }]
        );
        return;
      }
      
      // Initialize landmark service
      await arLandmarkService.initialize({
        maxDistance: 1000,
        enableVoiceDescriptions: voiceEnabled,
      });
      
      // Initialize overlay renderer
      arOverlayRenderer.initialize({
        performanceMode: 'balanced',
        maxOverlays: 10,
      });
      
      // Start AR session
      await arCameraService.startSession({
        quality: 'medium',
        targetFPS: 30,
        enableLandmarkDetection: true,
      });
      
      setIsInitialized(true);
      setIsLoading(false);
      
      // Voice announcement
      if (voiceEnabled) {
        voiceOrchestrationService.speak(
          'AR view activated. Point your camera at landmarks to learn more.',
          { priority: 'high' }
        );
      }
    } catch (error) {
      console.error('AR initialization failed:', error);
      Alert.alert('AR Error', 'Failed to initialize AR features.');
      navigation.goBack();
    }
  };
  
  /**
   * Cleanup AR resources
   */
  const cleanup = async () => {
    await arCameraService.stopSession();
    arOverlayRenderer.clearOverlays();
  };
  
  /**
   * Frame processor for AR
   */
  const frameProcessor = useFrameProcessor((frame: Frame) => {
    'worklet';
    
    // Skip if in safety mode
    if (safetyMode.value) return;
    
    // Process frame for AR
    arCameraService.processFrame(frame);
  }, []);
  
  /**
   * Update landmarks periodically
   */
  useEffect(() => {
    if (!isInitialized) return;
    
    const updateInterval = setInterval(async () => {
      try {
        const location = await locationService.getCurrentLocation();
        const orientation = await deviceOrientationService.getOrientation();
        
        const updatedLandmarks = await arLandmarkService.updateLandmarks(
          location,
          orientation,
          { width: SCREEN_WIDTH, height: SCREEN_HEIGHT }
        );
        
        setLandmarks(updatedLandmarks);
        
        // Update overlay positions
        arOverlayRenderer.updateOverlayPositions(updatedLandmarks);
      } catch (error) {
        console.error('Failed to update landmarks:', error);
      }
    }, 1000);
    
    return () => clearInterval(updateInterval);
  }, [isInitialized]);
  
  /**
   * Handle landmark tap
   */
  const handleLandmarkTap = useCallback(async (landmark) => {
    if (voiceEnabled) {
      // Request more information via voice
      const prompt = `Tell me more about ${landmark.name}`;
      await voiceOrchestrationService.processVoiceCommand(prompt, {
        context: { landmark, mode: 'ar' },
      });
    } else {
      // Show info modal
      navigation.navigate('LandmarkDetails', { landmark });
    }
  }, [voiceEnabled, navigation]);
  
  /**
   * Handle AR photo capture
   */
  const handlePhotoCapture = useCallback(async () => {
    setIsProcessing(true);
    
    try {
      const photoPath = await arCameraService.captureARPhoto();
      if (photoPath) {
        // Navigate to photo review
        navigation.navigate('ARPhotoReview', { photoPath, landmarks });
      }
    } catch (error) {
      console.error('Photo capture failed:', error);
      Alert.alert('Error', 'Failed to capture AR photo');
    } finally {
      setIsProcessing(false);
    }
  }, [navigation, landmarks]);
  
  /**
   * Handle mode switch
   */
  const handleModeSwitch = useCallback((newMode: string) => {
    setArMode(newMode);
    
    // Update AR configuration
    switch (newMode) {
      case 'landmark':
        arLandmarkService.setHistoricalMode(false);
        break;
      case 'historical':
        arLandmarkService.setHistoricalMode(true);
        break;
      case 'game':
        navigation.navigate('ARGames');
        break;
    }
  }, [navigation]);
  
  /**
   * Toggle controls visibility
   */
  const toggleControls = useCallback(() => {
    controlsVisible.value = withTiming(controlsVisible.value === 1 ? 0 : 1);
  }, []);
  
  // Animated styles
  const overlayAnimatedStyle = useAnimatedStyle(() => ({
    opacity: overlayOpacity.value,
  }));
  
  const controlsAnimatedStyle = useAnimatedStyle(() => ({
    opacity: controlsVisible.value,
    transform: [
      {
        translateY: withSpring(controlsVisible.value === 1 ? 0 : 100),
      },
    ],
  }));
  
  // Loading state
  if (isLoading) {
    return <LoadingView message="Initializing AR..." />;
  }
  
  // No camera device
  if (!device) {
    return (
      <View style={styles.container}>
        <Text style={styles.errorText}>No camera device available</Text>
        <TouchableOpacity style={styles.button} onPress={() => navigation.goBack()}>
          <Text style={styles.buttonText}>Go Back</Text>
        </TouchableOpacity>
      </View>
    );
  }
  
  return (
    <View style={styles.container}>
      {/* Camera View */}
      <Camera
        ref={cameraRef}
        style={StyleSheet.absoluteFill}
        device={device}
        isActive={!safetyMode.value}
        frameProcessor={frameProcessor}
        fps={30}
        enableZoomGesture
        photo
      />
      
      {/* AR Canvas Overlay */}
      <Canvas
        ref={canvasRef}
        style={StyleSheet.absoluteFill}
        mode="continuous"
      >
        <Picture
          picture={arOverlayRenderer.renderOverlays}
        />
      </Canvas>
      
      {/* Safety Overlay */}
      <ARSafetyOverlay
        vehicleSpeed={vehicleSpeed}
        safetyWarning={safetyWarning}
        visible={safetyMode.value}
      />
      
      {/* Landmark Overlays */}
      <Animated.View style={[StyleSheet.absoluteFill, overlayAnimatedStyle]}>
        {landmarks.map((landmark) => (
          <ARLandmarkOverlay
            key={landmark.id}
            landmark={landmark}
            onPress={() => handleLandmarkTap(landmark)}
          />
        ))}
      </Animated.View>
      
      {/* Touch to toggle controls */}
      <TouchableOpacity
        style={StyleSheet.absoluteFill}
        activeOpacity={1}
        onPress={toggleControls}
      />
      
      {/* Control Panel */}
      <Animated.View
        style={[
          styles.controlPanel,
          { paddingBottom: insets.bottom + 20 },
          controlsAnimatedStyle,
        ]}
      >
        <ARControlPanel
          mode={arMode}
          onModeChange={handleModeSwitch}
          onPhotoCapture={handlePhotoCapture}
          onClose={onClose}
          isProcessing={isProcessing}
          voiceEnabled={voiceEnabled}
        />
      </Animated.View>
      
      {/* Top Bar */}
      <View style={[styles.topBar, { paddingTop: insets.top + 10 }]}>
        <TouchableOpacity
          style={styles.closeButton}
          onPress={() => {
            cleanup();
            onClose?.();
          }}
        >
          <Text style={styles.closeButtonText}>×</Text>
        </TouchableOpacity>
        
        <View style={styles.modeIndicator}>
          <Text style={styles.modeText}>
            {arMode.charAt(0).toUpperCase() + arMode.slice(1)} Mode
          </Text>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  errorText: {
    color: '#fff',
    fontSize: 18,
    textAlign: 'center',
    marginBottom: 20,
  },
  button: {
    backgroundColor: '#2E86AB',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
    alignSelf: 'center',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  topBar: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
  },
  closeButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  closeButtonText: {
    color: '#fff',
    fontSize: 28,
    fontWeight: '300',
  },
  modeIndicator: {
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
  },
  modeText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  controlPanel: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    paddingTop: 20,
  },
});
