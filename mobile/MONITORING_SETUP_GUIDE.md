# Monitoring and Alerting Setup Guide

## Overview

Comprehensive monitoring and alerting has been implemented for the RoadTrip AI Storyteller mobile app, providing real-time insights into app performance, errors, and user experience.

## Components Implemented

### 1. Monitoring Service (`MonitoringService.ts`)
Central service that coordinates all monitoring activities:
- Performance tracking
- Error monitoring
- Network state monitoring
- Device health monitoring
- Custom metrics and events
- Alert generation

### 2. Performance Monitoring (`PerformanceMonitoring.ts`)
Tracks app and screen performance:
- Screen load times
- API call latency
- Frame rates
- Memory usage
- App startup time

### 3. Monitoring Dashboard (`MonitoringDashboard.tsx`)
Development tool for real-time monitoring:
- Active alerts display
- Device status metrics
- Screen performance data
- API performance tracking

### 4. Monitoring Hooks (`useMonitoring.ts`)
React hooks for easy integration:
- `useMonitoring` - Main monitoring hook
- `useRenderTracking` - Component render tracking
- `useAsyncTracking` - Async operation tracking

### 5. Configuration (`monitoring.config.ts`)
Centralized monitoring configuration:
- Performance thresholds
- Alert rules
- Sampling rates
- Feature toggles

## Setup Instructions

### 1. Initialize Monitoring on App Start

```typescript
// In App.tsx or index.ts
import { initializeMonitoring } from './src/services/monitoring/initializeMonitoring';

const App = () => {
  useEffect(() => {
    // Initialize monitoring
    initializeMonitoring();
    
    return () => {
      // Cleanup on unmount
      cleanupMonitoring();
    };
  }, []);
  
  // ... rest of app
};
```

### 2. Track Screen Performance

```typescript
import { useMonitoring } from '../hooks/useMonitoring';

const MyScreen = () => {
  const { markLoaded, logEvent, trackInteraction } = useMonitoring({
    screenName: 'MyScreen',
    trackFocus: true,
  });

  useEffect(() => {
    // Mark screen as loaded when ready
    markLoaded();
  }, []);

  const handleButtonPress = () => {
    trackInteraction('button_press', 'submit_button');
    // ... handle press
  };

  return <View>...</View>;
};
```

### 3. Track API Calls

```typescript
const { trackApi } = useMonitoring();

const fetchData = async () => {
  return trackApi('/api/data', 'GET', async () => {
    const response = await fetch('/api/data');
    return response.json();
  });
};
```

### 4. Track Custom Metrics

```typescript
const { logMetric } = useMonitoring();

// Track timing
const startTime = Date.now();
await someOperation();
logMetric('operation_duration', Date.now() - startTime, 'millisecond');

// Track counts
logMetric('items_processed', itemCount, 'none');

// Track percentages
logMetric('cache_hit_rate', hitRate * 100, 'percent');
```

### 5. Handle Errors

```typescript
const { logError } = useMonitoring();

try {
  await riskyOperation();
} catch (error) {
  logError(error as Error, {
    operation: 'risky_operation',
    context: additionalContext,
  });
}
```

## Monitoring Dashboard

### Development Access

The monitoring dashboard is available in development mode:

```typescript
// In a development screen or menu
import { MonitoringDashboard } from '../components/monitoring/MonitoringDashboard';

const DevMenu = () => {
  const [showMonitoring, setShowMonitoring] = useState(false);

  if (__DEV__ && showMonitoring) {
    return <MonitoringDashboard onClose={() => setShowMonitoring(false)} />;
  }
  
  // ... regular menu
};
```

### Dashboard Features
- **Active Alerts**: Real-time alerts with severity levels
- **Device Status**: Battery, memory, disk, network
- **Screen Performance**: Load times, render times, API calls
- **API Performance**: Endpoint latency and call counts

## Alert Configuration

### Alert Types

1. **Error Alerts** (Red)
   - High error rate (>5%)
   - Critical errors (OOM, crashes)
   - API failures

2. **Warning Alerts** (Yellow)
   - Slow performance (>3s)
   - High resource usage (>80%)
   - Network issues

3. **Info Alerts** (Blue)
   - Low battery (<20%)
   - Feature usage stats
   - User milestones

### Alert Rules

Configure in `monitoring.config.ts`:

```typescript
export const ALERT_RULES = [
  {
    name: 'Slow API Response',
    condition: (metrics) => metrics.apiLatency > 3000,
    severity: 'warning',
    message: (metrics) => `API latency is ${metrics.apiLatency}ms`,
  },
  // ... more rules
];
```

## Performance Thresholds

### Screen Performance
- **Excellent**: <1s load time
- **Good**: 1-2s load time
- **Fair**: 2-3s load time
- **Poor**: >3s load time

### API Performance
- **Fast**: <500ms
- **Normal**: 500ms-2s
- **Slow**: 2s-3s
- **Critical**: >3s

### Resource Usage
- **Memory**: Alert at >80% usage
- **Battery**: Alert at <20%
- **Disk**: Alert at <10% free

## Production Configuration

### 1. Environment-Based Config

```typescript
// Automatically configured based on environment
configureMonitoringForEnvironment(
  process.env.EXPO_PUBLIC_ENVIRONMENT as 'development' | 'staging' | 'production'
);
```

### 2. Sampling Rates

- **Development**: 100% sampling
- **Staging**: 50% events, 20% metrics
- **Production**: 10% events, 5% metrics

### 3. Data Retention

- **Alerts**: 7 days
- **Metrics**: 30 days
- **Errors**: 90 days

## Integration with Backend

### Health Check Endpoints

The monitoring service periodically checks:
- `/health` - Backend health
- `/api/proxy/maps/health` - Maps service
- `/api/proxy/booking/health` - Booking service

### Metric Aggregation

Metrics are sent to backend for aggregation:
- Performance metrics every 5 minutes
- Error reports immediately
- Custom events batched every minute

## Best Practices

### 1. Screen Tracking
```typescript
// Always track screen lifecycle
const monitoring = useMonitoring({ screenName: 'MyScreen' });

useEffect(() => {
  monitoring.markLoaded();
}, []);
```

### 2. Error Context
```typescript
// Include relevant context with errors
logError(error, {
  userId: currentUser.id,
  action: 'booking_submission',
  bookingData: { ... },
});
```

### 3. Custom Metrics
```typescript
// Use descriptive metric names
logMetric('booking_form_completion_time', duration, 'millisecond');
logMetric('search_results_count', count, 'none');
```

### 4. Performance Optimization
```typescript
// Only track important events
if (shouldTrackMetric('detailed_interaction')) {
  trackInteraction('gesture', 'complex_swipe', { ... });
}
```

## Troubleshooting

### Common Issues

1. **No metrics appearing**
   - Check monitoring is initialized
   - Verify sampling rates
   - Check feature flags

2. **Too many alerts**
   - Adjust thresholds in config
   - Implement alert cooldown
   - Filter by severity

3. **Performance impact**
   - Reduce sampling rates
   - Disable verbose logging
   - Use async tracking

### Debug Commands

```typescript
// Check monitoring status
console.log(monitoringService.getAlerts());

// Force metric collection
monitoringService.performHealthCheck();

// Clear all alerts
monitoringService.clearAlerts();
```

## Security Considerations

1. **No PII in metrics** - Don't log personal information
2. **Sanitize errors** - Remove sensitive data from error messages
3. **Secure transmission** - All metrics sent over HTTPS
4. **Access control** - Dashboard only in development

## Future Enhancements

1. **Push notifications** for critical alerts
2. **Email alerts** for production issues
3. **Custom dashboards** per user role
4. **ML-based anomaly detection**
5. **Integration with PagerDuty/Slack**

## Summary

The monitoring system provides:
- ✅ Real-time performance tracking
- ✅ Comprehensive error monitoring
- ✅ Device and network health checks
- ✅ Custom metrics and events
- ✅ Configurable alerts and thresholds
- ✅ Development dashboard
- ✅ Production-ready configuration

This ensures the app maintains high performance and reliability while providing actionable insights for continuous improvement.