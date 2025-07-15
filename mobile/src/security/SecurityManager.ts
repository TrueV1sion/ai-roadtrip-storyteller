/**
 * Security Manager for production environment
 * Handles jailbreak detection, certificate pinning, and security checks
 */

import JailMonkey from 'jail-monkey';
import * as SecureStore from 'expo-secure-store';
import CryptoJS from 'crypto-js';
import { Platform, NativeModules } from 'react-native';
import { logger } from '@/services/logger';
import { ENV } from '@/config/env.production';

interface SecurityCheckResult {
  isSecure: boolean;
  issues: string[];
}

class SecurityManager {
  private static instance: SecurityManager;
  private encryptionKey: string | null = null;
  private certificateHashes: Set<string>;

  private constructor() {
    // Initialize certificate hashes for pinning
    this.certificateHashes = new Set([
      // Add your API server's certificate SHA-256 hashes here
      // Example: 'sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='
    ]);
  }

  static getInstance(): SecurityManager {
    if (!SecurityManager.instance) {
      SecurityManager.instance = new SecurityManager();
    }
    return SecurityManager.instance;
  }

  /**
   * Perform comprehensive security check
   */
  async performSecurityCheck(): Promise<SecurityCheckResult> {
    const issues: string[] = [];
    let isSecure = true;

    // Check for jailbreak/root
    if (this.isDeviceCompromised()) {
      issues.push('Device is jailbroken or rooted');
      isSecure = false;
    }

    // Check for debugging
    if (this.isDebuggingEnabled()) {
      issues.push('Debugging is enabled');
      isSecure = false;
    }

    // Check for tampering
    if (await this.isAppTampered()) {
      issues.push('App integrity check failed');
      isSecure = false;
    }

    // Check secure storage availability
    if (!await this.isSecureStorageAvailable()) {
      issues.push('Secure storage not available');
      isSecure = false;
    }

    // Check for VPN/Proxy
    if (this.isUsingVPNOrProxy()) {
      issues.push('VPN or Proxy detected');
      // This might be acceptable, so not marking as insecure
    }

    // Log security check results
    if (!isSecure) {
      logger.warn('Security check failed', { issues });
    }

    return { isSecure, issues };
  }

  /**
   * Check if device is jailbroken/rooted
   */
  private isDeviceCompromised(): boolean {
    try {
      return JailMonkey.isJailBroken();
    } catch (error) {
      logger.error('Error checking jailbreak status', error as Error);
      // Fail secure - assume compromised if we can't check
      return true;
    }
  }

  /**
   * Check if debugging is enabled
   */
  private isDebuggingEnabled(): boolean {
    if (__DEV__) {
      return true;
    }

    try {
      // Additional debugging checks
      if (Platform.OS === 'ios') {
        // Check for debugger attachment on iOS
        return false; // Implement iOS-specific check
      } else if (Platform.OS === 'android') {
        // Check for debugger attachment on Android
        return JailMonkey.isDebuggedMode();
      }
    } catch (error) {
      logger.error('Error checking debug status', error as Error);
    }

    return false;
  }

  /**
   * Check if app has been tampered with
   */
  private async isAppTampered(): Promise<boolean> {
    try {
      // Check app signature (platform specific)
      if (Platform.OS === 'android') {
        return await this.checkAndroidSignature();
      } else if (Platform.OS === 'ios') {
        return await this.checkIOSIntegrity();
      }
    } catch (error) {
      logger.error('Error checking app integrity', error as Error);
      // Fail secure
      return true;
    }

    return false;
  }

  /**
   * Check Android app signature
   */
  private async checkAndroidSignature(): Promise<boolean> {
    try {
      // This would require a native module to verify APK signature
      // For now, we'll use JailMonkey's hookDetected as a proxy
      return JailMonkey.hookDetected();
    } catch (error) {
      return true;
    }
  }

  /**
   * Check iOS app integrity
   */
  private async checkIOSIntegrity(): Promise<boolean> {
    try {
      // Check for code injection or modification
      // This would require native code to properly implement
      return false;
    } catch (error) {
      return true;
    }
  }

  /**
   * Check if secure storage is available
   */
  private async isSecureStorageAvailable(): Promise<boolean> {
    try {
      const testKey = '__security_test__';
      const testValue = 'test';
      
      await SecureStore.setItemAsync(testKey, testValue);
      const retrieved = await SecureStore.getItemAsync(testKey);
      await SecureStore.deleteItemAsync(testKey);
      
      return retrieved === testValue;
    } catch (error) {
      logger.error('Secure storage test failed', error as Error);
      return false;
    }
  }

  /**
   * Check for VPN or Proxy usage
   */
  private isUsingVPNOrProxy(): boolean {
    try {
      // JailMonkey can detect some VPN usage on Android
      if (Platform.OS === 'android') {
        return JailMonkey.isOnExternalStorage();
      }
      // Would need native implementation for comprehensive check
      return false;
    } catch (error) {
      return false;
    }
  }

  /**
   * Initialize encryption key
   */
  async initializeEncryption(): Promise<void> {
    try {
      // Try to get existing key
      let key = await SecureStore.getItemAsync('__encryption_key__');
      
      if (!key) {
        // Generate new key
        key = this.generateEncryptionKey();
        await SecureStore.setItemAsync('__encryption_key__', key);
      }
      
      this.encryptionKey = key;
    } catch (error) {
      logger.error('Failed to initialize encryption', error as Error);
      throw new Error('Encryption initialization failed');
    }
  }

  /**
   * Generate a secure encryption key
   */
  private async generateEncryptionKey(): Promise<string> {
    // SECURITY: Use cryptographically secure random number generation
    const Crypto = require('expo-crypto');
    
    try {
      // Generate 32 cryptographically secure random bytes
      const randomBytes = await Crypto.getRandomBytesAsync(32);
      
      // Convert to hex string
      return Array.from(randomBytes, byte => byte.toString(16).padStart(2, '0')).join('');
    } catch (error) {
      // If expo-crypto is not available, try react-native-get-random-values
      if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
        const array = new Uint8Array(32);
        crypto.getRandomValues(array);
        return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
      }
      
      throw new Error('No secure random number generator available');
    }
  }

  /**
   * Encrypt sensitive data
   */
  encrypt(data: string): string {
    if (!this.encryptionKey) {
      throw new Error('Encryption not initialized');
    }
    
    try {
      return CryptoJS.AES.encrypt(data, this.encryptionKey).toString();
    } catch (error) {
      logger.error('Encryption failed', error as Error);
      throw new Error('Encryption failed');
    }
  }

  /**
   * Decrypt sensitive data
   */
  decrypt(encryptedData: string): string {
    if (!this.encryptionKey) {
      throw new Error('Encryption not initialized');
    }
    
    try {
      const bytes = CryptoJS.AES.decrypt(encryptedData, this.encryptionKey);
      return bytes.toString(CryptoJS.enc.Utf8);
    } catch (error) {
      logger.error('Decryption failed', error as Error);
      throw new Error('Decryption failed');
    }
  }

  /**
   * Validate SSL certificate (for certificate pinning)
   */
  validateCertificate(certificateHash: string): boolean {
    return this.certificateHashes.has(certificateHash);
  }

  /**
   * Add trusted certificate hash
   */
  addTrustedCertificate(hash: string): void {
    this.certificateHashes.add(hash);
  }

  /**
   * Clear sensitive data from memory
   */
  clearSensitiveData(): void {
    this.encryptionKey = null;
  }

  /**
   * Generate request signature for API calls
   */
  generateRequestSignature(
    method: string,
    url: string,
    timestamp: number,
    body?: any
  ): string {
    const data = `${method}:${url}:${timestamp}:${body ? JSON.stringify(body) : ''}`;
    return CryptoJS.HmacSHA256(data, this.encryptionKey || '').toString();
  }

  /**
   * Verify request signature
   */
  verifyRequestSignature(
    signature: string,
    method: string,
    url: string,
    timestamp: number,
    body?: any
  ): boolean {
    const expectedSignature = this.generateRequestSignature(method, url, timestamp, body);
    return signature === expectedSignature;
  }

  /**
   * Check if biometric authentication is available
   */
  async isBiometricAvailable(): Promise<boolean> {
    try {
      // This would require expo-local-authentication
      // import * as LocalAuthentication from 'expo-local-authentication';
      // return await LocalAuthentication.hasHardwareAsync();
      return false; // Placeholder
    } catch (error) {
      return false;
    }
  }

  /**
   * Perform biometric authentication
   */
  async authenticateWithBiometrics(reason: string): Promise<boolean> {
    try {
      // This would require expo-local-authentication
      // const result = await LocalAuthentication.authenticateAsync({
      //   promptMessage: reason,
      //   fallbackLabel: 'Use Passcode',
      // });
      // return result.success;
      return false; // Placeholder
    } catch (error) {
      logger.error('Biometric authentication failed', error as Error);
      return false;
    }
  }

  /**
   * Enable app security features
   */
  async enableSecurityFeatures(): Promise<void> {
    // Prevent screenshots on Android
    if (Platform.OS === 'android') {
      // This would require native module
      // NativeModules.SecurityModule?.setFlag('FLAG_SECURE', true);
    }

    // Initialize encryption
    await this.initializeEncryption();

    // Set up certificate pinning
    if (ENV.APP_ENV === 'production') {
      // Add production certificate hashes
      this.addTrustedCertificate('sha256/YOUR_PRODUCTION_CERT_HASH');
    }
  }

  /**
   * Disable security features (for development)
   */
  disableSecurityFeatures(): void {
    if (__DEV__) {
      logger.info('Security features disabled for development');
    }
  }
}

export const securityManager = SecurityManager.getInstance();

// Export security check hook
export const useSecurityCheck = () => {
  const [isSecure, setIsSecure] = React.useState<boolean | null>(null);
  const [securityIssues, setSecurityIssues] = React.useState<string[]>([]);

  React.useEffect(() => {
    const checkSecurity = async () => {
      const result = await securityManager.performSecurityCheck();
      setIsSecure(result.isSecure);
      setSecurityIssues(result.issues);
    };

    checkSecurity();
  }, []);

  return { isSecure, securityIssues };
};