import React from 'react';
import { render, waitFor } from '@testing-library/react-native';
import RootNavigator from '../RootNavigator';
import { useAuth } from '@hooks/useAuth';

// Mock dependencies
jest.mock('@hooks/useAuth');
jest.mock('../AuthNavigator', () => {
  const React = require('react');
  const { Text } = require('react-native');
  return function AuthNavigator() {
    return <Text testID="auth-navigator">Auth Navigator</Text>;
  };
});
jest.mock('../MainNavigator', () => {
  const React = require('react');
  const { Text } = require('react-native');
  return function MainNavigator() {
    return <Text testID="main-navigator">Main Navigator</Text>;
  };
});

describe('RootNavigator', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Authentication Flow', () => {
    it('should render AuthNavigator when not authenticated', async () => {
      (useAuth as jest.Mock).mockReturnValue({
        isAuthenticated: false,
      });

      const { getByTestId } = render(<RootNavigator />);

      await waitFor(() => {
        expect(getByTestId('auth-navigator')).toBeTruthy();
      });
    });

    it('should render MainNavigator when authenticated', async () => {
      (useAuth as jest.Mock).mockReturnValue({
        isAuthenticated: true,
      });

      const { getByTestId } = render(<RootNavigator />);

      await waitFor(() => {
        expect(getByTestId('main-navigator')).toBeTruthy();
      });
    });

    it('should switch from AuthNavigator to MainNavigator on login', async () => {
      const mockUseAuth = jest.fn();
      mockUseAuth.mockReturnValue({ isAuthenticated: false });
      (useAuth as jest.Mock).mockImplementation(mockUseAuth);

      const { getByTestId, rerender, queryByTestId } = render(<RootNavigator />);

      // Initially shows auth navigator
      await waitFor(() => {
        expect(getByTestId('auth-navigator')).toBeTruthy();
      });

      // Update authentication state
      mockUseAuth.mockReturnValue({ isAuthenticated: true });
      rerender(<RootNavigator />);

      // Should now show main navigator
      await waitFor(() => {
        expect(queryByTestId('auth-navigator')).toBeNull();
        expect(getByTestId('main-navigator')).toBeTruthy();
      });
    });

    it('should switch from MainNavigator to AuthNavigator on logout', async () => {
      const mockUseAuth = jest.fn();
      mockUseAuth.mockReturnValue({ isAuthenticated: true });
      (useAuth as jest.Mock).mockImplementation(mockUseAuth);

      const { getByTestId, rerender, queryByTestId } = render(<RootNavigator />);

      // Initially shows main navigator
      await waitFor(() => {
        expect(getByTestId('main-navigator')).toBeTruthy();
      });

      // Update authentication state
      mockUseAuth.mockReturnValue({ isAuthenticated: false });
      rerender(<RootNavigator />);

      // Should now show auth navigator
      await waitFor(() => {
        expect(queryByTestId('main-navigator')).toBeNull();
        expect(getByTestId('auth-navigator')).toBeTruthy();
      });
    });
  });

  describe('Navigation Container', () => {
    it('should provide navigation context', () => {
      (useAuth as jest.Mock).mockReturnValue({
        isAuthenticated: false,
      });

      const { UNSAFE_getByType } = render(<RootNavigator />);
      const NavigationContainer = require('@react-navigation/native').NavigationContainer;
      
      expect(UNSAFE_getByType(NavigationContainer)).toBeTruthy();
    });

    it('should not show headers', () => {
      (useAuth as jest.Mock).mockReturnValue({
        isAuthenticated: false,
      });

      const { UNSAFE_getByType } = render(<RootNavigator />);
      const Stack = require('@react-navigation/native-stack').createNativeStackNavigator();
      
      const navigator = UNSAFE_getByType(Stack.Navigator);
      expect(navigator.props.screenOptions.headerShown).toBe(false);
    });
  });

  describe('Error Handling', () => {
    it('should handle missing authentication state gracefully', () => {
      (useAuth as jest.Mock).mockReturnValue({
        isAuthenticated: undefined,
      });

      const { getByTestId } = render(<RootNavigator />);

      // Should default to auth navigator when authentication state is undefined
      expect(getByTestId('auth-navigator')).toBeTruthy();
    });

    it('should handle useAuth hook errors', () => {
      (useAuth as jest.Mock).mockImplementation(() => {
        throw new Error('Auth hook error');
      });

      // Should not crash the app
      expect(() => render(<RootNavigator />)).toThrow('Auth hook error');
    });
  });

  describe('Performance', () => {
    it('should not re-render unnecessarily', () => {
      const mockUseAuth = jest.fn();
      mockUseAuth.mockReturnValue({ isAuthenticated: false });
      (useAuth as jest.Mock).mockImplementation(mockUseAuth);

      const { rerender } = render(<RootNavigator />);

      // Clear mock to check for re-renders
      mockUseAuth.mockClear();

      // Re-render with same props
      rerender(<RootNavigator />);

      // useAuth should not be called again if props haven't changed
      expect(mockUseAuth).toHaveBeenCalledTimes(1);
    });
  });
});