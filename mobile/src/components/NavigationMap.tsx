import React, { useEffect, useRef, useState, useCallback } from 'react';
import { View, StyleSheet, Dimensions, Platform } from 'react-native';
import { logger } from '@/services/logger';
import MapView, { 
  PROVIDER_GOOGLE, 
  Marker, 
  Polyline, 
  Camera,
  Region 
} from 'react-native-maps';
import { MaterialIcons } from '@expo/vector-icons';
import * as Location from 'expo-location';

import { NavigationMapControls } from './NavigationMapControls';
import { NavigationOverlay } from './NavigationOverlay';
import { mapStyles } from '../styles/mapStyles';
import { useTheme } from '../hooks/useTheme';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

interface NavigationMapProps {
  route: any; // Google Directions route
  currentStepIndex: number;
  distanceToNextManeuver: number;
  timeToNextManeuver: number;
  currentSpeed: number;
  onNavigationUpdate: (update: any) => void;
}

export const NavigationMap: React.FC<NavigationMapProps> = ({
  route,
  currentStepIndex,
  distanceToNextManeuver,
  timeToNextManeuver,
  currentSpeed,
  onNavigationUpdate
}) => {
  const mapRef = useRef<MapView>(null);
  const { theme, isDarkMode } = useTheme();
  
  // State
  const [currentLocation, setCurrentLocation] = useState<Location.LocationObject | null>(null);
  const [heading, setHeading] = useState<number>(0);
  const [mapMode, setMapMode] = useState<'navigation' | 'overview'>('navigation');
  const [tilt, setTilt] = useState<number>(60); // 3D tilt angle
  const [zoom, setZoom] = useState<number>(18); // Zoom level for navigation
  const [locationSubscription, setLocationSubscription] = useState<Location.LocationSubscription | null>(null);

  // Navigation camera settings
  const NAVIGATION_CAMERA = {
    pitch: 60, // 3D perspective
    heading: 0, // Will be updated with device heading
    altitude: 200, // Height in meters
    zoom: 18, // Close zoom for navigation
  };

  const OVERVIEW_CAMERA = {
    pitch: 0, // Top-down view
    heading: 0,
    altitude: 5000,
    zoom: 14,
  };

  // Start location tracking
  useEffect(() => {
    startLocationTracking();
    return () => {
      if (locationSubscription) {
        locationSubscription.remove();
      }
    };
  }, []);

  const startLocationTracking = async () => {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        logger.error('Location permission denied');
        return;
      }

      // High accuracy location tracking for navigation
      const subscription = await Location.watchPositionAsync(
        {
          accuracy: Location.Accuracy.BestForNavigation,
          timeInterval: 1000, // Update every second
          distanceInterval: 5, // Or every 5 meters
        },
        (location) => {
          handleLocationUpdate(location);
        }
      );

      setLocationSubscription(subscription);

      // Also watch heading for rotation
      Location.watchHeadingAsync((headingData) => {
        setHeading(headingData.trueHeading);
        if (mapMode === 'navigation') {
          updateNavigationCamera(currentLocation, headingData.trueHeading);
        }
      });
    } catch (error) {
      logger.error('Error starting location tracking:', error);
    }
  };

  const handleLocationUpdate = (location: Location.LocationObject) => {
    setCurrentLocation(location);
    
    // Calculate navigation metrics
    if (route && currentStepIndex < route.legs[0].steps.length) {
      const currentStep = route.legs[0].steps[currentStepIndex];
      const nextPoint = currentStep.end_location;
      
      // Calculate distance to next maneuver
      const distance = calculateDistance(
        location.coords.latitude,
        location.coords.longitude,
        nextPoint.lat,
        nextPoint.lng
      );
      
      // Notify parent component
      onNavigationUpdate({
        currentLocation: {
          lat: location.coords.latitude,
          lng: location.coords.longitude
        },
        distanceToNextManeuver: distance,
        currentSpeed: location.coords.speed || 0,
        heading: location.coords.heading || 0
      });
    }

    // Update camera if in navigation mode
    if (mapMode === 'navigation') {
      updateNavigationCamera(location, heading);
    }
  };

  const updateNavigationCamera = (location: Location.LocationObject | null, currentHeading: number) => {
    if (!location || !mapRef.current) return;

    const camera: Camera = {
      center: {
        latitude: location.coords.latitude,
        longitude: location.coords.longitude,
      },
      pitch: NAVIGATION_CAMERA.pitch,
      heading: currentHeading, // Rotate map to match travel direction
      altitude: NAVIGATION_CAMERA.altitude,
      zoom: NAVIGATION_CAMERA.zoom,
    };

    mapRef.current.animateCamera(camera, { duration: 1000 });
  };

  const toggleMapMode = () => {
    const newMode = mapMode === 'navigation' ? 'overview' : 'navigation';
    setMapMode(newMode);

    if (newMode === 'overview' && mapRef.current && currentLocation) {
      // Show full route overview
      const camera: Camera = {
        center: {
          latitude: currentLocation.coords.latitude,
          longitude: currentLocation.coords.longitude,
        },
        ...OVERVIEW_CAMERA
      };
      mapRef.current.animateCamera(camera, { duration: 500 });
    } else if (newMode === 'navigation') {
      updateNavigationCamera(currentLocation, heading);
    }
  };

  const recenterMap = () => {
    if (currentLocation) {
      updateNavigationCamera(currentLocation, heading);
    }
  };

  // Calculate route polyline coordinates
  const getRoutePolyline = () => {
    if (!route) return [];
    
    const coordinates: any[] = [];
    route.legs.forEach((leg: any) => {
      leg.steps.forEach((step: any) => {
        // Decode polyline or use coordinates
        if (step.polyline) {
          coordinates.push(...decodePolyline(step.polyline.points));
        }
      });
    });
    
    return coordinates;
  };

  // Get upcoming maneuver for arrow display
  const getUpcomingManeuver = () => {
    if (!route || currentStepIndex >= route.legs[0].steps.length) return null;
    
    const currentStep = route.legs[0].steps[currentStepIndex];
    return {
      type: currentStep.maneuver,
      instruction: currentStep.html_instructions,
      distance: distanceToNextManeuver
    };
  };

  return (
    <View style={styles.container}>
      <MapView
        ref={mapRef}
        provider={PROVIDER_GOOGLE}
        style={styles.map}
        customMapStyle={isDarkMode ? mapStyles.dark : mapStyles.light}
        showsUserLocation={false} // We'll use custom marker
        showsMyLocationButton={false}
        showsCompass={false}
        rotateEnabled={true}
        pitchEnabled={true}
        toolbarEnabled={false}
        loadingEnabled={true}
        moveOnMarkerPress={false}
      >
        {/* Route polyline */}
        <Polyline
          coordinates={getRoutePolyline()}
          strokeColor={theme.colors.primary}
          strokeWidth={6}
          lineJoin="round"
          lineCap="round"
        />

        {/* Traveled route (different color) */}
        <Polyline
          coordinates={getTraveledRoute()}
          strokeColor={theme.colors.primaryLight}
          strokeWidth={6}
          lineJoin="round"
          lineCap="round"
        />

        {/* Current location marker with heading */}
        {currentLocation && (
          <Marker
            coordinate={{
              latitude: currentLocation.coords.latitude,
              longitude: currentLocation.coords.longitude,
            }}
            anchor={{ x: 0.5, y: 0.5 }}
            rotation={heading}
            flat={true}
          >
            <View style={styles.locationMarker}>
              <MaterialIcons 
                name="navigation" 
                size={32} 
                color={theme.colors.primary}
                style={{ transform: [{ rotate: `${heading}deg` }] }}
              />
            </View>
          </Marker>
        )}

        {/* Destination marker */}
        {route && (
          <Marker
            coordinate={{
              latitude: route.legs[route.legs.length - 1].end_location.lat,
              longitude: route.legs[route.legs.length - 1].end_location.lng,
            }}
          >
            <MaterialIcons name="place" size={32} color={theme.colors.error} />
          </Marker>
        )}
      </MapView>

      {/* Navigation overlay with turn instructions */}
      <NavigationOverlay
        currentStep={route?.legs[0].steps[currentStepIndex]}
        nextStep={route?.legs[0].steps[currentStepIndex + 1]}
        distanceToManeuver={distanceToNextManeuver}
        timeToManeuver={timeToNextManeuver}
        currentSpeed={currentSpeed}
      />

      {/* Map controls */}
      <NavigationMapControls
        mapMode={mapMode}
        onToggleMode={toggleMapMode}
        onRecenter={recenterMap}
        onZoomIn={() => setZoom(Math.min(zoom + 1, 20))}
        onZoomOut={() => setZoom(Math.max(zoom - 1, 10))}
      />
    </View>
  );
};

// Helper functions
const calculateDistance = (lat1: number, lon1: number, lat2: number, lon2: number): number => {
  const R = 6371e3; // Earth's radius in meters
  const φ1 = lat1 * Math.PI / 180;
  const φ2 = lat2 * Math.PI / 180;
  const Δφ = (lat2 - lat1) * Math.PI / 180;
  const Δλ = (lon2 - lon1) * Math.PI / 180;

  const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
          Math.cos(φ1) * Math.cos(φ2) *
          Math.sin(Δλ/2) * Math.sin(Δλ/2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));

  return R * c;
};

const decodePolyline = (encoded: string): Array<{latitude: number, longitude: number}> => {
  // Google polyline decoder
  const points: Array<{latitude: number, longitude: number}> = [];
  let index = 0;
  let lat = 0;
  let lng = 0;

  while (index < encoded.length) {
    let shift = 0;
    let result = 0;
    let byte;

    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);

    const dlat = ((result & 1) ? ~(result >> 1) : (result >> 1));
    lat += dlat;

    shift = 0;
    result = 0;

    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);

    const dlng = ((result & 1) ? ~(result >> 1) : (result >> 1));
    lng += dlng;

    points.push({
      latitude: lat / 1e5,
      longitude: lng / 1e5,
    });
  }

  return points;
};

const getTraveledRoute = () => {
  // TODO: Implement based on current position and route progress
  return [];
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  map: {
    ...StyleSheet.absoluteFillObject,
  },
  locationMarker: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'white',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 5,
  },
});