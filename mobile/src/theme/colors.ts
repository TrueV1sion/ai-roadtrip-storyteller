/**
 * Color palette following Bolt's dark theme design system
 * All colors are optimized for dark backgrounds and accessibility
 */

export const colors = {
  // Background colors
  background: {
    primary: '#0f0f23',    // Deep space black
    secondary: '#1a1a2e',  // Card backgrounds
    elevated: '#1e1b4b',   // Elevated surfaces
    overlay: 'rgba(0, 0, 0, 0.5)',
  },
  
  // Text colors
  text: {
    primary: '#ffffff',
    secondary: '#9ca3af',
    muted: '#6b7280',
    disabled: '#4b5563',
    inverse: '#0f0f23',
  },
  
  // Brand colors
  brand: {
    primary: '#7c3aed',    // Purple (AI/Voice)
    secondary: '#4f46e5',  // Indigo
    tertiary: '#2563eb',   // Blue
  },
  
  // Semantic colors
  semantic: {
    success: '#10b981',    // Emerald
    warning: '#f59e0b',    // Amber
    error: '#ef4444',      // Red
    info: '#3b82f6',       // Blue
  },
  
  // Personality colors
  personality: {
    mickey: '#ff6b6b',
    surfer: '#4ecdc4',
    mountain: '#45b7d1',
    dj: '#f39c12',
    scifi: '#00ffff',
    mystic: '#9370db',
  },
  
  // UI element colors
  ui: {
    border: '#374151',
    divider: '#1f2937',
    focus: '#7c3aed',
    hover: 'rgba(124, 58, 237, 0.1)',
    pressed: 'rgba(124, 58, 237, 0.2)',
  },
  
  // Social colors
  social: {
    facebook: '#1877f2',
    google: '#4285f4',
    apple: '#000000',
    twitter: '#1da1f2',
  },
  
  // Chart colors (for data visualization)
  chart: {
    primary: '#7c3aed',
    secondary: '#4f46e5',
    tertiary: '#2563eb',
    quaternary: '#10b981',
    quinary: '#f59e0b',
    senary: '#ef4444',
  },
  
  // Gradient definitions
  gradients: {
    primary: ['#7c3aed', '#4f46e5'],
    sunset: ['#ff6b6b', '#feca57'],
    ocean: ['#00d2ff', '#3a7bd5'],
    forest: ['#134e5e', '#71b280'],
    cosmic: ['#667eea', '#764ba2'],
    fire: ['#f12711', '#f5af19'],
  },
};

// Alpha variants for overlays and shadows
export const alpha = (color: string, opacity: number): string => {
  // Convert hex to rgba
  const hex = color.replace('#', '');
  const r = parseInt(hex.substring(0, 2), 16);
  const g = parseInt(hex.substring(2, 4), 16);
  const b = parseInt(hex.substring(4, 6), 16);
  
  return `rgba(${r}, ${g}, ${b}, ${opacity})`;
};

// Accessibility helpers
export const getContrastColor = (backgroundColor: string): string => {
  // Simple contrast calculation
  const hex = backgroundColor.replace('#', '');
  const r = parseInt(hex.substring(0, 2), 16);
  const g = parseInt(hex.substring(2, 4), 16);
  const b = parseInt(hex.substring(4, 6), 16);
  
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  
  return luminance > 0.5 ? colors.text.inverse : colors.text.primary;
};

// Export color modes for theme switching (future enhancement)
export const colorModes = {
  dark: colors, // Default
  // Light mode can be added in the future
};