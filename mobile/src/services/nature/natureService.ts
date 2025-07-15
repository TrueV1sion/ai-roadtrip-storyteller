import { APIClient } from '@utils/apiUtils';
import { Location } from '@/types/location';
import { Media } from '@/types/cultural';
import { memoizeAsync } from '@utils/cache';

export interface Wildlife {
  id: string;
  commonName: string;
  scientificName: string;
  taxonomy: {
    kingdom: string;
    phylum: string;
    class: string;
    order: string;
    family: string;
    genus: string;
    species: string;
  };
  description: string;
  habitat: string[];
  behavior: string;
  diet: string[];
  conservation: {
    status: string;
    threats: string[];
    population: string;
  };
  seasonality: {
    active: string[];
    breeding: string[];
    migration?: string[];
  };
  photos: Media[];
  sounds?: Media[];
  observations: number;
  lastSeen?: Date;
  probability: number;  // 0-1
  dangerLevel?: number;  // 0-5
  interactionGuidelines?: string;
}

export interface Plant {
  id: string;
  commonName: string;
  scientificName: string;
  taxonomy: {
    kingdom: string;
    phylum: string;
    class: string;
    order: string;
    family: string;
    genus: string;
    species: string;
  };
  description: string;
  nativeRange: string[];
  habitat: string[];
  characteristics: {
    type: string;
    height: string;
    spread: string;
    leafType: string;
    flowerColor?: string[];
    floweringSeason?: string[];
    fruitType?: string;
  };
  growthRequirements: {
    sunlight: string[];
    soil: string[];
    water: string;
    temperature: string;
  };
  uses: {
    medicinal?: string[];
    culinary?: string[];
    cultural?: string[];
  };
  photos: Media[];
  edible: boolean;
  poisonous: boolean;
  invasive: boolean;
  endangered: boolean;
  culturalSignificance?: string;
  probability: number;  // 0-1
}

export interface GeologicalInfo {
  id: string;
  name: string;
  type: string[];
  age: {
    period: string;
    epoch: string;
    yearsAgo: number;
  };
  description: string;
  formation: {
    type: string;
    process: string;
    materials: string[];
  };
  features: Array<{
    name: string;
    description: string;
    significance: string;
  }>;
  minerals: Array<{
    name: string;
    formula: string;
    color: string[];
    abundance: string;
  }>;
  history: {
    geological: string;
    human: string;
  };
  hazards?: Array<{
    type: string;
    risk: string;
    mitigation: string;
  }>;
  photos: Media[];
  culturalSignificance?: string;
  scientificSignificance?: string;
  educationalValue?: string;
}

class NatureService {
  private readonly iNaturalistClient: APIClient;
  private readonly plantIdClient: APIClient;
  private readonly usgsClient: APIClient;
  private readonly darkSkyClient: APIClient;

  constructor() {
    this.iNaturalistClient = new APIClient({
      baseURL: 'https://api.inaturalist.org/v1',
      timeout: 10000,
      rateLimit: {
        maxRequests: 100,
        windowMs: 60000,
      },
    });

    this.plantIdClient = new APIClient({
      baseURL: 'https://api.plant.id/v2',
      timeout: 8000,
      rateLimit: {
        maxRequests: 50,
        windowMs: 60000,
      },
    });

    this.usgsClient = new APIClient({
      baseURL: 'https://earthquake.usgs.gov/fdsnws',
      timeout: 10000,
      rateLimit: {
        maxRequests: 100,
        windowMs: 60000,
      },
    });

    this.darkSkyClient = new APIClient({
      baseURL: 'https://api.darksky.net/forecast',
      timeout: 8000,
      rateLimit: {
        maxRequests: 1000,
        windowMs: 86400000,  // 24 hours
      },
    });
  }

  getLocalWildlife = memoizeAsync(
    async (location: Location): Promise<Wildlife[]> => {
      const observations = await this.getINaturalistObservations(location);
      return this.enrichWildlifeData(observations);
    },
    100,  // Cache size
    1800  // TTL: 30 minutes
  );

  identifyPlants = memoizeAsync(
    async (image: string): Promise<Plant[]> => {
      const identifications = await this.getPlantIdentifications(image);
      return this.enrichPlantData(identifications);
    },
    50,   // Cache size
    3600  // TTL: 1 hour
  );

  getGeologicalInfo = memoizeAsync(
    async (location: Location): Promise<GeologicalInfo[]> => {
      const [geology, seismic] = await Promise.all([
        this.getUSGSGeology(location),
        this.getUSGSSeismic(location),
      ]);

      return this.mergeGeologicalData(geology, seismic);
    },
    100,  // Cache size
    86400 // TTL: 24 hours
  );

  private async getINaturalistObservations(location: Location): Promise<any[]> {
    // Implementation for fetching iNaturalist observations
    return [];
  }

  private async getPlantIdentifications(image: string): Promise<any[]> {
    // Implementation for identifying plants using Plant.id
    return [];
  }

  private async getUSGSGeology(location: Location): Promise<any[]> {
    // Implementation for fetching USGS geological data
    return [];
  }

  private async getUSGSSeismic(location: Location): Promise<any[]> {
    // Implementation for fetching USGS seismic data
    return [];
  }

  private async enrichWildlifeData(observations: any[]): Promise<Wildlife[]> {
    // Add context and details to wildlife observations:
    // - Behavioral patterns
    // - Seasonal information
    // - Conservation status
    // - Local significance
    return [];
  }

  private async enrichPlantData(identifications: any[]): Promise<Plant[]> {
    // Add context and details to plant identifications:
    // - Growth requirements
    // - Uses and significance
    // - Conservation status
    // - Local context
    return [];
  }

  private mergeGeologicalData(
    geology: any[],
    seismic: any[]
  ): GeologicalInfo[] {
    // Merge geological and seismic data:
    // - Formation history
    // - Current conditions
    // - Risk assessment
    // - Educational value
    return [];
  }
}

export default new NatureService(); 