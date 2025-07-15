import React from 'react';
import { renderHook, act } from '@testing-library/react-hooks';
import { render, fireEvent } from '@testing-library/react-native';
import { Text, Button } from 'react-native';
import { AppProvider, useApp } from '../AppContext';
import AsyncStorage from '@react-native-async-storage/async-storage';

jest.mock('@react-native-async-storage/async-storage');

describe('AppContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (AsyncStorage.getItem as jest.Mock).mockResolvedValue(null);
    (AsyncStorage.setItem as jest.Mock).mockResolvedValue(undefined);
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <AppProvider>{children}</AppProvider>
  );

  it('provides default values', () => {
    const { result } = renderHook(() => useApp(), { wrapper });

    expect(result.current.theme).toBe('light');
    expect(result.current.user).toBeNull();
    expect(result.current.preferences).toEqual({
      voiceEnabled: true,
      autoPlay: true,
      language: 'en',
    });
  });

  it('loads saved preferences on mount', async () => {
    const savedPrefs = {
      voiceEnabled: false,
      autoPlay: false,
      language: 'es',
    };
    
    (AsyncStorage.getItem as jest.Mock).mockResolvedValue(
      JSON.stringify(savedPrefs)
    );

    const { result, waitForNextUpdate } = renderHook(() => useApp(), { wrapper });

    await waitForNextUpdate();

    expect(AsyncStorage.getItem).toHaveBeenCalledWith('user_preferences');
    expect(result.current.preferences).toEqual(savedPrefs);
  });

  it('toggles theme', async () => {
    const { result } = renderHook(() => useApp(), { wrapper });

    expect(result.current.theme).toBe('light');

    await act(async () => {
      result.current.toggleTheme();
    });

    expect(result.current.theme).toBe('dark');
    expect(AsyncStorage.setItem).toHaveBeenCalledWith('theme', 'dark');

    await act(async () => {
      result.current.toggleTheme();
    });

    expect(result.current.theme).toBe('light');
  });

  it('sets user', async () => {
    const { result } = renderHook(() => useApp(), { wrapper });

    const testUser = {
      id: '1',
      name: 'Test User',
      email: 'test@example.com',
    };

    await act(async () => {
      result.current.setUser(testUser);
    });

    expect(result.current.user).toEqual(testUser);
    expect(AsyncStorage.setItem).toHaveBeenCalledWith(
      'current_user',
      JSON.stringify(testUser)
    );
  });

  it('updates preferences', async () => {
    const { result } = renderHook(() => useApp(), { wrapper });

    await act(async () => {
      result.current.updatePreferences({
        voiceEnabled: false,
        language: 'fr',
      });
    });

    expect(result.current.preferences).toEqual({
      voiceEnabled: false,
      autoPlay: true,
      language: 'fr',
    });

    expect(AsyncStorage.setItem).toHaveBeenCalledWith(
      'user_preferences',
      JSON.stringify({
        voiceEnabled: false,
        autoPlay: true,
        language: 'fr',
      })
    );
  });

  it('resets app state', async () => {
    const { result } = renderHook(() => useApp(), { wrapper });

    // Set some state first
    await act(async () => {
      result.current.setUser({ id: '1', name: 'Test', email: 'test@test.com' });
      result.current.toggleTheme();
      result.current.updatePreferences({ voiceEnabled: false });
    });

    // Reset
    await act(async () => {
      result.current.resetApp();
    });

    expect(result.current.user).toBeNull();
    expect(result.current.theme).toBe('light');
    expect(result.current.preferences).toEqual({
      voiceEnabled: true,
      autoPlay: true,
      language: 'en',
    });

    expect(AsyncStorage.removeItem).toHaveBeenCalledWith('current_user');
    expect(AsyncStorage.removeItem).toHaveBeenCalledWith('theme');
    expect(AsyncStorage.removeItem).toHaveBeenCalledWith('user_preferences');
  });

  it('provides context to components', () => {
    const TestComponent = () => {
      const { theme, toggleTheme } = useApp();
      return (
        <>
          <Text testID="theme-text">{theme}</Text>
          <Button title="Toggle" onPress={toggleTheme} testID="toggle-button" />
        </>
      );
    };

    const { getByTestId } = render(
      <AppProvider>
        <TestComponent />
      </AppProvider>
    );

    expect(getByTestId('theme-text').children[0]).toBe('light');

    fireEvent.press(getByTestId('toggle-button'));

    expect(getByTestId('theme-text').children[0]).toBe('dark');
  });

  it('handles loading state', async () => {
    const { result } = renderHook(() => useApp(), { wrapper });

    expect(result.current.isLoading).toBe(true);

    await act(async () => {
      // Wait for initial load
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    expect(result.current.isLoading).toBe(false);
  });

  it('persists journey state', async () => {
    const { result } = renderHook(() => useApp(), { wrapper });

    const journey = {
      id: 'journey-1',
      origin: { latitude: 37.7749, longitude: -122.4194, name: 'San Francisco' },
      destination: { latitude: 34.0522, longitude: -118.2437, name: 'Los Angeles' },
      startTime: new Date().toISOString(),
    };

    await act(async () => {
      result.current.setCurrentJourney(journey);
    });

    expect(result.current.currentJourney).toEqual(journey);
    expect(AsyncStorage.setItem).toHaveBeenCalledWith(
      'current_journey',
      JSON.stringify(journey)
    );
  });

  it('handles offline mode', async () => {
    const { result } = renderHook(() => useApp(), { wrapper });

    await act(async () => {
      result.current.setOfflineMode(true);
    });

    expect(result.current.isOffline).toBe(true);

    // Should cache important data when going offline
    expect(AsyncStorage.setItem).toHaveBeenCalledWith(
      'offline_mode',
      'true'
    );
  });

  it('manages notification preferences', async () => {
    const { result } = renderHook(() => useApp(), { wrapper });

    await act(async () => {
      result.current.updateNotificationSettings({
        enabled: true,
        types: ['journey', 'booking', 'alerts'],
      });
    });

    expect(result.current.notificationSettings).toEqual({
      enabled: true,
      types: ['journey', 'booking', 'alerts'],
    });
  });

  it('throws error when used outside provider', () => {
    // Suppress console.error for this test
    const originalError = console.error;
    console.error = jest.fn();

    expect(() => {
      renderHook(() => useApp());
    }).toThrow('useApp must be used within AppProvider');

    console.error = originalError;
  });
});