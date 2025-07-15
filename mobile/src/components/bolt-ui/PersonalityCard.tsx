/**
 * PersonalityCard Component
 * Migrated from Bolt's beautiful storyteller UI
 * Adapted to work with RoadTrip's Redux state management
 */

import React, { useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
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
import { useDispatch, useSelector } from 'react-redux';
import { LinearGradient } from 'expo-linear-gradient';
import { unifiedTheme } from '../../theme/unified';
import { VoicePersonality } from '../../types/voice';
import { selectVoicePersonality } from '../../store/slices/voiceSlice';
import { RootState } from '../../store';

const { width } = Dimensions.get('window');
const CARD_WIDTH = width * 0.8;
const CARD_HEIGHT = 200;

interface PersonalityCardProps {
  personality: VoicePersonality;
  isSelected?: boolean;
  onPress?: (personality: VoicePersonality) => void;
  style?: any;
}

export const PersonalityCard: React.FC<PersonalityCardProps> = ({
  personality,
  isSelected = false,
  onPress,
  style,
}) => {
  const dispatch = useDispatch();
  const scale = useSharedValue(1);
  const opacity = useSharedValue(1);

  // Get theme colors based on category
  const categoryColor = unifiedTheme.personalityColors[personality.category] || unifiedTheme.colors.primary[600];

  const handlePressIn = () => {
    scale.value = withSpring(0.95, unifiedTheme.animations.spring.gentle);
    opacity.value = withSpring(0.8);
  };

  const handlePressOut = () => {
    scale.value = withSpring(1, unifiedTheme.animations.spring.bouncy);
    opacity.value = withSpring(1);
  };

  const handlePress = () => {
    if (onPress) {
      onPress(personality);
    } else {
      dispatch(selectVoicePersonality(personality));
    }
  };

  const animatedStyle = useAnimatedStyle(() => {
    return {
      transform: [{ scale: scale.value }],
      opacity: opacity.value,
    };
  });

  const borderStyle = isSelected ? {
    borderWidth: 3,
    borderColor: categoryColor,
  } : {
    borderWidth: 1,
    borderColor: unifiedTheme.colors.surface.border,
  };

  return (
    <TouchableOpacity
      onPress={handlePress}
      onPressIn={handlePressIn}
      onPressOut={handlePressOut}
      activeOpacity={1}
    >
      <Animated.View
        style={[
          styles.card,
          borderStyle,
          animatedStyle,
          style,
        ]}
      >
        {/* Background Image */}
        <Image
          source={{ uri: personality.avatar_url || personality.image }}
          style={styles.backgroundImage}
          resizeMode="cover"
        />
        
        {/* Gradient Overlay */}
        <LinearGradient
          colors={['transparent', 'rgba(0,0,0,0.7)']}
          style={styles.gradient}
        />
        
        {/* Content */}
        <View style={styles.content}>
          {/* Active Badge */}
          {personality.is_active && (
            <View style={[styles.activeBadge, { backgroundColor: categoryColor }]}>
              <Text style={styles.activeText}>ACTIVE</Text>
            </View>
          )}
          
          {/* Personality Info */}
          <View style={styles.info}>
            <Text style={styles.name}>{personality.name}</Text>
            <Text style={styles.description} numberOfLines={2}>
              {personality.tagline || personality.description}
            </Text>
            <View style={styles.meta}>
              <View style={[styles.categoryBadge, { backgroundColor: unifiedTheme.utils.withOpacity(categoryColor, 0.2) }]}>
                <Text style={[styles.categoryText, { color: categoryColor }]}>
                  {personality.category}
                </Text>
              </View>
              {personality.popularity_score && (
                <Text style={styles.popularity}>
                  ⭐ {personality.popularity_score.toFixed(1)}
                </Text>
              )}
            </View>
          </View>
        </View>
      </Animated.View>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  card: {
    width: CARD_WIDTH,
    height: CARD_HEIGHT,
    borderRadius: unifiedTheme.borderRadius.xl,
    overflow: 'hidden',
    marginHorizontal: unifiedTheme.spacing[2],
    ...unifiedTheme.shadows.lg,
  },
  backgroundImage: {
    position: 'absolute',
    width: '100%',
    height: '100%',
  },
  gradient: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    height: '70%',
  },
  content: {
    flex: 1,
    padding: unifiedTheme.spacing[4],
    justifyContent: 'flex-end',
  },
  activeBadge: {
    position: 'absolute',
    top: unifiedTheme.spacing[4],
    right: unifiedTheme.spacing[4],
    paddingHorizontal: unifiedTheme.spacing[3],
    paddingVertical: unifiedTheme.spacing[1],
    borderRadius: unifiedTheme.borderRadius.full,
  },
  activeText: {
    ...unifiedTheme.typography.caption,
    color: 'white',
    fontFamily: unifiedTheme.fontFamilies.bold,
  },
  info: {
    gap: unifiedTheme.spacing[2],
  },
  name: {
    ...unifiedTheme.typography.personalityName,
    color: 'white',
  },
  description: {
    ...unifiedTheme.typography.personalityDescription,
    color: 'rgba(255,255,255,0.8)',
  },
  meta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: unifiedTheme.spacing[3],
  },
  categoryBadge: {
    paddingHorizontal: unifiedTheme.spacing[3],
    paddingVertical: unifiedTheme.spacing[1],
    borderRadius: unifiedTheme.borderRadius.full,
  },
  categoryText: {
    ...unifiedTheme.typography.caption,
    fontFamily: unifiedTheme.fontFamilies.medium,
  },
  popularity: {
    ...unifiedTheme.typography.caption,
    color: 'rgba(255,255,255,0.8)',
  },
});
