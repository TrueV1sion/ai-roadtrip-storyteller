import AsyncStorage from '@react-native-async-storage/async-storage';
import * as FileSystem from 'expo-file-system';
import NetInfo, { NetInfoState } from '@react-native-community/netinfo';
import * as SQLite from 'expo-sqlite';
import { ToastAndroid, Platform, Alert, AppState, AppStateStatus } from 'react-native';
import { Location, Route, Region } from '../types/location';
import { API_BASE_URL } from '../config';

// Define offline storage paths
const OFFLINE_ROOT_DIR = `${FileSystem.documentDirectory}offline/`;
const OFFLINE_MAPS_DIR = `${OFFLINE_ROOT_DIR}maps/`;
const OFFLINE_CONTENT_DIR = `${OFFLINE_ROOT_DIR}content/`;
const OFFLINE_AUDIO_DIR = `${OFFLINE_ROOT_DIR}audio/`;
const OFFLINE_IMAGES_DIR = `${OFFLINE_ROOT_DIR}images/`;
const OFFLINE_DB_NAME = 'offline.db';

// Define offline cache formats
interface RegionCache {
  region: Region;
  timeStamp: number;
  expiryDate: number; // Unix timestamp in milliseconds
  sizeBytes: number;
  tileCount: number;
  isComplete: boolean;
}

interface OfflineRoute {
  id: string;
  route: Route;
  originName: string;
  destinationName: string;
  timeStamp: number;
  expiryDate: number;
  sizeBytes: number;
}

interface OfflineContent {
  id: string;
  type: 'story' | 'trivia' | 'collectible';
  location: Location;
  content: any;
  timeStamp: number;
  expiryDate: number;
}

interface StorageStats {
  totalStorageUsed: number;
  maps: {
    count: number;
    sizeBytes: number;
  };
  routes: {
    count: number;
    sizeBytes: number;
  };
  content: {
    count: number;
    sizeBytes: number;
  };
  audio: {
    count: number;
    sizeBytes: number;
  };
  maxStorage: number;
  percentUsed: number;
}

interface SyncQueueItem {
  id: string;
  type: 'story_update' | 'user_preference' | 'analytics_event' | 'booking_data';
  data: any;
  priority: number; // 1-5, where 1 is highest priority
  attempts: number;
  maxAttempts: number;
  nextRetryTime: number;
  createdAt: number;
}

interface NetworkState {
  isConnected: boolean;
  connectionType: string;
  isInternetReachable: boolean | null;
  canSync: boolean;
}

interface OfflineCapabilities {
  canNavigate: boolean;
  canPlayStoredContent: boolean;
  canUseVoiceCommands: boolean;
  canShowMaps: boolean;
  estimatedOfflineTime: number; // in minutes
}

class OfflineManager {
  private isInitialized: boolean = false;
  private db: SQLite.WebSQLDatabase | null = null;
  private static instance: OfflineManager;
  private maxStorageBytes: number = 500 * 1024 * 1024; // 500MB default
  private networkState: NetworkState = {
    isConnected: false,
    connectionType: 'unknown',
    isInternetReachable: null,
    canSync: false
  };
  private syncQueue: SyncQueueItem[] = [];
  private syncInProgress: boolean = false;
  private networkUnsubscribe: (() => void) | null = null;
  private appStateUnsubscribe: (() => void) | null = null;
  private syncTimer: NodeJS.Timeout | null = null;
  private lastSyncAttempt: number = 0;
  private syncRetryDelay: number = 30000; // 30 seconds
  private maxSyncRetryDelay: number = 300000; // 5 minutes

  // Singleton pattern
  static getInstance(): OfflineManager {
    if (!OfflineManager.instance) {
      OfflineManager.instance = new OfflineManager();
    }
    return OfflineManager.instance;
  }

  private constructor() {}

  /**
   * Initialize the offline manager
   */
  async initialize(): Promise<void> {
    if (this.isInitialized) return;

    try {
      // Create necessary directories
      await this.ensureDirectoryExists(OFFLINE_ROOT_DIR);
      await this.ensureDirectoryExists(OFFLINE_MAPS_DIR);
      await this.ensureDirectoryExists(OFFLINE_CONTENT_DIR);
      await this.ensureDirectoryExists(OFFLINE_AUDIO_DIR);
      await this.ensureDirectoryExists(OFFLINE_IMAGES_DIR);

      // Open database
      this.db = SQLite.openDatabase(OFFLINE_DB_NAME);

      // Initialize database tables
      await this.initDatabase();

      // Load user preferences
      const maxStorageStr = await AsyncStorage.getItem('offline_max_storage');
      if (maxStorageStr) {
        this.maxStorageBytes = parseInt(maxStorageStr, 10);
      }

      // Initialize network monitoring
      await this.initNetworkMonitoring();

      // Load sync queue from storage
      await this.loadSyncQueue();

      // Clean expired content
      await this.cleanExpiredContent();

      // Start sync processing
      this.startSyncProcessor();

      // Listen for app state changes
      this.appStateUnsubscribe = AppState.addEventListener(
        'change',
        this.handleAppStateChange.bind(this)
      );

      this.isInitialized = true;
      console.log('OfflineManager initialized successfully');
    } catch (error) {
      console.error('Failed to initialize OfflineManager:', error);
      this.showNotification('Failed to initialize offline storage');
      throw error;
    }
  }

  /**
   * Initialize network monitoring
   */
  private async initNetworkMonitoring(): Promise<void> {
    // Get initial network state
    const netInfo = await NetInfo.fetch();
    this.updateNetworkState(netInfo);

    // Subscribe to network state changes
    this.networkUnsubscribe = NetInfo.addEventListener((state) => {
      this.updateNetworkState(state);
    });
  }

  /**
   * Update network state and trigger sync if connected
   */
  private updateNetworkState(netInfo: NetInfoState): void {
    const wasConnected = this.networkState.isConnected;
    
    this.networkState = {
      isConnected: netInfo.isConnected ?? false,
      connectionType: netInfo.type,
      isInternetReachable: netInfo.isInternetReachable,
      canSync: (netInfo.isConnected ?? false) && 
               (netInfo.isInternetReachable ?? false) &&
               (netInfo.type !== 'cellular' || this.shouldSyncOnCellular())
    };

    console.log('Network state updated:', this.networkState);

    // If we just came back online, attempt to sync
    if (!wasConnected && this.networkState.canSync && this.syncQueue.length > 0) {
      console.log('Network reconnected, triggering sync');
      this.processSyncQueue();
    }
  }

  /**
   * Check if we should sync on cellular connection
   */
  private async shouldSyncOnCellular(): Promise<boolean> {
    try {
      const setting = await AsyncStorage.getItem('sync_on_cellular');
      return setting === 'true';
    } catch {
      return false; // Default to Wi-Fi only
    }
  }

  /**
   * Handle app state changes
   */
  private handleAppStateChange(nextAppState: AppStateStatus): void {
    if (nextAppState === 'active' && this.networkState.canSync) {
      // App became active and we have connectivity, try to sync
      this.processSyncQueue();
    } else if (nextAppState === 'background') {
      // App went to background, save sync queue
      this.saveSyncQueue();
    }
  }

  /**
   * Start the sync processor timer
   */
  private startSyncProcessor(): void {
    if (this.syncTimer) {
      clearInterval(this.syncTimer);
    }

    this.syncTimer = setInterval(() => {
      if (this.networkState.canSync && this.syncQueue.length > 0) {
        this.processSyncQueue();
      }
    }, this.syncRetryDelay);
  }

  /**
   * Clean up resources
   */
  async cleanup(): Promise<void> {
    if (this.networkUnsubscribe) {
      this.networkUnsubscribe();
      this.networkUnsubscribe = null;
    }

    if (this.appStateUnsubscribe) {
      this.appStateUnsubscribe();
      this.appStateUnsubscribe = null;
    }

    if (this.syncTimer) {
      clearInterval(this.syncTimer);
      this.syncTimer = null;
    }

    await this.saveSyncQueue();
    this.isInitialized = false;
  }

  /**
   * Add item to sync queue
   */
  async addToSyncQueue(
    type: SyncQueueItem['type'],
    data: any,
    priority: number = 3,
    maxAttempts: number = 3
  ): Promise<void> {
    const item: SyncQueueItem = {
      id: `${type}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      type,
      data,
      priority,
      attempts: 0,
      maxAttempts,
      nextRetryTime: Date.now(),
      createdAt: Date.now()
    };

    this.syncQueue.push(item);
    await this.saveSyncQueue();

    // If we're online, try to sync immediately
    if (this.networkState.canSync) {
      this.processSyncQueue();
    }
  }

  /**
   * Process the sync queue
   */
  private async processSyncQueue(): Promise<void> {
    if (this.syncInProgress || !this.networkState.canSync || this.syncQueue.length === 0) {
      return;
    }

    this.syncInProgress = true;
    const now = Date.now();

    try {
      // Sort by priority (1 = highest) and creation time
      this.syncQueue.sort((a, b) => {
        if (a.priority !== b.priority) {
          return a.priority - b.priority;
        }
        return a.createdAt - b.createdAt;
      });

      // Process items that are ready for retry
      const itemsToProcess = this.syncQueue.filter(
        item => item.nextRetryTime <= now && item.attempts < item.maxAttempts
      );

      for (const item of itemsToProcess) {
        try {
          await this.syncItem(item);
          
          // Success - remove from queue
          this.syncQueue = this.syncQueue.filter(queueItem => queueItem.id !== item.id);
          console.log(`Successfully synced item ${item.id}`);
        } catch (error) {
          console.error(`Failed to sync item ${item.id}:`, error);
          
          // Increment attempts and calculate next retry time
          item.attempts++;
          if (item.attempts >= item.maxAttempts) {
            console.warn(`Max attempts reached for item ${item.id}, removing from queue`);
            this.syncQueue = this.syncQueue.filter(queueItem => queueItem.id !== item.id);
          } else {
            // Exponential backoff
            const backoffDelay = Math.min(
              this.syncRetryDelay * Math.pow(2, item.attempts - 1),
              this.maxSyncRetryDelay
            );
            item.nextRetryTime = now + backoffDelay;
          }
        }
      }

      await this.saveSyncQueue();
    } finally {
      this.syncInProgress = false;
      this.lastSyncAttempt = now;
    }
  }

  /**
   * Sync a single item
   */
  private async syncItem(item: SyncQueueItem): Promise<void> {
    const timeout = 10000; // 10 second timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      let endpoint = '';
      let method = 'POST';

      switch (item.type) {
        case 'story_update':
          endpoint = '/api/stories/sync';
          break;
        case 'user_preference':
          endpoint = '/api/user/preferences';
          method = 'PUT';
          break;
        case 'analytics_event':
          endpoint = '/api/analytics/events';
          break;
        case 'booking_data':
          endpoint = '/api/bookings/sync';
          break;
        default:
          throw new Error(`Unknown sync item type: ${item.type}`);
      }

      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(item.data),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      console.log(`Successfully synced ${item.type} item`);
    } finally {
      clearTimeout(timeoutId);
    }
  }

  /**
   * Load sync queue from storage
   */
  private async loadSyncQueue(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        this.syncQueue = [];
        resolve();
        return;
      }

      this.db.transaction(tx => {
        tx.executeSql(
          'SELECT * FROM sync_queue ORDER BY priority ASC, created_at ASC',
          [],
          (_, result) => {
            this.syncQueue = [];
            for (let i = 0; i < result.rows.length; i++) {
              const row = result.rows.item(i);
              this.syncQueue.push({
                id: row.id,
                type: row.type,
                data: JSON.parse(row.data),
                priority: row.priority,
                attempts: row.attempts,
                maxAttempts: row.max_attempts,
                nextRetryTime: row.next_retry_time,
                createdAt: row.created_at
              });
            }
            console.log(`Loaded ${this.syncQueue.length} items from sync queue`);
            resolve();
          },
          (_, error) => {
            console.error('Failed to load sync queue:', error);
            this.syncQueue = [];
            resolve(); // Don't reject, just start with empty queue
            return false;
          }
        );
      });
    });
  }

  /**
   * Save sync queue to storage
   */
  private async saveSyncQueue(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        resolve();
        return;
      }

      this.db.transaction(tx => {
        // Clear existing queue
        tx.executeSql('DELETE FROM sync_queue');

        // Insert current queue items
        this.syncQueue.forEach(item => {
          tx.executeSql(
            `INSERT INTO sync_queue 
             (id, type, data, priority, attempts, max_attempts, next_retry_time, created_at) 
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
            [
              item.id,
              item.type,
              JSON.stringify(item.data),
              item.priority,
              item.attempts,
              item.maxAttempts,
              item.nextRetryTime,
              item.createdAt
            ]
          );
        });
      }, 
      (error) => {
        console.error('Failed to save sync queue:', error);
        resolve(); // Don't fail the whole operation
      },
      () => {
        resolve();
      });
    });
  }

  /**
   * Get current network state
   */
  getNetworkState(): NetworkState {
    return { ...this.networkState };
  }

  /**
   * Get offline capabilities assessment
   */
  async getOfflineCapabilities(): Promise<OfflineCapabilities> {
    await this.initialize();

    const regions = await this.getDownloadedRegions();
    const routes = await this.getDownloadedRoutes();
    const stats = await this.getStorageStats();

    // Estimate how much offline content we have
    const hasMapData = regions.length > 0;
    const hasRouteData = routes.length > 0;
    const hasStoredContent = stats.content.count > 0 || stats.audio.count > 0;

    // Estimate offline time based on available content
    let estimatedOfflineTime = 0;
    if (hasMapData && hasRouteData) {
      estimatedOfflineTime += 120; // 2 hours for navigation
    }
    if (hasStoredContent) {
      estimatedOfflineTime += stats.audio.count * 5; // 5 minutes per audio item
    }

    return {
      canNavigate: hasMapData && hasRouteData,
      canPlayStoredContent: hasStoredContent,
      canUseVoiceCommands: true, // Voice commands work offline
      canShowMaps: hasMapData,
      estimatedOfflineTime
    };
  }

  /**
   * Get sync queue status
   */
  getSyncQueueStatus(): {
    totalItems: number;
    pendingItems: number;
    failedItems: number;
    lastSyncAttempt: number;
    canSync: boolean;
  } {
    const now = Date.now();
    const pendingItems = this.syncQueue.filter(item => 
      item.attempts < item.maxAttempts && item.nextRetryTime <= now
    ).length;
    const failedItems = this.syncQueue.filter(item => 
      item.attempts >= item.maxAttempts
    ).length;

    return {
      totalItems: this.syncQueue.length,
      pendingItems,
      failedItems,
      lastSyncAttempt: this.lastSyncAttempt,
      canSync: this.networkState.canSync
    };
  }

  /**
   * Clear failed sync items
   */
  async clearFailedSyncItems(): Promise<void> {
    this.syncQueue = this.syncQueue.filter(item => item.attempts < item.maxAttempts);
    await this.saveSyncQueue();
  }

  /**
   * Force sync now (if connected)
   */
  async forceSyncNow(): Promise<boolean> {
    if (!this.networkState.canSync) {
      return false;
    }

    await this.processSyncQueue();
    return true;
  }

  /**
   * Enable/disable sync on cellular
   */
  async setSyncOnCellular(enabled: boolean): Promise<void> {
    await AsyncStorage.setItem('sync_on_cellular', enabled.toString());
    
    // Update network state to reflect new setting
    const netInfo = await NetInfo.fetch();
    this.updateNetworkState(netInfo);
  }

  /**
   * Ensure a directory exists, creating it if necessary
   */
  private async ensureDirectoryExists(dirPath: string): Promise<void> {
    const dirInfo = await FileSystem.getInfoAsync(dirPath);
    if (!dirInfo.exists) {
      await FileSystem.makeDirectoryAsync(dirPath, { intermediates: true });
    }
  }

  /**
   * Initialize the SQLite database with required tables
   */
  private async initDatabase(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'));
        return;
      }

      this.db.transaction(tx => {
        // Create table for cached map regions
        tx.executeSql(
          `CREATE TABLE IF NOT EXISTS cached_regions (
            id TEXT PRIMARY KEY,
            region_data TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            expiry_date INTEGER NOT NULL,
            size_bytes INTEGER NOT NULL,
            tile_count INTEGER NOT NULL,
            is_complete INTEGER NOT NULL
          );`
        );

        // Create table for cached routes
        tx.executeSql(
          `CREATE TABLE IF NOT EXISTS cached_routes (
            id TEXT PRIMARY KEY,
            route_data TEXT NOT NULL,
            origin_name TEXT NOT NULL,
            destination_name TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            expiry_date INTEGER NOT NULL,
            size_bytes INTEGER NOT NULL
          );`
        );

        // Create table for cached content
        tx.executeSql(
          `CREATE TABLE IF NOT EXISTS cached_content (
            id TEXT PRIMARY KEY,
            content_type TEXT NOT NULL,
            location_data TEXT NOT NULL,
            content_data TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            expiry_date INTEGER NOT NULL
          );`
        );

        // Create table for download queue
        tx.executeSql(
          `CREATE TABLE IF NOT EXISTS download_queue (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            data TEXT NOT NULL,
            priority INTEGER NOT NULL,
            status TEXT NOT NULL,
            timestamp INTEGER NOT NULL
          );`
        );

        // Create table for sync queue
        tx.executeSql(
          `CREATE TABLE IF NOT EXISTS sync_queue (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            data TEXT NOT NULL,
            priority INTEGER NOT NULL,
            attempts INTEGER NOT NULL,
            max_attempts INTEGER NOT NULL,
            next_retry_time INTEGER NOT NULL,
            created_at INTEGER NOT NULL
          );`
        );
      }, 
      (error) => {
        console.error('Error initializing database:', error);
        reject(error);
      },
      () => {
        resolve();
      });
    });
  }

  /**
   * Download a map region for offline use
   */
  async downloadMapRegion(region: Region, expiryDays: number = 30): Promise<string> {
    try {
      await this.initialize();

      // Check if online
      const netInfo = await NetInfo.fetch();
      if (!netInfo.isConnected) {
        this.showNotification('Cannot download map: No internet connection');
        throw new Error('No internet connection');
      }

      // Check storage availability
      const stats = await this.getStorageStats();
      if (stats.percentUsed > 90) {
        this.showNotification('Storage almost full. Free some space or increase storage limit.');
        // Continue anyway but warn the user
      }

      // Generate unique ID for this region
      const regionId = this.generateRegionId(region);

      // Estimate size (this would be refined during actual download)
      const estimatedSize = this.estimateRegionSize(region);

      // Create region record
      const regionCache: RegionCache = {
        region,
        timeStamp: Date.now(),
        expiryDate: Date.now() + (expiryDays * 24 * 60 * 60 * 1000),
        sizeBytes: estimatedSize,
        tileCount: 0,
        isComplete: false,
      };

      // Store initial record
      await this.saveRegionToDB(regionId, regionCache);

      // Start download process (this would be an async operation in a real app)
      // In a real implementation, this would use a map provider's SDK to download tiles
      // For example with Google Maps: await MapboxOfflineManager.downloadRegion(region)
      
      // For this example, we'll simulate the download with a timeout
      setTimeout(async () => {
        // Update with "real" data after download
        regionCache.isComplete = true;
        regionCache.tileCount = this.calculateTileCount(region);
        regionCache.sizeBytes = this.calculateActualSize(regionCache.tileCount);
        
        await this.saveRegionToDB(regionId, regionCache);
        this.showNotification('Map region downloaded successfully');
      }, 3000);

      return regionId;
    } catch (error) {
      console.error('Error downloading map region:', error);
      throw error;
    }
  }

  /**
   * Download a route for offline use
   */
  async downloadRoute(
    origin: Location, 
    destination: Location,
    originName: string,
    destinationName: string,
    expiryDays: number = 30
  ): Promise<string> {
    try {
      await this.initialize();

      // Check if online
      const netInfo = await NetInfo.fetch();
      if (!netInfo.isConnected) {
        this.showNotification('Cannot download route: No internet connection');
        throw new Error('No internet connection');
      }

      // Generate unique ID
      const routeId = `route_${origin.latitude}_${origin.longitude}_${destination.latitude}_${destination.longitude}`;

      // Fetch route from server
      const response = await fetch(`${API_BASE_URL}/api/directions/preview`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          origin: {
            latitude: origin.latitude,
            longitude: origin.longitude,
          },
          destination: {
            latitude: destination.latitude,
            longitude: destination.longitude,
          },
          includeTraffic: false, // Traffic data isn't useful for offline
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch route: ${response.status}`);
      }

      const routeData = await response.json();
      const routeSize = JSON.stringify(routeData).length;

      // Store route
      const offlineRoute: OfflineRoute = {
        id: routeId,
        route: routeData,
        originName,
        destinationName,
        timeStamp: Date.now(),
        expiryDate: Date.now() + (expiryDays * 24 * 60 * 60 * 1000),
        sizeBytes: routeSize,
      };

      await this.saveRouteToDB(routeId, offlineRoute);

      // Also download the map region along the route
      const routeRegion = this.calculateRouteRegion(routeData.coordinates);
      await this.downloadMapRegion(routeRegion);

      this.showNotification('Route downloaded for offline use');
      return routeId;
    } catch (error) {
      console.error('Error downloading route:', error);
      throw error;
    }
  }

  /**
   * Save region data to database
   */
  private saveRegionToDB(regionId: string, regionCache: RegionCache): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'));
        return;
      }

      this.db.transaction(tx => {
        tx.executeSql(
          `INSERT OR REPLACE INTO cached_regions 
           (id, region_data, timestamp, expiry_date, size_bytes, tile_count, is_complete) 
           VALUES (?, ?, ?, ?, ?, ?, ?)`,
          [
            regionId,
            JSON.stringify(regionCache.region),
            regionCache.timeStamp,
            regionCache.expiryDate,
            regionCache.sizeBytes,
            regionCache.tileCount,
            regionCache.isComplete ? 1 : 0
          ],
          (_, result) => {
            resolve();
          },
          (_, error) => {
            reject(error);
            return false;
          }
        );
      });
    });
  }

  /**
   * Save route data to database
   */
  private saveRouteToDB(routeId: string, offlineRoute: OfflineRoute): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'));
        return;
      }

      this.db.transaction(tx => {
        tx.executeSql(
          `INSERT OR REPLACE INTO cached_routes 
           (id, route_data, origin_name, destination_name, timestamp, expiry_date, size_bytes) 
           VALUES (?, ?, ?, ?, ?, ?, ?)`,
          [
            routeId,
            JSON.stringify(offlineRoute.route),
            offlineRoute.originName,
            offlineRoute.destinationName,
            offlineRoute.timeStamp,
            offlineRoute.expiryDate,
            offlineRoute.sizeBytes
          ],
          (_, result) => {
            resolve();
          },
          (_, error) => {
            reject(error);
            return false;
          }
        );
      });
    });
  }

  /**
   * Get all downloaded map regions
   */
  async getDownloadedRegions(): Promise<RegionCache[]> {
    await this.initialize();
    
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'));
        return;
      }

      this.db.transaction(tx => {
        tx.executeSql(
          `SELECT * FROM cached_regions ORDER BY timestamp DESC`,
          [],
          (_, result) => {
            const regions: RegionCache[] = [];
            for (let i = 0; i < result.rows.length; i++) {
              const row = result.rows.item(i);
              regions.push({
                region: JSON.parse(row.region_data),
                timeStamp: row.timestamp,
                expiryDate: row.expiry_date,
                sizeBytes: row.size_bytes,
                tileCount: row.tile_count,
                isComplete: !!row.is_complete
              });
            }
            resolve(regions);
          },
          (_, error) => {
            reject(error);
            return false;
          }
        );
      });
    });
  }

  /**
   * Get all downloaded routes
   */
  async getDownloadedRoutes(): Promise<OfflineRoute[]> {
    await this.initialize();
    
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'));
        return;
      }

      this.db.transaction(tx => {
        tx.executeSql(
          `SELECT * FROM cached_routes ORDER BY timestamp DESC`,
          [],
          (_, result) => {
            const routes: OfflineRoute[] = [];
            for (let i = 0; i < result.rows.length; i++) {
              const row = result.rows.item(i);
              routes.push({
                id: row.id,
                route: JSON.parse(row.route_data),
                originName: row.origin_name,
                destinationName: row.destination_name,
                timeStamp: row.timestamp,
                expiryDate: row.expiry_date,
                sizeBytes: row.size_bytes
              });
            }
            resolve(routes);
          },
          (_, error) => {
            reject(error);
            return false;
          }
        );
      });
    });
  }

  /**
   * Get storage statistics
   */
  async getStorageStats(): Promise<StorageStats> {
    await this.initialize();

    try {
      // Get region stats
      const regions = await this.getDownloadedRegions();
      const regionTotalSize = regions.reduce((total, region) => total + region.sizeBytes, 0);

      // Get route stats
      const routes = await this.getDownloadedRoutes();
      const routeTotalSize = routes.reduce((total, route) => total + route.sizeBytes, 0);

      // Get content stats (would include more detailed implementation)
      const contentSize = 0; // placeholder
      const audioSize = 0; // placeholder
      const contentCount = 0; // placeholder
      const audioCount = 0; // placeholder

      const totalSize = regionTotalSize + routeTotalSize + contentSize + audioSize;

      return {
        totalStorageUsed: totalSize,
        maps: {
          count: regions.length,
          sizeBytes: regionTotalSize
        },
        routes: {
          count: routes.length,
          sizeBytes: routeTotalSize
        },
        content: {
          count: contentCount,
          sizeBytes: contentSize
        },
        audio: {
          count: audioCount,
          sizeBytes: audioSize
        },
        maxStorage: this.maxStorageBytes,
        percentUsed: (totalSize / this.maxStorageBytes) * 100
      };
    } catch (error) {
      console.error('Error getting storage stats:', error);
      throw error;
    }
  }

  /**
   * Clean expired content
   */
  async cleanExpiredContent(): Promise<void> {
    await this.initialize();

    const now = Date.now();

    if (!this.db) return;

    // Clean expired regions
    this.db.transaction(tx => {
      tx.executeSql(
        'DELETE FROM cached_regions WHERE expiry_date < ?',
        [now]
      );
      
      // Clean expired routes
      tx.executeSql(
        'DELETE FROM cached_routes WHERE expiry_date < ?',
        [now]
      );
      
      // Clean expired content
      tx.executeSql(
        'DELETE FROM cached_content WHERE expiry_date < ?',
        [now]
      );
    });
  }

  /**
   * Delete a map region
   */
  async deleteRegion(regionId: string): Promise<void> {
    await this.initialize();

    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'));
        return;
      }

      this.db.transaction(tx => {
        tx.executeSql(
          'DELETE FROM cached_regions WHERE id = ?',
          [regionId],
          (_, result) => {
            resolve();
          },
          (_, error) => {
            reject(error);
            return false;
          }
        );
      });
    });
  }

  /**
   * Delete a cached route
   */
  async deleteRoute(routeId: string): Promise<void> {
    await this.initialize();

    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'));
        return;
      }

      this.db.transaction(tx => {
        tx.executeSql(
          'DELETE FROM cached_routes WHERE id = ?',
          [routeId],
          (_, result) => {
            resolve();
          },
          (_, error) => {
            reject(error);
            return false;
          }
        );
      });
    });
  }

  /**
   * Set maximum storage limit for offline content
   */
  async setMaxStorage(bytes: number): Promise<void> {
    this.maxStorageBytes = bytes;
    await AsyncStorage.setItem('offline_max_storage', bytes.toString());
  }

  /**
   * Check if a route is available offline
   */
  async isRouteAvailableOffline(origin: Location, destination: Location): Promise<boolean> {
    await this.initialize();

    const routeId = `route_${origin.latitude}_${origin.longitude}_${destination.latitude}_${destination.longitude}`;
    
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'));
        return;
      }

      this.db.transaction(tx => {
        tx.executeSql(
          'SELECT id FROM cached_routes WHERE id = ?',
          [routeId],
          (_, result) => {
            resolve(result.rows.length > 0);
          },
          (_, error) => {
            reject(error);
            return false;
          }
        );
      });
    });
  }

  /**
   * Check if a map region is available offline
   */
  async isRegionAvailableOffline(region: Region): Promise<boolean> {
    await this.initialize();

    const regionId = this.generateRegionId(region);
    
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'));
        return;
      }

      this.db.transaction(tx => {
        tx.executeSql(
          'SELECT id FROM cached_regions WHERE id = ?',
          [regionId],
          (_, result) => {
            resolve(result.rows.length > 0);
          },
          (_, error) => {
            reject(error);
            return false;
          }
        );
      });
    });
  }

  /**
   * Generate a unique ID for a region
   */
  private generateRegionId(region: Region): string {
    return `region_${region.latitude.toFixed(3)}_${region.longitude.toFixed(3)}_${region.latitudeDelta.toFixed(3)}`;
  }

  /**
   * Estimate the size of a region in bytes
   */
  private estimateRegionSize(region: Region): number {
    // This is a simplistic calculation that should be replaced with more accurate estimation
    // based on zoom level, region size, and map provider specs
    const tileCount = this.calculateTileCount(region);
    return tileCount * 15000; // Assume average of 15KB per tile
  }

  /**
   * Calculate number of tiles for a region
   */
  private calculateTileCount(region: Region): number {
    // This is a simplistic calculation that should be replaced with more accurate calculation
    // based on zoom level, region size, and map provider specs
    const zoomLevel = Math.log2(360 / region.longitudeDelta) + 1;
    const tilesPerSide = Math.pow(2, zoomLevel);
    const lonTiles = (region.longitudeDelta / 360) * tilesPerSide;
    const latTiles = (region.latitudeDelta / 180) * tilesPerSide;
    return Math.ceil(lonTiles * latTiles);
  }

  /**
   * Calculate actual size based on tile count
   */
  private calculateActualSize(tileCount: number): number {
    // In a real app, this would measure actual downloaded files
    return tileCount * 15000; // Assume average of 15KB per tile
  }

  /**
   * Calculate region that contains all points in a route
   */
  private calculateRouteRegion(coordinates: Location[]): Region {
    if (!coordinates.length) {
      throw new Error('No coordinates provided');
    }

    let minLat = coordinates[0].latitude;
    let maxLat = coordinates[0].latitude;
    let minLng = coordinates[0].longitude;
    let maxLng = coordinates[0].longitude;

    coordinates.forEach((coord) => {
      minLat = Math.min(minLat, coord.latitude);
      maxLat = Math.max(maxLat, coord.latitude);
      minLng = Math.min(minLng, coord.longitude);
      maxLng = Math.max(maxLng, coord.longitude);
    });

    // Add padding
    const latPadding = (maxLat - minLat) * 0.1;
    const lngPadding = (maxLng - minLng) * 0.1;

    return {
      latitude: (minLat + maxLat) / 2,
      longitude: (minLng + maxLng) / 2,
      latitudeDelta: (maxLat - minLat) + 2 * latPadding,
      longitudeDelta: (maxLng - minLng) + 2 * lngPadding,
    };
  }

  /**
   * Show a notification to the user
   */
  private showNotification(message: string): void {
    if (Platform.OS === 'android') {
      ToastAndroid.show(message, ToastAndroid.SHORT);
    } else {
      // For iOS, use Alert since there's no Toast equivalent
      Alert.alert('Offline Maps', message);
    }
  }
}

export default OfflineManager.getInstance(); 