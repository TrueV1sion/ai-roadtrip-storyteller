import React, { useRef, useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Animated,
  Dimensions,
  AccessibilityInfo,
} from 'react-native';
import { BlurView } from 'expo-blur';
import * as Haptics from 'expo-haptics';
import { MaterialIcons, FontAwesome5 } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';

interface ARPointOfInterestProps {
  id: string;
  title: string;
  type: 'historical' | 'nature' | 'restaurant' | 'attraction' | 'navigation';
  distance: number; // in meters
  eta?: number; // in seconds
  onPress: () => void;
  onDismiss: () => void;
  position: { x: number; y: number }; // Normalized coordinates (0-1)
  isHighlighted?: boolean;
  showVoiceCTA?: boolean;
}

const { width: SCREEN_WIDTH } = Dimensions.get('window');

const ARPointOfInterest: React.FC<ARPointOfInterestProps> = ({
  id,
  title,
  type,
  distance,
  eta,
  onPress,
  onDismiss,
  position,
  isHighlighted = false,
  showVoiceCTA = true,
}) => {
  // Animation values
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0.8)).current;
  const glowAnim = useRef(new Animated.Value(0)).current;
  const progressAnim = useRef(new Animated.Value(0)).current;
  
  const [isInteracting, setIsInteracting] = useState(false);
  const dismissTimer = useRef<NodeJS.Timeout>();

  // Icon mapping
  const getIcon = () => {
    switch (type) {
      case 'historical':
        return <FontAwesome5 name="landmark" size={24} color="#FFFFFF" />;
      case 'nature':
        return <FontAwesome5 name="tree" size={24} color="#FFFFFF" />;
      case 'restaurant':
        return <MaterialIcons name="restaurant" size={24} color="#FFFFFF" />;
      case 'attraction':
        return <MaterialIcons name="attractions" size={24} color="#FFFFFF" />;
      case 'navigation':
        return <MaterialIcons name="navigation" size={24} color="#FFFFFF" />;
      default:
        return <MaterialIcons name="place" size={24} color="#FFFFFF" />;
    }
  };

  // Color scheme based on type
  const getColorScheme = () => {
    switch (type) {
      case 'historical':
        return ['#8B6914', '#DAA520']; // Gold
      case 'nature':
        return ['#228B22', '#32CD32']; // Green
      case 'restaurant':
        return ['#DC143C', '#FF6347']; // Red
      case 'attraction':
        return ['#4169E1', '#1E90FF']; // Blue
      case 'navigation':
        return ['#FF4500', '#FF8C00']; // Orange
      default:
        return ['#4169E1', '#1E90FF'];
    }
  };

  // Format distance display
  const formatDistance = () => {
    if (distance < 1000) {
      return `${Math.round(distance)} m`;
    }
    return `${(distance / 1000).toFixed(1)} km`;
  };

  // Format ETA display
  const formatETA = () => {
    if (!eta) return null;
    if (eta < 60) return `${eta} sec`;
    return `${Math.round(eta / 60)} min`;
  };

  // Entrance animation
  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 0.9,
        duration: 300,
        useNativeDriver: true,
      }),
      Animated.spring(scaleAnim, {
        toValue: 1,
        friction: 8,
        tension: 40,
        useNativeDriver: true,
      }),
    ]).start();

    // Auto-dismiss after 8 seconds if not interacting
    dismissTimer.current = setTimeout(() => {
      if (!isInteracting) {
        handleDismiss();
      }
    }, 8000);

    return () => {
      if (dismissTimer.current) {
        clearTimeout(dismissTimer.current);
      }
    };
  }, []);

  // Highlight animation
  useEffect(() => {
    if (isHighlighted) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(glowAnim, {
            toValue: 1,
            duration: 1000,
            useNativeDriver: false,
          }),
          Animated.timing(glowAnim, {
            toValue: 0,
            duration: 1000,
            useNativeDriver: false,
          }),
        ])
      ).start();
    }
  }, [isHighlighted]);

  // Progress animation for navigation
  useEffect(() => {
    if (type === 'navigation' && eta) {
      Animated.timing(progressAnim, {
        toValue: 1,
        duration: eta * 1000,
        useNativeDriver: false,
      }).start();
    }
  }, [type, eta]);

  const handlePress = () => {
    setIsInteracting(true);
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    
    // Announce for accessibility
    AccessibilityInfo.announceForAccessibility(`Selected ${title}`);
    
    // Visual feedback
    Animated.sequence([
      Animated.timing(scaleAnim, {
        toValue: 0.95,
        duration: 50,
        useNativeDriver: true,
      }),
      Animated.timing(scaleAnim, {
        toValue: 1.05,
        duration: 100,
        useNativeDriver: true,
      }),
      Animated.timing(scaleAnim, {
        toValue: 1,
        duration: 50,
        useNativeDriver: true,
      }),
    ]).start(() => {
      onPress();
    });
  };

  const handleDismiss = () => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 0,
        duration: 300,
        useNativeDriver: true,
      }),
      Animated.timing(scaleAnim, {
        toValue: 0.8,
        duration: 300,
        useNativeDriver: true,
      }),
    ]).start(() => {
      onDismiss();
    });
  };

  const colors = getColorScheme();
  
  // Calculate actual position
  const left = position.x * SCREEN_WIDTH;
  const top = position.y * SCREEN_WIDTH; // Use width for consistent aspect ratio

  return (
    <Animated.View
      style={[
        styles.container,
        {
          left,
          top,
          opacity: fadeAnim,
          transform: [
            { scale: scaleAnim },
            { translateX: -75 }, // Center horizontally (half of width)
            { translateY: -50 }, // Center vertically (half of height)
          ],
        },
      ]}
    >
      <TouchableOpacity
        activeOpacity={0.9}
        onPress={handlePress}
        onLongPress={() => setIsInteracting(true)}
        accessibilityLabel={`${title}, ${formatDistance()} away`}
        accessibilityHint="Double tap to hear the story"
        accessibilityRole="button"
      >
        <BlurView intensity={80} style={styles.blurContainer}>
          <LinearGradient
            colors={colors}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            style={styles.gradientBorder}
          >
            <View style={styles.content}>
              {/* Icon and Title */}
              <View style={styles.header}>
                <View style={styles.iconContainer}>{getIcon()}</View>
                <Text style={styles.title} numberOfLines={1}>
                  {title}
                </Text>
              </View>

              {/* Progress indicator for navigation */}
              {type === 'navigation' && eta && (
                <View style={styles.progressContainer}>
                  <Animated.View
                    style={[
                      styles.progressBar,
                      {
                        width: progressAnim.interpolate({
                          inputRange: [0, 1],
                          outputRange: ['0%', '100%'],
                        }),
                      },
                    ]}
                  />
                </View>
              )}

              {/* Distance and ETA */}
              <View style={styles.info}>
                <Text style={styles.distance}>📍 {formatDistance()}</Text>
                {eta && <Text style={styles.eta}>• {formatETA()}</Text>}
              </View>

              {/* Voice CTA */}
              {showVoiceCTA && (
                <Text style={styles.voiceCTA}>
                  <MaterialIcons name="mic" size={14} color="#FFFFFF" />
                  {' "Tap to hear the story"'}
                </Text>
              )}
            </View>
          </LinearGradient>

          {/* Glow effect when highlighted */}
          {isHighlighted && (
            <Animated.View
              style={[
                styles.glowEffect,
                {
                  opacity: glowAnim,
                },
              ]}
            />
          )}
        </BlurView>
      </TouchableOpacity>

      {/* Dismiss button */}
      <TouchableOpacity
        style={styles.dismissButton}
        onPress={handleDismiss}
        accessibilityLabel="Dismiss"
        accessibilityRole="button"
      >
        <MaterialIcons name="close" size={16} color="#FFFFFF" />
      </TouchableOpacity>
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    width: 180,
    minHeight: 100,
    zIndex: 100,
  },
  blurContainer: {
    borderRadius: 12,
    overflow: 'hidden',
  },
  gradientBorder: {
    padding: 2,
    borderRadius: 12,
  },
  content: {
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    borderRadius: 10,
    padding: 12,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  iconContainer: {
    marginRight: 8,
  },
  title: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: 'bold',
    flex: 1,
  },
  progressContainer: {
    height: 2,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    borderRadius: 1,
    marginBottom: 8,
    overflow: 'hidden',
  },
  progressBar: {
    height: '100%',
    backgroundColor: '#FFFFFF',
    borderRadius: 1,
  },
  info: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
  },
  distance: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '500',
  },
  eta: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '500',
    marginLeft: 6,
  },
  voiceCTA: {
    color: 'rgba(255, 255, 255, 0.8)',
    fontSize: 12,
    fontStyle: 'italic',
    flexDirection: 'row',
    alignItems: 'center',
  },
  dismissButton: {
    position: 'absolute',
    top: -8,
    right: -8,
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 101,
  },
  glowEffect: {
    position: 'absolute',
    top: -10,
    left: -10,
    right: -10,
    bottom: -10,
    borderRadius: 22,
    backgroundColor: 'transparent',
    borderWidth: 2,
    borderColor: '#FFFFFF',
    shadowColor: '#FFFFFF',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 10,
  },
});

export default ARPointOfInterest;