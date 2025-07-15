"""
Fixes for failing reservation management tests
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import re
import logging

logger = logging.getLogger(__name__)


class ReservationValidationFixes:
    """Fixes for reservation validation issues"""
    
    # Constants for validation
    MIN_PARTY_SIZE = 1
    MAX_PARTY_SIZE = 20
    MAX_BOOKING_DAYS_AHEAD = 90
    
    @staticmethod
    def validate_party_size(party_size: int) -> None:
        """
        Validate party size is within acceptable range
        FIX: Add proper validation that was missing
        """
        if party_size < ReservationValidationFixes.MIN_PARTY_SIZE:
            raise ValueError(f"Party size must be at least {ReservationValidationFixes.MIN_PARTY_SIZE}")
        
        if party_size > ReservationValidationFixes.MAX_PARTY_SIZE:
            raise ValueError(f"Party size cannot exceed {ReservationValidationFixes.MAX_PARTY_SIZE}")
    
    @staticmethod
    def validate_booking_time(date_time: datetime) -> None:
        """
        Validate booking time is valid
        FIX: Ensure consistent timezone handling
        """
        # Convert to UTC if not already
        if date_time.tzinfo is None:
            date_time = date_time.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        
        if date_time < now:
            raise ValueError("Cannot book in the past")
        
        max_future_date = now + timedelta(days=ReservationValidationFixes.MAX_BOOKING_DAYS_AHEAD)
        if date_time > max_future_date:
            raise ValueError(f"Cannot book more than {ReservationValidationFixes.MAX_BOOKING_DAYS_AHEAD} days in advance")
    
    @staticmethod
    def validate_customer_info(customer_info: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Validate customer information
        FIX: Return consistent error format
        """
        errors = {}
        required_fields = ['firstName', 'lastName', 'email', 'phone']
        
        for field in required_fields:
            if field not in customer_info or not customer_info[field]:
                errors[field] = [f"{field} is required"]
        
        # Validate email format
        if 'email' in customer_info and customer_info['email']:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, customer_info['email']):
                errors['email'] = ['Invalid email format']
        
        return errors


class ReservationTimezoneFixes:
    """Fixes for timezone handling in reservations"""
    
    @staticmethod
    def ensure_utc(date_time: datetime) -> datetime:
        """
        Ensure datetime is in UTC
        FIX: Consistent timezone handling
        """
        if date_time.tzinfo is None:
            # Assume UTC if no timezone
            return date_time.replace(tzinfo=timezone.utc)
        else:
            # Convert to UTC
            return date_time.astimezone(timezone.utc)
    
    @staticmethod
    def compare_deadlines(deadline: datetime, current_time: Optional[datetime] = None) -> bool:
        """
        Compare deadline with current time using consistent timezones
        FIX: Ensure both times are in same timezone for comparison
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        deadline_utc = ReservationTimezoneFixes.ensure_utc(deadline)
        current_utc = ReservationTimezoneFixes.ensure_utc(current_time)
        
        return current_utc < deadline_utc


class ReservationErrorHandlingFixes:
    """Fixes for error message consistency"""
    
    @staticmethod
    def format_booking_error(error: Exception) -> Dict[str, Any]:
        """
        Format booking errors consistently
        FIX: Standardize error response format
        """
        error_message = str(error)
        
        # Standard error response format
        return {
            "error": "booking_failed",
            "message": error_message,
            "details": {
                "type": type(error).__name__,
                "user_message": ReservationErrorHandlingFixes._get_user_friendly_message(error_message)
            }
        }
    
    @staticmethod
    def _get_user_friendly_message(error_message: str) -> str:
        """Convert technical errors to user-friendly messages"""
        error_mappings = {
            "fully booked": "This restaurant is fully booked for the selected time",
            "connection": "Unable to connect to booking service. Please try again",
            "invalid": "Some information provided is invalid. Please check and try again",
            "past": "Cannot make reservations for past dates",
            "unauthorized": "You don't have permission to perform this action"
        }
        
        lower_message = error_message.lower()
        for key, friendly_message in error_mappings.items():
            if key in lower_message:
                return friendly_message
        
        return "An error occurred while processing your reservation. Please try again"


# Apply fixes to ReservationManagementService
def apply_reservation_fixes():
    """Apply all fixes to the reservation management service"""
    from backend.app.services.reservation_management_service import ReservationManagementService
    
    # Store original methods
    original_create = ReservationManagementService.create_reservation
    original_modify = ReservationManagementService.modify_reservation
    
    async def create_reservation_with_validation(self, **kwargs):
        """Wrapper that adds validation"""
        # Validate party size
        if 'party_size' in kwargs:
            ReservationValidationFixes.validate_party_size(kwargs['party_size'])
        
        # Validate booking time
        if 'date_time' in kwargs:
            ReservationValidationFixes.validate_booking_time(kwargs['date_time'])
        
        # Validate customer info
        if 'customer_info' in kwargs:
            errors = ReservationValidationFixes.validate_customer_info(kwargs['customer_info'])
            if errors:
                raise ValueError(f"Invalid customer information: {errors}")
        
        try:
            return await original_create(self, **kwargs)
        except Exception as e:
            # Format error consistently
            formatted_error = ReservationErrorHandlingFixes.format_booking_error(e)
            raise Exception(formatted_error['details']['user_message'])
    
    async def modify_reservation_with_timezone_fix(self, **kwargs):
        """Wrapper that fixes timezone handling"""
        # Get existing reservation with proper timezone handling
        if 'confirmation_number' in kwargs:
            # Fetch existing reservation
            existing = await self.get_reservation(kwargs['confirmation_number'])
            
            if existing and 'modification_deadline' in existing:
                deadline = existing['modification_deadline']
                if isinstance(deadline, str):
                    deadline = datetime.fromisoformat(deadline)
                
                # Check deadline with proper timezone handling
                if not ReservationTimezoneFixes.compare_deadlines(deadline):
                    raise ValueError("Modification deadline has passed")
        
        # Ensure new datetime is in UTC
        if 'new_date_time' in kwargs:
            kwargs['new_date_time'] = ReservationTimezoneFixes.ensure_utc(kwargs['new_date_time'])
        
        return await original_modify(self, **kwargs)
    
    # Apply the wrapped methods
    ReservationManagementService.create_reservation = create_reservation_with_validation
    ReservationManagementService.modify_reservation = modify_reservation_with_timezone_fix
    
    # Add validation methods to the class
    ReservationManagementService._validate_customer_info = ReservationValidationFixes.validate_customer_info
    ReservationManagementService._validate_party_size = ReservationValidationFixes.validate_party_size
    ReservationManagementService._validate_booking_time = ReservationValidationFixes.validate_booking_time


# Additional fix for the missing import
from datetime import timedelta