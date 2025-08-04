/**
 * Sentry Configuration for different environments
 */

import Constants from 'expo-constants';

export interface SentryEnvironmentConfig {
  dsn: string;
  environment: 'development' | 'staging' | 'production';
  tracesSampleRate: number;
  profilesSampleRate: number;
  enableInDevelopment: boolean;
  debug: boolean;
  attachStacktrace: boolean;
  attachScreenshot: boolean;
  maxBreadcrumbs: number;
  enableAutoSessionTracking: boolean;
  sessionTrackingIntervalMillis: number;
  enableNativeCrashHandling: boolean;
  enableAutoPerformanceTracking: boolean;
}

const getEnvironment = (): 'development' | 'staging' | 'production' => {
  const env = Constants.expoConfig?.extra?.environment || process.env.NODE_ENV;
  
  switch (env) {
    case 'production':
      return 'production';
    case 'staging':
      return 'staging';
    default:
      return 'development';
  }
};

const SENTRY_DSN = Constants.expoConfig?.extra?.sentry?.dsn || process.env.SENTRY_DSN || '';

export const SENTRY_CONFIG: Record<string, SentryEnvironmentConfig> = {
  development: {
    dsn: SENTRY_DSN,
    environment: 'development',
    tracesSampleRate: 1.0, // 100% for development
    profilesSampleRate: 1.0, // 100% for development
    enableInDevelopment: false, // Usually disabled in dev
    debug: true,
    attachStacktrace: true,
    attachScreenshot: false, // Disabled in dev for performance
    maxBreadcrumbs: 100,
    enableAutoSessionTracking: true,
    sessionTrackingIntervalMillis: 30000,
    enableNativeCrashHandling: true,
    enableAutoPerformanceTracking: true,
  },
  staging: {
    dsn: SENTRY_DSN,
    environment: 'staging',
    tracesSampleRate: 0.5, // 50% for staging
    profilesSampleRate: 0.3, // 30% for staging
    enableInDevelopment: false,
    debug: false,
    attachStacktrace: true,
    attachScreenshot: true,
    maxBreadcrumbs: 100,
    enableAutoSessionTracking: true,
    sessionTrackingIntervalMillis: 30000,
    enableNativeCrashHandling: true,
    enableAutoPerformanceTracking: true,
  },
  production: {
    dsn: SENTRY_DSN,
    environment: 'production',
    tracesSampleRate: 0.1, // 10% for production to reduce overhead
    profilesSampleRate: 0.05, // 5% for production
    enableInDevelopment: false,
    debug: false,
    attachStacktrace: true,
    attachScreenshot: true,
    maxBreadcrumbs: 50, // Reduced for production
    enableAutoSessionTracking: true,
    sessionTrackingIntervalMillis: 60000, // Less frequent in production
    enableNativeCrashHandling: true,
    enableAutoPerformanceTracking: true,
  },
};

export const getCurrentSentryConfig = (): SentryEnvironmentConfig => {
  const environment = getEnvironment();
  return SENTRY_CONFIG[environment];
};

// Privacy-safe user context builder
export const buildUserContext = (user: {
  id: string;
  email?: string;
  username?: string;
  subscription?: string;
}) => {
  return {
    id: user.id,
    // Only include email/username if user has consented
    email: user.email ? hashEmail(user.email) : undefined,
    username: user.username,
    // Additional safe metadata
    subscription_type: user.subscription,
  };
};

// Hash email for privacy
const hashEmail = (email: string): string => {
  // Simple hash for privacy - in production use proper hashing
  const domain = email.split('@')[1];
  const username = email.split('@')[0];
  const hashedUsername = username.charAt(0) + '*'.repeat(username.length - 2) + username.charAt(username.length - 1);
  return `${hashedUsername}@${domain}`;
};

// Error filtering rules
export const shouldFilterError = (error: Error): boolean => {
  const errorMessage = error.message.toLowerCase();
  
  // Filter out known non-critical errors
  const ignoredErrors = [
    'network request failed',
    'task orphaned',
    'cancelled',
    'aborted',
  ];
  
  return ignoredErrors.some(ignored => errorMessage.includes(ignored));
};

// Breadcrumb filtering rules
export const shouldFilterBreadcrumb = (breadcrumb: any): boolean => {
  // Filter out noisy breadcrumbs
  if (breadcrumb.category === 'console' && breadcrumb.level === 'debug') {
    return true;
  }
  
  // Filter out sensitive URLs
  if (breadcrumb.category === 'fetch' && breadcrumb.data?.url) {
    const sensitiveUrls = ['/api/auth/', '/api/payment/'];
    return sensitiveUrls.some(url => breadcrumb.data.url.includes(url));
  }
  
  return false;
};

// Performance thresholds
export const PERFORMANCE_THRESHOLDS = {
  SCREEN_LOAD: {
    EXCELLENT: 1000,
    GOOD: 2000,
    FAIR: 3000,
    POOR: 5000,
  },
  API_CALL: {
    EXCELLENT: 500,
    GOOD: 1000,
    FAIR: 2000,
    POOR: 3000,
  },
  FRAME_RATE: {
    EXCELLENT: 60,
    GOOD: 45,
    FAIR: 30,
    POOR: 20,
  },
  MEMORY_USAGE: {
    EXCELLENT: 50,
    GOOD: 70,
    FAIR: 80,
    POOR: 90,
  },
};

// Release tracking
export const getReleaseInfo = () => {
  const version = Constants.manifest?.version || '1.0.0';
  const buildNumber = Constants.manifest?.ios?.buildNumber || 
                     Constants.manifest?.android?.versionCode?.toString() || 
                     '1';
  
  return {
    release: `${Constants.expoConfig?.slug || 'app'}@${version}+${buildNumber}`,
    dist: buildNumber,
    version,
  };
};