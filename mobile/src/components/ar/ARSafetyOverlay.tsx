import React, { useEffect, useRef, useState } from 'react';
import {
  View,
  StyleSheet,
  Animated,
  Text,
  Dimensions,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useAppContext } from '../../contexts/AppContext';

interface ARSafetyOverlayProps {
  children: React.ReactNode;
  vehicleSpeed: number;
  isDriverSide: boolean;
  weatherCondition: 'clear' | 'rain' | 'fog' | 'snow';
  timeOfDay: 'day' | 'night' | 'twilight';
  passengerAge: 'adult' | 'child';
  onSafetyOverride?: (reason: string) => void;
}

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

const ARSafetyOverlay: React.FC<ARSafetyOverlayProps> = ({
  children,
  vehicleSpeed,
  isDriverSide,
  weatherCondition,
  timeOfDay,
  passengerAge,
  onSafetyOverride,
}) => {
  const insets = useSafeAreaInsets();
  const fadeAnim = useRef(new Animated.Value(1)).current;
  const [safetyMode, setSafetyMode] = useState<'full' | 'reduced' | 'minimal' | 'hidden'>('full');
  const [brightnessMultiplier, setBrightnessMultiplier] = useState(1);

  // Speed-based safety thresholds
  const SPEED_THRESHOLDS = {
    full: 30,     // mph - All AR features
    reduced: 50,  // Simplified AR
    minimal: 70,  // Critical info only
    hidden: 80    // No AR
  };

  // Calculate safety mode based on conditions
  useEffect(() => {
    let mode: 'full' | 'reduced' | 'minimal' | 'hidden' = 'full';
    let brightness = 1;

    // Speed-based mode
    if (vehicleSpeed >= SPEED_THRESHOLDS.hidden) {
      mode = 'hidden';
    } else if (vehicleSpeed >= SPEED_THRESHOLDS.minimal) {
      mode = 'minimal';
    } else if (vehicleSpeed >= SPEED_THRESHOLDS.reduced) {
      mode = 'reduced';
    }

    // Weather adjustments
    if (weatherCondition !== 'clear') {
      if (mode === 'full') mode = 'reduced';
      if (weatherCondition === 'fog') brightness *= 0.5;
      if (weatherCondition === 'rain') brightness *= 0.7;
      if (weatherCondition === 'snow') brightness *= 0.6;
    }

    // Time of day adjustments
    if (timeOfDay === 'night') {
      brightness *= 0.6;
      if (mode === 'full') mode = 'reduced';
    } else if (timeOfDay === 'twilight') {
      brightness *= 0.8;
    }

    // Never show AR to driver
    if (isDriverSide) {
      mode = 'hidden';
      onSafetyOverride?.('AR disabled for driver safety');
    }

    setSafetyMode(mode);
    setBrightnessMultiplier(brightness);

    // Animate visibility changes
    Animated.timing(fadeAnim, {
      toValue: mode === 'hidden' ? 0 : 1,
      duration: mode === 'hidden' ? 500 : 2000, // Fast hide, slow show
      useNativeDriver: true,
    }).start();
  }, [vehicleSpeed, isDriverSide, weatherCondition, timeOfDay, fadeAnim, onSafetyOverride]);

  // Emergency hide function
  const emergencyHide = () => {
    Animated.timing(fadeAnim, {
      toValue: 0,
      duration: 0, // Instant
      useNativeDriver: true,
    }).start();
    onSafetyOverride?.('Emergency AR shutdown');
  };

  // Viewport coverage limiter
  const getMaxViewportCoverage = () => {
    switch (safetyMode) {
      case 'full': return 0.3; // 30% max coverage
      case 'reduced': return 0.2; // 20% max coverage
      case 'minimal': return 0.1; // 10% max coverage
      case 'hidden': return 0;
      default: return 0.3;
    }
  };

  return (
    <View style={styles.container}>
      <Animated.View
        style={[
          styles.arContainer,
          {
            opacity: fadeAnim,
            maxHeight: SCREEN_HEIGHT * getMaxViewportCoverage(),
          },
        ]}
      >
        {/* Brightness adjustment overlay */}
        <View
          style={[
            styles.brightnessOverlay,
            { opacity: 1 - brightnessMultiplier },
          ]}
          pointerEvents="none"
        />

        {/* Safety indicators */}
        {safetyMode !== 'full' && safetyMode !== 'hidden' && (
          <View style={[styles.safetyIndicator, { top: insets.top + 10 }]}>
            <Text style={styles.safetyText}>
              AR {safetyMode === 'minimal' ? 'Minimal' : 'Reduced'} Mode
            </Text>
          </View>
        )}

        {/* Child mode indicator */}
        {passengerAge === 'child' && (
          <View style={[styles.childModeIndicator, { top: insets.top + 10, right: 10 }]}>
            <Text style={styles.childModeText}>👶 Child Mode</Text>
          </View>
        )}

        {/* AR Content with safety constraints */}
        <View style={styles.contentWrapper}>
          {safetyMode !== 'hidden' && children}
        </View>
      </Animated.View>

      {/* Emergency override zone - always visible */}
      <View style={[styles.emergencyZone, { top: insets.top }]} />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  arContainer: {
    flex: 1,
    overflow: 'hidden',
  },
  brightnessOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'black',
    pointerEvents: 'none',
  },
  contentWrapper: {
    flex: 1,
  },
  safetyIndicator: {
    position: 'absolute',
    left: 10,
    backgroundColor: 'rgba(255, 149, 0, 0.9)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 15,
    zIndex: 1000,
  },
  safetyText: {
    color: 'white',
    fontSize: 12,
    fontWeight: 'bold',
  },
  childModeIndicator: {
    position: 'absolute',
    backgroundColor: 'rgba(52, 199, 89, 0.9)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 15,
    zIndex: 1000,
  },
  childModeText: {
    color: 'white',
    fontSize: 12,
    fontWeight: 'bold',
  },
  emergencyZone: {
    position: 'absolute',
    left: 0,
    right: 0,
    height: 50,
    zIndex: 9999,
  },
});

export default ARSafetyOverlay;