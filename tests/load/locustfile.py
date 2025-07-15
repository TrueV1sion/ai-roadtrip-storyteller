"""
Locust configuration file for load testing
Run with: locust -f locustfile.py --host=http://localhost:8000
"""
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner, WorkerRunner
import random
import json
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Initialize load test environment"""
    if isinstance(environment.runner, MasterRunner):
        logger.info("I'm on master node")
    elif isinstance(environment.runner, WorkerRunner):
        logger.info("I'm on worker node")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Actions to perform when test starts"""
    logger.info(f"Load test started with {environment.runner.target_user_count} users")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Actions to perform when test stops"""
    logger.info("Load test finished")
    
    # Print summary statistics
    stats = environment.stats
    logger.info(f"Total requests: {stats.total.num_requests}")
    logger.info(f"Total failures: {stats.total.num_failures}")
    logger.info(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    logger.info(f"RPS: {stats.total.current_rps:.2f}")


class BaseRoadTripUser(HttpUser):
    """Base class for road trip users"""
    abstract = True
    
    def on_start(self):
        """Setup user session"""
        self.user_id = random.randint(1000, 99999)
        self.email = f"test_user_{self.user_id}@example.com"
        
        # Try to login or register
        login_response = self.client.post(
            "/api/auth/login",
            json={"email": self.email, "password": "TestPassword123!"},
            catch_response=True
        )
        
        if login_response.status_code == 200:
            data = login_response.json()
            self.token = data.get("access_token")
            login_response.success()
        else:
            # Register new user
            register_response = self.client.post(
                "/api/auth/register",
                json={
                    "email": self.email,
                    "password": "TestPassword123!",
                    "full_name": f"Test User {self.user_id}"
                }
            )
            
            if register_response.status_code in [200, 201]:
                # Login after registration
                login_response = self.client.post(
                    "/api/auth/login",
                    json={"email": self.email, "password": "TestPassword123!"}
                )
                data = login_response.json()
                self.token = data.get("access_token")
        
        self.headers = {"Authorization": f"Bearer {self.token}"} if hasattr(self, 'token') else {}


class StandardUser(BaseRoadTripUser):
    """Standard user behavior pattern"""
    wait_time = between(2, 5)
    weight = 60  # 60% of users
    
    @task(40)
    def voice_assistant_query(self):
        """Most common user interaction"""
        queries = [
            "Navigate to Disneyland",
            "Find restaurants near me",
            "Tell me about this area",
            "What's the weather like?",
            "Find gas stations",
            "Book a hotel for tonight",
            "Play road trip music",
            "Find scenic routes"
        ]
        
        response = self.client.post(
            "/api/voice-assistant/interact",
            json={
                "user_input": random.choice(queries),
                "context": {
                    "origin": "San Francisco, CA",
                    "destination": "Los Angeles, CA",
                    "current_location": {
                        "lat": 36.7783 - random.random() * 2,
                        "lng": -119.4179 - random.random() * 2
                    }
                }
            },
            headers=self.headers,
            name="/api/voice-assistant/interact"
        )
    
    @task(20)
    def get_directions(self):
        """Get driving directions"""
        origins = ["San Francisco, CA", "San Jose, CA", "Oakland, CA"]
        destinations = ["Los Angeles, CA", "San Diego, CA", "Las Vegas, NV"]
        
        response = self.client.post(
            "/api/directions",
            json={
                "origin": random.choice(origins),
                "destination": random.choice(destinations),
                "preferences": {
                    "avoid_highways": random.choice([True, False]),
                    "scenic_route": random.choice([True, False])
                }
            },
            headers=self.headers,
            name="/api/directions"
        )
    
    @task(15)
    def get_stories(self):
        """Get personalized stories"""
        response = self.client.post(
            "/api/personalized-story",
            json={
                "origin": "San Francisco, CA",
                "destination": "Los Angeles, CA",
                "interests": random.sample(["history", "nature", "food", "music", "art"], 3)
            },
            headers=self.headers,
            name="/api/personalized-story"
        )
    
    @task(10)
    def search_hotels(self):
        """Search for hotels"""
        cities = ["Santa Barbara, CA", "Monterey, CA", "San Luis Obispo, CA"]
        checkin = (datetime.now() + timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d")
        checkout = (datetime.now() + timedelta(days=random.randint(2, 31))).strftime("%Y-%m-%d")
        
        response = self.client.get(
            "/api/booking/search",
            params={
                "location": random.choice(cities),
                "checkin": checkin,
                "checkout": checkout,
                "guests": random.randint(1, 4)
            },
            headers=self.headers,
            name="/api/booking/search"
        )
    
    @task(10)
    def play_game(self):
        """Play trivia game"""
        response = self.client.post(
            "/api/games/trivia/start",
            json={
                "location": {
                    "lat": 34.0522,
                    "lng": -118.2437
                },
                "difficulty": random.choice(["easy", "medium", "hard"])
            },
            headers=self.headers,
            name="/api/games/trivia/start"
        )
    
    @task(5)
    def update_preferences(self):
        """Update user preferences"""
        response = self.client.put(
            "/api/users/preferences",
            json={
                "interests": random.sample(
                    ["nature", "history", "food", "music", "art", "sports", "technology"],
                    random.randint(3, 5)
                ),
                "voice_personality": random.choice([
                    "friendly_companion",
                    "enthusiastic_guide", 
                    "knowledgeable_expert",
                    "casual_buddy"
                ])
            },
            headers=self.headers,
            name="/api/users/preferences"
        )


class PowerUser(BaseRoadTripUser):
    """Power user with complex interactions"""
    wait_time = between(1, 3)
    weight = 20  # 20% of users
    
    @task(30)
    def complex_journey_planning(self):
        """Plan complex multi-stop journey"""
        # Create journey with multiple waypoints
        response = self.client.post(
            "/api/journey/plan",
            json={
                "origin": "San Francisco, CA",
                "destination": "Los Angeles, CA",
                "waypoints": [
                    "Monterey, CA",
                    "Big Sur, CA",
                    "San Luis Obispo, CA",
                    "Santa Barbara, CA"
                ],
                "preferences": {
                    "scenic_route": True,
                    "avoid_highways": False,
                    "include_attractions": True,
                    "meal_stops": True,
                    "hotel_booking": True
                },
                "departure_date": (datetime.now() + timedelta(days=7)).isoformat()
            },
            headers=self.headers,
            name="/api/journey/plan"
        )
        
        if response.status_code == 200:
            journey_id = response.json().get("journey_id")
            
            # Get journey details
            self.client.get(
                f"/api/journey/{journey_id}/details",
                headers=self.headers,
                name="/api/journey/details"
            )
    
    @task(25)
    def event_journey_creation(self):
        """Create event-based journey"""
        events = [
            {"venue": "Hollywood Bowl", "type": "concert"},
            {"venue": "Dodger Stadium", "type": "sports"},
            {"venue": "Disneyland", "type": "theme_park"},
            {"venue": "Golden Gate Theater", "type": "theater"}
        ]
        
        event = random.choice(events)
        response = self.client.post(
            "/api/event-journey/create",
            json={
                "origin": "San Francisco, CA",
                "venue_name": event["venue"],
                "event_type": event["type"],
                "event_date": (datetime.now() + timedelta(days=14)).isoformat(),
                "preferences": {
                    "arrival_buffer": 90,
                    "include_parking": True,
                    "pre_event_dining": True
                }
            },
            headers=self.headers,
            name="/api/event-journey/create"
        )
    
    @task(20)
    def ar_experience(self):
        """Use AR features"""
        # Scan landmark
        response = self.client.post(
            "/api/ar/scan",
            json={
                "image": "mock_base64_image_data",
                "location": {
                    "lat": 37.8199,
                    "lng": -122.4783
                },
                "device_orientation": {
                    "heading": random.randint(0, 359),
                    "pitch": random.randint(-30, 30)
                }
            },
            headers=self.headers,
            name="/api/ar/scan"
        )
        
        # Get AR overlays
        self.client.get(
            "/api/ar/overlays",
            params={
                "lat": 37.8199,
                "lng": -122.4783,
                "radius": 500
            },
            headers=self.headers,
            name="/api/ar/overlays"
        )
    
    @task(15)
    def spotify_integration(self):
        """Spotify playlist generation"""
        response = self.client.get(
            "/api/spotify/road-trip-playlist",
            params={
                "origin": "San Francisco, CA",
                "destination": "Los Angeles, CA",
                "mood": random.choice(["energetic", "relaxed", "nostalgic", "adventure"]),
                "duration": random.randint(180, 480)  # 3-8 hours
            },
            headers=self.headers,
            name="/api/spotify/playlist"
        )
    
    @task(10)
    def advanced_booking(self):
        """Complex booking operations"""
        # Search and book multiple services
        checkin = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
        
        # Hotel booking
        hotel_response = self.client.get(
            "/api/booking/search",
            params={
                "location": "Santa Barbara, CA",
                "checkin": checkin,
                "checkout": (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d"),
                "guests": 2,
                "amenities": "pool,parking,breakfast"
            },
            headers=self.headers,
            name="/api/booking/search"
        )
        
        # Restaurant reservation
        self.client.post(
            "/api/reservations/restaurant",
            json={
                "restaurant_name": "The French Laundry",
                "date": checkin,
                "time": "19:00",
                "party_size": 2
            },
            headers=self.headers,
            name="/api/reservations/restaurant"
        )


class MobileUser(BaseRoadTripUser):
    """Mobile app specific user behavior"""
    wait_time = between(3, 7)
    weight = 15  # 15% of users
    
    @task(40)
    def real_time_navigation(self):
        """Real-time navigation updates"""
        # Simulate moving vehicle
        lat = 37.7749 - random.random() * 0.1
        lng = -122.4194 - random.random() * 0.1
        
        response = self.client.post(
            "/api/navigation/update",
            json={
                "location": {
                    "lat": lat,
                    "lng": lng
                },
                "speed": random.randint(0, 75),
                "heading": random.randint(0, 359)
            },
            headers=self.headers,
            name="/api/navigation/update"
        )
        
        # Get nearby points of interest
        self.client.get(
            "/api/poi/nearby",
            params={
                "lat": lat,
                "lng": lng,
                "radius": 5000,
                "types": "restaurant,gas_station,lodging"
            },
            headers=self.headers,
            name="/api/poi/nearby"
        )
    
    @task(30)
    def voice_commands(self):
        """Voice command processing"""
        commands = [
            "Hey Captain, what's nearby?",
            "Find the nearest gas station",
            "I'm hungry, what are my options?",
            "Tell me about this town",
            "How's the traffic ahead?",
            "Change music to something upbeat"
        ]
        
        response = self.client.post(
            "/api/voice/command",
            json={
                "audio": "mock_audio_data",
                "text": random.choice(commands),
                "context": {
                    "driving": True,
                    "speed": random.randint(30, 70)
                }
            },
            headers=self.headers,
            name="/api/voice/command"
        )
    
    @task(20)
    def offline_sync(self):
        """Offline data synchronization"""
        response = self.client.post(
            "/api/sync/offline",
            json={
                "last_sync": (datetime.now() - timedelta(hours=random.randint(1, 24))).isoformat(),
                "data": {
                    "saved_places": random.randint(0, 10),
                    "journey_progress": random.randint(0, 100),
                    "offline_stories": random.randint(0, 5)
                }
            },
            headers=self.headers,
            name="/api/sync/offline"
        )
    
    @task(10)
    def download_offline_content(self):
        """Download content for offline use"""
        response = self.client.post(
            "/api/offline/download",
            json={
                "content_type": random.choice(["stories", "maps", "games"]),
                "region": random.choice(["california", "nevada", "arizona"]),
                "quality": random.choice(["standard", "high"])
            },
            headers=self.headers,
            name="/api/offline/download"
        )


class RideshareUser(BaseRoadTripUser):
    """Rideshare driver behavior"""
    wait_time = between(5, 15)
    weight = 5  # 5% of users
    
    def on_start(self):
        """Initialize as rideshare driver"""
        super().on_start()
        
        # Enable driver mode
        self.client.post(
            "/api/rideshare/driver/enable",
            headers=self.headers
        )
    
    @task(50)
    def driver_status_update(self):
        """Update driver status and location"""
        response = self.client.post(
            "/api/rideshare/driver/status",
            json={
                "location": {
                    "lat": 34.0522 + random.uniform(-0.5, 0.5),
                    "lng": -118.2437 + random.uniform(-0.5, 0.5)
                },
                "available": random.choice([True, True, True, False]),  # 75% available
                "passenger_count": random.randint(0, 4)
            },
            headers=self.headers,
            name="/api/rideshare/driver/status"
        )
    
    @task(30)
    def get_passenger_content(self):
        """Get content for passengers"""
        response = self.client.get(
            "/api/rideshare/content/suggestions",
            params={
                "passenger_count": random.randint(1, 4),
                "trip_duration": random.randint(10, 60),
                "passenger_preferences": random.choice(["family", "business", "tourist"])
            },
            headers=self.headers,
            name="/api/rideshare/content"
        )
    
    @task(20)
    def trip_analytics(self):
        """Get trip analytics"""
        response = self.client.get(
            "/api/rideshare/analytics/trips",
            params={
                "period": random.choice(["today", "week", "month"]),
                "metrics": "earnings,ratings,distance"
            },
            headers=self.headers,
            name="/api/rideshare/analytics"
        )