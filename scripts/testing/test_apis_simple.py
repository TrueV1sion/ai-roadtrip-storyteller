#!/usr/bin/env python3
"""
Simple API test script that works with standard library only
"""
import json
import urllib.request
import urllib.parse
import ssl
import os
from datetime import datetime, timedelta

# Create SSL context for HTTPS requests
ssl_context = ssl.create_default_context()

def test_google_maps():
    """Test Google Maps API"""
    print("\n🗺️  Testing Google Maps API...")
    api_key = os.getenv('GOOGLE_MAPS_API_KEY', '').replace('\n', '')
    
    if not api_key or api_key == 'mock_google_maps_key_for_testing':
        print("   ❌ Google Maps API key not configured")
        return False
    
    # Test directions API
    origin = "San Francisco, CA"
    destination = "Los Angeles, CA"
    
    params = {
        'origin': origin,
        'destination': destination,
        'key': api_key
    }
    
    url = f"https://maps.googleapis.com/maps/api/directions/json?{urllib.parse.urlencode(params)}"
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, context=ssl_context) as response:
            data = json.loads(response.read())
            
        if data.get('status') == 'OK':
            route = data['routes'][0]
            leg = route['legs'][0]
            print(f"   ✅ Google Maps working!")
            print(f"   📍 Route: {origin} → {destination}")
            print(f"   📏 Distance: {leg['distance']['text']}")
            print(f"   ⏱️  Duration: {leg['duration']['text']}")
            return True
        else:
            print(f"   ❌ Maps API error: {data.get('error_message', data.get('status'))}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False

def test_recreation_gov():
    """Test Recreation.gov API"""
    print("\n🏕️  Testing Recreation.gov API...")
    api_key = os.getenv('RECREATION_GOV_API_KEY', '').replace('\n', '')
    
    if not api_key:
        print("   ❌ Recreation.gov API key not configured")
        print("   💡 Get a free API key at: https://ridb.recreation.gov/")
        return False
    
    # Search for Yellowstone facilities
    query = "yellowstone"
    params = {
        'query': query,
        'limit': 3
    }
    url = f"https://ridb.recreation.gov/api/v1/facilities?{urllib.parse.urlencode(params)}"
    
    try:
        req = urllib.request.Request(url)
        req.add_header('apikey', api_key)
        with urllib.request.urlopen(req, context=ssl_context) as response:
            data = json.loads(response.read())
            
        if 'RECDATA' in data:
            facilities = data['RECDATA']
            print(f"   ✅ Recreation.gov working! Found {len(facilities)} facilities")
            for i, facility in enumerate(facilities[:3], 1):
                print(f"   {i}. {facility.get('FacilityName', 'Unknown')}")
            return True
        else:
            print("   ❌ No data returned")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False

def test_ticketmaster():
    """Test Ticketmaster API"""
    print("\n🎫 Testing Ticketmaster API...")
    api_key = os.getenv('TICKETMASTER_API_KEY', '').replace('\n', '')
    
    if not api_key or api_key == 'mock_ticketmaster_key':
        print("   ❌ Ticketmaster API key not configured")
        return False
    
    # Search for events in San Francisco
    params = {
        'apikey': api_key,
        'city': 'San Francisco',
        'size': 3
    }
    
    url = f"https://app.ticketmaster.com/discovery/v2/events.json?{urllib.parse.urlencode(params)}"
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, context=ssl_context) as response:
            data = json.loads(response.read())
            
        if '_embedded' in data and 'events' in data['_embedded']:
            events = data['_embedded']['events']
            print(f"   ✅ Ticketmaster working! Found {len(events)} events")
            for i, event in enumerate(events[:3], 1):
                print(f"   {i}. {event.get('name', 'Unknown')}")
            return True
        else:
            print("   ❌ No events found")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False

def test_openweathermap():
    """Test OpenWeatherMap API"""
    print("\n☁️  Testing OpenWeatherMap API...")
    api_key = os.getenv('OPENWEATHERMAP_API_KEY', '').replace('\n', '')
    
    if not api_key or api_key == 'mock_weather_key':
        print("   ❌ OpenWeatherMap API key not configured")
        return False
    
    # Get weather for San Francisco - properly encode the URL
    city = "San Francisco"
    params = {
        'q': city,
        'appid': api_key,
        'units': 'imperial'
    }
    url = f"https://api.openweathermap.org/data/2.5/weather?{urllib.parse.urlencode(params)}"
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, context=ssl_context) as response:
            data = json.loads(response.read())
            
        if 'main' in data:
            print(f"   ✅ OpenWeatherMap working!")
            print(f"   🌡️  {city}: {data['main']['temp']:.1f}°F")
            print(f"   ☁️  Conditions: {data['weather'][0]['description']}")
            return True
        else:
            print("   ❌ No weather data returned")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False

def simulate_journey():
    """Simulate a simple journey"""
    print("\n🚗 Simulating a journey...")
    
    # Create a virtual journey
    journey = {
        "user": "Family of 4",
        "origin": "San Francisco, CA",
        "destination": "Disneyland, Anaheim, CA",
        "date": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
        "interests": ["theme_parks", "family", "entertainment"]
    }
    
    print(f"\n   👨‍👩‍👧‍👦 {journey['user']}")
    print(f"   📍 Route: {journey['origin']} → {journey['destination']}")
    print(f"   📅 Date: {journey['date']}")
    print(f"   🎯 Interests: {', '.join(journey['interests'])}")
    
    # Simulate AI response
    print("\n   🤖 AI Assistant: 'Welcome aboard! I'm Mickey, your magical guide to Disneyland!'")
    print("   🎭 Personality: Mickey Mouse Guide (auto-selected for Disney trip)")
    print("   📖 Story: 'Did you know Walt Disney created Disneyland in just 365 days?'")
    
    # Simulate booking suggestions
    print("\n   💰 Booking Opportunities:")
    print("   1. Blue Bayou Restaurant - Dine inside Pirates of the Caribbean!")
    print("   2. Grand Californian Hotel - Stay in Disney magic")
    print("   3. MaxPass - Skip the lines at popular attractions")
    
    return True

def main():
    """Run all tests"""
    print("=" * 60)
    print("🚀 AI Road Trip Storyteller - API Test Suite")
    print("=" * 60)
    
    # Load environment variables
    if os.path.exists('.env'):
        with open('.env') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    # Run tests
    results = {
        'Google Maps': test_google_maps(),
        'Recreation.gov': test_recreation_gov(),
        'Ticketmaster': test_ticketmaster(),
        'OpenWeatherMap': test_openweathermap()
    }
    
    # Simulate a journey
    simulate_journey()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    working = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\n✅ APIs Working: {working}/{total}")
    for api, status in results.items():
        icon = "✅" if status else "❌"
        print(f"   {icon} {api}")
    
    if working >= 3:
        print("\n🎉 Your system is ready for beta testing!")
        print("   - Real navigation with Google Maps")
        print("   - Real campgrounds with Recreation.gov")
        print("   - Real events with Ticketmaster")
        print("   - Real weather with OpenWeatherMap")
    else:
        print("\n⚠️  Some APIs need configuration")
    
    print("\n💡 Next steps:")
    print("1. Launch the backend: ./scripts/launch_beta.sh")
    print("2. Test with mobile app: cd mobile && npm start")
    print("3. Share with beta testers!")

if __name__ == "__main__":
    main()