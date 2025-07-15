"""
Restaurant booking service integrating OpenTable with the booking system.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional

from backend.app.integrations.booking.opentable_client import opentable_client
from backend.app.services.booking_service import BookingService
from app.core.enums import BookingType
from backend.app.core.logger import logger


class RestaurantBookingService:
    """Service for handling restaurant reservations through OpenTable."""
    
    def __init__(self):
        self.opentable = opentable_client
        self.booking_service = BookingService()
    
    async def search_restaurants(
        self,
        location: Dict[str, Any],
        preferences: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Search for restaurants based on location and preferences.
        
        Args:
            location: Location data (lat/lon or city/state)
            preferences: Search preferences (cuisine, price, etc.)
            
        Returns:
            List of restaurant options with availability
        """
        try:
            # Extract search parameters
            cuisine = preferences.get("cuisine")
            party_size = preferences.get("party_size", 2)
            date = preferences.get("date")
            time = preferences.get("time", "19:00")
            price_range = preferences.get("price_range")
            
            # Search restaurants
            results = await self.opentable.search_restaurants(
                location=location,
                cuisine=cuisine,
                party_size=party_size,
                date=date,
                time=time,
                price_range=price_range,
                radius_miles=preferences.get("radius_miles", 5.0)
            )
            
            # Enhance results with availability for top restaurants
            enhanced_restaurants = []
            for restaurant in results.get("restaurants", [])[:5]:  # Check top 5
                try:
                    availability = await self.opentable.get_availability(
                        restaurant_id=restaurant["id"],
                        date=date or datetime.now().strftime("%Y-%m-%d"),
                        time=time,
                        party_size=party_size
                    )
                    
                    restaurant["available_times"] = availability.get("available_times", [])
                    restaurant["has_availability"] = len(restaurant["available_times"]) > 0
                    enhanced_restaurants.append(restaurant)
                    
                except Exception as e:
                    logger.error(f"Failed to check availability for {restaurant['name']}: {e}")
                    restaurant["available_times"] = []
                    restaurant["has_availability"] = False
                    enhanced_restaurants.append(restaurant)
            
            return enhanced_restaurants
            
        except Exception as e:
            logger.error(f"Restaurant search failed: {e}")
            return []
    
    async def create_restaurant_booking(
        self,
        user_id: int,
        restaurant_id: str,
        booking_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a restaurant reservation.
        
        Args:
            user_id: User making the reservation
            restaurant_id: Restaurant identifier
            booking_details: Reservation details
            
        Returns:
            Booking confirmation with details
        """
        try:
            # Create OpenTable reservation
            reservation = await self.opentable.create_reservation(
                restaurant_id=restaurant_id,
                date=booking_details["date"],
                time=booking_details["time"],
                party_size=booking_details["party_size"],
                guest_info=booking_details["guest_info"],
                special_requests=booking_details.get("special_requests")
            )
            
            # Record in our booking system
            booking_data = {
                "user_id": user_id,
                "partner_id": 2,  # OpenTable partner ID
                "booking_type": BookingType.RESTAURANT,
                "service_date": f"{booking_details['date']} {booking_details['time']}",
                "gross_amount": booking_details["party_size"] * 50.0,  # Estimated
                "partner_booking_id": reservation["confirmation_number"],
                "metadata": {
                    "restaurant_name": reservation["restaurant_name"],
                    "party_size": booking_details["party_size"],
                    "special_requests": booking_details.get("special_requests"),
                    "cancellation_policy": reservation.get("cancellation_policy")
                }
            }
            
            booking = await self.booking_service.create_booking(booking_data)
            
            # Combine responses
            return {
                "booking_id": booking.id,
                "booking_reference": booking.booking_reference,
                "confirmation_number": reservation["confirmation_number"],
                "restaurant_name": reservation["restaurant_name"],
                "date": booking_details["date"],
                "time": booking_details["time"],
                "party_size": booking_details["party_size"],
                "guest_name": reservation["guest_name"],
                "commission_amount": reservation["commission_amount"],
                "status": "confirmed",
                "cancellation_policy": reservation.get("cancellation_policy"),
                "reservation_url": reservation.get("reservation_url")
            }
            
        except Exception as e:
            logger.error(f"Restaurant booking failed: {e}")
            raise
    
    async def get_restaurant_suggestions(
        self,
        location: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Get restaurant suggestions based on context.
        
        Args:
            location: Current location
            context: Journey context (time, preferences, etc.)
            
        Returns:
            List of restaurant suggestions
        """
        suggestions = []
        
        # Determine meal type based on time
        current_hour = context.get("current_time", datetime.now()).hour
        if 6 <= current_hour <= 10:
            meal_type = "breakfast"
            cuisines = ["American", "Cafe", "Brunch"]
        elif 11 <= current_hour <= 14:
            meal_type = "lunch"
            cuisines = ["American", "Italian", "Mexican", "Asian"]
        elif 17 <= current_hour <= 21:
            meal_type = "dinner"
            cuisines = ["Italian", "Steakhouse", "Seafood", "Asian"]
        else:
            meal_type = "late_night"
            cuisines = ["American", "Pizza", "Bar"]
        
        # Search for each cuisine type
        for cuisine in cuisines[:2]:  # Limit to avoid too many API calls
            try:
                results = await self.search_restaurants(
                    location=location,
                    preferences={
                        "cuisine": cuisine,
                        "party_size": context.get("party_size", 2),
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "time": self._get_next_meal_time(meal_type),
                        "radius_miles": 5.0
                    }
                )
                
                # Add top result as suggestion
                if results:
                    restaurant = results[0]
                    suggestions.append({
                        "type": "restaurant",
                        "name": restaurant["name"],
                        "cuisine": restaurant["cuisine"],
                        "rating": restaurant.get("rating", 4.0),
                        "price_range": restaurant.get("price_range", "$$"),
                        "distance": self._calculate_distance(
                            location,
                            restaurant["location"]
                        ),
                        "available_times": restaurant.get("available_times", [])[:3],
                        "action": {
                            "type": "book_restaurant",
                            "restaurant_id": restaurant["id"],
                            "meal_type": meal_type
                        }
                    })
                    
            except Exception as e:
                logger.error(f"Failed to get {cuisine} suggestions: {e}")
        
        return suggestions
    
    def _get_next_meal_time(self, meal_type: str) -> str:
        """Get typical time for meal type."""
        times = {
            "breakfast": "08:00",
            "lunch": "12:30",
            "dinner": "19:00",
            "late_night": "22:00"
        }
        return times.get(meal_type, "19:00")
    
    def _calculate_distance(
        self,
        location1: Dict[str, Any],
        location2: Dict[str, Any]
    ) -> float:
        """Calculate approximate distance between locations."""
        # Simplified distance calculation
        if "latitude" in location1 and "latitude" in location2:
            lat_diff = abs(location1["latitude"] - location2["latitude"])
            lon_diff = abs(location1["longitude"] - location2["longitude"])
            # Very rough approximation
            return round((lat_diff + lon_diff) * 69, 1)  # degrees to miles
        return 0.0
    
    async def cancel_restaurant_booking(
        self,
        booking_reference: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancel a restaurant reservation.
        
        Args:
            booking_reference: Booking reference number
            reason: Cancellation reason
            
        Returns:
            Cancellation confirmation
        """
        try:
            # Get booking details
            booking = await self.booking_service.get_booking_by_reference(booking_reference)
            
            if not booking or booking.booking_type != BookingType.RESTAURANT:
                raise ValueError("Invalid restaurant booking reference")
            
            # Cancel with OpenTable
            result = await self.opentable.cancel_reservation(
                booking.partner_booking_id,
                reason=reason
            )
            
            # Update booking status
            await self.booking_service.cancel_booking(booking.id)
            
            return {
                "booking_reference": booking_reference,
                "status": "cancelled",
                "cancelled_at": result["cancelled_at"],
                "refund_amount": result.get("refund_amount", 0)
            }
            
        except Exception as e:
            logger.error(f"Restaurant cancellation failed: {e}")
            raise


# Global instance
restaurant_booking_service = RestaurantBookingService()