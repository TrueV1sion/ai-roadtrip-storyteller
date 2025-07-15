import { Location } from './location';

export interface Story {
  id: string;
  title: string;
  content: string;
  source: string;
  location?: Location;
  date?: string;
  author?: string;
  tags?: string[];
  media?: Media[];
  relatedStories?: string[];  // IDs of related stories
  relevanceScore?: number;
  culturalSignificance?: number;  // 0-100
  verificationStatus?: 'verified' | 'unverified' | 'disputed';
}

export interface Media {
  id: string;
  type: 'image' | 'video' | 'audio' | 'document';
  url: string;
  title?: string;
  description?: string;
  creator?: string;
  date?: string;
  source: string;
  license?: string;
  format?: string;
  duration?: number;  // in seconds, for audio/video
  thumbnail?: string;
  tags?: string[];
  location?: Location;
  transcription?: string;
}

export interface CulturalEvent {
  id: string;
  name: string;
  description: string;
  startDate: Date;
  endDate: Date;
  location: Location;
  venue: {
    id: string;
    name: string;
    address: string;
    capacity?: number;
    accessibility?: string[];
  };
  category: string[];
  ticketUrl?: string;
  price?: {
    min: number;
    max: number;
    currency: string;
  };
  organizer: {
    id: string;
    name: string;
    description?: string;
    website?: string;
    contactInfo?: {
      email?: string;
      phone?: string;
    };
  };
  images?: string[];
  tags: string[];
  status: 'scheduled' | 'cancelled' | 'postponed';
  attendance?: {
    capacity: number;
    registered: number;
  };
  relevanceScore?: number;
  culturalSignificance?: number;  // 0-100
  relatedStories?: Story[];
  media?: Media[];
}

export interface CulturalSite {
  id: string;
  name: string;
  description: string;
  location: Location;
  type: string[];  // e.g., ['museum', 'historical_site', 'monument']
  openingHours?: {
    openNow: boolean;
    periods: OpeningPeriod[];
  };
  admissionInfo?: {
    price?: number;
    currency?: string;
    notes?: string;
  };
  accessibility?: string[];
  contact?: {
    phone?: string;
    email?: string;
    website?: string;
  };
  media?: Media[];
  stories?: Story[];
  events?: CulturalEvent[];
  rating?: number;
  reviews?: number;
  popularity?: number;  // 0-100
  culturalSignificance?: number;  // 0-100
  yearEstablished?: number;
  lastUpdated: Date;
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

export interface CulturalTour {
  id: string;
  name: string;
  description: string;
  duration: number;  // in minutes
  distance: number;  // in meters
  difficulty: 'easy' | 'moderate' | 'difficult';
  stops: CulturalTourStop[];
  themes: string[];
  accessibility?: string[];
  languages: string[];
  recommendedTransport: string[];
  media?: Media[];
  rating?: number;
  reviews?: number;
}

export interface CulturalTourStop {
  id: string;
  name: string;
  description: string;
  location: Location;
  duration: number;  // in minutes
  sites: CulturalSite[];
  stories?: Story[];
  media?: Media[];
  nextStop?: string;  // ID of next stop
} 