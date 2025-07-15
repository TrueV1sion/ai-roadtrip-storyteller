/**
 * PrimaryButton Component
 * Beautiful button from Bolt's design system
 */

import React from 'react';
import {
  TouchableOpacity,
  Text,
  StyleSheet,
  ActivityIndicator,
  View,
  ViewStyle,
  TextStyle,
} from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSpring,
} from 'react-native-reanimated';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { unifiedTheme } from '../../theme/unified';

interface PrimaryButtonProps {
  title: string;
  onPress: () => void;
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'small' | 'medium' | 'large';
  icon?: string;
  iconPosition?: 'left' | 'right';
  loading?: boolean;
  disabled?: boolean;
  fullWidth?: boolean;
  style?: ViewStyle;
  textStyle?: TextStyle;
}

const AnimatedTouchable = Animated.createAnimatedComponent(TouchableOpacity);

export const PrimaryButton: React.FC<PrimaryButtonProps> = ({
  title,
  onPress,
  variant = 'primary',
  size = 'medium',
  icon,
  iconPosition = 'left',
  loading = false,
  disabled = false,
  fullWidth = false,
  style,
  textStyle,
}) => {
  const scale = useSharedValue(1);

  const handlePressIn = () => {
    scale.value = withSpring(0.95, unifiedTheme.animations.spring.gentle);
  };

  const handlePressOut = () => {
    scale.value = withSpring(1, unifiedTheme.animations.spring.bouncy);
  };

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  const buttonStyles = [
    styles.base,
    styles[variant],
    styles[size],
    fullWidth && styles.fullWidth,
    disabled && styles.disabled,
    style,
  ];

  const textStyles = [
    styles.text,
    styles[`text_${variant}`],
    styles[`text_${size}`],
    textStyle,
  ];

  const iconSize = {
    small: 16,
    medium: 20,
    large: 24,
  }[size];

  const iconColor = {
    primary: 'white',
    secondary: unifiedTheme.colors.primary[600],
    ghost: unifiedTheme.colors.primary[600],
  }[variant];

  return (
    <AnimatedTouchable
      onPress={onPress}
      onPressIn={handlePressIn}
      onPressOut={handlePressOut}
      disabled={disabled || loading}
      activeOpacity={1}
      style={[buttonStyles, animatedStyle]}
    >
      <View style={styles.content}>
        {loading ? (
          <ActivityIndicator
            size="small"
            color={iconColor}
          />
        ) : (
          <>
            {icon && iconPosition === 'left' && (
              <MaterialCommunityIcons
                name={icon as any}
                size={iconSize}
                color={iconColor}
                style={styles.iconLeft}
              />
            )}
            <Text style={textStyles}>{title}</Text>
            {icon && iconPosition === 'right' && (
              <MaterialCommunityIcons
                name={icon as any}
                size={iconSize}
                color={iconColor}
                style={styles.iconRight}
              />
            )}
          </>
        )}
      </View>
    </AnimatedTouchable>
  );
};

const styles = StyleSheet.create({
  base: {
    borderRadius: unifiedTheme.borderRadius.lg,
    overflow: 'hidden',
    alignSelf: 'flex-start',
  },
  
  // Variants
  primary: {
    backgroundColor: unifiedTheme.colors.primary[600],
    ...unifiedTheme.shadows.base,
  },
  secondary: {
    backgroundColor: unifiedTheme.colors.primary[50],
    borderWidth: 1,
    borderColor: unifiedTheme.colors.primary[200],
  },
  ghost: {
    backgroundColor: 'transparent',
  },
  
  // Sizes
  small: {
    paddingHorizontal: unifiedTheme.spacing[3],
    paddingVertical: unifiedTheme.spacing[2],
  },
  medium: {
    paddingHorizontal: unifiedTheme.spacing[5],
    paddingVertical: unifiedTheme.spacing[3],
  },
  large: {
    paddingHorizontal: unifiedTheme.spacing[6],
    paddingVertical: unifiedTheme.spacing[4],
  },
  
  // States
  fullWidth: {
    alignSelf: 'stretch',
  },
  disabled: {
    opacity: 0.5,
  },
  
  // Content
  content: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  
  // Text styles
  text: {
    ...unifiedTheme.typography.button,
  },
  text_primary: {
    color: 'white',
  },
  text_secondary: {
    color: unifiedTheme.colors.primary[600],
  },
  text_ghost: {
    color: unifiedTheme.colors.primary[600],
  },
  text_small: {
    ...unifiedTheme.typography.buttonSmall,
  },
  text_medium: {
    ...unifiedTheme.typography.button,
  },
  text_large: {
    ...unifiedTheme.typography.buttonLarge,
  },
  
  // Icons
  iconLeft: {
    marginRight: unifiedTheme.spacing[2],
  },
  iconRight: {
    marginLeft: unifiedTheme.spacing[2],
  },
});
