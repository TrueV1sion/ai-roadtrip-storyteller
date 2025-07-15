"""
Comprehensive load testing scenarios for AI Road Trip Storyteller
"""
import asyncio
import random
import time
from typing import Dict, List, Any
from datetime import datetime
import statistics
import json

import aiohttp
from locust import HttpUser, task, between, events
from locust.env import Environment
from locust.stats import stats_printer, stats_history

from tests.load.test_load_personalized_stories import (
    create_test_journey,
    create_test_preferences
)


class RoadTripUser(HttpUser):
    """Simulated user for load testing"""
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Initialize user session"""
        # Login and get token
        response = self.client.post("/api/auth/login", json={
            "email": f"loadtest_{random.randint(1000, 9999)}@example.com",
            "password": "LoadTest123!"
        })
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            # Create user if login fails
            self.client.post("/api/auth/register", json={
                "email": f"loadtest_{random.randint(1000, 9999)}@example.com",
                "password": "LoadTest123!",
                "full_name": "Load Test User"
            })
            self.on_start()  # Retry login
    
    @task(30)
    def voice_assistant_interaction(self):
        """Simulate voice assistant interaction (most common)"""
        queries = [
            "I want to go to Disneyland from San Francisco",
            "Find me a good restaurant on the way",
            "Tell me about interesting stops near Highway 1",
            "Book a hotel for tonight near Los Angeles",
            "What's the weather like at my destination?",
            "Play some road trip music",
            "Find EV charging stations on my route",
            "Tell me a story about the Golden Gate Bridge"
        ]
        
        with self.client.post(
            "/api/voice-assistant/interact",
            json={
                "user_input": random.choice(queries),
                "context": {
                    "origin": "San Francisco, CA",
                    "destination": "Los Angeles, CA",
                    "current_location": {
                        "lat": 37.7749,
                        "lng": -122.4194
                    }
                }
            },
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Voice assistant failed: {response.status_code}")
    
    @task(20)
    def get_personalized_story(self):
        """Get personalized story content"""
        with self.client.post(
            "/api/personalized-story",
            json={
                "origin": "San Francisco, CA",
                "destination": "Los Angeles, CA",
                "interests": ["history", "nature", "food"],
                "duration": "6 hours"
            },
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Story generation failed: {response.status_code}")
    
    @task(15)
    def search_and_book(self):
        """Search for and book accommodations"""
        # Search hotels
        search_response = self.client.get(
            "/api/booking/search",
            params={
                "location": "Santa Barbara, CA",
                "checkin": "2024-06-20",
                "checkout": "2024-06-21",
                "guests": 2
            },
            headers=self.headers
        )
        
        if search_response.status_code == 200:
            hotels = search_response.json().get("hotels", [])
            if hotels:
                # Book first available hotel
                hotel = hotels[0]
                self.client.post(
                    "/api/booking/reserve",
                    json={
                        "hotel_id": hotel["id"],
                        "checkin": "2024-06-20",
                        "checkout": "2024-06-21",
                        "guests": 2,
                        "room_type": hotel["room_types"][0]["id"]
                    },
                    headers=self.headers
                )
    
    @task(10)
    def get_directions(self):
        """Get driving directions"""
        with self.client.post(
            "/api/directions",
            json={
                "origin": "San Francisco, CA",
                "destination": "Los Angeles, CA",
                "waypoints": ["Santa Barbara, CA"],
                "preferences": {
                    "avoid_highways": False,
                    "scenic_route": True
                }
            },
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Directions failed: {response.status_code}")
    
    @task(10)
    def event_journey(self):
        """Create event-based journey"""
        events = [
            {"venue": "Hollywood Bowl", "event_type": "concert"},
            {"venue": "Disneyland", "event_type": "theme_park"},
            {"venue": "Staples Center", "event_type": "sports"},
            {"venue": "Coachella", "event_type": "festival"}
        ]
        
        event = random.choice(events)
        with self.client.post(
            "/api/event-journey/create",
            json={
                "origin": "San Francisco, CA",
                "venue_name": event["venue"],
                "event_type": event["event_type"],
                "event_date": "2024-07-15T19:00:00",
                "preferences": {
                    "arrival_buffer": 60,
                    "include_parking": True
                }
            },
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Event journey failed: {response.status_code}")
    
    @task(5)
    def play_trivia_game(self):
        """Play location-based trivia game"""
        with self.client.post(
            "/api/games/trivia/start",
            json={
                "location": {
                    "lat": 34.0522,
                    "lng": -118.2437
                },
                "difficulty": "medium",
                "category": "local_history"
            },
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                game_id = response.json()["game_id"]
                # Answer a question
                self.client.post(
                    f"/api/games/trivia/{game_id}/answer",
                    json={
                        "question_id": 1,
                        "answer": "A"
                    },
                    headers=self.headers
                )
                response.success()
            else:
                response.failure(f"Trivia game failed: {response.status_code}")
    
    @task(5)
    def update_preferences(self):
        """Update user preferences"""
        self.client.put(
            "/api/users/preferences",
            json={
                "interests": ["nature", "history", "food", "music"],
                "voice_personality": "enthusiastic_guide",
                "language": "en",
                "accessibility": {
                    "large_text": False,
                    "voice_speed": "normal"
                }
            },
            headers=self.headers
        )
    
    @task(5)
    def get_spotify_playlist(self):
        """Get Spotify road trip playlist"""
        with self.client.get(
            "/api/spotify/road-trip-playlist",
            params={
                "origin": "San Francisco, CA",
                "destination": "Los Angeles, CA",
                "mood": "upbeat",
                "duration": 360  # 6 hours in minutes
            },
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code in [200, 401]:  # 401 if Spotify not connected
                response.success()
            else:
                response.failure(f"Spotify playlist failed: {response.status_code}")


class MobileAppUser(HttpUser):
    """Simulated mobile app user with specific patterns"""
    wait_time = between(2, 5)
    
    def on_start(self):
        """Mobile app initialization"""
        # Simulate app startup
        self.client.get("/api/health")
        self.client.get("/api/config/mobile")
        
        # Login
        response = self.client.post("/api/auth/login", json={
            "email": f"mobile_{random.randint(1000, 9999)}@example.com",
            "password": "Mobile123!",
            "device_id": f"device_{random.randint(100000, 999999)}"
        })
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(40)
    def voice_navigation(self):
        """Voice-first navigation interaction"""
        with self.client.post(
            "/api/voice-navigation/command",
            json={
                "command": "navigate",
                "text": "Take me to the nearest In-N-Out Burger",
                "context": {
                    "current_location": {
                        "lat": 34.0522,
                        "lng": -118.2437
                    },
                    "speed": 65,
                    "heading": 180
                }
            },
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Voice navigation failed: {response.status_code}")
    
    @task(20)
    def real_time_updates(self):
        """Get real-time journey updates"""
        with self.client.get(
            "/api/journey/updates",
            params={
                "lat": 34.0522,
                "lng": -118.2437,
                "include": "traffic,weather,points_of_interest"
            },
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Journey updates failed: {response.status_code}")
    
    @task(15)
    def ar_landmark_scan(self):
        """AR landmark scanning"""
        with self.client.post(
            "/api/ar/scan",
            json={
                "image": "base64_encoded_image_data",
                "location": {
                    "lat": 34.0522,
                    "lng": -118.2437
                },
                "device_orientation": {
                    "heading": 45,
                    "pitch": 0,
                    "roll": 0
                }
            },
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"AR scan failed: {response.status_code}")
    
    @task(10)
    def offline_sync(self):
        """Sync offline data"""
        with self.client.post(
            "/api/sync/offline",
            json={
                "last_sync": "2024-01-15T10:00:00Z",
                "data": {
                    "saved_places": 5,
                    "completed_journeys": 2,
                    "game_scores": 3
                }
            },
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Offline sync failed: {response.status_code}")


class RideshareDriverUser(HttpUser):
    """Simulated rideshare driver"""
    wait_time = between(5, 10)
    
    def on_start(self):
        """Initialize rideshare driver mode"""
        response = self.client.post("/api/auth/login", json={
            "email": f"driver_{random.randint(1000, 9999)}@example.com",
            "password": "Driver123!"
        })
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
            
            # Enable driver mode
            self.client.post(
                "/api/rideshare/driver/enable",
                headers=self.headers
            )
    
    @task(50)
    def update_driver_status(self):
        """Update driver location and status"""
        with self.client.post(
            "/api/rideshare/driver/status",
            json={
                "location": {
                    "lat": 34.0522 + random.uniform(-0.1, 0.1),
                    "lng": -118.2437 + random.uniform(-0.1, 0.1)
                },
                "available": True,
                "passenger_count": random.randint(0, 3)
            },
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Driver status update failed: {response.status_code}")
    
    @task(30)
    def get_passenger_suggestions(self):
        """Get content suggestions for passengers"""
        with self.client.get(
            "/api/rideshare/driver/suggestions",
            params={
                "passenger_count": 2,
                "trip_duration": 30,
                "time_of_day": "evening"
            },
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Passenger suggestions failed: {response.status_code}")


def run_load_test_scenarios():
    """Run comprehensive load test scenarios"""
    scenarios = [
        {
            "name": "Normal Load",
            "users": 100,
            "spawn_rate": 10,
            "duration": 300,  # 5 minutes
            "user_classes": [RoadTripUser]
        },
        {
            "name": "Peak Load",
            "users": 500,
            "spawn_rate": 50,
            "duration": 600,  # 10 minutes
            "user_classes": [RoadTripUser, MobileAppUser]
        },
        {
            "name": "Stress Test",
            "users": 1000,
            "spawn_rate": 100,
            "duration": 900,  # 15 minutes
            "user_classes": [RoadTripUser, MobileAppUser, RideshareDriverUser]
        },
        {
            "name": "Spike Test",
            "users": 2000,
            "spawn_rate": 500,
            "duration": 120,  # 2 minutes
            "user_classes": [RoadTripUser]
        },
        {
            "name": "Endurance Test",
            "users": 200,
            "spawn_rate": 20,
            "duration": 3600,  # 1 hour
            "user_classes": [RoadTripUser, MobileAppUser]
        }
    ]
    
    results = []
    
    for scenario in scenarios:
        print(f"\n{'='*50}")
        print(f"Running scenario: {scenario['name']}")
        print(f"Users: {scenario['users']}, Duration: {scenario['duration']}s")
        print(f"{'='*50}\n")
        
        # Setup environment
        env = Environment(user_classes=scenario['user_classes'])
        env.create_local_runner()
        
        # Start test
        env.runner.start(scenario['users'], spawn_rate=scenario['spawn_rate'])
        
        # Run for specified duration
        time.sleep(scenario['duration'])
        
        # Stop test
        env.runner.quit()
        
        # Collect results
        stats = env.stats
        result = {
            "scenario": scenario['name'],
            "total_requests": stats.total.num_requests,
            "failure_rate": stats.total.fail_ratio,
            "avg_response_time": stats.total.avg_response_time,
            "min_response_time": stats.total.min_response_time,
            "max_response_time": stats.total.max_response_time,
            "rps": stats.total.current_rps,
            "failures": stats.total.num_failures
        }
        
        results.append(result)
        
        # Cool down period
        time.sleep(30)
    
    return results


def analyze_results(results: List[Dict[str, Any]]):
    """Analyze load test results"""
    print("\n" + "="*60)
    print("LOAD TEST RESULTS SUMMARY")
    print("="*60)
    
    for result in results:
        print(f"\n{result['scenario']}:")
        print(f"  Total Requests: {result['total_requests']:,}")
        print(f"  Failure Rate: {result['failure_rate']:.2%}")
        print(f"  Average Response Time: {result['avg_response_time']:.2f}ms")
        print(f"  Min/Max Response Time: {result['min_response_time']:.2f}ms / {result['max_response_time']:.2f}ms")
        print(f"  Requests per Second: {result['rps']:.2f}")
        print(f"  Total Failures: {result['failures']:,}")
    
    # Performance thresholds
    print("\n" + "="*60)
    print("PERFORMANCE ANALYSIS")
    print("="*60)
    
    for result in results:
        print(f"\n{result['scenario']}:")
        
        # Response time analysis
        if result['avg_response_time'] < 200:
            print("  ✅ Response time: EXCELLENT")
        elif result['avg_response_time'] < 500:
            print("  ⚠️  Response time: ACCEPTABLE")
        else:
            print("  ❌ Response time: POOR")
        
        # Failure rate analysis
        if result['failure_rate'] < 0.01:
            print("  ✅ Reliability: EXCELLENT")
        elif result['failure_rate'] < 0.05:
            print("  ⚠️  Reliability: ACCEPTABLE")
        else:
            print("  ❌ Reliability: POOR")
        
        # Throughput analysis
        if result['rps'] > 100:
            print("  ✅ Throughput: EXCELLENT")
        elif result['rps'] > 50:
            print("  ⚠️  Throughput: ACCEPTABLE")
        else:
            print("  ❌ Throughput: POOR")
    
    # Save results
    with open("load_test_results.json", "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "results": results
        }, f, indent=2)
    
    print("\nResults saved to load_test_results.json")


if __name__ == "__main__":
    # Run load tests
    results = run_load_test_scenarios()
    
    # Analyze results
    analyze_results(results)