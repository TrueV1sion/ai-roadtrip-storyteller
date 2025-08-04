# Sentry Integration Examples

## Screen Performance Tracking

### Using the Performance Hook

```typescript
import React from 'react';
import { View, Text } from 'react-native';
import { usePerformanceTracking } from '@/hooks/usePerformanceTracking';

export default function BookingScreen() {
  // Automatically tracks screen performance
  usePerformanceTracking({
    screenName: 'BookingScreen',
    trackFocus: true,
  });

  return (
    <View>
      <Text>Booking Screen</Text>
    </View>
  );
}
```

### Manual Performance Tracking

```typescript
import React, { useEffect } from 'react';
import { 
  startScreenTracking, 
  markScreenLoaded, 
  endScreenTracking,
  trackCustomMetric 
} from '@/services/sentry/PerformanceMonitoring';

export default function ComplexScreen() {
  useEffect(() => {
    // Start tracking
    startScreenTracking('ComplexScreen');
    
    // Simulate data loading
    loadData().then(() => {
      // Mark screen as loaded when data is ready
      markScreenLoaded('ComplexScreen');
      
      // Track custom metrics
      trackCustomMetric('data_items_loaded', 150, 'none');
      trackCustomMetric('cache_hit_rate', 85, 'percent');
    });

    return () => {
      // Clean up tracking
      endScreenTracking('ComplexScreen');
    };
  }, []);

  return <View>{/* Screen content */}</View>;
}
```

## Error Tracking

### Try-Catch with Context

```typescript
import { captureException } from '@/services/sentry/SentryService';

async function fetchUserData(userId: string) {
  try {
    const response = await api.get(`/users/${userId}`);
    return response.data;
  } catch (error) {
    // Capture with context
    captureException(error as Error, {
      level: 'error',
      tags: {
        feature: 'user_profile',
        action: 'fetch_data',
      },
      extra: {
        userId,
        endpoint: `/users/${userId}`,
      },
    });
    
    // Re-throw or handle gracefully
    throw error;
  }
}
```

### Component Error Boundaries

```typescript
import React from 'react';
import { SentryErrorBoundary } from '@/components/error/SentryErrorBoundary';

export default function RiskyFeature() {
  return (
    <SentryErrorBoundary
      showDialog={true}
      enableAutoRecovery={true}
      onError={(error, errorInfo) => {
        // Custom error handling
        console.log('Feature crashed:', error);
      }}
    >
      <ComplexComponent />
    </SentryErrorBoundary>
  );
}
```

## API Performance Tracking

### Tracking API Calls

```typescript
import { trackApiCall } from '@/services/sentry/PerformanceMonitoring';

export async function getBookings() {
  return trackApiCall(
    '/api/bookings',
    'GET',
    async () => {
      const response = await fetch('/api/bookings');
      return response.json();
    }
  );
}
```

### With Axios Interceptor

```typescript
import axios from 'axios';
import { sentryService } from '@/services/sentry/SentryService';

// Add request interceptor
axios.interceptors.request.use((config) => {
  config.metadata = { startTime: performance.now() };
  return config;
});

// Add response interceptor
axios.interceptors.response.use(
  (response) => {
    const duration = performance.now() - response.config.metadata.startTime;
    
    // Track successful API call
    sentryService.trackApiCall(
      response.config.method?.toUpperCase() || 'GET',
      response.config.url || '',
      response.status,
      duration
    );
    
    return response;
  },
  (error) => {
    const duration = performance.now() - error.config?.metadata?.startTime || 0;
    
    // Track failed API call
    sentryService.trackApiCall(
      error.config?.method?.toUpperCase() || 'GET',
      error.config?.url || '',
      error.response?.status || 0,
      duration
    );
    
    // Capture the error
    captureException(error, {
      tags: {
        api_error: 'true',
        endpoint: error.config?.url,
      },
    });
    
    return Promise.reject(error);
  }
);
```

## User Interaction Tracking

### Button Click Tracking

```typescript
import { trackUserInteraction } from '@/services/sentry/SentryService';

function BookingButton({ bookingId }: { bookingId: string }) {
  const handlePress = () => {
    // Track interaction
    trackUserInteraction('booking_button_pressed', 'click', {
      bookingId,
      timestamp: new Date().toISOString(),
    });
    
    // Perform action
    navigateToBooking(bookingId);
  };

  return (
    <TouchableOpacity onPress={handlePress}>
      <Text>View Booking</Text>
    </TouchableOpacity>
  );
}
```

### Form Submission Tracking

```typescript
import { withErrorTracking } from '@/services/sentry/SentryService';

function PaymentForm() {
  const handleSubmit = async (formData: PaymentData) => {
    // Track with automatic error handling
    await withErrorTracking(
      async () => {
        // Track form submission
        trackUserInteraction('payment_form_submitted', 'submit', {
          amount: formData.amount,
          method: formData.paymentMethod,
        });
        
        // Process payment
        const result = await processPayment(formData);
        
        // Track success
        trackUserInteraction('payment_completed', 'success', {
          transactionId: result.transactionId,
        });
        
        return result;
      },
      {
        operation: 'payment_processing',
        description: 'Process user payment',
        tags: {
          feature: 'payments',
          payment_method: formData.paymentMethod,
        },
      }
    );
  };

  return <Form onSubmit={handleSubmit} />;
}
```

## User Context Management

### Setting User Context on Login

```typescript
import { setUserContext } from '@/services/sentry/SentryService';

async function handleLogin(credentials: LoginCredentials) {
  try {
    const user = await authService.login(credentials);
    
    // Set Sentry user context
    await setUserContext({
      id: user.id,
      username: user.username,
      email: user.email,
    });
    
    // Track successful login
    trackUserInteraction('user_logged_in', 'auth', {
      method: 'email',
    });
    
    return user;
  } catch (error) {
    captureException(error as Error, {
      tags: { auth_error: 'login' },
    });
    throw error;
  }
}
```

### Clearing Context on Logout

```typescript
import { sentryService } from '@/services/sentry/SentryService';

async function handleLogout() {
  // Track logout
  trackUserInteraction('user_logged_out', 'auth');
  
  // Clear user context
  await sentryService.clearUserContext();
  
  // Clear local storage
  await authService.logout();
}
```

## Custom Breadcrumbs

### Navigation Breadcrumbs

```typescript
import { sentryService } from '@/services/sentry/SentryService';

export function NavigationListener() {
  const navigation = useNavigation();
  
  useEffect(() => {
    const unsubscribe = navigation.addListener('state', (e) => {
      const currentRoute = navigation.getCurrentRoute();
      
      sentryService.addBreadcrumb({
        category: 'navigation',
        message: `Navigated to ${currentRoute?.name}`,
        level: 'info',
        data: {
          from: e.data.state?.previousRoute,
          to: currentRoute?.name,
          params: currentRoute?.params,
        },
      });
    });
    
    return unsubscribe;
  }, [navigation]);
  
  return null;
}
```

### Custom Event Breadcrumbs

```typescript
function trackCustomEvent(eventName: string, data?: any) {
  sentryService.addBreadcrumb({
    category: 'custom',
    message: eventName,
    level: 'info',
    type: 'default',
    data: {
      ...data,
      timestamp: new Date().toISOString(),
    },
  });
}

// Usage
trackCustomEvent('tutorial_completed', { 
  steps: 5, 
  duration: 120 
});
```

## Performance Monitoring

### App Startup Tracking

```typescript
import { trackAppStartup } from '@/services/sentry/PerformanceMonitoring';

// In App.tsx
export default function App() {
  const [isReady, setIsReady] = useState(false);
  const startTime = useRef(performance.now());
  
  useEffect(() => {
    const initializeApp = async () => {
      // Your initialization code
      await loadResources();
      
      // Track startup time
      const startupTime = performance.now() - startTime.current;
      trackAppStartup(startupTime);
      
      setIsReady(true);
    };
    
    initializeApp();
  }, []);
  
  if (!isReady) {
    return <SplashScreen />;
  }
  
  return <MainApp />;
}
```

### Memory Usage Tracking

```typescript
import { performanceMonitoring } from '@/services/sentry/PerformanceMonitoring';

// Track memory usage periodically
useEffect(() => {
  const interval = setInterval(() => {
    if (performance.memory) {
      performanceMonitoring.trackMemoryUsage(
        performance.memory.usedJSHeapSize,
        performance.memory.jsHeapSizeLimit
      );
    }
  }, 30000); // Every 30 seconds
  
  return () => clearInterval(interval);
}, []);
```

## Testing Sentry Integration

### Manual Test Button

```typescript
import React from 'react';
import { Button, View } from 'react-native';
import { captureException, captureMessage } from '@/services/sentry/SentryService';

export function SentryTestButtons() {
  return (
    <View>
      <Button
        title="Test JS Error"
        onPress={() => {
          throw new Error('Test Sentry JS Error');
        }}
      />
      
      <Button
        title="Test Captured Exception"
        onPress={() => {
          try {
            JSON.parse('invalid json');
          } catch (error) {
            captureException(error as Error, {
              tags: { test: 'true' },
              extra: { purpose: 'testing sentry integration' },
            });
          }
        }}
      />
      
      <Button
        title="Test Message"
        onPress={() => {
          captureMessage('Test Sentry Message', 'info', {
            tags: { test: 'true' },
          });
        }}
      />
      
      <Button
        title="Test Performance"
        onPress={async () => {
          const transaction = sentryService.startTransaction(
            'test_transaction',
            'test'
          );
          
          // Simulate work
          await new Promise(resolve => setTimeout(resolve, 1000));
          
          transaction?.finish();
        }}
      />
    </View>
  );
}
```

## Best Practices

1. **Always sanitize sensitive data** before sending to Sentry
2. **Use meaningful error messages** and context
3. **Group similar errors** using fingerprints
4. **Track user actions** that lead to errors
5. **Monitor performance** of critical user paths
6. **Set up alerts** for error spikes
7. **Use breadcrumbs** to understand error context
8. **Test error tracking** in development
9. **Configure sampling** appropriately for production
10. **Review Sentry dashboard** regularly