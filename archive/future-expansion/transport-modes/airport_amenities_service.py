"""
Airport Amenities Service

Provides comprehensive airport lounge access, dining options, terminal maps,
and amenity recommendations based on user preferences and wait times.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass
from enum import Enum

from backend.app.core.logger import get_logger
from backend.app.core.cache import get_cache
from backend.app.integrations.priority_pass_client import PriorityPassClient
from backend.app.integrations.airline_lounge_client import AirlineLoungeClient
from backend.app.integrations.airport_dining_client import AirportDiningClient
from backend.app.services.commission_calculator import CommissionCalculator

logger = get_logger(__name__)


class AmenityType(str, Enum):
    LOUNGE = "lounge"
    RESTAURANT = "restaurant"
    CAFE = "cafe"
    BAR = "bar"
    SHOP = "shop"
    SPA = "spa"
    SLEEPING_POD = "sleeping_pod"
    SHOWER = "shower"
    KIDS_AREA = "kids_area"
    QUIET_ZONE = "quiet_zone"


class BookingStatus(str, Enum):
    AVAILABLE = "available"
    WAITLIST = "waitlist"
    FULL = "full"
    CLOSED = "closed"


@dataclass
class AirportAmenity:
    """Represents an airport amenity"""
    id: str
    type: AmenityType
    name: str
    description: str
    terminal: str
    gate_area: Optional[str]
    location_description: str
    hours: Dict[str, str]
    amenities: List[str]
    price_range: Optional[str]
    rating: Optional[float]
    reviews_count: Optional[int]
    walking_time_minutes: Optional[int]
    booking_status: BookingStatus
    booking_url: Optional[str]
    commission_rate: Optional[float]
    image_urls: List[str]
    tags: List[str]


@dataclass
class LoungeAccess:
    """Lounge access details"""
    lounge_id: str
    access_type: str  # priority_pass, airline_status, paid
    requirements: List[str]
    guest_policy: Optional[str]
    price: Optional[float]
    duration_hours: Optional[int]
    amenities: List[str]


@dataclass
class DiningReservation:
    """Restaurant reservation details"""
    restaurant_id: str
    available_times: List[datetime]
    party_size_options: List[int]
    cuisine_type: str
    dietary_options: List[str]
    average_meal_duration_minutes: int
    price_per_person: Optional[float]


class AirportAmenitiesService:
    """Manages airport amenities and recommendations"""
    
    def __init__(self):
        self.cache = get_cache()
        self.priority_pass_client = PriorityPassClient()
        self.airline_lounge_client = AirlineLoungeClient()
        self.airport_dining_client = AirportDiningClient()
        self.commission_calculator = CommissionCalculator()
        
    async def get_airport_amenities(
        self,
        airport_code: str,
        terminal: Optional[str] = None,
        amenity_types: Optional[List[AmenityType]] = None,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> List[AirportAmenity]:
        """Get available amenities at an airport"""
        try:
            # Check cache
            cache_key = f"airport_amenities:{airport_code}:{terminal}"
            cached = await self.cache.get(cache_key)
            if cached:
                amenities = cached
            else:
                # Fetch from multiple sources concurrently
                amenities = await self._fetch_all_amenities(
                    airport_code, terminal
                )
                await self.cache.set(cache_key, amenities, expire=3600)
            
            # Filter by requested types
            if amenity_types:
                amenities = [
                    a for a in amenities 
                    if a.type in amenity_types
                ]
            
            # Apply user preferences
            if user_preferences:
                amenities = self._apply_preferences(
                    amenities, user_preferences
                )
            
            # Sort by relevance
            return self._sort_by_relevance(amenities, user_preferences)
            
        except Exception as e:
            logger.error(f"Failed to get airport amenities: {e}")
            return []
    
    async def _fetch_all_amenities(
        self,
        airport_code: str,
        terminal: Optional[str]
    ) -> List[AirportAmenity]:
        """Fetch amenities from all sources"""
        tasks = [
            self._fetch_lounges(airport_code, terminal),
            self._fetch_dining(airport_code, terminal),
            self._fetch_other_amenities(airport_code, terminal)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_amenities = []
        for result in results:
            if isinstance(result, list):
                all_amenities.extend(result)
            else:
                logger.error(f"Failed to fetch amenities: {result}")
        
        return all_amenities
    
    async def _fetch_lounges(
        self,
        airport_code: str,
        terminal: Optional[str]
    ) -> List[AirportAmenity]:
        """Fetch lounge information"""
        lounges = []
        
        # Priority Pass lounges
        pp_lounges = await self.priority_pass_client.get_lounges(
            airport_code, terminal
        )
        for lounge in pp_lounges:
            lounges.append(AirportAmenity(
                id=f"pp_{lounge['id']}",
                type=AmenityType.LOUNGE,
                name=lounge['name'],
                description=lounge['description'],
                terminal=lounge['terminal'],
                gate_area=lounge.get('gate_area'),
                location_description=lounge['location'],
                hours=lounge['hours'],
                amenities=lounge['amenities'],
                price_range="$$$",
                rating=lounge.get('rating'),
                reviews_count=lounge.get('reviews_count'),
                walking_time_minutes=None,
                booking_status=BookingStatus.AVAILABLE,
                booking_url=lounge.get('booking_url'),
                commission_rate=0.15,  # 15% commission
                image_urls=lounge.get('images', []),
                tags=['priority_pass', 'lounge']
            ))
        
        # Airline lounges
        airline_lounges = await self.airline_lounge_client.get_lounges(
            airport_code, terminal
        )
        for lounge in airline_lounges:
            lounges.append(AirportAmenity(
                id=f"airline_{lounge['id']}",
                type=AmenityType.LOUNGE,
                name=lounge['name'],
                description=lounge['description'],
                terminal=lounge['terminal'],
                gate_area=lounge.get('gate_area'),
                location_description=lounge['location'],
                hours=lounge['hours'],
                amenities=lounge['amenities'],
                price_range=lounge.get('price_range', "$$$"),
                rating=lounge.get('rating'),
                reviews_count=lounge.get('reviews_count'),
                walking_time_minutes=None,
                booking_status=self._parse_booking_status(
                    lounge.get('availability')
                ),
                booking_url=lounge.get('booking_url'),
                commission_rate=0.12,  # 12% commission
                image_urls=lounge.get('images', []),
                tags=[lounge['airline'], 'airline_lounge', 'lounge']
            ))
        
        return lounges
    
    async def _fetch_dining(
        self,
        airport_code: str,
        terminal: Optional[str]
    ) -> List[AirportAmenity]:
        """Fetch dining options"""
        dining_options = []
        
        restaurants = await self.airport_dining_client.get_restaurants(
            airport_code, terminal
        )
        
        for restaurant in restaurants:
            dining_type = self._determine_dining_type(restaurant)
            dining_options.append(AirportAmenity(
                id=f"dining_{restaurant['id']}",
                type=dining_type,
                name=restaurant['name'],
                description=restaurant.get('description', ''),
                terminal=restaurant['terminal'],
                gate_area=restaurant.get('gate_area'),
                location_description=restaurant['location'],
                hours=restaurant['hours'],
                amenities=restaurant.get('features', []),
                price_range=restaurant.get('price_range'),
                rating=restaurant.get('rating'),
                reviews_count=restaurant.get('reviews_count'),
                walking_time_minutes=None,
                booking_status=self._parse_booking_status(
                    restaurant.get('reservation_availability')
                ),
                booking_url=restaurant.get('reservation_url'),
                commission_rate=0.08 if restaurant.get('accepts_reservations') else None,
                image_urls=restaurant.get('images', []),
                tags=restaurant.get('cuisine_types', []) + ['dining']
            ))
        
        return dining_options
    
    async def _fetch_other_amenities(
        self,
        airport_code: str,
        terminal: Optional[str]
    ) -> List[AirportAmenity]:
        """Fetch other amenities like spas, sleeping pods, etc."""
        # This would integrate with additional APIs
        # For now, returning empty list
        return []
    
    def _determine_dining_type(self, restaurant: Dict) -> AmenityType:
        """Determine the type of dining establishment"""
        name_lower = restaurant['name'].lower()
        tags = [t.lower() for t in restaurant.get('tags', [])]
        
        if any(term in name_lower or term in tags for term in ['bar', 'pub', 'brewery']):
            return AmenityType.BAR
        elif any(term in name_lower or term in tags for term in ['cafe', 'coffee', 'starbucks']):
            return AmenityType.CAFE
        else:
            return AmenityType.RESTAURANT
    
    def _parse_booking_status(self, availability: Optional[str]) -> BookingStatus:
        """Parse availability into booking status"""
        if not availability:
            return BookingStatus.AVAILABLE
        
        availability_lower = availability.lower()
        if 'full' in availability_lower or 'sold out' in availability_lower:
            return BookingStatus.FULL
        elif 'waitlist' in availability_lower:
            return BookingStatus.WAITLIST
        elif 'closed' in availability_lower:
            return BookingStatus.CLOSED
        else:
            return BookingStatus.AVAILABLE
    
    def _apply_preferences(
        self,
        amenities: List[AirportAmenity],
        preferences: Dict[str, Any]
    ) -> List[AirportAmenity]:
        """Filter amenities based on user preferences"""
        filtered = amenities
        
        # Filter by price range
        if 'max_price_range' in preferences:
            max_range = preferences['max_price_range']
            filtered = [
                a for a in filtered
                if not a.price_range or len(a.price_range) <= len(max_range)
            ]
        
        # Filter by dietary restrictions for dining
        if 'dietary_restrictions' in preferences:
            restrictions = preferences['dietary_restrictions']
            filtered = [
                a for a in filtered
                if a.type not in [AmenityType.RESTAURANT, AmenityType.CAFE] or
                any(r in a.tags for r in restrictions)
            ]
        
        # Filter by minimum rating
        if 'min_rating' in preferences:
            min_rating = preferences['min_rating']
            filtered = [
                a for a in filtered
                if not a.rating or a.rating >= min_rating
            ]
        
        return filtered
    
    def _sort_by_relevance(
        self,
        amenities: List[AirportAmenity],
        preferences: Optional[Dict[str, Any]]
    ) -> List[AirportAmenity]:
        """Sort amenities by relevance score"""
        def relevance_score(amenity: AirportAmenity) -> float:
            score = 0.0
            
            # Rating contribution
            if amenity.rating:
                score += amenity.rating * 2
            
            # Reviews count contribution
            if amenity.reviews_count:
                score += min(amenity.reviews_count / 100, 5)
            
            # Commission rate contribution (business priority)
            if amenity.commission_rate:
                score += amenity.commission_rate * 10
            
            # Availability boost
            if amenity.booking_status == BookingStatus.AVAILABLE:
                score += 3
            
            # User preference matching
            if preferences:
                if 'preferred_amenities' in preferences:
                    matches = sum(
                        1 for a in amenity.amenities
                        if a in preferences['preferred_amenities']
                    )
                    score += matches * 2
            
            return score
        
        return sorted(amenities, key=relevance_score, reverse=True)
    
    async def get_lounge_access_options(
        self,
        lounge_id: str,
        user_id: str,
        flight_details: Dict[str, Any]
    ) -> List[LoungeAccess]:
        """Get available access options for a specific lounge"""
        try:
            # Extract lounge type and ID
            if lounge_id.startswith('pp_'):
                return await self._get_priority_pass_access(
                    lounge_id[3:], user_id, flight_details
                )
            elif lounge_id.startswith('airline_'):
                return await self._get_airline_lounge_access(
                    lounge_id[8:], user_id, flight_details
                )
            else:
                logger.warning(f"Unknown lounge type: {lounge_id}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to get lounge access options: {e}")
            return []
    
    async def _get_priority_pass_access(
        self,
        lounge_id: str,
        user_id: str,
        flight_details: Dict[str, Any]
    ) -> List[LoungeAccess]:
        """Get Priority Pass access options"""
        access_options = []
        
        # Check if user has Priority Pass membership
        membership = await self.priority_pass_client.check_membership(user_id)
        
        if membership:
            access_options.append(LoungeAccess(
                lounge_id=lounge_id,
                access_type="priority_pass",
                requirements=["Valid Priority Pass membership"],
                guest_policy=membership.get('guest_policy'),
                price=0.0,
                duration_hours=3,
                amenities=[]
            ))
        
        # Paid access option
        paid_access = await self.priority_pass_client.get_paid_access(lounge_id)
        if paid_access:
            access_options.append(LoungeAccess(
                lounge_id=lounge_id,
                access_type="paid",
                requirements=[],
                guest_policy="Additional fee per guest",
                price=paid_access['price'],
                duration_hours=paid_access.get('duration_hours', 3),
                amenities=paid_access.get('included_amenities', [])
            ))
        
        return access_options
    
    async def _get_airline_lounge_access(
        self,
        lounge_id: str,
        user_id: str,
        flight_details: Dict[str, Any]
    ) -> List[LoungeAccess]:
        """Get airline lounge access options"""
        access_options = []
        
        # Check airline status
        status = await self.airline_lounge_client.check_status(
            user_id, flight_details['airline']
        )
        
        if status and status['has_access']:
            access_options.append(LoungeAccess(
                lounge_id=lounge_id,
                access_type="airline_status",
                requirements=[f"{flight_details['airline']} {status['tier']} member"],
                guest_policy=status.get('guest_policy'),
                price=0.0,
                duration_hours=None,  # Usually until flight
                amenities=[]
            ))
        
        # Check if business/first class ticket grants access
        if flight_details.get('class') in ['business', 'first']:
            access_options.append(LoungeAccess(
                lounge_id=lounge_id,
                access_type="ticket_class",
                requirements=[f"{flight_details['class'].title()} class ticket"],
                guest_policy="Ticket holder only",
                price=0.0,
                duration_hours=None,
                amenities=[]
            ))
        
        # Paid day pass option
        day_pass = await self.airline_lounge_client.get_day_pass(lounge_id)
        if day_pass:
            access_options.append(LoungeAccess(
                lounge_id=lounge_id,
                access_type="paid",
                requirements=[],
                guest_policy="Additional fee per guest",
                price=day_pass['price'],
                duration_hours=day_pass.get('duration_hours'),
                amenities=day_pass.get('included_amenities', [])
            ))
        
        return access_options
    
    async def check_dining_availability(
        self,
        restaurant_id: str,
        party_size: int,
        preferred_time: datetime,
        duration_minutes: int = 60
    ) -> DiningReservation:
        """Check restaurant availability"""
        try:
            # Extract restaurant ID
            if restaurant_id.startswith('dining_'):
                restaurant_id = restaurant_id[7:]
            
            # Get availability from dining API
            availability = await self.airport_dining_client.check_availability(
                restaurant_id,
                party_size,
                preferred_time,
                duration_minutes
            )
            
            if not availability:
                return None
            
            return DiningReservation(
                restaurant_id=restaurant_id,
                available_times=availability['times'],
                party_size_options=availability['party_sizes'],
                cuisine_type=availability['cuisine'],
                dietary_options=availability.get('dietary_options', []),
                average_meal_duration_minutes=availability.get('avg_duration', 60),
                price_per_person=availability.get('avg_price')
            )
            
        except Exception as e:
            logger.error(f"Failed to check dining availability: {e}")
            return None
    
    async def book_amenity(
        self,
        amenity_id: str,
        user_id: str,
        booking_details: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Book an airport amenity"""
        try:
            # Route to appropriate booking method
            if amenity_id.startswith('pp_'):
                return await self._book_priority_pass_lounge(
                    amenity_id[3:], user_id, booking_details
                )
            elif amenity_id.startswith('airline_'):
                return await self._book_airline_lounge(
                    amenity_id[8:], user_id, booking_details
                )
            elif amenity_id.startswith('dining_'):
                return await self._book_restaurant(
                    amenity_id[7:], user_id, booking_details
                )
            else:
                logger.warning(f"Unknown amenity type: {amenity_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to book amenity: {e}")
            return None
    
    async def _book_priority_pass_lounge(
        self,
        lounge_id: str,
        user_id: str,
        booking_details: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Book Priority Pass lounge access"""
        booking = await self.priority_pass_client.book_lounge(
            lounge_id,
            user_id,
            booking_details
        )
        
        if booking:
            # Calculate commission
            commission = await self.commission_calculator.calculate_commission(
                'priority_pass',
                booking['total_amount'],
                {'lounge_id': lounge_id}
            )
            
            booking['commission'] = commission
            
            # Log successful booking
            logger.info(
                f"Booked Priority Pass lounge {lounge_id} for user {user_id}, "
                f"commission: ${commission:.2f}"
            )
        
        return booking
    
    async def _book_airline_lounge(
        self,
        lounge_id: str,
        user_id: str,
        booking_details: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Book airline lounge access"""
        booking = await self.airline_lounge_client.book_lounge(
            lounge_id,
            user_id,
            booking_details
        )
        
        if booking:
            # Calculate commission
            commission = await self.commission_calculator.calculate_commission(
                'airline_lounge',
                booking['total_amount'],
                {'lounge_id': lounge_id, 'airline': booking.get('airline')}
            )
            
            booking['commission'] = commission
            
            logger.info(
                f"Booked airline lounge {lounge_id} for user {user_id}, "
                f"commission: ${commission:.2f}"
            )
        
        return booking
    
    async def _book_restaurant(
        self,
        restaurant_id: str,
        user_id: str,
        booking_details: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Book restaurant reservation"""
        booking = await self.airport_dining_client.book_restaurant(
            restaurant_id,
            user_id,
            booking_details
        )
        
        if booking:
            # Calculate commission (usually based on party size)
            estimated_spend = (
                booking.get('party_size', 2) * 
                booking.get('avg_price_per_person', 30)
            )
            commission = await self.commission_calculator.calculate_commission(
                'airport_dining',
                estimated_spend,
                {'restaurant_id': restaurant_id}
            )
            
            booking['commission'] = commission
            
            logger.info(
                f"Booked restaurant {restaurant_id} for user {user_id}, "
                f"party of {booking.get('party_size')}, "
                f"commission: ${commission:.2f}"
            )
        
        return booking
    
    async def get_recommendations_by_wait_time(
        self,
        airport_code: str,
        terminal: str,
        wait_time_minutes: int,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Get amenity recommendations based on available wait time"""
        recommendations = []
        
        # Get all amenities
        amenities = await self.get_airport_amenities(
            airport_code, terminal, user_preferences=user_preferences
        )
        
        # Categorize by wait time
        if wait_time_minutes < 30:
            # Quick options: cafes, grab-and-go
            relevant_types = [AmenityType.CAFE, AmenityType.BAR]
            recommendations.append({
                'category': 'Quick Refreshment',
                'reason': f'Perfect for your {wait_time_minutes} minute wait',
                'options': [
                    a for a in amenities 
                    if a.type in relevant_types and
                    a.booking_status == BookingStatus.AVAILABLE
                ][:3]
            })
            
        elif wait_time_minutes < 90:
            # Medium wait: restaurants, express spa
            relevant_types = [AmenityType.RESTAURANT, AmenityType.LOUNGE]
            recommendations.append({
                'category': 'Dining & Relaxation',
                'reason': 'Enjoy a meal or lounge access',
                'options': [
                    a for a in amenities 
                    if a.type in relevant_types and
                    a.booking_status == BookingStatus.AVAILABLE
                ][:5]
            })
            
        else:
            # Long wait: full amenities
            recommendations.append({
                'category': 'Premium Lounges',
                'reason': 'Relax in comfort during your extended wait',
                'options': [
                    a for a in amenities 
                    if a.type == AmenityType.LOUNGE and
                    a.booking_status == BookingStatus.AVAILABLE
                ][:3]
            })
            
            recommendations.append({
                'category': 'Full Service Dining',
                'reason': 'Enjoy a leisurely meal',
                'options': [
                    a for a in amenities 
                    if a.type == AmenityType.RESTAURANT and
                    a.rating and a.rating >= 4.0
                ][:3]
            })
            
            # Add spa/wellness if available
            wellness = [
                a for a in amenities 
                if a.type in [AmenityType.SPA, AmenityType.SHOWER]
            ]
            if wellness:
                recommendations.append({
                    'category': 'Wellness & Refresh',
                    'reason': 'Refresh before your flight',
                    'options': wellness[:2]
                })
        
        return recommendations
    
    async def calculate_walking_times(
        self,
        amenities: List[AirportAmenity],
        current_gate: str,
        departure_gate: str
    ) -> List[AirportAmenity]:
        """Calculate walking times between gates and amenities"""
        # This would integrate with airport terminal maps API
        # For now, returning amenities with estimated times
        for amenity in amenities:
            if amenity.gate_area:
                # Simple estimation based on gate distance
                amenity.walking_time_minutes = self._estimate_walking_time(
                    current_gate, amenity.gate_area, departure_gate
                )
        
        return amenities
    
    def _estimate_walking_time(
        self,
        from_gate: str,
        amenity_location: str,
        to_gate: str
    ) -> int:
        """Estimate walking time between locations"""
        # Simplified calculation - would use real terminal maps
        base_time = 5
        
        # Add time if different concourse
        if from_gate[0] != amenity_location[0]:
            base_time += 10
        
        # Add time to reach departure gate
        if amenity_location[0] != to_gate[0]:
            base_time += 10
        
        return base_time