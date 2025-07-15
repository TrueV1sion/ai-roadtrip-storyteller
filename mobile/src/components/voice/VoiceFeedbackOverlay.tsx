import React, { useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Animated,
  Dimensions,
  Platform,
} from 'react-native';
import { BlurView } from 'expo-blur';
import { LinearGradient } from 'expo-linear-gradient';

interface VoiceFeedbackOverlayProps {
  message: string;
  type: 'info' | 'success' | 'warning' | 'error' | 'listening';
  duration?: number;
  onHide?: () => void;
}

const { width: SCREEN_WIDTH } = Dimensions.get('window');

export const VoiceFeedbackOverlay: React.FC<VoiceFeedbackOverlayProps> = ({
  message,
  type,
  duration = 3000,
  onHide,
}) => {
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(-100)).current;
  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    // Animate in
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 300,
        useNativeDriver: true,
      }),
      Animated.spring(slideAnim, {
        toValue: 0,
        tension: 50,
        friction: 8,
        useNativeDriver: true,
      }),
    ]).start();

    // Pulse animation for listening state
    if (type === 'listening') {
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
    }

    // Auto-hide after duration (except for listening state)
    if (type !== 'listening' && duration > 0) {
      const timer = setTimeout(() => {
        animateOut();
      }, duration);

      return () => clearTimeout(timer);
    }
  }, [type]);

  const animateOut = () => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 0,
        duration: 300,
        useNativeDriver: true,
      }),
      Animated.timing(slideAnim, {
        toValue: -100,
        duration: 300,
        useNativeDriver: true,
      }),
    ]).start(() => {
      onHide?.();
    });
  };

  const getTypeStyles = () => {
    switch (type) {
      case 'success':
        return {
          backgroundColor: 'rgba(76, 175, 80, 0.9)',
          iconColor: '#FFFFFF',
          gradientColors: ['rgba(76, 175, 80, 0.9)', 'rgba(56, 142, 60, 0.9)'],
        };
      case 'warning':
        return {
          backgroundColor: 'rgba(255, 152, 0, 0.9)',
          iconColor: '#FFFFFF',
          gradientColors: ['rgba(255, 152, 0, 0.9)', 'rgba(245, 124, 0, 0.9)'],
        };
      case 'error':
        return {
          backgroundColor: 'rgba(244, 67, 54, 0.9)',
          iconColor: '#FFFFFF',
          gradientColors: ['rgba(244, 67, 54, 0.9)', 'rgba(211, 47, 47, 0.9)'],
        };
      case 'listening':
        return {
          backgroundColor: 'rgba(0, 122, 255, 0.9)',
          iconColor: '#FFFFFF',
          gradientColors: ['rgba(0, 122, 255, 0.9)', 'rgba(0, 86, 179, 0.9)'],
        };
      default:
        return {
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          iconColor: '#FFFFFF',
          gradientColors: ['rgba(0, 0, 0, 0.8)', 'rgba(33, 33, 33, 0.8)'],
        };
    }
  };

  const typeStyles = getTypeStyles();

  return (
    <Animated.View
      style={[
        styles.container,
        {
          opacity: fadeAnim,
          transform: [
            { translateY: slideAnim },
            { scale: type === 'listening' ? pulseAnim : 1 },
          ],
        },
      ]}
      pointerEvents="none"
    >
      <BlurView intensity={Platform.OS === 'ios' ? 80 : 120} style={styles.blur}>
        <LinearGradient
          colors={typeStyles.gradientColors}
          style={styles.gradient}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
        >
          <View style={styles.content}>
            {type === 'listening' && (
              <View style={styles.listeningIndicator}>
                <View style={[styles.dot, { animationDelay: '0ms' }]} />
                <View style={[styles.dot, { animationDelay: '200ms' }]} />
                <View style={[styles.dot, { animationDelay: '400ms' }]} />
              </View>
            )}
            <Text style={styles.message} numberOfLines={2}>
              {message}
            </Text>
          </View>
        </LinearGradient>
      </BlurView>
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    top: 100,
    left: 20,
    right: 20,
    maxWidth: SCREEN_WIDTH - 40,
    alignSelf: 'center',
    borderRadius: 16,
    overflow: 'hidden',
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.3,
        shadowRadius: 8,
      },
      android: {
        elevation: 8,
      },
    }),
  },
  blur: {
    flex: 1,
  },
  gradient: {
    flex: 1,
    padding: 20,
  },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  message: {
    fontSize: 18,
    fontWeight: '600',
    color: '#FFFFFF',
    textAlign: 'center',
    flex: 1,
  },
  listeningIndicator: {
    flexDirection: 'row',
    marginRight: 12,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#FFFFFF',
    marginHorizontal: 2,
    ...Platform.select({
      ios: {
        animationName: 'pulse',
        animationDuration: '1.4s',
        animationIterationCount: 'infinite',
      },
    }),
  },
});