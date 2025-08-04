/**
 * Performance Monitoring Service for React Native
 * Tracks app performance, screen load times, and API latency
 */

import * as Sentry from 'sentry-expo';
import { sentryService } from './SentryService';
import { InteractionManager } from 'react-native';

export interface PerformanceMetrics {
  screenName: string;
  loadTime: number;
  renderTime: number;
  apiCalls: number;
  totalApiTime: number;
  memoryUsage?: number;
  jsFrameRate?: number;
}

class PerformanceMonitoring {
  private static instance: PerformanceMonitoring;
  private transactions: Map<string, Sentry.Native.Transaction> = new Map();
  private screenMetrics: Map<string, PerformanceMetrics> = new Map();
  private apiMetrics: Map<string, { count: number; totalTime: number }> = new Map();

  private constructor() {}

  static getInstance(): PerformanceMonitoring {
    if (!PerformanceMonitoring.instance) {
      PerformanceMonitoring.instance = new PerformanceMonitoring();
    }
    return PerformanceMonitoring.instance;
  }

  /**
   * Start screen performance tracking
   */
  startScreenTracking(screenName: string): void {
    if (!sentryService.isInitialized()) return;

    // Start Sentry transaction
    const transaction = sentryService.startTransaction(
      screenName,
      'navigation',
      `Screen: ${screenName}`
    );

    if (transaction) {
      this.transactions.set(screenName, transaction);
      
      // Initialize screen metrics
      this.screenMetrics.set(screenName, {
        screenName,
        loadTime: 0,
        renderTime: 0,
        apiCalls: 0,
        totalApiTime: 0,
      });

      // Track screen view
      sentryService.addBreadcrumb({
        message: `Screen viewed: ${screenName}`,
        category: 'navigation',
        type: 'navigation',
        level: 'info',
        data: {
          screen: screenName,
          timestamp: new Date().toISOString(),
        },
      });
    }
  }

  /**
   * Mark screen as loaded (initial render complete)
   */
  markScreenLoaded(screenName: string): void {
    const transaction = this.transactions.get(screenName);
    const metrics = this.screenMetrics.get(screenName);

    if (transaction && metrics) {
      const loadTime = performance.now();
      metrics.loadTime = loadTime;

      // Create span for loading
      const loadSpan = transaction.startChild({
        op: 'ui.load',
        description: `Load ${screenName}`,
      });
      loadSpan.finish();

      // Wait for interactions to complete
      InteractionManager.runAfterInteractions(() => {
        this.markScreenReady(screenName);
      });
    }
  }

  /**
   * Mark screen as ready (all interactions complete)
   */
  private markScreenReady(screenName: string): void {
    const transaction = this.transactions.get(screenName);
    const metrics = this.screenMetrics.get(screenName);

    if (transaction && metrics) {
      const renderTime = performance.now();
      metrics.renderTime = renderTime - metrics.loadTime;

      // Add performance data to transaction
      transaction.setData('load_time', metrics.loadTime);
      transaction.setData('render_time', metrics.renderTime);
      transaction.setData('total_time', renderTime);

      // Set measurement for better insights
      transaction.setMeasurement('load_time', metrics.loadTime, 'millisecond');
      transaction.setMeasurement('render_time', metrics.renderTime, 'millisecond');

      // Categorize performance
      const performanceLevel = this.categorizePerformance(renderTime);
      transaction.setTag('performance_level', performanceLevel);

      // Send custom performance event
      sentryService.captureMessage(
        `Screen Performance: ${screenName}`,
        'info',
        {
          tags: {
            screen: screenName,
            performance: performanceLevel,
          },
          extra: {
            metrics,
          },
        }
      );
    }
  }

  /**
   * End screen tracking
   */
  endScreenTracking(screenName: string): void {
    const transaction = this.transactions.get(screenName);
    const metrics = this.screenMetrics.get(screenName);

    if (transaction) {
      // Add final metrics
      if (metrics) {
        transaction.setData('api_calls', metrics.apiCalls);
        transaction.setData('total_api_time', metrics.totalApiTime);
        
        if (metrics.apiCalls > 0) {
          const avgApiTime = metrics.totalApiTime / metrics.apiCalls;
          transaction.setMeasurement('avg_api_time', avgApiTime, 'millisecond');
        }
      }

      // Finish transaction
      transaction.finish();
      this.transactions.delete(screenName);
    }

    // Clean up metrics
    this.screenMetrics.delete(screenName);
  }

  /**
   * Track API call performance
   */
  async trackApiCall<T>(
    url: string,
    method: string,
    fn: () => Promise<T>
  ): Promise<T> {
    const startTime = performance.now();
    const currentScreen = this.getCurrentScreen();
    
    // Start span for API call
    let span: Sentry.Native.Span | undefined;
    const transaction = currentScreen ? this.transactions.get(currentScreen) : undefined;
    
    if (transaction) {
      span = transaction.startChild({
        op: 'http',
        description: `${method} ${url}`,
      });
    }

    try {
      const result = await fn();
      const endTime = performance.now();
      const duration = endTime - startTime;

      // Record successful API call
      this.recordApiMetrics(url, duration, 'success', currentScreen);
      
      if (span) {
        span.setStatus('ok');
        span.setData('http.status_code', 200);
        span.finish();
      }

      // Track API performance
      sentryService.trackApiCall(method, url, 200, duration);

      return result;
    } catch (error) {
      const endTime = performance.now();
      const duration = endTime - startTime;

      // Record failed API call
      this.recordApiMetrics(url, duration, 'error', currentScreen);
      
      if (span) {
        span.setStatus('internal_error');
        span.setData('error', error);
        span.finish();
      }

      // Track API error
      const status = (error as any)?.response?.status || 0;
      sentryService.trackApiCall(method, url, status, duration);

      throw error;
    }
  }

  /**
   * Record API metrics
   */
  private recordApiMetrics(
    url: string,
    duration: number,
    status: 'success' | 'error',
    screenName?: string
  ): void {
    // Update global API metrics
    const apiMetric = this.apiMetrics.get(url) || { count: 0, totalTime: 0 };
    apiMetric.count++;
    apiMetric.totalTime += duration;
    this.apiMetrics.set(url, apiMetric);

    // Update screen-specific metrics
    if (screenName) {
      const screenMetric = this.screenMetrics.get(screenName);
      if (screenMetric) {
        screenMetric.apiCalls++;
        screenMetric.totalApiTime += duration;
      }
    }

    // Alert on slow API calls
    if (duration > 3000) {
      sentryService.captureMessage(
        `Slow API Call: ${url}`,
        'warning',
        {
          tags: {
            api_performance: 'slow',
            status,
          },
          extra: {
            url,
            duration,
            threshold: 3000,
          },
        }
      );
    }
  }

  /**
   * Track custom performance metric
   */
  trackCustomMetric(
    name: string,
    value: number,
    unit: 'millisecond' | 'second' | 'byte' | 'percent' | 'none' = 'none'
  ): void {
    const currentScreen = this.getCurrentScreen();
    const transaction = currentScreen ? this.transactions.get(currentScreen) : undefined;

    if (transaction) {
      transaction.setMeasurement(name, value, unit);
    }

    // Send custom metric event
    sentryService.captureMessage(
      `Custom Metric: ${name}`,
      'info',
      {
        tags: {
          metric_name: name,
          metric_unit: unit,
        },
        extra: {
          value,
          screen: currentScreen,
        },
      }
    );
  }

  /**
   * Track JS frame rate
   */
  trackFrameRate(frameRate: number): void {
    const currentScreen = this.getCurrentScreen();
    
    if (currentScreen) {
      const metrics = this.screenMetrics.get(currentScreen);
      if (metrics) {
        metrics.jsFrameRate = frameRate;
      }
    }

    // Alert on low frame rate
    if (frameRate < 30) {
      sentryService.captureMessage(
        'Low Frame Rate Detected',
        'warning',
        {
          tags: {
            performance_issue: 'low_frame_rate',
            screen: currentScreen || 'unknown',
          },
          extra: {
            frameRate,
            threshold: 30,
          },
        }
      );
    }
  }

  /**
   * Track memory usage
   */
  trackMemoryUsage(usedMemory: number, totalMemory: number): void {
    const memoryPercentage = (usedMemory / totalMemory) * 100;
    const currentScreen = this.getCurrentScreen();

    if (currentScreen) {
      const metrics = this.screenMetrics.get(currentScreen);
      if (metrics) {
        metrics.memoryUsage = memoryPercentage;
      }
    }

    // Alert on high memory usage
    if (memoryPercentage > 80) {
      sentryService.captureMessage(
        'High Memory Usage',
        'warning',
        {
          tags: {
            performance_issue: 'high_memory',
            screen: currentScreen || 'unknown',
          },
          extra: {
            usedMemory,
            totalMemory,
            percentage: memoryPercentage,
          },
        }
      );
    }
  }

  /**
   * Track app startup time
   */
  trackAppStartup(startupTime: number): void {
    const transaction = sentryService.startTransaction(
      'app_startup',
      'app.start',
      'Application Startup'
    );

    if (transaction) {
      transaction.setMeasurement('startup_time', startupTime, 'millisecond');
      
      // Categorize startup performance
      let performanceLevel = 'excellent';
      if (startupTime > 5000) performanceLevel = 'poor';
      else if (startupTime > 3000) performanceLevel = 'fair';
      else if (startupTime > 1500) performanceLevel = 'good';

      transaction.setTag('startup_performance', performanceLevel);
      transaction.finish();

      // Send startup metric
      sentryService.captureMessage(
        'App Startup Time',
        'info',
        {
          tags: {
            startup_performance: performanceLevel,
          },
          extra: {
            startup_time: startupTime,
          },
        }
      );
    }
  }

  /**
   * Get current screen name (you'll need to implement this based on your navigation)
   */
  private getCurrentScreen(): string | undefined {
    // This should be integrated with your navigation system
    // For now, return the first active transaction
    return Array.from(this.transactions.keys())[0];
  }

  /**
   * Categorize performance based on time
   */
  private categorizePerformance(timeMs: number): string {
    if (timeMs < 1000) return 'excellent';
    if (timeMs < 2000) return 'good';
    if (timeMs < 3000) return 'fair';
    return 'poor';
  }

  /**
   * Get performance summary
   */
  getPerformanceSummary(): {
    screens: Map<string, PerformanceMetrics>;
    apis: Map<string, { count: number; totalTime: number; avgTime: number }>;
  } {
    const apiSummary = new Map();
    
    this.apiMetrics.forEach((metric, url) => {
      apiSummary.set(url, {
        ...metric,
        avgTime: metric.totalTime / metric.count,
      });
    });

    return {
      screens: new Map(this.screenMetrics),
      apis: apiSummary,
    };
  }

  /**
   * Clear all metrics
   */
  clearMetrics(): void {
    this.transactions.clear();
    this.screenMetrics.clear();
    this.apiMetrics.clear();
  }
}

export const performanceMonitoring = PerformanceMonitoring.getInstance();

// Export convenience functions
export const startScreenTracking = (screenName: string) =>
  performanceMonitoring.startScreenTracking(screenName);

export const markScreenLoaded = (screenName: string) =>
  performanceMonitoring.markScreenLoaded(screenName);

export const endScreenTracking = (screenName: string) =>
  performanceMonitoring.endScreenTracking(screenName);

export const trackApiCall = <T>(url: string, method: string, fn: () => Promise<T>) =>
  performanceMonitoring.trackApiCall(url, method, fn);

export const trackCustomMetric = (name: string, value: number, unit?: any) =>
  performanceMonitoring.trackCustomMetric(name, value, unit);

export const trackAppStartup = (startupTime: number) =>
  performanceMonitoring.trackAppStartup(startupTime);