import React from 'react';
import { render, fireEvent, waitFor } from '@/utils/test-utils';
import GameLauncher from '../games/GameLauncher';
import { gameStateManager, GameType, GameDifficulty } from '@/services/gameEngine/GameStateManager';
import { locationService } from '@/services/locationService';

// Mock dependencies
jest.mock('@/services/gameEngine/GameStateManager');
jest.mock('@/services/locationService');
jest.mock('@expo/vector-icons', () => ({
  MaterialIcons: 'Icon',
  MaterialCommunityIcons: 'Icon',
  FontAwesome5: 'Icon',
}));
jest.mock('react-native-paper', () => ({
  ...jest.requireActual('react-native-paper'),
  Portal: ({ children }: any) => children,
  Modal: ({ visible, children }: any) => visible ? children : null,
}));

describe('GameLauncher', () => {
  const mockOnGameStart = jest.fn();
  const mockOnClose = jest.fn();
  
  const mockLocation = {
    latitude: 37.7749,
    longitude: -122.4194,
    timestamp: Date.now(),
    accuracy: 10,
  };

  const mockAvailableGames = [
    {
      type: GameType.TRIVIA,
      title: 'Location Trivia',
      description: 'Test your knowledge about nearby places',
      icon: 'quiz',
      difficulty: GameDifficulty.MEDIUM,
      estimatedTime: '5-10 min',
      pointsAvailable: 100,
    },
    {
      type: GameType.SCAVENGER_HUNT,
      title: 'Photo Hunt',
      description: 'Find and photograph landmarks',
      icon: 'camera',
      difficulty: GameDifficulty.EASY,
      estimatedTime: '15-20 min',
      pointsAvailable: 200,
    },
    {
      type: GameType.WORD_SCRAMBLE,
      title: 'Word Challenge',
      description: 'Unscramble location-based words',
      icon: 'text-fields',
      difficulty: GameDifficulty.HARD,
      estimatedTime: '3-5 min',
      pointsAvailable: 50,
    },
  ];

  const mockGameStats = {
    totalGamesPlayed: 42,
    totalPoints: 1850,
    favoriteGame: GameType.TRIVIA,
    averageScore: 75,
    achievements: ['First Game', 'Trivia Master', '10 Day Streak'],
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (locationService.getCurrentLocation as jest.Mock).mockResolvedValue(mockLocation);
    (gameStateManager.getAvailableGames as jest.Mock).mockReturnValue(mockAvailableGames);
    (gameStateManager.getPlayerStats as jest.Mock).mockReturnValue(mockGameStats);
    (gameStateManager.canPlayGame as jest.Mock).mockReturnValue(true);
  });

  it('renders game launcher with available games', () => {
    const { getByText } = render(
      <GameLauncher isVisible={true} onClose={mockOnClose} />
    );
    
    expect(getByText('Choose a Game')).toBeTruthy();
    expect(getByText('Location Trivia')).toBeTruthy();
    expect(getByText('Photo Hunt')).toBeTruthy();
    expect(getByText('Word Challenge')).toBeTruthy();
  });

  it('displays game details', () => {
    const { getByText } = render(
      <GameLauncher isVisible={true} onClose={mockOnClose} />
    );
    
    expect(getByText('Test your knowledge about nearby places')).toBeTruthy();
    expect(getByText('5-10 min')).toBeTruthy();
    expect(getByText('100 pts')).toBeTruthy();
  });

  it('shows difficulty indicators', () => {
    const { getAllByTestId } = render(
      <GameLauncher isVisible={true} onClose={mockOnClose} />
    );
    
    const easyIndicator = getAllByTestId('difficulty-EASY')[0];
    const mediumIndicator = getAllByTestId('difficulty-MEDIUM')[0];
    const hardIndicator = getAllByTestId('difficulty-HARD')[0];
    
    expect(easyIndicator).toBeTruthy();
    expect(mediumIndicator).toBeTruthy();
    expect(hardIndicator).toBeTruthy();
  });

  it('handles game selection', async () => {
    const { getByText } = render(
      <GameLauncher 
        isVisible={true} 
        onClose={mockOnClose}
        onGameStart={mockOnGameStart}
      />
    );
    
    const triviaCard = getByText('Location Trivia').parent?.parent;
    if (triviaCard) {
      fireEvent.press(triviaCard);
    }
    
    await waitFor(() => {
      expect(mockOnGameStart).toHaveBeenCalledWith(GameType.TRIVIA, {
        difficulty: GameDifficulty.MEDIUM,
        location: mockLocation,
      });
    });
  });

  it('shows player stats', async () => {
    const { getByText, getByTestId } = render(
      <GameLauncher isVisible={true} onClose={mockOnClose} />
    );
    
    const statsButton = getByTestId('stats-button');
    fireEvent.press(statsButton);
    
    await waitFor(() => {
      expect(getByText('Your Stats')).toBeTruthy();
      expect(getByText('42 games played')).toBeTruthy();
      expect(getByText('1,850 total points')).toBeTruthy();
      expect(getByText('75% average score')).toBeTruthy();
    });
  });

  it('displays achievements', async () => {
    const { getByText, getByTestId } = render(
      <GameLauncher isVisible={true} onClose={mockOnClose} />
    );
    
    const statsButton = getByTestId('stats-button');
    fireEvent.press(statsButton);
    
    await waitFor(() => {
      expect(getByText('Achievements')).toBeTruthy();
      expect(getByText('First Game')).toBeTruthy();
      expect(getByText('Trivia Master')).toBeTruthy();
      expect(getByText('10 Day Streak')).toBeTruthy();
    });
  });

  it('filters games by difficulty', async () => {
    const { getByText, queryByText } = render(
      <GameLauncher isVisible={true} onClose={mockOnClose} />
    );
    
    // Select easy difficulty filter
    const easyFilter = getByText('Easy');
    fireEvent.press(easyFilter);
    
    await waitFor(() => {
      expect(getByText('Photo Hunt')).toBeTruthy();
      expect(queryByText('Location Trivia')).toBeNull();
      expect(queryByText('Word Challenge')).toBeNull();
    });
  });

  it('shows game preview on long press', async () => {
    const { getByText, getByTestId } = render(
      <GameLauncher isVisible={true} onClose={mockOnClose} />
    );
    
    const triviaCard = getByText('Location Trivia').parent?.parent;
    if (triviaCard) {
      fireEvent(triviaCard, 'onLongPress');
    }
    
    await waitFor(() => {
      expect(getByText('Game Preview')).toBeTruthy();
      expect(getByTestId('game-preview-image')).toBeTruthy();
      expect(getByText(/Sample questions about/)).toBeTruthy();
    });
  });

  it('handles unavailable games', async () => {
    (gameStateManager.canPlayGame as jest.Mock).mockReturnValue(false);
    (gameStateManager.getGameRestriction as jest.Mock).mockReturnValue({
      reason: 'cooldown',
      timeRemaining: 300, // 5 minutes
    });
    
    const { getByText } = render(
      <GameLauncher isVisible={true} onClose={mockOnClose} />
    );
    
    const triviaCard = getByText('Location Trivia').parent?.parent;
    if (triviaCard) {
      fireEvent.press(triviaCard);
    }
    
    await waitFor(() => {
      expect(getByText(/Available in 5 minutes/)).toBeTruthy();
    });
  });

  it('shows loading state while fetching games', () => {
    (gameStateManager.getAvailableGames as jest.Mock).mockReturnValue(null);
    
    const { getByText } = render(
      <GameLauncher isVisible={true} onClose={mockOnClose} />
    );
    
    expect(getByText('Loading games...')).toBeTruthy();
  });

  it('handles location permission denied', async () => {
    (locationService.getCurrentLocation as jest.Mock).mockRejectedValue(
      new Error('Location permission denied')
    );
    
    const { getByText } = render(
      <GameLauncher isVisible={true} onClose={mockOnClose} />
    );
    
    await waitFor(() => {
      expect(getByText(/Location access required/)).toBeTruthy();
      expect(getByText('Enable Location')).toBeTruthy();
    });
  });

  it('shows game recommendations', () => {
    (gameStateManager.getRecommendedGames as jest.Mock).mockReturnValue([
      GameType.TRIVIA,
      GameType.WORD_SCRAMBLE,
    ]);
    
    const { getAllByTestId } = render(
      <GameLauncher isVisible={true} onClose={mockOnClose} />
    );
    
    const recommendedBadges = getAllByTestId('recommended-badge');
    expect(recommendedBadges.length).toBe(2);
  });

  it('displays multiplayer indicator', () => {
    const gamesWithMultiplayer = [
      ...mockAvailableGames,
      {
        type: GameType.COLLABORATIVE_STORY,
        title: 'Story Builder',
        description: 'Create stories with other travelers',
        icon: 'people',
        difficulty: GameDifficulty.MEDIUM,
        estimatedTime: '10-15 min',
        pointsAvailable: 150,
        multiplayer: true,
      },
    ];
    
    (gameStateManager.getAvailableGames as jest.Mock).mockReturnValue(gamesWithMultiplayer);
    
    const { getByTestId } = render(
      <GameLauncher isVisible={true} onClose={mockOnClose} />
    );
    
    expect(getByTestId('multiplayer-indicator')).toBeTruthy();
  });

  it('handles close button', () => {
    const { getByTestId } = render(
      <GameLauncher isVisible={true} onClose={mockOnClose} />
    );
    
    const closeButton = getByTestId('close-button');
    fireEvent.press(closeButton);
    
    expect(mockOnClose).toHaveBeenCalled();
  });

  it('shows daily challenge', () => {
    (gameStateManager.getDailyChallenge as jest.Mock).mockReturnValue({
      type: GameType.TRIVIA,
      title: 'Daily Geography Challenge',
      description: 'Complete for bonus points!',
      bonusPoints: 500,
      expiresIn: 14400, // 4 hours
    });
    
    const { getByText, getByTestId } = render(
      <GameLauncher isVisible={true} onClose={mockOnClose} />
    );
    
    expect(getByText('Daily Challenge')).toBeTruthy();
    expect(getByText('Daily Geography Challenge')).toBeTruthy();
    expect(getByText('+500 bonus pts')).toBeTruthy();
    expect(getByTestId('daily-challenge-timer')).toBeTruthy();
  });

  it('integrates with voice commands', async () => {
    const mockOnVoiceCommand = jest.fn();
    
    const { getByTestId } = render(
      <GameLauncher 
        isVisible={true} 
        onClose={mockOnClose}
        voiceEnabled={true}
        onVoiceCommand={mockOnVoiceCommand}
      />
    );
    
    const voiceButton = getByTestId('voice-select-button');
    fireEvent.press(voiceButton);
    
    await waitFor(() => {
      expect(mockOnVoiceCommand).toHaveBeenCalledWith('startListening');
    });
  });

  it('shows tutorial for new players', () => {
    (gameStateManager.isFirstTime as jest.Mock).mockReturnValue(true);
    
    const { getByText, getByTestId } = render(
      <GameLauncher isVisible={true} onClose={mockOnClose} />
    );
    
    expect(getByText('Welcome to Road Trip Games!')).toBeTruthy();
    expect(getByText(/Earn points and achievements/)).toBeTruthy();
    expect(getByTestId('tutorial-skip-button')).toBeTruthy();
  });
});