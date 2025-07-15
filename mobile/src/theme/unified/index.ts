/**
 * Unified Theme System
 * Combines Bolt's beautiful design with RoadTrip's functionality
 */

export * from './colors';
export * from './typography';
export * from './spacing';
export { animations } from './animations';

import { colors, withOpacity, personalityColors } from './colors';
import { typography, fontFamilies, fontSizes, lineHeights, letterSpacing } from './typography';
import { spacing, borderRadius, shadows, layout, zIndex } from './spacing';

// Complete unified theme object
export const unifiedTheme = {
  colors,
  typography,
  spacing,
  borderRadius,
  shadows,
  layout,
  zIndex,
  fontFamilies,
  fontSizes,
  lineHeights,
  letterSpacing,
  personalityColors,
  
  // Helper functions
  utils: {
    withOpacity,
  },
} as const;

// Theme type for TypeScript
export type UnifiedTheme = typeof unifiedTheme;

// Default export for convenience
export default unifiedTheme;
