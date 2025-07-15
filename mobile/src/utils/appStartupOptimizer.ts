import { Platform, AppState, Appearance, Dimensions } from 'react-native';
import * as FileSystem from 'expo-file-system';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SplashScreen from 'expo-splash-screen';
import NetInfo from '@react-native-community/netinfo';
import { recordAppStartupTime } from './performance';
import { setOfflineMode } from './connectionManager';
import { ImageCacheManager } from './optimizedImage';
import { optimizedApiClient } from '@/services/api/OptimizedApiClient';

// Constants
const STARTUP_TIMESTAMP_KEY = '@RoadTrip:startup_timestamp';
const PRELOAD_ASSETS_KEY = '@RoadTrip:preload_assets';
const STARTUP_CONFIG_KEY = '@RoadTrip:startup_config';
const DEFAULT_RESOURCE_TIMEOUT = 5000; // 5 seconds
const MAX_CONCURRENT_RESOURCES = 3;
const COLD_START_THRESHOLD = 60 * 1000; // 60 seconds

// Types
interface AssetPreloadConfig {
  images: string[];
  apis: string[];
  fonts: { [key: string]: string };
  preloadAll: boolean;
  coldStartOnly: boolean;
  initialDataPrefetched: boolean;
}

interface StartupConfig {
  splashMinimumTime: number;
  concurrentResourceLoading: number;
  preloadInBackground: boolean;
  preloadTimeout: number;
  enableOptimizations: boolean;
  aggressiveRamCleanup: boolean;
  prioritizeBootstrap: boolean;
}

// Default configurations
const defaultAssetPreloadConfig: AssetPreloadConfig = {
  images: [],
  apis: [],
  fonts: {},
  preloadAll: false,
  coldStartOnly: true,
  initialDataPrefetched: false,
};

const defaultStartupConfig: StartupConfig = {
  splashMinimumTime: 1000, // Min time to show splash screen
  concurrentResourceLoading: MAX_CONCURRENT_RESOURCES,
  preloadInBackground: true,
  preloadTimeout: DEFAULT_RESOURCE_TIMEOUT,
  enableOptimizations: true,
  aggressiveRamCleanup: Platform.OS === 'android',
  prioritizeBootstrap: true,
};

// Startup state
let startupTimestamp = Date.now();
let isAppStarted = false;
let startupPhase = 'initializing';
let preloadConfig: AssetPreloadConfig = { ...defaultAssetPreloadConfig };
let startupConfig: StartupConfig = { ...defaultStartupConfig };
let isColdStart = true;
let totalInitAssets = 0;
let loadedInitAssets = 0;

// Check if this is a cold start
async function checkColdStart(): Promise<boolean> {
  try {
    const lastStartupStr = await AsyncStorage.getItem(STARTUP_TIMESTAMP_KEY);
    if (!lastStartupStr) return true;
    
    const lastStartup = parseInt(lastStartupStr, 10);
    isColdStart = Date.now() - lastStartup > COLD_START_THRESHOLD;
    
    // Save current startup timestamp
    await AsyncStorage.setItem(STARTUP_TIMESTAMP_KEY, Date.now().toString());
    
    return isColdStart;
  } catch (error) {
    console.warn('Error checking cold start:', error);
    return true;
  }
}

// Load preload configurations
async function loadConfigurations(): Promise<void> {
  try {
    // Load asset preload config
    const preloadConfigStr = await AsyncStorage.getItem(PRELOAD_ASSETS_KEY);
    if (preloadConfigStr) {
      preloadConfig = {
        ...defaultAssetPreloadConfig,
        ...JSON.parse(preloadConfigStr),
      };
    }
    
    // Load startup config
    const startupConfigStr = await AsyncStorage.getItem(STARTUP_CONFIG_KEY);
    if (startupConfigStr) {
      startupConfig = {
        ...defaultStartupConfig,
        ...JSON.parse(startupConfigStr),
      };
    }
  } catch (error) {
    console.warn('Error loading startup configurations:', error);
  }
}

// Save updated configurations
export async function updatePreloadAssets(newConfig: Partial<AssetPreloadConfig>): Promise<void> {
  try {
    preloadConfig = {
      ...preloadConfig,
      ...newConfig,
    };
    
    await AsyncStorage.setItem(PRELOAD_ASSETS_KEY, JSON.stringify(preloadConfig));
  } catch (error) {
    console.error('Failed to update preload assets config:', error);
  }
}

// Save startup configurations
export async function updateStartupConfig(newConfig: Partial<StartupConfig>): Promise<void> {
  try {
    startupConfig = {
      ...startupConfig,
      ...newConfig,
    };
    
    await AsyncStorage.setItem(STARTUP_CONFIG_KEY, JSON.stringify(startupConfig));
  } catch (error) {
    console.error('Failed to update startup config:', error);
  }
}

// Clean up temporary files and caches
async function performStartupCleanup(): Promise<void> {
  try {
    startupPhase = 'cleanup';
    
    if (startupConfig.aggressiveRamCleanup) {
      // Empty the JS engine's garbage collector
      if (global.gc) {
        global.gc();
      }
      
      // Clean up temporary files
      const cacheDir = FileSystem.cacheDirectory;
      if (cacheDir) {
        const tempFiles = await FileSystem.readDirectoryAsync(cacheDir);
        const oldTempFiles = tempFiles.filter(file => 
          file.startsWith('temp_') || file.includes('_temp_')
        );
        
        // Delete old temporary files (in parallel)
        await Promise.all(
          oldTempFiles.map(file => 
            FileSystem.deleteAsync(`${cacheDir}${file}`, { idempotent: true })
          )
        );
      }
    }
  } catch (error) {
    console.warn('Error during startup cleanup:', error);
  }
}

// Preload critical assets
async function preloadCriticalAssets(): Promise<void> {
  try {
    startupPhase = 'preloading';
    
    // Skip if not a cold start and configured for cold start only
    if (!isColdStart && preloadConfig.coldStartOnly) {
      return;
    }
    
    // Skip if already prefetched
    if (preloadConfig.initialDataPrefetched) {
      return;
    }
    
    // Check network status
    const netInfo = await NetInfo.fetch();
    if (!netInfo.isConnected) {
      setOfflineMode(true);
      return;
    }
    
    // Preload critical API data
    const apis = preloadConfig.apis;
    if (apis.length > 0) {
      // Only load a subset for faster startup
      const criticalApis = preloadConfig.preloadAll ? apis : apis.slice(0, 2);
      
      // Set longer timeout for API requests
      const apiTimeout = startupConfig.preloadTimeout * 2;
      
      // Preload APIs sequentially to avoid overwhelming the network
      for (const apiEndpoint of criticalApis) {
        try {
          await Promise.race([
            optimizedApiClient.prefetch(apiEndpoint),
            new Promise((_, reject) => setTimeout(() => reject(new Error('API Timeout')), apiTimeout))
          ]);
        } catch (error) {
          console.warn(`Error preloading API ${apiEndpoint}:`, error);
        }
      }
    }
  } catch (error) {
    console.warn('Error preloading critical assets:', error);
  }
}

// Preload remaining assets in the background
async function preloadRemainingAssetsInBackground(): Promise<void> {
  // Only run if preloading in background is enabled
  if (!startupConfig.preloadInBackground) return;
  
  try {
    // Skip if not a cold start and configured for cold start only
    if (!isColdStart && preloadConfig.coldStartOnly) {
      return;
    }
    
    // Check if connected to the internet
    const netInfo = await NetInfo.fetch();
    if (!netInfo.isConnected) {
      return;
    }
    
    // Wait a bit to allow the app to become interactive first
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Process images in batches for better performance
    const images = preloadConfig.images;
    if (images.length > 0) {
      const imagesToLoad = preloadConfig.preloadAll ? images : images.slice(0, 5);
      
      // Load images in parallel batches
      for (let i = 0; i < imagesToLoad.length; i += startupConfig.concurrentResourceLoading) {
        const batch = imagesToLoad.slice(i, i + startupConfig.concurrentResourceLoading);
        
        await Promise.all(
          batch.map(imageUri => 
            ImageCacheManager.prefetchImage(imageUri)
              .catch(error => console.warn(`Error prefetching image ${imageUri}:`, error))
          )
        );
        
        // Pause briefly between batches
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    }
    
    // Preload remaining APIs
    const apis = preloadConfig.apis;
    if (apis.length > 0) {
      const remainingApis = preloadConfig.preloadAll ? apis : apis.slice(2);
      
      // Load APIs in parallel batches
      for (let i = 0; i < remainingApis.length; i += startupConfig.concurrentResourceLoading) {
        const batch = remainingApis.slice(i, i + startupConfig.concurrentResourceLoading);
        
        await Promise.all(
          batch.map(apiEndpoint => 
            optimizedApiClient.prefetch(apiEndpoint)
              .catch(error => console.warn(`Error preloading API ${apiEndpoint}:`, error))
          )
        );
        
        // Pause briefly between batches
        await new Promise(resolve => setTimeout(resolve, 200));
      }
    }
    
    // Mark initial data as prefetched
    preloadConfig.initialDataPrefetched = true;
    await updatePreloadAssets(preloadConfig);
    
  } catch (error) {
    console.warn('Error preloading assets in background:', error);
  }
}

// Initialize the app
export async function initializeApp(): Promise<void> {
  // Start measuring startup time
  startupTimestamp = Date.now();
  isAppStarted = false;
  
  // Keep splash screen visible
  try {
    await SplashScreen.preventAutoHideAsync();
  } catch (error) {
    console.warn('Error preventing splash screen auto hide:', error);
  }
  
  // Check if this is a cold start
  isColdStart = await checkColdStart();
  
  // Load configurations
  await loadConfigurations();
  
  // Perform startup cleanup
  await performStartupCleanup();
  
  // Preload critical assets
  if (startupConfig.prioritizeBootstrap) {
    await preloadCriticalAssets();
  }
}

// Hide splash screen and complete startup
export async function completeStartup(): Promise<void> {
  // Minimum time to show splash screen
  const elapsedTime = Date.now() - startupTimestamp;
  const remainingTime = Math.max(0, startupConfig.splashMinimumTime - elapsedTime);
  
  if (remainingTime > 0) {
    await new Promise(resolve => setTimeout(resolve, remainingTime));
  }
  
  try {
    // Hide splash screen
    await SplashScreen.hideAsync();
    
    // Record startup time
    const totalStartupTime = Date.now() - startupTimestamp;
    recordAppStartupTime(totalStartupTime);
    
    // Mark app as started
    isAppStarted = true;
    startupPhase = 'completed';
    
    // Start background preloading
    if (!startupConfig.prioritizeBootstrap) {
      preloadCriticalAssets().then(() => {
        preloadRemainingAssetsInBackground();
      });
    } else {
      preloadRemainingAssetsInBackground();
    }
    
    console.log(`App startup completed in ${totalStartupTime}ms (${isColdStart ? 'cold' : 'warm'} start)`);
  } catch (error) {
    console.error('Error completing startup:', error);
  }
}

// Add an asset to preload list
export function addAssetToPreload(assetUri: string, type: 'image' | 'api' = 'image'): void {
  if (type === 'image' && !preloadConfig.images.includes(assetUri)) {
    preloadConfig.images.push(assetUri);
    updatePreloadAssets(preloadConfig);
  } else if (type === 'api' && !preloadConfig.apis.includes(assetUri)) {
    preloadConfig.apis.push(assetUri);
    updatePreloadAssets(preloadConfig);
  }
}

// Get startup metrics
export function getStartupMetrics(): Record<string, any> {
  const currentTime = Date.now();
  return {
    startupDuration: isAppStarted ? (currentTime - startupTimestamp) : -1,
    isColdStart,
    startupPhase,
    initialAssetsLoaded: loadedInitAssets,
    totalInitialAssets: totalInitAssets,
    initialAssetsProgress: totalInitAssets > 0 ? loadedInitAssets / totalInitAssets : 0,
    preloadedImagesCount: preloadConfig.images.length,
    preloadedApisCount: preloadConfig.apis.length,
  };
}

// Reset startup optimization (for testing)
export async function resetStartupOptimization(): Promise<void> {
  try {
    await AsyncStorage.removeItem(STARTUP_TIMESTAMP_KEY);
    await AsyncStorage.removeItem(PRELOAD_ASSETS_KEY);
    await AsyncStorage.removeItem(STARTUP_CONFIG_KEY);
    
    preloadConfig = { ...defaultAssetPreloadConfig };
    startupConfig = { ...defaultStartupConfig };
    
    console.log('Startup optimization reset');
  } catch (error) {
    console.error('Failed to reset startup optimization:', error);
  }
}

// Export default config for reference
export const defaultConfig = {
  assetPreload: defaultAssetPreloadConfig,
  startup: defaultStartupConfig,
};