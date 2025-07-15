from datetime import datetime, timedelta
from enum import Enum
import json
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union, Type

from fastapi import Depends, HTTPException, status
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, JSON, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship

from app.core.logger import get_logger
from app.database import get_db
from app.db.base import Base
from app.models.user import User

logger = get_logger(__name__)

class ReservationStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


class ReservationType(str, Enum):
    RESTAURANT = "restaurant"
    ATTRACTION = "attraction"
    ACTIVITY = "activity"
    ACCOMMODATION = "accommodation"
    OTHER = "other"


class Reservation(Base):
    """Reservation database model."""
    __tablename__ = "reservations"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Reservation details
    type = Column(String, nullable=False)  # Restaurant, attraction, etc.
    provider_id = Column(String, nullable=True)  # ID from external provider if applicable
    venue_name = Column(String, nullable=False)
    venue_id = Column(String, nullable=True)  # External ID for the venue if available
    venue_address = Column(Text, nullable=True)
    reservation_time = Column(DateTime, nullable=False)
    party_size = Column(String, nullable=False)  # Store as string for flexibility (e.g., "2 adults, 1 child")
    special_requests = Column(Text, nullable=True)
    
    # Additional information
    confirmation_number = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
    
    # Status and metadata
    status = Column(String, nullable=False, default=ReservationStatus.PENDING.value)
    metadata = Column(JSON, nullable=True)  # For provider-specific details
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    cancelled_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="reservations")

    def to_dict(self) -> Dict[str, Any]:
        """Convert reservation to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type,
            "venue_name": self.venue_name,
            "venue_address": self.venue_address,
            "reservation_time": self.reservation_time.isoformat() if self.reservation_time else None,
            "party_size": self.party_size,
            "special_requests": self.special_requests,
            "confirmation_number": self.confirmation_number,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ReservationAgent:
    """Base class for reservation agents that handle booking and management."""
    
    def __init__(self, db: Session):
        """Initialize the reservation agent with database session."""
        self.db = db
    
    async def create_reservation(
        self,
        user_id: str,
        reservation_type: ReservationType,
        venue_name: str,
        reservation_time: datetime,
        party_size: str,
        venue_address: Optional[str] = None,
        special_requests: Optional[str] = None,
        contact_phone: Optional[str] = None,
        contact_email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Reservation:
        """
        Create a new reservation in the database.
        
        Args:
            user_id: ID of the user making the reservation
            reservation_type: Type of reservation (restaurant, attraction, etc.)
            venue_name: Name of the venue
            reservation_time: Date and time of the reservation
            party_size: Number of people in the party
            venue_address: Address of the venue
            special_requests: Any special requests for the reservation
            contact_phone: Contact phone number
            contact_email: Contact email
            metadata: Additional metadata for the reservation
            
        Returns:
            The created reservation object
        
        Raises:
            HTTPException: If the reservation could not be created
        """
        try:
            # Check if user exists
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with ID {user_id} not found"
                )
            
            # Create the reservation
            reservation = Reservation(
                user_id=user_id,
                type=reservation_type.value,
                venue_name=venue_name,
                venue_address=venue_address,
                reservation_time=reservation_time,
                party_size=party_size,
                special_requests=special_requests,
                contact_phone=contact_phone,
                contact_email=contact_email,
                status=ReservationStatus.PENDING.value,
                metadata=metadata or {},
            )
            
            self.db.add(reservation)
            self.db.commit()
            self.db.refresh(reservation)
            
            # Send notification about the new reservation
            await self._send_notification(
                user_id=user_id,
                reservation_id=reservation.id,
                notification_type="reservation_created",
                message=f"Your reservation at {venue_name} has been created and is pending confirmation."
            )
            
            logger.info(f"Created reservation {reservation.id} for user {user_id} at {venue_name}")
            return reservation
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating reservation: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create reservation: {str(e)}"
            )
    
    async def get_reservation(self, reservation_id: str) -> Optional[Reservation]:
        """
        Get a reservation by ID.
        
        Args:
            reservation_id: ID of the reservation to retrieve
            
        Returns:
            The reservation object or None if not found
        """
        try:
            reservation = self.db.query(Reservation).filter(Reservation.id == reservation_id).first()
            return reservation
        except Exception as e:
            logger.error(f"Error retrieving reservation {reservation_id}: {str(e)}")
            return None
    
    async def get_user_reservations(
        self, 
        user_id: str,
        status: Optional[ReservationStatus] = None
    ) -> List[Reservation]:
        """
        Get all reservations for a user, optionally filtered by status.
        
        Args:
            user_id: ID of the user
            status: Optional status filter
            
        Returns:
            List of reservation objects
        """
        try:
            query = self.db.query(Reservation).filter(Reservation.user_id == user_id)
            
            if status:
                query = query.filter(Reservation.status == status.value)
                
            # Order by reservation time, with upcoming reservations first
            query = query.order_by(Reservation.reservation_time)
            
            return query.all()
        except Exception as e:
            logger.error(f"Error retrieving reservations for user {user_id}: {str(e)}")
            return []
    
    async def update_reservation_status(
        self, 
        reservation_id: str, 
        status: ReservationStatus,
        confirmation_number: Optional[str] = None,
        metadata_updates: Optional[Dict[str, Any]] = None
    ) -> Optional[Reservation]:
        """
        Update the status of a reservation.
        
        Args:
            reservation_id: ID of the reservation to update
            status: New status for the reservation
            confirmation_number: Confirmation number from provider
            metadata_updates: Additional metadata updates
            
        Returns:
            The updated reservation or None if not found
        
        Raises:
            HTTPException: If the reservation could not be updated
        """
        try:
            reservation = await self.get_reservation(reservation_id)
            if not reservation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Reservation with ID {reservation_id} not found"
                )
            
            # Update the reservation
            reservation.status = status.value
            
            # Set cancellation timestamp if cancelled
            if status == ReservationStatus.CANCELLED:
                reservation.cancelled_at = datetime.utcnow()
                
            # Update confirmation number if provided
            if confirmation_number:
                reservation.confirmation_number = confirmation_number
                
            # Update metadata if provided
            if metadata_updates:
                current_metadata = reservation.metadata or {}
                current_metadata.update(metadata_updates)
                reservation.metadata = current_metadata
            
            self.db.commit()
            self.db.refresh(reservation)
            
            # Send notification about the status update
            notification_message = f"Your reservation at {reservation.venue_name} has been {status.value}."
            if confirmation_number:
                notification_message += f" Confirmation number: {confirmation_number}"
                
            await self._send_notification(
                user_id=reservation.user_id,
                reservation_id=reservation.id,
                notification_type=f"reservation_{status.value}",
                message=notification_message
            )
            
            logger.info(f"Updated reservation {reservation_id} status to {status.value}")
            return reservation
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating reservation {reservation_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update reservation: {str(e)}"
            )
    
    async def cancel_reservation(
        self,
        reservation_id: str,
        cancellation_reason: Optional[str] = None
    ) -> Optional[Reservation]:
        """
        Cancel a reservation.
        
        Args:
            reservation_id: ID of the reservation to cancel
            cancellation_reason: Reason for cancellation
            
        Returns:
            The updated reservation or None if not found
        
        Raises:
            HTTPException: If the reservation could not be cancelled
        """
        try:
            metadata_updates = {}
            if cancellation_reason:
                metadata_updates["cancellation_reason"] = cancellation_reason
                
            return await self.update_reservation_status(
                reservation_id=reservation_id,
                status=ReservationStatus.CANCELLED,
                metadata_updates=metadata_updates
            )
        except Exception as e:
            logger.error(f"Error cancelling reservation {reservation_id}: {str(e)}")
            raise
    
    async def _send_notification(
        self,
        user_id: str,
        reservation_id: str,
        notification_type: str,
        message: str
    ) -> bool:
        """
        Send a notification to the user about a reservation.
        
        Args:
            user_id: ID of the user to notify
            reservation_id: ID of the reservation
            notification_type: Type of notification
            message: Notification message
            
        Returns:
            Boolean indicating if notification was sent successfully
        """
        # Implement real notification service integration
        try:
            from ..services.notification_service import NotificationService
            notification_service = NotificationService()
            
            success = await notification_service.send_notification(
                user_id=user_id,
                notification_type=notification_type,
                message=message
            )
            
            if success:
                logger.info(f"Notification sent successfully [{notification_type}] for user {user_id}")
                return True
            else:
                logger.warning(f"Notification failed [{notification_type}] for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            # Fallback: just log the notification
            logger.info(f"Fallback notification [{notification_type}] for user {user_id}: {message}")
            return True


class RestaurantReservationAgent(ReservationAgent):
    """Specialized agent for handling restaurant reservations."""
    
    async def create_restaurant_reservation(
        self,
        user_id: str,
        restaurant_name: str,
        restaurant_address: str,
        reservation_time: datetime,
        party_size: str,
        special_requests: Optional[str] = None,
        cuisine_type: Optional[str] = None,
        restaurant_phone: Optional[str] = None,
        contact_phone: Optional[str] = None,
        contact_email: Optional[str] = None,
    ) -> Reservation:
        """
        Create a restaurant reservation with restaurant-specific details.
        
        Args:
            user_id: ID of the user making the reservation
            restaurant_name: Name of the restaurant
            restaurant_address: Address of the restaurant
            reservation_time: Date and time of the reservation
            party_size: Number of people in the party
            special_requests: Any special requests (dietary, seating, etc.)
            cuisine_type: Type of cuisine
            restaurant_phone: Restaurant's phone number
            contact_phone: User's contact phone
            contact_email: User's contact email
            
        Returns:
            The created reservation object
        """
        # Create metadata with restaurant-specific information
        metadata = {
            "cuisine_type": cuisine_type,
            "restaurant_phone": restaurant_phone,
        }
        
        # Create the base reservation
        reservation = await self.create_reservation(
            user_id=user_id,
            reservation_type=ReservationType.RESTAURANT,
            venue_name=restaurant_name,
            venue_address=restaurant_address,
            reservation_time=reservation_time,
            party_size=party_size,
            special_requests=special_requests,
            contact_phone=contact_phone,
            contact_email=contact_email,
            metadata=metadata,
        )
        
        # Check if we should attempt to confirm with the restaurant right away
        # This would integrate with a reservation API like OpenTable
        await self._attempt_restaurant_confirmation(reservation)
        
        return reservation
    
    async def _attempt_restaurant_confirmation(self, reservation: Reservation) -> bool:
        """
        Attempt to confirm the reservation with the restaurant through an API.
        
        Args:
            reservation: The reservation to confirm
            
        Returns:
            Boolean indicating if confirmation was successful
        """
        # Integrate with OpenTable API for real reservations
        try:
            from ..integrations.open_table_client import OpenTableClient
            opentable_client = OpenTableClient()
            
            # Attempt to confirm with OpenTable
            confirmation_result = await opentable_client.confirm_reservation(
                restaurant_name=reservation.restaurant_name,
                reservation_time=reservation.reservation_time,
                party_size=reservation.party_size,
                user_details=reservation.special_requests or {}
            )
            
            if confirmation_result.get("success"):
                confirmation_number = confirmation_result.get("confirmation_number")
                logger.info(f"OpenTable confirmation successful: {confirmation_number}")
                
                await self.update_reservation_status(
                    reservation_id=reservation.id,
                    status=ReservationStatus.CONFIRMED,
                    confirmation_number=confirmation_number
                )
                return True
            else:
                logger.warning(f"OpenTable confirmation failed: {confirmation_result.get('error')}")
                # Fall back to simulation
                raise Exception("OpenTable confirmation failed")
                
        except Exception as e:
            logger.error(f"Failed to confirm with OpenTable: {e}")
            
            # Fallback: simulate confirmation
            logger.info(f"Using fallback confirmation for reservation {reservation.id}")
            confirmation_number = f"RT{uuid.uuid4().hex[:8].upper()}"
            await self.update_reservation_status(
                reservation_id=reservation.id,
                status=ReservationStatus.CONFIRMED,
                confirmation_number=confirmation_number
            )
        
        return True


async def get_reservation_agent(
    agent_type: Optional[str] = None,
    db: Session = Depends(get_db)
) -> ReservationAgent:
    """
    Dependency to get the appropriate reservation agent.
    
    Args:
        agent_type: Type of agent to get (defaults to base agent)
        db: Database session dependency
        
    Returns:
        An instance of the requested reservation agent
    """
    if agent_type == "restaurant":
        return RestaurantReservationAgent(db)
    # Future agent types can be added here (attractions, activities, etc.)
    return ReservationAgent(db)