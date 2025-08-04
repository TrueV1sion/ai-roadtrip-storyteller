import React from 'react';
import {
  View,
  StyleSheet,
  ViewStyle,
  TouchableOpacity,
  Platform,
} from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  interpolate,
  Extrapolate,
} from 'react-native-reanimated';

interface CardProps {
  onPress?: () => void;
  elevation?: 'none' | 'low' | 'medium' | 'high';
  variant?: 'default' | 'bordered' | 'filled';
  padding?: 'none' | 'small' | 'medium' | 'large';
  margin?: 'none' | 'small' | 'medium' | 'large';
  backgroundColor?: string;
  borderColor?: string;
  borderRadius?: number;
  style?: ViewStyle;
  animatePress?: boolean;
  children: React.ReactNode;
}

const AnimatedTouchable = Animated.createAnimatedComponent(TouchableOpacity);

export const Card: React.FC<CardProps> = ({
  onPress,
  elevation = 'low',
  variant = 'default',
  padding = 'medium',
  margin = 'none',
  backgroundColor = '#1a1a2e',
  borderColor = '#374151',
  borderRadius = 16,
  style,
  animatePress = true,
  children,
}) => {
  const scale = useSharedValue(1);
  const shadowScale = useSharedValue(1);

  const handlePressIn = () => {
    if (animatePress && onPress) {
      'worklet';
      scale.value = withSpring(0.98, { damping: 15, stiffness: 400 });
      shadowScale.value = withSpring(0.8, { damping: 15, stiffness: 400 });
    }
  };

  const handlePressOut = () => {
    if (animatePress && onPress) {
      'worklet';
      scale.value = withSpring(1, { damping: 15, stiffness: 400 });
      shadowScale.value = withSpring(1, { damping: 15, stiffness: 400 });
    }
  };

  const animatedStyle = useAnimatedStyle(() => {
    const shadowRadius = interpolate(
      shadowScale.value,
      [0.8, 1],
      [
        elevationStyles[elevation]?.shadowRadius * 0.8 || 0,
        elevationStyles[elevation]?.shadowRadius || 0,
      ],
      Extrapolate.CLAMP
    );

    const shadowOpacity = interpolate(
      shadowScale.value,
      [0.8, 1],
      [
        elevationStyles[elevation]?.shadowOpacity * 0.8 || 0,
        elevationStyles[elevation]?.shadowOpacity || 0,
      ],
      Extrapolate.CLAMP
    );

    return {
      transform: [{ scale: scale.value }],
      ...Platform.select({
        ios: {
          shadowRadius,
          shadowOpacity,
        },
        android: {},
      }),
    };
  });

  const cardStyles = [
    styles.card,
    elevationStyles[elevation],
    variantStyles[variant],
    paddingStyles[padding],
    marginStyles[margin],
    {
      backgroundColor: variant === 'filled' ? backgroundColor : 'transparent',
      borderColor: variant === 'bordered' ? borderColor : 'transparent',
      borderRadius,
    },
    style,
  ];

  if (onPress) {
    return (
      <AnimatedTouchable
        onPress={onPress}
        onPressIn={handlePressIn}
        onPressOut={handlePressOut}
        activeOpacity={0.8}
        style={[cardStyles, animatedStyle]}
      >
        {children}
      </AnimatedTouchable>
    );
  }

  return (
    <Animated.View style={[cardStyles, animatedStyle]}>
      {children}
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  card: {
    overflow: 'hidden',
  },
});

const elevationStyles = StyleSheet.create({
  none: {},
  low: {
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
      },
      android: {
        elevation: 2,
      },
    }),
  },
  medium: {
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.15,
        shadowRadius: 8,
      },
      android: {
        elevation: 4,
      },
    }),
  },
  high: {
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 8 },
        shadowOpacity: 0.2,
        shadowRadius: 16,
      },
      android: {
        elevation: 8,
      },
    }),
  },
});

const variantStyles = StyleSheet.create({
  default: {
    backgroundColor: '#1a1a2e',
  },
  bordered: {
    backgroundColor: 'transparent',
    borderWidth: 2,
  },
  filled: {
    // Background color is set dynamically
  },
});

const paddingStyles = StyleSheet.create({
  none: {
    padding: 0,
  },
  small: {
    padding: 12,
  },
  medium: {
    padding: 16,
  },
  large: {
    padding: 24,
  },
});

const marginStyles = StyleSheet.create({
  none: {
    margin: 0,
  },
  small: {
    margin: 8,
  },
  medium: {
    margin: 16,
  },
  large: {
    margin: 24,
  },
});

export default Card;