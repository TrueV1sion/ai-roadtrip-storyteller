import React from 'react';
import {
  TouchableOpacity,
  Text,
  StyleSheet,
  ActivityIndicator,
  ViewStyle,
  TextStyle,
} from 'react-native';
import { THEME } from '@/config';

interface ButtonProps {
  onPress: () => void;
  title: string;
  variant?: 'primary' | 'secondary' | 'outline';
  size?: 'small' | 'medium' | 'large';
  disabled?: boolean;
  loading?: boolean;
  style?: ViewStyle;
  textStyle?: TextStyle;
  fullWidth?: boolean;
}

export function Button({
  onPress,
  title,
  variant = 'primary',
  size = 'medium',
  disabled = false,
  loading = false,
  style,
  textStyle,
  fullWidth = false,
}: ButtonProps) {
  const getBackgroundColor = () => {
    if (disabled) return '#e0e0e0';
    switch (variant) {
      case 'primary':
        return THEME.colors.primary;
      case 'secondary':
        return THEME.colors.secondary;
      case 'outline':
        return 'transparent';
      default:
        return THEME.colors.primary;
    }
  };

  const getTextColor = () => {
    if (disabled) return '#757575';
    switch (variant) {
      case 'primary':
      case 'secondary':
        return '#ffffff';
      case 'outline':
        return THEME.colors.primary;
      default:
        return '#ffffff';
    }
  };

  const getPadding = () => {
    switch (size) {
      case 'small':
        return THEME.spacing.sm;
      case 'large':
        return THEME.spacing.lg;
      default:
        return THEME.spacing.md;
    }
  };

  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={disabled || loading}
      style={[
        styles.button,
        {
          backgroundColor: getBackgroundColor(),
          padding: getPadding(),
          borderWidth: variant === 'outline' ? 2 : 0,
          borderColor: THEME.colors.primary,
          width: fullWidth ? '100%' : undefined,
        },
        style,
      ]}
      testID="button-container"
    >
      {loading ? (
        <ActivityIndicator 
          color={getTextColor()} 
          testID="activity-indicator"
        />
      ) : (
        <Text
          style={[
            styles.text,
            {
              color: getTextColor(),
              fontSize: size === 'small' ? 14 : size === 'large' ? 18 : 16,
            },
            textStyle,
          ]}
          testID="button-text"
        >
          {title}
        </Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  button: {
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  text: {
    fontWeight: '600',
    textAlign: 'center',
  },
}); 