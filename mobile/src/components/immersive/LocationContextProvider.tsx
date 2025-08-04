import React, { createContext, useState, useEffect, useContext, ReactNode } from 'react';
import { locationService, LocationData } from '../../services/locationService';

import { logger } from '@/services/logger';
interface LocationContextType {
  location: LocationData | null;
  timeOfDay: string;
  weather: string;
  mood: string;
  updateWeather: (weather: string) => void;
  updateMood: (mood: string) => void;
  refreshLocation: () => Promise<LocationData | null>;
  loading: boolean;
  error: string | null;
}

// Default context value
const defaultContextValue: LocationContextType = {
  location: null,
  timeOfDay: 'morning',
  weather: 'sunny',
  mood: 'happy',
  updateWeather: () => {},
  updateMood: () => {},
  refreshLocation: async () => null,
  loading: true,
  error: null
};

// Create the context
export const LocationContext = createContext<LocationContextType>(defaultContextValue);

// Hook for components to use the context
export const useLocationContext = () => useContext(LocationContext);

interface LocationContextProviderProps {
  children: ReactNode;
}

export const LocationContextProvider: React.FC<LocationContextProviderProps> = ({ children }) => {
  const [location, setLocation] = useState<LocationData | null>(null);
  const [timeOfDay, setTimeOfDay] = useState<string>('morning');
  const [weather, setWeather] = useState<string>('sunny');
  const [mood, setMood] = useState<string>('happy');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Initialize location and time of day
  useEffect(() => {
    initializeLocation();
    updateTimeOfDay();
  }, []);

  // Get time of day based on current hour
  const updateTimeOfDay = () => {
    const now = new Date();
    const hour = now.getHours();
    let newTimeOfDay = 'morning';
    
    if (hour >= 12 && hour < 17) {
      newTimeOfDay = 'afternoon';
    } else if (hour >= 17 && hour < 21) {
      newTimeOfDay = 'evening';
    } else if (hour >= 21 || hour < 5) {
      newTimeOfDay = 'night';
    }
    
    setTimeOfDay(newTimeOfDay);
  };

  // Initialize location service and get current location
  const initializeLocation = async () => {
    setLoading(true);
    setError(null);
    
    try {
      await locationService.initialize();
      const currentLocation = await locationService.getCurrentLocation({ 
        enableHighAccuracy: true 
      });
      
      if (currentLocation) {
        setLocation(currentLocation);
      } else {
        setError('Unable to get location. Please check location permissions.');
      }
    } catch (err) {
      logger.error('Error initializing location:', err);
      setError('Failed to initialize location service. Please check permissions.');
    } finally {
      setLoading(false);
    }
  };

  // Refresh the current location
  const refreshLocation = async (): Promise<LocationData | null> => {
    setLoading(true);
    setError(null);
    
    try {
      const currentLocation = await locationService.getCurrentLocation();
      setLocation(currentLocation);
      return currentLocation;
    } catch (err) {
      logger.error('Error refreshing location:', err);
      setError('Failed to get current location.');
      return null;
    } finally {
      setLoading(false);
    }
  };

  // Update weather
  const updateWeather = (newWeather: string) => {
    setWeather(newWeather);
  };

  // Update mood
  const updateMood = (newMood: string) => {
    setMood(newMood);
  };

  // Context value
  const contextValue: LocationContextType = {
    location,
    timeOfDay,
    weather,
    mood,
    updateWeather,
    updateMood,
    refreshLocation,
    loading,
    error
  };

  return (
    <LocationContext.Provider value={contextValue}>
      {children}
    </LocationContext.Provider>
  );
};

export default LocationContextProvider; 