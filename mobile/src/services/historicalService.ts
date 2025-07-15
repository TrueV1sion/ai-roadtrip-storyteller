import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import { LocationData } from '@services/locationService';
import { withRetry } from '@utils/async';
import { memoizeAsync } from '@utils/cache';
import { EXPO_PUBLIC_CULTURAL_API_KEY, EXPO_PUBLIC_WIKIPEDIA_API_KEY } from '@env';

export interface HistoricalEvent {
  date: string;
  description: string;
  significance: string;
  verified: boolean;
  source: string;
  category: string;
  location?: {
    latitude: number;
    longitude: number;
    name: string;
  };
  media?: {
    type: 'image' | 'video' | 'audio';
    url: string;
    caption: string;
  }[];
  relatedEvents?: string[];
  tags: string[];
  storyElements?: {
    funFacts: string[];
    trivia: string[];
    interactivePrompts: string[];
    kidFriendlyDescription?: string;
  };
  timeContext?: {
    timeOfDay: 'morning' | 'afternoon' | 'evening' | 'night';
    season: 'spring' | 'summer' | 'fall' | 'winter';
    isSpecialDay: boolean;
    specialDayName?: string;
  };
  engagement?: {
    popularity: number;
    userRatings: number;
    familyFriendly: boolean;
    recommendedAge?: string;
    visitDuration?: string;
  };
}

export interface LocalCulture {
  traditions: {
    name: string;
    description: string;
    period?: string;
    significance: string;
    storyElements?: {
      origin: string;
      modernPractice: string;
      familyActivities: string[];
      funFacts: string[];
    };
  }[];
  cuisine: {
    name: string;
    description: string;
    ingredients?: string[];
    origin: string;
    storyElements?: {
      history: string;
      preparation: string;
      familyRecipe?: string;
      tastingNotes: string[];
      kidFriendly: boolean;
    };
  }[];
  music: {
    genre: string;
    description: string;
    notable_artists?: string[];
    period?: string;
    storyElements?: {
      culturalImpact: string;
      danceStyles: string[];
      instruments: string[];
      learningResources: string[];
    };
  }[];
  demographics?: {
    languages: string[];
    ethnicities: string[];
    religions: string[];
    culturalStories: {
      title: string;
      narrative: string;
      significance: string;
    }[];
  };
  festivals?: {
    name: string;
    date: string;
    description: string;
    significance: string;
    storyElements?: {
      preparations: string[];
      activities: string[];
      familyGuide: string;
      photoSpots: string[];
      soundscape: string;
    };
  }[];
  localLegends?: {
    title: string;
    story: string;
    historicalBasis?: string;
    locations: string[];
    kidFriendlyVersion?: string;
  }[];
}

interface EnrichmentContext {
  timeOfDay: 'morning' | 'afternoon' | 'evening' | 'night';
  season: 'spring' | 'summer' | 'fall' | 'winter';
  weather?: string;
  userPreferences?: {
    interests: string[];
    previousVisits?: number;
    favoriteTypes?: string[];
    ageGroup?: string;
  };
}

class HistoricalService {
  private readonly WIKIPEDIA_API_URL = 'https://en.wikipedia.org/w/api.php';
  private readonly CULTURAL_API_KEY = EXPO_PUBLIC_CULTURAL_API_KEY;
  private readonly api: AxiosInstance;
  private readonly RATE_LIMIT = {
    maxRequests: 100,
    timeWindow: 60000, // 1 minute
    currentRequests: 0,
    windowStart: Date.now(),
  };

  constructor() {
    this.api = axios.create({
      timeout: 10000,
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
    });

    // Add request interceptor for rate limiting
    this.api.interceptors.request.use(async (config: AxiosRequestConfig) => {
      await this.checkRateLimit();
      return config;
    });
  }

  private async checkRateLimit(): Promise<void> {
    const now = Date.now();
    if (now - this.RATE_LIMIT.windowStart >= this.RATE_LIMIT.timeWindow) {
      // Reset window
      this.RATE_LIMIT.windowStart = now;
      this.RATE_LIMIT.currentRequests = 0;
    }

    if (this.RATE_LIMIT.currentRequests >= this.RATE_LIMIT.maxRequests) {
      const waitTime = this.RATE_LIMIT.timeWindow - (now - this.RATE_LIMIT.windowStart);
      await new Promise(resolve => setTimeout(resolve, waitTime));
      this.RATE_LIMIT.windowStart = Date.now();
      this.RATE_LIMIT.currentRequests = 0;
    }

    this.RATE_LIMIT.currentRequests++;
  }

  getHistoricalEvents = memoizeAsync(
    async (
      location: LocationData,
      radius: number = 10000,
      timeRange: { start?: Date; end?: Date } = {},
      context?: EnrichmentContext
    ): Promise<HistoricalEvent[]> => {
      return withRetry(async () => {
        const [wikiEvents, culturalEvents, archivalEvents] = await Promise.all([
          this.fetchWikipediaEvents(location, radius),
          this.fetchCulturalEvents(location, radius, timeRange),
          this.fetchArchivalEvents(location, radius, timeRange),
        ]);

        const combinedEvents = this.combineHistoricalEvents(
          wikiEvents,
          culturalEvents,
          archivalEvents
        );

        // Enrich with storytelling elements and context
        const enrichedEvents = await this.verifyAndEnrichEvents(combinedEvents, context);
        
        // Sort by relevance and engagement potential
        return this.sortEventsByRelevance(enrichedEvents, context);
      });
    },
    100,
    3600
  );

  getLocalCulture = memoizeAsync(
    async (location: LocationData): Promise<LocalCulture> => {
      return withRetry(async () => {
        // Fetch cultural data from multiple sources in parallel
        const [traditions, cuisine, music, demographics] = await Promise.all([
          this.fetchTraditionalCulture(location),
          this.fetchLocalCuisine(location),
          this.fetchLocalMusic(location),
          this.fetchDemographics(location),
        ]);

        return {
          traditions,
          cuisine,
          music,
          demographics,
          festivals: await this.fetchLocalFestivals(location),
        };
      });
    },
    50,  // Cache size
    7200 // TTL: 2 hours
  );

  private async fetchWikipediaEvents(
    location: LocationData,
    radius: number
  ): Promise<HistoricalEvent[]> {
    const response = await this.api.get(this.WIKIPEDIA_API_URL, {
      params: {
        action: 'query',
        format: 'json',
        list: 'geosearch',
        gsradius: radius,
        gscoord: `${location.latitude}|${location.longitude}`,
        gslimit: 50,
        origin: '*',
      },
    });

    const pages = response.data.query.geosearch;
    return Promise.all(
      pages.map(async (page: any) => {
        const details = await this.fetchWikipediaPageDetails(page.pageid);
        return this.parseWikipediaEventDetails(details);
      })
    );
  }

  private async fetchWikipediaPageDetails(pageId: number): Promise<any> {
    const response = await this.api.get(this.WIKIPEDIA_API_URL, {
      params: {
        action: 'query',
        format: 'json',
        prop: 'extracts|categories|coordinates|images',
        exintro: true,
        explaintext: true,
        pageids: pageId,
        origin: '*',
      },
    });

    return response.data.query.pages[pageId];
  }

  private parseWikipediaEventDetails(details: any): HistoricalEvent {
    // Implement Wikipedia response parsing
    return {
      date: '',
      description: details.extract || '',
      significance: '',
      verified: true,
      source: 'Wikipedia',
      category: 'historical',
      tags: [],
    };
  }

  private async fetchCulturalEvents(
    location: LocationData,
    radius: number,
    timeRange: { start?: Date; end?: Date }
  ): Promise<HistoricalEvent[]> {
    try {
      const response = await this.api.get('https://api.culturaldata.org/v1/events', {
        params: {
          api_key: this.CULTURAL_API_KEY,
          lat: location.latitude,
          lon: location.longitude,
          radius: Math.floor(radius / 1000), // Convert to km
          start_date: timeRange.start?.toISOString(),
          end_date: timeRange.end?.toISOString(),
          limit: 50
        }
      });

      return response.data.events.map((event: any) => ({
        date: event.date,
        description: event.description,
        significance: event.cultural_significance || 'Historical cultural event',
        verified: true,
        source: 'Cultural Data API',
        category: event.category || 'cultural',
        location: event.coordinates ? {
          latitude: event.coordinates.lat,
          longitude: event.coordinates.lon,
          name: event.location_name
        } : undefined,
        media: event.media?.map((m: any) => ({
          type: m.type,
          url: m.url,
          caption: m.caption
        })),
        tags: event.tags || []
      }));
    } catch (error) {
      console.error('Error fetching cultural events:', error);
      return [];
    }
  }

  private async fetchArchivalEvents(
    location: LocationData,
    radius: number,
    timeRange: { start?: Date; end?: Date }
  ): Promise<HistoricalEvent[]> {
    try {
      // Fetch from multiple archival sources in parallel
      const [nationalArchives, localArchives] = await Promise.all([
        this.fetchNationalArchives(location, radius, timeRange),
        this.fetchLocalArchives(location, radius, timeRange)
      ]);

      return [...nationalArchives, ...localArchives];
    } catch (error) {
      console.error('Error fetching archival events:', error);
      return [];
    }
  }

  private async fetchNationalArchives(
    location: LocationData,
    radius: number,
    timeRange: { start?: Date; end?: Date }
  ): Promise<HistoricalEvent[]> {
    try {
      const response = await this.api.get('https://catalog.archives.gov/api/v1', {
        params: {
          q: `location:(${location.latitude},${location.longitude},${radius}km)`,
          resultTypes: 'item',
          rows: 50,
          ...(timeRange.start && { fromDate: timeRange.start.toISOString().split('T')[0] }),
          ...(timeRange.end && { toDate: timeRange.end.toISOString().split('T')[0] })
        }
      });

      return response.data.results.map((item: any) => ({
        date: item.date || 'Unknown Date',
        description: item.description || item.title,
        significance: item.scope || 'National Archive Record',
        verified: true,
        source: 'National Archives',
        category: 'archival',
        location: item.geolocation ? {
          latitude: item.geolocation.latitude,
          longitude: item.geolocation.longitude,
          name: item.location || 'Unknown Location'
        } : undefined,
        media: item.digitalObjects?.map((obj: any) => ({
          type: this.getMediaType(obj.mime),
          url: obj.url,
          caption: obj.title
        })),
        tags: item.subjects || []
      }));
    } catch (error) {
      console.error('Error fetching from national archives:', error);
      return [];
    }
  }

  private async fetchLocalArchives(
    location: LocationData,
    radius: number,
    timeRange: { start?: Date; end?: Date }
  ): Promise<HistoricalEvent[]> {
    try {
      // This would typically connect to a local/state archives API
      // For now, returning an empty array as implementation depends on specific local archives
      return [];
    } catch (error) {
      console.error('Error fetching from local archives:', error);
      return [];
    }
  }

  private getMediaType(mime: string): 'image' | 'video' | 'audio' {
    if (mime.startsWith('image/')) return 'image';
    if (mime.startsWith('video/')) return 'video';
    if (mime.startsWith('audio/')) return 'audio';
    return 'image'; // default to image
  }

  private async verifyAndEnrichEvents(
    events: HistoricalEvent[],
    context?: EnrichmentContext
  ): Promise<HistoricalEvent[]> {
    return Promise.all(
      events.map(async (event) => {
        try {
          // Verify event details from multiple sources
          const verificationResult = await this.verifyHistoricalEvent(event);
          
          // Enrich with additional context and media
          const enrichedEvent = await this.enrichEventDetails(event, context);

          return {
            ...enrichedEvent,
            verified: verificationResult.verified,
          };
        } catch (error) {
          console.error(`Error processing historical event: ${error}`);
          return event;
        }
      })
    );
  }

  private async verifyHistoricalEvent(event: HistoricalEvent): Promise<{ verified: boolean }> {
    // Implement event verification logic
    return { verified: true };
  }

  private async enrichEventDetails(
    event: HistoricalEvent,
    context?: EnrichmentContext
  ): Promise<HistoricalEvent> {
    try {
      // Add storytelling elements
      const storyElements = await this.generateStoryElements(event, context);
      
      // Add time-based context
      const timeContext = this.generateTimeContext(context);
      
      // Add engagement metrics
      const engagement = await this.fetchEngagementMetrics(event);

      // Enhance media with high-quality sources
      const enhancedMedia = await this.enhanceEventMedia(event.media || []);

      return {
        ...event,
        storyElements,
        timeContext,
        engagement,
        media: enhancedMedia,
      };
    } catch (error) {
      console.error(`Error enriching event details: ${error}`);
      return event;
    }
  }

  private async generateStoryElements(
    event: HistoricalEvent,
    context?: EnrichmentContext
  ): Promise<HistoricalEvent['storyElements']> {
    try {
      const [funFacts, trivia] = await Promise.all([
        this.generateFunFacts(event),
        this.generateTrivia(event),
      ]);

      const interactivePrompts = await this.generateInteractivePrompts(event, context);
      const kidFriendlyDescription = await this.generateKidFriendlyDescription(event);

      return {
        funFacts,
        trivia,
        interactivePrompts,
        kidFriendlyDescription,
      };
    } catch (error) {
      console.error(`Error generating story elements: ${error}`);
      return {
        funFacts: [],
        trivia: [],
        interactivePrompts: [],
      };
    }
  }

  private generateTimeContext(context?: EnrichmentContext): HistoricalEvent['timeContext'] {
    const now = new Date();
    const hour = now.getHours();
    
    return {
      timeOfDay: this.getTimeOfDay(hour),
      season: this.getSeason(now),
      isSpecialDay: this.isSpecialDay(now),
      specialDayName: this.getSpecialDayName(now),
    };
  }

  private getTimeOfDay(hour: number): 'morning' | 'afternoon' | 'evening' | 'night' {
    if (hour >= 5 && hour < 12) return 'morning';
    if (hour >= 12 && hour < 17) return 'afternoon';
    if (hour >= 17 && hour < 21) return 'evening';
    return 'night';
  }

  private getSeason(date: Date): 'spring' | 'summer' | 'fall' | 'winter' {
    const month = date.getMonth();
    if (month >= 2 && month < 5) return 'spring';
    if (month >= 5 && month < 8) return 'summer';
    if (month >= 8 && month < 11) return 'fall';
    return 'winter';
  }

  private async sortEventsByRelevance(
    events: HistoricalEvent[],
    context?: EnrichmentContext
  ): Promise<HistoricalEvent[]> {
    return events.sort((a, b) => {
      let scoreA = 0;
      let scoreB = 0;

      // Factor 1: User interests match
      if (context?.userPreferences?.interests) {
        scoreA += this.calculateInterestScore(a, context.userPreferences.interests);
        scoreB += this.calculateInterestScore(b, context.userPreferences.interests);
      }

      // Factor 2: Time relevance
      if (context?.timeOfDay) {
        scoreA += this.calculateTimeRelevance(a, context);
        scoreB += this.calculateTimeRelevance(b, context);
      }

      // Factor 3: Engagement potential
      scoreA += (a.engagement?.popularity || 0) * 0.3;
      scoreB += (b.engagement?.popularity || 0) * 0.3;

      // Factor 4: Content richness
      scoreA += this.calculateContentRichness(a);
      scoreB += this.calculateContentRichness(b);

      return scoreB - scoreA;
    });
  }

  private calculateInterestScore(event: HistoricalEvent, interests: string[]): number {
    return interests.reduce((score, interest) => {
      if (event.tags.includes(interest)) score += 1;
      if (event.category === interest) score += 2;
      return score;
    }, 0);
  }

  private calculateTimeRelevance(event: HistoricalEvent, context: EnrichmentContext): number {
    if (event.timeContext?.timeOfDay === context.timeOfDay) return 1;
    if (event.timeContext?.season === context.season) return 0.5;
    return 0;
  }

  private calculateContentRichness(event: HistoricalEvent): number {
    let score = 0;
    if (event.media && event.media.length > 0) score += 1;
    if (event.storyElements?.funFacts?.length) score += 0.5;
    if (event.storyElements?.kidFriendlyDescription) score += 0.5;
    if (event.engagement?.familyFriendly) score += 1;
    return score;
  }

  private async generateFunFacts(event: HistoricalEvent): Promise<string[]> {
    // Implement fun facts generation logic
    return [];
  }

  private async generateTrivia(event: HistoricalEvent): Promise<string[]> {
    // Implement trivia generation logic
    return [];
  }

  private async generateInteractivePrompts(
    event: HistoricalEvent,
    context?: EnrichmentContext
  ): Promise<string[]> {
    try {
      const response = await this.api.post('https://api.culturaldata.org/v1/prompts', {
        event_type: event.category,
        time_of_day: context?.timeOfDay,
        age_group: context?.userPreferences?.ageGroup,
      });

      return response.data.prompts || [];
    } catch (error) {
      console.error('Error generating interactive prompts:', error);
      return [];
    }
  }

  private async generateKidFriendlyDescription(event: HistoricalEvent): Promise<string> {
    try {
      // Simplify language and add engaging elements for children
      const response = await this.api.post('https://api.culturaldata.org/v1/kid-friendly', {
        text: event.description,
        age_range: '5-12',
      });

      return response.data.description || event.description;
    } catch (error) {
      console.error('Error generating kid-friendly description:', error);
      return event.description;
    }
  }

  private async fetchTraditionalCulture(location: LocationData): Promise<LocalCulture['traditions']> {
    try {
      const response = await this.api.get('https://api.culturaldata.org/v1/traditions', {
        params: {
          api_key: this.CULTURAL_API_KEY,
          lat: location.latitude,
          lon: location.longitude,
        }
      });

      return response.data.traditions.map((tradition: any) => ({
        name: tradition.name,
        description: tradition.description,
        period: tradition.period,
        significance: tradition.significance,
        storyElements: {
          origin: tradition.origin,
          modernPractice: tradition.modern_practice,
          familyActivities: tradition.family_activities || [],
          funFacts: tradition.fun_facts || [],
        },
      }));
    } catch (error) {
      console.error('Error fetching traditional culture:', error);
      return [];
    }
  }

  private async fetchLocalCuisine(location: LocationData): Promise<LocalCulture['cuisine']> {
    try {
      const response = await this.api.get('https://api.culturaldata.org/v1/cuisine', {
        params: {
          api_key: this.CULTURAL_API_KEY,
          lat: location.latitude,
          lon: location.longitude,
        }
      });

      return response.data.cuisine.map((dish: any) => ({
        name: dish.name,
        description: dish.description,
        ingredients: dish.ingredients,
        origin: dish.origin,
        storyElements: {
          history: dish.history,
          preparation: dish.preparation,
          familyRecipe: dish.family_recipe,
          tastingNotes: dish.tasting_notes || [],
          kidFriendly: dish.kid_friendly || false,
        },
      }));
    } catch (error) {
      console.error('Error fetching local cuisine:', error);
      return [];
    }
  }

  private async fetchLocalMusic(location: LocationData): Promise<LocalCulture['music']> {
    try {
      const response = await this.api.get('https://api.culturaldata.org/v1/music', {
        params: {
          api_key: this.CULTURAL_API_KEY,
          lat: location.latitude,
          lon: location.longitude,
        }
      });

      return response.data.music.map((genre: any) => ({
        genre: genre.name,
        description: genre.description,
        notable_artists: genre.artists,
        period: genre.period,
        storyElements: {
          culturalImpact: genre.cultural_impact,
          danceStyles: genre.dance_styles || [],
          instruments: genre.instruments || [],
          learningResources: genre.learning_resources || [],
        },
      }));
    } catch (error) {
      console.error('Error fetching local music:', error);
      return [];
    }
  }

  private async fetchDemographics(location: LocationData): Promise<LocalCulture['demographics']> {
    try {
      const response = await this.api.get('https://api.culturaldata.org/v1/demographics', {
        params: {
          api_key: this.CULTURAL_API_KEY,
          lat: location.latitude,
          lon: location.longitude,
        }
      });

      const data = response.data.demographics;
      return {
        languages: data.languages || [],
        ethnicities: data.ethnicities || [],
        religions: data.religions || [],
        culturalStories: data.stories?.map((story: any) => ({
          title: story.title,
          narrative: story.narrative,
          significance: story.significance,
        })) || [],
      };
    } catch (error) {
      console.error('Error fetching demographics:', error);
      return {
        languages: [],
        ethnicities: [],
        religions: [],
        culturalStories: [],
      };
    }
  }

  private async fetchLocalFestivals(location: LocationData): Promise<LocalCulture['festivals']> {
    // Implement festivals fetching
    return [];
  }

  private combineHistoricalEvents(...eventSets: HistoricalEvent[][]): HistoricalEvent[] {
    const eventMap = new Map<string, HistoricalEvent>();

    eventSets.flat().forEach((event) => {
      const key = `${event.date}-${event.description}`;
      if (!eventMap.has(key) || !eventMap.get(key)?.verified) {
        eventMap.set(key, event);
      }
    });

    return Array.from(eventMap.values());
  }

  private async fetchEngagementMetrics(event: HistoricalEvent): Promise<HistoricalEvent['engagement']> {
    try {
      const response = await this.api.get('https://api.culturaldata.org/v1/metrics', {
        params: {
          event_id: event.date + '-' + event.description,
        }
      });

      const metrics = response.data.metrics;
      return {
        popularity: metrics.popularity || 0,
        userRatings: metrics.average_rating || 0,
        familyFriendly: metrics.family_friendly || false,
        recommendedAge: metrics.recommended_age,
        visitDuration: metrics.visit_duration,
      };
    } catch (error) {
      console.error('Error fetching engagement metrics:', error);
      return {
        popularity: 0,
        userRatings: 0,
        familyFriendly: false,
      };
    }
  }

  private async enhanceEventMedia(media: HistoricalEvent['media'] = []): Promise<HistoricalEvent['media']> {
    try {
      return await Promise.all(media.map(async (item) => {
        // Enhance media quality and add additional metadata
        const enhancedUrl = await this.getHighQualityMediaUrl(item.url);
        const enrichedCaption = await this.enrichMediaCaption(item.caption);
        
        return {
          ...item,
          url: enhancedUrl,
          caption: enrichedCaption,
        };
      }));
    } catch (error) {
      console.error('Error enhancing media:', error);
      return media;
    }
  }

  private async getHighQualityMediaUrl(url: string): Promise<string> {
    // Implement logic to get high-quality version of media
    return url;
  }

  private async enrichMediaCaption(caption: string): Promise<string> {
    // Implement logic to enhance caption with additional context
    return caption;
  }

  private isSpecialDay(date: Date): boolean {
    const specialDays = this.getSpecialDays();
    const dateString = date.toISOString().split('T')[0];
    return specialDays.has(dateString);
  }

  private getSpecialDayName(date: Date): string | undefined {
    const specialDays = this.getSpecialDays();
    const dateString = date.toISOString().split('T')[0];
    return specialDays.get(dateString);
  }

  private getSpecialDays(): Map<string, string> {
    // Return a map of special dates and their names
    const specialDays = new Map<string, string>();
    
    // Add major holidays and cultural celebrations
    specialDays.set('2024-01-01', 'New Year\'s Day');
    specialDays.set('2024-02-14', 'Valentine\'s Day');
    specialDays.set('2024-07-04', 'Independence Day');
    specialDays.set('2024-10-31', 'Halloween');
    specialDays.set('2024-12-25', 'Christmas');
    
    return specialDays;
  }
}

export const historicalService = new HistoricalService(); 