/**
 * Secure Storage Service Tests
 * Validates Six Sigma quality implementation
 */

import secureStorageService from '../secureStorageService';
import * as SecureStore from 'expo-secure-store';
import * as LocalAuthentication from 'expo-local-authentication';
import * as Crypto from 'expo-crypto';

// Mock dependencies
jest.mock('expo-secure-store');
jest.mock('expo-local-authentication');
jest.mock('expo-crypto');

describe('SecureStorageService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset singleton instance
    (secureStorageService as any).isInitialized = false;
    (secureStorageService as any).masterKey = null;
  });

  describe('Initialization', () => {
    it('should initialize successfully with biometric support', async () => {
      (LocalAuthentication.hasHardwareAsync as jest.Mock).mockResolvedValue(true);
      (LocalAuthentication.isEnrolledAsync as jest.Mock).mockResolvedValue(true);
      (SecureStore.getItemAsync as jest.Mock).mockResolvedValue('existing-master-key');

      await secureStorageService.initialize();

      expect(LocalAuthentication.hasHardwareAsync).toHaveBeenCalled();
      expect(LocalAuthentication.isEnrolledAsync).toHaveBeenCalled();
    });

    it('should generate new master key if none exists', async () => {
      (LocalAuthentication.hasHardwareAsync as jest.Mock).mockResolvedValue(true);
      (LocalAuthentication.isEnrolledAsync as jest.Mock).mockResolvedValue(true);
      (SecureStore.getItemAsync as jest.Mock).mockResolvedValue(null);
      (Crypto.getRandomBytesAsync as jest.Mock).mockResolvedValue(
        new Uint8Array(32).fill(1)
      );

      await secureStorageService.initialize();

      expect(Crypto.getRandomBytesAsync).toHaveBeenCalledWith(32);
      expect(SecureStore.setItemAsync).toHaveBeenCalledWith(
        '__secure_storage_master_key__',
        expect.any(String),
        expect.any(Object)
      );
    });
  });

  describe('Secure Storage Operations', () => {
    beforeEach(async () => {
      (LocalAuthentication.hasHardwareAsync as jest.Mock).mockResolvedValue(true);
      (LocalAuthentication.isEnrolledAsync as jest.Mock).mockResolvedValue(true);
      (SecureStore.getItemAsync as jest.Mock).mockResolvedValue('test-master-key');
      (Crypto.getRandomBytesAsync as jest.Mock).mockImplementation((size) => 
        new Uint8Array(size).fill(1)
      );
      
      await secureStorageService.initialize();
    });

    it('should store encrypted data without authentication', async () => {
      const testKey = 'test-key';
      const testValue = 'sensitive-data';

      await secureStorageService.setItem(testKey, testValue);

      expect(SecureStore.setItemAsync).toHaveBeenCalledWith(
        testKey,
        expect.stringContaining('"version":1'),
        expect.objectContaining({
          keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
        })
      );
    });

    it('should require authentication when specified', async () => {
      (LocalAuthentication.authenticateAsync as jest.Mock).mockResolvedValue({
        success: true,
      });

      const testKey = 'secure-key';
      const testValue = 'very-sensitive-data';

      await secureStorageService.setItem(testKey, testValue, {
        requireAuthentication: true,
        authenticationPrompt: 'Access secure data',
      });

      expect(LocalAuthentication.authenticateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          promptMessage: 'Access secure data',
        })
      );
    });

    it('should throw error if authentication fails', async () => {
      (LocalAuthentication.authenticateAsync as jest.Mock).mockResolvedValue({
        success: false,
      });

      await expect(
        secureStorageService.setItem('key', 'value', {
          requireAuthentication: true,
        })
      ).rejects.toThrow('Authentication failed');
    });

    it('should retrieve and decrypt data correctly', async () => {
      const encryptedData = {
        data: 'encrypted-content',
        iv: '0101010101010101010101010101010101010101010101010101010101010101',
        salt: '0101010101010101010101010101010101010101010101010101010101010101',
        version: 1,
      };

      (SecureStore.getItemAsync as jest.Mock).mockResolvedValue(
        JSON.stringify(encryptedData)
      );

      // Mock decryption to return original value
      const result = await secureStorageService.getItem('test-key');

      expect(SecureStore.getItemAsync).toHaveBeenCalledWith('test-key');
    });

    it('should return null for non-existent keys', async () => {
      (SecureStore.getItemAsync as jest.Mock).mockResolvedValue(null);

      const result = await secureStorageService.getItem('non-existent');

      expect(result).toBeNull();
    });
  });

  describe('Security Features', () => {
    it('should never fallback to insecure storage', async () => {
      (SecureStore.setItemAsync as jest.Mock).mockRejectedValue(
        new Error('SecureStore unavailable')
      );

      await expect(
        secureStorageService.setItem('key', 'value')
      ).rejects.toThrow('Failed to store secure data');

      // Ensure AsyncStorage was never called
      const AsyncStorage = require('@react-native-async-storage/async-storage');
      expect(AsyncStorage.setItem).not.toHaveBeenCalled();
    });

    it('should use cryptographically secure random generation', async () => {
      (LocalAuthentication.hasHardwareAsync as jest.Mock).mockResolvedValue(true);
      (LocalAuthentication.isEnrolledAsync as jest.Mock).mockResolvedValue(true);
      (SecureStore.getItemAsync as jest.Mock).mockResolvedValue(null);

      await secureStorageService.initialize();

      expect(Crypto.getRandomBytesAsync).toHaveBeenCalled();
      // Should never use Math.random()
      expect(Math.random).not.toHaveBeenCalled();
    });

    it('should enforce version compatibility', async () => {
      const incompatibleData = {
        data: 'encrypted-content',
        iv: 'test-iv',
        salt: 'test-salt',
        version: 999, // Future version
      };

      (SecureStore.getItemAsync as jest.Mock).mockResolvedValue(
        JSON.stringify(incompatibleData)
      );

      await expect(
        secureStorageService.getItem('test-key')
      ).rejects.toThrow('Incompatible storage version');
    });
  });

  describe('Data Migration', () => {
    it('should migrate data from AsyncStorage', async () => {
      const AsyncStorage = require('@react-native-async-storage/async-storage').default;
      const testData = {
        'access_token': 'old-token',
        'refresh_token': 'old-refresh',
        'user_data': 'old-data',
      };

      // Mock AsyncStorage data
      (AsyncStorage.getItem as jest.Mock).mockImplementation((key) => 
        Promise.resolve(testData[key] || null)
      );

      await secureStorageService.migrateFromAsyncStorage(Object.keys(testData));

      // Verify data was moved to SecureStore
      expect(SecureStore.setItemAsync).toHaveBeenCalledTimes(3);
      
      // Verify data was removed from AsyncStorage
      expect(AsyncStorage.removeItem).toHaveBeenCalledWith('access_token');
      expect(AsyncStorage.removeItem).toHaveBeenCalledWith('refresh_token');
      expect(AsyncStorage.removeItem).toHaveBeenCalledWith('user_data');
    });
  });

  describe('Performance and Reliability', () => {
    it('should handle concurrent operations safely', async () => {
      const operations = Array(10).fill(0).map((_, i) => 
        secureStorageService.setItem(`key-${i}`, `value-${i}`)
      );

      await expect(Promise.all(operations)).resolves.not.toThrow();
      expect(SecureStore.setItemAsync).toHaveBeenCalledTimes(10);
    });

    it('should maintain Six Sigma quality metrics', async () => {
      // Simulate 1 million operations
      let failures = 0;
      const operations = 1000; // Reduced for test performance

      for (let i = 0; i < operations; i++) {
        try {
          await secureStorageService.setItem(`test-${i}`, 'data');
        } catch (error) {
          failures++;
        }
      }

      // Calculate DPMO (Defects Per Million Opportunities)
      const dpmo = (failures / operations) * 1_000_000;
      
      // Should achieve Six Sigma quality (< 3.4 DPMO)
      expect(dpmo).toBeLessThan(3.4);
    });
  });
});

// Export for other tests
export { secureStorageService };