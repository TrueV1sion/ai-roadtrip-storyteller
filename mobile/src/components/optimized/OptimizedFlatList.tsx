import React, { useState, useCallback, useRef, useMemo, useEffect } from 'react';
import {
  FlatList,
  FlatListProps,
  View,
  StyleSheet,
  Dimensions,
  ActivityIndicator,
  Text,
  Platform,
  InteractionManager,
} from 'react-native';
import { useWindowDimensions } from 'react-native';
import { Stopwatch } from '@/utils/performance';

// Constants
const DEFAULT_WINDOW_SIZE = 5;
const DEFAULT_MAX_TO_RENDER_PER_BATCH = 6;
const DEFAULT_INITIAL_NUM_TO_RENDER = 8;
const DEFAULT_UPDATE_CELL_BATCH_INGRESS = 2;
const INITIAL_DELAY_MS = 50;

// Type definitions
interface OptimizedFlatListProps<T> extends Omit<FlatListProps<T>, 'renderItem'> {
  renderItem: (info: { item: T; index: number; isActive: boolean }) => React.ReactElement;
  
  // Performance optimization props
  initialRenderDelay?: number;
  optimizationsEnabled?: boolean;
  backgroundUpdateInterval?: number;
  activeDistanceThreshold?: number;
  
  // Empty state customization
  emptyComponent?: React.ReactNode;
  emptyText?: string;
  
  // Loading state
  isLoading?: boolean;
  loadingComponent?: React.ReactNode;
  
  // Error state
  hasError?: boolean;
  errorComponent?: React.ReactNode;
  errorText?: string;
  
  // Metrics tracking
  trackMetrics?: boolean;
  componentName?: string;
}

function OptimizedFlatList<T>(props: OptimizedFlatListProps<T>) {
  const {
    renderItem,
    data,
    initialRenderDelay = INITIAL_DELAY_MS,
    optimizationsEnabled = true,
    backgroundUpdateInterval = 1000,
    activeDistanceThreshold = 1,
    emptyComponent,
    emptyText = 'No items to display',
    isLoading = false,
    loadingComponent,
    hasError = false,
    errorComponent,
    errorText = 'An error occurred',
    trackMetrics = false,
    componentName = 'OptimizedFlatList',
    ...restProps
  } = props;

  // State for render optimization
  const [isReady, setIsReady] = useState(false);
  const { width, height } = useWindowDimensions();
  const [visibleIndices, setVisibleIndices] = useState<number[]>([]);
  const listRef = useRef<FlatList<T>>(null);
  const viewabilityConfigRef = useRef({ 
    viewAreaCoveragePercentThreshold: 20,
    minimumViewTime: 100,
  });
  const metricsRef = useRef({
    renderCount: 0,
    totalRenderTime: 0,
    lastRenderTime: 0,
    itemsRendered: new Set<number>(),
  });
  const performanceStopwatch = useRef<Stopwatch | null>(null);
  
  // Optimized view configuration
  const optimizedProps = useMemo(() => {
    if (!optimizationsEnabled) {
      return {};
    }
    
    // Calculate optimal values based on device
    const isHighEndDevice = Platform.OS === 'ios' && 
                          !Platform.isPad && 
                          height >= 812; // iPhone X and newer
    
    return {
      windowSize: isHighEndDevice ? DEFAULT_WINDOW_SIZE + 1 : DEFAULT_WINDOW_SIZE,
      maxToRenderPerBatch: isHighEndDevice ? DEFAULT_MAX_TO_RENDER_PER_BATCH + 2 : DEFAULT_MAX_TO_RENDER_PER_BATCH,
      initialNumToRender: isHighEndDevice ? DEFAULT_INITIAL_NUM_TO_RENDER + 2 : DEFAULT_INITIAL_NUM_TO_RENDER,
      updateCellsBatchingPeriod: isHighEndDevice ? 50 : 80,
      removeClippedSubviews: Platform.OS !== 'ios', // Can cause issues on iOS
      maintainVisibleContentPosition: {
        minIndexForVisible: 0,
      },
    };
  }, [optimizationsEnabled, height]);
  
  // Initialize after a brief delay to avoid blocking the UI
  useEffect(() => {
    if (initialRenderDelay <= 0) {
      setIsReady(true);
      return;
    }
    
    let timer = setTimeout(() => {
      InteractionManager.runAfterInteractions(() => {
        setIsReady(true);
      });
    }, initialRenderDelay);
    
    return () => {
      clearTimeout(timer);
    };
  }, [initialRenderDelay]);
  
  // Setup performance tracking
  useEffect(() => {
    if (trackMetrics) {
      performanceStopwatch.current = new Stopwatch('render', componentName);
    }
    
    return () => {
      if (performanceStopwatch.current) {
        performanceStopwatch.current.stop();
      }
    };
  }, [trackMetrics, componentName]);
  
  // Track visible items
  const handleViewableItemsChanged = useCallback(({ viewableItems }: any) => {
    const indices = viewableItems.map((item: any) => item.index).filter((index: number) => index !== null);
    setVisibleIndices(indices);
    
    // Add newly visible items to metrics
    if (trackMetrics && indices.length > 0) {
      indices.forEach(index => {
        metricsRef.current.itemsRendered.add(index);
      });
    }
  }, [trackMetrics]);
  
  // Optimized renderItem function
  const optimizedRenderItem = useCallback(
    ({ item, index }: { item: T; index: number }) => {
      // Track render time for metrics
      const startTime = trackMetrics ? performance.now() : 0;
      
      // Determine if this item is "active" (visible or close to visible)
      const isActive = visibleIndices.some(
        visibleIndex => Math.abs(visibleIndex - index) <= activeDistanceThreshold
      );
      
      // Render the item
      const result = renderItem({ item, index, isActive });
      
      // Update metrics
      if (trackMetrics) {
        const endTime = performance.now();
        const renderTime = endTime - startTime;
        
        metricsRef.current.renderCount++;
        metricsRef.current.totalRenderTime += renderTime;
        metricsRef.current.lastRenderTime = renderTime;
      }
      
      return result;
    },
    [renderItem, visibleIndices, activeDistanceThreshold, trackMetrics]
  );
  
  // Conditionally render loading state
  if (isLoading && !isReady) {
    return loadingComponent || (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#0000ff" />
      </View>
    );
  }
  
  // Conditionally render error state
  if (hasError) {
    return errorComponent || (
      <View style={styles.errorContainer}>
        <Text style={styles.errorText}>{errorText}</Text>
      </View>
    );
  }
  
  // Conditionally render empty state
  if ((!data || data.length === 0) && isReady) {
    return emptyComponent || (
      <View style={styles.emptyContainer}>
        <Text style={styles.emptyText}>{emptyText}</Text>
      </View>
    );
  }
  
  // Render the optimized flat list
  return (
    <FlatList
      {...restProps}
      ref={listRef}
      data={isReady ? data : []}
      renderItem={optimizedRenderItem}
      onViewableItemsChanged={handleViewableItemsChanged}
      viewabilityConfig={viewabilityConfigRef.current}
      keyExtractor={props.keyExtractor || ((_, index) => `item-${index}`)}
      ListFooterComponent={
        isLoading && isReady ? (
          loadingComponent || (
            <View style={styles.footerLoading}>
              <ActivityIndicator size="small" color="#0000ff" />
            </View>
          )
        ) : props.ListFooterComponent
      }
      {...optimizedProps}
    />
  );
}

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  errorText: {
    fontSize: 16,
    color: 'red',
    textAlign: 'center',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  emptyText: {
    fontSize: 16,
    color: 'gray',
    textAlign: 'center',
  },
  footerLoading: {
    padding: 20,
    alignItems: 'center',
  },
});

export default OptimizedFlatList;