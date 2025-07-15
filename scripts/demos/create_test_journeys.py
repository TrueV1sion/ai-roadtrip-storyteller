#!/usr/bin/env python3
"""
Create test journeys for beta testing
This script creates various journey scenarios to validate the AI orchestration
"""

import asyncio
import httpx
from datetime import datetime, timedelta
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000/api"

# Test scenarios covering all major use cases
TEST_JOURNEYS = [
    {
        "name": "Disney Family Adventure",
        "description": "Family of 4 driving to Disney World",
        "origin": "Atlanta, GA",
        "destination": "Walt Disney World, Orlando, FL",
        "preferences": {
            "travel_style": "family",
            "interests": ["theme_parks", "entertainment", "dining"],
            "ages": [8, 12, 35, 38]
        },
        "expected_personality": "Mickey Mouse Guide",
        "expected_bookings": ["restaurant", "hotel"]
    },
    {
        "name": "Taylor Swift Concert Journey",
        "description": "Solo driver to concert at Mercedes-Benz Stadium",
        "origin": "Nashville, TN", 
        "destination": "Mercedes-Benz Stadium, Atlanta, GA",
        "event_query": "Taylor Swift Atlanta",
        "preferences": {
            "travel_style": "solo",
            "interests": ["music", "concerts", "pop_culture"]
        },
        "expected_personality": "Pop Star Guide",
        "expected_bookings": ["restaurant", "parking"]
    },
    {
        "name": "Rideshare Driver Optimization",
        "description": "Uber driver daily route optimization",
        "origin": "San Francisco, CA",
        "mode": "rideshare_driver",
        "preferences": {
            "optimize_for": ["earnings", "efficiency"],
            "vehicle_type": "ev"
        },
        "expected_features": ["surge_avoidance", "charging_stops", "quick_meals"]
    },
    {
        "name": "Christmas Grandma Visit",
        "description": "Holiday family road trip",
        "origin": "Chicago, IL",
        "destination": "Cleveland, OH",
        "date": "2024-12-24",
        "preferences": {
            "travel_style": "family",
            "interests": ["family", "holiday", "traditions"]
        },
        "expected_personality": "Santa Claus",
        "expected_bookings": ["restaurant", "gift_shop"]
    },
    {
        "name": "Business Meeting Prep",
        "description": "Executive driving to important client meeting",
        "origin": "Boston, MA",
        "destination": "New York, NY",
        "preferences": {
            "travel_style": "business",
            "interests": ["productivity", "business", "efficiency"],
            "meeting_topic": "Q4 Sales Strategy"
        },
        "expected_personality": "Professional Guide",
        "expected_bookings": ["restaurant", "parking"]
    },
    {
        "name": "Yellowstone Camping Adventure",
        "description": "Outdoor enthusiasts heading to national park",
        "origin": "Denver, CO",
        "destination": "Yellowstone National Park, WY",
        "preferences": {
            "travel_style": "adventure",
            "interests": ["camping", "hiking", "nature", "photography"]
        },
        "expected_personality": "Adventurer",
        "expected_bookings": ["campground", "supplies"]
    },
    {
        "name": "EV Road Trip Challenge",
        "description": "Tesla driver on long-distance journey",
        "origin": "Los Angeles, CA",
        "destination": "Las Vegas, NV",
        "preferences": {
            "vehicle_type": "tesla_model_3",
            "interests": ["technology", "sustainability"],
            "optimize_for": ["charging", "efficiency"]
        },
        "expected_bookings": ["ev_charging", "restaurant"]
    },
    {
        "name": "Haunted Halloween Drive",
        "description": "Spooky road trip to Salem",
        "origin": "Providence, RI",
        "destination": "Salem, MA",
        "date": "2024-10-31",
        "preferences": {
            "interests": ["horror", "history", "supernatural"],
            "theme": "haunted"
        },
        "expected_personality": "Ghost Tour Guide",
        "expected_bookings": ["tour", "restaurant"]
    }
]

async def create_test_journey(client: httpx.AsyncClient, journey: Dict[str, Any]) -> Dict[str, Any]:
    """Create a single test journey"""
    print(f"\n🚗 Creating journey: {journey['name']}")
    print(f"   📍 Route: {journey.get('origin', 'Current Location')} → {journey['destination']}")
    
    # Step 1: Create user session
    user_data = {
        "name": f"Beta Tester - {journey['name']}",
        "preferences": journey.get("preferences", {})
    }
    
    # Step 2: Search for events if applicable
    if "event_query" in journey:
        print(f"   🎫 Searching for event: {journey['event_query']}")
        event_response = await client.get(
            f"{BASE_URL}/event-journeys/search-events",
            params={"query": journey["event_query"], "limit": 1}
        )
        if event_response.status_code == 200:
            events = event_response.json()
            if events:
                print(f"   ✅ Found event: {events[0]['name']}")
                journey["event_id"] = events[0]["id"]
    
    # Step 3: Create journey with voice assistant
    voice_request = {
        "user_input": f"I want to go to {journey['destination']}",
        "context": {
            "origin": journey.get("origin", "Current Location"),
            "destination": journey["destination"],
            "preferences": journey.get("preferences", {}),
            "date": journey.get("date", datetime.now().isoformat()),
            "mode": journey.get("mode", "driving")
        }
    }
    
    if "event_id" in journey:
        voice_request["context"]["event_id"] = journey["event_id"]
    
    print("   🤖 Activating AI assistant...")
    response = await client.post(
        f"{BASE_URL}/voice-assistant/interact",
        json=voice_request
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ Journey created successfully!")
        print(f"   🎭 Personality: {result.get('personality', 'Default')}")
        
        # Check for booking opportunities
        if "booking_opportunities" in result:
            print(f"   💰 Booking opportunities found: {len(result['booking_opportunities'])}")
            for booking in result["booking_opportunities"][:3]:
                print(f"      - {booking['type']}: {booking['name']} (${booking.get('price', 'N/A')})")
        
        return result
    else:
        print(f"   ❌ Failed to create journey: {response.status_code}")
        return None

async def test_personality_switching(client: httpx.AsyncClient):
    """Test dynamic personality switching"""
    print("\n🎭 Testing personality switching...")
    
    # Get available personalities
    response = await client.get(f"{BASE_URL}/voice/personalities")
    if response.status_code == 200:
        personalities = response.json()
        print(f"   Found {len(personalities)} personalities available")
        
        # Test contextual personality
        contexts = [
            {"location": {"state": "TX"}, "expected": "Texas Ranger"},
            {"date": "2024-12-25", "expected": "Santa"},
            {"event_type": "concert", "expected": "Pop Star Guide"},
            {"time": "23:00", "expected": "Night Owl"}
        ]
        
        for context in contexts:
            response = await client.post(
                f"{BASE_URL}/voice/personalities/contextual",
                json={"context": context}
            )
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Context {context} → {result['personality']['name']}")

async def test_booking_flows(client: httpx.AsyncClient):
    """Test booking creation flows"""
    print("\n💰 Testing booking flows...")
    
    # Test Recreation.gov campground search
    print("   🏕️ Testing campground search...")
    response = await client.get(
        f"{BASE_URL}/bookings/campgrounds/search",
        params={"query": "yellowstone", "limit": 3}
    )
    if response.status_code == 200:
        campgrounds = response.json()
        print(f"   ✅ Found {len(campgrounds)} campgrounds")
        if campgrounds:
            # Test availability
            campground_id = campgrounds[0]["id"]
            response = await client.get(
                f"{BASE_URL}/bookings/campgrounds/{campground_id}/availability",
                params={"start_date": "2024-07-01", "end_date": "2024-07-03"}
            )
            if response.status_code == 200:
                print("   ✅ Availability check successful")
    
    # Test restaurant search
    print("   🍽️ Testing restaurant search...")
    response = await client.get(
        f"{BASE_URL}/bookings/restaurants/search",
        params={"location": "San Francisco, CA", "cuisine": "italian"}
    )
    if response.status_code == 200:
        restaurants = response.json()
        print(f"   ✅ Found {len(restaurants)} restaurants")

async def generate_beta_report(journeys: list):
    """Generate beta testing report"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_journeys": len(journeys),
        "successful_journeys": sum(1 for j in journeys if j is not None),
        "features_tested": [
            "AI Orchestration",
            "Event Detection", 
            "Voice Personalities",
            "Booking Integration",
            "Rideshare Mode",
            "Holiday Themes"
        ],
        "test_scenarios": [j["name"] for j in TEST_JOURNEYS]
    }
    
    with open("beta_test_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print("\n📊 Beta Test Report Generated: beta_test_report.json")
    print(f"   ✅ Success rate: {report['successful_journeys']}/{report['total_journeys']}")

async def main():
    """Run all beta tests"""
    print("🚀 AI Road Trip Storyteller - Beta Test Suite")
    print("=" * 50)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Check if backend is running
        try:
            response = await client.get(f"{BASE_URL.replace('/api', '/health')}")
            if response.status_code != 200:
                print("❌ Backend is not running! Please run: ./scripts/launch_beta.sh")
                return
        except:
            print("❌ Cannot connect to backend! Please run: ./scripts/launch_beta.sh")
            return
        
        print("✅ Backend is running\n")
        
        # Create test journeys
        journeys = []
        for journey in TEST_JOURNEYS:
            result = await create_test_journey(client, journey)
            journeys.append(result)
            await asyncio.sleep(1)  # Avoid rate limiting
        
        # Test additional features
        await test_personality_switching(client)
        await test_booking_flows(client)
        
        # Generate report
        await generate_beta_report(journeys)
        
        print("\n✨ Beta testing complete!")
        print("\nNext steps:")
        print("1. Review beta_test_report.json")
        print("2. Check backend.log for any errors")
        print("3. Share test journeys with beta users")
        print("4. Monitor real user interactions")

if __name__ == "__main__":
    asyncio.run(main())