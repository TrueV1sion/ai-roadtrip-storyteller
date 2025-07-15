import React, { useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Animated,
  Dimensions,
} from 'react-native';
import { VoicePersonality } from '../../types/voice';
import { MaterialCommunityIcons } from '@expo/vector-icons';

interface PersonalityVisualizationProps {
  personality: VoicePersonality;
  isActive: boolean;
  currentEmotion?: string;
}

const { width } = Dimensions.get('window');

export const PersonalityVisualization: React.FC<PersonalityVisualizationProps> = ({
  personality,
  isActive,
  currentEmotion = 'neutral',
}) => {
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const rotateAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (isActive) {
      // Fade in
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 500,
        useNativeDriver: true,
      }).start();

      // Pulse animation
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, {
            toValue: 1.1,
            duration: 1000,
            useNativeDriver: true,
          }),
          Animated.timing(pulseAnim, {
            toValue: 1,
            duration: 1000,
            useNativeDriver: true,
          }),
        ])
      ).start();

      // Rotate animation for special personalities
      if (personality.active_holidays || personality.active_seasons) {
        Animated.loop(
          Animated.timing(rotateAnim, {
            toValue: 1,
            duration: 10000,
            useNativeDriver: true,
          })
        ).start();
      }
    } else {
      // Fade out
      Animated.timing(fadeAnim, {
        toValue: 0,
        duration: 300,
        useNativeDriver: true,
      }).start();
    }
  }, [isActive, personality]);

  const getEmotionColor = (emotion: string): string => {
    const emotionColors: Record<string, string> = {
      happiness: '#4CAF50',
      excitement: '#FF9800',
      calm: '#2196F3',
      mystery: '#9C27B0',
      love: '#E91E63',
      pride: '#F44336',
      nostalgia: '#795548',
      mischief: '#00BCD4',
      humor: '#FFEB3B',
    };
    return emotionColors[emotion] || '#666666';
  };

  const getPersonalityIcon = (personalityId: string): string => {
    const iconMap: Record<string, string> = {
      friendly_guide: 'human-greeting',
      local_expert: 'map-marker-account',
      historian: 'book-open-variant',
      adventurer: 'hiking',
      comedian: 'emoticon-happy',
      santa: 'santa',
      halloween_narrator: 'ghost',
      cupid: 'heart',
      leprechaun: 'clover',
      patriot: 'flag',
      harvest_guide: 'corn',
      inspirational: 'white-balance-sunny',
    };
    return iconMap[personalityId] || 'account';
  };

  const spin = rotateAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '360deg'],
  });

  // Get the dominant emotion from personality
  const dominantEmotion = Object.entries(personality.emotion_range)
    .sort(([, a], [, b]) => b - a)[0]?.[0] || 'neutral';

  const emotionColor = getEmotionColor(currentEmotion || dominantEmotion);

  return (
    <Animated.View
      style={[
        styles.container,
        {
          opacity: fadeAnim,
          transform: [{ scale: pulseAnim }],
        },
      ]}
    >
      <View style={[styles.emotionRing, { borderColor: emotionColor }]}>
        <Animated.View
          style={[
            styles.iconContainer,
            personality.active_holidays && { transform: [{ rotate: spin }] },
          ]}
        >
          <MaterialCommunityIcons
            name={getPersonalityIcon(personality.id)}
            size={48}
            color={emotionColor}
          />
        </Animated.View>
      </View>

      <Text style={styles.personalityName}>{personality.name}</Text>
      
      {isActive && (
        <View style={styles.emotionBar}>
          {Object.entries(personality.emotion_range).map(([emotion, value]) => (
            <View
              key={emotion}
              style={[
                styles.emotionSegment,
                {
                  backgroundColor: getEmotionColor(emotion),
                  flex: value,
                  opacity: emotion === currentEmotion ? 1 : 0.3,
                },
              ]}
            />
          ))}
        </View>
      )}

      {personality.regional_accent && (
        <View style={styles.accentBadge}>
          <Text style={styles.accentText}>{personality.regional_accent}</Text>
        </View>
      )}

      {personality.active_holidays && (
        <View style={styles.specialBadge}>
          <MaterialCommunityIcons name="star" size={16} color="#ffd700" />
          <Text style={styles.specialText}>Limited Edition</Text>
        </View>
      )}
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    padding: 20,
  },
  emotionRing: {
    width: 120,
    height: 120,
    borderRadius: 60,
    borderWidth: 4,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 15,
  },
  iconContainer: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  personalityName: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333333',
    marginBottom: 10,
  },
  emotionBar: {
    flexDirection: 'row',
    width: width * 0.7,
    height: 6,
    borderRadius: 3,
    overflow: 'hidden',
    marginTop: 10,
  },
  emotionSegment: {
    height: '100%',
  },
  accentBadge: {
    backgroundColor: '#e6f2ff',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
    marginTop: 10,
  },
  accentText: {
    fontSize: 12,
    color: '#0066cc',
    fontWeight: '600',
  },
  specialBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff3cd',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
    marginTop: 10,
  },
  specialText: {
    fontSize: 12,
    color: '#856404',
    fontWeight: '600',
    marginLeft: 4,
  },
});