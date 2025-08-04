import AsyncStorage from '@react-native-async-storage/async-storage';

import { logger } from '@/services/logger';
class StorageManager {
  async getItem<T>(key: string): Promise<T | null> {
    try {
      const value = await AsyncStorage.getItem(key);
      return value ? JSON.parse(value) as T : null;
    } catch (error) {
      logger.error(`Failed to get item ${key}:`, error);
      return null;
    }
  }

  async setItem(key: string, value: unknown): Promise<void> {
    try {
      await AsyncStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      logger.error(`Failed to set item ${key}:`, error);
    }
  }

  async removeItem(key: string): Promise<void> {
    try {
      await AsyncStorage.removeItem(key);
    } catch (error) {
      logger.error(`Failed to remove item ${key}:`, error);
    }
  }

  async clear(): Promise<void> {
    try {
      await AsyncStorage.clear();
    } catch (error) {
      logger.error('Failed to clear storage:', error);
    }
  }
}

export default new StorageManager(); 