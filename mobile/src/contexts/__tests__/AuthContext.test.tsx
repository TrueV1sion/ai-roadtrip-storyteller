import React from 'react';
import { renderHook, act } from '@testing-library/react-hooks';
import { AuthProvider, useAuth } from '../AuthContext';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { authService } from '../../services/authService';

jest.mock('@react-native-async-storage/async-storage');
jest.mock('../../services/authService');

describe('AuthContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (AsyncStorage.getItem as jest.Mock).mockResolvedValue(null);
    (AsyncStorage.setItem as jest.Mock).mockResolvedValue(undefined);
    (AsyncStorage.removeItem as jest.Mock).mockResolvedValue(undefined);
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <AuthProvider>{children}</AuthProvider>
  );

  it('provides default values', () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
    expect(result.current.isLoading).toBe(true);
  });

  it('loads saved auth state on mount', async () => {
    const savedToken = 'saved-token';
    const savedUser = {
      id: '1',
      email: 'test@example.com',
      name: 'Test User',
    };

    (AsyncStorage.getItem as jest.Mock)
      .mockResolvedValueOnce(savedToken)
      .mockResolvedValueOnce(JSON.stringify(savedUser));

    (authService.validateToken as jest.Mock).mockResolvedValue(true);

    const { result, waitForNextUpdate } = renderHook(() => useAuth(), { wrapper });

    await waitForNextUpdate();

    expect(AsyncStorage.getItem).toHaveBeenCalledWith('auth_token');
    expect(AsyncStorage.getItem).toHaveBeenCalledWith('auth_user');
    expect(authService.validateToken).toHaveBeenCalledWith(savedToken);
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user).toEqual(savedUser);
    expect(result.current.token).toBe(savedToken);
    expect(result.current.isLoading).toBe(false);
  });

  it('clears auth state if token is invalid', async () => {
    const savedToken = 'invalid-token';
    
    (AsyncStorage.getItem as jest.Mock).mockResolvedValueOnce(savedToken);
    (authService.validateToken as jest.Mock).mockResolvedValue(false);

    const { result, waitForNextUpdate } = renderHook(() => useAuth(), { wrapper });

    await waitForNextUpdate();

    expect(authService.validateToken).toHaveBeenCalledWith(savedToken);
    expect(AsyncStorage.removeItem).toHaveBeenCalledWith('auth_token');
    expect(AsyncStorage.removeItem).toHaveBeenCalledWith('auth_user');
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
  });

  it('handles login', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    const credentials = {
      email: 'test@example.com',
      password: 'password123',
    };

    const loginResponse = {
      token: 'new-token',
      user: {
        id: '1',
        email: 'test@example.com',
        name: 'Test User',
      },
    };

    (authService.login as jest.Mock).mockResolvedValue(loginResponse);

    await act(async () => {
      await result.current.login(credentials.email, credentials.password);
    });

    expect(authService.login).toHaveBeenCalledWith(credentials.email, credentials.password);
    expect(AsyncStorage.setItem).toHaveBeenCalledWith('auth_token', loginResponse.token);
    expect(AsyncStorage.setItem).toHaveBeenCalledWith('auth_user', JSON.stringify(loginResponse.user));
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user).toEqual(loginResponse.user);
    expect(result.current.token).toBe(loginResponse.token);
  });

  it('handles login failure', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    (authService.login as jest.Mock).mockRejectedValue(new Error('Invalid credentials'));

    await act(async () => {
      try {
        await result.current.login('test@example.com', 'wrong-password');
      } catch (error) {
        expect(error.message).toBe('Invalid credentials');
      }
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    expect(AsyncStorage.setItem).not.toHaveBeenCalled();
  });

  it('handles signup', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    const signupData = {
      email: 'new@example.com',
      password: 'password123',
      name: 'New User',
    };

    const signupResponse = {
      token: 'new-token',
      user: {
        id: '2',
        email: 'new@example.com',
        name: 'New User',
      },
    };

    (authService.signup as jest.Mock).mockResolvedValue(signupResponse);

    await act(async () => {
      await result.current.signup(signupData.email, signupData.password, signupData.name);
    });

    expect(authService.signup).toHaveBeenCalledWith(
      signupData.email,
      signupData.password,
      signupData.name
    );
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user).toEqual(signupResponse.user);
  });

  it('handles logout', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    // Login first
    await act(async () => {
      result.current.setAuthState({
        isAuthenticated: true,
        user: { id: '1', email: 'test@test.com', name: 'Test' },
        token: 'test-token',
      });
    });

    (authService.logout as jest.Mock).mockResolvedValue(undefined);

    await act(async () => {
      await result.current.logout();
    });

    expect(authService.logout).toHaveBeenCalled();
    expect(AsyncStorage.removeItem).toHaveBeenCalledWith('auth_token');
    expect(AsyncStorage.removeItem).toHaveBeenCalledWith('auth_user');
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
  });

  it('updates user profile', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    const initialUser = {
      id: '1',
      email: 'test@example.com',
      name: 'Test User',
    };

    // Set initial auth state
    await act(async () => {
      result.current.setAuthState({
        isAuthenticated: true,
        user: initialUser,
        token: 'test-token',
      });
    });

    const updatedUser = {
      ...initialUser,
      name: 'Updated User',
      bio: 'New bio',
    };

    (authService.updateProfile as jest.Mock).mockResolvedValue(updatedUser);

    await act(async () => {
      await result.current.updateUser({ name: 'Updated User', bio: 'New bio' });
    });

    expect(authService.updateProfile).toHaveBeenCalledWith({ 
      name: 'Updated User', 
      bio: 'New bio' 
    });
    expect(result.current.user).toEqual(updatedUser);
    expect(AsyncStorage.setItem).toHaveBeenCalledWith(
      'auth_user',
      JSON.stringify(updatedUser)
    );
  });

  it('refreshes token', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    const oldToken = 'old-token';
    const newToken = 'new-token';

    // Set initial auth state
    await act(async () => {
      result.current.setAuthState({
        isAuthenticated: true,
        user: { id: '1', email: 'test@test.com', name: 'Test' },
        token: oldToken,
      });
    });

    (authService.refreshToken as jest.Mock).mockResolvedValue(newToken);

    await act(async () => {
      await result.current.refreshToken();
    });

    expect(authService.refreshToken).toHaveBeenCalledWith(oldToken);
    expect(result.current.token).toBe(newToken);
    expect(AsyncStorage.setItem).toHaveBeenCalledWith('auth_token', newToken);
  });

  it('handles social login', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    const socialLoginResponse = {
      token: 'social-token',
      user: {
        id: '3',
        email: 'social@example.com',
        name: 'Social User',
        provider: 'google',
      },
    };

    (authService.socialLogin as jest.Mock).mockResolvedValue(socialLoginResponse);

    await act(async () => {
      await result.current.socialLogin('google');
    });

    expect(authService.socialLogin).toHaveBeenCalledWith('google');
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user).toEqual(socialLoginResponse.user);
  });

  it('checks authentication status', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    (authService.checkAuthStatus as jest.Mock).mockResolvedValue({
      isAuthenticated: true,
      user: { id: '1', email: 'test@test.com', name: 'Test' },
    });

    await act(async () => {
      const status = await result.current.checkAuthStatus();
      expect(status).toBe(true);
    });

    expect(authService.checkAuthStatus).toHaveBeenCalled();
  });

  it('throws error when used outside provider', () => {
    const originalError = console.error;
    console.error = jest.fn();

    expect(() => {
      renderHook(() => useAuth());
    }).toThrow('useAuth must be used within AuthProvider');

    console.error = originalError;
  });
});