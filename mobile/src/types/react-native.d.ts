/**
 * Custom type declaration file for React Native
 * This helps TypeScript find and use the React Native types
 */

// This is just a reference to the existing React Native types
// It tells TypeScript to look for the real types in node_modules
declare module 'react-native' {
  export * from 'react-native/types';
} 