/**
 * Fixes for failing mobile component tests
 */

import React, { useEffect, useRef } from 'react';
import { Animated, Platform, InteractionManager } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import NetInfo from '@react-native-community/netinfo';

import { logger } from '@/services/logger';
/**
 * Fix for confetti animation performance on older devices
 */
export const OptimizedConfettiAnimation: React.FC<{ trigger: boolean }> = ({ trigger }) => {
  const animationRef = useRef<Animated.CompositeAnimation | null>(null);
  
  useEffect(() => {
    if (trigger) {
      // Use InteractionManager to defer animation on older devices
      InteractionManager.runAfterInteractions(() => {
        // Check device performance capability
        const isLowEndDevice = Platform.OS === 'android' && Platform.Version < 28;
        
        if (isLowEndDevice) {
          // Simplified animation for older devices
          const simpleAnimation = Animated.timing(new Animated.Value(0), {
            toValue: 1,
            duration: 1000,
            useNativeDriver: true, // Always use native driver for performance
          });
          
          animationRef.current = simpleAnimation;
          simpleAnimation.start();
        } else {
          // Full confetti animation for capable devices
          const particles = Array.from({ length: 30 }, (_, i) => ({
            x: new Animated.Value(0),
            y: new Animated.Value(0),
            opacity: new Animated.Value(1),
          }));
          
          const animations = particles.map((particle) =>
            Animated.parallel([
              Animated.timing(particle.x, {
                toValue: (Math.random() - 0.5) * 300,
                duration: 2000,
                useNativeDriver: true,
              }),
              Animated.timing(particle.y, {
                toValue: 400,
                duration: 2000,
                useNativeDriver: true,
              }),
              Animated.timing(particle.opacity, {
                toValue: 0,
                duration: 2000,
                delay: 1000,
                useNativeDriver: true,
              }),
            ])
          );
          
          const compositeAnimation = Animated.parallel(animations);
          animationRef.current = compositeAnimation;
          compositeAnimation.start();
        }
      });
    }
    
    return () => {
      // Clean up animation on unmount
      if (animationRef.current) {
        animationRef.current.stop();
      }
    };
  }, [trigger]);
  
  // Return optimized confetti component
  return null; // Implementation would render actual confetti particles
};

/**
 * Fix for voice command integration mock
 */
export const MockVoiceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Properly configured mock for voice commands
  const mockVoiceCommands = {
    start: jest.fn(() => Promise.resolve()),
    stop: jest.fn(() => Promise.resolve()),
    cancel: jest.fn(() => Promise.resolve()),
    isRecognizing: jest.fn(() => Promise.resolve(false)),
    isAvailable: jest.fn(() => Promise.resolve(true)),
  };
  
  return (
    <VoiceContext.Provider value={mockVoiceCommands}>
      {children}
    </VoiceContext.Provider>
  );
};

/**
 * Fix for offline state handling with cache implementation
 */
export class OfflineCacheManager {
  private static instance: OfflineCacheManager;
  private cache: Map<string, any> = new Map();
  
  static getInstance(): OfflineCacheManager {
    if (!OfflineCacheManager.instance) {
      OfflineCacheManager.instance = new OfflineCacheManager();
    }
    return OfflineCacheManager.instance;
  }
  
  async initialize() {
    // Load cached data from AsyncStorage
    try {
      const keys = await AsyncStorage.getAllKeys();
      const cacheKeys = keys.filter(key => key.startsWith('cache_'));
      const values = await AsyncStorage.multiGet(cacheKeys);
      
      values.forEach(([key, value]) => {
        if (value) {
          try {
            this.cache.set(key, JSON.parse(value));
          } catch (e) {
            logger.error(`Failed to parse cache key ${key}:`, e);
          }
        }
      });
    } catch (error) {
      logger.error('Failed to initialize cache:', error);
    }
  }
  
  async get(key: string): Promise<any> {
    // Check memory cache first
    if (this.cache.has(`cache_${key}`)) {
      return this.cache.get(`cache_${key}`);
    }
    
    // Check AsyncStorage
    try {
      const value = await AsyncStorage.getItem(`cache_${key}`);
      if (value) {
        const parsed = JSON.parse(value);
        this.cache.set(`cache_${key}`, parsed);
        return parsed;
      }
    } catch (error) {
      logger.error(`Failed to get cache key ${key}:`, error);
    }
    
    return null;
  }
  
  async set(key: string, value: any, ttl?: number): Promise<void> {
    const cacheKey = `cache_${key}`;
    const cacheEntry = {
      value,
      timestamp: Date.now(),
      ttl: ttl || 3600000, // Default 1 hour
    };
    
    // Store in memory
    this.cache.set(cacheKey, cacheEntry);
    
    // Store in AsyncStorage
    try {
      await AsyncStorage.setItem(cacheKey, JSON.stringify(cacheEntry));
    } catch (error) {
      logger.error(`Failed to set cache key ${key}:`, error);
    }
  }
  
  async isExpired(key: string): Promise<boolean> {
    const entry = await this.get(key);
    if (!entry) return true;
    
    const now = Date.now();
    return now - entry.timestamp > entry.ttl;
  }
  
  async clear(): Promise<void> {
    // Clear memory cache
    this.cache.clear();
    
    // Clear AsyncStorage cache
    try {
      const keys = await AsyncStorage.getAllKeys();
      const cacheKeys = keys.filter(key => key.startsWith('cache_'));
      await AsyncStorage.multiRemove(cacheKeys);
    } catch (error) {
      logger.error('Failed to clear cache:', error);
    }
  }
}

/**
 * Hook for handling offline state with cache
 */
export const useOfflineCache = (key: string, fetcher: () => Promise<any>) => {
  const [data, setData] = React.useState<any>(null);
  const [loading, setLoading] = React.useState(true);
  const [isOffline, setIsOffline] = React.useState(false);
  const cacheManager = OfflineCacheManager.getInstance();
  
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      
      // Check network state
      const netInfo = await NetInfo.fetch();
      setIsOffline(!netInfo.isConnected);
      
      if (!netInfo.isConnected) {
        // Offline - try to load from cache
        const cachedData = await cacheManager.get(key);
        if (cachedData && !(await cacheManager.isExpired(key))) {
          setData(cachedData.value);
          setLoading(false);
          return;
        }
      }
      
      try {
        // Online - fetch fresh data
        const freshData = await fetcher();
        setData(freshData);
        
        // Cache the data
        await cacheManager.set(key, freshData);
      } catch (error) {
        logger.error('Failed to fetch data:', error);
        
        // Fall back to cache even if expired
        const cachedData = await cacheManager.get(key);
        if (cachedData) {
          setData(cachedData.value);
        }
      } finally {
        setLoading(false);
      }
    };
    
    loadData();
    
    // Set up network state listener
    const unsubscribe = NetInfo.addEventListener(state => {
      setIsOffline(!state.isConnected);
      if (state.isConnected) {
        loadData(); // Refresh when coming online
      }
    });
    
    return () => {
      unsubscribe();
    };
  }, [key]);
  
  return { data, loading, isOffline };
};

/**
 * Performance monitoring wrapper for components
 */
export const withPerformanceMonitoring = <P extends object>(
  Component: React.ComponentType<P>,
  componentName: string
) => {
  return React.forwardRef<any, P>((props, ref) => {
    const renderStartTime = useRef(Date.now());
    
    useEffect(() => {
      const renderEndTime = Date.now();
      const renderDuration = renderEndTime - renderStartTime.current;
      
      // Log performance metrics
      logger.debug(`${componentName} render time: ${renderDuration}ms`);
      
      // Report to analytics if render is slow
      if (renderDuration > 100) {
        logger.warn(`Slow render detected for ${componentName}: ${renderDuration}ms`);
      }
    });
    
    return <Component {...props} ref={ref} />;
  });
};

// Create context for voice commands
const VoiceContext = React.createContext<any>(null);

// Export fixes
export const MobileComponentFixes = {
  OptimizedConfettiAnimation,
  MockVoiceProvider,
  OfflineCacheManager,
  useOfflineCache,
  withPerformanceMonitoring,
};