/**
 * Service for enriching location data with additional information
 * from various APIs (Places, Weather, Wikipedia, etc.)
 */

import { LocationData } from './locationService';

// Types for enriched location data
export interface PlaceDetails {
  id: string;
  name: string;
  type: string;
  address?: string;
  distance?: number; // meters
  rating?: number;
  reviewCount?: number;
  photoUrl?: string;
  openNow?: boolean;
  priceLevel?: number; // 1-4
  tags?: string[];
  coordinates: {
    latitude: number;
    longitude: number;
  };
  contact?: {
    phone?: string;
    website?: string;
  };
}

export interface HistoricalFact {
  id: string;
  title: string;
  description: string;
  year?: number | string;
  source?: string;
  imageUrl?: string;
  link?: string;
  tags?: string[];
}

export interface WeatherData {
  currentConditions: {
    temperature: number; // celsius
    feelsLike: number; // celsius
    humidity: number; // percentage
    windSpeed: number; // km/h
    windDirection: string; // N, NE, E, etc.
    condition: string; // "Sunny", "Cloudy", etc.
    icon: string; // icon code
    precipitationProbability: number; // percentage
    uvIndex: number;
    visibility: number; // km
    timestamp: number;
  };
  forecast: Array<{
    date: string;
    dayOfWeek: string;
    high: number;
    low: number;
    condition: string;
    icon: string;
    precipitationProbability: number;
  }>;
}

export interface LocationEnrichmentResult {
  locationName: string;
  places: PlaceDetails[];
  historicalFacts: HistoricalFact[];
  weather?: WeatherData;
  fetchTimestamp: number;
}

class LocationEnrichmentService {
  private cachedResults: { [locationKey: string]: LocationEnrichmentResult } = {};
  private cacheValidityPeriod = 30 * 60 * 1000; // 30 minutes in milliseconds
  
  /**
   * Get enriched information for a location
   */
  async getEnrichedLocationInfo(
    location: LocationData,
    forceRefresh: boolean = false
  ): Promise<LocationEnrichmentResult> {
    // Generate a cache key based on rounded coordinates (approx 1km precision)
    const locationKey = `${Math.round(location.latitude * 100) / 100},${Math.round(location.longitude * 100) / 100}`;
    
    // Check cache if not forcing refresh
    if (!forceRefresh && this.cachedResults[locationKey]) {
      const cachedResult = this.cachedResults[locationKey];
      const now = Date.now();
      
      // Return cached result if still valid
      if (now - cachedResult.fetchTimestamp < this.cacheValidityPeriod) {
        return cachedResult;
      }
    }
    
    // Fetch all the data in parallel
    const [
      locationName,
      places,
      historicalFacts,
      weather
    ] = await Promise.all([
      this.getLocationName(location),
      this.getNearbyPlaces(location),
      this.getHistoricalFacts(location),
      this.getWeatherData(location)
    ]);
    
    // Combine results
    const result: LocationEnrichmentResult = {
      locationName,
      places,
      historicalFacts,
      weather,
      fetchTimestamp: Date.now()
    };
    
    // Cache the result
    this.cachedResults[locationKey] = result;
    
    return result;
  }
  
  /**
   * Get the name of a location (city, neighborhood, etc.)
   */
  private async getLocationName(location: LocationData): Promise<string> {
    // In a real implementation, this would use a geocoding API
    // For this example, we'll return a simulated value
    
    // Use the location to determine a simulated place name
    // New York coordinates: 40.7128, -74.0060
    if (Math.abs(location.latitude - 40.7128) < 0.1 && 
        Math.abs(location.longitude - (-74.0060)) < 0.1) {
      return 'New York City, NY';
    }
    
    // Chicago coordinates: 41.8781, -87.6298
    if (Math.abs(location.latitude - 41.8781) < 0.1 && 
        Math.abs(location.longitude - (-87.6298)) < 0.1) {
      return 'Chicago, IL';
    }
    
    // Default
    return 'Current Location';
  }
  
  /**
   * Get nearby places of interest
   */
  private async getNearbyPlaces(location: LocationData): Promise<PlaceDetails[]> {
    // In a real implementation, this would use a places API like Google Places
    // For this example, we'll return simulated data
    
    // Create simulated places based on the location
    return [
      {
        id: 'place1',
        name: 'Central Park',
        type: 'park',
        address: 'Central Park, New York, NY',
        distance: 1200,
        rating: 4.8,
        reviewCount: 52435,
        photoUrl: 'https://example.com/photos/central-park.jpg',
        tags: ['park', 'nature', 'recreation'],
        coordinates: {
          latitude: location.latitude + 0.01,
          longitude: location.longitude - 0.01
        },
        contact: {
          website: 'https://www.centralparknyc.org/'
        }
      },
      {
        id: 'place2',
        name: 'Empire State Building',
        type: 'landmark',
        address: '20 W 34th St, New York, NY 10001',
        distance: 2500,
        rating: 4.7,
        reviewCount: 87346,
        photoUrl: 'https://example.com/photos/empire-state.jpg',
        tags: ['landmark', 'architecture', 'tourist'],
        coordinates: {
          latitude: location.latitude - 0.008,
          longitude: location.longitude + 0.005
        },
        contact: {
          phone: '+12127363100',
          website: 'https://www.esbnyc.com/'
        }
      },
      {
        id: 'place3',
        name: 'Metropolitan Museum of Art',
        type: 'museum',
        address: '1000 5th Ave, New York, NY 10028',
        distance: 1800,
        rating: 4.9,
        reviewCount: 38291,
        photoUrl: 'https://example.com/photos/met-museum.jpg',
        tags: ['museum', 'art', 'culture'],
        coordinates: {
          latitude: location.latitude + 0.005,
          longitude: location.longitude + 0.01
        },
        contact: {
          phone: '+12125357710',
          website: 'https://www.metmuseum.org/'
        }
      },
      {
        id: 'place4',
        name: 'Statue of Liberty',
        type: 'landmark',
        address: 'New York, NY 10004',
        distance: 7500,
        rating: 4.7,
        reviewCount: 70123,
        photoUrl: 'https://example.com/photos/statue-liberty.jpg',
        tags: ['landmark', 'tourist', 'history'],
        coordinates: {
          latitude: location.latitude - 0.03,
          longitude: location.longitude - 0.02
        },
        contact: {
          website: 'https://www.nps.gov/stli/'
        }
      },
      {
        id: 'place5',
        name: 'Brooklyn Bridge',
        type: 'landmark',
        address: 'Brooklyn Bridge, New York, NY 10038',
        distance: 5000,
        rating: 4.8,
        reviewCount: 45678,
        photoUrl: 'https://example.com/photos/brooklyn-bridge.jpg',
        tags: ['landmark', 'architecture', 'tourist'],
        coordinates: {
          latitude: location.latitude - 0.02,
          longitude: location.longitude + 0.015
        }
      }
    ];
  }
  
  /**
   * Get historical facts about a location
   */
  private async getHistoricalFacts(location: LocationData): Promise<HistoricalFact[]> {
    // In a real implementation, this would use an API like Wikipedia
    // For this example, we'll return simulated data
    
    // New York facts
    if (Math.abs(location.latitude - 40.7128) < 0.1 && 
        Math.abs(location.longitude - (-74.0060)) < 0.1) {
      return [
        {
          id: 'fact1',
          title: 'The Founding of New York',
          description: 'New York City was founded in 1624 as a trading post by colonists of the Dutch Republic and was named New Amsterdam in 1626.',
          year: '1624',
          source: 'Wikipedia',
          tags: ['founding', 'colonial', 'dutch']
        },
        {
          id: 'fact2',
          title: 'The Statue of Liberty',
          description: 'The Statue of Liberty was a gift from the people of France to the United States and was dedicated on October 28, 1886.',
          year: '1886',
          source: 'Wikipedia',
          imageUrl: 'https://example.com/images/statue-liberty.jpg',
          tags: ['landmark', 'france', 'gift']
        },
        {
          id: 'fact3',
          title: 'The Empire State Building',
          description: 'The Empire State Building was completed in 1931 and was the tallest building in the world until 1970.',
          year: '1931',
          source: 'Wikipedia',
          imageUrl: 'https://example.com/images/empire-state.jpg',
          tags: ['architecture', 'skyscraper', 'landmark']
        }
      ];
    }
    
    // Generic facts for other locations
    return [
      {
        id: 'fact1',
        title: 'Local History',
        description: 'This area has a rich history dating back centuries with contributions from indigenous peoples and later settlers.',
        source: 'Location Enrichment Service',
        tags: ['history', 'general']
      },
      {
        id: 'fact2',
        title: 'Transportation Development',
        description: 'The development of transportation routes played a major role in shaping the growth and development of this region.',
        source: 'Location Enrichment Service',
        tags: ['transportation', 'development']
      },
      {
        id: 'fact3',
        title: 'Cultural Significance',
        description: 'This area has cultural significance to various groups who have lived here throughout history.',
        source: 'Location Enrichment Service',
        tags: ['culture', 'heritage']
      }
    ];
  }
  
  /**
   * Get weather data for a location
   */
  private async getWeatherData(location: LocationData): Promise<WeatherData> {
    // In a real implementation, this would use a weather API
    // For this example, we'll return simulated data
    
    const currentDate = new Date();
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    
    // Generate forecast for the next 5 days
    const forecast = Array.from({ length: 5 }, (_, i) => {
      const forecastDate = new Date();
      forecastDate.setDate(currentDate.getDate() + i + 1);
      
      return {
        date: `${forecastDate.getMonth() + 1}/${forecastDate.getDate()}`,
        dayOfWeek: days[forecastDate.getDay()],
        high: Math.round(20 + Math.random() * 10), // Random temp between 20-30
        low: Math.round(10 + Math.random() * 5),   // Random temp between 10-15
        condition: ['Sunny', 'Partly Cloudy', 'Cloudy', 'Light Rain', 'Sunny'][Math.floor(Math.random() * 5)],
        icon: ['sun', 'cloud-sun', 'cloud', 'cloud-rain', 'sun'][Math.floor(Math.random() * 5)],
        precipitationProbability: Math.round(Math.random() * 100)
      };
    });
    
    return {
      currentConditions: {
        temperature: 22,
        feelsLike: 23,
        humidity: 65,
        windSpeed: 12,
        windDirection: 'NE',
        condition: 'Partly Cloudy',
        icon: 'cloud-sun',
        precipitationProbability: 20,
        uvIndex: 4,
        visibility: 10,
        timestamp: Date.now()
      },
      forecast
    };
  }
  
  /**
   * Format places for display, potentially grouping by category
   */
  formatPlacesForDisplay(places: PlaceDetails[]): { [category: string]: PlaceDetails[] } {
    // Group places by type
    const groupedPlaces: { [category: string]: PlaceDetails[] } = {};
    
    places.forEach(place => {
      const category = this.prettifyCategory(place.type);
      
      if (!groupedPlaces[category]) {
        groupedPlaces[category] = [];
      }
      
      groupedPlaces[category].push(place);
    });
    
    // Sort each category by distance
    Object.keys(groupedPlaces).forEach(category => {
      groupedPlaces[category].sort((a, b) => (a.distance || 0) - (b.distance || 0));
    });
    
    return groupedPlaces;
  }
  
  /**
   * Format historical facts for display
   */
  formatHistoricalFactsForDisplay(facts: HistoricalFact[]): HistoricalFact[] {
    // Sort by year if available, otherwise preserve order
    return [...facts].sort((a, b) => {
      if (a.year && b.year) {
        // Convert year strings to numbers if they are years
        const yearA = typeof a.year === 'string' ? parseInt(a.year, 10) : a.year;
        const yearB = typeof b.year === 'string' ? parseInt(b.year, 10) : b.year;
        
        // If both are valid numbers, sort chronologically
        if (!isNaN(yearA as number) && !isNaN(yearB as number)) {
          return (yearA as number) - (yearB as number);
        }
      }
      
      // Default to preserve order
      return 0;
    });
  }
  
  /**
   * Format weather data for display
   */
  formatWeatherForDisplay(weather: WeatherData): {
    current: string;
    forecast: string;
    conditions: string[];
  } {
    // Format current conditions
    const current = `${weather.currentConditions.temperature}°C, ${weather.currentConditions.condition}`;
    
    // Format forecast
    const forecast = weather.forecast.map(day => 
      `${day.dayOfWeek}: ${day.condition}, ${day.high}°/${day.low}°`
    ).join('\n');
    
    // Individual conditions for displaying in UI
    const conditions = [
      `Feels like: ${weather.currentConditions.feelsLike}°C`,
      `Humidity: ${weather.currentConditions.humidity}%`,
      `Wind: ${weather.currentConditions.windSpeed} km/h ${weather.currentConditions.windDirection}`,
      `Precipitation: ${weather.currentConditions.precipitationProbability}%`,
      `UV Index: ${weather.currentConditions.uvIndex}`,
      `Visibility: ${weather.currentConditions.visibility} km`
    ];
    
    return { current, forecast, conditions };
  }
  
  /**
   * Make a category name prettier for display
   */
  private prettifyCategory(category: string): string {
    // Convert snake_case or kebab-case to Title Case
    const formatted = category
      .replace(/[-_]/g, ' ')
      .replace(/\w\S*/g, txt => txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase());
    
    // Special cases
    const specialCases: { [key: string]: string } = {
      'Poi': 'Points of Interest',
      'Landmark': 'Landmarks',
      'Museum': 'Museums',
      'Restaurant': 'Restaurants',
      'Cafe': 'Cafes & Coffee Shops',
      'Park': 'Parks & Nature',
      'Hotel': 'Hotels & Accommodations'
    };
    
    return specialCases[formatted] || formatted;
  }
}

// Singleton instance
export const locationEnrichmentService = new LocationEnrichmentService();
export default locationEnrichmentService;
