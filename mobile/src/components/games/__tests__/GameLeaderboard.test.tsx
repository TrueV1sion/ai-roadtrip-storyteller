import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';

import GameLeaderboard from '../GameLeaderboard';
import { gameApi } from '../../../services/api/gameApi';

// Mock dependencies
jest.mock('../../../services/api/gameApi');

const mockGameApi = gameApi as jest.Mocked<typeof gameApi>;

const mockStore = configureStore({
  reducer: {
    user: (state = { 
      id: 'user123',
      username: 'TestPlayer',
      avatar: 'avatar1',
    }) => state,
    games: (state = {
      currentGame: 'trivia',
    }) => state,
  },
});

const mockLeaderboardData = {
  global: [
    {
      rank: 1,
      userId: 'user456',
      username: 'TopPlayer',
      score: 10000,
      avatar: 'avatar2',
      country: 'US',
    },
    {
      rank: 2,
      userId: 'user789',
      username: 'SecondBest',
      score: 9500,
      avatar: 'avatar3',
      country: 'CA',
    },
    {
      rank: 3,
      userId: 'user123',
      username: 'TestPlayer',
      score: 9000,
      avatar: 'avatar1',
      country: 'US',
    },
  ],
  friends: [
    {
      rank: 1,
      userId: 'friend1',
      username: 'BestFriend',
      score: 8000,
      avatar: 'avatar4',
    },
    {
      rank: 2,
      userId: 'user123',
      username: 'TestPlayer',
      score: 7500,
      avatar: 'avatar1',
    },
  ],
  weekly: [
    {
      rank: 1,
      userId: 'user123',
      username: 'TestPlayer',
      score: 2000,
      avatar: 'avatar1',
      streak: 5,
    },
  ],
};

const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <Provider store={mockStore}>
      {component}
    </Provider>
  );
};

describe('GameLeaderboard Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGameApi.getLeaderboard.mockResolvedValue(mockLeaderboardData);
  });

  it('renders leaderboard tabs', async () => {
    const { getByText } = renderWithProviders(<GameLeaderboard gameType="trivia" />);
    
    await waitFor(() => {
      expect(getByText('Global')).toBeTruthy();
      expect(getByText('Friends')).toBeTruthy();
      expect(getByText('Weekly')).toBeTruthy();
    });
  });

  it('displays global leaderboard by default', async () => {
    const { getByText } = renderWithProviders(<GameLeaderboard gameType="trivia" />);
    
    await waitFor(() => {
      expect(getByText('TopPlayer')).toBeTruthy();
      expect(getByText('10,000')).toBeTruthy();
      expect(getByText('#1')).toBeTruthy();
    });
  });

  it('highlights current user in leaderboard', async () => {
    const { getByTestId } = renderWithProviders(<GameLeaderboard gameType="trivia" />);
    
    await waitFor(() => {
      const userRow = getByTestId('leaderboard-user-user123');
      expect(userRow).toHaveStyle({ backgroundColor: expect.any(String) });
    });
  });

  it('switches between leaderboard tabs', async () => {
    const { getByText } = renderWithProviders(<GameLeaderboard gameType="trivia" />);
    
    await waitFor(() => {
      expect(getByText('TopPlayer')).toBeTruthy();
    });
    
    // Switch to Friends tab
    fireEvent.press(getByText('Friends'));
    
    await waitFor(() => {
      expect(getByText('BestFriend')).toBeTruthy();
      expect(getByText('8,000')).toBeTruthy();
    });
    
    // Switch to Weekly tab
    fireEvent.press(getByText('Weekly'));
    
    await waitFor(() => {
      expect(getByText('5 day streak')).toBeTruthy();
    });
  });

  it('shows loading state while fetching', () => {
    mockGameApi.getLeaderboard.mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 1000))
    );
    
    const { getByTestId } = renderWithProviders(<GameLeaderboard gameType="trivia" />);
    expect(getByTestId('leaderboard-loading')).toBeTruthy();
  });

  it('handles empty leaderboard', async () => {
    mockGameApi.getLeaderboard.mockResolvedValue({
      global: [],
      friends: [],
      weekly: [],
    });
    
    const { getByText } = renderWithProviders(<GameLeaderboard gameType="trivia" />);
    
    await waitFor(() => {
      expect(getByText('No scores yet. Be the first!')).toBeTruthy();
    });
  });

  it('displays achievement badges', async () => {
    const leaderboardWithBadges = {
      ...mockLeaderboardData,
      global: [
        {
          ...mockLeaderboardData.global[0],
          badges: ['speed_demon', 'perfect_score', 'weekly_champion'],
        },
      ],
    };
    
    mockGameApi.getLeaderboard.mockResolvedValue(leaderboardWithBadges);
    
    const { getAllByTestId } = renderWithProviders(<GameLeaderboard gameType="trivia" />);
    
    await waitFor(() => {
      const badges = getAllByTestId(/badge-/);
      expect(badges).toHaveLength(3);
    });
  });

  it('allows filtering by time period', async () => {
    const { getByTestId, getByText } = renderWithProviders(
      <GameLeaderboard gameType="trivia" showFilters={true} />
    );
    
    await waitFor(() => {
      expect(getByTestId('time-filter')).toBeTruthy();
    });
    
    fireEvent.press(getByTestId('time-filter'));
    fireEvent.press(getByText('This Month'));
    
    expect(mockGameApi.getLeaderboard).toHaveBeenCalledWith(
      'trivia',
      expect.objectContaining({ period: 'month' })
    );
  });

  it('supports pull-to-refresh', async () => {
    const { getByTestId } = renderWithProviders(<GameLeaderboard gameType="trivia" />);
    
    await waitFor(() => {
      expect(getByTestId('leaderboard-list')).toBeTruthy();
    });
    
    const list = getByTestId('leaderboard-list');
    fireEvent(list, 'refresh');
    
    await waitFor(() => {
      expect(mockGameApi.getLeaderboard).toHaveBeenCalledTimes(2);
    });
  });

  it('shows user stats summary', async () => {
    const { getByText, getByTestId } = renderWithProviders(
      <GameLeaderboard gameType="trivia" showUserStats={true} />
    );
    
    await waitFor(() => {
      expect(getByTestId('user-stats')).toBeTruthy();
      expect(getByText('Your Rank: #3')).toBeTruthy();
      expect(getByText('Score: 9,000')).toBeTruthy();
    });
  });

  it('displays country flags for global leaderboard', async () => {
    const { getAllByTestId } = renderWithProviders(<GameLeaderboard gameType="trivia" />);
    
    await waitFor(() => {
      const flags = getAllByTestId(/country-flag-/);
      expect(flags).toHaveLength(3);
    });
  });

  it('handles pagination for large leaderboards', async () => {
    const largeLeaderboard = {
      global: Array.from({ length: 50 }, (_, i) => ({
        rank: i + 1,
        userId: `user${i}`,
        username: `Player${i}`,
        score: 10000 - i * 100,
        avatar: `avatar${i}`,
      })),
      hasMore: true,
    };
    
    mockGameApi.getLeaderboard.mockResolvedValue(largeLeaderboard);
    
    const { getByTestId } = renderWithProviders(<GameLeaderboard gameType="trivia" />);
    
    await waitFor(() => {
      const list = getByTestId('leaderboard-list');
      expect(list).toBeTruthy();
    });
    
    // Scroll to bottom to trigger pagination
    const list = getByTestId('leaderboard-list');
    fireEvent.scroll(list, {
      nativeEvent: {
        contentOffset: { y: 2000 },
        contentSize: { height: 2500 },
        layoutMeasurement: { height: 600 },
      },
    });
    
    await waitFor(() => {
      expect(mockGameApi.getLeaderboard).toHaveBeenCalledWith(
        'trivia',
        expect.objectContaining({ offset: 50 })
      );
    });
  });

  it('allows viewing player profiles', async () => {
    const onViewProfile = jest.fn();
    const { getByText } = renderWithProviders(
      <GameLeaderboard gameType="trivia" onViewProfile={onViewProfile} />
    );
    
    await waitFor(() => {
      expect(getByText('TopPlayer')).toBeTruthy();
    });
    
    fireEvent.press(getByText('TopPlayer'));
    
    expect(onViewProfile).toHaveBeenCalledWith({
      userId: 'user456',
      username: 'TopPlayer',
    });
  });

  it('shows improvement indicators', async () => {
    const leaderboardWithChanges = {
      global: [
        {
          ...mockLeaderboardData.global[0],
          previousRank: 3,
          improvement: 2,
        },
      ],
    };
    
    mockGameApi.getLeaderboard.mockResolvedValue(leaderboardWithChanges);
    
    const { getByTestId } = renderWithProviders(<GameLeaderboard gameType="trivia" />);
    
    await waitFor(() => {
      const improvement = getByTestId('rank-improvement-user456');
      expect(improvement).toBeTruthy();
      expect(improvement).toHaveTextContent('↑2');
    });
  });
});