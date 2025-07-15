/**
 * Performance optimization hooks for React Native
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { InteractionManager, Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

/**
 * Hook to defer heavy operations until after interactions
 */
export function useDeferredOperation<T>(
  operation: () => Promise<T>,
  dependencies: any[] = []
): {
  execute: () => Promise<T | null>;
  isExecuting: boolean;
  result: T | null;
  error: Error | null;
} {
  const [isExecuting, setIsExecuting] = useState(false);
  const [result, setResult] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);

  const execute = useCallback(async () => {
    setIsExecuting(true);
    setError(null);

    try {
      // Wait for interactions to complete
      await InteractionManager.runAfterInteractions(async () => {
        const res = await operation();
        setResult(res);
      });
      return result;
    } catch (err) {
      setError(err as Error);
      return null;
    } finally {
      setIsExecuting(false);
    }
  }, dependencies);

  return { execute, isExecuting, result, error };
}

/**
 * Hook for lazy loading with caching
 */
export function useLazyLoad<T>(
  loader: () => Promise<T>,
  cacheKey?: string,
  cacheDuration: number = 5 * 60 * 1000 // 5 minutes
): {
  data: T | null;
  loading: boolean;
  error: Error | null;
  load: () => Promise<void>;
  refresh: () => Promise<void>;
} {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const loadedRef = useRef(false);

  const loadFromCache = useCallback(async (): Promise<T | null> => {
    if (!cacheKey) return null;

    try {
      const cached = await AsyncStorage.getItem(cacheKey);
      if (cached) {
        const { data, timestamp } = JSON.parse(cached);
        if (Date.now() - timestamp < cacheDuration) {
          return data;
        }
      }
    } catch (err) {
      console.warn('Cache read error:', err);
    }
    return null;
  }, [cacheKey, cacheDuration]);

  const saveToCache = useCallback(async (data: T) => {
    if (!cacheKey) return;

    try {
      await AsyncStorage.setItem(cacheKey, JSON.stringify({
        data,
        timestamp: Date.now()
      }));
    } catch (err) {
      console.warn('Cache write error:', err);
    }
  }, [cacheKey]);

  const load = useCallback(async () => {
    if (loadedRef.current || loading) return;

    setLoading(true);
    setError(null);

    try {
      // Try cache first
      const cached = await loadFromCache();
      if (cached) {
        setData(cached);
        loadedRef.current = true;
        setLoading(false);
        return;
      }

      // Load fresh data
      const result = await loader();
      setData(result);
      loadedRef.current = true;
      
      // Save to cache
      await saveToCache(result);
    } catch (err) {
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, [loader, loading, loadFromCache, saveToCache]);

  const refresh = useCallback(async () => {
    loadedRef.current = false;
    if (cacheKey) {
      await AsyncStorage.removeItem(cacheKey);
    }
    await load();
  }, [cacheKey, load]);

  return { data, loading, error, load, refresh };
}

/**
 * Hook for performance monitoring
 */
export function usePerformanceMonitor(componentName: string) {
  const renderCount = useRef(0);
  const renderTime = useRef<number>(0);
  const mountTime = useRef<number>(Date.now());

  useEffect(() => {
    renderCount.current += 1;
    const startTime = Date.now();

    return () => {
      renderTime.current = Date.now() - startTime;
      
      // Log performance metrics in development
      if (__DEV__) {
        console.log(`[Performance] ${componentName}:`, {
          renderCount: renderCount.current,
          lastRenderTime: `${renderTime.current}ms`,
          totalMountTime: `${Date.now() - mountTime.current}ms`
        });
      }
    };
  });

  return {
    renderCount: renderCount.current,
    renderTime: renderTime.current,
    mountTime: Date.now() - mountTime.current
  };
}

/**
 * Hook for memory-efficient list rendering
 */
export function useVirtualizedList<T>(
  data: T[],
  itemHeight: number,
  containerHeight: number,
  overscan: number = 3
) {
  const [scrollOffset, setScrollOffset] = useState(0);

  const startIndex = Math.max(0, Math.floor(scrollOffset / itemHeight) - overscan);
  const endIndex = Math.min(
    data.length - 1,
    Math.ceil((scrollOffset + containerHeight) / itemHeight) + overscan
  );

  const visibleData = data.slice(startIndex, endIndex + 1);
  const totalHeight = data.length * itemHeight;
  const offsetY = startIndex * itemHeight;

  return {
    visibleData,
    totalHeight,
    offsetY,
    onScroll: (offset: number) => setScrollOffset(offset),
    startIndex,
    endIndex
  };
}

/**
 * Hook for debounced values
 */
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

/**
 * Hook for throttled callbacks
 */
export function useThrottle<T extends (...args: any[]) => any>(
  callback: T,
  delay: number
): T {
  const lastCall = useRef<number>(0);
  const timeout = useRef<NodeJS.Timeout | null>(null);

  return useCallback((...args: Parameters<T>) => {
    const now = Date.now();
    const timeSinceLastCall = now - lastCall.current;

    if (timeSinceLastCall >= delay) {
      lastCall.current = now;
      callback(...args);
    } else {
      if (timeout.current) {
        clearTimeout(timeout.current);
      }

      timeout.current = setTimeout(() => {
        lastCall.current = Date.now();
        callback(...args);
      }, delay - timeSinceLastCall);
    }
  }, [callback, delay]) as T;
}

/**
 * Hook for memory management
 */
export function useMemoryManagement() {
  const [memoryUsage, setMemoryUsage] = useState<{
    used: number;
    total: number;
    percentage: number;
  } | null>(null);

  useEffect(() => {
    const checkMemory = () => {
      if (Platform.OS === 'web' && 'memory' in performance) {
        const memory = (performance as any).memory;
        const usage = {
          used: memory.usedJSHeapSize,
          total: memory.totalJSHeapSize,
          percentage: (memory.usedJSHeapSize / memory.totalJSHeapSize) * 100
        };
        setMemoryUsage(usage);

        // Warn if memory usage is high
        if (usage.percentage > 90) {
          console.warn('High memory usage detected:', usage);
        }
      }
    };

    const interval = setInterval(checkMemory, 10000); // Check every 10 seconds
    checkMemory(); // Initial check

    return () => clearInterval(interval);
  }, []);

  return memoryUsage;
}

/**
 * Hook for batch operations
 */
export function useBatchOperation<T, R>(
  operation: (items: T[]) => Promise<R>,
  batchSize: number = 10,
  delay: number = 100
) {
  const queue = useRef<T[]>([]);
  const processing = useRef(false);
  const timeout = useRef<NodeJS.Timeout | null>(null);

  const processBatch = useCallback(async () => {
    if (processing.current || queue.current.length === 0) return;

    processing.current = true;
    const batch = queue.current.splice(0, batchSize);

    try {
      await operation(batch);
    } catch (error) {
      console.error('Batch operation error:', error);
      // Re-add failed items to queue
      queue.current.unshift(...batch);
    } finally {
      processing.current = false;

      // Process next batch if queue is not empty
      if (queue.current.length > 0) {
        timeout.current = setTimeout(processBatch, delay);
      }
    }
  }, [operation, batchSize, delay]);

  const add = useCallback((item: T) => {
    queue.current.push(item);

    if (!processing.current && !timeout.current) {
      timeout.current = setTimeout(processBatch, delay);
    }
  }, [processBatch, delay]);

  const flush = useCallback(async () => {
    if (timeout.current) {
      clearTimeout(timeout.current);
      timeout.current = null;
    }
    await processBatch();
  }, [processBatch]);

  useEffect(() => {
    return () => {
      if (timeout.current) {
        clearTimeout(timeout.current);
      }
    };
  }, []);

  return { add, flush, queueSize: queue.current.length };
}