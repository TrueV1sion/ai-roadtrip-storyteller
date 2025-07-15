/**
 * Unified Spacing and Layout System
 * Based on Bolt's clean spacing patterns
 */

// Base spacing unit (4px)
const SPACING_UNIT = 4;

// Spacing scale
export const spacing = {
  0: 0,
  1: SPACING_UNIT * 1,    // 4px
  2: SPACING_UNIT * 2,    // 8px
  3: SPACING_UNIT * 3,    // 12px
  4: SPACING_UNIT * 4,    // 16px
  5: SPACING_UNIT * 5,    // 20px
  6: SPACING_UNIT * 6,    // 24px
  7: SPACING_UNIT * 7,    // 28px
  8: SPACING_UNIT * 8,    // 32px
  10: SPACING_UNIT * 10,  // 40px
  12: SPACING_UNIT * 12,  // 48px
  16: SPACING_UNIT * 16,  // 64px
  20: SPACING_UNIT * 20,  // 80px
  24: SPACING_UNIT * 24,  // 96px
} as const;

// Border radius
export const borderRadius = {
  none: 0,
  sm: 4,
  base: 8,
  md: 12,
  lg: 16,
  xl: 20,
  '2xl': 24,
  '3xl': 32,
  full: 9999,
} as const;

// Shadow presets (from Bolt's subtle shadows)
export const shadows = {
  none: {
    shadowColor: 'transparent',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0,
    shadowRadius: 0,
    elevation: 0,
  },
  sm: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  base: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  md: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 4,
  },
  lg: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.2,
    shadowRadius: 16,
    elevation: 8,
  },
  xl: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 16 },
    shadowOpacity: 0.25,
    shadowRadius: 24,
    elevation: 12,
  },
} as const;

// Layout utilities
export const layout = {
  // Container padding (from Bolt's consistent padding)
  containerPadding: spacing[5], // 20px
  
  // Card styles
  card: {
    padding: spacing[4],
    borderRadius: borderRadius.lg,
    ...shadows.base,
  },
  
  // Screen safe areas
  screenPadding: {
    horizontal: spacing[5],
    vertical: spacing[4],
  },
  
  // Component spacing
  componentSpacing: {
    xs: spacing[2],
    sm: spacing[3],
    base: spacing[4],
    lg: spacing[6],
    xl: spacing[8],
  },
  
  // Grid system
  grid: {
    columns: 12,
    gutter: spacing[4],
  },
} as const;

// Z-index scale
export const zIndex = {
  hide: -1,
  auto: 'auto',
  base: 0,
  dropdown: 1000,
  sticky: 1100,
  fixed: 1200,
  modalBackdrop: 1300,
  modal: 1400,
  popover: 1500,
  tooltip: 1600,
} as const;
