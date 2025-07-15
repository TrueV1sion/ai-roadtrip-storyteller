import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Image,
  ImageProps,
  ImageURISource,
  Platform,
  View,
  StyleSheet,
  ActivityIndicator,
  InteractionManager,
  Animated,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as FileSystem from 'expo-file-system';
import { BlurView } from 'expo-blur';
import { Asset } from 'expo-asset';
import { manipulateAsync, SaveFormat } from 'expo-image-manipulator';
import { recordImageLoadPerformance } from './performance';

// Constants
const IMAGE_CACHE_KEY_PREFIX = '@RoadTrip:image_cache_';
const IMAGE_CACHE_EXPIRY = 7 * 24 * 60 * 60 * 1000; // 7 days in milliseconds
const LOW_MEMORY_THRESHOLD = 150; // MB

// Type definitions
interface OptimizedImageProps extends Omit<ImageProps, 'source'> {
  source: ImageURISource;
  lowQualitySource?: ImageURISource;
  withPlaceholder?: boolean;
  cacheTimeout?: number;
  resizeMode?: 'cover' | 'contain' | 'stretch' | 'repeat' | 'center';
  optimizeSize?: boolean;
  blurRadius?: number;
  priority?: 'high' | 'normal' | 'low';
  maxWidth?: number;
  maxHeight?: number;
  onLoadStart?: () => void;
  onLoadEnd?: (success: boolean) => void;
  fallbackSource?: ImageURISource;
}

// Interface for cache entry
interface CacheEntry {
  uri: string;
  timestamp: number;
  size?: number;
}

// Interface for the cache registry
interface CacheRegistry {
  entries: Record<string, CacheEntry>;
  totalSize: number;
  lastCleanup: number;
}

// In-memory cache registry
let cacheRegistry: CacheRegistry = {
  entries: {},
  totalSize: 0,
  lastCleanup: Date.now(),
};

// Initialize cache
async function initImageCache() {
  try {
    const cacheData = await AsyncStorage.getItem(`${IMAGE_CACHE_KEY_PREFIX}registry`);
    if (cacheData) {
      cacheRegistry = JSON.parse(cacheData);
    }
    
    // If it's been more than a day since the last cleanup, do it now
    if (Date.now() - cacheRegistry.lastCleanup > 24 * 60 * 60 * 1000) {
      await cleanupImageCache();
    }
  } catch (error) {
    console.warn('Failed to initialize image cache:', error);
    // Reset the cache registry if there was an error
    cacheRegistry = {
      entries: {},
      totalSize: 0,
      lastCleanup: Date.now(),
    };
  }
}

// Save the cache registry
async function saveCacheRegistry() {
  try {
    await AsyncStorage.setItem(
      `${IMAGE_CACHE_KEY_PREFIX}registry`,
      JSON.stringify(cacheRegistry)
    );
  } catch (error) {
    console.warn('Failed to save image cache registry:', error);
  }
}

// Clean up old images from the cache
async function cleanupImageCache() {
  const now = Date.now();
  cacheRegistry.lastCleanup = now;
  
  const keysToRemove: string[] = [];
  
  // Find expired entries
  for (const [key, entry] of Object.entries(cacheRegistry.entries)) {
    if (now - entry.timestamp > IMAGE_CACHE_EXPIRY) {
      keysToRemove.push(key);
    }
  }
  
  // Remove expired entries
  for (const key of keysToRemove) {
    const entry = cacheRegistry.entries[key];
    try {
      // Delete the cached file
      if (entry.uri && entry.uri.startsWith(FileSystem.cacheDirectory || '')) {
        await FileSystem.deleteAsync(entry.uri, { idempotent: true });
      }
      
      // Update the registry
      if (entry.size) {
        cacheRegistry.totalSize -= entry.size;
      }
      delete cacheRegistry.entries[key];
    } catch (error) {
      console.warn(`Failed to delete cached image ${key}:`, error);
    }
  }
  
  // Save the updated registry
  await saveCacheRegistry();
  
  console.log(`Cleaned up ${keysToRemove.length} expired images from cache`);
}

// Get a cached image or download and cache it
async function getCachedImage(
  source: ImageURISource,
  options: {
    maxWidth?: number;
    maxHeight?: number;
    optimizeSize?: boolean;
  } = {}
): Promise<string> {
  if (!source.uri) {
    throw new Error('Source URI is required');
  }
  
  const sourceUri = source.uri;
  const cacheKey = generateCacheKey(sourceUri, options);
  
  // Check if the image is already cached
  if (cacheRegistry.entries[cacheKey]) {
    const entry = cacheRegistry.entries[cacheKey];
    
    // Verify the cached file exists
    try {
      const fileInfo = await FileSystem.getInfoAsync(entry.uri);
      if (fileInfo.exists) {
        // Update the timestamp to mark it as recently used
        entry.timestamp = Date.now();
        return entry.uri;
      }
    } catch (error) {
      console.warn(`Cached file not found for ${cacheKey}:`, error);
    }
  }
  
  // If not cached or the cached file doesn't exist, download and cache it
  const cacheDir = FileSystem.cacheDirectory;
  if (!cacheDir) {
    throw new Error('Cache directory not available');
  }
  
  const filename = sourceUri.split('/').pop() || `image_${Date.now()}.jpg`;
  const filePath = `${cacheDir}${cacheKey}_${filename}`;
  
  try {
    // Download the image
    const downloadResult = await FileSystem.downloadAsync(sourceUri, filePath);
    
    // If optimization is requested and the image is larger than we need, resize it
    let finalUri = downloadResult.uri;
    if (options.optimizeSize && (options.maxWidth || options.maxHeight)) {
      try {
        // Get image dimensions
        const asset = await Asset.fromURI(finalUri).downloadAsync();
        if (asset && asset.width && asset.height) {
          const { width, height } = asset;
          
          // Check if resizing is needed
          const maxWidth = options.maxWidth || width;
          const maxHeight = options.maxHeight || height;
          
          if (width > maxWidth || height > maxHeight) {
            // Calculate new dimensions while maintaining aspect ratio
            const aspectRatio = width / height;
            let newWidth = width;
            let newHeight = height;
            
            if (width > maxWidth) {
              newWidth = maxWidth;
              newHeight = newWidth / aspectRatio;
            }
            
            if (newHeight > maxHeight) {
              newHeight = maxHeight;
              newWidth = newHeight * aspectRatio;
            }
            
            // Resize the image
            const manipResult = await manipulateAsync(
              finalUri,
              [{ resize: { width: Math.floor(newWidth), height: Math.floor(newHeight) } }],
              { compress: 0.8, format: SaveFormat.JPEG }
            );
            
            finalUri = manipResult.uri;
          }
        }
      } catch (error) {
        console.warn('Image optimization failed:', error);
        // Continue with the original downloaded image
      }
    }
    
    // Get file size
    const fileInfo = await FileSystem.getInfoAsync(finalUri);
    const fileSize = fileInfo.size || 0;
    
    // Update the cache registry
    cacheRegistry.entries[cacheKey] = {
      uri: finalUri,
      timestamp: Date.now(),
      size: fileSize,
    };
    
    cacheRegistry.totalSize += fileSize;
    
    // Save the updated registry
    await saveCacheRegistry();
    
    return finalUri;
  } catch (error) {
    console.error(`Failed to download and cache image ${sourceUri}:`, error);
    throw error;
  }
}

// Generate a cache key for an image source
function generateCacheKey(uri: string, options: any = {}): string {
  // Create a string representation of the URI and options
  const optionsString = JSON.stringify({
    maxWidth: options.maxWidth,
    maxHeight: options.maxHeight,
    optimizeSize: options.optimizeSize,
  });
  
  // Use a simple hash function
  function simpleHash(str: string): string {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return Math.abs(hash).toString(16);
  }
  
  return simpleHash(uri + optionsString);
}

// Optimized Image Component
const OptimizedImage: React.FC<OptimizedImageProps> = ({
  source,
  lowQualitySource,
  withPlaceholder = true,
  cacheTimeout = IMAGE_CACHE_EXPIRY,
  optimizeSize = true,
  blurRadius,
  priority = 'normal',
  maxWidth,
  maxHeight,
  style,
  onLoadStart,
  onLoadEnd,
  fallbackSource,
  ...props
}) => {
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [lowQualityUri, setLowQualityUri] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const loadStartTime = useRef(0);
  
  // Load the high-quality image
  const loadImage = useCallback(async () => {
    if (!source.uri) return;
    
    try {
      setLoading(true);
      if (onLoadStart) onLoadStart();
      loadStartTime.current = Date.now();
      
      // If priority is low, wait until after interactions
      if (priority === 'low') {
        await new Promise(resolve => InteractionManager.runAfterInteractions(resolve));
      }
      
      // Get the cached or downloaded image
      const cachedUri = await getCachedImage(source, {
        maxWidth,
        maxHeight,
        optimizeSize,
      });
      
      setImageUri(cachedUri);
      setError(false);
    } catch (error) {
      console.error('Failed to load image:', error);
      setError(true);
      if (onLoadEnd) onLoadEnd(false);
    }
  }, [source, maxWidth, maxHeight, optimizeSize, priority, onLoadStart, onLoadEnd]);
  
  // Load the low-quality placeholder
  const loadLowQualityImage = useCallback(async () => {
    if (!lowQualitySource?.uri) return;
    
    try {
      const lowQualityCachedUri = await getCachedImage(lowQualitySource, {
        maxWidth: 100, // Small size for placeholder
        maxHeight: 100,
        optimizeSize: true,
      });
      
      setLowQualityUri(lowQualityCachedUri);
    } catch (error) {
      console.warn('Failed to load low-quality image:', error);
      // Continue without the low-quality image
    }
  }, [lowQualitySource]);
  
  // Handle image load success
  const handleLoadSuccess = () => {
    setLoading(false);
    
    // Record performance metrics
    const loadTime = Date.now() - loadStartTime.current;
    if (source.uri) {
      recordImageLoadPerformance(source.uri, loadTime, maxWidth, maxHeight);
    }
    
    // Fade in the image
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 300,
      useNativeDriver: true,
    }).start();
    
    if (onLoadEnd) onLoadEnd(true);
  };
  
  // Handle image load error
  const handleLoadError = () => {
    setLoading(false);
    setError(true);
    if (onLoadEnd) onLoadEnd(false);
  };
  
  // Load the images on mount and when source changes
  useEffect(() => {
    // Reset state when source changes
    setImageUri(null);
    setLoading(true);
    setError(false);
    fadeAnim.setValue(0);
    
    // Load low-quality image first if available
    if (lowQualitySource?.uri && withPlaceholder) {
      loadLowQualityImage();
    }
    
    // Load high-quality image
    loadImage();
  }, [source.uri, lowQualitySource?.uri, loadImage, loadLowQualityImage, withPlaceholder, fadeAnim]);
  
  // Initialize the image cache on component mount
  useEffect(() => {
    initImageCache();
  }, []);
  
  // Render the component
  return (
    <View style={[styles.container, style]}>
      {/* Low-quality placeholder */}
      {withPlaceholder && lowQualityUri && (
        <Image
          source={{ uri: lowQualityUri }}
          style={[styles.image, { position: 'absolute' }]}
          blurRadius={Platform.OS === 'ios' ? 10 : 5}
          resizeMode={props.resizeMode || 'cover'}
        />
      )}
      
      {/* Main image */}
      {imageUri && !error && (
        <Animated.View style={{ opacity: fadeAnim, flex: 1 }}>
          <Image
            {...props}
            source={{ uri: imageUri }}
            style={styles.image}
            onLoad={handleLoadSuccess}
            onError={handleLoadError}
          />
          {blurRadius !== undefined && Platform.OS === 'ios' && (
            <BlurView
              style={StyleSheet.absoluteFill}
              tint="default"
              intensity={blurRadius}
            />
          )}
        </Animated.View>
      )}
      
      {/* Fallback image */}
      {error && fallbackSource && (
        <Image
          {...props}
          source={fallbackSource}
          style={styles.image}
        />
      )}
      
      {/* Loading indicator */}
      {loading && (
        <View style={styles.loaderContainer}>
          <ActivityIndicator size="small" color="#ffffff" />
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    overflow: 'hidden',
  },
  image: {
    width: '100%',
    height: '100%',
  },
  loaderContainer: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.2)',
  },
});

export default OptimizedImage;

// Export helper functions
export const ImageCacheManager = {
  clearCache: async () => {
    try {
      // Clear the cache registry
      cacheRegistry = {
        entries: {},
        totalSize: 0,
        lastCleanup: Date.now(),
      };
      
      await saveCacheRegistry();
      
      // Delete all cached image files
      const cacheDir = FileSystem.cacheDirectory;
      if (cacheDir) {
        const cacheFiles = await FileSystem.readDirectoryAsync(cacheDir);
        const imageFiles = cacheFiles.filter(file => 
          file.startsWith(IMAGE_CACHE_KEY_PREFIX) || file.includes('image_')
        );
        
        for (const file of imageFiles) {
          await FileSystem.deleteAsync(`${cacheDir}${file}`, { idempotent: true });
        }
      }
      
      return true;
    } catch (error) {
      console.error('Failed to clear image cache:', error);
      return false;
    }
  },
  
  getCacheInfo: () => ({
    totalSize: cacheRegistry.totalSize,
    entryCount: Object.keys(cacheRegistry.entries).length,
    lastCleanup: new Date(cacheRegistry.lastCleanup),
  }),
  
  prefetchImage: async (
    uri: string,
    options: {
      maxWidth?: number;
      maxHeight?: number;
      optimizeSize?: boolean;
    } = {}
  ) => {
    if (!uri) return false;
    
    try {
      await getCachedImage({ uri }, options);
      return true;
    } catch (error) {
      console.warn(`Failed to prefetch image ${uri}:`, error);
      return false;
    }
  },
  
  pruneCache: async (maxSize?: number) => {
    // If maxSize is not provided, use 80% of current size
    const targetSize = maxSize || Math.floor(cacheRegistry.totalSize * 0.8);
    
    if (cacheRegistry.totalSize <= targetSize) {
      return 0; // No pruning needed
    }
    
    // Sort entries by timestamp (oldest first)
    const entries = Object.entries(cacheRegistry.entries)
      .sort(([, a], [, b]) => a.timestamp - b.timestamp);
    
    let removedCount = 0;
    let removedSize = 0;
    
    for (const [key, entry] of entries) {
      if (cacheRegistry.totalSize - removedSize <= targetSize) {
        break; // Stop when we've freed enough space
      }
      
      try {
        // Delete the cached file
        if (entry.uri && entry.uri.startsWith(FileSystem.cacheDirectory || '')) {
          await FileSystem.deleteAsync(entry.uri, { idempotent: true });
        }
        
        // Update tracking variables
        removedCount++;
        if (entry.size) {
          removedSize += entry.size;
          cacheRegistry.totalSize -= entry.size;
        }
        
        // Remove from registry
        delete cacheRegistry.entries[key];
      } catch (error) {
        console.warn(`Failed to delete cached image ${key}:`, error);
      }
    }
    
    // Save the updated registry
    await saveCacheRegistry();
    
    return removedCount;
  },
};