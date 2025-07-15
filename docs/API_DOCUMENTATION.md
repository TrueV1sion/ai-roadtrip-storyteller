# AI Road Trip Storyteller API Documentation

Version: 1.0.0  
Base URL: `https://api.roadtripstoryteller.com`  
Last Updated: January 2025

## Table of Contents

1. [Authentication](#authentication)
2. [Core Endpoints](#core-endpoints)
3. [Voice Assistant](#voice-assistant)
4. [Journey Management](#journey-management)
5. [Booking & Reservations](#booking--reservations)
6. [Entertainment & Games](#entertainment--games)
7. [Personalization](#personalization)
8. [Real-time Features](#real-time-features)
9. [Mobile-Specific](#mobile-specific)
10. [Error Handling](#error-handling)
11. [Rate Limiting](#rate-limiting)
12. [WebSocket Events](#websocket-events)

## Authentication

### Overview
The API uses JWT (JSON Web Token) authentication. Tokens expire after 24 hours.

### Register
```http
POST /api/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "full_name": "John Doe"
}

Response 201:
{
  "id": 123,
  "email": "user@example.com",
  "full_name": "John Doe",
  "created_at": "2025-01-15T10:00:00Z"
}
```

### Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}

Response 200:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": 123,
    "email": "user@example.com",
    "full_name": "John Doe"
  }
}
```

### Two-Factor Authentication

#### Enable 2FA
```http
POST /api/auth/2fa/enable
Authorization: Bearer {token}

Response 200:
{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANS...",
  "backup_codes": [
    "12345678",
    "87654321",
    "11223344"
  ]
}
```

#### Verify 2FA
```http
POST /api/auth/2fa/verify
Authorization: Bearer {token}
Content-Type: application/json

{
  "code": "123456"
}

Response 200:
{
  "verified": true,
  "message": "2FA enabled successfully"
}
```

### Refresh Token
```http
POST /api/auth/refresh
Authorization: Bearer {token}

Response 200:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

## Core Endpoints

### Voice Assistant Interaction
The primary endpoint for all voice-based interactions.

```http
POST /api/voice-assistant/interact
Authorization: Bearer {token}
Content-Type: application/json

{
  "user_input": "I want to go to Disneyland",
  "context": {
    "origin": "San Francisco, CA",
    "destination": "Anaheim, CA",
    "current_location": {
      "lat": 37.7749,
      "lng": -122.4194
    },
    "preferences": {
      "voice_personality": "friendly_companion",
      "language": "en"
    }
  }
}

Response 200:
{
  "response": {
    "text": "Great choice! I'll help you plan an amazing trip to Disneyland...",
    "audio_url": "https://storage.googleapis.com/roadtrip-audio/response_123.mp3",
    "actions": [
      {
        "type": "show_route",
        "data": {
          "route_id": "route_456",
          "distance": "383 miles",
          "duration": "5 hours 45 minutes"
        }
      }
    ]
  },
  "metadata": {
    "processing_time": 1.23,
    "ai_model": "gemini-1.5-pro",
    "personality": "friendly_companion"
  }
}
```

### Get Directions
```http
POST /api/directions
Authorization: Bearer {token}
Content-Type: application/json

{
  "origin": "San Francisco, CA",
  "destination": "Los Angeles, CA",
  "waypoints": ["Monterey, CA", "Santa Barbara, CA"],
  "preferences": {
    "avoid_highways": false,
    "scenic_route": true,
    "prefer_fuel_efficient": true
  }
}

Response 200:
{
  "route": {
    "distance": "383 miles",
    "duration": "6 hours 30 minutes",
    "fuel_estimate": {
      "gallons": 12.5,
      "cost": "$65.00"
    },
    "waypoints": [
      {
        "location": "Monterey, CA",
        "arrival_time": "2025-01-15T12:30:00Z",
        "suggested_duration": "2 hours"
      }
    ],
    "polyline": "encoded_polyline_string",
    "scenic_highlights": [
      {
        "name": "Bixby Creek Bridge",
        "location": {"lat": 36.3714, "lng": -121.9033},
        "description": "Iconic bridge on Highway 1"
      }
    ]
  }
}
```

## Journey Management

### Create Journey
```http
POST /api/journey/create
Authorization: Bearer {token}
Content-Type: application/json

{
  "title": "California Coast Adventure",
  "origin": "San Francisco, CA",
  "destination": "San Diego, CA",
  "departure_date": "2025-02-01T09:00:00Z",
  "preferences": {
    "pace": "relaxed",
    "interests": ["beaches", "wildlife", "photography"],
    "budget": "moderate"
  }
}

Response 201:
{
  "journey_id": "journey_789",
  "title": "California Coast Adventure",
  "status": "planning",
  "created_at": "2025-01-15T10:00:00Z",
  "itinerary": {
    "days": [
      {
        "date": "2025-02-01",
        "segments": [
          {
            "type": "drive",
            "from": "San Francisco, CA",
            "to": "Santa Cruz, CA",
            "duration": "1.5 hours",
            "highlights": ["Half Moon Bay", "Pescadero Beach"]
          }
        ]
      }
    ]
  }
}
```

### Event Journey
Create journeys centered around events (concerts, sports, theme parks).

```http
POST /api/event-journey/create
Authorization: Bearer {token}
Content-Type: application/json

{
  "origin": "San Francisco, CA",
  "venue_name": "Hollywood Bowl",
  "event_type": "concert",
  "event_date": "2025-03-15T20:00:00Z",
  "preferences": {
    "arrival_buffer": 90,
    "include_parking": true,
    "pre_event_dining": true,
    "hotel_needed": true
  }
}

Response 201:
{
  "journey_id": "event_journey_123",
  "event_details": {
    "venue": "Hollywood Bowl",
    "event_type": "concert",
    "date": "2025-03-15T20:00:00Z"
  },
  "voice_personality": "music_enthusiast",
  "timeline": {
    "departure": "2025-03-15T13:00:00Z",
    "dinner_reservation": "2025-03-15T18:00:00Z",
    "arrival_at_venue": "2025-03-15T19:30:00Z"
  },
  "bookings": {
    "parking": {
      "location": "Hollywood Bowl Parking Lot B",
      "reserved": true,
      "cost": "$25.00"
    },
    "dinner": {
      "restaurant": "Musso & Frank Grill",
      "time": "18:00",
      "party_size": 2
    }
  }
}
```

### Family Journey
Specialized endpoint for family trips with children.

```http
POST /api/family-journey
Authorization: Bearer {token}
Content-Type: application/json

{
  "family_profile": {
    "adults": 2,
    "children": [
      {"age": 8, "interests": ["animals", "games"]},
      {"age": 12, "interests": ["technology", "sports"]}
    ]
  },
  "route": {
    "origin": "San Francisco, CA",
    "destination": "Disneyland, CA"
  },
  "preferences": {
    "pace": "relaxed",
    "meal_stops": "kid_friendly",
    "entertainment": "interactive"
  }
}

Response 200:
{
  "journey_id": "family_journey_456",
  "voice_personality": "mickey_mouse",
  "entertainment": {
    "games": ["I Spy", "20 Questions", "License Plate Game"],
    "stories": ["The History of Disneyland", "Walt Disney's Dream"],
    "trivia": {
      "categories": ["Disney", "California", "Animals"],
      "difficulty": "family"
    }
  },
  "recommended_stops": [
    {
      "name": "Casa de Fruta",
      "type": "rest_stop",
      "amenities": ["playground", "petting_zoo", "restaurant"],
      "duration": "45 minutes"
    }
  ]
}
```

## Booking & Reservations

### Search Hotels
```http
GET /api/booking/search?location=Santa+Barbara,CA&checkin=2025-02-15&checkout=2025-02-16&guests=2
Authorization: Bearer {token}

Response 200:
{
  "hotels": [
    {
      "id": "hotel_123",
      "name": "Beachside Inn",
      "rating": 4.5,
      "price_per_night": "$189.00",
      "amenities": ["pool", "parking", "breakfast"],
      "distance_from_route": "0.5 miles",
      "available_rooms": [
        {
          "type": "Ocean View King",
          "price": "$189.00",
          "cancellation": "free"
        }
      ]
    }
  ],
  "total_results": 25
}
```

### Make Reservation
```http
POST /api/booking/reserve
Authorization: Bearer {token}
Content-Type: application/json

{
  "hotel_id": "hotel_123",
  "room_type": "Ocean View King",
  "checkin": "2025-02-15",
  "checkout": "2025-02-16",
  "guests": {
    "adults": 2,
    "children": 0
  },
  "special_requests": "Late checkout if possible"
}

Response 201:
{
  "reservation_id": "res_789",
  "confirmation_number": "BK123456",
  "status": "confirmed",
  "hotel": {
    "name": "Beachside Inn",
    "address": "123 Ocean Ave, Santa Barbara, CA"
  },
  "total_cost": "$211.28",
  "commission_earned": "$21.13",
  "cancellation_policy": "Free cancellation until 24 hours before check-in"
}
```

### Restaurant Reservations
```http
POST /api/reservations/restaurant
Authorization: Bearer {token}
Content-Type: application/json

{
  "restaurant_id": "rest_456",
  "date": "2025-02-15",
  "time": "19:00",
  "party_size": 4,
  "special_requests": "Window table preferred"
}

Response 201:
{
  "reservation_id": "dining_123",
  "restaurant": "The French Laundry",
  "confirmation": "Confirmed for 4 at 7:00 PM",
  "special_notes": "Window table requested"
}
```

## Entertainment & Games

### Start Trivia Game
```http
POST /api/games/trivia/start
Authorization: Bearer {token}
Content-Type: application/json

{
  "location": {
    "lat": 34.0522,
    "lng": -118.2437
  },
  "difficulty": "medium",
  "category": "local_history",
  "players": ["Driver", "Passenger1"]
}

Response 200:
{
  "game_id": "trivia_game_123",
  "current_question": {
    "id": 1,
    "question": "What year was the Hollywood sign originally erected?",
    "options": ["1923", "1935", "1942", "1950"],
    "hint": "It was originally an advertisement"
  },
  "game_state": {
    "current_score": 0,
    "questions_remaining": 9,
    "time_limit": 30
  }
}
```

### Submit Answer
```http
POST /api/games/trivia/{game_id}/answer
Authorization: Bearer {token}
Content-Type: application/json

{
  "question_id": 1,
  "answer": "1923",
  "response_time": 12.5
}

Response 200:
{
  "correct": true,
  "explanation": "The Hollywood sign was erected in 1923 as an advertisement for a real estate development.",
  "points_earned": 100,
  "next_question": {
    "id": 2,
    "question": "Which famous pier is located in Santa Monica?",
    "options": ["Santa Monica Pier", "Venice Pier", "Malibu Pier", "Manhattan Pier"]
  }
}
```

### Scavenger Hunt
```http
POST /api/games/scavenger-hunt/create
Authorization: Bearer {token}
Content-Type: application/json

{
  "route_id": "route_456",
  "difficulty": "family",
  "duration": "full_trip"
}

Response 200:
{
  "hunt_id": "hunt_789",
  "items": [
    {
      "id": "item_1",
      "description": "Spot a red barn",
      "points": 10,
      "hint": "Common in agricultural areas"
    },
    {
      "id": "item_2",
      "description": "Find a historical marker",
      "points": 20,
      "bonus": "Take a photo for extra points"
    }
  ],
  "total_possible_points": 500
}
```

## Personalization

### Update Preferences
```http
PUT /api/users/preferences
Authorization: Bearer {token}
Content-Type: application/json

{
  "interests": ["nature", "history", "food", "music", "photography"],
  "voice_personality": "enthusiastic_guide",
  "language": "en",
  "accessibility": {
    "large_text": false,
    "voice_speed": "normal",
    "avoid_flashing": true
  },
  "travel_style": {
    "pace": "moderate",
    "spontaneity": "planned_with_flexibility",
    "budget": "moderate"
  }
}

Response 200:
{
  "updated": true,
  "preferences": {
    "interests": ["nature", "history", "food", "music", "photography"],
    "voice_personality": "enthusiastic_guide",
    "personalization_score": 0.85
  }
}
```

### Get Personalized Stories
```http
POST /api/personalized-story
Authorization: Bearer {token}
Content-Type: application/json

{
  "location": {
    "lat": 36.3714,
    "lng": -121.9033
  },
  "context": {
    "time_of_day": "sunset",
    "weather": "clear",
    "driving_speed": 45
  }
}

Response 200:
{
  "story": {
    "id": "story_123",
    "title": "The Legend of Bixby Bridge",
    "content": "As you approach this architectural marvel spanning the canyon...",
    "audio_url": "https://storage.googleapis.com/roadtrip-audio/story_123.mp3",
    "duration": "3:45",
    "category": "history",
    "personalization_match": 0.92
  },
  "related_content": [
    {
      "type": "photo_opportunity",
      "location": {"lat": 36.3715, "lng": -121.9030},
      "description": "Best viewpoint for sunset photos"
    }
  ]
}
```

## Real-time Features

### Navigation Updates
```http
POST /api/navigation/update
Authorization: Bearer {token}
Content-Type: application/json

{
  "location": {
    "lat": 34.0522,
    "lng": -118.2437
  },
  "speed": 65,
  "heading": 180,
  "altitude": 250
}

Response 200:
{
  "current_segment": {
    "road": "US-101 South",
    "next_exit": "Exit 42B - Sunset Blvd",
    "distance_to_exit": "2.3 miles"
  },
  "alerts": [
    {
      "type": "traffic",
      "severity": "moderate",
      "message": "Slow traffic ahead in 5 miles",
      "alternate_route": true
    }
  ],
  "nearby_poi": [
    {
      "name": "Griffith Observatory",
      "distance": "3.5 miles",
      "category": "attraction"
    }
  ]
}
```

### WebSocket Connection
```javascript
// Connect to real-time updates
const ws = new WebSocket('wss://api.roadtripstoryteller.com/ws');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'your_jwt_token'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'location_story':
      // New story available for current location
      playStory(data.story);
      break;
      
    case 'traffic_alert':
      // Real-time traffic update
      showTrafficAlert(data.alert);
      break;
      
    case 'booking_update':
      // Booking status changed
      updateBookingStatus(data.booking);
      break;
  }
};
```

## Mobile-Specific

### Offline Content Download
```http
POST /api/offline/download
Authorization: Bearer {token}
Content-Type: application/json

{
  "content_type": "route_package",
  "route_id": "route_456",
  "include": ["stories", "maps", "games"],
  "quality": "high"
}

Response 202:
{
  "download_id": "dl_123",
  "status": "preparing",
  "estimated_size": "245 MB",
  "items": {
    "stories": 45,
    "map_tiles": 1250,
    "games": 5
  },
  "download_url": "https://storage.googleapis.com/roadtrip-offline/dl_123.zip"
}
```

### Sync Offline Data
```http
POST /api/sync/offline
Authorization: Bearer {token}
Content-Type: application/json

{
  "last_sync": "2025-01-14T10:00:00Z",
  "device_id": "device_abc123",
  "data": {
    "game_scores": [
      {"game_id": "trivia_123", "score": 850}
    ],
    "saved_places": [
      {"lat": 34.0522, "lng": -118.2437, "note": "Great coffee shop"}
    ],
    "journey_progress": {
      "journey_id": "journey_789",
      "current_segment": 3,
      "miles_traveled": 125
    }
  }
}

Response 200:
{
  "sync_status": "success",
  "server_time": "2025-01-15T14:30:00Z",
  "updates": {
    "new_stories": 5,
    "reservation_changes": 1,
    "route_updates": 0
  }
}
```

## Rideshare Mode

### Enable Driver Mode
```http
POST /api/rideshare/driver/enable
Authorization: Bearer {token}

Response 200:
{
  "mode": "driver",
  "features_enabled": [
    "passenger_entertainment",
    "quick_facts",
    "ambient_music",
    "simplified_interface"
  ]
}
```

### Get Passenger Content
```http
GET /api/rideshare/content/suggestions?passenger_count=2&trip_duration=30
Authorization: Bearer {token}

Response 200:
{
  "suggestions": [
    {
      "type": "local_trivia",
      "content": "Did you know this neighborhood was once...",
      "duration": "2 minutes"
    },
    {
      "type": "playlist",
      "title": "Relaxing Evening Drive",
      "tracks": 12
    }
  ]
}
```

## Error Handling

All API errors follow a consistent format:

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The request body is missing required fields",
    "details": {
      "missing_fields": ["destination", "departure_date"]
    }
  },
  "request_id": "req_abc123",
  "timestamp": "2025-01-15T10:00:00Z"
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Invalid or expired token |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `INVALID_REQUEST` | 400 | Malformed request |
| `RATE_LIMITED` | 429 | Too many requests |
| `SERVER_ERROR` | 500 | Internal server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

## Rate Limiting

API requests are rate-limited to ensure fair usage:

- **Authenticated requests**: 1000 per hour
- **Voice assistant**: 500 per hour
- **Booking operations**: 100 per hour
- **Unauthenticated requests**: 100 per hour

Rate limit information is included in response headers:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 998
X-RateLimit-Reset: 1642267200
```

## WebSocket Events

### Event Types

#### Location-Based Story
```json
{
  "type": "location_story",
  "story": {
    "id": "story_123",
    "title": "The Golden Gate Bridge",
    "trigger_location": {"lat": 37.8199, "lng": -122.4783}
  }
}
```

#### Traffic Alert
```json
{
  "type": "traffic_alert",
  "alert": {
    "severity": "moderate",
    "location": {"lat": 34.0522, "lng": -118.2437},
    "message": "Accident ahead causing 15-minute delay",
    "alternate_available": true
  }
}
```

#### Booking Update
```json
{
  "type": "booking_update",
  "booking": {
    "id": "res_789",
    "type": "hotel",
    "status": "confirmed",
    "change": "Room upgraded to suite"
  }
}
```

#### Voice Personality Change
```json
{
  "type": "personality_change",
  "personality": {
    "name": "holiday_santa",
    "reason": "December detected",
    "greeting": "Ho ho ho! Let's make this journey magical!"
  }
}
```

## SDK Examples

### JavaScript/TypeScript
```typescript
import { RoadTripClient } from '@roadtrip/sdk';

const client = new RoadTripClient({
  apiKey: process.env.ROADTRIP_API_KEY,
  environment: 'production'
});

// Voice interaction
const response = await client.voiceAssistant.interact({
  input: "Find me a scenic route to Big Sur",
  context: {
    currentLocation: { lat: 37.7749, lng: -122.4194 }
  }
});

// Create journey
const journey = await client.journeys.create({
  origin: "San Francisco, CA",
  destination: "Los Angeles, CA",
  preferences: {
    scenic: true,
    pace: "relaxed"
  }
});
```

### Python
```python
from roadtrip import RoadTripClient

client = RoadTripClient(
    api_key=os.environ["ROADTRIP_API_KEY"]
)

# Get personalized story
story = client.stories.get_personalized(
    location={"lat": 34.0522, "lng": -118.2437},
    interests=["history", "movies"]
)

# Book hotel
reservation = client.bookings.create_hotel(
    hotel_id="hotel_123",
    checkin="2025-02-15",
    checkout="2025-02-16",
    guests=2
)
```

### Mobile (React Native)
```javascript
import { RoadTripMobile } from '@roadtrip/mobile-sdk';

// Initialize with offline support
const roadtrip = new RoadTripMobile({
  apiKey: 'your_api_key',
  enableOffline: true,
  cacheSize: 500 // MB
});

// Voice command with safety check
const handleVoiceCommand = async (command) => {
  if (await roadtrip.safety.isDrivingSafe()) {
    const response = await roadtrip.voice.process(command);
    return response;
  } else {
    return { 
      text: "Let's wait until it's safer to process that request",
      action: "defer"
    };
  }
};
```

## API Versioning

The API uses URL versioning. The current version is v1. When we release breaking changes, we'll introduce v2 while maintaining v1 for backward compatibility.

### Version Header
You can also specify the version via header:
```
X-API-Version: 1
```

## Support

- **Documentation**: https://docs.roadtripstoryteller.com
- **Status Page**: https://status.roadtripstoryteller.com
- **Support Email**: api-support@roadtripstoryteller.com
- **Developer Forum**: https://forum.roadtripstoryteller.com

## Changelog

### Version 1.0.0 (January 2025)
- Initial API release
- Voice assistant integration
- Journey management
- Booking system
- Real-time features
- Mobile offline support
- WebSocket events
- 20+ voice personalities
- Event-based journeys
- Family mode
- Rideshare mode