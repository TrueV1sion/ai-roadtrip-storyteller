/**
 * Lazy loading utilities for performance optimization
 */

import React, { lazy, Suspense, ComponentType } from 'react';
import { View, ActivityIndicator } from 'react-native';

// Loading component
const LoadingFallback = () => (
  <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
    <ActivityIndicator size="large" color="#0000ff" />
  </View>
);

/**
 * Create lazy loaded component with fallback
 */
export function lazyLoadComponent<T extends ComponentType<any>>(
  importFunc: () => Promise<{ default: T }>
): React.FC<React.ComponentProps<T>> {
  const LazyComponent = lazy(importFunc);
  
  return (props) => (
    <Suspense fallback={<LoadingFallback />}>
      <LazyComponent {...props} />
    </Suspense>
  );
}

/**
 * Preload component for faster access
 */
export async function preloadComponent(
  importFunc: () => Promise<any>
): Promise<void> {
  try {
    await importFunc();
  } catch (error) {
    console.error('Failed to preload component:', error);
  }
}

/**
 * Progressive image loading
 */
export const ProgressiveImage: React.FC<{
  source: { uri: string };
  placeholder?: { uri: string };
  style?: any;
}> = ({ source, placeholder, style }) => {
  const [loaded, setLoaded] = React.useState(false);
  
  return (
    <View style={style}>
      {placeholder && !loaded && (
        <Image
          source={placeholder}
          style={[style, { position: 'absolute' }]}
          blurRadius={2}
        />
      )}
      <Image
        source={source}
        style={style}
        onLoad={() => setLoaded(true)}
      />
    </View>
  );
};

/**
 * Lazy load routes for React Navigation
 */
export const lazyRoutes = {
  StoryScreen: lazyLoadComponent(() => import('../screens/StoryScreen')),
  BookingScreen: lazyLoadComponent(() => import('../screens/BookingScreen')),
  SettingsScreen: lazyLoadComponent(() => import('../screens/SettingsScreen')),
  ProfileScreen: lazyLoadComponent(() => import('../screens/ProfileScreen')),
  GameScreen: lazyLoadComponent(() => import('../screens/GameScreen')),
};

/**
 * Asset preloading for critical resources
 */
export class AssetPreloader {
  private static instance: AssetPreloader;
  private preloadedAssets: Map<string, any> = new Map();
  
  static getInstance(): AssetPreloader {
    if (!AssetPreloader.instance) {
      AssetPreloader.instance = new AssetPreloader();
    }
    return AssetPreloader.instance;
  }
  
  async preloadCriticalAssets(): Promise<void> {
    const criticalAssets = [
      require('../assets/images/logo.png'),
      require('../assets/images/map-marker.png'),
      require('../assets/sounds/notification.mp3'),
    ];
    
    await Promise.all(
      criticalAssets.map(async (asset, index) => {
        this.preloadedAssets.set(`critical_${index}`, asset);
      })
    );
  }
  
  async preloadVoiceAssets(voiceId: string): Promise<void> {
    // Preload voice-specific assets
    const voiceAssets = await fetch(`/api/voice/${voiceId}/assets`);
    this.preloadedAssets.set(`voice_${voiceId}`, voiceAssets);
  }
  
  getAsset(key: string): any {
    return this.preloadedAssets.get(key);
  }
}

/**
 * Memory-efficient list rendering
 */
export const OptimizedFlatList: React.FC<any> = (props) => {
  return (
    <FlatList
      {...props}
      removeClippedSubviews={true}
      maxToRenderPerBatch={10}
      updateCellsBatchingPeriod={50}
      initialNumToRender={10}
      windowSize={10}
      getItemLayout={props.getItemLayout}
      keyExtractor={props.keyExtractor || ((item, index) => index.toString())}
    />
  );
};
