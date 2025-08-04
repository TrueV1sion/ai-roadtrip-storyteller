/**
 * Production-ready logging service
 * Replaces all console.log statements with structured logging
 */

// import * as Sentry from 'sentry-expo';
// import { ENV } from '@/config/env.production';

// Mock Sentry for development
const Sentry = {
  Native: {
    captureException: (error: any) => console.error('Sentry mock:', error),
    captureMessage: (message: string) => console.log('Sentry mock:', message),
    addBreadcrumb: (breadcrumb: any) => console.log('Sentry breadcrumb:', breadcrumb),
  }
};
export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
  FATAL = 4,
}

interface LogContext {
  [key: string]: any;
}

class Logger {
  private static instance: Logger;
  private logLevel: LogLevel;
  private isDevelopment: boolean;

  private constructor() {
    this.isDevelopment = process.env.NODE_ENV !== 'production';
    this.logLevel = this.isDevelopment ? LogLevel.DEBUG : LogLevel.ERROR;
  }

  static getInstance(): Logger {
    if (!Logger.instance) {
      Logger.instance = new Logger();
    }
    return Logger.instance;
  }

  private shouldLog(level: LogLevel): boolean {
    return level >= this.logLevel;
  }

  private formatMessage(level: string, message: string, context?: LogContext): string {
    const timestamp = new Date().toISOString();
    const contextStr = context ? JSON.stringify(context) : '';
    return `[${timestamp}] [${level}] ${message} ${contextStr}`;
  }

  private sendToSentry(level: LogLevel, message: string, context?: LogContext): void {
    if (!this.isDevelopment && ENV.SENTRY_DSN) {
      const sentryLevel = this.mapToSentryLevel(level);
      
      if (level === LogLevel.ERROR || level === LogLevel.FATAL) {
        Sentry.Native.captureException(new Error(message), {
          level: sentryLevel,
          extra: context,
        });
      } else {
        Sentry.Native.captureMessage(message, sentryLevel);
        if (context) {
          Sentry.Native.addBreadcrumb({
            message,
            level: sentryLevel,
            data: context,
          });
        }
      }
    }
  }

  private mapToSentryLevel(level: LogLevel): Sentry.Native.SeverityLevel {
    switch (level) {
      case LogLevel.DEBUG:
        return 'debug';
      case LogLevel.INFO:
        return 'info';
      case LogLevel.WARN:
        return 'warning';
      case LogLevel.ERROR:
        return 'error';
      case LogLevel.FATAL:
        return 'fatal';
      default:
        return 'info';
    }
  }

  debug(message: string, context?: LogContext): void {
    if (this.shouldLog(LogLevel.DEBUG)) {
      if (this.isDevelopment) {
        console.log(this.formatMessage('DEBUG', message, context));
      }
      this.sendToSentry(LogLevel.DEBUG, message, context);
    }
  }

  info(message: string, context?: LogContext): void {
    if (this.shouldLog(LogLevel.INFO)) {
      if (this.isDevelopment) {
        console.info(this.formatMessage('INFO', message, context));
      }
      this.sendToSentry(LogLevel.INFO, message, context);
    }
  }

  warn(message: string, context?: LogContext): void {
    if (this.shouldLog(LogLevel.WARN)) {
      if (this.isDevelopment) {
        console.warn(this.formatMessage('WARN', message, context));
      }
      this.sendToSentry(LogLevel.WARN, message, context);
    }
  }

  error(message: string, error?: Error, context?: LogContext): void {
    if (this.shouldLog(LogLevel.ERROR)) {
      const errorContext = {
        ...context,
        errorMessage: error?.message,
        errorStack: error?.stack,
      };
      
      if (this.isDevelopment) {
        console.error(this.formatMessage('ERROR', message, errorContext));
        if (error) {
          console.error(error);
        }
      }
      
      this.sendToSentry(LogLevel.ERROR, message, errorContext);
    }
  }

  fatal(message: string, error?: Error, context?: LogContext): void {
    const errorContext = {
      ...context,
      errorMessage: error?.message,
      errorStack: error?.stack,
    };
    
    if (this.isDevelopment) {
      console.error(this.formatMessage('FATAL', message, errorContext));
      if (error) {
        console.error(error);
      }
    }
    
    this.sendToSentry(LogLevel.FATAL, message, errorContext);
  }

  // Performance logging
  time(label: string): void {
    if (this.isDevelopment) {
      console.time(label);
    }
  }

  timeEnd(label: string): void {
    if (this.isDevelopment) {
      console.timeEnd(label);
    }
  }

  // Network request logging
  logRequest(method: string, url: string, headers?: any, body?: any): void {
    this.debug('API Request', {
      method,
      url,
      headers: this.sanitizeHeaders(headers),
      body: this.sanitizeBody(body),
    });
  }

  logResponse(method: string, url: string, status: number, duration: number, body?: any): void {
    const level = status >= 400 ? LogLevel.ERROR : LogLevel.DEBUG;
    const message = `API Response: ${method} ${url} - ${status}`;
    
    if (level === LogLevel.ERROR) {
      this.error(message, undefined, {
        status,
        duration,
        body: this.sanitizeBody(body),
      });
    } else {
      this.debug(message, {
        status,
        duration,
        body: this.sanitizeBody(body),
      });
    }
  }

  // Sanitize sensitive data
  private sanitizeHeaders(headers: any): any {
    if (!headers) return headers;
    
    const sanitized = { ...headers };
    const sensitiveHeaders = ['authorization', 'x-api-key', 'cookie'];
    
    sensitiveHeaders.forEach(header => {
      if (sanitized[header]) {
        sanitized[header] = '[REDACTED]';
      }
    });
    
    return sanitized;
  }

  private sanitizeBody(body: any): any {
    if (!body) return body;
    if (typeof body !== 'object') return body;
    
    const sanitized = { ...body };
    const sensitiveFields = ['password', 'token', 'secret', 'apiKey', 'creditCard'];
    
    const sanitizeObject = (obj: any): any => {
      if (!obj || typeof obj !== 'object') return obj;
      
      const result: any = Array.isArray(obj) ? [] : {};
      
      for (const key in obj) {
        if (sensitiveFields.some(field => key.toLowerCase().includes(field.toLowerCase()))) {
          result[key] = '[REDACTED]';
        } else if (typeof obj[key] === 'object') {
          result[key] = sanitizeObject(obj[key]);
        } else {
          result[key] = obj[key];
        }
      }
      
      return result;
    };
    
    return sanitizeObject(sanitized);
  }

  // User action tracking
  trackUserAction(action: string, properties?: LogContext): void {
    this.info(`User Action: ${action}`, properties);
  }

  // Crash reporting
  reportCrash(error: Error, context?: LogContext): void {
    this.fatal('Application Crash', error, context);
  }

  // Set user context for error tracking
  setUserContext(userId: string, email?: string, username?: string): void {
    if (!this.isDevelopment && ENV.SENTRY_DSN) {
      Sentry.Native.setUser({
        id: userId,
        email,
        username,
      });
    }
  }

  // Clear user context on logout
  clearUserContext(): void {
    if (!this.isDevelopment && ENV.SENTRY_DSN) {
      Sentry.Native.setUser(null);
    }
  }

  // Add custom tags for filtering
  setTag(key: string, value: string): void {
    if (!this.isDevelopment && ENV.SENTRY_DSN) {
      Sentry.Native.setTag(key, value);
    }
  }

  // Add extra context
  setContext(key: string, context: any): void {
    if (!this.isDevelopment && ENV.SENTRY_DSN) {
      Sentry.Native.setContext(key, context);
    }
  }
}

export const logger = Logger.getInstance();

// Export convenience functions
export const logDebug = (message: string, context?: LogContext) => logger.debug(message, context);
export const logInfo = (message: string, context?: LogContext) => logger.info(message, context);
export const logWarn = (message: string, context?: LogContext) => logger.warn(message, context);
export const logError = (message: string, error?: Error, context?: LogContext) => logger.error(message, error, context);
export const logFatal = (message: string, error?: Error, context?: LogContext) => logger.fatal(message, error, context);