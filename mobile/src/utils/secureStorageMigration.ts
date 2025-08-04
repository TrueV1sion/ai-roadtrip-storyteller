/**
 * Secure Storage Migration Utility
 * Migrates sensitive data from AsyncStorage to SecureStore
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import secureStorageService from '../services/secureStorageService';
import * as SecureStore from 'expo-secure-store';

import { logger } from '@/services/logger';
interface MigrationResult {
  success: boolean;
  migratedKeys: string[];
  failedKeys: string[];
  errors: { key: string; error: string }[];
}

class SecureStorageMigration {
  // Keys that contain sensitive data and must be migrated
  private static readonly SENSITIVE_KEYS = [
    'access_token',
    'refresh_token',
    'token_expiry',
    'user_credentials',
    'user_email',
    'user_password',
    'api_key',
    'google_maps_key',
    'weather_api_key',
    'spotify_client_id',
    'spotify_client_secret',
    'csrf_token',
    'session_id',
    'biometric_settings',
    'encryption_key',
    'master_password',
  ];

  // Keys that can remain in AsyncStorage (non-sensitive)
  private static readonly SAFE_KEYS = [
    'user_preferences_theme',
    'app_language',
    'notification_settings',
    'tutorial_completed',
    'app_version',
    'last_sync_time',
  ];

  /**
   * Perform full migration of sensitive data
   */
  static async performMigration(): Promise<MigrationResult> {
    const result: MigrationResult = {
      success: true,
      migratedKeys: [],
      failedKeys: [],
      errors: [],
    };

    try {
      // Initialize secure storage
      await secureStorageService.initialize();

      // Get all keys from AsyncStorage
      const allKeys = await AsyncStorage.getAllKeys();
      
      // Filter sensitive keys
      const keysToMigrate = allKeys.filter(key => 
        this.SENSITIVE_KEYS.some(sensitiveKey => 
          key.toLowerCase().includes(sensitiveKey.toLowerCase())
        )
      );

      logger.debug(`Found ${keysToMigrate.length} sensitive keys to migrate`);

      // Migrate each key
      for (const key of keysToMigrate) {
        try {
          const value = await AsyncStorage.getItem(key);
          if (value !== null) {
            // Store in secure storage
            await secureStorageService.setItem(key, value);
            
            // Remove from AsyncStorage
            await AsyncStorage.removeItem(key);
            
            result.migratedKeys.push(key);
          }
        } catch (error) {
          result.success = false;
          result.failedKeys.push(key);
          result.errors.push({
            key,
            error: error.message || 'Unknown error',
          });
        }
      }

      // Log migration summary
      logger.debug(`Migration completed: ${result.migratedKeys.length} keys migrated`);
      if (result.failedKeys.length > 0) {
        logger.error(`Failed to migrate ${result.failedKeys.length} keys`);
      }

    } catch (error) {
      result.success = false;
      result.errors.push({
        key: 'general',
        error: error.message || 'Migration failed',
      });
    }

    return result;
  }

  /**
   * Check if migration is needed
   */
  static async isMigrationNeeded(): Promise<boolean> {
    try {
      const allKeys = await AsyncStorage.getAllKeys();
      
      // Check if any sensitive keys exist in AsyncStorage
      return allKeys.some(key => 
        this.SENSITIVE_KEYS.some(sensitiveKey => 
          key.toLowerCase().includes(sensitiveKey.toLowerCase())
        )
      );
    } catch (error) {
      logger.error('Error checking migration status:', error);
      return false;
    }
  }

  /**
   * Validate migration was successful
   */
  static async validateMigration(): Promise<boolean> {
    try {
      const allAsyncKeys = await AsyncStorage.getAllKeys();
      
      // Check no sensitive keys remain in AsyncStorage
      const remainingSensitiveKeys = allAsyncKeys.filter(key => 
        this.SENSITIVE_KEYS.some(sensitiveKey => 
          key.toLowerCase().includes(sensitiveKey.toLowerCase())
        )
      );

      if (remainingSensitiveKeys.length > 0) {
        logger.error('Sensitive keys still in AsyncStorage:', remainingSensitiveKeys);
        return false;
      }

      // Verify critical keys exist in SecureStore
      const criticalKeys = ['access_token', 'refresh_token'];
      for (const key of criticalKeys) {
        const value = await SecureStore.getItemAsync(key);
        if (!value) {
          logger.warn(`Critical key '${key}' not found in SecureStore`);
          // This might be okay if user hasn't logged in yet
        }
      }

      return true;
    } catch (error) {
      logger.error('Error validating migration:', error);
      return false;
    }
  }

  /**
   * Create backup before migration (development only)
   */
  static async createBackup(): Promise<Record<string, any>> {
    if (__DEV__) {
      try {
        const allKeys = await AsyncStorage.getAllKeys();
        const backup: Record<string, any> = {};
        
        for (const key of allKeys) {
          const value = await AsyncStorage.getItem(key);
          if (value !== null) {
            backup[key] = value;
          }
        }
        
        logger.debug('Backup created with', Object.keys(backup).length, 'keys');
        return backup;
      } catch (error) {
        logger.error('Error creating backup:', error);
        return {};
      }
    }
    
    return {};
  }

  /**
   * Clean up any remaining sensitive data patterns
   */
  static async cleanupSensitiveData(): Promise<void> {
    try {
      const allKeys = await AsyncStorage.getAllKeys();
      
      // Additional patterns to check
      const sensitivePatterns = [
        /password/i,
        /token/i,
        /key/i,
        /secret/i,
        /credential/i,
        /auth/i,
        /session/i,
        /pin/i,
        /cvv/i,
        /ssn/i,
      ];

      const keysToRemove = allKeys.filter(key => {
        // Skip known safe keys
        if (this.SAFE_KEYS.includes(key)) {
          return false;
        }
        
        // Check against sensitive patterns
        return sensitivePatterns.some(pattern => pattern.test(key));
      });

      if (keysToRemove.length > 0) {
        logger.warn(`Removing ${keysToRemove.length} potentially sensitive keys`);
        await AsyncStorage.multiRemove(keysToRemove);
      }
    } catch (error) {
      logger.error('Error cleaning up sensitive data:', error);
    }
  }
}

export default SecureStorageMigration;

// Export types
export type { MigrationResult };