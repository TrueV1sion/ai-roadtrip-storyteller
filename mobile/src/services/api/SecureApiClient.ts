/**
 * Secure API Client with Certificate Pinning
 * Six Sigma DMAIC - IMPROVE Phase Implementation
 * 
 * Enhanced API client that integrates certificate pinning and security checks
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';
import { API_URL, ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY, TOKEN_EXPIRY_KEY, CSRF_TOKEN_KEY, CSRF_HEADER_NAME } from '@/config';
import { logger } from '@/services/logger';
import CertificatePinningService from '../security/CertificatePinningService';
import EnhancedMobileSecurityService, { SecurityLevel } from '../security/EnhancedMobileSecurityService';
import ApiClient, { ApiError } from './ApiClient';

interface SecureApiClientOptions {
  baseURL?: string;
  headers?: Record<string, string>;
  enableRetry?: boolean;
  maxRetries?: number;
  retryStatusCodes?: number[];
  timeoutMs?: number;
  enableTokenRefresh?: boolean;
  requireMinimumSecurity?: SecurityLevel;
  enableCertificatePinning?: boolean;
  blockOnSecurityFailure?: boolean;
}

interface SecurityContext {
  deviceSecure: boolean;
  securityLevel: SecurityLevel;
  certificatePinningActive: boolean;
  restrictedFeatures: string[];
}

export class SecureApiClient extends ApiClient {
  private requireMinimumSecurity: SecurityLevel;
  private enableCertificatePinning: boolean;
  private blockOnSecurityFailure: boolean;
  private securityContext: SecurityContext | null = null;
  private securityCheckPromise: Promise<SecurityContext> | null = null;

  constructor(options: SecureApiClientOptions = {}) {
    super(options);
    
    this.requireMinimumSecurity = options.requireMinimumSecurity || SecurityLevel.LOW;
    this.enableCertificatePinning = options.enableCertificatePinning ?? true;
    this.blockOnSecurityFailure = options.blockOnSecurityFailure ?? false;
  }

  /**
   * Initialize secure API client
   */
  async initialize(): Promise<void> {
    try {
      // Initialize certificate pinning if enabled
      if (this.enableCertificatePinning && !__DEV__) {
        await CertificatePinningService.initialize();
        logger.info('Certificate pinning initialized for API client');
      }

      // Initialize security service
      await EnhancedMobileSecurityService.initialize();

      // Perform initial security check
      await this.performSecurityCheck();

      logger.info('Secure API client initialized', {
        certificatePinning: this.enableCertificatePinning,
        minimumSecurity: this.requireMinimumSecurity
      });
    } catch (error) {
      logger.error('Failed to initialize secure API client', error);
      // Don't throw - allow graceful degradation
    }
  }

  /**
   * Perform security check before API calls
   */
  private async performSecurityCheck(): Promise<SecurityContext> {
    // If already checking, return the existing promise
    if (this.securityCheckPromise) {
      return this.securityCheckPromise;
    }

    this.securityCheckPromise = (async () => {
      try {
        const securityStatus = await EnhancedMobileSecurityService.getLastSecurityStatus();
        
        if (!securityStatus) {
          // No cached status, trigger a check
          await EnhancedMobileSecurityService.performSecurityCheck();
          const newStatus = await EnhancedMobileSecurityService.getLastSecurityStatus();
          
          if (!newStatus) {
            throw new Error('Unable to determine security status');
          }
          
          return this.createSecurityContext(newStatus);
        }

        // Check if status is recent (within 5 minutes)
        const statusAge = Date.now() - new Date(securityStatus.timestamp).getTime();
        if (statusAge > 5 * 60 * 1000) {
          // Status is old, trigger new check in background
          EnhancedMobileSecurityService.performSecurityCheck().catch(error => {
            logger.error('Background security check failed', error);
          });
        }

        return this.createSecurityContext(securityStatus);
      } catch (error) {
        logger.error('Security check failed', error);
        
        // Return degraded security context
        return {
          deviceSecure: false,
          securityLevel: SecurityLevel.NONE,
          certificatePinningActive: false,
          restrictedFeatures: []
        };
      } finally {
        this.securityCheckPromise = null;
      }
    })();

    const context = await this.securityCheckPromise;
    this.securityContext = context;
    return context;
  }

  /**
   * Create security context from status
   */
  private createSecurityContext(status: any): SecurityContext {
    const levelValues = {
      [SecurityLevel.NONE]: 0,
      [SecurityLevel.LOW]: 1,
      [SecurityLevel.MEDIUM]: 2,
      [SecurityLevel.HIGH]: 3,
      [SecurityLevel.CRITICAL]: 4
    };

    const deviceSecure = levelValues[status.securityLevel] >= levelValues[this.requireMinimumSecurity];

    return {
      deviceSecure,
      securityLevel: status.securityLevel,
      certificatePinningActive: status.certificatePinningActive,
      restrictedFeatures: status.restrictedFeatures || []
    };
  }

  /**
   * Validate security before making request
   */
  private async validateSecurity(endpoint: string): Promise<void> {
    const context = await this.performSecurityCheck();

    // Check if endpoint requires specific security level
    const endpointSecurity = this.getEndpointSecurityLevel(endpoint);
    const requiredLevel = this.getHigherSecurityLevel(this.requireMinimumSecurity, endpointSecurity);

    const levelValues = {
      [SecurityLevel.NONE]: 0,
      [SecurityLevel.LOW]: 1,
      [SecurityLevel.MEDIUM]: 2,
      [SecurityLevel.HIGH]: 3,
      [SecurityLevel.CRITICAL]: 4
    };

    if (levelValues[context.securityLevel] < levelValues[requiredLevel]) {
      const message = `Security level ${context.securityLevel} is insufficient for this operation. Required: ${requiredLevel}`;
      
      if (this.blockOnSecurityFailure) {
        throw new ApiError(message, 403, { 
          securityLevel: context.securityLevel,
          requiredLevel,
          reason: 'insufficient_security'
        });
      } else {
        logger.warn(message);
      }
    }

    // Check if feature is restricted
    const feature = this.getFeatureFromEndpoint(endpoint);
    if (feature && context.restrictedFeatures.includes(feature)) {
      const message = `Feature '${feature}' is restricted due to security concerns`;
      
      if (this.blockOnSecurityFailure) {
        throw new ApiError(message, 403, {
          feature,
          restrictedFeatures: context.restrictedFeatures,
          reason: 'feature_restricted'
        });
      } else {
        logger.warn(message);
      }
    }
  }

  /**
   * Get endpoint security level based on path
   */
  private getEndpointSecurityLevel(endpoint: string): SecurityLevel {
    // Define security levels for different endpoints
    const securityMapping: Record<string, SecurityLevel> = {
      '/api/auth': SecurityLevel.HIGH,
      '/api/payment': SecurityLevel.CRITICAL,
      '/api/booking': SecurityLevel.HIGH,
      '/api/user/profile': SecurityLevel.HIGH,
      '/api/user/preferences': SecurityLevel.MEDIUM,
      '/api/stories': SecurityLevel.LOW,
      '/api/navigation': SecurityLevel.LOW,
      '/api/voice': SecurityLevel.MEDIUM
    };

    // Check for pattern matches
    for (const [pattern, level] of Object.entries(securityMapping)) {
      if (endpoint.startsWith(pattern)) {
        return level;
      }
    }

    return SecurityLevel.LOW;
  }

  /**
   * Get feature from endpoint
   */
  private getFeatureFromEndpoint(endpoint: string): string | null {
    const featureMapping: Record<string, string> = {
      '/api/payment': 'payment',
      '/api/auth/biometric': 'biometric_auth',
      '/api/maps/offline': 'offline_maps',
      '/api/voice': 'voice_commands',
      '/api/booking': 'booking'
    };

    for (const [pattern, feature] of Object.entries(featureMapping)) {
      if (endpoint.startsWith(pattern)) {
        return feature;
      }
    }

    return null;
  }

  /**
   * Get higher security level
   */
  private getHigherSecurityLevel(level1: SecurityLevel, level2: SecurityLevel): SecurityLevel {
    const levelValues = {
      [SecurityLevel.NONE]: 0,
      [SecurityLevel.LOW]: 1,
      [SecurityLevel.MEDIUM]: 2,
      [SecurityLevel.HIGH]: 3,
      [SecurityLevel.CRITICAL]: 4
    };

    return levelValues[level1] > levelValues[level2] ? level1 : level2;
  }

  /**
   * Override fetch with security checks
   */
  private async secureFetch<T>(
    url: string,
    options: RequestInit,
    retries = 0
  ): Promise<any> {
    // Validate security before request
    await this.validateSecurity(url);

    // Add security headers
    const secureHeaders = await this.getSecureHeaders(options.headers);
    options.headers = secureHeaders;

    // Log security context for sensitive endpoints
    if (this.getEndpointSecurityLevel(url) >= SecurityLevel.HIGH) {
      logger.info('Secure API request', {
        endpoint: url,
        securityLevel: this.securityContext?.securityLevel,
        certificatePinning: this.securityContext?.certificatePinningActive
      });
    }

    // Use parent fetch with retry logic
    return super['fetchWithRetry']<T>(url, options, retries);
  }

  /**
   * Get secure headers with additional security tokens
   */
  private async getSecureHeaders(headers?: HeadersInit): Promise<Record<string, string>> {
    const baseHeaders = headers instanceof Headers 
      ? Object.fromEntries(headers.entries())
      : headers || {};

    // Add security context headers
    if (this.securityContext) {
      baseHeaders['X-Security-Level'] = this.securityContext.securityLevel;
      baseHeaders['X-Device-Secure'] = String(this.securityContext.deviceSecure);
      
      if (this.securityContext.certificatePinningActive) {
        baseHeaders['X-Certificate-Pinning'] = 'enabled';
      }
    }

    // Add device fingerprint if available
    const deviceFingerprint = await this.getDeviceFingerprint();
    if (deviceFingerprint) {
      baseHeaders['X-Device-Fingerprint'] = deviceFingerprint;
    }

    return baseHeaders;
  }

  /**
   * Get device fingerprint from security service
   */
  private async getDeviceFingerprint(): Promise<string | null> {
    try {
      const status = await EnhancedMobileSecurityService.getLastSecurityStatus();
      return status?.deviceFingerprint || null;
    } catch {
      return null;
    }
  }

  /**
   * Secure HTTP methods with enhanced security
   */
  async get<T>(url: string, params?: Record<string, any>): Promise<T> {
    const headers = await this.getHeaders(false);
    
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
    
    const response = await this.secureFetch<T>(fullUrl, {
      method: 'GET',
      headers,
      credentials: 'include'
    });
    
    return response.data;
  }

  async post<T>(url: string, data?: any, params?: Record<string, any>): Promise<T> {
    const headers = await this.getHeaders(true);
    
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
    
    const response = await this.secureFetch<T>(fullUrl, {
      method: 'POST',
      headers,
      body: data ? JSON.stringify(data) : undefined,
      credentials: 'include'
    });
    
    return response.data;
  }

  async put<T>(url: string, data?: any): Promise<T> {
    const headers = await this.getHeaders(true);
    
    const response = await this.secureFetch<T>(url, {
      method: 'PUT',
      headers,
      body: data ? JSON.stringify(data) : undefined,
      credentials: 'include'
    });
    
    return response.data;
  }

  async patch<T>(url: string, data?: any): Promise<T> {
    const headers = await this.getHeaders(true);
    
    const response = await this.secureFetch<T>(url, {
      method: 'PATCH',
      headers,
      body: data ? JSON.stringify(data) : undefined,
      credentials: 'include'
    });
    
    return response.data;
  }

  async delete<T>(url: string, data?: any): Promise<T> {
    const headers = await this.getHeaders(true);
    
    const response = await this.secureFetch<T>(url, {
      method: 'DELETE',
      headers,
      body: data ? JSON.stringify(data) : undefined,
      credentials: 'include'
    });
    
    return response.data;
  }

  /**
   * Make a secure request with custom security level
   */
  async secureRequest<T>(
    url: string,
    options: RequestInit & { minimumSecurity?: SecurityLevel }
  ): Promise<T> {
    // Temporarily override minimum security if specified
    const originalMinSecurity = this.requireMinimumSecurity;
    if (options.minimumSecurity) {
      this.requireMinimumSecurity = options.minimumSecurity;
    }

    try {
      const headers = await this.getHeaders(options.method !== 'GET');
      const response = await this.secureFetch<T>(url, {
        ...options,
        headers: { ...headers, ...(options.headers || {}) }
      });
      
      return response.data;
    } finally {
      this.requireMinimumSecurity = originalMinSecurity;
    }
  }

  /**
   * Check if API is accessible based on security
   */
  async isApiAccessible(endpoint?: string): Promise<boolean> {
    try {
      const context = await this.performSecurityCheck();
      
      if (!endpoint) {
        return context.deviceSecure;
      }

      const requiredLevel = this.getEndpointSecurityLevel(endpoint);
      const levelValues = {
        [SecurityLevel.NONE]: 0,
        [SecurityLevel.LOW]: 1,
        [SecurityLevel.MEDIUM]: 2,
        [SecurityLevel.HIGH]: 3,
        [SecurityLevel.CRITICAL]: 4
      };

      return levelValues[context.securityLevel] >= levelValues[requiredLevel];
    } catch {
      return false;
    }
  }

  /**
   * Get current security context
   */
  async getSecurityContext(): Promise<SecurityContext> {
    if (!this.securityContext) {
      await this.performSecurityCheck();
    }
    return this.securityContext!;
  }

  /**
   * Update certificate pins dynamically
   */
  async updateCertificatePins(pins: any[]): Promise<void> {
    if (this.enableCertificatePinning) {
      await CertificatePinningService.updatePins(pins);
      logger.info('Certificate pins updated for secure API client');
    }
  }

  /**
   * Disable security checks (for testing only)
   */
  disableSecurityChecks(): void {
    logger.warn('Security checks disabled - FOR TESTING ONLY');
    this.blockOnSecurityFailure = false;
    this.requireMinimumSecurity = SecurityLevel.NONE;
  }

  /**
   * Re-enable security checks
   */
  enableSecurityChecks(): void {
    logger.info('Security checks re-enabled');
    this.blockOnSecurityFailure = true;
    this.requireMinimumSecurity = SecurityLevel.LOW;
  }
}

// Export singleton instance for app-wide use
export const secureApiClient = new SecureApiClient({
  requireMinimumSecurity: SecurityLevel.LOW,
  enableCertificatePinning: true,
  blockOnSecurityFailure: false // Warn but don't block by default
});

// Initialize on import
secureApiClient.initialize().catch(error => {
  logger.error('Failed to initialize secure API client', error);
});

export default SecureApiClient;