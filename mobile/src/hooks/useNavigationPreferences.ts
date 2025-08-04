import { useState, useCallback, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { NavigationPreferences, TravelMode } from '../types/navigation';

import { logger } from '@/services/logger';
const DEFAULT_PREFERENCES: NavigationPreferences = {
  defaultMode: 'driving' as TravelMode,
  avoidTolls: false,
  avoidHighways: false,
  avoidFerries: false,
  preferScenicRoutes: true,
  maxDetourTime: 15,
  alertSettings: {
    trafficDelays: true,
    nearbyPOIs: true,
    speedLimits: true,
    weatherAlerts: true,
    roadConditions: true,
  },
  voiceSettings: {
    enabled: true,
    volume: 0.8,
    language: 'en-US',
    voiceType: 'standard',
  },
};

const STORAGE_KEY = '@navigation_preferences';

export const useNavigationPreferences = () => {
  const [preferences, setPreferences] = useState<NavigationPreferences>(
    DEFAULT_PREFERENCES
  );
  const [loading, setLoading] = useState(true);

  // Load preferences from storage
  useEffect(() => {
    const loadPreferences = async () => {
      try {
        const stored = await AsyncStorage.getItem(STORAGE_KEY);
        if (stored) {
          setPreferences({
            ...DEFAULT_PREFERENCES,
            ...JSON.parse(stored),
          });
        }
      } catch (error) {
        logger.error('Error loading navigation preferences:', error);
      } finally {
        setLoading(false);
      }
    };

    loadPreferences();
  }, []);

  // Update preferences
  const updatePreferences = useCallback(
    async (updates: Partial<NavigationPreferences>) => {
      const newPreferences = {
        ...preferences,
        ...updates,
      };
      setPreferences(newPreferences);

      try {
        await AsyncStorage.setItem(
          STORAGE_KEY,
          JSON.stringify(newPreferences)
        );
      } catch (error) {
        logger.error('Error saving navigation preferences:', error);
      }
    },
    [preferences]
  );

  // Reset to defaults
  const resetPreferences = useCallback(async () => {
    setPreferences(DEFAULT_PREFERENCES);
    try {
      await AsyncStorage.removeItem(STORAGE_KEY);
    } catch (error) {
      logger.error('Error resetting navigation preferences:', error);
    }
  }, []);

  // Update specific settings
  const updateAlertSettings = useCallback(
    (updates: Partial<NavigationPreferences['alertSettings']>) => {
      updatePreferences({
        alertSettings: {
          ...preferences.alertSettings,
          ...updates,
        },
      });
    },
    [preferences.alertSettings, updatePreferences]
  );

  const updateVoiceSettings = useCallback(
    (updates: Partial<NavigationPreferences['voiceSettings']>) => {
      updatePreferences({
        voiceSettings: {
          ...preferences.voiceSettings,
          ...updates,
        },
      });
    },
    [preferences.voiceSettings, updatePreferences]
  );

  return {
    preferences,
    loading,
    updatePreferences,
    resetPreferences,
    updateAlertSettings,
    updateVoiceSettings,
  };
}; 