import { LRUCache } from 'lru-cache';
import * as SQLite from 'expo-sqlite';
import { Region, Location, Route } from '../../types/location';
import MapStorageOptimizer from './MapStorageOptimizer';

import { logger } from '@/services/logger';
// Priority levels for tile loading
export enum Priority {
  IMMEDIATE = 4,
  HIGH = 3,
  MEDIUM = 2,
  LOW = 1
}

// Interfaces
interface TileCoordinate {
  z: number;
  x: number;
  y: number;
}

interface TileLoadRequest {
  tile: TileCoordinate;
  priority: Priority;
  timestamp: number;
}

interface Viewport {
  center: Location;
  zoom: number;
  bounds: {
    north: number;
    south: number;
    east: number;
    west: number;
  };
}

interface MovementVector {
  lat: number;
  lng: number;
  speed: number; // meters per second
}

interface VectorTile {
  data: Uint8Array;
  layers: Map<string, any>;
  extent: number;
}

// Priority queue implementation
class PriorityQueue<T> {
  private heap: Array<{ item: T; priority: number }> = [];
  
  push(item: T, priority: number): void {
    this.heap.push({ item, priority });
    this.heap.sort((a, b) => b.priority - a.priority);
  }
  
  pop(): T | undefined {
    const item = this.heap.shift();
    return item?.item;
  }
  
  get length(): number {
    return this.heap.length;
  }
  
  clear(): void {
    this.heap = [];
  }
}

// Tile visibility tracker
class TileVisibilityTracker {
  private positionHistory: Array<{ position: Location; timestamp: number }> = [];
  private readonly MAX_HISTORY = 10;
  
  updatePosition(position: Location): void {
    const now = Date.now();
    this.positionHistory.push({ position, timestamp: now });
    
    // Keep only recent history
    if (this.positionHistory.length > this.MAX_HISTORY) {
      this.positionHistory.shift();
    }
  }
  
  getMovementVector(): MovementVector {
    if (this.positionHistory.length < 2) {
      return { lat: 0, lng: 0, speed: 0 };
    }
    
    const recent = this.positionHistory[this.positionHistory.length - 1];
    const previous = this.positionHistory[this.positionHistory.length - 2];
    
    const timeDelta = (recent.timestamp - previous.timestamp) / 1000; // seconds
    const latDelta = recent.position.latitude - previous.position.latitude;
    const lngDelta = recent.position.longitude - previous.position.longitude;
    
    // Calculate speed in meters per second
    const distance = this.haversineDistance(recent.position, previous.position);
    const speed = distance / timeDelta;
    
    return {
      lat: latDelta / timeDelta,
      lng: lngDelta / timeDelta,
      speed
    };
  }
  
  getSpeed(): number {
    return this.getMovementVector().speed;
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

export class ProgressiveMapLoader {
  private loadQueue: PriorityQueue<TileLoadRequest>;
  private activeLoads: Map<string, Promise<void>>;
  private tileCache: LRUCache<string, VectorTile>;
  private visibilityTracker: TileVisibilityTracker;
  private db: SQLite.WebSQLDatabase | null = null;
  private currentRoute: Route | null = null;
  private loadBatchSize: number = 10;
  private maxConcurrentLoads: number = 3;
  private onTileLoaded?: (tile: TileCoordinate) => void;
  
  constructor() {
    this.loadQueue = new PriorityQueue();
    this.activeLoads = new Map();
    this.tileCache = new LRUCache({ 
      max: 500, // 500 tiles in memory
      ttl: 5 * 60 * 1000, // 5 minutes TTL
      updateAgeOnGet: true
    });
    this.visibilityTracker = new TileVisibilityTracker();
    this.initializeDatabase();
  }
  
  private async initializeDatabase(): Promise<void> {
    this.db = SQLite.openDatabase('mbtiles.db');
  }
  
  /**
   * Set the current route for optimized loading
   */
  setRoute(route: Route): void {
    this.currentRoute = route;
    // Clear low priority loads when route changes
    this.loadQueue.clear();
    this.preloadRouteOverview();
  }
  
  /**
   * Main progressive loading method
   */
  async loadTilesForView(viewport: Viewport): Promise<void> {
    // Update position tracking
    this.visibilityTracker.updatePosition(viewport.center);
    
    // Phase 1: Load visible tiles immediately
    const visibleTiles = this.calculateVisibleTiles(viewport);
    await this.loadTilesWithPriority(visibleTiles, Priority.IMMEDIATE);
    
    // Phase 2: Preload route tiles if on a route
    if (this.currentRoute) {
      const routeTiles = this.calculateRouteTiles(this.currentRoute, viewport);
      this.scheduleLoadTiles(routeTiles, Priority.HIGH);
    }
    
    // Phase 3: Load surrounding area
    const surroundingTiles = this.calculateSurroundingTiles(viewport, 2);
    this.scheduleLoadTiles(surroundingTiles, Priority.MEDIUM);
    
    // Phase 4: Speculative loading based on movement
    const speculativeTiles = this.predictNextTiles(viewport);
    this.scheduleLoadTiles(speculativeTiles, Priority.LOW);
    
    // Process the queue
    this.processLoadQueue();
  }
  
  /**
   * Load tiles with specific priority
   */
  private async loadTilesWithPriority(
    tiles: TileCoordinate[],
    priority: Priority
  ): Promise<void> {
    const loadPromises: Promise<void>[] = [];
    
    for (const tile of tiles) {
      const tileKey = this.getTileKey(tile);
      
      // Check cache first
      if (this.tileCache.has(tileKey)) {
        continue;
      }
      
      // Check if already loading
      if (this.activeLoads.has(tileKey)) {
        if (priority >= Priority.HIGH) {
          loadPromises.push(this.activeLoads.get(tileKey)!);
        }
        continue;
      }
      
      // Add to load queue with priority
      this.loadQueue.push({ tile, priority, timestamp: Date.now() }, priority);
      
      if (priority === Priority.IMMEDIATE) {
        const loadPromise = this.loadTile(tile);
        this.activeLoads.set(tileKey, loadPromise);
        loadPromises.push(loadPromise);
      }
    }
    
    // Wait for immediate priority tiles
    if (priority === Priority.IMMEDIATE && loadPromises.length > 0) {
      await Promise.all(loadPromises);
    }
  }
  
  /**
   * Schedule tiles for loading
   */
  private scheduleLoadTiles(tiles: TileCoordinate[], priority: Priority): void {
    for (const tile of tiles) {
      const tileKey = this.getTileKey(tile);
      
      // Skip if already cached or loading
      if (this.tileCache.has(tileKey) || this.activeLoads.has(tileKey)) {
        continue;
      }
      
      this.loadQueue.push({ tile, priority, timestamp: Date.now() }, priority);
    }
  }
  
  /**
   * Process the load queue
   */
  private async processLoadQueue(): Promise<void> {
    while (this.loadQueue.length > 0 && this.activeLoads.size < this.maxConcurrentLoads) {
      const request = this.loadQueue.pop();
      if (!request) break;
      
      const tileKey = this.getTileKey(request.tile);
      
      // Skip if already loaded while in queue
      if (this.tileCache.has(tileKey) || this.activeLoads.has(tileKey)) {
        continue;
      }
      
      const loadPromise = this.loadTile(request.tile);
      this.activeLoads.set(tileKey, loadPromise);
      
      // Don't await, let it load in background
      loadPromise.finally(() => {
        this.activeLoads.delete(tileKey);
        // Continue processing queue
        if (this.loadQueue.length > 0) {
          this.processLoadQueue();
        }
      });
    }
  }
  
  /**
   * Load a single tile
   */
  private async loadTile(tile: TileCoordinate): Promise<void> {
    const tileKey = this.getTileKey(tile);
    
    try {
      // Load from MBTiles database
      const tileData = await this.loadTileFromDatabase(tile);
      
      if (tileData) {
        // Decompress
        const decompressed = await MapStorageOptimizer.decompressTile(tileData);
        
        // Parse vector tile
        const vectorTile: VectorTile = {
          data: decompressed,
          layers: new Map(), // Would parse actual vector tile format
          extent: 4096
        };
        
        // Cache in memory
        this.tileCache.set(tileKey, vectorTile);
        
        // Notify that tile is loaded
        if (this.onTileLoaded) {
          this.onTileLoaded(tile);
        }
      }
    } catch (error) {
      logger.error(`Error loading tile ${tileKey}:`, error);
    }
  }
  
  /**
   * Load tile data from database
   */
  private async loadTileFromDatabase(tile: TileCoordinate): Promise<Uint8Array | null> {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'));
        return;
      }
      
      this.db.transaction(tx => {
        // First try the deduplicated table
        tx.executeSql(
          `SELECT td.data 
           FROM tile_refs tr 
           JOIN tile_data td ON tr.data_id = td.id 
           WHERE tr.zoom_level = ? AND tr.tile_column = ? AND tr.tile_row = ?`,
          [tile.z, tile.x, tile.y],
          (_, result) => {
            if (result.rows.length > 0) {
              const data = result.rows.item(0).data;
              resolve(new Uint8Array(data));
            } else {
              // Fallback to standard MBTiles table
              tx.executeSql(
                'SELECT tile_data FROM tiles WHERE zoom_level = ? AND tile_column = ? AND tile_row = ?',
                [tile.z, tile.x, tile.y],
                (_, result) => {
                  if (result.rows.length > 0) {
                    const data = result.rows.item(0).tile_data;
                    resolve(new Uint8Array(data));
                  } else {
                    resolve(null);
                  }
                }
              );
            }
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
   * Calculate visible tiles for viewport
   */
  private calculateVisibleTiles(viewport: Viewport): TileCoordinate[] {
    const tiles: TileCoordinate[] = [];
    const zoom = Math.floor(viewport.zoom);
    
    // Convert bounds to tile coordinates
    const minTile = this.latLngToTile(viewport.bounds.south, viewport.bounds.west, zoom);
    const maxTile = this.latLngToTile(viewport.bounds.north, viewport.bounds.east, zoom);
    
    for (let x = minTile.x; x <= maxTile.x; x++) {
      for (let y = minTile.y; y <= maxTile.y; y++) {
        tiles.push({ z: zoom, x, y });
      }
    }
    
    return tiles;
  }
  
  /**
   * Calculate route tiles near current position
   */
  private calculateRouteTiles(route: Route, viewport: Viewport): TileCoordinate[] {
    if (!route.points || route.points.length === 0) return [];
    
    const tiles: TileCoordinate[] = [];
    const currentPos = viewport.center;
    const zoom = Math.floor(viewport.zoom);
    
    // Find closest point on route
    let closestIndex = 0;
    let minDistance = Infinity;
    
    route.points.forEach((point, index) => {
      const distance = this.calculateDistance(currentPos, point);
      if (distance < minDistance) {
        minDistance = distance;
        closestIndex = index;
      }
    });
    
    // Load tiles ahead on the route
    const lookaheadPoints = 50; // Look ahead 50 points
    const startIndex = closestIndex;
    const endIndex = Math.min(closestIndex + lookaheadPoints, route.points.length - 1);
    
    for (let i = startIndex; i <= endIndex; i += 5) { // Sample every 5th point
      const point = route.points[i];
      const pointTile = this.latLngToTile(point.latitude, point.longitude, zoom);
      
      // Add tile and surrounding tiles
      for (let dx = -1; dx <= 1; dx++) {
        for (let dy = -1; dy <= 1; dy++) {
          tiles.push({
            z: zoom,
            x: pointTile.x + dx,
            y: pointTile.y + dy
          });
        }
      }
    }
    
    // Remove duplicates
    return this.deduplicateTiles(tiles);
  }
  
  /**
   * Calculate surrounding tiles
   */
  private calculateSurroundingTiles(viewport: Viewport, radius: number): TileCoordinate[] {
    const tiles: TileCoordinate[] = [];
    const zoom = Math.floor(viewport.zoom);
    const centerTile = this.latLngToTile(viewport.center.latitude, viewport.center.longitude, zoom);
    
    for (let dx = -radius; dx <= radius; dx++) {
      for (let dy = -radius; dy <= radius; dy++) {
        // Skip tiles already in viewport
        if (Math.abs(dx) <= 1 && Math.abs(dy) <= 1) continue;
        
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
   * Predict next tiles based on movement
   */
  private predictNextTiles(viewport: Viewport): TileCoordinate[] {
    const movement = this.visibilityTracker.getMovementVector();
    const speed = movement.speed;
    
    // Don't predict if not moving or moving slowly
    if (speed < 2) { // Less than 2 m/s
      return [];
    }
    
    const tiles: TileCoordinate[] = [];
    const zoom = Math.floor(viewport.zoom);
    
    // Predict position in 5 seconds
    const predictTime = 5; // seconds
    const futurePosition: Location = {
      latitude: viewport.center.latitude + (movement.lat * predictTime),
      longitude: viewport.center.longitude + (movement.lng * predictTime)
    };
    
    // Calculate tiles for predicted position
    const futureTile = this.latLngToTile(futurePosition.latitude, futurePosition.longitude, zoom);
    
    // Get tiles in direction of movement
    const radius = Math.min(5, Math.floor(speed / 10)); // Radius based on speed
    
    for (let i = 1; i <= radius; i++) {
      const dx = Math.sign(movement.lng) * i;
      const dy = Math.sign(movement.lat) * i;
      
      tiles.push({
        z: zoom,
        x: futureTile.x + dx,
        y: futureTile.y + dy
      });
      
      // Add perpendicular tiles for wider coverage
      tiles.push({
        z: zoom,
        x: futureTile.x + dx,
        y: futureTile.y + dy + 1
      });
      tiles.push({
        z: zoom,
        x: futureTile.x + dx,
        y: futureTile.y + dy - 1
      });
    }
    
    return this.deduplicateTiles(tiles);
  }
  
  /**
   * Preload route overview tiles
   */
  private async preloadRouteOverview(): Promise<void> {
    if (!this.currentRoute) return;
    
    // Load overview tiles for the entire route at low zoom
    const overviewZoom = 10;
    const routeTiles: TileCoordinate[] = [];
    
    // Sample route points
    const sampleInterval = Math.max(1, Math.floor(this.currentRoute.points.length / 100));
    
    for (let i = 0; i < this.currentRoute.points.length; i += sampleInterval) {
      const point = this.currentRoute.points[i];
      const tile = this.latLngToTile(point.latitude, point.longitude, overviewZoom);
      routeTiles.push({ z: overviewZoom, x: tile.x, y: tile.y });
    }
    
    // Remove duplicates and schedule loading
    const uniqueTiles = this.deduplicateTiles(routeTiles);
    this.scheduleLoadTiles(uniqueTiles, Priority.LOW);
  }
  
  /**
   * Get tile from cache
   */
  getTile(tile: TileCoordinate): VectorTile | null {
    const tileKey = this.getTileKey(tile);
    return this.tileCache.get(tileKey) || null;
  }
  
  /**
   * Check if tile is loaded
   */
  isTileLoaded(tile: TileCoordinate): boolean {
    const tileKey = this.getTileKey(tile);
    return this.tileCache.has(tileKey);
  }
  
  /**
   * Set callback for when tiles are loaded
   */
  setOnTileLoaded(callback: (tile: TileCoordinate) => void): void {
    this.onTileLoaded = callback;
  }
  
  /**
   * Clear cache and reset
   */
  clearCache(): void {
    this.tileCache.clear();
    this.loadQueue.clear();
    this.activeLoads.clear();
  }
  
  /**
   * Get cache statistics
   */
  getCacheStats(): {
    cachedTiles: number;
    cacheSize: number;
    queueLength: number;
    activeLoads: number;
  } {
    return {
      cachedTiles: this.tileCache.size,
      cacheSize: this.tileCache.size * 50 * 1024, // Estimate 50KB per tile
      queueLength: this.loadQueue.length,
      activeLoads: this.activeLoads.size
    };
  }
  
  // Helper methods
  private getTileKey(tile: TileCoordinate): string {
    return `${tile.z}/${tile.x}/${tile.y}`;
  }
  
  private latLngToTile(lat: number, lng: number, zoom: number): { x: number; y: number } {
    const n = Math.pow(2, zoom);
    const x = Math.floor((lng + 180) / 360 * n);
    const latRad = lat * Math.PI / 180;
    const y = Math.floor((1 - Math.asinh(Math.tan(latRad)) / Math.PI) / 2 * n);
    
    return { x, y };
  }
  
  private calculateDistance(pos1: Location, pos2: Location): number {
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
  
  private deduplicateTiles(tiles: TileCoordinate[]): TileCoordinate[] {
    const seen = new Set<string>();
    return tiles.filter(tile => {
      const key = this.getTileKey(tile);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }
}

// Export singleton instance
export default new ProgressiveMapLoader();