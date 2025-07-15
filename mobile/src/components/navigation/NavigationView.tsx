import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View,
  StyleSheet,
  Dimensions,
  Platform,
  AppState,
  Vibration,
  Animated,
} from 'react-native';
import {
  Text,
  Surface,
  IconButton,
  Button,
  Portal,
  Modal,
  List,
  Chip,
  ProgressBar,
} from 'react-native-paper';
import MapView, { Marker, Polyline, PROVIDER_GOOGLE } from 'react-native-maps';
import * as Speech from 'expo-speech';
import * as Location from 'expo-location';
import { MaterialIcons } from '@expo/vector-icons';
import {
  Route,
  Location as LocationType,
  RouteStep,
} from '../../types/location';
import {
  NavigationState,
  NavigationEvent,
  RouteMetrics,
  RouteSegment,
} from '../../types/navigation';
import { formatDistance, formatDuration } from '../../utils/formatters';
import { COLORS, SPACING } from '../../theme';
import { useNavigationPreferences } from '../../hooks/useNavigationPreferences';
import { useVoiceGuidance } from '../../hooks/useVoiceGuidance';
import { useRouteAlternatives } from '../../hooks/useRouteAlternatives';
import { AlertBanner } from '../common/AlertBanner';
import { Audio } from 'expo-av';

interface NavigationViewProps {
  route: Route;
  alternativeRoutes?: Route[];
  onExit: () => void;
  onRouteChange: (newRoute: Route) => void;
}

interface TurnPreviewProps {
  instruction: string;
  maneuver?: string;
  distance: number;
  isApproaching: boolean;
}

const TurnPreview: React.FC<TurnPreviewProps> = ({
  instruction,
  maneuver,
  distance,
  isApproaching,
}) => {
  // Animation for the approaching state
  const approachingOpacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (isApproaching) {
      Animated.sequence([
        Animated.timing(approachingOpacity, {
          toValue: 1,
          duration: 500,
          useNativeDriver: true,
        }),
        Animated.timing(approachingOpacity, {
          toValue: 0.3,
          duration: 500,
          useNativeDriver: true,
        }),
      ]).start();
    }
  }, [isApproaching]);

  return (
    <Surface style={styles.turnPreview}>
      <View style={styles.turnIconContainer}>
        <MaterialIcons
          name={getManeuverIcon(maneuver)}
          size={40}
          color={isApproaching ? COLORS.primary : COLORS.text}
          style={styles.turnIcon}
        />
        {isApproaching && (
          <Animated.View
            style={[
              styles.approachingIndicator,
              { opacity: approachingOpacity },
            ]}
          />
        )}
      </View>
      <View style={styles.turnInfo}>
        <Text style={styles.turnInstruction}>{instruction}</Text>
        <Text style={styles.turnDistance}>
          {formatDistance(distance)}
        </Text>
      </View>
    </Surface>
  );
};

interface ProgressIndicatorProps {
  distanceTraveled: number;
  totalDistance: number;
  duration: number;
  timeElapsed: number;
}

const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({
  distanceTraveled,
  totalDistance,
  duration,
  timeElapsed,
}) => {
  // Calculate progress percentages
  const distancePercent = Math.min(100, Math.max(0, (distanceTraveled / totalDistance) * 100));
  const timePercent = Math.min(100, Math.max(0, (timeElapsed / duration) * 100));
  
  // Get formatted values
  const remainingDist = formatDistance(totalDistance - distanceTraveled);
  const remainingTime = formatDuration(duration - timeElapsed);
  
  return (
    <Surface style={styles.progressContainer}>
      <Text style={styles.progressTitle}>Are We There Yet?</Text>
      
      <View style={styles.progressSection}>
        <View style={styles.progressLabelContainer}>
          <Text style={styles.progressLabel}>Distance</Text>
          <Text style={styles.progressValue}>{remainingDist} to go</Text>
        </View>
        <ProgressBar
          progress={distancePercent / 100}
          color={COLORS.primary}
          style={styles.progressBar}
        />
        <Text style={styles.progressPercentage}>
          {Math.round(distancePercent)}%
        </Text>
      </View>
      
      <View style={styles.progressSection}>
        <View style={styles.progressLabelContainer}>
          <Text style={styles.progressLabel}>Time</Text>
          <Text style={styles.progressValue}>{remainingTime} left</Text>
        </View>
        <ProgressBar
          progress={timePercent / 100}
          color={COLORS.primary}
          style={styles.progressBar}
        />
        <Text style={styles.progressPercentage}>
          {Math.round(timePercent)}%
        </Text>
      </View>
      
      {/* Add journey milestones if we're on a long trip */}
      {totalDistance > 50000 && (
        <View style={styles.milestonesContainer}>
          {Array.from({ length: 4 }).map((_, index) => {
            const milestone = (index + 1) * 0.25;
            const isMilestoneReached = distancePercent / 100 >= milestone;
            return (
              <View 
                key={`milestone-${index}`}
                style={[
                  styles.milestone,
                  isMilestoneReached && styles.milestoneReached
                ]}
              >
                <Text style={styles.milestoneText}>
                  {milestone * 100}%
                </Text>
              </View>
            );
          })}
        </View>
      )}
    </Surface>
  );
};

export const NavigationView: React.FC<NavigationViewProps> = ({
  route,
  alternativeRoutes,
  onExit,
  onRouteChange,
}) => {
  const mapRef = useRef<MapView>(null);
  const [navigationState, setNavigationState] = useState<NavigationState>({
    currentRoute: route,
    alternativeRoutes,
    isNavigating: true,
  });
  const [currentLocation, setCurrentLocation] = useState<LocationType>();
  const [currentSegment, setCurrentSegment] = useState<RouteSegment>();
  const [showAlternatives, setShowAlternatives] = useState(false);
  const [alerts, setAlerts] = useState<NavigationEvent[]>([]);
  const [metrics, setMetrics] = useState<RouteMetrics>();
  
  const { preferences } = useNavigationPreferences();
  const { speak, stop: stopSpeech } = useVoiceGuidance();
  const { fetchAlternatives } = useRouteAlternatives();

  const [nextTurn, setNextTurn] = useState<{
    instruction: string;
    maneuver?: string;
    distance: number;
    isApproaching: boolean;
  }>();

  // Add total distance and duration state
  const [totalDistance, setTotalDistance] = useState(0);
  const [totalDuration, setTotalDuration] = useState(0);

  // Initialize location tracking
  useEffect(() => {
    let locationSubscription: any;

    const startLocationTracking = async () => {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') return;

      locationSubscription = await Location.watchPositionAsync(
        {
          accuracy: Location.Accuracy.BestForNavigation,
          distanceInterval: 10,
          timeInterval: 5000,
        },
        (location) => {
          setCurrentLocation({
            latitude: location.coords.latitude,
            longitude: location.coords.longitude,
            accuracy: location.coords.accuracy,
            timestamp: location.timestamp,
          });
        }
      );
    };

    startLocationTracking();
    return () => {
      if (locationSubscription) {
        locationSubscription.remove();
      }
      stopSpeech();
    };
  }, []);

  // Update navigation state based on current location
  useEffect(() => {
    if (!currentLocation || !navigationState.currentRoute) return;

    const segment = findCurrentSegment(
      currentLocation,
      navigationState.currentRoute
    );
    if (segment !== currentSegment) {
      setCurrentSegment(segment);
      
      // Announce new maneuver
      if (segment && preferences.voiceSettings.enabled) {
        speak(segment.instruction);
      }

      // Vibrate for upcoming turns
      if (segment?.maneuver) {
        Vibration.vibrate(200);
      }
    }

    // Check for traffic alerts
    checkTrafficAlerts(currentLocation, navigationState.currentRoute);

    // Update metrics
    updateRouteMetrics(currentLocation, navigationState.currentRoute);

    // Center map on current location
    mapRef.current?.animateCamera({
      center: currentLocation,
      pitch: 60,
      heading: segment?.bearing || 0,
      zoom: 17,
    });
  }, [currentLocation, navigationState.currentRoute]);

  // Update next turn information based on current location
  useEffect(() => {
    if (!currentLocation || !navigationState.currentRoute) return;

    const segment = findCurrentSegment(
      currentLocation,
      navigationState.currentRoute
    );
    
    if (segment) {
      const upcomingTurn = findNextTurn(
        currentLocation,
        segment,
        navigationState.currentRoute
      );
      
      if (upcomingTurn) {
        const isApproaching = upcomingTurn.distance < 200; // 200 meters threshold
        setNextTurn({
          instruction: upcomingTurn.instruction,
          maneuver: upcomingTurn.maneuver,
          distance: upcomingTurn.distance,
          isApproaching,
        });

        // Vibrate when approaching turn
        if (isApproaching) {
          Vibration.vibrate(200);
        }
      }
    }
  }, [currentLocation, navigationState.currentRoute]);

  // Handle traffic alerts
  const checkTrafficAlerts = useCallback((
    location: LocationType,
    route: Route
  ) => {
    // Check for significant delays
    const newAlerts: NavigationEvent[] = [];
    
    if (route.trafficDuration && route.duration) {
      const delay = route.trafficDuration - route.duration;
      if (delay > 300) { // 5+ minutes delay
        newAlerts.push({
          type: 'traffic',
          timestamp: Date.now(),
          location,
          details: {
            severity: delay > 900 ? 'high' : 'medium',
            duration: delay,
            reason: 'Heavy traffic ahead',
          },
        });
      }
    }

    // Update alerts if changed
    if (newAlerts.length > 0) {
      setAlerts(current => [...current, ...newAlerts]);
      
      // Announce severe alerts
      if (preferences.alertSettings.trafficDelays) {
        newAlerts
          .filter(alert => alert.details.severity === 'high')
          .forEach(alert => {
            speak(
              `Traffic alert: ${alert.details.reason}. ` +
              `Delay of ${formatDuration(alert.details.duration || 0)}.`
            );
          });
      }
    }
  }, [preferences, speak]);

  // Update route metrics
  const updateRouteMetrics = useCallback((
    location: LocationType,
    route: Route
  ) => {
    const remainingSegments = findRemainingSegments(location, route);
    const remainingDistance = remainingSegments.reduce(
      (sum, segment) => sum + segment.distance,
      0
    );
    const remainingDuration = remainingSegments.reduce(
      (sum, segment) => sum + (segment.trafficDuration || segment.duration),
      0
    );

    // Calculate environmental impact
    const fuelConsumption = calculateFuelConsumption(
      remainingDistance,
      route.steps
    );
    const co2Emissions = fuelConsumption * 2.31; // kg CO2 per liter

    setMetrics({
      distance: remainingDistance,
      duration: remainingDuration,
      trafficDuration: remainingDuration,
      fuelConsumption,
      co2Emissions,
      complexity: calculateRouteComplexity(remainingSegments),
      scenicScore: calculateScenicScore(remainingSegments),
      safetyScore: calculateSafetyScore(remainingSegments),
      comfortScore: calculateComfortScore(remainingSegments),
    });
  }, []);

  // Switch to alternative route
  const handleRouteChange = useCallback(async (newRoute: Route) => {
    setNavigationState(current => ({
      ...current,
      currentRoute: newRoute,
    }));
    onRouteChange(newRoute);
    setShowAlternatives(false);

    // Announce route change
    if (preferences.voiceSettings.enabled) {
      speak('Switching to alternate route');
    }
  }, [preferences, speak, onRouteChange]);

  // Initialize total distance and duration
  useEffect(() => {
    if (route) {
      const distance = route.steps.reduce((sum, step) => sum + step.distance, 0);
      const duration = route.steps.reduce((sum, step) => sum + step.duration, 0);
      setTotalDistance(distance);
      setTotalDuration(duration);
    }
  }, [route]);

  return (
    <View style={styles.container}>
      {/* Map View */}
      <MapView
        ref={mapRef}
        style={styles.map}
        provider={PROVIDER_GOOGLE}
        showsUserLocation
        followsUserLocation
        showsTraffic={preferences.alertSettings.trafficDelays}
      >
        {navigationState.currentRoute && (
          <>
            <Polyline
              coordinates={navigationState.currentRoute.steps.map(
                step => step.startLocation
              )}
              strokeWidth={5}
              strokeColor={COLORS.primary}
            />
            {currentSegment?.landmarks?.map(landmark => (
              <Marker
                key={landmark.name}
                coordinate={landmark.location}
                title={landmark.name}
                description={`${formatDistance(landmark.distance)} ahead`}
              />
            ))}
          </>
        )}
      </MapView>

      {/* Enhanced Navigation Header */}
      <Surface style={styles.header}>
        <IconButton
          icon="arrow-left"
          size={24}
          onPress={onExit}
        />
        {nextTurn ? (
          <TurnPreview
            instruction={nextTurn.instruction}
            maneuver={nextTurn.maneuver}
            distance={nextTurn.distance}
            isApproaching={nextTurn.isApproaching}
          />
        ) : (
          <View style={styles.headerContent}>
            <Text style={styles.nextManeuver}>
              Finding your route...
            </Text>
          </View>
        )}
        <IconButton
          icon={preferences.voiceSettings.enabled ? 'volume-high' : 'volume-off'}
          size={24}
          onPress={() => {
            // Toggle voice guidance
          }}
        />
      </Surface>

      {/* Alert Banner */}
      {alerts.length > 0 && (
        <AlertBanner
          alerts={alerts}
          onDismiss={(alertId) => {
            setAlerts(current =>
              current.filter(alert => alert.timestamp !== alertId)
            );
          }}
        />
      )}

      {/* Bottom Panel with Progress Indicator */}
      <Surface style={styles.bottomPanel}>
        {metrics && (
          <ProgressIndicator
            distanceTraveled={metrics.distance}
            totalDistance={totalDistance}
            duration={metrics.duration}
            timeElapsed={metrics.duration - metrics.trafficDuration}
          />
        )}
        
        <View style={styles.metrics}>
          <View style={styles.metricItem}>
            <MaterialIcons name="access-time" size={24} color={COLORS.text} />
            <Text style={styles.metricValue}>
              {metrics && formatDuration(metrics.trafficDuration || 0)}
            </Text>
          </View>
          <View style={styles.metricItem}>
            <MaterialIcons name="straighten" size={24} color={COLORS.text} />
            <Text style={styles.metricValue}>
              {metrics && formatDistance(metrics.distance)}
            </Text>
          </View>
          {preferences.alertSettings.speedLimits && currentSegment?.speedLimit && (
            <View style={styles.metricItem}>
              <MaterialIcons name="speed" size={24} color={COLORS.text} />
              <Text style={styles.metricValue}>
                {currentSegment.speedLimit} km/h
              </Text>
            </View>
          )}
        </View>

        <View style={styles.buttonRow}>
          <Button
            mode="outlined"
            icon="routes"
            onPress={() => setShowAlternatives(true)}
          >
            Routes
          </Button>
          <Button
            mode="outlined"
            icon={preferences.voiceSettings.enabled ? 'volume-high' : 'volume-off'}
            onPress={() => {
              // Toggle voice guidance
            }}
          >
            Voice
          </Button>
          {metrics?.scenicScore && (
            <Button
              mode="outlined"
              icon="tree"
              onPress={() => {
                // Show scenic route details
              }}
            >
              Scenic
            </Button>
          )}
        </View>

        {/* Environmental Impact */}
        {metrics?.co2Emissions && (
          <View style={styles.environmental}>
            <Text style={styles.environmentalTitle}>Environmental Impact</Text>
            <View style={styles.environmentalMetrics}>
              <Text>
                CO₂: {metrics.co2Emissions.toFixed(1)} kg
              </Text>
              <Text>
                Fuel: {metrics.fuelConsumption?.toFixed(1)} L
              </Text>
            </View>
            <ProgressBar
              progress={Math.min(metrics.co2Emissions / 10, 1)}
              color={
                metrics.co2Emissions < 5
                  ? COLORS.success
                  : metrics.co2Emissions < 8
                  ? COLORS.warning
                  : COLORS.error
              }
            />
          </View>
        )}
      </Surface>

      {/* Alternative Routes Modal */}
      <Portal>
        <Modal
          visible={showAlternatives}
          onDismiss={() => setShowAlternatives(false)}
          contentContainerStyle={styles.modal}
        >
          <Text style={styles.modalTitle}>Alternative Routes</Text>
          {navigationState.alternativeRoutes?.map((altRoute, index) => (
            <List.Item
              key={index}
              title={`Route ${index + 1}`}
              description={`${formatDuration(altRoute.duration)} · ${formatDistance(
                altRoute.distance
              )}`}
              left={props => (
                <List.Icon
                  {...props}
                  icon={
                    altRoute === navigationState.currentRoute
                      ? 'check-circle'
                      : 'map-marker-path'
                  }
                />
              )}
              right={props => (
                <View style={styles.routeMetrics}>
                  {altRoute.scenicScore && (
                    <Chip icon="tree" size={20}>
                      {altRoute.scenicScore}
                    </Chip>
                  )}
                  {altRoute.trafficDuration && (
                    <Chip
                      icon="car"
                      size={20}
                      style={{
                        backgroundColor:
                          altRoute.trafficDuration > altRoute.duration * 1.5
                            ? COLORS.error
                            : COLORS.success,
                      }}
                    >
                      +{formatDuration(
                        altRoute.trafficDuration - altRoute.duration
                      )}
                    </Chip>
                  )}
                </View>
              )}
              onPress={() => handleRouteChange(altRoute)}
            />
          ))}
        </Modal>
      </Portal>
    </View>
  );
};

// Helper function to get maneuver icon
const getManeuverIcon = (maneuver?: string): string => {
  switch (maneuver?.toLowerCase()) {
    case 'turn-right':
      return 'turn-right';
    case 'turn-left':
      return 'turn-left';
    case 'turn-slight-right':
      return 'subdirectory-arrow-right';
    case 'turn-slight-left':
      return 'subdirectory-arrow-left';
    case 'turn-sharp-right':
      return 'rotate-right';
    case 'turn-sharp-left':
      return 'rotate-left';
    case 'uturn-right':
      return 'u-turn-right';
    case 'uturn-left':
      return 'u-turn-left';
    case 'roundabout-right':
    case 'roundabout-left':
      return 'rotate-right';
    case 'merge':
      return 'merge-type';
    case 'fork':
      return 'call-split';
    case 'ramp':
      return 'call-merge';
    default:
      return 'straight';
  }
};

// Helper function to find next turn
const findNextTurn = (
  currentLocation: Location,
  currentSegment: RouteSegment,
  route: Route
): RouteSegment | null => {
  const segments = route.steps;
  const currentIndex = segments.findIndex(s => s === currentSegment);
  
  if (currentIndex === -1 || currentIndex === segments.length - 1) {
    return null;
  }

  return segments[currentIndex + 1];
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  map: {
    flex: 1,
  },
  header: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    alignItems: 'center',
    padding: SPACING.small,
    elevation: 4,
  },
  headerContent: {
    flex: 1,
  },
  nextManeuver: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  distance: {
    fontSize: 16,
    color: COLORS.textSecondary,
  },
  bottomPanel: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    padding: SPACING.medium,
    elevation: 4,
  },
  metrics: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: SPACING.medium,
  },
  metricItem: {
    alignItems: 'center',
  },
  metricValue: {
    fontSize: 16,
    marginTop: SPACING.xsmall,
  },
  buttonRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: SPACING.medium,
  },
  environmental: {
    padding: SPACING.small,
    backgroundColor: COLORS.surface,
    borderRadius: 8,
  },
  environmentalTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: SPACING.xsmall,
  },
  environmentalMetrics: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: SPACING.xsmall,
  },
  modal: {
    backgroundColor: COLORS.background,
    margin: SPACING.medium,
    padding: SPACING.medium,
    borderRadius: 8,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: SPACING.medium,
  },
  routeMetrics: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.xsmall,
  },
  turnPreview: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: SPACING.medium,
    borderRadius: 8,
    overflow: 'hidden',
  },
  turnIconContainer: {
    width: 60,
    height: 60,
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative',
  },
  turnIcon: {
    zIndex: 1,
  },
  approachingIndicator: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: COLORS.primary,
    borderRadius: 30,
  },
  turnInfo: {
    flex: 1,
    marginLeft: SPACING.small,
  },
  turnInstruction: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  turnDistance: {
    fontSize: 14,
    color: COLORS.textSecondary,
  },
  progressContainer: {
    padding: SPACING.medium,
    marginBottom: SPACING.medium,
    borderRadius: 12,
    elevation: 2,
    backgroundColor: '#fff',
  },
  progressTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: SPACING.small,
  },
  progressSection: {
    marginBottom: SPACING.medium,
  },
  progressLabelContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: SPACING.xsmall,
  },
  progressLabel: {
    fontSize: 12,
    color: COLORS.textSecondary,
  },
  progressValue: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  progressBar: {
    height: 8,
    borderRadius: 4,
    marginBottom: SPACING.xsmall,
  },
  progressPercentage: {
    fontSize: 12,
    color: COLORS.primary,
    fontWeight: '500',
    alignSelf: 'flex-end',
  },
  milestonesContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: SPACING.small,
  },
  milestone: {
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: COLORS.surface,
    justifyContent: 'center',
    alignItems: 'center',
  },
  milestoneReached: {
    backgroundColor: COLORS.primary,
  },
  milestoneText: {
    fontSize: 10,
    fontWeight: 'bold',
    color: '#fff',
  },
});

export default NavigationView; 