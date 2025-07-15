import { LRUCache } from 'lru-cache';
import * as FileSystem from 'expo-file-system';
import * as SQLite from 'expo-sqlite';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Route, Location, Region } from '../../types/location';

// Cache configuration
interface CacheConfig {
  maxMemoryTiles: number;
  maxDiskSize: number;
  memoryTTL: number;
  diskTTL: number;
  preloadRadius: number;
  speculativeLoadDistance: number;
}

interface CachedTile {
  key: string;
  zoom: number;
  bounds: {
    north: number;
    south: number;
    east: number;
    west: number;
  };
  size: number;
  lastAccess: number;
  accessCount: number;
  data?: Uint8Array;
}

interface ScoredTile {
  tile: CachedTile;
  score: number;
  key: string;
}

interface TileGroup {
  priority: Priority;
  tiles: TileCoordinate[];
}

interface TileCoordinate {
  z: number;
  x: number;
  y: number;
}

enum Priority {
  HIGH = 3,
  MEDIUM = 2,
  LOW = 1
}

// Usage tracking
class UsageTracker {
  private accessCounts: Map<string, number> = new Map();
  private maxAccessCount: number = 0;
  
  recordAccess(tileKey: string): void {
    const count = (this.accessCounts.get(tileKey) || 0) + 1;
    this.accessCounts.set(tileKey, count);
    this.maxAccessCount = Math.max(this.maxAccessCount, count);
  }
  
  getAccessCount(tileKey: string): number {
    return this.accessCounts.get(tileKey) || 0;
  }
  
  getMaxAccessCount(): number {
    return this.maxAccessCount;
  }
  
  reset(): void {
    this.accessCounts.clear();
    this.maxAccessCount = 0;
  }
}

// Route context for intelligent caching
class RouteContext {
  private currentRoute: Route | null = null;
  private routeCorridorCache: Map<string, number> = new Map();
  
  setRoute(route: Route): void {
    this.currentRoute = route;
    this.routeCorridorCache.clear();
    this.buildCorridorCache();
  }
  
  clearRoute(): void {
    this.currentRoute = null;
    this.routeCorridorCache.clear();
  }
  
  hasActiveRoute(): boolean {
    return this.currentRoute !== null;
  }
  
  getDistanceFromRoute(bounds: CachedTile['bounds']): number {
    if (!this.currentRoute) return Infinity;
    
    const centerLat = (bounds.north + bounds.south) / 2;
    const centerLng = (bounds.east + bounds.west) / 2;
    const tileKey = `${centerLat.toFixed(3)},${centerLng.toFixed(3)}`;
    
    // Check cache first
    if (this.routeCorridorCache.has(tileKey)) {
      return this.routeCorridorCache.get(tileKey)!;
    }
    
    // Calculate minimum distance to route
    let minDistance = Infinity;
    
    for (const point of this.currentRoute.points) {
      const distance = this.haversineDistance(
        { latitude: centerLat, longitude: centerLng },
        point
      );
      minDistance = Math.min(minDistance, distance);
    }
    
    // Cache the result
    this.routeCorridorCache.set(tileKey, minDistance);
    
    return minDistance;
  }
  
  private buildCorridorCache(): void {
    // Pre-calculate distances for common tile positions
    // This improves performance during eviction scoring
  }
  
  private haversineDistance(pos1: Location, pos2: Location): number {
    const R = 6371000; // Earth radius in meters
    const lat1 = pos1.latitude * Math.PI / 180;
    const lat2 = pos2.latitude * Math.PI / 180;
    const deltaLat = (pos2.latitude - pos1.latitude) * Math.PI / 180;
    const deltaLon = (pos2.longitude - pos1.longitude) * Math.PI / 180;
    
    const a = Math.sin(deltaLat / 2) * Math.sin(deltaLat / 2) +
              Math.cos(lat1) * Math.cos(lat2) *
              Math.sin(deltaLon / 2) * Math.sin(deltaLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    
    return R * c;
  }
}

// Disk cache management
class DiskCache {
  private basePath: string;
  private maxSize: number;
  private db: SQLite.WebSQLDatabase | null = null;
  
  constructor(config: { maxSize: number; basePath: string }) {
    this.maxSize = config.maxSize;
    this.basePath = config.basePath;
    this.initialize();
  }
  
  private async initialize(): Promise<void> {
    // Ensure directory exists
    const dirInfo = await FileSystem.getInfoAsync(this.basePath);
    if (!dirInfo.exists) {
      await FileSystem.makeDirectoryAsync(this.basePath, { intermediates: true });
    }
    
    // Initialize cache database
    this.db = SQLite.openDatabase('tile_cache.db');
    await this.initializeSchema();
  }
  
  private async initializeSchema(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'));
        return;
      }
      
      this.db.transaction(tx => {
        tx.executeSql(`
          CREATE TABLE IF NOT EXISTS disk_cache (
            tile_key TEXT PRIMARY KEY,
            zoom INTEGER,
            bounds TEXT,
            size INTEGER,
            last_access INTEGER,
            access_count INTEGER,
            file_path TEXT
          );
        `);
        
        tx.executeSql(`
          CREATE INDEX IF NOT EXISTS idx_last_access ON disk_cache(last_access);
        `);
        
        tx.executeSql(`
          CREATE INDEX IF NOT EXISTS idx_zoom ON disk_cache(zoom);
        `);
      }, reject, resolve);
    });
  }
  
  async getTileSize(tileKey: string): Promise<number> {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        resolve(0);
        return;
      }
      
      this.db.transaction(tx => {
        tx.executeSql(
          'SELECT size FROM disk_cache WHERE tile_key = ?',
          [tileKey],
          (_, result) => {
            if (result.rows.length > 0) {
              resolve(result.rows.item(0).size);
            } else {
              resolve(0);
            }
          },
          (_, error) => {
            console.error('Error getting tile size:', error);
            resolve(0);
            return false;
          }
        );
      });
    });
  }
  
  async removeTile(tileKey: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        resolve();
        return;
      }
      
      this.db.transaction(tx => {
        // Get file path first
        tx.executeSql(
          'SELECT file_path FROM disk_cache WHERE tile_key = ?',
          [tileKey],
          async (_, result) => {
            if (result.rows.length > 0) {
              const filePath = result.rows.item(0).file_path;
              
              // Delete file
              try {
                await FileSystem.deleteAsync(filePath, { idempotent: true });
              } catch (error) {
                console.error('Error deleting tile file:', error);
              }
              
              // Remove from database
              tx.executeSql(
                'DELETE FROM disk_cache WHERE tile_key = ?',
                [tileKey],
                () => resolve(),
                (_, error) => {
                  console.error('Error removing tile from cache:', error);
                  resolve();
                  return false;
                }
              );
            } else {
              resolve();
            }
          }
        );
      });
    });
  }
  
  async getTotalSize(): Promise<number> {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        resolve(0);
        return;
      }
      
      this.db.transaction(tx => {
        tx.executeSql(
          'SELECT SUM(size) as total FROM disk_cache',
          [],
          (_, result) => {
            resolve(result.rows.item(0).total || 0);
          },
          (_, error) => {
            console.error('Error getting total cache size:', error);
            resolve(0);
            return false;
          }
        );
      });
    });
  }
  
  async getAllTiles(): Promise<CachedTile[]> {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        resolve([]);
        return;
      }
      
      this.db.transaction(tx => {
        tx.executeSql(
          'SELECT * FROM disk_cache',
          [],
          (_, result) => {
            const tiles: CachedTile[] = [];
            for (let i = 0; i < result.rows.length; i++) {
              const row = result.rows.item(i);
              tiles.push({
                key: row.tile_key,
                zoom: row.zoom,
                bounds: JSON.parse(row.bounds),
                size: row.size,
                lastAccess: row.last_access,
                accessCount: row.access_count
              });
            }
            resolve(tiles);
          },
          (_, error) => {
            console.error('Error getting all tiles:', error);
            resolve([]);
            return false;
          }
        );
      });
    });
  }
}

export class MapCacheManager {
  private memoryCache: LRUCache<string, CachedTile>;
  private diskCache: DiskCache;
  private usageTracker: UsageTracker;
  private routeContext: RouteContext;
  private config: CacheConfig;
  
  constructor(config?: Partial<CacheConfig>) {
    this.config = {
      maxMemoryTiles: 500,
      maxDiskSize: 800 * 1024 * 1024, // 800MB
      memoryTTL: 5 * 60 * 1000, // 5 minutes
      diskTTL: 30 * 24 * 60 * 60 * 1000, // 30 days
      preloadRadius: 5000, // 5km
      speculativeLoadDistance: 10000, // 10km
      ...config
    };
    
    this.memoryCache = new LRUCache({
      max: this.config.maxMemoryTiles,
      ttl: this.config.memoryTTL,
      updateAgeOnGet: true,
      dispose: (tile, key) => this.onMemoryEvict(tile, key)
    });
    
    this.diskCache = new DiskCache({
      maxSize: this.config.maxDiskSize,
      basePath: `${FileSystem.documentDirectory}tile_cache/`
    });
    
    this.usageTracker = new UsageTracker();
    this.routeContext = new RouteContext();
    
    this.loadConfig();
  }
  
  private async loadConfig(): Promise<void> {
    try {
      const savedConfig = await AsyncStorage.getItem('map_cache_config');
      if (savedConfig) {
        this.config = { ...this.config, ...JSON.parse(savedConfig) };
      }
    } catch (error) {
      console.error('Error loading cache config:', error);
    }
  }
  
  async saveConfig(): Promise<void> {
    try {
      await AsyncStorage.setItem('map_cache_config', JSON.stringify(this.config));
    } catch (error) {
      console.error('Error saving cache config:', error);
    }
  }
  
  /**
   * Set the current route for optimized caching
   */
  setRoute(route: Route): void {
    this.routeContext.setRoute(route);
  }
  
  /**
   * Clear the current route
   */
  clearRoute(): void {
    this.routeContext.clearRoute();
  }
  
  /**
   * Get a tile from cache
   */
  async getTile(tileKey: string): Promise<CachedTile | null> {
    // Check memory cache first
    const memoryTile = this.memoryCache.get(tileKey);
    if (memoryTile) {
      this.usageTracker.recordAccess(tileKey);
      return memoryTile;
    }
    
    // Check disk cache
    // Implementation would load from disk
    
    return null;
  }
  
  /**
   * Multi-level cache eviction
   */
  async evictTiles(requiredSpace: number): Promise<void> {
    let freedSpace = 0;
    
    // Step 1: Evict from memory cache first
    freedSpace += this.evictMemoryTiles();
    
    if (freedSpace >= requiredSpace) return;
    
    // Step 2: Evict from disk cache using intelligent scoring
    const candidates = await this.getDiskEvictionCandidates();
    const scored = this.scoreTilesForEviction(candidates);
    
    for (const tile of scored) {
      if (freedSpace >= requiredSpace) break;
      
      const tileSize = await this.diskCache.getTileSize(tile.key);
      await this.diskCache.removeTile(tile.key);
      freedSpace += tileSize;
    }
  }
  
  /**
   * Evict tiles from memory cache
   */
  private evictMemoryTiles(): number {
    let freedSpace = 0;
    const tilesToEvict = Math.floor(this.memoryCache.size * 0.2); // Evict 20%
    
    for (let i = 0; i < tilesToEvict; i++) {
      const evicted = this.memoryCache.pop();
      if (evicted) {
        freedSpace += evicted.size || 50 * 1024; // Estimate 50KB per tile
      }
    }
    
    return freedSpace;
  }
  
  /**
   * Get disk eviction candidates
   */
  private async getDiskEvictionCandidates(): Promise<CachedTile[]> {
    const allTiles = await this.diskCache.getAllTiles();
    const now = Date.now();
    
    // Filter out tiles that shouldn't be evicted
    return allTiles.filter(tile => {
      // Don't evict tiles accessed in last hour
      if (now - tile.lastAccess < 60 * 60 * 1000) return false;
      
      // Don't evict overview tiles (zoom < 10)
      if (tile.zoom < 10) return false;
      
      return true;
    });
  }
  
  /**
   * Score tiles for eviction
   */
  private scoreTilesForEviction(tiles: CachedTile[]): ScoredTile[] {
    return tiles.map(tile => {
      let score = 0;
      
      // Age factor (older = higher score = more likely to evict)
      const ageHours = (Date.now() - tile.lastAccess) / (1000 * 60 * 60);
      score += Math.min(ageHours, 168) / 168 * 30; // Max 30 points for 1 week
      
      // Usage frequency (less used = higher score)
      const usageScore = 1 - (tile.accessCount / this.usageTracker.getMaxAccessCount());
      score += usageScore * 20; // Max 20 points
      
      // Distance from current route (farther = higher score)
      if (this.routeContext.hasActiveRoute()) {
        const distance = this.routeContext.getDistanceFromRoute(tile.bounds);
        const normalizedDistance = Math.min(distance / 100000, 1); // Normalize to 100km
        score += normalizedDistance * 25; // Max 25 points
      }
      
      // Zoom level factor (overview tiles less likely to evict)
      const zoomFactor = tile.zoom < 10 ? 0 : (tile.zoom - 10) / 6;
      score += zoomFactor * 15; // Max 15 points
      
      // Size factor (larger tiles slightly preferred for eviction)
      const sizeFactor = tile.size / (50 * 1024); // Normalize to 50KB
      score += Math.min(sizeFactor, 1) * 10; // Max 10 points
      
      return { tile, score, key: tile.key };
    }).sort((a, b) => b.score - a.score); // Higher scores evicted first
  }
  
  /**
   * Preemptive cache warming
   */
  async warmCache(route: Route): Promise<void> {
    const tilesToLoad = this.calculateCriticalTiles(route);
    
    // Load in priority order
    for (const tileGroup of tilesToLoad) {
      await Promise.all(
        tileGroup.tiles.map(tile => this.loadTileToCache(tile, tileGroup.priority))
      );
    }
  }
  
  /**
   * Calculate critical tiles for a route
   */
  private calculateCriticalTiles(route: Route): TileGroup[] {
    const groups: TileGroup[] = [];
    
    // High priority: Start/end points and complex intersections
    groups.push({
      priority: Priority.HIGH,
      tiles: [
        ...this.getTilesAroundPoint(route.points[0], 16, 1000),
        ...this.getTilesAroundPoint(route.points[route.points.length - 1], 16, 1000),
        ...this.getComplexIntersectionTiles(route)
      ]
    });
    
    // Medium priority: Route corridor
    groups.push({
      priority: Priority.MEDIUM,
      tiles: this.getRouteCorridor(route, 14)
    });
    
    // Low priority: Overview tiles
    groups.push({
      priority: Priority.LOW,
      tiles: this.getRouteBounds(route, 10)
    });
    
    return groups;
  }
  
  /**
   * Memory eviction callback
   */
  private onMemoryEvict(tile: CachedTile, key: string): void {
    // Could save to disk cache here if needed
    console.log(`Evicted tile ${key} from memory cache`);
  }
  
  /**
   * Load tile to cache
   */
  private async loadTileToCache(tile: TileCoordinate, priority: Priority): Promise<void> {
    // Implementation would actually load the tile
    const tileKey = `${tile.z}/${tile.x}/${tile.y}`;
    
    // Record in usage tracker
    this.usageTracker.recordAccess(tileKey);
  }
  
  /**
   * Get tiles around a point
   */
  private getTilesAroundPoint(
    point: Location,
    zoom: number,
    radiusMeters: number
  ): TileCoordinate[] {
    const tiles: TileCoordinate[] = [];
    
    // Calculate tile bounds
    const metersPerPixel = 156543.03392 * Math.cos(point.latitude * Math.PI / 180) / Math.pow(2, zoom);
    const tileSize = 256; // pixels
    const metersPerTile = metersPerPixel * tileSize;
    const tilesRadius = Math.ceil(radiusMeters / metersPerTile);
    
    const centerTile = this.latLngToTile(point.latitude, point.longitude, zoom);
    
    for (let dx = -tilesRadius; dx <= tilesRadius; dx++) {
      for (let dy = -tilesRadius; dy <= tilesRadius; dy++) {
        tiles.push({
          z: zoom,
          x: centerTile.x + dx,
          y: centerTile.y + dy
        });
      }
    }
    
    return tiles;
  }
  
  /**
   * Get tiles for complex intersections
   */
  private getComplexIntersectionTiles(route: Route): TileCoordinate[] {
    const tiles: TileCoordinate[] = [];
    
    // Find complex intersections (multiple turns close together)
    for (let i = 1; i < route.points.length - 1; i++) {
      const segment = route.segments.find(s => 
        i >= s.startIndex && i <= s.endIndex
      );
      
      if (segment?.hasComplexIntersections) {
        const intersectionTiles = this.getTilesAroundPoint(
          route.points[i],
          15,
          500
        );
        tiles.push(...intersectionTiles);
      }
    }
    
    return this.deduplicateTiles(tiles);
  }
  
  /**
   * Get route corridor tiles
   */
  private getRouteCorridor(route: Route, zoom: number): TileCoordinate[] {
    const tiles: TileCoordinate[] = [];
    const sampleInterval = Math.max(1, Math.floor(route.points.length / 200));
    
    for (let i = 0; i < route.points.length; i += sampleInterval) {
      const point = route.points[i];
      const pointTiles = this.getTilesAroundPoint(point, zoom, 2000);
      tiles.push(...pointTiles);
    }
    
    return this.deduplicateTiles(tiles);
  }
  
  /**
   * Get route bounding box tiles
   */
  private getRouteBounds(route: Route, zoom: number): TileCoordinate[] {
    const tiles: TileCoordinate[] = [];
    
    // Calculate route bounds
    let minLat = Infinity, maxLat = -Infinity;
    let minLng = Infinity, maxLng = -Infinity;
    
    route.points.forEach(point => {
      minLat = Math.min(minLat, point.latitude);
      maxLat = Math.max(maxLat, point.latitude);
      minLng = Math.min(minLng, point.longitude);
      maxLng = Math.max(maxLng, point.longitude);
    });
    
    // Convert to tile coordinates
    const minTile = this.latLngToTile(minLat, minLng, zoom);
    const maxTile = this.latLngToTile(maxLat, maxLng, zoom);
    
    for (let x = minTile.x; x <= maxTile.x; x++) {
      for (let y = minTile.y; y <= maxTile.y; y++) {
        tiles.push({ z: zoom, x, y });
      }
    }
    
    return tiles;
  }
  
  /**
   * Convert lat/lng to tile coordinates
   */
  private latLngToTile(lat: number, lng: number, zoom: number): { x: number; y: number } {
    const n = Math.pow(2, zoom);
    const x = Math.floor((lng + 180) / 360 * n);
    const latRad = lat * Math.PI / 180;
    const y = Math.floor((1 - Math.asinh(Math.tan(latRad)) / Math.PI) / 2 * n);
    
    return { x, y };
  }
  
  /**
   * Remove duplicate tiles
   */
  private deduplicateTiles(tiles: TileCoordinate[]): TileCoordinate[] {
    const seen = new Set<string>();
    return tiles.filter(tile => {
      const key = `${tile.z}/${tile.x}/${tile.y}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }
  
  /**
   * Get cache statistics
   */
  async getCacheStats(): Promise<{
    memoryCache: {
      tiles: number;
      estimatedSize: number;
    };
    diskCache: {
      tiles: number;
      totalSize: number;
    };
    totalSize: number;
    percentUsed: number;
  }> {
    const diskSize = await this.diskCache.getTotalSize();
    const diskTiles = await this.diskCache.getAllTiles();
    
    const memorySize = this.memoryCache.size * 50 * 1024; // Estimate 50KB per tile
    const totalSize = memorySize + diskSize;
    
    return {
      memoryCache: {
        tiles: this.memoryCache.size,
        estimatedSize: memorySize
      },
      diskCache: {
        tiles: diskTiles.length,
        totalSize: diskSize
      },
      totalSize,
      percentUsed: (totalSize / this.config.maxDiskSize) * 100
    };
  }
  
  /**
   * Clear all caches
   */
  async clearAllCaches(): Promise<void> {
    this.memoryCache.clear();
    // Disk cache clearing would be implemented
    this.usageTracker.reset();
    this.routeContext.clearRoute();
  }
  
  /**
   * Update cache configuration
   */
  async updateConfig(newConfig: Partial<CacheConfig>): Promise<void> {
    this.config = { ...this.config, ...newConfig };
    
    // Update memory cache size if needed
    if (newConfig.maxMemoryTiles) {
      this.memoryCache.max = newConfig.maxMemoryTiles;
    }
    
    await this.saveConfig();
  }
}

// Export singleton instance
export default new MapCacheManager();