import { useState, useCallback } from 'react';
import { Route, Location } from '../types/location';
import { NavigationPreferences } from '../types/navigation';
import { useNavigationPreferences } from './useNavigationPreferences';

interface AlternativeRoute extends Route {
  type: 'fastest' | 'scenic' | 'eco' | 'balanced';
  metrics: {
    scenicScore: number;
    co2Emissions: number;
    fuelConsumption: number;
    trafficDelay: number;
  };
  hasTolls: boolean;
  hasHighways: boolean;
  hasFerries: boolean;
  restrictions: {
    height?: number;  // in meters
    weight?: number;  // in tons
    width?: number;   // in meters
    hazmat?: boolean;
  };
}

export const useRouteAlternatives = () => {
  const { preferences } = useNavigationPreferences();
  const [alternatives, setAlternatives] = useState<AlternativeRoute[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchAlternatives = useCallback(async (
    origin: Location,
    destination: Location,
    waypoints?: Location[]
  ) => {
    setLoading(true);
    try {
      // Fetch multiple route options
      const routes = await Promise.all([
        fetchFastestRoute(origin, destination, waypoints),
        fetchScenicRoute(origin, destination, waypoints),
        fetchEcoFriendlyRoute(origin, destination, waypoints),
        fetchBalancedRoute(origin, destination, waypoints),
      ]);

      // Filter based on preferences
      const filteredRoutes = routes.filter(route => {
        if (!route) return false;
        
        // Apply preference filters
        if (preferences.avoidTolls && route.hasTolls) return false;
        if (preferences.avoidHighways && route.hasHighways) return false;
        if (preferences.avoidFerries && route.hasFerries) return false;

        // Check if scenic detour is within acceptable range
        if (route.type === 'scenic') {
          const fastestRoute = routes.find(r => r?.type === 'fastest');
          if (fastestRoute) {
            const detourTime = route.duration - fastestRoute.duration;
            const maxDetourSeconds = preferences.maxDetourTime * 60;
            if (detourTime > maxDetourSeconds) return false;
          }
        }

        return true;
      });

      setAlternatives(filteredRoutes.filter((r): r is AlternativeRoute => r !== null));
    } catch (error) {
      console.error('Error fetching route alternatives:', error);
    } finally {
      setLoading(false);
    }
  }, [preferences]);

  const fetchFastestRoute = async (
    origin: Location,
    destination: Location,
    waypoints?: Location[]
  ): Promise<AlternativeRoute | null> => {
    // Implementation would call your backend API
    return null;
  };

  const fetchScenicRoute = async (
    origin: Location,
    destination: Location,
    waypoints?: Location[]
  ): Promise<AlternativeRoute | null> => {
    // Implementation would call your backend API with scenic preferences
    return null;
  };

  const fetchEcoFriendlyRoute = async (
    origin: Location,
    destination: Location,
    waypoints?: Location[]
  ): Promise<AlternativeRoute | null> => {
    // Implementation would call your backend API with eco-friendly preferences
    return null;
  };

  const fetchBalancedRoute = async (
    origin: Location,
    destination: Location,
    waypoints?: Location[]
  ): Promise<AlternativeRoute | null> => {
    // Implementation would call your backend API with balanced preferences
    return null;
  };

  return {
    alternatives,
    loading,
    fetchAlternatives,
  };
}; 