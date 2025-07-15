export interface Location {
  latitude: number;
  longitude: number;
  altitude?: number;
  accuracy?: number;
  timestamp?: number;
}

export interface GeoArea {
  center: Location;
  radius: number;  // in meters
}

export interface Route {
  id: string;
  name?: string;
  origin: Location;
  destination: Location;
  waypoints: Location[];
  distance: number;  // in meters
  duration: number;  // in seconds
  trafficDuration?: number;  // in seconds
  polyline: string;
  bounds: {
    northeast: Location;
    southwest: Location;
  };
  steps: RouteStep[];
  alternativeRoutes?: Route[];
  scenicScore?: number;  // 0-100
  poiCount?: number;
}

export interface RouteStep {
  distance: number;
  duration: number;
  startLocation: Location;
  endLocation: Location;
  htmlInstructions: string;
  maneuver?: string;
  polyline: string;
}

export interface POI {
  id: string;
  name: string;
  location: Location;
  category: string[];
  rating?: number;
  userRatingsTotal?: number;
  priceLevel?: number;  // 1-4
  photos?: string[];
  openingHours?: {
    openNow: boolean;
    periods: OpeningPeriod[];
  };
  website?: string;
  phoneNumber?: string;
  address?: string;
  distanceFromRoute?: number;  // in meters
  duration?: number;  // time to reach from route
  popularity?: number;  // 0-100
  relevanceScore?: number;  // 0-100
}

export interface OpeningPeriod {
  open: {
    day: number;  // 0-6 (Sunday-Saturday)
    time: string;  // "HHMM" format
  };
  close: {
    day: number;
    time: string;
  };
}

export interface HistoricalSite extends POI {
  historicalPeriod?: string[];
  significance?: string;
  description?: string;
  yearEstablished?: number;
  nationalRegister?: boolean;
  stories?: Story[];
  media?: Media[];
  tours?: Tour[];
  historicalScore?: number;  // 0-100
}

export interface Story {
  id: string;
  title: string;
  content: string;
  source: string;
  date?: string;
  media?: Media[];
  relevanceScore?: number;
}

export interface Media {
  id: string;
  type: 'image' | 'video' | 'audio';
  url: string;
  title?: string;
  description?: string;
  date?: string;
  source: string;
  license?: string;
}

export interface Tour {
  id: string;
  name: string;
  description: string;
  duration: number;  // in minutes
  distance: number;  // in meters
  stops: TourStop[];
  accessibility?: string[];
  difficulty?: 'easy' | 'moderate' | 'difficult';
}

export interface TourStop {
  id: string;
  name: string;
  location: Location;
  description: string;
  duration: number;  // in minutes
  media?: Media[];
  nextStop?: string;  // ID of next stop
} 