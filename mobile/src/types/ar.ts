import { Timestamp } from './global.d';

// Basic AR point types

export interface ARPointBase {
  id: string;
  title: string;
  description: string;
  latitude: number;
  longitude: number;
  altitude?: number;
  type: string;
  metadata: Record<string, any>;
}

export interface HistoricalARPoint extends ARPointBase {
  year: number;
  historical_context: string;
  image_url?: string;
}

export interface NavigationARPoint extends ARPointBase {
  distance: number;
  eta?: number;
  direction: string;
}

export interface NatureARPoint extends ARPointBase {
  species?: string;
  ecosystem_info?: string;
  conservation_status?: string;
}

// Combine the point types into a discriminated union
export type ARPointResponse = 
  | (ARPointBase & { type: 'generic' }) 
  | (HistoricalARPoint & { type: 'historical' })
  | (NavigationARPoint & { type: 'navigation' })
  | (NatureARPoint & { type: 'nature' });

// Request/response types for API endpoints

export interface ARPointRequest {
  latitude: number;
  longitude: number;
  radius?: number;
  types?: string[];
}

export interface ARViewParameters {
  device_heading: number;
  device_pitch: number;
  camera_fov?: number;
}

export interface RenderableARElement {
  id: string;
  source_point_id: string;
  view_x: number;
  view_y: number;
  view_z: number;
  scale: number;
  opacity: number;
  visible: boolean;
  appearance: {
    icon?: string;
    color?: string;
    highlight_color?: string;
    show_year?: boolean;
    show_image?: boolean;
    show_distance?: boolean;
    show_eta?: boolean;
    show_species?: boolean;
    show_labels?: boolean;
    frame_style?: string;
    text_style?: string;
    animation?: string;
    arrow_type?: string;
    pulse_effect?: boolean;
    year?: number | string;
    distance?: number | string;
    eta?: number | string;
    species?: string;
    ecosystem_info?: string;
    conservation_status?: string;
    [key: string]: any;
  };
  interaction: {
    tappable?: boolean;
    expanded_view?: boolean;
    audio_feedback?: boolean;
    haptic_feedback?: boolean;
    show_timeline?: boolean;
    show_full_description?: boolean;
    show_gallery?: boolean;
    comparison_view?: boolean;
    show_full_instructions?: boolean;
    path_preview?: boolean;
    recenter_map?: boolean;
    estimate_time?: boolean;
    show_species_info?: boolean;
    show_ecosystem_info?: boolean;
    show_conservation_status?: boolean;
    camera_integration?: boolean;
    [key: string]: any;
  };
  title?: string;
  description?: string;
}

export interface ARRenderResponse {
  elements: RenderableARElement[];
  settings: ARRenderSettings;
  timestamp: string;
}

export interface ARRenderSettings {
  distance_scale: number;
  opacity: number;
  color_scheme: string;
  show_labels: boolean;
  show_distances: boolean;
  show_arrows: boolean;
  animation_speed: number;
  detail_level: number;
  accessibility_mode: boolean;
}

export interface ARRenderSettingsUpdate {
  distance_scale?: number;
  opacity?: number;
  color_scheme?: string;
  show_labels?: boolean;
  show_distances?: boolean;
  show_arrows?: boolean;
  animation_speed?: number;
  detail_level?: number;
  accessibility_mode?: boolean;
}

export interface HistoricalOverlayRequest {
  latitude: number;
  longitude: number;
  year?: number;
}

export interface HistoricalOverlayResponse {
  title: string;
  year: number;
  description: string;
  key_features: string[];
  daily_life: string;
  image_url?: string;
  latitude: number;
  longitude: number;
}