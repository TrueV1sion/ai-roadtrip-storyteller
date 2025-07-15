import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  View,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Platform,
  KeyboardAvoidingView,
  ActivityIndicator,
  Surface,
  Animated,
  Easing,
  Dimensions,
} from 'react-native';
import {
  Text,
  TextInput,
  IconButton,
  Button,
  Chip,
  Portal,
  Modal,
  List,
  Divider,
  Switch,
} from 'react-native-paper';
import { MaterialIcons, MaterialCommunityIcons } from '@expo/vector-icons';
import { Location, Route } from '../../types/location';
import { useNavigation } from '@react-navigation/native';
import { useLocationSearch } from '../../hooks/useLocationSearch';
import { useCurrentLocation } from '../../hooks/useCurrentLocation';
import { TravelMode } from '../../types/navigation';
import { formatDistance, formatDuration } from '../../utils/formatters';
import { COLORS, SPACING } from '../../theme';
import MapView, { Marker, Polyline, PROVIDER_GOOGLE } from 'react-native-maps';
import ErrorHandler from '../../services/ErrorHandler';
import { LineChart } from 'react-native-chart-kit';
import { API_BASE_URL } from '../../config';

interface DirectionsFormProps {
  onSubmit: (params: DirectionsParams) => Promise<void>;
  initialOrigin?: Location;
  initialDestination?: Location;
}

export interface DirectionsParams {
  origin: Location;
  destination: Location;
  waypoints?: Location[];
  mode: TravelMode;
  optimizeRoute: boolean;
  includeTraffic: boolean;
  includePlaces: boolean;
  alternatives: boolean;
  routeType: 'fastest' | 'scenic' | 'eco' | 'balanced';
}

interface RouteAlternative {
  coordinates: Location[];
  distance: number;
  duration: number;
  trafficDelay?: number;
  tollCost?: number;
  fuelConsumption?: number;
  co2Emissions?: number;
  scenicScore?: number;
  elevationProfile?: {
    distances: number[];
    elevations: number[];
    slopes: number[];
    maxElevation: number;
    minElevation: number;
    totalAscent: number;
    totalDescent: number;
  };
  weather?: Array<{
    position: number;
    condition: string;
    temperature: number;
    precipitation: number;
    windSpeed: number;
    icon: string;
    hourlyForecast?: Array<{
      time: string;
      temperature: number;
      condition: string;
      precipitation: number;
      icon: string;
    }>;
    alerts?: Array<{
      type: string;
      severity: 'advisory' | 'watch' | 'warning';
      description: string;
      validUntil: string;
    }>;
  }>;
}

export const DirectionsForm: React.FC<DirectionsFormProps> = ({
  onSubmit,
  initialOrigin,
  initialDestination,
}) => {
  const navigation = useNavigation();
  const { currentLocation } = useCurrentLocation();
  const { searchLocations, results, loading } = useLocationSearch();
  
  // Form state
  const [origin, setOrigin] = useState<Location | null>(initialOrigin || null);
  const [destination, setDestination] = useState<Location | null>(
    initialDestination || null
  );
  const [waypoints, setWaypoints] = useState<Location[]>([]);
  const [mode, setMode] = useState<TravelMode>('driving');
  const [optimizeRoute, setOptimizeRoute] = useState(true);
  const [includeTraffic, setIncludeTraffic] = useState(true);
  const [includePlaces, setIncludePlaces] = useState(true);
  const [alternatives, setAlternatives] = useState(false);
  const [routeType, setRouteType] = useState<'fastest' | 'scenic' | 'eco' | 'balanced'>('balanced');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewRoute, setPreviewRoute] = useState<Route | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);
  const mapRef = useRef<MapView>(null);

  // UI state
  const [searchFocus, setSearchFocus] = useState<
    'origin' | 'destination' | 'waypoint' | null
  >(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [waypointIndex, setWaypointIndex] = useState<number>(-1);
  const [showAdvancedOptions, setShowAdvancedOptions] = useState(false);

  // Animation values
  const mapHeight = useRef(new Animated.Value(0)).current;
  const routeInfoOpacity = useRef(new Animated.Value(0)).current;
  const routeTypeScale = useRef(new Animated.Value(1)).current;

  // Additional route preview information
  const [routeDetails, setRouteDetails] = useState<{
    trafficDelay?: number;
    tollCost?: number;
    fuelConsumption?: number;
    co2Emissions?: number;
    complexity?: number;
    scenicScore?: number;
  } | null>(null);

  const [alternativeRoutes, setAlternativeRoutes] = useState<RouteAlternative[]>([]);
  const [showAlternatives, setShowAlternatives] = useState(false);
  const [showElevation, setShowElevation] = useState(false);
  const [showWeather, setShowWeather] = useState(false);
  const alternativesScrollRef = useRef<ScrollView>(null);

  // Handle location selection
  const handleLocationSelect = useCallback((location: Location) => {
    switch (searchFocus) {
      case 'origin':
        setOrigin(location);
        break;
      case 'destination':
        setDestination(location);
        break;
      case 'waypoint':
        if (waypointIndex >= 0) {
          const newWaypoints = [...waypoints];
          newWaypoints[waypointIndex] = location;
          setWaypoints(newWaypoints);
        } else {
          setWaypoints([...waypoints, location]);
        }
        break;
    }
    setSearchFocus(null);
    setSearchQuery('');
  }, [searchFocus, waypoints, waypointIndex]);

  // Handle search input
  const handleSearchInput = useCallback((text: string) => {
    setSearchQuery(text);
    searchLocations(text);
  }, [searchLocations]);

  // Use current location
  const handleUseCurrentLocation = useCallback(() => {
    if (currentLocation && searchFocus) {
      handleLocationSelect(currentLocation);
    }
  }, [currentLocation, searchFocus, handleLocationSelect]);

  // Fetch route preview when origin and destination change
  useEffect(() => {
    if (origin && destination) {
      fetchRoutePreview();
    } else {
      setPreviewRoute(null);
    }
  }, [origin, destination, waypoints, mode, routeType]);

  // Animate map container height
  useEffect(() => {
    Animated.timing(mapHeight, {
      toValue: origin || destination ? 300 : 0,
      duration: 300,
      easing: Easing.inOut(Easing.ease),
      useNativeDriver: false,
    }).start();
  }, [origin, destination]);

  // Animate route info opacity
  useEffect(() => {
    Animated.timing(routeInfoOpacity, {
      toValue: previewRoute ? 1 : 0,
      duration: 200,
      useNativeDriver: true,
    }).start();
  }, [previewRoute]);

  // Animate route type selection
  const handleRouteTypePress = useCallback((type: typeof routeType) => {
    Animated.sequence([
      Animated.timing(routeTypeScale, {
        toValue: 0.95,
        duration: 100,
        useNativeDriver: true,
      }),
      Animated.timing(routeTypeScale, {
        toValue: 1,
        duration: 100,
        useNativeDriver: true,
      }),
    ]).start();
    setRouteType(type);
  }, []);

  // Add function to fetch preview route
  const fetchRoutePreview = async () => {
    if (!origin || !destination) return;
    
    try {
      setIsPreviewLoading(true);
      
      // Call backend to get route without starting navigation
      const response = await fetch(`${API_BASE_URL}/api/directions/preview`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          origin: {
            latitude: origin.latitude,
            longitude: origin.longitude,
          },
          destination: {
            latitude: destination.latitude,
            longitude: destination.longitude,
          },
          waypoints: waypoints.map(wp => ({
            latitude: wp.latitude,
            longitude: wp.longitude,
          })),
          mode,
          optimizeRoute,
          includeTraffic,
          includePlaces,
          alternatives,
          routeType,
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to fetch route: ${response.status}`);
      }
      
      const routeData = await response.json();
      setPreviewRoute(routeData);
      setShowPreview(true);
    } catch (err) {
      console.error('Failed to fetch route preview:', err);
      // Don't show error to user, just silently fail preview
      setPreviewRoute(null);
      setShowPreview(false);
    } finally {
      setIsPreviewLoading(false);
    }
  };

  // Add effect to update preview when parameters change
  useEffect(() => {
    const debounceTimeout = setTimeout(() => {
      if (origin && destination) {
        fetchRoutePreview();
      }
    }, 1000); // Debounce by 1 second
    
    return () => clearTimeout(debounceTimeout);
  }, [origin, destination, waypoints, mode, routeType, optimizeRoute]);

  // Add helper function for slope color
  const getSlopeColor = (slope: number) => {
    if (slope > 15) return 'rgb(192, 57, 43)';  // Steep uphill
    if (slope > 8) return 'rgb(230, 126, 34)';  // Moderate uphill
    if (slope > 3) return 'rgb(241, 196, 15)';  // Gentle uphill
    if (slope > -3) return 'rgb(39, 174, 96)';  // Flat
    if (slope > -8) return 'rgb(52, 152, 219)'; // Gentle downhill
    if (slope > -15) return 'rgb(155, 89, 182)'; // Moderate downhill
    return 'rgb(142, 68, 173)';                  // Steep downhill
  };

  // Enhanced elevation profile render
  const renderElevationProfile = (route: RouteAlternative) => {
    if (!route.elevationProfile) return null;

    const { distances, elevations, slopes, maxElevation, minElevation, totalAscent, totalDescent } = route.elevationProfile;
    const elevationRange = maxElevation - minElevation;

    return (
      <View style={styles.elevationChart}>
        <View style={styles.elevationHeader}>
          <Text style={styles.chartTitle}>Elevation Profile</Text>
          <View style={styles.elevationStats}>
            <View style={styles.elevationStat}>
              <MaterialIcons name="trending-up" size={16} color={COLORS.success} />
              <Text style={styles.elevationStatValue}>
                +{Math.round(totalAscent)}m
              </Text>
            </View>
            <View style={styles.elevationStat}>
              <MaterialIcons name="trending-down" size={16} color={COLORS.error} />
              <Text style={styles.elevationStatValue}>
                -{Math.round(totalDescent)}m
              </Text>
            </View>
          </View>
        </View>

        <LineChart
          data={{
            labels: distances.map(d => `${(d/1000).toFixed(1)}km`),
            datasets: [{
              data: elevations,
              color: (opacity = 1) => {
                const gradientColors = slopes.map(slope => getSlopeColor(slope));
                return gradientColors[Math.floor(opacity * (gradientColors.length - 1))];
              },
            }],
          }}
          width={Dimensions.get('window').width - 80}
          height={120}
          chartConfig={{
            backgroundColor: COLORS.surface,
            backgroundGradientFrom: COLORS.surface,
            backgroundGradientTo: COLORS.surface,
            decimalPlaces: 0,
            color: (opacity = 1) => `rgba(81, 150, 246, ${opacity})`,
            labelColor: () => COLORS.textSecondary,
            strokeWidth: 2,
            propsForBackgroundLines: {
              strokeDasharray: '5, 5',
              strokeWidth: 1,
            },
            propsForLabels: {
              fontSize: 10,
            },
          }}
          bezier
          style={styles.chart}
          withShadow={false}
          withDots={false}
          withInnerLines={true}
          withVerticalLines={false}
          yAxisLabel="m "
          yAxisInterval={Math.ceil(elevationRange / 4)}
        />

        {/* Slope Legend */}
        <View style={styles.slopeLegend}>
          <Text style={styles.legendTitle}>Slope Grade</Text>
          <View style={styles.legendItems}>
            {[
              { label: '>15%', color: 'rgb(192, 57, 43)' },
              { label: '8-15%', color: 'rgb(230, 126, 34)' },
              { label: '3-8%', color: 'rgb(241, 196, 15)' },
              { label: '±3%', color: 'rgb(39, 174, 96)' },
              { label: '-3-8%', color: 'rgb(52, 152, 219)' },
              { label: '<-8%', color: 'rgb(142, 68, 173)' },
            ].map(item => (
              <View key={item.label} style={styles.legendItem}>
                <View style={[styles.legendColor, { backgroundColor: item.color }]} />
                <Text style={styles.legendText}>{item.label}</Text>
              </View>
            ))}
          </View>
        </View>
      </View>
    );
  };

  // Enhanced weather render
  const renderWeatherDetails = (weather: RouteAlternative['weather'][0]) => (
    <View style={styles.weatherDetails}>
      <View style={styles.currentWeather}>
        {renderWeatherCondition(weather)}
      </View>

      {weather.hourlyForecast && (
        <View style={styles.hourlyForecast}>
          <Text style={styles.forecastTitle}>Hourly Forecast</Text>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            style={styles.hourlyScroll}
          >
            {weather.hourlyForecast.map((hour, index) => (
              <View key={index} style={styles.hourlyItem}>
                <Text style={styles.hourlyTime}>
                  {new Date(hour.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </Text>
                <MaterialCommunityIcons name={hour.icon} size={24} color={COLORS.text} />
                <Text style={styles.hourlyTemp}>{Math.round(hour.temperature)}°</Text>
                {hour.precipitation > 0 && (
                  <View style={styles.precipChance}>
                    <MaterialCommunityIcons name="water" size={12} color={COLORS.info} />
                    <Text style={styles.precipText}>{Math.round(hour.precipitation)}%</Text>
                  </View>
                )}
              </View>
            ))}
          </ScrollView>
        </View>
      )}

      {weather.alerts && weather.alerts.length > 0 && (
        <View style={styles.weatherAlerts}>
          <Text style={styles.alertsTitle}>Weather Alerts</Text>
          {weather.alerts.map((alert, index) => (
            <Surface key={index} style={[
              styles.alertCard,
              { backgroundColor: alert.severity === 'warning' ? COLORS.error + '20' :
                               alert.severity === 'watch' ? COLORS.warning + '20' :
                               COLORS.info + '20' }
            ]}>
              <View style={styles.alertHeader}>
                <MaterialCommunityIcons
                  name={alert.severity === 'warning' ? 'alert' :
                       alert.severity === 'watch' ? 'alert-circle' : 'information'}
                  size={20}
                  color={alert.severity === 'warning' ? COLORS.error :
                        alert.severity === 'watch' ? COLORS.warning : COLORS.info}
                />
                <Text style={[styles.alertType, {
                  color: alert.severity === 'warning' ? COLORS.error :
                         alert.severity === 'watch' ? COLORS.warning : COLORS.info
                }]}>
                  {alert.type}
                </Text>
              </View>
              <Text style={styles.alertDescription}>{alert.description}</Text>
              <Text style={styles.alertValidity}>
                Valid until: {new Date(alert.validUntil).toLocaleTimeString()}
              </Text>
            </Surface>
          ))}
        </View>
      )}
    </View>
  );

  // Render weather condition
  const renderWeatherCondition = (weather: RouteAlternative['weather'][0]) => (
    <View style={styles.weatherItem}>
      <MaterialCommunityIcons name={weather.icon} size={24} color={COLORS.text} />
      <Text style={styles.weatherTemp}>{Math.round(weather.temperature)}°C</Text>
      <Text style={styles.weatherDesc}>{weather.condition}</Text>
      {weather.precipitation > 0 && (
        <Text style={styles.weatherPrecip}>{weather.precipitation}mm</Text>
      )}
      <Text style={styles.weatherWind}>{Math.round(weather.windSpeed)} km/h</Text>
    </View>
  );

  // Update route card render to use enhanced components
  const renderRouteCard = (route: RouteAlternative, index: number) => (
    <Surface style={[styles.routeCard, index === 0 && styles.selectedRoute]}>
      <View style={styles.routeCardHeader}>
        <Text style={styles.routeCardTitle}>
          Route {index + 1} {index === 0 && '(Selected)'}
        </Text>
        {route.scenicScore && (
          <Chip icon="tree" style={styles.scenicChip}>
            {Math.round(route.scenicScore)}%
          </Chip>
        )}
      </View>

      <View style={styles.routeMetrics}>
        <View style={styles.routeMetricItem}>
          <MaterialIcons name="straighten" size={20} color={COLORS.text} />
          <Text style={styles.routeMetricValue}>
            {formatDistance(route.distance)}
          </Text>
        </View>
        <View style={styles.routeMetricItem}>
          <MaterialIcons name="access-time" size={20} color={COLORS.text} />
          <Text style={styles.routeMetricValue}>
            {formatDuration(route.duration)}
          </Text>
        </View>
        {route.trafficDelay && (
          <View style={styles.routeMetricItem}>
            <MaterialIcons name="traffic" size={20} color={COLORS.warning} />
            <Text style={[styles.routeMetricValue, { color: COLORS.warning }]}>
              +{formatDuration(route.trafficDelay)}
            </Text>
          </View>
        )}
      </View>

      {route.elevationProfile && showElevation && renderElevationProfile(route)}

      {route.weather && showWeather && (
        <View style={styles.weatherContainer}>
          <Text style={styles.chartTitle}>Weather Along Route</Text>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            style={styles.weatherScroll}
          >
            {route.weather.map((weather, i) => (
              <View key={i} style={styles.weatherStop}>
                <Text style={styles.weatherPosition}>
                  {Math.round(weather.position * 100)}%
                </Text>
                {renderWeatherDetails(weather)}
              </View>
            ))}
          </ScrollView>
        </View>
      )}

      <Button
        mode={index === 0 ? "contained" : "outlined"}
        onPress={() => {
          setPreviewRoute({
            coordinates: route.coordinates,
            distance: route.distance,
            duration: route.duration,
          });
          setRouteDetails({
            trafficDelay: route.trafficDelay,
            tollCost: route.tollCost,
            fuelConsumption: route.fuelConsumption,
            co2Emissions: route.co2Emissions,
            scenicScore: route.scenicScore,
          });
          mapRef.current?.fitToCoordinates(route.coordinates, {
            edgePadding: { top: 50, right: 50, bottom: 50, left: 50 },
            animated: true,
          });
        }}
        style={styles.routeSelectButton}
      >
        {index === 0 ? 'Current Route' : 'Select Route'}
      </Button>
    </Surface>
  );

  // Submit form
  const handleSubmit = useCallback(async () => {
    if (!origin || !destination) return;

    try {
      await onSubmit({
        origin,
        destination,
        waypoints: waypoints.length > 0 ? waypoints : undefined,
        mode,
        optimizeRoute,
        includeTraffic,
        includePlaces,
        alternatives,
        routeType,
      });
    } catch (error) {
      // Handle error
      console.error('Failed to get directions:', error);
    }
  }, [
    origin,
    destination,
    waypoints,
    mode,
    optimizeRoute,
    includeTraffic,
    includePlaces,
    alternatives,
    routeType,
    onSubmit,
  ]);

  // Add the map preview component 
  const renderRoutePreview = () => {
    if (!previewRoute || !origin || !destination) return null;
    
    // Calculate the region to display all points
    const points = [
      origin,
      ...waypoints,
      destination,
      ...(previewRoute.coordinates || []),
    ];
    
    const latitudes = points.map(p => p.latitude);
    const longitudes = points.map(p => p.longitude);
    
    const minLat = Math.min(...latitudes);
    const maxLat = Math.max(...latitudes);
    const minLng = Math.min(...longitudes);
    const maxLng = Math.max(...longitudes);
    
    const region = {
      latitude: (minLat + maxLat) / 2,
      longitude: (minLng + maxLng) / 2,
      latitudeDelta: (maxLat - minLat) * 1.5,
      longitudeDelta: (maxLng - minLng) * 1.5,
    };
    
    return (
      <View style={styles.mapPreviewContainer}>
        <Text style={styles.previewTitle}>Route Preview</Text>
        <MapView
          style={styles.mapPreview}
          region={region}
          provider={PROVIDER_GOOGLE}
          zoomEnabled
          scrollEnabled
          pitchEnabled={false}
          rotateEnabled={false}
        >
          {/* Origin Marker */}
          <Marker
            coordinate={origin}
            title="Origin"
            pinColor="green"
          />
          
          {/* Destination Marker */}
          <Marker
            coordinate={destination}
            title="Destination"
            pinColor="red"
          />
          
          {/* Waypoint Markers */}
          {waypoints.map((waypoint, index) => (
            <Marker
              key={`waypoint-${index}`}
              coordinate={waypoint}
              title={`Waypoint ${index + 1}`}
              pinColor="blue"
            />
          ))}
          
          {/* Route Polyline */}
          {previewRoute.coordinates && (
            <Polyline
              coordinates={previewRoute.coordinates}
              strokeWidth={5}
              strokeColor={COLORS.primary}
            />
          )}
        </MapView>
        
        {/* Route Summary */}
        {previewRoute.distance !== undefined && previewRoute.duration !== undefined && (
          <View style={styles.routeSummary}>
            <Text style={styles.summaryText}>
              Distance: {formatDistance(previewRoute.distance)}
            </Text>
            <Text style={styles.summaryText}>
              Time: {formatDuration(previewRoute.duration)}
            </Text>
          </View>
        )}
      </View>
    );
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <ScrollView style={styles.scrollView}>
        {/* Origin Input */}
        <View style={styles.inputContainer}>
          <MaterialIcons
            name="trip-origin"
            size={24}
            color={COLORS.primary}
            style={styles.inputIcon}
          />
          <TextInput
            mode="outlined"
            label="Starting point"
            value={
              searchFocus === 'origin'
                ? searchQuery
                : origin?.name || 'Choose starting point'
            }
            onFocus={() => setSearchFocus('origin')}
            onChangeText={handleSearchInput}
            right={
              <TextInput.Icon
                icon="crosshairs-gps"
                onPress={handleUseCurrentLocation}
              />
            }
            style={styles.input}
          />
        </View>

        {/* Waypoints */}
        {waypoints.map((waypoint, index) => (
          <View key={index} style={styles.inputContainer}>
            <MaterialIcons
              name="location-on"
              size={24}
              color={COLORS.secondary}
              style={styles.inputIcon}
            />
            <TextInput
              mode="outlined"
              label={`Stop ${index + 1}`}
              value={waypoint.name || `Stop ${index + 1}`}
              onFocus={() => {
                setSearchFocus('waypoint');
                setWaypointIndex(index);
              }}
              right={
                <TextInput.Icon
                  icon="close"
                  onPress={() => {
                    const newWaypoints = [...waypoints];
                    newWaypoints.splice(index, 1);
                    setWaypoints(newWaypoints);
                  }}
                />
              }
              style={styles.input}
            />
          </View>
        ))}

        {/* Add Waypoint Button */}
        <TouchableOpacity
          style={styles.addWaypointButton}
          onPress={() => {
            setSearchFocus('waypoint');
            setWaypointIndex(-1);
          }}
        >
          <MaterialIcons name="add" size={24} color={COLORS.primary} />
          <Text style={styles.addWaypointText}>Add stop</Text>
        </TouchableOpacity>

        {/* Destination Input */}
        <View style={styles.inputContainer}>
          <MaterialIcons
            name="place"
            size={24}
            color={COLORS.error}
            style={styles.inputIcon}
          />
          <TextInput
            mode="outlined"
            label="Destination"
            value={
              searchFocus === 'destination'
                ? searchQuery
                : destination?.name || 'Choose destination'
            }
            onFocus={() => setSearchFocus('destination')}
            onChangeText={handleSearchInput}
            style={styles.input}
          />
        </View>

        {/* Route Type Selection */}
        <View style={styles.routeTypeContainer}>
          <Text style={styles.sectionTitle}>Route Type</Text>
          <View style={styles.routeTypeGrid}>
            {([
              {
                type: 'fastest',
                icon: 'flash',
                description: 'Quickest route to your destination',
                color: COLORS.success,
              },
              {
                type: 'scenic',
                icon: 'tree',
                description: 'Beautiful views and points of interest',
                color: COLORS.nature,
              },
              {
                type: 'eco',
                icon: 'leaf',
                description: 'Optimized for lower emissions',
                color: COLORS.eco,
              },
              {
                type: 'balanced',
                icon: 'balance-scale',
                description: 'Mix of speed and experience',
                color: COLORS.balanced,
              },
            ] as const).map(({ type, icon, description, color }) => (
              <Animated.View
                key={type}
                style={[
                  styles.routeTypeCard,
                  {
                    transform: [
                      {
                        scale: routeType === type ? routeTypeScale : 1,
                      },
                    ],
                    backgroundColor: routeType === type ? color : COLORS.surface,
                  },
                ]}
              >
                <TouchableOpacity
                  onPress={() => handleRouteTypePress(type)}
                  style={styles.routeTypeButton}
                >
                  <MaterialIcons
                    name={icon}
                    size={24}
                    color={routeType === type ? COLORS.white : color}
                  />
                  <Text
                    style={[
                      styles.routeTypeTitle,
                      routeType === type && styles.routeTypeSelected,
                    ]}
                  >
                    {type.charAt(0).toUpperCase() + type.slice(1)}
                  </Text>
                  <Text
                    style={[
                      styles.routeTypeDescription,
                      routeType === type && styles.routeTypeSelected,
                    ]}
                  >
                    {description}
                  </Text>
                </TouchableOpacity>
              </Animated.View>
            ))}
          </View>
        </View>

        {/* Map Preview */}
        <Animated.View style={[styles.mapContainer, { height: mapHeight }]}>
          <MapView
            ref={mapRef}
            style={styles.map}
            provider={PROVIDER_GOOGLE}
            initialRegion={{
              latitude: origin?.latitude || destination?.latitude || 0,
              longitude: origin?.longitude || destination?.longitude || 0,
              latitudeDelta: 0.02,
              longitudeDelta: 0.02,
            }}
          >
            {origin && (
              <Marker
                coordinate={origin}
                title="Start"
                pinColor={COLORS.primary}
              />
            )}
            {destination && (
              <Marker
                coordinate={destination}
                title="End"
                pinColor={COLORS.error}
              />
            )}
            {waypoints.map((waypoint, index) => (
              <Marker
                key={index}
                coordinate={waypoint}
                title={`Stop ${index + 1}`}
                pinColor={COLORS.secondary}
              />
            ))}
            {previewRoute && (
              <Polyline
                coordinates={previewRoute.coordinates}
                strokeWidth={3}
                strokeColor={COLORS.primary}
              />
            )}
          </MapView>
          {isPreviewLoading && (
            <View style={styles.mapOverlay}>
              <ActivityIndicator size="large" color={COLORS.primary} />
            </View>
          )}
          {previewRoute && (
            <Animated.View
              style={[styles.routeInfo, { opacity: routeInfoOpacity }]}
            >
              <Surface style={styles.routeInfoCard}>
                <View style={styles.routeInfoSection}>
                  <View style={styles.routeInfoItem}>
                    <MaterialIcons name="straighten" size={20} color={COLORS.text} />
                    <Text style={styles.routeInfoText}>
                      {formatDistance(previewRoute.distance)}
                    </Text>
                  </View>
                  <View style={styles.routeInfoItem}>
                    <MaterialIcons name="access-time" size={20} color={COLORS.text} />
                    <Text style={styles.routeInfoText}>
                      {formatDuration(previewRoute.duration)}
                    </Text>
                  </View>
                  {routeDetails?.trafficDelay && (
                    <View style={styles.routeInfoItem}>
                      <MaterialIcons name="traffic" size={20} color={COLORS.warning} />
                      <Text style={[styles.routeInfoText, { color: COLORS.warning }]}>
                        +{formatDuration(routeDetails.trafficDelay)}
                      </Text>
                    </View>
                  )}
                </View>
                
                {routeDetails && (
                  <View style={styles.routeDetailsGrid}>
                    {routeDetails.tollCost && (
                      <View style={styles.routeDetailItem}>
                        <MaterialIcons name="attach-money" size={16} color={COLORS.text} />
                        <Text style={styles.routeDetailValue}>
                          ${routeDetails.tollCost.toFixed(2)}
                        </Text>
                        <Text style={styles.routeDetailLabel}>Tolls</Text>
                      </View>
                    )}
                    {routeDetails.fuelConsumption && (
                      <View style={styles.routeDetailItem}>
                        <MaterialIcons name="local-gas-station" size={16} color={COLORS.text} />
                        <Text style={styles.routeDetailValue}>
                          {routeDetails.fuelConsumption.toFixed(1)}L
                        </Text>
                        <Text style={styles.routeDetailLabel}>Fuel</Text>
                      </View>
                    )}
                    {routeDetails.co2Emissions && (
                      <View style={styles.routeDetailItem}>
                        <MaterialIcons name="eco" size={16} color={COLORS.eco} />
                        <Text style={styles.routeDetailValue}>
                          {routeDetails.co2Emissions.toFixed(1)}kg
                        </Text>
                        <Text style={styles.routeDetailLabel}>CO₂</Text>
                      </View>
                    )}
                    {routeDetails.scenicScore && (
                      <View style={styles.routeDetailItem}>
                        <MaterialIcons name="photo" size={16} color={COLORS.nature} />
                        <Text style={styles.routeDetailValue}>
                          {Math.round(routeDetails.scenicScore)}%
                        </Text>
                        <Text style={styles.routeDetailLabel}>Scenic</Text>
                      </View>
                    )}
                  </View>
                )}
              </Surface>
            </Animated.View>
          )}
        </Animated.View>

        {/* Travel Mode Selection */}
        <View style={styles.travelModeContainer}>
          {(['driving', 'walking', 'bicycling', 'transit'] as TravelMode[]).map(
            (travelMode) => (
              <Chip
                key={travelMode}
                selected={mode === travelMode}
                onPress={() => setMode(travelMode)}
                style={styles.modeChip}
                icon={`${travelMode}-outline`}
              >
                {travelMode.charAt(0).toUpperCase() + travelMode.slice(1)}
              </Chip>
            )
          )}
        </View>

        {/* Advanced Options */}
        <TouchableOpacity
          style={styles.advancedButton}
          onPress={() => setShowAdvancedOptions(true)}
        >
          <MaterialIcons name="tune" size={24} color={COLORS.primary} />
          <Text style={styles.advancedButtonText}>Route options</Text>
        </TouchableOpacity>

        {/* Route preview */}
        {renderRoutePreview()}

        {/* Submit Button */}
        <Button
          mode="contained"
          onPress={handleSubmit}
          disabled={!origin || !destination}
          style={styles.submitButton}
        >
          Start Navigation
        </Button>
      </ScrollView>

      {/* Location Search Results */}
      {searchFocus && (
        <Portal>
          <Modal
            visible={true}
            onDismiss={() => setSearchFocus(null)}
            contentContainerStyle={styles.searchResults}
          >
            <ScrollView>
              {loading ? (
                <Text>Searching...</Text>
              ) : (
                results.map((result) => (
                  <React.Fragment key={result.id}>
                    <List.Item
                      title={result.name}
                      description={result.address}
                      left={(props) => (
                        <List.Icon {...props} icon="map-marker" />
                      )}
                      onPress={() => handleLocationSelect(result)}
                    />
                    <Divider />
                  </React.Fragment>
                ))
              )}
            </ScrollView>
          </Modal>
        </Portal>
      )}

      {/* Advanced Options Modal */}
      <Portal>
        <Modal
          visible={showAdvancedOptions}
          onDismiss={() => setShowAdvancedOptions(false)}
          contentContainerStyle={styles.advancedOptions}
        >
          <Text style={styles.modalTitle}>Route Options</Text>
          
          <List.Item
            title="Optimize route"
            description="Find the most efficient order of stops"
            right={() => (
              <Switch
                value={optimizeRoute}
                onValueChange={setOptimizeRoute}
              />
            )}
          />
          <Divider />
          
          <List.Item
            title="Real-time traffic"
            description="Use current traffic conditions"
            right={() => (
              <Switch
                value={includeTraffic}
                onValueChange={setIncludeTraffic}
              />
            )}
          />
          <Divider />
          
          <List.Item
            title="Show places"
            description="Include details about stops along the route"
            right={() => (
              <Switch
                value={includePlaces}
                onValueChange={setIncludePlaces}
              />
            )}
          />
          <Divider />
          
          <List.Item
            title="Alternative routes"
            description="Show multiple route options"
            right={() => (
              <Switch
                value={alternatives}
                onValueChange={setAlternatives}
              />
            )}
          />
          
          <Button
            mode="contained"
            onPress={() => setShowAdvancedOptions(false)}
            style={styles.modalButton}
          >
            Done
          </Button>
        </Modal>
      </Portal>

      {previewRoute && alternativeRoutes.length > 0 && (
        <View style={styles.routeComparisonContainer}>
          <View style={styles.comparisonHeader}>
            <Text style={styles.sectionTitle}>Route Alternatives</Text>
            <View style={styles.comparisonToggles}>
              <Chip
                selected={showElevation}
                onPress={() => setShowElevation(!showElevation)}
                style={styles.toggleChip}
                icon="terrain"
              >
                Elevation
              </Chip>
              <Chip
                selected={showWeather}
                onPress={() => setShowWeather(!showWeather)}
                style={styles.toggleChip}
                icon="weather-partly-cloudy"
              >
                Weather
              </Chip>
            </View>
          </View>

          <ScrollView
            ref={alternativesScrollRef}
            horizontal
            showsHorizontalScrollIndicator={false}
            snapToInterval={Dimensions.get('window').width - 40}
            decelerationRate="fast"
            style={styles.routeCardsScroll}
          >
            {[previewRoute, ...alternativeRoutes].map((route, index) =>
              renderRouteCard(route, index)
            )}
          </ScrollView>

          <View style={styles.scrollIndicator}>
            {[previewRoute, ...alternativeRoutes].map((_, index) => (
              <View
                key={index}
                style={[
                  styles.scrollDot,
                  index === 0 && styles.scrollDotActive,
                ]}
              />
            ))}
          </View>
        </View>
      )}
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  scrollView: {
    flex: 1,
    padding: SPACING.medium,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: SPACING.small,
  },
  inputIcon: {
    marginRight: SPACING.small,
  },
  input: {
    flex: 1,
  },
  addWaypointButton: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: SPACING.small,
    marginBottom: SPACING.medium,
  },
  addWaypointText: {
    marginLeft: SPACING.small,
    color: COLORS.primary,
  },
  travelModeContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginVertical: SPACING.medium,
  },
  modeChip: {
    margin: SPACING.xsmall,
  },
  advancedButton: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: SPACING.small,
    marginBottom: SPACING.medium,
  },
  advancedButtonText: {
    marginLeft: SPACING.small,
    color: COLORS.primary,
  },
  submitButton: {
    marginVertical: SPACING.medium,
  },
  searchResults: {
    backgroundColor: '#fff',
    padding: SPACING.medium,
    margin: SPACING.medium,
    maxHeight: '80%',
    borderRadius: 8,
  },
  advancedOptions: {
    backgroundColor: '#fff',
    padding: SPACING.medium,
    margin: SPACING.medium,
    borderRadius: 8,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: SPACING.medium,
  },
  modalButton: {
    marginTop: SPACING.medium,
  },
  routeTypeContainer: {
    marginVertical: SPACING.medium,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: SPACING.small,
  },
  routeTypeGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    margin: -SPACING.xsmall,
  },
  routeTypeCard: {
    width: '50%',
    padding: SPACING.xsmall,
  },
  routeTypeButton: {
    padding: SPACING.medium,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: COLORS.surface,
    elevation: 2,
  },
  routeTypeTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginTop: SPACING.small,
    color: COLORS.text,
  },
  routeTypeDescription: {
    fontSize: 12,
    textAlign: 'center',
    marginTop: SPACING.xsmall,
    color: COLORS.textSecondary,
  },
  routeTypeSelected: {
    color: COLORS.white,
  },
  routeInfoCard: {
    padding: SPACING.medium,
    borderRadius: 12,
    elevation: 4,
  },
  routeInfoSection: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: SPACING.small,
  },
  routeInfoItem: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  routeInfoText: {
    marginLeft: SPACING.xsmall,
    fontSize: 14,
    fontWeight: 'bold',
  },
  routeDetailsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: SPACING.small,
    borderTopWidth: 1,
    borderTopColor: COLORS.border,
    paddingTop: SPACING.small,
  },
  routeDetailItem: {
    width: '25%',
    alignItems: 'center',
  },
  routeDetailValue: {
    fontSize: 14,
    fontWeight: 'bold',
    marginTop: SPACING.xsmall,
  },
  routeDetailLabel: {
    fontSize: 12,
    color: COLORS.textSecondary,
    marginTop: SPACING.xxsmall,
  },
  mapContainer: {
    height: 300,
    marginVertical: SPACING.medium,
    borderRadius: 8,
    overflow: 'hidden',
  },
  map: {
    flex: 1,
  },
  mapOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(255, 255, 255, 0.7)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  routeComparisonContainer: {
    marginTop: SPACING.medium,
  },
  comparisonHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SPACING.small,
  },
  comparisonToggles: {
    flexDirection: 'row',
  },
  toggleChip: {
    marginLeft: SPACING.xsmall,
  },
  routeCardsScroll: {
    marginHorizontal: -SPACING.medium,
    paddingHorizontal: SPACING.medium,
  },
  routeCard: {
    width: Dimensions.get('window').width - 40,
    marginRight: SPACING.medium,
    padding: SPACING.medium,
    borderRadius: 12,
    elevation: 4,
  },
  selectedRoute: {
    borderColor: COLORS.primary,
    borderWidth: 2,
  },
  routeCardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SPACING.small,
  },
  routeCardTitle: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  scenicChip: {
    backgroundColor: COLORS.nature,
  },
  routeMetrics: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: SPACING.medium,
  },
  routeMetricItem: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  routeMetricValue: {
    marginLeft: SPACING.xsmall,
    fontSize: 14,
    fontWeight: 'bold',
  },
  elevationChart: {
    marginVertical: SPACING.medium,
  },
  elevationHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SPACING.small,
  },
  elevationStats: {
    flexDirection: 'row',
    gap: SPACING.medium,
  },
  elevationStat: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.xsmall,
  },
  elevationStatValue: {
    fontSize: 12,
    fontWeight: 'bold',
  },
  slopeLegend: {
    marginTop: SPACING.small,
    padding: SPACING.small,
    backgroundColor: COLORS.surface + '40',
    borderRadius: 8,
  },
  legendTitle: {
    fontSize: 12,
    fontWeight: 'bold',
    marginBottom: SPACING.xsmall,
  },
  legendItems: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: SPACING.small,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.xxsmall,
  },
  legendColor: {
    width: 12,
    height: 12,
    borderRadius: 2,
  },
  legendText: {
    fontSize: 10,
    color: COLORS.textSecondary,
  },
  weatherContainer: {
    marginVertical: SPACING.medium,
  },
  weatherScroll: {
    marginHorizontal: -SPACING.small,
  },
  weatherStop: {
    alignItems: 'center',
    padding: SPACING.small,
  },
  weatherPosition: {
    fontSize: 12,
    color: COLORS.textSecondary,
    marginBottom: SPACING.xsmall,
  },
  weatherItem: {
    alignItems: 'center',
  },
  weatherTemp: {
    fontSize: 16,
    fontWeight: 'bold',
    marginTop: SPACING.xsmall,
  },
  weatherDesc: {
    fontSize: 12,
    color: COLORS.textSecondary,
    marginTop: SPACING.xxsmall,
  },
  weatherPrecip: {
    fontSize: 12,
    color: COLORS.info,
    marginTop: SPACING.xxsmall,
  },
  weatherWind: {
    fontSize: 12,
    color: COLORS.textSecondary,
    marginTop: SPACING.xxsmall,
  },
  routeSelectButton: {
    marginTop: SPACING.medium,
  },
  scrollIndicator: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: SPACING.small,
  },
  scrollDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: COLORS.border,
    marginHorizontal: 4,
  },
  scrollDotActive: {
    backgroundColor: COLORS.primary,
    width: 16,
  },
  weatherDetails: {
    marginTop: SPACING.medium,
  },
  currentWeather: {
    marginBottom: SPACING.medium,
  },
  hourlyForecast: {
    marginTop: SPACING.medium,
  },
  forecastTitle: {
    fontSize: 12,
    fontWeight: 'bold',
    marginBottom: SPACING.small,
  },
  hourlyScroll: {
    marginHorizontal: -SPACING.small,
  },
  hourlyItem: {
    alignItems: 'center',
    padding: SPACING.small,
    minWidth: 60,
  },
  hourlyTime: {
    fontSize: 10,
    color: COLORS.textSecondary,
    marginBottom: SPACING.xsmall,
  },
  hourlyTemp: {
    fontSize: 14,
    fontWeight: 'bold',
    marginTop: SPACING.xsmall,
  },
  precipChance: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
    marginTop: SPACING.xxsmall,
  },
  precipText: {
    fontSize: 10,
    color: COLORS.info,
  },
  weatherAlerts: {
    marginTop: SPACING.medium,
  },
  alertsTitle: {
    fontSize: 12,
    fontWeight: 'bold',
    marginBottom: SPACING.small,
  },
  alertCard: {
    padding: SPACING.small,
    borderRadius: 8,
    marginBottom: SPACING.small,
  },
  alertHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.xsmall,
    marginBottom: SPACING.xsmall,
  },
  alertType: {
    fontSize: 12,
    fontWeight: 'bold',
  },
  alertDescription: {
    fontSize: 12,
    color: COLORS.text,
    marginBottom: SPACING.xsmall,
  },
  alertValidity: {
    fontSize: 10,
    color: COLORS.textSecondary,
  },
  mapPreviewContainer: {
    marginVertical: SPACING.medium,
    borderRadius: 12,
    overflow: 'hidden',
    backgroundColor: '#f5f5f5',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  previewTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    padding: SPACING.small,
    backgroundColor: COLORS.primary + '15',
  },
  mapPreview: {
    height: 200,
    width: '100%',
  },
  routeSummary: {
    padding: SPACING.small,
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: '#fff',
  },
  summaryText: {
    fontSize: 14,
  },
});

export default DirectionsForm; 