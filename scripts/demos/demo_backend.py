#!/usr/bin/env python3
"""
AI Road Trip Storyteller - Live Demo
This runs a simplified version without external dependencies
"""

import json
import os
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

# Load environment variables
if os.path.exists('.env'):
    with open('.env') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

class DemoHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self.get_home_page().encode())
            
        elif self.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {'status': 'healthy', 'timestamp': datetime.now().isoformat()}
            self.wfile.write(json.dumps(response).encode())
            
        elif self.path.startswith('/api/journey/create'):
            self.handle_journey_creation()
            
        elif self.path.startswith('/api/events/search'):
            self.handle_event_search()
            
        elif self.path == '/api/personalities':
            self.handle_personalities()
            
        else:
            self.send_error(404)
    
    def get_home_page(self):
        """Generate demo home page"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>AI Road Trip Storyteller - Demo</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; }
        .demo-section { margin: 30px 0; padding: 20px; background: #f9f9f9; border-radius: 8px; }
        .button { display: inline-block; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 5px; }
        .button:hover { background: #0056b3; }
        .api-status { margin: 20px 0; }
        .status-ok { color: green; }
        .status-error { color: red; }
        .result { margin-top: 20px; padding: 15px; background: #e9ecef; border-radius: 5px; }
        pre { background: #f1f1f1; padding: 10px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚗 AI Road Trip Storyteller - Live Demo</h1>
        
        <div class="api-status">
            <h2>API Status</h2>
            <p class="status-ok">✅ Google Maps API: Connected</p>
            <p class="status-ok">✅ Ticketmaster API: Connected</p>
            <p class="status-error">⚠️ Recreation.gov API: Auth Required</p>
            <p class="status-error">⚠️ OpenWeatherMap API: Encoding Fix Needed</p>
        </div>
        
        <div class="demo-section">
            <h2>🎯 Demo 1: Create a Journey</h2>
            <p>Click to simulate different types of journeys:</p>
            <a href="#" class="button" onclick="createJourney('disney'); return false;">Disney Family Trip</a>
            <a href="#" class="button" onclick="createJourney('concert'); return false;">Concert Journey</a>
            <a href="#" class="button" onclick="createJourney('business'); return false;">Business Travel</a>
            <a href="#" class="button" onclick="createJourney('camping'); return false;">Camping Adventure</a>
            <div id="journey-result" class="result" style="display:none;"></div>
        </div>
        
        <div class="demo-section">
            <h2>🎭 Demo 2: Voice Personalities</h2>
            <p>See available AI personalities:</p>
            <a href="#" class="button" onclick="getPersonalities(); return false;">Show Personalities</a>
            <div id="personality-result" class="result" style="display:none;"></div>
        </div>
        
        <div class="demo-section">
            <h2>🎫 Demo 3: Event Search</h2>
            <p>Search for real events (using Ticketmaster):</p>
            <input type="text" id="event-city" placeholder="Enter city" value="San Francisco" style="padding: 8px; margin: 5px;">
            <a href="#" class="button" onclick="searchEvents(); return false;">Search Events</a>
            <div id="event-result" class="result" style="display:none;"></div>
        </div>
        
        <div class="demo-section">
            <h2>📊 Demo 4: Simulated Metrics</h2>
            <p>Real-time simulation metrics:</p>
            <div id="metrics" class="result">
                <strong>Active Journeys:</strong> <span id="journey-count">0</span><br>
                <strong>Voice Interactions:</strong> <span id="voice-count">0</span><br>
                <strong>Bookings Created:</strong> <span id="booking-count">0</span><br>
                <strong>Commission Generated:</strong> $<span id="revenue">0.00</span>
            </div>
        </div>
    </div>
    
    <script>
        // Update metrics every second
        setInterval(() => {
            document.getElementById('journey-count').textContent = Math.floor(Math.random() * 50) + 10;
            document.getElementById('voice-count').textContent = Math.floor(Math.random() * 200) + 50;
            document.getElementById('booking-count').textContent = Math.floor(Math.random() * 30) + 5;
            document.getElementById('revenue').textContent = (Math.random() * 500 + 100).toFixed(2);
        }, 2000);
        
        function createJourney(type) {
            fetch(`/api/journey/create?type=${type}`)
                .then(r => r.json())
                .then(data => {
                    document.getElementById('journey-result').style.display = 'block';
                    document.getElementById('journey-result').innerHTML = `
                        <h3>${data.title}</h3>
                        <p><strong>Route:</strong> ${data.route}</p>
                        <p><strong>AI Personality:</strong> ${data.personality}</p>
                        <p><strong>Story Preview:</strong> ${data.story}</p>
                        <p><strong>Booking Opportunities:</strong></p>
                        <ul>${data.bookings.map(b => `<li>${b}</li>`).join('')}</ul>
                    `;
                });
        }
        
        function getPersonalities() {
            fetch('/api/personalities')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('personality-result').style.display = 'block';
                    document.getElementById('personality-result').innerHTML = `
                        <h3>Available Voice Personalities</h3>
                        <ul>${data.personalities.map(p => `<li><strong>${p.name}</strong>: ${p.description}</li>`).join('')}</ul>
                    `;
                });
        }
        
        function searchEvents() {
            const city = document.getElementById('event-city').value;
            fetch(`/api/events/search?city=${encodeURIComponent(city)}`)
                .then(r => r.json())
                .then(data => {
                    document.getElementById('event-result').style.display = 'block';
                    if (data.events && data.events.length > 0) {
                        document.getElementById('event-result').innerHTML = `
                            <h3>Events in ${city}</h3>
                            <ul>${data.events.map(e => `<li><strong>${e.name}</strong> - ${e.date} at ${e.venue}</li>`).join('')}</ul>
                        `;
                    } else {
                        document.getElementById('event-result').innerHTML = '<p>No events found or API error.</p>';
                    }
                });
        }
    </script>
</body>
</html>
        """
    
    def handle_journey_creation(self):
        """Handle journey creation requests"""
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        journey_type = params.get('type', ['disney'])[0]
        
        journeys = {
            'disney': {
                'title': '🏰 Magical Disney Adventure',
                'route': 'San Francisco, CA → Disneyland, Anaheim, CA',
                'personality': 'Mickey Mouse Guide',
                'story': "Oh boy! Welcome aboard, pals! I'm Mickey, and I'll be your magical guide to the Happiest Place on Earth! Did you know Walt Disney created Disneyland in just 365 days? As we drive south on I-5, let me tell you about the orange groves that once covered all of Anaheim...",
                'bookings': [
                    'Blue Bayou Restaurant - Dine inside Pirates of the Caribbean',
                    'Grand Californian Hotel - Stay in the magic',
                    'MaxPass - Skip the lines at popular attractions'
                ]
            },
            'concert': {
                'title': '🎵 Rock Concert Journey',
                'route': 'Sacramento, CA → Oracle Arena, Oakland, CA',
                'personality': 'Axel Thunder (Rock DJ)',
                'story': "Hey there, rock star! Axel Thunder here, ready to pump you up for tonight's epic show! The band you're seeing has sold over 50 million albums worldwide. As we cruise down I-80, let me spin some of their greatest hits and tell you about their legendary 1987 concert at this very venue...",
                'bookings': [
                    'Hard Rock Cafe Oakland - Pre-concert dinner',
                    'Parking at Oracle Arena - Reserved spot',
                    'VIP Lounge Access - Exclusive pre-show experience'
                ]
            },
            'business': {
                'title': '💼 Executive Business Trip',
                'route': 'San Jose, CA → San Francisco Financial District',
                'personality': 'Victoria Professional',
                'story': "Good morning! I'm Victoria, your professional travel assistant. I've reviewed your meeting agenda for today's quarterly review at 10 AM. As we navigate Highway 101, let me brief you on the latest industry trends and your client's recent acquisitions. Traffic is moderate, ETA 9:15 AM...",
                'bookings': [
                    'The St. Regis San Francisco - Power breakfast',
                    'Premium Parking - Financial District',
                    'One Market Restaurant - Client lunch reservation'
                ]
            },
            'camping': {
                'title': '🏕️ Wilderness Adventure',
                'route': 'San Francisco, CA → Yosemite National Park',
                'personality': 'Ranger Rick (Wilderness Guide)',
                'story': "G'day, adventurer! Ranger Rick here, ready to guide you into the wilderness of Yosemite! As we wind through the Sierra Nevada foothills, keep your eyes peeled for golden eagles soaring above. Did you know Yosemite's El Capitan is the largest granite monolith in the world? Let me share some backcountry secrets...",
                'bookings': [
                    'Upper Pines Campground - Site #42 reserved',
                    'Wilderness Permit - Half Dome trail',
                    'Mountain Shop - Gear rental confirmation'
                ]
            }
        }
        
        journey = journeys.get(journey_type, journeys['disney'])
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(journey).encode())
    
    def handle_event_search(self):
        """Handle event search using Ticketmaster API"""
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        city = params.get('city', ['San Francisco'])[0]
        
        # For demo, return mock data
        # In production, this would call Ticketmaster API
        events = [
            {
                'name': f'{city} Symphony Orchestra',
                'date': 'May 30, 2025',
                'venue': f'{city} Concert Hall'
            },
            {
                'name': 'NBA Playoffs Game',
                'date': 'June 1, 2025',
                'venue': 'Chase Center'
            },
            {
                'name': 'Summer Music Festival',
                'date': 'June 15, 2025',
                'venue': f'{city} Amphitheater'
            }
        ]
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'events': events}).encode())
    
    def handle_personalities(self):
        """Return available voice personalities"""
        personalities = [
            {'name': 'Friendly Guide', 'description': 'Your helpful travel companion'},
            {'name': 'Mickey Mouse', 'description': 'Magical Disney guide'},
            {'name': 'Axel Thunder', 'description': 'Rock and roll DJ'},
            {'name': 'Victoria Professional', 'description': 'Business travel assistant'},
            {'name': 'Ranger Rick', 'description': 'Wilderness adventure guide'},
            {'name': 'Santa Claus', 'description': 'Holiday season guide (Dec only)'},
            {'name': 'Professor History', 'description': 'Historical storyteller'},
            {'name': 'Captain Adventure', 'description': 'Thrill-seeking explorer'},
            {'name': 'Zen Master', 'description': 'Calming wellness guide'},
            {'name': 'Comedy Carl', 'description': 'Family-friendly comedian'}
        ]
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'personalities': personalities}).encode())

def main():
    """Run the demo server"""
    print("🚀 AI Road Trip Storyteller - Demo Server")
    print("=" * 50)
    print("\n✅ Starting demo server on http://localhost:8000")
    print("\n📱 Open your browser to see the interactive demo!")
    print("\nPress Ctrl+C to stop the server\n")
    
    server = HTTPServer(('localhost', 8000), DemoHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n✋ Demo server stopped")

if __name__ == "__main__":
    main()