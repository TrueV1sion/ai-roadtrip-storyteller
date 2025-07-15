/**
 * NavigationStatus Component
 * Drive-safe status display with progress tracking
 */

import React, { useEffect } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  withRepeat,
  withSequence,
  interpolate,
  Extrapolate,
} from 'react-native-reanimated';
import { LinearGradient } from 'expo-linear-gradient';
import Svg, { Path } from 'react-native-svg';
import { lightTheme as theme } from '../../theme';

interface NavigationStatusProps {
  status: string;
  progress: number; // 0 to 1
  eta?: string;
  distance?: string;
  nextTurn?: {
    direction: 'left' | 'right' | 'straight';
    distance: string;
    instruction: string;
  };
  speed?: number;
  speedLimit?: number;
}

const AnimatedLinearGradient = Animated.createAnimatedComponent(LinearGradient);

export const NavigationStatus: React.FC<NavigationStatusProps> = ({
  status,
  progress,
  eta,
  distance,
  nextTurn,
  speed,
  speedLimit,
}) => {
  const progressAnimation = useSharedValue(0);
  const pulseAnimation = useSharedValue(1);
  const statusDotAnimation = useSharedValue(0);

  // Animate progress bar
  useEffect(() => {
    progressAnimation.value = withTiming(progress, {
      duration: theme.animation.duration.slow,
    });
  }, [progress]);

  // Status dot pulse
  useEffect(() => {
    statusDotAnimation.value = withRepeat(
      withSequence(
        withTiming(1, { duration: 1000 }),
        withTiming(0.6, { duration: 1000 })
      ),
      -1
    );
  }, []);

  // Progress bar style
  const progressStyle = useAnimatedStyle(() => ({
    width: `${interpolate(
      progressAnimation.value,
      [0, 1],
      [0, 100],
      Extrapolate.CLAMP
    )}%`,
  }));

  // Status dot style
  const statusDotStyle = useAnimatedStyle(() => ({
    opacity: statusDotAnimation.value,
    transform: [
      {
        scale: interpolate(
          statusDotAnimation.value,
          [0.6, 1],
          [0.8, 1],
          Extrapolate.CLAMP
        ),
      },
    ],
  }));

  // Get turn icon
  const getTurnIcon = (direction: string) => {
    switch (direction) {
      case 'left':
        return (
          <Path
            d="M15.41 16.59L10.83 12l4.58-4.59L14 6l-6 6 6 6 1.41-1.41z"
            fill={theme.colors.text.inverse}
          />
        );
      case 'right':
        return (
          <Path
            d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z"
            fill={theme.colors.text.inverse}
          />
        );
      default:
        return (
          <Path
            d="M12 2l-1.41 1.41L16.17 9H4v2h12.17l-5.58 5.59L12 18l8-8z"
            fill={theme.colors.text.inverse}
          />
        );
    }
  };

  // Speed indicator color
  const getSpeedColor = () => {
    if (!speed || !speedLimit) return theme.colors.success;
    if (speed > speedLimit + 5) return theme.colors.error;
    if (speed > speedLimit) return theme.colors.warning;
    return theme.colors.success;
  };

  return (
    <View style={styles.container}>
      {/* Main status bar */}
      <View style={styles.statusBar}>
        <LinearGradient
          colors={['rgba(13, 17, 23, 0.95)', 'rgba(13, 17, 23, 0.85)']}
          style={styles.statusGradient}
        >
          {/* Status indicator */}
          <View style={styles.statusRow}>
            <Animated.View style={[styles.statusDot, statusDotStyle]}>
              <LinearGradient
                colors={theme.colors.gradients.aurora}
                style={styles.statusDotGradient}
              />
            </Animated.View>
            <Text style={styles.statusText} numberOfLines={1}>
              {status}
            </Text>
          </View>

          {/* ETA and Distance */}
          <View style={styles.metaRow}>
            {eta && (
              <View style={styles.metaItem}>
                <Text style={styles.metaLabel}>ETA</Text>
                <Text style={styles.metaValue}>{eta}</Text>
              </View>
            )}
            {distance && (
              <View style={styles.metaItem}>
                <Text style={styles.metaLabel}>Distance</Text>
                <Text style={styles.metaValue}>{distance}</Text>
              </View>
            )}
            {speed !== undefined && (
              <View style={styles.metaItem}>
                <Text style={styles.metaLabel}>Speed</Text>
                <Text style={[styles.metaValue, { color: getSpeedColor() }]}>
                  {speed} mph
                </Text>
              </View>
            )}
          </View>
        </LinearGradient>
      </View>

      {/* Progress bar */}
      <View style={styles.progressContainer}>
        <Animated.View style={[styles.progressBar, progressStyle]}>
          <AnimatedLinearGradient
            colors={theme.colors.gradients.aurora}
            style={styles.progressGradient}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
          />
        </Animated.View>
        <View style={styles.progressBackground} />
      </View>

      {/* Next turn indicator */}
      {nextTurn && (
        <Animated.View
          entering={theme.animation.animations.slideInUp}
          style={styles.nextTurnContainer}
        >
          <LinearGradient
            colors={[theme.colors.primary[600], theme.colors.primary[700]]}
            style={styles.nextTurnGradient}
          >
            <View style={styles.turnIcon}>
              <Svg width={24} height={24} viewBox="0 0 24 24">
                {getTurnIcon(nextTurn.direction)}
              </Svg>
            </View>
            <View style={styles.turnInfo}>
              <Text style={styles.turnDistance}>{nextTurn.distance}</Text>
              <Text style={styles.turnInstruction} numberOfLines={1}>
                {nextTurn.instruction}
              </Text>
            </View>
          </LinearGradient>
        </Animated.View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: '100%',
  },
  statusBar: {
    overflow: 'hidden',
    borderRadius: theme.layout.borderRadius.lg,
    ...theme.elevation.medium,
  },
  statusGradient: {
    padding: theme.spacing.md,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.sm,
    marginBottom: theme.spacing.xs,
  },
  statusDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    overflow: 'hidden',
  },
  statusDotGradient: {
    flex: 1,
  },
  statusText: {
    ...theme.typography.titleMedium,
    color: theme.colors.text.inverse,
    flex: 1,
  },
  metaRow: {
    flexDirection: 'row',
    gap: theme.spacing.xl,
  },
  metaItem: {
    gap: theme.spacing.xxs,
  },
  metaLabel: {
    ...theme.typography.labelSmall,
    color: theme.colors.neutral[400],
    textTransform: 'uppercase',
  },
  metaValue: {
    ...theme.typography.bodyLarge,
    color: theme.colors.text.inverse,
    fontWeight: theme.typography.fontWeight.semibold,
  },
  progressContainer: {
    height: 4,
    marginTop: -2,
    position: 'relative',
  },
  progressBackground: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: theme.colors.neutral[800],
    opacity: 0.3,
  },
  progressBar: {
    height: '100%',
    position: 'absolute',
    left: 0,
    top: 0,
  },
  progressGradient: {
    flex: 1,
  },
  nextTurnContainer: {
    marginTop: theme.spacing.sm,
    borderRadius: theme.layout.borderRadius.md,
    overflow: 'hidden',
    ...theme.elevation.low,
  },
  nextTurnGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: theme.spacing.sm,
    gap: theme.spacing.sm,
  },
  turnIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  turnInfo: {
    flex: 1,
    gap: 2,
  },
  turnDistance: {
    ...theme.typography.labelLarge,
    color: theme.colors.text.inverse,
    fontWeight: theme.typography.fontWeight.bold,
  },
  turnInstruction: {
    ...theme.typography.bodySmall,
    color: theme.colors.neutral[200],
  },
});