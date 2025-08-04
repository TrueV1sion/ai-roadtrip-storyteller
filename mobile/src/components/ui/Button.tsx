import React from 'react';
import {
  TouchableOpacity,
  Text,
  StyleSheet,
  ViewStyle,
  TextStyle,
  ActivityIndicator,
  View,
} from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  withTiming,
  interpolate,
  Extrapolate,
} from 'react-native-reanimated';
import { Haptics } from 'expo-haptics';

export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
export type ButtonSize = 'small' | 'medium' | 'large';

interface ButtonProps {
  variant?: ButtonVariant;
  size?: ButtonSize;
  onPress: () => void;
  onLongPress?: () => void;
  disabled?: boolean;
  loading?: boolean;
  fullWidth?: boolean;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  hapticFeedback?: boolean;
  style?: ViewStyle;
  textStyle?: TextStyle;
  children: React.ReactNode;
}

const AnimatedTouchable = Animated.createAnimatedComponent(TouchableOpacity);

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'medium',
  onPress,
  onLongPress,
  disabled = false,
  loading = false,
  fullWidth = false,
  icon,
  iconPosition = 'left',
  hapticFeedback = true,
  style,
  textStyle,
  children,
}) => {
  const scale = useSharedValue(1);
  const opacity = useSharedValue(1);

  const handlePressIn = () => {
    'worklet';
    scale.value = withSpring(0.95, { damping: 15, stiffness: 400 });
    opacity.value = withTiming(0.8, { duration: 100 });
  };

  const handlePressOut = () => {
    'worklet';
    scale.value = withSpring(1, { damping: 15, stiffness: 400 });
    opacity.value = withTiming(1, { duration: 100 });
  };

  const handlePress = () => {
    if (hapticFeedback) {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    }
    onPress();
  };

  const animatedStyle = useAnimatedStyle(() => {
    return {
      transform: [{ scale: scale.value }],
      opacity: interpolate(
        opacity.value,
        [0.8, 1],
        [0.8, disabled ? 0.5 : 1],
        Extrapolate.CLAMP
      ),
    };
  });

  const buttonStyles = [
    styles.button,
    styles[variant],
    styles[size],
    fullWidth && styles.fullWidth,
    disabled && styles.disabled,
    style,
  ];

  const textStyles = [
    styles.text,
    styles[`${variant}Text`],
    styles[`${size}Text`],
    textStyle,
  ];

  const iconContainerStyle = [
    styles.iconContainer,
    iconPosition === 'right' && styles.iconRight,
  ];

  const LoadingIndicator = () => (
    <ActivityIndicator
      size={size === 'small' ? 'small' : 'small'}
      color={variant === 'primary' ? '#FFFFFF' : '#7c3aed'}
      style={styles.loader}
    />
  );

  return (
    <AnimatedTouchable
      onPress={handlePress}
      onLongPress={onLongPress}
      onPressIn={handlePressIn}
      onPressOut={handlePressOut}
      disabled={disabled || loading}
      activeOpacity={0.8}
      style={[buttonStyles, animatedStyle]}
    >
      {loading ? (
        <LoadingIndicator />
      ) : (
        <View style={styles.content}>
          {icon && iconPosition === 'left' && (
            <View style={iconContainerStyle}>{icon}</View>
          )}
          <Text style={textStyles}>{children}</Text>
          {icon && iconPosition === 'right' && (
            <View style={iconContainerStyle}>{icon}</View>
          )}
        </View>
      )}
    </AnimatedTouchable>
  );
};

const styles = StyleSheet.create({
  button: {
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
  },
  
  // Variants
  primary: {
    backgroundColor: '#7c3aed',
  },
  secondary: {
    backgroundColor: '#4f46e5',
  },
  outline: {
    backgroundColor: 'transparent',
    borderWidth: 2,
    borderColor: '#374151',
  },
  ghost: {
    backgroundColor: 'transparent',
  },
  danger: {
    backgroundColor: '#ef4444',
  },
  
  // Sizes
  small: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    minHeight: 36,
  },
  medium: {
    paddingHorizontal: 24,
    paddingVertical: 12,
    minHeight: 44,
  },
  large: {
    paddingHorizontal: 32,
    paddingVertical: 16,
    minHeight: 52,
  },
  
  // Text styles
  text: {
    fontFamily: 'Inter-SemiBold',
    textAlign: 'center',
  },
  primaryText: {
    color: '#FFFFFF',
  },
  secondaryText: {
    color: '#FFFFFF',
  },
  outlineText: {
    color: '#9ca3af',
  },
  ghostText: {
    color: '#9ca3af',
  },
  dangerText: {
    color: '#FFFFFF',
  },
  
  // Text sizes
  smallText: {
    fontSize: 14,
  },
  mediumText: {
    fontSize: 16,
  },
  largeText: {
    fontSize: 18,
  },
  
  // States
  disabled: {
    opacity: 0.5,
  },
  fullWidth: {
    width: '100%',
  },
  
  // Content
  content: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconContainer: {
    marginRight: 8,
  },
  iconRight: {
    marginRight: 0,
    marginLeft: 8,
  },
  loader: {
    marginVertical: 2,
  },
});

export default Button;