/**
 * Performance polyfills and optimizations loaded before main module
 */

// Optimize console methods in production
if (!__DEV__) {
  global.console = {
    ...console,
    log: () => {},
    debug: () => {},
    info: () => {},
    warn: () => {},
    trace: () => {},
    // Keep error and assert for debugging critical issues
    error: console.error,
    assert: console.assert,
  };
}

// Performance timing polyfill
if (!global.performance) {
  global.performance = {
    now: () => Date.now(),
  };
}

// RequestIdleCallback polyfill
if (!global.requestIdleCallback) {
  global.requestIdleCallback = (callback, options = {}) => {
    const timeout = options.timeout || 50;
    const start = Date.now();
    
    return setTimeout(() => {
      callback({
        didTimeout: false,
        timeRemaining: () => Math.max(0, timeout - (Date.now() - start)),
      });
    }, 0);
  };
}

if (!global.cancelIdleCallback) {
  global.cancelIdleCallback = clearTimeout;
}

// Optimize Promise handling
const originalPromise = global.Promise;
global.Promise = class OptimizedPromise extends originalPromise {
  constructor(executor) {
    super((resolve, reject) => {
      // Wrap executor to catch synchronous errors
      try {
        executor(resolve, reject);
      } catch (error) {
        reject(error);
      }
    });
  }
};

// Image preloading optimization
global.preloadImages = (urls) => {
  if (!Array.isArray(urls)) return;
  
  urls.forEach(url => {
    const img = new Image();
    img.src = url;
  });
};

// Memory pressure handler
let memoryPressureCallbacks = [];
global.onMemoryPressure = (callback) => {
  memoryPressureCallbacks.push(callback);
};

// Simulate memory pressure detection (would need native module in production)
if (__DEV__) {
  setInterval(() => {
    if (performance.memory && performance.memory.usedJSHeapSize > performance.memory.totalJSHeapSize * 0.9) {
      memoryPressureCallbacks.forEach(cb => cb());
    }
  }, 30000);
}

// Optimize Array methods for large datasets
const originalMap = Array.prototype.map;
Array.prototype.map = function(callback, thisArg) {
  // Use native map for small arrays
  if (this.length < 1000) {
    return originalMap.call(this, callback, thisArg);
  }
  
  // Optimized implementation for large arrays
  const result = new Array(this.length);
  for (let i = 0; i < this.length; i++) {
    if (i in this) {
      result[i] = callback.call(thisArg, this[i], i, this);
    }
  }
  return result;
};

// Export for use in other modules
module.exports = {
  onMemoryPressure: global.onMemoryPressure,
  preloadImages: global.preloadImages,
};