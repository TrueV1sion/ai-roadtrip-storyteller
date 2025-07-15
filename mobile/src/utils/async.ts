/**
 * Sleep for a specified duration.
 * @param ms Duration in milliseconds
 */
export const sleep = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Configuration for retry operations
 */
export interface RetryConfig {
  maxAttempts: number;
  baseDelay: number;
  maxDelay: number;
  shouldRetry?: (error: any, attempt: number) => boolean;
  onRetry?: (error: any, attempt: number) => void;
}

/**
 * Default retry configuration
 */
export const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxAttempts: 3,
  baseDelay: 1000,  // 1 second
  maxDelay: 10000,  // 10 seconds
  shouldRetry: (error: any, attempt: number) => attempt < 3,
};

/**
 * Execute an async operation with retry logic
 * @param operation Function to execute
 * @param config Retry configuration
 */
export async function withRetry<T>(
  operation: () => Promise<T>,
  config: Partial<RetryConfig> = {}
): Promise<T> {
  const finalConfig = { ...DEFAULT_RETRY_CONFIG, ...config };
  let lastError: Error | null = null;

  for (let attempt = 1; attempt <= finalConfig.maxAttempts; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error as Error;

      if (
        attempt < finalConfig.maxAttempts &&
        finalConfig.shouldRetry?.(error, attempt)
      ) {
        // Calculate exponential backoff delay
        const delay = Math.min(
          finalConfig.baseDelay * Math.pow(2, attempt - 1),
          finalConfig.maxDelay
        );

        // Call onRetry callback if provided
        finalConfig.onRetry?.(error, attempt);

        // Wait before next attempt
        await sleep(delay);
        continue;
      }

      throw error;
    }
  }

  throw lastError;
}

/**
 * Execute multiple async operations with concurrency control
 * @param tasks Array of async operations
 * @param concurrency Maximum number of concurrent operations
 */
export async function withConcurrency<T>(
  tasks: (() => Promise<T>)[],
  concurrency: number
): Promise<T[]> {
  const results: T[] = [];
  const executing: Promise<void>[] = [];

  for (const task of tasks) {
    const p = Promise.resolve().then(async () => {
      const result = await task();
      results.push(result);
    });

    executing.push(p);

    if (executing.length >= concurrency) {
      await Promise.race(executing);
      executing.splice(
        0,
        executing.length,
        ...executing.filter((p) => !p.isFulfilled)
      );
    }
  }

  await Promise.all(executing);
  return results;
}

/**
 * Create a debounced version of an async function
 * @param fn Function to debounce
 * @param wait Wait time in milliseconds
 */
export function debounceAsync<T extends (...args: any[]) => Promise<any>>(
  fn: T,
  wait: number
): (...args: Parameters<T>) => Promise<ReturnType<T>> {
  let timeout: NodeJS.Timeout;
  let pendingPromise: Promise<ReturnType<T>> | null = null;

  return (...args: Parameters<T>): Promise<ReturnType<T>> => {
    if (pendingPromise) {
      return pendingPromise;
    }

    pendingPromise = new Promise((resolve, reject) => {
      const later = () => {
        timeout = undefined as any;
        pendingPromise = null;
        fn(...args).then(resolve).catch(reject);
      };

      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    });

    return pendingPromise;
  };
}

/**
 * Create a throttled version of an async function
 * @param fn Function to throttle
 * @param limit Time limit in milliseconds
 */
export function throttleAsync<T extends (...args: any[]) => Promise<any>>(
  fn: T,
  limit: number
): (...args: Parameters<T>) => Promise<ReturnType<T>> {
  let inThrottle = false;
  let lastResult: ReturnType<T>;

  return (...args: Parameters<T>): Promise<ReturnType<T>> => {
    if (!inThrottle) {
      inThrottle = true;
      lastResult = fn(...args);
      setTimeout(() => (inThrottle = false), limit);
    }
    return Promise.resolve(lastResult);
  };
} 