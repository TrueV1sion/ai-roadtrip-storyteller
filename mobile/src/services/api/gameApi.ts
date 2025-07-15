import { ApiClient } from './ApiClient';

export interface GameSession {
  session_id: string;
  game_type: string;
  players: Array<{
    id: string;
    name: string;
    score: number;
  }>;
  started_at: string;
  location: any;
  status: string;
}

export interface TriviaQuestion {
  id: string;
  text: string;
  options: string[];
  time_limit: number;
  category: string;
  points: number;
}

export interface AnswerResult {
  correct: boolean;
  points_earned: number;
  correct_answer: string;
  player_score: number;
  current_streak: number;
  leaderboard: Array<[string, number]>;
  new_achievements?: Array<{
    name: string;
    description: string;
    icon: string;
    points: number;
  }>;
}

export interface ScavengerItem {
  id: string;
  name: string;
  description: string;
  hint: string;
  points: number;
  location_clue?: string;
  photo_required: boolean;
  found: boolean;
  found_by?: string;
}

export interface Achievement {
  id: string;
  name: string;
  description: string;
  icon: string;
  points: number;
  unlocked: boolean;
  unlocked_at?: string;
}

export interface LeaderboardEntry {
  player_name: string;
  score: number;
  games_played: number;
  achievements: string[];
  rank: number;
}

class GameApi {
  private apiClient: ApiClient;

  constructor() {
    this.apiClient = new ApiClient();
  }

  // Game Session Management
  async createSession(data: {
    game_type: string;
    players: any[];
    location: any;
    difficulty?: string;
    theme?: string;
  }): Promise<GameSession> {
    const response = await this.apiClient.post('/games/sessions', data);
    return response.data;
  }

  async getGameState(sessionId: string): Promise<any> {
    const response = await this.apiClient.get(`/games/sessions/${sessionId}`);
    return response.data;
  }

  async endSession(sessionId: string): Promise<any> {
    const response = await this.apiClient.delete(`/games/sessions/${sessionId}`);
    return response.data;
  }

  // Trivia Game
  async getNextQuestion(sessionId: string): Promise<TriviaQuestion | null> {
    try {
      const response = await this.apiClient.get(`/games/trivia/questions/${sessionId}`);
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        return null; // No more questions
      }
      throw error;
    }
  }

  async submitAnswer(
    sessionId: string,
    data: { answer: string; time_taken: number }
  ): Promise<AnswerResult> {
    const response = await this.apiClient.post(
      `/games/trivia/answer/${sessionId}`,
      data
    );
    return response.data;
  }

  async getCategories(): Promise<string[]> {
    const response = await this.apiClient.get('/games/trivia/categories');
    return response.data;
  }

  async generateQuestions(params: {
    location: any;
    count?: number;
    categories?: string[];
    age_range?: [number, number];
  }): Promise<any> {
    const response = await this.apiClient.post('/games/trivia/generate-questions', params);
    return response.data;
  }

  // Scavenger Hunt
  async getScavengerItems(sessionId: string): Promise<ScavengerItem[]> {
    const response = await this.apiClient.get(`/games/scavenger/items/${sessionId}`);
    return response.data;
  }

  async markItemFound(
    sessionId: string,
    data: { item_id: string; photo_url?: string }
  ): Promise<any> {
    const response = await this.apiClient.post(
      `/games/scavenger/found/${sessionId}`,
      data
    );
    return response.data;
  }

  async generateScavengerHunt(params: {
    location: any;
    radius?: number;
    count?: number;
    theme?: string;
  }): Promise<any> {
    const response = await this.apiClient.post('/games/scavenger/generate-hunt', params);
    return response.data;
  }

  // Achievements
  async getAchievements(): Promise<Achievement[]> {
    const response = await this.apiClient.get('/games/achievements');
    return response.data;
  }

  async getRecentAchievements(limit: number = 10): Promise<Achievement[]> {
    const response = await this.apiClient.get('/games/achievements/recent', {
      params: { limit },
    });
    return response.data;
  }

  // Leaderboards
  async getGlobalLeaderboard(
    limit: number = 10,
    offset: number = 0
  ): Promise<LeaderboardEntry[]> {
    const response = await this.apiClient.get('/games/leaderboard/global', {
      params: { limit, offset },
    });
    return response.data;
  }

  async getFriendsLeaderboard(limit: number = 10): Promise<LeaderboardEntry[]> {
    const response = await this.apiClient.get('/games/leaderboard/friends', {
      params: { limit },
    });
    return response.data;
  }

  async getSessionLeaderboard(sessionId: string): Promise<any[]> {
    const response = await this.apiClient.get(`/games/leaderboard/session/${sessionId}`);
    return response.data;
  }

  // Game History
  async getGameHistory(params: {
    limit?: number;
    offset?: number;
    game_type?: string;
  }): Promise<any> {
    const response = await this.apiClient.get('/games/history', { params });
    return response.data;
  }

  // Educational Content
  async getEducationalContent(
    questionId: string,
    extended: boolean = false
  ): Promise<any> {
    const response = await this.apiClient.get(`/games/educational/${questionId}`, {
      params: { extended },
    });
    return response.data;
  }

  // Themes
  async getAvailableThemes(): Promise<string[]> {
    const response = await this.apiClient.get('/games/themes');
    return response.data;
  }

  async createThemedQuiz(params: {
    theme: string;
    location: any;
    question_count?: number;
    age_range?: [number, number];
  }): Promise<any> {
    const response = await this.apiClient.post('/games/themed-quiz', params);
    return response.data;
  }

  // Hints
  async getHint(sessionId: string, hintLevel: number = 1): Promise<{ hint: string }> {
    const response = await this.apiClient.get(`/games/hint/${sessionId}`, {
      params: { hint_level: hintLevel },
    });
    return response.data;
  }

  // Location Triggers
  async getLocationTriggers(params: {
    latitude: number;
    longitude: number;
    radius?: number;
  }): Promise<any> {
    const response = await this.apiClient.get('/games/location-triggers', { params });
    return response.data;
  }

  // Upload photo for scavenger hunt
  async uploadPhoto(photoUri: string): Promise<string> {
    const formData = new FormData();
    formData.append('photo', {
      uri: photoUri,
      type: 'image/jpeg',
      name: 'scavenger_photo.jpg',
    } as any);

    const response = await this.apiClient.post('/upload/photo', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data.url;
  }
}

export const gameApi = new GameApi();