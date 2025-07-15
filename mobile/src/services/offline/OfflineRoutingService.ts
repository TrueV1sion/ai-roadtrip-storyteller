/**
 * Offline Routing Service
 * Handles route calculation without internet connectivity
 */

import * as RNFS from 'react-native-fs';
import { Route, Location, RouteSegment } from '../../types/location';
import { mapTileManager } from './MapTileManager';
import { performanceMonitor } from '../performanceMonitor';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface RoutingNode {
  id: string;
  location: Location;
  connections: Map<string, RoutingEdge>;
}

interface RoutingEdge {
  targetId: string;
  distance: number;
  duration: number;
  roadType: string;
  speedLimit: number;
  elevation: number;
}

interface RoutingGraph {
  nodes: Map<string, RoutingNode>;
  quadTree: QuadTree;
  metadata: {
    version: string;
    region: string;
    lastUpdated: Date;
  };
}

interface RouteRequest {
  start: Location;
  end: Location;
  waypoints?: Location[];
  avoidHighways?: boolean;
  avoidTolls?: boolean;
  preferScenic?: boolean;
}

interface RouteResult {
  route: Route;
  alternatives: Route[];
  confidence: number;
}

// Quad tree for spatial indexing
class QuadTree {
  private root: QuadNode;
  private maxDepth: number = 12;
  
  constructor(bounds: { minLat: number; maxLat: number; minLon: number; maxLon: number }) {
    this.root = new QuadNode(bounds, 0);
  }
  
  insert(node: RoutingNode): void {
    this.root.insert(node, this.maxDepth);
  }
  
  findNearestNode(location: Location, maxDistance: number = 1000): RoutingNode | null {
    return this.root.findNearest(location, maxDistance);
  }
  
  findNodesInBounds(bounds: { minLat: number; maxLat: number; minLon: number; maxLon: number }): RoutingNode[] {
    return this.root.findInBounds(bounds);
  }
}

class QuadNode {
  private nodes: RoutingNode[] = [];
  private children: QuadNode[] | null = null;
  private maxNodesPerQuad = 50;
  
  constructor(
    private bounds: { minLat: number; maxLat: number; minLon: number; maxLon: number },
    private depth: number
  ) {}
  
  insert(node: RoutingNode, maxDepth: number): void {
    if (this.children) {
      const childIndex = this.getChildIndex(node.location);
      this.children[childIndex].insert(node, maxDepth);
      return;
    }
    
    this.nodes.push(node);
    
    if (this.nodes.length > this.maxNodesPerQuad && this.depth < maxDepth) {
      this.subdivide();
    }
  }
  
  findNearest(location: Location, maxDistance: number): RoutingNode | null {
    let nearest: RoutingNode | null = null;
    let minDistance = maxDistance;
    
    if (this.children) {
      // Search children
      for (const child of this.children) {
        if (this.boundsIntersectCircle(child.bounds, location, maxDistance)) {
          const childNearest = child.findNearest(location, minDistance);
          if (childNearest) {
            const distance = this.calculateDistance(location, childNearest.location);
            if (distance < minDistance) {
              nearest = childNearest;
              minDistance = distance;
            }
          }
        }
      }
    } else {
      // Search nodes in this quad
      for (const node of this.nodes) {
        const distance = this.calculateDistance(location, node.location);
        if (distance < minDistance) {
          nearest = node;
          minDistance = distance;
        }
      }
    }
    
    return nearest;
  }
  
  findInBounds(searchBounds: { minLat: number; maxLat: number; minLon: number; maxLon: number }): RoutingNode[] {
    const results: RoutingNode[] = [];
    
    if (!this.boundsIntersect(this.bounds, searchBounds)) {
      return results;
    }
    
    if (this.children) {
      for (const child of this.children) {
        results.push(...child.findInBounds(searchBounds));
      }
    } else {
      for (const node of this.nodes) {
        if (this.pointInBounds(node.location, searchBounds)) {
          results.push(node);
        }
      }
    }
    
    return results;
  }
  
  private subdivide(): void {
    const midLat = (this.bounds.minLat + this.bounds.maxLat) / 2;
    const midLon = (this.bounds.minLon + this.bounds.maxLon) / 2;
    
    this.children = [
      // NW
      new QuadNode({
        minLat: midLat,
        maxLat: this.bounds.maxLat,
        minLon: this.bounds.minLon,
        maxLon: midLon
      }, this.depth + 1),
      // NE
      new QuadNode({
        minLat: midLat,
        maxLat: this.bounds.maxLat,
        minLon: midLon,
        maxLon: this.bounds.maxLon
      }, this.depth + 1),
      // SW
      new QuadNode({
        minLat: this.bounds.minLat,
        maxLat: midLat,
        minLon: this.bounds.minLon,
        maxLon: midLon
      }, this.depth + 1),
      // SE
      new QuadNode({
        minLat: this.bounds.minLat,
        maxLat: midLat,
        minLon: midLon,
        maxLon: this.bounds.maxLon
      }, this.depth + 1)
    ];
    
    // Redistribute nodes
    for (const node of this.nodes) {
      const childIndex = this.getChildIndex(node.location);
      this.children[childIndex].nodes.push(node);
    }
    
    this.nodes = [];
  }
  
  private getChildIndex(location: Location): number {
    const midLat = (this.bounds.minLat + this.bounds.maxLat) / 2;
    const midLon = (this.bounds.minLon + this.bounds.maxLon) / 2;
    
    if (location.latitude >= midLat) {
      return location.longitude >= midLon ? 1 : 0; // NE : NW
    } else {
      return location.longitude >= midLon ? 3 : 2; // SE : SW
    }
  }
  
  private boundsIntersect(a: any, b: any): boolean {
    return !(
      a.maxLat < b.minLat ||
      a.minLat > b.maxLat ||
      a.maxLon < b.minLon ||
      a.minLon > b.maxLon
    );
  }
  
  private boundsIntersectCircle(bounds: any, center: Location, radius: number): boolean {
    // Convert radius from meters to approximate degrees
    const radiusDegrees = radius / 111111; // Rough approximation
    
    const circleBounds = {
      minLat: center.latitude - radiusDegrees,
      maxLat: center.latitude + radiusDegrees,
      minLon: center.longitude - radiusDegrees,
      maxLon: center.longitude + radiusDegrees
    };
    
    return this.boundsIntersect(bounds, circleBounds);
  }
  
  private pointInBounds(point: Location, bounds: any): boolean {
    return (
      point.latitude >= bounds.minLat &&
      point.latitude <= bounds.maxLat &&
      point.longitude >= bounds.minLon &&
      point.longitude <= bounds.maxLon
    );
  }
  
  private calculateDistance(a: Location, b: Location): number {
    const R = 6371000; // Earth radius in meters
    const lat1 = a.latitude * Math.PI / 180;
    const lat2 = b.latitude * Math.PI / 180;
    const deltaLat = (b.latitude - a.latitude) * Math.PI / 180;
    const deltaLon = (b.longitude - a.longitude) * Math.PI / 180;
    
    const h = Math.sin(deltaLat / 2) * Math.sin(deltaLat / 2) +
              Math.cos(lat1) * Math.cos(lat2) *
              Math.sin(deltaLon / 2) * Math.sin(deltaLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h));
    
    return R * c;
  }
}

class OfflineRoutingService {
  private static instance: OfflineRoutingService;
  private routingGraph: RoutingGraph | null = null;
  private graphPath = `${RNFS.DocumentDirectoryPath}/routing_graph.dat`;
  private routeCache: Map<string, RouteResult> = new Map();
  private readonly maxCacheSize = 100;
  
  private constructor() {
    this.loadRoutingGraph();
  }
  
  static getInstance(): OfflineRoutingService {
    if (!OfflineRoutingService.instance) {
      OfflineRoutingService.instance = new OfflineRoutingService();
    }
    return OfflineRoutingService.instance;
  }
  
  /**
   * Load routing graph from storage
   */
  private async loadRoutingGraph(): Promise<void> {
    try {
      const exists = await RNFS.exists(this.graphPath);
      if (!exists) {
        console.log('No offline routing graph found');
        return;
      }
      
      const data = await RNFS.readFile(this.graphPath, 'utf8');
      const graphData = JSON.parse(data);
      
      // Reconstruct graph
      this.routingGraph = {
        nodes: new Map(),
        quadTree: new QuadTree({
          minLat: -90,
          maxLat: 90,
          minLon: -180,
          maxLon: 180
        }),
        metadata: graphData.metadata
      };
      
      // Load nodes
      for (const nodeData of graphData.nodes) {
        const node: RoutingNode = {
          id: nodeData.id,
          location: nodeData.location,
          connections: new Map(nodeData.connections)
        };
        this.routingGraph.nodes.set(node.id, node);
        this.routingGraph.quadTree.insert(node);
      }
      
      console.log(`Loaded routing graph with ${this.routingGraph.nodes.size} nodes`);
      
    } catch (error) {
      console.error('Failed to load routing graph:', error);
    }
  }
  
  /**
   * Calculate route offline
   */
  async calculateRoute(request: RouteRequest): Promise<RouteResult | null> {
    const startTime = Date.now();
    
    // Check cache first
    const cacheKey = this.getCacheKey(request);
    const cached = this.routeCache.get(cacheKey);
    if (cached) {
      performanceMonitor.logEvent('offline_route_cache_hit', { cacheKey });
      return cached;
    }
    
    if (!this.routingGraph) {
      console.error('No routing graph available');
      return null;
    }
    
    try {
      // Find nearest nodes
      const startNode = this.routingGraph.quadTree.findNearestNode(request.start);
      const endNode = this.routingGraph.quadTree.findNearestNode(request.end);
      
      if (!startNode || !endNode) {
        console.error('Could not find route nodes');
        return null;
      }
      
      // Calculate main route
      const mainRoute = await this.calculateRouteAStar(
        startNode,
        endNode,
        request
      );
      
      if (!mainRoute) {
        return null;
      }
      
      // Calculate alternatives
      const alternatives = await this.calculateAlternativeRoutes(
        startNode,
        endNode,
        request,
        mainRoute
      );
      
      const result: RouteResult = {
        route: mainRoute,
        alternatives,
        confidence: this.calculateConfidence(mainRoute)
      };
      
      // Cache result
      this.cacheRoute(cacheKey, result);
      
      // Log performance
      performanceMonitor.logEvent('offline_route_calculated', {
        duration: Date.now() - startTime,
        distance: mainRoute.distanceMeters,
        nodeCount: mainRoute.points.length
      });
      
      return result;
      
    } catch (error) {
      console.error('Route calculation failed:', error);
      return null;
    }
  }
  
  /**
   * A* pathfinding algorithm
   */
  private async calculateRouteAStar(
    start: RoutingNode,
    end: RoutingNode,
    request: RouteRequest
  ): Promise<Route | null> {
    const openSet = new Map<string, { node: RoutingNode; f: number; g: number; parent: string | null }>();
    const closedSet = new Set<string>();
    
    // Initialize with start node
    openSet.set(start.id, {
      node: start,
      f: this.heuristic(start.location, end.location),
      g: 0,
      parent: null
    });
    
    while (openSet.size > 0) {
      // Get node with lowest f score
      let current = this.getLowestFScore(openSet);
      if (!current) break;
      
      // Check if we reached the end
      if (current.node.id === end.id) {
        return this.reconstructRoute(current, openSet, start, end);
      }
      
      // Move to closed set
      openSet.delete(current.node.id);
      closedSet.add(current.node.id);
      
      // Explore neighbors
      for (const [neighborId, edge] of current.node.connections) {
        if (closedSet.has(neighborId)) continue;
        
        // Check constraints
        if (request.avoidHighways && edge.roadType === 'highway') continue;
        if (request.avoidTolls && edge.roadType === 'toll') continue;
        
        const neighbor = this.routingGraph!.nodes.get(neighborId);
        if (!neighbor) continue;
        
        const tentativeG = current.g + edge.distance;
        
        const existing = openSet.get(neighborId);
        if (!existing || tentativeG < existing.g) {
          const f = tentativeG + this.heuristic(neighbor.location, end.location);
          
          openSet.set(neighborId, {
            node: neighbor,
            f,
            g: tentativeG,
            parent: current.node.id
          });
        }
      }
    }
    
    return null;
  }
  
  /**
   * Calculate alternative routes
   */
  private async calculateAlternativeRoutes(
    start: RoutingNode,
    end: RoutingNode,
    request: RouteRequest,
    mainRoute: Route
  ): Promise<Route[]> {
    const alternatives: Route[] = [];
    
    // Try different routing strategies
    const strategies = [
      { ...request, preferScenic: true },
      { ...request, avoidHighways: !request.avoidHighways }
    ];
    
    for (const strategy of strategies) {
      const route = await this.calculateRouteAStar(start, end, strategy);
      if (route && this.isSignificantlyDifferent(route, mainRoute)) {
        alternatives.push(route);
      }
      
      if (alternatives.length >= 2) break;
    }
    
    return alternatives;
  }
  
  /**
   * Reconstruct route from A* result
   */
  private reconstructRoute(
    end: any,
    openSet: Map<string, any>,
    startNode: RoutingNode,
    endNode: RoutingNode
  ): Route {
    const points: Location[] = [];
    const segments: RouteSegment[] = [];
    let current = end;
    let totalDistance = 0;
    let totalDuration = 0;
    
    // Trace back path
    const path: string[] = [];
    while (current) {
      path.unshift(current.node.id);
      if (current.parent) {
        current = openSet.get(current.parent) || { node: this.routingGraph!.nodes.get(current.parent) };
      } else {
        break;
      }
    }
    
    // Build route
    for (let i = 0; i < path.length; i++) {
      const node = this.routingGraph!.nodes.get(path[i])!;
      points.push(node.location);
      
      if (i > 0) {
        const prevNode = this.routingGraph!.nodes.get(path[i - 1])!;
        const edge = prevNode.connections.get(path[i])!;
        
        totalDistance += edge.distance;
        totalDuration += edge.duration;
        
        segments.push({
          startIndex: i - 1,
          endIndex: i,
          distance: edge.distance,
          duration: edge.duration,
          roadType: edge.roadType,
          speedLimit: edge.speedLimit,
          isUrban: edge.speedLimit < 45,
          hasComplexIntersections: false,
          elevation: edge.elevation
        });
      }
    }
    
    return {
      id: `offline_${Date.now()}`,
      points,
      segments,
      distanceMeters: totalDistance,
      durationSeconds: totalDuration,
      lengthMiles: totalDistance / 1609.34,
      source: 'offline',
      confidence: 0.8
    };
  }
  
  /**
   * Heuristic function for A*
   */
  private heuristic(a: Location, b: Location): number {
    // Use straight-line distance as heuristic
    const R = 6371000;
    const lat1 = a.latitude * Math.PI / 180;
    const lat2 = b.latitude * Math.PI / 180;
    const deltaLat = (b.latitude - a.latitude) * Math.PI / 180;
    const deltaLon = (b.longitude - a.longitude) * Math.PI / 180;
    
    const h = Math.sin(deltaLat / 2) * Math.sin(deltaLat / 2) +
              Math.cos(lat1) * Math.cos(lat2) *
              Math.sin(deltaLon / 2) * Math.sin(deltaLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h));
    
    return R * c;
  }
  
  /**
   * Get node with lowest f score
   */
  private getLowestFScore(openSet: Map<string, any>): any {
    let lowest = null;
    let lowestF = Infinity;
    
    for (const [id, data] of openSet) {
      if (data.f < lowestF) {
        lowest = data;
        lowestF = data.f;
      }
    }
    
    return lowest;
  }
  
  /**
   * Check if route is significantly different
   */
  private isSignificantlyDifferent(route1: Route, route2: Route): boolean {
    // Routes are different if they differ by more than 20% in distance
    const distanceDiff = Math.abs(route1.distanceMeters - route2.distanceMeters);
    const avgDistance = (route1.distanceMeters + route2.distanceMeters) / 2;
    
    if (distanceDiff / avgDistance > 0.2) {
      return true;
    }
    
    // Check overlap percentage
    const overlap = this.calculateRouteOverlap(route1, route2);
    return overlap < 0.7; // Less than 70% overlap
  }
  
  /**
   * Calculate route overlap percentage
   */
  private calculateRouteOverlap(route1: Route, route2: Route): number {
    let overlapCount = 0;
    const threshold = 100; // 100 meters
    
    for (const point1 of route1.points) {
      for (const point2 of route2.points) {
        const distance = this.heuristic(point1, point2);
        if (distance < threshold) {
          overlapCount++;
          break;
        }
      }
    }
    
    return overlapCount / route1.points.length;
  }
  
  /**
   * Calculate route confidence
   */
  private calculateConfidence(route: Route): number {
    let confidence = 0.8; // Base confidence for offline
    
    // Adjust based on graph age
    if (this.routingGraph?.metadata.lastUpdated) {
      const ageMonths = (Date.now() - new Date(this.routingGraph.metadata.lastUpdated).getTime()) / (30 * 24 * 60 * 60 * 1000);
      confidence -= Math.min(ageMonths * 0.05, 0.3); // Reduce up to 30% for old data
    }
    
    // Adjust based on route complexity
    const complexityFactor = route.segments.length / route.lengthMiles;
    if (complexityFactor > 10) {
      confidence -= 0.1; // Complex route
    }
    
    return Math.max(confidence, 0.5);
  }
  
  /**
   * Generate cache key for route request
   */
  private getCacheKey(request: RouteRequest): string {
    const parts = [
      `${request.start.latitude.toFixed(4)},${request.start.longitude.toFixed(4)}`,
      `${request.end.latitude.toFixed(4)},${request.end.longitude.toFixed(4)}`,
      request.avoidHighways ? 'nh' : '',
      request.avoidTolls ? 'nt' : '',
      request.preferScenic ? 'sc' : ''
    ];
    
    if (request.waypoints) {
      request.waypoints.forEach(wp => {
        parts.push(`${wp.latitude.toFixed(4)},${wp.longitude.toFixed(4)}`);
      });
    }
    
    return parts.join('_');
  }
  
  /**
   * Cache route result
   */
  private cacheRoute(key: string, result: RouteResult): void {
    this.routeCache.set(key, result);
    
    // Maintain cache size
    if (this.routeCache.size > this.maxCacheSize) {
      const firstKey = this.routeCache.keys().next().value;
      this.routeCache.delete(firstKey);
    }
  }
  
  /**
   * Update routing graph from downloaded data
   */
  async updateRoutingGraph(regionBounds: any, graphData: any): Promise<void> {
    try {
      if (!this.routingGraph) {
        // Initialize new graph
        this.routingGraph = {
          nodes: new Map(),
          quadTree: new QuadTree({
            minLat: -90,
            maxLat: 90,
            minLon: -180,
            maxLon: 180
          }),
          metadata: {
            version: '1.0',
            region: 'mixed',
            lastUpdated: new Date()
          }
        };
      }
      
      // Merge new nodes
      let addedCount = 0;
      for (const nodeData of graphData.nodes) {
        const node: RoutingNode = {
          id: nodeData.id,
          location: nodeData.location,
          connections: new Map(nodeData.connections)
        };
        
        if (!this.routingGraph.nodes.has(node.id)) {
          this.routingGraph.nodes.set(node.id, node);
          this.routingGraph.quadTree.insert(node);
          addedCount++;
        }
      }
      
      console.log(`Added ${addedCount} new routing nodes`);
      
      // Persist to storage
      await this.saveRoutingGraph();
      
      // Clear cache as routes may have changed
      this.routeCache.clear();
      
    } catch (error) {
      console.error('Failed to update routing graph:', error);
    }
  }
  
  /**
   * Save routing graph to storage
   */
  private async saveRoutingGraph(): Promise<void> {
    if (!this.routingGraph) return;
    
    try {
      const graphData = {
        metadata: this.routingGraph.metadata,
        nodes: Array.from(this.routingGraph.nodes.values()).map(node => ({
          id: node.id,
          location: node.location,
          connections: Array.from(node.connections.entries())
        }))
      };
      
      await RNFS.writeFile(this.graphPath, JSON.stringify(graphData), 'utf8');
      
      console.log(`Saved routing graph with ${this.routingGraph.nodes.size} nodes`);
      
    } catch (error) {
      console.error('Failed to save routing graph:', error);
    }
  }
  
  /**
   * Get routing coverage for a region
   */
  getRoutingCoverage(bounds: any): {
    hasBasicCoverage: boolean;
    nodeCount: number;
    coveragePercent: number;
  } {
    if (!this.routingGraph) {
      return { hasBasicCoverage: false, nodeCount: 0, coveragePercent: 0 };
    }
    
    const nodesInBounds = this.routingGraph.quadTree.findNodesInBounds(bounds);
    const nodeCount = nodesInBounds.length;
    
    // Estimate coverage based on node density
    const area = (bounds.maxLat - bounds.minLat) * (bounds.maxLon - bounds.minLon);
    const expectedNodes = area * 1000; // Expected ~1000 nodes per degree square
    const coveragePercent = Math.min((nodeCount / expectedNodes) * 100, 100);
    
    return {
      hasBasicCoverage: nodeCount > 100,
      nodeCount,
      coveragePercent
    };
  }
  
  /**
   * Clear all cached data
   */
  clearCache(): void {
    this.routeCache.clear();
  }
}

// Export singleton instance
export const offlineRoutingService = OfflineRoutingService.getInstance();
