/**
 * Legacy theme redirect
 * This file maintains backward compatibility while redirecting to the new design system
 */

import { lightTheme } from '../design/theme';

// Map old color names to new theme structure
export const COLORS = {
  primary: lightTheme.colors.primary[500],
  secondary: lightTheme.colors.secondary[500],
  success: lightTheme.colors.success,
  warning: lightTheme.colors.warning,
  error: lightTheme.colors.error,
  background: lightTheme.colors.surface.background,
  surface: lightTheme.colors.surface.card,
  text: lightTheme.colors.text.primary,
  textSecondary: lightTheme.colors.text.secondary,
  border: lightTheme.colors.neutral[300],
  spotify: '#1DB954', // Keep Spotify brand color
};

// Map old spacing to new system
export const SPACING = {
  tiny: lightTheme.spacing.xxs,
  small: lightTheme.spacing.xs,
  medium: lightTheme.spacing.md,
  large: lightTheme.spacing.lg,
  xlarge: lightTheme.spacing.xl,
};

// Map old font sizes to new typography scale
export const FONT_SIZES = {
  small: lightTheme.typography.bodySmall.fontSize,
  medium: lightTheme.typography.bodyMedium.fontSize,
  large: lightTheme.typography.bodyLarge.fontSize,
  xlarge: lightTheme.typography.titleMedium.fontSize,
  xxlarge: lightTheme.typography.headlineSmall.fontSize,
  title: lightTheme.typography.headlineLarge.fontSize,
};

// Map old border radius to new system
export const BORDER_RADIUS = {
  small: lightTheme.layout.borderRadius.sm,
  medium: lightTheme.layout.borderRadius.md,
  large: lightTheme.layout.borderRadius.lg,
  xlarge: lightTheme.layout.borderRadius.xl,
  rounded: lightTheme.layout.borderRadius.full,
};

// Export new theme for gradual migration
export { lightTheme, darkTheme } from '../design/theme';
export type { Theme } from '../design/theme';