// Voice Command Mapping for Voice-First Navigation

export interface VoiceCommand {
  patterns: string[];
  action: string;
  category: 'navigation' | 'control' | 'query' | 'booking' | 'entertainment' | 'settings';
  requiresConfirmation?: boolean;
  parameters?: string[];
}

export const VOICE_COMMANDS: VoiceCommand[] = [
  // Navigation Commands
  {
    patterns: [
      'navigate to {destination}',
      'take me to {destination}',
      'go to {destination}',
      'directions to {destination}',
      'find route to {destination}'
    ],
    action: 'NAVIGATE_TO',
    category: 'navigation',
    parameters: ['destination']
  },
  {
    patterns: [
      'find gas station',
      'where is the nearest gas station',
      'I need gas',
      'find fuel'
    ],
    action: 'FIND_GAS_STATION',
    category: 'navigation'
  },
  {
    patterns: [
      'find rest stop',
      'where can I rest',
      'find rest area',
      'I need a break'
    ],
    action: 'FIND_REST_STOP',
    category: 'navigation'
  },
  {
    patterns: [
      'alternative routes',
      'show other routes',
      'different route',
      'scenic route',
      'avoid traffic'
    ],
    action: 'SHOW_ALTERNATIVES',
    category: 'navigation'
  },
  {
    patterns: [
      'stop navigation',
      'cancel navigation',
      'end navigation',
      'stop directions'
    ],
    action: 'STOP_NAVIGATION',
    category: 'navigation',
    requiresConfirmation: true
  },

  // Control Commands
  {
    patterns: [
      'pause',
      'pause story',
      'stop talking',
      'be quiet'
    ],
    action: 'PAUSE_NARRATION',
    category: 'control'
  },
  {
    patterns: [
      'resume',
      'continue',
      'continue story',
      'keep going'
    ],
    action: 'RESUME_NARRATION',
    category: 'control'
  },
  {
    patterns: [
      'volume up',
      'louder',
      'increase volume',
      'turn it up'
    ],
    action: 'VOLUME_UP',
    category: 'control'
  },
  {
    patterns: [
      'volume down',
      'quieter',
      'decrease volume',
      'turn it down'
    ],
    action: 'VOLUME_DOWN',
    category: 'control'
  },
  {
    patterns: [
      'mute',
      'silence',
      'no sound'
    ],
    action: 'MUTE',
    category: 'control'
  },

  // Query Commands
  {
    patterns: [
      'what is nearby',
      'what is around me',
      'points of interest',
      'what can I see'
    ],
    action: 'QUERY_NEARBY',
    category: 'query'
  },
  {
    patterns: [
      'how far to {destination}',
      'distance to {destination}',
      'how many miles to {destination}',
      'ETA to {destination}'
    ],
    action: 'QUERY_DISTANCE',
    category: 'query',
    parameters: ['destination']
  },
  {
    patterns: [
      'current location',
      'where am I',
      'what is my location',
      'where are we'
    ],
    action: 'QUERY_LOCATION',
    category: 'query'
  },
  {
    patterns: [
      'traffic status',
      'how is traffic',
      'traffic ahead',
      'any delays'
    ],
    action: 'QUERY_TRAFFIC',
    category: 'query'
  },

  // Booking Commands
  {
    patterns: [
      'book restaurant',
      'make reservation',
      'find restaurant',
      'I am hungry'
    ],
    action: 'BOOK_RESTAURANT',
    category: 'booking'
  },
  {
    patterns: [
      'book hotel',
      'find hotel',
      'need accommodation',
      'place to stay'
    ],
    action: 'BOOK_HOTEL',
    category: 'booking'
  },
  {
    patterns: [
      'buy tickets for {attraction}',
      'book tickets',
      'get tickets for {attraction}'
    ],
    action: 'BOOK_TICKETS',
    category: 'booking',
    parameters: ['attraction']
  },

  // Entertainment Commands
  {
    patterns: [
      'tell me a story',
      'start story',
      'begin narrative',
      'entertain me'
    ],
    action: 'START_STORY',
    category: 'entertainment'
  },
  {
    patterns: [
      'play trivia',
      'start trivia',
      'trivia game',
      'quiz me'
    ],
    action: 'START_TRIVIA',
    category: 'entertainment'
  },
  {
    patterns: [
      'change theme to {theme}',
      'switch to {theme} theme',
      '{theme} mode'
    ],
    action: 'CHANGE_THEME',
    category: 'entertainment',
    parameters: ['theme']
  },
  {
    patterns: [
      'side quest',
      'adventure',
      'explore nearby',
      'find something interesting'
    ],
    action: 'SUGGEST_SIDEQUEST',
    category: 'entertainment'
  },

  // Settings Commands
  {
    patterns: [
      'settings',
      'open settings',
      'preferences'
    ],
    action: 'OPEN_SETTINGS',
    category: 'settings'
  },
  {
    patterns: [
      'help',
      'what can you do',
      'voice commands',
      'help me'
    ],
    action: 'SHOW_HELP',
    category: 'settings'
  },
  {
    patterns: [
      'emergency',
      'call emergency',
      'nine one one',
      'help emergency'
    ],
    action: 'EMERGENCY',
    category: 'settings',
    requiresConfirmation: false
  }
];

// Function to match voice input to commands
export function matchVoiceCommand(input: string): { command: VoiceCommand; params: Record<string, string> } | null {
  const normalizedInput = input.toLowerCase().trim();
  
  for (const command of VOICE_COMMANDS) {
    for (const pattern of command.patterns) {
      const regex = createPatternRegex(pattern);
      const match = normalizedInput.match(regex);
      
      if (match) {
        const params: Record<string, string> = {};
        
        if (command.parameters) {
          command.parameters.forEach((param, index) => {
            params[param] = match[index + 1] || '';
          });
        }
        
        return { command, params };
      }
    }
  }
  
  return null;
}

// Convert pattern with parameters to regex
function createPatternRegex(pattern: string): RegExp {
  const escapedPattern = pattern
    .replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    .replace(/\{(\w+)\}/g, '(.+)');
  
  return new RegExp(`^${escapedPattern}$`, 'i');
}

// Voice feedback templates
export const VOICE_FEEDBACK = {
  CONFIRMATION_NEEDED: 'Do you want to {action}? Say yes to confirm or no to cancel.',
  ACTION_CONFIRMED: 'OK, {action}.',
  ACTION_CANCELLED: 'Cancelled.',
  NAVIGATION_STARTED: 'Starting navigation to {destination}.',
  NAVIGATION_STOPPED: 'Navigation stopped.',
  STORY_PAUSED: 'Story paused. Say resume when ready.',
  STORY_RESUMED: 'Resuming story.',
  VOLUME_CHANGED: 'Volume {direction}.',
  SEARCHING: 'Searching for {query}...',
  ERROR: 'Sorry, I didn\'t understand that. Try saying help for available commands.',
  HELP: 'You can say things like: navigate to a destination, find gas station, tell me a story, or play trivia. What would you like to do?'
};

// Safety prompts
export const SAFETY_PROMPTS = {
  DRIVER_CONFIRMATION: 'For your safety, please confirm you are a passenger or have safely pulled over.',
  HANDS_FREE_REMINDER: 'Remember to keep your hands on the wheel and eyes on the road.',
  COMPLEX_ACTION: 'This action requires your attention. Would you like me to wait until you\'ve stopped?'
};