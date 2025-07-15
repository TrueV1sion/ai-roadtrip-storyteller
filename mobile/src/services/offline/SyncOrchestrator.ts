/**
 * Sync Orchestrator Service
 * Intelligently manages offline data synchronization
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import NetInfo from '@react-native-community/netinfo';
import { mapTileManager, TileRegion } from './MapTileManager';
import { offlineRoutingService } from './OfflineRoutingService';
import { storyPreGenerator } from './StoryPreGenerator';
import { offlineManager } from '../OfflineManager';
import { performanceMonitor } from '../performanceMonitor';
import { Route } from '../../types/location';

interface SyncTask {
  id: string;
  type: 'maps' | 'routing' | 'stories' | 'voice';
  priority: number;
  routeId: string;
  region?: TileRegion;
  status: 'pending' | 'syncing' | 'completed' | 'failed';
  progress: number;
  createdAt: Date;
  startedAt?: Date;
  completedAt?: Date;
  error?: string;
  retryCount: number;
  estimatedSize: number;
}

interface SyncPolicy {
  wifiOnly: boolean;
  batterySaverMode: boolean;
  backgroundSync: boolean;
  autoSync: boolean;
  maxStorageGB: number;
  syncWindow: {
    start: number; // Hour in 24h format
    end: number;
  };
}

interface SyncStatus {
  isActive: boolean;
  currentTask: SyncTask | null;
  queuedTasks: number;
  completedTasks: number;
  failedTasks: number;
  totalProgress: number;
  estimatedTimeRemaining: number;
  dataUsage: {
    session: number;
    total: number;
  };
}

interface NetworkConditions {
  type: 'wifi' | 'cellular' | 'none';
  effectiveType: '2g' | '3g' | '4g' | '5g' | 'unknown';
  isExpensive: boolean;
  details: {
    isConnected: boolean;
    isInternetReachable: boolean;
    strength?: number;
  };
}

class SyncOrchestrator {
  private static instance: SyncOrchestrator;
  private syncQueue: Map<string, SyncTask> = new Map();
  private activeSyncs: Map<string, SyncTask> = new Map();
  private syncPolicy: SyncPolicy;
  private isSyncing: boolean = false;
  private currentNetworkConditions: NetworkConditions | null = null;
  private syncInterval: NodeJS.Timeout | null = null;
  private dataUsageSession: number = 0;
  private readonly maxConcurrentSyncs = 3;
  private readonly maxRetries = 3;
  
  private constructor() {
    this.syncPolicy = this.getDefaultPolicy();
    this.initialize();
  }
  
  static getInstance(): SyncOrchestrator {
    if (!SyncOrchestrator.instance) {
      SyncOrchestrator.instance = new SyncOrchestrator();
    }
    return SyncOrchestrator.instance;
  }
  
  /**
   * Initialize sync orchestrator
   */
  private async initialize(): Promise<void> {
    // Load saved policy
    await this.loadSyncPolicy();
    
    // Monitor network conditions
    this.setupNetworkMonitoring();
    
    // Setup periodic sync check
    this.setupPeriodicSync();
    
    // Load pending tasks
    await this.loadPendingTasks();
  }
  
  /**
   * Sync offline data for a route
   */
  async syncRouteData(route: Route, options?: Partial<{
    mapsOnly: boolean;
    storiesOnly: boolean;
    priority: number;
  }>): Promise<string> {
    const syncId = `sync_${route.id}_${Date.now()}`;
    
    // Create sync tasks
    const tasks: SyncTask[] = [];
    
    if (!options?.storiesOnly) {
      // Map tiles task
      const mapRegion = await this.createRegionFromRoute(route);
      tasks.push({
        id: `${syncId}_maps`,
        type: 'maps',
        priority: options?.priority || 5,
        routeId: route.id,
        region: mapRegion,
        status: 'pending',
        progress: 0,
        createdAt: new Date(),
        retryCount: 0,
        estimatedSize: await this.estimateMapSize(mapRegion)
      });
      
      // Routing data task
      tasks.push({
        id: `${syncId}_routing`,
        type: 'routing',
        priority: (options?.priority || 5) + 1, // Higher priority than maps
        routeId: route.id,
        status: 'pending',
        progress: 0,
        createdAt: new Date(),
        retryCount: 0,
        estimatedSize: 50 * 1024 * 1024 // Estimate 50MB
      });
    }
    
    if (!options?.mapsOnly) {
      // Stories task
      tasks.push({
        id: `${syncId}_stories`,
        type: 'stories',
        priority: (options?.priority || 5) - 1, // Lower priority
        routeId: route.id,
        status: 'pending',
        progress: 0,
        createdAt: new Date(),
        retryCount: 0,
        estimatedSize: 100 * 1024 * 1024 // Estimate 100MB
      });
    }
    
    // Add tasks to queue
    for (const task of tasks) {
      this.syncQueue.set(task.id, task);
    }
    
    // Save pending tasks
    await this.savePendingTasks();
    
    // Start sync if conditions allow
    this.checkAndStartSync();
    
    performanceMonitor.logEvent('sync_requested', {
      syncId,
      routeId: route.id,
      taskCount: tasks.length,
      totalEstimatedSize: tasks.reduce((sum, t) => sum + t.estimatedSize, 0)
    });
    
    return syncId;
  }
  
  /**
   * Check conditions and start sync if appropriate
   */
  private async checkAndStartSync(): Promise<void> {
    // Check if already syncing
    if (this.isSyncing || this.activeSyncs.size >= this.maxConcurrentSyncs) {
      return;
    }
    
    // Check network conditions
    if (!this.isNetworkSuitable()) {
      console.log('Network conditions not suitable for sync');
      return;
    }
    
    // Check battery
    if (!(await this.isBatterySuitable())) {
      console.log('Battery conditions not suitable for sync');
      return;
    }
    
    // Check time window
    if (!this.isInSyncWindow()) {
      console.log('Outside sync time window');
      return;
    }
    
    // Check storage
    if (!(await this.hasEnoughStorage())) {
      console.log('Insufficient storage for sync');
      return;
    }
    
    // Start syncing
    this.startNextSync();
  }
  
  /**
   * Start next sync task
   */
  private async startNextSync(): Promise<void> {
    // Get highest priority pending task
    const nextTask = this.getNextTask();
    if (!nextTask) {
      this.isSyncing = false;
      return;
    }
    
    this.isSyncing = true;
    nextTask.status = 'syncing';
    nextTask.startedAt = new Date();
    this.activeSyncs.set(nextTask.id, nextTask);
    
    // Notify sync started
    this.notifySyncStatus();
    
    try {
      // Execute sync based on type
      switch (nextTask.type) {
        case 'maps':
          await this.syncMapTiles(nextTask);
          break;
        case 'routing':
          await this.syncRoutingData(nextTask);
          break;
        case 'stories':
          await this.syncStories(nextTask);
          break;
        case 'voice':
          await this.syncVoiceData(nextTask);
          break;
      }
      
      // Mark as completed
      nextTask.status = 'completed';
      nextTask.completedAt = new Date();
      nextTask.progress = 100;
      
      performanceMonitor.logEvent('sync_task_completed', {
        taskId: nextTask.id,
        type: nextTask.type,
        duration: nextTask.completedAt.getTime() - nextTask.startedAt!.getTime(),
        dataUsed: this.dataUsageSession
      });
      
    } catch (error) {
      console.error('Sync task failed:', error);
      nextTask.status = 'failed';
      nextTask.error = error.message;
      nextTask.retryCount++;
      
      // Re-queue if retries available
      if (nextTask.retryCount < this.maxRetries) {
        nextTask.status = 'pending';
        this.syncQueue.set(nextTask.id, nextTask);
      }
    } finally {
      // Clean up
      this.activeSyncs.delete(nextTask.id);
      this.syncQueue.delete(nextTask.id);
      await this.savePendingTasks();
      
      // Continue with next task
      if (this.activeSyncs.size < this.maxConcurrentSyncs) {
        this.startNextSync();
      }
    }
  }
  
  /**
   * Sync map tiles
   */
  private async syncMapTiles(task: SyncTask): Promise<void> {
    if (!task.region) {
      throw new Error('No region defined for map sync');
    }
    
    // Monitor progress
    const progressCallback = (progress: any) => {
      task.progress = (progress.downloadedTiles / progress.totalTiles) * 100;
      this.dataUsageSession += progress.sizeBytes - (task.estimatedSize * (task.progress / 100));
      this.notifySyncProgress(task);
    };
    
    // Start download
    await mapTileManager.downloadRegion(task.region);
    
    // Wait for completion
    await new Promise<void>((resolve, reject) => {
      const checkInterval = setInterval(() => {
        const progress = mapTileManager.getDownloadProgress(task.region!.id);
        
        if (!progress) {
          clearInterval(checkInterval);
          reject(new Error('Download progress lost'));
          return;
        }
        
        progressCallback(progress);
        
        if (progress.status === 'completed') {
          clearInterval(checkInterval);
          resolve();
        } else if (progress.status === 'failed') {
          clearInterval(checkInterval);
          reject(new Error('Download failed'));
        }
      }, 1000);
    });
  }
  
  /**
   * Sync routing data
   */
  private async syncRoutingData(task: SyncTask): Promise<void> {
    // Simulate routing data download
    // In production, this would download routing graph data
    const steps = 10;
    for (let i = 0; i < steps; i++) {
      await new Promise(resolve => setTimeout(resolve, 500));
      task.progress = ((i + 1) / steps) * 100;
      this.notifySyncProgress(task);
      
      // Update routing graph
      if (i === steps - 1) {
        // Final update
        await offlineRoutingService.updateRoutingGraph(
          { minLat: -90, maxLat: 90, minLon: -180, maxLon: 180 },
          { nodes: [] } // Would contain actual routing data
        );
      }
    }
  }
  
  /**
   * Sync stories
   */
  private async syncStories(task: SyncTask): Promise<void> {
    // Get route data
    const route = await this.getRoute(task.routeId);
    if (!route) {
      throw new Error('Route not found');
    }
    
    // Start story generation
    await storyPreGenerator.preGenerateStoriesForRoute(route);
    
    // Monitor progress
    await new Promise<void>((resolve, reject) => {
      const checkInterval = setInterval(() => {
        const progress = storyPreGenerator.getGenerationProgress(route.id);
        
        if (!progress) {
          clearInterval(checkInterval);
          reject(new Error('Generation progress lost'));
          return;
        }
        
        task.progress = (progress.generatedPoints / progress.totalPoints) * 100;
        this.notifySyncProgress(task);
        
        if (progress.status === 'completed') {
          clearInterval(checkInterval);
          resolve();
        } else if (progress.status === 'failed') {
          clearInterval(checkInterval);
          reject(new Error('Generation failed'));
        }
      }, 1000);
    });
  }
  
  /**
   * Sync voice data
   */
  private async syncVoiceData(task: SyncTask): Promise<void> {
    // This would download voice personality data
    // For now, simulate progress
    const steps = 5;
    for (let i = 0; i < steps; i++) {
      await new Promise(resolve => setTimeout(resolve, 1000));
      task.progress = ((i + 1) / steps) * 100;
      this.notifySyncProgress(task);
    }
  }
  
  /**
   * Get sync status
   */
  getSyncStatus(): SyncStatus {
    const allTasks = [...this.syncQueue.values(), ...this.activeSyncs.values()];
    const completedTasks = allTasks.filter(t => t.status === 'completed').length;
    const failedTasks = allTasks.filter(t => t.status === 'failed' && t.retryCount >= this.maxRetries).length;
    
    // Calculate total progress
    let totalProgress = 0;
    if (allTasks.length > 0) {
      totalProgress = allTasks.reduce((sum, t) => sum + t.progress, 0) / allTasks.length;
    }
    
    // Estimate time remaining
    let estimatedTimeRemaining = 0;
    this.activeSyncs.forEach(task => {
      if (task.startedAt && task.progress > 0) {
        const elapsed = Date.now() - task.startedAt.getTime();
        const rate = task.progress / elapsed;
        const remaining = (100 - task.progress) / rate;
        estimatedTimeRemaining += remaining;
      }
    });
    
    return {
      isActive: this.isSyncing,
      currentTask: this.activeSyncs.values().next().value || null,
      queuedTasks: this.syncQueue.size,
      completedTasks,
      failedTasks,
      totalProgress,
      estimatedTimeRemaining,
      dataUsage: {
        session: this.dataUsageSession,
        total: this.dataUsageSession // Would track total across sessions
      }
    };
  }
  
  /**
   * Update sync policy
   */
  async updateSyncPolicy(policy: Partial<SyncPolicy>): Promise<void> {
    this.syncPolicy = { ...this.syncPolicy, ...policy };
    await this.saveSyncPolicy();
    
    // Restart sync check
    this.checkAndStartSync();
  }
  
  /**
   * Cancel sync
   */
  async cancelSync(syncId?: string): Promise<void> {
    if (syncId) {
      // Cancel specific sync
      const task = this.activeSyncs.get(syncId) || this.syncQueue.get(syncId);
      if (task) {
        task.status = 'failed';
        task.error = 'Cancelled by user';
        this.activeSyncs.delete(syncId);
        this.syncQueue.delete(syncId);
      }
    } else {
      // Cancel all syncs
      this.activeSyncs.forEach(task => {
        task.status = 'failed';
        task.error = 'Cancelled by user';
      });
      this.activeSyncs.clear();
      this.isSyncing = false;
    }
    
    await this.savePendingTasks();
    this.notifySyncStatus();
  }
  
  /**
   * Clear sync queue
   */
  async clearSyncQueue(): Promise<void> {
    this.syncQueue.clear();
    await this.savePendingTasks();
    this.notifySyncStatus();
  }
  
  // Helper methods
  
  private getDefaultPolicy(): SyncPolicy {
    return {
      wifiOnly: true,
      batterySaverMode: true,
      backgroundSync: true,
      autoSync: true,
      maxStorageGB: 2,
      syncWindow: {
        start: 2, // 2 AM
        end: 6    // 6 AM
      }
    };
  }
  
  private async loadSyncPolicy(): Promise<void> {
    try {
      const saved = await AsyncStorage.getItem('sync_policy');
      if (saved) {
        this.syncPolicy = { ...this.syncPolicy, ...JSON.parse(saved) };
      }
    } catch (error) {
      console.error('Failed to load sync policy:', error);
    }
  }
  
  private async saveSyncPolicy(): Promise<void> {
    try {
      await AsyncStorage.setItem('sync_policy', JSON.stringify(this.syncPolicy));
    } catch (error) {
      console.error('Failed to save sync policy:', error);
    }
  }
  
  private setupNetworkMonitoring(): void {
    NetInfo.addEventListener(state => {
      this.currentNetworkConditions = {
        type: state.type as any,
        effectiveType: state.details?.cellularGeneration || 'unknown',
        isExpensive: state.details?.isConnectionExpensive || false,
        details: {
          isConnected: state.isConnected || false,
          isInternetReachable: state.isInternetReachable || false
        }
      };
      
      // Check sync when network changes
      if (state.isConnected) {
        this.checkAndStartSync();
      }
    });
  }
  
  private setupPeriodicSync(): void {
    // Check every 5 minutes
    this.syncInterval = setInterval(() => {
      if (this.syncPolicy.autoSync) {
        this.checkAndStartSync();
      }
    }, 5 * 60 * 1000);
  }
  
  private isNetworkSuitable(): boolean {
    if (!this.currentNetworkConditions) return false;
    if (!this.currentNetworkConditions.details.isInternetReachable) return false;
    
    if (this.syncPolicy.wifiOnly && this.currentNetworkConditions.type !== 'wifi') {
      return false;
    }
    
    // Don't sync on slow connections
    if (this.currentNetworkConditions.effectiveType === '2g') {
      return false;
    }
    
    return true;
  }
  
  private async isBatterySuitable(): Promise<boolean> {
    if (!this.syncPolicy.batterySaverMode) return true;
    
    // Would check actual battery level
    // For now, return true
    return true;
  }
  
  private isInSyncWindow(): boolean {
    if (!this.syncPolicy.backgroundSync) return true;
    
    const now = new Date();
    const hour = now.getHours();
    
    const { start, end } = this.syncPolicy.syncWindow;
    
    if (start <= end) {
      return hour >= start && hour < end;
    } else {
      // Window crosses midnight
      return hour >= start || hour < end;
    }
  }
  
  private async hasEnoughStorage(): Promise<boolean> {
    // Would check actual storage
    // For now, return true
    return true;
  }
  
  private getNextTask(): SyncTask | null {
    let highestPriority = -1;
    let nextTask: SyncTask | null = null;
    
    for (const task of this.syncQueue.values()) {
      if (task.status === 'pending' && task.priority > highestPriority) {
        highestPriority = task.priority;
        nextTask = task;
      }
    }
    
    return nextTask;
  }
  
  private async createRegionFromRoute(route: Route): Promise<TileRegion> {
    // Calculate bounds
    let minLat = Infinity, maxLat = -Infinity;
    let minLon = Infinity, maxLon = -Infinity;
    
    route.points.forEach(point => {
      minLat = Math.min(minLat, point.latitude);
      maxLat = Math.max(maxLat, point.latitude);
      minLon = Math.min(minLon, point.longitude);
      maxLon = Math.max(maxLon, point.longitude);
    });
    
    // Add buffer
    const buffer = 0.1; // degrees
    
    return {
      id: `route_${route.id}`,
      name: `Route ${route.id}`,
      bounds: {
        minLat: minLat - buffer,
        maxLat: maxLat + buffer,
        minLon: minLon - buffer,
        maxLon: maxLon + buffer
      },
      minZoom: 8,
      maxZoom: 16,
      style: 'standard',
      priority: 5
    };
  }
  
  private async estimateMapSize(region: TileRegion): Promise<number> {
    // Rough estimation based on area and zoom levels
    const area = (region.bounds.maxLat - region.bounds.minLat) * 
                 (region.bounds.maxLon - region.bounds.minLon);
    const zoomLevels = region.maxZoom - region.minZoom + 1;
    
    // Estimate ~500KB per square degree per zoom level
    return area * zoomLevels * 500 * 1024;
  }
  
  private async getRoute(routeId: string): Promise<Route | null> {
    // Would fetch from route storage
    // For now, return null
    return null;
  }
  
  private async loadPendingTasks(): Promise<void> {
    try {
      const saved = await AsyncStorage.getItem('sync_pending_tasks');
      if (saved) {
        const tasks: SyncTask[] = JSON.parse(saved);
        tasks.forEach(task => {
          if (task.status === 'pending') {
            this.syncQueue.set(task.id, task);
          }
        });
      }
    } catch (error) {
      console.error('Failed to load pending tasks:', error);
    }
  }
  
  private async savePendingTasks(): Promise<void> {
    try {
      const tasks = Array.from(this.syncQueue.values());
      await AsyncStorage.setItem('sync_pending_tasks', JSON.stringify(tasks));
    } catch (error) {
      console.error('Failed to save pending tasks:', error);
    }
  }
  
  private notifySyncStatus(): void {
    offlineManager.emit('syncStatusChanged', this.getSyncStatus());
  }
  
  private notifySyncProgress(task: SyncTask): void {
    offlineManager.emit('syncProgress', {
      taskId: task.id,
      type: task.type,
      progress: task.progress,
      routeId: task.routeId
    });
  }
  
  /**
   * Get sync history
   */
  async getSyncHistory(): Promise<SyncTask[]> {
    // Would load from persistent storage
    return [];
  }
  
  /**
   * Clean up old sync data
   */
  async cleanupOldSyncs(): Promise<void> {
    // Would remove old completed/failed tasks
  }
}

// Export singleton instance
export const syncOrchestrator = SyncOrchestrator.getInstance();
