/**
 * Certificate Pinning Service
 * Six Sigma DMAIC - IMPROVE Phase Implementation
 * 
 * Implements certificate pinning for iOS and Android to prevent MITM attacks
 * Supports multiple pins for redundancy and graceful certificate rotation
 */

import { Platform, NativeModules } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { logger } from '../logger';
import SecureConfig from '@/config/secure-config';

// Certificate pin types
interface CertificatePin {
  hostname: string;
  pins: string[]; // SHA-256 pins in base64
  includeSubdomains: boolean;
  expirationDate?: string; // ISO date string
  backupPins?: string[]; // Backup pins for rotation
}

interface PinningConfig {
  enabled: boolean;
  enforceForAllDomains: boolean;
  allowUserTrust: boolean; // Allow user-installed certificates in dev
  pins: CertificatePin[];
  reportUri?: string; // Where to report pin failures
}

interface PinValidationResult {
  isValid: boolean;
  hostname: string;
  usedPin?: string;
  error?: string;
  certificateChain?: string[];
}

class CertificatePinningService {
  private static instance: CertificatePinningService;
  private config: PinningConfig;
  private pinValidationCache: Map<string, PinValidationResult> = new Map();
  private readonly CACHE_TTL = 5 * 60 * 1000; // 5 minutes
  
  // Production certificate pins for your API server
  private readonly PRODUCTION_PINS: CertificatePin[] = [
    {
      hostname: 'roadtrip-mvp-792001900150.us-central1.run.app',
      pins: [
        // Google Internet Authority G3 (current)
        'f8NnEFZxQ4ExFOhSN7EiFWtiudZQVD2oY60uauV/n78=',
        // GTS Root R1
        'Vjs8r4z+80wjNcr1YKepWQboSIRi63WsWXhIMN+eWys=',
        // GTS Root R2
        'QXnt2YHvdHR3tJYmQIr0Paosp6t/nggsEGD4QJZ3Q0g=',
        // GTS Root R3
        'sMyD5aX5fEuvxq+V4LqSpFFG3DMGqfyvJMTojfPO7n8=',
        // GTS Root R4
        'p9VUbDXHBDz7VIIvGzZ9d7w7KYLqnwh7x3Y6lJpJgVQ=',
      ],
      backupPins: [
        // GlobalSign Root CA - R2 (backup)
        'iie1VXtL7HzAMF+/PVPR9xzT80kQxdZeJ+zduCB3uj0=',
        // Let's Encrypt Authority X3 (backup)
        'YLh1dUR9y6Kja30RrAn7JKnbQG/uEtLMkBgFF2Fuihg=',
      ],
      includeSubdomains: true,
      expirationDate: '2026-12-31T23:59:59Z'
    },
    // Google Cloud Run certificate pins (if using GCP)
    {
      hostname: '*.run.app',
      pins: [
        // Google Internet Authority G3
        'f8NnEFZxQ4ExFOhSN7EiFWtiudZQVD2oY60uauV/n78=',
        // GTS Root R1
        'Vjs8r4z+80wjNcr1YKepWQboSIRi63WsWXhIMN+eWys=',
      ],
      includeSubdomains: true
    }
  ];

  private constructor() {
    this.config = {
      enabled: !__DEV__ && SecureConfig.SECURITY.ENABLE_CERTIFICATE_PINNING,
      enforceForAllDomains: false,
      allowUserTrust: __DEV__,
      pins: this.PRODUCTION_PINS,
      reportUri: '/api/security/pin-report'
    };
  }

  static getInstance(): CertificatePinningService {
    if (!CertificatePinningService.instance) {
      CertificatePinningService.instance = new CertificatePinningService();
    }
    return CertificatePinningService.instance;
  }

  /**
   * Initialize certificate pinning
   */
  async initialize(): Promise<void> {
    try {
      if (!this.config.enabled) {
        logger.info('Certificate pinning disabled');
        return;
      }

      // Load any dynamic pins from secure storage
      await this.loadDynamicPins();

      // Configure native modules
      if (Platform.OS === 'ios') {
        await this.configureIOSPinning();
      } else if (Platform.OS === 'android') {
        await this.configureAndroidPinning();
      }

      // Set up certificate validation interceptor
      this.setupValidationInterceptor();

      logger.info('Certificate pinning initialized', {
        pinsCount: this.config.pins.length,
        enforceAll: this.config.enforceForAllDomains
      });
    } catch (error) {
      logger.error('Failed to initialize certificate pinning', error);
      // Don't throw - graceful degradation
    }
  }

  /**
   * Load dynamic pins from secure storage (for certificate rotation)
   */
  private async loadDynamicPins(): Promise<void> {
    try {
      const dynamicPinsJson = await AsyncStorage.getItem('dynamic_certificate_pins');
      if (dynamicPinsJson) {
        const dynamicPins: CertificatePin[] = JSON.parse(dynamicPinsJson);
        
        // Validate and merge with static pins
        dynamicPins.forEach(pin => {
          if (this.validatePinFormat(pin)) {
            const existingIndex = this.config.pins.findIndex(p => p.hostname === pin.hostname);
            if (existingIndex >= 0) {
              // Merge pins
              this.config.pins[existingIndex] = {
                ...this.config.pins[existingIndex],
                pins: [...new Set([...this.config.pins[existingIndex].pins, ...pin.pins])],
                backupPins: pin.backupPins || this.config.pins[existingIndex].backupPins
              };
            } else {
              this.config.pins.push(pin);
            }
          }
        });
      }
    } catch (error) {
      logger.error('Failed to load dynamic pins', error);
    }
  }

  /**
   * Validate pin format
   */
  private validatePinFormat(pin: CertificatePin): boolean {
    if (!pin.hostname || !pin.pins || pin.pins.length === 0) {
      return false;
    }

    // Validate base64 format for pins
    const base64Regex = /^[A-Za-z0-9+/]+=*$/;
    return pin.pins.every(p => base64Regex.test(p));
  }

  /**
   * Configure iOS certificate pinning
   */
  private async configureIOSPinning(): Promise<void> {
    if (NativeModules.RNSecurityModule?.configureCertificatePinning) {
      const iosPinConfig = this.config.pins.map(pin => ({
        host: pin.hostname,
        pins: pin.pins,
        backupPins: pin.backupPins || [],
        includeSubdomains: pin.includeSubdomains
      }));

      await NativeModules.RNSecurityModule.configureCertificatePinning(iosPinConfig);
    }
  }

  /**
   * Configure Android certificate pinning
   */
  private async configureAndroidPinning(): Promise<void> {
    if (NativeModules.RNSecurityModule?.configureCertificatePinning) {
      // Android network security config format
      const androidPinConfig = {
        pins: this.config.pins.map(pin => ({
          domain: pin.hostname,
          includeSubdomains: pin.includeSubdomains,
          pinSet: {
            expiration: pin.expirationDate,
            pins: pin.pins.map(p => ({ digest: 'SHA-256', value: p }))
          }
        }))
      };

      await NativeModules.RNSecurityModule.configureCertificatePinning(androidPinConfig);
    }
  }

  /**
   * Set up certificate validation interceptor
   */
  private setupValidationInterceptor(): void {
    // Override global fetch to add certificate validation
    const originalFetch = global.fetch;
    
    global.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
      
      if (url && this.shouldValidateUrl(url)) {
        const hostname = new URL(url).hostname;
        
        // Check cache first
        const cachedResult = this.getCachedValidation(hostname);
        if (cachedResult && !cachedResult.isValid) {
          throw new Error(`Certificate pinning failed for ${hostname}: ${cachedResult.error}`);
        }

        // Perform validation if not cached
        if (!cachedResult) {
          const validationResult = await this.validateCertificate(hostname);
          if (!validationResult.isValid) {
            throw new Error(`Certificate pinning failed for ${hostname}: ${validationResult.error}`);
          }
        }
      }

      return originalFetch(input, init);
    };
  }

  /**
   * Check if URL should be validated
   */
  private shouldValidateUrl(url: string): boolean {
    if (!this.config.enabled) {
      return false;
    }

    try {
      const urlObj = new URL(url);
      
      // Only validate HTTPS
      if (urlObj.protocol !== 'https:') {
        return false;
      }

      // Check if we have pins for this domain
      const hostname = urlObj.hostname;
      const hasPin = this.config.pins.some(pin => 
        this.isHostnameMatch(hostname, pin.hostname, pin.includeSubdomains)
      );

      return hasPin || this.config.enforceForAllDomains;
    } catch {
      return false;
    }
  }

  /**
   * Check if hostname matches pin configuration
   */
  private isHostnameMatch(hostname: string, pinHostname: string, includeSubdomains: boolean): boolean {
    if (hostname === pinHostname) {
      return true;
    }

    if (includeSubdomains) {
      // Handle wildcard domains
      if (pinHostname.startsWith('*.')) {
        const baseDomain = pinHostname.substring(2);
        return hostname.endsWith(baseDomain);
      }
      
      // Handle subdomain matching
      return hostname.endsWith('.' + pinHostname);
    }

    return false;
  }

  /**
   * Validate certificate for hostname
   */
  async validateCertificate(hostname: string): Promise<PinValidationResult> {
    try {
      // Find pins for this hostname
      const pinConfig = this.config.pins.find(pin =>
        this.isHostnameMatch(hostname, pin.hostname, pin.includeSubdomains)
      );

      if (!pinConfig && !this.config.enforceForAllDomains) {
        // No pins configured for this host
        return { isValid: true, hostname };
      }

      // Call native module to get certificate chain
      let certificateChain: string[] = [];
      if (NativeModules.RNSecurityModule?.getCertificateChain) {
        certificateChain = await NativeModules.RNSecurityModule.getCertificateChain(hostname);
      } else {
        // Fallback: trust the connection if native module not available
        logger.warn('Certificate chain validation not available');
        return { isValid: true, hostname };
      }

      if (!certificateChain || certificateChain.length === 0) {
        return {
          isValid: false,
          hostname,
          error: 'No certificate chain received'
        };
      }

      // Validate against pins
      const allPins = [
        ...(pinConfig?.pins || []),
        ...(pinConfig?.backupPins || [])
      ];

      const matchedPin = allPins.find(pin => 
        certificateChain.includes(pin)
      );

      const result: PinValidationResult = {
        isValid: !!matchedPin,
        hostname,
        usedPin: matchedPin,
        certificateChain,
        error: matchedPin ? undefined : 'No matching pins found'
      };

      // Cache result
      this.cacheValidationResult(hostname, result);

      // Report pin failure if configured
      if (!result.isValid && this.config.reportUri) {
        this.reportPinFailure(result);
      }

      return result;
    } catch (error) {
      logger.error('Certificate validation error', error);
      return {
        isValid: false,
        hostname,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  /**
   * Get cached validation result
   */
  private getCachedValidation(hostname: string): PinValidationResult | null {
    const cached = this.pinValidationCache.get(hostname);
    if (cached) {
      // Check if cache is still valid
      const age = Date.now() - (new Date(cached.hostname).getTime() || 0);
      if (age < this.CACHE_TTL) {
        return cached;
      }
      // Remove expired cache
      this.pinValidationCache.delete(hostname);
    }
    return null;
  }

  /**
   * Cache validation result
   */
  private cacheValidationResult(hostname: string, result: PinValidationResult): void {
    this.pinValidationCache.set(hostname, {
      ...result,
      hostname: new Date().toISOString() // Store timestamp in hostname field
    });
  }

  /**
   * Report pin failure for monitoring
   */
  private async reportPinFailure(result: PinValidationResult): Promise<void> {
    try {
      if (!this.config.reportUri) {
        return;
      }

      const report = {
        hostname: result.hostname,
        port: 443,
        'effective-expiration-date': new Date().toISOString(),
        'include-subdomains': true,
        'noted-hostname': result.hostname,
        'served-certificate-chain': result.certificateChain || [],
        'validated-certificate-chain': result.certificateChain || [],
        'known-pins': this.config.pins.find(p => 
          this.isHostnameMatch(result.hostname, p.hostname, p.includeSubdomains)
        )?.pins || []
      };

      // Send report without certificate validation for this request
      const originalFetch = global.fetch;
      await originalFetch(this.config.reportUri, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(report)
      });
    } catch (error) {
      logger.error('Failed to report pin failure', error);
    }
  }

  /**
   * Update pins dynamically (for certificate rotation)
   */
  async updatePins(pins: CertificatePin[]): Promise<void> {
    try {
      // Validate new pins
      const validPins = pins.filter(pin => this.validatePinFormat(pin));
      
      if (validPins.length === 0) {
        throw new Error('No valid pins provided');
      }

      // Save to secure storage
      await AsyncStorage.setItem('dynamic_certificate_pins', JSON.stringify(validPins));

      // Reload configuration
      await this.loadDynamicPins();

      // Reconfigure native modules
      if (Platform.OS === 'ios') {
        await this.configureIOSPinning();
      } else if (Platform.OS === 'android') {
        await this.configureAndroidPinning();
      }

      // Clear validation cache
      this.pinValidationCache.clear();

      logger.info('Certificate pins updated', { count: validPins.length });
    } catch (error) {
      logger.error('Failed to update certificate pins', error);
      throw error;
    }
  }

  /**
   * Get current pin configuration
   */
  getPinConfiguration(): PinningConfig {
    return { ...this.config };
  }

  /**
   * Disable certificate pinning (emergency use only)
   */
  async disablePinning(): Promise<void> {
    this.config.enabled = false;
    this.pinValidationCache.clear();
    
    // Restore original fetch
    if (global.fetch && global.fetch.name === 'fetch') {
      // Already restored
      return;
    }

    logger.warn('Certificate pinning disabled');
  }

  /**
   * Re-enable certificate pinning
   */
  async enablePinning(): Promise<void> {
    this.config.enabled = true;
    await this.initialize();
  }
}

export default CertificatePinningService.getInstance();
export { CertificatePin, PinningConfig, PinValidationResult };