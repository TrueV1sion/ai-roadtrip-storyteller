/**
 * FAANG-Quality Theme System
 * Central theme configuration for AI Road Trip Storyteller
 */

import { colors, darkColors, getGradient, withOpacity } from './tokens/colors';
import { typeScale, fontFamily, fontWeight, getTypography } from './tokens/typography';
import { spacing, componentSpacing, layout, safeArea } from './tokens/spacing';
import { elevation, specialEffects, getElevation, componentElevation } from './tokens/elevation';
import { timing, duration, spring, animations, gestures } from './tokens/animation';

// Light theme configuration
export const lightTheme = {
  // Design tokens
  colors,
  typography: typeScale,
  spacing,
  elevation,
  animation: {
    timing,
    duration,
    spring,
    animations,
    gestures,
  },
  
  // Component-specific theming
  components: {
    spacing: componentSpacing,
    elevation: componentElevation,
  },
  
  // Layout configuration
  layout,
  safeArea,
  
  // Helper functions
  utils: {
    getGradient,
    withOpacity,
    getTypography,
    getElevation,
  },
  
  // Theme metadata
  isDark: false,
  name: 'light',
};

// Dark theme configuration
export const darkTheme = {
  ...lightTheme,
  colors: darkColors,
  
  // Dark mode specific adjustments
  elevation: {
    ...elevation,
    // Reduce shadow intensity in dark mode
    low: getElevation(1),
    medium: getElevation(2),
    high: getElevation(4),
    highest: getElevation(8),
  },
  
  // Theme metadata
  isDark: true,
  name: 'dark',
};

// Type definitions
export type Theme = typeof lightTheme;
export type ThemeColors = typeof colors;
export type ThemeTypography = typeof typeScale;
export type ThemeSpacing = typeof spacing;
export type ThemeElevation = typeof elevation;
export type ThemeAnimation = typeof animations;

// Default export
export default lightTheme;

// Named exports for convenience
export {
  colors,
  darkColors,
  typeScale,
  spacing,
  elevation,
  animations,
  fontFamily,
  fontWeight,
  specialEffects,
};

// Theme context type for React Context
export interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
  isSystemTheme: boolean;
  setSystemTheme: (useSystem: boolean) => void;
}

// Semantic theme mappings
export const semanticColors = {
  // Backgrounds
  background: {
    primary: 'surface.background',
    secondary: 'surface.card',
    elevated: 'surface.elevated',
    overlay: 'surface.overlay',
  },
  
  // Text
  text: {
    primary: 'text.primary',
    secondary: 'text.secondary',
    tertiary: 'text.tertiary',
    inverse: 'text.inverse',
    disabled: 'text.disabled',
  },
  
  // Interactive elements
  interactive: {
    primary: 'primary.500',
    primaryHover: 'primary.600',
    primaryActive: 'primary.700',
    secondary: 'secondary.500',
    secondaryHover: 'secondary.600',
    secondaryActive: 'secondary.700',
  },
  
  // Status
  status: {
    success: 'success',
    warning: 'warning',
    error: 'error',
    info: 'info',
  },
  
  // Special
  special: {
    aurora: 'aurora',
    gradient: 'gradients',
  },
};

// Component theme variants
export const variants = {
  button: {
    primary: {
      backgroundColor: colors.primary[500],
      color: colors.text.inverse,
      pressedBackgroundColor: colors.primary[600],
    },
    secondary: {
      backgroundColor: colors.secondary[500],
      color: colors.text.inverse,
      pressedBackgroundColor: colors.secondary[600],
    },
    ghost: {
      backgroundColor: 'transparent',
      color: colors.primary[500],
      pressedBackgroundColor: withOpacity(colors.primary[500], 0.1),
    },
    danger: {
      backgroundColor: colors.error,
      color: colors.text.inverse,
      pressedBackgroundColor: withOpacity(colors.error, 0.8),
    },
  },
  
  card: {
    default: {
      backgroundColor: colors.surface.card,
      borderColor: colors.neutral[200],
      ...componentElevation.card,
    },
    elevated: {
      backgroundColor: colors.surface.elevated,
      borderColor: 'transparent',
      ...componentElevation.cardHover,
    },
    ghost: {
      backgroundColor: withOpacity(colors.surface.card, 0.5),
      borderColor: withOpacity(colors.neutral[200], 0.3),
      ...elevation.none,
    },
  },
  
  input: {
    default: {
      backgroundColor: colors.surface.card,
      borderColor: colors.neutral[300],
      focusBorderColor: colors.primary[500],
    },
    filled: {
      backgroundColor: colors.neutral[100],
      borderColor: 'transparent',
      focusBorderColor: colors.primary[500],
    },
    outlined: {
      backgroundColor: 'transparent',
      borderColor: colors.neutral[300],
      focusBorderColor: colors.primary[500],
    },
  },
};