"""
Event-sourced booking service demonstrating event store integration.

This shows how the booking service emits events for complete audit trail.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from backend.app.services.booking_service import BookingService
from backend.app.core.event_store import EventStore, EventType, Event
from backend.app.core.logger import get_logger
from backend.app.core.tracing import trace_method

logger = get_logger(__name__)


class EventSourcedBookingService(BookingService):
    """
    Enhanced booking service that emits events for all state changes.
    
    This provides:
    - Complete audit trail of all booking changes
    - Event replay capability for debugging
    - Analytics and reporting from event stream
    - Compliance with data retention requirements
    """
    
    def __init__(self, event_store: EventStore):
        super().__init__()
        self.event_store = event_store
    
    @trace_method(name="booking.create_with_events")
    async def create_booking(
        self,
        user_id: str,
        partner: str,
        venue_id: str,
        date: datetime,
        party_size: int,
        special_requests: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a booking with full event sourcing."""
        
        # Generate booking ID
        booking_id = self._generate_booking_id()
        
        # Emit booking created event
        self.event_store.append(
            event_type=EventType.BOOKING_CREATED,
            aggregate_id=booking_id,
            aggregate_type="Booking",
            event_data={
                "partner": partner,
                "venue_id": venue_id,
                "date": date.isoformat(),
                "party_size": party_size,
                "special_requests": special_requests,
                "user_preferences": kwargs.get("user_preferences", {})
            },
            user_id=user_id,
            metadata={
                "source": "web",
                "ip_address": kwargs.get("ip_address"),
                "user_agent": kwargs.get("user_agent")
            }
        )
        
        try:
            # Call partner API
            result = await super().create_booking(
                partner=partner,
                venue_id=venue_id,
                date=date,
                party_size=party_size,
                user_data={"user_id": user_id, "special_requests": special_requests}
            )
            
            if result["success"]:
                # Emit booking confirmed event
                self.event_store.append(
                    event_type=EventType.BOOKING_CONFIRMED,
                    aggregate_id=booking_id,
                    aggregate_type="Booking",
                    event_data={
                        "confirmation_number": result["confirmation_number"],
                        "total_amount": result.get("total_amount", 0),
                        "venue_name": result.get("venue_name"),
                        "booking_time": result.get("booking_time"),
                        "partner_response": result
                    },
                    user_id=user_id,
                    metadata={
                        "processing_time_ms": result.get("processing_time", 0)
                    }
                )
                
                # Calculate and emit commission event
                if result.get("total_amount", 0) > 0:
                    commission = self._calculate_commission(
                        partner, 
                        result["total_amount"]
                    )
                    
                    self.event_store.append(
                        event_type=EventType.COMMISSION_CALCULATED,
                        aggregate_id=booking_id,
                        aggregate_type="Booking",
                        event_data={
                            "booking_amount": result["total_amount"],
                            "commission_rate": commission["rate"],
                            "commission_amount": commission["amount"],
                            "tier": commission["tier"]
                        },
                        user_id=user_id
                    )
            else:
                # Emit booking failed event
                self.event_store.append(
                    event_type=EventType.SYSTEM_ERROR,
                    aggregate_id=booking_id,
                    aggregate_type="Booking",
                    event_data={
                        "error_type": "booking_failed",
                        "error_message": result.get("error", "Unknown error"),
                        "partner": partner,
                        "venue_id": venue_id
                    },
                    user_id=user_id
                )
            
            return {
                **result,
                "booking_id": booking_id
            }
            
        except Exception as e:
            # Emit error event
            self.event_store.append(
                event_type=EventType.SYSTEM_ERROR,
                aggregate_id=booking_id,
                aggregate_type="Booking",
                event_data={
                    "error_type": "booking_exception",
                    "error_message": str(e),
                    "partner": partner,
                    "venue_id": venue_id
                },
                user_id=user_id,
                metadata={
                    "exception_type": type(e).__name__
                }
            )
            raise
    
    async def cancel_booking(
        self,
        booking_id: str,
        user_id: str,
        confirmation_number: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cancel a booking with event emission."""
        
        # Emit cancellation started event
        self.event_store.append(
            event_type=EventType.BOOKING_CANCELLED,
            aggregate_id=booking_id,
            aggregate_type="Booking",
            event_data={
                "confirmation_number": confirmation_number,
                "cancellation_reason": reason,
                "initiated_by": "user",
                "timestamp": datetime.utcnow().isoformat()
            },
            user_id=user_id
        )
        
        try:
            # Get booking details from event history
            events = self.event_store.get_events(booking_id, "Booking")
            
            # Find original booking details
            booking_data = None
            commission_data = None
            
            for event in events:
                if event.event_type == EventType.BOOKING_CONFIRMED:
                    booking_data = event.event_data
                elif event.event_type == EventType.COMMISSION_CALCULATED:
                    commission_data = event.event_data
            
            if not booking_data:
                raise ValueError("Booking not found")
            
            # Call partner cancellation API
            partner = self._get_partner_from_confirmation(confirmation_number)
            result = await super().cancel_booking(
                partner=partner,
                confirmation_number=confirmation_number
            )
            
            if result["success"] and commission_data:
                # Calculate commission reversal
                reversal_amount = self._calculate_commission_reversal(
                    commission_data["commission_amount"],
                    booking_data.get("date"),
                    datetime.utcnow()
                )
                
                # Emit commission reversal event
                self.event_store.append(
                    event_type=EventType.COMMISSION_REVERSED,
                    aggregate_id=booking_id,
                    aggregate_type="Booking",
                    event_data={
                        "original_commission": commission_data["commission_amount"],
                        "reversal_amount": reversal_amount,
                        "reversal_reason": "booking_cancelled",
                        "cancellation_fee": result.get("cancellation_fee", 0)
                    },
                    user_id=user_id
                )
            
            return result
            
        except Exception as e:
            # Emit error event
            self.event_store.append(
                event_type=EventType.SYSTEM_ERROR,
                aggregate_id=booking_id,
                aggregate_type="Booking",
                event_data={
                    "error_type": "cancellation_failed",
                    "error_message": str(e),
                    "confirmation_number": confirmation_number
                },
                user_id=user_id
            )
            raise
    
    async def modify_booking(
        self,
        booking_id: str,
        user_id: str,
        confirmation_number: str,
        modifications: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Modify a booking with event tracking."""
        
        # Emit modification event
        self.event_store.append(
            event_type=EventType.BOOKING_MODIFIED,
            aggregate_id=booking_id,
            aggregate_type="Booking",
            event_data={
                "confirmation_number": confirmation_number,
                "modifications": modifications,
                "modified_at": datetime.utcnow().isoformat()
            },
            user_id=user_id
        )
        
        # Process modification...
        # (Implementation details)
        
        return {"success": True, "message": "Booking modified"}
    
    def _calculate_commission(
        self, 
        partner: str, 
        amount: float
    ) -> Dict[str, Any]:
        """Calculate commission for a booking."""
        # Commission tiers
        commission_rates = {
            "opentable": {"tier1": 0.10, "tier2": 0.12, "tier3": 0.15},
            "recreation.gov": {"flat": 0.08},
            "shell_recharge": {"flat": 0.05}
        }
        
        partner_rates = commission_rates.get(partner.lower(), {"flat": 0.10})
        
        # Simple tiered calculation
        if "tier1" in partner_rates:
            if amount < 100:
                rate = partner_rates["tier1"]
                tier = "tier1"
            elif amount < 500:
                rate = partner_rates["tier2"]
                tier = "tier2"
            else:
                rate = partner_rates["tier3"]
                tier = "tier3"
        else:
            rate = partner_rates["flat"]
            tier = "flat"
        
        return {
            "rate": rate,
            "amount": amount * rate,
            "tier": tier
        }
    
    def _calculate_commission_reversal(
        self,
        original_commission: float,
        booking_date: str,
        cancellation_date: datetime
    ) -> float:
        """Calculate commission reversal amount based on cancellation policy."""
        # Simple policy: full reversal if cancelled > 24 hours before
        # Otherwise, 50% reversal
        
        booking_dt = datetime.fromisoformat(booking_date)
        hours_before = (booking_dt - cancellation_date).total_seconds() / 3600
        
        if hours_before > 24:
            return original_commission
        else:
            return original_commission * 0.5
    
    def _generate_booking_id(self) -> str:
        """Generate a unique booking ID."""
        import uuid
        return str(uuid.uuid4())
    
    def _get_partner_from_confirmation(self, confirmation_number: str) -> str:
        """Determine partner from confirmation number format."""
        # Simple logic based on prefix
        if confirmation_number.startswith("OT"):
            return "opentable"
        elif confirmation_number.startswith("RG"):
            return "recreation.gov"
        elif confirmation_number.startswith("SR"):
            return "shell_recharge"
        else:
            return "unknown"