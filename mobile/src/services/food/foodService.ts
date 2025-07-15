import { APIClient } from '@utils/apiUtils';
import { Location } from '@/types/location';
import { Media } from '@/types/cultural';
import { memoizeAsync } from '@utils/cache';

export interface Restaurant {
  id: string;
  name: string;
  description?: string;
  location: Location;
  cuisine: string[];
  priceRange: 1 | 2 | 3 | 4;  // $ to $$$$
  rating: number;
  reviews: number;
  hours: {
    openNow: boolean;
    periods: BusinessHours[];
  };
  photos: string[];
  menu?: Menu;
  specialties: string[];
  localDishes: string[];
  reservationUrl?: string;
  waitTime?: number;  // in minutes
  delivery: boolean;
  takeout: boolean;
  popularTimes?: PopularTimes[];
  localContext?: string;
  culturalSignificance?: number;  // 0-100
  sustainabilityScore?: number;  // 0-100
}

export interface BusinessHours {
  day: number;  // 0-6 (Sunday-Saturday)
  open: string;  // "HHMM" format
  close: string;  // "HHMM" format
}

export interface Menu {
  sections: MenuSection[];
  lastUpdated: Date;
  currency: string;
  specialMenus?: {
    vegetarian?: boolean;
    vegan?: boolean;
    glutenFree?: boolean;
    halal?: boolean;
    kosher?: boolean;
  };
}

export interface MenuSection {
  name: string;
  description?: string;
  items: MenuItem[];
}

export interface MenuItem {
  id: string;
  name: string;
  description?: string;
  price: number;
  photos?: string[];
  ingredients?: string[];
  allergens?: string[];
  nutritionalInfo?: NutritionalInfo;
  spicyLevel?: number;  // 0-5
  popular?: boolean;
  localSpecialty?: boolean;
}

export interface NutritionalInfo {
  calories: number;
  protein: number;
  carbohydrates: number;
  fat: number;
  fiber?: number;
  sodium?: number;
}

export interface PopularTimes {
  day: number;  // 0-6 (Sunday-Saturday)
  hours: Array<{
    hour: number;  // 0-23
    percentage: number;  // 0-100
  }>;
}

export interface FoodStory {
  id: string;
  title: string;
  content: string;
  cuisine: string[];
  dishes: string[];
  historicalPeriod?: string;
  culturalContext: string;
  location: Location;
  media?: Media[];
  recipes?: Recipe[];
  restaurants?: string[];  // Restaurant IDs
  relevanceScore?: number;
}

export interface Recipe {
  id: string;
  name: string;
  description: string;
  cuisine: string[];
  difficulty: 'easy' | 'medium' | 'hard';
  prepTime: number;  // in minutes
  cookTime: number;  // in minutes
  servings: number;
  ingredients: Ingredient[];
  instructions: string[];
  nutritionalInfo: NutritionalInfo;
  photos?: string[];
  video?: string;
  tips?: string[];
  variations?: string[];
  localContext?: string;
  culturalSignificance?: string;
  sustainabilityScore?: number;  // 0-100
}

export interface Ingredient {
  name: string;
  amount: number;
  unit: string;
  notes?: string;
  substitutes?: string[];
}

class FoodService {
  private readonly yelpClient: APIClient;
  private readonly spoonacularClient: APIClient;
  private readonly openTableClient: APIClient;
  private readonly tastyClient: APIClient;

  constructor() {
    this.yelpClient = new APIClient({
      baseURL: 'https://api.yelp.com/v3',
      timeout: 10000,
      rateLimit: {
        maxRequests: 100,
        windowMs: 60000,
      },
    });

    this.spoonacularClient = new APIClient({
      baseURL: 'https://api.spoonacular.com/recipes',
      timeout: 8000,
      rateLimit: {
        maxRequests: 50,
        windowMs: 60000,
      },
    });

    this.openTableClient = new APIClient({
      baseURL: 'https://platform.opentable.com/v2',
      timeout: 8000,
      rateLimit: {
        maxRequests: 60,
        windowMs: 60000,
      },
    });

    this.tastyClient = new APIClient({
      baseURL: 'https://tasty.p.rapidapi.com',
      timeout: 8000,
      rateLimit: {
        maxRequests: 50,
        windowMs: 60000,
      },
    });
  }

  getLocalFood = memoizeAsync(
    async (location: Location): Promise<Restaurant[]> => {
      const [yelpRestaurants, openTableRestaurants] = await Promise.all([
        this.getYelpRestaurants(location),
        this.getOpenTableRestaurants(location),
      ]);

      return this.mergeAndRankRestaurants(yelpRestaurants, openTableRestaurants);
    },
    100,  // Cache size
    900   // TTL: 15 minutes
  );

  getFoodHistory = memoizeAsync(
    async (location: Location): Promise<FoodStory[]> => {
      const stories = await this.getTastyStories(location);
      return this.enrichStoriesWithContext(stories, location);
    },
    50,   // Cache size
    3600  // TTL: 1 hour
  );

  getLocalRecipes = memoizeAsync(
    async (location: Location): Promise<Recipe[]> => {
      const [spoonacularRecipes, tastyRecipes] = await Promise.all([
        this.getSpoonacularRecipes(location),
        this.getTastyRecipes(location),
      ]);

      return this.mergeAndRankRecipes(spoonacularRecipes, tastyRecipes);
    },
    100,  // Cache size
    3600  // TTL: 1 hour
  );

  private async getYelpRestaurants(location: Location): Promise<Restaurant[]> {
    // Implementation for fetching Yelp restaurants
    return [];
  }

  private async getOpenTableRestaurants(location: Location): Promise<Restaurant[]> {
    // Implementation for fetching OpenTable restaurants
    return [];
  }

  private async getTastyStories(location: Location): Promise<FoodStory[]> {
    // Implementation for fetching Tasty food stories
    return [];
  }

  private async getSpoonacularRecipes(location: Location): Promise<Recipe[]> {
    // Implementation for fetching Spoonacular recipes
    return [];
  }

  private async getTastyRecipes(location: Location): Promise<Recipe[]> {
    // Implementation for fetching Tasty recipes
    return [];
  }

  private mergeAndRankRestaurants(
    yelpRestaurants: Restaurant[],
    openTableRestaurants: Restaurant[]
  ): Restaurant[] {
    // Merge and rank restaurants based on:
    // - Distance from current location
    // - Ratings and reviews
    // - Cultural significance
    // - Local specialties
    return [];
  }

  private async enrichStoriesWithContext(
    stories: FoodStory[],
    location: Location
  ): Promise<FoodStory[]> {
    // Add local context and cultural significance to food stories:
    // - Historical connections
    // - Cultural traditions
    // - Local ingredients and techniques
    return [];
  }

  private mergeAndRankRecipes(
    spoonacularRecipes: Recipe[],
    tastyRecipes: Recipe[]
  ): Recipe[] {
    // Merge and rank recipes based on:
    // - Local relevance
    // - Seasonal ingredients
    // - Cultural significance
    // - User preferences
    return [];
  }
}

export default new FoodService(); 