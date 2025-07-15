export interface Track {
  id: string;
  title: string;
  artist: string;
  album?: string;
  url: string;
  duration: number;  // in seconds
  thumbnailUrl?: string;
  genre?: string[];
  mood?: string[];
  tempo?: number;    // beats per minute
  key?: string;      // musical key
  energy?: number;   // 0-1 scale
  valence?: number;  // 0-1 scale (emotional positivity)
  metadata: {
    createdAt: string;
    source: string;
    license: string;
    tags: string[];
  };
}

export interface Playlist {
  id: string;
  title: string;
  description: string;
  tracks: Track[];
  duration: number;  // total duration in seconds
  creator?: {
    name: string;
    avatar?: string;
  };
  metadata: {
    createdAt: string;
    updatedAt: string;
    tags: string[];
    mood?: string[];
    genre?: string[];
    timeOfDay?: ('morning' | 'afternoon' | 'evening' | 'night')[];
    weather?: ('sunny' | 'rainy' | 'cloudy' | 'snowy')[];
    season?: ('spring' | 'summer' | 'fall' | 'winter')[];
  };
}

export interface AudioMixConfig {
  storyVolume: number;     // 0-1
  musicVolume: number;     // 0-1
  ambientVolume: number;   // 0-1
  crossfadeDuration: number;  // in seconds
  musicFadeIn: number;     // in seconds
  musicFadeOut: number;    // in seconds
  duckingAmount: number;   // 0-1 (how much to reduce music during speech)
  duckingSpeed: number;    // in milliseconds
  equalizerSettings?: {
    bass: number;      // -12 to 12 dB
    mid: number;       // -12 to 12 dB
    treble: number;    // -12 to 12 dB
  };
}

export interface AudioTransition {
  type: 'crossfade' | 'cut' | 'fadeOut' | 'fadeIn';
  duration: number;  // in seconds
  curve: 'linear' | 'exponential' | 'logarithmic';
  startVolume: number;  // 0-1
  endVolume: number;    // 0-1
}

export interface AudioSegment {
  trackId: string;
  startTime: number;  // in seconds
  duration: number;   // in seconds
  volume: number;     // 0-1
  fadeIn?: AudioTransition;
  fadeOut?: AudioTransition;
  loop?: boolean;
  playbackRate?: number;  // 0.5-2.0
}

export interface AudioTimeline {
  segments: AudioSegment[];
  transitions: AudioTransition[];
  totalDuration: number;  // in seconds
  markers: Array<{
    time: number;
    type: 'story' | 'music' | 'ambient' | 'effect';
    description: string;
  }>;
} 