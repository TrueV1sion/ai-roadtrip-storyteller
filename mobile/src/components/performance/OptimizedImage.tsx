/**
 * Optimized image component with lazy loading and caching
 */
import React, { useState, useEffect, useRef } from 'react';
import { logger } from '@/services/logger';
import {
  Image,
  View,
  ActivityIndicator,
  StyleSheet,
  Animated,
  ImageSourcePropType,
  ViewStyle,
  ImageStyle,
  Platform
} from 'react-native';
import FastImage from 'react-native-fast-image';

interface OptimizedImageProps {
  source: ImageSourcePropType | { uri: string };
  style?: ImageStyle;
  containerStyle?: ViewStyle;
  resizeMode?: 'cover' | 'contain' | 'stretch' | 'center';
  priority?: 'low' | 'normal' | 'high';
  placeholder?: ImageSourcePropType;
  onLoad?: () => void;
  onError?: (error: any) => void;
  fadeInDuration?: number;
  cachePolicy?: 'memory' | 'disk' | 'memory-disk';
  preload?: boolean;
}

export const OptimizedImage: React.FC<OptimizedImageProps> = ({
  source,
  style,
  containerStyle,
  resizeMode = 'cover',
  priority = 'normal',
  placeholder,
  onLoad,
  onError,
  fadeInDuration = 300,
  cachePolicy = 'memory-disk',
  preload = false
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const isMounted = useRef(true);

  useEffect(() => {
    return () => {
      isMounted.current = false;
    };
  }, []);

  useEffect(() => {
    if (preload && 'uri' in source && source.uri) {
      FastImage.preload([{ uri: source.uri }]);
    }
  }, [source, preload]);

  const handleLoad = () => {
    if (!isMounted.current) return;

    setLoading(false);
    
    // Fade in animation
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: fadeInDuration,
      useNativeDriver: true
    }).start();

    onLoad?.();
  };

  const handleError = (err: any) => {
    if (!isMounted.current) return;

    setLoading(false);
    setError(true);
    onError?.(err);
  };

  const getCachePriority = () => {
    const priorityMap = {
      low: FastImage.priority.low,
      normal: FastImage.priority.normal,
      high: FastImage.priority.high
    };
    return priorityMap[priority];
  };

  const getCacheControl = () => {
    switch (cachePolicy) {
      case 'memory':
        return FastImage.cacheControl.immutable;
      case 'disk':
        return FastImage.cacheControl.cacheOnly;
      case 'memory-disk':
      default:
        return FastImage.cacheControl.immutable;
    }
  };

  if (error && placeholder) {
    return (
      <View style={[styles.container, containerStyle]}>
        <Image
          source={placeholder}
          style={[styles.image, style]}
          resizeMode={resizeMode}
        />
      </View>
    );
  }

  // Use FastImage for better performance on native platforms
  if (Platform.OS !== 'web') {
    return (
      <View style={[styles.container, containerStyle]}>
        {loading && placeholder && (
          <Image
            source={placeholder}
            style={[styles.image, style, styles.placeholder]}
            resizeMode={resizeMode}
          />
        )}
        {loading && !placeholder && (
          <View style={[styles.loadingContainer, style]}>
            <ActivityIndicator size="small" color="#007AFF" />
          </View>
        )}
        <Animated.View style={{ opacity: fadeAnim }}>
          <FastImage
            source={typeof source === 'object' && 'uri' in source ? source : { uri: '' }}
            style={[styles.image, style] as any}
            resizeMode={FastImage.resizeMode[resizeMode]}
            onLoad={handleLoad}
            onError={handleError}
            priority={getCachePriority()}
            cache={getCacheControl()}
          />
        </Animated.View>
      </View>
    );
  }

  // Fallback for web
  return (
    <View style={[styles.container, containerStyle]}>
      {loading && placeholder && (
        <Image
          source={placeholder}
          style={[styles.image, style, styles.placeholder]}
          resizeMode={resizeMode}
        />
      )}
      {loading && !placeholder && (
        <View style={[styles.loadingContainer, style]}>
          <ActivityIndicator size="small" color="#007AFF" />
        </View>
      )}
      <Animated.Image
        source={source}
        style={[styles.image, style, { opacity: fadeAnim }]}
        resizeMode={resizeMode}
        onLoad={handleLoad}
        onError={handleError}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'relative',
  },
  image: {
    width: '100%',
    height: '100%',
  },
  placeholder: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
  },
  loadingContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f0f0f0',
  },
});

// Image preloader utility
export class ImagePreloader {
  private static queue: string[] = [];
  private static processing = false;
  private static batchSize = 5;

  static async preloadImages(urls: string[], priority: 'low' | 'normal' | 'high' = 'normal') {
    const priorityMap = {
      low: FastImage.priority.low,
      normal: FastImage.priority.normal,
      high: FastImage.priority.high
    };

    const images = urls.map(uri => ({
      uri,
      priority: priorityMap[priority]
    }));

    if (priority === 'high') {
      // Preload high priority images immediately
      await FastImage.preload(images);
    } else {
      // Queue lower priority images
      this.queue.push(...urls);
      this.processQueue();
    }
  }

  private static async processQueue() {
    if (this.processing || this.queue.length === 0) return;

    this.processing = true;
    const batch = this.queue.splice(0, this.batchSize);

    try {
      await FastImage.preload(batch.map(uri => ({ uri })));
    } catch (error) {
      logger.warn('Image preload error:', error);
    }

    this.processing = false;

    // Process next batch
    if (this.queue.length > 0) {
      setTimeout(() => this.processQueue(), 100);
    }
  }

  static clearCache() {
    if (Platform.OS !== 'web') {
      FastImage.clearDiskCache();
      FastImage.clearMemoryCache();
    }
  }
}