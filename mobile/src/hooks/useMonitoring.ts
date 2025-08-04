/**
 * useMonitoring Hook
 * Simplifies monitoring integration in React components
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import { monitoringService, trackScreen, trackEvent, trackMetric, trackError } from '../services/monitoring/MonitoringService';

export interface UseMonitoringOptions {
  screenName?: string;
  trackFocus?: boolean;
  trackMount?: boolean;
  customMetrics?: Record<string, number>;
}

export const useMonitoring = (options: UseMonitoringOptions = {}) => {
  const navigation = useNavigation();
  const screenTracker = useRef<any>(null);
  const mountTime = useRef<number>(Date.now());

  // Get screen name from navigation if not provided
  const screenName = options.screenName || navigation.getId() || 'Unknown';

  // Track screen mount
  useEffect(() => {
    if (options.trackMount !== false) {
      screenTracker.current = trackScreen(screenName);
      screenTracker.current.start();

      // Track mount time
      trackMetric(`${screenName}_mount_time`, Date.now() - mountTime.current, 'millisecond');
    }

    return () => {
      if (screenTracker.current) {
        screenTracker.current.end();
      }
    };
  }, [screenName, options.trackMount]);

  // Track screen focus
  useFocusEffect(
    useCallback(() => {
      if (options.trackFocus) {
        trackEvent('screen_focus', { screen: screenName });
      }

      return () => {
        if (options.trackFocus) {
          trackEvent('screen_blur', { screen: screenName });
        }
      };
    }, [screenName, options.trackFocus])
  );

  // Track custom metrics on mount
  useEffect(() => {
    if (options.customMetrics) {
      Object.entries(options.customMetrics).forEach(([name, value]) => {
        trackMetric(name, value);
      });
    }
  }, [options.customMetrics]);

  // Mark screen as loaded
  const markLoaded = useCallback(() => {
    if (screenTracker.current) {
      screenTracker.current.loaded();
    }
  }, []);

  // Track custom event
  const logEvent = useCallback((eventName: string, properties?: Record<string, any>) => {
    trackEvent(`${screenName}_${eventName}`, {
      screen: screenName,
      ...properties,
    });
  }, [screenName]);

  // Track custom metric
  const logMetric = useCallback((
    metricName: string,
    value: number,
    unit?: 'millisecond' | 'second' | 'byte' | 'percent' | 'none'
  ) => {
    trackMetric(`${screenName}_${metricName}`, value, unit, { screen: screenName });
  }, [screenName]);

  // Track error with screen context
  const logError = useCallback((error: Error, context?: Record<string, any>) => {
    trackError(error, {
      screen: screenName,
      ...context,
    });
  }, [screenName]);

  // Track API call with monitoring
  const trackApi = useCallback(async <T,>(
    url: string,
    method: string,
    fn: () => Promise<T>
  ): Promise<T> => {
    return monitoringService.trackApiCall(url, method, async () => {
      try {
        const result = await fn();
        logEvent('api_success', { url, method });
        return result;
      } catch (error) {
        logEvent('api_error', { url, method, error: (error as Error).message });
        throw error;
      }
    });
  }, [logEvent]);

  // Track user interaction
  const trackInteraction = useCallback((
    interactionType: string,
    target: string,
    metadata?: Record<string, any>
  ) => {
    logEvent('user_interaction', {
      type: interactionType,
      target,
      ...metadata,
    });
  }, [logEvent]);

  // Track performance timing
  const trackTiming = useCallback((
    timingName: string,
    startTime: number,
    metadata?: Record<string, any>
  ) => {
    const duration = Date.now() - startTime;
    logMetric(timingName, duration, 'millisecond');
    logEvent('timing', {
      name: timingName,
      duration,
      ...metadata,
    });
  }, [logEvent, logMetric]);

  return {
    // Core functions
    markLoaded,
    logEvent,
    logMetric,
    logError,
    trackApi,
    
    // Convenience functions
    trackInteraction,
    trackTiming,
    
    // Direct access to monitoring service
    monitoringService,
  };
};

// Hook for tracking component render performance
export const useRenderTracking = (componentName: string) => {
  const renderCount = useRef(0);
  const lastRenderTime = useRef(Date.now());

  useEffect(() => {
    renderCount.current++;
    const timeSinceLastRender = Date.now() - lastRenderTime.current;
    lastRenderTime.current = Date.now();

    // Track render metrics
    trackMetric(`${componentName}_render_count`, renderCount.current, 'none');
    
    if (renderCount.current > 1) {
      trackMetric(`${componentName}_render_interval`, timeSinceLastRender, 'millisecond');
    }

    // Warn about excessive re-renders
    if (renderCount.current > 10) {
      trackEvent('excessive_renders', {
        component: componentName,
        count: renderCount.current,
      });
    }
  });

  return renderCount.current;
};

// Hook for tracking async operation performance
export const useAsyncTracking = <T,>(
  operationName: string,
  asyncFn: () => Promise<T>
): [() => Promise<T>, boolean, Error | null] => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const trackedFn = useCallback(async () => {
    const startTime = Date.now();
    setLoading(true);
    setError(null);

    try {
      trackEvent(`${operationName}_start`);
      const result = await asyncFn();
      
      const duration = Date.now() - startTime;
      trackMetric(`${operationName}_duration`, duration, 'millisecond');
      trackEvent(`${operationName}_success`, { duration });
      
      return result;
    } catch (err) {
      const duration = Date.now() - startTime;
      const error = err as Error;
      
      setError(error);
      trackError(error, {
        operation: operationName,
        duration,
      });
      trackEvent(`${operationName}_error`, {
        error: error.message,
        duration,
      });
      
      throw error;
    } finally {
      setLoading(false);
    }
  }, [operationName, asyncFn]);

  return [trackedFn, loading, error];
};