import React, { useState, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Localization from 'expo-localization';

import i18n, { LocalizationContext } from './index';

import { logger } from '@/services/logger';
interface LocalizationProviderProps {
  children: React.ReactNode;
}

export const LocalizationProvider: React.FC<LocalizationProviderProps> = ({ children }) => {
  const [locale, setLocale] = useState(i18n.locale);
  
  useEffect(() => {
    // Load saved locale preference on mount
    const loadSavedLocale = async () => {
      try {
        const savedLocale = await AsyncStorage.getItem('user_locale');
        if (savedLocale) {
          i18n.locale = savedLocale;
          setLocale(savedLocale);
        }
      } catch (error) {
        logger.error('Failed to load locale preference:', error);
      }
    };
    
    loadSavedLocale();
  }, []);
  
  const handleSetLocale = async (newLocale: string) => {
    try {
      i18n.locale = newLocale;
      setLocale(newLocale);
      await AsyncStorage.setItem('user_locale', newLocale);
    } catch (error) {
      logger.error('Failed to save locale preference:', error);
    }
  };
  
  const localeName = (localeCode: string) => {
    const names: Record<string, string> = {
      en: 'English',
      es: 'Español',
      fr: 'Français',
      de: 'Deutsch',
      ja: '日本語',
      zh: '中文',
    };
    return names[localeCode] || localeCode;
  };
  
  const contextValue = {
    locale,
    t: (scope: string, options?: Record<string, any>) => i18n.t(scope, options),
    setLocale: handleSetLocale,
    locales: Object.keys(i18n.translations),
    localeName,
  };
  
  return (
    <LocalizationContext.Provider value={contextValue}>
      {children}
    </LocalizationContext.Provider>
  );
}; 