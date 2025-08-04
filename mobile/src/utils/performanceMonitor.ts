/**
 * Performance monitoring utility for React Native
 */
import { InteractionManager, NativeModules, Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { logger } from '@/services/logger';
interface PerformanceMetrics {
  componentName: string;
  renderTime: number;
  mountTime: number;
  interactionTime: number;
  memoryUsage?: number;
  timestamp: number;
}

interface PerformanceReport {
  averageRenderTime: number;
  averageMountTime: number;
  averageInteractionTime: number;
  totalRenders: number;
  slowRenders: number;
  memoryPeaks: number[];
}

class PerformanceMonitor {
  private metrics: Map<string, PerformanceMetrics[]> = new Map();
  private isEnabled: boolean = __DEV__;
  private slowRenderThreshold: number = 16.67; // 60fps threshold
  private metricsLimit: number = 100; // Keep last 100 metrics per component
  private reportInterval: number = 60000; // 1 minute

  constructor() {
    if (this.isEnabled) {
      this.startPeriodicReporting();
      this.setupMemoryMonitoring();
    }
  }

  /**
   * Track component render performance
   */
  trackRender(componentName: string, renderTime: number) {
    if (!this.isEnabled) return;

    const metrics = this.getComponentMetrics(componentName);
    
    // Warn about slow renders
    if (renderTime > this.slowRenderThreshold) {
      logger.warn(
        `[Performance] Slow render detected in ${componentName}: ${renderTime.toFixed(2)}ms`
      );
    }

    metrics.push({
      componentName,
      renderTime,
      mountTime: 0,
      interactionTime: 0,
      timestamp: Date.now()
    });

    this.trimMetrics(componentName);
  }

  /**
   * Track component mount performance
   */
  trackMount(componentName: string, mountTime: number) {
    if (!this.isEnabled) return;

    const metrics = this.getComponentMetrics(componentName);
    
    metrics.push({
      componentName,
      renderTime: 0,
      mountTime,
      interactionTime: 0,
      timestamp: Date.now()
    });

    this.trimMetrics(componentName);
  }

  /**
   * Track user interaction performance
   */
  async trackInteraction(
    interactionName: string,
    operation: () => Promise<any>
  ): Promise<any> {
    if (!this.isEnabled) {
      return operation();
    }

    const startTime = Date.now();
    
    try {
      // Wait for animations to complete
      await InteractionManager.runAfterInteractions(async () => {
        const result = await operation();
        const interactionTime = Date.now() - startTime;
        
        const metrics = this.getComponentMetrics(interactionName);
        metrics.push({
          componentName: interactionName,
          renderTime: 0,
          mountTime: 0,
          interactionTime,
          timestamp: Date.now()
        });

        this.trimMetrics(interactionName);
        
        if (interactionTime > 100) {
          logger.warn(
            `[Performance] Slow interaction detected: ${interactionName} took ${interactionTime}ms`
          );
        }
        
        return result;
      });
    } catch (error) {
      logger.error(`[Performance] Interaction error in ${interactionName}:`, error);
      throw error;
    }
  }

  /**
   * Get performance report for a component
   */
  getReport(componentName: string): PerformanceReport | null {
    const metrics = this.metrics.get(componentName);
    if (!metrics || metrics.length === 0) return null;

    const renderTimes = metrics.map(m => m.renderTime).filter(t => t > 0);
    const mountTimes = metrics.map(m => m.mountTime).filter(t => t > 0);
    const interactionTimes = metrics.map(m => m.interactionTime).filter(t => t > 0);

    return {
      averageRenderTime: this.average(renderTimes),
      averageMountTime: this.average(mountTimes),
      averageInteractionTime: this.average(interactionTimes),
      totalRenders: renderTimes.length,
      slowRenders: renderTimes.filter(t => t > this.slowRenderThreshold).length,
      memoryPeaks: [] // TODO: Implement memory tracking
    };
  }

  /**
   * Get overall performance summary
   */
  getSummary(): Map<string, PerformanceReport> {
    const summary = new Map<string, PerformanceReport>();
    
    for (const [componentName] of this.metrics) {
      const report = this.getReport(componentName);
      if (report) {
        summary.set(componentName, report);
      }
    }
    
    return summary;
  }

  /**
   * Clear all metrics
   */
  clearMetrics() {
    this.metrics.clear();
  }

  /**
   * Export metrics to AsyncStorage
   */
  async exportMetrics(): Promise<void> {
    try {
      const summary = this.getSummary();
      const data = Object.fromEntries(summary);
      
      await AsyncStorage.setItem(
        '@performance_metrics',
        JSON.stringify({
          data,
          exportedAt: Date.now()
        })
      );
      
      logger.debug('[Performance] Metrics exported successfully');
    } catch (error) {
      logger.error('[Performance] Failed to export metrics:', error);
    }
  }

  /**
   * Private helper methods
   */
  private getComponentMetrics(componentName: string): PerformanceMetrics[] {
    if (!this.metrics.has(componentName)) {
      this.metrics.set(componentName, []);
    }
    return this.metrics.get(componentName)!;
  }

  private trimMetrics(componentName: string) {
    const metrics = this.metrics.get(componentName);
    if (metrics && metrics.length > this.metricsLimit) {
      metrics.splice(0, metrics.length - this.metricsLimit);
    }
  }

  private average(numbers: number[]): number {
    if (numbers.length === 0) return 0;
    return numbers.reduce((a, b) => a + b, 0) / numbers.length;
  }

  private startPeriodicReporting() {
    setInterval(() => {
      const summary = this.getSummary();
      
      if (summary.size > 0) {
        logger.debug('[Performance] Periodic Report:');
        summary.forEach((report, componentName) => {
          if (report.totalRenders > 0) {
            logger.debug(`  ${componentName}:`, {
              avgRender: `${report.averageRenderTime.toFixed(2)}ms`,
              slowRenders: `${report.slowRenders}/${report.totalRenders}`,
              avgMount: `${report.averageMountTime.toFixed(2)}ms`
            });
          }
        });
      }
    }, this.reportInterval);
  }

  private setupMemoryMonitoring() {
    if (Platform.OS === 'android' && NativeModules.DeviceInfo) {
      // Android memory monitoring
      setInterval(() => {
        try {
          // This would require a native module implementation
          // NativeModules.DeviceInfo.getMemoryInfo((info) => {
          //   if (info.availMem < 50 * 1024 * 1024) { // Less than 50MB
          //     logger.warn('[Performance] Low memory warning:', info);
          //   }
          // });
        } catch (error) {
          // Silently fail if module not available
        }
      }, 30000); // Check every 30 seconds
    }
  }
}

// Singleton instance
export const performanceMonitor = new PerformanceMonitor();

// Performance HOC for class components
export function withPerformanceTracking<P extends object>(
  Component: React.ComponentType<P>,
  componentName?: string
) {
  const displayName = componentName || Component.displayName || Component.name || 'Component';
  
  return class extends React.Component<P> {
    private mountTime: number = 0;

    componentDidMount() {
      this.mountTime = Date.now();
      performanceMonitor.trackMount(displayName, Date.now() - this.mountTime);
    }

    componentDidUpdate() {
      performanceMonitor.trackRender(displayName, Date.now() - this.mountTime);
    }

    render() {
      const startTime = Date.now();
      const result = <Component {...this.props} />;
      performanceMonitor.trackRender(displayName, Date.now() - startTime);
      return result;
    }
  };
}

// React Navigation performance tracking
export function trackNavigationPerformance(routeName: string) {
  const startTime = Date.now();
  
  return {
    onTransitionStart: () => {
      logger.debug(`[Navigation] Starting transition to ${routeName}`);
    },
    onTransitionEnd: () => {
      const duration = Date.now() - startTime;
      logger.debug(`[Navigation] Completed transition to ${routeName} in ${duration}ms`);
      
      if (duration > 300) {
        logger.warn(`[Navigation] Slow transition detected: ${routeName} took ${duration}ms`);
      }
    }
  };
}