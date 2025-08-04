"""
Booking Agent - Handles all reservation and booking requests
Integrates with the comprehensive reservation management system
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum
from sqlalchemy import select

from ..core.unified_ai_client import UnifiedAIClient
from .reservation_management_service import ReservationManagementService, BookingProvider
from .restaurant_booking_service import restaurant_booking_service
from ..models.user import User

logger = logging.getLogger(__name__)


class BookingType(Enum):
    RESTAURANT = "restaurant"
    ATTRACTION = "attraction"
    ACTIVITY = "activity"
    ACCOMMODATION = "accommodation"


class BookingAgent:
    """
    Specialized agent for handling all booking and reservation requests.
    Coordinates with the reservation management service for multi-provider support.
    """
    
    def __init__(self, ai_client: UnifiedAIClient, db=None):
        self.ai_client = ai_client
        self.reservation_service = ReservationManagementService()
        self.db = db
        
        # Initialize external clients
        from ..integrations.ticketmaster_client import TicketmasterClient
        from ..integrations.recreation_gov_client import RecreationGovClient
        from ..integrations.viator_client import ViatorClient
        
        self.ticketmaster_client = TicketmasterClient()
        self.rec_gov_client = RecreationGovClient()
        try:
            self.viator_client = ViatorClient()
        except Exception as e:
            self.viator_client = None
        
    async def process_booking_request(self, user_input: str, context: Dict[str, Any], 
                                    user: User) -> Dict[str, Any]:
        """Process a booking request and return recommendations or confirmations"""
        
        try:
            # Analyze the booking intent
            booking_intent = await self._analyze_booking_intent(user_input, context)
            
            if booking_intent['type'] == BookingType.RESTAURANT.value:
                return await self._handle_restaurant_booking(booking_intent, context, user)
            elif booking_intent['type'] == BookingType.ATTRACTION.value:
                return await self._handle_attraction_booking(booking_intent, context, user)
            elif booking_intent['type'] == BookingType.ACTIVITY.value:
                return await self._handle_activity_booking(booking_intent, context, user)
            else:
                return await self._handle_general_booking(booking_intent, context, user)
                
        except Exception as e:
            logger.error(f"Booking request processing failed: {e}")
            return {
                'status': 'error',
                'message': "I couldn't process your booking request. Could you provide more details?",
                'fallback': True
            }
    
    async def _analyze_booking_intent(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user input to determine booking intent"""
        
        analysis_prompt = f"""
        Analyze this booking request:
        
        User request: "{user_input}"
        Current location: {context.get('location', {}).get('name', 'Unknown')}
        Time: {context.get('current_time', datetime.now()).strftime('%I:%M %p')}
        
        Determine:
        1. Booking type (restaurant, attraction, activity, accommodation)
        2. Desired time/date (if specified)
        3. Party size
        4. Specific preferences (cuisine, price range, amenities)
        5. Urgency (immediate, future, browsing)
        
        Extract key information and respond in JSON format.
        """
        
        response = await self.ai_client.generate_structured_response(
            analysis_prompt, expected_format="booking_intent"
        )
        
        return response
    
    async def _handle_restaurant_booking(self, intent: Dict[str, Any], 
                                       context: Dict[str, Any], user: User) -> Dict[str, Any]:
        """Handle restaurant reservations"""
        
        try:
            # Use the enhanced restaurant booking service
            location = context.get('location', {})
            
            # Convert location format
            search_location = {
                'latitude': location.get('lat', location.get('latitude', 0)),
                'longitude': location.get('lng', location.get('longitude', 0))
            }
            
            # Search for restaurants with OpenTable integration
            search_results = await restaurant_booking_service.search_restaurants(
                location=search_location,
                preferences={
                    'cuisine': intent.get('preferences', {}).get('cuisine'),
                    'party_size': intent.get('party_size', 2),
                    'date': intent.get('desired_date', datetime.now().strftime('%Y-%m-%d')),
                    'time': intent.get('desired_time', '19:00'),
                    'price_range': intent.get('preferences', {}).get('price_range'),
                    'radius_miles': 5.0
                }
            )
            
            if not search_results:
                return {
                    'status': 'no_results',
                    'message': "I couldn't find any available restaurants matching your criteria. Would you like to try different options?",
                    'suggestions': await self._generate_alternative_suggestions(intent, context)
                }
            
            # Format recommendations
            recommendations = self._format_restaurant_recommendations(search_results[:5])
            
            # Generate conversational response
            response_prompt = f"""
            Create a friendly, conversational response presenting these restaurant options:
            {recommendations}
            
            Context: User is looking for {intent.get('preferences', {}).get('cuisine', 'a restaurant')} 
            for {intent.get('party_size', 2)} people.
            
            Be helpful and offer to make a reservation.
            """
            
            conversational_response = await self.ai_client.generate_response(response_prompt)
            
            return {
                'status': 'success',
                'message': conversational_response,
                'recommendations': search_results[:5],
                'booking_ready': True,
                'intent': intent,
                'provider': 'opentable'
            }
            
        except Exception as e:
            logger.error(f"Restaurant booking failed: {e}")
            return {
                'status': 'error',
                'message': "I'm having trouble searching for restaurants. Let me try a different approach.",
                'fallback': True
            }
    
    async def _handle_attraction_booking(self, intent: Dict[str, Any], 
                                       context: Dict[str, Any], user: User) -> Dict[str, Any]:
        """Handle attraction ticket bookings"""
        
        # For now, provide information about attractions
        # Full implementation would integrate with ticketing APIs
        return {
            'status': 'info',
            'message': f"I found some great attractions near {context.get('location', {}).get('name', 'your location')}. Let me share the details and help you plan your visit.",
            'recommendations': [],
            'booking_ready': False
        }
    
    async def _handle_activity_booking(self, intent: Dict[str, Any], 
                                      context: Dict[str, Any], user: User) -> Dict[str, Any]:
        """Handle activity bookings"""
        
        activity_type = intent.get('activity_type', 'general')
        location = context.get('location', {})
        date = intent.get('date')
        
        try:
            # Search for activities using integrations
            activities = []
            
            # Try Viator for tours and activities
            if hasattr(self, 'viator_client'):
                viator_results = await self.viator_client.search_activities(
                    latitude=location.get('lat'),
                    longitude=location.get('lng'),
                    activity_type=activity_type,
                    date=date
                )
                activities.extend(viator_results)
            
            # Try Recreation.gov for outdoor activities
            if activity_type in ['camping', 'hiking', 'outdoor']:
                rec_results = await self.rec_gov_client.search_activities(
                    latitude=location.get('lat'),
                    longitude=location.get('lng'),
                    activity_type=activity_type,
                    date=date
                )
                activities.extend(rec_results)
            
            # Try Ticketmaster for events
            if activity_type in ['event', 'concert', 'show', 'sports']:
                events = await self.ticketmaster_client.search_events(
                    latitude=location.get('lat'),
                    longitude=location.get('lng'),
                    keyword=intent.get('keyword', activity_type),
                    date=date
                )
                activities.extend(events)
            
            if activities:
                # Format recommendations
                formatted_activities = self._format_activity_recommendations(activities[:5])
                
                # Generate AI response
                activity_prompt = f"""
                The user is looking for {activity_type} activities near {location.get('name', 'their location')}.
                Here are the options I found:
                
                {formatted_activities}
                
                Create a friendly response presenting these options and asking which one interests them.
                """
                
                ai_response = await self.ai_client.generate_response(activity_prompt)
                
                return {
                    'status': 'success',
                    'message': ai_response,
                    'recommendations': activities[:5],
                    'booking_ready': True
                }
            else:
                return {
                    'status': 'info',
                    'message': f"I couldn't find any {activity_type} activities available near {location.get('name', 'your location')} for your selected date. Would you like me to search for different types of activities or expand the search area?",
                    'recommendations': [],
                    'booking_ready': False
                }
                
        except Exception as e:
            logger.error(f"Activity booking search failed: {e}")
            return {
                'status': 'error',
                'message': "I encountered an issue searching for activities. Would you like me to try again?",
                'recommendations': [],
                'booking_ready': False
            }
    
    async def _handle_general_booking(self, intent: Dict[str, Any], 
                                    context: Dict[str, Any], user: User) -> Dict[str, Any]:
        """Handle general or unclear booking requests"""
        
        clarification_prompt = f"""
        The user wants to book something but the type is unclear.
        Create a friendly response asking for clarification.
        Suggest common options like restaurants, attractions, or activities.
        Keep it conversational and helpful.
        """
        
        response = await self.ai_client.generate_response(clarification_prompt)
        
        return {
            'status': 'needs_clarification',
            'message': response,
            'suggestions': ['restaurants', 'attractions', 'activities', 'tours']
        }
    
    def _format_restaurant_recommendations(self, results: List[Dict[str, Any]]) -> str:
        """Format restaurant search results for AI processing"""
        
        formatted = []
        for i, restaurant in enumerate(results, 1):
            formatted.append(f"""
            {i}. {restaurant['name']}
            - Cuisine: {restaurant.get('cuisine', 'Various')}
            - Rating: {restaurant.get('rating', 'N/A')}/5
            - Price: {'$' * int(restaurant.get('price_range', '2'))}
            - Distance: {restaurant.get('distance', 0):.1f} miles
            - Available times: {', '.join(restaurant.get('available_times', [])[:3])}
            """)
        
        return '\n'.join(formatted)
    
    def _format_activity_recommendations(self, results: List[Dict[str, Any]]) -> str:
        """Format activity search results for AI processing"""
        
        formatted = []
        for i, activity in enumerate(results, 1):
            formatted.append(f"""
            {i}. {activity.get('name', 'Activity')}
            - Type: {activity.get('type', 'General')}
            - Provider: {activity.get('provider', 'N/A')}
            - Rating: {activity.get('rating', 'N/A')}/5
            - Price: ${activity.get('price', 'N/A')}
            - Duration: {activity.get('duration', 'N/A')}
            - Available: {activity.get('availability', 'Check availability')}
            - Distance: {activity.get('distance', 0):.1f} miles
            """)
        
        return '\n'.join(formatted)
    
    async def _generate_alternative_suggestions(self, intent: Dict[str, Any], 
                                              context: Dict[str, Any]) -> List[str]:
        """Generate alternative suggestions when no results found"""
        
        suggestions_prompt = f"""
        No restaurants were found for:
        - Cuisine: {intent.get('preferences', {}).get('cuisine', 'any')}
        - Time: {intent.get('desired_date', 'not specified')}
        - Party size: {intent.get('party_size', 2)}
        
        Suggest 3 alternative approaches (different times, cuisines, or nearby areas).
        Keep suggestions brief and actionable.
        """
        
        response = await self.ai_client.generate_structured_response(
            suggestions_prompt, expected_format="alternatives"
        )
        
        return response.get('suggestions', [
            "Try a different time slot",
            "Expand your cuisine preferences",
            "Look in nearby areas"
        ])
    
    async def confirm_booking(self, selection: Dict[str, Any], user: User) -> Dict[str, Any]:
        """Confirm and finalize a booking"""
        
        try:
            # Check if this is an OpenTable booking
            if selection.get('provider', '').lower() == 'opentable':
                # Use the restaurant booking service
                booking_result = await restaurant_booking_service.create_restaurant_booking(
                    user_id=user.id,
                    restaurant_id=selection['venue_id'],
                    booking_details={
                        'date': selection['date'],
                        'time': selection['time'],
                        'party_size': selection['party_size'],
                        'guest_info': selection['customer_info'],
                        'special_requests': selection.get('special_requests')
                    }
                )
                
                confirmation_number = booking_result['confirmation_number']
                venue_name = booking_result['restaurant_name']
            else:
                # Use the existing reservation service for other providers
                provider = BookingProvider[selection['provider'].upper()]
                
                booking_result = await self.reservation_service.create_reservation(
                    user_id=str(user.id),
                    provider=provider,
                    venue_id=selection['venue_id'],
                    date_time=datetime.fromisoformat(selection['date_time']),
                    party_size=selection['party_size'],
                    customer_info=selection['customer_info'],
                    special_requests=selection.get('special_requests'),
                    occasion_type=selection.get('occasion_type')
                )
                
                confirmation_number = booking_result['confirmation_number']
                venue_name = selection['venue_name']
            
            # Generate confirmation message
            confirmation_prompt = f"""
            Create a friendly confirmation message for:
            - Restaurant: {venue_name}
            - Date/Time: {selection.get('date_time', f"{selection.get('date')} {selection.get('time')}")}
            - Party size: {selection['party_size']}
            - Confirmation #: {confirmation_number}
            
            Be warm and helpful, mentioning they'll receive email confirmation.
            """
            
            message = await self.ai_client.generate_response(confirmation_prompt)
            
            return {
                'status': 'confirmed',
                'message': message,
                'confirmation_number': confirmation_number,
                'booking_details': booking_result
            }
            
        except Exception as e:
            logger.error(f"Booking confirmation failed: {e}")
            return {
                'status': 'error',
                'message': "I couldn't complete your reservation. Would you like me to try again or help you contact the restaurant directly?",
                'fallback': True
            }
    
    async def check_existing_reservations(self, user: User, timeframe: str = "upcoming") -> Dict[str, Any]:
        """Check user's existing reservations"""
        
        try:
            from ..models.booking import Booking
            from sqlalchemy import and_, or_
            from datetime import datetime, timedelta
            
            # Define timeframe filters
            now = datetime.utcnow()
            if timeframe == "upcoming":
                filter_condition = and_(
                    Booking.user_id == user.id,
                    Booking.booking_datetime >= now,
                    Booking.status.in_(['confirmed', 'pending'])
                )
            elif timeframe == "past":
                filter_condition = and_(
                    Booking.user_id == user.id,
                    Booking.booking_datetime < now
                )
            elif timeframe == "today":
                today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                today_end = today_start + timedelta(days=1)
                filter_condition = and_(
                    Booking.user_id == user.id,
                    Booking.booking_datetime >= today_start,
                    Booking.booking_datetime < today_end
                )
            else:  # all
                filter_condition = Booking.user_id == user.id
            
            # Query database
            async with self.db() as session:
                result = await session.execute(
                    select(Booking)
                    .where(filter_condition)
                    .order_by(Booking.booking_datetime)
                    .limit(10)
                )
                bookings = result.scalars().all()
            
            # Format reservations
            reservations = []
            for booking in bookings:
                reservations.append({
                    'id': str(booking.id),
                    'type': booking.booking_type,
                    'vendor': booking.vendor_name,
                    'datetime': booking.booking_datetime.isoformat(),
                    'status': booking.status,
                    'details': booking.booking_details,
                    'confirmation_code': booking.confirmation_code
                })
            
            if reservations:
                message = f"You have {len(reservations)} {timeframe} reservation(s). Would you like me to show the details?"
            else:
                message = f"You don't have any {timeframe} reservations."
            
            return {
                'status': 'success',
                'reservations': reservations,
                'message': message,
                'count': len(reservations)
            }
            
        except Exception as e:
            logger.error(f"Failed to check reservations: {e}")
            return {
                'status': 'error',
                'message': "I couldn't retrieve your reservations right now.",
                'fallback': True
            }
    
    async def suggest_proactive_bookings(self, context: Dict[str, Any], user: User) -> Optional[Dict[str, Any]]:
        """Proactively suggest bookings based on context"""
        
        # Check if it's meal time and no recent restaurant booking
        current_time = context.get('current_time', datetime.now())
        location = context.get('location', {})
        
        # Lunch time check (11:30 AM - 1:30 PM)
        if 11.5 <= current_time.hour + current_time.minute/60 <= 13.5:
            return {
                'type': 'restaurant',
                'timing': 'lunch',
                'message': "It's getting close to lunch time. Would you like me to find some restaurants nearby?",
                'context': {'meal_type': 'lunch', 'urgency': 'soon'}
            }
        
        # Dinner time check (5:30 PM - 7:30 PM)
        elif 17.5 <= current_time.hour + current_time.minute/60 <= 19.5:
            return {
                'type': 'restaurant',
                'timing': 'dinner',
                'message': "Evening is approaching. Shall I look for dinner options along your route?",
                'context': {'meal_type': 'dinner', 'urgency': 'planning'}
            }
        
        # Check for nearby attractions during daytime
        elif 9 <= current_time.hour <= 17 and context.get('journey_stage') != 'in_transit':
            return {
                'type': 'attraction',
                'timing': 'daytime',
                'message': "There are some interesting attractions nearby. Would you like to explore any?",
                'context': {'activity_type': 'sightseeing', 'urgency': 'optional'}
            }
        
        return None