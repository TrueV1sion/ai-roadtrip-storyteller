import React, { useState, useEffect } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  TouchableOpacity, 
  StatusBar,
  Alert,
  BackHandler
} from 'react-native';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { Camera } from 'expo-camera';
import * as Location from 'expo-location';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ARView } from '../components/ar';
import { FontAwesome5 } from '@expo/vector-icons';

type ARScreenParams = {
  mode?: 'historical' | 'navigation' | 'nature' | 'all';
  latitude?: number;
  longitude?: number;
  radius?: number;
  year?: number;
};

const ARScreen: React.FC = () => {
  const navigation = useNavigation();
  const route = useRoute<RouteProp<{ params: ARScreenParams }, 'params'>>();
  
  const [hasPermissions, setHasPermissions] = useState<boolean | null>(null);
  const [mode, setMode] = useState<string>(route.params?.mode || 'all');
  
  useEffect(() => {
    // Check for required permissions
    const checkPermissions = async () => {
      const [cameraPermission, locationPermission] = await Promise.all([
        Camera.requestCameraPermissionsAsync(),
        Location.requestForegroundPermissionsAsync()
      ]);
      
      if (cameraPermission.status !== 'granted' || locationPermission.status !== 'granted') {
        setHasPermissions(false);
        Alert.alert(
          'Permissions Required',
          'Camera and location permissions are required to use the AR features.',
          [
            { text: 'Cancel', style: 'cancel', onPress: () => navigation.goBack() },
            { text: 'Settings', onPress: () => {
              // Open settings - implementation may vary by platform
              navigation.goBack();
            }}
          ]
        );
      } else {
        setHasPermissions(true);
      }
    };
    
    checkPermissions();
    
    // Handle back button on Android
    const backHandler = BackHandler.addEventListener('hardwareBackPress', () => {
      navigation.goBack();
      return true;
    });
    
    return () => {
      backHandler.remove();
    };
  }, [navigation]);
  
  // Determine which AR point types to show based on mode
  const getARTypes = () => {
    switch (mode) {
      case 'historical':
        return ['historical'];
      case 'navigation':
        return ['navigation'];
      case 'nature':
        return ['nature'];
      case 'all':
      default:
        return ['historical', 'navigation', 'nature'];
    }
  };
  
  const handleCloseAR = () => {
    navigation.goBack();
  };
  
  if (hasPermissions === null) {
    // Still checking permissions
    return (
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="dark-content" />
        <View style={styles.messageContainer}>
          <Text style={styles.message}>Checking permissions...</Text>
        </View>
      </SafeAreaView>
    );
  }
  
  if (hasPermissions === false) {
    // Permissions denied
    return (
      <SafeAreaView style={styles.container}>
        <StatusBar barStyle="dark-content" />
        <View style={styles.messageContainer}>
          <FontAwesome5 name="exclamation-triangle" size={50} color="#ff9800" />
          <Text style={styles.errorTitle}>Permissions Required</Text>
          <Text style={styles.message}>
            Camera and location permissions are required to use the AR features.
          </Text>
          <TouchableOpacity 
            style={styles.button}
            onPress={() => navigation.goBack()}
          >
            <Text style={styles.buttonText}>Go Back</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }
  
  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="black" />
      <ARView 
        types={getARTypes()}
        radius={route.params?.radius || 500}
        onClose={handleCloseAR}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: 'black',
  },
  messageContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  errorTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    marginVertical: 10,
  },
  message: {
    fontSize: 16,
    textAlign: 'center',
    marginVertical: 10,
  },
  button: {
    backgroundColor: '#2196F3',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 5,
    marginTop: 20,
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
});

export default ARScreen;