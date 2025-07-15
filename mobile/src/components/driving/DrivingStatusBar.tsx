import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Animated,
  Platform
} from 'react-native';
import { FontAwesome5, MaterialIcons, Ionicons } from '@expo/vector-icons';
import { DrivingStatusType } from '../../types/driving';

interface DrivingStatusBarProps {
  status: DrivingStatusType;
  onRestBreakPress?: () => void;
  onFuelStationPress?: () => void;
  onTrafficPress?: () => void;
}

const DrivingStatusBar: React.FC<DrivingStatusBarProps> = ({
  status,
  onRestBreakPress,
  onFuelStationPress,
  onTrafficPress
}) => {
  const [alertAnimation] = useState(new Animated.Value(1));
  
  // Setup alert animation if there are alerts
  useEffect(() => {
    if (status.alerts && status.alerts.length > 0) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(alertAnimation, {
            toValue: 0.4,
            duration: 500,
            useNativeDriver: true
          }),
          Animated.timing(alertAnimation, {
            toValue: 1,
            duration: 500,
            useNativeDriver: true
          })
        ])
      ).start();
    } else {
      alertAnimation.setValue(1);
    }
  }, [status.alerts]);
  
  // Get rest indicator color based on driver fatigue level
  const getRestColor = () => {
    switch (status.driver_fatigue_level) {
      case 'high':
        return '#FF5252';
      case 'moderate':
        return '#FFC107';
      default:
        return '#4CAF50';
    }
  };
  
  // Get fuel indicator color based on fuel level
  const getFuelColor = () => {
    if (status.fuel_level <= 10) {
      return '#FF5252';
    } else if (status.fuel_level <= 20) {
      return '#FFC107';
    } else {
      return '#4CAF50';
    }
  };
  
  // Format driving time in hours and minutes
  const formatDrivingTime = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    
    if (hours > 0) {
      return `${hours}h ${mins}m`;
    } else {
      return `${mins}m`;
    }
  };
  
  // Format distance
  const formatDistance = (km: number) => {
    return `${km.toFixed(1)} km`;
  };
  
  return (
    <View style={styles.container}>
      {/* Rest indicator */}
      <TouchableOpacity 
        style={[styles.indicatorContainer, { opacity: status.rest_break_due ? 0.9 : 0.7 }]}
        onPress={onRestBreakPress}
        disabled={!onRestBreakPress}
      >
        <Animated.View style={[
          styles.iconContainer,
          { backgroundColor: getRestColor(), opacity: status.rest_break_due ? alertAnimation : 1 }
        ]}>
          <FontAwesome5 name="bed" size={16} color="white" />
        </Animated.View>
        <View style={styles.indicatorTextContainer}>
          <Text style={styles.indicatorLabel}>Driving Time</Text>
          <Text style={styles.indicatorValue}>{formatDrivingTime(status.driving_time)}</Text>
        </View>
      </TouchableOpacity>
      
      {/* Fuel indicator */}
      <TouchableOpacity 
        style={[styles.indicatorContainer, { opacity: status.fuel_level <= 20 ? 0.9 : 0.7 }]}
        onPress={onFuelStationPress}
        disabled={!onFuelStationPress}
      >
        <Animated.View style={[
          styles.iconContainer,
          { backgroundColor: getFuelColor(), opacity: status.fuel_level <= 20 ? alertAnimation : 1 }
        ]}>
          <FontAwesome5 name="gas-pump" size={16} color="white" />
        </Animated.View>
        <View style={styles.indicatorTextContainer}>
          <Text style={styles.indicatorLabel}>Fuel</Text>
          <Text style={styles.indicatorValue}>{status.fuel_level.toFixed(0)}%</Text>
        </View>
      </TouchableOpacity>
      
      {/* Distance indicator */}
      <View style={[styles.indicatorContainer, { opacity: 0.7 }]}>
        <View style={[styles.iconContainer, { backgroundColor: '#2196F3' }]}>
          <FontAwesome5 name="route" size={16} color="white" />
        </View>
        <View style={styles.indicatorTextContainer}>
          <Text style={styles.indicatorLabel}>Distance</Text>
          <Text style={styles.indicatorValue}>{formatDistance(status.distance_covered)}</Text>
        </View>
      </View>
      
      {/* Traffic indicator button */}
      <TouchableOpacity 
        style={styles.trafficButton}
        onPress={onTrafficPress}
        disabled={!onTrafficPress}
      >
        <MaterialIcons name="traffic" size={20} color="white" />
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    height: 60,
    backgroundColor: 'rgba(33, 33, 33, 0.9)',
    borderRadius: 10,
    marginHorizontal: 16,
    marginBottom: 10,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-around',
    paddingHorizontal: 10,
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.3,
        shadowRadius: 4,
      },
      android: {
        elevation: 5,
      },
    }),
  },
  indicatorContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 8,
  },
  iconContainer: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 8,
  },
  indicatorTextContainer: {
    flexDirection: 'column',
  },
  indicatorLabel: {
    color: 'rgba(255, 255, 255, 0.7)',
    fontSize: 10,
    marginBottom: 2,
  },
  indicatorValue: {
    color: 'white',
    fontSize: 14,
    fontWeight: 'bold',
  },
  trafficButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#2196F3',
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 5,
  },
});

export default DrivingStatusBar;