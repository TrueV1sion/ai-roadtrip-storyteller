/**
 * Secure Token Manager
 * Handles secure storage and lifecycle management of authentication tokens
 * Implements OWASP best practices for token security
 */

import secureStorageService from '@/services/secureStorageService';
import { logger } from '@/services/logger';
import { sentryService } from '@/services/sentry/SentryService';
import NetInfo from '@react-native-community/netinfo';
import { Platform } from 'react-native';

interface TokenData {
  accessToken: string;
  refreshToken: string;
  expiryTime: number;
  tokenType: string;
  scope?: string;
}

interface SecureTokenConfig {
  requireBiometricForRefresh?: boolean;
  tokenRotationEnabled?: boolean;
  maxTokenAge?: number; // Maximum age in milliseconds
  autoRefreshBuffer?: number; // Time before expiry to auto-refresh (ms)
}

class SecureTokenManager {
  private static instance: SecureTokenManager;
  private config: SecureTokenConfig;
  private refreshPromise: Promise<boolean> | null = null;
  private tokenRotationInterval: NodeJS.Timeout | null = null;
  
  // Token storage keys with prefixes to avoid collisions
  private readonly ACCESS_TOKEN_KEY = 'secure_auth_access_token';
  private readonly REFRESH_TOKEN_KEY = 'secure_auth_refresh_token';
  private readonly TOKEN_METADATA_KEY = 'secure_auth_token_metadata';
  private readonly TOKEN_FINGERPRINT_KEY = 'secure_auth_token_fingerprint';
  
  // Security constants
  private readonly MAX_TOKEN_AGE = 7 * 24 * 60 * 60 * 1000; // 7 days
  private readonly AUTO_REFRESH_BUFFER = 5 * 60 * 1000; // 5 minutes
  private readonly TOKEN_ROTATION_INTERVAL = 24 * 60 * 60 * 1000; // 24 hours

  private constructor() {
    this.config = {
      requireBiometricForRefresh: true,
      tokenRotationEnabled: true,
      maxTokenAge: this.MAX_TOKEN_AGE,
      autoRefreshBuffer: this.AUTO_REFRESH_BUFFER,
    };
  }

  static getInstance(): SecureTokenManager {
    if (!SecureTokenManager.instance) {
      SecureTokenManager.instance = new SecureTokenManager();
    }
    return SecureTokenManager.instance;
  }

  /**
   * Initialize the token manager
   */
  async initialize(config?: Partial<SecureTokenConfig>): Promise<void> {
    if (config) {
      this.config = { ...this.config, ...config };
    }

    // Initialize secure storage
    await secureStorageService.initialize();

    // Set up token rotation if enabled
    if (this.config.tokenRotationEnabled) {
      this.setupTokenRotation();
    }

    // Validate existing tokens on startup
    await this.validateStoredTokens();
  }

  /**
   * Store tokens securely with metadata
   */
  async storeTokens(
    accessToken: string,
    refreshToken: string,
    expiresIn: number,
    tokenType: string = 'Bearer',
    scope?: string
  ): Promise<void> {
    try {
      const expiryTime = Date.now() + (expiresIn * 1000);
      
      // Generate token fingerprint for additional validation
      const fingerprint = await this.generateTokenFingerprint(accessToken);
      
      // Store access token (no biometric required for frequent access)
      await secureStorageService.setItem(this.ACCESS_TOKEN_KEY, accessToken);
      
      // Store refresh token with biometric protection
      await secureStorageService.setItem(
        this.REFRESH_TOKEN_KEY,
        refreshToken,
        {
          requireAuthentication: this.config.requireBiometricForRefresh,
          authenticationPrompt: 'Authenticate to store refresh token',
        }
      );
      
      // Store metadata
      const metadata = {
        expiryTime,
        tokenType,
        scope,
        storedAt: Date.now(),
        platform: Platform.OS,
      };
      
      await secureStorageService.setItem(
        this.TOKEN_METADATA_KEY,
        JSON.stringify(metadata)
      );
      
      // Store fingerprint for validation
      await secureStorageService.setItem(this.TOKEN_FINGERPRINT_KEY, fingerprint);
      
      // Track successful token storage
      sentryService.trackUserInteraction('tokens_stored', 'auth', {
        tokenType,
        hasScope: !!scope,
      });
      
    } catch (error) {
      logger.error('Failed to store tokens securely:', error);
      sentryService.captureException(error as Error, {
        tags: { security_error: 'token_storage' },
      });
      throw new Error('Failed to store authentication tokens securely');
    }
  }

  /**
   * Retrieve tokens with validation
   */
  async getTokens(): Promise<TokenData | null> {
    try {
      // Get all token data
      const [accessToken, refreshToken, metadataStr, storedFingerprint] = await Promise.all([
        secureStorageService.getItem(this.ACCESS_TOKEN_KEY),
        secureStorageService.getItem(this.REFRESH_TOKEN_KEY),
        secureStorageService.getItem(this.TOKEN_METADATA_KEY),
        secureStorageService.getItem(this.TOKEN_FINGERPRINT_KEY),
      ]);

      if (!accessToken || !refreshToken || !metadataStr) {
        return null;
      }

      const metadata = JSON.parse(metadataStr);
      
      // Validate token fingerprint
      const currentFingerprint = await this.generateTokenFingerprint(accessToken);
      if (storedFingerprint && storedFingerprint !== currentFingerprint) {
        logger.error('Token fingerprint mismatch - possible tampering detected');
        await this.clearTokens();
        return null;
      }
      
      // Check max token age
      const tokenAge = Date.now() - metadata.storedAt;
      if (tokenAge > (this.config.maxTokenAge || this.MAX_TOKEN_AGE)) {
        logger.warn('Token exceeded maximum age');
        await this.clearTokens();
        return null;
      }

      return {
        accessToken,
        refreshToken,
        expiryTime: metadata.expiryTime,
        tokenType: metadata.tokenType || 'Bearer',
        scope: metadata.scope,
      };
    } catch (error) {
      logger.error('Failed to retrieve tokens:', error);
      return null;
    }
  }

  /**
   * Get access token with automatic refresh if needed
   */
  async getValidAccessToken(): Promise<string | null> {
    const tokens = await this.getTokens();
    if (!tokens) return null;

    // Check if token needs refresh
    const timeUntilExpiry = tokens.expiryTime - Date.now();
    const needsRefresh = timeUntilExpiry < (this.config.autoRefreshBuffer || this.AUTO_REFRESH_BUFFER);

    if (needsRefresh) {
      // Check network connectivity before refresh
      const netInfo = await NetInfo.fetch();
      if (!netInfo.isConnected) {
        logger.warn('Cannot refresh token - no network connection');
        // Return existing token if still valid
        return timeUntilExpiry > 0 ? tokens.accessToken : null;
      }

      // Refresh token
      const refreshed = await this.refreshToken(tokens.refreshToken);
      if (refreshed) {
        const newTokens = await this.getTokens();
        return newTokens?.accessToken || null;
      }
    }

    return tokens.accessToken;
  }

  /**
   * Refresh token with biometric authentication
   */
  async refreshToken(refreshToken: string): Promise<boolean> {
    // Prevent concurrent refresh attempts
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    this.refreshPromise = this._performTokenRefresh(refreshToken);
    
    try {
      const result = await this.refreshPromise;
      return result;
    } finally {
      this.refreshPromise = null;
    }
  }

  /**
   * Perform the actual token refresh
   */
  private async _performTokenRefresh(refreshToken: string): Promise<boolean> {
    try {
      // This should call your backend refresh endpoint
      // For now, returning false as placeholder
      logger.info('Token refresh requested');
      
      // Track refresh attempt
      sentryService.trackUserInteraction('token_refresh_attempted', 'auth');
      
      // TODO: Implement actual refresh logic with backend
      // const response = await api.post('/auth/refresh', { refresh_token: refreshToken });
      // await this.storeTokens(response.access_token, response.refresh_token, response.expires_in);
      
      return false;
    } catch (error) {
      logger.error('Token refresh failed:', error);
      sentryService.captureException(error as Error, {
        tags: { security_error: 'token_refresh' },
      });
      return false;
    }
  }

  /**
   * Clear all tokens
   */
  async clearTokens(): Promise<void> {
    try {
      await Promise.all([
        secureStorageService.removeItem(this.ACCESS_TOKEN_KEY),
        secureStorageService.removeItem(this.REFRESH_TOKEN_KEY),
        secureStorageService.removeItem(this.TOKEN_METADATA_KEY),
        secureStorageService.removeItem(this.TOKEN_FINGERPRINT_KEY),
      ]);

      // Stop token rotation
      if (this.tokenRotationInterval) {
        clearInterval(this.tokenRotationInterval);
        this.tokenRotationInterval = null;
      }

      sentryService.trackUserInteraction('tokens_cleared', 'auth');
    } catch (error) {
      logger.error('Failed to clear tokens:', error);
    }
  }

  /**
   * Validate stored tokens on app startup
   */
  private async validateStoredTokens(): Promise<void> {
    const tokens = await this.getTokens();
    if (!tokens) return;

    // Check if tokens are expired
    const isExpired = tokens.expiryTime < Date.now();
    if (isExpired) {
      logger.info('Stored tokens are expired, clearing...');
      await this.clearTokens();
      return;
    }

    // Validate token structure
    if (!this.isValidTokenFormat(tokens.accessToken)) {
      logger.warn('Invalid access token format detected');
      await this.clearTokens();
      return;
    }

    logger.info('Stored tokens validated successfully');
  }

  /**
   * Generate token fingerprint for validation
   */
  private async generateTokenFingerprint(token: string): Promise<string> {
    // Use first and last 10 characters of token + device ID
    const tokenPart = token.substring(0, 10) + token.substring(token.length - 10);
    const deviceId = Platform.OS + '_' + (Platform.Version || 'unknown');
    return `${tokenPart}_${deviceId}`;
  }

  /**
   * Validate token format (basic JWT validation)
   */
  private isValidTokenFormat(token: string): boolean {
    // Basic JWT format validation (three base64 parts separated by dots)
    const parts = token.split('.');
    return parts.length === 3 && parts.every(part => {
      try {
        // Check if it's valid base64
        return /^[A-Za-z0-9_-]+$/.test(part);
      } catch {
        return false;
      }
    });
  }

  /**
   * Set up automatic token rotation
   */
  private setupTokenRotation(): void {
    // Clear any existing interval
    if (this.tokenRotationInterval) {
      clearInterval(this.tokenRotationInterval);
    }

    // Set up new rotation interval
    this.tokenRotationInterval = setInterval(async () => {
      const tokens = await this.getTokens();
      if (tokens && tokens.refreshToken) {
        logger.info('Performing scheduled token rotation');
        await this.refreshToken(tokens.refreshToken);
      }
    }, this.TOKEN_ROTATION_INTERVAL);
  }

  /**
   * Check if user is authenticated
   */
  async isAuthenticated(): Promise<boolean> {
    const token = await this.getValidAccessToken();
    return !!token;
  }

  /**
   * Get token expiry time
   */
  async getTokenExpiry(): Promise<number | null> {
    const tokens = await this.getTokens();
    return tokens?.expiryTime || null;
  }
}

export const secureTokenManager = SecureTokenManager.getInstance();

// Export convenience functions
export const storeTokens = (
  accessToken: string,
  refreshToken: string,
  expiresIn: number,
  tokenType?: string,
  scope?: string
) => secureTokenManager.storeTokens(accessToken, refreshToken, expiresIn, tokenType, scope);

export const getValidAccessToken = () => secureTokenManager.getValidAccessToken();
export const clearTokens = () => secureTokenManager.clearTokens();
export const isAuthenticated = () => secureTokenManager.isAuthenticated();