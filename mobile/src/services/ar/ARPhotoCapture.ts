/**
 * AR Photo Capture Service
 * Handles capturing photos with AR overlays and journey documentation
 */

import { Image } from 'react-native';
import RNFS from 'react-native-fs';
import { format } from 'date-fns';
import Canvas from 'react-native-canvas';
import { ARLandmark } from './ARLandmarkService';
import { locationService } from '../locationService';
import { tripMemoryService } from '../tripMemoryService';
import { performanceMonitor } from '../performanceMonitor';

import { logger } from '@/services/logger';
export interface ARPhotoMetadata {
  id: string;
  timestamp: Date;
  location: {
    latitude: number;
    longitude: number;
    name?: string;
  };
  landmarks: ARLandmark[];
  journey?: {
    tripId: string;
    elapsed: number;
    milestone?: string;
  };
  weather?: {
    condition: string;
    temperature: number;
  };
  story?: {
    context: string;
    quote?: string;
  };
}

export interface ARPhotoFrame {
  type: 'minimal' | 'detailed' | 'story' | 'milestone';
  includeDate: boolean;
  includeLocation: boolean;
  includeLandmarks: boolean;
  includeWeather: boolean;
  includeQuote: boolean;
  customText?: string;
}

export interface PhotoCaptureResult {
  originalPath: string;
  processedPath: string;
  thumbnailPath: string;
  metadata: ARPhotoMetadata;
  shareUrl?: string;
}

export class ARPhotoCaptureService {
  private static instance: ARPhotoCaptureService;
  private photosDirectory: string;
  private processingQueue: Array<() => Promise<void>> = [];
  private isProcessing: boolean = false;
  
  // Photo settings
  private readonly PHOTO_QUALITY = 0.9;
  private readonly THUMBNAIL_SIZE = 200;
  private readonly MAX_DIMENSION = 2048;
  
  // Frame styles
  private readonly frameStyles = {
    minimal: {
      padding: 20,
      fontSize: 14,
      opacity: 0.8,
    },
    detailed: {
      padding: 30,
      fontSize: 16,
      opacity: 0.9,
    },
    story: {
      padding: 40,
      fontSize: 18,
      opacity: 0.95,
    },
    milestone: {
      padding: 50,
      fontSize: 20,
      opacity: 1.0,
    },
  };
  
  private constructor() {
    this.photosDirectory = `${RNFS.DocumentDirectoryPath}/ar_photos`;
    this.ensureDirectoryExists();
  }
  
  static getInstance(): ARPhotoCaptureService {
    if (!ARPhotoCaptureService.instance) {
      ARPhotoCaptureService.instance = new ARPhotoCaptureService();
    }
    return ARPhotoCaptureService.instance;
  }
  
  /**
   * Capture AR photo with overlays
   */
  async captureARPhoto(
    photoPath: string,
    landmarks: ARLandmark[],
    frame: ARPhotoFrame = {
      type: 'minimal',
      includeDate: true,
      includeLocation: true,
      includeLandmarks: true,
      includeWeather: false,
      includeQuote: false,
    }
  ): Promise<PhotoCaptureResult> {
    const startTime = Date.now();
    
    try {
      // Generate metadata
      const metadata = await this.generatePhotoMetadata(landmarks);
      
      // Process photo with AR overlays
      const processedPath = await this.processPhotoWithOverlays(
        photoPath,
        metadata,
        frame
      );
      
      // Generate thumbnail
      const thumbnailPath = await this.generateThumbnail(processedPath);
      
      // Save to trip memories
      await this.saveToTripMemory(processedPath, metadata);
      
      // Log capture metrics
      performanceMonitor.logEvent('ar_photo_captured', {
        processingTime: Date.now() - startTime,
        landmarks: landmarks.length,
        frameType: frame.type,
      });
      
      return {
        originalPath: photoPath,
        processedPath,
        thumbnailPath,
        metadata,
      };
    } catch (error) {
      logger.error('AR photo capture failed:', error);
      throw error;
    }
  }
  
  /**
   * Generate photo metadata
   */
  private async generatePhotoMetadata(
    landmarks: ARLandmark[]
  ): Promise<ARPhotoMetadata> {
    const location = await locationService.getCurrentLocation();
    const currentTrip = await tripMemoryService.getCurrentTrip();
    
    const metadata: ARPhotoMetadata = {
      id: `ar_photo_${Date.now()}`,
      timestamp: new Date(),
      location: {
        latitude: location.latitude,
        longitude: location.longitude,
        name: location.name,
      },
      landmarks: landmarks.filter(l => l.screenPosition?.visible),
    };
    
    // Add journey info if on a trip
    if (currentTrip) {
      metadata.journey = {
        tripId: currentTrip.id,
        elapsed: Date.now() - currentTrip.startTime.getTime(),
        milestone: await this.detectMilestone(currentTrip),
      };
    }
    
    // Add weather if available
    const weather = await this.getCurrentWeather(location);
    if (weather) {
      metadata.weather = weather;
    }
    
    // Add story context
    if (landmarks.length > 0) {
      metadata.story = {
        context: await this.generateStoryContext(landmarks),
        quote: await this.generateQuote(landmarks[0]),
      };
    }
    
    return metadata;
  }
  
  /**
   * Process photo with AR overlays
   */
  private async processPhotoWithOverlays(
    originalPath: string,
    metadata: ARPhotoMetadata,
    frame: ARPhotoFrame
  ): Promise<string> {
    return new Promise((resolve, reject) => {
      Image.getSize(
        originalPath,
        async (width, height) => {
          try {
            // Create canvas
            const canvas = new Canvas(width, height);
            const ctx = canvas.getContext('2d');
            
            // Draw original photo
            const img = new Canvas.Image();
            img.src = originalPath;
            ctx.drawImage(img, 0, 0, width, height);
            
            // Apply frame overlay
            await this.drawFrameOverlay(ctx, width, height, metadata, frame);
            
            // Draw landmark overlays
            if (frame.includeLandmarks) {
              await this.drawLandmarkOverlays(ctx, metadata.landmarks, width, height);
            }
            
            // Save processed image
            const processedPath = `${this.photosDirectory}/processed_${Date.now()}.jpg`;
            const dataUrl = canvas.toDataURL('image/jpeg', this.PHOTO_QUALITY);
            const base64 = dataUrl.split(',')[1];
            
            await RNFS.writeFile(processedPath, base64, 'base64');
            resolve(processedPath);
          } catch (error) {
            reject(error);
          }
        },
        (error) => reject(error)
      );
    });
  }
  
  /**
   * Draw frame overlay on photo
   */
  private async drawFrameOverlay(
    ctx: CanvasRenderingContext2D,
    width: number,
    height: number,
    metadata: ARPhotoMetadata,
    frame: ARPhotoFrame
  ): Promise<void> {
    const style = this.frameStyles[frame.type];
    const padding = style.padding;
    
    // Semi-transparent overlay at bottom
    const overlayHeight = this.calculateOverlayHeight(frame);
    ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
    ctx.fillRect(0, height - overlayHeight, width, overlayHeight);
    
    // Text styling
    ctx.fillStyle = '#ffffff';
    ctx.font = `${style.fontSize}px SF Pro Display`;
    ctx.textAlign = 'left';
    
    let yOffset = height - overlayHeight + padding;
    
    // Date and time
    if (frame.includeDate) {
      const dateText = format(metadata.timestamp, 'MMMM d, yyyy • h:mm a');
      ctx.fillText(dateText, padding, yOffset);
      yOffset += style.fontSize + 10;
    }
    
    // Location
    if (frame.includeLocation && metadata.location.name) {
      ctx.fillText(`📍 ${metadata.location.name}`, padding, yOffset);
      yOffset += style.fontSize + 10;
    }
    
    // Weather
    if (frame.includeWeather && metadata.weather) {
      const weatherText = `${metadata.weather.condition} • ${metadata.weather.temperature}°`;
      ctx.fillText(weatherText, padding, yOffset);
      yOffset += style.fontSize + 10;
    }
    
    // Quote
    if (frame.includeQuote && metadata.story?.quote) {
      ctx.font = `italic ${style.fontSize}px Georgia`;
      ctx.fillStyle = `rgba(255, 255, 255, ${style.opacity})`;
      
      // Word wrap quote
      const words = metadata.story.quote.split(' ');
      let line = '';
      const maxWidth = width - padding * 2;
      
      words.forEach((word) => {
        const testLine = line + word + ' ';
        const metrics = ctx.measureText(testLine);
        
        if (metrics.width > maxWidth && line.length > 0) {
          ctx.fillText(line, padding, yOffset);
          line = word + ' ';
          yOffset += style.fontSize + 5;
        } else {
          line = testLine;
        }
      });
      
      if (line.length > 0) {
        ctx.fillText(line, padding, yOffset);
      }
    }
    
    // Custom text
    if (frame.customText) {
      ctx.font = `${style.fontSize}px SF Pro Display`;
      ctx.fillStyle = '#ffffff';
      ctx.fillText(frame.customText, padding, yOffset);
    }
    
    // Journey milestone badge
    if (frame.type === 'milestone' && metadata.journey?.milestone) {
      this.drawMilestoneBadge(ctx, width, height, metadata.journey.milestone);
    }
  }
  
  /**
   * Draw landmark overlays
   */
  private async drawLandmarkOverlays(
    ctx: CanvasRenderingContext2D,
    landmarks: ARLandmark[],
    width: number,
    height: number
  ): Promise<void> {
    landmarks.forEach((landmark) => {
      if (!landmark.screenPosition?.visible) return;
      
      const x = (landmark.screenPosition.x / 100) * width; // Convert percentage to pixels
      const y = (landmark.screenPosition.y / 100) * height;
      
      // Draw landmark bubble
      const bubbleWidth = 200;
      const bubbleHeight = 60;
      const bubbleX = Math.max(10, Math.min(x - bubbleWidth / 2, width - bubbleWidth - 10));
      const bubbleY = Math.max(10, y - bubbleHeight - 20);
      
      // Bubble background
      ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
      ctx.strokeStyle = 'rgba(0, 0, 0, 0.1)';
      ctx.lineWidth = 1;
      
      // Rounded rectangle
      const radius = 8;
      ctx.beginPath();
      ctx.moveTo(bubbleX + radius, bubbleY);
      ctx.lineTo(bubbleX + bubbleWidth - radius, bubbleY);
      ctx.quadraticCurveTo(bubbleX + bubbleWidth, bubbleY, bubbleX + bubbleWidth, bubbleY + radius);
      ctx.lineTo(bubbleX + bubbleWidth, bubbleY + bubbleHeight - radius);
      ctx.quadraticCurveTo(bubbleX + bubbleWidth, bubbleY + bubbleHeight, bubbleX + bubbleWidth - radius, bubbleY + bubbleHeight);
      ctx.lineTo(bubbleX + radius, bubbleY + bubbleHeight);
      ctx.quadraticCurveTo(bubbleX, bubbleY + bubbleHeight, bubbleX, bubbleY + bubbleHeight - radius);
      ctx.lineTo(bubbleX, bubbleY + radius);
      ctx.quadraticCurveTo(bubbleX, bubbleY, bubbleX + radius, bubbleY);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
      
      // Pointer triangle
      ctx.beginPath();
      ctx.moveTo(x - 10, bubbleY + bubbleHeight);
      ctx.lineTo(x, y - 5);
      ctx.lineTo(x + 10, bubbleY + bubbleHeight);
      ctx.closePath();
      ctx.fill();
      
      // Landmark text
      ctx.fillStyle = '#1a1a1a';
      ctx.font = '14px SF Pro Display';
      ctx.textAlign = 'center';
      ctx.fillText(
        landmark.name,
        bubbleX + bubbleWidth / 2,
        bubbleY + 25
      );
      
      // Distance
      ctx.font = '12px SF Pro Text';
      ctx.fillStyle = '#666';
      ctx.fillText(
        this.formatDistance(landmark.distance),
        bubbleX + bubbleWidth / 2,
        bubbleY + 45
      );
    });
  }
  
  /**
   * Generate thumbnail
   */
  private async generateThumbnail(imagePath: string): Promise<string> {
    // This would use image manipulation library
    // For now, return same path
    return imagePath;
  }
  
  /**
   * Save to trip memory
   */
  private async saveToTripMemory(
    photoPath: string,
    metadata: ARPhotoMetadata
  ): Promise<void> {
    await tripMemoryService.addMemory({
      type: 'ar_photo',
      timestamp: metadata.timestamp,
      location: metadata.location,
      data: {
        photoPath,
        landmarks: metadata.landmarks.map(l => ({
          id: l.id,
          name: l.name,
          type: l.type,
        })),
        metadata,
      },
    });
  }
  
  /**
   * Batch process photos
   */
  async batchProcessPhotos(
    photos: string[],
    frame: ARPhotoFrame
  ): Promise<PhotoCaptureResult[]> {
    const results: PhotoCaptureResult[] = [];
    
    // Process in queue to avoid memory issues
    for (const photo of photos) {
      const result = await this.captureARPhoto(photo, [], frame);
      results.push(result);
    }
    
    return results;
  }
  
  /**
   * Create journey montage
   */
  async createJourneyMontage(
    photos: PhotoCaptureResult[],
    options: {
      title?: string;
      music?: string;
      duration?: number;
    } = {}
  ): Promise<string> {
    // This would create a video montage
    // For now, return placeholder
    return 'montage_path';
  }
  
  // Utility functions
  
  private async ensureDirectoryExists(): Promise<void> {
    const exists = await RNFS.exists(this.photosDirectory);
    if (!exists) {
      await RNFS.mkdir(this.photosDirectory);
    }
  }
  
  private calculateOverlayHeight(frame: ARPhotoFrame): number {
    const baseHeight = 100;
    let height = baseHeight;
    
    if (frame.includeDate) height += 30;
    if (frame.includeLocation) height += 30;
    if (frame.includeWeather) height += 30;
    if (frame.includeQuote) height += 60;
    if (frame.customText) height += 40;
    
    return Math.min(height, 300); // Max overlay height
  }
  
  private async detectMilestone(trip: any): Promise<string | undefined> {
    // Detect journey milestones
    const elapsed = Date.now() - trip.startTime.getTime();
    const hours = elapsed / (1000 * 60 * 60);
    
    if (Math.floor(hours) === 1 && hours < 1.1) {
      return 'First Hour!';
    } else if (Math.floor(hours) === 5 && hours < 5.1) {
      return '5 Hours Strong!';
    }
    
    // Distance milestones would be calculated here
    return undefined;
  }
  
  private async getCurrentWeather(location: any): Promise<any> {
    // This would call weather service
    return null;
  }
  
  private async generateStoryContext(landmarks: ARLandmark[]): Promise<string> {
    const types = [...new Set(landmarks.map(l => l.type))];
    return `Discovered ${landmarks.length} ${types.join(' and ')} landmarks`;
  }
  
  private async generateQuote(landmark: ARLandmark): Promise<string> {
    // This would generate contextual quotes
    const quotes = {
      historical: '"Every place has a story waiting to be discovered"',
      nature: '"Nature is the art of God"',
      landmark: '"The journey is the destination"',
    };
    return quotes[landmark.type] || quotes.landmark;
  }
  
  private drawMilestoneBadge(
    ctx: CanvasRenderingContext2D,
    width: number,
    height: number,
    milestone: string
  ): void {
    const badgeSize = 120;
    const x = width - badgeSize - 20;
    const y = 20;
    
    // Badge background
    ctx.fillStyle = '#FFD700';
    ctx.beginPath();
    ctx.arc(x + badgeSize / 2, y + badgeSize / 2, badgeSize / 2, 0, Math.PI * 2);
    ctx.fill();
    
    // Badge text
    ctx.fillStyle = '#1a1a1a';
    ctx.font = 'bold 16px SF Pro Display';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(milestone, x + badgeSize / 2, y + badgeSize / 2);
  }
  
  private formatDistance(meters: number): string {
    if (meters < 100) {
      return `${Math.round(meters)}m away`;
    } else if (meters < 1000) {
      return `${Math.round(meters / 10) * 10}m away`;
    } else {
      return `${(meters / 1000).toFixed(1)}km away`;
    }
  }
}

// Export singleton instance
export const arPhotoCaptureService = ARPhotoCaptureService.getInstance();
