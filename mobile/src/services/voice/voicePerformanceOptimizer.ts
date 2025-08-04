/**
 * Voice Performance Optimizer
 * Implements caching, request batching, and performance monitoring
 * for world-class voice experience
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import NetInfo from '@react-native-community/netinfo';
import { EventEmitter } from 'events';
import * as Crypto from 'expo-crypto';

import { logger } from '@/services/logger';
interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number;
}

interface PerformanceMetrics {
  operationName: string;
  duration: number;
  timestamp: number;
  success: boolean;
  cacheHit?: boolean;
}

interface RequestBatch {
  id: string;
  requests: Array<{
    key: string;
    resolver: (value: any) => void;
    rejecter: (error: any) => void;
  }>;
  timer: NodeJS.Timeout;
}

class VoicePerformanceOptimizer extends EventEmitter {
  private cache: Map<string, CacheEntry<any>> = new Map();
  private performanceBuffer: PerformanceMetrics[] = [];
  private requestBatches: Map<string, RequestBatch> = new Map();
  private offlineQueue: Array<{
    operation: string;
    params: any;
    timestamp: number;
  }> = [];
  
  // Performance thresholds
  private readonly PERFORMANCE_THRESHOLDS = {
    VOICE_PROCESSING: 2000, // 2 seconds
    CACHE_OPERATION: 50,    // 50ms
    NETWORK_TIMEOUT: 5000,  // 5 seconds
  };

  // Cache configuration
  private readonly CACHE_CONFIG = {
    MAX_SIZE: 100,
    DEFAULT_TTL: 300000, // 5 minutes
    INTENT_TTL: 600000,  // 10 minutes for intent analysis
    RESTAURANT_TTL: 1800000, // 30 minutes for restaurant data
  };

  // Batch configuration
  private readonly BATCH_CONFIG = {
    DELAY: 50, // 50ms delay for batching
    MAX_SIZE: 10,
  };

  constructor() {
    super();
    this.initializeOfflineSupport();
    this.startPerformanceMonitoring();
    this.loadPersistedCache();
  }

  /**
   * Cache-aware operation wrapper
   */
  async withCache<T>(
    key: string,
    operation: () => Promise<T>,
    ttl?: number
  ): Promise<T> {
    const startTime = Date.now();
    
    // Check cache first
    const cached = await this.getFromCache<T>(key);
    if (cached !== null) {
      this.recordMetric({
        operationName: 'cache_hit',
        duration: Date.now() - startTime,
        timestamp: Date.now(),
        success: true,
        cacheHit: true,
      });
      return cached;
    }

    // Execute operation
    try {
      const result = await operation();
      
      // Cache the result
      await this.setInCache(key, result, ttl || this.CACHE_CONFIG.DEFAULT_TTL);
      
      this.recordMetric({
        operationName: 'cache_miss',
        duration: Date.now() - startTime,
        timestamp: Date.now(),
        success: true,
        cacheHit: false,
      });
      
      return result;
    } catch (error) {
      this.recordMetric({
        operationName: 'cache_operation_error',
        duration: Date.now() - startTime,
        timestamp: Date.now(),
        success: false,
      });
      throw error;
    }
  }

  /**
   * Batch multiple requests to reduce API calls
   */
  async batchRequest<T>(
    batchKey: string,
    requestKey: string,
    batchProcessor: (keys: string[]) => Promise<Map<string, T>>
  ): Promise<T> {
    return new Promise((resolve, reject) => {
      // Get or create batch
      let batch = this.requestBatches.get(batchKey);
      
      if (!batch) {
        batch = {
          id: batchKey,
          requests: [],
          timer: setTimeout(() => this.processBatch(batchKey, batchProcessor), this.BATCH_CONFIG.DELAY),
        };
        this.requestBatches.set(batchKey, batch);
      }

      // Add request to batch
      batch.requests.push({
        key: requestKey,
        resolver: resolve,
        rejecter: reject,
      });

      // Process immediately if batch is full
      if (batch.requests.length >= this.BATCH_CONFIG.MAX_SIZE) {
        clearTimeout(batch.timer);
        this.processBatch(batchKey, batchProcessor);
      }
    });
  }

  /**
   * Performance monitoring wrapper
   */
  async measurePerformance<T>(
    operationName: string,
    operation: () => Promise<T>
  ): Promise<T> {
    const startTime = Date.now();
    
    try {
      const result = await operation();
      const duration = Date.now() - startTime;
      
      this.recordMetric({
        operationName,
        duration,
        timestamp: Date.now(),
        success: true,
      });

      // Check against thresholds
      this.checkPerformanceThreshold(operationName, duration);
      
      return result;
    } catch (error) {
      const duration = Date.now() - startTime;
      
      this.recordMetric({
        operationName,
        duration,
        timestamp: Date.now(),
        success: false,
      });
      
      throw error;
    }
  }

  /**
   * Offline queue management
   */
  async queueForOffline(operation: string, params: any): Promise<void> {
    const queueItem = {
      operation,
      params,
      timestamp: Date.now(),
    };
    
    this.offlineQueue.push(queueItem);
    
    // Persist queue
    await AsyncStorage.setItem(
      '@voice_offline_queue',
      JSON.stringify(this.offlineQueue)
    );
    
    this.emit('offlineQueueUpdated', this.offlineQueue.length);
  }

  /**
   * Process offline queue when connection restored
   */
  async processOfflineQueue(): Promise<void> {
    if (this.offlineQueue.length === 0) return;
    
    const queue = [...this.offlineQueue];
    this.offlineQueue = [];
    
    for (const item of queue) {
      try {
        this.emit('processingOfflineItem', item);
        // Process based on operation type
        await this.processOfflineOperation(item);
      } catch (error) {
        logger.error('Failed to process offline item:', error);
        // Re-queue if still offline
        const netState = await NetInfo.fetch();
        if (!netState.isConnected) {
          this.offlineQueue.push(item);
        }
      }
    }
    
    // Update persisted queue
    await AsyncStorage.setItem(
      '@voice_offline_queue',
      JSON.stringify(this.offlineQueue)
    );
  }

  /**
   * Get performance report
   */
  getPerformanceReport(): {
    summary: any;
    recentMetrics: PerformanceMetrics[];
    recommendations: string[];
  } {
    const recentMetrics = this.performanceBuffer.slice(-100);
    
    // Calculate summary statistics
    const summary = this.calculatePerformanceSummary(recentMetrics);
    
    // Generate recommendations
    const recommendations = this.generatePerformanceRecommendations(summary);
    
    return {
      summary,
      recentMetrics,
      recommendations,
    };
  }

  /**
   * Clear cache based on strategy
   */
  async clearCache(strategy: 'all' | 'expired' | 'lru' = 'expired'): Promise<void> {
    const startTime = Date.now();
    
    switch (strategy) {
      case 'all':
        this.cache.clear();
        break;
        
      case 'expired':
        const now = Date.now();
        for (const [key, entry] of this.cache.entries()) {
          if (now - entry.timestamp > entry.ttl) {
            this.cache.delete(key);
          }
        }
        break;
        
      case 'lru':
        // Keep most recent half of cache
        if (this.cache.size > this.CACHE_CONFIG.MAX_SIZE) {
          const entries = Array.from(this.cache.entries())
            .sort((a, b) => b[1].timestamp - a[1].timestamp);
          
          const toKeep = entries.slice(0, this.CACHE_CONFIG.MAX_SIZE / 2);
          this.cache.clear();
          
          for (const [key, value] of toKeep) {
            this.cache.set(key, value);
          }
        }
        break;
    }
    
    // Persist cache changes
    await this.persistCache();
    
    this.emit('cacheCleared', {
      strategy,
      duration: Date.now() - startTime,
      remainingSize: this.cache.size,
    });
  }

  /**
   * Optimize for current network conditions
   */
  async optimizeForNetwork(): Promise<void> {
    const netState = await NetInfo.fetch();
    
    if (!netState.isConnected) {
      // Offline mode - use aggressive caching
      this.CACHE_CONFIG.DEFAULT_TTL = 3600000; // 1 hour
      this.emit('networkOptimization', 'offline');
    } else if (netState.type === 'cellular') {
      // Cellular - moderate caching
      this.CACHE_CONFIG.DEFAULT_TTL = 900000; // 15 minutes
      this.emit('networkOptimization', 'cellular');
    } else {
      // WiFi - normal caching
      this.CACHE_CONFIG.DEFAULT_TTL = 300000; // 5 minutes
      this.emit('networkOptimization', 'wifi');
    }
  }

  // Private methods

  private async getFromCache<T>(key: string): Promise<T | null> {
    // Check memory cache
    const cached = this.cache.get(key);
    
    if (cached) {
      const now = Date.now();
      if (now - cached.timestamp <= cached.ttl) {
        return cached.data;
      } else {
        // Expired
        this.cache.delete(key);
      }
    }
    
    // Check persistent cache
    try {
      const stored = await AsyncStorage.getItem(`@voice_cache:${key}`);
      if (stored) {
        const parsed = JSON.parse(stored) as CacheEntry<T>;
        const now = Date.now();
        
        if (now - parsed.timestamp <= parsed.ttl) {
          // Restore to memory cache
          this.cache.set(key, parsed);
          return parsed.data;
        }
      }
    } catch (error) {
      logger.error('Cache retrieval error:', error);
    }
    
    return null;
  }

  private async setInCache<T>(key: string, data: T, ttl: number): Promise<void> {
    const entry: CacheEntry<T> = {
      data,
      timestamp: Date.now(),
      ttl,
    };
    
    // Set in memory
    this.cache.set(key, entry);
    
    // Enforce cache size limit
    if (this.cache.size > this.CACHE_CONFIG.MAX_SIZE) {
      await this.clearCache('lru');
    }
    
    // Persist important entries
    if (ttl > 300000) { // Persist if TTL > 5 minutes
      try {
        await AsyncStorage.setItem(
          `@voice_cache:${key}`,
          JSON.stringify(entry)
        );
      } catch (error) {
        logger.error('Cache persistence error:', error);
      }
    }
  }

  private async processBatch<T>(
    batchKey: string,
    batchProcessor: (keys: string[]) => Promise<Map<string, T>>
  ): Promise<void> {
    const batch = this.requestBatches.get(batchKey);
    if (!batch) return;
    
    this.requestBatches.delete(batchKey);
    
    const keys = batch.requests.map(r => r.key);
    
    try {
      const results = await batchProcessor(keys);
      
      // Resolve individual requests
      for (const request of batch.requests) {
        const result = results.get(request.key);
        if (result !== undefined) {
          request.resolver(result);
        } else {
          request.rejecter(new Error(`No result for key: ${request.key}`));
        }
      }
    } catch (error) {
      // Reject all requests in batch
      for (const request of batch.requests) {
        request.rejecter(error);
      }
    }
  }

  private recordMetric(metric: PerformanceMetrics): void {
    this.performanceBuffer.push(metric);
    
    // Keep buffer size limited
    if (this.performanceBuffer.length > 1000) {
      this.performanceBuffer = this.performanceBuffer.slice(-500);
    }
    
    this.emit('performanceMetric', metric);
  }

  private checkPerformanceThreshold(operationName: string, duration: number): void {
    const threshold = this.PERFORMANCE_THRESHOLDS[operationName as keyof typeof this.PERFORMANCE_THRESHOLDS];
    
    if (threshold && duration > threshold) {
      this.emit('performanceThresholdExceeded', {
        operationName,
        duration,
        threshold,
        exceedance: duration - threshold,
      });
    }
  }

  private calculatePerformanceSummary(metrics: PerformanceMetrics[]): any {
    if (metrics.length === 0) return {};
    
    const byOperation = new Map<string, number[]>();
    
    for (const metric of metrics) {
      if (!byOperation.has(metric.operationName)) {
        byOperation.set(metric.operationName, []);
      }
      byOperation.get(metric.operationName)!.push(metric.duration);
    }
    
    const summary: any = {};
    
    for (const [operation, durations] of byOperation.entries()) {
      const sorted = durations.sort((a, b) => a - b);
      summary[operation] = {
        count: durations.length,
        min: sorted[0],
        max: sorted[sorted.length - 1],
        avg: durations.reduce((a, b) => a + b, 0) / durations.length,
        p50: sorted[Math.floor(sorted.length * 0.5)],
        p95: sorted[Math.floor(sorted.length * 0.95)],
        p99: sorted[Math.floor(sorted.length * 0.99)],
      };
    }
    
    return summary;
  }

  private generatePerformanceRecommendations(summary: any): string[] {
    const recommendations: string[] = [];
    
    for (const [operation, stats] of Object.entries(summary)) {
      const operationStats = stats as any;
      
      if (operationStats.p95 > 2000) {
        recommendations.push(
          `${operation} is slow (p95: ${operationStats.p95}ms). Consider optimization.`
        );
      }
      
      if (operationStats.max > 5000) {
        recommendations.push(
          `${operation} has timeout issues (max: ${operationStats.max}ms).`
        );
      }
    }
    
    // Cache recommendations
    const cacheHitRate = this.calculateCacheHitRate();
    if (cacheHitRate < 0.3) {
      recommendations.push(
        `Low cache hit rate (${(cacheHitRate * 100).toFixed(1)}%). Consider increasing cache TTL.`
      );
    }
    
    return recommendations;
  }

  private calculateCacheHitRate(): number {
    const cacheMetrics = this.performanceBuffer.filter(
      m => m.operationName === 'cache_hit' || m.operationName === 'cache_miss'
    );
    
    if (cacheMetrics.length === 0) return 0;
    
    const hits = cacheMetrics.filter(m => m.cacheHit === true).length;
    return hits / cacheMetrics.length;
  }

  private async initializeOfflineSupport(): Promise<void> {
    // Load offline queue
    try {
      const stored = await AsyncStorage.getItem('@voice_offline_queue');
      if (stored) {
        this.offlineQueue = JSON.parse(stored);
      }
    } catch (error) {
      logger.error('Failed to load offline queue:', error);
    }
    
    // Monitor network state
    NetInfo.addEventListener(state => {
      if (state.isConnected && this.offlineQueue.length > 0) {
        this.processOfflineQueue();
      }
    });
  }

  private async loadPersistedCache(): Promise<void> {
    try {
      const keys = await AsyncStorage.getAllKeys();
      const cacheKeys = keys.filter(k => k.startsWith('@voice_cache:'));
      
      for (const key of cacheKeys) {
        const value = await AsyncStorage.getItem(key);
        if (value) {
          const cacheKey = key.replace('@voice_cache:', '');
          const entry = JSON.parse(value);
          
          // Only restore if not expired
          if (Date.now() - entry.timestamp <= entry.ttl) {
            this.cache.set(cacheKey, entry);
          } else {
            // Clean up expired entry
            await AsyncStorage.removeItem(key);
          }
        }
      }
    } catch (error) {
      logger.error('Failed to load persisted cache:', error);
    }
  }

  private async persistCache(): Promise<void> {
    // Persist current cache state
    const promises: Promise<void>[] = [];
    
    for (const [key, entry] of this.cache.entries()) {
      if (entry.ttl > 300000) { // Only persist long-lived entries
        promises.push(
          AsyncStorage.setItem(
            `@voice_cache:${key}`,
            JSON.stringify(entry)
          )
        );
      }
    }
    
    await Promise.all(promises);
  }

  private startPerformanceMonitoring(): void {
    // Regular performance check
    setInterval(() => {
      const report = this.getPerformanceReport();
      
      if (report.recommendations.length > 0) {
        this.emit('performanceReport', report);
      }
      
      // Auto-optimize based on metrics
      this.autoOptimize(report.summary);
    }, 60000); // Every minute
  }

  private autoOptimize(summary: any): void {
    // Adjust cache TTL based on performance
    const avgResponseTime = summary.VOICE_PROCESSING?.avg || 0;
    
    if (avgResponseTime > 3000) {
      // Slow responses - increase caching
      this.CACHE_CONFIG.DEFAULT_TTL = Math.min(
        this.CACHE_CONFIG.DEFAULT_TTL * 1.5,
        3600000 // Max 1 hour
      );
    } else if (avgResponseTime < 1000) {
      // Fast responses - can reduce caching
      this.CACHE_CONFIG.DEFAULT_TTL = Math.max(
        this.CACHE_CONFIG.DEFAULT_TTL * 0.8,
        60000 // Min 1 minute
      );
    }
  }

  private async processOfflineOperation(item: any): Promise<void> {
    // Implementation depends on operation type
    // This is a placeholder for specific offline operation handling
    logger.debug('Processing offline operation:', item);
  }
}

// Export singleton instance
export const voicePerformanceOptimizer = new VoicePerformanceOptimizer();
export default voicePerformanceOptimizer;