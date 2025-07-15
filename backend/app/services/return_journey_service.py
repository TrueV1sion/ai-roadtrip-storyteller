"""Service for automating return journey scheduling and reminders."""

from datetime import datetime, timedelta
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from backend.app.models.parking_reservation import ParkingReservation
from backend.app.models.user import User
from backend.app.services.directions_service import DirectionsService
from backend.app.services.master_orchestration_agent import MasterOrchestrationAgent
from backend.app.core.logger import logger
from backend.app.core.cache import cache_manager


class ReturnJourneyService:
    """Service for managing automated return journey scheduling."""
    
    def __init__(self, db: Session):
        """Initialize the return journey service."""
        self.db = db
        self.directions_service = DirectionsService()
        self.orchestration_agent = MasterOrchestrationAgent()
    
    def schedule_return_journey(
        self,
        parking_reservation_id: str,
        user_id: str,
        buffer_minutes: int = 30
    ) -> Dict:
        """
        Schedule an automated return journey based on parking reservation.
        
        Args:
            parking_reservation_id: The parking reservation ID
            user_id: The user ID
            buffer_minutes: Extra time to add for buffer (default: 30 minutes)
            
        Returns:
            Dictionary with scheduling details
        """
        try:
            # Get parking reservation
            reservation = self.db.query(ParkingReservation).filter(
                and_(
                    ParkingReservation.id == parking_reservation_id,
                    ParkingReservation.user_id == user_id
                )
            ).first()
            
            if not reservation:
                raise ValueError("Parking reservation not found")
            
            # Calculate estimated travel time
            directions = self.directions_service.get_directions(
                origin=reservation.location_name,
                destination=reservation.metadata.get("origin_address", "Home")
            )
            
            if not directions or not directions.get("routes"):
                raise ValueError("Could not calculate return route")
            
            # Get travel duration
            duration_seconds = directions["routes"][0]["legs"][0]["duration"]["value"]
            travel_time_minutes = duration_seconds // 60
            
            # Calculate pickup time with buffer
            estimated_pickup_time = reservation.check_out_time - timedelta(
                minutes=travel_time_minutes + buffer_minutes
            )
            
            # Update reservation with scheduling info
            reservation.estimated_pickup_time = estimated_pickup_time
            reservation.return_journey_scheduled = True
            self.db.commit()
            
            # Schedule reminder notification
            self._schedule_reminder_notification(reservation, estimated_pickup_time)
            
            return {
                "scheduled": True,
                "estimated_pickup_time": estimated_pickup_time.isoformat(),
                "travel_time_minutes": travel_time_minutes,
                "buffer_minutes": buffer_minutes,
                "parking_location": reservation.location_name,
                "destination": reservation.metadata.get("origin_address", "Home")
            }
            
        except Exception as e:
            logger.error(f"Error scheduling return journey: {str(e)}")
            raise
    
    def check_pending_returns(self) -> List[Dict]:
        """
        Check for parking reservations with upcoming returns.
        
        Returns:
            List of reservations needing return journey reminders
        """
        try:
            # Find reservations with check-out in next 24 hours
            cutoff_time = datetime.utcnow() + timedelta(hours=24)
            current_time = datetime.utcnow()
            
            pending_returns = self.db.query(ParkingReservation).filter(
                and_(
                    ParkingReservation.check_out_time > current_time,
                    ParkingReservation.check_out_time <= cutoff_time,
                    ParkingReservation.return_reminder_sent == False,
                    ParkingReservation.parking_photo_url.isnot(None)
                )
            ).all()
            
            results = []
            for reservation in pending_returns:
                results.append({
                    "reservation_id": reservation.id,
                    "user_id": reservation.user_id,
                    "location": reservation.location_name,
                    "check_out_time": reservation.check_out_time.isoformat(),
                    "parking_photo_url": reservation.parking_photo_url,
                    "spot_info": f"{reservation.lot_name} - {reservation.spot_number}" if reservation.spot_number else reservation.lot_name
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error checking pending returns: {str(e)}")
            return []
    
    def send_return_reminder(self, parking_reservation_id: str) -> bool:
        """
        Send a return journey reminder with parking photo.
        
        Args:
            parking_reservation_id: The parking reservation ID
            
        Returns:
            True if reminder was sent successfully
        """
        try:
            reservation = self.db.query(ParkingReservation).filter(
                ParkingReservation.id == parking_reservation_id
            ).first()
            
            if not reservation:
                logger.error(f"Parking reservation {parking_reservation_id} not found")
                return False
            
            # Get user
            user = self.db.query(User).filter(User.id == reservation.user_id).first()
            if not user:
                logger.error(f"User {reservation.user_id} not found")
                return False
            
            # Create reminder message with photo reference
            reminder_context = {
                "type": "return_journey_reminder",
                "parking_location": reservation.location_name,
                "lot_name": reservation.lot_name,
                "spot_number": reservation.spot_number,
                "vehicle": f"{reservation.vehicle_color} {reservation.vehicle_make} {reservation.vehicle_model}",
                "parking_photo_url": reservation.parking_photo_url,
                "check_out_time": reservation.check_out_time.isoformat(),
                "estimated_pickup_time": reservation.estimated_pickup_time.isoformat() if reservation.estimated_pickup_time else None
            }
            
            # Use orchestration agent to generate personalized reminder
            response = self.orchestration_agent.process_request(
                user_input="Remind me about my return journey and help me find my car",
                context=reminder_context,
                user_id=reservation.user_id
            )
            
            # Mark reminder as sent
            reservation.return_reminder_sent = True
            self.db.commit()
            
            # Cache the reminder for quick access
            cache_key = f"return_reminder:{reservation.id}"
            cache_manager.set(cache_key, reminder_context, ttl=3600)  # 1 hour cache
            
            logger.info(f"Return reminder sent for reservation {parking_reservation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending return reminder: {str(e)}")
            return False
    
    def get_parking_photo_context(self, parking_reservation_id: str) -> Optional[Dict]:
        """
        Get parking photo and context for easy car location.
        
        Args:
            parking_reservation_id: The parking reservation ID
            
        Returns:
            Dictionary with photo URL and parking context
        """
        try:
            # Check cache first
            cache_key = f"parking_context:{parking_reservation_id}"
            cached_context = cache_manager.get(cache_key)
            if cached_context:
                return cached_context
            
            reservation = self.db.query(ParkingReservation).filter(
                ParkingReservation.id == parking_reservation_id
            ).first()
            
            if not reservation or not reservation.parking_photo_url:
                return None
            
            context = {
                "photo_url": reservation.parking_photo_url,
                "location": reservation.location_name,
                "lot": reservation.lot_name,
                "spot": reservation.spot_number,
                "vehicle": {
                    "make": reservation.vehicle_make,
                    "model": reservation.vehicle_model,
                    "color": reservation.vehicle_color,
                    "license_plate": reservation.license_plate
                },
                "parked_at": reservation.photo_uploaded_at.isoformat() if reservation.photo_uploaded_at else None,
                "terminal": reservation.terminal,
                "walking_directions": self._generate_walking_directions(reservation)
            }
            
            # Cache for future requests
            cache_manager.set(cache_key, context, ttl=7200)  # 2 hour cache
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting parking photo context: {str(e)}")
            return None
    
    def _schedule_reminder_notification(
        self,
        reservation: ParkingReservation,
        reminder_time: datetime
    ) -> None:
        """
        Schedule a reminder notification for the return journey.
        
        Args:
            reservation: The parking reservation
            reminder_time: When to send the reminder
        """
        # This would integrate with a task queue or notification service
        # For now, we'll log the scheduling
        logger.info(
            f"Scheduled return reminder for reservation {reservation.id} at {reminder_time}"
        )
    
    def _generate_walking_directions(self, reservation: ParkingReservation) -> str:
        """
        Generate walking directions from terminal to parking spot.
        
        Args:
            reservation: The parking reservation
            
        Returns:
            Text description of walking directions
        """
        directions = []
        
        if reservation.terminal:
            directions.append(f"Exit from {reservation.terminal}")
        
        if reservation.lot_name:
            directions.append(f"Head to {reservation.lot_name}")
        
        if reservation.spot_number:
            directions.append(f"Your car is in spot {reservation.spot_number}")
        
        if reservation.vehicle_color and reservation.vehicle_make:
            directions.append(
                f"Look for your {reservation.vehicle_color} {reservation.vehicle_make} {reservation.vehicle_model}"
            )
        
        return " → ".join(directions) if directions else "Check your parking photo for location"