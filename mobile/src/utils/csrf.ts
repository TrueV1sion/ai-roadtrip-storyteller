/**
 * CSRF token management for secure API requests
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import { apiService } from '../services/apiService';

const CSRF_TOKEN_KEY = '@csrf_token';
const CSRF_HEADER_NAME = 'X-CSRF-Token';

class CSRFManager {
  private token: string | null = null;
  private tokenPromise: Promise<string> | null = null;

  /**
   * Get CSRF token, fetching from server if needed
   */
  async getToken(): Promise<string> {
    // If we're already fetching, wait for that request
    if (this.tokenPromise) {
      return this.tokenPromise;
    }

    // Check memory cache
    if (this.token) {
      return this.token;
    }

    // Check AsyncStorage
    try {
      const storedToken = await AsyncStorage.getItem(CSRF_TOKEN_KEY);
      if (storedToken) {
        this.token = storedToken;
        return storedToken;
      }
    } catch (error) {
      console.error('Error reading CSRF token from storage:', error);
    }

    // Fetch new token from server
    this.tokenPromise = this.fetchNewToken();
    try {
      const token = await this.tokenPromise;
      return token;
    } finally {
      this.tokenPromise = null;
    }
  }

  /**
   * Fetch new CSRF token from server
   */
  private async fetchNewToken(): Promise<string> {
    try {
      const response = await apiService.get('/csrf/token');
      const { csrf_token } = response.data;

      if (!csrf_token) {
        throw new Error('No CSRF token received from server');
      }

      // Store in memory and AsyncStorage
      this.token = csrf_token;
      await AsyncStorage.setItem(CSRF_TOKEN_KEY, csrf_token);

      return csrf_token;
    } catch (error) {
      console.error('Error fetching CSRF token:', error);
      throw error;
    }
  }

  /**
   * Clear stored CSRF token (e.g., on logout)
   */
  async clearToken(): Promise<void> {
    this.token = null;
    this.tokenPromise = null;
    try {
      await AsyncStorage.removeItem(CSRF_TOKEN_KEY);
    } catch (error) {
      console.error('Error clearing CSRF token:', error);
    }
  }

  /**
   * Add CSRF token to request headers
   */
  async addTokenToHeaders(headers: Record<string, string>): Promise<Record<string, string>> {
    try {
      const token = await this.getToken();
      return {
        ...headers,
        [CSRF_HEADER_NAME]: token,
      };
    } catch (error) {
      console.error('Error adding CSRF token to headers:', error);
      // Return headers without CSRF token if fetch fails
      return headers;
    }
  }

  /**
   * Handle CSRF validation error by fetching new token
   */
  async handleCSRFError(): Promise<string> {
    // Clear existing token
    await this.clearToken();
    
    // Fetch new token
    return this.getToken();
  }
}

export const csrfManager = new CSRFManager();

/**
 * Axios request interceptor to add CSRF token
 */
export const setupCSRFInterceptor = (axiosInstance: any) => {
  // Request interceptor to add CSRF token
  axiosInstance.interceptors.request.use(
    async (config: any) => {
      // Only add CSRF for state-changing methods
      const needsCSRF = ['post', 'put', 'delete', 'patch'].includes(
        config.method?.toLowerCase() || ''
      );

      if (needsCSRF && !config.headers['Authorization']) {
        // Don't add CSRF if we have a Bearer token (JWT)
        config.headers = await csrfManager.addTokenToHeaders(config.headers || {});
      }

      return config;
    },
    (error: any) => {
      return Promise.reject(error);
    }
  );

  // Response interceptor to handle CSRF errors
  axiosInstance.interceptors.response.use(
    (response: any) => response,
    async (error: any) => {
      const originalRequest = error.config;

      // Check if it's a CSRF error and we haven't already retried
      if (
        error.response?.status === 403 &&
        error.response?.data?.detail?.includes('CSRF') &&
        !originalRequest._retry
      ) {
        originalRequest._retry = true;

        try {
          // Get new CSRF token
          await csrfManager.handleCSRFError();
          
          // Retry the request with new token
          originalRequest.headers = await csrfManager.addTokenToHeaders(
            originalRequest.headers || {}
          );
          
          return axiosInstance(originalRequest);
        } catch (csrfError) {
          // If CSRF token fetch fails, reject with original error
          return Promise.reject(error);
        }
      }

      return Promise.reject(error);
    }
  );
};