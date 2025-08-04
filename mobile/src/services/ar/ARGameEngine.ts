/**
 * AR Game Engine
 * Simple AR games for road trips
 */

import { ARLandmark } from './ARLandmarkService';
import { voiceOrchestrationService } from '../voiceOrchestrationService';
import { gameOrchestrator } from '../games/game_orchestrator';
import { performanceMonitor } from '../performanceMonitor';

import { logger } from '@/services/logger';
export interface ARGame {
  id: string;
  type: 'scavenger' | 'landmark_quiz' | 'photo_hunt' | 'time_travel';
  name: string;
  description: string;
  difficulty: 'easy' | 'medium' | 'hard';
  duration: number; // minutes
  points: number;
  requirements: {
    minLandmarks?: number;
    locationTypes?: string[];
    weatherConditions?: string[];
  };
}

export interface ARGameSession {
  gameId: string;
  startTime: Date;
  endTime?: Date;
  score: number;
  progress: number; // 0-100
  objectives: ARGameObjective[];
  achievements: string[];
}

export interface ARGameObjective {
  id: string;
  description: string;
  type: 'find' | 'photograph' | 'answer' | 'visit';
  target?: string;
  completed: boolean;
  points: number;
}

export class ARGameEngine {
  private static instance: ARGameEngine;
  private currentSession: ARGameSession | null = null;
  private availableGames: Map<string, ARGame> = new Map();
  
  private constructor() {
    this.initializeGames();
  }
  
  static getInstance(): ARGameEngine {
    if (!ARGameEngine.instance) {
      ARGameEngine.instance = new ARGameEngine();
    }
    return ARGameEngine.instance;
  }
  
  /**
   * Initialize available AR games
   */
  private initializeGames(): void {
    const games: ARGame[] = [
      {
        id: 'landmark_hunter',
        type: 'scavenger',
        name: 'Landmark Hunter',
        description: 'Find and photograph famous landmarks',
        difficulty: 'easy',
        duration: 30,
        points: 100,
        requirements: {
          minLandmarks: 3,
        },
      },
      {
        id: 'history_detective',
        type: 'landmark_quiz',
        name: 'History Detective',
        description: 'Answer questions about historical sites',
        difficulty: 'medium',
        duration: 20,
        points: 150,
        requirements: {
          locationTypes: ['historical'],
        },
      },
      {
        id: 'photo_safari',
        type: 'photo_hunt',
        name: 'Photo Safari',
        description: 'Capture specific types of landmarks',
        difficulty: 'easy',
        duration: 45,
        points: 200,
        requirements: {
          minLandmarks: 5,
        },
      },
      {
        id: 'time_traveler',
        type: 'time_travel',
        name: 'Time Traveler',
        description: 'Experience landmarks through history',
        difficulty: 'hard',
        duration: 60,
        points: 300,
        requirements: {
          locationTypes: ['historical'],
          minLandmarks: 3,
        },
      },
    ];
    
    games.forEach((game) => {
      this.availableGames.set(game.id, game);
    });
  }
  
  /**
   * Get available games for current context
   */
  getAvailableGames(landmarks: ARLandmark[]): ARGame[] {
    return Array.from(this.availableGames.values()).filter((game) => {
      // Check landmark count
      if (game.requirements.minLandmarks && 
          landmarks.length < game.requirements.minLandmarks) {
        return false;
      }
      
      // Check location types
      if (game.requirements.locationTypes) {
        const hasRequiredTypes = game.requirements.locationTypes.some(
          (type) => landmarks.some((landmark) => landmark.type === type)
        );
        if (!hasRequiredTypes) return false;
      }
      
      return true;
    });
  }
  
  /**
   * Start AR game session
   */
  async startGame(
    gameId: string,
    landmarks: ARLandmark[]
  ): Promise<ARGameSession> {
    const game = this.availableGames.get(gameId);
    if (!game) {
      throw new Error('Game not found');
    }
    
    // End current session if exists
    if (this.currentSession) {
      await this.endGame();
    }
    
    // Generate objectives based on game type
    const objectives = this.generateObjectives(game, landmarks);
    
    // Create session
    this.currentSession = {
      gameId,
      startTime: new Date(),
      score: 0,
      progress: 0,
      objectives,
      achievements: [],
    };
    
    // Announce game start
    await voiceOrchestrationService.speak(
      `Starting ${game.name}. ${game.description}. You have ${game.duration} minutes!`,
      { priority: 'high' }
    );
    
    // Log event
    performanceMonitor.logEvent('ar_game_started', {
      gameId,
      objectives: objectives.length,
    });
    
    return this.currentSession;
  }
  
  /**
   * Generate game objectives
   */
  private generateObjectives(
    game: ARGame,
    landmarks: ARLandmark[]
  ): ARGameObjective[] {
    const objectives: ARGameObjective[] = [];
    
    switch (game.type) {
      case 'scavenger':
        // Find specific landmarks
        landmarks.slice(0, 5).forEach((landmark, index) => {
          objectives.push({
            id: `obj_${index}`,
            description: `Find ${landmark.name}`,
            type: 'find',
            target: landmark.id,
            completed: false,
            points: 20,
          });
        });
        break;
      
      case 'landmark_quiz':
        // Answer questions about landmarks
        landmarks.slice(0, 3).forEach((landmark, index) => {
          objectives.push({
            id: `obj_${index}`,
            description: `Answer a question about ${landmark.name}`,
            type: 'answer',
            target: landmark.id,
            completed: false,
            points: 30,
          });
        });
        break;
      
      case 'photo_hunt':
        // Photograph specific types
        const types = ['historical', 'nature', 'landmark'];
        types.forEach((type, index) => {
          objectives.push({
            id: `obj_${index}`,
            description: `Photograph a ${type} location`,
            type: 'photograph',
            target: type,
            completed: false,
            points: 25,
          });
        });
        break;
      
      case 'time_travel':
        // Visit historical sites
        landmarks
          .filter((l) => l.type === 'historical')
          .slice(0, 3)
          .forEach((landmark, index) => {
            objectives.push({
              id: `obj_${index}`,
              description: `Experience ${landmark.name} through time`,
              type: 'visit',
              target: landmark.id,
              completed: false,
              points: 50,
            });
          });
        break;
    }
    
    return objectives;
  }
  
  /**
   * Check objective completion
   */
  async checkObjective(
    action: {
      type: 'found' | 'photographed' | 'answered' | 'visited';
      targetId: string;
      data?: any;
    }
  ): Promise<{
    completed: boolean;
    points: number;
    achievement?: string;
  }> {
    if (!this.currentSession) {
      return { completed: false, points: 0 };
    }
    
    let completedObjective: ARGameObjective | undefined;
    let points = 0;
    
    // Find matching objective
    for (const objective of this.currentSession.objectives) {
      if (objective.completed) continue;
      
      const matches = 
        (action.type === 'found' && objective.type === 'find' && objective.target === action.targetId) ||
        (action.type === 'photographed' && objective.type === 'photograph') ||
        (action.type === 'answered' && objective.type === 'answer' && objective.target === action.targetId) ||
        (action.type === 'visited' && objective.type === 'visit' && objective.target === action.targetId);
      
      if (matches) {
        objective.completed = true;
        completedObjective = objective;
        points = objective.points;
        break;
      }
    }
    
    if (completedObjective) {
      // Update score and progress
      this.currentSession.score += points;
      const completedCount = this.currentSession.objectives.filter(o => o.completed).length;
      this.currentSession.progress = (completedCount / this.currentSession.objectives.length) * 100;
      
      // Voice feedback
      await voiceOrchestrationService.speak(
        `Great! ${completedObjective.description} completed. ${points} points earned!`,
        { priority: 'high' }
      );
      
      // Check for achievements
      const achievement = this.checkAchievements();
      
      // Check game completion
      if (this.currentSession.progress === 100) {
        await this.completeGame();
      }
      
      return {
        completed: true,
        points,
        achievement,
      };
    }
    
    return { completed: false, points: 0 };
  }
  
  /**
   * Check for achievements
   */
  private checkAchievements(): string | undefined {
    if (!this.currentSession) return undefined;
    
    // Fast completion
    const elapsed = Date.now() - this.currentSession.startTime.getTime();
    if (elapsed < 5 * 60 * 1000 && this.currentSession.progress >= 50) {
      this.currentSession.achievements.push('speed_demon');
      return 'Speed Demon - Completed objectives super fast!';
    }
    
    // Perfect score
    if (this.currentSession.score >= 150 && this.currentSession.objectives.every(o => o.completed)) {
      this.currentSession.achievements.push('perfectionist');
      return 'Perfectionist - All objectives completed!';
    }
    
    return undefined;
  }
  
  /**
   * Complete game
   */
  private async completeGame(): Promise<void> {
    if (!this.currentSession) return;
    
    const game = this.availableGames.get(this.currentSession.gameId);
    if (!game) return;
    
    // Calculate bonus
    const timeBonus = this.calculateTimeBonus();
    const finalScore = this.currentSession.score + timeBonus;
    
    // Announce completion
    await voiceOrchestrationService.speak(
      `Congratulations! You completed ${game.name} with ${finalScore} points! ` +
      `${this.currentSession.achievements.length > 0 ? 
        `You earned: ${this.currentSession.achievements.join(', ')}` : ''}`,
      { priority: 'high' }
    );
    
    // Log completion
    performanceMonitor.logEvent('ar_game_completed', {
      gameId: this.currentSession.gameId,
      score: finalScore,
      duration: Date.now() - this.currentSession.startTime.getTime(),
      achievements: this.currentSession.achievements,
    });
  }
  
  /**
   * End current game
   */
  async endGame(): Promise<void> {
    if (!this.currentSession) return;
    
    this.currentSession.endTime = new Date();
    
    // Save to game history
    await this.saveGameHistory();
    
    this.currentSession = null;
  }
  
  /**
   * Get current session
   */
  getCurrentSession(): ARGameSession | null {
    return this.currentSession;
  }
  
  /**
   * Calculate time bonus
   */
  private calculateTimeBonus(): number {
    if (!this.currentSession) return 0;
    
    const game = this.availableGames.get(this.currentSession.gameId);
    if (!game) return 0;
    
    const elapsed = Date.now() - this.currentSession.startTime.getTime();
    const targetTime = game.duration * 60 * 1000;
    
    if (elapsed < targetTime * 0.5) {
      return 50; // Completed in half the time
    } else if (elapsed < targetTime * 0.75) {
      return 25; // Completed in 3/4 time
    }
    
    return 0;
  }
  
  /**
   * Save game history
   */
  private async saveGameHistory(): Promise<void> {
    // This would save to persistent storage
    // For now, just log
    logger.debug('Game history saved');
  }
  
  /**
   * Get game leaderboard
   */
  async getLeaderboard(gameId: string): Promise<any[]> {
    // This would fetch from backend
    return [];
  }
}

// Export singleton instance
export const arGameEngine = ARGameEngine.getInstance();
