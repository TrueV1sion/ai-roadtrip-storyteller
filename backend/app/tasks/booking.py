"""
Asynchronous booking tasks for processing reservations and confirmations.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from celery import Task
from celery.exceptions import Retry

from backend.app.core.celery_app import celery_app
from backend.app.core.database_manager import DatabaseManager
from backend.app.services.booking_service import BookingService
from backend.app.services.commission_calculator import CommissionCalculator
from backend.app.core.logger import get_logger
from backend.app.tasks.notifications import send_booking_confirmation_email
from backend.app.core.resilience import with_circuit_breaker
from backend.app.models.booking import Booking, BookingStatus

logger = get_logger(__name__)

class BookingTask(Task):
    """Base task class with database connection management."""
    
    _db_manager = None
    _booking_service = None
    _commission_calculator = None
    
    @property
    def db_manager(self):
        if self._db_manager is None:
            self._db_manager = DatabaseManager()
        return self._db_manager
    
    @property
    def booking_service(self):
        if self._booking_service is None:
            self._booking_service = BookingService()
        return self._booking_service
    
    @property
    def commission_calculator(self):
        if self._commission_calculator is None:
            self._commission_calculator = CommissionCalculator()
        return self._commission_calculator


@celery_app.task(
    bind=True,
    base=BookingTask,
    name='booking.process_reservation',
    max_retries=5,
    default_retry_delay=30
)
def process_reservation(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a reservation asynchronously.
    
    This task:
    1. Creates the booking with the partner API
    2. Calculates commission
    3. Updates the database
    4. Sends confirmation email
    5. Triggers analytics update
    """
    try:
        logger.info(f"Processing reservation: {booking_data.get('id')}")
        
        # Extract booking details
        user_id = booking_data['user_id']
        partner = booking_data['partner']
        venue_id = booking_data['venue_id']
        booking_date = datetime.fromisoformat(booking_data['booking_date'])
        party_size = booking_data.get('party_size', 2)
        
        # Create booking with partner API
        with with_circuit_breaker(f"{partner}_booking"):
            result = self.booking_service.create_booking(
                partner=partner,
                venue_id=venue_id,
                date=booking_date,
                party_size=party_size,
                user_data=booking_data.get('user_data', {})
            )
        
        if not result['success']:
            raise Exception(f"Booking failed: {result.get('error')}")
        
        # Calculate commission
        commission_data = self.commission_calculator.calculate_commission(
            partner=partner,
            booking_amount=result['total_amount'],
            booking_type=booking_data.get('type', 'restaurant')
        )
        
        # Create database record
        with self.db_manager.get_session() as session:
            booking = Booking(
                user_id=user_id,
                partner=partner,
                venue_id=venue_id,
                confirmation_number=result['confirmation_number'],
                booking_date=booking_date,
                party_size=party_size,
                total_amount=result['total_amount'],
                commission_amount=commission_data['commission_amount'],
                commission_rate=commission_data['commission_rate'],
                status=BookingStatus.CONFIRMED,
                partner_response=result
            )
            session.add(booking)
            session.commit()
            
            booking_id = booking.id
        
        # Send confirmation email asynchronously
        send_booking_confirmation_email.apply_async(
            args=[{
                'booking_id': booking_id,
                'user_id': user_id,
                'confirmation_number': result['confirmation_number'],
                'venue_name': result.get('venue_name'),
                'booking_date': booking_date.isoformat(),
                'party_size': party_size
            }],
            countdown=2  # Wait 2 seconds
        )
        
        # Trigger analytics update
        update_booking_analytics.apply_async(
            args=[booking_id, commission_data],
            countdown=5
        )
        
        logger.info(f"Successfully processed booking {booking_id}")
        
        return {
            'success': True,
            'booking_id': booking_id,
            'confirmation_number': result['confirmation_number'],
            'commission': commission_data
        }
        
    except Exception as e:
        logger.error(f"Error processing reservation: {str(e)}")
        
        # Retry with exponential backoff
        countdown = 30 * (2 ** self.request.retries)
        raise self.retry(exc=e, countdown=countdown)


@celery_app.task(
    bind=True,
    base=BookingTask,
    name='booking.check_pending_confirmations',
    max_retries=3
)
def check_pending_confirmations(self) -> Dict[str, Any]:
    """
    Periodic task to check for pending booking confirmations.
    """
    try:
        with self.db_manager.get_session() as session:
            # Find bookings pending confirmation for more than 5 minutes
            cutoff_time = datetime.utcnow() - timedelta(minutes=5)
            pending_bookings = session.query(Booking).filter(
                Booking.status == BookingStatus.PENDING,
                Booking.created_at < cutoff_time
            ).all()
            
            processed = 0
            failed = 0
            
            for booking in pending_bookings:
                try:
                    # Check status with partner
                    status = self.booking_service.check_booking_status(
                        partner=booking.partner,
                        confirmation_number=booking.confirmation_number
                    )
                    
                    if status['confirmed']:
                        booking.status = BookingStatus.CONFIRMED
                        processed += 1
                    elif status.get('cancelled'):
                        booking.status = BookingStatus.CANCELLED
                        failed += 1
                        
                        # Trigger refund process if needed
                        if booking.commission_amount > 0:
                            process_booking_cancellation.apply_async(
                                args=[booking.id]
                            )
                    
                    session.commit()
                    
                except Exception as e:
                    logger.error(f"Error checking booking {booking.id}: {str(e)}")
                    failed += 1
            
            logger.info(f"Checked {len(pending_bookings)} pending bookings: "
                       f"{processed} confirmed, {failed} failed")
            
            return {
                'total': len(pending_bookings),
                'confirmed': processed,
                'failed': failed
            }
            
    except Exception as e:
        logger.error(f"Error in check_pending_confirmations: {str(e)}")
        raise self.retry(exc=e, countdown=300)  # Retry in 5 minutes


@celery_app.task(
    bind=True,
    base=BookingTask,
    name='booking.process_cancellation',
    max_retries=3
)
def process_booking_cancellation(self, booking_id: int) -> Dict[str, Any]:
    """
    Process booking cancellation and commission reversal.
    """
    try:
        with self.db_manager.get_session() as session:
            booking = session.query(Booking).filter_by(id=booking_id).first()
            
            if not booking:
                logger.error(f"Booking {booking_id} not found")
                return {'success': False, 'error': 'Booking not found'}
            
            # Cancel with partner
            result = self.booking_service.cancel_booking(
                partner=booking.partner,
                confirmation_number=booking.confirmation_number
            )
            
            if result['success']:
                booking.status = BookingStatus.CANCELLED
                booking.cancelled_at = datetime.utcnow()
                
                # Reverse commission
                if booking.commission_amount > 0:
                    reversal_amount = self.commission_calculator.calculate_reversal(
                        original_commission=booking.commission_amount,
                        booking_date=booking.booking_date,
                        cancellation_date=datetime.utcnow()
                    )
                    
                    booking.commission_reversed = reversal_amount
                    
                    # Update analytics
                    update_commission_reversal.apply_async(
                        args=[booking_id, reversal_amount]
                    )
                
                session.commit()
                
                # Send cancellation notification
                send_booking_cancellation_email.apply_async(
                    args=[{
                        'booking_id': booking_id,
                        'user_id': booking.user_id,
                        'venue_name': booking.venue_name
                    }]
                )
                
                return {
                    'success': True,
                    'booking_id': booking_id,
                    'commission_reversed': reversal_amount if booking.commission_amount > 0 else 0
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Cancellation failed')
                }
                
    except Exception as e:
        logger.error(f"Error processing cancellation: {str(e)}")
        raise self.retry(exc=e, countdown=60)


@celery_app.task(
    base=BookingTask,
    name='booking.update_analytics'
)
def update_booking_analytics(booking_id: int, commission_data: Dict[str, Any]):
    """Update booking analytics and revenue tracking."""
    try:
        logger.info(f"Updating analytics for booking {booking_id}")
        
        # This would integrate with your analytics system
        # For now, we'll just log the commission data
        logger.info(f"Commission data: {commission_data}")
        
        # In a real implementation, this would:
        # 1. Update revenue dashboards
        # 2. Track conversion metrics
        # 3. Update partner performance metrics
        # 4. Generate reports
        
    except Exception as e:
        logger.error(f"Error updating analytics: {str(e)}")


@celery_app.task(
    base=BookingTask,
    name='booking.update_commission_reversal'
)
def update_commission_reversal(booking_id: int, reversal_amount: float):
    """Update commission reversal in analytics."""
    try:
        logger.info(f"Processing commission reversal for booking {booking_id}: ${reversal_amount}")
        
        # Update analytics with reversal
        # This would integrate with your revenue tracking system
        
    except Exception as e:
        logger.error(f"Error updating commission reversal: {str(e)}")