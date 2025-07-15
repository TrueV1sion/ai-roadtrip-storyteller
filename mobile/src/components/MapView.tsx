import React, { useState, useEffect, useRef } from 'react';
import { StyleSheet, View, Text, ActivityIndicator, Button, Alert } from 'react-native'; // Alert import is correct
import MapView, { Marker, Polyline, PROVIDER_GOOGLE } from 'react-native-maps'; // Removed MapViewProps import
import { locationService, LocationData } from '@services/locationService'; // Use alias
import { apiClient } from '@services/api/ApiClient'; // Use alias

// Interface for the backend directions response (matching backend/app/routes/utils.py)
interface DirectionsResponse {
  routes: Array<{
    overview_polyline?: { points: string }; // Encoded polyline string
    legs?: Array<any>; // Contains duration, distance, steps etc.
    // Add other fields as needed from Google Directions API response
  }>;
}

// Function to decode polyline (standard algorithm)
// Source: https://developers.google.com/maps/documentation/utilities/polylineutility
function decodePolyline(encoded: string): Array<{ latitude: number; longitude: number }> {
    let points: Array<{ latitude: number; longitude: number }> = [];
    let index = 0, len = encoded.length;
    let lat = 0, lng = 0;

    while (index < len) {
        let b, shift = 0, result = 0;
        do {
            b = encoded.charCodeAt(index++) - 63;
            result |= (b & 0x1f) << shift;
            shift += 5;
        } while (b >= 0x20);
        let dlat = ((result & 1) ? ~(result >> 1) : (result >> 1));
        lat += dlat;

        shift = 0;
        result = 0;
        do {
            b = encoded.charCodeAt(index++) - 63;
            result |= (b & 0x1f) << shift;
            shift += 5;
        } while (b >= 0x20);
        let dlng = ((result & 1) ? ~(result >> 1) : (result >> 1));
        lng += dlng;

        points.push({ latitude: lat / 1e5, longitude: lng / 1e5 });
    }
    return points;
}


const MapScreenComponent: React.FC = () => {
  const [currentLocation, setCurrentLocation] = useState<LocationData | null>(null);
  const [isLoadingLocation, setIsLoadingLocation] = useState(true);
  const [routeCoordinates, setRouteCoordinates] = useState<Array<{ latitude: number; longitude: number }>>([]);
  const [isFetchingRoute, setIsFetchingRoute] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mapRef = useRef<MapView>(null); // Keep the ref definition

  useEffect(() => {
    const fetchInitialLocation = async () => {
      setIsLoadingLocation(true);
      setError(null);
      await locationService.initialize();
      const location = await locationService.getCurrentLocation();
      if (location) {
        setCurrentLocation(location);
      } else {
        setError('Could not get current location. Please ensure location services are enabled.');
      }
      setIsLoadingLocation(false);
    };
    fetchInitialLocation();
  }, []);

  const fetchRoute = async (destination: string) => {
      if (!currentLocation) {
          Alert.alert("Error", "Current location not available to calculate route.");
          return;
      }
      setIsFetchingRoute(true);
      setError(null);
      setRouteCoordinates([]);

      try {
          const originString = `${currentLocation.latitude},${currentLocation.longitude}`;
          const response: DirectionsResponse = await apiClient.post('/api/directions', {
              origin: originString,
              destination: destination,
              mode: 'driving'
          });

          if (response.routes && response.routes.length > 0 && response.routes[0].overview_polyline) {
              const points = decodePolyline(response.routes[0].overview_polyline.points);
              setRouteCoordinates(points);
              // Fit map to route (Commented out due to ref type issue)
              // mapRef.current?.fitToCoordinates(points, {
              //     edgePadding: { top: 50, right: 50, bottom: 50, left: 50 },
              //     animated: true,
              // });
          } else {
              setError("No route found.");
          }
      } catch (err: any) {
          console.error("Error fetching directions:", err);
          setError(`Failed to fetch route: ${err.message || err}`);
      } finally {
          setIsFetchingRoute(false);
      }
  };

  if (isLoadingLocation) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" />
        <Text>Getting your location...</Text>
      </View>
    );
  }

  if (error && !currentLocation) {
      return (
          <View style={styles.centered}>
              <Text style={styles.errorText}>{error}</Text>
          </View>
      );
  }

  if (!currentLocation) {
       return (
          <View style={styles.centered}>
              <Text style={styles.errorText}>Location could not be determined.</Text>
          </View>
      );
  }

  return (
    <View style={styles.container}>
      <MapView
        // ref={mapRef} // Removed due to type error
        style={styles.map}
        provider={PROVIDER_GOOGLE}
        initialRegion={{
          latitude: currentLocation.latitude,
          longitude: currentLocation.longitude,
          latitudeDelta: 0.0922,
          longitudeDelta: 0.0421,
        }}
        showsUserLocation={true}
        loadingEnabled={true}
      >
        {routeCoordinates.length > 0 && (
          <Polyline
            coordinates={routeCoordinates}
            strokeColor="#007AFF"
            strokeWidth={4}
          />
        )}
      </MapView>
      <View style={styles.controls}>
        <Button
            title={isFetchingRoute ? "Fetching Route..." : "Route to Times Square"}
            onPress={() => fetchRoute("Times Square, New York, NY")}
            disabled={isFetchingRoute || !currentLocation}
        />
         {error && <Text style={styles.errorText}>{error}</Text>}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  map: {
    flex: 1,
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
   controls: {
    position: 'absolute',
    bottom: 20,
    left: 20,
    right: 20,
    backgroundColor: 'rgba(255,255,255,0.8)',
    padding: 10,
    borderRadius: 8,
  },
  errorText: {
      color: 'red',
      marginTop: 10,
      textAlign: 'center',
  }
});

export default MapScreenComponent;