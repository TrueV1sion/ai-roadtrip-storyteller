import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  View,
  FlatList,
  StyleSheet,
  Dimensions,
  TouchableOpacity,
  Animated,
  NativeSyntheticEvent,
  NativeScrollEvent,
  ViewToken,
  Platform,
} from 'react-native';
import OptimizedImage from '@/utils/optimizedImage';
import { Stopwatch, recordImageLoadPerformance } from '@/utils/performance';

// Get screen dimensions
const { width: SCREEN_WIDTH } = Dimensions.get('window');

// Type definitions
interface ImageItem {
  uri: string;
  id: string;
  thumbnail?: string;
  width?: number;
  height?: number;
  title?: string;
  description?: string;
}

interface ImageCarouselProps {
  // Data
  images: ImageItem[];
  initialIndex?: number;
  
  // Styling
  width?: number;
  height?: number;
  borderRadius?: number;
  containerStyle?: any;
  imageStyle?: any;
  
  // Behavior
  autoPlay?: boolean;
  autoPlayInterval?: number;
  loop?: boolean;
  paginationEnabled?: boolean;
  
  // Performance
  lazyLoad?: boolean;
  preloadCount?: number;
  lowQualityPreview?: boolean;
  
  // Events
  onImageChange?: (index: number) => void;
  onImagePress?: (index: number, item: ImageItem) => void;
  
  // Accessibility
  testID?: string;
  pauseOnUserInteraction?: boolean;
}

const OptimizedImageCarousel: React.FC<ImageCarouselProps> = ({
  images,
  initialIndex = 0,
  width = SCREEN_WIDTH,
  height = 250,
  borderRadius = 8,
  containerStyle,
  imageStyle,
  autoPlay = false,
  autoPlayInterval = 3000,
  loop = false,
  paginationEnabled = true,
  lazyLoad = true,
  preloadCount = 2,
  lowQualityPreview = true,
  onImageChange,
  onImagePress,
  testID,
  pauseOnUserInteraction = true,
}) => {
  // State
  const [activeIndex, setActiveIndex] = useState(initialIndex);
  const [isPaused, setIsPaused] = useState(false);
  const [loadedImages, setLoadedImages] = useState<Record<string, boolean>>({});
  const [isUserInteracting, setIsUserInteracting] = useState(false);
  
  // Refs
  const flatListRef = useRef<FlatList<ImageItem>>(null);
  const scrollX = useRef(new Animated.Value(0)).current;
  const autoPlayTimerRef = useRef<NodeJS.Timeout | null>(null);
  const performanceStopwatch = useRef<Stopwatch | null>(null);
  const viewConfigRef = useRef({ viewAreaCoveragePercentThreshold: 50 });
  
  // Performance tracking
  useEffect(() => {
    performanceStopwatch.current = new Stopwatch('render', 'ImageCarousel');
    return () => {
      if (performanceStopwatch.current) {
        performanceStopwatch.current.stop();
      }
    };
  }, []);
  
  // Track loaded images
  const handleImageLoad = useCallback((id: string, loadTime: number, imageUri: string) => {
    setLoadedImages(prev => ({ ...prev, [id]: true }));
    recordImageLoadPerformance(imageUri, loadTime);
  }, []);
  
  // Scroll to initial index on mount
  useEffect(() => {
    if (flatListRef.current && initialIndex > 0 && initialIndex < images.length) {
      flatListRef.current.scrollToIndex({
        index: initialIndex,
        animated: false,
      });
    }
  }, [initialIndex, images.length]);
  
  // Auto play functionality
  useEffect(() => {
    // Setup auto play timer
    const setupAutoPlay = () => {
      if (autoPlay && !isPaused && (!pauseOnUserInteraction || !isUserInteracting)) {
        autoPlayTimerRef.current = setTimeout(() => {
          if (images.length > 1) {
            let nextIndex = activeIndex + 1;
            
            // Handle looping
            if (nextIndex >= images.length) {
              if (loop) {
                nextIndex = 0;
              } else {
                // Reverse direction if not looping
                setIsPaused(true);
                return;
              }
            }
            
            // Scroll to next image
            if (flatListRef.current) {
              flatListRef.current.scrollToIndex({
                index: nextIndex,
                animated: true,
              });
            }
          }
        }, autoPlayInterval);
      }
    };
    
    // Clear existing timer and set up a new one
    if (autoPlayTimerRef.current) {
      clearTimeout(autoPlayTimerRef.current);
    }
    
    setupAutoPlay();
    
    // Cleanup
    return () => {
      if (autoPlayTimerRef.current) {
        clearTimeout(autoPlayTimerRef.current);
      }
    };
  }, [autoPlay, autoPlayInterval, activeIndex, images.length, loop, isPaused, isUserInteracting, pauseOnUserInteraction]);
  
  // Preload images in advance
  useEffect(() => {
    if (!lazyLoad || !preloadCount) return;
    
    const preloadImages = async () => {
      // Determine which images to preload
      const startIdx = Math.max(0, activeIndex - preloadCount);
      const endIdx = Math.min(images.length - 1, activeIndex + preloadCount);
      
      // Preload images within range
      for (let i = startIdx; i <= endIdx; i++) {
        const image = images[i];
        if (image && image.uri && !loadedImages[image.id]) {
          try {
            // Use the ImageCacheManager from OptimizedImage
            await Promise.race([
              fetch(image.uri, { method: 'HEAD' }),
              new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout')), 2000)),
            ]);
          } catch (error) {
            // Ignore preloading errors
          }
        }
      }
    };
    
    preloadImages();
  }, [activeIndex, images, lazyLoad, preloadCount, loadedImages]);
  
  // Handle scroll events
  const handleScroll = Animated.event(
    [{ nativeEvent: { contentOffset: { x: scrollX } } }],
    { useNativeDriver: false }
  );
  
  // Handle scroll end
  const handleMomentumScrollEnd = (event: NativeSyntheticEvent<NativeScrollEvent>) => {
    const contentOffset = event.nativeEvent.contentOffset;
    const newIndex = Math.round(contentOffset.x / width);
    
    if (newIndex !== activeIndex) {
      setActiveIndex(newIndex);
      if (onImageChange) {
        onImageChange(newIndex);
      }
    }
  };
  
  // Handle viewable items changed
  const handleViewableItemsChanged = useCallback(
    ({ viewableItems }: { viewableItems: ViewToken[] }) => {
      if (viewableItems.length > 0 && viewableItems[0].index !== null) {
        setActiveIndex(viewableItems[0].index);
        if (onImageChange) {
          onImageChange(viewableItems[0].index);
        }
      }
    },
    [onImageChange]
  );
  
  // Handle image press
  const handleImagePress = useCallback(
    (index: number) => {
      if (onImagePress) {
        onImagePress(index, images[index]);
      }
    },
    [images, onImagePress]
  );
  
  // Handle user interaction
  const handleTouchStart = useCallback(() => {
    setIsUserInteracting(true);
  }, []);
  
  const handleTouchEnd = useCallback(() => {
    setIsUserInteracting(false);
  }, []);
  
  // Render pagination dots
  const renderPagination = () => {
    if (!paginationEnabled || images.length <= 1) return null;
    
    return (
      <View style={styles.paginationContainer}>
        {images.map((_, index) => {
          // Interpolate dot opacity based on scroll position
          const opacity = scrollX.interpolate({
            inputRange: [(index - 1) * width, index * width, (index + 1) * width],
            outputRange: [0.4, 1, 0.4],
            extrapolate: 'clamp',
          });
          
          // Interpolate dot scale based on scroll position
          const scale = scrollX.interpolate({
            inputRange: [(index - 1) * width, index * width, (index + 1) * width],
            outputRange: [0.8, 1.2, 0.8],
            extrapolate: 'clamp',
          });
          
          return (
            <Animated.View
              key={`dot-${index}`}
              style={[
                styles.paginationDot,
                {
                  opacity,
                  transform: [{ scale }],
                },
              ]}
            />
          );
        })}
      </View>
    );
  };
  
  // Render image item
  const renderItem = useCallback(
    ({ item, index }: { item: ImageItem; index: number }) => {
      // Calculate distance from active index for loading priority
      const distance = Math.abs(index - activeIndex);
      
      // Determine loading priority
      const loadPriority = distance <= 1 ? 'high' : distance <= preloadCount ? 'normal' : 'low';
      
      // Calculate if this image should be loaded based on lazy loading settings
      const shouldLoad = !lazyLoad || distance <= preloadCount;
      
      return (
        <TouchableOpacity
          activeOpacity={0.9}
          onPress={() => handleImagePress(index)}
          style={{ width }}
          testID={`${testID}-image-${index}`}
        >
          <OptimizedImage
            source={{ uri: item.uri }}
            lowQualitySource={lowQualityPreview && item.thumbnail ? { uri: item.thumbnail } : undefined}
            style={[
              {
                width,
                height,
                borderRadius,
              },
              imageStyle,
            ]}
            resizeMode="cover"
            withPlaceholder={true}
            optimizeSize={true}
            maxWidth={width * 2} // 2x for high-DPI screens
            maxHeight={height * 2}
            priority={loadPriority}
            onLoadEnd={(success) => {
              if (success) {
                handleImageLoad(item.id, 0, item.uri);
              }
            }}
            fallbackSource={require('@/assets/image-placeholder.png')}
          />
        </TouchableOpacity>
      );
    },
    [activeIndex, borderRadius, handleImageLoad, handleImagePress, height, imageStyle, lazyLoad, lowQualityPreview, preloadCount, testID, width]
  );
  
  // Keyextractor
  const keyExtractor = useCallback((item: ImageItem) => item.id, []);
  
  // Handle list errors
  const handleScrollToIndexFailed = useCallback(
    (info: {
      index: number;
      highestMeasuredFrameIndex: number;
      averageItemLength: number;
    }) => {
      // Workaround for scroll to index failed
      setTimeout(() => {
        if (flatListRef.current) {
          flatListRef.current.scrollToIndex({
            index: info.index,
            animated: false,
          });
        }
      }, 100);
    },
    []
  );
  
  // Handle empty state
  if (!images || images.length === 0) {
    return (
      <View
        style={[
          {
            width,
            height,
            borderRadius,
          },
          styles.emptyContainer,
          containerStyle,
        ]}
        testID={testID}
      >
        <OptimizedImage
          source={require('@/assets/image-placeholder.png')}
          style={[
            {
              width: width * 0.5,
              height: height * 0.5,
            },
          ]}
          resizeMode="contain"
        />
      </View>
    );
  }
  
  // Render single image (no need for carousel)
  if (images.length === 1) {
    return (
      <View
        style={[
          {
            width,
            height,
            borderRadius,
          },
          containerStyle,
        ]}
        testID={testID}
      >
        <OptimizedImage
          source={{ uri: images[0].uri }}
          style={[
            {
              width,
              height,
              borderRadius,
            },
            imageStyle,
          ]}
          resizeMode="cover"
          onLoadEnd={(success) => {
            if (success) {
              handleImageLoad(images[0].id, 0, images[0].uri);
            }
          }}
          fallbackSource={require('@/assets/image-placeholder.png')}
        />
      </View>
    );
  }
  
  // Render carousel
  return (
    <View
      style={[
        {
          width,
          height,
          borderRadius,
        },
        containerStyle,
      ]}
      testID={testID}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      <FlatList
        ref={flatListRef}
        data={images}
        renderItem={renderItem}
        keyExtractor={keyExtractor}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        onScroll={handleScroll}
        onMomentumScrollEnd={handleMomentumScrollEnd}
        onViewableItemsChanged={handleViewableItemsChanged}
        viewabilityConfig={viewConfigRef.current}
        onScrollToIndexFailed={handleScrollToIndexFailed}
        initialNumToRender={Math.min(3, images.length)}
        maxToRenderPerBatch={3}
        windowSize={5}
        removeClippedSubviews={Platform.OS !== 'ios'} // Can cause issues on iOS
        getItemLayout={(_, index) => ({
          length: width,
          offset: width * index,
          index,
        })}
      />
      
      {renderPagination()}
    </View>
  );
};

const styles = StyleSheet.create({
  paginationContainer: {
    position: 'absolute',
    bottom: 15,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    width: '100%',
  },
  paginationDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#FFFFFF',
    marginHorizontal: 4,
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 1,
    },
    shadowOpacity: 0.22,
    shadowRadius: 2.22,
    elevation: 3,
  },
  emptyContainer: {
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f9f9f9',
  },
});

export default OptimizedImageCarousel;