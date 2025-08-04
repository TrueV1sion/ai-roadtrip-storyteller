# Sentry Integration Guide

## Overview

This document outlines the comprehensive Sentry integration implemented for the AI Road Trip Storyteller mobile app. The integration provides crash reporting, error tracking, performance monitoring, and user feedback capabilities.

## Features Implemented

### 1. **Crash Reporting**
- Automatic crash capture for both JavaScript and native crashes
- Detailed error context including device info, app state, and user actions
- Source map support for readable stack traces in production

### 2. **Error Boundaries**
- Custom `SentryErrorBoundary` component with enhanced UI
- Automatic error recovery with retry logic
- User feedback collection on errors
- Network status awareness

### 3. **Performance Monitoring**
- Screen load time tracking
- API call latency monitoring
- Frame rate monitoring
- Memory usage tracking
- Custom performance metrics

### 4. **User Context**
- Privacy-safe user identification
- Session tracking
- Breadcrumb trail for debugging

### 5. **Environment Configuration**
- Separate configurations for development, staging, and production
- Configurable sample rates to optimize costs
- Environment-specific debug settings

## Setup Instructions

### 1. Configure Sentry DSN

Add your Sentry DSN to the appropriate configuration files:

```bash
# .env file
SENTRY_DSN=https://your-dsn@sentry.io/project-id
SENTRY_ORG=your-org-slug
SENTRY_PROJECT=roadtrip-mobile
SENTRY_AUTH_TOKEN=your-auth-token
```

### 2. Update app.production.json

Ensure your `app.production.json` includes the Sentry configuration:

```json
{
  "expo": {
    "extra": {
      "sentry": {
        "dsn": "${SENTRY_DSN}",
        "environment": "production"
      }
    }
  }
}
```

### 3. Initialize Sentry

Sentry is automatically initialized in `App.tsx` when the app starts. No additional setup required.

## Usage Examples

### Error Handling with Custom Hook

```typescript
import { useErrorHandler } from '@/hooks/useErrorHandler';

function MyComponent() {
  const { handleError, handleAsyncError } = useErrorHandler();

  const fetchData = async () => {
    await handleAsyncError(
      async () => {
        const response = await api.getData();
        return response;
      },
      {
        showAlert: true,
        retryAction: fetchData,
        context: { screen: 'MyComponent' }
      }
    );
  };

  return <View>...</View>;
}
```

### Manual Error Capture

```typescript
import { captureException } from '@/services/sentry/SentryService';

try {
  // Your code
} catch (error) {
  captureException(error, {
    level: 'error',
    tags: { feature: 'voice_command' },
    extra: { userId: user.id }
  });
}
```

### Performance Tracking

```typescript
import { performanceMonitoring } from '@/services/sentry/PerformanceMonitoring';

// In your screen component
useEffect(() => {
  performanceMonitoring.startScreenTracking('ProfileScreen');
  
  // When data is loaded
  performanceMonitoring.markScreenLoaded('ProfileScreen');
  
  return () => {
    performanceMonitoring.endScreenTracking('ProfileScreen');
  };
}, []);
```

### Track Custom Metrics

```typescript
import { trackCustomMetric } from '@/services/sentry/PerformanceMonitoring';

// Track a custom metric
trackCustomMetric('story_generation_time', 1500, 'millisecond');
```

## Build & Deployment

### Source Maps

For production builds, upload source maps to Sentry:

```bash
# After building your app
npm run build:ios
npm run build:android

# Upload source maps
./scripts/upload-sourcemaps.sh
```

### Release Tracking

Releases are automatically tracked using the format:
`roadtrip-mobile@{version}+{buildNumber}`

## Performance Considerations

### Sample Rates

- **Development**: 100% traces, 100% profiles (for testing)
- **Staging**: 50% traces, 30% profiles
- **Production**: 10% traces, 5% profiles (to reduce costs)

### Data Sanitization

Sensitive data is automatically sanitized:
- Passwords, tokens, and API keys are redacted
- Email addresses are hashed for privacy
- Credit card information is never logged

## Monitoring Dashboard

### Key Metrics to Monitor

1. **Crash Free Rate**: Target > 99.5%
2. **Average Screen Load Time**: Target < 2 seconds
3. **API Response Time**: Target < 1 second
4. **JavaScript Error Rate**: Target < 0.5%

### Alerts Configuration

Set up alerts in Sentry for:
- Crash rate spike (> 1%)
- New error types
- Performance regression (> 20% increase in load time)
- High memory usage (> 80%)

## Troubleshooting

### Common Issues

1. **Source maps not working**
   - Ensure `SENTRY_AUTH_TOKEN` has correct permissions
   - Verify release name matches between app and uploaded maps

2. **Missing user context**
   - Check if `setUserContext` is called after login
   - Verify user data is properly sanitized

3. **Performance data not showing**
   - Confirm `tracesSampleRate` is > 0
   - Check if transactions are being finished

### Debug Mode

Enable debug mode in development:

```typescript
// src/config/sentry.config.ts
development: {
  debug: true,
  // ... other config
}
```

## Best Practices

1. **Always use error boundaries** for critical UI sections
2. **Add context** to errors for better debugging
3. **Track user interactions** before errors occur
4. **Monitor performance** of key user flows
5. **Review Sentry issues** weekly and prioritize fixes

## Privacy & Compliance

- User data is sanitized before sending to Sentry
- IP addresses are not stored
- Personal information is hashed or redacted
- Compliance with GDPR and CCPA requirements

## Support

For issues or questions:
1. Check Sentry documentation: https://docs.sentry.io/
2. Review error details in Sentry dashboard
3. Contact the development team for assistance