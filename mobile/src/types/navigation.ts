/**
 * Navigation Types - Type definitions for navigation features
 */

export interface Location {
  lat: number;
  lng: number;
}

export interface Route {
  summary: string;
  bounds: any;
  copyrights: string;
  legs: RouteLeg[];
  overview_coordinates: number[][];
}

export interface RouteLeg {
  distance: Distance;
  duration: Duration;
  start_location: Location;
  end_location: Location;
  start_address: string;
  end_address: string;
  steps: RouteStep[];
}

export interface RouteStep {
  distance: Distance;
  duration: Duration;
  html_instructions: string;
  instructions?: string;
  maneuver?: string;
  start_location?: Location;
  end_location?: Location;
  polyline?: { points: string };
  travel_mode: string;
}

export interface Distance {
  text: string;
  value: number;
}

export interface Duration {
  text: string;
  value: number;
}

export interface NavigationStartRequest {
  route: Route;
  current_location: Location;
  destination: Location;
  navigation_preferences?: {
    voice_personality?: string;
    verbosity?: string;
    audio_priority?: string;
    announce_street_names?: boolean;
    announce_distances?: boolean;
  };
}

export interface NavigationUpdateRequest {
  current_location: Location;
  current_step_index: number;
  distance_to_next_maneuver: number;
  time_to_next_maneuver: number;
  current_speed: number;
  is_on_highway: boolean;
  approaching_complex_intersection: boolean;
  story_playing: boolean;
  audio_priority?: string;
  last_instruction_time?: Date;
}

export interface NavigationInstruction {
  text: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  timing: 'immediate' | 'prepare' | 'reminder' | 'initial' | 'confirmation';
  maneuver_type?: string;
  street_name?: string;
  exit_number?: string;
}

export interface OrchestrationAction {
  action: 'interrupt_all' | 'pause_story' | 'duck_all' | 'wait_for_gap';
  restore_after?: boolean;
  fade_duration_ms?: number;
  duck_level_db?: number;
  max_wait_seconds?: number;
}

export interface NavigationInstructionResponse {
  has_instruction: boolean;
  instruction?: NavigationInstruction;
  audio_url?: string;
  audio_duration?: number;
  orchestration_action?: OrchestrationAction;
  next_check_seconds: number;
}

export interface NavigationStateResponse {
  active: boolean;
  route_id?: string;
  current_instruction_index: number;
  last_instruction_time?: Date;
}

export interface NavigationContext {
  currentStepIndex: number;
  distanceToNextManeuver: number;
  timeToNextManeuver: number;
  currentSpeed: number;
  isOnHighway: boolean;
  approachingComplexIntersection: boolean;
  storyPlaying: boolean;
  lastInstructionTime?: Date;
}

export interface NavigationMetrics {
  distanceToNextManeuver: number;
  timeToNextManeuver: number;
  currentSpeed: number;
  isOnHighway: boolean;
  approachingComplexIntersection: boolean;
  shouldAdvanceStep: boolean;
}