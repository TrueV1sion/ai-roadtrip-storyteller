import { createContext, useContext } from 'react';
import * as Localization from 'expo-localization';
import { I18n } from 'i18n-js';

// Import translations - these will be created separately
import en from './locales/en.json';

// Create base i18n instance
const i18n = new I18n({
  en,
  // Other languages will be added as they're created
});

// Set the locale from device or default to English
i18n.locale = Localization.locale.split('-')[0] || 'en';
i18n.enableFallback = true;
i18n.defaultLocale = 'en';

// Create context for localization
export interface LocalizationContextType {
  locale: string;
  t: (scope: string, options?: Record<string, any>) => string;
  setLocale: (locale: string) => void;
  locales: string[];
  localeName: (locale: string) => string;
}

export const LocalizationContext = createContext<LocalizationContextType>({
  locale: i18n.locale,
  t: (scope: string, options?: Record<string, any>) => i18n.t(scope, options),
  setLocale: (locale: string) => {},
  locales: ['en'],
  localeName: (locale: string) => {
    const names: Record<string, string> = {
      en: 'English',
      es: 'Español',
      fr: 'Français',
      de: 'Deutsch',
      ja: '日本語',
      zh: '中文',
    };
    return names[locale] || locale;
  }
});

// Create hook for using translations
export const useTranslation = () => useContext(LocalizationContext);

export default i18n; 