import axios, { AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { User } from '@/types/user';
import { API_URL } from '@/config';
import * as SecureStore from 'expo-secure-store';

// Auth storage keys
const ACCESS_TOKEN_KEY = 'accessToken';
const REFRESH_TOKEN_KEY = 'refreshToken';
const TOKEN_EXPIRY_KEY = 'tokenExpiry';

// Auth endpoint
const API_AUTH_URL = `${API_URL}/api/auth`;

// Token response interface
interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

interface AuthResponse {
  user: User;
}

// Create axios instance for auth
const api = axios.create({
  baseURL: API_AUTH_URL,
});

// Store tokens securely
const storeTokens = async (
  accessToken: string,
  refreshToken: string,
  expiresIn: number
) => {
  const expiryTime = Date.now() + expiresIn * 1000;
  
  try {
    // Use SecureStore for sensitive data
    await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, accessToken);
    await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, refreshToken);
    await SecureStore.setItemAsync(TOKEN_EXPIRY_KEY, expiryTime.toString());
  } catch (error) {
    console.error('Error storing tokens securely:', error);
    // SECURITY: Never fallback to AsyncStorage for sensitive tokens
    // If secure storage fails, the operation must fail
    throw new Error('Failed to store authentication tokens securely. Please try again.');
  }
};

// Get tokens
const getTokens = async () => {
  try {
    // Try SecureStore first
    let accessToken = await SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
    let refreshToken = await SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
    let expiryTimeStr = await SecureStore.getItemAsync(TOKEN_EXPIRY_KEY);
    
    // SECURITY: No fallback to AsyncStorage - tokens must be in SecureStore only
    // If tokens are not in SecureStore, user must re-authenticate
    
    const expiryTime = expiryTimeStr ? parseInt(expiryTimeStr) : 0;
    
    return {
      accessToken,
      refreshToken,
      expiryTime
    };
  } catch (error) {
    console.error('Error getting tokens:', error);
    return {
      accessToken: null,
      refreshToken: null,
      expiryTime: 0
    };
  }
};

// Clear tokens
const clearTokens = async () => {
  try {
    // Clear from SecureStore
    await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
    await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
    await SecureStore.deleteItemAsync(TOKEN_EXPIRY_KEY);
    
    // Clear from AsyncStorage as well
    await AsyncStorage.removeItem(ACCESS_TOKEN_KEY);
    await AsyncStorage.removeItem(REFRESH_TOKEN_KEY);
    await AsyncStorage.removeItem(TOKEN_EXPIRY_KEY);
  } catch (error) {
    console.error('Error clearing tokens:', error);
  }
};

// Check if token is expired or about to expire (within 5 minutes)
const isTokenExpired = (expiryTime: number) => {
  return Date.now() + 5 * 60 * 1000 > expiryTime;
};

// Refresh token function
const refreshTokens = async (): Promise<boolean> => {
  try {
    const { refreshToken } = await getTokens();
    
    if (!refreshToken) {
      return false;
    }
    
    // Call refresh endpoint
    const response = await axios.post<TokenResponse>(
      `${API_AUTH_URL}/refresh`,
      { refresh_token: refreshToken }
    );
    
    const { access_token, refresh_token, expires_in } = response.data;
    
    // Store new tokens
    await storeTokens(access_token, refresh_token, expires_in);
    
    return true;
  } catch (error) {
    console.error('Token refresh failed:', error);
    return false;
  }
};

// Add request interceptor to inject token
api.interceptors.request.use(async (config) => {
  const { accessToken, expiryTime } = await getTokens();
  
  // If token is expired and not currently refreshing
  if (accessToken && isTokenExpired(expiryTime) && !config.url?.includes('/refresh')) {
    const refreshed = await refreshTokens();
    
    if (refreshed) {
      const { accessToken: newToken } = await getTokens();
      if (newToken) {
        config.headers.Authorization = `Bearer ${newToken}`;
      }
    }
  } else if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  
  return config;
});

// Add response interceptor to handle 401 errors
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };
    
    // If error is 401 and not already retrying
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        const refreshed = await refreshTokens();
        
        if (refreshed) {
          const { accessToken } = await getTokens();
          
          if (accessToken && originalRequest.headers) {
            // Update the original request with new token
            originalRequest.headers.Authorization = `Bearer ${accessToken}`;
            return axios(originalRequest);
          }
        }
      } catch (refreshError) {
        console.error('Token refresh failed in error interceptor:', refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

export const authService = {
  async login(email: string, password: string): Promise<User> {
    try {
      // Get token
      const tokenResponse = await api.post<TokenResponse>('/token', {
        username: email,  // FastAPI OAuth2 expects 'username'
        password,
      }, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });
      
      const { access_token, refresh_token, expires_in } = tokenResponse.data;
      
      // Store tokens
      await storeTokens(access_token, refresh_token, expires_in);
      
      // Get user data
      const userResponse = await api.get<User>('/me', {
        headers: {
          Authorization: `Bearer ${access_token}`
        }
      });
      
      return userResponse.data;
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  },

  async register(userData: {
    email: string;
    password: string;
    name: string;
    interests: string[];
  }): Promise<User> {
    try {
      // Register user
      const registerResponse = await api.post<User>('/register', userData);
      
      // After registration, login to get tokens
      return await this.login(userData.email, userData.password);
    } catch (error) {
      console.error('Registration failed:', error);
      throw error;
    }
  },

  async getCurrentUser(): Promise<User> {
    const { accessToken, expiryTime } = await getTokens();
    
    // Refresh token if expired
    if (accessToken && isTokenExpired(expiryTime)) {
      await refreshTokens();
    }
    
    const response = await api.get<User>('/me');
    return response.data;
  },

  async updateUser(userData: Partial<User>): Promise<User> {
    const response = await api.put<User>('/me', userData);
    return response.data;
  },

  async logout(): Promise<void> {
    try {
      const { accessToken } = await getTokens();
      
      if (accessToken) {
        // Revoke token at server
        await api.post('/revoke', {
          token: accessToken,
          token_type_hint: 'access_token'
        });
      }
    } catch (error) {
      console.error('Error during server logout:', error);
    } finally {
      // Clear tokens locally regardless of server response
      await clearTokens();
    }
  },

  async forgotPassword(email: string): Promise<void> {
    await api.post('/forgot-password', { email });
  },

  async resetPassword(token: string, newPassword: string): Promise<void> {
    await api.post('/reset-password', {
      token,
      new_password: newPassword,
    });
  },

  async changePassword(
    currentPassword: string,
    newPassword: string
  ): Promise<void> {
    await api.post('/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
  },
  
  async refreshTokens(): Promise<boolean> {
    return refreshTokens();
  },
  
  // Helper method to check if user is authenticated
  async isAuthenticated(): Promise<boolean> {
    try {
      const { accessToken, refreshToken, expiryTime } = await getTokens();
      
      // If no tokens, not authenticated
      if (!accessToken && !refreshToken) {
        return false;
      }
      
      // If access token is valid, authenticated
      if (accessToken && !isTokenExpired(expiryTime)) {
        return true;
      }
      
      // If access token expired but refresh token exists, try to refresh
      if (refreshToken) {
        return await refreshTokens();
      }
      
      return false;
    } catch (error) {
      console.error('Authentication check failed:', error);
      return false;
    }
  }
};