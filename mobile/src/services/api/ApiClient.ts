import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';
import { API_URL, ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY, TOKEN_EXPIRY_KEY, TOKEN_REFRESH_BUFFER, SECURE_STORAGE_ENABLED, CSRF_TOKEN_KEY } from '@/config';

// API Response types
interface ApiResponse<T> {
  data: T;
  status: number;
  headers: Record<string, string>;
}

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// API client options
interface ApiClientOptions {
  baseURL?: string;
  headers?: Record<string, string>;
  enableRetry?: boolean;
  maxRetries?: number;
  retryStatusCodes?: number[];
  timeoutMs?: number;
  enableTokenRefresh?: boolean;
}

// Error class for API errors
export class ApiError extends Error {
  status: number;
  data: any;
  
  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export class ApiClient {
  private baseURL: string;
  private defaultHeaders: Record<string, string>;
  private enableRetry: boolean;
  private maxRetries: number;
  private retryStatusCodes: number[];
  private timeoutMs: number;
  private enableTokenRefresh: boolean;
  private isRefreshing: boolean = false;
  private refreshPromise: Promise<boolean> | null = null;

  constructor(options: ApiClientOptions = {}) {
    this.baseURL = options.baseURL || API_URL || '';
    this.defaultHeaders = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...(options.headers || {})
    };
    this.enableRetry = options.enableRetry ?? true;
    this.maxRetries = options.maxRetries ?? 3;
    this.retryStatusCodes = options.retryStatusCodes ?? [408, 429, 500, 502, 503, 504];
    this.timeoutMs = options.timeoutMs || 30000;
    this.enableTokenRefresh = options.enableTokenRefresh ?? true;
  }

  // Store tokens securely
  private async storeTokens(
    accessToken: string,
    refreshToken: string,
    expiresIn: number
  ): Promise<void> {
    const expiryTime = Date.now() + expiresIn * 1000;
    
    if (SECURE_STORAGE_ENABLED) {
      try {
        await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, accessToken);
        await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, refreshToken);
        await SecureStore.setItemAsync(TOKEN_EXPIRY_KEY, expiryTime.toString());
        return;
      } catch (error) {
        console.error('Error storing tokens in SecureStore, falling back to AsyncStorage:', error);
      }
    }
    
    // Fallback to AsyncStorage
    await AsyncStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    await AsyncStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    await AsyncStorage.setItem(TOKEN_EXPIRY_KEY, expiryTime.toString());
  }

  // Get tokens
  private async getTokens(): Promise<{
    accessToken: string | null;
    refreshToken: string | null;
    expiryTime: number;
  }> {
    let accessToken: string | null = null;
    let refreshToken: string | null = null;
    let expiryTimeStr: string | null = null;
    
    if (SECURE_STORAGE_ENABLED) {
      try {
        accessToken = await SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
        refreshToken = await SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
        expiryTimeStr = await SecureStore.getItemAsync(TOKEN_EXPIRY_KEY);
        
        // If found in SecureStore, return early
        if (accessToken && refreshToken && expiryTimeStr) {
          return {
            accessToken,
            refreshToken,
            expiryTime: parseInt(expiryTimeStr) || 0
          };
        }
      } catch (error) {
        console.error('Error accessing SecureStore, falling back to AsyncStorage:', error);
      }
    }
    
    // Fallback to AsyncStorage or continue if tokens weren't found in SecureStore
    try {
      if (!accessToken) {
        accessToken = await AsyncStorage.getItem(ACCESS_TOKEN_KEY);
      }
      
      if (!refreshToken) {
        refreshToken = await AsyncStorage.getItem(REFRESH_TOKEN_KEY);
      }
      
      if (!expiryTimeStr) {
        expiryTimeStr = await AsyncStorage.getItem(TOKEN_EXPIRY_KEY);
      }
      
      return {
        accessToken,
        refreshToken,
        expiryTime: expiryTimeStr ? parseInt(expiryTimeStr) : 0
      };
    } catch (error) {
      console.error('Error getting tokens:', error);
      return {
        accessToken: null,
        refreshToken: null,
        expiryTime: 0
      };
    }
  }

  // Clear tokens
  private async clearTokens(): Promise<void> {
    if (SECURE_STORAGE_ENABLED) {
      try {
        await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
        await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
        await SecureStore.deleteItemAsync(TOKEN_EXPIRY_KEY);
        await SecureStore.deleteItemAsync(CSRF_TOKEN_KEY);
      } catch (error) {
        console.error('Error clearing tokens from SecureStore:', error);
      }
    }
    
    // Also clear from AsyncStorage as a failsafe
    try {
      await AsyncStorage.removeItem(ACCESS_TOKEN_KEY);
      await AsyncStorage.removeItem(REFRESH_TOKEN_KEY);
      await AsyncStorage.removeItem(TOKEN_EXPIRY_KEY);
      await AsyncStorage.removeItem(CSRF_TOKEN_KEY);
    } catch (error) {
      console.error('Error clearing tokens from AsyncStorage:', error);
    }
  }
  
  // Store CSRF token
  private async storeCSRFToken(token: string): Promise<void> {
    if (SECURE_STORAGE_ENABLED) {
      try {
        await SecureStore.setItemAsync(CSRF_TOKEN_KEY, token);
        return;
      } catch (error) {
        console.error('Error storing CSRF token in SecureStore, falling back to AsyncStorage:', error);
      }
    }
    
    // Fallback to AsyncStorage
    await AsyncStorage.setItem(CSRF_TOKEN_KEY, token);
  }
  
  // Get CSRF token
  private async getCSRFToken(): Promise<string | null> {
    let token: string | null = null;
    
    if (SECURE_STORAGE_ENABLED) {
      try {
        token = await SecureStore.getItemAsync(CSRF_TOKEN_KEY);
        if (token) {
          return token;
        }
      } catch (error) {
        console.error('Error accessing CSRF token from SecureStore, falling back to AsyncStorage:', error);
      }
    }
    
    // Fallback to AsyncStorage or continue if token wasn't found in SecureStore
    try {
      token = await AsyncStorage.getItem(CSRF_TOKEN_KEY);
      return token;
    } catch (error) {
      console.error('Error getting CSRF token:', error);
      return null;
    }
  }
  
  // Fetch a new CSRF token from the server
  public async fetchCSRFToken(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseURL}/api/csrf-token`, {
        method: 'GET',
        credentials: 'include', // Important to include cookies
      });
      
      if (!response.ok) {
        console.error('Failed to fetch CSRF token:', response.status);
        return false;
      }
      
      // In React Native, we can't access cookies directly like in a browser
      // Extract token from response headers (Set-Cookie)
      const setCookieHeader = response.headers.get('set-cookie');
      if (setCookieHeader) {
        // Parse the Set-Cookie header to extract the CSRF token
        const csrfMatch = setCookieHeader.match(/csrf_token=([^;]+)/);
        if (csrfMatch && csrfMatch[1]) {
          const token = csrfMatch[1];
          await this.storeCSRFToken(token);
          return true;
        }
      }
      
      // If we can't get it from headers, try to get it from a dedicated header
      const csrfToken = response.headers.get('X-CSRF-Token');
      if (csrfToken) {
        await this.storeCSRFToken(csrfToken);
        return true;
      }
      
      // If all else fails, try to parse the response JSON for a token
      try {
        const data = await response.json();
        if (data.csrf_token) {
          await this.storeCSRFToken(data.csrf_token);
          return true;
        }
      } catch (e) {
        // Ignore JSON parsing errors
      }
      
      console.warn('Could not extract CSRF token from response');
      return false;
    } catch (error) {
      console.error('Error fetching CSRF token:', error);
      return false;
    }
  }

  // Check if token needs refresh (expired or about to expire)
  private isTokenExpiring(expiryTime: number): boolean {
    return Date.now() + TOKEN_REFRESH_BUFFER > expiryTime;
  }

  // Refresh token
  private async refreshToken(): Promise<boolean> {
    // If already refreshing, return the existing promise
    if (this.isRefreshing && this.refreshPromise) {
      return this.refreshPromise;
    }
    
    this.isRefreshing = true;
    
    this.refreshPromise = (async () => {
      try {
        const { refreshToken } = await this.getTokens();
        
        if (!refreshToken) {
          return false;
        }
        
        const response = await fetch(`${this.baseURL}/api/auth/refresh`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ refresh_token: refreshToken })
        });
        
        if (!response.ok) {
          // If refresh failed, clear tokens
          await this.clearTokens();
          return false;
        }
        
        const data: TokenResponse = await response.json();
        
        // Store new tokens
        await this.storeTokens(
          data.access_token,
          data.refresh_token,
          data.expires_in
        );
        
        return true;
      } catch (error) {
        console.error('Token refresh failed:', error);
        return false;
      } finally {
        this.isRefreshing = false;
        this.refreshPromise = null;
      }
    })();
    
    return this.refreshPromise;
  }

  // Get request headers with auth token and CSRF token
  private async getHeaders(includeCSRF: boolean = false): Promise<Record<string, string>> {
    try {
      const headers = { ...this.defaultHeaders };
      
      // Add authorization token if enabled
      if (this.enableTokenRefresh) {
        const { accessToken, expiryTime } = await this.getTokens();
        
        // If token exists and is expiring soon, try to refresh it
        if (accessToken && this.isTokenExpiring(expiryTime)) {
          const refreshed = await this.refreshToken();
          
          if (refreshed) {
            const { accessToken: newToken } = await this.getTokens();
            if (newToken) {
              headers['Authorization'] = `Bearer ${newToken}`;
            }
          }
        }
        
        // Use existing token if available
        if (accessToken) {
          headers['Authorization'] = `Bearer ${accessToken}`;
        }
      }
      
      // Add CSRF token for non-GET requests
      if (includeCSRF) {
        const csrfToken = await this.getCSRFToken();
        
        if (csrfToken) {
          headers[CSRF_HEADER_NAME] = csrfToken;
        } else {
          // Try to fetch a new CSRF token
          const fetched = await this.fetchCSRFToken();
          if (fetched) {
            const newToken = await this.getCSRFToken();
            if (newToken) {
              headers[CSRF_HEADER_NAME] = newToken;
            }
          }
        }
      }
      
      return headers;
    } catch (error) {
      console.error('Error preparing headers:', error);
      return this.defaultHeaders;
    }
  }

  // Timeout promise
  private createTimeoutPromise(): Promise<Response> {
    return new Promise((_, reject) => {
      setTimeout(() => {
        reject(new Error(`Request timed out after ${this.timeoutMs}ms`));
      }, this.timeoutMs);
    });
  }

  // Parse response
  private async parseResponse<T>(response: Response): Promise<ApiResponse<T>> {
    const headers: Record<string, string> = {};
    response.headers.forEach((value, key) => {
      headers[key] = value;
    });
    
    // Prepare response object
    const apiResponse: ApiResponse<T> = {
      status: response.status,
      headers,
      data: {} as T
    };
    
    // For 204 No Content, return empty data
    if (response.status === 204) {
      return apiResponse;
    }
    
    // Try to parse as JSON
    try {
      apiResponse.data = await response.json();
      return apiResponse;
    } catch (error) {
      // If can't parse as JSON, try to get text
      try {
        const text = await response.text();
        apiResponse.data = text as unknown as T;
        return apiResponse;
      } catch (textError) {
        // If all else fails, return empty data
        return apiResponse;
      }
    }
  }

  // Generic request method with retry logic
  private async fetchWithRetry<T>(
    url: string,
    options: RequestInit,
    retries = 0
  ): Promise<ApiResponse<T>> {
    try {
      const fullUrl = url.startsWith('http') ? url : `${this.baseURL}${url}`;
      
      // Add request timeout
      const fetchPromise = fetch(fullUrl, options);
      const response = await Promise.race([
        fetchPromise,
        this.createTimeoutPromise()
      ]);
      
      // Handle 401 Unauthorized
      if (response.status === 401 && this.enableTokenRefresh && retries === 0) {
        // Try to refresh token and retry request once
        const refreshed = await this.refreshToken();
        
        if (refreshed) {
          // Update auth header with new token
          const { accessToken } = await this.getTokens();
          if (accessToken && options.headers) {
            const headers = new Headers(options.headers);
            headers.set('Authorization', `Bearer ${accessToken}`);
            
            // Retry request with new token
            return this.fetchWithRetry<T>(
              url,
              { ...options, headers },
              retries + 1
            );
          }
        } else {
          // If refresh failed, clear tokens
          await this.clearTokens();
        }
      }
      
      // Handle 403 Forbidden which might be CSRF related
      if (response.status === 403 && options.method !== 'GET' && retries === 0) {
        const errorBody = await response.text();
        
        if (errorBody.includes('CSRF') || errorBody.includes('csrf')) {
          console.warn('CSRF token error detected, fetching new token and retrying...');
          // Try to get a new CSRF token and retry
          const csrfSuccess = await this.fetchCSRFToken();
          
          if (csrfSuccess) {
            // Get the new token
            const csrfToken = await this.getCSRFToken();
            if (csrfToken && options.headers) {
              const headers = new Headers(options.headers);
              headers.set(CSRF_HEADER_NAME, csrfToken);
              
              // Retry with new CSRF token
              return this.fetchWithRetry<T>(
                url,
                { ...options, headers },
                retries + 1
              );
            }
          }
        }
      }
      
      // Check other error responses
      if (!response.ok) {
        // Handle retryable status codes
        const shouldRetry = this.enableRetry && 
                           retries < this.maxRetries && 
                           this.retryStatusCodes.includes(response.status);
                       
        if (shouldRetry) {
          // Exponential backoff
          const delay = Math.pow(2, retries + 1) * 1000;
          await new Promise(resolve => setTimeout(resolve, delay));
          return this.fetchWithRetry<T>(url, options, retries + 1);
        }
        
        // Parse error response
        let errorData: any;
        try {
          errorData = await response.json();
        } catch {
          try {
            errorData = { message: await response.text() };
          } catch {
            errorData = { message: 'An unknown error occurred' };
          }
        }
        
        const message = errorData.detail || errorData.message || `Request failed with status ${response.status}`;
        throw new ApiError(message, response.status, errorData);
      }
      
      // Parse successful response
      return await this.parseResponse<T>(response);
    } catch (error: any) {
      // Handle network errors or timeouts
      if (error.message === 'Network request failed' || error.message.includes('timed out')) {
        if (retries < this.maxRetries) {
          // Exponential backoff
          const delay = Math.pow(2, retries + 1) * 1000;
          await new Promise(resolve => setTimeout(resolve, delay));
          return this.fetchWithRetry<T>(url, options, retries + 1);
        }
      }
      
      // Re-throw API errors
      if (error instanceof ApiError) {
        throw error;
      }
      
      // Wrap other errors
      throw new ApiError(
        error.message || 'Request failed',
        0,
        { originalError: error }
      );
    }
  }

  // HTTP methods
  async get<T>(url: string, params?: Record<string, any>): Promise<T> {
    const headers = await this.getHeaders(false); // No CSRF for GET
    
    // Add query params to URL if provided
    let fullUrl = url;
    if (params) {
      const queryParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          queryParams.append(key, String(value));
        }
      });
      
      const queryString = queryParams.toString();
      if (queryString) {
        fullUrl += (url.includes('?') ? '&' : '?') + queryString;
      }
    }
    
    const response = await this.fetchWithRetry<T>(fullUrl, {
      method: 'GET',
      headers,
      credentials: 'include', // Include cookies for CSRF
    });
    
    return response.data;
  }
  
  async post<T>(url: string, data?: any, params?: Record<string, any>): Promise<T> {
    const headers = await this.getHeaders(true); // Include CSRF for POST
    
    // Add query params to URL if provided
    let fullUrl = url;
    if (params) {
      const queryParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          queryParams.append(key, String(value));
        }
      });
      
      const queryString = queryParams.toString();
      if (queryString) {
        fullUrl += (url.includes('?') ? '&' : '?') + queryString;
      }
    }
    
    const response = await this.fetchWithRetry<T>(fullUrl, {
      method: 'POST',
      headers,
      body: data ? JSON.stringify(data) : undefined,
      credentials: 'include', // Include cookies for CSRF
    });
    
    return response.data;
  }
  
  async put<T>(url: string, data?: any): Promise<T> {
    const headers = await this.getHeaders(true); // Include CSRF for PUT
    
    const response = await this.fetchWithRetry<T>(url, {
      method: 'PUT',
      headers,
      body: data ? JSON.stringify(data) : undefined,
      credentials: 'include', // Include cookies for CSRF
    });
    
    return response.data;
  }
  
  async patch<T>(url: string, data?: any): Promise<T> {
    const headers = await this.getHeaders(true); // Include CSRF for PATCH
    
    const response = await this.fetchWithRetry<T>(url, {
      method: 'PATCH',
      headers,
      body: data ? JSON.stringify(data) : undefined,
      credentials: 'include', // Include cookies for CSRF
    });
    
    return response.data;
  }
  
  async delete<T>(url: string, data?: any): Promise<T> {
    const headers = await this.getHeaders(true); // Include CSRF for DELETE
    
    const response = await this.fetchWithRetry<T>(url, {
      method: 'DELETE',
      headers,
      body: data ? JSON.stringify(data) : undefined,
      credentials: 'include', // Include cookies for CSRF
    });
    
    return response.data;
  }

  // Auth token management
  async setAuthToken(token: string): Promise<void> {
    await this.storeTokens(token, '', 3600); // Default 1-hour expiry
  }

  async clearAuthToken(): Promise<void> {
    await this.clearTokens();
  }
  
  // Helper to check if authenticated
  async isAuthenticated(): Promise<boolean> {
    const { accessToken, refreshToken, expiryTime } = await this.getTokens();
    
    // If no tokens, not authenticated
    if (!accessToken && !refreshToken) {
      return false;
    }
    
    // If access token is valid, authenticated
    if (accessToken && !this.isTokenExpiring(expiryTime)) {
      return true;
    }
    
    // If access token is expiring but refresh token exists, try to refresh
    if (refreshToken) {
      return await this.refreshToken();
    }
    
    return false;
  }
}

// Export a singleton instance for app-wide use
export const apiClient = new ApiClient();

// Export default for when custom instances are needed
export default ApiClient;