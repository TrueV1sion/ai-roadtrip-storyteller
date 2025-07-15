import React, { useState, useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import { ActivityIndicator, View, StyleSheet } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import AsyncStorage from '@react-native-async-storage/async-storage';

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
  
  // Check if the user has completed onboarding
  useEffect(() => {
    const checkOnboardingStatus = async () => {
      try {
        const hasCompletedOnboarding = await AsyncStorage.getItem('hasCompletedOnboarding');
        if (hasCompletedOnboarding === 'true') {
          setInitialRoute('Main');
        }
      } catch (error) {
        console.error('Error checking onboarding status:', error);
      } finally {
        setIsReady(true);
      }
    };
    
    checkOnboardingStatus();
  }, []);
  
  if (!isReady) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#6200ee" />
      </View>
    );
  }
  
  return (
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
  );
}

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
}); 