import React, { useState, useRef } from 'react';
import {
  TextInput,
  View,
  Text,
  StyleSheet,
  TextInputProps,
  TouchableOpacity,
  ViewStyle,
  TextStyle,
} from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  interpolate,
  Extrapolate,
} from 'react-native-reanimated';
import { Eye, EyeOff } from 'lucide-react-native';

interface InputProps extends Omit<TextInputProps, 'style'> {
  label?: string;
  error?: string;
  hint?: string;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  variant?: 'default' | 'filled' | 'outlined';
  size?: 'small' | 'medium' | 'large';
  fullWidth?: boolean;
  containerStyle?: ViewStyle;
  inputStyle?: TextStyle;
  labelStyle?: TextStyle;
  errorStyle?: TextStyle;
  hintStyle?: TextStyle;
}

export const Input: React.FC<InputProps> = ({
  label,
  error,
  hint,
  icon,
  iconPosition = 'left',
  variant = 'default',
  size = 'medium',
  fullWidth = false,
  containerStyle,
  inputStyle,
  labelStyle,
  errorStyle,
  hintStyle,
  secureTextEntry,
  value,
  onFocus,
  onBlur,
  ...textInputProps
}) => {
  const [isFocused, setIsFocused] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const inputRef = useRef<TextInput>(null);
  
  const focusAnimation = useSharedValue(0);
  const errorAnimation = useSharedValue(error ? 1 : 0);

  const handleFocus = (e: any) => {
    setIsFocused(true);
    focusAnimation.value = withTiming(1, { duration: 200 });
    onFocus?.(e);
  };

  const handleBlur = (e: any) => {
    setIsFocused(false);
    focusAnimation.value = withTiming(0, { duration: 200 });
    onBlur?.(e);
  };

  React.useEffect(() => {
    errorAnimation.value = withTiming(error ? 1 : 0, { duration: 200 });
  }, [error]);

  const animatedContainerStyle = useAnimatedStyle(() => {
    const borderColor = interpolate(
      errorAnimation.value,
      [0, 1],
      [0, 1],
      Extrapolate.CLAMP
    );

    const focusBorderColor = interpolate(
      focusAnimation.value,
      [0, 1],
      [0, 1],
      Extrapolate.CLAMP
    );

    return {
      borderColor: error
        ? '#ef4444'
        : isFocused
        ? '#7c3aed'
        : '#374151',
      transform: [
        {
          scale: interpolate(
            focusAnimation.value,
            [0, 1],
            [1, 1.01],
            Extrapolate.CLAMP
          ),
        },
      ],
    };
  });

  const animatedLabelStyle = useAnimatedStyle(() => {
    const hasValue = value && value.length > 0;
    const shouldFloat = isFocused || hasValue;

    return {
      transform: [
        {
          translateY: interpolate(
            shouldFloat ? 1 : 0,
            [0, 1],
            [0, -24],
            Extrapolate.CLAMP
          ),
        },
        {
          scale: interpolate(
            shouldFloat ? 1 : 0,
            [0, 1],
            [1, 0.85],
            Extrapolate.CLAMP
          ),
        },
      ],
    };
  });

  const containerStyles = [
    styles.container,
    fullWidth && styles.fullWidth,
    containerStyle,
  ];

  const inputContainerStyles = [
    styles.inputContainer,
    styles[variant],
    styles[size],
    error && styles.errorContainer,
  ];

  const inputStyles = [
    styles.input,
    styles[`${size}Input`],
    icon && iconPosition === 'left' && styles.inputWithLeftIcon,
    icon && iconPosition === 'right' && styles.inputWithRightIcon,
    secureTextEntry && styles.inputWithRightIcon,
    inputStyle,
  ];

  const labelStyles = [
    styles.label,
    isFocused && styles.labelFocused,
    error && styles.labelError,
    labelStyle,
  ];

  return (
    <View style={containerStyles}>
      {label && (
        <Animated.Text style={[labelStyles, animatedLabelStyle]}>
          {label}
        </Animated.Text>
      )}
      
      <Animated.View style={[inputContainerStyles, animatedContainerStyle]}>
        {icon && iconPosition === 'left' && (
          <View style={styles.iconLeft}>{icon}</View>
        )}
        
        <TextInput
          ref={inputRef}
          value={value}
          onFocus={handleFocus}
          onBlur={handleBlur}
          secureTextEntry={secureTextEntry && !showPassword}
          placeholderTextColor="#6b7280"
          style={inputStyles}
          {...textInputProps}
        />
        
        {icon && iconPosition === 'right' && !secureTextEntry && (
          <View style={styles.iconRight}>{icon}</View>
        )}
        
        {secureTextEntry && (
          <TouchableOpacity
            onPress={() => setShowPassword(!showPassword)}
            style={styles.iconRight}
          >
            {showPassword ? (
              <EyeOff size={20} color="#6b7280" />
            ) : (
              <Eye size={20} color="#6b7280" />
            )}
          </TouchableOpacity>
        )}
      </Animated.View>
      
      {error && (
        <Animated.Text
          style={[
            styles.error,
            errorStyle,
            {
              opacity: errorAnimation.value,
              transform: [
                {
                  translateY: interpolate(
                    errorAnimation.value,
                    [0, 1],
                    [-10, 0],
                    Extrapolate.CLAMP
                  ),
                },
              ],
            },
          ]}
        >
          {error}
        </Animated.Text>
      )}
      
      {hint && !error && (
        <Text style={[styles.hint, hintStyle]}>{hint}</Text>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginBottom: 20,
  },
  fullWidth: {
    width: '100%',
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: 12,
    overflow: 'hidden',
  },
  
  // Variants
  default: {
    backgroundColor: '#1a1a2e',
    borderWidth: 2,
    borderColor: '#374151',
  },
  filled: {
    backgroundColor: '#1a1a2e',
    borderWidth: 0,
  },
  outlined: {
    backgroundColor: 'transparent',
    borderWidth: 2,
    borderColor: '#374151',
  },
  
  // Sizes
  small: {
    height: 40,
    paddingHorizontal: 12,
  },
  medium: {
    height: 48,
    paddingHorizontal: 16,
  },
  large: {
    height: 56,
    paddingHorizontal: 20,
  },
  
  // Input
  input: {
    flex: 1,
    color: '#ffffff',
    fontFamily: 'Inter-Regular',
  },
  smallInput: {
    fontSize: 14,
  },
  mediumInput: {
    fontSize: 16,
  },
  largeInput: {
    fontSize: 18,
  },
  inputWithLeftIcon: {
    paddingLeft: 0,
  },
  inputWithRightIcon: {
    paddingRight: 0,
  },
  
  // Icons
  iconLeft: {
    marginRight: 12,
  },
  iconRight: {
    marginLeft: 12,
  },
  
  // Label
  label: {
    position: 'absolute',
    left: 16,
    top: 14,
    fontSize: 16,
    fontFamily: 'Inter-Regular',
    color: '#9ca3af',
    backgroundColor: '#0f0f23',
    paddingHorizontal: 4,
    zIndex: 1,
  },
  labelFocused: {
    color: '#7c3aed',
  },
  labelError: {
    color: '#ef4444',
  },
  
  // Error & Hint
  error: {
    fontSize: 12,
    fontFamily: 'Inter-Regular',
    color: '#ef4444',
    marginTop: 4,
    marginLeft: 16,
  },
  hint: {
    fontSize: 12,
    fontFamily: 'Inter-Regular',
    color: '#6b7280',
    marginTop: 4,
    marginLeft: 16,
  },
  
  // States
  errorContainer: {
    borderColor: '#ef4444',
  },
});

export default Input;