import NetInfo, { NetInfoState, NetInfoSubscription } from '@react-native-community/netinfo';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';
import { optimizedApiClient } from '@/services/api/OptimizedApiClient';

import { logger } from '@/services/logger';
// Constants
const CONNECTION_STATE_KEY = '@RoadTrip:connection_state';
const CONNECTION_SETTINGS_KEY = '@RoadTrip:connection_settings';
const DEFAULT_PING_INTERVAL = 30000; // 30 seconds
const MAX_OFFLINE_SCREEN_DELAY = 2000; // 2 seconds
const CONNECTION_CHECK_URLS = [
  'https://www.google.com',
  'https://www.cloudflare.com',
  'https://www.amazon.com'
];

// Types
interface ConnectionSettings {
  enableOfflineMode: boolean;
  autoEnableOfflineMode: boolean;
  mobileDataSaving: boolean;
  preloadOnWifi: boolean;
  offlineContentPrefetchEnabled: boolean;
  offlineContentMaxSizeMB: number;
  connectionCheckInterval: number;
  unreliableNetworkThreshold: number;
}

interface NetworkMetrics {
  lastCheckTime: number;
  connectionSuccessRate: number;
  avgLatency: number;
  latestLatencies: number[];
  lastConnectionType: string | null;
  unreliableConnectionCount: number;
  offlineModeActivations: number;
}

// Default settings
const defaultConnectionSettings: ConnectionSettings = {
  enableOfflineMode: true,
  autoEnableOfflineMode: true,
  mobileDataSaving: true,
  preloadOnWifi: true,
  offlineContentPrefetchEnabled: true,
  offlineContentMaxSizeMB: 200, // 200 MB
  connectionCheckInterval: DEFAULT_PING_INTERVAL,
  unreliableNetworkThreshold: 3,
};

// State
let isOffline = false;
let manualOfflineMode = false;
let currentConnectionType: string | null = null;
let currentConnectionQuality: 'unknown' | 'poor' | 'moderate' | 'good' = 'unknown';
let isConnected = true;
let isInternetReachable: boolean | null = true;
let unreliableConnectionCounter = 0;
let netInfoUnsubscribe: NetInfoSubscription | null = null;
let pingIntervalId: NodeJS.Timeout | null = null;
let connectionSettings: ConnectionSettings = { ...defaultConnectionSettings };
let networkMetrics: NetworkMetrics = {
  lastCheckTime: 0,
  connectionSuccessRate: 1,
  avgLatency: 0,
  latestLatencies: [],
  lastConnectionType: null,
  unreliableConnectionCount: 0,
  offlineModeActivations: 0,
};
let connectionStatusListeners: Array<(status: ConnectionStatus) => void> = [];

// Type for connection status
export interface ConnectionStatus {
  isOffline: boolean;
  isManualOfflineMode: boolean;
  connectionType: string | null;
  connectionQuality: 'unknown' | 'poor' | 'moderate' | 'good';
  isConnected: boolean;
  isInternetReachable: boolean | null;
  isUnreliableConnection: boolean;
}

// Initialize the connection manager
export async function initConnectionManager(): Promise<void> {
  try {
    // Load saved settings
    const savedSettingsStr = await AsyncStorage.getItem(CONNECTION_SETTINGS_KEY);
    if (savedSettingsStr) {
      connectionSettings = {
        ...defaultConnectionSettings,
        ...JSON.parse(savedSettingsStr),
      };
    }
    
    // Load saved state
    const savedStateStr = await AsyncStorage.getItem(CONNECTION_STATE_KEY);
    if (savedStateStr) {
      const savedState = JSON.parse(savedStateStr);
      manualOfflineMode = savedState.manualOfflineMode || false;
    }
    
    // Start monitoring network state
    startNetworkMonitoring();
    
    // Start connection checking
    if (connectionSettings.autoEnableOfflineMode) {
      startConnectionChecking();
    }
  } catch (error) {
    logger.error('Error initializing connection manager:', error);
  }
}

// Start monitoring network state
function startNetworkMonitoring(): void {
  // Unsubscribe if already subscribed
  if (netInfoUnsubscribe) {
    netInfoUnsubscribe();
  }
  
  // Subscribe to network changes
  netInfoUnsubscribe = NetInfo.addEventListener(state => {
    handleNetworkStateChange(state);
  });
  
  // Get initial state
  NetInfo.fetch().then(state => {
    handleNetworkStateChange(state);
  });
}

// Handle network state changes
function handleNetworkStateChange(state: NetInfoState): void {
  // Update state
  isConnected = !!state.isConnected;
  isInternetReachable = state.isInternetReachable;
  currentConnectionType = state.type;
  
  // Determine if we're offline
  const networkOffline = !isConnected || isInternetReachable === false;
  
  // Determine connection quality
  if (state.type === 'wifi') {
    currentConnectionQuality = 'good';
  } else if (state.type === 'cellular') {
    if (state.details && 'cellularGeneration' in state.details) {
      const generation = state.details.cellularGeneration;
      if (generation === '4g' || generation === '5g') {
        currentConnectionQuality = 'good';
      } else if (generation === '3g') {
        currentConnectionQuality = 'moderate';
      } else {
        currentConnectionQuality = 'poor';
      }
    } else {
      currentConnectionQuality = 'moderate';
    }
  } else if (state.type === 'ethernet' || state.type === 'vpn') {
    currentConnectionQuality = 'good';
  } else {
    currentConnectionQuality = 'unknown';
  }
  
  // Update API client
  if (optimizedApiClient) {
    // Update offline mode
    optimizedApiClient.setOfflineMode(networkOffline || manualOfflineMode);
    
    // Update low bandwidth mode
    if (connectionSettings.mobileDataSaving && state.type === 'cellular') {
      optimizedApiClient.setLowBandwidthMode(true);
    } else {
      optimizedApiClient.setLowBandwidthMode(false);
    }
    
    // Apply mobile data saving setting
    optimizedApiClient.setMobileDataSaving(connectionSettings.mobileDataSaving);
  }
  
  // Update offline status
  isOffline = networkOffline || manualOfflineMode;
  
  // Set offline mode if auto-enable is on and we're offline
  if (connectionSettings.autoEnableOfflineMode && networkOffline && !manualOfflineMode) {
    logger.debug('Auto-enabling offline mode due to network disconnection');
    manualOfflineMode = true;
    saveConnectionState();
    
    // Update metrics
    networkMetrics.offlineModeActivations++;
  }
  
  // Notify listeners
  notifyConnectionStatusListeners();
  
  // Save metrics
  networkMetrics.lastConnectionType = state.type;
}

// Start periodic connection checking
function startConnectionChecking(): void {
  // Clear existing interval
  if (pingIntervalId) {
    clearInterval(pingIntervalId);
  }
  
  // Start new interval
  pingIntervalId = setInterval(() => {
    checkConnection();
  }, connectionSettings.connectionCheckInterval);
  
  // Perform an immediate check
  checkConnection();
}

// Stop connection checking
function stopConnectionChecking(): void {
  if (pingIntervalId) {
    clearInterval(pingIntervalId);
    pingIntervalId = null;
  }
}

// Check connection by pinging servers
async function checkConnection(): Promise<boolean> {
  // Skip if already in manual offline mode
  if (manualOfflineMode) return false;
  
  // Skip if NetInfo already reports disconnected
  if (!isConnected) return false;
  
  // Update last check time
  networkMetrics.lastCheckTime = Date.now();
  
  try {
    // Try to ping multiple servers with a timeout
    let successCount = 0;
    const latencies: number[] = [];
    
    for (const url of CONNECTION_CHECK_URLS) {
      try {
        const startTime = Date.now();
        const response = await Promise.race([
          fetch(url, { method: 'HEAD', cache: 'no-cache' }),
          new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout')), 5000)),
        ]);
        
        const latency = Date.now() - startTime;
        
        if (response && response.ok) {
          successCount++;
          latencies.push(latency);
        }
      } catch (error) {
        // Ignore individual fetch errors
      }
    }
    
    // Calculate connection quality metrics
    const connectionSuccessRate = successCount / CONNECTION_CHECK_URLS.length;
    
    // Update metrics
    networkMetrics.connectionSuccessRate = connectionSuccessRate;
    
    if (latencies.length > 0) {
      const avgLatency = latencies.reduce((sum, val) => sum + val, 0) / latencies.length;
      networkMetrics.avgLatency = avgLatency;
      
      // Keep track of recent latencies (up to 10)
      networkMetrics.latestLatencies.push(avgLatency);
      if (networkMetrics.latestLatencies.length > 10) {
        networkMetrics.latestLatencies.shift();
      }
    }
    
    // Handle unreliable connection
    if (connectionSuccessRate < 0.5 || (latencies.length > 0 && networkMetrics.avgLatency > 2000)) {
      // Increment counter for unreliable connections
      unreliableConnectionCounter++;
      networkMetrics.unreliableConnectionCount++;
      
      // Auto enable offline mode if threshold reached
      if (connectionSettings.autoEnableOfflineMode && 
          unreliableConnectionCounter >= connectionSettings.unreliableNetworkThreshold) {
        logger.debug('Auto-enabling offline mode due to unreliable connection');
        setOfflineMode(true);
      }
      
      return false;
    } else {
      // Reset counter if connection is good
      unreliableConnectionCounter = 0;
      return true;
    }
  } catch (error) {
    logger.warn('Error checking connection:', error);
    
    // Increment counter for connection errors
    unreliableConnectionCounter++;
    networkMetrics.unreliableConnectionCount++;
    
    // Auto enable offline mode if threshold reached
    if (connectionSettings.autoEnableOfflineMode && 
        unreliableConnectionCounter >= connectionSettings.unreliableNetworkThreshold) {
      logger.debug('Auto-enabling offline mode due to connection errors');
      setOfflineMode(true);
    }
    
    return false;
  }
}

// Save connection state
async function saveConnectionState(): Promise<void> {
  try {
    await AsyncStorage.setItem(CONNECTION_STATE_KEY, JSON.stringify({
      manualOfflineMode,
    }));
  } catch (error) {
    logger.warn('Error saving connection state:', error);
  }
}

// Save connection settings
async function saveConnectionSettings(): Promise<void> {
  try {
    await AsyncStorage.setItem(CONNECTION_SETTINGS_KEY, JSON.stringify(connectionSettings));
  } catch (error) {
    logger.warn('Error saving connection settings:', error);
  }
}

// Get current connection status
export function getConnectionStatus(): ConnectionStatus {
  return {
    isOffline,
    isManualOfflineMode: manualOfflineMode,
    connectionType: currentConnectionType,
    connectionQuality: currentConnectionQuality,
    isConnected,
    isInternetReachable,
    isUnreliableConnection: unreliableConnectionCounter >= connectionSettings.unreliableNetworkThreshold,
  };
}

// Set offline mode
export function setOfflineMode(enabled: boolean): void {
  manualOfflineMode = enabled;
  isOffline = enabled || !isConnected || isInternetReachable === false;
  
  // Update API client
  if (optimizedApiClient) {
    optimizedApiClient.setOfflineMode(isOffline);
  }
  
  // Save state
  saveConnectionState();
  
  // Update metrics if enabling
  if (enabled) {
    networkMetrics.offlineModeActivations++;
  }
  
  // Notify listeners
  notifyConnectionStatusListeners();
  
  logger.debug(`Offline mode ${enabled ? 'enabled' : 'disabled'}`);
}

// Update connection settings
export function updateConnectionSettings(newSettings: Partial<ConnectionSettings>): void {
  connectionSettings = {
    ...connectionSettings,
    ...newSettings,
  };
  
  // Apply mobile data saving setting to API client
  if ('mobileDataSaving' in newSettings && optimizedApiClient) {
    optimizedApiClient.setMobileDataSaving(connectionSettings.mobileDataSaving);
  }
  
  // Update connection checking interval
  if ('connectionCheckInterval' in newSettings) {
    // Restart connection checking with new interval
    if (pingIntervalId) {
      stopConnectionChecking();
      startConnectionChecking();
    }
  }
  
  // Toggle connection checking based on auto enable setting
  if ('autoEnableOfflineMode' in newSettings) {
    if (connectionSettings.autoEnableOfflineMode && !pingIntervalId) {
      startConnectionChecking();
    } else if (!connectionSettings.autoEnableOfflineMode && pingIntervalId) {
      stopConnectionChecking();
    }
  }
  
  // Save settings
  saveConnectionSettings();
}

// Get connection settings
export function getConnectionSettings(): ConnectionSettings {
  return { ...connectionSettings };
}

// Get connection metrics
export function getConnectionMetrics(): NetworkMetrics {
  return { ...networkMetrics };
}

// Reset connection metrics
export function resetConnectionMetrics(): void {
  networkMetrics = {
    lastCheckTime: 0,
    connectionSuccessRate: 1,
    avgLatency: 0,
    latestLatencies: [],
    lastConnectionType: currentConnectionType,
    unreliableConnectionCount: 0,
    offlineModeActivations: 0,
  };
}

// Register a connection status listener
export function addConnectionStatusListener(
  listener: (status: ConnectionStatus) => void
): () => void {
  connectionStatusListeners.push(listener);
  
  // Return unsubscribe function
  return () => {
    connectionStatusListeners = connectionStatusListeners.filter(l => l !== listener);
  };
}

// Notify all connection status listeners
function notifyConnectionStatusListeners(): void {
  const status = getConnectionStatus();
  connectionStatusListeners.forEach(listener => {
    try {
      listener(status);
    } catch (error) {
      logger.error('Error in connection status listener:', error);
    }
  });
}

// Test connection and return status
export async function testConnection(): Promise<{
  success: boolean;
  latency: number;
  details: string;
}> {
  try {
    const startTime = Date.now();
    const response = await Promise.race([
      fetch('https://www.google.com', { method: 'HEAD', cache: 'no-cache' }),
      new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout')), 5000)),
    ]);
    
    const latency = Date.now() - startTime;
    
    if (response && response.ok) {
      return {
        success: true,
        latency,
        details: `Connected with ${latency}ms latency`,
      };
    } else {
      return {
        success: false,
        latency: -1,
        details: 'Connection test failed: server response not OK',
      };
    }
  } catch (error) {
    return {
      success: false,
      latency: -1,
      details: `Connection test failed: ${error instanceof Error ? error.message : 'unknown error'}`,
    };
  }
}

// Cleanup
export function cleanupConnectionManager(): void {
  // Unsubscribe from NetInfo
  if (netInfoUnsubscribe) {
    netInfoUnsubscribe();
    netInfoUnsubscribe = null;
  }
  
  // Stop connection checking
  if (pingIntervalId) {
    clearInterval(pingIntervalId);
    pingIntervalId = null;
  }
  
  // Clear listeners
  connectionStatusListeners = [];
}

// Reset to defaults (for testing)
export async function resetConnectionManager(): Promise<void> {
  try {
    await AsyncStorage.removeItem(CONNECTION_STATE_KEY);
    await AsyncStorage.removeItem(CONNECTION_SETTINGS_KEY);
    
    manualOfflineMode = false;
    connectionSettings = { ...defaultConnectionSettings };
    resetConnectionMetrics();
    
    // Update API client
    if (optimizedApiClient) {
      optimizedApiClient.setOfflineMode(false);
      optimizedApiClient.setLowBandwidthMode(false);
      optimizedApiClient.setMobileDataSaving(defaultConnectionSettings.mobileDataSaving);
    }
    
    // Restart monitoring
    startNetworkMonitoring();
    
    // Restart connection checking
    if (defaultConnectionSettings.autoEnableOfflineMode) {
      stopConnectionChecking();
      startConnectionChecking();
    } else {
      stopConnectionChecking();
    }
    
    // Notify listeners
    notifyConnectionStatusListeners();
    
    logger.debug('Connection manager reset to defaults');
  } catch (error) {
    logger.error('Error resetting connection manager:', error);
  }
}