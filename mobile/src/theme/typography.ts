/**
 * Typography system using Inter font family
 * Consistent type scale for visual hierarchy
 */

export const typography = {
  // Font families
  fontFamily: {
    regular: 'Inter-Regular',
    medium: 'Inter-Medium',
    semiBold: 'Inter-SemiBold',
    bold: 'Inter-Bold',
  },
  
  // Font sizes
  fontSize: {
    xs: 10,
    sm: 12,
    base: 14,
    md: 16,
    lg: 18,
    xl: 20,
    '2xl': 24,
    '3xl': 28,
    '4xl': 32,
    '5xl': 40,
    '6xl': 48,
  },
  
  // Line heights
  lineHeight: {
    tight: 1.25,
    normal: 1.5,
    relaxed: 1.75,
    loose: 2,
  },
  
  // Letter spacing
  letterSpacing: {
    tighter: -0.05,
    tight: -0.025,
    normal: 0,
    wide: 0.025,
    wider: 0.05,
    widest: 0.1,
  },
  
  // Font weights (iOS/Android compatible)
  fontWeight: {
    regular: '400' as const,
    medium: '500' as const,
    semiBold: '600' as const,
    bold: '700' as const,
  },
  
  // Predefined text styles
  styles: {
    // Headings
    h1: {
      fontFamily: 'Inter-Bold',
      fontSize: 48,
      lineHeight: 56,
      letterSpacing: -1.5,
    },
    h2: {
      fontFamily: 'Inter-Bold',
      fontSize: 40,
      lineHeight: 48,
      letterSpacing: -0.5,
    },
    h3: {
      fontFamily: 'Inter-Bold',
      fontSize: 32,
      lineHeight: 40,
      letterSpacing: 0,
    },
    h4: {
      fontFamily: 'Inter-SemiBold',
      fontSize: 28,
      lineHeight: 36,
      letterSpacing: 0.25,
    },
    h5: {
      fontFamily: 'Inter-SemiBold',
      fontSize: 24,
      lineHeight: 32,
      letterSpacing: 0,
    },
    h6: {
      fontFamily: 'Inter-SemiBold',
      fontSize: 20,
      lineHeight: 28,
      letterSpacing: 0.15,
    },
    
    // Body text
    body1: {
      fontFamily: 'Inter-Regular',
      fontSize: 16,
      lineHeight: 24,
      letterSpacing: 0.5,
    },
    body2: {
      fontFamily: 'Inter-Regular',
      fontSize: 14,
      lineHeight: 20,
      letterSpacing: 0.25,
    },
    
    // Supporting text
    subtitle1: {
      fontFamily: 'Inter-Medium',
      fontSize: 18,
      lineHeight: 26,
      letterSpacing: 0.15,
    },
    subtitle2: {
      fontFamily: 'Inter-Medium',
      fontSize: 16,
      lineHeight: 24,
      letterSpacing: 0.1,
    },
    
    // Small text
    caption: {
      fontFamily: 'Inter-Regular',
      fontSize: 12,
      lineHeight: 16,
      letterSpacing: 0.4,
    },
    overline: {
      fontFamily: 'Inter-Medium',
      fontSize: 10,
      lineHeight: 16,
      letterSpacing: 1.5,
      textTransform: 'uppercase' as const,
    },
    
    // Interactive elements
    button: {
      fontFamily: 'Inter-SemiBold',
      fontSize: 16,
      lineHeight: 24,
      letterSpacing: 1.25,
    },
    link: {
      fontFamily: 'Inter-Medium',
      fontSize: 16,
      lineHeight: 24,
      letterSpacing: 0.5,
      textDecorationLine: 'underline' as const,
    },
  },
};