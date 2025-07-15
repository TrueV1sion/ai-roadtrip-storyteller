#!/usr/bin/env python3
"""
Test Backend MVP Endpoint - Verify the MVP voice endpoint is working
"""

import asyncio
import aiohttp
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))


async def test_mvp_endpoint():
    """Test the MVP voice endpoint"""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing MVP Voice Endpoint")
    print("=" * 50)
    
    # Test 1: Health check
    print("\n1️⃣ Testing MVP health endpoint...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/api/mvp/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Health check passed: {data}")
                else:
                    print(f"❌ Health check failed: {response.status}")
    except Exception as e:
        print(f"❌ Health check error: {e}")
        print("   Make sure backend is running: cd backend && uvicorn app.main:app --reload")
        return
    
    # Test 2: Navigation command
    print("\n2️⃣ Testing navigation command...")
    navigation_payload = {
        "user_input": "Navigate to Golden Gate Bridge",
        "context": {
            "location": {
                "lat": 37.7749,
                "lng": -122.4194
            },
            "location_name": "San Francisco"
        }
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/api/mvp/voice",
                json=navigation_payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Navigation command successful!")
                    print(f"   Response type: {data['response'].get('type')}")
                    print(f"   Destination: {data['response'].get('destination')}")
                    print(f"   Story: {data['response'].get('text', '')[:100]}...")
                    if data.get('audio_url'):
                        print(f"   Audio URL: {data['audio_url']}")
                else:
                    error_text = await response.text()
                    print(f"❌ Navigation command failed: {response.status}")
                    print(f"   Error: {error_text}")
    except Exception as e:
        print(f"❌ Navigation command error: {e}")
    
    # Test 3: Location story request
    print("\n3️⃣ Testing location story request...")
    story_payload = {
        "user_input": "Tell me about this area",
        "context": {
            "location": {
                "lat": 40.7128,
                "lng": -74.0060
            },
            "location_name": "New York City"
        }
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/api/mvp/voice",
                json=story_payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Story request successful!")
                    print(f"   Response type: {data['response'].get('type')}")
                    print(f"   Story: {data['response'].get('text', '')[:100]}...")
                    if data.get('audio_url'):
                        print(f"   Audio URL: {data['audio_url']}")
                else:
                    error_text = await response.text()
                    print(f"❌ Story request failed: {response.status}")
                    print(f"   Error: {error_text}")
    except Exception as e:
        print(f"❌ Story request error: {e}")
    
    print("\n" + "=" * 50)
    print("📊 MVP Backend Test Summary")
    print("=" * 50)
    print("\nTo test the full flow:")
    print("1. Ensure backend is running: cd backend && uvicorn app.main:app --reload")
    print("2. Check Google Cloud credentials are configured")
    print("3. Run mobile app: cd mobile && npm start")
    print("4. Test voice commands on the SimpleMVPNavigationScreen")


async def main():
    await test_mvp_endpoint()


if __name__ == "__main__":
    asyncio.run(main())