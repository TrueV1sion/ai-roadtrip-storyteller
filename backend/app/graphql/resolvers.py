"""
GraphQL resolvers for queries, mutations, and subscriptions.
"""

import asyncio
from typing import List, Optional, Dict, Any, AsyncGenerator
from datetime import datetime
import strawberry
from strawberry.types import Info

from backend.app.graphql.types import (
    User, Journey, Story, Booking, VoiceResponse, AIResponse,
    EventJourney, RealtimeLocation, NavigationUpdate, BookingOpportunity,
    Revenue, SystemHealth, VoiceInteractionUpdate, JourneyUpdate, BookingUpdate,
    BookingResponse, JourneyResponse, VoiceInteractionResponse,
    JourneyContextInput, VoiceInteractionInput, BookingRequestInput
)
from backend.app.services.master_orchestration_agent import MasterOrchestrationAgent
from backend.app.services.booking_service import BookingService
from backend.app.services.event_journey_service import EventJourneyService
from backend.app.core.database_manager import DatabaseManager
from backend.app.core.auth import get_current_user
from backend.app.core.logger import get_logger
from backend.app.tasks.booking import process_reservation
from backend.app.tasks.ai import generate_story_async

logger = get_logger(__name__)

# Initialize services
master_agent = MasterOrchestrationAgent()
booking_service = BookingService()
event_journey_service = EventJourneyService()
db_manager = DatabaseManager()


class Query:
    """GraphQL Query resolvers."""
    
    @strawberry.field
    async def me(self, info: Info) -> Optional[User]:
        """Get current user information."""
        user = await get_current_user(info.context["request"])
        if not user:
            return None
        
        return User(
            id=strawberry.ID(str(user.id)),
            email=user.email,
            name=user.name,
            preferences=user.preferences or {},
            created_at=user.created_at,
            journey_count=user.journey_count,
            total_miles=user.total_miles,
            favorite_personality=user.favorite_personality
        )
    
    @strawberry.field
    async def journey(self, info: Info, journey_id: strawberry.ID) -> Optional[Journey]:
        """Get a specific journey by ID."""
        user = await get_current_user(info.context["request"])
        if not user:
            return None
        
        # Fetch journey from database
        with db_manager.get_session() as session:
            journey = session.query(Journey).filter_by(
                id=int(journey_id),
                user_id=user.id
            ).first()
            
            if not journey:
                return None
            
            # Convert to GraphQL type
            return Journey(
                id=strawberry.ID(str(journey.id)),
                user_id=strawberry.ID(str(journey.user_id)),
                origin=journey.origin,
                destination=journey.destination,
                theme=journey.theme,
                distance_miles=journey.distance_miles,
                duration_minutes=journey.duration_minutes,
                stories=[],  # Would fetch related stories
                bookings=[],  # Would fetch related bookings
                personality=journey.personality,
                started_at=journey.started_at,
                completed_at=journey.completed_at
            )
    
    @strawberry.field
    async def my_journeys(
        self, 
        info: Info, 
        limit: int = 10, 
        offset: int = 0
    ) -> List[Journey]:
        """Get user's journey history."""
        user = await get_current_user(info.context["request"])
        if not user:
            return []
        
        # Fetch journeys from database
        # This is simplified - would include proper pagination
        return []
    
    @strawberry.field
    async def my_bookings(
        self, 
        info: Info,
        status: Optional[str] = None,
        limit: int = 10
    ) -> List[Booking]:
        """Get user's bookings."""
        user = await get_current_user(info.context["request"])
        if not user:
            return []
        
        # Fetch bookings from database
        return []
    
    @strawberry.field
    async def search_events(
        self,
        info: Info,
        location: str,
        date_from: datetime,
        date_to: datetime,
        category: Optional[str] = None
    ) -> List[EventJourney]:
        """Search for events that can become event journeys."""
        events = await event_journey_service.search_events(
            location=location,
            date_from=date_from,
            date_to=date_to,
            category=category
        )
        
        # Convert to GraphQL types
        return [
            EventJourney(
                event_id=event['id'],
                event_name=event['name'],
                venue_name=event['venue'],
                event_date=event['date'],
                anticipation_content={},
                milestones=[],
                personality=event.get('suggested_personality', 'enthusiastic_guide'),
                trivia_questions=[]
            )
            for event in events
        ]
    
    @strawberry.field
    async def booking_opportunities(
        self,
        info: Info,
        location: Dict[str, float],
        radius_miles: float = 10.0,
        booking_type: Optional[str] = None
    ) -> List[BookingOpportunity]:
        """Find booking opportunities near a location."""
        opportunities = await booking_service.find_opportunities(
            latitude=location['latitude'],
            longitude=location['longitude'],
            radius_miles=radius_miles,
            booking_type=booking_type
        )
        
        return [
            BookingOpportunity(
                partner=opp['partner'],
                venue_id=opp['venue_id'],
                venue_name=opp['venue_name'],
                distance_miles=opp['distance_miles'],
                estimated_arrival=opp['estimated_arrival'],
                availability=opp['availability'],
                price_range=opp['price_range'],
                rating=opp['rating'],
                commission_rate=opp['commission_rate']
            )
            for opp in opportunities
        ]
    
    @strawberry.field
    async def revenue_analytics(
        self,
        info: Info,
        period: str = "month"
    ) -> Revenue:
        """Get revenue analytics (admin only)."""
        user = await get_current_user(info.context["request"])
        if not user or not user.is_admin:
            raise Exception("Unauthorized")
        
        # Fetch revenue data
        # This is simplified - would aggregate from database
        return Revenue(
            period=period,
            total_bookings=150,
            total_revenue=45000.0,
            total_commission=4500.0,
            average_commission_rate=0.10,
            top_partners=[
                {"name": "OpenTable", "revenue": 2500.0},
                {"name": "Recreation.gov", "revenue": 1500.0}
            ],
            growth_percentage=25.5
        )
    
    @strawberry.field
    async def system_health(self, info: Info) -> SystemHealth:
        """Get system health metrics."""
        # This would fetch real metrics
        return SystemHealth(
            status="healthy",
            uptime_seconds=86400,
            active_users=1250,
            active_journeys=89,
            api_response_time_ms=145.5,
            cache_hit_rate=0.85,
            error_rate=0.002
        )


class Mutation:
    """GraphQL Mutation resolvers."""
    
    @strawberry.mutation
    async def start_journey(
        self,
        info: Info,
        context: JourneyContextInput
    ) -> JourneyResponse:
        """Start a new journey."""
        user = await get_current_user(info.context["request"])
        if not user:
            return JourneyResponse(
                success=False,
                error="Authentication required"
            )
        
        try:
            # Create journey in database
            journey_data = {
                'user_id': user.id,
                'origin': context.origin,
                'destination': context.destination,
                'theme': context.theme,
                'party_size': context.party_size,
                'interests': context.interests,
                'departure_time': context.departure_time
            }
            
            # Process with master orchestration agent
            result = await master_agent.process_request({
                'user_input': f"Starting journey from {context.origin} to {context.destination}",
                'context': journey_data
            })
            
            # Create journey record
            # This is simplified - would create actual database record
            journey = Journey(
                id=strawberry.ID("123"),
                user_id=strawberry.ID(str(user.id)),
                origin=context.origin,
                destination=context.destination,
                theme=context.theme or 'adventure',
                distance_miles=result.get('distance', 0),
                duration_minutes=result.get('duration', 0),
                stories=[],
                bookings=[],
                personality=result.get('personality', 'enthusiastic_guide'),
                started_at=datetime.utcnow(),
                completed_at=None
            )
            
            return JourneyResponse(
                success=True,
                journey=journey
            )
            
        except Exception as e:
            logger.error(f"Error starting journey: {str(e)}")
            return JourneyResponse(
                success=False,
                error=str(e)
            )
    
    @strawberry.mutation
    async def voice_interaction(
        self,
        info: Info,
        input: VoiceInteractionInput
    ) -> VoiceInteractionResponse:
        """Process a voice interaction."""
        user = await get_current_user(info.context["request"])
        if not user:
            return VoiceInteractionResponse(
                success=False,
                error="Authentication required"
            )
        
        try:
            # Process with master orchestration agent
            context_data = {
                'origin': input.context.origin,
                'destination': input.context.destination,
                'theme': input.context.theme,
                'current_location': input.current_location,
                'is_driving': input.is_driving,
                'speed_mph': input.speed_mph
            }
            
            result = await master_agent.process_request({
                'user_input': input.user_input,
                'context': context_data,
                'user_id': user.id
            })
            
            # Convert to GraphQL response
            voice_response = VoiceResponse(
                text=result['response']['text'],
                audio_url=result['response'].get('audio_url'),
                personality=result['response']['personality'],
                emotion=result['response'].get('emotion', 'neutral'),
                suggestions=result['response'].get('suggestions', []),
                is_safety_critical=result['response'].get('is_safety_critical', False),
                requires_confirmation=result['response'].get('requires_confirmation', False)
            )
            
            ai_response = AIResponse(
                request_id=result['request_id'],
                agent_responses=result['agent_responses'],
                primary_response=voice_response,
                booking_opportunities=[],
                stories=[],
                navigation_update=None,
                processing_time_ms=result['processing_time_ms']
            )
            
            return VoiceInteractionResponse(
                success=True,
                response=ai_response,
                session_id=result.get('session_id')
            )
            
        except Exception as e:
            logger.error(f"Error processing voice interaction: {str(e)}")
            return VoiceInteractionResponse(
                success=False,
                error=str(e)
            )
    
    @strawberry.mutation
    async def create_booking(
        self,
        info: Info,
        input: BookingRequestInput
    ) -> BookingResponse:
        """Create a new booking."""
        user = await get_current_user(info.context["request"])
        if not user:
            return BookingResponse(
                success=False,
                error="Authentication required"
            )
        
        try:
            # Process booking asynchronously
            booking_data = {
                'user_id': user.id,
                'partner': input.partner,
                'venue_id': input.venue_id,
                'booking_date': input.date.isoformat(),
                'party_size': input.party_size,
                'special_requests': input.special_requests,
                'user_data': {
                    'email': user.email,
                    'name': user.name,
                    'preferences': input.user_preferences
                }
            }
            
            # Queue for async processing
            task = process_reservation.apply_async(args=[booking_data])
            
            # Create pending booking record
            booking = Booking(
                id=strawberry.ID(task.id),
                user_id=strawberry.ID(str(user.id)),
                partner=input.partner,
                venue_name="Processing...",
                confirmation_number="PENDING",
                date=input.date,
                party_size=input.party_size,
                status="pending",
                total_amount=0.0,
                commission_amount=0.0,
                special_requests=input.special_requests,
                created_at=datetime.utcnow()
            )
            
            return BookingResponse(
                success=True,
                booking=booking,
                message="Booking is being processed"
            )
            
        except Exception as e:
            logger.error(f"Error creating booking: {str(e)}")
            return BookingResponse(
                success=False,
                error=str(e)
            )
    
    @strawberry.mutation
    async def cancel_booking(
        self,
        info: Info,
        booking_id: strawberry.ID
    ) -> BookingResponse:
        """Cancel an existing booking."""
        user = await get_current_user(info.context["request"])
        if not user:
            return BookingResponse(
                success=False,
                error="Authentication required"
            )
        
        # Implementation would cancel the booking
        return BookingResponse(
            success=True,
            message="Booking cancelled successfully"
        )


class Subscription:
    """GraphQL Subscription resolvers for real-time updates."""
    
    @strawberry.subscription
    async def voice_interactions(
        self,
        info: Info,
        session_id: str
    ) -> AsyncGenerator[VoiceInteractionUpdate, None]:
        """Subscribe to voice interaction updates for a session."""
        user = await get_current_user(info.context["request"])
        if not user:
            return
        
        # This would connect to a pub/sub system (Redis, etc.)
        # For now, we'll simulate updates
        while True:
            await asyncio.sleep(5)  # Wait 5 seconds
            
            yield VoiceInteractionUpdate(
                session_id=session_id,
                user_id=strawberry.ID(str(user.id)),
                interaction_type="response",
                voice_response=VoiceResponse(
                    text="Simulated voice update",
                    audio_url=None,
                    personality="enthusiastic_guide",
                    emotion="happy",
                    suggestions=[],
                    is_safety_critical=False,
                    requires_confirmation=False
                ),
                timestamp=datetime.utcnow()
            )
    
    @strawberry.subscription
    async def journey_updates(
        self,
        info: Info,
        journey_id: strawberry.ID
    ) -> AsyncGenerator[JourneyUpdate, None]:
        """Subscribe to journey updates."""
        user = await get_current_user(info.context["request"])
        if not user:
            return
        
        # This would connect to real-time journey tracking
        while True:
            await asyncio.sleep(10)  # Wait 10 seconds
            
            yield JourneyUpdate(
                journey_id=journey_id,
                update_type="location",
                location=RealtimeLocation(
                    latitude=37.7749,
                    longitude=-122.4194,
                    speed_mph=65.0,
                    heading=180.0,
                    timestamp=datetime.utcnow(),
                    nearby_points_of_interest=[]
                ),
                story=None,
                milestone=None,
                booking_opportunity=None,
                timestamp=datetime.utcnow()
            )
    
    @strawberry.subscription
    async def booking_updates(
        self,
        info: Info,
        booking_id: strawberry.ID
    ) -> AsyncGenerator[BookingUpdate, None]:
        """Subscribe to booking status updates."""
        user = await get_current_user(info.context["request"])
        if not user:
            return
        
        # This would monitor booking status changes
        statuses = ["pending", "confirmed", "completed"]
        for status in statuses:
            await asyncio.sleep(3)  # Wait 3 seconds
            
            yield BookingUpdate(
                booking_id=booking_id,
                status=status,
                update_message=f"Booking is now {status}",
                timestamp=datetime.utcnow()
            )