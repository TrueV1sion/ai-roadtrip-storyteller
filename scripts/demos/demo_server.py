#!/usr/bin/env python3
"""
Simple demo server for AI Road Trip Storyteller.
Uses only Python standard library - no external dependencies.
"""
import http.server
import socketserver
import json
import os
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import random

PORT = 8000

class RoadTripHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler for Road Trip API demo."""
    
    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.get_home_page().encode())
            
        elif parsed_path.path == '/health':
            self.send_json_response({
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0",
                "mode": "demo"
            })
            
        elif parsed_path.path == '/health/detailed':
            self.send_json_response({
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0",
                "environment": "demo",
                "services": {
                    "database": {"status": "mock", "message": "Using in-memory database"},
                    "redis": {"status": "mock", "message": "Using in-memory cache"},
                    "ai": {"status": "mock", "message": "Using mock AI responses"}
                },
                "features": {
                    "voice_personalities": 20,
                    "booking_integrations": 7,
                    "ai_agents": 5
                }
            })
            
        elif parsed_path.path == '/api/voice-assistant/demo':
            self.handle_voice_demo()
            
        else:
            self.send_error(404, "Endpoint not found")
    
    def do_POST(self):
        """Handle POST requests."""
        if self.path == '/api/voice-assistant/interact':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                response = self.generate_voice_response(data)
                self.send_json_response(response)
            except Exception as e:
                self.send_error(400, f"Invalid request: {str(e)}")
        else:
            self.send_error(404, "Endpoint not found")
    
    def send_json_response(self, data):
        """Send JSON response."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
    
    def handle_voice_demo(self):
        """Handle voice assistant demo."""
        demos = [
            {
                "input": "I want to go to Disneyland",
                "personality": "Mickey Mouse Guide",
                "response": "Oh boy! Let's make your Disneyland dreams come true! Ha-ha!",
                "story": "Did you know Walt Disney created Disneyland in just 365 days?",
                "bookings": ["Blue Bayou Restaurant", "Grand Californian Hotel"]
            },
            {
                "input": "Plan a road trip to the Grand Canyon",
                "personality": "Desert Explorer",
                "response": "Partner, let's explore one of nature's greatest wonders!",
                "story": "The Grand Canyon is 277 river miles long and up to 18 miles wide.",
                "bookings": ["Desert View Campground", "El Tovar Hotel"]
            }
        ]
        
        demo = random.choice(demos)
        self.send_json_response({
            "demo": True,
            "example_input": demo["input"],
            "voice_personality": demo["personality"],
            "ai_response": demo["response"],
            "story_snippet": demo["story"],
            "booking_opportunities": demo["bookings"]
        })
    
    def generate_voice_response(self, data):
        """Generate mock voice assistant response."""
        user_input = data.get('user_input', '')
        context = data.get('context', {})
        
        # Detect intent
        intent = "unknown"
        if any(word in user_input.lower() for word in ['disney', 'disneyland', 'mickey']):
            intent = "disney_trip"
            personality = "Mickey Mouse Guide"
            response = "Oh boy! Let's plan your magical Disney adventure! Ha-ha!"
        elif any(word in user_input.lower() for word in ['concert', 'music', 'festival']):
            intent = "event_trip"
            personality = "Rock DJ"
            response = "Alright! Let's rock this road trip to your concert!"
        else:
            intent = "general_trip"
            personality = "Friendly Navigator"
            response = "I'd be happy to help plan your journey!"
        
        return {
            "status": "success",
            "intent": intent,
            "voice_personality": {
                "name": personality,
                "auto_selected": True,
                "reason": f"Selected based on: {intent}"
            },
            "response": response,
            "story": {
                "snippet": "Here's an interesting fact about your destination...",
                "full_story": "This would be a longer, engaging story."
            },
            "bookings": {
                "available": True,
                "suggestions": [
                    {"type": "restaurant", "name": "Local Favorite Restaurant"},
                    {"type": "hotel", "name": "Comfort Inn"}
                ]
            },
            "metadata": {
                "processing_time_ms": random.randint(50, 200),
                "ai_model": "mock-mode",
                "cache_hit": False
            }
        }
    
    def get_home_page(self):
        """Generate home page HTML."""
        return '''
<!DOCTYPE html>
<html>
<head>
    <title>AI Road Trip Storyteller - Demo</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; }
        .endpoint { background: #f0f0f0; padding: 10px; margin: 10px 0; border-radius: 5px; font-family: monospace; }
        .feature { margin: 20px 0; padding: 15px; border-left: 4px solid #007AFF; background: #f8f9fa; }
        button { background: #007AFF; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin: 5px; }
        button:hover { background: #0051D5; }
        #response { margin-top: 20px; padding: 15px; background: #f0f0f0; border-radius: 5px; white-space: pre-wrap; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚗 AI Road Trip Storyteller - Demo Server</h1>
        
        <p>Welcome to the demo server! This is running in mock mode without external dependencies.</p>
        
        <h2>Available Endpoints:</h2>
        <div class="endpoint">GET /health - Basic health check</div>
        <div class="endpoint">GET /health/detailed - Detailed system status</div>
        <div class="endpoint">GET /api/voice-assistant/demo - Voice assistant demo</div>
        <div class="endpoint">POST /api/voice-assistant/interact - Interactive voice endpoint</div>
        
        <h2>Key Features:</h2>
        <div class="feature">
            <strong>🎭 20+ Voice Personalities</strong><br>
            From Mickey Mouse to Rock DJ, personalities auto-select based on your destination
        </div>
        <div class="feature">
            <strong>🤖 5 Specialized AI Agents</strong><br>
            Story Generation, Booking, Navigation, Context Awareness, and Local Expert
        </div>
        <div class="feature">
            <strong>📱 Booking Integrations</strong><br>
            OpenTable, Recreation.gov, Ticketmaster, and more
        </div>
        
        <h2>Try the Demo:</h2>
        <button onclick="testHealth()">Test Health Check</button>
        <button onclick="testVoiceDemo()">Test Voice Demo</button>
        <button onclick="testDisneyTrip()">Plan Disney Trip</button>
        <button onclick="testConcertTrip()">Plan Concert Trip</button>
        
        <div id="response"></div>
    </div>
    
    <script>
        function showResponse(data) {
            document.getElementById('response').textContent = JSON.stringify(data, null, 2);
        }
        
        async function testHealth() {
            const response = await fetch('/health/detailed');
            const data = await response.json();
            showResponse(data);
        }
        
        async function testVoiceDemo() {
            const response = await fetch('/api/voice-assistant/demo');
            const data = await response.json();
            showResponse(data);
        }
        
        async function testDisneyTrip() {
            const response = await fetch('/api/voice-assistant/interact', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    user_input: "I want to take my family to Disneyland",
                    context: {origin: "San Francisco, CA"}
                })
            });
            const data = await response.json();
            showResponse(data);
        }
        
        async function testConcertTrip() {
            const response = await fetch('/api/voice-assistant/interact', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    user_input: "Planning a trip to a music festival",
                    context: {origin: "Los Angeles, CA"}
                })
            });
            const data = await response.json();
            showResponse(data);
        }
    </script>
</body>
</html>
'''

def main():
    """Start the demo server."""
    print("\n" + "="*60)
    print("🚗 AI Road Trip Storyteller - Demo Server")
    print("="*60)
    print("\nStarting demo server (no dependencies required)...")
    
    # Create simple HTTP server
    with socketserver.TCPServer(("", PORT), RoadTripHandler) as httpd:
        print(f"\n✅ Server running at: http://localhost:{PORT}")
        print("\nAvailable endpoints:")
        print("  - Home page with demo UI: http://localhost:8000")
        print("  - Health check: http://localhost:8000/health")
        print("  - Detailed health: http://localhost:8000/health/detailed")
        print("  - Voice demo: http://localhost:8000/api/voice-assistant/demo")
        print("\nPress Ctrl+C to stop the server\n")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nServer stopped.")

if __name__ == "__main__":
    main()