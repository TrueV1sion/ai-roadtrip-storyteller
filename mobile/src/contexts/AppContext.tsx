import React, { createContext, useContext, useEffect, useState, useRef } from 'react';
import { AppState, AppStateStatus } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { initConnectionManager, getConnectionStatus, ConnectionStatus } from '@/utils/connectionManager';
import { getStartupMetrics, initializeApp, completeStartup } from '@/utils/appStartupOptimizer';
import { initPerformanceMonitoring } from '@/utils/performance';
import { optimizedApiClient } from '@/services/api/OptimizedApiClient';
import { ImageCacheManager } from '@/utils/optimizedImage';

// Types
interface PerformanceMetrics {
  memoryUsage: number;
  batteryLevel?: number;
  startupTime: number;
  cacheStats: {
    apiCacheSize: number;
    imageCacheSize: number;
  };
}

interface AppContextType {
  isAppReady: boolean;
  isOfflineMode: boolean;
  connectionStatus: ConnectionStatus;
  performanceMetrics: PerformanceMetrics;
  clearImageCache: () => Promise<boolean>;
  clearApiCache: () => Promise<void>;
  toggleOfflineMode: () => void;
}

// Create context
const AppContext = createContext<AppContextType | undefined>(undefined);

// Initial performance metrics
const initialPerformanceMetrics: PerformanceMetrics = {
  memoryUsage: 0,
  startupTime: 0,
  cacheStats: {
    apiCacheSize: 0,
    imageCacheSize: 0,
  },
};

// Provider component
export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // State
  const [isAppReady, setIsAppReady] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>(getConnectionStatus());
  const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetrics>(initialPerformanceMetrics);
  
  // Refs
  const appState = useRef(AppState.currentState);
  const metricsIntervalRef = useRef<NodeJS.Timeout | null>(null);
  
  // Initialize app
  useEffect(() => {
    const setupApp = async () => {
      try {
        // Initialize utilities
        await initPerformanceMonitoring();
        await initConnectionManager();
        await initializeApp();
        
        // Initialize any other services here
        
        // Update connection status
        setConnectionStatus(getConnectionStatus());
        
        // Complete startup and mark app as ready
        await completeStartup();
        setIsAppReady(true);
        
        // Start metrics collection
        startMetricsCollection();
      } catch (error) {
        console.error('Error setting up app:', error);
        
        // Fall back to completing startup even with errors
        await completeStartup();
        setIsAppReady(true);
      }
    };
    
    setupApp();
    
    // Clean up on unmount
    return () => {
      if (metricsIntervalRef.current) {
        clearInterval(metricsIntervalRef.current);
      }
    };
  }, []);
  
  // App state change handler
  useEffect(() => {
    const subscription = AppState.addEventListener('change', handleAppStateChange);
    
    return () => {
      subscription.remove();
    };
  }, []);
  
  // Handle app state changes
  const handleAppStateChange = (nextAppState: AppStateStatus) => {
    // If app was in background and is now active
    if (appState.current.match(/inactive|background/) && nextAppState === 'active') {
      // Refresh connection status
      setConnectionStatus(getConnectionStatus());
      
      // Refresh metrics
      updatePerformanceMetrics();
    }
    
    appState.current = nextAppState;
  };
  
  // Start metrics collection
  const startMetricsCollection = () => {
    // Update metrics immediately
    updatePerformanceMetrics();
    
    // Schedule regular updates
    metricsIntervalRef.current = setInterval(() => {
      updatePerformanceMetrics();
    }, 30000); // 30 seconds
  };
  
  // Update performance metrics
  const updatePerformanceMetrics = async () => {
    try {
      // Get startup metrics
      const startupMetrics = getStartupMetrics();
      
      // Get API cache stats
      const apiCacheStats = optimizedApiClient.getCacheStats();
      
      // Get image cache stats
      const imageCacheInfo = ImageCacheManager.getCacheInfo();
      
      // Update metrics state
      setPerformanceMetrics({
        memoryUsage: 0, // Would need a native module to get actual memory usage
        startupTime: startupMetrics.startupDuration,
        cacheStats: {
          apiCacheSize: apiCacheStats.totalSizeBytes || 0,
          imageCacheSize: imageCacheInfo.totalSize || 0,
        },
      });
    } catch (error) {
      console.error('Error updating performance metrics:', error);
    }
  };
  
  // Clear image cache
  const clearImageCache = async (): Promise<boolean> => {
    try {
      const success = await ImageCacheManager.clearCache();
      
      // Update metrics after clearing
      updatePerformanceMetrics();
      
      return success;
    } catch (error) {
      console.error('Error clearing image cache:', error);
      return false;
    }
  };
  
  // Clear API cache
  const clearApiCache = async (): Promise<void> => {
    try {
      await optimizedApiClient.clearCache();
      
      // Update metrics after clearing
      updatePerformanceMetrics();
    } catch (error) {
      console.error('Error clearing API cache:', error);
    }
  };
  
  // Toggle offline mode
  const toggleOfflineMode = () => {
    import('@/utils/connectionManager').then(({ setOfflineMode, getConnectionStatus }) => {
      const status = getConnectionStatus();
      setOfflineMode(!status.isManualOfflineMode);
      setConnectionStatus(getConnectionStatus());
    });
  };
  
  // Context value
  const contextValue: AppContextType = {
    isAppReady,
    isOfflineMode: connectionStatus.isOffline,
    connectionStatus,
    performanceMetrics,
    clearImageCache,
    clearApiCache,
    toggleOfflineMode,
  };
  
  // Render
  return (
    <AppContext.Provider value={contextValue}>
      {children}
    </AppContext.Provider>
  );
};

// Custom hook for using the context
export const useApp = (): AppContextType => {
  const context = useContext(AppContext);
  
  if (context === undefined) {
    throw new Error('useApp must be used within an AppProvider');
  }
  
  return context;
};

export default AppContext;