import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Image,
  Platform
} from 'react-native';
import { FontAwesome5, MaterialIcons } from '@expo/vector-icons';
import { RestStopType } from '../../types/driving';

interface RestBreakCardProps {
  restStop: RestStopType;
  onPress: () => void;
  onNavigate: () => void;
}

const RestBreakCard: React.FC<RestBreakCardProps> = ({
  restStop,
  onPress,
  onNavigate
}) => {
  // Format distance in km or m
  const formatDistance = (meters: number) => {
    if (meters >= 1000) {
      return `${(meters / 1000).toFixed(1)} km`;
    } else {
      return `${Math.round(meters)} m`;
    }
  };
  
  // Format time (in minutes) to string
  const formatTime = (minutes: number) => {
    return `${minutes} min`;
  };
  
  // Get icon based on category
  const getCategoryIcon = () => {
    switch (restStop.category) {
      case 'rest_area':
        return <FontAwesome5 name="umbrella-beach" size={16} color="#4CAF50" />;
      case 'restaurant':
        return <FontAwesome5 name="utensils" size={16} color="#FF9800" />;
      case 'service_station':
        return <FontAwesome5 name="gas-pump" size={16} color="#2196F3" />;
      default:
        return <FontAwesome5 name="map-marker-alt" size={16} color="#9C27B0" />;
    }
  };
  
  // Get facility icons
  const getFacilityIcons = () => {
    const iconMapping: { [key: string]: { name: string; color: string } } = {
      'restrooms': { name: 'restroom', color: '#2196F3' },
      'food': { name: 'restaurant', color: '#FF9800' },
      'fuel': { name: 'local-gas-station', color: '#F44336' },
      'wifi': { name: 'wifi', color: '#4CAF50' },
      'picnic_area': { name: 'deck', color: '#8BC34A' },
      'convenience_store': { name: 'storefront', color: '#9C27B0' },
      'vending_machines': { name: 'local-drink', color: '#00BCD4' }
    };
    
    return (
      <View style={styles.facilityIconsContainer}>
        {restStop.facilities.map((facility, index) => {
          const iconInfo = iconMapping[facility] || { name: 'help', color: '#757575' };
          return (
            <View key={index} style={styles.facilityIconWrapper}>
              <MaterialIcons name={iconInfo.name} size={16} color={iconInfo.color} />
            </View>
          );
        })}
      </View>
    );
  };
  
  // Get background image based on category
  const getBackgroundImage = () => {
    switch (restStop.category) {
      case 'rest_area':
        return require('../../../assets/images/rest_area.jpg');
      case 'restaurant':
        return require('../../../assets/images/restaurant.jpg');
      case 'service_station':
        return require('../../../assets/images/service_station.jpg');
      default:
        return require('../../../assets/images/rest_stop.jpg');
    }
  };
  
  return (
    <TouchableOpacity style={styles.container} onPress={onPress} activeOpacity={0.8}>
      <View style={styles.card}>
        <View style={styles.imageContainer}>
          <Image 
            source={getBackgroundImage()} 
            style={styles.backgroundImage}
            resizeMode="cover"
          />
          <View style={styles.categoryBadge}>
            {getCategoryIcon()}
            <Text style={styles.categoryText}>{restStop.category.replace('_', ' ')}</Text>
          </View>
        </View>
        
        <View style={styles.content}>
          <Text style={styles.title}>{restStop.name}</Text>
          
          <View style={styles.metricsContainer}>
            <View style={styles.metricItem}>
              <FontAwesome5 name="map-marker-alt" size={12} color="#F44336" style={styles.metricIcon} />
              <Text style={styles.metricText}>{formatDistance(restStop.distance_from_current)}</Text>
            </View>
            
            <View style={styles.metricItem}>
              <FontAwesome5 name="road" size={12} color="#2196F3" style={styles.metricIcon} />
              <Text style={styles.metricText}>{formatDistance(restStop.distance_from_route)}</Text>
            </View>
            
            <View style={styles.metricItem}>
              <FontAwesome5 name="clock" size={12} color="#4CAF50" style={styles.metricIcon} />
              <Text style={styles.metricText}>{formatTime(restStop.estimated_duration)}</Text>
            </View>
            
            {restStop.rating ? (
              <View style={styles.metricItem}>
                <FontAwesome5 name="star" size={12} color="#FFC107" style={styles.metricIcon} />
                <Text style={styles.metricText}>{restStop.rating.toFixed(1)}</Text>
              </View>
            ) : null}
          </View>
          
          {getFacilityIcons()}
        </View>
        
        <TouchableOpacity 
          style={styles.navigateButton}
          onPress={onNavigate}
        >
          <FontAwesome5 name="directions" size={16} color="white" />
        </TouchableOpacity>
      </View>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    marginHorizontal: 16,
    marginVertical: 8,
  },
  card: {
    backgroundColor: 'white',
    borderRadius: 12,
    overflow: 'hidden',
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
      },
      android: {
        elevation: 3,
      },
    }),
  },
  imageContainer: {
    height: 100,
    overflow: 'hidden',
  },
  backgroundImage: {
    width: '100%',
    height: '100%',
  },
  categoryBadge: {
    position: 'absolute',
    top: 10,
    left: 10,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 20,
    flexDirection: 'row',
    alignItems: 'center',
  },
  categoryText: {
    fontSize: 12,
    fontWeight: 'bold',
    marginLeft: 5,
    textTransform: 'capitalize',
  },
  content: {
    padding: 15,
  },
  title: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  metricsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 10,
  },
  metricItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 12,
    marginBottom: 5,
  },
  metricIcon: {
    marginRight: 4,
  },
  metricText: {
    fontSize: 12,
    color: '#555',
  },
  facilityIconsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  facilityIconWrapper: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#f5f5f5',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 8,
    marginBottom: 5,
  },
  navigateButton: {
    position: 'absolute',
    right: 15,
    bottom: 15,
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#2196F3',
    justifyContent: 'center',
    alignItems: 'center',
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.2,
        shadowRadius: 1.5,
      },
      android: {
        elevation: 2,
      },
    }),
  },
});

export default RestBreakCard;