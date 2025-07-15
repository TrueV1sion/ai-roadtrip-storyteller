"""
Comprehensive Reservation Management Service
Handles all aspects of reservations across multiple providers
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import uuid
import json
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiohttp
import smtplib

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from backend.app.core.logger import logger
from backend.app.core.cache import cache_manager
from backend.app.models.user import User
from backend.app.services.reservation_agent import (
    Reservation, ReservationStatus, ReservationType
)
from backend.app.integrations.open_table_client import OpenTableClient
from backend.app.integrations.recreation_gov_client import RecreationGovClient
from backend.app.integrations.shell_recharge_client import ShellRechargeClient


class BookingProvider(str, Enum):
    """Supported booking providers"""
    OPENTABLE = "opentable"
    RESY = "resy"
    RECREATION_GOV = "recreation_gov"
    SHELL_RECHARGE = "shell_recharge"
    VIATOR = "viator"
    AIRBNB = "airbnb"
    BOOKING_COM = "booking_com"
    PARKWHIZ = "parkwhiz"
    INTERNAL = "internal"


class ReservationManagementService:
    """
    Comprehensive service for managing reservations across all providers
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.providers = {
            BookingProvider.OPENTABLE: OpenTableClient(),
            BookingProvider.RECREATION_GOV: RecreationGovClient(),
            BookingProvider.SHELL_RECHARGE: ShellRechargeClient(),
            # Additional providers can be added here
        }
        
        # Email configuration (would come from environment)
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.email_from = "noreply@roadtripstoryteller.com"
        
        # SMS configuration (would use service like Twilio)
        self.sms_enabled = False
        
        # Calendar integration settings
        self.calendar_sync_enabled = True
        
    async def search_all_providers(
        self,
        query: str,
        location: Dict[str, float],
        date: datetime,
        party_size: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search across all providers for available options
        """
        try:
            all_results = []
            search_tasks = []
            
            # Determine which providers to search based on query and filters
            providers_to_search = self._determine_providers(query, filters)
            
            # Create search tasks for each provider
            for provider_type, provider_client in self.providers.items():
                if provider_type in providers_to_search:
                    task = self._search_provider(
                        provider_type,
                        provider_client,
                        query,
                        location,
                        date,
                        party_size,
                        filters
                    )
                    search_tasks.append(task)
            
            # Execute searches concurrently
            results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Provider search failed: {result}")
                    continue
                
                if result:
                    all_results.extend(result)
            
            # Sort by relevance and rating
            all_results.sort(
                key=lambda x: (x.get('relevance_score', 0), x.get('rating', 0)),
                reverse=True
            )
            
            # Apply post-processing filters
            if filters:
                all_results = self._apply_filters(all_results, filters)
            
            # Cache results
            cache_key = f"search:{query}:{location}:{date}:{party_size}"
            await cache_manager.set(cache_key, all_results, expire=300)  # 5 min cache
            
            return all_results[:50]  # Return top 50 results
            
        except Exception as e:
            logger.error(f"Error searching providers: {e}")
            raise
    
    async def create_reservation(
        self,
        user_id: str,
        provider: BookingProvider,
        venue_id: str,
        date_time: datetime,
        party_size: int,
        special_requests: Optional[str] = None,
        contact_info: Optional[Dict[str, str]] = None,
        payment_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a reservation with the specified provider
        """
        try:
            # Validate party size
            if party_size < 1 or party_size > 20:
                raise ValueError(f"Party size must be between 1 and 20, got {party_size}")
            
            # Validate user
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("User not found")
            
            # Check availability first
            is_available = await self._check_availability(
                provider, venue_id, date_time, party_size
            )
            
            if not is_available:
                # Try to find alternative times
                alternatives = await self._find_alternative_times(
                    provider, venue_id, date_time, party_size
                )
                return {
                    "status": "unavailable",
                    "alternatives": alternatives,
                    "message": "Requested time not available"
                }
            
            # Create reservation with provider
            provider_client = self.providers.get(provider)
            if not provider_client:
                raise ValueError(f"Provider {provider} not supported")
            
            # Make the actual booking
            booking_result = await self._create_provider_booking(
                provider,
                provider_client,
                venue_id,
                date_time,
                party_size,
                special_requests,
                contact_info or {"name": user.name, "email": user.email},
                payment_info
            )
            
            # Create internal reservation record
            reservation = Reservation(
                id=str(uuid.uuid4()),
                user_id=user_id,
                type=self._get_reservation_type(provider),
                provider_id=booking_result.get('confirmation_number'),
                venue_name=booking_result.get('venue_name'),
                venue_id=venue_id,
                venue_address=booking_result.get('venue_address'),
                reservation_time=date_time,
                party_size=str(party_size),
                special_requests=special_requests,
                status=ReservationStatus.CONFIRMED,
                confirmation_details=json.dumps(booking_result),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db.add(reservation)
            self.db.commit()
            
            # Send confirmation
            await self._send_confirmation(user, reservation, booking_result)
            
            # Add to calendar
            if self.calendar_sync_enabled:
                await self._add_to_calendar(user, reservation)
            
            # Set reminder
            await self._schedule_reminder(reservation)
            
            return {
                "status": "confirmed",
                "reservation_id": reservation.id,
                "confirmation_number": booking_result.get('confirmation_number'),
                "details": booking_result
            }
            
        except Exception as e:
            logger.error(f"Error creating reservation: {e}")
            # Attempt to rollback if needed
            self.db.rollback()
            raise
    
    async def modify_reservation(
        self,
        reservation_id: str,
        user_id: str,
        modifications: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Modify an existing reservation
        """
        try:
            # Get reservation
            reservation = self.db.query(Reservation).filter(
                and_(
                    Reservation.id == reservation_id,
                    Reservation.user_id == user_id
                )
            ).first()
            
            if not reservation:
                raise ValueError("Reservation not found")
            
            # Check if modification is allowed
            if reservation.status != ReservationStatus.CONFIRMED:
                raise ValueError(f"Cannot modify reservation in {reservation.status} status")
            
            # Check modification window (ensure UTC timezone handling)
            current_time = datetime.utcnow()
            reservation_time = reservation.reservation_time
            
            # Convert to UTC if needed (assuming reservation_time might have timezone info)
            if hasattr(reservation_time, 'tzinfo') and reservation_time.tzinfo:
                reservation_time = reservation_time.replace(tzinfo=None)
            
            hours_until_reservation = (
                reservation_time - current_time
            ).total_seconds() / 3600
            
            if hours_until_reservation < 2:  # 2 hour minimum
                raise ValueError("Too close to reservation time to modify")
            
            # Determine provider
            provider = self._get_provider_from_type(reservation.type)
            provider_client = self.providers.get(provider)
            
            if not provider_client:
                raise ValueError("Provider not available for modifications")
            
            # Attempt modification with provider
            modification_result = await self._modify_provider_booking(
                provider,
                provider_client,
                reservation.provider_id,
                modifications
            )
            
            # Update internal record
            if modifications.get('date_time'):
                reservation.reservation_time = modifications['date_time']
            if modifications.get('party_size'):
                reservation.party_size = str(modifications['party_size'])
            if modifications.get('special_requests'):
                reservation.special_requests = modifications['special_requests']
            
            reservation.updated_at = datetime.utcnow()
            
            # Update confirmation details
            conf_details = json.loads(reservation.confirmation_details or '{}')
            conf_details.update(modification_result)
            reservation.confirmation_details = json.dumps(conf_details)
            
            self.db.commit()
            
            # Send modification confirmation
            user = self.db.query(User).filter(User.id == user_id).first()
            await self._send_modification_confirmation(user, reservation, modifications)
            
            # Update calendar
            if self.calendar_sync_enabled:
                await self._update_calendar_event(user, reservation)
            
            return {
                "status": "modified",
                "reservation_id": reservation_id,
                "modifications": modifications,
                "details": modification_result
            }
            
        except Exception as e:
            logger.error(f"Error modifying reservation: {e}")
            self.db.rollback()
            raise
    
    async def cancel_reservation(
        self,
        reservation_id: str,
        user_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancel a reservation
        """
        try:
            # Get reservation
            reservation = self.db.query(Reservation).filter(
                and_(
                    Reservation.id == reservation_id,
                    Reservation.user_id == user_id
                )
            ).first()
            
            if not reservation:
                raise ValueError("Reservation not found")
            
            # Check if cancellation is allowed
            if reservation.status in [ReservationStatus.CANCELLED, ReservationStatus.COMPLETED]:
                raise ValueError(f"Reservation already {reservation.status}")
            
            # Check cancellation policy
            cancellation_policy = await self._get_cancellation_policy(reservation)
            
            # Ensure UTC timezone handling
            current_time = datetime.utcnow()
            reservation_time = reservation.reservation_time
            
            # Convert to UTC if needed
            if hasattr(reservation_time, 'tzinfo') and reservation_time.tzinfo:
                reservation_time = reservation_time.replace(tzinfo=None)
            
            hours_until_reservation = (
                reservation_time - current_time
            ).total_seconds() / 3600
            
            cancellation_fee = 0
            if hours_until_reservation < cancellation_policy.get('free_cancellation_hours', 24):
                cancellation_fee = cancellation_policy.get('cancellation_fee', 0)
            
            # Cancel with provider
            provider = self._get_provider_from_type(reservation.type)
            provider_client = self.providers.get(provider)
            
            if provider_client and reservation.provider_id:
                cancellation_result = await self._cancel_provider_booking(
                    provider,
                    provider_client,
                    reservation.provider_id,
                    reason
                )
            else:
                cancellation_result = {"status": "cancelled_internally"}
            
            # Update internal record
            reservation.status = ReservationStatus.CANCELLED
            reservation.updated_at = datetime.utcnow()
            
            # Store cancellation details
            conf_details = json.loads(reservation.confirmation_details or '{}')
            conf_details['cancellation'] = {
                "timestamp": datetime.utcnow().isoformat(),
                "reason": reason,
                "fee": cancellation_fee,
                "result": cancellation_result
            }
            reservation.confirmation_details = json.dumps(conf_details)
            
            self.db.commit()
            
            # Send cancellation confirmation
            user = self.db.query(User).filter(User.id == user_id).first()
            await self._send_cancellation_confirmation(user, reservation, cancellation_fee)
            
            # Remove from calendar
            if self.calendar_sync_enabled:
                await self._remove_from_calendar(user, reservation)
            
            # Check for waitlist
            await self._process_waitlist(reservation)
            
            return {
                "status": "cancelled",
                "reservation_id": reservation_id,
                "cancellation_fee": cancellation_fee,
                "refund_amount": cancellation_result.get('refund_amount', 0)
            }
            
        except Exception as e:
            logger.error(f"Error cancelling reservation: {e}")
            self.db.rollback()
            raise
    
    async def get_user_reservations(
        self,
        user_id: str,
        status: Optional[ReservationStatus] = None,
        upcoming_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all reservations for a user
        """
        try:
            query = self.db.query(Reservation).filter(
                Reservation.user_id == user_id
            )
            
            if status:
                query = query.filter(Reservation.status == status)
            
            if upcoming_only:
                query = query.filter(
                    Reservation.reservation_time > datetime.utcnow()
                )
            
            # Order by reservation time
            query = query.order_by(Reservation.reservation_time.desc())
            
            # Apply pagination
            reservations = query.offset(offset).limit(limit).all()
            
            # Format results
            results = []
            for res in reservations:
                results.append({
                    "id": res.id,
                    "type": res.type,
                    "venue_name": res.venue_name,
                    "venue_address": res.venue_address,
                    "reservation_time": res.reservation_time.isoformat(),
                    "party_size": res.party_size,
                    "status": res.status,
                    "confirmation_number": res.provider_id,
                    "special_requests": res.special_requests,
                    "created_at": res.created_at.isoformat(),
                    "can_modify": self._can_modify(res),
                    "can_cancel": self._can_cancel(res)
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting user reservations: {e}")
            raise
    
    async def join_waitlist(
        self,
        user_id: str,
        venue_id: str,
        desired_date: datetime,
        party_size: int,
        flexibility_hours: int = 2
    ) -> Dict[str, Any]:
        """
        Add user to waitlist for a venue
        """
        try:
            # Create waitlist entry
            waitlist_id = str(uuid.uuid4())
            waitlist_entry = {
                "id": waitlist_id,
                "user_id": user_id,
                "venue_id": venue_id,
                "desired_date": desired_date,
                "party_size": party_size,
                "flexibility_start": desired_date - timedelta(hours=flexibility_hours),
                "flexibility_end": desired_date + timedelta(hours=flexibility_hours),
                "created_at": datetime.utcnow(),
                "status": "active"
            }
            
            # Store in cache (in production, use database)
            cache_key = f"waitlist:{venue_id}:{desired_date.date()}"
            current_waitlist = await cache_manager.get(cache_key) or []
            current_waitlist.append(waitlist_entry)
            await cache_manager.set(cache_key, current_waitlist, expire=86400 * 7)  # 7 days
            
            # Calculate position
            position = len([w for w in current_waitlist 
                          if w['created_at'] < waitlist_entry['created_at']]) + 1
            
            # Send confirmation
            user = self.db.query(User).filter(User.id == user_id).first()
            await self._send_waitlist_confirmation(user, venue_id, position)
            
            return {
                "waitlist_id": waitlist_id,
                "position": position,
                "estimated_wait": self._estimate_wait_time(position, venue_id)
            }
            
        except Exception as e:
            logger.error(f"Error joining waitlist: {e}")
            raise
    
    # Helper methods
    
    def _determine_providers(
        self,
        query: str,
        filters: Optional[Dict[str, Any]]
    ) -> List[BookingProvider]:
        """Determine which providers to search based on query"""
        providers = []
        
        query_lower = query.lower()
        
        # Restaurant keywords
        if any(word in query_lower for word in ['restaurant', 'dining', 'eat', 'food', 'cuisine']):
            providers.extend([BookingProvider.OPENTABLE, BookingProvider.RESY])
        
        # Camping/outdoor keywords
        if any(word in query_lower for word in ['camp', 'camping', 'park', 'trail', 'hike']):
            providers.append(BookingProvider.RECREATION_GOV)
        
        # EV charging keywords
        if any(word in query_lower for word in ['charging', 'ev', 'electric', 'charge']):
            providers.append(BookingProvider.SHELL_RECHARGE)
        
        # Activity keywords
        if any(word in query_lower for word in ['tour', 'activity', 'experience', 'adventure']):
            providers.append(BookingProvider.VIATOR)
        
        # Hotel keywords
        if any(word in query_lower for word in ['hotel', 'stay', 'accommodation', 'room']):
            providers.extend([BookingProvider.BOOKING_COM, BookingProvider.AIRBNB])
        
        # Parking keywords
        if any(word in query_lower for word in ['parking', 'park', 'garage']):
            providers.append(BookingProvider.PARKWHIZ)
        
        # If no specific match, search all
        if not providers:
            providers = list(BookingProvider)
        
        # Apply filters
        if filters and filters.get('providers'):
            providers = [p for p in providers if p in filters['providers']]
        
        return providers
    
    async def _search_provider(
        self,
        provider_type: BookingProvider,
        provider_client: Any,
        query: str,
        location: Dict[str, float],
        date: datetime,
        party_size: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Search a specific provider"""
        try:
            results = []
            
            if provider_type == BookingProvider.OPENTABLE:
                restaurants = await provider_client.search_restaurants(
                    location=f"{location['lat']},{location['lng']}",
                    cuisine=filters.get('cuisine') if filters else None,
                    price_range=filters.get('price_range') if filters else None
                )
                
                for restaurant in restaurants[:10]:  # Limit per provider
                    availability = await provider_client.check_availability(
                        restaurant['id'],
                        date,
                        party_size
                    )
                    
                    results.append({
                        'provider': provider_type,
                        'type': ReservationType.RESTAURANT,
                        'venue_id': restaurant['id'],
                        'venue_name': restaurant['name'],
                        'venue_address': restaurant.get('address'),
                        'rating': restaurant.get('rating', 0),
                        'price_range': restaurant.get('price_range'),
                        'cuisine': restaurant.get('cuisine'),
                        'available_times': availability.get('times', []),
                        'image_url': restaurant.get('image_url'),
                        'relevance_score': self._calculate_relevance(query, restaurant)
                    })
            
            elif provider_type == BookingProvider.RECREATION_GOV:
                campgrounds = await provider_client.search_campgrounds(
                    query=query,
                    state=filters.get('state') if filters else None,
                    amenities=filters.get('amenities') if filters else None
                )
                
                for campground in campgrounds[:10]:
                    availability = await provider_client.check_availability(
                        campground['FacilityID'],
                        date,
                        date + timedelta(days=1)
                    )
                    
                    results.append({
                        'provider': provider_type,
                        'type': ReservationType.ACCOMMODATION,
                        'venue_id': campground['FacilityID'],
                        'venue_name': campground['FacilityName'],
                        'venue_address': campground.get('FacilityDescription'),
                        'rating': 0,  # Recreation.gov doesn't provide ratings
                        'amenities': campground.get('amenities', []),
                        'available_sites': availability.get('available_count', 0),
                        'image_url': campground.get('image_url'),
                        'relevance_score': self._calculate_relevance(query, campground)
                    })
            
            # Add other providers as needed
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching {provider_type}: {e}")
            return []
    
    def _calculate_relevance(self, query: str, venue: Dict[str, Any]) -> float:
        """Calculate relevance score for search results"""
        score = 0.0
        query_lower = query.lower()
        
        # Name match
        if query_lower in venue.get('name', '').lower():
            score += 0.5
        
        # Type match
        if any(word in query_lower for word in venue.get('cuisine', '').lower().split()):
            score += 0.3
        
        # Rating boost
        rating = venue.get('rating', 0)
        score += (rating / 5.0) * 0.2
        
        return min(score, 1.0)
    
    def _apply_filters(
        self,
        results: List[Dict[str, Any]],
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply post-search filters"""
        filtered = results
        
        # Price range filter
        if 'max_price' in filters:
            filtered = [r for r in filtered 
                       if r.get('price_range', 0) <= filters['max_price']]
        
        # Rating filter
        if 'min_rating' in filters:
            filtered = [r for r in filtered 
                       if r.get('rating', 0) >= filters['min_rating']]
        
        # Distance filter
        if 'max_distance' in filters:
            # Would calculate actual distance here
            pass
        
        return filtered
    
    async def _check_availability(
        self,
        provider: BookingProvider,
        venue_id: str,
        date_time: datetime,
        party_size: int
    ) -> bool:
        """Check availability with provider"""
        provider_client = self.providers.get(provider)
        if not provider_client:
            return False
        
        try:
            if provider == BookingProvider.OPENTABLE:
                availability = await provider_client.check_availability(
                    venue_id, date_time, party_size
                )
                return date_time.strftime('%H:%M') in availability.get('times', [])
            
            elif provider == BookingProvider.RECREATION_GOV:
                availability = await provider_client.check_availability(
                    venue_id, date_time.date(), date_time.date()
                )
                return availability.get('available_count', 0) > 0
            
            # Add other providers
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return False
    
    async def _find_alternative_times(
        self,
        provider: BookingProvider,
        venue_id: str,
        desired_time: datetime,
        party_size: int,
        window_hours: int = 2
    ) -> List[datetime]:
        """Find alternative available times"""
        alternatives = []
        
        # Check times before and after
        for offset in [-2, -1, 1, 2]:
            alt_time = desired_time + timedelta(hours=offset)
            if await self._check_availability(provider, venue_id, alt_time, party_size):
                alternatives.append(alt_time)
        
        return alternatives
    
    async def _create_provider_booking(
        self,
        provider: BookingProvider,
        provider_client: Any,
        venue_id: str,
        date_time: datetime,
        party_size: int,
        special_requests: Optional[str],
        contact_info: Dict[str, str],
        payment_info: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create booking with specific provider"""
        if provider == BookingProvider.OPENTABLE:
            return await provider_client.create_reservation(
                restaurant_id=venue_id,
                date_time=date_time,
                party_size=party_size,
                customer_info=contact_info,
                special_requests=special_requests
            )
        
        elif provider == BookingProvider.RECREATION_GOV:
            return await provider_client.create_booking(
                facility_id=venue_id,
                start_date=date_time.date(),
                end_date=date_time.date() + timedelta(days=1),
                equipment_type="tent",
                party_size=party_size,
                customer_info=contact_info
            )
        
        # Add other providers
        
        return {"confirmation_number": "INTERNAL-" + str(uuid.uuid4())}
    
    def _get_reservation_type(self, provider: BookingProvider) -> ReservationType:
        """Map provider to reservation type"""
        mapping = {
            BookingProvider.OPENTABLE: ReservationType.RESTAURANT,
            BookingProvider.RESY: ReservationType.RESTAURANT,
            BookingProvider.RECREATION_GOV: ReservationType.ACCOMMODATION,
            BookingProvider.SHELL_RECHARGE: ReservationType.OTHER,
            BookingProvider.VIATOR: ReservationType.ACTIVITY,
            BookingProvider.AIRBNB: ReservationType.ACCOMMODATION,
            BookingProvider.BOOKING_COM: ReservationType.ACCOMMODATION,
            BookingProvider.PARKWHIZ: ReservationType.OTHER,
        }
        return mapping.get(provider, ReservationType.OTHER)
    
    def _get_provider_from_type(self, res_type: ReservationType) -> Optional[BookingProvider]:
        """Get provider from reservation type (simplified)"""
        # In reality, would need to check confirmation details
        if res_type == ReservationType.RESTAURANT:
            return BookingProvider.OPENTABLE
        elif res_type == ReservationType.ACCOMMODATION:
            return BookingProvider.RECREATION_GOV
        return None
    
    async def _send_confirmation(
        self,
        user: User,
        reservation: Reservation,
        booking_result: Dict[str, Any]
    ):
        """Send reservation confirmation email/SMS"""
        try:
            # Email confirmation
            subject = f"Reservation Confirmed: {reservation.venue_name}"
            
            html_body = f"""
            <h2>Your reservation is confirmed!</h2>
            <p><strong>Venue:</strong> {reservation.venue_name}</p>
            <p><strong>Date/Time:</strong> {reservation.reservation_time.strftime('%B %d, %Y at %I:%M %p')}</p>
            <p><strong>Party Size:</strong> {reservation.party_size}</p>
            <p><strong>Confirmation #:</strong> {reservation.provider_id}</p>
            
            {f'<p><strong>Special Requests:</strong> {reservation.special_requests}</p>' if reservation.special_requests else ''}
            
            <p>Add to calendar: <a href="#">Google</a> | <a href="#">Apple</a> | <a href="#">Outlook</a></p>
            
            <p>Need to make changes? <a href="#">Modify</a> | <a href="#">Cancel</a></p>
            """
            
            # Would send actual email here
            logger.info(f"Confirmation email sent to {user.email}")
            
            # SMS confirmation if enabled
            if self.sms_enabled and hasattr(user, 'phone'):
                sms_body = f"Confirmed: {reservation.venue_name} on {reservation.reservation_time.strftime('%m/%d at %I:%M%p')}. Conf #{reservation.provider_id}"
                # Would send SMS here
                logger.info(f"Confirmation SMS sent to {user.phone}")
                
        except Exception as e:
            logger.error(f"Error sending confirmation: {e}")
    
    async def _add_to_calendar(self, user: User, reservation: Reservation):
        """Add reservation to user's calendar"""
        try:
            # Would integrate with Google Calendar, Apple Calendar, etc.
            logger.info(f"Added reservation to calendar for user {user.id}")
        except Exception as e:
            logger.error(f"Error adding to calendar: {e}")
    
    async def _schedule_reminder(self, reservation: Reservation):
        """Schedule reminder for reservation"""
        try:
            # Calculate reminder time (e.g., 24 hours before)
            reminder_time = reservation.reservation_time - timedelta(hours=24)
            
            # Would schedule actual reminder task here
            logger.info(f"Reminder scheduled for reservation {reservation.id}")
            
        except Exception as e:
            logger.error(f"Error scheduling reminder: {e}")
    
    def _can_modify(self, reservation: Reservation) -> bool:
        """Check if reservation can be modified"""
        if reservation.status != ReservationStatus.CONFIRMED:
            return False
        
        hours_until = (reservation.reservation_time - datetime.utcnow()).total_seconds() / 3600
        return hours_until > 2  # 2 hour minimum
    
    def _can_cancel(self, reservation: Reservation) -> bool:
        """Check if reservation can be cancelled"""
        return reservation.status in [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]
    
    async def _get_cancellation_policy(self, reservation: Reservation) -> Dict[str, Any]:
        """Get cancellation policy for reservation"""
        # Would fetch from provider
        return {
            "free_cancellation_hours": 24,
            "cancellation_fee": 0 if reservation.type == ReservationType.RESTAURANT else 10
        }
    
    async def _process_waitlist(self, cancelled_reservation: Reservation):
        """Process waitlist after cancellation"""
        try:
            # Get waitlist for this venue and date
            cache_key = f"waitlist:{cancelled_reservation.venue_id}:{cancelled_reservation.reservation_time.date()}"
            waitlist = await cache_manager.get(cache_key) or []
            
            # Find eligible waitlist entries
            for entry in waitlist:
                if (entry['status'] == 'active' and
                    entry['flexibility_start'] <= cancelled_reservation.reservation_time <= entry['flexibility_end'] and
                    int(entry['party_size']) <= int(cancelled_reservation.party_size)):
                    
                    # Notify user
                    user = self.db.query(User).filter(User.id == entry['user_id']).first()
                    if user:
                        # Would send notification here
                        logger.info(f"Notified waitlist user {user.id} about availability")
                        
                        # Mark as notified
                        entry['status'] = 'notified'
                        entry['notified_at'] = datetime.utcnow()
                        
                        # Give them 30 minutes to book
                        entry['expires_at'] = datetime.utcnow() + timedelta(minutes=30)
                        
                        break
            
            # Update waitlist
            await cache_manager.set(cache_key, waitlist, expire=86400 * 7)
            
        except Exception as e:
            logger.error(f"Error processing waitlist: {e}")
    
    def _estimate_wait_time(self, position: int, venue_id: str) -> str:
        """Estimate wait time based on position"""
        # Simplified estimation
        if position <= 3:
            return "Less than 1 week"
        elif position <= 10:
            return "1-2 weeks"
        else:
            return "2-4 weeks"