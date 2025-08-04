/**
 * Secure Authentication Hook
 * Provides secure token management and auth state
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { AppState, AppStateStatus } from 'react-native';
import { secureTokenManager } from '@/services/security/SecureTokenManager';
import secureStorageService from '@/services/secureStorageService';
import { authService } from '@/services/authService';
import { setUserContext, clearUserContext } from '@/services/sentry/SentryService';
import { logger } from '@/services/logger';
import { User } from '@/types/user';

interface UseSecureAuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: User | null;
  error: Error | null;
  tokenExpiry: number | null;
}

interface UseSecureAuthActions {
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  refreshAuth: () => Promise<boolean>;
  checkBiometricAvailability: () => Promise<boolean>;
  enableBiometricAuth: () => Promise<boolean>;
}

export function useSecureAuth(): UseSecureAuthState & UseSecureAuthActions {
  const [state, setState] = useState<UseSecureAuthState>({
    isAuthenticated: false,
    isLoading: true,
    user: null,
    error: null,
    tokenExpiry: null,
  });

  const appStateRef = useRef<AppStateStatus>(AppState.currentState);
  const refreshTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Initialize secure storage and check auth state
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        // Initialize secure storage
        await secureStorageService.initialize();
        await secureTokenManager.initialize();

        // Check if user is authenticated
        const isAuth = await secureTokenManager.isAuthenticated();
        
        if (isAuth) {
          // Get user data
          const user = await authService.getCurrentUser();
          const expiry = await secureTokenManager.getTokenExpiry();
          
          setState({
            isAuthenticated: true,
            isLoading: false,
            user,
            error: null,
            tokenExpiry: expiry,
          });

          // Set Sentry context
          if (user) {
            await setUserContext({
              id: user.id.toString(),
              username: user.name,
              email: user.email,
            });
          }

          // Schedule token refresh
          scheduleTokenRefresh(expiry);
        } else {
          setState(prev => ({
            ...prev,
            isLoading: false,
          }));
        }
      } catch (error) {
        logger.error('Failed to initialize auth:', error);
        setState(prev => ({
          ...prev,
          isLoading: false,
          error: error as Error,
        }));
      }
    };

    initializeAuth();
  }, []);

  // Handle app state changes for token refresh
  useEffect(() => {
    const handleAppStateChange = (nextAppState: AppStateStatus) => {
      if (
        appStateRef.current.match(/inactive|background/) &&
        nextAppState === 'active' &&
        state.isAuthenticated
      ) {
        // App came to foreground, check token validity
        checkAndRefreshToken();
      }
      appStateRef.current = nextAppState;
    };

    const subscription = AppState.addEventListener('change', handleAppStateChange);
    return () => subscription.remove();
  }, [state.isAuthenticated]);

  // Schedule automatic token refresh
  const scheduleTokenRefresh = useCallback((expiry: number | null) => {
    if (refreshTimeoutRef.current) {
      clearTimeout(refreshTimeoutRef.current);
    }

    if (!expiry) return;

    const timeUntilExpiry = expiry - Date.now();
    const refreshTime = timeUntilExpiry - (5 * 60 * 1000); // 5 minutes before expiry

    if (refreshTime > 0) {
      refreshTimeoutRef.current = setTimeout(() => {
        checkAndRefreshToken();
      }, refreshTime);
    }
  }, []);

  // Check and refresh token if needed
  const checkAndRefreshToken = useCallback(async () => {
    try {
      const token = await secureTokenManager.getValidAccessToken();
      if (!token) {
        // Token refresh failed, logout user
        await logout();
      } else {
        // Update expiry time
        const expiry = await secureTokenManager.getTokenExpiry();
        setState(prev => ({
          ...prev,
          tokenExpiry: expiry,
        }));
        scheduleTokenRefresh(expiry);
      }
    } catch (error) {
      logger.error('Token refresh check failed:', error);
    }
  }, []);

  // Login function
  const login = useCallback(async (email: string, password: string): Promise<boolean> => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      // Perform login
      const user = await authService.login(email, password);
      
      // Get token expiry
      const expiry = await secureTokenManager.getTokenExpiry();
      
      setState({
        isAuthenticated: true,
        isLoading: false,
        user,
        error: null,
        tokenExpiry: expiry,
      });

      // Set Sentry context
      await setUserContext({
        id: user.id.toString(),
        username: user.name,
        email: user.email,
      });

      // Schedule token refresh
      scheduleTokenRefresh(expiry);

      return true;
    } catch (error) {
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: error as Error,
      }));
      return false;
    }
  }, [scheduleTokenRefresh]);

  // Logout function
  const logout = useCallback(async () => {
    try {
      // Clear tokens
      await authService.logout();
      await secureTokenManager.clearTokens();
      
      // Clear Sentry context
      await clearUserContext();
      
      // Clear refresh timeout
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
      }
      
      setState({
        isAuthenticated: false,
        isLoading: false,
        user: null,
        error: null,
        tokenExpiry: null,
      });
    } catch (error) {
      logger.error('Logout failed:', error);
      // Force clear state even if logout fails
      setState({
        isAuthenticated: false,
        isLoading: false,
        user: null,
        error: error as Error,
        tokenExpiry: null,
      });
    }
  }, []);

  // Refresh authentication
  const refreshAuth = useCallback(async (): Promise<boolean> => {
    try {
      const token = await secureTokenManager.getValidAccessToken();
      if (token) {
        const user = await authService.getCurrentUser();
        const expiry = await secureTokenManager.getTokenExpiry();
        
        setState(prev => ({
          ...prev,
          user,
          tokenExpiry: expiry,
        }));
        
        scheduleTokenRefresh(expiry);
        return true;
      }
      return false;
    } catch (error) {
      logger.error('Auth refresh failed:', error);
      return false;
    }
  }, [scheduleTokenRefresh]);

  // Check biometric availability
  const checkBiometricAvailability = useCallback(async (): Promise<boolean> => {
    try {
      const LocalAuthentication = await import('expo-local-authentication');
      const hasHardware = await LocalAuthentication.hasHardwareAsync();
      const isEnrolled = await LocalAuthentication.isEnrolledAsync();
      return hasHardware && isEnrolled;
    } catch (error) {
      logger.error('Biometric check failed:', error);
      return false;
    }
  }, []);

  // Enable biometric authentication
  const enableBiometricAuth = useCallback(async (): Promise<boolean> => {
    try {
      const available = await checkBiometricAvailability();
      if (!available) {
        throw new Error('Biometric authentication not available');
      }

      // Store a flag in secure storage with biometric protection
      await secureStorageService.setItem('biometric_auth_enabled', 'true', {
        requireAuthentication: true,
        authenticationPrompt: 'Enable biometric authentication',
      });

      return true;
    } catch (error) {
      logger.error('Failed to enable biometric auth:', error);
      setState(prev => ({
        ...prev,
        error: error as Error,
      }));
      return false;
    }
  }, [checkBiometricAvailability]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
      }
    };
  }, []);

  return {
    // State
    isAuthenticated: state.isAuthenticated,
    isLoading: state.isLoading,
    user: state.user,
    error: state.error,
    tokenExpiry: state.tokenExpiry,
    // Actions
    login,
    logout,
    refreshAuth,
    checkBiometricAvailability,
    enableBiometricAuth,
  };
}

// Higher-order component for protected routes
export function withSecureAuth<P extends object>(
  Component: React.ComponentType<P>
): React.ComponentType<P> {
  return (props: P) => {
    const { isAuthenticated, isLoading } = useSecureAuth();
    
    if (isLoading) {
      // Return loading component
      return <LoadingScreen />;
    }
    
    if (!isAuthenticated) {
      // Redirect to login
      return <LoginScreen />;
    }
    
    return <Component {...props} />;
  };
}

// Placeholder components (should be imported from actual components)
const LoadingScreen = () => null;
const LoginScreen = () => null;