import { Platform, InteractionManager } from 'react-native';
import { PerformanceObserver } from 'perf_hooks'; // This is supported in React Native
import AsyncStorage from '@react-native-async-storage/async-storage';

// Constants for performance entries
const PERFORMANCE_METRICS_KEY = '@RoadTrip:performance_metrics';
const METRIC_THRESHOLD_KEY = '@RoadTrip:metric_thresholds';
const MAX_METRICS_STORED = 100;

// Default thresholds for key performance metrics (in milliseconds)
const DEFAULT_THRESHOLDS = {
  renderTime: 16.67, // 60fps frame (16.67ms)
  apiResponseTime: 1000, // 1 second
  imageLoadTime: 200, // 200ms
  jsExecutionTime: 50, // 50ms
  navigationTransitionTime: 500, // 500ms
  memoryWarningThreshold: 150, // MB
};

// Types for performance metrics
type PerformanceMetricType = 
  | 'render' 
  | 'api' 
  | 'image' 
  | 'jsExecution' 
  | 'navigation' 
  | 'startup'
  | 'memory';

interface PerformanceMetric {
  type: PerformanceMetricType;
  component?: string;
  duration: number;
  timestamp: number;
  metadata?: Record<string, any>;
}

interface PerformanceInfo {
  metrics: PerformanceMetric[];
  deviceInfo: {
    platform: string;
    version: string;
    model?: string;
    memory?: number;
  };
}

// The global performance data store
let performanceData: PerformanceInfo = {
  metrics: [],
  deviceInfo: {
    platform: Platform.OS,
    version: Platform.Version.toString(),
  }
};

// In-memory reference to thresholds
let metricThresholds = { ...DEFAULT_THRESHOLDS };

/**
 * Initializes the performance monitoring system.
 * Loads saved metrics and thresholds from storage.
 */
export async function initPerformanceMonitoring(): Promise<void> {
  try {
    // Load previously saved metrics
    const savedMetrics = await AsyncStorage.getItem(PERFORMANCE_METRICS_KEY);
    if (savedMetrics) {
      performanceData = JSON.parse(savedMetrics);
    }

    // Load custom thresholds if available
    const savedThresholds = await AsyncStorage.getItem(METRIC_THRESHOLD_KEY);
    if (savedThresholds) {
      metricThresholds = { ...DEFAULT_THRESHOLDS, ...JSON.parse(savedThresholds) };
    }

    // Set up performance observer if available
    if (typeof PerformanceObserver !== 'undefined') {
      const observer = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        entries.forEach(entry => {
          // Process performance entry
          recordPerformanceEntry(entry);
        });
      });
      
      // Observe different performance entry types
      observer.observe({ entryTypes: ['measure', 'resource', 'longtask'] });
    }

    console.log('Performance monitoring initialized');
  } catch (error) {
    console.error('Failed to initialize performance monitoring:', error);
  }
}

/**
 * Records a performance entry from the PerformanceObserver
 */
function recordPerformanceEntry(entry: any): void {
  // Map performance entry types to our metric types
  let type: PerformanceMetricType | undefined;
  
  switch (entry.entryType) {
    case 'measure':
      if (entry.name.startsWith('render_')) {
        type = 'render';
      } else if (entry.name.startsWith('js_')) {
        type = 'jsExecution';
      } else if (entry.name.startsWith('navigation_')) {
        type = 'navigation';
      }
      break;
    case 'resource':
      if (entry.name.includes('/api/')) {
        type = 'api';
      } else if (/\.(jpg|jpeg|png|gif|webp)$/.test(entry.name)) {
        type = 'image';
      }
      break;
    case 'longtask':
      type = 'jsExecution';
      break;
  }

  if (type) {
    recordMetric(type, entry.duration, {
      name: entry.name,
      startTime: entry.startTime,
    });
  }
}

/**
 * Records a performance metric.
 * 
 * @param type Type of metric being recorded
 * @param duration Duration in milliseconds
 * @param metadata Optional additional data about the metric
 */
export function recordMetric(
  type: PerformanceMetricType, 
  duration: number, 
  metadata?: Record<string, any>,
  component?: string
): void {
  // Create the metric object
  const metric: PerformanceMetric = {
    type,
    duration,
    timestamp: Date.now(),
    metadata,
    component,
  };

  // Add to in-memory store
  performanceData.metrics.push(metric);
  
  // Limit the number of metrics stored
  if (performanceData.metrics.length > MAX_METRICS_STORED) {
    performanceData.metrics = performanceData.metrics.slice(-MAX_METRICS_STORED);
  }

  // Check if this metric exceeds threshold
  const threshold = getThresholdForMetricType(type);
  if (threshold && duration > threshold) {
    console.warn(`Performance threshold exceeded: ${type} took ${duration}ms (threshold: ${threshold}ms)`, metadata);
    
    // Send to analytics in the background
    InteractionManager.runAfterInteractions(() => {
      reportPerformanceIssue(metric);
    });
  }

  // Save metrics periodically (we don't want to save on every metric to avoid performance overhead)
  if (performanceData.metrics.length % 10 === 0) {
    saveMetrics();
  }
}

/**
 * Gets the threshold for a specific metric type
 */
function getThresholdForMetricType(type: PerformanceMetricType): number | undefined {
  switch (type) {
    case 'render':
      return metricThresholds.renderTime;
    case 'api':
      return metricThresholds.apiResponseTime;
    case 'image':
      return metricThresholds.imageLoadTime;
    case 'jsExecution':
      return metricThresholds.jsExecutionTime;
    case 'navigation':
      return metricThresholds.navigationTransitionTime;
    default:
      return undefined;
  }
}

/**
 * Saves metrics to AsyncStorage
 */
export async function saveMetrics(): Promise<void> {
  try {
    await AsyncStorage.setItem(PERFORMANCE_METRICS_KEY, JSON.stringify(performanceData));
  } catch (error) {
    console.error('Failed to save performance metrics:', error);
  }
}

/**
 * Reports a performance issue to analytics or monitoring system
 */
function reportPerformanceIssue(metric: PerformanceMetric): void {
  // This would integrate with your analytics or error reporting system
  // For now, we'll just log it
  console.warn('Performance issue detected:', metric);
}

/**
 * Clears all stored performance metrics
 */
export async function clearMetrics(): Promise<void> {
  performanceData.metrics = [];
  try {
    await AsyncStorage.removeItem(PERFORMANCE_METRICS_KEY);
  } catch (error) {
    console.error('Failed to clear performance metrics:', error);
  }
}

/**
 * Updates the thresholds for performance metrics
 */
export async function updateThresholds(newThresholds: Partial<typeof DEFAULT_THRESHOLDS>): Promise<void> {
  metricThresholds = { ...metricThresholds, ...newThresholds };
  try {
    await AsyncStorage.setItem(METRIC_THRESHOLD_KEY, JSON.stringify(metricThresholds));
  } catch (error) {
    console.error('Failed to update metric thresholds:', error);
  }
}

/**
 * Gets all recorded performance metrics
 */
export function getMetrics(): PerformanceMetric[] {
  return [...performanceData.metrics];
}

/**
 * Gets performance summary statistics
 */
export function getPerformanceSummary(): Record<string, any> {
  const metrics = performanceData.metrics;
  const summary: Record<string, any> = {
    totalMetrics: metrics.length,
    averages: {},
    max: {},
    min: {},
    p95: {}, // 95th percentile
  };

  // Group metrics by type
  const groupedMetrics: Record<string, number[]> = {};
  
  metrics.forEach(metric => {
    if (!groupedMetrics[metric.type]) {
      groupedMetrics[metric.type] = [];
    }
    groupedMetrics[metric.type].push(metric.duration);
  });

  // Calculate statistics for each type
  Object.entries(groupedMetrics).forEach(([type, durations]) => {
    durations.sort((a, b) => a - b);
    
    const sum = durations.reduce((total, val) => total + val, 0);
    const avg = sum / durations.length;
    const min = durations[0];
    const max = durations[durations.length - 1];
    const p95Index = Math.floor(durations.length * 0.95);
    const p95 = durations[p95Index];

    summary.averages[type] = avg;
    summary.max[type] = max;
    summary.min[type] = min;
    summary.p95[type] = p95;
  });

  return summary;
}

/**
 * Performance measurement utility that can be used as a decorator or directly
 */
export function measurePerformance(
  type: PerformanceMetricType,
  componentOrName?: string | Function,
  methodName?: string | PropertyDescriptor,
  descriptor?: PropertyDescriptor
): Function | void {
  // If called as a decorator for a class method
  if (typeof componentOrName === 'object' || typeof methodName === 'object') {
    const targetDescriptor = (methodName as PropertyDescriptor) || descriptor;
    const originalMethod = targetDescriptor.value;
    const componentName = typeof componentOrName === 'function' 
      ? componentOrName.name 
      : 'UnknownComponent';

    targetDescriptor.value = function(...args: any[]) {
      const start = performance.now();
      const result = originalMethod.apply(this, args);
      
      // Handle promises
      if (result && typeof result.then === 'function') {
        return result.then((value: any) => {
          const end = performance.now();
          recordMetric(type, end - start, { args }, componentName);
          return value;
        });
      }
      
      const end = performance.now();
      recordMetric(type, end - start, { args }, componentName);
      return result;
    };
    
    return;
  }
  
  // If called as a function
  return (target: any, name?: string, descriptor?: PropertyDescriptor) => {
    if (descriptor && descriptor.value) {
      const originalMethod = descriptor.value;
      const componentName = typeof componentOrName === 'string' 
        ? componentOrName 
        : (typeof target === 'function' ? target.name : 'UnknownComponent');

      descriptor.value = function(...args: any[]) {
        const start = performance.now();
        const result = originalMethod.apply(this, args);
        
        // Handle promises
        if (result && typeof result.then === 'function') {
          return result.then((value: any) => {
            const end = performance.now();
            recordMetric(type, end - start, { args }, componentName);
            return value;
          });
        }
        
        const end = performance.now();
        recordMetric(type, end - start, { args }, componentName);
        return result;
      };
    }
    return descriptor;
  };
}

/**
 * Utility to measure a block of code execution time
 */
export class Stopwatch {
  private startTime: number;
  private type: PerformanceMetricType;
  private component?: string;
  private metadata?: Record<string, any>;

  constructor(type: PerformanceMetricType, component?: string, metadata?: Record<string, any>) {
    this.startTime = performance.now();
    this.type = type;
    this.component = component;
    this.metadata = metadata;
  }

  stop(): number {
    const duration = performance.now() - this.startTime;
    recordMetric(this.type, duration, this.metadata, this.component);
    return duration;
  }
}

/**
 * Measures render performance using React component lifecycle methods
 */
export function measureRenderPerformance(Component: React.ComponentType<any>): React.ComponentType<any> {
  const componentName = Component.displayName || Component.name;
  
  return class PerformanceWrapper extends React.Component<any> {
    private renderStart: number = 0;
    
    static displayName = `PerformanceMonitor(${componentName})`;
    
    UNSAFE_componentWillMount() {
      this.renderStart = performance.now();
    }
    
    componentDidMount() {
      const renderTime = performance.now() - this.renderStart;
      recordMetric('render', renderTime, {}, componentName);
    }
    
    componentDidUpdate() {
      const updateTime = performance.now() - this.renderStart;
      recordMetric('render', updateTime, { isUpdate: true }, componentName);
    }
    
    UNSAFE_componentWillUpdate() {
      this.renderStart = performance.now();
    }
    
    render() {
      return <Component {...this.props} />;
    }
  };
}

/**
 * Record API call performance
 */
export function recordApiPerformance(
  endpoint: string, 
  method: string, 
  duration: number,
  status?: number,
  dataSize?: number
): void {
  recordMetric('api', duration, {
    endpoint,
    method,
    status,
    dataSize
  });
}

/**
 * Record image loading performance
 */
export function recordImageLoadPerformance(
  imageUri: string,
  duration: number,
  width?: number,
  height?: number
): void {
  recordMetric('image', duration, {
    uri: imageUri,
    dimensions: width && height ? `${width}x${height}` : undefined
  });
}

/**
 * Record application startup time
 */
export function recordAppStartupTime(duration: number): void {
  recordMetric('startup', duration, {
    coldStart: true,
    timestamp: Date.now()
  });
}

/**
 * Record memory usage
 */
export function recordMemoryUsage(memoryUsageMB: number): void {
  recordMetric('memory', memoryUsageMB, {
    unit: 'MB',
    timestamp: Date.now()
  });
  
  // Check for memory warnings
  if (memoryUsageMB > metricThresholds.memoryWarningThreshold) {
    console.warn(`High memory usage detected: ${memoryUsageMB}MB`);
  }
}