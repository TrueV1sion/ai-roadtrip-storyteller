/**
 * Custom module declarations to help TypeScript resolve modules
 */

// React Native
declare module 'react-native' {
  // Include any missing exports here if needed
}

// Handle other common modules that might cause TypeScript errors
declare module '*.svg' {
  import React from 'react';
  import { SvgProps } from 'react-native-svg';
  const content: React.FC<SvgProps>;
  export default content;
}

declare module '*.png' {
  const content: number;
  export default content;
}

declare module '*.jpg' {
  const content: number;
  export default content;
}

declare module '*.json' {
  const content: any;
  export default content;
}

// Add module declarations for any libraries that might be missing types
declare module 'expo-status-bar' {
  import React from 'react';
  
  export type StatusBarStyle = 'auto' | 'inverted' | 'light' | 'dark';
  export type StatusBarAnimation = 'fade' | 'none' | 'slide';
  
  export interface StatusBarProps {
    style?: StatusBarStyle;
    hidden?: boolean;
    animated?: boolean;
    backgroundColor?: string;
    translucent?: boolean;
    networkActivityIndicatorVisible?: boolean;
    barStyle?: StatusBarStyle;
  }
  
  export class StatusBar extends React.Component<StatusBarProps> {}
  
  export default StatusBar;
}

// Add type definitions for AsyncStorage
declare module '@react-native-async-storage/async-storage' {
  const AsyncStorage: {
    getItem: (key: string) => Promise<string | null>;
    setItem: (key: string, value: string) => Promise<void>;
    removeItem: (key: string) => Promise<void>;
    mergeItem: (key: string, value: string) => Promise<void>;
    clear: () => Promise<void>;
    getAllKeys: () => Promise<string[]>;
    multiGet: (keys: string[]) => Promise<[string, string | null][]>;
    multiSet: (keyValuePairs: [string, string][]) => Promise<void>;
    multiRemove: (keys: string[]) => Promise<void>;
    multiMerge: (keyValuePairs: [string, string][]) => Promise<void>;
    flushGetRequests: () => void;
  };
  
  export default AsyncStorage;
}

// Add more missing type declarations as needed 