import { Alert } from 'react-native';
import NetInfo from '@react-native-community/netinfo';

interface ErrorConfig {
  title: string;
  message: string;
  retry?: () => Promise<void>;
  fallback?: () => void;
}

class ErrorHandler {
  private static instance: ErrorHandler;
  private retryAttempts: Map<string, number> = new Map();
  private readonly MAX_RETRIES = 3;
  private readonly RETRY_DELAY = 1000; // ms

  private constructor() {}

  static getInstance(): ErrorHandler {
    if (!ErrorHandler.instance) {
      ErrorHandler.instance = new ErrorHandler();
    }
    return ErrorHandler.instance;
  }

  async handleError(error: any, config: ErrorConfig): Promise<void> {
    console.error('Error occurred:', error);

    // Check network connectivity
    const netInfo = await NetInfo.fetch();
    if (!netInfo.isConnected) {
      this.showOfflineError(config);
      return;
    }

    // Handle specific error types
    if (error.name === 'ApiError') {
      this.handleApiError(error, config);
    } else if (error.name === 'TimeoutError') {
      this.handleTimeoutError(error, config);
    } else if (error.name === 'StorageError') {
      this.handleStorageError(error, config);
    } else {
      this.handleGenericError(error, config);
    }
  }

  private showOfflineError(config: ErrorConfig): void {
    Alert.alert(
      'No Internet Connection',
      'Please check your connection and try again.',
      [
        {
          text: 'Try Again',
          onPress: async () => {
            if (config.retry) {
              const netInfo = await NetInfo.fetch();
              if (netInfo.isConnected) {
                await config.retry();
              } else {
                this.showOfflineError(config);
              }
            }
          },
        },
        config.fallback
          ? { text: 'Use Offline Mode', onPress: config.fallback }
          : { text: 'OK', style: 'cancel' },
      ]
    );
  }

  private async handleApiError(error: any, config: ErrorConfig): Promise<void> {
    const errorKey = `${error.endpoint}_${error.code}`;
    const attempts = this.retryAttempts.get(errorKey) || 0;

    if (error.code === 429) { // Rate limit
      this.showRateLimitError(config);
    } else if (error.code >= 500) { // Server error
      if (attempts < this.MAX_RETRIES) {
        this.retryAttempts.set(errorKey, attempts + 1);
        await this.retryWithDelay(config);
      } else {
        this.showServerError(config);
      }
    } else {
      Alert.alert(
        config.title,
        error.message || config.message,
        this.getActionButtons(config)
      );
    }
  }

  private handleTimeoutError(error: any, config: ErrorConfig): void {
    Alert.alert(
      'Request Timeout',
      'The operation is taking longer than expected. Please try again.',
      this.getActionButtons(config)
    );
  }

  private handleStorageError(error: any, config: ErrorConfig): void {
    Alert.alert(
      'Storage Error',
      'Unable to access local storage. Please ensure you have enough space.',
      this.getActionButtons(config)
    );
  }

  private handleGenericError(error: any, config: ErrorConfig): void {
    Alert.alert(
      config.title,
      config.message,
      this.getActionButtons(config)
    );
  }

  private showRateLimitError(config: ErrorConfig): void {
    Alert.alert(
      'Too Many Requests',
      'Please wait a moment before trying again.',
      [
        {
          text: 'OK',
          style: 'cancel',
        },
      ]
    );
  }

  private showServerError(config: ErrorConfig): void {
    Alert.alert(
      'Server Error',
      'We're experiencing technical difficulties. Please try again later.',
      this.getActionButtons(config)
    );
  }

  private getActionButtons(config: ErrorConfig): Array<{
    text: string;
    onPress?: () => void;
    style?: 'default' | 'cancel' | 'destructive';
  }> {
    const buttons = [];

    if (config.retry) {
      buttons.push({
        text: 'Try Again',
        onPress: config.retry,
      });
    }

    if (config.fallback) {
      buttons.push({
        text: 'Use Offline Mode',
        onPress: config.fallback,
      });
    }

    buttons.push({
      text: 'OK',
      style: 'cancel',
    });

    return buttons;
  }

  private async retryWithDelay(config: ErrorConfig): Promise<void> {
    if (!config.retry) return;

    await new Promise(resolve => setTimeout(resolve, this.RETRY_DELAY));
    await config.retry();
  }

  // Custom error classes
  createApiError(message: string, code: number, endpoint: string): Error {
    const error = new Error(message);
    error.name = 'ApiError';
    (error as any).code = code;
    (error as any).endpoint = endpoint;
    return error;
  }

  createTimeoutError(message: string): Error {
    const error = new Error(message);
    error.name = 'TimeoutError';
    return error;
  }

  createStorageError(message: string): Error {
    const error = new Error(message);
    error.name = 'StorageError';
    return error;
  }
}

export default ErrorHandler.getInstance(); 