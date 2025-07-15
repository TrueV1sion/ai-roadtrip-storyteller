import AsyncStorage from '@react-native-async-storage/async-storage';
import authService from '../authService';
import apiManager from '../api/apiManager';

jest.mock('../api/apiManager');
jest.mock('@react-native-async-storage/async-storage');

const mockedApiManager = apiManager as jest.Mocked<typeof apiManager>;
const mockedAsyncStorage = AsyncStorage as jest.Mocked<typeof AsyncStorage>;

describe('AuthService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('login', () => {
    it('successfully logs in user', async () => {
      const mockUser = { id: 1, email: 'test@example.com', token: 'test-token' };
      mockedApiManager.post.mockResolvedValueOnce(mockUser);

      const result = await authService.login('test@example.com', 'password');

      expect(mockedApiManager.post).toHaveBeenCalledWith('/auth/login', {
        email: 'test@example.com',
        password: 'password'
      });
      expect(mockedAsyncStorage.setItem).toHaveBeenCalledWith('authToken', 'test-token');
      expect(mockedAsyncStorage.setItem).toHaveBeenCalledWith('user', JSON.stringify(mockUser));
      expect(result).toEqual(mockUser);
    });

    it('handles login failure', async () => {
      const errorMessage = 'Invalid credentials';
      mockedApiManager.post.mockRejectedValueOnce(new Error(errorMessage));

      await expect(authService.login('test@example.com', 'wrong-password'))
        .rejects.toThrow(errorMessage);
      
      expect(mockedAsyncStorage.setItem).not.toHaveBeenCalled();
    });

    it('validates email format', async () => {
      await expect(authService.login('invalid-email', 'password'))
        .rejects.toThrow('Invalid email format');
      
      expect(mockedApiManager.post).not.toHaveBeenCalled();
    });

    it('validates password length', async () => {
      await expect(authService.login('test@example.com', '123'))
        .rejects.toThrow('Password must be at least 6 characters');
      
      expect(mockedApiManager.post).not.toHaveBeenCalled();
    });
  });

  describe('register', () => {
    it('successfully registers new user', async () => {
      const mockUser = { id: 1, email: 'new@example.com', token: 'new-token' };
      mockedApiManager.post.mockResolvedValueOnce(mockUser);

      const result = await authService.register({
        email: 'new@example.com',
        password: 'password123',
        name: 'New User'
      });

      expect(mockedApiManager.post).toHaveBeenCalledWith('/auth/register', {
        email: 'new@example.com',
        password: 'password123',
        name: 'New User'
      });
      expect(mockedAsyncStorage.setItem).toHaveBeenCalledWith('authToken', 'new-token');
      expect(result).toEqual(mockUser);
    });

    it('handles duplicate email error', async () => {
      const errorResponse = {
        response: {
          status: 409,
          data: { error: 'Email already exists' }
        }
      };
      mockedApiManager.post.mockRejectedValueOnce(errorResponse);

      await expect(authService.register({
        email: 'existing@example.com',
        password: 'password123',
        name: 'User'
      })).rejects.toMatchObject(errorResponse);
    });
  });

  describe('logout', () => {
    it('clears user data and token', async () => {
      await authService.logout();

      expect(mockedAsyncStorage.removeItem).toHaveBeenCalledWith('authToken');
      expect(mockedAsyncStorage.removeItem).toHaveBeenCalledWith('user');
      expect(mockedApiManager.post).toHaveBeenCalledWith('/auth/logout');
    });

    it('continues logout even if API call fails', async () => {
      mockedApiManager.post.mockRejectedValueOnce(new Error('Network error'));

      await authService.logout();

      expect(mockedAsyncStorage.removeItem).toHaveBeenCalledWith('authToken');
      expect(mockedAsyncStorage.removeItem).toHaveBeenCalledWith('user');
    });
  });

  describe('getCurrentUser', () => {
    it('returns cached user if available', async () => {
      const mockUser = { id: 1, email: 'test@example.com' };
      mockedAsyncStorage.getItem.mockResolvedValueOnce(JSON.stringify(mockUser));

      const result = await authService.getCurrentUser();

      expect(result).toEqual(mockUser);
      expect(mockedApiManager.get).not.toHaveBeenCalled();
    });

    it('fetches user from API if not cached', async () => {
      const mockUser = { id: 1, email: 'test@example.com' };
      mockedAsyncStorage.getItem.mockResolvedValueOnce(null);
      mockedApiManager.get.mockResolvedValueOnce(mockUser);

      const result = await authService.getCurrentUser();

      expect(mockedApiManager.get).toHaveBeenCalledWith('/auth/me');
      expect(mockedAsyncStorage.setItem).toHaveBeenCalledWith('user', JSON.stringify(mockUser));
      expect(result).toEqual(mockUser);
    });

    it('returns null if user not authenticated', async () => {
      mockedAsyncStorage.getItem.mockResolvedValueOnce(null);
      mockedApiManager.get.mockRejectedValueOnce({ response: { status: 401 } });

      const result = await authService.getCurrentUser();

      expect(result).toBeNull();
    });
  });

  describe('refreshToken', () => {
    it('refreshes authentication token', async () => {
      const mockResponse = { token: 'new-token' };
      mockedApiManager.post.mockResolvedValueOnce(mockResponse);

      const result = await authService.refreshToken();

      expect(mockedApiManager.post).toHaveBeenCalledWith('/auth/refresh');
      expect(mockedAsyncStorage.setItem).toHaveBeenCalledWith('authToken', 'new-token');
      expect(result).toEqual('new-token');
    });

    it('handles refresh failure', async () => {
      mockedApiManager.post.mockRejectedValueOnce(new Error('Invalid refresh token'));

      await expect(authService.refreshToken()).rejects.toThrow('Invalid refresh token');
      expect(mockedAsyncStorage.setItem).not.toHaveBeenCalled();
    });
  });

  describe('isAuthenticated', () => {
    it('returns true when token exists', async () => {
      mockedAsyncStorage.getItem.mockResolvedValueOnce('valid-token');

      const result = await authService.isAuthenticated();

      expect(result).toBe(true);
    });

    it('returns false when no token', async () => {
      mockedAsyncStorage.getItem.mockResolvedValueOnce(null);

      const result = await authService.isAuthenticated();

      expect(result).toBe(false);
    });
  });
});