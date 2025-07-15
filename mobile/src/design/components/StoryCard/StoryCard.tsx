/**
 * StoryCard Component
 * Immersive content display with glass morphism effect
 */

import React from 'react';
import {
  TouchableOpacity,
  View,
  Text,
  Image,
  StyleSheet,
  Dimensions,
  Platform,
} from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSpring,
  interpolate,
  Extrapolate,
} from 'react-native-reanimated';
import { LinearGradient } from 'expo-linear-gradient';
import { BlurView } from 'expo-blur';
import Svg, { Path } from 'react-native-svg';
import { lightTheme as theme } from '../../theme';

interface StoryCardProps {
  title: string;
  description: string;
  duration: string;
  imageUrl?: string;
  narrator?: string;
  isPlaying?: boolean;
  progress?: number;
  onPress: () => void;
  style?: any;
}

const { width: screenWidth } = Dimensions.get('window');
const CARD_WIDTH = screenWidth - theme.spacing.xl;
const CARD_HEIGHT = 200;

export const StoryCard: React.FC<StoryCardProps> = ({
  title,
  description,
  duration,
  imageUrl,
  narrator,
  isPlaying = false,
  progress = 0,
  onPress,
  style,
}) => {
  const scale = useSharedValue(1);
  const translateY = useSharedValue(0);

  const handlePressIn = () => {
    scale.value = withSpring(0.98, { damping: 15, stiffness: 400 });
    translateY.value = withSpring(2, { damping: 15, stiffness: 400 });
  };

  const handlePressOut = () => {
    scale.value = withSpring(1, { damping: 15, stiffness: 400 });
    translateY.value = withSpring(0, { damping: 15, stiffness: 400 });
  };

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [
      { scale: scale.value },
      { translateY: translateY.value },
    ],
  }));

  const progressStyle = useAnimatedStyle(() => ({
    width: `${interpolate(
      progress,
      [0, 1],
      [0, 100],
      Extrapolate.CLAMP
    )}%`,
  }));

  return (
    <TouchableOpacity
      onPress={onPress}
      onPressIn={handlePressIn}
      onPressOut={handlePressOut}
      activeOpacity={1}
    >
      <Animated.View style={[styles.container, animatedStyle, style]}>
        {/* Background image */}
        {imageUrl && (
          <Image
            source={{ uri: imageUrl }}
            style={styles.backgroundImage}
            resizeMode="cover"
          />
        )}
        
        {/* Gradient overlay */}
        <LinearGradient
          colors={['transparent', 'rgba(0,0,0,0.7)', 'rgba(0,0,0,0.9)']}
          style={styles.gradientOverlay}
          start={{ x: 0, y: 0 }}
          end={{ x: 0, y: 1 }}
        />

        {/* Glass morphism content */}
        <View style={styles.contentWrapper}>
          {Platform.OS === 'ios' ? (
            <BlurView
              style={styles.blurContainer}
              blurType="dark"
              blurAmount={10}
              reducedTransparencyFallbackColor="rgba(0,0,0,0.8)"
            >
              <ContentInner
                title={title}
                description={description}
                duration={duration}
                narrator={narrator}
                isPlaying={isPlaying}
              />
            </BlurView>
          ) : (
            <View style={[styles.blurContainer, styles.androidBlur]}>
              <ContentInner
                title={title}
                description={description}
                duration={duration}
                narrator={narrator}
                isPlaying={isPlaying}
              />
            </View>
          )}
        </View>

        {/* Progress bar */}
        {isPlaying && (
          <View style={styles.progressContainer}>
            <Animated.View style={[styles.progressBar, progressStyle]}>
              <LinearGradient
                colors={theme.colors.gradients.aurora}
                style={styles.progressGradient}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
              />
            </Animated.View>
          </View>
        )}

        {/* Aurora decoration */}
        <View style={styles.auroraDecoration}>
          <LinearGradient
            colors={[...theme.colors.gradients.aurora, 'transparent']}
            style={styles.auroraGradient}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
          />
        </View>
      </Animated.View>
    </TouchableOpacity>
  );
};

// Inner content component
const ContentInner: React.FC<{
  title: string;
  description: string;
  duration: string;
  narrator?: string;
  isPlaying: boolean;
}> = ({ title, description, duration, narrator, isPlaying }) => (
  <View style={styles.content}>
    <View style={styles.header}>
      <Text style={styles.title} numberOfLines={2}>
        {title}
      </Text>
      {isPlaying && (
        <View style={styles.playingIndicator}>
          <View style={styles.playingDot} />
          <Text style={styles.playingText}>Now Playing</Text>
        </View>
      )}
    </View>

    <Text style={styles.description} numberOfLines={2}>
      {description}
    </Text>

    <View style={styles.footer}>
      <View style={styles.metaItem}>
        <Svg width={16} height={16} viewBox="0 0 24 24">
          <Path
            d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"
            fill={theme.colors.neutral[300]}
          />
        </Svg>
        <Text style={styles.metaText}>{duration}</Text>
      </View>

      {narrator && (
        <View style={styles.metaItem}>
          <Svg width={16} height={16} viewBox="0 0 24 24">
            <Path
              d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"
              fill={theme.colors.neutral[300]}
            />
          </Svg>
          <Text style={styles.metaText}>{narrator}</Text>
        </View>
      )}
    </View>
  </View>
);

const styles = StyleSheet.create({
  container: {
    width: CARD_WIDTH,
    height: CARD_HEIGHT,
    borderRadius: theme.layout.borderRadius.xl,
    overflow: 'hidden',
    ...theme.elevation.medium,
  },
  backgroundImage: {
    ...StyleSheet.absoluteFillObject,
    width: '100%',
    height: '100%',
  },
  gradientOverlay: {
    ...StyleSheet.absoluteFillObject,
  },
  contentWrapper: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'flex-end',
  },
  blurContainer: {
    padding: theme.spacing.lg,
    borderBottomLeftRadius: theme.layout.borderRadius.xl,
    borderBottomRightRadius: theme.layout.borderRadius.xl,
  },
  androidBlur: {
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
  },
  content: {
    gap: theme.spacing.sm,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: theme.spacing.md,
  },
  title: {
    ...theme.typography.titleLarge,
    color: theme.colors.text.inverse,
    flex: 1,
  },
  playingIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.xs,
    backgroundColor: theme.colors.primary[500],
    paddingHorizontal: theme.spacing.sm,
    paddingVertical: theme.spacing.xxs,
    borderRadius: theme.layout.borderRadius.full,
  },
  playingDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: theme.colors.text.inverse,
  },
  playingText: {
    ...theme.typography.labelSmall,
    color: theme.colors.text.inverse,
  },
  description: {
    ...theme.typography.bodyMedium,
    color: theme.colors.neutral[200],
  },
  footer: {
    flexDirection: 'row',
    gap: theme.spacing.lg,
  },
  metaItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: theme.spacing.xs,
  },
  metaText: {
    ...theme.typography.labelMedium,
    color: theme.colors.neutral[300],
  },
  progressContainer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: 3,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
  },
  progressBar: {
    height: '100%',
  },
  progressGradient: {
    flex: 1,
  },
  auroraDecoration: {
    position: 'absolute',
    top: -50,
    right: -50,
    width: 100,
    height: 100,
    opacity: 0.3,
  },
  auroraGradient: {
    flex: 1,
    borderRadius: 50,
  },
});