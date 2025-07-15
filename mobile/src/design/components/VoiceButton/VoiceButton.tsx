/**
 * VoiceButton Component
 * Primary interaction point with Aurora-themed animations
 */

import React, { useEffect } from 'react';
import {
  TouchableOpacity,
  View,
  StyleSheet,
  Text,
  Platform,
  Vibration,
} from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withTiming,
  withSequence,
  interpolate,
  Extrapolate,
  withSpring,
  runOnJS,
} from 'react-native-reanimated';
import { LinearGradient } from 'expo-linear-gradient';
import Svg, { Path } from 'react-native-svg';
import { lightTheme as theme } from '../../theme';

interface VoiceButtonProps {
  isListening: boolean;
  onPress: () => void;
  size?: number;
  disabled?: boolean;
  transcript?: string;
}

const AnimatedLinearGradient = Animated.createAnimatedComponent(LinearGradient);

export const VoiceButton: React.FC<VoiceButtonProps> = ({
  isListening,
  onPress,
  size = 80,
  disabled = false,
  transcript,
}) => {
  // Animation values
  const scale = useSharedValue(1);
  const rotation = useSharedValue(0);
  const pulseScale = useSharedValue(1);
  const pulseOpacity = useSharedValue(0);
  const glowIntensity = useSharedValue(0);

  // Haptic feedback
  const triggerHaptic = async () => {
    try {
      const Haptics = await import('expo-haptics');
      await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    } catch {
      // Fallback to vibration if haptics not available
      Vibration.vibrate(10);
    }
  };

  // Handle press with haptic
  const handlePress = () => {
    'worklet';
    runOnJS(triggerHaptic)();
    scale.value = withSequence(
      withSpring(0.9, { damping: 10, stiffness: 400 }),
      withSpring(1, { damping: 10, stiffness: 400 })
    );
    runOnJS(onPress)();
  };

  // Listening animation
  useEffect(() => {
    if (isListening) {
      // Start pulse animation
      pulseScale.value = withRepeat(
        withSequence(
          withTiming(1.3, { duration: 1000 }),
          withTiming(1, { duration: 1000 })
        ),
        -1
      );
      
      pulseOpacity.value = withRepeat(
        withSequence(
          withTiming(0.6, { duration: 1000 }),
          withTiming(0, { duration: 1000 })
        ),
        -1
      );
      
      // Glow effect
      glowIntensity.value = withRepeat(
        withSequence(
          withTiming(1, { duration: 800 }),
          withTiming(0.3, { duration: 800 })
        ),
        -1
      );
      
      // Subtle rotation
      rotation.value = withRepeat(
        withSequence(
          withTiming(5, { duration: 2000 }),
          withTiming(-5, { duration: 2000 })
        ),
        -1
      );
    } else {
      // Reset animations
      pulseScale.value = withTiming(1, { duration: 300 });
      pulseOpacity.value = withTiming(0, { duration: 300 });
      glowIntensity.value = withTiming(0, { duration: 300 });
      rotation.value = withTiming(0, { duration: 300 });
    }
  }, [isListening]);

  // Animated styles
  const buttonStyle = useAnimatedStyle(() => ({
    transform: [
      { scale: scale.value },
      { rotate: `${rotation.value}deg` },
    ],
  }));

  const pulseStyle = useAnimatedStyle(() => ({
    transform: [{ scale: pulseScale.value }],
    opacity: pulseOpacity.value,
  }));

  const glowStyle = useAnimatedStyle(() => ({
    opacity: interpolate(
      glowIntensity.value,
      [0, 1],
      [0, 0.8],
      Extrapolate.CLAMP
    ),
  }));

  // Gradient colors based on state
  const gradientColors = isListening
    ? theme.colors.gradients.aurora
    : theme.colors.gradients.journey;

  return (
    <View style={[styles.container, { width: size * 2, height: size * 2 }]}>
      {/* Pulse effect */}
      <Animated.View
        style={[
          styles.pulse,
          pulseStyle,
          {
            width: size * 1.8,
            height: size * 1.8,
            borderRadius: size * 0.9,
          },
        ]}
      >
        <LinearGradient
          colors={[...gradientColors, 'transparent']}
          style={styles.pulseGradient}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
        />
      </Animated.View>

      {/* Glow effect */}
      <Animated.View
        style={[
          styles.glow,
          glowStyle,
          {
            width: size * 1.5,
            height: size * 1.5,
            borderRadius: size * 0.75,
          },
        ]}
        pointerEvents="none"
      >
        <LinearGradient
          colors={[theme.colors.aurora.blue, theme.colors.aurora.purple, 'transparent']}
          style={styles.glowGradient}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
        />
      </Animated.View>

      {/* Main button */}
      <TouchableOpacity
        onPress={handlePress}
        disabled={disabled}
        activeOpacity={0.8}
      >
        <Animated.View style={[styles.button, buttonStyle, { width: size, height: size }]}>
          <AnimatedLinearGradient
            colors={gradientColors}
            style={[styles.gradient, { borderRadius: size / 2 }]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
          >
            <View style={styles.iconContainer}>
              {/* Microphone icon */}
              <Svg width={size * 0.5} height={size * 0.5} viewBox="0 0 24 24">
                <Path
                  d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"
                  fill="white"
                />
                <Path
                  d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"
                  fill="white"
                />
              </Svg>
            </View>
          </AnimatedLinearGradient>
        </Animated.View>
      </TouchableOpacity>

      {/* Listening indicator */}
      {isListening && (
        <View style={styles.listeningIndicator}>
          <Text style={styles.listeningText}>Listening...</Text>
        </View>
      )}

      {/* Transcript preview */}
      {transcript && (
        <Animated.View
          entering={theme.animation.animations.fadeIn}
          style={styles.transcriptContainer}
        >
          <Text style={styles.transcriptText} numberOfLines={2}>
            "{transcript}"
          </Text>
        </Animated.View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  button: {
    ...theme.elevation.high,
  },
  gradient: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconContainer: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  pulse: {
    position: 'absolute',
  },
  pulseGradient: {
    flex: 1,
  },
  glow: {
    position: 'absolute',
  },
  glowGradient: {
    flex: 1,
  },
  listeningIndicator: {
    position: 'absolute',
    bottom: -30,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.xs,
    backgroundColor: theme.colors.primary[500],
    borderRadius: theme.layout.borderRadius.full,
  },
  listeningText: {
    ...theme.typography.labelMedium,
    color: theme.colors.text.inverse,
  },
  transcriptContainer: {
    position: 'absolute',
    bottom: -60,
    width: 200,
    alignItems: 'center',
  },
  transcriptText: {
    ...theme.typography.bodySmall,
    color: theme.colors.text.secondary,
    textAlign: 'center',
    fontStyle: 'italic',
  },
});