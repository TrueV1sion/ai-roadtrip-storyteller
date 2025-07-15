/**
 * AR Landmark Service
 * Handles landmark detection and information overlay for AR experiences
 */

import { arService } from '../arService';
import { locationService } from '../locationService';
import { cacheService } from '../cacheService';
import { voiceOrchestrationService } from '../voiceOrchestrationService';
import { performanceMonitor } from '../performanceMonitor';

export interface ARLandmark {
  id: string;
  name: string;
  type: 'landmark' | 'historical' | 'restaurant' | 'nature' | 'entertainment';
  location: {
    latitude: number;
    longitude: number;
    altitude?: number;
  };
  distance: number; // meters from user
  bearing: number; // degrees from north
  description: string;
  imageUrl?: string;
  rating?: number;
  category: string[];
  historicalInfo?: {
    year?: number;
    era?: string;
    significance?: string;
    imageUrl?: string;
  };
  screenPosition?: {
    x: number;
    y: number;
    visible: boolean;
  };
  confidence: number; // 0-1 detection confidence
}

export interface LandmarkCluster {
  id: string;
  landmarks: ARLandmark[];
  center: {
    latitude: number;
    longitude: number;
  };
  radius: number;
  screenPosition?: {
    x: number;
    y: number;
  };
}

interface LandmarkDetectionConfig {
  maxDistance: number; // Maximum detection distance in meters
  minConfidence: number; // Minimum confidence threshold
  clusteringEnabled: boolean;
  clusterRadius: number; // Radius for clustering in meters
  maxLandmarksVisible: number;
  enableHistoricalMode: boolean;
  enableVoiceDescriptions: boolean;
}

export class ARLandmarkService {
  private static instance: ARLandmarkService;
  private landmarks: Map<string, ARLandmark> = new Map();
  private clusters: Map<string, LandmarkCluster> = new Map();
  private config: LandmarkDetectionConfig;
  private lastUpdateTime: number = 0;
  private updateInterval: number = 1000; // 1 second
  private isProcessing: boolean = false;
  
  // Cache keys
  private readonly CACHE_PREFIX = 'ar_landmarks_';
  private readonly CACHE_TTL = 3600; // 1 hour
  
  private constructor() {
    this.config = {
      maxDistance: 1000, // 1km default
      minConfidence: 0.7,
      clusteringEnabled: true,
      clusterRadius: 50, // 50 meters
      maxLandmarksVisible: 10,
      enableHistoricalMode: true,
      enableVoiceDescriptions: true,
    };
  }
  
  static getInstance(): ARLandmarkService {
    if (!ARLandmarkService.instance) {
      ARLandmarkService.instance = new ARLandmarkService();
    }
    return ARLandmarkService.instance;
  }
  
  /**
   * Initialize landmark detection service
   */
  async initialize(config?: Partial<LandmarkDetectionConfig>): Promise<void> {
    if (config) {
      this.config = { ...this.config, ...config };
    }
    
    // Preload landmark data for current location
    const location = await locationService.getCurrentLocation();
    if (location) {
      await this.preloadLandmarksForLocation(
        location.latitude,
        location.longitude
      );
    }
  }
  
  /**
   * Update landmarks based on current location and camera orientation
   */
  async updateLandmarks(
    userLocation: { latitude: number; longitude: number },
    cameraOrientation: { heading: number; pitch: number; roll: number },
    viewportSize: { width: number; height: number }
  ): Promise<ARLandmark[]> {
    const now = Date.now();
    
    // Throttle updates
    if (now - this.lastUpdateTime < this.updateInterval) {
      return Array.from(this.landmarks.values());
    }
    
    // Prevent concurrent processing
    if (this.isProcessing) {
      return Array.from(this.landmarks.values());
    }
    
    this.isProcessing = true;
    this.lastUpdateTime = now;
    
    try {
      // Fetch nearby landmarks
      const nearbyLandmarks = await this.fetchNearbyLandmarks(
        userLocation.latitude,
        userLocation.longitude
      );
      
      // Update landmark positions and visibility
      const visibleLandmarks = this.calculateVisibleLandmarks(
        nearbyLandmarks,
        userLocation,
        cameraOrientation,
        viewportSize
      );
      
      // Apply clustering if enabled
      if (this.config.clusteringEnabled) {
        this.clusterLandmarks(visibleLandmarks);
      }
      
      // Limit number of visible landmarks
      const limitedLandmarks = this.limitVisibleLandmarks(visibleLandmarks);
      
      // Update stored landmarks
      this.updateStoredLandmarks(limitedLandmarks);
      
      // Trigger voice descriptions for new landmarks
      if (this.config.enableVoiceDescriptions) {
        await this.announceNewLandmarks(limitedLandmarks);
      }
      
      return limitedLandmarks;
    } catch (error) {
      console.error('Failed to update landmarks:', error);
      return Array.from(this.landmarks.values());
    } finally {
      this.isProcessing = false;
    }
  }
  
  /**
   * Fetch nearby landmarks from cache or API
   */
  private async fetchNearbyLandmarks(
    latitude: number,
    longitude: number
  ): Promise<ARLandmark[]> {
    const cacheKey = `${this.CACHE_PREFIX}${latitude.toFixed(3)}_${longitude.toFixed(3)}`;
    
    // Try cache first
    const cached = await cacheService.get<ARLandmark[]>(cacheKey);
    if (cached) {
      return cached;
    }
    
    // Fetch from AR service
    const arPoints = await arService.getARPoints(
      { latitude, longitude },
      this.config.maxDistance,
      ['landmark', 'historical', 'restaurant', 'nature', 'entertainment']
    );
    
    // Convert AR points to landmarks
    const landmarks = arPoints.map((point): ARLandmark => ({
      id: point.id,
      name: point.name,
      type: this.mapARTypeToLandmarkType(point.type),
      location: point.location,
      distance: this.calculateDistance(
        latitude,
        longitude,
        point.location.latitude,
        point.location.longitude
      ),
      bearing: this.calculateBearing(
        latitude,
        longitude,
        point.location.latitude,
        point.location.longitude
      ),
      description: point.description || '',
      imageUrl: point.metadata?.imageUrl,
      rating: point.metadata?.rating,
      category: point.metadata?.categories || [],
      historicalInfo: point.metadata?.historical,
      confidence: 1.0, // API results have full confidence
    }));
    
    // Cache results
    await cacheService.set(cacheKey, landmarks, this.CACHE_TTL);
    
    return landmarks;
  }
  
  /**
   * Calculate which landmarks are visible in current camera view
   */
  private calculateVisibleLandmarks(
    landmarks: ARLandmark[],
    userLocation: { latitude: number; longitude: number },
    cameraOrientation: { heading: number; pitch: number; roll: number },
    viewportSize: { width: number; height: number }
  ): ARLandmark[] {
    const fov = {
      horizontal: 60, // degrees
      vertical: 45, // degrees
    };
    
    return landmarks
      .map((landmark) => {
        // Calculate relative bearing
        const relativeBearing = this.normalizeAngle(
          landmark.bearing - cameraOrientation.heading
        );
        
        // Check if within horizontal FOV
        if (Math.abs(relativeBearing) > fov.horizontal / 2) {
          return { ...landmark, screenPosition: { x: 0, y: 0, visible: false } };
        }
        
        // Calculate elevation angle
        const elevationAngle = this.calculateElevationAngle(
          userLocation,
          landmark.location,
          landmark.distance
        );
        
        // Check if within vertical FOV
        const relativeElevation = elevationAngle - cameraOrientation.pitch;
        if (Math.abs(relativeElevation) > fov.vertical / 2) {
          return { ...landmark, screenPosition: { x: 0, y: 0, visible: false } };
        }
        
        // Calculate screen position
        const x = viewportSize.width / 2 + 
          (relativeBearing / (fov.horizontal / 2)) * (viewportSize.width / 2);
        const y = viewportSize.height / 2 - 
          (relativeElevation / (fov.vertical / 2)) * (viewportSize.height / 2);
        
        return {
          ...landmark,
          screenPosition: {
            x: Math.round(x),
            y: Math.round(y),
            visible: true,
          },
        };
      })
      .filter((landmark) => landmark.screenPosition?.visible);
  }
  
  /**
   * Cluster nearby landmarks to prevent overlap
   */
  private clusterLandmarks(landmarks: ARLandmark[]): void {
    this.clusters.clear();
    
    const clustered = new Set<string>();
    
    landmarks.forEach((landmark) => {
      if (clustered.has(landmark.id)) return;
      
      // Find nearby landmarks
      const cluster: ARLandmark[] = [landmark];
      clustered.add(landmark.id);
      
      landmarks.forEach((other) => {
        if (clustered.has(other.id)) return;
        
        const distance = this.calculateDistance(
          landmark.location.latitude,
          landmark.location.longitude,
          other.location.latitude,
          other.location.longitude
        );
        
        if (distance <= this.config.clusterRadius) {
          cluster.push(other);
          clustered.add(other.id);
        }
      });
      
      // Create cluster if multiple landmarks
      if (cluster.length > 1) {
        const clusterId = `cluster_${cluster.map(l => l.id).join('_')}`;
        const center = this.calculateClusterCenter(cluster);
        
        this.clusters.set(clusterId, {
          id: clusterId,
          landmarks: cluster,
          center,
          radius: this.config.clusterRadius,
          screenPosition: cluster[0].screenPosition, // Use first landmark's position
        });
      }
    });
  }
  
  /**
   * Limit number of visible landmarks based on priority
   */
  private limitVisibleLandmarks(landmarks: ARLandmark[]): ARLandmark[] {
    if (landmarks.length <= this.config.maxLandmarksVisible) {
      return landmarks;
    }
    
    // Sort by priority (distance, rating, type)
    return landmarks
      .sort((a, b) => {
        // Prioritize historical in historical mode
        if (this.config.enableHistoricalMode) {
          if (a.type === 'historical' && b.type !== 'historical') return -1;
          if (b.type === 'historical' && a.type !== 'historical') return 1;
        }
        
        // Then by rating
        const ratingDiff = (b.rating || 0) - (a.rating || 0);
        if (Math.abs(ratingDiff) > 0.5) return ratingDiff;
        
        // Finally by distance
        return a.distance - b.distance;
      })
      .slice(0, this.config.maxLandmarksVisible);
  }
  
  /**
   * Update stored landmarks map
   */
  private updateStoredLandmarks(landmarks: ARLandmark[]): void {
    // Mark existing landmarks as not visible
    this.landmarks.forEach((landmark) => {
      if (landmark.screenPosition) {
        landmark.screenPosition.visible = false;
      }
    });
    
    // Update with new landmarks
    landmarks.forEach((landmark) => {
      this.landmarks.set(landmark.id, landmark);
    });
  }
  
  /**
   * Announce new landmarks via voice
   */
  private async announceNewLandmarks(landmarks: ARLandmark[]): Promise<void> {
    const newLandmarks = landmarks.filter(
      (landmark) => !this.landmarks.has(landmark.id)
    );
    
    if (newLandmarks.length === 0) return;
    
    // Announce first new landmark
    const landmark = newLandmarks[0];
    const announcement = this.generateLandmarkAnnouncement(landmark);
    
    await voiceOrchestrationService.speak(announcement, {
      priority: 'low',
      interruptible: true,
    });
  }
  
  /**
   * Generate voice announcement for landmark
   */
  private generateLandmarkAnnouncement(landmark: ARLandmark): string {
    const direction = this.bearingToCompass(landmark.bearing);
    const distance = this.formatDistance(landmark.distance);
    
    let announcement = `${landmark.name} is ${distance} to your ${direction}.`;
    
    if (landmark.type === 'historical' && landmark.historicalInfo?.year) {
      announcement += ` Built in ${landmark.historicalInfo.year}.`;
    }
    
    if (landmark.rating && landmark.rating >= 4.5) {
      announcement += ' Highly rated.';
    }
    
    return announcement;
  }
  
  /**
   * Get landmark by ID
   */
  getLandmark(id: string): ARLandmark | undefined {
    return this.landmarks.get(id);
  }
  
  /**
   * Get all visible landmarks
   */
  getVisibleLandmarks(): ARLandmark[] {
    return Array.from(this.landmarks.values()).filter(
      (landmark) => landmark.screenPosition?.visible
    );
  }
  
  /**
   * Get clusters
   */
  getClusters(): LandmarkCluster[] {
    return Array.from(this.clusters.values());
  }
  
  /**
   * Enable/disable historical mode
   */
  setHistoricalMode(enabled: boolean): void {
    this.config.enableHistoricalMode = enabled;
    this.landmarks.clear(); // Force refresh
  }
  
  /**
   * Preload landmarks for a location
   */
  private async preloadLandmarksForLocation(
    latitude: number,
    longitude: number
  ): Promise<void> {
    try {
      await this.fetchNearbyLandmarks(latitude, longitude);
    } catch (error) {
      console.error('Failed to preload landmarks:', error);
    }
  }
  
  // Utility functions
  
  private calculateDistance(
    lat1: number,
    lon1: number,
    lat2: number,
    lon2: number
  ): number {
    const R = 6371e3; // Earth radius in meters
    const φ1 = (lat1 * Math.PI) / 180;
    const φ2 = (lat2 * Math.PI) / 180;
    const Δφ = ((lat2 - lat1) * Math.PI) / 180;
    const Δλ = ((lon2 - lon1) * Math.PI) / 180;
    
    const a =
      Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
      Math.cos(φ1) * Math.cos(φ2) * Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    
    return R * c;
  }
  
  private calculateBearing(
    lat1: number,
    lon1: number,
    lat2: number,
    lon2: number
  ): number {
    const φ1 = (lat1 * Math.PI) / 180;
    const φ2 = (lat2 * Math.PI) / 180;
    const Δλ = ((lon2 - lon1) * Math.PI) / 180;
    
    const y = Math.sin(Δλ) * Math.cos(φ2);
    const x =
      Math.cos(φ1) * Math.sin(φ2) -
      Math.sin(φ1) * Math.cos(φ2) * Math.cos(Δλ);
    
    const θ = Math.atan2(y, x);
    
    return ((θ * 180) / Math.PI + 360) % 360;
  }
  
  private calculateElevationAngle(
    userLocation: { latitude: number; longitude: number },
    landmarkLocation: { latitude: number; longitude: number; altitude?: number },
    distance: number
  ): number {
    // Simplified calculation assuming flat earth for short distances
    const heightDifference = (landmarkLocation.altitude || 0) - 0; // Assume user at sea level
    return (Math.atan2(heightDifference, distance) * 180) / Math.PI;
  }
  
  private normalizeAngle(angle: number): number {
    while (angle > 180) angle -= 360;
    while (angle < -180) angle += 360;
    return angle;
  }
  
  private calculateClusterCenter(landmarks: ARLandmark[]): {
    latitude: number;
    longitude: number;
  } {
    const sumLat = landmarks.reduce((sum, l) => sum + l.location.latitude, 0);
    const sumLon = landmarks.reduce((sum, l) => sum + l.location.longitude, 0);
    
    return {
      latitude: sumLat / landmarks.length,
      longitude: sumLon / landmarks.length,
    };
  }
  
  private bearingToCompass(bearing: number): string {
    const directions = ['north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest'];
    const index = Math.round(bearing / 45) % 8;
    return directions[index];
  }
  
  private formatDistance(meters: number): string {
    if (meters < 100) {
      return `${Math.round(meters)} meters`;
    } else if (meters < 1000) {
      return `${Math.round(meters / 10) * 10} meters`;
    } else {
      return `${(meters / 1000).toFixed(1)} kilometers`;
    }
  }
  
  private mapARTypeToLandmarkType(
    arType: string
  ): ARLandmark['type'] {
    const typeMap: Record<string, ARLandmark['type']> = {
      landmark: 'landmark',
      historical: 'historical',
      restaurant: 'restaurant',
      nature: 'nature',
      entertainment: 'entertainment',
    };
    
    return typeMap[arType] || 'landmark';
  }
}

// Export singleton instance
export const arLandmarkService = ARLandmarkService.getInstance();
