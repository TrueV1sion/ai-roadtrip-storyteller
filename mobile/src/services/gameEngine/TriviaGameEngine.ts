import { LocationData } from '../locationService';
import { GameDifficulty } from './GameStateManager';
import { logger } from '@/services/logger';
import { apiClient } from '../api/ApiClient'; // Import the API client

export enum TriviaCategory {
  GENERAL = 'general',
  HISTORY = 'history',
  GEOGRAPHY = 'geography',
  SCIENCE = 'science',
  ENTERTAINMENT = 'entertainment',
  LANDMARKS = 'landmarks',
  CULTURE = 'culture'
}

export interface TriviaQuestion {
  id: string;
  question: string;
  options: string[];
  correctOptionIndex: number;
  explanation?: string;
  category: string;
  difficulty: GameDifficulty;
  timeLimit?: number; // in seconds
  imageUrl?: string;
  locationBased: boolean; // Keep this to know if it was intended to be location-based
}

export interface TriviaGame {
  id: string;
  questions: TriviaQuestion[];
  currentQuestionIndex: number;
  startTime: number;
  endTime?: number;
  isCompleted: boolean;
  score: number;
  maxScore: number;
  difficulty: GameDifficulty;
  location: LocationData; // Store location used for fetching
}

export interface TriviaResult {
  score: number;
  maxScore: number;
  correctAnswers: number;
  incorrectAnswers: number;
  skippedAnswers: number;
  percentageCorrect: number;
  timeSpentSeconds: number;
  categories: string[];
}

/**
 * TriviaGameEngine handles the state and logic for trivia games
 */
class TriviaGameEngine {
  private activeGame: TriviaGame | null = null;
  // private questionBank: TriviaQuestion[] = []; // Removed static question bank
  private categories: {[key: string]: { id: string, name: string, description: string, icon: string }} = {};

  constructor() {
    this.initializeCategories();
    // Removed call to generateSampleQuestions();
  }

  // initializeCategories remains the same
  private initializeCategories() {
    this.categories = {
      [TriviaCategory.GENERAL]: { id: TriviaCategory.GENERAL, name: 'General Knowledge', description: 'Questions about a variety of topics', icon: 'help-circle-outline' },
      [TriviaCategory.HISTORY]: { id: TriviaCategory.HISTORY, name: 'History', description: 'Questions about historical events and people', icon: 'time-outline' },
      [TriviaCategory.GEOGRAPHY]: { id: TriviaCategory.GEOGRAPHY, name: 'Geography', description: 'Questions about places, landforms and geography', icon: 'globe-outline' },
      [TriviaCategory.SCIENCE]: { id: TriviaCategory.SCIENCE, name: 'Science', description: 'Questions about scientific facts and discoveries', icon: 'flask-outline' },
      [TriviaCategory.ENTERTAINMENT]: { id: TriviaCategory.ENTERTAINMENT, name: 'Entertainment', description: 'Questions about movies, music, and pop culture', icon: 'film-outline' },
      [TriviaCategory.LANDMARKS]: { id: TriviaCategory.LANDMARKS, name: 'Landmarks', description: 'Questions about famous landmarks around the world', icon: 'location-outline' },
      [TriviaCategory.CULTURE]: { id: TriviaCategory.CULTURE, name: 'Culture', description: 'Questions about customs, traditions, and cultural practices', icon: 'people-outline' }
    };
  }

  // Removed generateSampleQuestions method
  // private generateSampleQuestions() { ... }

  /**
   * Generate a new trivia game by fetching questions from the backend API.
   */
  async generateGame(
    location: LocationData,
    difficulty: GameDifficulty = GameDifficulty.MEDIUM,
    questionCount: number = 5,
    categories?: string[]
  ): Promise<TriviaGame | null> { // Return null on failure
    logger.debug(`Generating trivia game for loc: ${location.latitude},${location.longitude}, diff: ${difficulty}, count: ${questionCount}, cats: ${categories}`);
    try {
      // Fetch questions from the backend API
      const params: any = {
        latitude: location.latitude,
        longitude: location.longitude,
        difficulty: difficulty,
        count: questionCount,
      };
      if (categories && categories.length > 0) {
        // API expects comma-separated string or repeated query params? Assuming repeated for now.
        // Adjust if API expects categories=cat1,cat2
         params.categories = categories; // Pass as array, apiClient might handle it
      }

      // Assuming the backend returns questions matching the TriviaQuestion interface
      const fetchedQuestions: TriviaQuestion[] = await apiClient.get('/api/games/trivia/questions', params);

      if (!fetchedQuestions || fetchedQuestions.length === 0) {
        logger.error('No questions received from API');
        // Handle error: maybe return a default game or null
        return null;
      }

      // Create a new game with fetched questions
      this.activeGame = {
        id: `trivia_${Date.now()}`, // Generate client-side ID for now
        questions: fetchedQuestions, // Use fetched questions
        currentQuestionIndex: 0,
        startTime: Date.now(),
        isCompleted: false,
        score: 0,
        maxScore: fetchedQuestions.length,
        difficulty,
        location // Store the location used to generate the game
      };

      logger.debug(`Trivia game generated with ${fetchedQuestions.length} questions.`);
      return this.activeGame;

    } catch (error) {
      logger.error('Error generating trivia game from API:', error);
      // Handle API error appropriately (e.g., show message to user)
      this.activeGame = null; // Ensure no active game on error
      return null;
    }
  }

  // Fisher-Yates shuffle algorithm (can be removed if backend shuffles)
  private shuffleArray<T>(array: T[]): T[] {
    const newArray = [...array];
    for (let i = newArray.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [newArray[i], newArray[j]] = [newArray[j], newArray[i]];
    }
    return newArray;
  }

  // answerQuestion, skipQuestion, completeGame, getActiveGame, getCategories, getCategory
  // remain the same as they operate on the activeGame state.

  /**
   * Answer the current question
   */
  answerQuestion(optionIndex: number): boolean {
    if (!this.activeGame || this.activeGame.isCompleted) {
      logger.warn('Cannot answer question: No active game or game already completed.');
      return false;
    }

    const currentQuestion = this.activeGame.questions[this.activeGame.currentQuestionIndex];
    if (!currentQuestion) {
        logger.error('Error: Current question is undefined.');
        return false; // Should not happen in a valid game state
    }
    const isCorrect = optionIndex === currentQuestion.correctOptionIndex;

    if (isCorrect) {
      this.activeGame.score += 1;
    }

    this.activeGame.currentQuestionIndex += 1;

    if (this.activeGame.currentQuestionIndex >= this.activeGame.questions.length) {
      this.activeGame.isCompleted = true;
      this.activeGame.endTime = Date.now();
      logger.debug(`Game ${this.activeGame.id} completed. Score: ${this.activeGame.score}/${this.activeGame.maxScore}`);
    }

    return isCorrect;
  }

  /**
   * Skip the current question
   */
  skipQuestion(): void {
    if (!this.activeGame || this.activeGame.isCompleted) {
       logger.warn('Cannot skip question: No active game or game already completed.');
      return;
    }

    this.activeGame.currentQuestionIndex += 1;

    if (this.activeGame.currentQuestionIndex >= this.activeGame.questions.length) {
      this.activeGame.isCompleted = true;
      this.activeGame.endTime = Date.now();
       logger.debug(`Game ${this.activeGame.id} completed via skip. Score: ${this.activeGame.score}/${this.activeGame.maxScore}`);
    }
  }

  /**
   * Complete the current game and get results
   */
  completeGame(): TriviaResult | null { // Return null if no active game
    if (!this.activeGame) {
      logger.warn('No active game to complete');
      return null;
    }

    if (!this.activeGame.isCompleted) {
        this.activeGame.isCompleted = true;
        this.activeGame.endTime = Date.now();
    }

    const correctAnswers = this.activeGame.score;
    const totalQuestions = this.activeGame.questions.length;
    // Ensure currentQuestionIndex doesn't exceed totalQuestions for calculation
    const questionsAttemptedOrSkipped = Math.min(this.activeGame.currentQuestionIndex, totalQuestions);
    const incorrectAnswers = questionsAttemptedOrSkipped - correctAnswers;
    const skippedAnswers = totalQuestions - questionsAttemptedOrSkipped; // Questions not reached
    const percentageCorrect = totalQuestions > 0 ? (correctAnswers / totalQuestions) * 100 : 0;
    const timeSpentSeconds = this.activeGame.endTime ? Math.floor((this.activeGame.endTime - this.activeGame.startTime) / 1000) : 0;

    const categories = [...new Set(this.activeGame.questions.map(q => q.category))];

    const result: TriviaResult = {
      score: correctAnswers,
      maxScore: totalQuestions,
      correctAnswers,
      incorrectAnswers,
      skippedAnswers,
      percentageCorrect,
      timeSpentSeconds,
      categories
    };

    this.activeGame = null; // Reset active game after completion

    return result;
  }

  /**
   * Get the active game
   */
  getActiveGame(): TriviaGame | null {
    return this.activeGame;
  }

  /**
   * Get available categories
   */
  getCategories(): { id: string, name: string, description: string, icon: string }[] {
    return Object.values(this.categories);
  }

  /**
   * Get a specific category
   */
  getCategory(id: string): { id: string, name: string, description: string, icon: string } | undefined {
    return this.categories[id];
  }
}

// Singleton instance
export const triviaGameEngine = new TriviaGameEngine();
export default triviaGameEngine;
