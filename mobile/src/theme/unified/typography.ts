/**
 * Unified Typography System
 * Based on Bolt's clean typography with Inter font
 */

import { Platform } from 'react-native';

// Font families
export const fontFamilies = {
  regular: Platform.select({
    ios: 'Inter-Regular',
    android: 'Inter-Regular',
    default: 'Inter-Regular',
  }),
  medium: Platform.select({
    ios: 'Inter-Medium',
    android: 'Inter-Medium',
    default: 'Inter-Medium',
  }),
  semiBold: Platform.select({
    ios: 'Inter-SemiBold',
    android: 'Inter-SemiBold',
    default: 'Inter-SemiBold',
  }),
  bold: Platform.select({
    ios: 'Inter-Bold',
    android: 'Inter-Bold',
    default: 'Inter-Bold',
  }),
} as const;

// Font sizes
export const fontSizes = {
  xs: 12,
  sm: 14,
  base: 16,
  lg: 18,
  xl: 20,
  '2xl': 24,
  '3xl': 30,
  '4xl': 36,
  '5xl': 48,
} as const;

// Line heights
export const lineHeights = {
  tight: 1.25,
  normal: 1.5,
  relaxed: 1.75,
  loose: 2,
} as const;

// Letter spacing
export const letterSpacing = {
  tighter: -0.05,
  tight: -0.025,
  normal: 0,
  wide: 0.025,
  wider: 0.05,
  widest: 0.1,
} as const;

// Typography presets (from Bolt's clean style)
export const typography = {
  // Headings
  h1: {
    fontFamily: fontFamilies.bold,
    fontSize: fontSizes['4xl'],
    lineHeight: lineHeights.tight,
    letterSpacing: letterSpacing.tight,
  },
  h2: {
    fontFamily: fontFamilies.bold,
    fontSize: fontSizes['3xl'],
    lineHeight: lineHeights.tight,
    letterSpacing: letterSpacing.tight,
  },
  h3: {
    fontFamily: fontFamilies.semiBold,
    fontSize: fontSizes['2xl'],
    lineHeight: lineHeights.normal,
  },
  h4: {
    fontFamily: fontFamilies.semiBold,
    fontSize: fontSizes.xl,
    lineHeight: lineHeights.normal,
  },
  h5: {
    fontFamily: fontFamilies.semiBold,
    fontSize: fontSizes.lg,
    lineHeight: lineHeights.normal,
  },
  h6: {
    fontFamily: fontFamilies.semiBold,
    fontSize: fontSizes.base,
    lineHeight: lineHeights.normal,
  },
  
  // Body text
  body: {
    fontFamily: fontFamilies.regular,
    fontSize: fontSizes.base,
    lineHeight: lineHeights.normal,
  },
  bodyLarge: {
    fontFamily: fontFamilies.regular,
    fontSize: fontSizes.lg,
    lineHeight: lineHeights.relaxed,
  },
  bodySmall: {
    fontFamily: fontFamilies.regular,
    fontSize: fontSizes.sm,
    lineHeight: lineHeights.normal,
  },
  
  // UI elements
  button: {
    fontFamily: fontFamilies.medium,
    fontSize: fontSizes.base,
    lineHeight: lineHeights.normal,
    letterSpacing: letterSpacing.wide,
  },
  buttonLarge: {
    fontFamily: fontFamilies.medium,
    fontSize: fontSizes.lg,
    lineHeight: lineHeights.normal,
    letterSpacing: letterSpacing.wide,
  },
  buttonSmall: {
    fontFamily: fontFamilies.medium,
    fontSize: fontSizes.sm,
    lineHeight: lineHeights.normal,
  },
  
  // Labels and captions
  label: {
    fontFamily: fontFamilies.medium,
    fontSize: fontSizes.sm,
    lineHeight: lineHeights.normal,
    letterSpacing: letterSpacing.wide,
  },
  caption: {
    fontFamily: fontFamilies.regular,
    fontSize: fontSizes.xs,
    lineHeight: lineHeights.normal,
  },
  
  // Special styles from Bolt
  personalityName: {
    fontFamily: fontFamilies.semiBold,
    fontSize: fontSizes.lg,
    lineHeight: lineHeights.tight,
  },
  personalityDescription: {
    fontFamily: fontFamilies.regular,
    fontSize: fontSizes.sm,
    lineHeight: lineHeights.normal,
    color: '#737373',
  },
  storyTitle: {
    fontFamily: fontFamilies.semiBold,
    fontSize: fontSizes.xl,
    lineHeight: lineHeights.tight,
  },
  storyDuration: {
    fontFamily: fontFamilies.medium,
    fontSize: fontSizes.sm,
    lineHeight: lineHeights.normal,
    color: '#a3a3a3',
  },
} as const;
