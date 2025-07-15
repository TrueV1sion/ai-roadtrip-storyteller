export interface UserInterests {
  history: boolean;
  nature: boolean;
  science: boolean;
  culture: boolean;
  music: boolean;
  food: boolean;
  architecture: boolean;
  folklore: boolean;
}

export interface User {
  id: string;
  email: string;
  name: string;
  interests: UserInterests;
  created_at: string;
  updated_at: string;
}

export interface UserProfile extends User {
  total_trips: number;
  total_stories: number;
  favorite_stories: number;
  average_rating: number;
}

export interface UserSettings {
  notifications_enabled: boolean;
  offline_mode_enabled: boolean;
  dark_mode_enabled: boolean;
  location_tracking_enabled: boolean;
  music_enabled: boolean;
  voice_enabled: boolean;
  auto_play_stories: boolean;
  language: string;
  distance_unit: 'miles' | 'kilometers';
} 