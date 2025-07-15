/**
 * Types for the driving assistant features
 */

// RestStop types
export interface RestStopType {
  id: string;
  name: string;
  location: {
    latitude: number;
    longitude: number;
  };
  distance_from_current: number;
  distance_from_route: number;
  facilities: string[];
  rating?: number;
  estimated_duration: number;
  arrival_time: string;
  category: string;
  amenities: {
    [key: string]: boolean;
  };
}

// FuelStation types
export interface FuelStationType {
  id: string;
  name: string;
  location: {
    latitude: number;
    longitude: number;
  };
  distance_from_current: number;
  distance_from_route: number;
  fuel_types: string[];
  prices?: {
    [fuelType: string]: number;
  };
  brand?: string;
  rating?: number;
  amenities?: {
    [key: string]: boolean;
  };
  busy_level?: string;
}

// TrafficIncident types
export interface TrafficIncidentType {
  id: string;
  type: string;
  severity: number;
  description: string;
  location: {
    latitude: number;
    longitude: number;
  };
  start_time: string;
  end_time?: string;
  affected_roads: string[];
  delay_minutes?: number;
}

// RouteSegment types
export interface RouteSegmentType {
  segment_id: string;
  start_location: {
    latitude: number;
    longitude: number;
  };
  end_location: {
    latitude: number;
    longitude: number;
  };
  distance: number;
  normal_duration: number;
  current_duration: number;
  traffic_level: string;
  speed_limit?: number;
  incidents: TrafficIncidentType[];
}

// DrivingStatus types
export interface DrivingStatusType {
  driving_time: number;
  distance_covered: number;
  fuel_level: number;
  estimated_range: number;
  rest_break_due: boolean;
  next_rest_recommended_in?: number;
  alerts: string[];
  driver_fatigue_level: string;
}

// TrafficInfo types
export interface TrafficInfoType {
  route_id: string;
  overall_traffic: string;
  total_distance: number;
  normal_duration: number;
  current_duration: number;
  delay_seconds: number;
  delay_percentage: number;
  incidents: TrafficIncidentType[];
  segments: RouteSegmentType[];
  alternate_routes: {
    route_id: string;
    description: string;
    distance: number;
    duration: number;
    traffic_level: string;
  }[];
}

// Request types
export interface RestBreakRequestType {
  current_location: {
    latitude: number;
    longitude: number;
  };
  destination: {
    latitude: number;
    longitude: number;
  };
  route_polyline: string;
  driving_time_minutes: number;
  vehicle_type?: string;
  preferences?: {
    [key: string]: any;
  };
}

export interface FuelStationRequestType {
  current_location: {
    latitude: number;
    longitude: number;
  };
  route_polyline: string;
  fuel_level: number;
  fuel_type?: string;
  range_km?: number;
  preferences?: {
    [key: string]: any;
  };
}

export interface TrafficInfoRequestType {
  route_id: string;
  route_polyline: string;
  current_location: {
    latitude: number;
    longitude: number;
  };
  destination: {
    latitude: number;
    longitude: number;
  };
}

export interface DrivingStatusRequestType {
  driving_time_minutes: number;
  distance_covered: number;
  fuel_level: number;
  estimated_range: number;
  last_break_time?: string;
}