/**
 * Memory management utilities for mobile app
 */

interface MemoryStats {
  used: number;
  limit: number;
  percentage: number;
}

export class MemoryManager {
  private static instance: MemoryManager;
  private memoryWarningThreshold = 0.8; // 80% of limit
  private caches: Map<string, WeakMap<any, any>> = new Map();
  
  static getInstance(): MemoryManager {
    if (!MemoryManager.instance) {
      MemoryManager.instance = new MemoryManager();
    }
    return MemoryManager.instance;
  }
  
  constructor() {
    this.setupMemoryMonitoring();
  }
  
  private setupMemoryMonitoring(): void {
    // Monitor memory usage every 30 seconds
    setInterval(() => {
      const stats = this.getMemoryStats();
      if (stats.percentage > this.memoryWarningThreshold) {
        this.performMemoryCleanup();
      }
    }, 30000);
  }
  
  getMemoryStats(): MemoryStats {
    // This would use native modules in production
    const used = 120; // MB (simulated)
    const limit = 150; // MB (simulated)
    
    return {
      used,
      limit,
      percentage: used / limit
    };
  }
  
  performMemoryCleanup(): void {
    console.log('Performing memory cleanup...');
    
    // Clear non-critical caches
    this.clearCache('images', 0.5); // Keep 50% of images
    this.clearCache('stories', 0.3); // Keep 30% of stories
    this.clearCache('voice', 0.2); // Keep 20% of voice data
    
    // Force garbage collection if available
    if (global.gc) {
      global.gc();
    }
  }
  
  createCache(name: string): WeakMap<any, any> {
    const cache = new WeakMap();
    this.caches.set(name, cache);
    return cache;
  }
  
  clearCache(name: string, keepPercentage: number = 0): void {
    const cache = this.caches.get(name);
    if (cache && keepPercentage === 0) {
      // WeakMap will be garbage collected
      this.caches.delete(name);
    }
    // Partial clearing would require different data structure
  }
  
  // Story-specific memory management
  cleanupStoryResources(storyId: string): void {
    // Clean up story-specific resources
    const storyCache = this.caches.get('stories');
    if (storyCache) {
      // Remove story data
      // In practice, this would be more sophisticated
    }
  }
  
  // Image memory optimization
  optimizeImageMemory(imageUri: string, maxWidth: number, maxHeight: number): string {
    // Return optimized image URI with size constraints
    return `${imageUri}?w=${maxWidth}&h=${maxHeight}&q=80`;
  }
  
  // Audio buffer management
  private audioBuffers: Map<string, ArrayBuffer> = new Map();
  
  preloadAudioBuffer(audioId: string, buffer: ArrayBuffer): void {
    // Limit audio buffer cache size
    if (this.audioBuffers.size > 10) {
      // Remove oldest buffers
      const firstKey = this.audioBuffers.keys().next().value;
      this.audioBuffers.delete(firstKey);
    }
    
    this.audioBuffers.set(audioId, buffer);
  }
  
  getAudioBuffer(audioId: string): ArrayBuffer | undefined {
    return this.audioBuffers.get(audioId);
  }
  
  // Prevent memory leaks in components
  createCleanupManager() {
    const subscriptions: Array<() => void> = [];
    const timeouts: number[] = [];
    const intervals: number[] = [];
    
    return {
      addSubscription: (cleanup: () => void) => {
        subscriptions.push(cleanup);
      },
      
      addTimeout: (id: number) => {
        timeouts.push(id);
      },
      
      addInterval: (id: number) => {
        intervals.push(id);
      },
      
      cleanup: () => {
        subscriptions.forEach(cleanup => cleanup());
        timeouts.forEach(id => clearTimeout(id));
        intervals.forEach(id => clearInterval(id));
        
        subscriptions.length = 0;
        timeouts.length = 0;
        intervals.length = 0;
      }
    };
  }
}

// React hook for memory-aware components
export function useMemoryAware() {
  const [memoryStats, setMemoryStats] = React.useState<MemoryStats>({
    used: 0,
    limit: 150,
    percentage: 0
  });
  
  const [isLowMemory, setIsLowMemory] = React.useState(false);
  
  React.useEffect(() => {
    const manager = MemoryManager.getInstance();
    
    const checkMemory = () => {
      const stats = manager.getMemoryStats();
      setMemoryStats(stats);
      setIsLowMemory(stats.percentage > 0.8);
    };
    
    checkMemory();
    const interval = setInterval(checkMemory, 10000);
    
    return () => clearInterval(interval);
  }, []);
  
  return { memoryStats, isLowMemory };
}
