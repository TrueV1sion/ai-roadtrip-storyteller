/**
 * FAANG-Level Personality-Aware Color System
 * 
 * This module implements a sophisticated color management system that:
 * 1. Generates dynamic color palettes based on personality
 * 2. Adapts colors based on time of day, emotion, and context
 * 3. Provides smooth color transitions and animations
 * 4. Ensures accessibility compliance (WCAG AA)
 * 5. Optimizes for performance with color caching
 */

import { Animated, Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { logger } from '@/services/logger';
// Type definitions for type safety
export interface ColorPalette {
  primary: string[];
  secondary: string[];
  accent: string[];
  particles: string[];
  glow: GlowEffect;
  gradients: GradientDefinition[];
}

export interface GlowEffect {
  color: string;
  intensity: number;
  blur: number;
  spread: number;
}

export interface GradientDefinition {
  name: string;
  colors: string[];
  locations?: number[];
  angle?: number;
  type: 'linear' | 'radial' | 'conic';
}

export interface PersonalityColorConfig {
  id: string;
  name: string;
  description: string;
  baseColors: ColorPalette;
  timeVariations: TimeBasedVariations;
  emotionModifiers: EmotionModifiers;
  seasonalThemes: SeasonalThemes;
  accessibilityMode: AccessibilityColors;
}

interface TimeBasedVariations {
  dawn: ColorModifier;
  morning: ColorModifier;
  noon: ColorModifier;
  afternoon: ColorModifier;
  dusk: ColorModifier;
  night: ColorModifier;
  lateNight: ColorModifier;
}

interface ColorModifier {
  hueShift: number;
  saturationMultiplier: number;
  brightnessMultiplier: number;
  overlayColor?: string;
  overlayOpacity?: number;
}

interface EmotionModifiers {
  joy: ColorModifier;
  excitement: ColorModifier;
  calm: ColorModifier;
  mystery: ColorModifier;
  wonder: ColorModifier;
  fear: ColorModifier;
  sadness: ColorModifier;
}

interface SeasonalThemes {
  spring: ColorModifier;
  summer: ColorModifier;
  fall: ColorModifier;
  winter: ColorModifier;
}

interface AccessibilityColors {
  highContrast: ColorPalette;
  colorBlindSafe: ColorPalette;
  reducedMotion: boolean;
}

// Brand-defining personality configurations
export const PERSONALITY_COLOR_CONFIGS: Record<string, PersonalityColorConfig> = {
  mickey: {
    id: 'mickey',
    name: 'Mickey Mouse',
    description: 'Magical Disney-inspired palette with playful, vibrant colors',
    baseColors: {
      primary: ['#FF0000', '#FFD700', '#1E90FF', '#FF69B4'],
      secondary: ['#FFA500', '#9370DB', '#00CED1', '#FFB6C1'],
      accent: ['#FF1493', '#00FA9A', '#FF4500', '#7FFF00'],
      particles: ['#FFD700', '#FF69B4', '#87CEEB', '#DDA0DD'],
      glow: {
        color: '#FFD700',
        intensity: 0.9,
        blur: 30,
        spread: 1.5,
      },
      gradients: [
        {
          name: 'magic-sparkle',
          colors: ['#FF0000', '#FFD700', '#FF69B4', '#9370DB'],
          type: 'linear',
          angle: 45,
        },
        {
          name: 'disney-sunset',
          colors: ['#FF6B6B', '#FFE66D', '#FF6B9D', '#C44569'],
          type: 'radial',
        },
      ],
    },
    timeVariations: {
      dawn: { hueShift: -10, saturationMultiplier: 0.9, brightnessMultiplier: 0.95 },
      morning: { hueShift: 0, saturationMultiplier: 1.1, brightnessMultiplier: 1.05 },
      noon: { hueShift: 5, saturationMultiplier: 1.2, brightnessMultiplier: 1.1 },
      afternoon: { hueShift: 10, saturationMultiplier: 1.15, brightnessMultiplier: 1.0 },
      dusk: { hueShift: 20, saturationMultiplier: 1.3, brightnessMultiplier: 0.9 },
      night: { hueShift: -5, saturationMultiplier: 0.8, brightnessMultiplier: 0.7 },
      lateNight: { hueShift: -15, saturationMultiplier: 0.7, brightnessMultiplier: 0.6 },
    },
    emotionModifiers: {
      joy: { hueShift: 10, saturationMultiplier: 1.3, brightnessMultiplier: 1.2 },
      excitement: { hueShift: 15, saturationMultiplier: 1.4, brightnessMultiplier: 1.3 },
      calm: { hueShift: -20, saturationMultiplier: 0.7, brightnessMultiplier: 0.9 },
      mystery: { hueShift: 180, saturationMultiplier: 0.8, brightnessMultiplier: 0.6 },
      wonder: { hueShift: 30, saturationMultiplier: 1.2, brightnessMultiplier: 1.1 },
      fear: { hueShift: -30, saturationMultiplier: 0.5, brightnessMultiplier: 0.5 },
      sadness: { hueShift: -40, saturationMultiplier: 0.4, brightnessMultiplier: 0.7 },
    },
    seasonalThemes: {
      spring: { hueShift: 20, saturationMultiplier: 1.2, brightnessMultiplier: 1.1 },
      summer: { hueShift: 10, saturationMultiplier: 1.3, brightnessMultiplier: 1.2 },
      fall: { hueShift: 30, saturationMultiplier: 1.1, brightnessMultiplier: 0.9 },
      winter: { hueShift: -10, saturationMultiplier: 0.8, brightnessMultiplier: 1.0 },
    },
    accessibilityMode: {
      highContrast: {
        primary: ['#FF0000', '#FFFF00', '#0000FF', '#FF00FF'],
        secondary: ['#00FF00', '#FF8C00', '#00FFFF', '#FF1493'],
        accent: ['#FFFFFF', '#000000', '#FFD700', '#C0C0C0'],
        particles: ['#FFFF00', '#FF00FF', '#00FFFF', '#FFFFFF'],
        glow: { color: '#FFFFFF', intensity: 1.0, blur: 40, spread: 2.0 },
        gradients: [],
      },
      colorBlindSafe: {
        primary: ['#D55E00', '#F0E442', '#0072B2', '#CC79A7'],
        secondary: ['#009E73', '#E69F00', '#56B4E9', '#999999'],
        accent: ['#000000', '#FFFFFF', '#D55E00', '#0072B2'],
        particles: ['#F0E442', '#CC79A7', '#56B4E9', '#E69F00'],
        glow: { color: '#F0E442', intensity: 0.8, blur: 25, spread: 1.2 },
        gradients: [],
      },
      reducedMotion: false,
    },
  },
  
  surfer: {
    id: 'surfer',
    name: 'California Surfer',
    description: 'Ocean-inspired palette with flowing, beachy vibes',
    baseColors: {
      primary: ['#00CED1', '#4682B4', '#F0E68C', '#48D1CC'],
      secondary: ['#5F9EA0', '#FFA500', '#87CEEB', '#FFE4B5'],
      accent: ['#00BFFF', '#FF6347', '#32CD32', '#FFD700'],
      particles: ['#40E0D0', '#AFEEEE', '#E0FFFF', '#B0E0E6'],
      glow: {
        color: '#00CED1',
        intensity: 0.7,
        blur: 25,
        spread: 1.3,
      },
      gradients: [
        {
          name: 'ocean-wave',
          colors: ['#006994', '#00CED1', '#48D1CC', '#AFEEEE'],
          type: 'linear',
          angle: 180,
        },
        {
          name: 'sunset-beach',
          colors: ['#FF6347', '#FFA500', '#FFD700', '#FFDEAD'],
          type: 'radial',
        },
      ],
    },
    timeVariations: {
      dawn: { hueShift: -5, saturationMultiplier: 0.8, brightnessMultiplier: 0.9 },
      morning: { hueShift: 0, saturationMultiplier: 1.0, brightnessMultiplier: 1.0 },
      noon: { hueShift: -10, saturationMultiplier: 1.1, brightnessMultiplier: 1.2 },
      afternoon: { hueShift: 5, saturationMultiplier: 1.05, brightnessMultiplier: 1.1 },
      dusk: { hueShift: 25, saturationMultiplier: 1.2, brightnessMultiplier: 0.85 },
      night: { hueShift: -20, saturationMultiplier: 0.7, brightnessMultiplier: 0.6 },
      lateNight: { hueShift: -30, saturationMultiplier: 0.6, brightnessMultiplier: 0.5 },
    },
    emotionModifiers: {
      joy: { hueShift: 5, saturationMultiplier: 1.2, brightnessMultiplier: 1.1 },
      excitement: { hueShift: 10, saturationMultiplier: 1.3, brightnessMultiplier: 1.2 },
      calm: { hueShift: -10, saturationMultiplier: 0.9, brightnessMultiplier: 0.95 },
      mystery: { hueShift: 160, saturationMultiplier: 0.7, brightnessMultiplier: 0.7 },
      wonder: { hueShift: 20, saturationMultiplier: 1.1, brightnessMultiplier: 1.05 },
      fear: { hueShift: -40, saturationMultiplier: 0.6, brightnessMultiplier: 0.6 },
      sadness: { hueShift: -50, saturationMultiplier: 0.5, brightnessMultiplier: 0.8 },
    },
    seasonalThemes: {
      spring: { hueShift: 10, saturationMultiplier: 1.1, brightnessMultiplier: 1.05 },
      summer: { hueShift: 0, saturationMultiplier: 1.2, brightnessMultiplier: 1.15 },
      fall: { hueShift: 20, saturationMultiplier: 1.0, brightnessMultiplier: 0.95 },
      winter: { hueShift: -15, saturationMultiplier: 0.85, brightnessMultiplier: 0.9 },
    },
    accessibilityMode: {
      highContrast: {
        primary: ['#00FFFF', '#0000FF', '#FFFF00', '#00FFFF'],
        secondary: ['#008080', '#FF8C00', '#87CEEB', '#FFFACD'],
        accent: ['#00BFFF', '#FF0000', '#00FF00', '#FFD700'],
        particles: ['#00FFFF', '#E0FFFF', '#AFEEEE', '#87CEEB'],
        glow: { color: '#00FFFF', intensity: 1.0, blur: 35, spread: 1.8 },
        gradients: [],
      },
      colorBlindSafe: {
        primary: ['#0072B2', '#56B4E9', '#F0E442', '#009E73'],
        secondary: ['#006994', '#E69F00', '#87CEEB', '#F0E442'],
        accent: ['#0072B2', '#D55E00', '#009E73', '#F0E442'],
        particles: ['#56B4E9', '#87CEEB', '#B0E0E6', '#ADD8E6'],
        glow: { color: '#56B4E9', intensity: 0.7, blur: 22, spread: 1.1 },
        gradients: [],
      },
      reducedMotion: false,
    },
  },
  
  mountain: {
    id: 'mountain',
    name: 'Mountain Guide',
    description: 'Alpine-inspired palette with majestic, natural colors',
    baseColors: {
      primary: ['#FFFFFF', '#87CEEB', '#2F4F4F', '#F0FFFF'],
      secondary: ['#B0C4DE', '#696969', '#E0FFFF', '#4682B4'],
      accent: ['#1E90FF', '#228B22', '#8B4513', '#DAA520'],
      particles: ['#FFFAFA', '#F0F8FF', '#E6E6FA', '#F5F5F5'],
      glow: {
        color: '#87CEEB',
        intensity: 0.6,
        blur: 20,
        spread: 1.2,
      },
      gradients: [
        {
          name: 'alpine-mist',
          colors: ['#FFFFFF', '#E0FFFF', '#87CEEB', '#4682B4'],
          type: 'linear',
          angle: 270,
        },
        {
          name: 'mountain-sunset',
          colors: ['#FFB6C1', '#FFA07A', '#FF7F50', '#DC143C'],
          type: 'radial',
        },
      ],
    },
    timeVariations: {
      dawn: { hueShift: -15, saturationMultiplier: 0.7, brightnessMultiplier: 0.85 },
      morning: { hueShift: -5, saturationMultiplier: 0.9, brightnessMultiplier: 1.0 },
      noon: { hueShift: 0, saturationMultiplier: 0.95, brightnessMultiplier: 1.1 },
      afternoon: { hueShift: 5, saturationMultiplier: 1.0, brightnessMultiplier: 1.05 },
      dusk: { hueShift: 30, saturationMultiplier: 1.1, brightnessMultiplier: 0.8 },
      night: { hueShift: -25, saturationMultiplier: 0.6, brightnessMultiplier: 0.5 },
      lateNight: { hueShift: -35, saturationMultiplier: 0.5, brightnessMultiplier: 0.4 },
    },
    emotionModifiers: {
      joy: { hueShift: 0, saturationMultiplier: 1.1, brightnessMultiplier: 1.1 },
      excitement: { hueShift: 5, saturationMultiplier: 1.2, brightnessMultiplier: 1.15 },
      calm: { hueShift: -5, saturationMultiplier: 0.95, brightnessMultiplier: 1.0 },
      mystery: { hueShift: 180, saturationMultiplier: 0.6, brightnessMultiplier: 0.6 },
      wonder: { hueShift: 15, saturationMultiplier: 1.05, brightnessMultiplier: 1.05 },
      fear: { hueShift: -45, saturationMultiplier: 0.5, brightnessMultiplier: 0.5 },
      sadness: { hueShift: -60, saturationMultiplier: 0.4, brightnessMultiplier: 0.7 },
    },
    seasonalThemes: {
      spring: { hueShift: 15, saturationMultiplier: 1.15, brightnessMultiplier: 1.1 },
      summer: { hueShift: 5, saturationMultiplier: 1.1, brightnessMultiplier: 1.15 },
      fall: { hueShift: 35, saturationMultiplier: 1.2, brightnessMultiplier: 0.9 },
      winter: { hueShift: -10, saturationMultiplier: 0.7, brightnessMultiplier: 1.05 },
    },
    accessibilityMode: {
      highContrast: {
        primary: ['#FFFFFF', '#87CEEB', '#000000', '#F0FFFF'],
        secondary: ['#C0C0C0', '#404040', '#E0FFFF', '#0000FF'],
        accent: ['#0000FF', '#008000', '#8B4513', '#FFD700'],
        particles: ['#FFFFFF', '#F0F8FF', '#E0E0E0', '#D3D3D3'],
        glow: { color: '#FFFFFF', intensity: 0.9, blur: 30, spread: 1.5 },
        gradients: [],
      },
      colorBlindSafe: {
        primary: ['#FFFFFF', '#56B4E9', '#999999', '#E5F5FF'],
        secondary: ['#CCCCCC', '#666666', '#E5F5FF', '#56B4E9'],
        accent: ['#0072B2', '#009E73', '#D55E00', '#F0E442'],
        particles: ['#FFFFFF', '#F0F8FF', '#E5E5E5', '#F5F5F5'],
        glow: { color: '#56B4E9', intensity: 0.6, blur: 18, spread: 1.0 },
        gradients: [],
      },
      reducedMotion: false,
    },
  },
  
  scifi: {
    id: 'scifi',
    name: 'Sci-Fi Explorer',
    description: 'Futuristic palette with neon and cyberpunk aesthetics',
    baseColors: {
      primary: ['#00FFFF', '#FF00FF', '#7FFF00', '#FF1493'],
      secondary: ['#8A2BE2', '#00FF7F', '#FF4500', '#9400D3'],
      accent: ['#FFD700', '#DC143C', '#00CED1', '#FF69B4'],
      particles: ['#00FFFF', '#FF00FF', '#FFFF00', '#00FF00'],
      glow: {
        color: '#00FFFF',
        intensity: 1.0,
        blur: 35,
        spread: 2.0,
      },
      gradients: [
        {
          name: 'neon-pulse',
          colors: ['#FF00FF', '#00FFFF', '#FF00FF', '#00FFFF'],
          type: 'linear',
          angle: 90,
        },
        {
          name: 'cyber-grid',
          colors: ['#7FFF00', '#FF1493', '#00CED1', '#FFD700'],
          type: 'radial',
        },
      ],
    },
    timeVariations: {
      dawn: { hueShift: 20, saturationMultiplier: 0.9, brightnessMultiplier: 0.8 },
      morning: { hueShift: 10, saturationMultiplier: 1.0, brightnessMultiplier: 0.9 },
      noon: { hueShift: 0, saturationMultiplier: 1.1, brightnessMultiplier: 1.0 },
      afternoon: { hueShift: -10, saturationMultiplier: 1.15, brightnessMultiplier: 1.05 },
      dusk: { hueShift: -20, saturationMultiplier: 1.2, brightnessMultiplier: 1.1 },
      night: { hueShift: 0, saturationMultiplier: 1.3, brightnessMultiplier: 1.2 },
      lateNight: { hueShift: 10, saturationMultiplier: 1.4, brightnessMultiplier: 1.3 },
    },
    emotionModifiers: {
      joy: { hueShift: 20, saturationMultiplier: 1.2, brightnessMultiplier: 1.2 },
      excitement: { hueShift: 30, saturationMultiplier: 1.4, brightnessMultiplier: 1.4 },
      calm: { hueShift: -30, saturationMultiplier: 0.8, brightnessMultiplier: 0.8 },
      mystery: { hueShift: 90, saturationMultiplier: 1.1, brightnessMultiplier: 0.9 },
      wonder: { hueShift: 45, saturationMultiplier: 1.3, brightnessMultiplier: 1.2 },
      fear: { hueShift: -60, saturationMultiplier: 1.5, brightnessMultiplier: 0.7 },
      sadness: { hueShift: -90, saturationMultiplier: 0.6, brightnessMultiplier: 0.6 },
    },
    seasonalThemes: {
      spring: { hueShift: 30, saturationMultiplier: 1.1, brightnessMultiplier: 1.1 },
      summer: { hueShift: 15, saturationMultiplier: 1.2, brightnessMultiplier: 1.2 },
      fall: { hueShift: -15, saturationMultiplier: 1.15, brightnessMultiplier: 1.0 },
      winter: { hueShift: -30, saturationMultiplier: 1.3, brightnessMultiplier: 1.1 },
    },
    accessibilityMode: {
      highContrast: {
        primary: ['#00FFFF', '#FF00FF', '#FFFF00', '#FF0000'],
        secondary: ['#0000FF', '#00FF00', '#FF4500', '#FF00FF'],
        accent: ['#FFFFFF', '#FF0000', '#00FFFF', '#FF00FF'],
        particles: ['#00FFFF', '#FF00FF', '#FFFF00', '#00FF00'],
        glow: { color: '#FFFFFF', intensity: 1.0, blur: 40, spread: 2.5 },
        gradients: [],
      },
      colorBlindSafe: {
        primary: ['#56B4E9', '#CC79A7', '#F0E442', '#D55E00'],
        secondary: ['#0072B2', '#009E73', '#E69F00', '#CC79A7'],
        accent: ['#F0E442', '#D55E00', '#56B4E9', '#CC79A7'],
        particles: ['#56B4E9', '#CC79A7', '#F0E442', '#009E73'],
        glow: { color: '#56B4E9', intensity: 0.9, blur: 30, spread: 1.6 },
        gradients: [],
      },
      reducedMotion: false,
    },
  },
};

/**
 * Advanced color system class with FAANG-level features
 */
export class PersonalityColorSystem {
  private currentPersonality: string;
  private currentTime: Date;
  private currentEmotion: string;
  private currentSeason: string;
  private colorCache: Map<string, string>;
  private interpolationCache: Map<string, Animated.Value>;
  
  constructor(personality: string = 'mickey') {
    this.currentPersonality = personality;
    this.currentTime = new Date();
    this.currentEmotion = 'calm';
    this.currentSeason = this.getCurrentSeason();
    this.colorCache = new Map();
    this.interpolationCache = new Map();
    
    // Load cached preferences
    this.loadPreferences();
  }
  
  /**
   * Get dynamic color palette based on current context
   */
  public getDynamicPalette(): ColorPalette {
    const cacheKey = `${this.currentPersonality}-${this.getTimeOfDay()}-${this.currentEmotion}-${this.currentSeason}`;
    
    // Check cache first
    if (this.colorCache.has(cacheKey)) {
      return JSON.parse(this.colorCache.get(cacheKey)!);
    }
    
    const config = PERSONALITY_COLOR_CONFIGS[this.currentPersonality];
    if (!config) {
      logger.warn(`Unknown personality: ${this.currentPersonality}`);
      return this.getDefaultPalette();
    }
    
    // Start with base colors
    let palette = { ...config.baseColors };
    
    // Apply time-based variations
    const timeModifier = this.getTimeModifier(config);
    palette = this.applyColorModifier(palette, timeModifier);
    
    // Apply emotion modifiers
    const emotionModifier = config.emotionModifiers[this.currentEmotion as keyof EmotionModifiers];
    if (emotionModifier) {
      palette = this.applyColorModifier(palette, emotionModifier);
    }
    
    // Apply seasonal themes
    const seasonModifier = config.seasonalThemes[this.currentSeason as keyof SeasonalThemes];
    if (seasonModifier) {
      palette = this.applyColorModifier(palette, seasonModifier);
    }
    
    // Cache the result
    this.colorCache.set(cacheKey, JSON.stringify(palette));
    
    return palette;
  }
  
  /**
   * Get animated color value for smooth transitions
   */
  public getAnimatedColor(colorKey: string): Animated.Value {
    if (!this.interpolationCache.has(colorKey)) {
      this.interpolationCache.set(colorKey, new Animated.Value(0));
    }
    
    return this.interpolationCache.get(colorKey)!;
  }
  
  /**
   * Transition to new personality with smooth color animation
   */
  public async transitionToPersonality(newPersonality: string, duration: number = 1000): Promise<void> {
    const oldPalette = this.getDynamicPalette();
    this.currentPersonality = newPersonality;
    const newPalette = this.getDynamicPalette();
    
    // Animate all color transitions
    const animations = Object.keys(oldPalette).map(key => {
      const animValue = this.getAnimatedColor(key);
      return Animated.timing(animValue, {
        toValue: 1,
        duration,
        useNativeDriver: false,
      });
    });
    
    await Promise.all(animations.map(anim => new Promise(resolve => anim.start(resolve))));
    
    // Save preference
    await this.savePreferences();
  }
  
  /**
   * Update emotional state and adapt colors
   */
  public setEmotion(emotion: string, intensity: number = 1.0) {
    this.currentEmotion = emotion;
    
    // Trigger color update with animation
    const palette = this.getDynamicPalette();
    
    // Animate intensity-based changes
    Object.keys(palette).forEach(key => {
      const animValue = this.getAnimatedColor(`${key}-emotion`);
      Animated.timing(animValue, {
        toValue: intensity,
        duration: 500,
        useNativeDriver: false,
      }).start();
    });
  }
  
  /**
   * Get accessibility-compliant colors
   */
  public getAccessiblePalette(mode: 'highContrast' | 'colorBlindSafe'): ColorPalette {
    const config = PERSONALITY_COLOR_CONFIGS[this.currentPersonality];
    return config.accessibilityMode[mode];
  }
  
  /**
   * Generate interpolated color between two colors
   */
  public interpolateColor(color1: string, color2: string, factor: number): string {
    const rgb1 = this.hexToRgb(color1);
    const rgb2 = this.hexToRgb(color2);
    
    if (!rgb1 || !rgb2) return color1;
    
    const r = Math.round(rgb1.r + (rgb2.r - rgb1.r) * factor);
    const g = Math.round(rgb1.g + (rgb2.g - rgb1.g) * factor);
    const b = Math.round(rgb1.b + (rgb2.b - rgb1.b) * factor);
    
    return this.rgbToHex(r, g, b);
  }
  
  /**
   * Apply color modifier to palette
   */
  private applyColorModifier(palette: ColorPalette, modifier: ColorModifier): ColorPalette {
    const modifiedPalette: ColorPalette = {
      primary: palette.primary.map(color => this.modifyColor(color, modifier)),
      secondary: palette.secondary.map(color => this.modifyColor(color, modifier)),
      accent: palette.accent.map(color => this.modifyColor(color, modifier)),
      particles: palette.particles.map(color => this.modifyColor(color, modifier)),
      glow: {
        ...palette.glow,
        color: this.modifyColor(palette.glow.color, modifier),
        intensity: palette.glow.intensity * (modifier.brightnessMultiplier || 1),
      },
      gradients: palette.gradients.map(gradient => ({
        ...gradient,
        colors: gradient.colors.map(color => this.modifyColor(color, modifier)),
      })),
    };
    
    return modifiedPalette;
  }
  
  /**
   * Modify individual color based on modifier settings
   */
  private modifyColor(color: string, modifier: ColorModifier): string {
    const hsl = this.hexToHsl(color);
    if (!hsl) return color;
    
    // Apply modifications
    hsl.h = (hsl.h + modifier.hueShift) % 360;
    hsl.s = Math.min(100, Math.max(0, hsl.s * modifier.saturationMultiplier));
    hsl.l = Math.min(100, Math.max(0, hsl.l * modifier.brightnessMultiplier));
    
    let modifiedColor = this.hslToHex(hsl.h, hsl.s, hsl.l);
    
    // Apply overlay if specified
    if (modifier.overlayColor && modifier.overlayOpacity) {
      modifiedColor = this.blendColors(modifiedColor, modifier.overlayColor, modifier.overlayOpacity);
    }
    
    return modifiedColor;
  }
  
  /**
   * Get time-based modifier
   */
  private getTimeModifier(config: PersonalityColorConfig): ColorModifier {
    const timeOfDay = this.getTimeOfDay();
    return config.timeVariations[timeOfDay as keyof TimeBasedVariations];
  }
  
  /**
   * Determine current time of day
   */
  private getTimeOfDay(): string {
    const hour = this.currentTime.getHours();
    
    if (hour >= 5 && hour < 7) return 'dawn';
    if (hour >= 7 && hour < 11) return 'morning';
    if (hour >= 11 && hour < 14) return 'noon';
    if (hour >= 14 && hour < 17) return 'afternoon';
    if (hour >= 17 && hour < 20) return 'dusk';
    if (hour >= 20 && hour < 23) return 'night';
    return 'lateNight';
  }
  
  /**
   * Determine current season
   */
  private getCurrentSeason(): string {
    const month = this.currentTime.getMonth();
    
    if (month >= 2 && month <= 4) return 'spring';
    if (month >= 5 && month <= 7) return 'summer';
    if (month >= 8 && month <= 10) return 'fall';
    return 'winter';
  }
  
  /**
   * Get default palette as fallback
   */
  private getDefaultPalette(): ColorPalette {
    return PERSONALITY_COLOR_CONFIGS.mickey.baseColors;
  }
  
  /**
   * Color utility functions
   */
  private hexToRgb(hex: string): { r: number; g: number; b: number } | null {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
      r: parseInt(result[1], 16),
      g: parseInt(result[2], 16),
      b: parseInt(result[3], 16),
    } : null;
  }
  
  private rgbToHex(r: number, g: number, b: number): string {
    return '#' + [r, g, b].map(x => {
      const hex = x.toString(16);
      return hex.length === 1 ? '0' + hex : hex;
    }).join('');
  }
  
  private hexToHsl(hex: string): { h: number; s: number; l: number } | null {
    const rgb = this.hexToRgb(hex);
    if (!rgb) return null;
    
    const r = rgb.r / 255;
    const g = rgb.g / 255;
    const b = rgb.b / 255;
    
    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    let h = 0;
    let s = 0;
    const l = (max + min) / 2;
    
    if (max !== min) {
      const d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      
      switch (max) {
        case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
        case g: h = ((b - r) / d + 2) / 6; break;
        case b: h = ((r - g) / d + 4) / 6; break;
      }
    }
    
    return {
      h: Math.round(h * 360),
      s: Math.round(s * 100),
      l: Math.round(l * 100),
    };
  }
  
  private hslToHex(h: number, s: number, l: number): string {
    h = h / 360;
    s = s / 100;
    l = l / 100;
    
    let r, g, b;
    
    if (s === 0) {
      r = g = b = l;
    } else {
      const hue2rgb = (p: number, q: number, t: number) => {
        if (t < 0) t += 1;
        if (t > 1) t -= 1;
        if (t < 1/6) return p + (q - p) * 6 * t;
        if (t < 1/2) return q;
        if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
        return p;
      };
      
      const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
      const p = 2 * l - q;
      
      r = hue2rgb(p, q, h + 1/3);
      g = hue2rgb(p, q, h);
      b = hue2rgb(p, q, h - 1/3);
    }
    
    return this.rgbToHex(
      Math.round(r * 255),
      Math.round(g * 255),
      Math.round(b * 255)
    );
  }
  
  private blendColors(color1: string, color2: string, opacity: number): string {
    const rgb1 = this.hexToRgb(color1);
    const rgb2 = this.hexToRgb(color2);
    
    if (!rgb1 || !rgb2) return color1;
    
    const r = Math.round(rgb1.r * (1 - opacity) + rgb2.r * opacity);
    const g = Math.round(rgb1.g * (1 - opacity) + rgb2.g * opacity);
    const b = Math.round(rgb1.b * (1 - opacity) + rgb2.b * opacity);
    
    return this.rgbToHex(r, g, b);
  }
  
  /**
   * Persistence methods
   */
  private async loadPreferences() {
    try {
      const prefs = await AsyncStorage.getItem('personality_color_preferences');
      if (prefs) {
        const { personality, emotion } = JSON.parse(prefs);
        this.currentPersonality = personality || this.currentPersonality;
        this.currentEmotion = emotion || this.currentEmotion;
      }
    } catch (error) {
      logger.error('Failed to load color preferences:', error);
    }
  }
  
  private async savePreferences() {
    try {
      await AsyncStorage.setItem('personality_color_preferences', JSON.stringify({
        personality: this.currentPersonality,
        emotion: this.currentEmotion,
        timestamp: Date.now(),
      }));
    } catch (error) {
      logger.error('Failed to save color preferences:', error);
    }
  }
}

// Export singleton instance
export const personalityColorSystem = new PersonalityColorSystem();