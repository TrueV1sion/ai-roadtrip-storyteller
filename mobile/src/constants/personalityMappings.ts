/**
 * Personality ID Mappings
 * Maps frontend personality IDs to backend PersonalityType enum values
 */

export const PERSONALITY_MAPPINGS = {
  // Frontend ID -> Backend ID
  'navigator': 'friendly_guide',
  'friendly-guide': 'friendly_guide',
  'educational-expert': 'historian',
  'adventurer': 'adventurer',
  'comedian': 'comedian',
  'local-expert': 'local_expert',
  'mickey-mouse': 'adventurer', // Using adventurer for Disney character
  'rock-dj': 'west_coast_cool', // Using west coast for rock personality
  'santa-claus': 'santa',
  'halloween-narrator': 'halloween_narrator',
  'cupid': 'cupid',
  'leprechaun': 'leprechaun',
  'patriot': 'patriot',
  'harvest-guide': 'harvest_guide',
  'inspirational': 'inspirational',
  'southern-charm': 'southern_charm',
  'new-england-scholar': 'new_england_scholar',
  'midwest-neighbor': 'midwest_neighbor',
  'west-coast-cool': 'west_coast_cool',
  'mountain-sage': 'mountain_sage',
  'texas-ranger': 'texas_ranger',
  'jazz-storyteller': 'jazz_storyteller',
  'beach-vibes': 'beach_vibes',
} as const;

export type FrontendPersonalityId = keyof typeof PERSONALITY_MAPPINGS;
export type BackendPersonalityId = typeof PERSONALITY_MAPPINGS[FrontendPersonalityId];

/**
 * Convert frontend personality ID to backend format
 */
export function toBackendPersonalityId(frontendId: string): string {
  return PERSONALITY_MAPPINGS[frontendId as FrontendPersonalityId] || 'friendly_guide';
}

/**
 * Personality display names and descriptions
 */
export const PERSONALITY_INFO = {
  'navigator': {
    name: 'Professional Navigator',
    description: 'Clear, professional guidance',
    category: 'core',
  },
  'friendly-guide': {
    name: 'Friendly Guide',
    description: 'Warm and conversational',
    category: 'core',
  },
  'educational-expert': {
    name: 'Educational Expert',
    description: 'Informative and engaging',
    category: 'core',
  },
  'adventurer': {
    name: 'Adventure Explorer',
    description: 'High-energy outdoor enthusiast',
    category: 'core',
  },
  'comedian': {
    name: 'Comedy Host',
    description: 'Family-friendly jokes and puns',
    category: 'core',
  },
  'local-expert': {
    name: 'Local Expert',
    description: 'Insider tips and regional knowledge',
    category: 'core',
  },
  'mickey-mouse': {
    name: 'Mickey Mouse',
    description: 'Oh boy! Disney magic awaits!',
    category: 'event',
  },
  'rock-dj': {
    name: 'Rock DJ',
    description: 'High energy concert vibes',
    category: 'event',
  },
  'santa-claus': {
    name: 'Santa Claus',
    description: 'Ho ho ho! Holiday cheer',
    category: 'seasonal',
  },
  'halloween-narrator': {
    name: 'Halloween Narrator',
    description: 'Spooky tales await...',
    category: 'seasonal',
  },
  'cupid': {
    name: 'Cupid',
    description: 'Love is in the air!',
    category: 'seasonal',
  },
  'leprechaun': {
    name: 'Lucky Leprechaun',
    description: 'Top of the morning to ye!',
    category: 'seasonal',
  },
  'patriot': {
    name: 'Patriotic Host',
    description: 'Stars, stripes, and stories',
    category: 'seasonal',
  },
  'harvest-guide': {
    name: 'Harvest Guide',
    description: 'Thanksgiving warmth and gratitude',
    category: 'seasonal',
  },
  'inspirational': {
    name: 'Motivational Coach',
    description: 'Uplifting and empowering',
    category: 'specialty',
  },
  'southern-charm': {
    name: 'Southern Charm',
    description: 'Sweet as sweet tea',
    category: 'regional',
  },
  'new-england-scholar': {
    name: 'New England Scholar',
    description: 'Refined and intellectual',
    category: 'regional',
  },
  'midwest-neighbor': {
    name: 'Midwest Neighbor',
    description: 'Friendly and down-to-earth',
    category: 'regional',
  },
  'west-coast-cool': {
    name: 'West Coast Cool',
    description: 'Laid-back California vibes',
    category: 'regional',
  },
  'mountain-sage': {
    name: 'Mountain Sage',
    description: 'Wise tales from the peaks',
    category: 'regional',
  },
  'texas-ranger': {
    name: 'Texas Ranger',
    description: 'Big stories from the Lone Star State',
    category: 'regional',
  },
  'jazz-storyteller': {
    name: 'Jazz Storyteller',
    description: 'Smooth tales with rhythm',
    category: 'regional',
  },
  'beach-vibes': {
    name: 'Beach Vibes',
    description: 'Surf, sun, and stories',
    category: 'regional',
  },
} as const;