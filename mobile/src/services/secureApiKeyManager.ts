/**
 * Secure API Key Manager
 * Handles API keys securely without exposing them in environment variables
 */

import secureStorageService from './secureStorageService';
import { API_CONFIG } from '../config/api';

interface ApiKeyConfig {
  keyId: string;
  endpoint: string;
  fallbackToProxy: boolean;
}

class SecureApiKeyManager {
  private static instance: SecureApiKeyManager;
  private apiKeys: Map<string, string> = new Map();
  private initialized = false;

  private readonly API_KEY_CONFIGS: Record<string, ApiKeyConfig> = {
    GOOGLE_MAPS: {
      keyId: 'google_maps_api_key',
      endpoint: '/api/proxy/google-maps',
      fallbackToProxy: true,
    },
    OPENWEATHER: {
      keyId: 'openweather_api_key',
      endpoint: '/api/proxy/weather',
      fallbackToProxy: true,
    },
    TICKETMASTER: {
      keyId: 'ticketmaster_api_key',
      endpoint: '/api/proxy/events',
      fallbackToProxy: true,
    },
    SPOTIFY: {
      keyId: 'spotify_client_secret',
      endpoint: '/api/proxy/spotify',
      fallbackToProxy: true,
    },
  };

  private constructor() {}

  static getInstance(): SecureApiKeyManager {
    if (!SecureApiKeyManager.instance) {
      SecureApiKeyManager.instance = new SecureApiKeyManager();
    }
    return SecureApiKeyManager.instance;
  }

  /**
   * Initialize API key manager
   * In production, keys should be fetched from secure backend
   */
  async initialize(): Promise<void> {
    if (this.initialized) return;

    try {
      // In production, fetch encrypted keys from backend
      // For now, check if keys exist in secure storage
      for (const [serviceName, config] of Object.entries(this.API_KEY_CONFIGS)) {
        const storedKey = await secureStorageService.getItem(config.keyId);
        if (storedKey) {
          this.apiKeys.set(serviceName, storedKey);
        }
      }

      this.initialized = true;
    } catch (error) {
      console.error('Failed to initialize API key manager:', error);
      // Continue with proxy fallback
      this.initialized = true;
    }
  }

  /**
   * Get API key for a service
   * Returns null if proxy should be used instead
   */
  async getApiKey(serviceName: string): Promise<string | null> {
    await this.ensureInitialized();

    // Check if we have the key in memory
    const cachedKey = this.apiKeys.get(serviceName);
    if (cachedKey) {
      return cachedKey;
    }

    // Check configuration
    const config = this.API_KEY_CONFIGS[serviceName];
    if (!config) {
      throw new Error(`Unknown service: ${serviceName}`);
    }

    // Try to fetch from secure storage
    try {
      const storedKey = await secureStorageService.getItem(config.keyId);
      if (storedKey) {
        this.apiKeys.set(serviceName, storedKey);
        return storedKey;
      }
    } catch (error) {
      console.error(`Failed to retrieve API key for ${serviceName}:`, error);
    }

    // Return null to indicate proxy should be used
    return null;
  }

  /**
   * Get proxy endpoint for a service
   */
  getProxyEndpoint(serviceName: string): string {
    const config = this.API_KEY_CONFIGS[serviceName];
    if (!config) {
      throw new Error(`Unknown service: ${serviceName}`);
    }
    return `${API_CONFIG.BASE_URL}${config.endpoint}`;
  }

  /**
   * Check if a service should use proxy
   */
  async shouldUseProxy(serviceName: string): Promise<boolean> {
    const config = this.API_KEY_CONFIGS[serviceName];
    if (!config || !config.fallbackToProxy) {
      return false;
    }

    // Use proxy if no API key is available
    const apiKey = await this.getApiKey(serviceName);
    return !apiKey;
  }

  /**
   * Store API key securely (admin function)
   */
  async storeApiKey(
    serviceName: string,
    apiKey: string,
    requireAuth: boolean = true
  ): Promise<void> {
    const config = this.API_KEY_CONFIGS[serviceName];
    if (!config) {
      throw new Error(`Unknown service: ${serviceName}`);
    }

    await secureStorageService.setItem(config.keyId, apiKey, {
      requireAuthentication: requireAuth,
      authenticationPrompt: `Store API key for ${serviceName}?`,
    });

    // Update cache
    this.apiKeys.set(serviceName, apiKey);
  }

  /**
   * Remove API key (admin function)
   */
  async removeApiKey(serviceName: string): Promise<void> {
    const config = this.API_KEY_CONFIGS[serviceName];
    if (!config) {
      throw new Error(`Unknown service: ${serviceName}`);
    }

    await secureStorageService.removeItem(config.keyId);
    this.apiKeys.delete(serviceName);
  }

  /**
   * Clear all API keys (requires authentication)
   */
  async clearAllApiKeys(): Promise<void> {
    for (const [serviceName, config] of Object.entries(this.API_KEY_CONFIGS)) {
      await secureStorageService.removeItem(config.keyId);
      this.apiKeys.delete(serviceName);
    }
  }

  private async ensureInitialized(): Promise<void> {
    if (!this.initialized) {
      await this.initialize();
    }
  }
}

export default SecureApiKeyManager.getInstance();

// Service name constants
export const API_SERVICES = {
  GOOGLE_MAPS: 'GOOGLE_MAPS',
  OPENWEATHER: 'OPENWEATHER',
  TICKETMASTER: 'TICKETMASTER',
  SPOTIFY: 'SPOTIFY',
} as const;

export type ApiServiceName = keyof typeof API_SERVICES;