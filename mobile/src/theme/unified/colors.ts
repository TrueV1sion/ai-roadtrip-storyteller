/**
 * Unified Color System
 * Combines Bolt's beautiful aesthetic with RoadTrip's semantic needs
 */

export const colors = {
  // Primary Brand Colors (from Bolt)
  primary: {
    50: '#f5f3ff',
    100: '#ede9fe',
    200: '#ddd6fe',
    300: '#c4b5fd',
    400: '#a78bfa',
    500: '#8b5cf6',
    600: '#7c3aed', // Main brand color
    700: '#6d28d9',
    800: '#5b21b6',
    900: '#4c1d95',
  },

  // Secondary Colors (from Bolt)
  secondary: {
    50: '#ecfdf5',
    100: '#d1fae5',
    200: '#a7f3d0',
    300: '#6ee7b7',
    400: '#34d399',
    500: '#10b981', // Success green
    600: '#059669',
    700: '#047857',
    800: '#065f46',
    900: '#064e3b',
  },

  // Accent Colors (from Bolt's personality cards)
  accent: {
    red: '#ff6b6b',
    orange: '#f59e0b',
    blue: '#45b7d1',
    teal: '#4ecdc4',
    purple: '#7c3aed',
    pink: '#ec4899',
  },

  // Neutral Colors
  neutral: {
    50: '#fafafa',
    100: '#f5f5f5',
    200: '#e5e5e5',
    300: '#d4d4d4',
    400: '#a3a3a3',
    500: '#737373',
    600: '#525252',
    700: '#404040',
    800: '#262626',
    900: '#171717',
  },

  // Semantic Colors
  semantic: {
    error: '#ef4444',
    warning: '#f59e0b',
    success: '#10b981',
    info: '#3b82f6',
  },

  // Surface Colors
  surface: {
    background: '#ffffff',
    foreground: '#171717',
    card: '#ffffff',
    cardHover: '#fafafa',
    border: '#e5e5e5',
    borderFocus: '#7c3aed',
  },

  // Dark mode colors (future enhancement)
  dark: {
    background: '#0f0f0f',
    foreground: '#ffffff',
    card: '#1a1a1a',
    cardHover: '#262626',
    border: '#404040',
    borderFocus: '#8b5cf6',
  },
} as const;

// Helper function to get color with opacity
export const withOpacity = (color: string, opacity: number): string => {
  const hex = color.replace('#', '');
  const r = parseInt(hex.substring(0, 2), 16);
  const g = parseInt(hex.substring(2, 4), 16);
  const b = parseInt(hex.substring(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${opacity})`;
};

// Personality color mapping (from Bolt)
export const personalityColors = {
  'Event-Based': colors.accent.red,
  'Regional': colors.accent.teal,
  'Professional': colors.accent.blue,
  'Seasonal': colors.accent.orange,
  'Special': colors.accent.purple,
} as const;
