# Navigation Voice Integration

## Overview

The AI Road Trip Storyteller now includes **intelligent turn-by-turn voice navigation** that seamlessly integrates with the storytelling experience. This system orchestrates navigation instructions with ongoing narratives, ensuring driving safety while maintaining engagement.

## Architecture

### Components

1. **NavigationVoiceService** (`backend/app/services/navigation_voice_service.py`)
   - Processes Google Directions API route data into voice instructions
   - Generates multiple instruction variants (initial, reminder, prepare, immediate)
   - Handles SSML markup for clear pronunciation
   - Manages instruction timing based on speed and road type

2. **Master Orchestration Agent Integration**
   - Coordinates navigation voice with story playback
   - Implements audio ducking and pausing strategies
   - Maintains single voice interface for all interactions
   - Prioritizes safety-critical navigation over entertainment

3. **Audio Orchestration System**
   - Priority levels: CRITICAL > HIGH > MEDIUM > LOW
   - Actions: interrupt_all, pause_story, duck_all, wait_for_gap
   - Smooth transitions with configurable fade durations

### Navigation Priority Levels

```python
class NavigationPriority(Enum):
    CRITICAL = "critical"  # Immediate turns, exits (interrupts everything)
    HIGH = "high"         # Upcoming maneuvers (pauses stories)
    MEDIUM = "medium"     # Distance updates (ducks audio)
    LOW = "low"           # General guidance (waits for gaps)
```

## API Endpoints

### Start Navigation
```http
POST /api/navigation/start
{
  "route": {...},  // Google Directions route object
  "current_location": {"lat": 40.7128, "lng": -74.0060},
  "destination": {"lat": 40.7589, "lng": -73.9851},
  "navigation_preferences": {
    "voice_personality": "professional",
    "verbosity": "detailed",
    "audio_priority": "safety_first"
  }
}
```

### Update Navigation (Real-time position)
```http
POST /api/navigation/update
{
  "current_location": {"lat": 40.7150, "lng": -74.0058},
  "current_step_index": 0,
  "distance_to_next_maneuver": 1500,  // meters
  "time_to_next_maneuver": 120,       // seconds
  "current_speed": 50,                // km/h
  "is_on_highway": false,
  "story_playing": true,
  "audio_priority": "balanced"
}
```

Response includes:
- Navigation instruction text
- Audio URL for voice instruction
- Orchestration action (how to handle current audio)
- Next check interval

### Stop Navigation
```http
POST /api/navigation/stop
```

## Voice Instruction Types

### 1. Initial Announcement (2mi/0.5mi)
- "In 2 miles, take exit 42B"
- "In half a mile, turn left onto Main Street"
- Medium priority, doesn't interrupt stories

### 2. Reminder (1mi/0.25mi)
- "Exit 42B in 1 mile"
- "Turn left onto Main Street in a quarter mile"
- High priority, pauses stories

### 3. Prepare Instruction (500ft/165ft)
- "Prepare to turn left onto Main Street"
- "Take exit 42B on the right"
- Critical priority, interrupts all audio

### 4. Immediate (200ft/50ft)
- "Turn left now"
- "Take the exit now"
- Critical priority, maximum urgency

### 5. Confirmation (post-maneuver)
- "Continue on Main Street for 2 miles"
- Low priority, waits for audio gaps

## Distance Thresholds

### Highway Driving
- Initial: 3200m (2 miles)
- Reminder: 1600m (1 mile)
- Prepare: 800m (0.5 miles)
- Immediate: 200m (650 feet)

### City Driving
- Initial: 800m (0.5 miles)
- Reminder: 400m (0.25 miles)
- Prepare: 150m (500 feet)
- Immediate: 50m (165 feet)

## Audio Orchestration Rules

### Safety First Mode
- All navigation instructions interrupt stories
- Maximum volume boost for instructions
- No story resumption until safe

### Balanced Mode (Default)
- Critical/High priority interrupts stories
- Medium priority ducks audio
- Low priority waits for gaps
- Stories resume after instructions

### Story Focused Mode
- Only critical instructions interrupt
- Other instructions wait for natural pauses
- Minimal disruption to narrative flow

## Voice Personalities

### Professional Navigator (Default)
- Voice: en-US-Neural2-J
- Clear, authoritative male voice
- Neutral tone, precise pronunciation
- +2dB volume boost for clarity

### Emergency Mode
- Voice: en-US-Neural2-A
- Urgent female voice
- Faster speaking rate (1.2x)
- +5dB volume boost
- Higher pitch for attention

### User Preference
- Configurable voice selection
- Adjustable verbosity levels
- Timing preferences (early/normal/late)

## SSML Enhancements

The system uses Speech Synthesis Markup Language for:
- Emphasis on direction words (left, right, straight)
- Pauses before numbers for clarity
- Proper pronunciation of exit numbers
- Speed adjustments based on urgency

Example SSML:
```xml
<speak>
  <emphasis level="strong">Turn left</emphasis> 
  <break time="200ms"/>
  onto Main Street in 
  <say-as interpret-as="number">500</say-as> feet
</speak>
```

## Mobile Integration

The mobile app should:
1. Track device location continuously during navigation
2. Calculate distance/time to next maneuver
3. Call update endpoint every 5-30 seconds based on proximity
4. Handle audio playback with proper priorities
5. Implement audio ducking/pausing as directed

## Testing

Use the test endpoint in development:
```http
POST /api/navigation/simulate-position
{
  "current_location": {"lat": 40.7150, "lng": -74.0058},
  "distance_to_next_maneuver": 500,
  "current_speed": 50,
  "story_playing": true
}
```

## Future Enhancements

1. **Multi-language Support**
   - Localized navigation instructions
   - Regional pronunciation variants

2. **Contextual Awareness**
   - Weather-based instruction adjustments
   - Traffic condition integration
   - Time-of-day considerations

3. **Advanced Orchestration**
   - Predictive instruction scheduling
   - Natural story pause detection
   - Seamless narrative integration

4. **Personalization**
   - Learning user preferences
   - Adaptive verbosity
   - Custom instruction timing

## Implementation Status

✅ **Completed:**
- NavigationVoiceService core implementation
- Master Orchestration Agent integration
- API endpoints for navigation control
- SSML markup generation
- Distance-based instruction selection
- Audio orchestration rules

🚧 **In Progress:**
- Mobile app integration
- Real-time position tracking
- Audio ducking implementation

📋 **Planned:**
- Multi-language support
- Advanced context awareness
- Personalization features