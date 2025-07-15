"""
Simulation Engine for AI Road Trip Storyteller
Generates realistic user behaviors and journey scenarios for testing
"""

import asyncio
import json
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import httpx
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UserPersona(Enum):
    FAMILY_VACATION = "family_vacation"
    BUSINESS_TRAVELER = "business_traveler"
    RIDESHARE_DRIVER = "rideshare_driver"
    ADVENTURE_SEEKER = "adventure_seeker"
    HISTORY_BUFF = "history_buff"
    FOODIE_EXPLORER = "foodie_explorer"
    NATURE_LOVER = "nature_lover"
    COUPLE_ROMANTIC = "couple_romantic"
    SOLO_WANDERER = "solo_wanderer"
    GROUP_FRIENDS = "group_friends"


class JourneyType(Enum):
    DAILY_COMMUTE = "daily_commute"
    WEEKEND_TRIP = "weekend_trip"
    CROSS_COUNTRY = "cross_country"
    SCENIC_ROUTE = "scenic_route"
    BUSINESS_TRIP = "business_trip"
    FOOD_TOUR = "food_tour"
    HISTORICAL_TOUR = "historical_tour"
    NATURE_EXPLORATION = "nature_exploration"


class VoicePersonality(Enum):
    ENTHUSIASTIC_GUIDE = "enthusiastic_guide"
    CALM_NARRATOR = "calm_narrator"
    WITTY_COMPANION = "witty_companion"
    EDUCATIONAL_EXPERT = "educational_expert"
    MYSTICAL_STORYTELLER = "mystical_storyteller"


@dataclass
class SimulatedUser:
    id: str
    persona: UserPersona
    age_group: str
    preferences: Dict[str, Any]
    voice_personality: VoicePersonality
    interaction_frequency: float  # 0-1, how often they interact
    booking_probability: float  # 0-1, likelihood to make bookings
    created_at: datetime
    
    
@dataclass
class SimulatedJourney:
    id: str
    user_id: str
    journey_type: JourneyType
    origin: Dict[str, float]
    destination: Dict[str, float]
    waypoints: List[Dict[str, Any]]
    start_time: datetime
    estimated_duration: int  # minutes
    weather_condition: str
    traffic_level: str
    

@dataclass
class SimulatedInteraction:
    timestamp: datetime
    user_id: str
    journey_id: str
    interaction_type: str
    command: str
    response_time: float
    success: bool
    metadata: Dict[str, Any]


class SimulationEngine:
    """Main simulation engine for generating and managing test scenarios"""
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.users: Dict[str, SimulatedUser] = {}
        self.journeys: Dict[str, SimulatedJourney] = {}
        self.interactions: List[SimulatedInteraction] = []
        self.metrics = {
            "total_users": 0,
            "total_journeys": 0,
            "total_interactions": 0,
            "bookings_requested": 0,
            "bookings_completed": 0,
            "errors": 0,
            "response_times": []
        }
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
        self.executor.shutdown(wait=True)
        
    def generate_users(self, count: int) -> List[SimulatedUser]:
        """Generate diverse user profiles"""
        users = []
        
        persona_weights = {
            UserPersona.FAMILY_VACATION: 0.25,
            UserPersona.BUSINESS_TRAVELER: 0.15,
            UserPersona.RIDESHARE_DRIVER: 0.10,
            UserPersona.ADVENTURE_SEEKER: 0.10,
            UserPersona.HISTORY_BUFF: 0.08,
            UserPersona.FOODIE_EXPLORER: 0.08,
            UserPersona.NATURE_LOVER: 0.08,
            UserPersona.COUPLE_ROMANTIC: 0.08,
            UserPersona.SOLO_WANDERER: 0.04,
            UserPersona.GROUP_FRIENDS: 0.04
        }
        
        for i in range(count):
            # Select persona based on weights
            persona = random.choices(
                list(persona_weights.keys()),
                weights=list(persona_weights.values())
            )[0]
            
            user = SimulatedUser(
                id=f"sim_user_{i}_{int(time.time())}",
                persona=persona,
                age_group=self._get_age_group(persona),
                preferences=self._get_preferences(persona),
                voice_personality=self._get_voice_personality(persona),
                interaction_frequency=self._get_interaction_frequency(persona),
                booking_probability=self._get_booking_probability(persona),
                created_at=datetime.now()
            )
            
            users.append(user)
            self.users[user.id] = user
            
        self.metrics["total_users"] += count
        logger.info(f"Generated {count} simulated users")
        return users
        
    def _get_age_group(self, persona: UserPersona) -> str:
        """Get appropriate age group for persona"""
        age_groups = {
            UserPersona.FAMILY_VACATION: random.choice(["25-34", "35-44", "45-54"]),
            UserPersona.BUSINESS_TRAVELER: random.choice(["25-34", "35-44", "45-54", "55-64"]),
            UserPersona.RIDESHARE_DRIVER: random.choice(["18-24", "25-34", "35-44"]),
            UserPersona.ADVENTURE_SEEKER: random.choice(["18-24", "25-34", "35-44"]),
            UserPersona.HISTORY_BUFF: random.choice(["35-44", "45-54", "55-64", "65+"]),
            UserPersona.FOODIE_EXPLORER: random.choice(["25-34", "35-44", "45-54"]),
            UserPersona.NATURE_LOVER: random.choice(["25-34", "35-44", "45-54", "55-64"]),
            UserPersona.COUPLE_ROMANTIC: random.choice(["25-34", "35-44"]),
            UserPersona.SOLO_WANDERER: random.choice(["18-24", "25-34", "35-44"]),
            UserPersona.GROUP_FRIENDS: random.choice(["18-24", "25-34"])
        }
        return age_groups.get(persona, "25-34")
        
    def _get_preferences(self, persona: UserPersona) -> Dict[str, Any]:
        """Generate preferences based on persona"""
        base_prefs = {
            "interests": [],
            "pace": "moderate",
            "detail_level": "balanced",
            "music_preference": "mixed",
            "stop_frequency": "moderate"
        }
        
        persona_prefs = {
            UserPersona.FAMILY_VACATION: {
                "interests": ["family-friendly", "educational", "entertainment"],
                "pace": "relaxed",
                "detail_level": "simple",
                "music_preference": "family",
                "stop_frequency": "frequent"
            },
            UserPersona.BUSINESS_TRAVELER: {
                "interests": ["efficiency", "local-insights", "dining"],
                "pace": "fast",
                "detail_level": "concise",
                "music_preference": "background",
                "stop_frequency": "minimal"
            },
            UserPersona.RIDESHARE_DRIVER: {
                "interests": ["traffic", "efficiency", "local-knowledge"],
                "pace": "efficient",
                "detail_level": "minimal",
                "music_preference": "popular",
                "stop_frequency": "none"
            },
            UserPersona.ADVENTURE_SEEKER: {
                "interests": ["adventure", "outdoor", "unique-experiences"],
                "pace": "flexible",
                "detail_level": "detailed",
                "music_preference": "energetic",
                "stop_frequency": "frequent"
            },
            UserPersona.HISTORY_BUFF: {
                "interests": ["history", "culture", "architecture"],
                "pace": "relaxed",
                "detail_level": "comprehensive",
                "music_preference": "classical",
                "stop_frequency": "frequent"
            },
            UserPersona.FOODIE_EXPLORER: {
                "interests": ["cuisine", "local-food", "restaurants"],
                "pace": "relaxed",
                "detail_level": "detailed",
                "music_preference": "cultural",
                "stop_frequency": "frequent"
            },
            UserPersona.NATURE_LOVER: {
                "interests": ["nature", "hiking", "scenic-views"],
                "pace": "relaxed",
                "detail_level": "balanced",
                "music_preference": "ambient",
                "stop_frequency": "moderate"
            }
        }
        
        return persona_prefs.get(persona, base_prefs)
        
    def _get_voice_personality(self, persona: UserPersona) -> VoicePersonality:
        """Select appropriate voice personality for persona"""
        personality_map = {
            UserPersona.FAMILY_VACATION: VoicePersonality.ENTHUSIASTIC_GUIDE,
            UserPersona.BUSINESS_TRAVELER: VoicePersonality.CALM_NARRATOR,
            UserPersona.RIDESHARE_DRIVER: VoicePersonality.CALM_NARRATOR,
            UserPersona.ADVENTURE_SEEKER: VoicePersonality.ENTHUSIASTIC_GUIDE,
            UserPersona.HISTORY_BUFF: VoicePersonality.EDUCATIONAL_EXPERT,
            UserPersona.FOODIE_EXPLORER: VoicePersonality.WITTY_COMPANION,
            UserPersona.NATURE_LOVER: VoicePersonality.MYSTICAL_STORYTELLER,
            UserPersona.COUPLE_ROMANTIC: VoicePersonality.MYSTICAL_STORYTELLER,
            UserPersona.SOLO_WANDERER: VoicePersonality.WITTY_COMPANION,
            UserPersona.GROUP_FRIENDS: VoicePersonality.WITTY_COMPANION
        }
        return personality_map.get(persona, VoicePersonality.CALM_NARRATOR)
        
    def _get_interaction_frequency(self, persona: UserPersona) -> float:
        """Get interaction frequency based on persona"""
        frequencies = {
            UserPersona.FAMILY_VACATION: 0.7,
            UserPersona.BUSINESS_TRAVELER: 0.3,
            UserPersona.RIDESHARE_DRIVER: 0.2,
            UserPersona.ADVENTURE_SEEKER: 0.8,
            UserPersona.HISTORY_BUFF: 0.9,
            UserPersona.FOODIE_EXPLORER: 0.6,
            UserPersona.NATURE_LOVER: 0.5,
            UserPersona.COUPLE_ROMANTIC: 0.4,
            UserPersona.SOLO_WANDERER: 0.6,
            UserPersona.GROUP_FRIENDS: 0.8
        }
        # Add some randomness
        base = frequencies.get(persona, 0.5)
        return max(0.1, min(1.0, base + random.uniform(-0.1, 0.1)))
        
    def _get_booking_probability(self, persona: UserPersona) -> float:
        """Get booking probability based on persona"""
        probabilities = {
            UserPersona.FAMILY_VACATION: 0.6,
            UserPersona.BUSINESS_TRAVELER: 0.7,
            UserPersona.RIDESHARE_DRIVER: 0.0,
            UserPersona.ADVENTURE_SEEKER: 0.4,
            UserPersona.HISTORY_BUFF: 0.5,
            UserPersona.FOODIE_EXPLORER: 0.8,
            UserPersona.NATURE_LOVER: 0.3,
            UserPersona.COUPLE_ROMANTIC: 0.7,
            UserPersona.SOLO_WANDERER: 0.2,
            UserPersona.GROUP_FRIENDS: 0.5
        }
        base = probabilities.get(persona, 0.4)
        return max(0.0, min(1.0, base + random.uniform(-0.1, 0.1)))
        
    async def simulate_journey(self, user: SimulatedUser) -> SimulatedJourney:
        """Simulate a journey for a user"""
        journey_type = self._select_journey_type(user.persona)
        
        # Generate route based on journey type
        origin, destination, waypoints = self._generate_route(journey_type)
        
        # Generate journey timing
        start_time = self._generate_start_time(journey_type)
        duration = self._estimate_duration(journey_type, origin, destination)
        
        journey = SimulatedJourney(
            id=f"sim_journey_{user.id}_{int(time.time())}",
            user_id=user.id,
            journey_type=journey_type,
            origin=origin,
            destination=destination,
            waypoints=waypoints,
            start_time=start_time,
            estimated_duration=duration,
            weather_condition=self._generate_weather(),
            traffic_level=self._generate_traffic(start_time)
        )
        
        self.journeys[journey.id] = journey
        self.metrics["total_journeys"] += 1
        
        logger.info(f"Generated journey {journey.id} for user {user.id}")
        return journey
        
    def _select_journey_type(self, persona: UserPersona) -> JourneyType:
        """Select appropriate journey type for persona"""
        journey_map = {
            UserPersona.FAMILY_VACATION: [
                JourneyType.WEEKEND_TRIP,
                JourneyType.SCENIC_ROUTE,
                JourneyType.NATURE_EXPLORATION
            ],
            UserPersona.BUSINESS_TRAVELER: [
                JourneyType.BUSINESS_TRIP,
                JourneyType.DAILY_COMMUTE
            ],
            UserPersona.RIDESHARE_DRIVER: [
                JourneyType.DAILY_COMMUTE
            ],
            UserPersona.ADVENTURE_SEEKER: [
                JourneyType.CROSS_COUNTRY,
                JourneyType.NATURE_EXPLORATION,
                JourneyType.SCENIC_ROUTE
            ],
            UserPersona.HISTORY_BUFF: [
                JourneyType.HISTORICAL_TOUR,
                JourneyType.WEEKEND_TRIP
            ],
            UserPersona.FOODIE_EXPLORER: [
                JourneyType.FOOD_TOUR,
                JourneyType.WEEKEND_TRIP
            ],
            UserPersona.NATURE_LOVER: [
                JourneyType.NATURE_EXPLORATION,
                JourneyType.SCENIC_ROUTE
            ]
        }
        
        options = journey_map.get(persona, [JourneyType.WEEKEND_TRIP])
        return random.choice(options)
        
    def _generate_route(self, journey_type: JourneyType) -> Tuple[Dict[str, float], Dict[str, float], List[Dict[str, Any]]]:
        """Generate realistic route coordinates"""
        # Sample routes for different journey types
        routes = {
            JourneyType.DAILY_COMMUTE: [
                {
                    "origin": {"lat": 37.7749, "lng": -122.4194, "name": "San Francisco, CA"},
                    "destination": {"lat": 37.4419, "lng": -122.1430, "name": "Palo Alto, CA"},
                    "waypoints": []
                },
                {
                    "origin": {"lat": 40.7128, "lng": -74.0060, "name": "New York, NY"},
                    "destination": {"lat": 40.6892, "lng": -74.0445, "name": "Jersey City, NJ"},
                    "waypoints": []
                }
            ],
            JourneyType.WEEKEND_TRIP: [
                {
                    "origin": {"lat": 34.0522, "lng": -118.2437, "name": "Los Angeles, CA"},
                    "destination": {"lat": 36.1069, "lng": -115.1728, "name": "Las Vegas, NV"},
                    "waypoints": [
                        {"lat": 34.8697, "lng": -116.6276, "name": "Barstow, CA"}
                    ]
                },
                {
                    "origin": {"lat": 37.7749, "lng": -122.4194, "name": "San Francisco, CA"},
                    "destination": {"lat": 36.7783, "lng": -119.4179, "name": "Yosemite, CA"},
                    "waypoints": [
                        {"lat": 37.3541, "lng": -121.9552, "name": "San Jose, CA"}
                    ]
                }
            ],
            JourneyType.CROSS_COUNTRY: [
                {
                    "origin": {"lat": 40.7128, "lng": -74.0060, "name": "New York, NY"},
                    "destination": {"lat": 34.0522, "lng": -118.2437, "name": "Los Angeles, CA"},
                    "waypoints": [
                        {"lat": 39.7392, "lng": -104.9903, "name": "Denver, CO"},
                        {"lat": 36.1627, "lng": -115.1485, "name": "Las Vegas, NV"}
                    ]
                }
            ],
            JourneyType.SCENIC_ROUTE: [
                {
                    "origin": {"lat": 36.1069, "lng": -112.1129, "name": "Grand Canyon, AZ"},
                    "destination": {"lat": 37.2982, "lng": -113.0263, "name": "Zion National Park, UT"},
                    "waypoints": [
                        {"lat": 36.8619, "lng": -111.3743, "name": "Page, AZ"}
                    ]
                },
                {
                    "origin": {"lat": 36.5054, "lng": -121.9253, "name": "Carmel-by-the-Sea, CA"},
                    "destination": {"lat": 35.2828, "lng": -120.6596, "name": "San Luis Obispo, CA"},
                    "waypoints": [
                        {"lat": 36.2704, "lng": -121.8081, "name": "Big Sur, CA"}
                    ]
                }
            ],
            JourneyType.FOOD_TOUR: [
                {
                    "origin": {"lat": 29.9511, "lng": -90.0715, "name": "New Orleans, LA"},
                    "destination": {"lat": 29.4241, "lng": -98.4936, "name": "San Antonio, TX"},
                    "waypoints": [
                        {"lat": 30.2672, "lng": -97.7431, "name": "Austin, TX"}
                    ]
                }
            ],
            JourneyType.HISTORICAL_TOUR: [
                {
                    "origin": {"lat": 39.9042, "lng": -77.0369, "name": "Gettysburg, PA"},
                    "destination": {"lat": 38.9072, "lng": -77.0369, "name": "Washington, DC"},
                    "waypoints": [
                        {"lat": 39.2904, "lng": -76.6122, "name": "Baltimore, MD"}
                    ]
                }
            ],
            JourneyType.NATURE_EXPLORATION: [
                {
                    "origin": {"lat": 44.4280, "lng": -110.5885, "name": "Yellowstone, WY"},
                    "destination": {"lat": 43.8791, "lng": -110.6818, "name": "Grand Teton, WY"},
                    "waypoints": []
                }
            ],
            JourneyType.BUSINESS_TRIP: [
                {
                    "origin": {"lat": 47.6062, "lng": -122.3321, "name": "Seattle, WA"},
                    "destination": {"lat": 45.5152, "lng": -122.6784, "name": "Portland, OR"},
                    "waypoints": []
                }
            ]
        }
        
        route_options = routes.get(journey_type, routes[JourneyType.WEEKEND_TRIP])
        selected_route = random.choice(route_options)
        
        return (
            selected_route["origin"],
            selected_route["destination"],
            selected_route["waypoints"]
        )
        
    def _generate_start_time(self, journey_type: JourneyType) -> datetime:
        """Generate realistic start time based on journey type"""
        now = datetime.now()
        
        if journey_type == JourneyType.DAILY_COMMUTE:
            # Morning or evening commute
            if random.random() < 0.7:  # Morning commute
                hour = random.randint(6, 9)
            else:  # Evening commute
                hour = random.randint(16, 19)
            return now.replace(hour=hour, minute=random.randint(0, 59))
            
        elif journey_type == JourneyType.BUSINESS_TRIP:
            # Business hours
            hour = random.randint(8, 17)
            return now.replace(hour=hour, minute=random.randint(0, 59))
            
        elif journey_type in [JourneyType.WEEKEND_TRIP, JourneyType.SCENIC_ROUTE]:
            # Weekend morning starts
            hour = random.randint(7, 11)
            # Adjust to weekend
            days_until_saturday = (5 - now.weekday()) % 7
            weekend_date = now + timedelta(days=days_until_saturday)
            return weekend_date.replace(hour=hour, minute=random.randint(0, 59))
            
        else:
            # Random daytime
            hour = random.randint(8, 16)
            return now.replace(hour=hour, minute=random.randint(0, 59))
            
    def _estimate_duration(self, journey_type: JourneyType, origin: Dict, destination: Dict) -> int:
        """Estimate journey duration in minutes"""
        duration_map = {
            JourneyType.DAILY_COMMUTE: random.randint(20, 60),
            JourneyType.WEEKEND_TRIP: random.randint(120, 480),
            JourneyType.CROSS_COUNTRY: random.randint(1440, 2880),  # 1-2 days
            JourneyType.SCENIC_ROUTE: random.randint(180, 360),
            JourneyType.BUSINESS_TRIP: random.randint(60, 240),
            JourneyType.FOOD_TOUR: random.randint(240, 480),
            JourneyType.HISTORICAL_TOUR: random.randint(180, 360),
            JourneyType.NATURE_EXPLORATION: random.randint(240, 480)
        }
        return duration_map.get(journey_type, 180)
        
    def _generate_weather(self) -> str:
        """Generate random weather condition"""
        weather_options = [
            "clear",
            "partly_cloudy",
            "cloudy",
            "light_rain",
            "rain",
            "fog",
            "snow"
        ]
        weights = [0.4, 0.2, 0.15, 0.1, 0.08, 0.05, 0.02]
        return random.choices(weather_options, weights=weights)[0]
        
    def _generate_traffic(self, start_time: datetime) -> str:
        """Generate traffic level based on time"""
        hour = start_time.hour
        
        # Rush hour traffic
        if (7 <= hour <= 9) or (17 <= hour <= 19):
            return random.choice(["heavy", "moderate", "heavy"])
        # Mid-day
        elif 10 <= hour <= 15:
            return random.choice(["light", "moderate", "light"])
        # Evening/night
        else:
            return random.choice(["light", "very_light"])
            
    async def simulate_interactions(self, journey: SimulatedJourney, user: SimulatedUser, real_time: bool = False):
        """Simulate user interactions during a journey"""
        interaction_types = self._get_interaction_types(user.persona)
        
        # Calculate number of interactions based on journey duration and user frequency
        num_interactions = int(
            (journey.estimated_duration / 30) * user.interaction_frequency * 
            random.uniform(0.8, 1.2)
        )
        
        current_time = journey.start_time
        time_increment = journey.estimated_duration / max(num_interactions, 1)
        
        for i in range(num_interactions):
            if real_time:
                await asyncio.sleep(random.uniform(5, 15))  # Real-time delay
                
            interaction_type = random.choice(interaction_types)
            command = self._generate_command(interaction_type, user, journey)
            
            # Simulate API call
            start_time = time.time()
            try:
                response = await self._make_api_call(interaction_type, command, user, journey)
                response_time = time.time() - start_time
                success = True
            except Exception as e:
                logger.error(f"Interaction failed: {e}")
                response_time = time.time() - start_time
                success = False
                self.metrics["errors"] += 1
                
            interaction = SimulatedInteraction(
                timestamp=current_time,
                user_id=user.id,
                journey_id=journey.id,
                interaction_type=interaction_type,
                command=command,
                response_time=response_time,
                success=success,
                metadata={
                    "persona": user.persona.value,
                    "journey_type": journey.journey_type.value
                }
            )
            
            self.interactions.append(interaction)
            self.metrics["total_interactions"] += 1
            self.metrics["response_times"].append(response_time)
            
            # Check for booking opportunity
            if interaction_type in ["restaurant_request", "attraction_request"] and success:
                if random.random() < user.booking_probability:
                    await self._simulate_booking(user, journey, interaction_type)
                    
            current_time += timedelta(minutes=time_increment)
            
    def _get_interaction_types(self, persona: UserPersona) -> List[str]:
        """Get appropriate interaction types for persona"""
        base_interactions = [
            "story_request",
            "navigation_update",
            "voice_command"
        ]
        
        persona_specific = {
            UserPersona.FAMILY_VACATION: [
                "trivia_game",
                "restaurant_request",
                "attraction_request",
                "rest_stop_request"
            ],
            UserPersona.BUSINESS_TRAVELER: [
                "traffic_update",
                "eta_request",
                "restaurant_request"
            ],
            UserPersona.RIDESHARE_DRIVER: [
                "traffic_update",
                "alternate_route",
                "gas_station_request"
            ],
            UserPersona.ADVENTURE_SEEKER: [
                "side_quest_request",
                "scenic_route_request",
                "photo_spot_request"
            ],
            UserPersona.HISTORY_BUFF: [
                "historical_info",
                "landmark_details",
                "museum_request"
            ],
            UserPersona.FOODIE_EXPLORER: [
                "restaurant_request",
                "local_specialty",
                "food_tour_request"
            ],
            UserPersona.NATURE_LOVER: [
                "trail_info",
                "scenic_route_request",
                "weather_update"
            ]
        }
        
        return base_interactions + persona_specific.get(persona, [])
        
    def _generate_command(self, interaction_type: str, user: SimulatedUser, journey: SimulatedJourney) -> str:
        """Generate realistic voice command"""
        commands = {
            "story_request": [
                "Tell me about this area",
                "What's the history of this place?",
                "Any interesting stories about where we are?",
                "What happened here?"
            ],
            "navigation_update": [
                "How much longer?",
                "What's our ETA?",
                "Are we on the fastest route?",
                "Any traffic ahead?"
            ],
            "voice_command": [
                "Change voice to {voice}",
                "Pause story",
                "Resume",
                "Skip this story"
            ],
            "trivia_game": [
                "Let's play trivia",
                "Start a game",
                "Quiz us about this area",
                "Family trivia time"
            ],
            "restaurant_request": [
                "Find restaurants nearby",
                "I'm hungry, what's good around here?",
                "Book a table for dinner",
                "What's the best local food?"
            ],
            "attraction_request": [
                "What attractions are nearby?",
                "Any fun stops for kids?",
                "Museums around here?",
                "Things to do nearby"
            ],
            "side_quest_request": [
                "Any hidden gems nearby?",
                "Surprise me with a detour",
                "What's unique around here?",
                "Adventure time!"
            ],
            "traffic_update": [
                "Traffic report",
                "Any delays ahead?",
                "Should we take an alternate route?",
                "Accident reports?"
            ],
            "historical_info": [
                "Tell me the history",
                "What's significant about this place?",
                "Historical landmarks nearby?",
                "When was this founded?"
            ]
        }
        
        command_options = commands.get(interaction_type, ["Tell me more"])
        command = random.choice(command_options)
        
        # Personalize some commands
        if "{voice}" in command:
            command = command.format(voice=random.choice(["calm", "energetic", "mysterious"]))
            
        return command
        
    async def _make_api_call(self, interaction_type: str, command: str, user: SimulatedUser, journey: SimulatedJourney):
        """Make actual API call to test system"""
        endpoint_map = {
            "story_request": "/api/v1/story/generate",
            "navigation_update": "/api/v1/directions/status",
            "voice_command": "/api/v1/voice/command",
            "trivia_game": "/api/v1/games/trivia",
            "restaurant_request": "/api/v1/places/restaurants",
            "attraction_request": "/api/v1/places/attractions",
            "side_quest_request": "/api/v1/side-quests/generate",
            "traffic_update": "/api/v1/directions/traffic",
            "historical_info": "/api/v1/story/historical"
        }
        
        endpoint = endpoint_map.get(interaction_type, "/api/v1/voice/command")
        
        # Prepare request data
        data = {
            "user_id": user.id,
            "command": command,
            "location": {
                "lat": journey.origin["lat"],
                "lng": journey.origin["lng"]
            },
            "preferences": user.preferences,
            "voice_personality": user.voice_personality.value,
            "journey_context": {
                "type": journey.journey_type.value,
                "weather": journey.weather_condition,
                "traffic": journey.traffic_level
            }
        }
        
        response = await self.client.post(
            f"{self.api_base_url}{endpoint}",
            json=data
        )
        response.raise_for_status()
        return response.json()
        
    async def _simulate_booking(self, user: SimulatedUser, journey: SimulatedJourney, booking_type: str):
        """Simulate a booking request"""
        self.metrics["bookings_requested"] += 1
        
        booking_data = {
            "user_id": user.id,
            "journey_id": journey.id,
            "type": booking_type,
            "party_size": random.randint(1, 6) if user.persona == UserPersona.FAMILY_VACATION else random.randint(1, 2),
            "preferences": user.preferences,
            "time_preference": "along_route"
        }
        
        try:
            response = await self.client.post(
                f"{self.api_base_url}/api/v1/bookings/create",
                json=booking_data
            )
            response.raise_for_status()
            self.metrics["bookings_completed"] += 1
            logger.info(f"Booking completed for user {user.id}")
        except Exception as e:
            logger.error(f"Booking failed: {e}")
            
    async def run_load_test(self, num_users: int, duration_minutes: int, concurrent_users: int = 10):
        """Run load testing scenario"""
        logger.info(f"Starting load test: {num_users} users, {duration_minutes} minutes, {concurrent_users} concurrent")
        
        # Generate users
        users = self.generate_users(num_users)
        
        # Create concurrent simulation tasks
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        active_simulations = []
        user_index = 0
        
        while time.time() < end_time and user_index < len(users):
            # Maintain concurrent user count
            active_simulations = [s for s in active_simulations if not s.done()]
            
            while len(active_simulations) < concurrent_users and user_index < len(users):
                user = users[user_index]
                journey = await self.simulate_journey(user)
                
                # Create simulation task
                task = asyncio.create_task(
                    self.simulate_interactions(journey, user, real_time=False)
                )
                active_simulations.append(task)
                user_index += 1
                
                # Stagger starts
                await asyncio.sleep(random.uniform(1, 3))
                
            await asyncio.sleep(1)
            
        # Wait for remaining simulations
        if active_simulations:
            await asyncio.gather(*active_simulations)
            
        logger.info("Load test completed")
        
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        if self.metrics["response_times"]:
            response_times = np.array(self.metrics["response_times"])
            response_metrics = {
                "mean": float(np.mean(response_times)),
                "median": float(np.median(response_times)),
                "p95": float(np.percentile(response_times, 95)),
                "p99": float(np.percentile(response_times, 99)),
                "min": float(np.min(response_times)),
                "max": float(np.max(response_times))
            }
        else:
            response_metrics = {}
            
        # Calculate conversion rates
        booking_conversion = (
            self.metrics["bookings_completed"] / self.metrics["bookings_requested"]
            if self.metrics["bookings_requested"] > 0 else 0
        )
        
        # Persona distribution
        persona_dist = {}
        for user in self.users.values():
            persona = user.persona.value
            persona_dist[persona] = persona_dist.get(persona, 0) + 1
            
        return {
            "summary": {
                "total_users": self.metrics["total_users"],
                "total_journeys": self.metrics["total_journeys"],
                "total_interactions": self.metrics["total_interactions"],
                "total_errors": self.metrics["errors"],
                "error_rate": self.metrics["errors"] / max(self.metrics["total_interactions"], 1)
            },
            "bookings": {
                "requested": self.metrics["bookings_requested"],
                "completed": self.metrics["bookings_completed"],
                "conversion_rate": booking_conversion
            },
            "response_times": response_metrics,
            "persona_distribution": persona_dist,
            "interactions_per_journey": (
                self.metrics["total_interactions"] / max(self.metrics["total_journeys"], 1)
            )
        }
        
    def export_results(self, filename: str = "simulation_results.json"):
        """Export simulation results to file"""
        results = {
            "metrics": self.get_metrics_summary(),
            "users": [asdict(user) for user in self.users.values()],
            "journeys": [asdict(journey) for journey in self.journeys.values()],
            "interactions": [asdict(interaction) for interaction in self.interactions[-1000:]],  # Last 1000
            "timestamp": datetime.now().isoformat()
        }
        
        # Convert datetime objects to strings
        def convert_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: convert_datetime(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_datetime(item) for item in obj]
            return obj
            
        results = convert_datetime(results)
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
            
        logger.info(f"Results exported to {filename}")


async def main():
    """Example usage of simulation engine"""
    async with SimulationEngine() as engine:
        # Quick test
        print("Running quick simulation test...")
        
        # Generate a few users
        users = engine.generate_users(5)
        
        # Simulate journeys
        for user in users:
            journey = await engine.simulate_journey(user)
            await engine.simulate_interactions(journey, user, real_time=False)
            
        # Print metrics
        metrics = engine.get_metrics_summary()
        print(json.dumps(metrics, indent=2))
        
        # Export results
        engine.export_results()
        
        # Run load test
        print("\nRunning load test...")
        await engine.run_load_test(
            num_users=50,
            duration_minutes=5,
            concurrent_users=10
        )
        
        # Final metrics
        final_metrics = engine.get_metrics_summary()
        print("\nFinal Metrics:")
        print(json.dumps(final_metrics, indent=2))
        
        # Export load test results
        engine.export_results("load_test_results.json")


if __name__ == "__main__":
    asyncio.run(main())