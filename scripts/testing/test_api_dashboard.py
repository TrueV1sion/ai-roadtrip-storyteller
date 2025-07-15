#!/usr/bin/env python3
"""
API Testing Dashboard for AI Road Trip Storyteller
"""

import os
import sys
import json
import requests
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time
from dataclasses import dataclass, asdict
from pathlib import Path
import random

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@dataclass
class APITestResult:
    name: str
    status: str  # "success", "warning", "error"
    response_time: float
    message: str
    details: Optional[Dict] = None

class APITestDashboard:
    def __init__(self):
        self.env_vars = self._load_env_vars()
        self.results: List[APITestResult] = []
        
    def _load_env_vars(self) -> Dict[str, str]:
        """Load environment variables from .env file"""
        env_vars = {}
        env_file = Path(".env")
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip().strip('"').strip("'")
                        
        # Also load from environment
        for key in os.environ:
            if key.startswith(("GOOGLE_", "OPENWEATHER_", "TICKETMASTER_", "SPOTIFY_", "DATABASE_", "REDIS_")):
                env_vars[key] = os.environ[key]
                
        return env_vars
        
    def print_header(self, text: str):
        """Print formatted header"""
        print("\n" + "=" * 70)
        print(f" {text.center(68)} ")
        print("=" * 70 + "\n")
        
    def print_result(self, result: APITestResult):
        """Print test result with color coding"""
        colors = {
            "success": "\033[92m",
            "warning": "\033[93m",
            "error": "\033[91m"
        }
        symbols = {
            "success": "✓",
            "warning": "⚠",
            "error": "✗"
        }
        
        color = colors.get(result.status, "")
        symbol = symbols.get(result.status, "")
        reset = "\033[0m"
        
        print(f"{color}[{symbol}] {result.name:<30} {result.response_time:>6.2f}ms  {result.message}{reset}")
        
        if result.details:
            for key, value in result.details.items():
                print(f"    {key}: {value}")
                
    async def test_google_maps(self) -> APITestResult:
        """Test Google Maps Directions API"""
        api_key = self.env_vars.get("GOOGLE_MAPS_API_KEY")
        
        if not api_key:
            return APITestResult(
                name="Google Maps API",
                status="error",
                response_time=0,
                message="API key not configured"
            )
            
        start_time = time.time()
        
        try:
            response = requests.get(
                "https://maps.googleapis.com/maps/api/directions/json",
                params={
                    "origin": "Golden Gate Bridge, San Francisco, CA",
                    "destination": "Hollywood Sign, Los Angeles, CA",
                    "key": api_key,
                    "alternatives": "true"
                },
                timeout=10
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "OK":
                    routes = data.get("routes", [])
                    return APITestResult(
                        name="Google Maps API",
                        status="success",
                        response_time=response_time,
                        message=f"Found {len(routes)} routes",
                        details={
                            "Primary Route": routes[0]["summary"] if routes else "N/A",
                            "Distance": routes[0]["legs"][0]["distance"]["text"] if routes else "N/A",
                            "Duration": routes[0]["legs"][0]["duration"]["text"] if routes else "N/A"
                        }
                    )
                else:
                    return APITestResult(
                        name="Google Maps API",
                        status="error",
                        response_time=response_time,
                        message=f"API Error: {data.get('status')}",
                        details={"error_message": data.get("error_message", "Unknown error")}
                    )
            else:
                return APITestResult(
                    name="Google Maps API",
                    status="error",
                    response_time=response_time,
                    message=f"HTTP {response.status_code}"
                )
                
        except Exception as e:
            return APITestResult(
                name="Google Maps API",
                status="error",
                response_time=(time.time() - start_time) * 1000,
                message=f"Connection error: {str(e)}"
            )
            
    async def test_weather_api(self) -> APITestResult:
        """Test OpenWeather API"""
        api_key = self.env_vars.get("OPENWEATHER_API_KEY")
        
        if not api_key:
            return APITestResult(
                name="Weather API",
                status="warning",
                response_time=0,
                message="Optional API not configured"
            )
            
        start_time = time.time()
        
        try:
            response = requests.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "q": "San Francisco,US",
                    "appid": api_key,
                    "units": "imperial"
                },
                timeout=10
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                return APITestResult(
                    name="Weather API",
                    status="success",
                    response_time=response_time,
                    message="Connected successfully",
                    details={
                        "Location": data.get("name", "Unknown"),
                        "Temperature": f"{data['main']['temp']}°F",
                        "Conditions": data['weather'][0]['description'].title(),
                        "Humidity": f"{data['main']['humidity']}%"
                    }
                )
            else:
                return APITestResult(
                    name="Weather API",
                    status="error",
                    response_time=response_time,
                    message=f"HTTP {response.status_code}"
                )
                
        except Exception as e:
            return APITestResult(
                name="Weather API",
                status="error",
                response_time=(time.time() - start_time) * 1000,
                message=f"Connection error: {str(e)}"
            )
            
    async def test_ticketmaster(self) -> APITestResult:
        """Test Ticketmaster API"""
        api_key = self.env_vars.get("TICKETMASTER_API_KEY")
        
        if not api_key:
            return APITestResult(
                name="Ticketmaster API",
                status="warning",
                response_time=0,
                message="Optional API not configured"
            )
            
        start_time = time.time()
        
        try:
            response = requests.get(
                "https://app.ticketmaster.com/discovery/v2/events",
                params={
                    "apikey": api_key,
                    "city": "San Francisco",
                    "size": 5,
                    "sort": "date,asc"
                },
                timeout=10
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                events = data.get("_embedded", {}).get("events", [])
                return APITestResult(
                    name="Ticketmaster API",
                    status="success",
                    response_time=response_time,
                    message=f"Found {len(events)} upcoming events",
                    details={
                        f"Event {i+1}": event["name"][:50]
                        for i, event in enumerate(events[:3])
                    } if events else {"Note": "No events found"}
                )
            else:
                return APITestResult(
                    name="Ticketmaster API",
                    status="error",
                    response_time=response_time,
                    message=f"HTTP {response.status_code}"
                )
                
        except Exception as e:
            return APITestResult(
                name="Ticketmaster API",
                status="error",
                response_time=(time.time() - start_time) * 1000,
                message=f"Connection error: {str(e)}"
            )
            
    async def test_database(self) -> APITestResult:
        """Test PostgreSQL connection"""
        db_url = self.env_vars.get("DATABASE_URL")
        
        if not db_url:
            return APITestResult(
                name="PostgreSQL Database",
                status="error",
                response_time=0,
                message="Database URL not configured"
            )
            
        start_time = time.time()
        
        try:
            import psycopg2
            from urllib.parse import urlparse
            
            # Parse database URL
            parsed = urlparse(db_url)
            
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path[1:],
                user=parsed.username,
                password=parsed.password
            )
            
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
            table_count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            response_time = (time.time() - start_time) * 1000
            
            return APITestResult(
                name="PostgreSQL Database",
                status="success",
                response_time=response_time,
                message="Connected successfully",
                details={
                    "Version": version.split(',')[0],
                    "Tables": f"{table_count} tables in public schema"
                }
            )
            
        except ImportError:
            return APITestResult(
                name="PostgreSQL Database",
                status="warning",
                response_time=0,
                message="psycopg2 not installed - install with: pip install psycopg2-binary"
            )
        except Exception as e:
            return APITestResult(
                name="PostgreSQL Database",
                status="error",
                response_time=(time.time() - start_time) * 1000,
                message=f"Connection error: {str(e)}"
            )
            
    async def test_redis(self) -> APITestResult:
        """Test Redis connection"""
        redis_url = self.env_vars.get("REDIS_URL")
        
        if not redis_url:
            return APITestResult(
                name="Redis Cache",
                status="error",
                response_time=0,
                message="Redis URL not configured"
            )
            
        start_time = time.time()
        
        try:
            import redis
            
            r = redis.from_url(redis_url)
            
            # Test basic operations
            test_key = "roadtrip:test:ping"
            test_value = f"test_{datetime.now().isoformat()}"
            
            r.set(test_key, test_value, ex=60)
            retrieved = r.get(test_key)
            
            info = r.info()
            
            response_time = (time.time() - start_time) * 1000
            
            if retrieved and retrieved.decode() == test_value:
                return APITestResult(
                    name="Redis Cache",
                    status="success",
                    response_time=response_time,
                    message="Connected successfully",
                    details={
                        "Version": info.get("redis_version", "Unknown"),
                        "Memory Used": f"{info.get('used_memory_human', 'Unknown')}",
                        "Connected Clients": info.get("connected_clients", "Unknown")
                    }
                )
            else:
                return APITestResult(
                    name="Redis Cache",
                    status="error",
                    response_time=response_time,
                    message="Read/write test failed"
                )
                
        except ImportError:
            return APITestResult(
                name="Redis Cache",
                status="warning",
                response_time=0,
                message="redis not installed - install with: pip install redis"
            )
        except Exception as e:
            return APITestResult(
                name="Redis Cache",
                status="error",
                response_time=(time.time() - start_time) * 1000,
                message=f"Connection error: {str(e)}"
            )
            
    async def test_google_vertex_ai(self) -> APITestResult:
        """Test Google Vertex AI"""
        project_id = self.env_vars.get("VERTEX_AI_PROJECT_ID")
        location = self.env_vars.get("VERTEX_AI_LOCATION")
        credentials_path = self.env_vars.get("GOOGLE_APPLICATION_CREDENTIALS")
        
        if not all([project_id, location, credentials_path]):
            return APITestResult(
                name="Google Vertex AI",
                status="error",
                response_time=0,
                message="Vertex AI not fully configured",
                details={
                    "Project ID": "Configured" if project_id else "Missing",
                    "Location": "Configured" if location else "Missing",
                    "Credentials": "Configured" if credentials_path else "Missing"
                }
            )
            
        start_time = time.time()
        
        try:
            # Check if credentials file exists
            if not Path(credentials_path).exists():
                return APITestResult(
                    name="Google Vertex AI",
                    status="error",
                    response_time=0,
                    message=f"Credentials file not found: {credentials_path}"
                )
                
            # Try to import and test
            from google.cloud import aiplatform
            
            aiplatform.init(project=project_id, location=location)
            
            response_time = (time.time() - start_time) * 1000
            
            return APITestResult(
                name="Google Vertex AI",
                status="success",
                response_time=response_time,
                message="Initialized successfully",
                details={
                    "Project": project_id,
                    "Location": location,
                    "Credentials": os.path.basename(credentials_path)
                }
            )
            
        except ImportError:
            return APITestResult(
                name="Google Vertex AI",
                status="warning",
                response_time=0,
                message="google-cloud-aiplatform not installed"
            )
        except Exception as e:
            return APITestResult(
                name="Google Vertex AI",
                status="error",
                response_time=(time.time() - start_time) * 1000,
                message=f"Initialization error: {str(e)}"
            )
            
    def generate_test_booking(self):
        """Generate a test booking scenario"""
        self.print_header("Test Booking Scenario")
        
        # Sample trip data
        trip_data = {
            "origin": "San Francisco, CA",
            "destination": "Los Angeles, CA",
            "date": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
            "travelers": 4,
            "interests": ["history", "food", "nature", "entertainment"]
        }
        
        print(f"🚗 Trip Details:")
        print(f"   From: {trip_data['origin']}")
        print(f"   To: {trip_data['destination']}")
        print(f"   Date: {trip_data['date']}")
        print(f"   Travelers: {trip_data['travelers']}")
        print(f"   Interests: {', '.join(trip_data['interests'])}")
        
        print("\n🍽️  Restaurant Recommendations:")
        restaurants = [
            "The French Laundry (Yountville) - Fine dining experience",
            "Harris Ranch Inn (Coalinga) - Famous steakhouse",
            "Pea Soup Andersen's (Buellton) - Classic road trip stop"
        ]
        for i, restaurant in enumerate(restaurants, 1):
            print(f"   {i}. {restaurant}")
            
        print("\n🎫 Event Suggestions:")
        events = [
            "Hollywood Bowl Concert - Evening performance",
            "Griffith Observatory - Stargazing session",
            "Santa Barbara Wine Tour - Afternoon tasting"
        ]
        for i, event in enumerate(events, 1):
            print(f"   {i}. {event}")
            
        print("\n🏞️  Points of Interest:")
        pois = [
            "Big Sur Coastal Drive - Scenic detour (+45 min)",
            "Hearst Castle - Historical tour (2-3 hours)",
            "Solvang Danish Village - Cultural experience"
        ]
        for i, poi in enumerate(pois, 1):
            print(f"   {i}. {poi}")
            
        print("\n✨ To make bookings, the system would:")
        print("   1. Use OpenTable API for restaurant reservations")
        print("   2. Use Ticketmaster API for event tickets")
        print("   3. Integrate with attraction booking systems")
        print("   4. Send confirmations via email/SMS")
        print("   5. Add to trip itinerary automatically")
        
    async def run_all_tests(self):
        """Run all API tests"""
        self.print_header("AI Road Trip Storyteller - API Test Dashboard")
        print(f"Testing at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run all tests concurrently
        tests = [
            self.test_google_maps(),
            self.test_google_vertex_ai(),
            self.test_database(),
            self.test_redis(),
            self.test_weather_api(),
            self.test_ticketmaster()
        ]
        
        print("\nRunning API tests...\n")
        
        results = await asyncio.gather(*tests)
        
        # Display results
        required_apis = ["Google Maps API", "Google Vertex AI", "PostgreSQL Database", "Redis Cache"]
        optional_apis = ["Weather API", "Ticketmaster API"]
        
        print("🔴 Required APIs:")
        for result in results:
            if result.name in required_apis:
                self.print_result(result)
                
        print("\n🟡 Optional APIs:")
        for result in results:
            if result.name in optional_apis:
                self.print_result(result)
                
        # Summary
        successful = sum(1 for r in results if r.status == "success")
        warnings = sum(1 for r in results if r.status == "warning")
        errors = sum(1 for r in results if r.status == "error")
        
        self.print_header("Test Summary")
        print(f"✓ Successful: {successful}")
        print(f"⚠ Warnings: {warnings}")
        print(f"✗ Errors: {errors}")
        
        avg_response_time = sum(r.response_time for r in results if r.response_time > 0) / len([r for r in results if r.response_time > 0])
        print(f"\n⏱  Average response time: {avg_response_time:.2f}ms")
        
        # Check if all required APIs are working
        required_working = all(
            r.status == "success" for r in results 
            if r.name in required_apis
        )
        
        if required_working:
            print("\n✅ All required APIs are operational!")
            print("\nThe application is ready to run.")
        else:
            print("\n⚠️  Some required APIs are not working.")
            print("Please check the configuration and error messages above.")
            
        # Generate test booking
        if successful >= 2:
            self.generate_test_booking()
            
    def run(self):
        """Run the dashboard"""
        asyncio.run(self.run_all_tests())

if __name__ == "__main__":
    dashboard = APITestDashboard()
    dashboard.run()