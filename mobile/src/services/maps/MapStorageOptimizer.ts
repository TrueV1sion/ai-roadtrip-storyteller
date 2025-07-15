import { Buffer } from 'buffer';
import * as FileSystem from 'expo-file-system';
import * as SQLite from 'expo-sqlite';
import { compress, decompress } from 'fflate';
import { Region, Location, Route } from '../../types/location';

// Constants for tile storage optimization
const TILE_SIZE_BY_ZOOM: Record<number, number> = {
  8: 8 * 1024,    // 8 KB per tile (overview)
  9: 10 * 1024,   // 10 KB
  10: 12 * 1024,  // 12 KB
  11: 15 * 1024,  // 15 KB
  12: 20 * 1024,  // 20 KB
  13: 25 * 1024,  // 25 KB
  14: 30 * 1024,  // 30 KB (urban detail)
  15: 35 * 1024,  // 35 KB
  16: 40 * 1024   // 40 KB (maximum detail)
};

const ZOOM_STRATEGY = {
  HIGHWAY_ZOOM: 11,
  URBAN_ZOOM: 14,
  DESTINATION_ZOOM: 16,
  OVERVIEW_ZOOM: 8,
  MIN_ZOOM: 8,
  MAX_ZOOM: 16,
  RENDER_MAX_ZOOM: 20
};

// Interfaces
interface TileCoordinate {
  z: number;
  x: number;
  y: number;
}

interface ZoomLevel {
  range: [Location, Location];
  minZoom: number;
  maxZoom: number;
  priority: number;
}

interface OptimizedZoomPlan {
  segments: Array<{
    range: [Location, Location];
    zoomLevels: number[];
    allocatedBytes: number;
  }>;
  totalSize: number;
  coverage: TileCoordinate[];
}

interface CompressionResult {
  data: Uint8Array;
  originalSize: number;
  compressedSize: number;
  compressionRatio: number;
}

interface StorageEstimate {
  tileDataSize: number;
  databaseOverhead: number;
  totalSize: number;
  tilesPerMile: number;
  bytesPerMile: number;
  estimatedCompressionRatio: number;
}

export class MapStorageOptimizer {
  private db: SQLite.WebSQLDatabase | null = null;
  private readonly DB_NAME = 'mbtiles.db';
  private readonly MBTILES_DIR = `${FileSystem.documentDirectory}mbtiles/`;
  private tileHashes: Map<string, number> = new Map();
  private nextTileId: number = 1;

  constructor() {
    this.initializeStorage();
  }

  private async initializeStorage(): Promise<void> {
    // Ensure directory exists
    const dirInfo = await FileSystem.getInfoAsync(this.MBTILES_DIR);
    if (!dirInfo.exists) {
      await FileSystem.makeDirectoryAsync(this.MBTILES_DIR, { intermediates: true });
    }

    // Initialize MBTiles database
    this.db = SQLite.openDatabase(this.DB_NAME);
    await this.initializeMBTilesSchema();
  }

  private async initializeMBTilesSchema(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'));
        return;
      }

      this.db.transaction(tx => {
        // MBTiles schema
        tx.executeSql(`
          CREATE TABLE IF NOT EXISTS tiles (
            zoom_level INTEGER,
            tile_column INTEGER,
            tile_row INTEGER,
            tile_data BLOB,
            PRIMARY KEY (zoom_level, tile_column, tile_row)
          );
        `);

        tx.executeSql(`
          CREATE TABLE IF NOT EXISTS metadata (
            name TEXT,
            value TEXT,
            PRIMARY KEY (name)
          );
        `);

        // Custom optimization tables
        tx.executeSql(`
          CREATE TABLE IF NOT EXISTS tile_refs (
            zoom_level INTEGER,
            tile_column INTEGER,
            tile_row INTEGER,
            data_id INTEGER,
            PRIMARY KEY (zoom_level, tile_column, tile_row),
            FOREIGN KEY (data_id) REFERENCES tile_data(id)
          );
        `);

        tx.executeSql(`
          CREATE TABLE IF NOT EXISTS tile_data (
            id INTEGER PRIMARY KEY,
            data BLOB,
            hash TEXT UNIQUE,
            size INTEGER,
            compression_ratio REAL
          );
        `);

        // Insert metadata
        tx.executeSql(`
          INSERT OR REPLACE INTO metadata (name, value) VALUES
          ('name', 'AI Road Trip Offline Maps'),
          ('type', 'baselayer'),
          ('version', '1.0'),
          ('description', 'Optimized offline maps for road trips'),
          ('format', 'pbf'),
          ('compression', 'brotli');
        `);
      }, 
      (error) => {
        console.error('Error initializing MBTiles schema:', error);
        reject(error);
      },
      () => {
        console.log('MBTiles schema initialized successfully');
        resolve();
      });
    });
  }

  /**
   * Calculate optimal zoom levels for a route
   */
  calculateOptimalZoomLevels(route: Route): ZoomLevel[] {
    const zoomLevels: ZoomLevel[] = [];
    
    // Analyze route segments
    for (let i = 0; i < route.segments.length; i++) {
      const segment = route.segments[i];
      const start = route.points[segment.startIndex];
      const end = route.points[segment.endIndex];
      
      if (segment.roadType === 'highway' && segment.speedLimit > 55) {
        zoomLevels.push({
          range: [start, end],
          minZoom: 8,
          maxZoom: 11,
          priority: 1
        });
      } else if (segment.isUrban || segment.hasComplexIntersections) {
        zoomLevels.push({
          range: [start, end],
          minZoom: 12,
          maxZoom: 16,
          priority: 3
        });
      } else {
        zoomLevels.push({
          range: [start, end],
          minZoom: 10,
          maxZoom: 14,
          priority: 2
        });
      }
    }
    
    return this.mergeAdjacentZoomLevels(zoomLevels);
  }

  /**
   * Optimize zoom levels to fit within storage budget
   */
  optimizeZoomLevelsForBudget(
    zoomLevels: ZoomLevel[],
    routeLength: number,
    budgetBytes: number = 800 * 1024 * 1024
  ): OptimizedZoomPlan {
    const bytesPerMile = budgetBytes / routeLength;
    let allocatedBytes = 0;
    const optimizedPlan: OptimizedZoomPlan = {
      segments: [],
      totalSize: 0,
      coverage: []
    };
    
    // First pass: Allocate minimum zoom levels
    zoomLevels.forEach(segment => {
      const segmentLength = this.calculateSegmentLength(segment.range);
      const baseAllocation = segmentLength * bytesPerMile * 0.7; // 70% for base
      allocatedBytes += baseAllocation;
      
      optimizedPlan.segments.push({
        range: segment.range,
        zoomLevels: [segment.minZoom],
        allocatedBytes: baseAllocation
      });
    });
    
    // Second pass: Add detail where budget allows
    let remainingBudget = budgetBytes - allocatedBytes;
    const sortedByPriority = zoomLevels.sort((a, b) => b.priority - a.priority);
    
    for (const segment of sortedByPriority) {
      const segmentIndex = optimizedPlan.segments.findIndex(
        s => s.range[0] === segment.range[0]
      );
      
      if (segmentIndex === -1) continue;
      
      // Calculate cost of additional zoom levels
      for (let z = segment.minZoom + 1; z <= segment.maxZoom; z++) {
        const additionalCost = this.estimateZoomLevelCost(segment.range, z);
        
        if (additionalCost <= remainingBudget) {
          optimizedPlan.segments[segmentIndex].zoomLevels.push(z);
          optimizedPlan.segments[segmentIndex].allocatedBytes += additionalCost;
          remainingBudget -= additionalCost;
        } else {
          break;
        }
      }
    }
    
    // Calculate total size and coverage
    optimizedPlan.totalSize = budgetBytes - remainingBudget;
    optimizedPlan.coverage = this.calculateTileCoverage(optimizedPlan.segments);
    
    return optimizedPlan;
  }

  /**
   * Compress tile data using Brotli-like compression
   */
  async compressTile(tileData: Uint8Array): Promise<CompressionResult> {
    return new Promise((resolve, reject) => {
      try {
        // Use fflate for compression (similar to Brotli but works in React Native)
        compress(tileData, { level: 6 }, (err, compressed) => {
          if (err) {
            reject(err);
            return;
          }
          
          resolve({
            data: compressed,
            originalSize: tileData.length,
            compressedSize: compressed.length,
            compressionRatio: compressed.length / tileData.length
          });
        });
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Decompress tile data
   */
  async decompressTile(compressedData: Uint8Array): Promise<Uint8Array> {
    return new Promise((resolve, reject) => {
      decompress(compressedData, (err, decompressed) => {
        if (err) {
          reject(err);
          return;
        }
        resolve(decompressed);
      });
    });
  }

  /**
   * Store tile with deduplication
   */
  async storeTileWithDeduplication(
    z: number,
    x: number,
    y: number,
    tileData: Uint8Array
  ): Promise<number> {
    // Calculate hash
    const hash = await this.hashTileData(tileData);
    
    // Check if we already have this tile data
    if (this.tileHashes.has(hash)) {
      const dataId = this.tileHashes.get(hash)!;
      
      // Just create a reference to existing data
      await this.createTileReference(z, x, y, dataId);
      return dataId;
    }
    
    // Compress new tile
    const compressed = await this.compressTile(tileData);
    
    // Store new unique tile
    const dataId = await this.storeTileData(hash, compressed);
    this.tileHashes.set(hash, dataId);
    
    // Create reference
    await this.createTileReference(z, x, y, dataId);
    
    return dataId;
  }

  /**
   * Calculate route corridor for efficient tile selection
   */
  calculateRouteCorridor(route: Route, bufferMeters: number = 1000): TileCoordinate[] {
    const tiles = new Set<string>();
    
    route.points.forEach((point, index) => {
      let currentBuffer = bufferMeters;
      
      // Adaptive buffer based on context
      if (index === 0 || index === route.points.length - 1) {
        currentBuffer *= 2; // Double buffer at start/end
      }
      
      // Check if we're in an urban area or complex intersection
      const segment = this.findSegmentForPoint(route, index);
      if (segment?.isUrban) {
        currentBuffer *= 1.5;
      }
      
      // Get tiles for each zoom level in the segment's range
      const zoomLevels = this.getZoomLevelsForPoint(route, index);
      
      zoomLevels.forEach(zoom => {
        const tilesAtZoom = this.getTilesInRadius(point, currentBuffer, zoom);
        tilesAtZoom.forEach(tile => {
          tiles.add(`${tile.z}/${tile.x}/${tile.y}`);
        });
      });
    });
    
    // Convert set to array of TileCoordinates
    return Array.from(tiles).map(key => {
      const [z, x, y] = key.split('/').map(Number);
      return { z, x, y };
    });
  }

  /**
   * Estimate storage requirements for a route
   */
  async estimateRouteStorage(route: Route): Promise<StorageEstimate> {
    const zoomLevels = this.calculateOptimalZoomLevels(route);
    const optimizedPlan = this.optimizeZoomLevelsForBudget(
      zoomLevels,
      route.lengthMiles
    );
    
    let totalSize = 0;
    let totalTiles = 0;
    
    // Calculate size for each segment
    for (const segment of optimizedPlan.segments) {
      const tiles = this.calculateTilesForSegment(segment);
      totalTiles += tiles.length;
      
      const segmentSize = tiles.reduce((sum, tile) => {
        const baseSize = TILE_SIZE_BY_ZOOM[tile.z] || 30 * 1024;
        const compressionRatio = 0.4; // Assume 60% compression
        return sum + (baseSize * compressionRatio);
      }, 0);
      
      totalSize += segmentSize;
    }
    
    // Add overhead
    const dbOverhead = totalSize * 0.05; // 5% overhead
    const totalWithOverhead = totalSize + dbOverhead;
    
    return {
      tileDataSize: totalSize,
      databaseOverhead: dbOverhead,
      totalSize: totalWithOverhead,
      tilesPerMile: totalTiles / route.lengthMiles,
      bytesPerMile: totalWithOverhead / route.lengthMiles,
      estimatedCompressionRatio: 0.4
    };
  }

  /**
   * Get storage statistics
   */
  async getStorageStats(): Promise<{
    totalTiles: number;
    uniqueTileData: number;
    deduplicationRatio: number;
    totalSize: number;
    averageCompressionRatio: number;
  }> {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'));
        return;
      }

      this.db.transaction(tx => {
        // Get total tiles
        tx.executeSql(
          'SELECT COUNT(*) as count FROM tile_refs',
          [],
          (_, result) => {
            const totalTiles = result.rows.item(0).count;
            
            // Get unique tile data
            tx.executeSql(
              'SELECT COUNT(*) as count, SUM(size) as total_size, AVG(compression_ratio) as avg_ratio FROM tile_data',
              [],
              (_, dataResult) => {
                const uniqueData = dataResult.rows.item(0).count;
                const totalSize = dataResult.rows.item(0).total_size || 0;
                const avgRatio = dataResult.rows.item(0).avg_ratio || 0;
                
                resolve({
                  totalTiles,
                  uniqueTileData: uniqueData,
                  deduplicationRatio: totalTiles / (uniqueData || 1),
                  totalSize,
                  averageCompressionRatio: avgRatio
                });
              }
            );
          }
        );
      }, reject);
    });
  }

  // Helper methods
  private async hashTileData(data: Uint8Array): Promise<string> {
    // Simple hash implementation for React Native
    let hash = 0;
    for (let i = 0; i < data.length; i++) {
      hash = ((hash << 5) - hash) + data[i];
      hash = hash & hash; // Convert to 32-bit integer
    }
    return hash.toString(16);
  }

  private mergeAdjacentZoomLevels(levels: ZoomLevel[]): ZoomLevel[] {
    // Merge adjacent segments with same zoom requirements
    const merged: ZoomLevel[] = [];
    
    levels.forEach((level, index) => {
      if (index === 0) {
        merged.push(level);
        return;
      }
      
      const last = merged[merged.length - 1];
      if (last.minZoom === level.minZoom && 
          last.maxZoom === level.maxZoom && 
          last.priority === level.priority) {
        // Extend the range
        last.range[1] = level.range[1];
      } else {
        merged.push(level);
      }
    });
    
    return merged;
  }

  private calculateSegmentLength(range: [Location, Location]): number {
    // Haversine formula for distance
    const R = 3959; // Earth radius in miles
    const lat1 = range[0].latitude * Math.PI / 180;
    const lat2 = range[1].latitude * Math.PI / 180;
    const deltaLat = (range[1].latitude - range[0].latitude) * Math.PI / 180;
    const deltaLon = (range[1].longitude - range[0].longitude) * Math.PI / 180;
    
    const a = Math.sin(deltaLat / 2) * Math.sin(deltaLat / 2) +
              Math.cos(lat1) * Math.cos(lat2) *
              Math.sin(deltaLon / 2) * Math.sin(deltaLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    
    return R * c;
  }

  private estimateZoomLevelCost(range: [Location, Location], zoom: number): number {
    const tiles = this.calculateTilesForRange(range, zoom);
    const tileSize = TILE_SIZE_BY_ZOOM[zoom] || 30 * 1024;
    const compressionRatio = 0.4;
    return tiles.length * tileSize * compressionRatio;
  }

  private calculateTileCoverage(segments: OptimizedZoomPlan['segments']): TileCoordinate[] {
    const tiles: TileCoordinate[] = [];
    
    segments.forEach(segment => {
      segment.zoomLevels.forEach(zoom => {
        const segmentTiles = this.calculateTilesForRange(segment.range, zoom);
        tiles.push(...segmentTiles);
      });
    });
    
    return tiles;
  }

  private calculateTilesForSegment(
    segment: OptimizedZoomPlan['segments'][0]
  ): TileCoordinate[] {
    const tiles: TileCoordinate[] = [];
    
    segment.zoomLevels.forEach(zoom => {
      const segmentTiles = this.calculateTilesForRange(segment.range, zoom);
      tiles.push(...segmentTiles);
    });
    
    return tiles;
  }

  private calculateTilesForRange(
    range: [Location, Location],
    zoom: number
  ): TileCoordinate[] {
    const tiles: TileCoordinate[] = [];
    
    // Convert lat/lng to tile coordinates
    const startTile = this.latLngToTile(range[0].latitude, range[0].longitude, zoom);
    const endTile = this.latLngToTile(range[1].latitude, range[1].longitude, zoom);
    
    const minX = Math.min(startTile.x, endTile.x);
    const maxX = Math.max(startTile.x, endTile.x);
    const minY = Math.min(startTile.y, endTile.y);
    const maxY = Math.max(startTile.y, endTile.y);
    
    for (let x = minX; x <= maxX; x++) {
      for (let y = minY; y <= maxY; y++) {
        tiles.push({ z: zoom, x, y });
      }
    }
    
    return tiles;
  }

  private getTilesInRadius(
    center: Location,
    radiusMeters: number,
    zoom: number
  ): TileCoordinate[] {
    const tiles: TileCoordinate[] = [];
    
    // Calculate tile bounds
    const metersPerPixel = 156543.03392 * Math.cos(center.latitude * Math.PI / 180) / Math.pow(2, zoom);
    const tileSize = 256; // pixels
    const metersPerTile = metersPerPixel * tileSize;
    const tilesRadius = Math.ceil(radiusMeters / metersPerTile);
    
    const centerTile = this.latLngToTile(center.latitude, center.longitude, zoom);
    
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

  private latLngToTile(lat: number, lng: number, zoom: number): { x: number; y: number } {
    const n = Math.pow(2, zoom);
    const x = Math.floor((lng + 180) / 360 * n);
    const latRad = lat * Math.PI / 180;
    const y = Math.floor((1 - Math.asinh(Math.tan(latRad)) / Math.PI) / 2 * n);
    
    return { x, y };
  }

  private findSegmentForPoint(route: Route, pointIndex: number): Route['segments'][0] | null {
    return route.segments.find(segment => 
      pointIndex >= segment.startIndex && pointIndex <= segment.endIndex
    ) || null;
  }

  private getZoomLevelsForPoint(route: Route, pointIndex: number): number[] {
    const segment = this.findSegmentForPoint(route, pointIndex);
    if (!segment) return [12]; // Default zoom
    
    if (segment.roadType === 'highway') {
      return [8, 10, 11];
    } else if (segment.isUrban) {
      return [12, 14, 16];
    } else {
      return [10, 12, 14];
    }
  }

  private async createTileReference(
    z: number,
    x: number,
    y: number,
    dataId: number
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'));
        return;
      }

      this.db.transaction(tx => {
        tx.executeSql(
          'INSERT OR REPLACE INTO tile_refs (zoom_level, tile_column, tile_row, data_id) VALUES (?, ?, ?, ?)',
          [z, x, y, dataId],
          () => resolve(),
          (_, error) => {
            reject(error);
            return false;
          }
        );
      });
    });
  }

  private async storeTileData(
    hash: string,
    compressed: CompressionResult
  ): Promise<number> {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        reject(new Error('Database not initialized'));
        return;
      }

      this.db.transaction(tx => {
        tx.executeSql(
          'INSERT INTO tile_data (data, hash, size, compression_ratio) VALUES (?, ?, ?, ?)',
          [
            compressed.data,
            hash,
            compressed.compressedSize,
            compressed.compressionRatio
          ],
          (_, result) => {
            const dataId = result.insertId;
            this.nextTileId = dataId + 1;
            resolve(dataId);
          },
          (_, error) => {
            reject(error);
            return false;
          }
        );
      });
    });
  }
}

// Export singleton instance
export default new MapStorageOptimizer();