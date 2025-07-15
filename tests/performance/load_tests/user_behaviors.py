"""
Advanced User Behavior Patterns for Load Testing
===============================================

This module defines realistic user behavior patterns for comprehensive load testing
of the AI Road Trip Storyteller application.
"""

import random
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
from locust import HttpUser, task, between, TaskSet, events
from locust.exception import RescheduleTask
import logging

logger = logging.getLogger(__name__)


class BaseRoadTripUser(HttpUser):
    """Base class with common functionality for all user types"""
    abstract = True
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id = None
        self.token = None
        self.headers = {}
        self.journey_id = None
        self.current_location = {
            "lat": 37.7749,  # San Francisco
            "lng": -122.4194
        }
        
    def on_start(self):
        """Initialize user session"""
        self.authenticate()
        self.setup_user_profile()
        
    def authenticate(self):
        """Authenticate user and get token"""
        email = f"loadtest_{random.randint(10000, 99999)}@example.com"
        password = "LoadTest123!"
        
        # Try login first
        with self.client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.user_id = data.get("user_id")
                response.success()
            else:
                # Register new user
                with self.client.post(
                    "/api/auth/register",
                    json={
                        "email": email,
                        "password": password,
                        "full_name": f"Load Test User {random.randint(1000, 9999)}"
                    },
                    catch_response=True
                ) as reg_response:
                    if reg_response.status_code in [200, 201]:
                        # Login after registration
                        self.authenticate()
                        reg_response.success()
                    else:
                        reg_response.failure(f"Registration failed: {reg_response.status_code}")
                        
        self.headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        
    def setup_user_profile(self):
        """Setup user preferences and profile"""
        if not self.token:
            return
            
        preferences = {
            "interests": random.sample(
                ["history", "nature", "food", "music", "art", "adventure", "culture", "photography"],
                random.randint(3, 5)
            ),
            "voice_personality": random.choice([
                "friendly_companion", "enthusiastic_guide", "knowledgeable_expert",
                "casual_buddy", "zen_master", "comedy_captain", "professor_knowitall"
            ]),
            "language": "en",
            "accessibility": {
                "large_text": random.choice([True, False]),
                "voice_speed": random.choice(["slow", "normal", "fast"]),
                "simplified_interface": random.choice([True, False])
            }
        }
        
        self.client.put(
            "/api/users/preferences",
            json=preferences,
            headers=self.headers
        )
        
    def update_location(self, lat_delta: float = 0.01, lng_delta: float = 0.01):
        """Simulate movement by updating location"""
        self.current_location["lat"] += random.uniform(-lat_delta, lat_delta)
        self.current_location["lng"] += random.uniform(-lng_delta, lng_delta)


class StandardTravelerUser(BaseRoadTripUser):
    """Standard road trip user - 60% of traffic"""
    wait_time = between(2, 5)
    weight = 60
    
    @task(40)
    def voice_interaction(self):
        """Primary interaction method - voice commands"""
        commands = [
            "Hey Captain, navigate to Disneyland",
            "Find me a good restaurant nearby",
            "Tell me about this area",
            "What's the weather like ahead?",
            "Find the nearest gas station",
            "Play some road trip music",
            "How long until we reach our destination?",
            "Find a scenic route to our destination",
            "Tell me a story about this place",
            "Find hotels for tonight"
        ]
        
        with self.client.post(
            "/api/voice-assistant/interact",
            json={
                "user_input": random.choice(commands),
                "context": {
                    "origin": "San Francisco, CA",
                    "destination": "Los Angeles, CA",
                    "current_location": self.current_location,
                    "speed": random.randint(0, 75),
                    "time_of_day": datetime.now().strftime("%H:%M")
                }
            },
            headers=self.headers,
            name="/api/voice-assistant/interact",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                # Simulate processing time for voice response
                time.sleep(random.uniform(0.5, 2))
                response.success()
            else:
                response.failure(f"Voice command failed: {response.status_code}")
                
    @task(20)
    def get_personalized_stories(self):
        """Get AI-generated stories during journey"""
        story_types = ["historical", "local_legend", "nature", "cultural", "funny", "educational"]
        
        with self.client.post(
            "/api/personalized-story",
            json={
                "origin": "San Francisco, CA",
                "destination": "Los Angeles, CA",
                "current_location": self.current_location,
                "story_type": random.choice(story_types),
                "interests": ["history", "nature", "local_culture"],
                "duration": random.choice(["short", "medium", "long"])
            },
            headers=self.headers,
            name="/api/personalized-story",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                # Simulate listening to story
                story_duration = random.uniform(30, 180)  # 30s to 3min
                time.sleep(min(story_duration, 5))  # Cap at 5s for testing
                response.success()
            else:
                response.failure(f"Story generation failed: {response.status_code}")
                
    @task(15)
    def search_points_of_interest(self):
        """Search for nearby points of interest"""
        poi_types = ["restaurant", "gas_station", "hotel", "attraction", "rest_area", "scenic_viewpoint"]
        
        with self.client.get(
            "/api/poi/search",
            params={
                "lat": self.current_location["lat"],
                "lng": self.current_location["lng"],
                "radius": random.choice([5000, 10000, 25000]),  # 5-25km
                "types": random.choice(poi_types)
            },
            headers=self.headers,
            name="/api/poi/search",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
                self.update_location()
            else:
                response.failure(f"POI search failed: {response.status_code}")
                
    @task(10)
    def get_directions(self):
        """Get navigation directions"""
        destinations = [
            "Los Angeles, CA", "San Diego, CA", "Las Vegas, NV",
            "Santa Barbara, CA", "Monterey, CA", "Yosemite National Park"
        ]
        
        with self.client.post(
            "/api/directions",
            json={
                "origin": f"{self.current_location['lat']},{self.current_location['lng']}",
                "destination": random.choice(destinations),
                "preferences": {
                    "avoid_tolls": random.choice([True, False]),
                    "avoid_highways": random.choice([True, False]),
                    "scenic_route": random.choice([True, False])
                }
            },
            headers=self.headers,
            name="/api/directions",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Directions failed: {response.status_code}")
                
    @task(10)
    def play_road_trip_games(self):
        """Play interactive games during trip"""
        games = ["trivia", "20_questions", "license_plate_game", "road_sign_bingo"]
        
        game_type = random.choice(games)
        with self.client.post(
            f"/api/games/{game_type}/start",
            json={
                "location": self.current_location,
                "difficulty": random.choice(["easy", "medium", "hard"]),
                "players": random.randint(1, 4)
            },
            headers=self.headers,
            name=f"/api/games/{game_type}/start",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                game_id = response.json().get("game_id")
                response.success()
                
                # Play a few rounds
                for _ in range(random.randint(1, 5)):
                    self.client.post(
                        f"/api/games/{game_type}/{game_id}/play",
                        json={"action": "answer", "value": random.choice(["A", "B", "C", "D"])},
                        headers=self.headers,
                        name=f"/api/games/{game_type}/play"
                    )
                    time.sleep(random.uniform(1, 3))
            else:
                response.failure(f"Game start failed: {response.status_code}")
                
    @task(5)
    def check_weather(self):
        """Check weather conditions"""
        with self.client.get(
            "/api/weather/current",
            params={
                "lat": self.current_location["lat"],
                "lng": self.current_location["lng"]
            },
            headers=self.headers,
            name="/api/weather/current",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Weather check failed: {response.status_code}")


class PowerTravelerUser(BaseRoadTripUser):
    """Power users with complex interactions - 20% of traffic"""
    wait_time = between(1, 3)
    weight = 20
    
    def on_start(self):
        """Initialize power user with journey planning"""
        super().on_start()
        self.create_journey_plan()
        
    def create_journey_plan(self):
        """Create a comprehensive journey plan"""
        with self.client.post(
            "/api/journey/plan",
            json={
                "origin": "San Francisco, CA",
                "destination": "Los Angeles, CA",
                "waypoints": [
                    "Half Moon Bay, CA",
                    "Santa Cruz, CA",
                    "Monterey, CA",
                    "Big Sur, CA",
                    "San Luis Obispo, CA",
                    "Santa Barbara, CA"
                ],
                "preferences": {
                    "scenic_route": True,
                    "include_attractions": True,
                    "meal_stops": True,
                    "hotel_booking": True,
                    "ev_charging": random.choice([True, False])
                },
                "departure_date": (datetime.now() + timedelta(days=random.randint(1, 30))).isoformat(),
                "trip_duration_days": random.randint(2, 7)
            },
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                self.journey_id = response.json().get("journey_id")
                response.success()
            else:
                response.failure(f"Journey planning failed: {response.status_code}")
                
    @task(30)
    def complex_voice_interactions(self):
        """Complex multi-turn voice conversations"""
        conversation_starters = [
            "Plan a romantic weekend getaway to wine country",
            "I want to visit all the national parks in California",
            "Find the best surf spots along the coast",
            "Create a foodie tour of Los Angeles",
            "Plan a family trip to Disneyland with stops along the way"
        ]
        
        # Start conversation
        with self.client.post(
            "/api/voice-assistant/conversation/start",
            json={
                "initial_query": random.choice(conversation_starters),
                "context": {
                    "location": self.current_location,
                    "preferences": {
                        "budget": random.choice(["economy", "moderate", "luxury"]),
                        "interests": ["food", "nature", "culture", "adventure"]
                    }
                }
            },
            headers=self.headers,
            name="/api/voice-assistant/conversation",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                conversation_id = response.json().get("conversation_id")
                response.success()
                
                # Continue conversation
                follow_ups = [
                    "What about restaurants?",
                    "Can you book that for me?",
                    "What's the weather forecast?",
                    "Any special events happening?",
                    "Change the route to avoid highways"
                ]
                
                for follow_up in random.sample(follow_ups, random.randint(1, 3)):
                    self.client.post(
                        f"/api/voice-assistant/conversation/{conversation_id}/continue",
                        json={"query": follow_up},
                        headers=self.headers,
                        name="/api/voice-assistant/conversation/continue"
                    )
                    time.sleep(random.uniform(1, 3))
            else:
                response.failure(f"Conversation start failed: {response.status_code}")
                
    @task(25)
    def integrated_booking_flow(self):
        """Complete booking flow with multiple services"""
        checkin_date = (datetime.now() + timedelta(days=random.randint(1, 60))).strftime("%Y-%m-%d")
        checkout_date = (datetime.now() + timedelta(days=random.randint(2, 61))).strftime("%Y-%m-%d")
        
        # Search hotels
        with self.client.get(
            "/api/booking/hotels/search",
            params={
                "location": "Santa Barbara, CA",
                "checkin": checkin_date,
                "checkout": checkout_date,
                "guests": random.randint(1, 4),
                "amenities": "pool,parking,breakfast,pet_friendly"
            },
            headers=self.headers,
            name="/api/booking/hotels/search",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                hotels = response.json().get("hotels", [])
                response.success()
                
                if hotels:
                    # Book hotel
                    hotel = random.choice(hotels[:5])  # Pick from top 5
                    self.client.post(
                        "/api/booking/hotels/reserve",
                        json={
                            "hotel_id": hotel["id"],
                            "checkin": checkin_date,
                            "checkout": checkout_date,
                            "room_type": hotel["room_types"][0]["id"],
                            "special_requests": "Late checkout please"
                        },
                        headers=self.headers,
                        name="/api/booking/hotels/reserve"
                    )
                    
        # Search restaurants
        with self.client.post(
            "/api/booking/restaurants/search",
            json={
                "location": "Santa Barbara, CA",
                "date": checkin_date,
                "time": "19:00",
                "party_size": random.randint(2, 6),
                "cuisine": random.choice(["italian", "seafood", "american", "mexican"])
            },
            headers=self.headers,
            name="/api/booking/restaurants/search",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
                
    @task(20)
    def event_based_journey(self):
        """Plan journey around specific events"""
        events = [
            {"venue": "Hollywood Bowl", "type": "concert", "artist": "Los Angeles Philharmonic"},
            {"venue": "Dodger Stadium", "type": "sports", "team": "LA Dodgers"},
            {"venue": "Coachella Valley", "type": "festival", "name": "Coachella"},
            {"venue": "San Diego Comic-Con", "type": "convention", "name": "Comic-Con"},
            {"venue": "Monterey Bay Aquarium", "type": "attraction", "name": "Special Exhibition"}
        ]
        
        event = random.choice(events)
        event_date = (datetime.now() + timedelta(days=random.randint(7, 90))).isoformat()
        
        with self.client.post(
            "/api/event-journey/create",
            json={
                "origin": "San Francisco, CA",
                "event": event,
                "event_date": event_date,
                "preferences": {
                    "arrival_buffer_minutes": random.choice([60, 90, 120]),
                    "include_parking": True,
                    "pre_event_dining": True,
                    "post_event_hotel": True,
                    "vip_experience": random.choice([True, False])
                }
            },
            headers=self.headers,
            name="/api/event-journey/create",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                journey_id = response.json().get("journey_id")
                response.success()
                
                # Get journey details
                self.client.get(
                    f"/api/event-journey/{journey_id}/details",
                    headers=self.headers,
                    name="/api/event-journey/details"
                )
            else:
                response.failure(f"Event journey creation failed: {response.status_code}")
                
    @task(15)
    def ar_experiences(self):
        """Augmented reality interactions"""
        # Scan landmark
        with self.client.post(
            "/api/ar/landmark/scan",
            json={
                "image_data": "base64_encoded_image_mock",
                "location": self.current_location,
                "device_info": {
                    "orientation": {
                        "heading": random.randint(0, 359),
                        "pitch": random.randint(-45, 45),
                        "roll": random.randint(-10, 10)
                    },
                    "camera_fov": 60
                }
            },
            headers=self.headers,
            name="/api/ar/landmark/scan",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                landmark_info = response.json()
                response.success()
                
                # Get AR overlays
                self.client.get(
                    "/api/ar/overlays",
                    params={
                        "lat": self.current_location["lat"],
                        "lng": self.current_location["lng"],
                        "radius": 1000,
                        "types": "historical,cultural,natural"
                    },
                    headers=self.headers,
                    name="/api/ar/overlays"
                )
            else:
                response.failure(f"AR scan failed: {response.status_code}")
                
    @task(10)
    def spotify_integration(self):
        """Spotify playlist management"""
        moods = ["road_trip_classics", "energetic", "relaxed", "nostalgic", "discovery"]
        
        with self.client.get(
            "/api/spotify/generate-playlist",
            params={
                "origin": "San Francisco, CA",
                "destination": "Los Angeles, CA",
                "mood": random.choice(moods),
                "duration_hours": random.randint(2, 8),
                "include_local_artists": True
            },
            headers=self.headers,
            name="/api/spotify/generate-playlist",
            catch_response=True
        ) as response:
            if response.status_code in [200, 401]:  # 401 if not connected to Spotify
                response.success()
            else:
                response.failure(f"Spotify playlist generation failed: {response.status_code}")


class MobileAppUser(BaseRoadTripUser):
    """Mobile-specific user behavior - 15% of traffic"""
    wait_time = between(3, 7)
    weight = 15
    
    def on_start(self):
        """Mobile app startup sequence"""
        # App initialization
        self.client.get("/api/health/mobile", name="/api/health/mobile")
        self.client.get("/api/config/mobile", name="/api/config/mobile")
        
        # Device registration
        self.device_id = f"device_{random.randint(100000, 999999)}"
        self.client.post(
            "/api/devices/register",
            json={
                "device_id": self.device_id,
                "platform": random.choice(["ios", "android"]),
                "app_version": "2.1.0",
                "os_version": random.choice(["iOS 17.0", "Android 14"])
            },
            name="/api/devices/register"
        )
        
        super().on_start()
        
    @task(40)
    def real_time_navigation(self):
        """Real-time navigation with continuous updates"""
        # Simulate driving
        for _ in range(random.randint(5, 15)):
            self.update_location(0.001, 0.001)  # Small movements
            
            with self.client.post(
                "/api/navigation/update",
                json={
                    "location": self.current_location,
                    "speed": random.randint(0, 75),
                    "heading": random.randint(0, 359),
                    "altitude": random.randint(0, 1000),
                    "accuracy": random.uniform(5, 20)
                },
                headers=self.headers,
                name="/api/navigation/update",
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Navigation update failed: {response.status_code}")
                    
            # Get nearby alerts
            if random.random() < 0.3:  # 30% chance
                self.client.get(
                    "/api/navigation/alerts",
                    params={
                        "lat": self.current_location["lat"],
                        "lng": self.current_location["lng"],
                        "radius": 5000
                    },
                    headers=self.headers,
                    name="/api/navigation/alerts"
                )
                
            time.sleep(random.uniform(1, 3))  # Update interval
            
    @task(25)
    def voice_commands_driving_mode(self):
        """Voice commands optimized for driving"""
        driving_commands = [
            "Find the nearest rest stop",
            "How's traffic ahead?",
            "Find gas under $4",
            "Call home",
            "Text my ETA to mom",
            "Skip this song",
            "Volume up",
            "Find Starbucks on my route"
        ]
        
        with self.client.post(
            "/api/voice/driving-mode",
            json={
                "command": random.choice(driving_commands),
                "context": {
                    "driving": True,
                    "speed": random.randint(40, 70),
                    "hands_free": True,
                    "location": self.current_location
                }
            },
            headers=self.headers,
            name="/api/voice/driving-mode",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Driving mode voice command failed: {response.status_code}")
                
    @task(20)
    def offline_content_sync(self):
        """Download and sync offline content"""
        content_types = ["maps", "stories", "games", "poi_data"]
        
        # Check what needs syncing
        with self.client.get(
            "/api/offline/status",
            headers=self.headers,
            name="/api/offline/status",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
                
                # Download content
                for content_type in random.sample(content_types, random.randint(1, 3)):
                    self.client.post(
                        "/api/offline/download",
                        json={
                            "content_type": content_type,
                            "region": {
                                "center": self.current_location,
                                "radius_km": random.choice([50, 100, 200])
                            },
                            "quality": random.choice(["standard", "high"])
                        },
                        headers=self.headers,
                        name="/api/offline/download"
                    )
            else:
                response.failure(f"Offline status check failed: {response.status_code}")
                
    @task(10)
    def camera_features(self):
        """Camera-based features (photo spots, AR)"""
        with self.client.post(
            "/api/camera/photo-spot",
            json={
                "location": self.current_location,
                "image_metadata": {
                    "width": 4032,
                    "height": 3024,
                    "orientation": "landscape"
                }
            },
            headers=self.headers,
            name="/api/camera/photo-spot",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
                
                # Share photo
                if random.random() < 0.3:  # 30% chance
                    self.client.post(
                        "/api/social/share",
                        json={
                            "type": "photo",
                            "location": self.current_location,
                            "caption": "Amazing view on our road trip!",
                            "tags": ["roadtrip", "california", "travel"]
                        },
                        headers=self.headers,
                        name="/api/social/share"
                    )
            else:
                response.failure(f"Photo spot detection failed: {response.status_code}")
                
    @task(5)
    def app_settings_sync(self):
        """Sync app settings and preferences"""
        with self.client.post(
            "/api/settings/sync",
            json={
                "device_id": self.device_id,
                "settings": {
                    "notifications": {
                        "traffic_alerts": True,
                        "poi_suggestions": True,
                        "story_updates": False
                    },
                    "privacy": {
                        "location_sharing": "friends_only",
                        "trip_history": True
                    },
                    "display": {
                        "theme": random.choice(["light", "dark", "auto"]),
                        "map_style": random.choice(["standard", "satellite", "terrain"])
                    }
                }
            },
            headers=self.headers,
            name="/api/settings/sync",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Settings sync failed: {response.status_code}")


class RideshareDriverUser(BaseRoadTripUser):
    """Rideshare driver behavior - 5% of traffic"""
    wait_time = between(5, 15)
    weight = 5
    
    def on_start(self):
        """Initialize rideshare driver mode"""
        super().on_start()
        
        # Enable driver mode
        with self.client.post(
            "/api/rideshare/driver/enable",
            json={
                "vehicle_info": {
                    "make": random.choice(["Toyota", "Honda", "Tesla", "Ford"]),
                    "model": random.choice(["Camry", "Accord", "Model 3", "Fusion"]),
                    "year": random.randint(2018, 2024),
                    "capacity": random.randint(3, 6)
                },
                "driver_preferences": {
                    "max_distance_km": random.choice([50, 100, 200]),
                    "passenger_rating_min": random.choice([4.0, 4.5, 4.7]),
                    "trip_types": ["airport", "city", "long_distance"]
                }
            },
            headers=self.headers,
            name="/api/rideshare/driver/enable",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                self.driver_id = response.json().get("driver_id")
                response.success()
            else:
                response.failure(f"Driver mode activation failed: {response.status_code}")
                
    @task(50)
    def driver_status_updates(self):
        """Regular driver status updates"""
        statuses = ["available", "busy", "offline"]
        weights = [0.7, 0.2, 0.1]  # 70% available, 20% busy, 10% offline
        
        status = random.choices(statuses, weights=weights)[0]
        
        with self.client.post(
            "/api/rideshare/driver/status",
            json={
                "status": status,
                "location": self.current_location,
                "passenger_count": random.randint(0, 4) if status == "busy" else 0,
                "estimated_arrival": random.randint(5, 30) if status == "busy" else None
            },
            headers=self.headers,
            name="/api/rideshare/driver/status",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
                self.update_location(0.005, 0.005)  # Driver movement
            else:
                response.failure(f"Driver status update failed: {response.status_code}")
                
    @task(30)
    def passenger_entertainment(self):
        """Get content for passenger entertainment"""
        passenger_profiles = [
            {"type": "family", "ages": [35, 33, 8, 6]},
            {"type": "business", "interests": ["tech", "finance"]},
            {"type": "tourist", "origin": "international"},
            {"type": "student", "destination": "university"}
        ]
        
        profile = random.choice(passenger_profiles)
        
        with self.client.get(
            "/api/rideshare/content/suggestions",
            params={
                "passenger_profile": json.dumps(profile),
                "trip_duration_minutes": random.randint(10, 90),
                "time_of_day": datetime.now().strftime("%H:%M"),
                "route": f"{self.current_location['lat']},{self.current_location['lng']}"
            },
            headers=self.headers,
            name="/api/rideshare/content/suggestions",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                content = response.json()
                response.success()
                
                # Start content playback
                if content.get("stories"):
                    self.client.post(
                        "/api/rideshare/content/play",
                        json={
                            "content_id": content["stories"][0]["id"],
                            "passenger_count": len(profile.get("ages", [1]))
                        },
                        headers=self.headers,
                        name="/api/rideshare/content/play"
                    )
            else:
                response.failure(f"Content suggestions failed: {response.status_code}")
                
    @task(15)
    def trip_optimization(self):
        """Optimize route for multiple passengers"""
        with self.client.post(
            "/api/rideshare/route/optimize",
            json={
                "current_location": self.current_location,
                "pickups": [
                    {"lat": self.current_location["lat"] + 0.01, "lng": self.current_location["lng"] + 0.01},
                    {"lat": self.current_location["lat"] - 0.01, "lng": self.current_location["lng"] + 0.02}
                ],
                "dropoffs": [
                    {"lat": self.current_location["lat"] + 0.05, "lng": self.current_location["lng"] - 0.03},
                    {"lat": self.current_location["lat"] + 0.08, "lng": self.current_location["lng"] + 0.05}
                ],
                "preferences": {
                    "minimize": random.choice(["time", "distance", "cost"]),
                    "avoid_highways": False
                }
            },
            headers=self.headers,
            name="/api/rideshare/route/optimize",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Route optimization failed: {response.status_code}")
                
    @task(5)
    def earnings_dashboard(self):
        """Check earnings and statistics"""
        periods = ["today", "week", "month"]
        
        with self.client.get(
            "/api/rideshare/driver/earnings",
            params={
                "period": random.choice(periods),
                "include_tips": True,
                "include_bonuses": True
            },
            headers=self.headers,
            name="/api/rideshare/driver/earnings",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Earnings dashboard failed: {response.status_code}")


class StressTestUser(BaseRoadTripUser):
    """Aggressive user for stress testing"""
    wait_time = between(0.1, 0.5)  # Very aggressive
    
    @task(50)
    def rapid_fire_requests(self):
        """Send rapid requests to stress the system"""
        endpoints = [
            ("/api/voice-assistant/interact", "POST"),
            ("/api/directions", "POST"),
            ("/api/poi/search", "GET"),
            ("/api/weather/current", "GET"),
            ("/api/stories/generate", "POST")
        ]
        
        endpoint, method = random.choice(endpoints)
        
        if method == "POST":
            data = {
                "query": "stress test",
                "location": self.current_location,
                "timestamp": datetime.now().isoformat()
            }
            response = self.client.post(endpoint, json=data, headers=self.headers)
        else:
            params = {
                "lat": self.current_location["lat"],
                "lng": self.current_location["lng"]
            }
            response = self.client.get(endpoint, params=params, headers=self.headers)
            
    @task(30)
    def concurrent_ai_requests(self):
        """Multiple concurrent AI requests"""
        queries = [
            "Generate a story about the area",
            "What's interesting nearby?",
            "Plan my route",
            "Find restaurants"
        ]
        
        # Fire multiple requests without waiting
        for query in random.sample(queries, random.randint(2, 4)):
            self.client.post(
                "/api/ai/query",
                json={"query": query, "context": self.current_location},
                headers=self.headers,
                name="/api/ai/query"
            )
            
    @task(20)
    def large_payload_requests(self):
        """Send requests with large payloads"""
        # Large journey with many waypoints
        waypoints = [
            {"lat": self.current_location["lat"] + i * 0.01, "lng": self.current_location["lng"] + i * 0.01}
            for i in range(50)  # 50 waypoints
        ]
        
        self.client.post(
            "/api/journey/calculate",
            json={
                "origin": self.current_location,
                "destination": {"lat": 34.0522, "lng": -118.2437},
                "waypoints": waypoints,
                "options": {
                    "optimize": True,
                    "include_alternates": True,
                    "detailed_instructions": True
                }
            },
            headers=self.headers,
            name="/api/journey/calculate"
        )


# User class registry
USER_CLASSES = [
    StandardTravelerUser,
    PowerTravelerUser,
    MobileAppUser,
    RideshareDriverUser,
    StressTestUser
]