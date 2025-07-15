import { LRUCache, memoize, memoizeAsync } from '../cache';

describe('LRUCache', () => {
  let cache: LRUCache<string, number>;

  beforeEach(() => {
    cache = new LRUCache<string, number>(3, 1); // maxSize: 3, ttl: 1 second
  });

  test('should set and get values correctly', () => {
    cache.set('a', 1);
    cache.set('b', 2);
    
    expect(cache.get('a')).toBe(1);
    expect(cache.get('b')).toBe(2);
    expect(cache.get('c')).toBeUndefined();
  });

  test('should respect max size limit', () => {
    cache.set('a', 1);
    cache.set('b', 2);
    cache.set('c', 3);
    cache.set('d', 4); // Should evict oldest item

    expect(cache.get('a')).toBeUndefined(); // Should be evicted
    expect(cache.get('b')).toBe(2);
    expect(cache.get('c')).toBe(3);
    expect(cache.get('d')).toBe(4);
  });

  test('should respect TTL', async () => {
    cache.set('a', 1);
    
    expect(cache.get('a')).toBe(1);
    
    await new Promise(resolve => setTimeout(resolve, 1100)); // Wait for TTL
    
    expect(cache.get('a')).toBeUndefined();
  });

  test('should update access time on get', () => {
    cache.set('a', 1);
    cache.set('b', 2);
    cache.set('c', 3);
    
    // Access 'a' to make it most recently used
    cache.get('a');
    
    cache.set('d', 4); // Should evict oldest unaccessed item ('b')
    
    expect(cache.get('a')).toBe(1);
    expect(cache.get('b')).toBeUndefined();
    expect(cache.get('c')).toBe(3);
    expect(cache.get('d')).toBe(4);
  });
});

describe('memoize', () => {
  test('should cache function results', () => {
    const fn = jest.fn((x: number) => x * 2);
    const memoizedFn = memoize(fn, 2);

    expect(memoizedFn(2)).toBe(4);
    expect(memoizedFn(2)).toBe(4);
    expect(fn).toHaveBeenCalledTimes(1);
  });

  test('should respect max size', () => {
    const fn = jest.fn((x: number) => x * 2);
    const memoizedFn = memoize(fn, 2);

    memoizedFn(1);
    memoizedFn(2);
    memoizedFn(3); // Should evict memoizedFn(1) result
    memoizedFn(1); // Should recompute

    expect(fn).toHaveBeenCalledTimes(4);
  });
});

describe('memoizeAsync', () => {
  test('should cache async function results', async () => {
    const fn = jest.fn(async (x: number) => x * 2);
    const memoizedFn = memoizeAsync(fn, 2);

    expect(await memoizedFn(2)).toBe(4);
    expect(await memoizedFn(2)).toBe(4);
    expect(fn).toHaveBeenCalledTimes(1);
  });

  test('should handle errors', async () => {
    const error = new Error('test error');
    const fn = jest.fn(async () => { throw error; });
    const memoizedFn = memoizeAsync(fn, 2);

    await expect(memoizedFn()).rejects.toThrow(error);
    await expect(memoizedFn()).rejects.toThrow(error);
    expect(fn).toHaveBeenCalledTimes(2); // Should not cache errors
  });

  test('should not cache rejected promises', async () => {
    const fn = jest.fn(async (x: number) => {
      if (x < 0) throw new Error('negative');
      return x * 2;
    });
    const memoizedFn = memoizeAsync(fn, 2);

    await expect(memoizedFn(-1)).rejects.toThrow('negative');
    expect(await memoizedFn(2)).toBe(4);
    await expect(memoizedFn(-1)).rejects.toThrow('negative');
    expect(fn).toHaveBeenCalledTimes(3);
  });
}); 