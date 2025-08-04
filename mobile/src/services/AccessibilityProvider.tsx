import React, { createContext, useState, useContext, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { AccessibilityInfo, Platform } from 'react-native';

import { logger } from '@/services/logger';
export interface AccessibilityPreferences {
  highContrast: boolean;
  largeText: boolean;
  reduceMotion: boolean;
  screenReader: boolean;
  hapticFeedback: boolean;
}

interface AccessibilityContextType {
  preferences: AccessibilityPreferences;
  updatePreferences: (preferences: Partial<AccessibilityPreferences>) => Promise<void>;
  isScreenReaderEnabled: boolean;
  getFontScale: () => number;
  getAccessibleColors: (normal: { background: string, text: string }) => { background: string, text: string };
}

const defaultPreferences: AccessibilityPreferences = {
  highContrast: false,
  largeText: false,
  reduceMotion: false,
  screenReader: false,
  hapticFeedback: true,
};

export const AccessibilityContext = createContext<AccessibilityContextType>({
  preferences: defaultPreferences,
  updatePreferences: async () => {},
  isScreenReaderEnabled: false,
  getFontScale: () => 1,
  getAccessibleColors: (normal) => normal,
});

export const useAccessibility = () => useContext(AccessibilityContext);

interface AccessibilityProviderProps {
  children: React.ReactNode;
}

export const AccessibilityProvider: React.FC<AccessibilityProviderProps> = ({ children }) => {
  const [preferences, setPreferences] = useState<AccessibilityPreferences>(defaultPreferences);
  const [isScreenReaderEnabled, setIsScreenReaderEnabled] = useState(false);
  
  // Load preferences on mount and listen for screen reader changes
  useEffect(() => {
    const loadPreferences = async () => {
      try {
        const storedPrefs = await AsyncStorage.getItem('accessibility_preferences');
        if (storedPrefs) {
          setPreferences(JSON.parse(storedPrefs));
        }
      } catch (error) {
        logger.error('Failed to load accessibility preferences:', error);
      }
    };
    
    const handleScreenReaderChanged = (isEnabled: boolean) => {
      setIsScreenReaderEnabled(isEnabled);
      updatePreferences({ screenReader: isEnabled });
    };
    
    // Check if screen reader is enabled
    AccessibilityInfo.isScreenReaderEnabled().then(setIsScreenReaderEnabled);
    
    // Subscribe to screen reader changes
    const subscription = AccessibilityInfo.addEventListener(
      'screenReaderChanged',
      handleScreenReaderChanged
    );
    
    loadPreferences();
    
    return () => {
      if (Platform.OS === 'ios') {
        // iOS uses a different return type
        subscription.remove();
      } else {
        // Android uses a function directly
        AccessibilityInfo.removeEventListener(
          'screenReaderChanged',
          handleScreenReaderChanged
        );
      }
    };
  }, []);
  
  const updatePreferences = async (newPrefs: Partial<AccessibilityPreferences>) => {
    try {
      const updatedPreferences = { ...preferences, ...newPrefs };
      setPreferences(updatedPreferences);
      await AsyncStorage.setItem('accessibility_preferences', JSON.stringify(updatedPreferences));
    } catch (error) {
      logger.error('Failed to save accessibility preferences:', error);
    }
  };
  
  const getFontScale = () => {
    return preferences.largeText ? 1.3 : 1.0;
  };
  
  const getAccessibleColors = (normal: { background: string, text: string }) => {
    if (preferences.highContrast) {
      return {
        background: '#000000',
        text: '#FFFFFF'
      };
    }
    return normal;
  };
  
  return (
    <AccessibilityContext.Provider
      value={{
        preferences,
        updatePreferences,
        isScreenReaderEnabled,
        getFontScale,
        getAccessibleColors,
      }}
    >
      {children}
    </AccessibilityContext.Provider>
  );
}; 