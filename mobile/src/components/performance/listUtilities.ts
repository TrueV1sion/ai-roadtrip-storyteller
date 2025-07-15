/**
 * List utilities for OptimizedList component
 */
import { RefObject } from 'react';
import { FlatList } from 'react-native';

export function scrollToTop<T>(listRef: RefObject<FlatList<T>>) {
  listRef.current?.scrollToOffset({ offset: 0, animated: true });
}

export function scrollToIndex<T>(
  listRef: RefObject<FlatList<T>>,
  index: number,
  animated = true
) {
  listRef.current?.scrollToIndex({ index, animated });
}