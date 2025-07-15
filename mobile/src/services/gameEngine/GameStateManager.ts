import AsyncStorage from '@react-native-async-storage/async-storage';

export enum GameType {
  TRIVIA = 'trivia',
  SCAVENGER_HUNT = 'scavenger_hunt',
  STORY_ADVENTURE = 'story_adventure'
}

export enum GameDifficulty {
  EASY = 'easy',
  MEDIUM = 'medium',
  HARD = 'hard'
}

export interface GameState {
  userId: string;
  unlockedGameTypes: GameType[];
  // Player progress
  level: number;
  xp: number;
  xpToNextLevel: number;
  // Achievements
  achievements: Achievement[];
  // Game history
  completedGames: CompletedGame[];
  // Player preferences
  preferences: GamePreferences;
}

export interface Achievement {
  id: string;
  title: string;
  description: string;
  completed: boolean;
  completedDate?: number;
  progress?: number;
  maxProgress?: number;
  icon?: string;
}

export interface CompletedGame {
  id: string;
  type: GameType;
  score: number;
  maxScore: number;
  completedDate: number;
  difficulty: GameDifficulty;
  metadata?: any;
}

export interface GamePreferences {
  preferredDifficulty: GameDifficulty;
  preferredCategories: string[];
  soundEffects: boolean;
  backgroundMusic: boolean;
  vibration: boolean;
  notifications: boolean;
}

const STORAGE_KEY = 'road_trip_game_state';

/**
 * GameStateManager handles overall game state, progression, and persistent storage
 */
class GameStateManager {
  private state: GameState = {
    userId: '',
    unlockedGameTypes: [GameType.TRIVIA],
    level: 1,
    xp: 0,
    xpToNextLevel: 100,
    achievements: [],
    completedGames: [],
    preferences: {
      preferredDifficulty: GameDifficulty.MEDIUM,
      preferredCategories: [],
      soundEffects: true,
      backgroundMusic: true,
      vibration: true,
      notifications: true
    }
  };
  
  private initialized = false;
  
  /**
   * Initialize the game state manager
   */
  async initialize(): Promise<void> {
    if (this.initialized) {
      return;
    }
    
    // Try to load state from storage
    try {
      const storedState = await AsyncStorage.getItem(STORAGE_KEY);
      
      if (storedState) {
        this.state = JSON.parse(storedState);
      } else {
        // If no state, generate a new one with default values
        this.state = {
          ...this.state,
          userId: `user_${Date.now()}`,
          achievements: this.generateDefaultAchievements()
        };
        
        // Save initial state
        await this.saveState();
      }
      
      this.initialized = true;
    } catch (error) {
      console.error('Error initializing game state:', error);
      
      // Generate fallback state
      this.state = {
        ...this.state,
        userId: `user_${Date.now()}`,
        achievements: this.generateDefaultAchievements()
      };
      
      this.initialized = true;
    }
  }
  
  /**
   * Generate default achievements
   */
  private generateDefaultAchievements(): Achievement[] {
    return [
      {
        id: 'first_trivia',
        title: 'Trivia Novice',
        description: 'Complete your first trivia game',
        completed: false,
        icon: 'help-circle-outline'
      },
      {
        id: 'trivia_master',
        title: 'Trivia Master',
        description: 'Get a perfect score in a trivia game',
        completed: false,
        icon: 'ribbon-outline'
      },
      {
        id: 'explorer',
        title: 'Explorer',
        description: 'Visit 5 different locations',
        completed: false,
        progress: 0,
        maxProgress: 5,
        icon: 'map-outline'
      },
      {
        id: 'history_buff',
        title: 'History Buff',
        description: 'Answer 20 history questions correctly',
        completed: false,
        progress: 0,
        maxProgress: 20,
        icon: 'time-outline'
      },
      {
        id: 'speed_demon',
        title: 'Speed Demon',
        description: 'Complete a trivia game in under 60 seconds',
        completed: false,
        icon: 'timer-outline'
      }
    ];
  }
  
  /**
   * Save current state to storage
   */
  private async saveState(): Promise<void> {
    try {
      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(this.state));
    } catch (error) {
      console.error('Error saving game state:', error);
    }
  }
  
  /**
   * Get the current game state
   */
  getState(): GameState {
    return { ...this.state };
  }
  
  /**
   * Add experience points and check for level up
   */
  async addXP(amount: number): Promise<{ leveledUp: boolean, newLevel?: number }> {
    if (!this.initialized) {
      await this.initialize();
    }
    
    this.state.xp += amount;
    
    let leveledUp = false;
    let newLevel = this.state.level;
    
    // Check for level up
    while (this.state.xp >= this.state.xpToNextLevel) {
      this.state.xp -= this.state.xpToNextLevel;
      this.state.level++;
      newLevel = this.state.level;
      
      // Increase XP required for next level (simple formula)
      this.state.xpToNextLevel = Math.floor(this.state.xpToNextLevel * 1.5);
      
      leveledUp = true;
    }
    
    await this.saveState();
    
    return { leveledUp, newLevel: leveledUp ? newLevel : undefined };
  }
  
  /**
   * Unlock a new game type
   */
  async unlockGameType(gameType: GameType): Promise<boolean> {
    if (!this.initialized) {
      await this.initialize();
    }
    
    if (this.state.unlockedGameTypes.includes(gameType)) {
      return false; // Already unlocked
    }
    
    this.state.unlockedGameTypes.push(gameType);
    await this.saveState();
    
    return true;
  }
  
  /**
   * Record a completed game
   */
  async recordCompletedGame(gameData: Omit<CompletedGame, 'completedDate'>): Promise<void> {
    if (!this.initialized) {
      await this.initialize();
    }
    
    const completedGame: CompletedGame = {
      ...gameData,
      completedDate: Date.now()
    };
    
    this.state.completedGames.push(completedGame);
    
    // Add XP based on game performance
    const xpGained = Math.floor((gameData.score / gameData.maxScore) * 50) + 10;
    await this.addXP(xpGained);
    
    // Check achievements
    await this.checkAchievements(completedGame);
    
    await this.saveState();
  }
  
  /**
   * Check for achievements after completing a game
   */
  private async checkAchievements(game: CompletedGame): Promise<void> {
    // First trivia game
    if (game.type === GameType.TRIVIA) {
      const firstTriviaAchievement = this.state.achievements.find(a => a.id === 'first_trivia');
      if (firstTriviaAchievement && !firstTriviaAchievement.completed) {
        firstTriviaAchievement.completed = true;
        firstTriviaAchievement.completedDate = Date.now();
      }
    }
    
    // Perfect score
    if (game.score === game.maxScore) {
      const perfectScoreAchievement = this.state.achievements.find(a => a.id === 'trivia_master');
      if (perfectScoreAchievement && !perfectScoreAchievement.completed) {
        perfectScoreAchievement.completed = true;
        perfectScoreAchievement.completedDate = Date.now();
      }
    }
    
    // Speed demon (complete under 60 seconds)
    if (game.type === GameType.TRIVIA && game.metadata?.timeSpentSeconds < 60) {
      const speedDemonAchievement = this.state.achievements.find(a => a.id === 'speed_demon');
      if (speedDemonAchievement && !speedDemonAchievement.completed) {
        speedDemonAchievement.completed = true;
        speedDemonAchievement.completedDate = Date.now();
      }
    }
    
    // History buff (increment counter for history questions)
    if (game.type === GameType.TRIVIA && game.metadata?.categories?.includes('history')) {
      const historyBuffAchievement = this.state.achievements.find(a => a.id === 'history_buff');
      if (historyBuffAchievement && !historyBuffAchievement.completed) {
        const correctHistoryQuestions = game.metadata?.correctCategories?.history || 0;
        historyBuffAchievement.progress = (historyBuffAchievement.progress || 0) + correctHistoryQuestions;
        
        if (historyBuffAchievement.progress >= historyBuffAchievement.maxProgress!) {
          historyBuffAchievement.completed = true;
          historyBuffAchievement.completedDate = Date.now();
        }
      }
    }
    
    // Explorer (unique locations)
    if (game.metadata?.location) {
      const explorerAchievement = this.state.achievements.find(a => a.id === 'explorer');
      if (explorerAchievement && !explorerAchievement.completed) {
        // Get unique locations (simple check based on latitude/longitude rounded to 2 decimal places)
        const locations = this.state.completedGames
          .filter(g => g.metadata?.location)
          .map(g => `${g.metadata.location.latitude.toFixed(2)},${g.metadata.location.longitude.toFixed(2)}`);
        
        // Add current location
        const currentLocation = `${game.metadata.location.latitude.toFixed(2)},${game.metadata.location.longitude.toFixed(2)}`;
        if (!locations.includes(currentLocation)) {
          locations.push(currentLocation);
        }
        
        // Count unique locations
        const uniqueLocations = new Set(locations);
        explorerAchievement.progress = uniqueLocations.size;
        
        if (explorerAchievement.progress >= explorerAchievement.maxProgress!) {
          explorerAchievement.completed = true;
          explorerAchievement.completedDate = Date.now();
        }
      }
    }
  }
  
  /**
   * Update user preferences
   */
  async updatePreferences(preferences: Partial<GamePreferences>): Promise<void> {
    if (!this.initialized) {
      await this.initialize();
    }
    
    this.state.preferences = {
      ...this.state.preferences,
      ...preferences
    };
    
    await this.saveState();
  }
  
  /**
   * Reset game state (for testing)
   */
  async resetState(): Promise<void> {
    this.state = {
      userId: `user_${Date.now()}`,
      unlockedGameTypes: [GameType.TRIVIA],
      level: 1,
      xp: 0,
      xpToNextLevel: 100,
      achievements: this.generateDefaultAchievements(),
      completedGames: [],
      preferences: {
        preferredDifficulty: GameDifficulty.MEDIUM,
        preferredCategories: [],
        soundEffects: true,
        backgroundMusic: true,
        vibration: true,
        notifications: true
      }
    };
    
    await this.saveState();
  }
}

// Singleton instance
export const gameStateManager = new GameStateManager();
export default gameStateManager;
