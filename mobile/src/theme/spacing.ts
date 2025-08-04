/**
 * Spacing system based on 8px grid
 * Consistent spacing creates visual rhythm and hierarchy
 */

export const spacing = {
  // Base unit (8px grid)
  unit: 8,
  
  // Named spacing values
  xxs: 2,   // 2px
  xs: 4,    // 4px
  sm: 8,    // 8px
  md: 16,   // 16px
  lg: 24,   // 24px
  xl: 32,   // 32px
  xxl: 48,  // 48px
  xxxl: 64, // 64px
  
  // Component-specific spacing
  gutter: 16,        // Default gutter between elements
  containerPadding: 20, // Screen edge padding
  cardPadding: 16,   // Card internal padding
  sectionGap: 30,    // Gap between sections
  
  // Layout spacing
  layout: {
    screenPadding: 20,
    sectionSpacing: 40,
    cardSpacing: 16,
    listItemSpacing: 12,
    gridGap: 16,
  },
  
  // Safe area insets (will be updated dynamically)
  safeArea: {
    top: 0,
    bottom: 0,
    left: 0,
    right: 0,
  },
};

// Spacing utilities
export const createSpacing = (...values: number[]): string => {
  return values.map(v => `${v}px`).join(' ');
};

export const getSpacing = (multiplier: number): number => {
  return spacing.unit * multiplier;
};