# Proactive Story System - Complete Integration Guide

## Overview
The proactive story system automatically generates and delivers stories at optimal moments during a journey, replacing the rigid 15-minute interval system with dynamic, context-aware timing.

## System Components

### 1. **Story Timing Orchestrator** (`story_timing_orchestrator.py`)
- Calculates optimal story timing based on journey context
- Considers driving complexity, passenger engagement, journey phase
- Supports perfect moment overrides (POIs, golden hour, milestones)

### 2. **Passenger Engagement Tracker** (`passenger_engagement_tracker.py`)
- Monitors user interactions and engagement levels
- Uses time-decay algorithm for event relevance
- Provides engagement metrics for timing decisions

### 3. **Story Opportunity Scheduler** (`story_opportunity_scheduler.py`)
- Background service checking for story opportunities every 30 seconds
- Manages active journey monitoring
- Triggers story generation when timing conditions are met

### 4. **Story Queue Manager** (`story_queue_manager.py`)
- Priority queue system for story delivery
- Manages perfect moment stories vs regular interval stories
- Ensures proper story spacing and prevents overload

### 5. **Journey Tracking API** (`routes/journey_tracking.py`)
- Endpoints for starting/stopping journey monitoring
- Location update handling
- Pending story checking for mobile app

## Mobile App Integration

### Starting a Journey
```javascript
// When user starts their trip
const response = await fetch('/api/journey/start-journey', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    current_location: { lat: 37.7749, lng: -122.4194 },
    destination: { lat: 37.3382, lng: -121.8863 },
    passengers: [
      { user_id: userId, age: 'adult' }
    ],
    vehicle_info: {
      type: 'car',
      speed_kmh: 0
    },
    route_info: {
      total_distance_km: 78.5,
      estimated_duration_minutes: 65
    }
  })
});
```

### Updating Location (Every 30-60 seconds)
```javascript
// In your location tracking service
const updateLocation = async (location) => {
  await fetch('/api/journey/update-location', {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      current_location: location,
      journey_stage: calculateJourneyStage(progress),
      vehicle_info: {
        speed_kmh: currentSpeed,
        average_speed_kmh: averageSpeed
      },
      route_info: {
        remaining_distance_km: remainingDistance,
        traffic_level: trafficLevel,
        nearest_poi: nearestPOI
      },
      weather: currentWeather
    })
  });
};
```

### Checking for Pending Stories (Poll every 10-30 seconds)
```javascript
// In your story polling service
const checkForStory = async () => {
  const response = await fetch('/api/journey/check-pending-story', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  const data = await response.json();
  if (data.has_story) {
    // Trigger story generation
    await generateAndPlayStory(data.journey_context);
    
    // Record story delivery
    await fetch('/api/story-timing/record-story-delivered', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
  }
};

// Set up polling
setInterval(checkForStory, 15000); // Check every 15 seconds
```

### Recording Engagement Events
```javascript
// When user interacts with stories
const recordEngagement = async (eventType) => {
  await fetch('/api/story-timing/record-engagement-event', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      event_type: eventType, // e.g., "USER_REQUEST_STORY", "STORY_COMPLETED"
      metadata: {
        story_id: currentStoryId,
        user_action: userAction
      }
    })
  });
};

// Usage examples:
recordEngagement('USER_REQUEST_STORY');      // User asks for a story
recordEngagement('STORY_COMPLETED');         // Story finishes playing
recordEngagement('STORY_SKIPPED');           // User skips story
recordEngagement('USER_POSITIVE_RESPONSE');  // User gives positive feedback
```

### Ending a Journey
```javascript
// When trip is complete
await fetch('/api/journey/end-journey', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
```

## Configuration

### Timing Parameters
Located in `StoryTimingOrchestrator`:
```python
# Base timing by journey phase (minutes)
DEPARTURE: 3.0
EARLY: 5.0
CRUISE: 6.0
APPROACHING: 4.0
ARRIVAL: 2.5

# Bounds
MIN_INTERVAL: 1.5 minutes
MAX_INTERVAL: 12.0 minutes
```

### Perfect Moment Triggers
- **POI Proximity**: < 2km from point of interest
- **Golden Hour**: 6-7 AM, 6-7 PM
- **Journey Milestones**: 25%, 50%, 75% completion
- **User Request**: Immediate delivery

### Engagement Event Weights
```python
USER_REQUEST_STORY: 1.0      # Highest weight
USER_FOLLOWUP_QUESTION: 0.9
USER_POSITIVE_RESPONSE: 0.8
USER_INTERACTION: 0.7
STORY_COMPLETED: 0.6
USER_NEUTRAL_RESPONSE: 0.5
STORY_STARTED: 0.4
NO_RESPONSE: 0.3
STORY_SKIPPED: 0.2
USER_NEGATIVE_RESPONSE: 0.15
USER_SAYS_STOP: 0.1          # Lowest weight
```

## Monitoring & Debugging

### Check System Status
```bash
# View scheduler logs
docker logs backend_container | grep "Story opportunity"

# Check active journeys
curl http://localhost:8000/api/journey/journey-status \
  -H "Authorization: Bearer $TOKEN"

# View story timing metrics
curl http://localhost:8000/metrics | grep story_
```

### Common Issues

**Stories Not Triggering**
1. Verify journey is started (`/api/journey/start-journey`)
2. Check location updates are being sent
3. Ensure scheduler is running (check logs)
4. Verify engagement tracker has events

**Too Many/Few Stories**
1. Review engagement levels in logs
2. Check driving complexity assessment
3. Verify timing multipliers
4. Adjust base timing values if needed

**Perfect Moments Missed**
1. Ensure POI data in route_info
2. Verify time zone for golden hour
3. Check journey progress calculation

## Testing

### Manual Testing
```python
# Test story opportunity check
curl -X POST http://localhost:8000/api/story-timing/check-story-opportunity \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "current_location": {"lat": 37.7749, "lng": -122.4194},
    "journey_stage": "cruise",
    "route_info": {
      "nearest_poi": {
        "name": "Golden Gate Bridge",
        "distance_km": 1.5
      }
    }
  }'
```

### Load Testing
```python
# Simulate multiple active journeys
for i in range(100):
    start_journey(f"test_user_{i}")
    
# Monitor performance
watch "curl -s localhost:8000/metrics | grep story_"
```

## Metrics

The system records:
- `story_timing_interval_minutes` - Calculated timing intervals
- `story_engagement_level` - Current engagement levels
- `story_opportunity_checks_triggered` - Stories triggered
- `story_opportunity_checks_skipped` - Stories deferred
- `stories_delivered_total` - Total stories delivered
- `engagement_event_{type}` - Engagement events by type

## Future Enhancements

1. **Machine Learning Integration**
   - Learn optimal timing per user
   - Predict engagement patterns
   - Personalize story intervals

2. **Advanced Queue Management**
   - Story pre-generation for perfect moments
   - Multi-story narrative arcs
   - Conditional story chains

3. **Real-time Adjustments**
   - Traffic-aware timing
   - Weather-based story selection
   - Group dynamics detection

4. **Analytics Dashboard**
   - Story performance metrics
   - Engagement heatmaps
   - A/B testing framework