# Map Storage and Rendering Optimization Strategy

## Executive Summary

This document outlines an optimal map storage and rendering strategy for the AI Road Trip Storyteller mobile app using MapLibre GL Native with MBTiles format. The strategy focuses on achieving <800MB storage per 1000 miles while maintaining excellent performance and user experience.

## 1. Optimal Zoom Level Strategy

### Dynamic Zoom Level Selection

```typescript
interface ZoomLevelStrategy {
  // Base zoom levels for different contexts
  HIGHWAY_ZOOM: 11,      // For highway driving (less detail needed)
  URBAN_ZOOM: 14,        // For city driving (more detail)
  DESTINATION_ZOOM: 16,  // For final approach to destinations
  OVERVIEW_ZOOM: 8,      // For route planning overview
  
  // Adaptive zoom range
  MIN_ZOOM: 8,           // Minimum downloadable zoom
  MAX_ZOOM: 16,          // Maximum downloadable zoom
  RENDER_MAX_ZOOM: 20    // Maximum rendering zoom (vector scaling)
}

// Intelligent zoom level calculation
function calculateOptimalZoomLevels(routeData: Route): ZoomLevel[] {
  const zoomLevels: ZoomLevel[] = [];
  
  // Analyze route segments
  routeData.segments.forEach(segment => {
    if (segment.roadType === 'highway' && segment.speedLimit > 55) {
      zoomLevels.push({
        range: [segment.start, segment.end],
        minZoom: 8,
        maxZoom: 11,
        priority: 1
      });
    } else if (segment.isUrban || segment.hasComplexIntersections) {
      zoomLevels.push({
        range: [segment.start, segment.end],
        minZoom: 12,
        maxZoom: 16,
        priority: 3
      });
    } else {
      zoomLevels.push({
        range: [segment.start, segment.end],
        minZoom: 10,
        maxZoom: 14,
        priority: 2
      });
    }
  });
  
  return optimizeZoomLevels(zoomLevels);
}

// Storage calculation per zoom level
const TILE_SIZE_BY_ZOOM = {
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
```

### Zoom Level Optimization Algorithm

```typescript
function optimizeZoomLevels(segments: ZoomLevel[]): OptimizedZoomPlan {
  const budget = 800 * 1024 * 1024; // 800MB
  const routeLength = calculateRouteLength(segments);
  const bytesPerMile = budget / 1000; // Target ratio
  
  // Priority-based allocation
  let allocatedBytes = 0;
  const optimizedPlan: OptimizedZoomPlan = {
    segments: [],
    totalSize: 0,
    coverage: []
  };
  
  // First pass: Allocate minimum zoom levels
  segments.forEach(segment => {
    const baseAllocation = calculateBaseAllocation(segment, bytesPerMile);
    allocatedBytes += baseAllocation;
    optimizedPlan.segments.push({
      ...segment,
      allocatedBytes: baseAllocation,
      zoomLevels: [segment.minZoom]
    });
  });
  
  // Second pass: Add detail where budget allows
  const remainingBudget = budget - allocatedBytes;
  const sortedByPriority = segments.sort((a, b) => b.priority - a.priority);
  
  for (const segment of sortedByPriority) {
    const additionalZoomLevels = calculateAdditionalZoomLevels(
      segment,
      remainingBudget,
      bytesPerMile
    );
    
    if (additionalZoomLevels.cost <= remainingBudget) {
      segment.zoomLevels.push(...additionalZoomLevels.levels);
      remainingBudget -= additionalZoomLevels.cost;
    }
  }
  
  return optimizedPlan;
}
```

## 2. Tile Compression Techniques

### MBTiles Compression Strategy

```typescript
interface CompressionConfig {
  // Compression algorithms
  algorithm: 'gzip' | 'brotli' | 'zstd';
  level: number; // 1-9 for gzip, 1-11 for brotli, 1-22 for zstd
  
  // Vector tile optimization
  simplification: {
    tolerance: number;      // Douglas-Peucker tolerance
    minZoom: number;       // Start simplification at this zoom
    maxPoints: number;     // Maximum points per feature
  };
  
  // Feature filtering
  featureFilter: {
    removeByZoom: Map<number, string[]>; // Features to remove at each zoom
    propertyFilter: string[];             // Properties to remove
  };
}

const OPTIMAL_COMPRESSION: CompressionConfig = {
  algorithm: 'brotli',
  level: 6, // Balance between size and CPU usage
  
  simplification: {
    tolerance: 0.5,
    minZoom: 10,
    maxPoints: 1000
  },
  
  featureFilter: {
    removeByZoom: new Map([
      [8, ['building', 'poi_label', 'minor_road']],
      [10, ['building', 'small_poi']],
      [12, ['building_outline']],
      [14, []] // Keep all features at zoom 14+
    ]),
    propertyFilter: ['source', 'source_layer', 'unused_property']
  }
};

// Tile compression implementation
async function compressTile(tile: VectorTile): Promise<CompressedTile> {
  // Step 1: Simplify geometry
  const simplified = simplifyTileGeometry(tile, OPTIMAL_COMPRESSION.simplification);
  
  // Step 2: Filter features
  const filtered = filterTileFeatures(simplified, tile.zoom, OPTIMAL_COMPRESSION.featureFilter);
  
  // Step 3: Optimize properties
  const optimized = optimizeTileProperties(filtered);
  
  // Step 4: Apply compression
  const compressed = await compress(optimized, {
    algorithm: OPTIMAL_COMPRESSION.algorithm,
    level: OPTIMAL_COMPRESSION.level
  });
  
  return {
    data: compressed,
    originalSize: tile.size,
    compressedSize: compressed.length,
    compressionRatio: tile.size / compressed.length
  };
}

// Batch compression for better performance
async function batchCompressTiles(tiles: VectorTile[]): Promise<MBTilesData> {
  const BATCH_SIZE = 100;
  const compressed: CompressedTile[] = [];
  
  // Process in parallel batches
  for (let i = 0; i < tiles.length; i += BATCH_SIZE) {
    const batch = tiles.slice(i, i + BATCH_SIZE);
    const compressedBatch = await Promise.all(
      batch.map(tile => compressTile(tile))
    );
    compressed.push(...compressedBatch);
  }
  
  // Create MBTiles database
  return createMBTiles(compressed);
}
```

### Storage Optimization Techniques

```typescript
// Deduplication strategy for identical tiles
class TileDeduplicator {
  private tileHashes: Map<string, number> = new Map();
  private tileData: Map<number, Uint8Array> = new Map();
  private nextId: number = 1;
  
  async addTile(z: number, x: number, y: number, data: Uint8Array): Promise<number> {
    const hash = await this.hashTile(data);
    
    if (this.tileHashes.has(hash)) {
      // Reuse existing tile
      return this.tileHashes.get(hash)!;
    }
    
    // Store new unique tile
    const id = this.nextId++;
    this.tileHashes.set(hash, id);
    this.tileData.set(id, data);
    
    return id;
  }
  
  private async hashTile(data: Uint8Array): Promise<string> {
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    return Array.from(new Uint8Array(hashBuffer))
      .map(b => b.toString(16).padStart(2, '0'))
      .join('');
  }
  
  getStorageStats(): StorageStats {
    const uniqueTiles = this.tileData.size;
    const totalReferences = this.tileHashes.size;
    const savedTiles = totalReferences - uniqueTiles;
    
    return {
      uniqueTiles,
      totalReferences,
      savedTiles,
      compressionRatio: totalReferences / uniqueTiles
    };
  }
}
```

## 3. Region Boundary Algorithms

### Intelligent Region Calculation

```typescript
interface RegionBoundary {
  bounds: LatLngBounds;
  buffer: number; // Buffer in meters
  shape: 'rectangle' | 'polygon' | 'corridor';
  segments: RouteSegment[];
}

// Corridor-based region calculation for routes
function calculateRouteCorridor(route: Route, bufferMeters: number): RegionBoundary {
  const corridor: LatLng[] = [];
  
  // Create buffered corridor along route
  route.points.forEach((point, index) => {
    if (index === 0 || index === route.points.length - 1) {
      // Larger buffer at start/end points
      const circlePoints = createCircleBuffer(point, bufferMeters * 2);
      corridor.push(...circlePoints);
    } else {
      // Calculate perpendicular buffer points
      const bearing = calculateBearing(
        route.points[index - 1],
        route.points[index + 1]
      );
      
      const leftPoint = calculateDestination(
        point,
        bearing - 90,
        bufferMeters
      );
      const rightPoint = calculateDestination(
        point,
        bearing + 90,
        bufferMeters
      );
      
      corridor.push(leftPoint, rightPoint);
    }
  });
  
  // Optimize corridor shape
  const optimized = douglasPeucker(corridor, 100); // 100m tolerance
  
  return {
    bounds: calculateBounds(optimized),
    buffer: bufferMeters,
    shape: 'corridor',
    segments: analyzeRouteSegments(route, optimized)
  };
}

// Adaptive buffer calculation based on context
function calculateAdaptiveBuffer(segment: RouteSegment): number {
  const BASE_BUFFER = 1000; // 1km base buffer
  
  let buffer = BASE_BUFFER;
  
  // Adjust based on speed
  if (segment.averageSpeed > 60) {
    buffer *= 2; // Double buffer for highways
  }
  
  // Adjust based on point density
  if (segment.poiDensity > 10) {
    buffer *= 1.5; // More buffer in areas with many POIs
  }
  
  // Adjust based on navigation complexity
  if (segment.turnCount > 5) {
    buffer *= 1.3; // More buffer for complex navigation
  }
  
  return Math.min(buffer, 5000); // Cap at 5km
}

// Tile selection within region
function selectTilesForRegion(region: RegionBoundary, zoomLevels: number[]): TileCoordinate[] {
  const tiles: TileCoordinate[] = [];
  
  zoomLevels.forEach(zoom => {
    const tileBounds = region.bounds.toTileBounds(zoom);
    
    for (let x = tileBounds.minX; x <= tileBounds.maxX; x++) {
      for (let y = tileBounds.minY; y <= tileBounds.maxY; y++) {
        // Check if tile intersects with actual corridor shape
        if (region.shape === 'corridor') {
          const tilePoly = getTilePolygon(zoom, x, y);
          if (intersectsPolygon(tilePoly, region.segments)) {
            tiles.push({ z: zoom, x, y });
          }
        } else {
          tiles.push({ z: zoom, x, y });
        }
      }
    }
  });
  
  return tiles;
}
```

## 4. Progressive Loading Implementation

### Smart Progressive Loading System

```typescript
class ProgressiveMapLoader {
  private loadQueue: PriorityQueue<TileLoadRequest>;
  private activeLoads: Map<string, Promise<void>>;
  private tileCache: LRUCache<string, VectorTile>;
  private visibilityTracker: TileVisibilityTracker;
  
  constructor(private mbtilesDb: MBTilesDatabase) {
    this.loadQueue = new PriorityQueue(this.compareTilePriority);
    this.activeLoads = new Map();
    this.tileCache = new LRUCache({ max: 500 }); // 500 tiles in memory
    this.visibilityTracker = new TileVisibilityTracker();
  }
  
  // Progressive loading strategy
  async loadTilesForView(viewport: Viewport, route?: Route): Promise<void> {
    // Phase 1: Load visible tiles immediately
    const visibleTiles = this.calculateVisibleTiles(viewport);
    await this.loadTilesWithPriority(visibleTiles, Priority.IMMEDIATE);
    
    // Phase 2: Preload route tiles
    if (route) {
      const routeTiles = this.calculateRouteTiles(route, viewport);
      await this.loadTilesWithPriority(routeTiles, Priority.HIGH);
    }
    
    // Phase 3: Load surrounding area
    const surroundingTiles = this.calculateSurroundingTiles(viewport, 2);
    this.loadTilesWithPriority(surroundingTiles, Priority.MEDIUM);
    
    // Phase 4: Speculative loading based on movement
    const speculativeTiles = this.predictNextTiles(viewport);
    this.loadTilesWithPriority(speculativeTiles, Priority.LOW);
  }
  
  private async loadTilesWithPriority(
    tiles: TileCoordinate[],
    priority: Priority
  ): Promise<void> {
    const loadPromises: Promise<void>[] = [];
    
    for (const tile of tiles) {
      const tileKey = `${tile.z}/${tile.x}/${tile.y}`;
      
      // Check cache first
      if (this.tileCache.has(tileKey)) {
        continue;
      }
      
      // Check if already loading
      if (this.activeLoads.has(tileKey)) {
        loadPromises.push(this.activeLoads.get(tileKey)!);
        continue;
      }
      
      // Add to load queue
      const loadPromise = this.loadTile(tile, priority);
      this.activeLoads.set(tileKey, loadPromise);
      loadPromises.push(loadPromise);
    }
    
    // Wait for high priority tiles
    if (priority >= Priority.HIGH) {
      await Promise.all(loadPromises);
    }
  }
  
  private async loadTile(tile: TileCoordinate, priority: Priority): Promise<void> {
    const tileKey = `${tile.z}/${tile.x}/${tile.y}`;
    
    try {
      // Load from MBTiles
      const tileData = await this.mbtilesDb.getTile(tile.z, tile.x, tile.y);
      
      if (tileData) {
        // Decompress and parse
        const decompressed = await this.decompressTile(tileData);
        const vectorTile = new VectorTile(decompressed);
        
        // Cache in memory
        this.tileCache.set(tileKey, vectorTile);
        
        // Render tile
        await this.renderTile(vectorTile, tile);
      }
    } finally {
      this.activeLoads.delete(tileKey);
    }
  }
  
  // Predictive loading based on movement
  private predictNextTiles(viewport: Viewport): TileCoordinate[] {
    const movement = this.visibilityTracker.getMovementVector();
    const speed = this.visibilityTracker.getSpeed();
    
    // Predict future position
    const futureTime = Math.min(5000, 60000 / speed); // 5 seconds or time to travel 1km
    const futurePosition = {
      lat: viewport.center.lat + movement.lat * futureTime,
      lng: viewport.center.lng + movement.lng * futureTime
    };
    
    // Calculate tiles for predicted position
    const futureViewport = {
      ...viewport,
      center: futurePosition
    };
    
    return this.calculateVisibleTiles(futureViewport);
  }
}

// Priority queue for tile loading
enum Priority {
  IMMEDIATE = 4,
  HIGH = 3,
  MEDIUM = 2,
  LOW = 1
}

class PriorityQueue<T> {
  private heap: Array<{ item: T; priority: number }> = [];
  
  constructor(private compare: (a: T, b: T) => number) {}
  
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
}
```

## 5. Cache Eviction Policies

### Intelligent Cache Management

```typescript
class MapCacheManager {
  private memoryCache: LRUCache<string, CachedTile>;
  private diskCache: DiskCache;
  private usageTracker: UsageTracker;
  private routeContext: RouteContext;
  
  constructor(config: CacheConfig) {
    this.memoryCache = new LRUCache({
      max: config.maxMemoryTiles,
      ttl: config.memoryTTL,
      updateAgeOnGet: true,
      dispose: (tile, key) => this.onMemoryEvict(tile, key)
    });
    
    this.diskCache = new DiskCache({
      maxSize: config.maxDiskSize,
      basePath: config.diskPath
    });
    
    this.usageTracker = new UsageTracker();
    this.routeContext = new RouteContext();
  }
  
  // Multi-level cache eviction strategy
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
  
  // Scoring algorithm for eviction
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
  
  // Preemptive cache warming
  async warmCache(route: Route): Promise<void> {
    const tilesToLoad = this.calculateCriticalTiles(route);
    
    // Load in priority order
    for (const tileGroup of tilesToLoad) {
      await Promise.all(
        tileGroup.tiles.map(tile => this.loadTileToCache(tile, tileGroup.priority))
      );
    }
  }
  
  // Critical tiles calculation
  private calculateCriticalTiles(route: Route): TileGroup[] {
    const groups: TileGroup[] = [];
    
    // High priority: Start/end points and complex intersections
    groups.push({
      priority: Priority.HIGH,
      tiles: [
        ...this.getTilesAroundPoint(route.start, 16, 1000),
        ...this.getTilesAroundPoint(route.end, 16, 1000),
        ...route.complexIntersections.flatMap(point => 
          this.getTilesAroundPoint(point, 15, 500)
        )
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
}

// Cache configuration
interface CacheConfig {
  maxMemoryTiles: number;        // e.g., 500 tiles
  maxDiskSize: number;           // e.g., 800MB
  memoryTTL: number;             // e.g., 5 minutes
  diskTTL: number;               // e.g., 30 days
  preloadRadius: number;         // e.g., 5km
  speculativeLoadDistance: number; // e.g., 10km
}

const OPTIMAL_CACHE_CONFIG: CacheConfig = {
  maxMemoryTiles: 500,
  maxDiskSize: 800 * 1024 * 1024,
  memoryTTL: 5 * 60 * 1000,
  diskTTL: 30 * 24 * 60 * 60 * 1000,
  preloadRadius: 5000,
  speculativeLoadDistance: 10000
};
```

## 6. Performance Optimization Tips

### Rendering Performance Optimizations

```typescript
class PerformanceOptimizedRenderer {
  private renderQueue: RenderQueue;
  private frameScheduler: FrameScheduler;
  private tileRenderer: TileRenderer;
  private performanceMonitor: PerformanceMonitor;
  
  // Optimized rendering pipeline
  async renderFrame(viewport: Viewport): Promise<void> {
    const startTime = performance.now();
    
    // 1. Frustum culling
    const visibleTiles = this.frustumCull(viewport);
    
    // 2. Level-of-detail selection
    const lodTiles = this.selectLOD(visibleTiles, viewport.zoom);
    
    // 3. Batch rendering by style layer
    const batches = this.createRenderBatches(lodTiles);
    
    // 4. Render with frame budget
    await this.renderWithBudget(batches, 16); // 16ms budget for 60fps
    
    // 5. Monitor performance
    this.performanceMonitor.recordFrame(performance.now() - startTime);
  }
  
  // Frame-budget aware rendering
  private async renderWithBudget(
    batches: RenderBatch[],
    budgetMs: number
  ): Promise<void> {
    const startTime = performance.now();
    let rendered = 0;
    
    for (const batch of batches) {
      const elapsed = performance.now() - startTime;
      const remaining = budgetMs - elapsed;
      
      if (remaining < 2) { // Less than 2ms remaining
        // Defer to next frame
        this.renderQueue.defer(batch);
        break;
      }
      
      await this.tileRenderer.renderBatch(batch);
      rendered++;
    }
    
    // Schedule deferred batches
    if (this.renderQueue.hasPending()) {
      requestAnimationFrame(() => this.renderDeferred());
    }
  }
  
  // Optimized label placement
  private optimizeLabelPlacement(tiles: RenderedTile[]): void {
    const labelIndex = new LabelCollisionIndex();
    
    // Sort labels by priority
    const labels = tiles.flatMap(tile => tile.labels)
      .sort((a, b) => b.priority - a.priority);
    
    // Place labels avoiding collisions
    const placed: Label[] = [];
    for (const label of labels) {
      if (!labelIndex.collides(label.bounds)) {
        labelIndex.insert(label.bounds);
        placed.push(label);
      }
    }
    
    // Update visible labels
    this.updateVisibleLabels(placed);
  }
  
  // GPU optimization strategies
  private setupGPUOptimizations(): void {
    const gl = this.tileRenderer.getContext();
    
    // Enable GPU optimizations
    gl.enable(gl.DEPTH_TEST);
    gl.enable(gl.CULL_FACE);
    gl.cullFace(gl.BACK);
    
    // Use vertex array objects for better performance
    if (gl.createVertexArray) {
      this.tileRenderer.useVAO = true;
    }
    
    // Enable instanced rendering for repeated features
    if (gl.drawArraysInstanced) {
      this.tileRenderer.useInstancing = true;
    }
    
    // Optimize texture usage
    this.setupTextureAtlas();
  }
  
  // Battery optimization
  private optimizeForBattery(batteryLevel: number): void {
    if (batteryLevel < 0.2) { // Less than 20% battery
      // Reduce render frequency
      this.frameScheduler.setTargetFPS(30);
      
      // Disable non-essential layers
      this.tileRenderer.disableLayers(['3d-buildings', 'terrain-shading']);
      
      // Reduce tile prefetch radius
      this.tileLoader.setPrefetchRadius(2000); // 2km instead of 5km
      
      // Use lower quality textures
      this.tileRenderer.setTextureQuality('low');
    }
  }
}

// Performance monitoring
class PerformanceMonitor {
  private frameTimings: number[] = [];
  private tileLoadTimings: Map<string, number> = new Map();
  
  recordFrame(duration: number): void {
    this.frameTimings.push(duration);
    if (this.frameTimings.length > 60) {
      this.frameTimings.shift();
    }
    
    // Check for performance issues
    if (duration > 33) { // Missing 30fps target
      console.warn(`Slow frame: ${duration.toFixed(2)}ms`);
      this.analyzePerformanceIssue();
    }
  }
  
  getMetrics(): PerformanceMetrics {
    const avgFrameTime = this.frameTimings.reduce((a, b) => a + b, 0) / this.frameTimings.length;
    const p95FrameTime = this.percentile(this.frameTimings, 0.95);
    
    return {
      avgFPS: 1000 / avgFrameTime,
      p95FPS: 1000 / p95FrameTime,
      droppedFrames: this.frameTimings.filter(t => t > 16.67).length,
      avgTileLoadTime: this.getAvgTileLoadTime()
    };
  }
}
```

### Memory Optimization Strategies

```typescript
// Tile memory pooling
class TileMemoryPool {
  private pool: VectorTile[] = [];
  private maxPoolSize: number = 50;
  
  acquireTile(): VectorTile {
    if (this.pool.length > 0) {
      return this.pool.pop()!;
    }
    return new VectorTile();
  }
  
  releaseTile(tile: VectorTile): void {
    tile.clear(); // Clear tile data
    if (this.pool.length < this.maxPoolSize) {
      this.pool.push(tile);
    }
  }
}

// Texture atlas for reduced draw calls
class TextureAtlasManager {
  private atlas: TextureAtlas;
  private iconMap: Map<string, AtlasRegion> = new Map();
  
  async buildAtlas(icons: string[]): Promise<void> {
    // Pack icons into texture atlas
    const packed = await this.packIcons(icons);
    
    // Create single texture
    this.atlas = await this.createTextureAtlas(packed);
    
    // Map icon names to atlas regions
    packed.regions.forEach(region => {
      this.iconMap.set(region.name, region);
    });
  }
  
  getIconUV(iconName: string): UV {
    const region = this.iconMap.get(iconName);
    if (!region) return { u: 0, v: 0, w: 0, h: 0 };
    
    return {
      u: region.x / this.atlas.width,
      v: region.y / this.atlas.height,
      w: region.width / this.atlas.width,
      h: region.height / this.atlas.height
    };
  }
}
```

## Storage Calculations and Budgeting

### Detailed Storage Analysis

```typescript
// Storage calculator for 1000-mile route
class RouteStorageCalculator {
  calculateStorage(route: Route): StorageEstimate {
    const segments = this.analyzeRoute(route);
    let totalSize = 0;
    
    segments.forEach(segment => {
      const tiles = this.calculateTilesForSegment(segment);
      const compressedSize = tiles.reduce((sum, tile) => {
        const baseSize = TILE_SIZE_BY_ZOOM[tile.zoom] || 30 * 1024;
        const compressionRatio = this.getCompressionRatio(tile);
        return sum + (baseSize * compressionRatio);
      }, 0);
      
      totalSize += compressedSize;
    });
    
    // Add overhead for MBTiles database
    const dbOverhead = totalSize * 0.05; // 5% overhead
    const totalWithOverhead = totalSize + dbOverhead;
    
    return {
      tileDataSize: totalSize,
      databaseOverhead: dbOverhead,
      totalSize: totalWithOverhead,
      tilesPerMile: this.calculateTilesPerMile(segments),
      bytesPerMile: totalWithOverhead / route.lengthMiles,
      estimatedCompressionRatio: 0.4 // 60% size reduction
    };
  }
  
  // Example calculation for 1000-mile route
  getTypicalRouteEstimate(): StorageBreakdown {
    return {
      highway: {
        miles: 700,
        zoomLevels: [8, 10, 11],
        tilesPerMile: 15,
        bytesPerMile: 500 * 1024, // 500KB/mile
        totalSize: 350 * 1024 * 1024 // 350MB
      },
      urban: {
        miles: 200,
        zoomLevels: [10, 12, 14, 16],
        tilesPerMile: 50,
        bytesPerMile: 1.5 * 1024 * 1024, // 1.5MB/mile
        totalSize: 300 * 1024 * 1024 // 300MB
      },
      rural: {
        miles: 100,
        zoomLevels: [8, 10, 12],
        tilesPerMile: 20,
        bytesPerMile: 700 * 1024, // 700KB/mile
        totalSize: 70 * 1024 * 1024 // 70MB
      },
      total: {
        miles: 1000,
        averageBytesPerMile: 720 * 1024, // 720KB/mile
        totalSize: 720 * 1024 * 1024, // 720MB (under 800MB target)
        compressionSavings: 480 * 1024 * 1024 // 480MB saved via compression
      }
    };
  }
}
```

## Implementation Checklist

```typescript
// Implementation priorities
const IMPLEMENTATION_PLAN = {
  phase1: {
    duration: '2 weeks',
    tasks: [
      'Implement MBTiles reader/writer',
      'Basic tile compression with Brotli',
      'Simple zoom level selection (fixed levels)',
      'Memory cache with LRU eviction'
    ]
  },
  phase2: {
    duration: '3 weeks',
    tasks: [
      'Dynamic zoom level optimization',
      'Progressive loading system',
      'Corridor-based region calculation',
      'Disk cache management'
    ]
  },
  phase3: {
    duration: '2 weeks',
    tasks: [
      'Performance optimizations',
      'Battery usage optimization',
      'Advanced compression strategies',
      'Predictive tile loading'
    ]
  },
  phase4: {
    duration: '1 week',
    tasks: [
      'Performance monitoring',
      'Storage analytics',
      'User settings for quality/storage trade-offs',
      'Testing and optimization'
    ]
  }
};
```

## Conclusion

This optimization strategy provides a comprehensive approach to achieving the <800MB per 1000 miles storage target while maintaining excellent map rendering performance. The key innovations include:

1. **Dynamic zoom level selection** based on route context
2. **Advanced compression** using Brotli with vector tile optimization
3. **Intelligent region calculation** using corridor-based boundaries
4. **Progressive loading** with predictive prefetching
5. **Multi-level caching** with context-aware eviction
6. **Performance optimizations** for smooth 60fps rendering

The strategy balances storage efficiency, rendering performance, and battery life to deliver an optimal offline mapping experience for road trip users.