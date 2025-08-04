/**
 * Map Tile Manager
 * Handles offline map tile storage and retrieval
 */

import SQLite from 'react-native-sqlite-storage';
import RNFS from 'react-native-fs';
import { fflate } from 'fflate';
import MapLibreGL from '@maplibre/maplibre-react-native';
import { performanceMonitor } from '../performanceMonitor';
import { offlineManager } from '../OfflineManager';

import { logger } from '@/services/logger';
export interface TileCoordinate {
  z: number; // zoom level
  x: number; // tile column
  y: number; // tile row
}

export interface TileRegion {
  id: string;
  name: string;
  bounds: {
    minLat: number;
    maxLat: number;
    minLon: number;
    maxLon: number;
  };
  minZoom: number;
  maxZoom: number;
  style: 'standard' | 'satellite' | 'terrain';
  priority: number;
  downloadedAt?: Date;
  sizeBytes?: number;
  tileCount?: number;
}

export interface TileDownloadProgress {
  regionId: string;
  totalTiles: number;
  downloadedTiles: number;
  sizeBytes: number;
  estimatedTimeRemaining: number;
  status: 'pending' | 'downloading' | 'completed' | 'failed' | 'paused';
}

class MapTileManager {
  private static instance: MapTileManager;
  private db: SQLite.SQLiteDatabase | null = null;
  private downloadQueue: Map<string, TileDownloadProgress> = new Map();
  private isDownloading: boolean = false;
  private readonly maxConcurrentDownloads = 3;
  
  // Storage paths
  private readonly tilesDirectory = `${RNFS.DocumentDirectoryPath}/offline_tiles`;
  private readonly mbtilesPath = `${this.tilesDirectory}/tiles.mbtiles`;
  
  private constructor() {
    this.initializeStorage();
  }
  
  static getInstance(): MapTileManager {
    if (!MapTileManager.instance) {
      MapTileManager.instance = new MapTileManager();
    }
    return MapTileManager.instance;
  }
  
  /**
   * Initialize storage and database
   */
  private async initializeStorage(): Promise<void> {
    try {
      // Create tiles directory
      const dirExists = await RNFS.exists(this.tilesDirectory);
      if (!dirExists) {
        await RNFS.mkdir(this.tilesDirectory);
      }
      
      // Open MBTiles database
      this.db = await SQLite.openDatabase({
        name: 'tiles.mbtiles',
        location: 'default',
      });
      
      // Initialize MBTiles schema
      await this.initializeMBTilesSchema();
      
    } catch (error) {
      logger.error('Failed to initialize map tile storage:', error);
    }
  }
  
  /**
   * Initialize MBTiles database schema
   */
  private async initializeMBTilesSchema(): Promise<void> {
    if (!this.db) return;
    
    await this.db.transaction((tx) => {
      // MBTiles metadata table
      tx.executeSql(`
        CREATE TABLE IF NOT EXISTS metadata (
          name TEXT PRIMARY KEY,
          value TEXT
        );
      `);
      
      // Tiles table
      tx.executeSql(`
        CREATE TABLE IF NOT EXISTS tiles (
          zoom_level INTEGER,
          tile_column INTEGER,
          tile_row INTEGER,
          tile_data BLOB,
          tile_hash TEXT,
          PRIMARY KEY (zoom_level, tile_column, tile_row)
        );
      `);
      
      // Create indexes
      tx.executeSql('CREATE INDEX IF NOT EXISTS tile_index ON tiles (zoom_level, tile_column, tile_row);');
      tx.executeSql('CREATE INDEX IF NOT EXISTS tile_hash_index ON tiles (tile_hash);');
      
      // Deduplication table
      tx.executeSql(`
        CREATE TABLE IF NOT EXISTS tile_data (
          hash TEXT PRIMARY KEY,
          data BLOB,
          compressed_size INTEGER,
          created_at INTEGER
        );
      `);
      
      // Regions table
      tx.executeSql(`
        CREATE TABLE IF NOT EXISTS regions (
          id TEXT PRIMARY KEY,
          name TEXT,
          bounds TEXT,
          min_zoom INTEGER,
          max_zoom INTEGER,
          style TEXT,
          priority INTEGER,
          downloaded_at INTEGER,
          size_bytes INTEGER,
          tile_count INTEGER
        );
      `);
      
      // Set metadata
      tx.executeSql("INSERT OR REPLACE INTO metadata VALUES ('format', 'pbf')");
      tx.executeSql("INSERT OR REPLACE INTO metadata VALUES ('bounds', '-180,-85,180,85')");
      tx.executeSql("INSERT OR REPLACE INTO metadata VALUES ('center', '0,0,2')");
      tx.executeSql("INSERT OR REPLACE INTO metadata VALUES ('minzoom', '0')");
      tx.executeSql("INSERT OR REPLACE INTO metadata VALUES ('maxzoom', '16')");
    });
  }
  
  /**
   * Download tiles for a region
   */
  async downloadRegion(region: TileRegion): Promise<void> {
    const tiles = this.calculateTilesForRegion(region);
    const totalTiles = tiles.length;
    
    // Initialize progress
    const progress: TileDownloadProgress = {
      regionId: region.id,
      totalTiles,
      downloadedTiles: 0,
      sizeBytes: 0,
      estimatedTimeRemaining: 0,
      status: 'pending',
    };
    
    this.downloadQueue.set(region.id, progress);
    
    // Start download if not already downloading
    if (!this.isDownloading) {
      this.processDownloadQueue();
    }
  }
  
  /**
   * Calculate tiles needed for a region
   */
  private calculateTilesForRegion(region: TileRegion): TileCoordinate[] {
    const tiles: TileCoordinate[] = [];
    
    for (let z = region.minZoom; z <= region.maxZoom; z++) {
      const minTileX = this.lon2tile(region.bounds.minLon, z);
      const maxTileX = this.lon2tile(region.bounds.maxLon, z);
      const minTileY = this.lat2tile(region.bounds.maxLat, z);
      const maxTileY = this.lat2tile(region.bounds.minLat, z);
      
      for (let x = minTileX; x <= maxTileX; x++) {
        for (let y = minTileY; y <= maxTileY; y++) {
          tiles.push({ z, x, y });
        }
      }
    }
    
    return tiles;
  }
  
  /**
   * Process download queue
   */
  private async processDownloadQueue(): Promise<void> {
    this.isDownloading = true;
    
    for (const [regionId, progress] of this.downloadQueue) {
      if (progress.status === 'pending') {
        progress.status = 'downloading';
        await this.downloadRegionTiles(regionId);
      }
    }
    
    this.isDownloading = false;
  }
  
  /**
   * Download tiles for a specific region
   */
  private async downloadRegionTiles(regionId: string): Promise<void> {
    const progress = this.downloadQueue.get(regionId);
    if (!progress) return;
    
    const region = await this.getRegion(regionId);
    if (!region) return;
    
    const tiles = this.calculateTilesForRegion(region);
    const startTime = Date.now();
    
    // Download tiles in batches
    const batchSize = this.maxConcurrentDownloads;
    for (let i = 0; i < tiles.length; i += batchSize) {
      const batch = tiles.slice(i, i + batchSize);
      
      await Promise.all(
        batch.map(async (tile) => {
          try {
            const tileData = await this.downloadTile(tile, region.style);
            if (tileData) {
              await this.storeTile(tile, tileData);
              progress.downloadedTiles++;
              progress.sizeBytes += tileData.byteLength;
              
              // Update progress
              const elapsed = Date.now() - startTime;
              const tilesPerSecond = progress.downloadedTiles / (elapsed / 1000);
              const remainingTiles = progress.totalTiles - progress.downloadedTiles;
              progress.estimatedTimeRemaining = remainingTiles / tilesPerSecond;
              
              // Notify progress
              this.notifyProgress(progress);
            }
          } catch (error) {
            logger.error(`Failed to download tile ${tile.z}/${tile.x}/${tile.y}:`, error);
          }
        })
      );
      
      // Check if download was cancelled
      if (progress.status === 'paused' || progress.status === 'failed') {
        break;
      }
    }
    
    // Mark as completed
    if (progress.downloadedTiles === progress.totalTiles) {
      progress.status = 'completed';
      await this.updateRegionMetadata(regionId, {
        downloadedAt: new Date(),
        sizeBytes: progress.sizeBytes,
        tileCount: progress.totalTiles,
      });
    }
    
    // Log completion
    performanceMonitor.logEvent('offline_map_download_complete', {
      regionId,
      tiles: progress.totalTiles,
      sizeBytes: progress.sizeBytes,
      duration: Date.now() - startTime,
    });
  }
  
  /**
   * Download a single tile through backend proxy
   */
  private async downloadTile(
    tile: TileCoordinate,
    style: string
  ): Promise<ArrayBuffer | null> {
    try {
      // Import the maps proxy service
      const { mapsProxy } = await import('@/services/api/mapsProxy');
      
      // Download through backend proxy - no API key needed
      const tileData = await mapsProxy.downloadMapTile({
        z: tile.z,
        x: tile.x,
        y: tile.y,
        style: style,
        provider: 'maptiler'
      });
      
      // Compress tile data
      const compressed = await this.compressTile(tileData);
      return compressed;
      
    } catch (error) {
      logger.error('Tile download failed:', error);
      return null;
    }
  }
  
  /**
   * Compress tile data
   */
  private async compressTile(data: ArrayBuffer): Promise<ArrayBuffer> {
    return new Promise((resolve, reject) => {
      const uint8Array = new Uint8Array(data);
      
      fflate.gzip(uint8Array, (err, compressed) => {
        if (err) {
          reject(err);
        } else {
          resolve(compressed.buffer);
        }
      });
    });
  }
  
  /**
   * Store tile in database
   */
  private async storeTile(
    tile: TileCoordinate,
    data: ArrayBuffer
  ): Promise<void> {
    if (!this.db) return;
    
    // Calculate hash for deduplication
    const hash = await this.calculateHash(data);
    
    await this.db.transaction((tx) => {
      // Store tile data if not exists
      tx.executeSql(
        'INSERT OR IGNORE INTO tile_data (hash, data, compressed_size, created_at) VALUES (?, ?, ?, ?)',
        [hash, data, data.byteLength, Date.now()]
      );
      
      // Store tile reference
      tx.executeSql(
        'INSERT OR REPLACE INTO tiles (zoom_level, tile_column, tile_row, tile_hash) VALUES (?, ?, ?, ?)',
        [tile.z, tile.x, tile.y, hash]
      );
    });
  }
  
  /**
   * Get tile from storage
   */
  async getTile(tile: TileCoordinate): Promise<ArrayBuffer | null> {
    if (!this.db) return null;
    
    return new Promise((resolve, reject) => {
      this.db!.transaction((tx) => {
        tx.executeSql(
          `SELECT td.data FROM tiles t 
           JOIN tile_data td ON t.tile_hash = td.hash 
           WHERE t.zoom_level = ? AND t.tile_column = ? AND t.tile_row = ?`,
          [tile.z, tile.x, tile.y],
          (_, results) => {
            if (results.rows.length > 0) {
              const data = results.rows.item(0).data;
              resolve(data);
            } else {
              resolve(null);
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
   * Configure MapLibre for offline usage
   */
  async configureOfflineMap(): Promise<void> {
    // Set MapLibre to use our custom tile source
    MapLibreGL.offlineManager.setTileCountLimit(50000);
    MapLibreGL.offlineManager.setProgressEventThrottle(500);
    
    // Create custom tile source
    const tileSource = {
      type: 'vector',
      tiles: [`mbtiles://${this.mbtilesPath}/{z}/{x}/{y}.pbf`],
      minzoom: 0,
      maxzoom: 16,
    };
    
    // Register offline pack
    await MapLibreGL.offlineManager.createPack({
      name: 'roadtrip-offline',
      styleURL: 'asset://styles/maplibre-style.json',
      bounds: [[-180, -85], [180, 85]],
      minZoom: 0,
      maxZoom: 16,
    });
  }
  
  /**
   * Get download progress for a region
   */
  getDownloadProgress(regionId: string): TileDownloadProgress | null {
    return this.downloadQueue.get(regionId) || null;
  }
  
  /**
   * Pause download
   */
  pauseDownload(regionId: string): void {
    const progress = this.downloadQueue.get(regionId);
    if (progress && progress.status === 'downloading') {
      progress.status = 'paused';
    }
  }
  
  /**
   * Resume download
   */
  resumeDownload(regionId: string): void {
    const progress = this.downloadQueue.get(regionId);
    if (progress && progress.status === 'paused') {
      progress.status = 'pending';
      if (!this.isDownloading) {
        this.processDownloadQueue();
      }
    }
  }
  
  /**
   * Delete region
   */
  async deleteRegion(regionId: string): Promise<void> {
    if (!this.db) return;
    
    const region = await this.getRegion(regionId);
    if (!region) return;
    
    const tiles = this.calculateTilesForRegion(region);
    
    await this.db.transaction((tx) => {
      // Delete tiles
      tiles.forEach((tile) => {
        tx.executeSql(
          'DELETE FROM tiles WHERE zoom_level = ? AND tile_column = ? AND tile_row = ?',
          [tile.z, tile.x, tile.y]
        );
      });
      
      // Delete region
      tx.executeSql('DELETE FROM regions WHERE id = ?', [regionId]);
      
      // Clean up orphaned tile data
      tx.executeSql(`
        DELETE FROM tile_data WHERE hash NOT IN (SELECT DISTINCT tile_hash FROM tiles)
      `);
    });
    
    // Remove from download queue
    this.downloadQueue.delete(regionId);
  }
  
  /**
   * Get all downloaded regions
   */
  async getDownloadedRegions(): Promise<TileRegion[]> {
    if (!this.db) return [];
    
    return new Promise((resolve, reject) => {
      this.db!.transaction((tx) => {
        tx.executeSql(
          'SELECT * FROM regions WHERE downloaded_at IS NOT NULL ORDER BY downloaded_at DESC',
          [],
          (_, results) => {
            const regions: TileRegion[] = [];
            for (let i = 0; i < results.rows.length; i++) {
              const row = results.rows.item(i);
              regions.push({
                id: row.id,
                name: row.name,
                bounds: JSON.parse(row.bounds),
                minZoom: row.min_zoom,
                maxZoom: row.max_zoom,
                style: row.style,
                priority: row.priority,
                downloadedAt: new Date(row.downloaded_at),
                sizeBytes: row.size_bytes,
                tileCount: row.tile_count,
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
   * Get storage statistics
   */
  async getStorageStats(): Promise<{
    totalSize: number;
    tileCount: number;
    regionCount: number;
    oldestTile: Date | null;
  }> {
    if (!this.db) {
      return { totalSize: 0, tileCount: 0, regionCount: 0, oldestTile: null };
    }
    
    return new Promise((resolve, reject) => {
      this.db!.transaction((tx) => {
        // Get total size
        tx.executeSql(
          'SELECT SUM(compressed_size) as total_size, COUNT(*) as tile_count, MIN(created_at) as oldest FROM tile_data',
          [],
          (_, sizeResults) => {
            const totalSize = sizeResults.rows.item(0).total_size || 0;
            const tileCount = sizeResults.rows.item(0).tile_count || 0;
            const oldest = sizeResults.rows.item(0).oldest;
            
            // Get region count
            tx.executeSql(
              'SELECT COUNT(*) as region_count FROM regions WHERE downloaded_at IS NOT NULL',
              [],
              (_, regionResults) => {
                const regionCount = regionResults.rows.item(0).region_count || 0;
                
                resolve({
                  totalSize,
                  tileCount,
                  regionCount,
                  oldestTile: oldest ? new Date(oldest) : null,
                });
              }
            );
          },
          (_, error) => {
            reject(error);
            return false;
          }
        );
      });
    });
  }
  
  // Utility functions
  
  private lon2tile(lon: number, zoom: number): number {
    return Math.floor(((lon + 180) / 360) * Math.pow(2, zoom));
  }
  
  private lat2tile(lat: number, zoom: number): number {
    return Math.floor(
      ((1 -
        Math.log(
          Math.tan((lat * Math.PI) / 180) + 1 / Math.cos((lat * Math.PI) / 180)
        ) /
          Math.PI) /
        2) *
        Math.pow(2, zoom)
    );
  }
  
  private async calculateHash(data: ArrayBuffer): Promise<string> {
    // Simple hash for deduplication
    const uint8Array = new Uint8Array(data);
    let hash = 0;
    for (let i = 0; i < uint8Array.length; i++) {
      hash = ((hash << 5) - hash) + uint8Array[i];
      hash = hash & hash; // Convert to 32-bit integer
    }
    return hash.toString(16);
  }
  
  private async getRegion(regionId: string): Promise<TileRegion | null> {
    if (!this.db) return null;
    
    return new Promise((resolve, reject) => {
      this.db!.transaction((tx) => {
        tx.executeSql(
          'SELECT * FROM regions WHERE id = ?',
          [regionId],
          (_, results) => {
            if (results.rows.length > 0) {
              const row = results.rows.item(0);
              resolve({
                id: row.id,
                name: row.name,
                bounds: JSON.parse(row.bounds),
                minZoom: row.min_zoom,
                maxZoom: row.max_zoom,
                style: row.style,
                priority: row.priority,
                downloadedAt: row.downloaded_at ? new Date(row.downloaded_at) : undefined,
                sizeBytes: row.size_bytes,
                tileCount: row.tile_count,
              });
            } else {
              resolve(null);
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
  
  private async updateRegionMetadata(
    regionId: string,
    metadata: Partial<TileRegion>
  ): Promise<void> {
    if (!this.db) return;
    
    await this.db.transaction((tx) => {
      if (metadata.downloadedAt) {
        tx.executeSql(
          'UPDATE regions SET downloaded_at = ? WHERE id = ?',
          [metadata.downloadedAt.getTime(), regionId]
        );
      }
      if (metadata.sizeBytes !== undefined) {
        tx.executeSql(
          'UPDATE regions SET size_bytes = ? WHERE id = ?',
          [metadata.sizeBytes, regionId]
        );
      }
      if (metadata.tileCount !== undefined) {
        tx.executeSql(
          'UPDATE regions SET tile_count = ? WHERE id = ?',
          [metadata.tileCount, regionId]
        );
      }
    });
  }
  
  private notifyProgress(progress: TileDownloadProgress): void {
    // Emit progress event
    offlineManager.emit('mapDownloadProgress', progress);
  }
}

// Export singleton instance
export const mapTileManager = MapTileManager.getInstance();
