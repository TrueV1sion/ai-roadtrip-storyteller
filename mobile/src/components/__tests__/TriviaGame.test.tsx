import React from 'react';
import { render, fireEvent, waitFor } from '@/utils/test-utils';
import { Alert } from 'react-native';
import TriviaGameComponent from '../games/TriviaGame';
import { triviaGameEngine, TriviaGame, TriviaQuestion } from '@/services/gameEngine/TriviaGameEngine';
import { locationService } from '@/services/locationService';
import { GameDifficulty } from '@/services/gameEngine/GameStateManager';

// Mock dependencies
jest.mock('@/services/gameEngine/TriviaGameEngine');
jest.mock('@/services/locationService');
jest.mock('@expo/vector-icons', () => ({
  Ionicons: 'Icon',
}));

// Mock Alert
jest.spyOn(Alert, 'alert');

describe('TriviaGameComponent', () => {
  const mockOnClose = jest.fn();
  const mockLocation = {
    latitude: 37.7749,
    longitude: -122.4194,
    timestamp: Date.now(),
    accuracy: 10,
    altitude: null,
    altitudeAccuracy: null,
    heading: null,
    speed: null,
  };

  const mockQuestion: TriviaQuestion = {
    id: 'q1',
    question: 'What is the capital of California?',
    options: ['Los Angeles', 'San Francisco', 'Sacramento', 'San Diego'],
    correctOptionIndex: 2,
    category: 'Geography',
    difficulty: GameDifficulty.MEDIUM,
    explanation: 'Sacramento has been the capital of California since 1854.',
    timeLimit: 30,
  };

  const mockGame: TriviaGame = {
    id: 'game1',
    questions: [mockQuestion],
    currentQuestionIndex: 0,
    score: 0,
    maxScore: 100,
    correctAnswers: 0,
    incorrectAnswers: 0,
    skippedAnswers: 0,
    startTime: Date.now(),
    endTime: null,
    isCompleted: false,
    difficulty: GameDifficulty.MEDIUM,
    categories: ['Geography'],
  };

  const mockResult = {
    score: 100,
    maxScore: 100,
    correctAnswers: 1,
    incorrectAnswers: 0,
    skippedAnswers: 0,
    percentageCorrect: 100,
    timeSpentSeconds: 45,
    difficulty: GameDifficulty.MEDIUM,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    (locationService.getCurrentLocation as jest.Mock).mockResolvedValue(mockLocation);
    (locationService.getSimulatedLocation as jest.Mock).mockReturnValue(mockLocation);
    (triviaGameEngine.generateGame as jest.Mock).mockReturnValue(mockGame);
    (triviaGameEngine.getActiveGame as jest.Mock).mockReturnValue(mockGame);
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  it('renders loading state initially', () => {
    const { getByText } = render(<TriviaGameComponent onClose={mockOnClose} />);
    
    expect(getByText('Preparing your trivia game...')).toBeTruthy();
  });

  it('initializes game with location', async () => {
    const { getByText } = render(
      <TriviaGameComponent 
        onClose={mockOnClose}
        location={mockLocation}
        difficulty={GameDifficulty.HARD}
        questionCount={10}
        categories={['History', 'Science']}
      />
    );
    
    await waitFor(() => {
      expect(triviaGameEngine.generateGame).toHaveBeenCalledWith(
        mockLocation,
        GameDifficulty.HARD,
        10,
        ['History', 'Science']
      );
    });
  });

  it('gets current location if not provided', async () => {
    render(<TriviaGameComponent onClose={mockOnClose} />);
    
    await waitFor(() => {
      expect(locationService.getCurrentLocation).toHaveBeenCalled();
    });
  });

  it('falls back to simulated location on error', async () => {
    (locationService.getCurrentLocation as jest.Mock).mockRejectedValue(new Error('Location error'));
    
    render(<TriviaGameComponent onClose={mockOnClose} />);
    
    await waitFor(() => {
      expect(locationService.getSimulatedLocation).toHaveBeenCalled();
    });
  });

  it('displays question after loading', async () => {
    const { getByText } = render(<TriviaGameComponent onClose={mockOnClose} />);
    
    await waitFor(() => {
      expect(getByText('What is the capital of California?')).toBeTruthy();
      expect(getByText('Question 1/1')).toBeTruthy();
      expect(getByText('GEOGRAPHY')).toBeTruthy();
    });
  });

  it('displays all answer options', async () => {
    const { getByText } = render(<TriviaGameComponent onClose={mockOnClose} />);
    
    await waitFor(() => {
      expect(getByText('A. Los Angeles')).toBeTruthy();
      expect(getByText('B. San Francisco')).toBeTruthy();
      expect(getByText('C. Sacramento')).toBeTruthy();
      expect(getByText('D. San Diego')).toBeTruthy();
    });
  });

  it('handles correct answer selection', async () => {
    (triviaGameEngine.answerQuestion as jest.Mock).mockReturnValue(true);
    
    const { getByText } = render(<TriviaGameComponent onClose={mockOnClose} />);
    
    await waitFor(() => {
      const correctOption = getByText('C. Sacramento');
      fireEvent.press(correctOption);
    });
    
    await waitFor(() => {
      expect(triviaGameEngine.answerQuestion).toHaveBeenCalledWith(2);
      expect(getByText('Correct!')).toBeTruthy();
      expect(getByText('Sacramento has been the capital of California since 1854.')).toBeTruthy();
    });
  });

  it('handles incorrect answer selection', async () => {
    (triviaGameEngine.answerQuestion as jest.Mock).mockReturnValue(false);
    
    const { getByText } = render(<TriviaGameComponent onClose={mockOnClose} />);
    
    await waitFor(() => {
      const incorrectOption = getByText('A. Los Angeles');
      fireEvent.press(incorrectOption);
    });
    
    await waitFor(() => {
      expect(triviaGameEngine.answerQuestion).toHaveBeenCalledWith(0);
      expect(getByText('Incorrect!')).toBeTruthy();
    });
  });

  it('handles skip button', async () => {
    const { getByText } = render(<TriviaGameComponent onClose={mockOnClose} />);
    
    await waitFor(() => {
      const skipButton = getByText('Skip');
      fireEvent.press(skipButton);
    });
    
    await waitFor(() => {
      expect(triviaGameEngine.skipQuestion).toHaveBeenCalled();
    });
  });

  it('shows quit confirmation on close', async () => {
    const { getByTestId } = render(<TriviaGameComponent onClose={mockOnClose} />);
    
    await waitFor(() => {
      const closeButton = getByTestId('close-button');
      fireEvent.press(closeButton);
    });
    
    expect(Alert.alert).toHaveBeenCalledWith(
      'Quit Game',
      'Are you sure you want to quit? Your progress will be lost.',
      expect.arrayContaining([
        expect.objectContaining({ text: 'Cancel' }),
        expect.objectContaining({ text: 'Quit' }),
      ])
    );
  });

  it('displays timer countdown', async () => {
    const { getByText } = render(<TriviaGameComponent onClose={mockOnClose} />);
    
    await waitFor(() => {
      expect(getByText('30s')).toBeTruthy();
    });
    
    // Advance timer by 5 seconds
    jest.advanceTimersByTime(5000);
    
    await waitFor(() => {
      expect(getByText('25s')).toBeTruthy();
    });
  });

  it('auto-skips when time runs out', async () => {
    const { getByText } = render(<TriviaGameComponent onClose={mockOnClose} />);
    
    await waitFor(() => {
      expect(getByText('30s')).toBeTruthy();
    });
    
    // Advance timer to timeout
    jest.advanceTimersByTime(30000);
    
    await waitFor(() => {
      expect(triviaGameEngine.skipQuestion).toHaveBeenCalled();
    });
  });

  it('shows results when game is completed', async () => {
    (triviaGameEngine.getActiveGame as jest.Mock).mockReturnValue({
      ...mockGame,
      isCompleted: true,
    });
    (triviaGameEngine.completeGame as jest.Mock).mockReturnValue(mockResult);
    
    const { getByText } = render(<TriviaGameComponent onClose={mockOnClose} />);
    
    // Answer a question to trigger completion
    await waitFor(() => {
      const option = getByText('C. Sacramento');
      fireEvent.press(option);
    });
    
    // Wait for auto-advance
    jest.advanceTimersByTime(3000);
    
    await waitFor(() => {
      expect(getByText('Game Results')).toBeTruthy();
      expect(getByText('100')).toBeTruthy();
      expect(getByText('/100')).toBeTruthy();
      expect(getByText('100% Correct')).toBeTruthy();
      expect(getByText('1 Correct')).toBeTruthy();
      expect(getByText('0 Incorrect')).toBeTruthy();
      expect(getByText('0 Skipped')).toBeTruthy();
    });
  });

  it('handles play again', async () => {
    (triviaGameEngine.getActiveGame as jest.Mock).mockReturnValue({
      ...mockGame,
      isCompleted: true,
    });
    (triviaGameEngine.completeGame as jest.Mock).mockReturnValue(mockResult);
    
    const { getByText } = render(<TriviaGameComponent onClose={mockOnClose} />);
    
    // Complete the game
    await waitFor(() => {
      const option = getByText('C. Sacramento');
      fireEvent.press(option);
    });
    
    jest.advanceTimersByTime(3000);
    
    await waitFor(() => {
      const playAgainButton = getByText('Play Again');
      fireEvent.press(playAgainButton);
    });
    
    // Advance timer for re-initialization
    jest.advanceTimersByTime(500);
    
    await waitFor(() => {
      // Should generate a new game
      expect(triviaGameEngine.generateGame).toHaveBeenCalledTimes(2);
    });
  });

  it('handles exit from results', async () => {
    (triviaGameEngine.getActiveGame as jest.Mock).mockReturnValue({
      ...mockGame,
      isCompleted: true,
    });
    (triviaGameEngine.completeGame as jest.Mock).mockReturnValue(mockResult);
    
    const { getByText } = render(<TriviaGameComponent onClose={mockOnClose} />);
    
    // Complete the game
    await waitFor(() => {
      const option = getByText('C. Sacramento');
      fireEvent.press(option);
    });
    
    jest.advanceTimersByTime(3000);
    
    await waitFor(() => {
      const exitButton = getByText('Exit');
      fireEvent.press(exitButton);
    });
    
    expect(mockOnClose).toHaveBeenCalled();
  });

  it('disables options after selection', async () => {
    const { getByText } = render(<TriviaGameComponent onClose={mockOnClose} />);
    
    await waitFor(() => {
      const option = getByText('C. Sacramento');
      fireEvent.press(option);
    });
    
    // Try to press another option
    const anotherOption = getByText('A. Los Angeles');
    fireEvent.press(anotherOption);
    
    // Should only register one answer
    expect(triviaGameEngine.answerQuestion).toHaveBeenCalledTimes(1);
  });

  it('formats time correctly in results', async () => {
    (triviaGameEngine.getActiveGame as jest.Mock).mockReturnValue({
      ...mockGame,
      isCompleted: true,
    });
    (triviaGameEngine.completeGame as jest.Mock).mockReturnValue({
      ...mockResult,
      timeSpentSeconds: 125, // 2m 5s
    });
    
    const { getByText } = render(<TriviaGameComponent onClose={mockOnClose} />);
    
    // Complete the game
    await waitFor(() => {
      const option = getByText('C. Sacramento');
      fireEvent.press(option);
    });
    
    jest.advanceTimersByTime(3000);
    
    await waitFor(() => {
      expect(getByText('Time: 2m 5s')).toBeTruthy();
    });
  });
});