import React, { useState, useEffect, useRef } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  TouchableOpacity, 
  Platform, 
  ActivityIndicator,
  Alert
} from 'react-native';
import { Camera } from 'expo-camera';
import * as Location from 'expo-location';
import { Accelerometer, Magnetometer } from 'expo-sensors';
import { useIsFocused } from '@react-navigation/native';
import { ARPointResponse, ARRenderResponse, ARViewParameters } from '../../types/ar';
import { ApiClient } from '../../services/api/ApiClient';
import ARElement from './ARElement';
import ARControls from './ARControls';
import ARInfo from './ARInfo';

interface ARViewProps {
  types?: string[];
  radius?: number;
  onClose: () => void;
}

const ARView: React.FC<ARViewProps> = ({ 
  types = ['historical', 'navigation', 'nature'],
  radius = 500,
  onClose 
}) => {
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  const [arPoints, setARPoints] = useState<ARPointResponse[]>([]);
  const [renderableElements, setRenderableElements] = useState<ARRenderResponse | null>(null);
  const [selectedElement, setSelectedElement] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Sensor state
  const [location, setLocation] = useState<Location.LocationObject | null>(null);
  const [heading, setHeading] = useState(0);
  const [pitch, setPitch] = useState(0);
  
  // References
  const cameraRef = useRef<Camera>(null);
  const locationSubscription = useRef<Location.LocationSubscription | null>(null);
  const headingSubscription = useRef<Location.LocationHeadingSubscription | null>(null);
  const accelerometerSubscription = useRef<{ remove: () => void } | null>(null);
  
  const isFocused = useIsFocused();
  
  useEffect(() => {
    // Request permissions and initialize sensors
    (async () => {
      try {
        const { status: cameraStatus } = await Camera.requestCameraPermissionsAsync();
        const { status: locationStatus } = await Location.requestForegroundPermissionsAsync();
        
        if (cameraStatus !== 'granted' || locationStatus !== 'granted') {
          setHasPermission(false);
          setError('Camera and location permissions are required for AR features');
          return;
        }
        
        setHasPermission(true);
        
        // Start location tracking
        locationSubscription.current = await Location.watchPositionAsync(
          {
            accuracy: Location.Accuracy.BestForNavigation,
            distanceInterval: 5,
            timeInterval: 1000
          },
          (newLocation) => {
            setLocation(newLocation);
          }
        );
        
        // Start heading tracking
        headingSubscription.current = await Location.watchHeadingAsync((newHeading) => {
          setHeading(newHeading.trueHeading);
        });
        
        // Start accelerometer for pitch
        accelerometerSubscription.current = Accelerometer.addListener((data) => {
          // Convert accelerometer data to pitch angle
          const x = data.x;
          const y = data.y;
          const z = data.z;
          
          // Calculate pitch (in degrees)
          const pitch = Math.atan2(-x, Math.sqrt(y * y + z * z)) * (180 / Math.PI);
          setPitch(pitch);
        });
        
        // Set update interval for accelerometer
        Accelerometer.setUpdateInterval(100);
        
      } catch (err) {
        setError('Error initializing AR: ' + (err instanceof Error ? err.message : String(err)));
        setHasPermission(false);
      }
    })();
    
    // Cleanup subscriptions
    return () => {
      if (locationSubscription.current) {
        locationSubscription.current.remove();
      }
      if (headingSubscription.current) {
        headingSubscription.current.remove();
      }
      if (accelerometerSubscription.current) {
        accelerometerSubscription.current.remove();
      }
    };
  }, []);
  
  useEffect(() => {
    // Fetch AR points when location changes
    const fetchARPoints = async () => {
      if (!location || !isFocused) return;
      
      try {
        setLoading(true);
        
        // Fetch AR points
        const response = await ApiClient.post<ARPointResponse[]>('/ar/points', {
          latitude: location.coords.latitude,
          longitude: location.coords.longitude,
          radius: radius,
          types: types
        });
        
        setARPoints(response);
        
        // Get view parameters for rendering
        const viewParams: ARViewParameters = {
          device_heading: heading,
          device_pitch: pitch,
          camera_fov: 60.0 // Default FOV, could be calculated based on device
        };
        
        // Fetch renderable elements
        const renderResponse = await ApiClient.post<ARRenderResponse>('/ar/render', {
          latitude: location.coords.latitude,
          longitude: location.coords.longitude,
          radius: radius,
          types: types
        }, viewParams);
        
        setRenderableElements(renderResponse);
        setLoading(false);
      } catch (err) {
        setError('Error fetching AR data: ' + (err instanceof Error ? err.message : String(err)));
        setLoading(false);
      }
    };
    
    fetchARPoints();
    
    // Set up a timer to periodically refresh AR data
    const refreshTimer = setInterval(fetchARPoints, 10000);
    
    return () => {
      clearInterval(refreshTimer);
    };
  }, [location, isFocused, heading, pitch, radius, types]);
  
  if (hasPermission === null) {
    return <View style={styles.container}>
      <ActivityIndicator size="large" color="#0000ff" />
      <Text style={styles.text}>Requesting permissions...</Text>
    </View>;
  }
  
  if (hasPermission === false) {
    return <View style={styles.container}>
      <Text style={styles.errorText}>{error || 'Camera or location permission not granted'}</Text>
      <TouchableOpacity style={styles.button} onPress={onClose}>
        <Text style={styles.buttonText}>Close AR View</Text>
      </TouchableOpacity>
    </View>;
  }
  
  const handleElementPress = (elementId: string) => {
    setSelectedElement(elementId);
  };
  
  const closeElementInfo = () => {
    setSelectedElement(null);
  };
  
  return (
    <View style={styles.container}>
      <Camera
        ref={cameraRef}
        style={styles.camera}
        type={Camera.Constants.Type.BACK}
      >
        {loading && (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color="#ffffff" />
            <Text style={styles.loadingText}>Loading AR Experience...</Text>
          </View>
        )}
        
        {error && (
          <View style={styles.errorContainer}>
            <Text style={styles.errorText}>{error}</Text>
            <TouchableOpacity 
              style={styles.retryButton} 
              onPress={() => {
                setError(null);
                setLoading(true);
              }}
            >
              <Text style={styles.buttonText}>Retry</Text>
            </TouchableOpacity>
          </View>
        )}
        
        {/* Render AR elements */}
        {!loading && !error && renderableElements && renderableElements.elements.map((element) => (
          <ARElement
            key={element.id}
            element={element}
            onPress={() => handleElementPress(element.id)}
          />
        ))}
        
        {/* Show detailed info when an element is selected */}
        {selectedElement && renderableElements && (
          <ARInfo
            element={renderableElements.elements.find(e => e.id === selectedElement)!}
            onClose={closeElementInfo}
          />
        )}
        
        {/* AR Controls */}
        <ARControls onClose={onClose} />
        
        {/* Debug info - remove in production */}
        {__DEV__ && (
          <View style={styles.debugContainer}>
            <Text style={styles.debugText}>
              Heading: {heading.toFixed(1)}°{'\n'}
              Pitch: {pitch.toFixed(1)}°{'\n'}
              Elements: {renderableElements?.elements.length || 0}
            </Text>
          </View>
        )}
      </Camera>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  camera: {
    flex: 1,
  },
  text: {
    color: 'white',
    fontSize: 18,
    textAlign: 'center',
    marginTop: 10,
  },
  loadingContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.5)',
  },
  loadingText: {
    color: 'white',
    fontSize: 18,
    marginTop: 10,
  },
  errorContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.7)',
    padding: 20,
  },
  errorText: {
    color: 'red',
    fontSize: 18,
    textAlign: 'center',
    marginBottom: 20,
  },
  retryButton: {
    backgroundColor: '#2196F3',
    padding: 15,
    borderRadius: 5,
  },
  button: {
    backgroundColor: '#2196F3',
    padding: 15,
    borderRadius: 5,
    marginTop: 20,
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    textAlign: 'center',
  },
  debugContainer: {
    position: 'absolute',
    top: 40,
    left: 10,
    backgroundColor: 'rgba(0,0,0,0.5)',
    padding: 10,
    borderRadius: 5,
  },
  debugText: {
    color: 'white',
    fontSize: 12,
  },
});

export default ARView;