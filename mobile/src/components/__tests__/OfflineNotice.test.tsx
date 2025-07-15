import React from 'react';
import { render, fireEvent, waitFor } from '@/utils/test-utils';
import { NetInfo } from '@react-native-community/netinfo';
import OfflineNotice from '../navigation/OfflineNotice';
import { offlineManager } from '@/services/OfflineManager';

// Mock dependencies
jest.mock('@react-native-community/netinfo', () => ({
  addEventListener: jest.fn(),
  fetch: jest.fn(),
}));
jest.mock('@/services/OfflineManager');
jest.mock('@expo/vector-icons', () => ({
  MaterialIcons: 'Icon',
  MaterialCommunityIcons: 'Icon',
}));

describe('OfflineNotice', () => {
  const mockNetInfoUnsubscribe = jest.fn();
  const mockOnRetry = jest.fn();
  
  const mockConnectedState = {
    isConnected: true,
    isInternetReachable: true,
    type: 'wifi',
    details: {
      isConnectionExpensive: false,
      cellularGeneration: null,
    },
  };
  
  const mockOfflineState = {
    isConnected: false,
    isInternetReachable: false,
    type: 'none',
    details: null,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (NetInfo.addEventListener as jest.Mock).mockReturnValue(mockNetInfoUnsubscribe);
    (NetInfo.fetch as jest.Mock).mockResolvedValue(mockConnectedState);
    (offlineManager.getOfflineData as jest.Mock).mockReturnValue({
      cachedRoutes: 3,
      cachedStories: 12,
      downloadedMaps: 2,
      lastSync: new Date(Date.now() - 3600000), // 1 hour ago
    });
  });

  it('renders nothing when online', async () => {
    const { queryByText } = render(<OfflineNotice />);
    
    await waitFor(() => {
      expect(queryByText(/offline/i)).toBeNull();
    });
  });

  it('shows offline notice when disconnected', async () => {
    (NetInfo.fetch as jest.Mock).mockResolvedValue(mockOfflineState);
    
    const { getByText } = render(<OfflineNotice />);
    
    await waitFor(() => {
      expect(getByText('You are offline')).toBeTruthy();
    });
  });

  it('displays offline data availability', async () => {
    (NetInfo.fetch as jest.Mock).mockResolvedValue(mockOfflineState);
    
    const { getByText } = render(<OfflineNotice />);
    
    await waitFor(() => {
      expect(getByText(/3 routes available offline/)).toBeTruthy();
      expect(getByText(/12 stories cached/)).toBeTruthy();
      expect(getByText(/2 map areas downloaded/)).toBeTruthy();
    });
  });

  it('shows last sync time', async () => {
    (NetInfo.fetch as jest.Mock).mockResolvedValue(mockOfflineState);
    
    const { getByText } = render(<OfflineNotice />);
    
    await waitFor(() => {
      expect(getByText(/Last synced: 1 hour ago/)).toBeTruthy();
    });
  });

  it('handles retry connection', async () => {
    (NetInfo.fetch as jest.Mock).mockResolvedValue(mockOfflineState);
    
    const { getByText } = render(
      <OfflineNotice onRetry={mockOnRetry} />
    );
    
    await waitFor(() => {
      const retryButton = getByText('Retry');
      fireEvent.press(retryButton);
    });
    
    expect(mockOnRetry).toHaveBeenCalled();
    expect(NetInfo.fetch).toHaveBeenCalled();
  });

  it('shows different message for limited connectivity', async () => {
    (NetInfo.fetch as jest.Mock).mockResolvedValue({
      isConnected: true,
      isInternetReachable: false,
      type: 'wifi',
      details: null,
    });
    
    const { getByText } = render(<OfflineNotice />);
    
    await waitFor(() => {
      expect(getByText('Limited connectivity')).toBeTruthy();
      expect(getByText(/Some features may not work/)).toBeTruthy();
    });
  });

  it('displays connection type when available', async () => {
    (NetInfo.fetch as jest.Mock).mockResolvedValue({
      ...mockOfflineState,
      type: 'cellular',
      details: {
        cellularGeneration: '4g',
      },
    });
    
    const { getByText } = render(<OfflineNotice />);
    
    await waitFor(() => {
      expect(getByText(/Cellular 4G detected but no internet/)).toBeTruthy();
    });
  });

  it('auto-hides after reconnection', async () => {
    const { rerender, queryByText } = render(<OfflineNotice />);
    
    // Start offline
    const mockListener = (NetInfo.addEventListener as jest.Mock).mock.calls[0][0];
    mockListener(mockOfflineState);
    
    await waitFor(() => {
      expect(queryByText('You are offline')).toBeTruthy();
    });
    
    // Reconnect
    mockListener(mockConnectedState);
    
    await waitFor(() => {
      expect(queryByText('You are offline')).toBeNull();
    });
  });

  it('shows persistent mode option', async () => {
    (NetInfo.fetch as jest.Mock).mockResolvedValue(mockOfflineState);
    
    const { getByText } = render(
      <OfflineNotice showPersistentMode={true} />
    );
    
    await waitFor(() => {
      expect(getByText('Stay offline')).toBeTruthy();
    });
    
    const stayOfflineButton = getByText('Stay offline');
    fireEvent.press(stayOfflineButton);
    
    expect(offlineManager.enablePersistentOfflineMode).toHaveBeenCalled();
  });

  it('displays download progress when syncing', async () => {
    (offlineManager.isSyncing as jest.Mock).mockReturnValue(true);
    (offlineManager.getSyncProgress as jest.Mock).mockReturnValue({
      current: 45,
      total: 100,
      percentage: 45,
    });
    
    const { getByText, getByTestId } = render(<OfflineNotice />);
    
    await waitFor(() => {
      expect(getByText(/Syncing offline data/)).toBeTruthy();
      expect(getByText('45%')).toBeTruthy();
      expect(getByTestId('sync-progress-bar')).toBeTruthy();
    });
  });

  it('handles manual sync trigger', async () => {
    (NetInfo.fetch as jest.Mock).mockResolvedValue(mockOfflineState);
    
    const { getByTestId } = render(<OfflineNotice />);
    
    await waitFor(() => {
      const syncButton = getByTestId('sync-now-button');
      fireEvent.press(syncButton);
    });
    
    expect(offlineManager.syncOfflineData).toHaveBeenCalled();
  });

  it('shows warning for expensive connection', async () => {
    (NetInfo.fetch as jest.Mock).mockResolvedValue({
      isConnected: true,
      isInternetReachable: true,
      type: 'cellular',
      details: {
        isConnectionExpensive: true,
        cellularGeneration: '3g',
      },
    });
    
    const { getByText } = render(
      <OfflineNotice showConnectionWarnings={true} />
    );
    
    await waitFor(() => {
      expect(getByText(/Using cellular data/)).toBeTruthy();
      expect(getByText(/May incur charges/)).toBeTruthy();
    });
  });

  it('collapses to minimal view', async () => {
    (NetInfo.fetch as jest.Mock).mockResolvedValue(mockOfflineState);
    
    const { getByTestId, queryByText } = render(
      <OfflineNotice collapsible={true} />
    );
    
    await waitFor(() => {
      const collapseButton = getByTestId('collapse-button');
      fireEvent.press(collapseButton);
    });
    
    await waitFor(() => {
      expect(queryByText(/3 routes available offline/)).toBeNull();
      expect(getByTestId('minimal-offline-indicator')).toBeTruthy();
    });
  });

  it('cleanup unsubscribes from NetInfo', () => {
    const { unmount } = render(<OfflineNotice />);
    
    unmount();
    
    expect(mockNetInfoUnsubscribe).toHaveBeenCalled();
  });

  it('handles offline manager errors gracefully', async () => {
    (NetInfo.fetch as jest.Mock).mockResolvedValue(mockOfflineState);
    (offlineManager.getOfflineData as jest.Mock).mockImplementation(() => {
      throw new Error('Offline manager error');
    });
    
    const { getByText, queryByText } = render(<OfflineNotice />);
    
    await waitFor(() => {
      expect(getByText('You are offline')).toBeTruthy();
      expect(queryByText(/routes available/)).toBeNull();
    });
  });

  it('shows airplane mode detection', async () => {
    (NetInfo.fetch as jest.Mock).mockResolvedValue({
      ...mockOfflineState,
      type: 'unknown',
      details: {
        isAirplaneMode: true,
      },
    });
    
    const { getByText } = render(<OfflineNotice />);
    
    await waitFor(() => {
      expect(getByText(/Airplane mode is on/)).toBeTruthy();
    });
  });

  it('provides offline mode tips', async () => {
    (NetInfo.fetch as jest.Mock).mockResolvedValue(mockOfflineState);
    
    const { getByText, getByTestId } = render(
      <OfflineNotice showTips={true} />
    );
    
    await waitFor(() => {
      const tipsButton = getByTestId('offline-tips-button');
      fireEvent.press(tipsButton);
    });
    
    await waitFor(() => {
      expect(getByText('Offline Mode Tips')).toBeTruthy();
      expect(getByText(/Download maps for your route/)).toBeTruthy();
      expect(getByText(/Cache stories before traveling/)).toBeTruthy();
    });
  });
});