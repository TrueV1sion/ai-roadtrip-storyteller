"""
GraphQL type definitions using Strawberry.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import strawberry
from strawberry.types import Info

# Enums
@strawberry.enum
class VoicePersonality(Enum):
    ENTHUSIASTIC_GUIDE = "enthusiastic_guide"
    MICKEY = "mickey"
    SANTA_CLAUS = "santa_claus"
    ROCK_DJ = "rock_dj"
    SPORTS_COMMENTATOR = "sports_commentator"
    BROADWAY_NARRATOR = "broadway_narrator"
    SPOOKY_NARRATOR = "spooky_narrator"
    BEACH_VIBES_GUIDE = "beach_vibes_guide"
    FOODIE_EXPERT = "foodie_expert"
    HISTORY_PROFESSOR = "history_professor"
    NATURE_ENTHUSIAST = "nature_enthusiast"
    COMEDY_HOST = "comedy_host"
    MEDITATION_GURU = "meditation_guru"
    PIRATE_CAPTAIN = "pirate_captain"
    COWBOY_NARRATOR = "cowboy_narrator"
    JAZZ_MUSICIAN = "jazz_musician"
    TECH_ENTHUSIAST = "tech_enthusiast"
    FITNESS_COACH = "fitness_coach"
    STORYTELLER_GRANDPARENT = "storyteller_grandparent"
    LOCAL_EXPERT = "local_expert"


@strawberry.enum
class BookingStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


@strawberry.enum
class JourneyTheme(Enum):
    FAMILY = "family"
    ADVENTURE = "adventure"
    CULTURAL = "cultural"
    SCENIC = "scenic"
    FOODIE = "foodie"
    HISTORICAL = "historical"
    ENTERTAINMENT = "entertainment"
    RELAXATION = "relaxation"


# Input Types
@strawberry.input
class LocationInput:
    latitude: float
    longitude: float
    address: Optional[str] = None


@strawberry.input
class JourneyContextInput:
    origin: str
    destination: str
    theme: Optional[JourneyTheme] = None
    party_size: Optional[int] = None
    interests: Optional[List[str]] = None
    departure_time: Optional[datetime] = None


@strawberry.input
class VoiceInteractionInput:
    user_input: str
    context: JourneyContextInput
    current_location: Optional[LocationInput] = None
    is_driving: bool = False
    speed_mph: Optional[float] = None


@strawberry.input
class BookingRequestInput:
    partner: str
    venue_id: str
    date: datetime
    party_size: int
    special_requests: Optional[str] = None
    user_preferences: Optional[Dict[str, Any]] = None


# Output Types
@strawberry.type
class User:
    id: strawberry.ID
    email: str
    name: Optional[str]
    preferences: Dict[str, Any]
    created_at: datetime
    journey_count: int
    total_miles: float
    favorite_personality: Optional[VoicePersonality]


@strawberry.type
class VoiceResponse:
    text: str
    audio_url: Optional[str]
    personality: VoicePersonality
    emotion: str
    suggestions: List[str]
    is_safety_critical: bool
    requires_confirmation: bool


@strawberry.type
class Story:
    id: strawberry.ID
    title: str
    content: str
    theme: JourneyTheme
    location: LocationInput
    audio_url: Optional[str]
    image_url: Optional[str]
    duration_seconds: int
    is_location_specific: bool


@strawberry.type
class Booking:
    id: strawberry.ID
    user_id: strawberry.ID
    partner: str
    venue_name: str
    confirmation_number: str
    date: datetime
    party_size: int
    status: BookingStatus
    total_amount: float
    commission_amount: float
    special_requests: Optional[str]
    created_at: datetime


@strawberry.type
class Journey:
    id: strawberry.ID
    user_id: strawberry.ID
    origin: str
    destination: str
    theme: JourneyTheme
    distance_miles: float
    duration_minutes: int
    stories: List[Story]
    bookings: List[Booking]
    personality: VoicePersonality
    started_at: datetime
    completed_at: Optional[datetime]


@strawberry.type
class EventJourney:
    event_id: str
    event_name: str
    venue_name: str
    event_date: datetime
    anticipation_content: Dict[str, Any]
    milestones: List[Dict[str, Any]]
    personality: VoicePersonality
    trivia_questions: List[Dict[str, Any]]


@strawberry.type
class RealtimeLocation:
    latitude: float
    longitude: float
    speed_mph: float
    heading: float
    timestamp: datetime
    nearby_points_of_interest: List[Dict[str, Any]]


@strawberry.type
class BookingOpportunity:
    partner: str
    venue_id: str
    venue_name: str
    distance_miles: float
    estimated_arrival: datetime
    availability: bool
    price_range: str
    rating: float
    commission_rate: float


@strawberry.type
class NavigationUpdate:
    current_location: RealtimeLocation
    next_turn: Optional[str]
    distance_to_turn_miles: Optional[float]
    time_to_destination_minutes: int
    traffic_condition: str
    alternate_routes: List[Dict[str, Any]]


@strawberry.type
class AIResponse:
    request_id: str
    agent_responses: Dict[str, Any]
    primary_response: VoiceResponse
    booking_opportunities: List[BookingOpportunity]
    stories: List[Story]
    navigation_update: Optional[NavigationUpdate]
    processing_time_ms: int


@strawberry.type
class Revenue:
    period: str
    total_bookings: int
    total_revenue: float
    total_commission: float
    average_commission_rate: float
    top_partners: List[Dict[str, Any]]
    growth_percentage: float


@strawberry.type
class SystemHealth:
    status: str
    uptime_seconds: int
    active_users: int
    active_journeys: int
    api_response_time_ms: float
    cache_hit_rate: float
    error_rate: float


# Subscription Types
@strawberry.type
class VoiceInteractionUpdate:
    session_id: str
    user_id: strawberry.ID
    interaction_type: str
    voice_response: VoiceResponse
    timestamp: datetime


@strawberry.type
class JourneyUpdate:
    journey_id: strawberry.ID
    update_type: str
    location: RealtimeLocation
    story: Optional[Story]
    milestone: Optional[Dict[str, Any]]
    booking_opportunity: Optional[BookingOpportunity]
    timestamp: datetime


@strawberry.type
class BookingUpdate:
    booking_id: strawberry.ID
    status: BookingStatus
    update_message: str
    timestamp: datetime


# Mutation Response Types
@strawberry.type
class MutationResponse:
    success: bool
    message: Optional[str]
    error: Optional[str]


@strawberry.type
class BookingResponse(MutationResponse):
    booking: Optional[Booking]


@strawberry.type
class JourneyResponse(MutationResponse):
    journey: Optional[Journey]


@strawberry.type
class VoiceInteractionResponse(MutationResponse):
    response: Optional[AIResponse]
    session_id: Optional[str]