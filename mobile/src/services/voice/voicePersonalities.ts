import { Voice, SpeakingStyle } from './voiceTypes';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { logger } from '@/services/logger';
export interface VoicePersonality {
  id: string;
  name: string;
  description: string;
  voice: Voice;
  defaultStyle: SpeakingStyle;
  contextualStyles: {
    storytelling: SpeakingStyle;
    navigation: SpeakingStyle;
    factual: SpeakingStyle;
    emergency: SpeakingStyle;
  };
  traits: {
    humor: number;  // 0-1
    formality: number;  // 0-1
    enthusiasm: number;  // 0-1
    empathy: number;  // 0-1
  };
  catchphrases: string[];
  transitionPhrases: {
    resumeStory: string[];
    changeLocation: string[];
    pointOfInterest: string[];
    userQuestion: string[];
  };
}

export interface GuideTheme {
  id: string;
  name: string;
  description: string;
  personality: VoicePersonality;
  backgroundMusic: {
    default: string;
    scenic: string;
    urban: string;
    historical: string;
  };
  soundEffects: {
    transition: string;
    pointOfInterest: string;
    achievement: string;
    alert: string;
  };
  visualTheme: {
    primaryColor: string;
    secondaryColor: string;
    accentColor: string;
    iconSet: string;
  };
}

// Default voice personalities
export const DEFAULT_PERSONALITIES: VoicePersonality[] = [
  {
    id: 'adventurous-explorer',
    name: 'Adventure Guide',
    description: 'An enthusiastic explorer who brings excitement to every discovery',
    voice: {
      id: 'en-US-DavisNeural',
      name: 'Davis',
      gender: 'male',
      language: 'en',
      locale: 'en-US',
      neural: true,
      capabilities: ['emotion', 'style', 'rate', 'pitch'],
    },
    defaultStyle: {
      type: 'conversational',
      intensity: 0.8,
      emotion: {
        type: 'excitement',
        level: 0.7,
      },
    },
    contextualStyles: {
      storytelling: {
        type: 'narrative',
        intensity: 0.9,
        emotion: {
          type: 'excitement',
          level: 0.8,
        },
      },
      navigation: {
        type: 'conversational',
        intensity: 0.7,
        emotion: {
          type: 'happiness',
          level: 0.6,
        },
      },
      factual: {
        type: 'newscast',
        intensity: 0.5,
        emotion: {
          type: 'surprise',
          level: 0.4,
        },
      },
      emergency: {
        type: 'conversational',
        intensity: 0.9,
        emotion: {
          type: 'fear',
          level: 0.7,
        },
      },
    },
    traits: {
      humor: 0.7,
      formality: 0.4,
      enthusiasm: 0.9,
      empathy: 0.6,
    },
    catchphrases: [
      "Let's explore this amazing place!",
      "Adventure awaits around every corner!",
      "Time for another exciting discovery!",
    ],
    transitionPhrases: {
      resumeStory: [
        "Now, where were we on our adventure? Ah yes...",
        "Back to our exciting journey...",
        "Let's continue our exploration...",
      ],
      changeLocation: [
        "Look what we have here!",
        "This place has a fascinating story...",
        "You won't believe what's coming up next!",
      ],
      pointOfInterest: [
        "Hold on, you've got to see this!",
        "This is something special...",
        "Here's a hidden gem for you!",
      ],
      userQuestion: [
        "Great question, fellow explorer!",
        "Ah, your curiosity matches mine!",
        "Let me share what I know about that...",
      ],
    },
  },
  {
    id: 'historical-scholar',
    name: 'History Professor',
    description: 'A knowledgeable historian who brings the past to life',
    voice: {
      id: 'en-US-GuyNeural',
      name: 'Guy',
      gender: 'male',
      language: 'en',
      locale: 'en-US',
      neural: true,
      capabilities: ['emotion', 'style', 'rate', 'pitch'],
    },
    defaultStyle: {
      type: 'narrative',
      intensity: 0.6,
      emotion: {
        type: 'happiness',
        level: 0.4,
      },
    },
    contextualStyles: {
      storytelling: {
        type: 'narrative',
        intensity: 0.7,
        emotion: {
          type: 'happiness',
          level: 0.5,
        },
      },
      navigation: {
        type: 'conversational',
        intensity: 0.5,
        emotion: {
          type: 'happiness',
          level: 0.3,
        },
      },
      factual: {
        type: 'newscast',
        intensity: 0.8,
        emotion: {
          type: 'surprise',
          level: 0.3,
        },
      },
      emergency: {
        type: 'conversational',
        intensity: 0.7,
        emotion: {
          type: 'fear',
          level: 0.5,
        },
      },
    },
    traits: {
      humor: 0.4,
      formality: 0.8,
      enthusiasm: 0.6,
      empathy: 0.7,
    },
    catchphrases: [
      "As history tells us...",
      "This reminds me of a fascinating historical event...",
      "Let's examine this through the lens of history...",
    ],
    transitionPhrases: {
      resumeStory: [
        "Returning to our historical narrative...",
        "As we were discussing in our historical context...",
        "Let's continue our journey through time...",
      ],
      changeLocation: [
        "This location has quite a story to tell...",
        "The historical significance of this place...",
        "If these walls could talk...",
      ],
      pointOfInterest: [
        "This site holds particular historical importance...",
        "Let me share an interesting historical fact...",
        "This reminds me of a remarkable event...",
      ],
      userQuestion: [
        "An excellent inquiry into our historical context...",
        "That's a fascinating historical question...",
        "Let me provide some historical perspective...",
      ],
    },
  },
];

// Default guide themes
export const DEFAULT_THEMES: GuideTheme[] = [
  {
    id: 'adventure-explorer',
    name: 'Adventure Explorer',
    description: 'An exciting theme for the adventurous traveler',
    personality: DEFAULT_PERSONALITIES[0],
    backgroundMusic: {
      default: 'adventure-theme.mp3',
      scenic: 'nature-exploration.mp3',
      urban: 'city-adventure.mp3',
      historical: 'discovery-theme.mp3',
    },
    soundEffects: {
      transition: 'whoosh.mp3',
      pointOfInterest: 'discovery.mp3',
      achievement: 'triumph.mp3',
      alert: 'attention.mp3',
    },
    visualTheme: {
      primaryColor: '#2E7D32',
      secondaryColor: '#1B5E20',
      accentColor: '#FFD700',
      iconSet: 'adventure',
    },
  },
  {
    id: 'historical-journey',
    name: 'Historical Journey',
    description: 'A sophisticated theme for history enthusiasts',
    personality: DEFAULT_PERSONALITIES[1],
    backgroundMusic: {
      default: 'classical-theme.mp3',
      scenic: 'ambient-classical.mp3',
      urban: 'city-classical.mp3',
      historical: 'period-music.mp3',
    },
    soundEffects: {
      transition: 'page-turn.mp3',
      pointOfInterest: 'bell.mp3',
      achievement: 'fanfare.mp3',
      alert: 'gong.mp3',
    },
    visualTheme: {
      primaryColor: '#795548',
      secondaryColor: '#4E342E',
      accentColor: '#D4AF37',
      iconSet: 'historical',
    },
  },
];

class VoicePersonalityManager {
  private customPersonalities: VoicePersonality[] = [];
  private customThemes: GuideTheme[] = [];

  async initialize(): Promise<void> {
    await this.loadCustomPersonalities();
    await this.loadCustomThemes();
  }

  async createCustomPersonality(personality: VoicePersonality): Promise<void> {
    this.customPersonalities.push(personality);
    await this.saveCustomPersonalities();
  }

  async createCustomTheme(theme: GuideTheme): Promise<void> {
    this.customThemes.push(theme);
    await this.saveCustomThemes();
  }

  getAllPersonalities(): VoicePersonality[] {
    return [...DEFAULT_PERSONALITIES, ...this.customPersonalities];
  }

  getAllThemes(): GuideTheme[] {
    return [...DEFAULT_THEMES, ...this.customThemes];
  }

  getPersonalityById(id: string): VoicePersonality | undefined {
    return this.getAllPersonalities().find(p => p.id === id);
  }

  getThemeById(id: string): GuideTheme | undefined {
    return this.getAllThemes().find(t => t.id === id);
  }

  private async loadCustomPersonalities(): Promise<void> {
    try {
      const stored = await AsyncStorage.getItem('@custom_personalities');
      if (stored) {
        this.customPersonalities = JSON.parse(stored);
      }
    } catch (error) {
      logger.error('Failed to load custom personalities:', error);
    }
  }

  private async saveCustomPersonalities(): Promise<void> {
    try {
      await AsyncStorage.setItem(
        '@custom_personalities',
        JSON.stringify(this.customPersonalities)
      );
    } catch (error) {
      logger.error('Failed to save custom personalities:', error);
    }
  }

  private async loadCustomThemes(): Promise<void> {
    try {
      const stored = await AsyncStorage.getItem('@custom_themes');
      if (stored) {
        this.customThemes = JSON.parse(stored);
      }
    } catch (error) {
      logger.error('Failed to load custom themes:', error);
    }
  }

  private async saveCustomThemes(): Promise<void> {
    try {
      await AsyncStorage.setItem(
        '@custom_themes',
        JSON.stringify(this.customThemes)
      );
    } catch (error) {
      logger.error('Failed to save custom themes:', error);
    }
  }
}

export default new VoicePersonalityManager(); 