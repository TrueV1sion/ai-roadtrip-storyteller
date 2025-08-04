import React, { useState, useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import { ActivityIndicator, View, StyleSheet } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { logger } from '@/services/logger';
import { initializeSentry } from '@/services/sentry/SentryService';
import { ENV } from '@/config/env.production';
import { SentryErrorBoundary } from '@/components/error/SentryErrorBoundary';
import EnhancedMobileSecurityService from '@/services/security/EnhancedMobileSecurityService';
import { DevelopmentConfig } from '@/config/development';
// Onboarding screens
import OnboardingScreen from './screens/OnboardingScreen';
import PermissionsScreen from './screens/PermissionsScreen';

// Main screens
import ImmersiveExperience from './screens/ImmersiveExperience';
import SpotifyAuthScreen from './screens/SpotifyAuthScreen';

// New UX enhancement screens
import AccessibilitySettingsScreen from './screens/AccessibilitySettingsScreen';
import LanguageSettingsScreen from './screens/LanguageSettingsScreen';
import OfflineDiscoveryScreen from './screens/OfflineDiscoveryScreen';

// Providers
import { LocalizationProvider } from './i18n/LocalizationProvider';
import { AccessibilityProvider } from './services/AccessibilityProvider';

// Define the root stack parameter list
export type RootStackParamList = {
  Onboarding: undefined;
  Permissions: undefined;
  Main: undefined;
  SpotifyAuth: undefined;
  AccessibilitySettings: undefined;
  LanguageSettings: undefined;
  OfflineDiscovery: undefined;
  ImmersiveExperience: undefined;
};

// Create the navigator
const Stack = createStackNavigator<RootStackParamList>();

export default function App() {
  const [isReady, setIsReady] = useState(false);
  const [initialRoute, setInitialRoute] = useState<keyof RootStackParamList>('Onboarding');
  
  // Initialize app and check onboarding status
  useEffect(() => {
    const initializeApp = async () => {
      try {
        // Skip Sentry in development if no DSN provided
        if (!__DEV__ || ENV.SENTRY_DSN) {
          await initializeSentry({
            dsn: ENV.SENTRY_DSN,
            environment: ENV.APP_ENV as 'development' | 'staging' | 'production',
            enableInDevelopment: false,
            tracesSampleRate: ENV.APP_ENV === 'production' ? 0.1 : 1.0,
            attachScreenshot: true,
            attachStacktrace: true,
          });
          logger.info('Sentry initialized successfully');
        } else {
          logger.info('Skipping Sentry in development mode');
        }
        
        // Skip security service in development if disabled
        if (!__DEV__ || !DevelopmentConfig.DISABLE_SECURITY) {
          await EnhancedMobileSecurityService.initialize();
          logger.info('Security service initialized successfully');
        } else {
          logger.info('Security service disabled in development mode');
        }
        
        // Check onboarding status
        const hasCompletedOnboarding = await AsyncStorage.getItem('hasCompletedOnboarding');
        if (hasCompletedOnboarding === 'true') {
          setInitialRoute('Main');
        }
      } catch (error) {
        logger.error('Error initializing app:', error);
      } finally {
        setIsReady(true);
      }
    };
    
    initializeApp();
  }, []);
  
  if (!isReady) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#6200ee" />
      </View>
    );
  }
  
  return (
    <SentryErrorBoundary 
      showDialog={true}
      enableAutoRecovery={true}
      onError={(error, errorInfo) => {
        logger.error('App Error Boundary caught error:', error, { errorInfo });
      }}
    >
      <GestureHandlerRootView style={{ flex: 1 }}>
        <SafeAreaProvider>
          <LocalizationProvider>
            <AccessibilityProvider>
              <NavigationContainer>
                <StatusBar style="auto" />
                <Stack.Navigator
                  initialRouteName={initialRoute}
                  screenOptions={{
                    headerShown: false,
                  }}
                >
                {/* Onboarding Flow */}
                <Stack.Screen name="Onboarding" component={OnboardingScreen} />
                <Stack.Screen name="Permissions" component={PermissionsScreen} />
                
                {/* Main App */}
                <Stack.Screen name="Main" component={ImmersiveExperience} />
                
                {/* Feature Screens */}
                <Stack.Screen 
                  name="SpotifyAuth" 
                  component={SpotifyAuthScreen} 
                  options={{
                    headerShown: true,
                    title: 'Connect to Spotify',
                  }}
                />
                
                {/* User Experience Enhancement Screens */}
                <Stack.Screen 
                  name="AccessibilitySettings" 
                  component={AccessibilitySettingsScreen} 
                  options={{
                    headerShown: true,
                    title: 'Accessibility',
                  }}
                />
                <Stack.Screen 
                  name="LanguageSettings" 
                  component={LanguageSettingsScreen} 
                  options={{
                    headerShown: true,
                    title: 'Language',
                  }}
                />
                <Stack.Screen 
                  name="OfflineDiscovery" 
                  component={OfflineDiscoveryScreen} 
                  options={{
                    headerShown: true,
                    title: 'Offline Content',
                  }}
                />
              </Stack.Navigator>
            </NavigationContainer>
          </AccessibilityProvider>
        </LocalizationProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
    </SentryErrorBoundary>
  );
}

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
}); 