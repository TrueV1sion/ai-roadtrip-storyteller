/**
 * Story Pre-Generator Service
 * Pre-generates AI stories for offline access during road trips
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import * as RNFS from 'react-native-fs';
import { compress, decompress } from 'fflate';
import { Location, Route, RouteSegment } from '../../types/location';
import { offlineManager } from '../OfflineManager';
import { performanceMonitor } from '../performanceMonitor';
import { apiClient } from '../api/client';

import { logger } from '@/services/logger';
interface StoryPoint {
  id: string;
  location: Location;
  title: string;
  type: 'landmark' | 'scenic' | 'historical' | 'cultural' | 'nature';
  description: string;
  radius: number; // Trigger radius in meters
  priority: number;
}

interface PreGeneratedStory {
  id: string;
  storyPointId: string;
  voicePersonality: string;
  content: string;
  audioUrl?: string;
  duration: number;
  metadata: {
    generatedAt: Date;
    expiresAt: Date;
    tags: string[];
    sentiment: 'positive' | 'neutral' | 'educational';
  };
}

interface StoryBundle {
  routeId: string;
  stories: PreGeneratedStory[];
  storyPoints: StoryPoint[];
  metadata: {
    generatedAt: Date;
    routeLength: number;
    estimatedDuration: number;
    voicePersonalities: string[];
  };
}

interface GenerationProgress {
  routeId: string;
  totalPoints: number;
  generatedPoints: number;
  currentPoint: string;
  estimatedTimeRemaining: number;
  status: 'pending' | 'generating' | 'completed' | 'failed';
}

class StoryPreGenerator {
  private static instance: StoryPreGenerator;
  private storyCache: Map<string, StoryBundle> = new Map();
  private generationQueue: Map<string, GenerationProgress> = new Map();
  private isGenerating: boolean = false;
  private readonly storiesDirectory = `${RNFS.DocumentDirectoryPath}/offline_stories`;
  private readonly maxStoriesPerPoint = 3; // Multiple personalities
  private readonly storyExpirationDays = 30;
  
  // Voice personalities to pre-generate
  private readonly voicePersonalities = [
    'morgan_freeman',
    'david_attenborough',
    'friendly_guide'
  ];
  
  private constructor() {
    this.initializeStorage();
  }
  
  static getInstance(): StoryPreGenerator {
    if (!StoryPreGenerator.instance) {
      StoryPreGenerator.instance = new StoryPreGenerator();
    }
    return StoryPreGenerator.instance;
  }
  
  /**
   * Initialize storage
   */
  private async initializeStorage(): Promise<void> {
    try {
      const dirExists = await RNFS.exists(this.storiesDirectory);
      if (!dirExists) {
        await RNFS.mkdir(this.storiesDirectory);
      }
      
      // Load cached story metadata
      await this.loadCachedMetadata();
      
    } catch (error) {
      logger.error('Failed to initialize story storage:', error);
    }
  }
  
  /**
   * Pre-generate stories for a route
   */
  async preGenerateStoriesForRoute(route: Route): Promise<void> {
    const startTime = Date.now();
    
    // Check if already generating
    if (this.generationQueue.has(route.id)) {
      logger.debug('Already generating stories for route:', route.id);
      return;
    }
    
    // Extract story points from route
    const storyPoints = await this.extractStoryPoints(route);
    
    // Initialize progress
    const progress: GenerationProgress = {
      routeId: route.id,
      totalPoints: storyPoints.length,
      generatedPoints: 0,
      currentPoint: '',
      estimatedTimeRemaining: storyPoints.length * 5, // 5 seconds per point estimate
      status: 'pending'
    };
    
    this.generationQueue.set(route.id, progress);
    
    // Start generation if not already running
    if (!this.isGenerating) {
      this.processGenerationQueue();
    }
    
    performanceMonitor.logEvent('story_pregeneration_started', {
      routeId: route.id,
      storyPointCount: storyPoints.length,
      routeLength: route.lengthMiles
    });
  }
  
  /**
   * Extract story points from route
   */
  private async extractStoryPoints(route: Route): Promise<StoryPoint[]> {
    const storyPoints: StoryPoint[] = [];
    const pointSpacing = 5; // Miles between story points
    
    // Add start point
    storyPoints.push({
      id: `${route.id}_start`,
      location: route.points[0],
      title: 'Journey Begins',
      type: 'landmark',
      description: 'The start of your adventure',
      radius: 1000,
      priority: 10
    });
    
    // Sample points along route
    let accumulatedDistance = 0;
    for (let i = 0; i < route.segments.length; i++) {
      const segment = route.segments[i];
      accumulatedDistance += segment.distance / 1609.34; // Convert to miles
      
      if (accumulatedDistance >= pointSpacing) {
        const pointIndex = Math.min(segment.endIndex, route.points.length - 1);
        const location = route.points[pointIndex];
        
        // Determine story type based on segment
        const storyType = this.determineStoryType(segment, location);
        
        storyPoints.push({
          id: `${route.id}_point_${i}`,
          location,
          title: `Mile ${Math.round(accumulatedDistance)}`,
          type: storyType,
          description: `Story point along ${segment.roadType}`,
          radius: segment.isUrban ? 500 : 2000,
          priority: segment.hasComplexIntersections ? 8 : 5
        });
        
        accumulatedDistance = 0;
      }
    }
    
    // Add end point
    storyPoints.push({
      id: `${route.id}_end`,
      location: route.points[route.points.length - 1],
      title: 'Journey Complete',
      type: 'landmark',
      description: 'You have arrived at your destination',
      radius: 1000,
      priority: 10
    });
    
    // Enhance with POI data if available
    const enhancedPoints = await this.enhanceWithPOIData(storyPoints);
    
    return enhancedPoints;
  }
  
  /**
   * Process generation queue
   */
  private async processGenerationQueue(): Promise<void> {
    this.isGenerating = true;
    
    for (const [routeId, progress] of this.generationQueue) {
      if (progress.status === 'pending') {
        progress.status = 'generating';
        await this.generateStoriesForRoute(routeId);
      }
    }
    
    this.isGenerating = false;
  }
  
  /**
   * Generate stories for a specific route
   */
  private async generateStoriesForRoute(routeId: string): Promise<void> {
    const progress = this.generationQueue.get(routeId);
    if (!progress) return;
    
    try {
      // Get route data
      const routeData = await this.getRouteData(routeId);
      if (!routeData) {
        throw new Error('Route data not found');
      }
      
      const { route, storyPoints } = routeData;
      const stories: PreGeneratedStory[] = [];
      const generationStartTime = Date.now();
      
      // Generate stories for each point
      for (let i = 0; i < storyPoints.length; i++) {
        const point = storyPoints[i];
        progress.currentPoint = point.title;
        progress.generatedPoints = i;
        
        // Update time estimate
        const elapsed = (Date.now() - generationStartTime) / 1000;
        const avgTimePerPoint = elapsed / (i + 1);
        const remaining = (storyPoints.length - i - 1) * avgTimePerPoint;
        progress.estimatedTimeRemaining = Math.round(remaining);
        
        // Generate stories for each voice personality
        for (const personality of this.voicePersonalities) {
          try {
            const story = await this.generateSingleStory(point, personality, route);
            if (story) {
              stories.push(story);
            }
          } catch (error) {
            logger.error(`Failed to generate story for ${point.id} with ${personality}:`, error);
          }
        }
        
        // Notify progress
        this.notifyGenerationProgress(progress);
      }
      
      // Create story bundle
      const bundle: StoryBundle = {
        routeId,
        stories,
        storyPoints,
        metadata: {
          generatedAt: new Date(),
          routeLength: route.lengthMiles,
          estimatedDuration: route.durationSeconds,
          voicePersonalities: this.voicePersonalities
        }
      };
      
      // Save bundle
      await this.saveStoryBundle(bundle);
      
      // Mark as completed
      progress.status = 'completed';
      progress.generatedPoints = storyPoints.length;
      
      performanceMonitor.logEvent('story_pregeneration_completed', {
        routeId,
        storyCount: stories.length,
        duration: Date.now() - generationStartTime,
        bundleSize: JSON.stringify(bundle).length
      });
      
    } catch (error) {
      logger.error('Story generation failed:', error);
      progress.status = 'failed';
    }
  }
  
  /**
   * Generate a single story
   */
  private async generateSingleStory(
    point: StoryPoint,
    personality: string,
    route: Route
  ): Promise<PreGeneratedStory | null> {
    try {
      // Check if online
      const isOnline = await offlineManager.isOnline();
      if (!isOnline) {
        logger.debug('Cannot generate stories offline');
        return null;
      }
      
      // Call API to generate story
      const response = await apiClient.post('/stories/generate', {
        location: point.location,
        type: point.type,
        voicePersonality: personality,
        context: {
          routeId: route.id,
          pointTitle: point.title,
          description: point.description,
          nearbySegment: this.getNearbySegmentInfo(point.location, route)
        }
      });
      
      const story: PreGeneratedStory = {
        id: `${point.id}_${personality}_${Date.now()}`,
        storyPointId: point.id,
        voicePersonality: personality,
        content: response.data.content,
        audioUrl: response.data.audioUrl,
        duration: response.data.duration || 30,
        metadata: {
          generatedAt: new Date(),
          expiresAt: new Date(Date.now() + this.storyExpirationDays * 24 * 60 * 60 * 1000),
          tags: response.data.tags || [],
          sentiment: response.data.sentiment || 'neutral'
        }
      };
      
      return story;
      
    } catch (error) {
      logger.error('Failed to generate story:', error);
      return null;
    }
  }
  
  /**
   * Save story bundle to storage
   */
  private async saveStoryBundle(bundle: StoryBundle): Promise<void> {
    try {
      // Compress bundle
      const bundleJson = JSON.stringify(bundle);
      const compressed = await this.compressData(bundleJson);
      
      // Save to file
      const filePath = `${this.storiesDirectory}/${bundle.routeId}.stories`;
      await RNFS.writeFile(filePath, compressed, 'base64');
      
      // Update cache
      this.storyCache.set(bundle.routeId, bundle);
      
      // Save metadata
      await this.saveCachedMetadata();
      
      logger.debug(`Saved story bundle for route ${bundle.routeId}: ${bundle.stories.length} stories`);
      
    } catch (error) {
      logger.error('Failed to save story bundle:', error);
    }
  }
  
  /**
   * Load story bundle for route
   */
  async loadStoriesForRoute(routeId: string): Promise<StoryBundle | null> {
    // Check cache first
    const cached = this.storyCache.get(routeId);
    if (cached) {
      return cached;
    }
    
    try {
      // Load from file
      const filePath = `${this.storiesDirectory}/${routeId}.stories`;
      const exists = await RNFS.exists(filePath);
      
      if (!exists) {
        return null;
      }
      
      // Read and decompress
      const compressed = await RNFS.readFile(filePath, 'base64');
      const decompressed = await this.decompressData(compressed);
      const bundle: StoryBundle = JSON.parse(decompressed);
      
      // Check expiration
      const now = new Date();
      const validStories = bundle.stories.filter(story => 
        new Date(story.metadata.expiresAt) > now
      );
      
      if (validStories.length === 0) {
        // All stories expired
        await this.deleteStoryBundle(routeId);
        return null;
      }
      
      bundle.stories = validStories;
      
      // Update cache
      this.storyCache.set(routeId, bundle);
      
      return bundle;
      
    } catch (error) {
      logger.error('Failed to load story bundle:', error);
      return null;
    }
  }
  
  /**
   * Get story for current location
   */
  async getStoryForLocation(
    location: Location,
    routeId: string,
    voicePersonality: string
  ): Promise<PreGeneratedStory | null> {
    const bundle = await this.loadStoriesForRoute(routeId);
    if (!bundle) return null;
    
    // Find nearest story point
    let nearestPoint: StoryPoint | null = null;
    let minDistance = Infinity;
    
    for (const point of bundle.storyPoints) {
      const distance = this.calculateDistance(location, point.location);
      if (distance < point.radius && distance < minDistance) {
        nearestPoint = point;
        minDistance = distance;
      }
    }
    
    if (!nearestPoint) return null;
    
    // Find story for personality
    const story = bundle.stories.find(s => 
      s.storyPointId === nearestPoint!.id && 
      s.voicePersonality === voicePersonality
    );
    
    return story || null;
  }
  
  /**
   * Get generation progress
   */
  getGenerationProgress(routeId: string): GenerationProgress | null {
    return this.generationQueue.get(routeId) || null;
  }
  
  /**
   * Delete story bundle
   */
  private async deleteStoryBundle(routeId: string): Promise<void> {
    try {
      const filePath = `${this.storiesDirectory}/${routeId}.stories`;
      await RNFS.unlink(filePath);
      this.storyCache.delete(routeId);
      this.generationQueue.delete(routeId);
    } catch (error) {
      logger.error('Failed to delete story bundle:', error);
    }
  }
  
  /**
   * Get storage statistics
   */
  async getStorageStats(): Promise<{
    totalBundles: number;
    totalStories: number;
    totalSize: number;
    oldestBundle: Date | null;
    expiringCount: number;
  }> {
    let totalSize = 0;
    let totalStories = 0;
    let oldestDate: Date | null = null;
    let expiringCount = 0;
    const now = new Date();
    const expirationThreshold = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000); // 7 days
    
    for (const [routeId, bundle] of this.storyCache) {
      totalStories += bundle.stories.length;
      
      // Calculate size
      const bundleSize = JSON.stringify(bundle).length;
      totalSize += bundleSize;
      
      // Check oldest
      const generatedAt = new Date(bundle.metadata.generatedAt);
      if (!oldestDate || generatedAt < oldestDate) {
        oldestDate = generatedAt;
      }
      
      // Count expiring
      bundle.stories.forEach(story => {
        if (new Date(story.metadata.expiresAt) < expirationThreshold) {
          expiringCount++;
        }
      });
    }
    
    return {
      totalBundles: this.storyCache.size,
      totalStories,
      totalSize,
      oldestBundle: oldestDate,
      expiringCount
    };
  }
  
  // Helper methods
  
  private determineStoryType(segment: RouteSegment, location: Location): StoryPoint['type'] {
    if (segment.roadType === 'scenic') return 'scenic';
    if (segment.isUrban) return 'cultural';
    if (segment.elevation && Math.abs(segment.elevation) > 100) return 'nature';
    return 'historical';
  }
  
  private async enhanceWithPOIData(points: StoryPoint[]): Promise<StoryPoint[]> {
    // This would integrate with POI database or API
    // For now, return as-is
    return points;
  }
  
  private async getRouteData(routeId: string): Promise<{ route: Route; storyPoints: StoryPoint[] } | null> {
    // This would fetch from route storage
    // For now, return null
    return null;
  }
  
  private getNearbySegmentInfo(location: Location, route: Route): any {
    // Find segment containing this location
    for (const segment of route.segments) {
      const startPoint = route.points[segment.startIndex];
      const endPoint = route.points[segment.endIndex];
      
      // Simple check - in production would use more sophisticated point-to-line distance
      const distToStart = this.calculateDistance(location, startPoint);
      const distToEnd = this.calculateDistance(location, endPoint);
      const segmentLength = this.calculateDistance(startPoint, endPoint);
      
      if (distToStart + distToEnd < segmentLength * 1.1) {
        return {
          roadType: segment.roadType,
          speedLimit: segment.speedLimit,
          isUrban: segment.isUrban
        };
      }
    }
    
    return {};
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
  
  private async compressData(data: string): Promise<string> {
    return new Promise((resolve, reject) => {
      const uint8Array = new TextEncoder().encode(data);
      compress(uint8Array, { level: 6 }, (err, compressed) => {
        if (err) {
          reject(err);
        } else {
          // Convert to base64 for storage
          const base64 = btoa(String.fromCharCode(...compressed));
          resolve(base64);
        }
      });
    });
  }
  
  private async decompressData(base64: string): Promise<string> {
    return new Promise((resolve, reject) => {
      // Convert from base64
      const compressed = Uint8Array.from(atob(base64), c => c.charCodeAt(0));
      
      decompress(compressed, (err, decompressed) => {
        if (err) {
          reject(err);
        } else {
          const text = new TextDecoder().decode(decompressed);
          resolve(text);
        }
      });
    });
  }
  
  private async loadCachedMetadata(): Promise<void> {
    try {
      const metadata = await AsyncStorage.getItem('story_cache_metadata');
      if (metadata) {
        const parsed = JSON.parse(metadata);
        // Restore cache metadata
        for (const routeId of parsed.cachedRoutes || []) {
          // Lazy load bundles as needed
        }
      }
    } catch (error) {
      logger.error('Failed to load cache metadata:', error);
    }
  }
  
  private async saveCachedMetadata(): Promise<void> {
    try {
      const metadata = {
        cachedRoutes: Array.from(this.storyCache.keys()),
        lastUpdated: new Date()
      };
      await AsyncStorage.setItem('story_cache_metadata', JSON.stringify(metadata));
    } catch (error) {
      logger.error('Failed to save cache metadata:', error);
    }
  }
  
  private notifyGenerationProgress(progress: GenerationProgress): void {
    // Emit progress event
    offlineManager.emit('storyGenerationProgress', progress);
  }
  
  /**
   * Clear all cached stories
   */
  async clearAllStories(): Promise<void> {
    try {
      // Delete all story files
      const files = await RNFS.readDir(this.storiesDirectory);
      for (const file of files) {
        if (file.name.endsWith('.stories')) {
          await RNFS.unlink(file.path);
        }
      }
      
      // Clear cache
      this.storyCache.clear();
      this.generationQueue.clear();
      
      // Clear metadata
      await AsyncStorage.removeItem('story_cache_metadata');
      
      logger.debug('Cleared all cached stories');
      
    } catch (error) {
      logger.error('Failed to clear stories:', error);
    }
  }
}

// Export singleton instance
export const storyPreGenerator = StoryPreGenerator.getInstance();
