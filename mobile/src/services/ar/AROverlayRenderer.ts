/**
 * AR Overlay Renderer
 * Handles rendering of AR overlays with high performance
 */

import { Canvas, Skia, useFont } from '@shopify/react-native-skia';
import { SharedValue, useAnimatedStyle, withSpring, withTiming } from 'react-native-reanimated';
import { ARLandmark } from './ARLandmarkService';
import { performanceMonitor } from '../performanceMonitor';

import { logger } from '@/services/logger';
export interface AROverlay {
  id: string;
  type: 'landmark' | 'navigation' | 'game' | 'photo';
  position: {
    x: number;
    y: number;
  };
  size: {
    width: number;
    height: number;
  };
  content: any;
  priority: number;
  opacity: SharedValue<number>;
  scale: SharedValue<number>;
  visible: boolean;
  interactive: boolean;
}

export interface OverlayTheme {
  backgroundColor: string;
  textColor: string;
  borderColor: string;
  borderWidth: number;
  borderRadius: number;
  shadowColor: string;
  shadowOpacity: number;
  shadowRadius: number;
  fontFamily: string;
}

export interface RenderConfig {
  maxOverlays: number;
  enableAnimations: boolean;
  enableShadows: boolean;
  enableBlur: boolean;
  performanceMode: 'high' | 'balanced' | 'battery';
  theme: 'light' | 'dark' | 'auto';
}

export class AROverlayRenderer {
  private static instance: AROverlayRenderer;
  private overlays: Map<string, AROverlay> = new Map();
  private renderConfig: RenderConfig;
  private themes: Record<string, OverlayTheme>;
  private frameCount: number = 0;
  private lastFrameTime: number = 0;
  private fps: number = 0;
  
  // Performance thresholds
  private readonly TARGET_FPS = 60;
  private readonly MIN_FPS = 30;
  private readonly OVERLAY_POOL_SIZE = 50;
  
  private constructor() {
    this.renderConfig = {
      maxOverlays: 10,
      enableAnimations: true,
      enableShadows: true,
      enableBlur: true,
      performanceMode: 'balanced',
      theme: 'auto',
    };
    
    this.themes = {
      light: {
        backgroundColor: 'rgba(255, 255, 255, 0.92)',
        textColor: '#1a1a1a',
        borderColor: 'rgba(0, 0, 0, 0.1)',
        borderWidth: 1,
        borderRadius: 16,
        shadowColor: '#000',
        shadowOpacity: 0.1,
        shadowRadius: 8,
        fontFamily: 'SF Pro Display',
      },
      dark: {
        backgroundColor: 'rgba(20, 20, 20, 0.88)',
        textColor: '#ffffff',
        borderColor: 'rgba(255, 255, 255, 0.1)',
        borderWidth: 1,
        borderRadius: 16,
        shadowColor: '#000',
        shadowOpacity: 0.3,
        shadowRadius: 12,
        fontFamily: 'SF Pro Display',
      },
    };
  }
  
  static getInstance(): AROverlayRenderer {
    if (!AROverlayRenderer.instance) {
      AROverlayRenderer.instance = new AROverlayRenderer();
    }
    return AROverlayRenderer.instance;
  }
  
  /**
   * Initialize renderer with configuration
   */
  initialize(config?: Partial<RenderConfig>): void {
    if (config) {
      this.renderConfig = { ...this.renderConfig, ...config };
    }
    
    // Adjust config based on performance mode
    this.optimizeForPerformanceMode();
    
    // Start performance monitoring
    this.startPerformanceMonitoring();
  }
  
  /**
   * Create landmark overlay
   */
  createLandmarkOverlay(landmark: ARLandmark): AROverlay {
    const theme = this.getCurrentTheme();
    
    return {
      id: `overlay_${landmark.id}`,
      type: 'landmark',
      position: landmark.screenPosition || { x: 0, y: 0 },
      size: { width: 280, height: 100 },
      content: {
        landmark,
        theme,
      },
      priority: this.calculatePriority(landmark),
      opacity: { value: 0 },
      scale: { value: 0.8 },
      visible: true,
      interactive: true,
    };
  }
  
  /**
   * Create navigation overlay
   */
  createNavigationOverlay(
    direction: string,
    distance: string,
    position: { x: number; y: number }
  ): AROverlay {
    const theme = this.getCurrentTheme();
    
    return {
      id: `nav_overlay_${Date.now()}`,
      type: 'navigation',
      position,
      size: { width: 200, height: 80 },
      content: {
        direction,
        distance,
        theme,
      },
      priority: 100, // High priority for navigation
      opacity: { value: 0 },
      scale: { value: 1 },
      visible: true,
      interactive: false,
    };
  }
  
  /**
   * Add overlay with animation
   */
  addOverlay(overlay: AROverlay): void {
    // Check overlay limit
    if (this.overlays.size >= this.renderConfig.maxOverlays) {
      this.removeLowestPriorityOverlay();
    }
    
    // Add overlay
    this.overlays.set(overlay.id, overlay);
    
    // Animate in
    if (this.renderConfig.enableAnimations) {
      overlay.opacity.value = withTiming(1, { duration: 300 });
      overlay.scale.value = withSpring(1, {
        damping: 15,
        stiffness: 100,
      });
    } else {
      overlay.opacity.value = 1;
      overlay.scale.value = 1;
    }
    
    // Log performance
    performanceMonitor.logEvent('ar_overlay_added', {
      type: overlay.type,
      overlayCount: this.overlays.size,
    });
  }
  
  /**
   * Remove overlay with animation
   */
  removeOverlay(id: string): void {
    const overlay = this.overlays.get(id);
    if (!overlay) return;
    
    // Animate out
    if (this.renderConfig.enableAnimations) {
      overlay.opacity.value = withTiming(0, { duration: 200 }, () => {
        this.overlays.delete(id);
      });
      overlay.scale.value = withTiming(0.8, { duration: 200 });
    } else {
      this.overlays.delete(id);
    }
  }
  
  /**
   * Update overlay positions
   */
  updateOverlayPositions(landmarks: ARLandmark[]): void {
    landmarks.forEach((landmark) => {
      const overlayId = `overlay_${landmark.id}`;
      const overlay = this.overlays.get(overlayId);
      
      if (overlay && landmark.screenPosition) {
        // Smooth position updates
        if (this.renderConfig.enableAnimations) {
          overlay.position = {
            x: withSpring(landmark.screenPosition.x, {
              damping: 20,
              stiffness: 90,
            }),
            y: withSpring(landmark.screenPosition.y, {
              damping: 20,
              stiffness: 90,
            }),
          };
        } else {
          overlay.position = landmark.screenPosition;
        }
        
        overlay.visible = landmark.screenPosition.visible;
      }
    });
  }
  
  /**
   * Render all overlays
   */
  renderOverlays(canvas: Canvas): void {
    const startTime = performance.now();
    
    // Sort overlays by priority
    const sortedOverlays = Array.from(this.overlays.values())
      .filter((overlay) => overlay.visible)
      .sort((a, b) => b.priority - a.priority)
      .slice(0, this.renderConfig.maxOverlays);
    
    // Render each overlay
    sortedOverlays.forEach((overlay) => {
      this.renderOverlay(canvas, overlay);
    });
    
    // Update performance metrics
    const renderTime = performance.now() - startTime;
    this.updatePerformanceMetrics(renderTime);
  }
  
  /**
   * Render individual overlay
   */
  private renderOverlay(canvas: Canvas, overlay: AROverlay): void {
    const paint = Skia.Paint();
    const theme = overlay.content.theme;
    
    // Background
    paint.setColor(Skia.Color(theme.backgroundColor));
    if (this.renderConfig.enableShadows) {
      paint.setMaskFilter(
        Skia.MaskFilter.MakeBlur(Skia.BlurStyle.Normal, theme.shadowRadius)
      );
    }
    
    const rect = Skia.RRect.MakeRectXY(
      Skia.Rect.MakeXYWH(
        overlay.position.x - overlay.size.width / 2,
        overlay.position.y - overlay.size.height / 2,
        overlay.size.width,
        overlay.size.height
      ),
      theme.borderRadius,
      theme.borderRadius
    );
    
    canvas.drawRRect(rect, paint);
    
    // Border
    paint.setStyle(Skia.PaintStyle.Stroke);
    paint.setStrokeWidth(theme.borderWidth);
    paint.setColor(Skia.Color(theme.borderColor));
    canvas.drawRRect(rect, paint);
    
    // Content
    switch (overlay.type) {
      case 'landmark':
        this.renderLandmarkContent(canvas, overlay);
        break;
      case 'navigation':
        this.renderNavigationContent(canvas, overlay);
        break;
      case 'game':
        this.renderGameContent(canvas, overlay);
        break;
      case 'photo':
        this.renderPhotoContent(canvas, overlay);
        break;
    }
  }
  
  /**
   * Render landmark content
   */
  private renderLandmarkContent(canvas: Canvas, overlay: AROverlay): void {
    const landmark = overlay.content.landmark as ARLandmark;
    const theme = overlay.content.theme;
    const font = useFont(require('../../assets/fonts/SF-Pro-Display-Bold.otf'), 18);
    
    if (!font) return;
    
    const x = overlay.position.x - overlay.size.width / 2 + 20;
    const y = overlay.position.y - overlay.size.height / 2 + 30;
    
    // Icon based on type
    const icon = this.getLandmarkIcon(landmark.type);
    canvas.drawText(icon, x, y, font, Skia.Paint());
    
    // Name
    const namePaint = Skia.Paint();
    namePaint.setColor(Skia.Color(theme.textColor));
    canvas.drawText(landmark.name, x + 30, y, font, namePaint);
    
    // Distance
    const distanceFont = useFont(require('../../assets/fonts/SF-Pro-Text-Regular.otf'), 14);
    if (distanceFont) {
      const distanceText = this.formatDistance(landmark.distance);
      canvas.drawText(distanceText, x, y + 25, distanceFont, namePaint);
    }
    
    // Rating
    if (landmark.rating) {
      const ratingText = `★ ${landmark.rating.toFixed(1)}`;
      canvas.drawText(ratingText, x, y + 45, distanceFont, namePaint);
    }
  }
  
  /**
   * Get current theme based on config
   */
  private getCurrentTheme(): OverlayTheme {
    if (this.renderConfig.theme === 'auto') {
      // Would check system theme
      return this.themes.light;
    }
    return this.themes[this.renderConfig.theme] || this.themes.light;
  }
  
  /**
   * Calculate overlay priority
   */
  private calculatePriority(landmark: ARLandmark): number {
    let priority = 50; // Base priority
    
    // Adjust by type
    if (landmark.type === 'historical') priority += 20;
    if (landmark.type === 'landmark') priority += 10;
    
    // Adjust by distance (closer = higher priority)
    priority += Math.max(0, 20 - landmark.distance / 50);
    
    // Adjust by rating
    if (landmark.rating) {
      priority += landmark.rating * 2;
    }
    
    return Math.round(priority);
  }
  
  /**
   * Remove lowest priority overlay
   */
  private removeLowestPriorityOverlay(): void {
    let lowestPriority = Infinity;
    let lowestId = '';
    
    this.overlays.forEach((overlay) => {
      if (overlay.priority < lowestPriority) {
        lowestPriority = overlay.priority;
        lowestId = overlay.id;
      }
    });
    
    if (lowestId) {
      this.removeOverlay(lowestId);
    }
  }
  
  /**
   * Optimize settings for performance mode
   */
  private optimizeForPerformanceMode(): void {
    switch (this.renderConfig.performanceMode) {
      case 'high':
        // All features enabled
        break;
      
      case 'balanced':
        // Reduce some effects
        this.renderConfig.enableBlur = false;
        this.renderConfig.maxOverlays = 8;
        break;
      
      case 'battery':
        // Minimize processing
        this.renderConfig.enableAnimations = false;
        this.renderConfig.enableShadows = false;
        this.renderConfig.enableBlur = false;
        this.renderConfig.maxOverlays = 5;
        break;
    }
  }
  
  /**
   * Update performance metrics
   */
  private updatePerformanceMetrics(renderTime: number): void {
    this.frameCount++;
    
    const now = Date.now();
    const deltaTime = now - this.lastFrameTime;
    
    if (deltaTime >= 1000) {
      // Calculate FPS
      this.fps = (this.frameCount * 1000) / deltaTime;
      this.frameCount = 0;
      this.lastFrameTime = now;
      
      // Adapt quality if needed
      if (this.fps < this.MIN_FPS) {
        this.adaptQualityForPerformance();
      }
      
      // Log metrics
      performanceMonitor.logMetric('ar_overlay_fps', this.fps);
      performanceMonitor.logMetric('ar_overlay_render_time', renderTime);
    }
  }
  
  /**
   * Adapt quality settings for better performance
   */
  private adaptQualityForPerformance(): void {
    if (this.renderConfig.performanceMode === 'high') {
      // Switch to balanced mode
      this.renderConfig.performanceMode = 'balanced';
      this.optimizeForPerformanceMode();
      logger.debug('AR: Switching to balanced performance mode');
    }
  }
  
  /**
   * Start performance monitoring
   */
  private startPerformanceMonitoring(): void {
    setInterval(() => {
      performanceMonitor.logMetric('ar_overlay_count', this.overlays.size);
      performanceMonitor.logMetric('ar_overlay_memory', this.estimateMemoryUsage());
    }, 5000);
  }
  
  /**
   * Estimate memory usage
   */
  private estimateMemoryUsage(): number {
    // Rough estimate: 10KB per overlay
    return this.overlays.size * 10 * 1024; // bytes
  }
  
  /**
   * Get landmark icon
   */
  private getLandmarkIcon(type: string): string {
    const icons: Record<string, string> = {
      landmark: '🏛️',
      historical: '🏺',
      restaurant: '🍽️',
      nature: '🌳',
      entertainment: '🎭',
    };
    return icons[type] || '📍';
  }
  
  /**
   * Format distance for display
   */
  private formatDistance(meters: number): string {
    if (meters < 100) {
      return `${Math.round(meters)}m`;
    } else if (meters < 1000) {
      return `${Math.round(meters / 10) * 10}m`;
    } else {
      return `${(meters / 1000).toFixed(1)}km`;
    }
  }
  
  /**
   * Clear all overlays
   */
  clearOverlays(): void {
    this.overlays.forEach((overlay) => {
      this.removeOverlay(overlay.id);
    });
  }
  
  /**
   * Get current configuration
   */
  getConfig(): RenderConfig {
    return { ...this.renderConfig };
  }
  
  /**
   * Update configuration
   */
  updateConfig(config: Partial<RenderConfig>): void {
    this.renderConfig = { ...this.renderConfig, ...config };
    this.optimizeForPerformanceMode();
  }
}

// Export singleton instance
export const arOverlayRenderer = AROverlayRenderer.getInstance();
