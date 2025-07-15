import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
  Alert,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import MapView, { Marker, Polyline } from 'react-native-maps';
import { SafeArea } from '../SafeArea';
import { Card } from '../Card';
import { Button } from '../Button';
import { apiManager } from '../../services/api/apiManager';
import { theme } from '../../theme';

interface NavigationSegment {
  from_location: string;
  to_location: string;
  direction: string;
  distance_meters: number;
  walking_time_minutes: number;
  accessibility_time_minutes?: number;
  landmarks: string[];
  amenities_along_route: string[];
}

interface NavigationRoute {
  route_id: string;
  type: string;
  segments: NavigationSegment[];
  total_distance_meters: number;
  total_walking_time_minutes: number;
  accessibility_time_minutes?: number;
  amenities_summary: Record<string, number>;
  congestion_level: string;
  real_time_alerts: string[];
}

interface SecurityWaitTimes {
  main_checkpoint: {
    standard_lanes: number;
    tsa_precheck: number;
    clear?: number;
  };
  alternate_checkpoint?: {
    standard_lanes: number;
    tsa_precheck: number;
  };
  last_updated: string;
}

export const TerminalNavigator: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [currentLocation, setCurrentLocation] = useState('gate_44');
  const [destination, setDestination] = useState('');
  const [routeType, setRouteType] = useState<'fastest' | 'accessible' | 'scenic'>('fastest');
  const [route, setRoute] = useState<NavigationRoute | null>(null);
  const [securityWaitTimes, setSecurityWaitTimes] = useState<SecurityWaitTimes | null>(null);
  const [nearbyAmenities, setNearbyAmenities] = useState<any[]>([]);
  const [showingMap, setShowingMap] = useState(false);

  useEffect(() => {
    loadSecurityWaitTimes();
    loadNearbyAmenities();
  }, [currentLocation]);

  const loadSecurityWaitTimes = async () => {
    try {
      const response = await apiManager.get('/api/airport/terminal/security-wait-times', {
        params: { airport: 'LAX', terminal: '4' },
      });
      setSecurityWaitTimes(response.data);
    } catch (error) {
      console.error('Failed to load security wait times:', error);
    }
  };

  const loadNearbyAmenities = async () => {
    try {
      const response = await apiManager.get('/api/airport/terminal/nearby-amenities', {
        params: { location: currentLocation },
      });
      setNearbyAmenities(response.data);
    } catch (error) {
      console.error('Failed to load nearby amenities:', error);
    }
  };

  const calculateRoute = async () => {
    if (!destination) {
      Alert.alert('Select Destination', 'Please select where you want to go');
      return;
    }

    try {
      setLoading(true);
      const response = await apiManager.post('/api/airport/terminal/navigate', {
        airport: 'LAX',
        from_location: currentLocation,
        to_location: destination,
        route_type: routeType,
      });
      setRoute(response.data);
      setShowingMap(true);
    } catch (error) {
      console.error('Failed to calculate route:', error);
      Alert.alert('Navigation Error', 'Unable to calculate route');
    } finally {
      setLoading(false);
    }
  };

  const renderQuickDestinations = () => (
    <View>
      <Text style={styles.sectionTitle}>Quick Destinations</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
        {[
          { id: 'security_t4', name: 'Security', icon: 'shield-check' },
          { id: 'baggage_claim', name: 'Baggage', icon: 'bag-suitcase' },
          { id: 'restroom_nearest', name: 'Restroom', icon: 'human-male-female' },
          { id: 'food_court', name: 'Food Court', icon: 'food' },
          { id: 'lounge_pp_t4', name: 'Lounges', icon: 'sofa' },
          { id: 'gate_transfer', name: 'Other Gates', icon: 'airplane' },
        ].map((dest) => (
          <TouchableOpacity
            key={dest.id}
            style={[
              styles.quickDestCard,
              destination === dest.id && styles.quickDestCardSelected,
            ]}
            onPress={() => setDestination(dest.id)}
          >
            <MaterialCommunityIcons
              name={dest.icon}
              size={32}
              color={destination === dest.id ? theme.colors.primary : theme.colors.textSecondary}
            />
            <Text
              style={[
                styles.quickDestText,
                destination === dest.id && styles.quickDestTextSelected,
              ]}
            >
              {dest.name}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </View>
  );

  const renderRouteTypeSelector = () => (
    <View>
      <Text style={styles.sectionTitle}>Route Preference</Text>
      <View style={styles.routeTypeContainer}>
        {[
          { type: 'fastest', label: 'Fastest', icon: 'run-fast' },
          { type: 'accessible', label: 'Accessible', icon: 'wheelchair-accessibility' },
          { type: 'scenic', label: 'Scenic', icon: 'shopping' },
        ].map((option) => (
          <TouchableOpacity
            key={option.type}
            style={[
              styles.routeTypeButton,
              routeType === option.type && styles.routeTypeButtonActive,
            ]}
            onPress={() => setRouteType(option.type as any)}
          >
            <MaterialCommunityIcons
              name={option.icon}
              size={20}
              color={routeType === option.type ? '#fff' : theme.colors.textSecondary}
            />
            <Text
              style={[
                styles.routeTypeText,
                routeType === option.type && styles.routeTypeTextActive,
              ]}
            >
              {option.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );

  const renderSecurityWaitTimes = () => {
    if (!securityWaitTimes) return null;

    return (
      <Card style={styles.securityCard}>
        <View style={styles.securityHeader}>
          <MaterialCommunityIcons name="shield-check" size={24} color={theme.colors.primary} />
          <Text style={styles.securityTitle}>Security Wait Times</Text>
        </View>
        <View style={styles.securityContent}>
          <View style={styles.securityLane}>
            <Text style={styles.laneType}>Standard</Text>
            <Text style={styles.waitTime}>
              {securityWaitTimes.main_checkpoint.standard_lanes} min
            </Text>
          </View>
          <View style={styles.securityLane}>
            <Text style={styles.laneType}>TSA Pre✓</Text>
            <Text style={styles.waitTimeShort}>
              {securityWaitTimes.main_checkpoint.tsa_precheck} min
            </Text>
          </View>
          {securityWaitTimes.main_checkpoint.clear && (
            <View style={styles.securityLane}>
              <Text style={styles.laneType}>CLEAR</Text>
              <Text style={styles.waitTimeShort}>
                {securityWaitTimes.main_checkpoint.clear} min
              </Text>
            </View>
          )}
        </View>
      </Card>
    );
  };

  const renderNearbyAmenities = () => (
    <View>
      <Text style={styles.sectionTitle}>Nearby</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
        {nearbyAmenities.map((amenity, index) => (
          <Card key={index} style={styles.nearbyCard}>
            <MaterialCommunityIcons
              name={getAmenityIcon(amenity.name)}
              size={24}
              color={theme.colors.primary}
            />
            <Text style={styles.nearbyName}>{amenity.name}</Text>
            <Text style={styles.nearbyDistance}>
              {amenity.walking_time} min walk
            </Text>
          </Card>
        ))}
      </ScrollView>
    </View>
  );

  const getAmenityIcon = (name: string) => {
    const lowerName = name.toLowerCase();
    if (lowerName.includes('restroom')) return 'human-male-female';
    if (lowerName.includes('charging')) return 'battery-charging';
    if (lowerName.includes('atm')) return 'cash';
    if (lowerName.includes('starbucks') || lowerName.includes('coffee')) return 'coffee';
    return 'map-marker';
  };

  const renderRoute = () => {
    if (!route) return null;

    return (
      <View style={styles.routeContainer}>
        <View style={styles.routeHeader}>
          <TouchableOpacity onPress={() => setShowingMap(false)}>
            <MaterialCommunityIcons name="arrow-left" size={24} color={theme.colors.text} />
          </TouchableOpacity>
          <Text style={styles.routeTitle}>Your Route</Text>
          <TouchableOpacity onPress={() => setRoute(null)}>
            <MaterialCommunityIcons name="close" size={24} color={theme.colors.text} />
          </TouchableOpacity>
        </View>

        <Card style={styles.routeSummary}>
          <View style={styles.routeStats}>
            <View style={styles.routeStat}>
              <MaterialCommunityIcons name="walk" size={20} color={theme.colors.primary} />
              <Text style={styles.routeStatValue}>
                {route.total_walking_time_minutes} min
              </Text>
            </View>
            <View style={styles.routeStat}>
              <MaterialCommunityIcons name="map-marker-distance" size={20} color={theme.colors.primary} />
              <Text style={styles.routeStatValue}>
                {(route.total_distance_meters / 1000).toFixed(2)} km
              </Text>
            </View>
            <View style={styles.routeStat}>
              <MaterialCommunityIcons
                name={getCongestionIcon(route.congestion_level)}
                size={20}
                color={getCongestionColor(route.congestion_level)}
              />
              <Text style={styles.routeStatValue}>
                {route.congestion_level} traffic
              </Text>
            </View>
          </View>
        </Card>

        {route.real_time_alerts.length > 0 && (
          <Card style={styles.alertsCard}>
            {route.real_time_alerts.map((alert, index) => (
              <View key={index} style={styles.alert}>
                <MaterialCommunityIcons
                  name="alert-circle"
                  size={20}
                  color={theme.colors.warning}
                />
                <Text style={styles.alertText}>{alert}</Text>
              </View>
            ))}
          </Card>
        )}

        <ScrollView style={styles.directionsScroll}>
          {route.segments.map((segment, index) => (
            <Card key={index} style={styles.segmentCard}>
              <View style={styles.segmentHeader}>
                <View style={styles.stepNumber}>
                  <Text style={styles.stepNumberText}>{index + 1}</Text>
                </View>
                <View style={styles.segmentContent}>
                  <Text style={styles.segmentDirection}>{segment.direction}</Text>
                  <Text style={styles.segmentDetails}>
                    {segment.distance_meters}m • {segment.walking_time_minutes} min
                  </Text>
                  {segment.landmarks.length > 0 && (
                    <Text style={styles.segmentLandmarks}>
                      Pass by: {segment.landmarks.join(', ')}
                    </Text>
                  )}
                </View>
              </View>
            </Card>
          ))}
        </ScrollView>

        <Button
          title="Start Navigation"
          onPress={() => Alert.alert('Navigation Started', 'Follow the directions to reach your destination')}
          style={styles.startButton}
        />
      </View>
    );
  };

  const getCongestionIcon = (level: string) => {
    switch (level) {
      case 'low':
        return 'traffic-light';
      case 'medium':
        return 'traffic-light';
      case 'high':
        return 'traffic-light';
      default:
        return 'traffic-light';
    }
  };

  const getCongestionColor = (level: string) => {
    switch (level) {
      case 'low':
        return theme.colors.success;
      case 'medium':
        return theme.colors.warning;
      case 'high':
        return theme.colors.error;
      default:
        return theme.colors.textSecondary;
    }
  };

  if (showingMap && route) {
    return <SafeArea>{renderRoute()}</SafeArea>;
  }

  return (
    <SafeArea>
      <ScrollView style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.title}>Terminal Navigation</Text>
          <Text style={styles.subtitle}>LAX Terminal 4</Text>
        </View>

        {renderSecurityWaitTimes()}
        {renderQuickDestinations()}
        {renderRouteTypeSelector()}
        {renderNearbyAmenities()}

        <Button
          title="Get Directions"
          onPress={calculateRoute}
          loading={loading}
          disabled={!destination}
          style={styles.navigateButton}
        />
      </ScrollView>
    </SafeArea>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  header: {
    padding: 20,
    paddingBottom: 10,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 16,
    color: theme.colors.textSecondary,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: theme.colors.text,
    marginHorizontal: 20,
    marginTop: 20,
    marginBottom: 12,
  },
  quickDestCard: {
    width: 80,
    height: 80,
    backgroundColor: theme.colors.backgroundLight,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginHorizontal: 6,
    marginLeft: 20,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  quickDestCardSelected: {
    borderColor: theme.colors.primary,
    backgroundColor: theme.colors.primaryLight,
  },
  quickDestText: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    marginTop: 4,
  },
  quickDestTextSelected: {
    color: theme.colors.primary,
    fontWeight: '600',
  },
  routeTypeContainer: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    gap: 12,
  },
  routeTypeButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    backgroundColor: theme.colors.backgroundLight,
    borderRadius: 8,
    gap: 8,
  },
  routeTypeButtonActive: {
    backgroundColor: theme.colors.primary,
  },
  routeTypeText: {
    fontSize: 14,
    color: theme.colors.textSecondary,
  },
  routeTypeTextActive: {
    color: '#fff',
    fontWeight: '600',
  },
  securityCard: {
    margin: 20,
    padding: 16,
  },
  securityHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  securityTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: theme.colors.text,
    marginLeft: 8,
  },
  securityContent: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  securityLane: {
    alignItems: 'center',
  },
  laneType: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    marginBottom: 4,
  },
  waitTime: {
    fontSize: 20,
    fontWeight: 'bold',
    color: theme.colors.warning,
  },
  waitTimeShort: {
    fontSize: 20,
    fontWeight: 'bold',
    color: theme.colors.success,
  },
  nearbyCard: {
    width: 100,
    padding: 12,
    marginHorizontal: 6,
    marginLeft: 20,
    alignItems: 'center',
  },
  nearbyName: {
    fontSize: 14,
    fontWeight: '600',
    color: theme.colors.text,
    marginTop: 8,
    textAlign: 'center',
  },
  nearbyDistance: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    marginTop: 4,
  },
  navigateButton: {
    margin: 20,
  },
  routeContainer: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  routeHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
  },
  routeTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: theme.colors.text,
  },
  routeSummary: {
    margin: 16,
    padding: 16,
  },
  routeStats: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  routeStat: {
    alignItems: 'center',
  },
  routeStatValue: {
    fontSize: 14,
    fontWeight: '600',
    color: theme.colors.text,
    marginTop: 4,
  },
  alertsCard: {
    marginHorizontal: 16,
    marginBottom: 16,
    padding: 12,
    backgroundColor: theme.colors.warningLight,
  },
  alert: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  alertText: {
    flex: 1,
    fontSize: 14,
    color: theme.colors.text,
    marginLeft: 8,
  },
  directionsScroll: {
    flex: 1,
  },
  segmentCard: {
    marginHorizontal: 16,
    marginBottom: 8,
    padding: 16,
  },
  segmentHeader: {
    flexDirection: 'row',
  },
  stepNumber: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: theme.colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  stepNumberText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 16,
  },
  segmentContent: {
    flex: 1,
  },
  segmentDirection: {
    fontSize: 16,
    fontWeight: '600',
    color: theme.colors.text,
    marginBottom: 4,
  },
  segmentDetails: {
    fontSize: 14,
    color: theme.colors.textSecondary,
  },
  segmentLandmarks: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    marginTop: 4,
    fontStyle: 'italic',
  },
  startButton: {
    margin: 16,
  },
});