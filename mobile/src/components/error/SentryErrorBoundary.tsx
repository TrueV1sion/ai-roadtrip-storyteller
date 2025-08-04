/**
 * Enhanced Error Boundary with Sentry Integration
 * Provides comprehensive error catching and reporting
 */

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { logger } from '@/services/logger';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Alert,
  Platform,
  Dimensions,
  Image,
} from 'react-native';
import { sentryService } from '@/services/sentry/SentryService';
import AsyncStorage from '@react-native-async-storage/async-storage';
import NetInfo from '@react-native-community/netinfo';

const { width, height } = Dimensions.get('window');

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  showDialog?: boolean;
  enableAutoRecovery?: boolean;
  maxRetries?: number;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  errorCount: number;
  isRecovering: boolean;
  isOnline: boolean;
  errorId: string | null;
}

interface ErrorReport {
  id: string;
  error: {
    message: string;
    stack?: string;
  };
  errorInfo: {
    componentStack: string;
  };
  timestamp: string;
  deviceInfo: {
    platform: string;
    version: string | number;
  };
  appState: {
    isOnline: boolean;
    errorCount: number;
  };
}

export class SentryErrorBoundary extends Component<Props, State> {
  private resetTimeoutId: NodeJS.Timeout | null = null;
  private unsubscribeNetInfo: (() => void) | null = null;
  private readonly maxRetries: number;

  constructor(props: Props) {
    super(props);
    this.maxRetries = props.maxRetries || 3;
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorCount: 0,
      isRecovering: false,
      isOnline: true,
      errorId: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  async componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    const { errorCount } = this.state;
    const newErrorCount = errorCount + 1;

    // Generate error ID for tracking
    const errorId = this.generateErrorId();

    this.setState({
      errorInfo,
      errorCount: newErrorCount,
      errorId,
    });

    // Create comprehensive error report
    const errorReport = await this.createErrorReport(error, errorInfo, errorId);

    // Send to Sentry with enhanced context
    sentryService.captureException(error, {
      level: 'error',
      tags: {
        error_boundary: 'true',
        error_count: newErrorCount.toString(),
        error_id: errorId,
        component_stack: this.extractComponentName(errorInfo.componentStack),
      },
      extra: {
        componentStack: errorInfo.componentStack,
        errorBoundary: true,
        errorCount: newErrorCount,
        errorReport,
      },
      fingerprint: [
        'error-boundary',
        error.name,
        this.extractComponentName(errorInfo.componentStack),
      ],
    });

    // Store error report locally
    await this.storeErrorReport(errorReport);

    // Track error occurrence
    sentryService.trackUserInteraction('error_boundary_triggered', 'error', {
      error_message: error.message,
      error_count: newErrorCount,
    });

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // Auto-recovery logic
    if (this.props.enableAutoRecovery && newErrorCount >= this.maxRetries) {
      this.scheduleAutoRecovery();
    }
  }

  componentDidMount() {
    // Monitor network status
    this.unsubscribeNetInfo = NetInfo.addEventListener(state => {
      this.setState({ isOnline: state.isConnected || false });
    });

    // Set up global error handler
    this.setupGlobalErrorHandler();
  }

  componentWillUnmount() {
    if (this.resetTimeoutId) {
      clearTimeout(this.resetTimeoutId);
    }
    if (this.unsubscribeNetInfo) {
      this.unsubscribeNetInfo();
    }
  }

  /**
   * Set up global error handler for unhandled promise rejections
   */
  private setupGlobalErrorHandler = () => {
    const originalHandler = global.ErrorUtils?.getGlobalHandler();
    
    global.ErrorUtils?.setGlobalHandler((error: Error, isFatal?: boolean) => {
      if (isFatal) {
        sentryService.captureException(error, {
          level: 'fatal',
          tags: {
            global_handler: 'true',
            fatal: 'true',
          },
        });
      }
      
      // Call original handler
      if (originalHandler) {
        originalHandler(error, isFatal);
      }
    });
  };

  /**
   * Generate unique error ID
   */
  private generateErrorId = (): string => {
    return `err_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  };

  /**
   * Extract component name from stack
   */
  private extractComponentName = (componentStack: string): string => {
    const match = componentStack.match(/in (\w+)/);
    return match ? match[1] : 'Unknown';
  };

  /**
   * Create comprehensive error report
   */
  private createErrorReport = async (
    error: Error,
    errorInfo: ErrorInfo,
    errorId: string
  ): Promise<ErrorReport> => {
    const netInfo = await NetInfo.fetch();
    
    return {
      id: errorId,
      error: {
        message: error.message,
        stack: error.stack,
      },
      errorInfo: {
        componentStack: errorInfo.componentStack,
      },
      timestamp: new Date().toISOString(),
      deviceInfo: {
        platform: Platform.OS,
        version: Platform.Version,
      },
      appState: {
        isOnline: netInfo.isConnected || false,
        errorCount: this.state.errorCount + 1,
      },
    };
  };

  /**
   * Store error report locally
   */
  private storeErrorReport = async (report: ErrorReport): Promise<void> => {
    try {
      const key = '@error_reports';
      const existingReports = await AsyncStorage.getItem(key);
      const reports = existingReports ? JSON.parse(existingReports) : [];
      
      reports.unshift(report);
      
      // Keep only last 10 reports
      if (reports.length > 10) {
        reports.length = 10;
      }
      
      await AsyncStorage.setItem(key, JSON.stringify(reports));
    } catch (error) {
      logger.error('Failed to store error report:', error);
    }
  };

  /**
   * Schedule automatic recovery
   */
  private scheduleAutoRecovery = (): void => {
    if (this.resetTimeoutId) {
      clearTimeout(this.resetTimeoutId);
    }

    this.resetTimeoutId = setTimeout(() => {
      if (this.props.showDialog) {
        Alert.alert(
          'Multiple Errors Detected',
          'The app has encountered multiple errors and needs to restart.',
          [
            {
              text: 'Restart Now',
              onPress: this.handleReset,
            },
            {
              text: 'Report & Restart',
              onPress: this.handleReportAndReset,
            },
          ],
          { cancelable: false }
        );
      } else {
        this.handleReset();
      }
    }, 2000);
  };

  /**
   * Handle error reset
   */
  private handleReset = (): void => {
    sentryService.trackUserInteraction('error_boundary_reset', 'recovery', {
      error_count: this.state.errorCount,
      error_id: this.state.errorId,
    });

    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorCount: 0,
      isRecovering: false,
      errorId: null,
    });

    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  /**
   * Handle report and reset
   */
  private handleReportAndReset = async (): Promise<void> => {
    this.setState({ isRecovering: true });

    try {
      // Send detailed error report
      if (this.state.error && this.state.errorId) {
        sentryService.captureMessage(
          `User reported error: ${this.state.error.message}`,
          'error',
          {
            tags: {
              user_reported: 'true',
              error_id: this.state.errorId,
            },
            extra: {
              errorStack: this.state.error.stack,
              componentStack: this.state.errorInfo?.componentStack,
            },
          }
        );
      }

      Alert.alert(
        'Thank You',
        'The error has been reported. The app will now restart.',
        [{ text: 'OK', onPress: this.handleReset }]
      );
    } catch (error) {
      logger.error('Failed to report error:', error);
      this.handleReset();
    }
  };

  /**
   * Handle send feedback
   */
  private handleSendFeedback = (): void => {
    const { error, errorId } = this.state;
    
    Alert.prompt(
      'Send Feedback',
      'Please describe what you were doing when the error occurred:',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Send',
          onPress: (feedback?: string) => {
            if (feedback && error) {
              sentryService.captureMessage(
                `User feedback for error: ${feedback}`,
                'info',
                {
                  tags: {
                    error_feedback: 'true',
                    error_id: errorId || 'unknown',
                  },
                  extra: {
                    original_error: error.message,
                    user_feedback: feedback,
                  },
                }
              );
              
              Alert.alert('Thank You', 'Your feedback has been sent.');
            }
          },
        },
      ],
      'plain-text'
    );
  };

  render() {
    const { hasError, error, errorInfo, errorCount, isRecovering, isOnline, errorId } = this.state;
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
            showsVerticalScrollIndicator={false}
          >
            <View style={styles.errorContainer}>
              <View style={styles.iconContainer}>
                <Text style={styles.errorIcon}>⚠️</Text>
              </View>

              <Text style={styles.errorTitle}>Oops! Something went wrong</Text>
              
              <Text style={styles.errorMessage}>
                We're sorry for the inconvenience. The app encountered an unexpected error.
              </Text>

              {!isOnline && (
                <View style={styles.offlineNotice}>
                  <Text style={styles.offlineText}>
                    📡 You appear to be offline. Some features may not work properly.
                  </Text>
                </View>
              )}

              {__DEV__ && (
                <View style={styles.debugInfo}>
                  <Text style={styles.debugTitle}>Debug Information:</Text>
                  <Text style={styles.debugText}>
                    Error ID: {errorId}
                  </Text>
                  <Text style={styles.debugText}>
                    {error.name}: {error.message}
                  </Text>
                  <ScrollView style={styles.stackScrollView}>
                    <Text style={styles.debugStack} numberOfLines={20}>
                      {error.stack}
                    </Text>
                  </ScrollView>
                  {errorInfo && (
                    <ScrollView style={styles.stackScrollView}>
                      <Text style={styles.debugStack} numberOfLines={20}>
                        Component Stack: {errorInfo.componentStack}
                      </Text>
                    </ScrollView>
                  )}
                </View>
              )}

              <View style={styles.actionContainer}>
                <TouchableOpacity
                  style={[styles.primaryButton, isRecovering && styles.disabledButton]}
                  onPress={this.handleReset}
                  disabled={isRecovering}
                >
                  <Text style={styles.primaryButtonText}>
                    {isRecovering ? 'Restarting...' : 'Try Again'}
                  </Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.secondaryButton}
                  onPress={this.handleReportAndReset}
                  disabled={isRecovering}
                >
                  <Text style={styles.secondaryButtonText}>Report & Restart</Text>
                </TouchableOpacity>

                {__DEV__ && (
                  <TouchableOpacity
                    style={styles.feedbackButton}
                    onPress={this.handleSendFeedback}
                    disabled={isRecovering}
                  >
                    <Text style={styles.feedbackButtonText}>Send Feedback</Text>
                  </TouchableOpacity>
                )}
              </View>

              {errorCount > 1 && (
                <Text style={styles.errorCount}>
                  This error has occurred {errorCount} times
                </Text>
              )}

              <Text style={styles.errorId}>Error ID: {errorId}</Text>
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
    backgroundColor: '#f8f9fa',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    paddingVertical: 40,
  },
  errorContainer: {
    paddingHorizontal: 24,
    alignItems: 'center',
    maxWidth: 400,
    alignSelf: 'center',
    width: '100%',
  },
  iconContainer: {
    marginBottom: 24,
  },
  errorIcon: {
    fontSize: 64,
  },
  errorTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#dc3545',
    marginBottom: 16,
    textAlign: 'center',
  },
  errorMessage: {
    fontSize: 16,
    color: '#495057',
    textAlign: 'center',
    marginBottom: 32,
    lineHeight: 24,
  },
  offlineNotice: {
    backgroundColor: '#fff3cd',
    borderColor: '#ffeaa7',
    borderWidth: 1,
    borderRadius: 8,
    padding: 12,
    marginBottom: 24,
    width: '100%',
  },
  offlineText: {
    color: '#856404',
    fontSize: 14,
    textAlign: 'center',
  },
  debugInfo: {
    backgroundColor: '#f8f9fa',
    borderColor: '#dee2e6',
    borderWidth: 1,
    borderRadius: 8,
    padding: 16,
    marginBottom: 24,
    width: '100%',
  },
  debugTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#495057',
    marginBottom: 8,
  },
  debugText: {
    fontSize: 12,
    color: '#6c757d',
    marginBottom: 8,
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
  },
  stackScrollView: {
    maxHeight: 150,
    marginBottom: 8,
  },
  debugStack: {
    fontSize: 11,
    color: '#6c757d',
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    lineHeight: 16,
  },
  actionContainer: {
    width: '100%',
    maxWidth: 320,
  },
  primaryButton: {
    backgroundColor: '#007bff',
    paddingVertical: 16,
    paddingHorizontal: 24,
    borderRadius: 8,
    marginBottom: 12,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  primaryButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    textAlign: 'center',
  },
  secondaryButton: {
    backgroundColor: '#fff',
    paddingVertical: 16,
    paddingHorizontal: 24,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#007bff',
    marginBottom: 12,
  },
  secondaryButtonText: {
    color: '#007bff',
    fontSize: 16,
    fontWeight: '500',
    textAlign: 'center',
  },
  feedbackButton: {
    paddingVertical: 12,
    paddingHorizontal: 16,
  },
  feedbackButtonText: {
    color: '#6c757d',
    fontSize: 14,
    textAlign: 'center',
    textDecorationLine: 'underline',
  },
  disabledButton: {
    opacity: 0.6,
  },
  errorCount: {
    fontSize: 12,
    color: '#6c757d',
    marginTop: 16,
    textAlign: 'center',
  },
  errorId: {
    fontSize: 11,
    color: '#adb5bd',
    marginTop: 8,
    textAlign: 'center',
  },
});

// Create a higher-order component for easy wrapping
export function withSentryErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  errorBoundaryProps?: Partial<Props>
): React.ComponentType<P> {
  return (props: P) => (
    <SentryErrorBoundary {...errorBoundaryProps}>
      <Component {...props} />
    </SentryErrorBoundary>
  );
}

export default SentryErrorBoundary;