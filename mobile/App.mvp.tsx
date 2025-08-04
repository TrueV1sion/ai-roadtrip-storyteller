import React, { useEffect, useState } from 'react';
import { StatusBar } from 'expo-status-bar';
import { StyleSheet, View, Text, ActivityIndicator } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import * as Font from 'expo-font';
import { Ionicons } from '@expo/vector-icons';

// MVP Screen
import SimpleMVPNavigationScreen from './src/screens/SimpleMVPNavigationScreen';

// Feature configuration
import { FEATURES } from './src/config/features';

const Stack = createStackNavigator();

// Loading screen component
const LoadingScreen = () => (
  <View style={styles.loadingContainer}>
    <ActivityIndicator size="large" color="#007AFF" />
    <Text style={styles.loadingText}>Loading AI Road Trip...</Text>
  </View>
);

export default function App() {
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    // Load required assets
    const loadAssets = async () => {
      try {
        // Load fonts
        await Font.loadAsync({
          ...Ionicons.font,
        });
        
        // Add any other initialization here
        
        setIsReady(true);
      } catch (error) {
        console.error('Error loading assets:', error);
        // Still set ready to true to avoid infinite loading
        setIsReady(true);
      }
    };

    loadAssets();
  }, []);

  if (!isReady) {
    return (
      <SafeAreaProvider>
        <LoadingScreen />
      </SafeAreaProvider>
    );
  }

  return (
    <SafeAreaProvider>
      <NavigationContainer>
        <Stack.Navigator
          screenOptions={{
            headerStyle: {
              backgroundColor: '#007AFF',
            },
            headerTintColor: '#FFFFFF',
            headerTitleStyle: {
              fontWeight: '600',
            },
          }}
        >
          <Stack.Screen
            name="Navigation"
            component={SimpleMVPNavigationScreen}
            options={{
              title: 'AI Road Trip Storyteller',
              headerShown: true,
            }}
          />
        </Stack.Navigator>
      </NavigationContainer>
      <StatusBar style="light" />
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#666666',
  },
});