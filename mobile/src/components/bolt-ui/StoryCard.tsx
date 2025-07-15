/**
 * StoryCard Component
 * Migrated from Bolt's storyteller UI
 * Displays story information with play controls
 */

import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Platform,
} from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSpring,
} from 'react-native-reanimated';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useDispatch, useSelector } from 'react-redux';
import { unifiedTheme } from '../../theme/unified';
import { Story } from '../../types/story';
import { 
  playStory, 
  pauseStory, 
  likeStory, 
  shareStory 
} from '../../store/slices/storySlice';
import { RootState } from '../../store';

interface StoryCardProps {
  story: Story;
  isPlaying?: boolean;
  onPress?: () => void;
}

export const StoryCard: React.FC<StoryCardProps> = ({
  story,
  isPlaying = false,
  onPress,
}) => {
  const dispatch = useDispatch();
  const scale = useSharedValue(1);
  
  // Get story state from Redux
  const { likedStories } = useSelector((state: RootState) => state.story);
  const isLiked = likedStories.includes(story.id);

  const handlePressIn = () => {
    scale.value = withSpring(0.98, unifiedTheme.animations.spring.gentle);
  };

  const handlePressOut = () => {
    scale.value = withSpring(1, unifiedTheme.animations.spring.bouncy);
  };

  const handlePlayPause = () => {
    if (isPlaying) {
      dispatch(pauseStory());
    } else {
      dispatch(playStory(story));
    }
  };

  const handleLike = () => {
    dispatch(likeStory(story.id));
  };

  const handleShare = () => {
    dispatch(shareStory(story));
  };

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  // Format duration from seconds to mm:ss
  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <TouchableOpacity
      onPress={onPress}
      onPressIn={handlePressIn}
      onPressOut={handlePressOut}
      activeOpacity={1}
    >
      <Animated.View style={[styles.card, animatedStyle]}>
        {/* Play/Pause Button */}
        <TouchableOpacity 
          style={styles.playButton} 
          onPress={handlePlayPause}
        >
          <View style={[
            styles.playButtonInner,
            isPlaying && styles.playButtonActive
          ]}>
            <MaterialCommunityIcons
              name={isPlaying ? 'pause' : 'play'}
              size={24}
              color="white"
            />
          </View>
        </TouchableOpacity>

        {/* Story Info */}
        <View style={styles.content}>
          <View style={styles.header}>
            <Text style={styles.title} numberOfLines={1}>
              {story.title}
            </Text>
            <Text style={styles.duration}>
              {formatDuration(story.duration)}
            </Text>
          </View>
          
          <View style={styles.meta}>
            <View style={styles.narrator}>
              <MaterialCommunityIcons
                name="microphone"
                size={14}
                color={unifiedTheme.colors.neutral[500]}
              />
              <Text style={styles.narratorText}>
                {story.narrator}
              </Text>
            </View>
            
            <View style={styles.location}>
              <MaterialCommunityIcons
                name="map-marker"
                size={14}
                color={unifiedTheme.colors.neutral[500]}
              />
              <Text style={styles.locationText} numberOfLines={1}>
                {story.location}
              </Text>
            </View>
          </View>
        </View>

        {/* Action Buttons */}
        <View style={styles.actions}>
          <TouchableOpacity 
            style={styles.actionButton}
            onPress={handleLike}
          >
            <MaterialCommunityIcons
              name={isLiked ? 'heart' : 'heart-outline'}
              size={20}
              color={isLiked ? unifiedTheme.colors.accent.red : unifiedTheme.colors.neutral[400]}
            />
          </TouchableOpacity>
          
          <TouchableOpacity 
            style={styles.actionButton}
            onPress={handleShare}
          >
            <MaterialCommunityIcons
              name="share-variant"
              size={20}
              color={unifiedTheme.colors.neutral[400]}
            />
          </TouchableOpacity>
        </View>

        {/* Playing Indicator */}
        {isPlaying && (
          <View style={styles.playingIndicator}>
            <View style={styles.playingDot} />
            <Text style={styles.playingText}>Now Playing</Text>
          </View>
        )}
      </Animated.View>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: unifiedTheme.colors.surface.card,
    borderRadius: unifiedTheme.borderRadius.lg,
    padding: unifiedTheme.spacing[4],
    marginVertical: unifiedTheme.spacing[2],
    flexDirection: 'row',
    alignItems: 'center',
    ...unifiedTheme.shadows.base,
  },
  playButton: {
    marginRight: unifiedTheme.spacing[4],
  },
  playButtonInner: {
    width: 48,
    height: 48,
    borderRadius: unifiedTheme.borderRadius.full,
    backgroundColor: unifiedTheme.colors.primary[600],
    justifyContent: 'center',
    alignItems: 'center',
  },
  playButtonActive: {
    backgroundColor: unifiedTheme.colors.secondary[500],
  },
  content: {
    flex: 1,
    marginRight: unifiedTheme.spacing[3],
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: unifiedTheme.spacing[2],
  },
  title: {
    ...unifiedTheme.typography.storyTitle,
    color: unifiedTheme.colors.neutral[900],
    flex: 1,
    marginRight: unifiedTheme.spacing[2],
  },
  duration: {
    ...unifiedTheme.typography.storyDuration,
  },
  meta: {
    flexDirection: 'row',
    gap: unifiedTheme.spacing[4],
  },
  narrator: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: unifiedTheme.spacing[1],
  },
  narratorText: {
    ...unifiedTheme.typography.caption,
    color: unifiedTheme.colors.neutral[600],
  },
  location: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: unifiedTheme.spacing[1],
    flex: 1,
  },
  locationText: {
    ...unifiedTheme.typography.caption,
    color: unifiedTheme.colors.neutral[600],
    flex: 1,
  },
  actions: {
    flexDirection: 'row',
    gap: unifiedTheme.spacing[2],
  },
  actionButton: {
    padding: unifiedTheme.spacing[2],
  },
  playingIndicator: {
    position: 'absolute',
    top: unifiedTheme.spacing[2],
    right: unifiedTheme.spacing[2],
    flexDirection: 'row',
    alignItems: 'center',
    gap: unifiedTheme.spacing[1],
    backgroundColor: unifiedTheme.colors.secondary[100],
    paddingHorizontal: unifiedTheme.spacing[2],
    paddingVertical: unifiedTheme.spacing[1],
    borderRadius: unifiedTheme.borderRadius.full,
  },
  playingDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: unifiedTheme.colors.secondary[500],
  },
  playingText: {
    ...unifiedTheme.typography.caption,
    color: unifiedTheme.colors.secondary[700],
    fontFamily: unifiedTheme.fontFamilies.medium,
  },
});
