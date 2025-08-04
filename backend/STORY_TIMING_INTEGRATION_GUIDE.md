# Dynamic Story Timing System - Integration Guide

## Overview
The dynamic story timing system replaces the fixed 15-minute interval with context-aware timing. This guide explains how to properly integrate it into your existing system.

## Critical Integration Points

### 1. **Proactive Story Checking**
The `check_story_opportunity()` method needs to be called periodically. You have several options:

#### Option A: Background Task (Recommended)
```python
# In your background task runner (e.g., Celery)
@celery_app.task
def check_story_opportunities():
    """Run every minute during active journeys"""
    for active_journey in get_active_journeys():
        journey_context = build_journey_context(active_journey)
        if orchestrator.check_story_opportunity(journey_context):
            trigger_story_generation.delay(active_journey.id)
```

#### Option B: Location Update Hook
```python
# In your location update handler
async def handle_location_update(user_id: str, location: dict):
    # Existing location processing...
    
    # Check story opportunity
    journey_context = await build_journey_context(user_id, location)
    if await orchestrator.check_story_opportunity(journey_context):
        await generate_and_deliver_story(user_id)
```

#### Option C: API Polling
Use the `/api/story-timing/check-story-opportunity` endpoint from the mobile app.

### 2. **Engagement Event Recording**
Record user interactions to improve timing accuracy:

```python
# When user requests a story
orchestrator.record_engagement_event(
    user_id, 
    EngagementEventType.USER_REQUEST_STORY
)

# When user skips a story
orchestrator.record_engagement_event(
    user_id, 
    EngagementEventType.STORY_SKIPPED
)

# When story completes
orchestrator.record_engagement_event(
    user_id, 
    EngagementEventType.STORY_COMPLETED
)
```

### 3. **Story Delivery Recording**
Always record when a story is delivered:

```python
# After successful story delivery
orchestrator.record_story_delivered()
```

## Architecture Considerations

### 1. **Singleton Pattern**
The MasterOrchestrationAgent should be a singleton to maintain state across requests:

```python
_orchestrator_instance = None

def get_orchestrator():
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = MasterOrchestrationAgent(ai_client)
    return _orchestrator_instance
```

### 2. **State Persistence**
For production, consider persisting timing state:
- Last story time per user
- Engagement events
- Journey progress

### 3. **Metrics Integration**
The system has placeholders for metrics. Integrate with your metrics system:
- Story timing intervals histogram
- Engagement levels gauge
- Override triggers counter

## Testing Integration

### Manual Testing Scenarios

1. **Highway Driving Test**
   - Set driving_complexity to VERY_LOW
   - Set engagement to 0.8
   - Expect: 3-4 minute intervals

2. **City Traffic Test**
   - Set driving_complexity to HIGH
   - Set traffic to "heavy"
   - Expect: 8-10 minute intervals

3. **POI Approach Test**
   - Set nearest_poi_distance to 1.5km
   - Expect: Immediate story trigger

## Configuration Options

### Timing Bounds
```python
MIN_INTERVAL_MINUTES = 1.5  # Never less than this
MAX_INTERVAL_MINUTES = 12.0  # Never more than this
```

### Base Timings by Phase
```python
DEPARTURE: 3.0 minutes
EARLY: 5.0 minutes  
CRUISE: 6.0 minutes
APPROACHING: 4.0 minutes
ARRIVAL: 2.5 minutes
```

### Multiplier Ranges
- Driving Complexity: 0.7x to 3.0x
- Engagement: 0.6x to 1.8x
- Passenger Type: 0.7x to 1.0x

## Troubleshooting

### Stories Not Triggering
1. Check if `check_story_opportunity()` is being called
2. Verify journey context data is complete
3. Check engagement tracker state
4. Look for "Story opportunity detected" in logs

### Too Frequent Stories
1. Verify `record_story_delivered()` is called
2. Check engagement level calculations
3. Review driving complexity assessment

### Missing Context Data
The system has fallbacks for missing data:
- Default timing: 5 minutes
- Default engagement: 0.5
- Default complexity: MODERATE

## Migration from Fixed Timing

1. Remove hardcoded `story_interval_minutes = 15`
2. Remove manual timing checks in story request handlers
3. Add periodic story opportunity checks
4. Start recording engagement events
5. Monitor and adjust multipliers as needed

## API Endpoints

- `POST /api/story-timing/check-story-opportunity` - Check if story should trigger
- `POST /api/story-timing/record-story-delivered` - Record story delivery
- `POST /api/story-timing/record-engagement-event` - Record user interaction
- `GET /api/story-timing/timing-status` - Get current timing state

## Future Enhancements

1. **Learning System**: Adjust base timings based on user preferences
2. **Mood Detection**: Incorporate sentiment analysis
3. **Traffic Prediction**: Pre-adjust timing for expected conditions
4. **Group Dynamics**: Different timing for multiple passengers
5. **Content-Based Timing**: Adjust based on story type/length