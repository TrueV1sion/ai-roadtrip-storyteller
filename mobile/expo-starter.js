#!/usr/bin/env node

/**
 * Expo Starter with Module Fix
 * This wrapper handles the ES module issues
 */

// Set environment
process.env.EXPO_PUBLIC_API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';
process.env.NODE_NO_WARNINGS = '1';

// Clear require cache for problematic modules
const modulesToClear = ['expo-constants', 'expo-modules-core'];
modulesToClear.forEach(mod => {
  Object.keys(require.cache).forEach(key => {
    if (key.includes(mod)) {
      delete require.cache[key];
    }
  });
});

console.log('🚀 AI Road Trip Storyteller - Mobile App');
console.log('========================================');
console.log('');
console.log('Starting Expo development server...');
console.log('Backend API should be running at: http://localhost:8000');
console.log('');

// Start Expo CLI
try {
  require('expo/bin/cli');
} catch (error) {
  console.error('Error starting Expo:', error.message);
  console.log('');
  console.log('Try running: npm install --legacy-peer-deps');
}