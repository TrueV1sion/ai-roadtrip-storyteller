/**
 * Comprehensive Sentry Service for React Native
 * Implements crash reporting, performance monitoring, and error tracking
 */

import * as Sentry from 'sentry-expo';
import Constants from 'expo-constants';
import { Platform } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { logger } from '@/services/logger';
export interface SentryConfig {
  dsn: string;
  environment: 'development' | 'staging' | 'production';
  enableInDevelopment?: boolean;
  tracesSampleRate?: number;
  profilesSampleRate?: number;
  debug?: boolean;
  attachStacktrace?: boolean;
  attachScreenshot?: boolean;
  maxBreadcrumbs?: number;
  beforeSend?: (event: Sentry.Native.Event) => Sentry.Native.Event | null;
}

class SentryService {
  private static instance: SentryService;
  private initialized = false;
  private userContext: Sentry.Native.User | null = null;

  private constructor() {}

  static getInstance(): SentryService {
    if (!SentryService.instance) {
      SentryService.instance = new SentryService();
    }
    return SentryService.instance;
  }

  /**
   * Initialize Sentry with comprehensive configuration
   */
  async initialize(config: Partial<SentryConfig> = {}): Promise<void> {
    if (this.initialized) {
      logger.warn('Sentry already initialized');
      return;
    }

    const isDevelopment = __DEV__;
    const environment = this.getEnvironment();
    
    // Get DSN from config or environment
    const dsn = config.dsn || Constants.expoConfig?.extra?.sentry?.dsn;
    
    if (!dsn) {
      logger.warn('Sentry DSN not provided, skipping initialization');
      return;
    }

    // Skip initialization in development unless explicitly enabled
    if (isDevelopment && !config.enableInDevelopment) {
      logger.debug('Sentry disabled in development mode');
      return;
    }

    try {
      Sentry.init({
        dsn,
        environment: config.environment || environment,
        debug: config.debug || isDevelopment,
        tracesSampleRate: config.tracesSampleRate || this.getTracesSampleRate(environment),
        profilesSampleRate: config.profilesSampleRate || 0.1,
        attachStacktrace: config.attachStacktrace !== false,
        attachScreenshot: config.attachScreenshot !== false,
        maxBreadcrumbs: config.maxBreadcrumbs || 100,
        
        // Release tracking
        release: Constants.manifest?.version || '1.0.0',
        dist: Constants.manifest?.ios?.buildNumber || Constants.manifest?.android?.versionCode?.toString() || '1',
        
        // Integration configuration
        integrations: [
          Sentry.nativeScreenIntegration({
            maskAllText: false,
            maskAllImages: false,
          }),
          Sentry.nativeReleaseIntegration(),
          Sentry.breadcrumbsIntegration({
            console: true,
            dom: true,
            fetch: true,
            history: true,
            sentry: true,
            xhr: true,
          }),
        ],
        
        // Before send hook for data sanitization
        beforeSend: config.beforeSend || this.defaultBeforeSend,
        
        // Breadcrumb filtering
        beforeBreadcrumb: this.beforeBreadcrumb,
      });

      // Set initial tags
      this.setDefaultTags();
      
      // Load stored user context
      await this.loadStoredUserContext();
      
      this.initialized = true;
      logger.debug('Sentry initialized successfully');
    } catch (error) {
      logger.error('Failed to initialize Sentry:', error);
    }
  }

  /**
   * Get environment based on expo configuration
   */
  private getEnvironment(): 'development' | 'staging' | 'production' {
    const env = Constants.expoConfig?.extra?.environment;
    if (env === 'staging') return 'staging';
    if (env === 'production') return 'production';
    return 'development';
  }

  /**
   * Get appropriate traces sample rate based on environment
   */
  private getTracesSampleRate(environment: string): number {
    switch (environment) {
      case 'production':
        return 0.1; // 10% in production
      case 'staging':
        return 0.5; // 50% in staging
      default:
        return 1.0; // 100% in development
    }
  }

  /**
   * Default before send hook to sanitize sensitive data
   */
  private defaultBeforeSend = (event: Sentry.Native.Event): Sentry.Native.Event | null => {
    // Remove sensitive data from request
    if (event.request) {
      this.sanitizeRequest(event.request);
    }

    // Remove sensitive data from breadcrumbs
    if (event.breadcrumbs) {
      event.breadcrumbs = event.breadcrumbs.map(breadcrumb => 
        this.sanitizeBreadcrumb(breadcrumb)
      );
    }

    // Remove sensitive data from extra context
    if (event.extra) {
      event.extra = this.sanitizeData(event.extra);
    }

    // Remove sensitive data from contexts
    if (event.contexts) {
      event.contexts = this.sanitizeData(event.contexts);
    }

    return event;
  };

  /**
   * Filter breadcrumbs before they are added
   */
  private beforeBreadcrumb = (breadcrumb: Sentry.Native.Breadcrumb): Sentry.Native.Breadcrumb | null => {
    // Filter out noisy breadcrumbs
    if (breadcrumb.category === 'console' && breadcrumb.level === 'debug') {
      return null;
    }

    // Sanitize breadcrumb data
    return this.sanitizeBreadcrumb(breadcrumb);
  };

  /**
   * Sanitize request data
   */
  private sanitizeRequest(request: any): void {
    const sensitiveHeaders = ['authorization', 'cookie', 'x-api-key', 'x-auth-token'];
    
    if (request.headers) {
      sensitiveHeaders.forEach(header => {
        if (request.headers[header]) {
          request.headers[header] = '[REDACTED]';
        }
      });
    }

    if (request.cookies) {
      request.cookies = '[REDACTED]';
    }
  }

  /**
   * Sanitize breadcrumb data
   */
  private sanitizeBreadcrumb(breadcrumb: Sentry.Native.Breadcrumb): Sentry.Native.Breadcrumb {
    if (breadcrumb.data) {
      breadcrumb.data = this.sanitizeData(breadcrumb.data);
    }
    return breadcrumb;
  }

  /**
   * Recursively sanitize sensitive data
   */
  private sanitizeData(data: any): any {
    if (!data || typeof data !== 'object') return data;

    const sensitiveKeys = [
      'password', 'token', 'secret', 'apiKey', 'api_key',
      'authToken', 'auth_token', 'creditCard', 'credit_card',
      'ssn', 'socialSecurity', 'private', 'privateKey'
    ];

    const sanitized = Array.isArray(data) ? [...data] : { ...data };

    Object.keys(sanitized).forEach(key => {
      const lowerKey = key.toLowerCase();
      
      if (sensitiveKeys.some(sensitive => lowerKey.includes(sensitive.toLowerCase()))) {
        sanitized[key] = '[REDACTED]';
      } else if (typeof sanitized[key] === 'object') {
        sanitized[key] = this.sanitizeData(sanitized[key]);
      }
    });

    return sanitized;
  }

  /**
   * Set default tags for all events
   */
  private setDefaultTags(): void {
    Sentry.Native.setTags({
      platform: Platform.OS,
      platform_version: Platform.Version.toString(),
      expo_version: Constants.expoConfig?.version || 'unknown',
      app_version: Constants.manifest?.version || 'unknown',
      device_type: this.getDeviceType(),
    });
  }

  /**
   * Get device type
   */
  private getDeviceType(): string {
    const { isDevice } = Constants;
    if (!isDevice) return 'simulator';
    
    return Platform.select({
      ios: 'ios_device',
      android: 'android_device',
      default: 'unknown',
    }) || 'unknown';
  }

  /**
   * Load stored user context from AsyncStorage
   */
  private async loadStoredUserContext(): Promise<void> {
    try {
      const storedUser = await AsyncStorage.getItem('@sentry_user_context');
      if (storedUser) {
        const user = JSON.parse(storedUser);
        this.setUserContext(user);
      }
    } catch (error) {
      logger.error('Failed to load stored user context:', error);
    }
  }

  /**
   * Set user context for error tracking
   */
  async setUserContext(user: Sentry.Native.User): Promise<void> {
    if (!this.initialized) return;

    // Sanitize user data
    const sanitizedUser: Sentry.Native.User = {
      id: user.id,
      username: user.username,
      email: user.email,
      // Don't include sensitive data
    };

    this.userContext = sanitizedUser;
    Sentry.Native.setUser(sanitizedUser);

    // Store user context for persistence
    try {
      await AsyncStorage.setItem('@sentry_user_context', JSON.stringify(sanitizedUser));
    } catch (error) {
      logger.error('Failed to store user context:', error);
    }
  }

  /**
   * Clear user context (e.g., on logout)
   */
  async clearUserContext(): Promise<void> {
    if (!this.initialized) return;

    this.userContext = null;
    Sentry.Native.setUser(null);

    try {
      await AsyncStorage.removeItem('@sentry_user_context');
    } catch (error) {
      logger.error('Failed to clear user context:', error);
    }
  }

  /**
   * Capture exception with additional context
   */
  captureException(
    error: Error,
    context?: {
      level?: Sentry.Native.SeverityLevel;
      tags?: { [key: string]: string };
      extra?: { [key: string]: any };
      user?: Sentry.Native.User;
      fingerprint?: string[];
    }
  ): string | undefined {
    if (!this.initialized) {
      logger.error('Sentry not initialized, logging error:', error);
      return undefined;
    }

    const scope = new Sentry.Native.Scope();

    if (context) {
      if (context.level) {
        scope.setLevel(context.level);
      }
      if (context.tags) {
        Object.entries(context.tags).forEach(([key, value]) => {
          scope.setTag(key, value);
        });
      }
      if (context.extra) {
        Object.entries(context.extra).forEach(([key, value]) => {
          scope.setExtra(key, value);
        });
      }
      if (context.user) {
        scope.setUser(context.user);
      }
      if (context.fingerprint) {
        scope.setFingerprint(context.fingerprint);
      }
    }

    return Sentry.Native.captureException(error, scope);
  }

  /**
   * Capture message
   */
  captureMessage(
    message: string,
    level: Sentry.Native.SeverityLevel = 'info',
    context?: {
      tags?: { [key: string]: string };
      extra?: { [key: string]: any };
    }
  ): string | undefined {
    if (!this.initialized) {
      logger.debug(`[${level}] ${message}`);
      return undefined;
    }

    const scope = new Sentry.Native.Scope();
    scope.setLevel(level);

    if (context) {
      if (context.tags) {
        Object.entries(context.tags).forEach(([key, value]) => {
          scope.setTag(key, value);
        });
      }
      if (context.extra) {
        Object.entries(context.extra).forEach(([key, value]) => {
          scope.setExtra(key, value);
        });
      }
    }

    return Sentry.Native.captureMessage(message, scope);
  }

  /**
   * Add breadcrumb
   */
  addBreadcrumb(breadcrumb: Sentry.Native.Breadcrumb): void {
    if (!this.initialized) return;
    Sentry.Native.addBreadcrumb(breadcrumb);
  }

  /**
   * Set tag
   */
  setTag(key: string, value: string): void {
    if (!this.initialized) return;
    Sentry.Native.setTag(key, value);
  }

  /**
   * Set multiple tags
   */
  setTags(tags: { [key: string]: string }): void {
    if (!this.initialized) return;
    Sentry.Native.setTags(tags);
  }

  /**
   * Set extra context
   */
  setExtra(key: string, extra: any): void {
    if (!this.initialized) return;
    Sentry.Native.setExtra(key, this.sanitizeData(extra));
  }

  /**
   * Set multiple extras
   */
  setExtras(extras: { [key: string]: any }): void {
    if (!this.initialized) return;
    Sentry.Native.setExtras(this.sanitizeData(extras));
  }

  /**
   * Set context
   */
  setContext(key: string, context: any): void {
    if (!this.initialized) return;
    Sentry.Native.setContext(key, this.sanitizeData(context));
  }

  /**
   * Start a transaction for performance monitoring
   */
  startTransaction(
    name: string,
    operation: string,
    description?: string
  ): Sentry.Native.Transaction | undefined {
    if (!this.initialized) return undefined;

    return Sentry.Native.startTransaction({
      name,
      op: operation,
      description,
    });
  }

  /**
   * Track user interaction
   */
  trackUserInteraction(
    name: string,
    operation: string,
    data?: { [key: string]: any }
  ): void {
    if (!this.initialized) return;

    this.addBreadcrumb({
      message: `User interaction: ${name}`,
      category: 'user',
      type: 'user',
      level: 'info',
      data: {
        operation,
        ...data,
      },
    });
  }

  /**
   * Track navigation
   */
  trackNavigation(from: string, to: string, params?: any): void {
    if (!this.initialized) return;

    this.addBreadcrumb({
      message: `Navigation: ${from} -> ${to}`,
      category: 'navigation',
      type: 'navigation',
      level: 'info',
      data: {
        from,
        to,
        params: this.sanitizeData(params),
      },
    });
  }

  /**
   * Track API call
   */
  trackApiCall(
    method: string,
    url: string,
    status?: number,
    duration?: number
  ): void {
    if (!this.initialized) return;

    this.addBreadcrumb({
      message: `API Call: ${method} ${url}`,
      category: 'fetch',
      type: 'http',
      level: status && status >= 400 ? 'error' : 'info',
      data: {
        method,
        url,
        status_code: status,
        duration,
      },
    });
  }

  /**
   * Wrap async function with error tracking
   */
  async withErrorTracking<T>(
    fn: () => Promise<T>,
    context?: {
      operation: string;
      description?: string;
      tags?: { [key: string]: string };
    }
  ): Promise<T> {
    const transaction = context?.operation
      ? this.startTransaction(context.operation, 'function', context.description)
      : undefined;

    try {
      if (context?.tags && transaction) {
        Object.entries(context.tags).forEach(([key, value]) => {
          transaction.setTag(key, value);
        });
      }

      const result = await fn();
      transaction?.finish();
      return result;
    } catch (error) {
      transaction?.setStatus('internal_error');
      transaction?.finish();
      
      this.captureException(error as Error, {
        tags: context?.tags,
        extra: {
          operation: context?.operation,
          description: context?.description,
        },
      });
      
      throw error;
    }
  }

  /**
   * Check if Sentry is initialized
   */
  isInitialized(): boolean {
    return this.initialized;
  }
}

export const sentryService = SentryService.getInstance();

// Export convenience functions
export const initializeSentry = (config?: Partial<SentryConfig>) => 
  sentryService.initialize(config);

export const captureException = (error: Error, context?: any) => 
  sentryService.captureException(error, context);

export const captureMessage = (message: string, level?: Sentry.Native.SeverityLevel, context?: any) => 
  sentryService.captureMessage(message, level, context);

export const setUserContext = (user: Sentry.Native.User) => 
  sentryService.setUserContext(user);

export const trackUserInteraction = (name: string, operation: string, data?: any) => 
  sentryService.trackUserInteraction(name, operation, data);

export const trackNavigation = (from: string, to: string, params?: any) => 
  sentryService.trackNavigation(from, to, params);

export const withErrorTracking = <T>(fn: () => Promise<T>, context?: any) => 
  sentryService.withErrorTracking(fn, context);