/**
 * Unified Animation System
 * Based on Bolt's smooth animations using Reanimated
 */

import { Easing } from 'react-native-reanimated';

// Duration presets
export const duration = {
  instant: 0,
  fast: 200,
  normal: 300,
  slow: 500,
  slower: 800,
} as const;

// Easing functions
export const easing = {
  // Standard easings
  linear: Easing.linear,
  ease: Easing.ease,
  easeIn: Easing.in(Easing.ease),
  easeOut: Easing.out(Easing.ease),
  easeInOut: Easing.inOut(Easing.ease),
  
  // Cubic easings (smooth like Bolt)
  easeInCubic: Easing.in(Easing.cubic),
  easeOutCubic: Easing.out(Easing.cubic),
  easeInOutCubic: Easing.inOut(Easing.cubic),
  
  // Expo easings (dramatic)
  easeInExpo: Easing.in(Easing.exp),
  easeOutExpo: Easing.out(Easing.exp),
  easeInOutExpo: Easing.inOut(Easing.exp),
  
  // Spring-like
  spring: Easing.out(Easing.poly(4)),
  bounce: Easing.bounce,
} as const;

// Spring configurations
export const spring = {
  // Gentle spring (like Bolt's cards)
  gentle: {
    damping: 15,
    stiffness: 100,
    mass: 1,
  },
  // Bouncy spring
  bouncy: {
    damping: 10,
    stiffness: 150,
    mass: 0.8,
  },
  // Stiff spring
  stiff: {
    damping: 20,
    stiffness: 200,
    mass: 1,
  },
  // No wobble
  noWobble: {
    damping: 26,
    stiffness: 170,
    mass: 1,
  },
} as const;

// Animation presets
export const animations = {
  // Fade animations
  fadeIn: {
    from: { opacity: 0 },
    to: { opacity: 1 },
    duration: duration.normal,
    easing: easing.easeOut,
  },
  fadeOut: {
    from: { opacity: 1 },
    to: { opacity: 0 },
    duration: duration.normal,
    easing: easing.easeIn,
  },
  
  // Scale animations (like Bolt's personality cards)
  scaleIn: {
    from: { transform: [{ scale: 0.9 }], opacity: 0 },
    to: { transform: [{ scale: 1 }], opacity: 1 },
    duration: duration.normal,
    easing: easing.easeOutCubic,
  },
  scalePress: {
    from: { transform: [{ scale: 1 }] },
    to: { transform: [{ scale: 0.95 }] },
    duration: duration.fast,
    easing: easing.easeInOutCubic,
  },
  
  // Slide animations
  slideInRight: {
    from: { transform: [{ translateX: 100 }], opacity: 0 },
    to: { transform: [{ translateX: 0 }], opacity: 1 },
    duration: duration.normal,
    easing: easing.easeOutCubic,
  },
  slideInBottom: {
    from: { transform: [{ translateY: 50 }], opacity: 0 },
    to: { transform: [{ translateY: 0 }], opacity: 1 },
    duration: duration.normal,
    easing: easing.easeOutCubic,
  },
  
  // Card entrance (Bolt style)
  cardEntrance: {
    from: { 
      transform: [{ scale: 0.95 }, { translateY: 10 }], 
      opacity: 0 
    },
    to: { 
      transform: [{ scale: 1 }, { translateY: 0 }], 
      opacity: 1 
    },
    duration: duration.slow,
    easing: easing.spring,
  },
} as const;
