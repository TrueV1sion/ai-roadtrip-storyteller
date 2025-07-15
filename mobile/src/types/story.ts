import { Location } from './location';

export interface Story {
  id: string;
  title: string;
  description: string;
  content: string;
  categories: string[];
  location: Location;
  distance?: number;  // distance from current location
  duration: number;   // story duration in seconds
  audio: {
    url: string;
    duration: number;
    transcript?: string;
  };
  media: Media[];
  relevanceScore?: number;  // 0-1 score based on user interests
  landmarks?: Array<{
    name: string;
    description: string;
    location: Location;
    distance: number;  // distance from story location
    images?: string[];
  }>;
  author?: {
    name: string;
    bio?: string;
    avatar?: string;
  };
  metadata: {
    createdAt: string;
    updatedAt: string;
    source?: string;
    license?: string;
    tags: string[];
    difficulty?: 'easy' | 'moderate' | 'challenging';
    mood?: string[];
    timeOfDay?: ('morning' | 'afternoon' | 'evening' | 'night')[];
    weather?: ('sunny' | 'rainy' | 'cloudy' | 'snowy')[];
    season?: ('spring' | 'summer' | 'fall' | 'winter')[];
  };
}

export interface Media {
  id: string;
  type: 'image' | 'video' | 'audio';
  url: string;
  title?: string;
  description?: string;
  thumbnailUrl?: string;
  duration?: number;  // for video/audio
  width?: number;     // for images/videos
  height?: number;    // for images/videos
  metadata: {
    createdAt: string;
    source?: string;
    license?: string;
    location?: Location;
    tags: string[];
  };
}

export interface StoryCollection {
  id: string;
  title: string;
  description: string;
  stories: Story[];
  curator?: {
    name: string;
    bio?: string;
    avatar?: string;
  };
  metadata: {
    createdAt: string;
    updatedAt: string;
    tags: string[];
    theme?: string;
    estimatedDuration: number;  // total duration in seconds
    difficulty?: 'easy' | 'moderate' | 'challenging';
    recommendedTimeOfDay?: ('morning' | 'afternoon' | 'evening' | 'night')[];
  };
}

export interface StoryProgress {
  storyId: string;
  position: number;  // current position in seconds
  completed: boolean;
  lastPlayed: string;
  rating?: number;  // user rating 1-5
  notes?: string;
  bookmarked: boolean;
} 