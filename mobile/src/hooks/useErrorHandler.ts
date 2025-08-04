/**
 * Custom error handling hook with Sentry integration
 * Provides consistent error handling across the app
 */

import { useCallback, useRef } from 'react';
import { Alert } from 'react-native';
import { captureException, trackUserInteraction } from '@/services/sentry/SentryService';
import { logger } from '@/services/logger';
import NetInfo from '@react-native-community/netinfo';

export interface ErrorHandlerOptions {
  showAlert?: boolean;
  fallbackAction?: () => void;
  retryAction?: () => Promise<void>;
  context?: Record<string, any>;
  silent?: boolean;
  level?: 'error' | 'warning' | 'info';
}

export interface ErrorHandler {
  handleError: (error: Error, options?: ErrorHandlerOptions) => void;
  handleAsyncError: <T>(
    fn: () => Promise<T>,
    options?: ErrorHandlerOptions
  ) => Promise<T | undefined>;
  clearError: () => void;
}

export const useErrorHandler = (): ErrorHandler => {
  const retryCountRef = useRef<Map<string, number>>(new Map());

  /**
   * Handle error with Sentry reporting
   */
  const handleError = useCallback((error: Error, options: ErrorHandlerOptions = {}) => {
    const {
      showAlert = true,
      fallbackAction,
      retryAction,
      context = {},
      silent = false,
      level = 'error',
    } = options;

    // Log error
    logger.error('Error handled by useErrorHandler', error, context);

    // Capture in Sentry
    const errorId = captureException(error, {
      level: level as any,
      tags: {
        error_handler: 'hook',
        silent: silent.toString(),
      },
      extra: {
        ...context,
        hasRetryAction: !!retryAction,
        hasFallbackAction: !!fallbackAction,
      },
    });

    // Track error interaction
    trackUserInteraction('error_handled', 'error', {
      error_message: error.message,
      error_id: errorId,
      has_retry: !!retryAction,
      has_fallback: !!fallbackAction,
    });

    // Don't show UI if silent
    if (silent) {
      if (fallbackAction) {
        fallbackAction();
      }
      return;
    }

    // Show alert if enabled
    if (showAlert) {
      showErrorAlert(error, {
        errorId,
        fallbackAction,
        retryAction,
        onRetry: () => handleRetry(error.message, retryAction),
      });
    }
  }, []);

  /**
   * Handle retry logic with exponential backoff
   */
  const handleRetry = useCallback(async (
    errorKey: string,
    retryAction?: () => Promise<void>
  ) => {
    if (!retryAction) return;

    const retryCount = retryCountRef.current.get(errorKey) || 0;
    const maxRetries = 3;
    
    if (retryCount >= maxRetries) {
      Alert.alert(
        'Max Retries Reached',
        'Unable to complete the operation after multiple attempts.',
        [{ text: 'OK' }]
      );
      retryCountRef.current.delete(errorKey);
      return;
    }

    // Check network status
    const netInfo = await NetInfo.fetch();
    if (!netInfo.isConnected) {
      Alert.alert(
        'No Internet Connection',
        'Please check your connection and try again.',
        [{ text: 'OK' }]
      );
      return;
    }

    // Exponential backoff
    const delay = Math.pow(2, retryCount) * 1000;
    setTimeout(async () => {
      try {
        retryCountRef.current.set(errorKey, retryCount + 1);
        await retryAction();
        // Success - clear retry count
        retryCountRef.current.delete(errorKey);
      } catch (retryError) {
        handleError(retryError as Error, {
          context: { 
            originalError: errorKey,
            retryAttempt: retryCount + 1,
          },
        });
      }
    }, delay);
  }, [handleError]);

  /**
   * Show error alert with options
   */
  const showErrorAlert = useCallback((
    error: Error,
    options: {
      errorId?: string;
      fallbackAction?: () => void;
      retryAction?: () => Promise<void>;
      onRetry?: () => void;
    }
  ) => {
    const { errorId, fallbackAction, retryAction, onRetry } = options;
    
    const buttons: any[] = [];

    if (retryAction && onRetry) {
      buttons.push({
        text: 'Retry',
        onPress: onRetry,
      });
    }

    if (fallbackAction) {
      buttons.push({
        text: 'Continue Offline',
        onPress: fallbackAction,
        style: 'default',
      });
    }

    buttons.push({
      text: 'OK',
      style: 'cancel',
    });

    if (__DEV__ && errorId) {
      buttons.push({
        text: 'Copy Error ID',
        onPress: () => {
          // In a real app, you'd copy to clipboard
          Alert.alert('Error ID', errorId);
        },
      });
    }

    Alert.alert(
      'Something went wrong',
      getErrorMessage(error),
      buttons
    );
  }, []);

  /**
   * Handle async operations with error catching
   */
  const handleAsyncError = useCallback(async <T,>(
    fn: () => Promise<T>,
    options: ErrorHandlerOptions = {}
  ): Promise<T | undefined> => {
    try {
      return await fn();
    } catch (error) {
      handleError(error as Error, options);
      return undefined;
    }
  }, [handleError]);

  /**
   * Clear error state
   */
  const clearError = useCallback(() => {
    retryCountRef.current.clear();
  }, []);

  return {
    handleError,
    handleAsyncError,
    clearError,
  };
};

/**
 * Get user-friendly error message
 */
const getErrorMessage = (error: Error): string => {
  // Network errors
  if (error.message.toLowerCase().includes('network')) {
    return 'Unable to connect to the server. Please check your internet connection.';
  }
  
  // Timeout errors
  if (error.message.toLowerCase().includes('timeout')) {
    return 'The request took too long. Please try again.';
  }
  
  // Permission errors
  if (error.message.toLowerCase().includes('permission')) {
    return 'Permission denied. Please check your app settings.';
  }
  
  // API errors
  if ((error as any).response?.status >= 500) {
    return 'Server error. Please try again later.';
  }
  
  if ((error as any).response?.status === 404) {
    return 'The requested resource was not found.';
  }
  
  if ((error as any).response?.status === 403) {
    return 'You do not have permission to perform this action.';
  }
  
  if ((error as any).response?.status === 401) {
    return 'Your session has expired. Please log in again.';
  }
  
  // Default message
  return error.message || 'An unexpected error occurred. Please try again.';
};

/**
 * Global error handler for unhandled promises
 */
export const setupGlobalErrorHandler = () => {
  // Handle unhandled promise rejections
  const originalHandler = global.onunhandledrejection;
  
  global.onunhandledrejection = (event: any) => {
    const error = event.reason || new Error('Unhandled Promise Rejection');
    
    captureException(error, {
      level: 'error',
      tags: {
        error_type: 'unhandled_promise_rejection',
      },
      extra: {
        promise: event.promise,
      },
    });
    
    // Call original handler if exists
    if (originalHandler) {
      originalHandler(event);
    }
  };
};