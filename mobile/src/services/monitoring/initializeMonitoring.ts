/**
 * Monitoring Initialization Module
 * Sets up all monitoring services on app startup
 */

import { monitoringService } from './MonitoringService';
import { sentryService } from '../sentry/SentryService';
import { MONITORING_CONFIG } from '../../config/monitoring.config';
import { logger } from '../logger';
import { AppState, AppStateStatus, Platform } from 'react-native';
// import crashlytics from '@react-native-firebase/crashlytics'; // Uncomment when Firebase is set up

let isInitialized = false;

export const initializeMonitoring = async (): Promise<void> => {
  if (isInitialized) {
    logger.warn('Monitoring already initialized');
    return;
  }

  try {
    logger.info('Initializing monitoring services...');

    // 1. Initialize Sentry
    if (MONITORING_CONFIG.sentry.enabled && MONITORING_CONFIG.sentry.dsn) {
      await sentryService.initialize({
        dsn: MONITORING_CONFIG.sentry.dsn,
        environment: MONITORING_CONFIG.sentry.environment,
        debug: MONITORING_CONFIG.sentry.debug,
        tracesSampleRate: MONITORING_CONFIG.sentry.tracesSampleRate,
        attachScreenshot: MONITORING_CONFIG.sentry.attachScreenshot,
        attachViewHierarchy: MONITORING_CONFIG.sentry.attachViewHierarchy,
      });
      logger.info('Sentry initialized successfully');
    }

    // 2. Initialize Firebase Crashlytics (if available)
    // Uncomment when Firebase is set up
    // try {
    //   if (crashlytics) {
    //     await crashlytics().setCrashlyticsCollectionEnabled(!__DEV__);
    //     logger.info('Firebase Crashlytics initialized');
    //   }
    // } catch (error) {
    //   logger.warn('Firebase Crashlytics not available', error);
    // }

    // 3. Initialize main monitoring service
    await monitoringService.initialize({
      enablePerformanceMonitoring: MONITORING_CONFIG.features.enablePerformanceMonitoring,
      enableErrorTracking: MONITORING_CONFIG.features.enableErrorTracking,
      enableNetworkMonitoring: MONITORING_CONFIG.features.enableNetworkMonitoring,
      enableDeviceMonitoring: MONITORING_CONFIG.features.enableDeviceMonitoring,
      enableCustomMetrics: MONITORING_CONFIG.features.enableCustomMetrics,
      sampleRate: MONITORING_CONFIG.sampling.events,
    });

    // 4. Set up global error handlers
    setupGlobalErrorHandlers();

    // 5. Set up app state monitoring
    setupAppStateMonitoring();

    // 6. Track app launch
    trackAppLaunch();

    isInitialized = true;
    logger.info('Monitoring services initialized successfully');
  } catch (error) {
    logger.error('Failed to initialize monitoring', error as Error);
    // Don't throw - app should still work without monitoring
  }
};

/**
 * Set up global error handlers
 */
const setupGlobalErrorHandlers = () => {
  // React Native global error handler
  const originalHandler = ErrorUtils.getGlobalHandler();
  ErrorUtils.setGlobalHandler((error: Error, isFatal?: boolean) => {
    logger.error(`Global error handler: ${isFatal ? 'FATAL' : 'NON-FATAL'}`, error);
    
    // Track with monitoring service
    monitoringService.trackError(error, {
      fatal: isFatal,
      type: 'global_error_handler',
    });

    // Track with Sentry
    sentryService.captureException(error, {
      tags: { fatal: isFatal },
      level: isFatal ? 'fatal' : 'error',
    });

    // Track with Crashlytics
    // Uncomment when Firebase is set up
    // try {
    //   if (crashlytics && !__DEV__) {
    //     crashlytics().recordError(error);
    //     if (isFatal) {
    //       crashlytics().log('Fatal error occurred');
    //     }
    //   }
    // } catch (e) {
    //   // Ignore crashlytics errors
    // }

    // Call original handler
    if (originalHandler) {
      originalHandler(error, isFatal);
    }
  });

  // Promise rejection handler
  const handleUnhandledRejection = (reason: any, promise: Promise<any>) => {
    const error = new Error(`Unhandled Promise Rejection: ${reason}`);
    logger.error('Unhandled promise rejection', error);
    
    monitoringService.trackError(error, {
      type: 'unhandled_promise_rejection',
      reason: String(reason),
    });
  };

  // @ts-ignore - global promise rejection handler
  if (!global.onunhandledrejection) {
    global.onunhandledrejection = handleUnhandledRejection;
  }
};

/**
 * Set up app state monitoring
 */
const setupAppStateMonitoring = () => {
  let appStartTime = Date.now();
  let lastAppState: AppStateStatus = AppState.currentState;

  AppState.addEventListener('change', (nextAppState: AppStateStatus) => {
    const stateChangeTime = Date.now();
    
    // Track state transitions
    monitoringService.trackEvent('app_state_transition', {
      from: lastAppState,
      to: nextAppState,
      duration: stateChangeTime - appStartTime,
    });

    // Track background time
    if (lastAppState === 'background' && nextAppState === 'active') {
      const backgroundDuration = stateChangeTime - appStartTime;
      monitoringService.trackMetric('background_duration', backgroundDuration, 'millisecond');
    }

    // Track foreground time
    if (lastAppState === 'active' && nextAppState === 'background') {
      const foregroundDuration = stateChangeTime - appStartTime;
      monitoringService.trackMetric('foreground_duration', foregroundDuration, 'millisecond');
    }

    lastAppState = nextAppState;
    appStartTime = stateChangeTime;
  });
};

/**
 * Track app launch metrics
 */
const trackAppLaunch = () => {
  const launchTime = Date.now();
  
  // Track cold start (app was completely closed)
  monitoringService.trackEvent('app_launch', {
    type: 'cold_start',
    timestamp: launchTime,
  });

  // Set user context
  sentryService.setUserContext({
    id: 'anonymous', // Replace with actual user ID when available
  });

  // Set initial tags
  sentryService.setTags({
    app_version: MONITORING_CONFIG.sentry.environment,
    platform: Platform.OS,
  });

  // Add breadcrumb
  sentryService.addBreadcrumb({
    message: 'App launched',
    category: 'app',
    type: 'navigation',
    level: 'info',
    data: {
      launch_time: launchTime,
    },
  });
};

/**
 * Clean up monitoring services
 */
export const cleanupMonitoring = () => {
  if (!isInitialized) return;

  try {
    monitoringService.cleanup();
    isInitialized = false;
    logger.info('Monitoring services cleaned up');
  } catch (error) {
    logger.error('Error cleaning up monitoring', error as Error);
  }
};

/**
 * Configure monitoring for specific environment
 */
export const configureMonitoringForEnvironment = (environment: 'development' | 'staging' | 'production') => {
  switch (environment) {
    case 'development':
      // High sampling, verbose logging
      MONITORING_CONFIG.sampling.events = 1.0;
      MONITORING_CONFIG.sampling.metrics = 1.0;
      MONITORING_CONFIG.development.logToConsole = true;
      MONITORING_CONFIG.development.verboseLogging = true;
      break;
      
    case 'staging':
      // Medium sampling, normal logging
      MONITORING_CONFIG.sampling.events = 0.5;
      MONITORING_CONFIG.sampling.metrics = 0.2;
      MONITORING_CONFIG.development.logToConsole = false;
      MONITORING_CONFIG.development.verboseLogging = false;
      break;
      
    case 'production':
      // Low sampling, minimal logging
      MONITORING_CONFIG.sampling.events = 0.1;
      MONITORING_CONFIG.sampling.metrics = 0.05;
      MONITORING_CONFIG.development.logToConsole = false;
      MONITORING_CONFIG.development.verboseLogging = false;
      MONITORING_CONFIG.development.showMonitoringDashboard = false;
      break;
  }
  
  logger.info(`Monitoring configured for ${environment} environment`);
};