import React, { useEffect, useState } from 'react';
import { View, StyleSheet, ActivityIndicator } from 'react-native';
import { Text } from 'react-native-paper';
import { useRoute } from '@react-navigation/native';
import NetInfo from '@react-native-community/netinfo';

import MapComponent from './MapComponent';
import NavigationControls from './NavigationControls';
import NavigationHeader from './NavigationHeader';
import RouteDetails from './RouteDetails';
import StoryOverlay from '../stories/StoryOverlay';
import OfflineNotice from './OfflineNotice';
import { COLORS } from '../../theme';
import OfflineManager from '../../services/OfflineManager';

import { logger } from '@/services/logger';
interface NavigationContainerProps {
  route: any; // From route params
  onExit: () => void;
}

const NavigationContainer: React.FC<NavigationContainerProps> = ({ route, onExit }) => {
  const [isLoading, setIsLoading] = useState(true);
  const [navigationData, setNavigationData] = useState<any>(null);
  const [showStory, setShowStory] = useState(false);
  const [currentStoryIndex, setCurrentStoryIndex] = useState(0);
  const [isOffline, setIsOffline] = useState(false);
  const [offlineRoute, setOfflineRoute] = useState<any>(null);
  
  // Initialize and load route data
  useEffect(() => {
    // Initialize the navigation
    const initNavigation = async () => {
      try {
        setIsLoading(true);
        
        // Check if we have network
        const networkState = await NetInfo.fetch();
        const isConnected = networkState.isConnected;
        setIsOffline(!isConnected);
        
        if (!isConnected) {
          // Try to load offline route
          await loadOfflineRoute();
        } else {
          // Online mode - use the route data from params
          const { routeData } = route.params;
          setNavigationData(routeData);
          
          // If we have auto-download enabled, save this route for offline use
          const shouldAutoDownload = true; // This should come from settings
          if (shouldAutoDownload) {
            try {
              await OfflineManager.downloadRoute({
                id: routeData.routeId || `route_${Date.now()}`,
                originName: routeData.origin.name,
                destinationName: routeData.destination.name,
                routeData: routeData
              });
              logger.debug('Route saved for offline use');
            } catch (err) {
              logger.error('Failed to save route for offline use:', err);
            }
          }
        }
      } catch (error) {
        logger.error('Error initializing navigation:', error);
      } finally {
        setIsLoading(false);
      }
    };
    
    // Initialize the navigation when component mounts
    initNavigation();
    
    // Set up network connectivity listener
    const unsubscribe = NetInfo.addEventListener(state => {
      setIsOffline(!state.isConnected);
    });
    
    return () => {
      // Clean up network listener
      unsubscribe();
    };
  }, [route.params]);
  
  // Load offline route if available
  const loadOfflineRoute = async () => {
    try {
      const { routeData } = route.params;
      const routeId = routeData.routeId || `route_${routeData.origin.id}_${routeData.destination.id}`;
      
      // Check if we have this route available offline
      const offlineRouteData = await OfflineManager.getOfflineRoute(routeId);
      
      if (offlineRouteData) {
        setOfflineRoute(offlineRouteData);
        setNavigationData(offlineRouteData.routeData);
        logger.debug('Using offline route data');
      } else {
        logger.debug('No offline route data available');
        // Show error or fallback UI since we're offline with no cached data
      }
    } catch (error) {
      logger.error('Error loading offline route:', error);
    }
  };
  
  // Handle showing a story
  const handleShowStory = (index: number) => {
    setCurrentStoryIndex(index);
    setShowStory(true);
  };
  
  // Close story overlay
  const handleCloseStory = () => {
    setShowStory(false);
  };
  
  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={COLORS.primary} />
        <Text style={styles.loadingText}>Preparing your navigation...</Text>
      </View>
    );
  }
  
  if (!navigationData && isOffline) {
    return (
      <View style={styles.errorContainer}>
        <Text style={styles.errorTitle}>No offline data available</Text>
        <Text style={styles.errorMessage}>
          You are currently offline and this route hasn't been downloaded for offline use.
        </Text>
        <Text style={styles.errorHint}>
          Connect to the internet or try a different route that you've downloaded.
        </Text>
        <View style={styles.buttonContainer}>
          <Text onPress={onExit} style={styles.exitButton}>Return to Map</Text>
        </View>
      </View>
    );
  }
  
  return (
    <View style={styles.container}>
      {/* Map component */}
      <MapComponent 
        route={navigationData}
        isOffline={isOffline}
      />
      
      {/* Navigation header */}
      <NavigationHeader 
        destination={navigationData.destination}
        onExit={onExit}
      />
      
      {/* Offline notice */}
      {isOffline && <OfflineNotice />}
      
      {/* Route details panel */}
      <RouteDetails 
        route={navigationData}
        onShowStory={handleShowStory}
        isOffline={isOffline}
      />
      
      {/* Navigation controls */}
      <NavigationControls 
        onExit={onExit}
        isOffline={isOffline}
      />
      
      {/* Story overlay (shown when a story is selected) */}
      {showStory && (
        <StoryOverlay
          stories={navigationData.stories || []}
          initialIndex={currentStoryIndex}
          onClose={handleCloseStory}
          isOffline={isOffline}
        />
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: COLORS.background,
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: COLORS.background,
    padding: 20,
  },
  errorTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 12,
  },
  errorMessage: {
    fontSize: 16,
    textAlign: 'center',
    marginBottom: 8,
  },
  errorHint: {
    fontSize: 14,
    textAlign: 'center',
    color: COLORS.textSecondary,
    marginBottom: 24,
  },
  buttonContainer: {
    marginTop: 16,
  },
  exitButton: {
    fontSize: 16,
    color: COLORS.primary,
    padding: 10,
  },
});

export default NavigationContainer; 