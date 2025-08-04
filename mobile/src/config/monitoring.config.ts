/**
 * Monitoring Configuration
 * Centralized configuration for app monitoring and alerting
 */

export const MONITORING_CONFIG = {
  // Sentry Configuration
  sentry: {
    enabled: true,
    dsn: process.env.EXPO_PUBLIC_SENTRY_DSN,
    environment: process.env.EXPO_PUBLIC_ENVIRONMENT || 'development',
    debug: __DEV__,
    tracesSampleRate: __DEV__ ? 1.0 : 0.1, // 100% in dev, 10% in prod
    attachScreenshot: true,
    attachViewHierarchy: true,
  },

  // Performance Thresholds
  performance: {
    slowScreenLoadMs: 3000,
    slowApiCallMs: 3000,
    slowRenderMs: 16.67, // 60 FPS threshold
    maxMemoryUsagePercent: 80,
    minBatteryPercent: 20,
    minDiskSpacePercent: 10,
  },

  // Error Thresholds
  errors: {
    maxErrorRate: 0.05, // 5%
    minCrashFreeRate: 0.95, // 95%
    criticalErrorPatterns: [
      /out of memory/i,
      /unhandled promise rejection/i,
      /maximum call stack/i,
      /network request failed/i,
      /unable to connect/i,
      /authentication failed/i,
      /permission denied/i,
    ],
  },

  // Monitoring Features
  features: {
    enablePerformanceMonitoring: true,
    enableErrorTracking: true,
    enableNetworkMonitoring: true,
    enableDeviceMonitoring: true,
    enableCustomMetrics: true,
    enableScreenTracking: true,
    enableApiTracking: true,
    enableUserInteractionTracking: true,
  },

  // Sampling Rates (0.0 to 1.0)
  sampling: {
    events: __DEV__ ? 1.0 : 0.1,
    metrics: __DEV__ ? 1.0 : 0.05,
    customEvents: __DEV__ ? 1.0 : 0.01,
  },

  // Alert Configuration
  alerts: {
    enabled: true,
    channels: ['console', 'sentry'], // Add 'push', 'email' when configured
    cooldownMinutes: 15, // Don't repeat same alert for 15 minutes
    maxAlertsPerSession: 50,
  },

  // Metrics to Track
  metrics: {
    // Screen metrics
    screens: [
      'HomeScreen',
      'MapScreen',
      'NavigationScreen',
      'BookingScreen',
      'SettingsScreen',
    ],

    // API endpoints to monitor
    apis: [
      '/api/stories/generate',
      '/api/navigation/route',
      '/api/booking/search',
      '/api/voice/synthesize',
      '/api/auth/login',
    ],

    // Custom metrics
    custom: {
      app_startup_time: { unit: 'millisecond', threshold: 5000 },
      story_generation_time: { unit: 'millisecond', threshold: 10000 },
      map_load_time: { unit: 'millisecond', threshold: 2000 },
      voice_synthesis_time: { unit: 'millisecond', threshold: 3000 },
      booking_search_time: { unit: 'millisecond', threshold: 5000 },
    },
  },

  // Health Check Configuration
  healthCheck: {
    enabled: true,
    intervalMinutes: 5,
    endpoints: {
      backend: '/health',
      maps: '/api/proxy/maps/health',
      booking: '/api/proxy/booking/health',
    },
  },

  // Data Retention
  retention: {
    alertsDays: 7,
    metricsDays: 30,
    errorsDays: 90,
  },

  // Development Tools
  development: {
    showMonitoringDashboard: __DEV__,
    logToConsole: __DEV__,
    verboseLogging: false,
    mockErrors: false,
  },
};

// Alert Rules
export const ALERT_RULES = [
  {
    name: 'High Error Rate',
    condition: (metrics: any) => metrics.errorRate > MONITORING_CONFIG.errors.maxErrorRate,
    severity: 'error',
    message: (metrics: any) => `Error rate is ${(metrics.errorRate * 100).toFixed(1)}%`,
  },
  {
    name: 'Slow Screen Load',
    condition: (metrics: any) => metrics.screenLoadTime > MONITORING_CONFIG.performance.slowScreenLoadMs,
    severity: 'warning',
    message: (metrics: any) => `Screen load time is ${metrics.screenLoadTime}ms`,
  },
  {
    name: 'High Memory Usage',
    condition: (metrics: any) => metrics.memoryUsage > MONITORING_CONFIG.performance.maxMemoryUsagePercent,
    severity: 'warning',
    message: (metrics: any) => `Memory usage is ${metrics.memoryUsage}%`,
  },
  {
    name: 'Low Battery',
    condition: (metrics: any) => metrics.batteryLevel < MONITORING_CONFIG.performance.minBatteryPercent,
    severity: 'info',
    message: (metrics: any) => `Battery level is ${metrics.batteryLevel}%`,
  },
  {
    name: 'API Degradation',
    condition: (metrics: any) => metrics.apiLatency > MONITORING_CONFIG.performance.slowApiCallMs,
    severity: 'warning',
    message: (metrics: any) => `API latency is ${metrics.apiLatency}ms`,
  },
];

// Metric Definitions
export const METRIC_DEFINITIONS = {
  // Performance Metrics
  performance: {
    fps: {
      name: 'Frame Rate',
      unit: 'fps',
      goodThreshold: 60,
      warningThreshold: 30,
    },
    memory: {
      name: 'Memory Usage',
      unit: 'percent',
      goodThreshold: 50,
      warningThreshold: 80,
    },
    cpu: {
      name: 'CPU Usage',
      unit: 'percent',
      goodThreshold: 50,
      warningThreshold: 80,
    },
  },

  // Business Metrics
  business: {
    storyCompletionRate: {
      name: 'Story Completion Rate',
      unit: 'percent',
      goodThreshold: 80,
      warningThreshold: 60,
    },
    bookingConversionRate: {
      name: 'Booking Conversion Rate',
      unit: 'percent',
      goodThreshold: 10,
      warningThreshold: 5,
    },
    voiceRecognitionAccuracy: {
      name: 'Voice Recognition Accuracy',
      unit: 'percent',
      goodThreshold: 90,
      warningThreshold: 70,
    },
  },
};

// Export helper to check if monitoring is enabled
export const isMonitoringEnabled = (feature: keyof typeof MONITORING_CONFIG.features): boolean => {
  return MONITORING_CONFIG.features[feature] ?? false;
};

// Export helper to get sampling rate
export const getSamplingRate = (type: keyof typeof MONITORING_CONFIG.sampling): number => {
  return MONITORING_CONFIG.sampling[type] ?? 0.1;
};

// Export helper to check if metric should be tracked
export const shouldTrackMetric = (metricName: string): boolean => {
  return Math.random() < getSamplingRate('metrics');
};