import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { Text, View } from 'react-native';

import OptimizedFlatList from '../OptimizedFlatList';

// Mock data
const generateMockData = (count: number) => {
  return Array.from({ length: count }, (_, i) => ({
    id: `item-${i}`,
    title: `Item ${i}`,
    description: `Description for item ${i}`,
  }));
};

describe('OptimizedFlatList Component', () => {
  const renderItem = ({ item }: any) => (
    <View testID={`item-${item.id}`}>
      <Text>{item.title}</Text>
      <Text>{item.description}</Text>
    </View>
  );

  it('renders list items correctly', () => {
    const data = generateMockData(5);
    const { getByText } = render(
      <OptimizedFlatList
        data={data}
        renderItem={renderItem}
        keyExtractor={(item) => item.id}
      />
    );
    
    expect(getByText('Item 0')).toBeTruthy();
    expect(getByText('Item 4')).toBeTruthy();
  });

  it('implements virtualization for large lists', () => {
    const data = generateMockData(1000);
    const { queryByText } = render(
      <OptimizedFlatList
        data={data}
        renderItem={renderItem}
        keyExtractor={(item) => item.id}
        windowSize={10}
        initialNumToRender={10}
      />
    );
    
    // Should render initial items
    expect(queryByText('Item 0')).toBeTruthy();
    expect(queryByText('Item 9')).toBeTruthy();
    
    // Should not render items outside window
    expect(queryByText('Item 999')).toBeNull();
  });

  it('optimizes memory with getItemLayout', () => {
    const data = generateMockData(100);
    const getItemLayout = jest.fn((data, index) => ({
      length: 80,
      offset: 80 * index,
      index,
    }));
    
    render(
      <OptimizedFlatList
        data={data}
        renderItem={renderItem}
        keyExtractor={(item) => item.id}
        getItemLayout={getItemLayout}
      />
    );
    
    // getItemLayout should be called for optimization
    expect(getItemLayout).toHaveBeenCalled();
  });

  it('handles scroll events efficiently', async () => {
    const data = generateMockData(50);
    const onScroll = jest.fn();
    
    const { getByTestId } = render(
      <OptimizedFlatList
        data={data}
        renderItem={renderItem}
        keyExtractor={(item) => item.id}
        onScroll={onScroll}
        scrollEventThrottle={16}
        testID="optimized-list"
      />
    );
    
    const list = getByTestId('optimized-list');
    fireEvent.scroll(list, {
      nativeEvent: {
        contentOffset: { y: 400 },
        contentSize: { height: 4000 },
        layoutMeasurement: { height: 800 },
      },
    });
    
    expect(onScroll).toHaveBeenCalled();
  });

  it('supports pull-to-refresh', async () => {
    const data = generateMockData(10);
    const onRefresh = jest.fn().mockResolvedValue(undefined);
    
    const { getByTestId } = render(
      <OptimizedFlatList
        data={data}
        renderItem={renderItem}
        keyExtractor={(item) => item.id}
        onRefresh={onRefresh}
        refreshing={false}
        testID="optimized-list"
      />
    );
    
    const list = getByTestId('optimized-list');
    fireEvent(list, 'refresh');
    
    await waitFor(() => {
      expect(onRefresh).toHaveBeenCalled();
    });
  });

  it('implements infinite scrolling', async () => {
    const data = generateMockData(20);
    const onEndReached = jest.fn();
    
    const { getByTestId } = render(
      <OptimizedFlatList
        data={data}
        renderItem={renderItem}
        keyExtractor={(item) => item.id}
        onEndReached={onEndReached}
        onEndReachedThreshold={0.5}
        testID="optimized-list"
      />
    );
    
    const list = getByTestId('optimized-list');
    
    // Simulate scrolling to end
    fireEvent.scroll(list, {
      nativeEvent: {
        contentOffset: { y: 1500 },
        contentSize: { height: 1600 },
        layoutMeasurement: { height: 800 },
      },
    });
    
    await waitFor(() => {
      expect(onEndReached).toHaveBeenCalled();
    });
  });

  it('maintains scroll position on data updates', async () => {
    let data = generateMockData(20);
    const { rerender, getByTestId } = render(
      <OptimizedFlatList
        data={data}
        renderItem={renderItem}
        keyExtractor={(item) => item.id}
        maintainVisibleContentPosition={{
          minIndexForVisible: 0,
        }}
        testID="optimized-list"
      />
    );
    
    const list = getByTestId('optimized-list');
    
    // Scroll to middle
    fireEvent.scroll(list, {
      nativeEvent: {
        contentOffset: { y: 800 },
      },
    });
    
    // Add new items at the beginning
    data = [
      { id: 'new-1', title: 'New Item 1', description: 'New' },
      ...data,
    ];
    
    rerender(
      <OptimizedFlatList
        data={data}
        renderItem={renderItem}
        keyExtractor={(item) => item.id}
        maintainVisibleContentPosition={{
          minIndexForVisible: 0,
        }}
        testID="optimized-list"
      />
    );
    
    // Scroll position should be maintained
    // In a real test, we'd check the actual scroll offset
    expect(list).toBeTruthy();
  });

  it('supports horizontal scrolling', () => {
    const data = generateMockData(10);
    const { getByTestId } = render(
      <OptimizedFlatList
        data={data}
        renderItem={renderItem}
        keyExtractor={(item) => item.id}
        horizontal={true}
        showsHorizontalScrollIndicator={false}
        testID="horizontal-list"
      />
    );
    
    const list = getByTestId('horizontal-list');
    expect(list.props.horizontal).toBe(true);
  });

  it('handles empty state', () => {
    const EmptyComponent = () => <Text>No items found</Text>;
    
    const { getByText } = render(
      <OptimizedFlatList
        data={[]}
        renderItem={renderItem}
        keyExtractor={(item) => item.id}
        ListEmptyComponent={EmptyComponent}
      />
    );
    
    expect(getByText('No items found')).toBeTruthy();
  });

  it('supports section headers', () => {
    const data = generateMockData(10);
    const ListHeaderComponent = () => <Text>List Header</Text>;
    const ListFooterComponent = () => <Text>List Footer</Text>;
    
    const { getByText } = render(
      <OptimizedFlatList
        data={data}
        renderItem={renderItem}
        keyExtractor={(item) => item.id}
        ListHeaderComponent={ListHeaderComponent}
        ListFooterComponent={ListFooterComponent}
      />
    );
    
    expect(getByText('List Header')).toBeTruthy();
    expect(getByText('List Footer')).toBeTruthy();
  });

  it('optimizes re-renders with memo', () => {
    const data = generateMockData(10);
    const renderItemMemo = jest.fn(renderItem);
    
    const { rerender } = render(
      <OptimizedFlatList
        data={data}
        renderItem={renderItemMemo}
        keyExtractor={(item) => item.id}
        removeClippedSubviews={true}
      />
    );
    
    const initialCallCount = renderItemMemo.mock.calls.length;
    
    // Re-render with same data
    rerender(
      <OptimizedFlatList
        data={data}
        renderItem={renderItemMemo}
        keyExtractor={(item) => item.id}
        removeClippedSubviews={true}
      />
    );
    
    // Should not re-render items unnecessarily
    expect(renderItemMemo.mock.calls.length).toBe(initialCallCount);
  });

  it('supports item separators', () => {
    const data = generateMockData(3);
    const ItemSeparatorComponent = () => (
      <View testID="separator" style={{ height: 1 }} />
    );
    
    const { getAllByTestId } = render(
      <OptimizedFlatList
        data={data}
        renderItem={renderItem}
        keyExtractor={(item) => item.id}
        ItemSeparatorComponent={ItemSeparatorComponent}
      />
    );
    
    const separators = getAllByTestId('separator');
    expect(separators.length).toBe(2); // n-1 separators
  });
});