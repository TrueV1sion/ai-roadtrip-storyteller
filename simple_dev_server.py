#!/usr/bin/env python3
"""
Simple Development Server for AI Road Trip Storyteller
Minimal dependencies, mock mode for quick preview
"""

import sys
import os
sys.path.insert(0, 'backend')

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
from datetime import datetime
import random

# Create minimal FastAPI app
app = FastAPI(
    title="AI Road Trip Storyteller - Dev Preview",
    description="Development preview with mock data",
    version="1.0.0"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock data
MOCK_STORIES = [
    "As you drive through the misty mountains, the ancient spirits whisper tales of gold miners who once walked these paths...",
    "The road curves ahead, revealing a hidden valley where legends say a magical spring grants wishes to weary travelers...",
    "Your journey takes you past the old lighthouse, where the keeper's ghost still lights the way for lost souls..."
]

MOCK_VOICES = [
    {"id": "morgan_freeman", "name": "Morgan Freeman", "description": "Wise narrator"},
    {"id": "david_attenborough", "name": "David Attenborough", "description": "Nature documentarian"},
    {"id": "storyteller", "name": "Classic Storyteller", "description": "Warm, engaging voice"}
]

# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
        <head>
            <title>AI Road Trip Storyteller - Dev Preview</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
                .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                h1 { color: #333; }
                .endpoint { background: #f0f0f0; padding: 10px; margin: 10px 0; border-radius: 5px; font-family: monospace; }
                .method { color: #007bff; font-weight: bold; }
                a { color: #007bff; text-decoration: none; }
                a:hover { text-decoration: underline; }
                .status { color: #28a745; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚗 AI Road Trip Storyteller - Development Preview</h1>
                <p class="status">✅ Server is running in mock mode</p>
                
                <h2>Available Endpoints:</h2>
                
                <div class="endpoint">
                    <span class="method">GET</span> <a href="/docs">/docs</a> - Interactive API Documentation
                </div>
                
                <div class="endpoint">
                    <span class="method">GET</span> <a href="/health">/health</a> - Health Check
                </div>
                
                <div class="endpoint">
                    <span class="method">GET</span> <a href="/api/v1/stories/generate">/api/v1/stories/generate</a> - Generate Story (Mock)
                </div>
                
                <div class="endpoint">
                    <span class="method">GET</span> <a href="/api/v1/voices">/api/v1/voices</a> - List Voice Personalities
                </div>
                
                <h2>Development Notes:</h2>
                <ul>
                    <li>This is a mock server for development preview</li>
                    <li>No external APIs or databases required</li>
                    <li>All responses use mock data</li>
                    <li>Perfect for UI development and testing</li>
                </ul>
                
                <h2>Mobile App Connection:</h2>
                <p>Set your mobile app's API URL to: <code>http://localhost:8000</code></p>
            </div>
        </body>
    </html>
    """

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "mode": "development_mock"
    }

# Generate story endpoint
@app.get("/api/v1/stories/generate")
async def generate_story(lat: float = 37.7749, lng: float = -122.4194):
    return {
        "story": random.choice(MOCK_STORIES),
        "location": {"latitude": lat, "longitude": lng},
        "duration": random.randint(30, 90),
        "voice_id": "morgan_freeman",
        "timestamp": datetime.now().isoformat()
    }

# Voice personalities
@app.get("/api/v1/voices")
async def list_voices():
    return {"voices": MOCK_VOICES}

# Mock authentication
@app.post("/api/v1/auth/login")
async def mock_login(email: str = "demo@example.com", password: str = "demo"):
    return {
        "access_token": "mock-jwt-token-12345",
        "token_type": "bearer",
        "user": {
            "id": 1,
            "email": email,
            "name": "Demo User"
        }
    }

# Mock user profile
@app.get("/api/v1/users/me")
async def get_current_user():
    return {
        "id": 1,
        "email": "demo@example.com",
        "name": "Demo User",
        "preferences": {
            "voice_id": "morgan_freeman",
            "story_length": "medium",
            "interests": ["history", "nature", "mystery"]
        }
    }

# Mock bookings
@app.get("/api/v1/bookings/search")
async def search_bookings(query: str = "hotel"):
    return {
        "results": [
            {
                "id": "1",
                "name": "Grand Hotel",
                "type": "accommodation",
                "price": "$150/night",
                "rating": 4.5
            },
            {
                "id": "2", 
                "name": "Cozy Inn",
                "type": "accommodation",
                "price": "$80/night",
                "rating": 4.2
            }
        ]
    }

# Mock navigation
@app.post("/api/v1/navigation/route")
async def get_route():
    return {
        "route": {
            "distance": "125 miles",
            "duration": "2 hours 15 minutes",
            "waypoints": [
                {"name": "Start", "lat": 37.7749, "lng": -122.4194},
                {"name": "Scenic Overlook", "lat": 37.8267, "lng": -122.4233},
                {"name": "Destination", "lat": 37.8716, "lng": -122.2727}
            ]
        }
    }

if __name__ == "__main__":
    print("\n🚗 AI Road Trip Storyteller - Simple Dev Server")
    print("=" * 50)
    print("✅ Starting server with mock data...")
    print("\nAccess points:")
    print("  • Main page:    http://localhost:8000")
    print("  • API Docs:     http://localhost:8000/docs") 
    print("  • Health Check: http://localhost:8000/health")
    print("\n✨ No configuration required - using mock data!")
    print("=" * 50)
    print("\nPress Ctrl+C to stop...\n")
    
    # Run the server
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)