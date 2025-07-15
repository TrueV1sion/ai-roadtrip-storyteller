"""
API Examples and Documentation Enhancements
Provides detailed examples for common API operations
"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class APIExample(BaseModel):
    """Base model for API examples"""
    title: str
    description: str
    curl_example: str
    python_example: str
    javascript_example: str
    response_example: Dict[str, Any]


# Authentication Examples
AUTH_EXAMPLES = {
    "register": APIExample(
        title="User Registration",
        description="Register a new user account",
        curl_example="""
curl -X POST https://api.roadtripstoryteller.com/api/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "full_name": "John Doe"
  }'
""",
        python_example="""
import requests

response = requests.post(
    "https://api.roadtripstoryteller.com/api/auth/register",
    json={
        "email": "user@example.com",
        "password": "SecurePassword123!",
        "full_name": "John Doe"
    }
)

data = response.json()
print(f"User ID: {data['id']}")
""",
        javascript_example="""
const response = await fetch('https://api.roadtripstoryteller.com/api/auth/register', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        email: 'user@example.com',
        password: 'SecurePassword123!',
        full_name: 'John Doe'
    })
});

const data = await response.json();
console.log(`User ID: ${data.id}`);
""",
        response_example={
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "email": "user@example.com",
            "full_name": "John Doe",
            "created_at": "2024-01-01T00:00:00Z",
            "is_active": True,
            "is_premium": False
        }
    ),
    
    "login": APIExample(
        title="User Login",
        description="Authenticate and receive JWT tokens",
        curl_example="""
curl -X POST https://api.roadtripstoryteller.com/api/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }'
""",
        python_example="""
import requests

response = requests.post(
    "https://api.roadtripstoryteller.com/api/auth/login",
    json={
        "email": "user@example.com",
        "password": "SecurePassword123!"
    }
)

data = response.json()
access_token = data['access_token']
refresh_token = data['refresh_token']

# Use the access token for authenticated requests
headers = {"Authorization": f"Bearer {access_token}"}
""",
        javascript_example="""
const response = await fetch('https://api.roadtripstoryteller.com/api/auth/login', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        email: 'user@example.com',
        password: 'SecurePassword123!'
    })
});

const data = await response.json();
const { access_token, refresh_token } = data;

// Store tokens securely
localStorage.setItem('access_token', access_token);
localStorage.setItem('refresh_token', refresh_token);
""",
        response_example={
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "expires_in": 3600
        }
    )
}

# Story Generation Examples
STORY_EXAMPLES = {
    "generate_story": APIExample(
        title="Generate AI Story",
        description="Generate a story based on current location and context",
        curl_example="""
curl -X POST https://api.roadtripstoryteller.com/api/story/generate \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "latitude": 40.7128,
    "longitude": -74.0060,
    "story_type": "historical",
    "personality": "morgan_freeman",
    "include_local_facts": true
  }'
""",
        python_example="""
import requests

headers = {"Authorization": "Bearer YOUR_ACCESS_TOKEN"}

response = requests.post(
    "https://api.roadtripstoryteller.com/api/story/generate",
    headers=headers,
    json={
        "latitude": 40.7128,
        "longitude": -74.0060,
        "story_type": "historical",
        "personality": "morgan_freeman",
        "include_local_facts": True
    }
)

story = response.json()
print(f"Story: {story['content']}")
print(f"Audio URL: {story['audio_url']}")
""",
        javascript_example="""
const response = await fetch('https://api.roadtripstoryteller.com/api/story/generate', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer YOUR_ACCESS_TOKEN',
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        latitude: 40.7128,
        longitude: -74.0060,
        story_type: 'historical',
        personality: 'morgan_freeman',
        include_local_facts: true
    })
});

const story = await response.json();
console.log(`Story: ${story.content}`);

// Play the audio
const audio = new Audio(story.audio_url);
audio.play();
""",
        response_example={
            "id": "story_123456",
            "content": "As we approach the bustling streets of New York City, let me tell you about the remarkable history that unfolded right here...",
            "audio_url": "https://storage.roadtripstoryteller.com/audio/story_123456.mp3",
            "duration_seconds": 180,
            "location": {
                "name": "New York City",
                "state": "New York",
                "country": "USA"
            },
            "personality": "morgan_freeman",
            "created_at": "2024-01-01T00:00:00Z"
        }
    )
}

# Voice Assistant Examples
VOICE_EXAMPLES = {
    "voice_command": APIExample(
        title="Process Voice Command",
        description="Send voice command for processing",
        curl_example="""
curl -X POST https://api.roadtripstoryteller.com/api/voice/command \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
  -H "Content-Type: multipart/form-data" \\
  -F "audio=@voice_command.wav" \\
  -F "language=en-US"
""",
        python_example="""
import requests

headers = {"Authorization": "Bearer YOUR_ACCESS_TOKEN"}

with open("voice_command.wav", "rb") as audio_file:
    files = {"audio": audio_file}
    data = {"language": "en-US"}
    
    response = requests.post(
        "https://api.roadtripstoryteller.com/api/voice/command",
        headers=headers,
        files=files,
        data=data
    )

result = response.json()
print(f"Transcription: {result['transcription']}")
print(f"Intent: {result['intent']}")
print(f"Response: {result['response']}")
""",
        javascript_example="""
const formData = new FormData();
formData.append('audio', audioBlob, 'voice_command.wav');
formData.append('language', 'en-US');

const response = await fetch('https://api.roadtripstoryteller.com/api/voice/command', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer YOUR_ACCESS_TOKEN',
    },
    body: formData
});

const result = await response.json();
console.log(`Transcription: ${result.transcription}`);
console.log(`Intent: ${result.intent}`);
console.log(`Response: ${result.response}`);
""",
        response_example={
            "transcription": "Tell me about this area",
            "intent": "location_info",
            "confidence": 0.95,
            "response": "You're currently in Manhattan, New York City. Would you like to hear about the history, attractions, or restaurants nearby?",
            "audio_response_url": "https://storage.roadtripstoryteller.com/audio/response_123456.mp3",
            "context": {
                "location": "Manhattan, NY",
                "available_topics": ["history", "attractions", "restaurants"]
            }
        }
    )
}

# Booking Examples
BOOKING_EXAMPLES = {
    "search_hotels": APIExample(
        title="Search Hotels",
        description="Search for available hotels near a location",
        curl_example="""
curl -X GET "https://api.roadtripstoryteller.com/api/bookings/hotels/search?latitude=40.7128&longitude=-74.0060&radius=5&checkin=2024-06-01&checkout=2024-06-03" \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
""",
        python_example="""
import requests
from datetime import datetime, timedelta

headers = {"Authorization": "Bearer YOUR_ACCESS_TOKEN"}

params = {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "radius": 5,
    "checkin": datetime.now().strftime("%Y-%m-%d"),
    "checkout": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
}

response = requests.get(
    "https://api.roadtripstoryteller.com/api/bookings/hotels/search",
    headers=headers,
    params=params
)

hotels = response.json()
for hotel in hotels['results']:
    print(f"{hotel['name']} - ${hotel['price_per_night']}/night")
""",
        javascript_example="""
const params = new URLSearchParams({
    latitude: 40.7128,
    longitude: -74.0060,
    radius: 5,
    checkin: '2024-06-01',
    checkout: '2024-06-03'
});

const response = await fetch(
    `https://api.roadtripstoryteller.com/api/bookings/hotels/search?${params}`,
    {
        headers: {
            'Authorization': 'Bearer YOUR_ACCESS_TOKEN',
        }
    }
);

const hotels = await response.json();
hotels.results.forEach(hotel => {
    console.log(`${hotel.name} - $${hotel.price_per_night}/night`);
});
""",
        response_example={
            "results": [
                {
                    "id": "hotel_123",
                    "name": "Manhattan Luxury Hotel",
                    "address": "123 5th Avenue, New York, NY 10001",
                    "rating": 4.5,
                    "price_per_night": 299.99,
                    "amenities": ["WiFi", "Pool", "Gym", "Restaurant"],
                    "availability": True,
                    "images": [
                        "https://images.roadtripstoryteller.com/hotels/123/main.jpg"
                    ],
                    "distance_km": 0.5
                }
            ],
            "total_results": 15,
            "page": 1,
            "per_page": 10
        }
    )
}

# Trip Planning Examples
TRIP_EXAMPLES = {
    "create_trip": APIExample(
        title="Create New Trip",
        description="Plan a new road trip with multiple stops",
        curl_example="""
curl -X POST https://api.roadtripstoryteller.com/api/trips/create \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "East Coast Adventure",
    "start_location": {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "name": "New York City"
    },
    "end_location": {
        "latitude": 25.7617,
        "longitude": -80.1918,
        "name": "Miami"
    },
    "waypoints": [
        {
            "latitude": 39.9526,
            "longitude": -75.1652,
            "name": "Philadelphia"
        },
        {
            "latitude": 38.9072,
            "longitude": -77.0369,
            "name": "Washington DC"
        }
    ],
    "start_date": "2024-06-01",
    "preferences": {
        "story_types": ["historical", "cultural"],
        "personality": "david_attenborough",
        "include_attractions": true,
        "include_restaurants": true
    }
  }'
""",
        python_example="""
import requests
from datetime import datetime

headers = {"Authorization": "Bearer YOUR_ACCESS_TOKEN"}

trip_data = {
    "name": "East Coast Adventure",
    "start_location": {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "name": "New York City"
    },
    "end_location": {
        "latitude": 25.7617,
        "longitude": -80.1918,
        "name": "Miami"
    },
    "waypoints": [
        {
            "latitude": 39.9526,
            "longitude": -75.1652,
            "name": "Philadelphia"
        },
        {
            "latitude": 38.9072,
            "longitude": -77.0369,
            "name": "Washington DC"
        }
    ],
    "start_date": "2024-06-01",
    "preferences": {
        "story_types": ["historical", "cultural"],
        "personality": "david_attenborough",
        "include_attractions": True,
        "include_restaurants": True
    }
}

response = requests.post(
    "https://api.roadtripstoryteller.com/api/trips/create",
    headers=headers,
    json=trip_data
)

trip = response.json()
print(f"Trip ID: {trip['id']}")
print(f"Total Distance: {trip['total_distance_km']} km")
print(f"Estimated Duration: {trip['estimated_duration_hours']} hours")
""",
        javascript_example="""
const tripData = {
    name: "East Coast Adventure",
    start_location: {
        latitude: 40.7128,
        longitude: -74.0060,
        name: "New York City"
    },
    end_location: {
        latitude: 25.7617,
        longitude: -80.1918,
        name: "Miami"
    },
    waypoints: [
        {
            latitude: 39.9526,
            longitude: -75.1652,
            name: "Philadelphia"
        },
        {
            latitude: 38.9072,
            longitude: -77.0369,
            name: "Washington DC"
        }
    ],
    start_date: "2024-06-01",
    preferences: {
        story_types: ["historical", "cultural"],
        personality: "david_attenborough",
        include_attractions: true,
        include_restaurants: true
    }
};

const response = await fetch('https://api.roadtripstoryteller.com/api/trips/create', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer YOUR_ACCESS_TOKEN',
        'Content-Type': 'application/json',
    },
    body: JSON.stringify(tripData)
});

const trip = await response.json();
console.log(`Trip ID: ${trip.id}`);
console.log(`Total Distance: ${trip.total_distance_km} km`);
""",
        response_example={
            "id": "trip_789012",
            "name": "East Coast Adventure",
            "status": "planned",
            "total_distance_km": 2092.5,
            "estimated_duration_hours": 22.5,
            "route": {
                "polyline": "encoded_polyline_string",
                "segments": [
                    {
                        "from": "New York City",
                        "to": "Philadelphia",
                        "distance_km": 152.4,
                        "duration_hours": 2.5
                    }
                ]
            },
            "suggested_stops": [
                {
                    "name": "Liberty Bell",
                    "type": "attraction",
                    "location": {
                        "latitude": 39.9496,
                        "longitude": -75.1503
                    },
                    "description": "Historic symbol of American independence"
                }
            ],
            "created_at": "2024-01-01T00:00:00Z"
        }
    )
}


def get_api_examples() -> Dict[str, Dict[str, APIExample]]:
    """
    Get all API examples organized by category
    """
    return {
        "Authentication": AUTH_EXAMPLES,
        "Story Generation": STORY_EXAMPLES,
        "Voice Assistant": VOICE_EXAMPLES,
        "Bookings": BOOKING_EXAMPLES,
        "Trip Planning": TRIP_EXAMPLES
    }


def generate_example_markdown(category: str, examples: Dict[str, APIExample]) -> str:
    """
    Generate markdown documentation for API examples
    """
    markdown = f"# {category} Examples\n\n"
    
    for key, example in examples.items():
        markdown += f"## {example.title}\n\n"
        markdown += f"{example.description}\n\n"
        
        markdown += "### cURL Example\n```bash\n"
        markdown += example.curl_example.strip()
        markdown += "\n```\n\n"
        
        markdown += "### Python Example\n```python\n"
        markdown += example.python_example.strip()
        markdown += "\n```\n\n"
        
        markdown += "### JavaScript Example\n```javascript\n"
        markdown += example.javascript_example.strip()
        markdown += "\n```\n\n"
        
        markdown += "### Response Example\n```json\n"
        import json
        markdown += json.dumps(example.response_example, indent=2)
        markdown += "\n```\n\n"
    
    return markdown