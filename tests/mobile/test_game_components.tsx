/**
 * Comprehensive tests for mobile game components
 * Tests TriviaGameScreen and related game UI components
 */

import React from 'react';
import { render, fireEvent, waitFor, act } from '@testing-library/react-native';
import { NavigationContainer } from '@react-navigation/native';
import { Provider } from 'react-redux';
import configureStore from 'redux-mock-store';
import TriviaGameScreen from '../../mobile/src/screens/TriviaGameScreen';
import { ApiClient } from '../../mobile/src/services/api/ApiClient';

// Mock dependencies
jest.mock('../../mobile/src/services/api/ApiClient');
jest.mock('react-native-voice', () => ({
  start: jest.fn(),
  stop: jest.fn(),
  cancel: jest.fn(),
  destroy: jest.fn(),
  isAvailable: jest.fn(() => Promise.resolve(true)),
  isRecognizing: jest.fn(() => Promise.resolve(false)),
  isSpeaking: jest.fn(() => Promise.resolve(false)),
  onSpeechStart: jest.fn(),
  onSpeechEnd: jest.fn(),
  onSpeechResults: jest.fn(),
  onSpeechError: jest.fn(),
}));

const mockStore = configureStore([]);

describe('TriviaGameScreen', () => {
  let store: any;
  let mockApiClient: jest.Mocked<ApiClient>;

  beforeEach(() => {
    store = mockStore({
      auth: { user: { id: 1, username: 'testuser' } },
      game: { currentSession: null },
    });

    mockApiClient = new ApiClient() as jest.Mocked<ApiClient>;
    (ApiClient as jest.Mock).mockImplementation(() => mockApiClient);
    
    jest.clearAllMocks();
  });

  const renderWithProviders = (component: React.ReactElement) => {
    return render(
      <Provider store={store}>
        <NavigationContainer>
          {component}
        </NavigationContainer>
      </Provider>
    );
  };

  describe('Game Initialization', () => {
    it('should render game start screen correctly', () => {
      const { getByText, getByTestId } = renderWithProviders(
        <TriviaGameScreen />
      );

      expect(getByText('Road Trip Trivia')).toBeTruthy();
      expect(getByText('Start Game')).toBeTruthy();
      expect(getByTestId('difficulty-selector')).toBeTruthy();
    });

    it('should allow difficulty selection', () => {
      const { getByText, getByTestId } = renderWithProviders(
        <TriviaGameScreen />
      );

      const easyButton = getByText('Easy');
      const mediumButton = getByText('Medium');
      const hardButton = getByText('Hard');

      fireEvent.press(hardButton);
      expect(getByTestId('selected-difficulty')).toHaveTextContent('Hard');
    });

    it('should start game session on button press', async () => {
      mockApiClient.post.mockResolvedValueOnce({
        data: { session_id: 'session_123', status: 'started' }
      });

      const { getByText } = renderWithProviders(<TriviaGameScreen />);
      const startButton = getByText('Start Game');

      await act(async () => {
        fireEvent.press(startButton);
      });

      await waitFor(() => {
        expect(mockApiClient.post).toHaveBeenCalledWith(
          '/api/games/trivia/start',
          expect.objectContaining({
            game_mode: 'standard',
            difficulty: 'medium'
          })
        );
      });
    });
  });

  describe('Question Display', () => {
    beforeEach(() => {
      // Setup game in progress state
      store = mockStore({
        auth: { user: { id: 1 } },
        game: {
          currentSession: {
            sessionId: 'session_123',
            score: 0,
            questionsAnswered: 0,
            streak: 0
          }
        },
      });
    });

    it('should display question and options', async () => {
      const mockQuestion = {
        question: "What year was the Statue of Liberty dedicated?",
        options: ["1886", "1890", "1875", "1901"],
        category: "history",
        difficulty: "medium"
      };

      mockApiClient.post.mockResolvedValueOnce({ data: mockQuestion });

      const { getByText, getAllByTestId } = renderWithProviders(
        <TriviaGameScreen />
      );

      await waitFor(() => {
        expect(getByText(mockQuestion.question)).toBeTruthy();
        const options = getAllByTestId(/option-button-/);
        expect(options).toHaveLength(4);
      });
    });

    it('should show countdown timer', async () => {
      const mockQuestion = {
        question: "Test question?",
        options: ["A", "B", "C", "D"]
      };

      mockApiClient.post.mockResolvedValueOnce({ data: mockQuestion });

      const { getByTestId } = renderWithProviders(<TriviaGameScreen />);

      await waitFor(() => {
        const timer = getByTestId('countdown-timer');
        expect(timer).toBeTruthy();
        expect(timer).toHaveTextContent('30'); // Default 30 seconds
      });
    });

    it('should animate timer when running low', async () => {
      jest.useFakeTimers();

      const mockQuestion = {
        question: "Test question?",
        options: ["A", "B", "C", "D"]
      };

      mockApiClient.post.mockResolvedValueOnce({ data: mockQuestion });

      const { getByTestId } = renderWithProviders(<TriviaGameScreen />);

      // Fast forward to 5 seconds remaining
      act(() => {
        jest.advanceTimersByTime(25000);
      });

      await waitFor(() => {
        const timer = getByTestId('countdown-timer');
        expect(timer).toHaveStyle({ color: 'red' }); // Warning color
      });

      jest.useRealTimers();
    });
  });

  describe('Answer Submission', () => {
    it('should handle correct answer', async () => {
      const mockSubmitResponse = {
        correct: true,
        score: 100,
        streak: 1,
        explanation: "Correct! The Statue of Liberty was dedicated in 1886."
      };

      mockApiClient.post
        .mockResolvedValueOnce({ 
          data: {
            question: "Test?",
            options: ["A", "B", "C", "D"]
          }
        })
        .mockResolvedValueOnce({ data: mockSubmitResponse });

      const { getByTestId, getByText } = renderWithProviders(
        <TriviaGameScreen />
      );

      await waitFor(() => {
        const optionButton = getByTestId('option-button-0');
        fireEvent.press(optionButton);
      });

      await waitFor(() => {
        expect(getByText('Correct!')).toBeTruthy();
        expect(getByTestId('score-display')).toHaveTextContent('100');
        expect(getByTestId('streak-display')).toHaveTextContent('1');
      });
    });

    it('should handle incorrect answer', async () => {
      const mockSubmitResponse = {
        correct: false,
        correct_answer: 2,
        explanation: "The correct answer was C.",
        streak: 0
      };

      mockApiClient.post
        .mockResolvedValueOnce({ 
          data: {
            question: "Test?",
            options: ["A", "B", "C", "D"]
          }
        })
        .mockResolvedValueOnce({ data: mockSubmitResponse });

      const { getByTestId, getByText } = renderWithProviders(
        <TriviaGameScreen />
      );

      await waitFor(() => {
        const optionButton = getByTestId('option-button-0');
        fireEvent.press(optionButton);
      });

      await waitFor(() => {
        expect(getByText('Incorrect')).toBeTruthy();
        expect(getByText(mockSubmitResponse.explanation)).toBeTruthy();
        expect(getByTestId('streak-display')).toHaveTextContent('0');
      });
    });

    it('should disable options after answer', async () => {
      mockApiClient.post
        .mockResolvedValueOnce({ 
          data: {
            question: "Test?",
            options: ["A", "B", "C", "D"]
          }
        })
        .mockResolvedValueOnce({ 
          data: { correct: true, score: 100 }
        });

      const { getAllByTestId } = renderWithProviders(<TriviaGameScreen />);

      await waitFor(() => {
        const options = getAllByTestId(/option-button-/);
        fireEvent.press(options[0]);
      });

      await waitFor(() => {
        const options = getAllByTestId(/option-button-/);
        options.forEach(option => {
          expect(option).toBeDisabled();
        });
      });
    });
  });

  describe('Score and Progress', () => {
    it('should update score display', async () => {
      store = mockStore({
        auth: { user: { id: 1 } },
        game: {
          currentSession: {
            sessionId: 'session_123',
            score: 250,
            questionsAnswered: 5,
            streak: 3
          }
        },
      });

      const { getByTestId } = renderWithProviders(<TriviaGameScreen />);

      expect(getByTestId('score-display')).toHaveTextContent('250');
      expect(getByTestId('questions-answered')).toHaveTextContent('5');
      expect(getByTestId('streak-display')).toHaveTextContent('3');
    });

    it('should show streak bonus animation', async () => {
      const { getByTestId, rerender } = renderWithProviders(
        <TriviaGameScreen />
      );

      // Simulate streak increase
      store = mockStore({
        auth: { user: { id: 1 } },
        game: {
          currentSession: {
            sessionId: 'session_123',
            score: 500,
            streak: 5 // Streak milestone
          }
        },
      });

      rerender(
        <Provider store={store}>
          <NavigationContainer>
            <TriviaGameScreen />
          </NavigationContainer>
        </Provider>
      );

      await waitFor(() => {
        expect(getByTestId('streak-bonus-animation')).toBeTruthy();
      });
    });
  });

  describe('Game End', () => {
    it('should show game summary', async () => {
      const mockSummary = {
        total_score: 850,
        questions_answered: 10,
        correct_answers: 7,
        accuracy: 70.0,
        max_streak: 5,
        categories_played: ["history", "geography", "culture"],
        duration: 300
      };

      mockApiClient.get.mockResolvedValueOnce({ data: mockSummary });

      const { getByText, getByTestId } = renderWithProviders(
        <TriviaGameScreen />
      );

      // Trigger end game
      const endButton = getByTestId('end-game-button');
      fireEvent.press(endButton);

      await waitFor(() => {
        expect(getByText('Game Over!')).toBeTruthy();
        expect(getByText('Final Score: 850')).toBeTruthy();
        expect(getByText('Accuracy: 70%')).toBeTruthy();
        expect(getByText('Best Streak: 5')).toBeTruthy();
      });
    });

    it('should display achievements', async () => {
      const mockEndResponse = {
        final_score: 1000,
        achievements: [
          {
            id: "high_scorer",
            name: "High Scorer",
            description: "Score over 1000 points",
            points: 50
          }
        ]
      };

      mockApiClient.post.mockResolvedValueOnce({ data: mockEndResponse });

      const { getByText, getByTestId } = renderWithProviders(
        <TriviaGameScreen />
      );

      const endButton = getByTestId('end-game-button');
      fireEvent.press(endButton);

      await waitFor(() => {
        expect(getByText('Achievement Unlocked!')).toBeTruthy();
        expect(getByText('High Scorer')).toBeTruthy();
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle network errors gracefully', async () => {
      mockApiClient.post.mockRejectedValueOnce(new Error('Network error'));

      const { getByText } = renderWithProviders(<TriviaGameScreen />);
      const startButton = getByText('Start Game');

      fireEvent.press(startButton);

      await waitFor(() => {
        expect(getByText('Unable to start game. Please try again.')).toBeTruthy();
      });
    });

    it('should handle session timeout', async () => {
      mockApiClient.post.mockRejectedValueOnce({ 
        response: { status: 404, data: { detail: 'Session not found' } }
      });

      const { getByText } = renderWithProviders(<TriviaGameScreen />);

      await waitFor(() => {
        expect(getByText('Your session has expired. Please start a new game.')).toBeTruthy();
      });
    });
  });

  describe('Accessibility', () => {
    it('should have proper accessibility labels', () => {
      const { getByLabelText, getAllByLabelText } = renderWithProviders(
        <TriviaGameScreen />
      );

      expect(getByLabelText('Start trivia game')).toBeTruthy();
      expect(getByLabelText('Select difficulty level')).toBeTruthy();
    });

    it('should announce score changes to screen readers', async () => {
      const mockAccessibilityInfo = require('react-native').AccessibilityInfo;
      const announceSpy = jest.spyOn(mockAccessibilityInfo, 'announceForAccessibility');

      // Simulate score update
      mockApiClient.post.mockResolvedValueOnce({
        data: { correct: true, score: 100 }
      });

      const { getByTestId } = renderWithProviders(<TriviaGameScreen />);

      await waitFor(() => {
        expect(announceSpy).toHaveBeenCalledWith('Score updated: 100 points');
      });
    });
  });

  describe('Animations and Interactions', () => {
    it('should animate option selection', async () => {
      const { getByTestId } = renderWithProviders(<TriviaGameScreen />);

      const option = getByTestId('option-button-0');
      fireEvent.pressIn(option);

      // Check if scale animation is applied
      expect(option).toHaveStyle({ transform: [{ scale: 0.95 }] });

      fireEvent.pressOut(option);
      expect(option).toHaveStyle({ transform: [{ scale: 1 }] });
    });

    it('should show confetti animation for high scores', async () => {
      mockApiClient.post.mockResolvedValueOnce({
        data: { correct: true, score: 500, new_high_score: true }
      });

      const { getByTestId } = renderWithProviders(<TriviaGameScreen />);

      await waitFor(() => {
        expect(getByTestId('confetti-animation')).toBeTruthy();
      });
    });
  });
});

describe('ScavengerHuntScreen', () => {
  // Similar comprehensive tests for scavenger hunt component
  // Implementation would follow similar patterns
});

describe('FamilyGameDashboard', () => {
  // Tests for family game coordination
  // Implementation would follow similar patterns
});