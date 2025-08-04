/**
 * Optimized list component with virtualization and performance enhancements
 */
import React, { useCallback, useMemo, useRef } from 'react';
import { logger } from '@/services/logger';
import {
  FlatList,
  FlatListProps,
  ViewToken,
  Platform,
  ListRenderItem,
  View,
  Text,
  StyleSheet
} from 'react-native';
import { useDebounce, useThrottle } from '../../hooks/usePerformanceOptimization';

interface OptimizedListProps<T> extends Omit<FlatListProps<T>, 'renderItem'> {
  data: T[];
  renderItem: ListRenderItem<T>;
  itemHeight?: number;
  batchSize?: number;
  updateCellsBatchingPeriod?: number;
  windowSize?: number;
  maxToRenderPerBatch?: number;
  removeClippedSubviews?: boolean;
  initialNumToRender?: number;
  onEndReachedThreshold?: number;
  maintainVisibleContentPosition?: boolean;
  debug?: boolean;
}

export function OptimizedList<T>({
  data,
  renderItem,
  itemHeight,
  batchSize = 10,
  updateCellsBatchingPeriod = 50,
  windowSize = 21,
  maxToRenderPerBatch = 10,
  removeClippedSubviews = Platform.OS === 'android',
  initialNumToRender = 10,
  onEndReachedThreshold = 0.5,
  maintainVisibleContentPosition = false,
  debug = false,
  onScroll,
  onViewableItemsChanged,
  ...props
}: OptimizedListProps<T>) {
  const listRef = useRef<FlatList<T>>(null);
  const viewabilityConfig = useRef({
    minimumViewTime: 100,
    viewAreaCoveragePercentThreshold: 50,
    waitForInteraction: true
  }).current;

  // Performance metrics
  const renderCount = useRef(0);
  const lastRenderTime = useRef(Date.now());

  // Throttled scroll handler
  const throttledScroll = useThrottle((event: any) => {
    onScroll?.(event);
  }, 16); // ~60fps

  // Optimized viewable items handler
  const handleViewableItemsChanged = useCallback((info: {
    viewableItems: ViewToken[];
    changed: ViewToken[];
  }) => {
    if (debug) {
      logger.debug(`[OptimizedList] Viewable items: ${info.viewableItems.length}`);
    }
    onViewableItemsChanged?.(info);
  }, [onViewableItemsChanged, debug]);

  // Memoized item separator
  const ItemSeparator = useMemo(() => {
    return props.ItemSeparatorComponent || (() => null);
  }, [props.ItemSeparatorComponent]);

  // Optimized render item with performance tracking
  const optimizedRenderItem = useCallback<ListRenderItem<T>>((info) => {
    if (debug) {
      renderCount.current++;
      const now = Date.now();
      if (now - lastRenderTime.current > 1000) {
        logger.debug(`[OptimizedList] Render rate: ${renderCount.current} items/sec`);
        renderCount.current = 0;
        lastRenderTime.current = now;
      }
    }

    return renderItem(info);
  }, [renderItem, debug]);

  // Optimized key extractor
  const keyExtractor = useCallback((item: T, index: number) => {
    if (props.keyExtractor) {
      return props.keyExtractor(item, index);
    }
    // Default key extractor
    if ((item as any).id !== undefined) {
      return String((item as any).id);
    }
    if ((item as any).key !== undefined) {
      return String((item as any).key);
    }
    return String(index);
  }, [props.keyExtractor]);

  // Get item layout optimization
  const getItemLayout = useMemo(() => {
    if (itemHeight && !props.getItemLayout) {
      return (_: any, index: number) => ({
        length: itemHeight,
        offset: itemHeight * index,
        index
      });
    }
    return props.getItemLayout;
  }, [itemHeight, props.getItemLayout]);

  // Scroll to top utility
  const scrollToTop = useCallback(() => {
    listRef.current?.scrollToOffset({ offset: 0, animated: true });
  }, []);

  // Scroll to index utility
  const scrollToIndex = useCallback((index: number, animated = true) => {
    listRef.current?.scrollToIndex({ index, animated });
  }, []);

  // Optimized empty component
  const ListEmptyComponent = useMemo(() => {
    if (props.ListEmptyComponent) {
      return props.ListEmptyComponent;
    }
    return (
      <View style={styles.emptyContainer}>
        <Text style={styles.emptyText}>No items to display</Text>
      </View>
    );
  }, [props.ListEmptyComponent]);

  return (
    <FlatList
      ref={listRef}
      data={data}
      renderItem={optimizedRenderItem}
      keyExtractor={keyExtractor}
      getItemLayout={getItemLayout}
      ItemSeparatorComponent={ItemSeparator}
      ListEmptyComponent={ListEmptyComponent}
      
      // Performance optimizations
      removeClippedSubviews={removeClippedSubviews}
      maxToRenderPerBatch={maxToRenderPerBatch}
      updateCellsBatchingPeriod={updateCellsBatchingPeriod}
      windowSize={windowSize}
      initialNumToRender={initialNumToRender}
      onEndReachedThreshold={onEndReachedThreshold}
      
      // Scroll optimizations
      onScroll={throttledScroll}
      scrollEventThrottle={16}
      
      // Viewability
      onViewableItemsChanged={handleViewableItemsChanged}
      viewabilityConfig={viewabilityConfig}
      
      // Maintain position
      maintainVisibleContentPosition={
        maintainVisibleContentPosition
          ? {
              minIndexForVisible: 0,
              autoscrollToTopThreshold: 10
            }
          : undefined
      }
      
      // Debug mode
      debug={debug}
      
      {...props}
    />
  );
}

// Memoized list item wrapper for better performance
export const MemoizedListItem = React.memo<{
  item: any;
  renderItem: (item: any) => React.ReactElement;
}>(({ item, renderItem }) => {
  return renderItem(item);
}, (prevProps, nextProps) => {
  // Custom comparison for better performance
  return JSON.stringify(prevProps.item) === JSON.stringify(nextProps.item);
});

const styles = StyleSheet.create({
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
    minHeight: 200
  },
  emptyText: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center'
  }
});

// Export additional utilities
export { scrollToTop, scrollToIndex } from './listUtilities';