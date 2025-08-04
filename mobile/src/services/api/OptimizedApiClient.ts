import AsyncStorage from '@react-native-async-storage/async-storage';
import * as FileSystem from 'expo-file-system';
import { API_URL } from '@/config';
import { ApiClient, ApiError } from './ApiClient';
import { recordApiPerformance } from '@/utils/performance';
import NetInfo from '@react-native-community/netinfo';
import { Platform } from 'react-native';

import { logger } from '@/services/logger';
// Cache settings
const API_CACHE_PREFIX = '@RoadTrip:api_cache:';
const DEFAULT_CACHE_TTL = 60 * 60 * 1000; // 1 hour
const MAX_CACHE_ENTRIES = 200;
const MAX_CACHE_SIZE_MB = 10; // Maximum cache size in MB

// Types
interface CacheSettings {
  ttl: number;
  networkPolicy: 'networkOnly' | 'cacheOnly' | 'cacheFirst' | 'networkFirst' | 'staleWhileRevalidate';
  isPrivate: boolean; // Whether the data contains user-specific info
  forceRefresh?: boolean;
}

interface CacheMetadata {
  url: string;
  timestamp: number;
  expiryTime: number;
  size: number;
  etag?: string;
  lastModified?: string;
  isPrivate: boolean;
}

interface CacheRegistry {
  entries: Record<string, CacheMetadata>;
  totalSize: number;
  lastCleanup: number;
}

interface CacheResponse<T> {
  data: T;
  metadata: CacheMetadata;
  isStale: boolean;
}

interface ApiResponse<T> {
  data: T;
  fromCache?: boolean;
  status: number;
  headers: Record<string, string>;
}

// Default cache settings
const defaultCacheSettings: CacheSettings = {
  ttl: DEFAULT_CACHE_TTL,
  networkPolicy: 'networkFirst',
  isPrivate: false,
};

export class OptimizedApiClient extends ApiClient {
  private cacheRegistry: CacheRegistry = {
    entries: {},
    totalSize: 0,
    lastCleanup: Date.now(),
  };
  private cacheInitialized = false;
  private offlineMode = false;
  private compressLargeResponses = true;
  private compressionThreshold = 50 * 1024; // 50KB
  private lowBandwidthMode = false;
  private connectionType: string | null = null;
  private mobileDataSavingEnabled = false;

  constructor(options: any = {}) {
    super(options);
    
    // Initialize cache and network state
    this.initCache();
    this.setupNetworkMonitoring();
    
    // Additional options
    this.compressLargeResponses = options.compressLargeResponses ?? true;
    this.compressionThreshold = options.compressionThreshold ?? 50 * 1024;
    this.mobileDataSavingEnabled = options.mobileDataSavingEnabled ?? false;
  }

  private async initCache(): Promise<void> {
    if (this.cacheInitialized) return;
    
    try {
      // Load cache registry from storage
      const registryData = await AsyncStorage.getItem(`${API_CACHE_PREFIX}registry`);
      if (registryData) {
        this.cacheRegistry = JSON.parse(registryData);
      }
      
      // Run cleanup if needed
      if (Date.now() - this.cacheRegistry.lastCleanup > 24 * 60 * 60 * 1000) {
        await this.cleanupCache();
      }
      
      this.cacheInitialized = true;
    } catch (error) {
      logger.error('Failed to initialize API cache:', error);
      // Reset registry on error
      this.cacheRegistry = {
        entries: {},
        totalSize: 0,
        lastCleanup: Date.now(),
      };
    }
  }

  private setupNetworkMonitoring(): void {
    // Subscribe to network info changes
    NetInfo.addEventListener(state => {
      this.offlineMode = !state.isConnected;
      this.connectionType = state.type;
      
      // Set low bandwidth mode for cellular connections
      if (this.mobileDataSavingEnabled) {
        this.lowBandwidthMode = state.type === 'cellular';
      }
      
      // Log network state change
      logger.debug('Network state changed:', {
        isConnected: state.isConnected,
        type: state.type,
        offlineMode: this.offlineMode,
        lowBandwidthMode: this.lowBandwidthMode,
      });
    });
  }

  private async saveRegistry(): Promise<void> {
    try {
      await AsyncStorage.setItem(
        `${API_CACHE_PREFIX}registry`,
        JSON.stringify(this.cacheRegistry)
      );
    } catch (error) {
      logger.error('Failed to save cache registry:', error);
    }
  }

  private async cleanupCache(): Promise<void> {
    const now = Date.now();
    this.cacheRegistry.lastCleanup = now;
    
    // Find expired entries
    const expiredKeys: string[] = [];
    const sizeMap: Record<string, number> = {};
    let totalSize = 0;
    
    // First pass: identify expired entries and calculate sizes
    for (const [key, metadata] of Object.entries(this.cacheRegistry.entries)) {
      sizeMap[key] = metadata.size;
      totalSize += metadata.size;
      
      if (now > metadata.expiryTime) {
        expiredKeys.push(key);
      }
    }
    
    // Delete expired entries
    for (const key of expiredKeys) {
      await this.removeCacheEntry(key);
    }
    
    // If still exceeding maximum size, remove least recently used entries
    if (totalSize > MAX_CACHE_SIZE_MB * 1024 * 1024) {
      // Sort entries by timestamp (oldest first)
      const entries = Object.entries(this.cacheRegistry.entries)
        .sort(([, a], [, b]) => a.timestamp - b.timestamp);
      
      // Remove oldest entries until under size limit
      let currentSize = totalSize;
      for (const [key, metadata] of entries) {
        if (currentSize <= MAX_CACHE_SIZE_MB * 1024 * 1024) {
          break;
        }
        
        await this.removeCacheEntry(key);
        currentSize -= metadata.size;
      }
    }
    
    // Update registry
    await this.saveRegistry();
  }

  private async removeCacheEntry(key: string): Promise<void> {
    try {
      const metadata = this.cacheRegistry.entries[key];
      if (!metadata) return;
      
      // Delete the file
      const filePath = this.getCacheFilePath(key);
      await FileSystem.deleteAsync(filePath, { idempotent: true });
      
      // Update registry
      this.cacheRegistry.totalSize -= metadata.size;
      delete this.cacheRegistry.entries[key];
    } catch (error) {
      logger.warn(`Failed to remove cache entry ${key}:`, error);
    }
  }

  private getCacheFilePath(key: string): string {
    return `${FileSystem.cacheDirectory}${key.replace(/[\/\?=]/g, '_')}.json`;
  }

  private generateCacheKey(url: string, params?: Record<string, any>): string {
    // Create a string representation of the URL and query params
    let fullUrl = url;
    
    if (params) {
      const queryParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          queryParams.append(key, String(value));
        }
      });
      
      const queryString = queryParams.toString();
      if (queryString) {
        fullUrl += (url.includes('?') ? '&' : '?') + queryString;
      }
    }
    
    // Return a cache key based on the URL
    return `${API_CACHE_PREFIX}${fullUrl}`;
  }

  private async getCachedResponse<T>(
    key: string, 
    url: string
  ): Promise<CacheResponse<T> | null> {
    if (!this.cacheInitialized) {
      await this.initCache();
    }
    
    // Check if entry exists in registry
    const metadata = this.cacheRegistry.entries[key];
    if (!metadata) {
      return null;
    }
    
    try {
      // Read the cache file
      const filePath = this.getCacheFilePath(key);
      const fileInfo = await FileSystem.getInfoAsync(filePath);
      
      if (!fileInfo.exists) {
        // Clean up registry if file doesn't exist
        delete this.cacheRegistry.entries[key];
        this.cacheRegistry.totalSize -= metadata.size;
        await this.saveRegistry();
        return null;
      }
      
      // Read and parse file
      const content = await FileSystem.readAsStringAsync(filePath);
      let cachedData: T;
      
      try {
        cachedData = JSON.parse(content);
      } catch (e) {
        // Handle compressed data
        if (content.startsWith('compressed:')) {
          const base64Data = content.substring(11); // Remove 'compressed:' prefix
          const decompressedData = await FileSystem.readAsStringAsync(
            FileSystem.documentDirectory + 'temp_decompress.txt',
            { encoding: FileSystem.EncodingType.Base64 }
          );
          cachedData = JSON.parse(decompressedData);
        } else {
          throw e;
        }
      }
      
      // Check if cache is stale
      const now = Date.now();
      const isStale = now > metadata.expiryTime;
      
      // Update last accessed timestamp
      metadata.timestamp = now;
      await this.saveRegistry();
      
      return {
        data: cachedData,
        metadata,
        isStale,
      };
    } catch (error) {
      logger.warn(`Error reading cache for ${url}:`, error);
      return null;
    }
  }

  private async saveCachedResponse<T>(
    key: string,
    url: string,
    data: T,
    settings: CacheSettings,
    headers: Record<string, string>
  ): Promise<void> {
    if (!this.cacheInitialized) {
      await this.initCache();
    }
    
    try {
      // Prepare data for saving
      let dataToSave: string;
      let isCompressed = false;
      
      // Stringify the data
      const jsonData = JSON.stringify(data);
      
      // Compress large responses if enabled
      if (this.compressLargeResponses && jsonData.length > this.compressionThreshold) {
        try {
          // Write to temp file
          const tempFile = `${FileSystem.documentDirectory}temp_compress.txt`;
          await FileSystem.writeAsStringAsync(tempFile, jsonData);
          
          // Read as base64 (equivalent to compression for storage)
          const base64Data = await FileSystem.readAsStringAsync(
            tempFile,
            { encoding: FileSystem.EncodingType.Base64 }
          );
          
          // Only use compressed version if it's actually smaller
          if (base64Data.length < jsonData.length) {
            dataToSave = `compressed:${base64Data}`;
            isCompressed = true;
          } else {
            dataToSave = jsonData;
          }
          
          // Clean up temp file
          await FileSystem.deleteAsync(tempFile, { idempotent: true });
        } catch (e) {
          // Fallback to uncompressed data
          dataToSave = jsonData;
          logger.warn('Compression failed, using uncompressed data:', e);
        }
      } else {
        dataToSave = jsonData;
      }
      
      // Write to cache file
      const filePath = this.getCacheFilePath(key);
      await FileSystem.writeAsStringAsync(filePath, dataToSave);
      
      // Get file size
      const fileInfo = await FileSystem.getInfoAsync(filePath);
      const fileSize = fileInfo.size || 0;
      
      // Create metadata
      const now = Date.now();
      const metadata: CacheMetadata = {
        url,
        timestamp: now,
        expiryTime: now + settings.ttl,
        size: fileSize,
        isPrivate: settings.isPrivate,
        etag: headers['etag'] || headers['ETag'],
        lastModified: headers['last-modified'] || headers['Last-Modified'],
      };
      
      // Check if entry already exists
      if (this.cacheRegistry.entries[key]) {
        // Update size delta
        this.cacheRegistry.totalSize -= this.cacheRegistry.entries[key].size;
      }
      
      // Add to registry
      this.cacheRegistry.entries[key] = metadata;
      this.cacheRegistry.totalSize += fileSize;
      
      // Save registry
      await this.saveRegistry();
      
      // Clean up cache if needed
      if (Object.keys(this.cacheRegistry.entries).length > MAX_CACHE_ENTRIES ||
          this.cacheRegistry.totalSize > MAX_CACHE_SIZE_MB * 1024 * 1024) {
        await this.cleanupCache();
      }
    } catch (error) {
      logger.error(`Failed to cache response for ${url}:`, error);
    }
  }

  // Override GET method with caching support
  async get<T>(
    url: string, 
    params?: Record<string, any>, 
    cacheOptions?: Partial<CacheSettings>
  ): Promise<T> {
    const startTime = Date.now();
    const settings: CacheSettings = { ...defaultCacheSettings, ...cacheOptions };
    const cacheKey = this.generateCacheKey(url, params);
    let responseSize = 0;
    let fromCache = false;
    
    try {
      let data: T;
      let cacheResponse: CacheResponse<T> | null = null;
      const fullUrl = url.startsWith('http') ? url : `${this.baseURL}${url}`;
      
      // Handle different network policies
      switch (settings.networkPolicy) {
        case 'cacheOnly':
          // Only use cache
          cacheResponse = await this.getCachedResponse<T>(cacheKey, url);
          if (cacheResponse) {
            data = cacheResponse.data;
            fromCache = true;
          } else {
            throw new ApiError('No cached data available for offline use', 0, { url });
          }
          break;
          
        case 'networkOnly':
          // Skip cache, always use network
          if (this.offlineMode) {
            throw new ApiError('Network is unavailable', 0, { url });
          }
          
          // Call parent implementation
          data = await super.get<T>(url, params);
          
          // Cache the response for future offline use
          if (data && !settings.isPrivate) {
            await this.saveCachedResponse(cacheKey, url, data, settings, {});
          }
          break;
          
        case 'cacheFirst':
          // Try cache first, then network
          cacheResponse = await this.getCachedResponse<T>(cacheKey, url);
          
          if (cacheResponse && !cacheResponse.isStale) {
            // Use cache if available and not stale
            data = cacheResponse.data;
            fromCache = true;
          } else if (this.offlineMode) {
            // In offline mode, use stale cache if available
            if (cacheResponse) {
              data = cacheResponse.data;
              fromCache = true;
            } else {
              throw new ApiError('No cached data available for offline use', 0, { url });
            }
          } else {
            // Otherwise use network
            try {
              const headers = cacheResponse?.metadata 
                ? this.addCacheHeaders({}, cacheResponse.metadata)
                : {};
                
              const response = await this.fetchWithRetry<T>(fullUrl, {
                method: 'GET',
                headers,
              });
              
              data = response.data;
              responseSize = JSON.stringify(data).length;
              
              // Cache the response
              if (data && !settings.isPrivate) {
                await this.saveCachedResponse(cacheKey, url, data, settings, response.headers);
              }
            } catch (error) {
              // If network fails, fall back to cache
              if (cacheResponse) {
                data = cacheResponse.data;
                fromCache = true;
                logger.debug(`Network request failed, using cached data for ${url}`);
              } else {
                throw error;
              }
            }
          }
          break;
          
        case 'staleWhileRevalidate':
          // Use cache immediately, then update in background
          cacheResponse = await this.getCachedResponse<T>(cacheKey, url);
          
          if (cacheResponse) {
            // Use cache data immediately
            data = cacheResponse.data;
            fromCache = true;
            
            // If cache is stale and online, update in background
            if (cacheResponse.isStale && !this.offlineMode) {
              // Don't await, do this in background
              this.fetchWithRetry<T>(fullUrl, {
                method: 'GET',
                headers: this.addCacheHeaders({}, cacheResponse.metadata),
              }).then(response => {
                // Cache the updated response
                if (response.data && !settings.isPrivate) {
                  this.saveCachedResponse(cacheKey, url, response.data, settings, response.headers);
                }
              }).catch(error => {
                logger.warn(`Background refresh failed for ${url}:`, error);
              });
            }
          } else if (this.offlineMode) {
            throw new ApiError('No cached data available for offline use', 0, { url });
          } else {
            // No cache, get from network
            const response = await this.fetchWithRetry<T>(fullUrl, {
              method: 'GET',
              headers: {},
            });
            
            data = response.data;
            responseSize = JSON.stringify(data).length;
            
            // Cache the response
            if (data && !settings.isPrivate) {
              await this.saveCachedResponse(cacheKey, url, data, settings, response.headers);
            }
          }
          break;
          
        case 'networkFirst':
        default:
          // Try network first, then cache
          if (this.offlineMode) {
            // In offline mode, use cache
            cacheResponse = await this.getCachedResponse<T>(cacheKey, url);
            if (cacheResponse) {
              data = cacheResponse.data;
              fromCache = true;
            } else {
              throw new ApiError('No cached data available for offline use', 0, { url });
            }
          } else {
            // Online mode, try network first
            try {
              // Get cache headers for conditional request
              cacheResponse = await this.getCachedResponse<T>(cacheKey, url);
              const headers = cacheResponse?.metadata 
                ? this.addCacheHeaders({}, cacheResponse.metadata)
                : {};
              
              const response = await this.fetchWithRetry<T>(fullUrl, {
                method: 'GET',
                headers,
              });
              
              // Check if we got a 304 Not Modified with empty response
              if (response.status === 304 && cacheResponse) {
                data = cacheResponse.data;
                fromCache = true;
                
                // Update cache timestamp to extend TTL
                await this.updateCacheTimestamp(cacheKey, settings.ttl);
              } else {
                data = response.data;
                responseSize = JSON.stringify(data).length;
                
                // Cache the response
                if (data && !settings.isPrivate) {
                  await this.saveCachedResponse(cacheKey, url, data, settings, response.headers);
                }
              }
            } catch (error) {
              // If network fails, fall back to cache
              cacheResponse = await this.getCachedResponse<T>(cacheKey, url);
              if (cacheResponse) {
                data = cacheResponse.data;
                fromCache = true;
                logger.debug(`Network request failed, using cached data for ${url}`);
              } else {
                throw error;
              }
            }
          }
          break;
      }
      
      // Record API performance metrics
      const duration = Date.now() - startTime;
      recordApiPerformance(url, 'GET', duration, 200, responseSize);
      
      return data;
    } catch (error) {
      // Record API error
      const duration = Date.now() - startTime;
      const status = error instanceof ApiError ? error.status : 0;
      recordApiPerformance(url, 'GET', duration, status, 0);
      
      throw error;
    }
  }

  // Update cache entry timestamp to extend TTL
  private async updateCacheTimestamp(key: string, ttl: number): Promise<void> {
    const metadata = this.cacheRegistry.entries[key];
    if (metadata) {
      const now = Date.now();
      metadata.timestamp = now;
      metadata.expiryTime = now + ttl;
      await this.saveRegistry();
    }
  }

  // Add cache headers for conditional requests
  private addCacheHeaders(
    headers: Record<string, string>,
    metadata: CacheMetadata
  ): Record<string, string> {
    const result = { ...headers };
    
    // Add ETag for caching
    if (metadata.etag) {
      result['If-None-Match'] = metadata.etag;
    }
    
    // Add Last-Modified
    if (metadata.lastModified) {
      result['If-Modified-Since'] = metadata.lastModified;
    }
    
    return result;
  }

  // Override the fetch with retry method to handle offline mode
  private async fetchWithRetry<T>(
    url: string,
    options: RequestInit,
    retries = 0
  ): Promise<ApiResponse<T>> {
    if (this.offlineMode && retries === 0) {
      throw new ApiError('Network is unavailable', 0, { url });
    }
    
    // Adjust request for low bandwidth mode
    if (this.lowBandwidthMode) {
      // Add a custom header to tell the server we're in low bandwidth mode
      if (!options.headers) {
        options.headers = {};
      }
      
      (options.headers as Record<string, string>)['X-Low-Bandwidth-Mode'] = 'true';
      
      // Request less data in low bandwidth mode
      if (url.includes('?')) {
        url += '&low_bandwidth=true';
      } else {
        url += '?low_bandwidth=true';
      }
    }
    
    // Use parent implementation
    return super.fetchWithRetry<T>(url, options, retries);
  }

  // Cache management methods
  async clearCache(): Promise<void> {
    try {
      // Reset the registry
      this.cacheRegistry = {
        entries: {},
        totalSize: 0,
        lastCleanup: Date.now(),
      };
      
      // Save empty registry
      await this.saveRegistry();
      
      // Clear cache directory files
      const cacheDir = FileSystem.cacheDirectory;
      if (cacheDir) {
        const files = await FileSystem.readDirectoryAsync(cacheDir);
        const apiCacheFiles = files.filter(file => file.startsWith(API_CACHE_PREFIX.replace('@', '')));
        
        for (const file of apiCacheFiles) {
          await FileSystem.deleteAsync(`${cacheDir}${file}`, { idempotent: true });
        }
      }
      
      logger.debug('API cache cleared successfully');
    } catch (error) {
      logger.error('Failed to clear API cache:', error);
    }
  }

  async clearCacheForEndpoint(urlPattern: string): Promise<number> {
    let cleared = 0;
    
    try {
      // Find matching entries
      for (const [key, metadata] of Object.entries(this.cacheRegistry.entries)) {
        if (metadata.url.includes(urlPattern)) {
          await this.removeCacheEntry(key);
          cleared++;
        }
      }
      
      // Save updated registry
      await this.saveRegistry();
      
      logger.debug(`Cleared ${cleared} cache entries for pattern: ${urlPattern}`);
      return cleared;
    } catch (error) {
      logger.error(`Failed to clear cache for pattern ${urlPattern}:`, error);
      return cleared;
    }
  }

  async clearPrivateCache(): Promise<number> {
    let cleared = 0;
    
    try {
      // Find private entries
      for (const [key, metadata] of Object.entries(this.cacheRegistry.entries)) {
        if (metadata.isPrivate) {
          await this.removeCacheEntry(key);
          cleared++;
        }
      }
      
      // Save updated registry
      await this.saveRegistry();
      
      logger.debug(`Cleared ${cleared} private cache entries`);
      return cleared;
    } catch (error) {
      logger.error('Failed to clear private cache:', error);
      return cleared;
    }
  }

  getCacheStats(): Record<string, any> {
    return {
      totalEntries: Object.keys(this.cacheRegistry.entries).length,
      totalSizeBytes: this.cacheRegistry.totalSize,
      totalSizeMB: Math.round(this.cacheRegistry.totalSize / (1024 * 1024) * 100) / 100,
      lastCleanup: new Date(this.cacheRegistry.lastCleanup).toISOString(),
      privateEntries: Object.values(this.cacheRegistry.entries).filter(m => m.isPrivate).length,
      offlineMode: this.offlineMode,
      lowBandwidthMode: this.lowBandwidthMode,
      connectionType: this.connectionType,
    };
  }

  // Network status methods
  setOfflineMode(enabled: boolean): void {
    this.offlineMode = enabled;
    logger.debug(`Offline mode ${enabled ? 'enabled' : 'disabled'}`);
  }

  setLowBandwidthMode(enabled: boolean): void {
    this.lowBandwidthMode = enabled;
    logger.debug(`Low bandwidth mode ${enabled ? 'enabled' : 'disabled'}`);
  }

  setMobileDataSaving(enabled: boolean): void {
    this.mobileDataSavingEnabled = enabled;
    // Update low bandwidth mode based on current connection type
    if (enabled && this.connectionType === 'cellular') {
      this.lowBandwidthMode = true;
    } else if (!enabled) {
      this.lowBandwidthMode = false;
    }
  }

  // Prefetch an API endpoint for offline use
  async prefetch(url: string, params?: Record<string, any>, ttl?: number): Promise<boolean> {
    try {
      const settings: CacheSettings = {
        ...defaultCacheSettings,
        ttl: ttl || DEFAULT_CACHE_TTL,
        networkPolicy: 'networkOnly',
        isPrivate: false,
      };
      
      // Force a fresh network request to cache the result
      await this.get(url, params, settings);
      return true;
    } catch (error) {
      logger.warn(`Failed to prefetch ${url}:`, error);
      return false;
    }
  }
}

// Export a singleton instance for app-wide use
export const optimizedApiClient = new OptimizedApiClient({
  baseURL: API_URL,
  mobileDataSavingEnabled: true,
});

// Export default for when custom instances are needed
export default OptimizedApiClient;