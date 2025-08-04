# Sentry Setup Guide for React Native

## Status: READY FOR CONFIGURATION ⚠️

Sentry crash reporting and performance monitoring is fully implemented but needs to be configured with your Sentry DSN.

## Implementation Details

### 1. Core Sentry Service ✅
- **Location**: `src/services/sentry/SentryService.ts`
- **Features**:
  - Comprehensive error tracking
  - Performance monitoring
  - Breadcrumb tracking
  - User context management
  - Sensitive data sanitization
  - Network status awareness
  - Custom error fingerprinting

### 2. Error Boundary Integration ✅
- **Location**: `src/components/error/SentryErrorBoundary.tsx`
- **Features**:
  - Automatic error catching and reporting
  - User-friendly error UI
  - Error recovery mechanisms
  - Offline error storage
  - Debug information in development
  - User feedback collection

### 3. App Integration ✅
- **Location**: `src/App.tsx`
- Already integrated with Sentry initialization

## Installation Instructions

### Step 1: Install Sentry SDK

```bash
# Using npm
npm install sentry-expo

# Or using yarn
yarn add sentry-expo

# For bare React Native projects (if ejected from Expo)
npm install @sentry/react-native
cd ios && pod install
```

### Step 2: Create Sentry Account and Project

1. Go to [sentry.io](https://sentry.io) and create an account
2. Create a new project:
   - Platform: React Native
   - Project Name: "RoadTrip Mobile"
3. Copy your DSN from the project settings

### Step 3: Configure Environment Variables

1. Create `.env` file in mobile directory:
```env
EXPO_PUBLIC_SENTRY_DSN=https://YOUR_DSN_HERE@sentry.io/YOUR_PROJECT_ID
```

2. Update `.env.production`:
```env
EXPO_PUBLIC_SENTRY_DSN=https://YOUR_PRODUCTION_DSN@sentry.io/YOUR_PROJECT_ID
```

### Step 4: Configure app.config.js (Already Done ✅)

The app.config.js is already configured to read the Sentry DSN:
```javascript
extra: {
  EXPO_PUBLIC_SENTRY_DSN: process.env.EXPO_PUBLIC_SENTRY_DSN,
}
```

### Step 5: Configure Sentry Plugin (For Expo)

Add to `app.config.js`:
```javascript
plugins: [
  'expo-constants',
  [
    'sentry-expo',
    {
      dsn: process.env.EXPO_PUBLIC_SENTRY_DSN,
      enableInExpoDevelopment: false,
      debug: false,
    }
  ]
]
```

### Step 6: Configure Source Maps (Production)

For production builds, configure source map upload:

1. Install Sentry CLI:
```bash
npm install -g @sentry/cli
```

2. Create `.sentryclirc`:
```ini
[defaults]
org = your-org-name
project = roadtrip-mobile

[auth]
token = YOUR_AUTH_TOKEN
```

3. Add to package.json scripts:
```json
{
  "scripts": {
    "postbuild:ios": "sentry-cli releases files roadtrip-mobile@1.0.0 upload-sourcemaps --dist ios ./build",
    "postbuild:android": "sentry-cli releases files roadtrip-mobile@1.0.0 upload-sourcemaps --dist android ./build"
  }
}
```

## Configuration Options

### Environment-Based Configuration

The Sentry service automatically adjusts settings based on environment:

| Environment | Traces Sample Rate | Debug Mode | Screenshots |
|-------------|-------------------|------------|-------------|
| Development | 100% | Yes | Yes |
| Staging | 50% | No | Yes |
| Production | 10% | No | Yes |

### Custom Configuration

You can customize Sentry initialization in `App.tsx`:

```typescript
await initializeSentry({
  dsn: ENV.SENTRY_DSN,
  environment: 'production',
  tracesSampleRate: 0.2, // 20% of transactions
  profilesSampleRate: 0.1, // 10% profiling
  attachScreenshot: true,
  attachStacktrace: true,
  maxBreadcrumbs: 100,
  beforeSend: (event) => {
    // Custom event filtering
    if (event.environment === 'development') {
      return null; // Don't send dev events
    }
    return event;
  },
});
```

## Features Implemented

### 1. Automatic Error Tracking
- JavaScript errors
- React component errors
- Unhandled promise rejections
- Native crashes (iOS/Android)

### 2. Performance Monitoring
```typescript
// Transaction tracking
const transaction = sentryService.startTransaction(
  'checkout',
  'user_action',
  'User checkout flow'
);

// ... perform operations ...

transaction?.finish();
```

### 3. User Context
```typescript
// Set user context after login
await setUserContext({
  id: user.id,
  username: user.username,
  email: user.email,
});

// Clear on logout
await sentryService.clearUserContext();
```

### 4. Breadcrumb Tracking
Automatic breadcrumbs for:
- Navigation changes
- API calls
- User interactions
- Console logs
- Network requests

### 5. Custom Error Tracking
```typescript
// With context
captureException(error, {
  level: 'error',
  tags: {
    feature: 'booking',
    action: 'payment',
  },
  extra: {
    bookingId: '12345',
    amount: 99.99,
  },
});

// Simple message
captureMessage('Payment gateway timeout', 'warning');
```

### 6. Privacy Protection

The service automatically sanitizes:
- Passwords
- API keys
- Auth tokens
- Credit card information
- Social security numbers
- Any field containing "private", "secret", etc.

## Testing Sentry Integration

### 1. Test JavaScript Error
```typescript
// Add this to a test component
const TestSentry = () => {
  const throwError = () => {
    throw new Error('Test Sentry JavaScript error');
  };

  return (
    <Button title="Test JS Error" onPress={throwError} />
  );
};
```

### 2. Test Native Crash (iOS)
```typescript
import { NativeModules } from 'react-native';

// This will cause a native crash
NativeModules.SentryCrash.crash();
```

### 3. Test Captured Exception
```typescript
const testSentry = () => {
  try {
    // Some operation that might fail
    JSON.parse('invalid json');
  } catch (error) {
    captureException(error as Error, {
      tags: { test: 'true' },
    });
  }
};
```

### 4. Verify in Sentry Dashboard
1. Trigger test errors
2. Go to your Sentry project dashboard
3. Check "Issues" for errors
4. Check "Performance" for transactions
5. Verify breadcrumbs and context are attached

## Production Checklist

- [ ] Set production Sentry DSN in environment variables
- [ ] Configure release tracking in CI/CD
- [ ] Set up source map uploads
- [ ] Configure alert rules in Sentry
- [ ] Set up issue assignment workflow
- [ ] Configure data retention policies
- [ ] Set up performance budgets
- [ ] Configure release health tracking

## Monitoring Dashboard

### Key Metrics to Monitor
1. **Crash-free rate**: Target > 99.5%
2. **Error rate**: Track spikes and trends
3. **Performance**: P95 transaction duration
4. **User impact**: Affected users per release

### Recommended Alerts
1. Error rate spike (> 100 errors/hour)
2. New error types in production
3. Performance regression (> 20% increase)
4. Crash-free rate drop (< 99%)

## Troubleshooting

### Sentry Not Capturing Events
1. Verify DSN is correctly set
2. Check network connectivity
3. Ensure Sentry is initialized before errors occur
4. Check beforeSend filter isn't dropping events

### Missing Source Maps
1. Ensure source maps are generated during build
2. Verify Sentry CLI is configured correctly
3. Check release names match between app and Sentry

### Performance Issues
1. Reduce tracesSampleRate in production
2. Limit breadcrumb collection
3. Use sampling for high-volume events

## Advanced Features

### 1. Profiling (Experimental)
```typescript
profilesSampleRate: 0.1, // 10% of transactions
```

### 2. Session Replay (Coming Soon)
Will capture user sessions for debugging

### 3. Custom Integrations
```typescript
integrations: [
  new Sentry.Integrations.ReactNativeTracing({
    tracingOrigins: ['localhost', /^\//],
    routingInstrumentation: reactNavigationInstrumentation,
  }),
]
```

## Security Considerations

1. **DSN Exposure**: The DSN is client-safe but don't include auth tokens
2. **PII Filtering**: Always sanitize sensitive data before sending
3. **Data Retention**: Configure according to privacy requirements
4. **User Consent**: May need user consent for error tracking in EU

## Cost Management

Sentry pricing is based on event volume:
- Use sampling to control costs
- Filter out noisy/low-value events
- Set quotas and spending caps
- Monitor usage in Sentry dashboard

## References

- [Sentry React Native Docs](https://docs.sentry.io/platforms/react-native/)
- [Expo Sentry Setup](https://docs.expo.dev/guides/using-sentry/)
- [Performance Monitoring](https://docs.sentry.io/platforms/react-native/performance/)
- [Privacy & Security](https://sentry.io/security/)