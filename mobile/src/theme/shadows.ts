/**
 * Shadow system for elevation and depth
 * Platform-specific implementations for iOS and Android
 */

import { Platform } from 'react-native';

export const shadows = {
  // No elevation
  none: {
    ...Platform.select({
      ios: {
        shadowColor: 'transparent',
        shadowOffset: { width: 0, height: 0 },
        shadowOpacity: 0,
        shadowRadius: 0,
      },
      android: {
        elevation: 0,
      },
    }),
  },
  
  // Subtle elevation (cards, inputs)
  sm: {
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.05,
        shadowRadius: 2,
      },
      android: {
        elevation: 2,
      },
    }),
  },
  
  // Default elevation (buttons, cards)
  md: {
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
      },
      android: {
        elevation: 4,
      },
    }),
  },
  
  // Medium elevation (modals, popups)
  lg: {
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.15,
        shadowRadius: 8,
      },
      android: {
        elevation: 8,
      },
    }),
  },
  
  // High elevation (dropdowns, tooltips)
  xl: {
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 8 },
        shadowOpacity: 0.2,
        shadowRadius: 16,
      },
      android: {
        elevation: 16,
      },
    }),
  },
  
  // Maximum elevation (sticky elements)
  xxl: {
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 16 },
        shadowOpacity: 0.25,
        shadowRadius: 32,
      },
      android: {
        elevation: 24,
      },
    }),
  },
  
  // Colored shadows for brand elements
  brand: {
    ...Platform.select({
      ios: {
        shadowColor: '#7c3aed',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.3,
        shadowRadius: 8,
      },
      android: {
        elevation: 8,
        // Android doesn't support colored shadows natively
        // Consider using a View with opacity as workaround
      },
    }),
  },
  
  // Glow effect for active elements
  glow: {
    ...Platform.select({
      ios: {
        shadowColor: '#7c3aed',
        shadowOffset: { width: 0, height: 0 },
        shadowOpacity: 0.5,
        shadowRadius: 20,
      },
      android: {
        elevation: 0,
        // Use custom implementation for glow on Android
      },
    }),
  },
  
  // Inner shadow (inset effect)
  inner: {
    // React Native doesn't support inner shadows natively
    // This would require a custom implementation
    ...Platform.select({
      ios: {},
      android: {},
    }),
  },
};

// Dynamic shadow generator
export const createShadow = (
  elevation: number,
  color: string = '#000',
  opacity?: number
) => {
  const shadowOpacity = opacity || (0.05 + elevation * 0.01);
  const shadowRadius = elevation * 0.5;
  
  return Platform.select({
    ios: {
      shadowColor: color,
      shadowOffset: {
        width: 0,
        height: elevation * 0.5,
      },
      shadowOpacity: Math.min(shadowOpacity, 0.3),
      shadowRadius,
    },
    android: {
      elevation: Math.min(elevation, 24),
    },
  });
};

// Animated shadow helper
export const animatedShadow = (
  animatedValue: any,
  minElevation: number = 0,
  maxElevation: number = 16
) => {
  if (Platform.OS === 'ios') {
    return {
      shadowOpacity: animatedValue.interpolate({
        inputRange: [0, 1],
        outputRange: [0.05 + minElevation * 0.01, 0.05 + maxElevation * 0.01],
      }),
      shadowRadius: animatedValue.interpolate({
        inputRange: [0, 1],
        outputRange: [minElevation * 0.5, maxElevation * 0.5],
      }),
      shadowOffset: {
        width: 0,
        height: animatedValue.interpolate({
          inputRange: [0, 1],
          outputRange: [minElevation * 0.5, maxElevation * 0.5],
        }),
      },
    };
  } else {
    return {
      elevation: animatedValue.interpolate({
        inputRange: [0, 1],
        outputRange: [minElevation, Math.min(maxElevation, 24)],
      }),
    };
  }
};