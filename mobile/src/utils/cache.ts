/**
 * A simple LRU (Least Recently Used) cache implementation
 */
export class LRUCache<K, V> {
  private cache: Map<K, { value: V; timestamp: number }>;
  private readonly maxSize: number;
  private readonly ttl: number;

  constructor(maxSize: number, ttlSeconds: number) {
    this.cache = new Map();
    this.maxSize = maxSize;
    this.ttl = ttlSeconds * 1000; // Convert to milliseconds
  }

  /**
   * Get a value from the cache
   * @param key Cache key
   * @returns Cached value or undefined if not found
   */
  get(key: K): V | undefined {
    const item = this.cache.get(key);
    if (!item) return undefined;

    const now = Date.now();
    if (now - item.timestamp > this.ttl) {
      this.cache.delete(key);
      return undefined;
    }

    // Move to end (most recently used)
    this.cache.delete(key);
    this.cache.set(key, item);
    return item.value;
  }

  /**
   * Set a value in the cache
   * @param key Cache key
   * @param value Value to cache
   */
  set(key: K, value: V): void {
    if (this.cache.size >= this.maxSize) {
      // Remove least recently used item (first item)
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }

    this.cache.set(key, { value, timestamp: Date.now() });
  }

  /**
   * Clear all items from the cache
   */
  clear(): void {
    this.cache.clear();
  }

  /**
   * Get the number of items in the cache
   */
  size(): number {
    return this.cache.size;
  }

  /**
   * Check if a key exists in the cache
   * @param key Cache key
   */
  has(key: K): boolean {
    return this.cache.has(key);
  }

  /**
   * Get all keys in the cache
   */
  keys(): IterableIterator<K> {
    return this.cache.keys();
  }

  /**
   * Get all values in the cache
   */
  values(): IterableIterator<V> {
    return this.cache.values();
  }

  /**
   * Get all entries in the cache
   */
  entries(): IterableIterator<[K, V]> {
    return this.cache.entries();
  }
}

/**
 * Create a memoized version of a function with LRU caching
 * @param fn Function to memoize
 * @param maxSize Maximum cache size
 * @param ttlSeconds Time to live in seconds
 */
export function memoize<T extends (...args: any[]) => any>(
  fn: T,
  maxSize: number = 100,
  ttlSeconds: number = 3600
): T {
  const cache = new LRUCache<string, ReturnType<T>>(maxSize, ttlSeconds);

  return ((...args: Parameters<T>): ReturnType<T> => {
    const key = JSON.stringify(args);
    const cached = cache.get(key);
    
    if (cached !== undefined) {
      return cached;
    }

    const result = fn(...args);
    cache.set(key, result);
    return result;
  }) as T;
}

/**
 * Create an async memoized version of a function with LRU caching
 * @param fn Async function to memoize
 * @param maxSize Maximum cache size
 * @param ttlSeconds Time to live in seconds
 */
export function memoizeAsync<T extends (...args: any[]) => Promise<any>>(
  fn: T,
  maxSize: number = 100,
  ttlSeconds: number = 3600
): T {
  const cache = new LRUCache<string, { result: any; timestamp: number }>(maxSize, ttlSeconds);

  return (async (...args: Parameters<T>): Promise<ReturnType<T>> => {
    const key = JSON.stringify(args);
    const cached = cache.get(key);

    if (cached) {
      return cached.result;
    }

    const result = await fn(...args);
    cache.set(key, { result, timestamp: Date.now() });
    return result;
  }) as T;
} 