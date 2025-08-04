/**
 * Unified Monitoring Service
 * Integrates performance monitoring, error tracking, and alerting
 */

import { performanceMonitoring } from '../sentry/PerformanceMonitoring';
import { sentryService } from '../sentry/SentryService';
import { logger } from '../logger';
import { Platform, AppState, AppStateStatus } from 'react-native';
import NetInfo from '@react-native-community/netinfo';
import DeviceInfo from 'react-native-device-info';

export interface MonitoringConfig {
  enablePerformanceMonitoring: boolean;
  enableErrorTracking: boolean;
  enableNetworkMonitoring: boolean;
  enableDeviceMonitoring: boolean;
  enableCustomMetrics: boolean;
  sampleRate: number;
}

export interface HealthMetrics {
  timestamp: string;
  appVersion: string;
  platform: string;
  osVersion: string;
  deviceModel: string;
  isConnected: boolean;
  connectionType: string | null;
  memoryUsage: number;
  batteryLevel: number;
  diskSpace: number;
  crashFreeRate: number;
  activeUsers: number;
  apiHealth: Record<string, { success: number; failure: number; avgLatency: number }>;
}

export interface Alert {
  id: string;
  type: 'error' | 'warning' | 'info';
  title: string;
  message: string;
  threshold?: number;
  currentValue?: number;
  timestamp: string;
  metadata?: Record<string, any>;
}

class MonitoringService {
  private static instance: MonitoringService;
  private config: MonitoringConfig;
  private isInitialized = false;
  private appStateSubscription: any;
  private netInfoSubscription: any;
  private sessionStartTime: number = Date.now();
  private sessionEvents: number = 0;
  private alerts: Alert[] = [];
  private healthCheckInterval?: NodeJS.Timeout;

  private readonly THRESHOLDS = {
    ERROR_RATE: 0.05, // 5% error rate
    CRASH_FREE_RATE: 0.95, // 95% crash-free
    API_LATENCY: 3000, // 3 seconds
    MEMORY_USAGE: 0.8, // 80% memory
    BATTERY_LOW: 0.2, // 20% battery
    DISK_SPACE_LOW: 0.1, // 10% free space
    SLOW_SCREEN_LOAD: 3000, // 3 seconds
  };

  private constructor() {
    this.config = {
      enablePerformanceMonitoring: true,
      enableErrorTracking: true,
      enableNetworkMonitoring: true,
      enableDeviceMonitoring: true,
      enableCustomMetrics: true,
      sampleRate: 1.0,
    };
  }

  static getInstance(): MonitoringService {
    if (!MonitoringService.instance) {
      MonitoringService.instance = new MonitoringService();
    }
    return MonitoringService.instance;
  }

  /**
   * Initialize monitoring service
   */
  async initialize(config?: Partial<MonitoringConfig>): Promise<void> {
    if (this.isInitialized) {
      logger.warn('Monitoring service already initialized');
      return;
    }

    this.config = { ...this.config, ...config };

    try {
      // Initialize Sentry if not already done
      if (!sentryService.isInitialized()) {
        await sentryService.initialize();
      }

      // Set up app state monitoring
      this.setupAppStateMonitoring();

      // Set up network monitoring
      if (this.config.enableNetworkMonitoring) {
        this.setupNetworkMonitoring();
      }

      // Set up device monitoring
      if (this.config.enableDeviceMonitoring) {
        this.setupDeviceMonitoring();
      }

      // Start health check interval
      this.startHealthChecks();

      // Track app startup
      const startupTime = Date.now() - this.sessionStartTime;
      performanceMonitoring.trackAppStartup(startupTime);

      this.isInitialized = true;
      logger.info('Monitoring service initialized', { config: this.config });
    } catch (error) {
      logger.error('Failed to initialize monitoring service', error as Error);
      sentryService.captureException(error);
    }
  }

  /**
   * Set up app state monitoring
   */
  private setupAppStateMonitoring(): void {
    this.appStateSubscription = AppState.addEventListener(
      'change',
      (nextAppState: AppStateStatus) => {
        this.trackAppStateChange(nextAppState);
      }
    );
  }

  /**
   * Set up network monitoring
   */
  private setupNetworkMonitoring(): void {
    this.netInfoSubscription = NetInfo.addEventListener(state => {
      this.trackNetworkChange(state);
    });
  }

  /**
   * Set up device monitoring
   */
  private async setupDeviceMonitoring(): Promise<void> {
    try {
      // Monitor battery level
      const batteryLevel = await DeviceInfo.getBatteryLevel();
      if (batteryLevel < this.THRESHOLDS.BATTERY_LOW) {
        this.createAlert({
          type: 'warning',
          title: 'Low Battery',
          message: `Battery level is ${(batteryLevel * 100).toFixed(0)}%`,
          threshold: this.THRESHOLDS.BATTERY_LOW,
          currentValue: batteryLevel,
        });
      }

      // Monitor disk space
      const freeDiskStorage = await DeviceInfo.getFreeDiskStorage();
      const totalDiskCapacity = await DeviceInfo.getTotalDiskCapacity();
      const diskUsageRatio = 1 - (freeDiskStorage / totalDiskCapacity);
      
      if (diskUsageRatio > (1 - this.THRESHOLDS.DISK_SPACE_LOW)) {
        this.createAlert({
          type: 'warning',
          title: 'Low Disk Space',
          message: `Only ${((1 - diskUsageRatio) * 100).toFixed(0)}% disk space remaining`,
          threshold: this.THRESHOLDS.DISK_SPACE_LOW,
          currentValue: 1 - diskUsageRatio,
        });
      }
    } catch (error) {
      logger.error('Device monitoring error', error as Error);
    }
  }

  /**
   * Start periodic health checks
   */
  private startHealthChecks(): void {
    // Run health check every 5 minutes
    this.healthCheckInterval = setInterval(() => {
      this.performHealthCheck();
    }, 5 * 60 * 1000);

    // Run initial health check
    this.performHealthCheck();
  }

  /**
   * Perform health check
   */
  private async performHealthCheck(): Promise<void> {
    try {
      const metrics = await this.collectHealthMetrics();
      
      // Check crash-free rate
      if (metrics.crashFreeRate < this.THRESHOLDS.CRASH_FREE_RATE) {
        this.createAlert({
          type: 'error',
          title: 'High Crash Rate',
          message: `Crash-free rate is ${(metrics.crashFreeRate * 100).toFixed(1)}%`,
          threshold: this.THRESHOLDS.CRASH_FREE_RATE,
          currentValue: metrics.crashFreeRate,
        });
      }

      // Check API health
      Object.entries(metrics.apiHealth).forEach(([endpoint, stats]) => {
        const errorRate = stats.failure / (stats.success + stats.failure);
        if (errorRate > this.THRESHOLDS.ERROR_RATE) {
          this.createAlert({
            type: 'error',
            title: 'High API Error Rate',
            message: `${endpoint} has ${(errorRate * 100).toFixed(1)}% error rate`,
            threshold: this.THRESHOLDS.ERROR_RATE,
            currentValue: errorRate,
            metadata: { endpoint, stats },
          });
        }

        if (stats.avgLatency > this.THRESHOLDS.API_LATENCY) {
          this.createAlert({
            type: 'warning',
            title: 'Slow API Response',
            message: `${endpoint} average latency is ${stats.avgLatency}ms`,
            threshold: this.THRESHOLDS.API_LATENCY,
            currentValue: stats.avgLatency,
            metadata: { endpoint, stats },
          });
        }
      });

      // Send health metrics to backend
      this.sendHealthMetrics(metrics);
    } catch (error) {
      logger.error('Health check failed', error as Error);
    }
  }

  /**
   * Collect health metrics
   */
  private async collectHealthMetrics(): Promise<HealthMetrics> {
    const netInfo = await NetInfo.fetch();
    const performanceSummary = performanceMonitoring.getPerformanceSummary();
    
    // Calculate API health from performance data
    const apiHealth: Record<string, any> = {};
    performanceSummary.apis.forEach((stats, endpoint) => {
      apiHealth[endpoint] = {
        success: stats.count, // This is simplified - you'd track success/failure separately
        failure: 0,
        avgLatency: stats.avgTime,
      };
    });

    return {
      timestamp: new Date().toISOString(),
      appVersion: DeviceInfo.getVersion(),
      platform: Platform.OS,
      osVersion: DeviceInfo.getSystemVersion(),
      deviceModel: DeviceInfo.getModel(),
      isConnected: netInfo.isConnected || false,
      connectionType: netInfo.type,
      memoryUsage: await this.getMemoryUsage(),
      batteryLevel: await DeviceInfo.getBatteryLevel(),
      diskSpace: await this.getDiskSpacePercentage(),
      crashFreeRate: 0.99, // This would come from crash reporting service
      activeUsers: 1, // This would come from analytics
      apiHealth,
    };
  }

  /**
   * Track screen performance
   */
  trackScreen(screenName: string): {
    start: () => void;
    loaded: () => void;
    end: () => void;
  } {
    performanceMonitoring.startScreenTracking(screenName);
    
    return {
      start: () => performanceMonitoring.startScreenTracking(screenName),
      loaded: () => {
        performanceMonitoring.markScreenLoaded(screenName);
        this.sessionEvents++;
      },
      end: () => {
        performanceMonitoring.endScreenTracking(screenName);
        
        // Check for slow screen loads
        const metrics = performanceMonitoring.getPerformanceSummary();
        const screenMetric = metrics.screens.get(screenName);
        if (screenMetric && screenMetric.renderTime > this.THRESHOLDS.SLOW_SCREEN_LOAD) {
          this.createAlert({
            type: 'warning',
            title: 'Slow Screen Load',
            message: `${screenName} took ${screenMetric.renderTime}ms to load`,
            threshold: this.THRESHOLDS.SLOW_SCREEN_LOAD,
            currentValue: screenMetric.renderTime,
            metadata: { screenName, metrics: screenMetric },
          });
        }
      },
    };
  }

  /**
   * Track custom event
   */
  trackEvent(eventName: string, properties?: Record<string, any>): void {
    if (!this.shouldSample()) return;

    sentryService.addBreadcrumb({
      message: eventName,
      category: 'custom',
      type: 'info',
      level: 'info',
      data: properties,
    });

    this.sessionEvents++;
    
    logger.info(`Event: ${eventName}`, properties);
  }

  /**
   * Track custom metric
   */
  trackMetric(
    name: string,
    value: number,
    unit: 'millisecond' | 'second' | 'byte' | 'percent' | 'none' = 'none',
    tags?: Record<string, string>
  ): void {
    if (!this.config.enableCustomMetrics || !this.shouldSample()) return;

    performanceMonitoring.trackCustomMetric(name, value, unit);
    
    // Log metric for backend aggregation
    logger.info('Custom metric', {
      name,
      value,
      unit,
      tags,
      timestamp: new Date().toISOString(),
    });
  }

  /**
   * Track API call with monitoring
   */
  async trackApiCall<T>(
    url: string,
    method: string,
    fn: () => Promise<T>
  ): Promise<T> {
    if (!this.config.enablePerformanceMonitoring) {
      return fn();
    }

    return performanceMonitoring.trackApiCall(url, method, fn);
  }

  /**
   * Track error with context
   */
  trackError(error: Error, context?: Record<string, any>): void {
    if (!this.config.enableErrorTracking) return;

    sentryService.captureException(error, {
      tags: {
        session_duration: Date.now() - this.sessionStartTime,
        session_events: this.sessionEvents,
      },
      extra: context,
    });

    // Create alert for critical errors
    if (this.isCriticalError(error)) {
      this.createAlert({
        type: 'error',
        title: 'Critical Error',
        message: error.message,
        metadata: { error: error.stack, context },
      });
    }
  }

  /**
   * Create monitoring alert
   */
  private createAlert(alert: Omit<Alert, 'id' | 'timestamp'>): void {
    const fullAlert: Alert = {
      ...alert,
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString(),
    };

    this.alerts.push(fullAlert);
    
    // Keep only last 100 alerts
    if (this.alerts.length > 100) {
      this.alerts = this.alerts.slice(-100);
    }

    // Send alert to backend
    this.sendAlert(fullAlert);
    
    // Log alert
    logger.warn(`Alert: ${alert.title}`, alert);
  }

  /**
   * Get current alerts
   */
  getAlerts(type?: Alert['type']): Alert[] {
    if (type) {
      return this.alerts.filter(alert => alert.type === type);
    }
    return [...this.alerts];
  }

  /**
   * Clear alerts
   */
  clearAlerts(type?: Alert['type']): void {
    if (type) {
      this.alerts = this.alerts.filter(alert => alert.type !== type);
    } else {
      this.alerts = [];
    }
  }

  /**
   * Track app state change
   */
  private trackAppStateChange(appState: AppStateStatus): void {
    this.trackEvent('app_state_change', { state: appState });
    
    if (appState === 'background') {
      // Save session data
      this.saveSessionData();
    } else if (appState === 'active') {
      // Resume session
      this.resumeSession();
    }
  }

  /**
   * Track network change
   */
  private trackNetworkChange(state: any): void {
    this.trackEvent('network_change', {
      isConnected: state.isConnected,
      type: state.type,
      details: state.details,
    });

    if (!state.isConnected) {
      this.createAlert({
        type: 'warning',
        title: 'Network Disconnected',
        message: 'The device has lost network connectivity',
        metadata: { networkState: state },
      });
    }
  }

  /**
   * Send health metrics to backend
   */
  private async sendHealthMetrics(metrics: HealthMetrics): Promise<void> {
    try {
      // This would send to your monitoring backend
      logger.info('Health metrics', metrics);
    } catch (error) {
      logger.error('Failed to send health metrics', error as Error);
    }
  }

  /**
   * Send alert to backend
   */
  private async sendAlert(alert: Alert): Promise<void> {
    try {
      // This would send to your alerting backend
      logger.warn('Monitoring alert', alert);
    } catch (error) {
      logger.error('Failed to send alert', error as Error);
    }
  }

  /**
   * Helper methods
   */
  private shouldSample(): boolean {
    return Math.random() < this.config.sampleRate;
  }

  private isCriticalError(error: Error): boolean {
    // Define what constitutes a critical error
    const criticalPatterns = [
      /out of memory/i,
      /unhandled promise rejection/i,
      /maximum call stack/i,
      /network request failed/i,
      /unable to connect/i,
    ];

    return criticalPatterns.some(pattern => pattern.test(error.message));
  }

  private async getMemoryUsage(): Promise<number> {
    if (Platform.OS === 'ios') {
      const used = await DeviceInfo.getUsedMemory();
      const total = await DeviceInfo.getTotalMemory();
      return used / total;
    }
    return 0; // Android doesn't provide memory info easily
  }

  private async getDiskSpacePercentage(): Promise<number> {
    const free = await DeviceInfo.getFreeDiskStorage();
    const total = await DeviceInfo.getTotalDiskCapacity();
    return free / total;
  }

  private saveSessionData(): void {
    // Save session data for crash recovery
    const sessionData = {
      startTime: this.sessionStartTime,
      events: this.sessionEvents,
      alerts: this.alerts.length,
    };
    // Would save to AsyncStorage or similar
  }

  private resumeSession(): void {
    // Resume session tracking
    this.sessionEvents++;
  }

  /**
   * Cleanup
   */
  cleanup(): void {
    if (this.appStateSubscription) {
      this.appStateSubscription.remove();
    }
    if (this.netInfoSubscription) {
      this.netInfoSubscription();
    }
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
    }
  }
}

export const monitoringService = MonitoringService.getInstance();

// Export convenience functions
export const trackScreen = (screenName: string) => monitoringService.trackScreen(screenName);
export const trackEvent = (eventName: string, properties?: Record<string, any>) => 
  monitoringService.trackEvent(eventName, properties);
export const trackMetric = (name: string, value: number, unit?: any, tags?: Record<string, string>) =>
  monitoringService.trackMetric(name, value, unit, tags);
export const trackError = (error: Error, context?: Record<string, any>) =>
  monitoringService.trackError(error, context);
export const trackApiCall = <T>(url: string, method: string, fn: () => Promise<T>) =>
  monitoringService.trackApiCall(url, method, fn);