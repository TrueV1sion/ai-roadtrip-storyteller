# API Quick Reference Guide

## Authentication Headers
```
Authorization: Bearer {your_jwt_token}
Content-Type: application/json
```

## Common Response Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `429` - Rate Limited
- `500` - Server Error

## Essential Endpoints

### 🎤 Voice Assistant
```http
POST /api/voice-assistant/interact
{
  "user_input": "string",
  "context": {
    "origin": "string",
    "destination": "string",
    "current_location": {"lat": number, "lng": number}
  }
}
```

### 🗺️ Directions
```http
POST /api/directions
{
  "origin": "string",
  "destination": "string",
  "waypoints": ["string"],
  "preferences": {
    "scenic_route": boolean,
    "avoid_highways": boolean
  }
}
```

### 🏨 Hotel Search
```http
GET /api/booking/search?location={city}&checkin={date}&checkout={date}&guests={number}
```

### 🎮 Start Game
```http
POST /api/games/trivia/start
{
  "location": {"lat": number, "lng": number},
  "difficulty": "easy|medium|hard"
}
```

### 📖 Get Story
```http
POST /api/personalized-story
{
  "location": {"lat": number, "lng": number},
  "interests": ["string"]
}
```

### 🎫 Event Journey
```http
POST /api/event-journey/create
{
  "origin": "string",
  "venue_name": "string",
  "event_type": "string",
  "event_date": "ISO 8601 datetime"
}
```

### 👨‍👩‍👧‍👦 Family Journey
```http
POST /api/family-journey
{
  "family_profile": {
    "adults": number,
    "children": [{"age": number, "interests": ["string"]}]
  },
  "route": {
    "origin": "string",
    "destination": "string"
  }
}
```

### 🚗 Rideshare Mode
```http
POST /api/rideshare/driver/enable
GET /api/rideshare/content/suggestions?passenger_count={number}
```

### 📱 Offline Download
```http
POST /api/offline/download
{
  "content_type": "route_package",
  "route_id": "string",
  "include": ["stories", "maps", "games"]
}
```

### 🔄 Sync Data
```http
POST /api/sync/offline
{
  "last_sync": "ISO 8601 datetime",
  "data": {
    "game_scores": [],
    "saved_places": [],
    "journey_progress": {}
  }
}
```

## WebSocket Events

### Connection
```javascript
const ws = new WebSocket('wss://api.roadtripstoryteller.com/ws');
ws.send(JSON.stringify({type: 'auth', token: 'your_token'}));
```

### Event Types
- `location_story` - New story for current location
- `traffic_alert` - Real-time traffic update
- `booking_update` - Booking status change
- `personality_change` - Voice personality switched

## Rate Limits
| Endpoint Type | Limit |
|--------------|-------|
| Voice Assistant | 500/hour |
| General API | 1000/hour |
| Booking | 100/hour |
| WebSocket | 1 connection |

## Error Response Format
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": {}
  },
  "request_id": "req_abc123"
}
```

## Environment URLs
- **Production**: `https://api.roadtripstoryteller.com`
- **Staging**: `https://staging-api.roadtripstoryteller.com`
- **Development**: `http://localhost:8000`

## SDK Installation

### JavaScript/Node.js
```bash
npm install @roadtrip/sdk
```

### Python
```bash
pip install roadtrip-sdk
```

### React Native
```bash
npm install @roadtrip/mobile-sdk
```

## Quick Examples

### Get Route with Stories
```javascript
// 1. Get directions
const route = await client.directions.create({
  origin: "San Francisco, CA",
  destination: "Los Angeles, CA"
});

// 2. Get stories along route
const stories = await client.stories.getForRoute(route.id);

// 3. Start playing first story
await client.audio.play(stories[0].audio_url);
```

### Complete Hotel Booking
```python
# Search hotels
hotels = client.bookings.search_hotels(
    location="Santa Barbara, CA",
    checkin="2025-02-15",
    guests=2
)

# Book first available
if hotels:
    reservation = client.bookings.reserve(
        hotel_id=hotels[0]["id"],
        room_type=hotels[0]["rooms"][0]["type"]
    )
```

### Handle Voice Commands
```javascript
// React Native with safety
const processVoiceCommand = async (audioData) => {
  const context = await getLocationContext();
  
  if (context.speed > 70) {
    // Defer complex operations at high speed
    return { deferred: true };
  }
  
  return await roadtrip.voice.process({
    audio: audioData,
    context: context
  });
};
```

## Testing

### Test Credentials
```
Email: demo@roadtripstoryteller.com
Password: DemoUser123!
API Key: demo_api_key_123
```

### Mock Mode
Add header for mock responses:
```
X-Mock-Mode: true
```

## Support Contacts
- **API Issues**: api-support@roadtripstoryteller.com
- **Status Page**: https://status.roadtripstoryteller.com
- **Documentation**: https://docs.roadtripstoryteller.com