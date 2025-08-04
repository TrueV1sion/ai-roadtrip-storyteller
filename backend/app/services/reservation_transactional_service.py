"""
Enhanced Reservation Management Service with Proper Transaction Handling
"""

from datetime import datetime
from typing import Dict, Any, Optional
import uuid
import json

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.logger import logger
from app.core.transaction_manager import transactional, TransactionValidator
from app.models.user import User
from app.services.reservation_agent import (
    Reservation, ReservationStatus, ReservationType
)
from app.services.reservation_management_service import (
    ReservationManagementService, BookingProvider
)


class ReservationTransactionalService(ReservationManagementService):
    """
    Extended reservation service with proper transaction management.
    
    This service ensures that all reservation operations are atomic,
    preventing partial data from being saved when operations fail.
    """
    
    @transactional()
    def create_reservation_sync(
        self,
        user_id: str,
        provider: BookingProvider,
        venue_id: str,
        date_time: datetime,
        party_size: int,
        special_requests: Optional[str] = None,
        contact_info: Optional[Dict[str, str]] = None,
        booking_result: Optional[Dict[str, Any]] = None
    ) -> Reservation:
        """
        Synchronous version of create_reservation with transaction support.
        
        This method should be called after the async provider booking
        has been completed successfully.
        """
        # Validate user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        
        # Create internal reservation record
        reservation = Reservation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            type=self._get_reservation_type(provider),
            provider_id=booking_result.get('confirmation_number') if booking_result else None,
            venue_name=booking_result.get('venue_name') if booking_result else venue_id,
            venue_id=venue_id,
            venue_address=booking_result.get('venue_address') if booking_result else '',
            reservation_time=date_time,
            party_size=str(party_size),
            special_requests=special_requests,
            status=ReservationStatus.CONFIRMED,
            confirmation_details=json.dumps(booking_result) if booking_result else '{}',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Validate foreign keys
        validator = TransactionValidator()
        if not validator.validate_foreign_keys(self.db, reservation):
            raise ValueError("Foreign key validation failed for reservation")
        
        self.db.add(reservation)
        self.db.flush()  # Get ID without committing
        
        logger.info(
            f"Created reservation {reservation.id} for user {user_id} "
            f"at {venue_id} for {date_time}"
        )
        
        return reservation
    
    @transactional()
    def modify_reservation_sync(
        self,
        reservation_id: str,
        user_id: str,
        modifications: Dict[str, Any],
        modification_result: Optional[Dict[str, Any]] = None
    ) -> Reservation:
        """
        Synchronous version of modify_reservation with transaction support.
        """
        # Get reservation with lock for update
        reservation = self.db.query(Reservation).filter(
            and_(
                Reservation.id == reservation_id,
                Reservation.user_id == user_id
            )
        ).with_for_update().first()
        
        if not reservation:
            raise ValueError("Reservation not found")
        
        # Check if modification is allowed
        if reservation.status != ReservationStatus.CONFIRMED:
            raise ValueError(f"Cannot modify reservation in {reservation.status} status")
        
        # Check modification window
        current_time = datetime.utcnow()
        reservation_time = reservation.reservation_time
        
        # Convert to UTC if needed
        if hasattr(reservation_time, 'tzinfo') and reservation_time.tzinfo:
            reservation_time = reservation_time.replace(tzinfo=None)
        
        hours_until_reservation = (
            reservation_time - current_time
        ).total_seconds() / 3600
        
        if hours_until_reservation < 2:  # 2 hour minimum
            raise ValueError("Too close to reservation time to modify")
        
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
        if modification_result:
            conf_details.update(modification_result)
        conf_details['last_modified'] = datetime.utcnow().isoformat()
        reservation.confirmation_details = json.dumps(conf_details)
        
        self.db.flush()
        
        logger.info(f"Modified reservation {reservation_id} for user {user_id}")
        
        return reservation
    
    @transactional()
    def cancel_reservation_sync(
        self,
        reservation_id: str,
        user_id: str,
        reason: Optional[str] = None,
        cancellation_fee: float = 0,
        cancellation_result: Optional[Dict[str, Any]] = None
    ) -> Reservation:
        """
        Synchronous version of cancel_reservation with transaction support.
        """
        # Get reservation with lock for update
        reservation = self.db.query(Reservation).filter(
            and_(
                Reservation.id == reservation_id,
                Reservation.user_id == user_id
            )
        ).with_for_update().first()
        
        if not reservation:
            raise ValueError("Reservation not found")
        
        # Check if cancellation is allowed
        if reservation.status in [ReservationStatus.CANCELLED, ReservationStatus.COMPLETED]:
            raise ValueError(f"Reservation already {reservation.status}")
        
        # Update reservation status
        reservation.status = ReservationStatus.CANCELLED
        reservation.updated_at = datetime.utcnow()
        
        # Store cancellation details
        conf_details = json.loads(reservation.confirmation_details or '{}')
        conf_details['cancellation'] = {
            "timestamp": datetime.utcnow().isoformat(),
            "reason": reason,
            "fee": cancellation_fee,
            "result": cancellation_result or {"status": "cancelled_internally"}
        }
        reservation.confirmation_details = json.dumps(conf_details)
        
        self.db.flush()
        
        logger.info(
            f"Cancelled reservation {reservation_id} for user {user_id} "
            f"with fee {cancellation_fee}"
        )
        
        return reservation
    
    @transactional()
    def bulk_update_reservation_status(
        self,
        reservation_ids: list[str],
        new_status: ReservationStatus,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update multiple reservation statuses in a single transaction.
        """
        updated = []
        failed = []
        
        for reservation_id in reservation_ids:
            try:
                reservation = self.db.query(Reservation).filter(
                    Reservation.id == reservation_id
                ).with_for_update().first()
                
                if not reservation:
                    failed.append({
                        "id": reservation_id,
                        "error": "Not found"
                    })
                    continue
                
                # Update status
                reservation.status = new_status
                reservation.updated_at = datetime.utcnow()
                
                # Add reason if provided
                if reason:
                    conf_details = json.loads(reservation.confirmation_details or '{}')
                    conf_details['bulk_update'] = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "new_status": new_status.value,
                        "reason": reason
                    }
                    reservation.confirmation_details = json.dumps(conf_details)
                
                updated.append(reservation_id)
                
            except Exception as e:
                failed.append({
                    "id": reservation_id,
                    "error": str(e)
                })
        
        # If all failed, raise exception to rollback
        if len(failed) == len(reservation_ids):
            raise ValueError("All reservation updates failed")
        
        self.db.flush()
        
        logger.info(
            f"Bulk updated {len(updated)} reservations to {new_status}, "
            f"{len(failed)} failed"
        )
        
        return {
            "updated": updated,
            "failed": failed,
            "total": len(reservation_ids)
        }
    
    def create_reservation_with_rollback(
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
        Create reservation with automatic rollback on provider failure.
        
        This method handles the complex case where we need to:
        1. Check availability
        2. Create provider booking (async)
        3. Create database record (sync with transaction)
        4. Handle rollback if any step fails
        """
        import asyncio
        
        # Start a transaction
        with transaction_manager.transaction(self.db):
            # First, validate user exists
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("User not found")
            
            # Run async provider booking
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Check availability
            provider_client = self.providers.get(provider)
            if not provider_client:
                raise ValueError(f"Provider {provider} not supported")
            
            is_available = loop.run_until_complete(
                self._check_availability(provider, venue_id, date_time, party_size)
            )
            
            if not is_available:
                raise ValueError("Requested time not available")
            
            # Make provider booking
            booking_result = loop.run_until_complete(
                self._create_provider_booking(
                    provider,
                    provider_client,
                    venue_id,
                    date_time,
                    party_size,
                    special_requests,
                    contact_info or {"name": user.name, "email": user.email},
                    payment_info
                )
            )
            
            # Create database record (within transaction)
            reservation = self.create_reservation_sync(
                user_id=user_id,
                provider=provider,
                venue_id=venue_id,
                date_time=date_time,
                party_size=party_size,
                special_requests=special_requests,
                contact_info=contact_info,
                booking_result=booking_result
            )
            
            # Transaction commits here if all successful
            return {
                "status": "confirmed",
                "reservation_id": reservation.id,
                "confirmation_number": booking_result.get('confirmation_number'),
                "details": booking_result
            }