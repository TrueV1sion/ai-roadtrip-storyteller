/**
 * Production-ready Error Boundary component
 * Catches JavaScript errors anywhere in the component tree
 */

import React, { Component, ErrorInfo, ReactNode } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Alert,
} from 'react-native';
import { logger } from '@/services/logger';
import { ENV } from '@/config/env.production';
import AsyncStorage from '@react-native-async-storage/async-storage';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  errorCount: number;
}

class ErrorBoundary extends Component<Props, State> {
  private resetTimeoutId: NodeJS.Timeout | null = null;

  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorCount: 0,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  async componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log to console in development
    if (__DEV__) {
      logger.error('ErrorBoundary caught an error:', error, errorInfo);
    }

    // Update error count
    const errorCount = this.state.errorCount + 1;
    this.setState({ errorInfo, errorCount });

    // Log to monitoring service
    logger.error('Component Error Boundary triggered', error, {
      componentStack: errorInfo.componentStack,
      errorBoundary: true,
      errorCount,
    });

    // Store error details for crash reporting
    await this.storeErrorDetails(error, errorInfo);

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // Auto-recover after multiple errors (prevent infinite error loop)
    if (errorCount >= 3) {
      this.scheduleReset();
    }
  }

  async storeErrorDetails(error: Error, errorInfo: ErrorInfo) {
    try {
      const errorDetails = {
        message: error.message,
        stack: error.stack,
        componentStack: errorInfo.componentStack,
        timestamp: new Date().toISOString(),
      };

      // Store last error for debugging
      await AsyncStorage.setItem(
        '@last_error',
        JSON.stringify(errorDetails)
      );

      // Store error history (keep last 10 errors)
      const historyKey = '@error_history';
      const existingHistory = await AsyncStorage.getItem(historyKey);
      const history = existingHistory ? JSON.parse(existingHistory) : [];
      
      history.unshift(errorDetails);
      if (history.length > 10) {
        history.pop();
      }

      await AsyncStorage.setItem(historyKey, JSON.stringify(history));
    } catch (storageError) {
      logger.error('Failed to store error details', storageError as Error);
    }
  }

  scheduleReset = () => {
    if (this.resetTimeoutId) {
      clearTimeout(this.resetTimeoutId);
    }

    this.resetTimeoutId = setTimeout(() => {
      Alert.alert(
        'Multiple Errors Detected',
        'The app has encountered multiple errors. Would you like to restart?',
        [
          {
            text: 'Cancel',
            style: 'cancel',
          },
          {
            text: 'Restart',
            onPress: this.handleReset,
          },
        ]
      );
    }, 2000);
  };

  componentWillUnmount() {
    if (this.resetTimeoutId) {
      clearTimeout(this.resetTimeoutId);
    }
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorCount: 0,
    });
  };

  handleReportError = async () => {
    const { error, errorInfo } = this.state;
    
    if (!error) return;

    try {
      // In production, this would send to your error reporting endpoint
      logger.error('User reported error', error, {
        userReported: true,
        componentStack: errorInfo?.componentStack,
      });

      Alert.alert(
        'Thank You',
        'The error has been reported to our team. We apologize for the inconvenience.',
        [{ text: 'OK' }]
      );
    } catch (reportError) {
      Alert.alert(
        'Report Failed',
        'Unable to send error report. Please try again later.',
        [{ text: 'OK' }]
      );
    }
  };

  render() {
    const { hasError, error, errorInfo, errorCount } = this.state;
    const { children, fallback } = this.props;

    if (hasError && error) {
      // Use custom fallback if provided
      if (fallback) {
        return <>{fallback}</>;
      }

      // Default error UI
      return (
        <View style={styles.container}>
          <ScrollView 
            style={styles.scrollView}
            contentContainerStyle={styles.scrollContent}
          >
            <View style={styles.errorContainer}>
              <Text style={styles.errorTitle}>Oops! Something went wrong</Text>
              
              <Text style={styles.errorMessage}>
                We apologize for the inconvenience. The app encountered an unexpected error.
              </Text>

              {__DEV__ && (
                <View style={styles.debugInfo}>
                  <Text style={styles.debugTitle}>Debug Information:</Text>
                  <Text style={styles.debugText}>
                    {error.name}: {error.message}
                  </Text>
                  <Text style={styles.debugStack} numberOfLines={10}>
                    {error.stack}
                  </Text>
                  {errorInfo && (
                    <Text style={styles.debugStack} numberOfLines={10}>
                      Component Stack: {errorInfo.componentStack}
                    </Text>
                  )}
                </View>
              )}

              <View style={styles.actionContainer}>
                <TouchableOpacity
                  style={styles.primaryButton}
                  onPress={this.handleReset}
                >
                  <Text style={styles.primaryButtonText}>Try Again</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.secondaryButton}
                  onPress={this.handleReportError}
                >
                  <Text style={styles.secondaryButtonText}>Report Error</Text>
                </TouchableOpacity>
              </View>

              {errorCount > 1 && (
                <Text style={styles.errorCount}>
                  Error occurred {errorCount} times
                </Text>
              )}
            </View>
          </ScrollView>
        </View>
      );
    }

    return children;
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
  },
  errorContainer: {
    padding: 20,
    alignItems: 'center',
  },
  errorTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#e74c3c',
    marginBottom: 16,
    textAlign: 'center',
  },
  errorMessage: {
    fontSize: 16,
    color: '#333',
    textAlign: 'center',
    marginBottom: 24,
    lineHeight: 24,
  },
  debugInfo: {
    backgroundColor: '#f9f9f9',
    padding: 16,
    borderRadius: 8,
    marginBottom: 24,
    width: '100%',
  },
  debugTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#666',
    marginBottom: 8,
  },
  debugText: {
    fontSize: 12,
    color: '#666',
    marginBottom: 8,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  debugStack: {
    fontSize: 10,
    color: '#666',
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  actionContainer: {
    width: '100%',
    maxWidth: 300,
  },
  primaryButton: {
    backgroundColor: '#3498db',
    paddingVertical: 14,
    paddingHorizontal: 32,
    borderRadius: 8,
    marginBottom: 12,
  },
  primaryButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  secondaryButton: {
    backgroundColor: 'transparent',
    paddingVertical: 14,
    paddingHorizontal: 32,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#3498db',
  },
  secondaryButtonText: {
    color: '#3498db',
    fontSize: 16,
    textAlign: 'center',
  },
  errorCount: {
    fontSize: 12,
    color: '#999',
    marginTop: 16,
  },
});

// Create a higher-order component for easy wrapping
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  fallback?: ReactNode,
  onError?: (error: Error, errorInfo: ErrorInfo) => void
): React.ComponentType<P> {
  return (props: P) => (
    <ErrorBoundary fallback={fallback} onError={onError}>
      <Component {...props} />
    </ErrorBoundary>
  );
}

export default ErrorBoundary;