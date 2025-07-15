/**
 * Driving Context Hook
 * 
 * Provides current driving context including speed, navigation state,
 * traffic conditions, and other safety-relevant information.
 */

import { useState, useEffect, useRef } from 'react';
import * as Location from 'expo-location';
import { useNavigation } from '@react-navigation/native';
import { locationService } from '../services/locationService';
import { navigationService } from '../services/navigation/navigationService';
import { weatherService } from '../services/weatherService';

export interface DrivingContext {
  speed: number; // mph
  isNavigating: boolean;
  isMoving: boolean;
  trafficCondition: 'light' | 'normal' | 'heavy';
  weatherCondition: 'clear' | 'rain' | 'snow' | 'fog';
  upcomingManeuver?: string;
  maneuverDistance?: number; // miles
  tripDuration: number; // minutes
  lastStopTime?: Date;
  isHighway: boolean;
  isUrban: boolean;
  roadType?: string;
}

export interface DrivingMetrics {
  averageSpeed: number;
  maxSpeed: number;
  totalDistance: number; // miles
  movingTime: number; // minutes
  stoppedTime: number; // minutes
  accelerationEvents: number;
  brakingEvents: number;
}

export const useDrivingContext = () => {
  const [context, setContext] = useState<DrivingContext>({
    speed: 0,
    isNavigating: false,
    isMoving: false,
    trafficCondition: 'normal',
    weatherCondition: 'clear',
    tripDuration: 0,
    isHighway: false,
    isUrban: false
  });

  const [metrics, setMetrics] = useState<DrivingMetrics>({
    averageSpeed: 0,
    maxSpeed: 0,
    totalDistance: 0,
    movingTime: 0,
    stoppedTime: 0,
    accelerationEvents: 0,
    brakingEvents: 0
  });

  const locationSubscription = useRef<Location.LocationSubscription | null>(null);
  const speedHistory = useRef<number[]>([]);
  const lastSpeed = useRef<number>(0);
  const tripStartTime = useRef<Date>(new Date());
  const lastUpdateTime = useRef<Date>(new Date());
  const distanceAccumulator = useRef<number>(0);

  useEffect(() => {
    startLocationTracking();
    return () => {
      if (locationSubscription.current) {
        locationSubscription.current.remove();
      }
    };
  }, []);

  const startLocationTracking = async () => {
    try {
      // Request location permissions
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        console.error('Location permission denied');
        return;
      }

      // Subscribe to location updates
      locationSubscription.current = await Location.watchPositionAsync(
        {
          accuracy: Location.Accuracy.BestForNavigation,
          timeInterval: 1000, // Update every second
          distanceInterval: 5, // Update every 5 meters
        },
        handleLocationUpdate
      );

      // Start periodic context updates
      const contextInterval = setInterval(updateDrivingContext, 5000); // Every 5 seconds
      
      return () => clearInterval(contextInterval);
    } catch (error) {
      console.error('Failed to start location tracking:', error);
    }
  };

  const handleLocationUpdate = async (location: Location.LocationObject) => {
    const { coords } = location;
    const speedMph = (coords.speed || 0) * 2.237; // Convert m/s to mph
    
    // Update speed history
    speedHistory.current.push(speedMph);
    if (speedHistory.current.length > 60) { // Keep last minute
      speedHistory.current.shift();
    }

    // Detect acceleration/braking events
    const speedChange = speedMph - lastSpeed.current;
    if (Math.abs(speedChange) > 5) { // Significant change
      setMetrics(prev => ({
        ...prev,
        accelerationEvents: speedChange > 0 ? prev.accelerationEvents + 1 : prev.accelerationEvents,
        brakingEvents: speedChange < 0 ? prev.brakingEvents + 1 : prev.brakingEvents
      }));
    }

    // Update distance
    if (lastSpeed.current > 0) {
      const timeDelta = (Date.now() - lastUpdateTime.current.getTime()) / 1000 / 3600; // hours
      const distance = lastSpeed.current * timeDelta;
      distanceAccumulator.current += distance;
    }

    // Update context
    setContext(prev => ({
      ...prev,
      speed: speedMph,
      isMoving: speedMph > 1,
      isHighway: speedMph > 55,
      isUrban: speedMph < 35 && speedMph > 0
    }));

    // Update metrics
    const avgSpeed = speedHistory.current.reduce((a, b) => a + b, 0) / speedHistory.current.length;
    const maxSpeed = Math.max(...speedHistory.current);
    const tripMinutes = (Date.now() - tripStartTime.current.getTime()) / 1000 / 60;
    const movingTime = speedHistory.current.filter(s => s > 1).length / 60; // minutes
    
    setMetrics(prev => ({
      ...prev,
      averageSpeed: avgSpeed,
      maxSpeed: maxSpeed,
      totalDistance: distanceAccumulator.current,
      movingTime: movingTime,
      stoppedTime: tripMinutes - movingTime
    }));

    lastSpeed.current = speedMph;
    lastUpdateTime.current = new Date();
  };

  const updateDrivingContext = async () => {
    try {
      // Get navigation state
      const navState = await navigationService.getCurrentState();
      const isNavigating = navState?.isActive || false;
      const upcomingManeuver = navState?.nextManeuver;
      const maneuverDistance = navState?.nextManeuverDistance;

      // Get traffic data (mock for now)
      const trafficCondition = await getTrafficCondition();

      // Get weather data
      const location = await locationService.getCurrentLocation();
      const weather = await weatherService.getCurrentWeather(
        location.coords.latitude,
        location.coords.longitude
      );
      
      const weatherCondition = mapWeatherCondition(weather);

      // Calculate trip duration
      const tripDuration = (Date.now() - tripStartTime.current.getTime()) / 1000 / 60;

      // Detect road type
      const roadType = await detectRoadType(location);

      setContext(prev => ({
        ...prev,
        isNavigating,
        upcomingManeuver,
        maneuverDistance,
        trafficCondition,
        weatherCondition,
        tripDuration,
        roadType
      }));
    } catch (error) {
      console.error('Failed to update driving context:', error);
    }
  };

  const getTrafficCondition = async (): Promise<'light' | 'normal' | 'heavy'> => {
    // In production, this would call a traffic API
    // For now, use speed-based estimation
    const avgSpeed = speedHistory.current.reduce((a, b) => a + b, 0) / speedHistory.current.length;
    const currentSpeed = context.speed;
    
    if (context.isHighway) {
      if (currentSpeed < 25 && avgSpeed < 30) return 'heavy';
      if (currentSpeed < 45 && avgSpeed < 50) return 'normal';
      return 'light';
    } else if (context.isUrban) {
      if (currentSpeed < 10 && avgSpeed < 15) return 'heavy';
      if (currentSpeed < 20 && avgSpeed < 25) return 'normal';
      return 'light';
    }
    
    return 'normal';
  };

  const mapWeatherCondition = (weather: any): 'clear' | 'rain' | 'snow' | 'fog' => {
    if (!weather) return 'clear';
    
    const condition = weather.weather?.[0]?.main?.toLowerCase() || '';
    
    if (condition.includes('rain') || condition.includes('drizzle')) return 'rain';
    if (condition.includes('snow')) return 'snow';
    if (condition.includes('fog') || condition.includes('mist')) return 'fog';
    
    return 'clear';
  };

  const detectRoadType = async (location: Location.LocationObject): Promise<string> => {
    // In production, use reverse geocoding or map data
    // For now, use speed-based detection
    if (context.speed > 55) return 'highway';
    if (context.speed > 35) return 'arterial';
    if (context.speed > 0) return 'local';
    return 'parked';
  };

  const resetTrip = () => {
    tripStartTime.current = new Date();
    speedHistory.current = [];
    distanceAccumulator.current = 0;
    setMetrics({
      averageSpeed: 0,
      maxSpeed: 0,
      totalDistance: 0,
      movingTime: 0,
      stoppedTime: 0,
      accelerationEvents: 0,
      brakingEvents: 0
    });
  };

  const pauseTracking = () => {
    if (locationSubscription.current) {
      locationSubscription.current.remove();
      locationSubscription.current = null;
    }
  };

  const resumeTracking = () => {
    if (!locationSubscription.current) {
      startLocationTracking();
    }
  };

  return {
    context,
    metrics,
    resetTrip,
    pauseTracking,
    resumeTracking,
    isTracking: locationSubscription.current !== null
  };
};