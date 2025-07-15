/**
 * @jest-environment jsdom
 */

import axios from 'axios';
import { historicalService } from '../historicalService';
import { LocationData } from '../locationService';
import type { Mock } from 'jest';

// Extend global Jest types
declare global {
  namespace jest {
    interface Matchers<R> {
      toHaveProperty: (property: string) => R;
    }
  }
}

// Mock axios
const mockAxios = {
  create: jest.fn(() => ({
    get: jest.fn(),
    post: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
  })),
};

jest.mock('axios', () => mockAxios);

describe('HistoricalService', () => {
  const mockLocation: LocationData = {
    latitude: 40.7128,
    longitude: -74.0060,
  };

  const mockContext = {
    timeOfDay: 'afternoon' as const,
    season: 'summer' as const,
    weather: 'sunny',
    userPreferences: {
      interests: ['history', 'culture'],
      previousVisits: 2,
      favoriteTypes: ['landmarks', 'museums'],
      ageGroup: 'family',
    },
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Story Elements Generation', () => {
    const mockEvent = {
      date: '2024-01-01',
      description: 'Historic landmark description',
      significance: 'Major cultural site',
      verified: true,
      source: 'Cultural API',
      category: 'landmark',
      tags: ['history', 'architecture'],
    };

    test('generates kid-friendly descriptions', async () => {
      const mockResponse = {
        data: {
          description: 'A fun and simple explanation for kids!',
        },
      };

      (axios.create().post as jest.Mock).mockResolvedValueOnce(mockResponse);

      const result = await historicalService['generateKidFriendlyDescription'](mockEvent);
      
      expect(result).toBe('A fun and simple explanation for kids!');
      expect(axios.create().post).toHaveBeenCalledWith(
        'https://api.culturaldata.org/v1/kid-friendly',
        expect.objectContaining({
          text: mockEvent.description,
          age_range: '5-12',
        })
      );
    });

    test('generates interactive prompts based on context', async () => {
      const mockPrompts = {
        data: {
          prompts: [
            'Can you spot the architectural features?',
            'What do you think happened here?',
            'How has this place changed over time?',
          ],
        },
      };

      (axios.create().post as jest.Mock).mockResolvedValueOnce(mockPrompts);

      const result = await historicalService['generateInteractivePrompts'](mockEvent, mockContext);

      expect(result).toHaveLength(3);
      expect(result).toContain('Can you spot the architectural features?');
      expect(axios.create().post).toHaveBeenCalledWith(
        'https://api.culturaldata.org/v1/prompts',
        expect.objectContaining({
          event_type: mockEvent.category,
          time_of_day: mockContext.timeOfDay,
          age_group: mockContext.userPreferences.ageGroup,
        })
      );
    });

    test('enriches events with time context', () => {
      const timeContext = historicalService['generateTimeContext'](mockContext);

      expect(timeContext).toHaveProperty('timeOfDay');
      expect(timeContext).toHaveProperty('season');
      expect(timeContext).toHaveProperty('isSpecialDay');
    });
  });

  describe('Content Personalization', () => {
    const mockEvents = [
      {
        date: '2024-01-01',
        description: 'Event 1',
        category: 'history',
        tags: ['history'],
        engagement: { popularity: 0.8, familyFriendly: true },
        timeContext: { timeOfDay: 'afternoon', season: 'summer' },
      },
      {
        date: '2024-01-02',
        description: 'Event 2',
        category: 'culture',
        tags: ['culture'],
        engagement: { popularity: 0.6, familyFriendly: false },
        timeContext: { timeOfDay: 'morning', season: 'winter' },
      },
    ];

    test('calculates interest scores correctly', () => {
      const score1 = historicalService['calculateInterestScore'](
        mockEvents[0] as any,
        mockContext.userPreferences.interests
      );
      const score2 = historicalService['calculateInterestScore'](
        mockEvents[1] as any,
        mockContext.userPreferences.interests
      );

      expect(score1).toBeGreaterThan(0);
      expect(score2).toBeGreaterThan(0);
      expect(score1).not.toBe(score2);
    });

    test('calculates time relevance correctly', () => {
      const score1 = historicalService['calculateTimeRelevance'](
        mockEvents[0] as any,
        mockContext
      );
      const score2 = historicalService['calculateTimeRelevance'](
        mockEvents[1] as any,
        mockContext
      );

      expect(score1).toBe(1.5); // Matches both time and season
      expect(score2).toBe(0); // Matches neither
    });

    test('calculates content richness correctly', () => {
      const mockRichEvent = {
        ...mockEvents[0],
        media: [{ type: 'image', url: 'test.jpg', caption: 'test' }],
        storyElements: {
          funFacts: ['fact1', 'fact2'],
          kidFriendlyDescription: 'kid friendly',
        },
      };

      const score = historicalService['calculateContentRichness'](mockRichEvent as any);
      expect(score).toBeGreaterThan(1);
    });

    test('sorts events by relevance', async () => {
      const sortedEvents = await historicalService['sortEventsByRelevance'](
        mockEvents as any,
        mockContext
      );

      expect(sortedEvents[0].category).toBe('history');
      expect(sortedEvents[1].category).toBe('culture');
    });
  });

  describe('Media Enhancement', () => {
    const mockMedia = [
      {
        type: 'image' as const,
        url: 'test.jpg',
        caption: 'Original caption',
      },
    ];

    test('enhances media quality and captions', async () => {
      const enhancedMedia = await historicalService['enhanceEventMedia'](mockMedia);

      expect(enhancedMedia[0]).toHaveProperty('url');
      expect(enhancedMedia[0]).toHaveProperty('caption');
      expect(enhancedMedia[0].url).toBeDefined();
      expect(enhancedMedia[0].caption).toBeDefined();
    });
  });

  describe('Special Days Detection', () => {
    test('identifies special days correctly', () => {
      const christmasDate = new Date('2024-12-25');
      const regularDate = new Date('2024-03-15');

      expect(historicalService['isSpecialDay'](christmasDate)).toBe(true);
      expect(historicalService['isSpecialDay'](regularDate)).toBe(false);
    });

    test('returns correct special day names', () => {
      const christmasDate = new Date('2024-12-25');
      const regularDate = new Date('2024-03-15');

      expect(historicalService['getSpecialDayName'](christmasDate)).toBe('Christmas');
      expect(historicalService['getSpecialDayName'](regularDate)).toBeUndefined();
    });
  });

  describe('Error Handling', () => {
    test('handles API errors gracefully in story generation', async () => {
      (axios.create().post as jest.Mock).mockRejectedValueOnce(new Error('API Error'));

      const result = await historicalService['generateKidFriendlyDescription'](
        { description: 'test' } as any
      );

      expect(result).toBe('test'); // Returns original description on error
    });

    test('handles missing context gracefully', () => {
      const timeContext = historicalService['generateTimeContext'](undefined);

      expect(timeContext).toHaveProperty('timeOfDay');
      expect(timeContext).toHaveProperty('season');
      expect(timeContext).toHaveProperty('isSpecialDay');
    });
  });
}); 