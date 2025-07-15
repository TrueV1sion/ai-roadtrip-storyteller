import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Platform
} from 'react-native';
import { FontAwesome5, MaterialIcons, MaterialCommunityIcons } from '@expo/vector-icons';
import { FuelStationType } from '../../types/driving';

interface FuelStationCardProps {
  station: FuelStationType;
  preferredFuelType?: string;
  onPress: () => void;
  onNavigate: () => void;
}

const FuelStationCard: React.FC<FuelStationCardProps> = ({
  station,
  preferredFuelType = 'regular',
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
  
  // Get color for busy level
  const getBusyLevelColor = () => {
    switch (station.busy_level) {
      case 'low':
        return '#4CAF50';
      case 'medium':
        return '#FFC107';
      case 'high':
        return '#F44336';
      default:
        return '#9E9E9E';
    }
  };
  
  // Get icon and color for fuel type
  const getFuelTypeIcon = (type: string) => {
    switch (type) {
      case 'regular':
        return { icon: 'gas-pump', color: '#2196F3' };
      case 'premium':
        return { icon: 'gas-pump', color: '#F44336' };
      case 'diesel':
        return { icon: 'truck', color: '#795548' };
      case 'electric':
        return { icon: 'bolt', color: '#4CAF50' };
      default:
        return { icon: 'gas-pump', color: '#9E9E9E' };
    }
  };
  
  // Get amenity icons
  const getAmenityIcons = () => {
    const amenities = station.amenities || {};
    
    const amenityIcons = [
      { key: 'restrooms', name: 'restroom', color: '#2196F3' },
      { key: 'food', name: 'restaurant', color: '#FF9800' },
      { key: 'convenience_store', name: 'storefront', color: '#9C27B0' },
      { key: 'car_wash', name: 'local-car-wash', color: '#03A9F4' },
      { key: 'ev_charging', name: 'electrical-services', color: '#4CAF50' }
    ];
    
    return (
      <View style={styles.amenitiesContainer}>
        {amenityIcons.map((amenity) => 
          amenities[amenity.key] ? (
            <View key={amenity.key} style={styles.amenityIconWrapper}>
              <MaterialIcons name={amenity.name} size={14} color={amenity.color} />
            </View>
          ) : null
        )}
      </View>
    );
  };
  
  // Render fuel prices
  const renderFuelPrices = () => {
    if (!station.prices) return null;
    
    return (
      <View style={styles.pricesContainer}>
        {Object.entries(station.prices).map(([type, price]) => {
          const fuelTypeInfo = getFuelTypeIcon(type);
          const isPreferred = type === preferredFuelType;
          
          return (
            <View 
              key={type} 
              style={[
                styles.priceItem,
                isPreferred && styles.preferredFuelType
              ]}
            >
              <FontAwesome5 
                name={fuelTypeInfo.icon} 
                size={12} 
                color={fuelTypeInfo.color} 
                style={styles.priceIcon} 
              />
              <Text 
                style={[
                  styles.priceText,
                  isPreferred && styles.preferredPriceText
                ]}
              >
                ${price.toFixed(2)}
              </Text>
              <Text style={styles.fuelTypeText}>{type}</Text>
            </View>
          );
        })}
      </View>
    );
  };
  
  return (
    <TouchableOpacity style={styles.container} onPress={onPress} activeOpacity={0.8}>
      <View style={styles.card}>
        <View style={styles.header}>
          <View style={styles.brandContainer}>
            {station.brand ? (
              <Text style={styles.brandText}>{station.brand}</Text>
            ) : (
              <Text style={styles.brandText}>Gas Station</Text>
            )}
            
            {station.rating ? (
              <View style={styles.ratingContainer}>
                <FontAwesome5 name="star" size={12} color="#FFC107" style={styles.ratingIcon} />
                <Text style={styles.ratingText}>{station.rating.toFixed(1)}</Text>
              </View>
            ) : null}
          </View>
          
          <View style={[styles.busyIndicator, { backgroundColor: getBusyLevelColor() }]}>
            <Text style={styles.busyText}>
              {station.busy_level || 'Unknown'}
            </Text>
          </View>
        </View>
        
        <View style={styles.content}>
          <Text style={styles.title}>{station.name}</Text>
          
          <View style={styles.metricsContainer}>
            <View style={styles.metricItem}>
              <FontAwesome5 name="map-marker-alt" size={12} color="#F44336" style={styles.metricIcon} />
              <Text style={styles.metricText}>{formatDistance(station.distance_from_current)}</Text>
            </View>
            
            <View style={styles.metricItem}>
              <FontAwesome5 name="road" size={12} color="#2196F3" style={styles.metricIcon} />
              <Text style={styles.metricText}>{formatDistance(station.distance_from_route)}</Text>
            </View>
          </View>
          
          {renderFuelPrices()}
          
          {getAmenityIcons()}
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
    padding: 15,
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
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  brandContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  brandText: {
    fontSize: 12,
    color: '#757575',
    textTransform: 'uppercase',
  },
  ratingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFF8E1',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 10,
    marginLeft: 8,
  },
  ratingIcon: {
    marginRight: 2,
  },
  ratingText: {
    fontSize: 12,
    color: '#FF9800',
    fontWeight: 'bold',
  },
  busyIndicator: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 10,
  },
  busyText: {
    fontSize: 10,
    color: 'white',
    fontWeight: 'bold',
    textTransform: 'uppercase',
  },
  content: {
    paddingBottom: 10,
  },
  title: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 8,
  },
  metricsContainer: {
    flexDirection: 'row',
    marginBottom: 10,
  },
  metricItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 12,
  },
  metricIcon: {
    marginRight: 4,
  },
  metricText: {
    fontSize: 12,
    color: '#555',
  },
  pricesContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 10,
  },
  priceItem: {
    flexDirection: 'column',
    alignItems: 'center',
    marginRight: 15,
    borderWidth: 1,
    borderColor: '#E0E0E0',
    borderRadius: 8,
    padding: 8,
    minWidth: 65,
  },
  preferredFuelType: {
    borderColor: '#4CAF50',
    backgroundColor: 'rgba(76, 175, 80, 0.05)',
  },
  priceIcon: {
    marginBottom: 3,
  },
  priceText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#333',
  },
  preferredPriceText: {
    color: '#4CAF50',
  },
  fuelTypeText: {
    fontSize: 10,
    color: '#757575',
    textTransform: 'capitalize',
  },
  amenitiesContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  amenityIconWrapper: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#f5f5f5',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 8,
    marginTop: 5,
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

export default FuelStationCard;