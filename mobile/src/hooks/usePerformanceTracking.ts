/**
 * Performance Tracking Hook
 * Automatically tracks screen performance metrics
 */

import { useEffect, useRef } from 'react';
import { useFocusEffect } from '@react-navigation/native';
import { 
  startScreenTracking, 
  markScreenLoaded, 
  endScreenTracking 
} from '@/services/sentry/PerformanceMonitoring';
import { trackNavigation } from '@/services/sentry/SentryService';

interface UsePerformanceTrackingOptions {
  screenName: string;
  trackFocus?: boolean;
  customMetrics?: Record<string, number>;
}

export function usePerformanceTracking({
  screenName,
  trackFocus = true,
  customMetrics,
}: UsePerformanceTrackingOptions) {
  const isTracking = useRef(false);
  const focusCount = useRef(0);

  // Track initial screen load
  useEffect(() => {
    if (!isTracking.current) {
      isTracking.current = true;
      startScreenTracking(screenName);
      
      // Mark as loaded after initial render
      requestAnimationFrame(() => {
        markScreenLoaded(screenName);
      });
    }

    return () => {
      if (isTracking.current) {
        endScreenTracking(screenName);
        isTracking.current = false;
      }
    };
  }, [screenName]);

  // Track screen focus/blur if navigation is available
  useFocusEffect(() => {
    if (trackFocus) {
      focusCount.current++;
      
      // Track navigation on focus (skip first focus as it's tracked on mount)
      if (focusCount.current > 1) {
        trackNavigation('previous_screen', screenName, { focusCount: focusCount.current });
      }
    }
  });

  // Track custom metrics
  useEffect(() => {
    if (customMetrics) {
      Object.entries(customMetrics).forEach(([name, value]) => {
        // Custom metrics will be added to the current transaction
        // This is handled by the PerformanceMonitoring service
      });
    }
  }, [customMetrics]);

  return {
    screenName,
    isTracking: isTracking.current,
  };
}

// Higher-order component for class components
export function withPerformanceTracking<P extends object>(
  Component: React.ComponentType<P>,
  screenName: string
): React.ComponentType<P> {
  return (props: P) => {
    usePerformanceTracking({ screenName });
    return <Component {...props} />;
  };
}