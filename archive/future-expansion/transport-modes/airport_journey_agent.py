"""
Airport Journey Agent for the Master Orchestration system.

This agent specializes in:
- Detecting airport trips
- Managing flight information
- Coordinating parking bookings
- Optimizing departure timing
- Handling pickup/dropoff scenarios
- Airport amenity recommendations (lounges, dining)
- Terminal navigation assistance
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import re

from backend.app.core.logger import get_logger
from backend.app.core.tracing import trace_method
from backend.app.services.airport_service import AirportService, AirportCode
from backend.app.integrations.flight_tracker_client import flight_tracker
from backend.app.models.airport import FlightStatus
from backend.app.core.event_store import EventStore, EventType
from backend.app.services.airport_amenities_service import AirportAmenitiesService
from backend.app.services.terminal_navigation_service import TerminalNavigationService

logger = get_logger(__name__)


class AirportJourneyAgent:
    """
    Specialized agent for airport-related journeys.
    
    This agent is activated by the Master Orchestration Agent when
    an airport destination is detected.
    """
    
    def __init__(self, airport_service: AirportService, event_store: EventStore):
        self.airport_service = airport_service
        self.event_store = event_store
        self.flight_pattern = re.compile(r'([A-Z]{2})\s*(\d+)', re.IGNORECASE)
        self.amenities_service = AirportAmenitiesService()
        self.navigation_service = TerminalNavigationService()
    
    @trace_method(name="airport_agent.analyze")
    async def analyze_journey_intent(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze if this is an airport journey and extract relevant information.
        
        Args:
            user_input: User's request
            context: Journey context
            
        Returns:
            Analysis results with airport journey details
        """
        analysis = {
            "is_airport_journey": False,
            "journey_type": None,  # "dropoff", "pickup", "parking"
            "airport_info": None,
            "flight_info": None,
            "needs_parking": False,
            "needs_lounge": False,
            "needs_dining": False,
            "confidence": 0.0
        }
        
        # Check destination for airport
        destination = context.get("destination", "").lower()
        airport_detected = await self.airport_service.detect_airport_trip(destination)
        
        if airport_detected:
            analysis["is_airport_journey"] = True
            analysis["airport_info"] = airport_detected
            analysis["confidence"] = 0.9
            
            # Determine journey type from user input
            user_input_lower = user_input.lower()
            
            if any(word in user_input_lower for word in ["pick up", "pickup", "picking up", "collect"]):
                analysis["journey_type"] = "pickup"
            elif any(word in user_input_lower for word in ["drop off", "dropoff", "dropping off"]):
                analysis["journey_type"] = "dropoff"
            elif any(word in user_input_lower for word in ["park", "parking", "flying", "flight"]):
                analysis["journey_type"] = "parking"
                analysis["needs_parking"] = True
            else:
                # Default to dropoff if going to airport
                analysis["journey_type"] = "dropoff"
            
            # Check for amenity needs
            if any(word in user_input_lower for word in ["lounge", "relax", "wait"]):
                analysis["needs_lounge"] = True
            if any(word in user_input_lower for word in ["eat", "food", "restaurant", "hungry", "dining"]):
                analysis["needs_dining"] = True
            
            # Extract flight information
            flight_info = self._extract_flight_info(user_input, context)
            if flight_info:
                analysis["flight_info"] = flight_info
                analysis["confidence"] = 1.0
        
        # Also check if origin is an airport (return journey)
        origin = context.get("origin", "").lower()
        origin_airport = await self.airport_service.detect_airport_trip(origin)
        
        if origin_airport and not airport_detected:
            analysis["is_airport_journey"] = True
            analysis["journey_type"] = "return"
            analysis["airport_info"] = origin_airport
            analysis["confidence"] = 0.9
        
        return analysis
    
    @trace_method(name="airport_agent.create_journey")
    async def create_airport_journey(
        self,
        user_id: str,
        journey_analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a complete airport journey experience.
        
        Args:
            user_id: User ID
            journey_analysis: Analysis from analyze_journey_intent
            context: Journey context
            
        Returns:
            Complete journey plan with recommendations
        """
        airport_info = journey_analysis["airport_info"]
        journey_type = journey_analysis["journey_type"]
        
        response = {
            "journey_type": journey_type,
            "airport": airport_info,
            "recommendations": [],
            "voice_personality": "captain",
            "notifications": []
        }
        
        if journey_type == "parking":
            # Handle parking journey
            response.update(await self._create_parking_journey(
                user_id, airport_info, journey_analysis.get("flight_info"), context
            ))
            
        elif journey_type == "pickup":
            # Handle pickup journey
            response.update(await self._create_pickup_journey(
                user_id, airport_info, journey_analysis.get("flight_info"), context
            ))
            
        elif journey_type == "dropoff":
            # Handle dropoff journey
            response.update(await self._create_dropoff_journey(
                user_id, airport_info, journey_analysis.get("flight_info"), context
            ))
            
        elif journey_type == "return":
            # Handle return from airport
            response.update(await self._create_return_journey(
                user_id, airport_info, context
            ))
        
        # Emit journey created event
        self.event_store.append(
            event_type=EventType.JOURNEY_STARTED,
            aggregate_id=f"airport_journey_{datetime.now().timestamp()}",
            aggregate_type="AirportJourney",
            event_data={
                "journey_type": journey_type,
                "airport_code": airport_info["code"],
                "user_id": user_id,
                "flight_info": journey_analysis.get("flight_info")
            },
            user_id=user_id
        )
        
        return response
    
    async def _create_parking_journey(
        self,
        user_id: str,
        airport_info: Dict[str, Any],
        flight_info: Optional[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a journey for someone parking at the airport."""
        
        journey_updates = {
            "parking_needed": True,
            "recommendations": []
        }
        
        # Calculate optimal departure time if we have flight info
        if flight_info and flight_info.get("departure_time"):
            departure_calc = await self.airport_service.calculate_optimal_departure_time(
                flight_time=flight_info["departure_time"],
                origin=context.get("origin", "Current location"),
                airport_code=airport_info["code"],
                has_bags_to_check=flight_info.get("checked_bags", True),
                has_precheck=context.get("user_preferences", {}).get("has_precheck", False),
                international=flight_info.get("international", False)
            )
            
            journey_updates["departure_timing"] = departure_calc
            journey_updates["notifications"] = departure_calc["alerts"]
            
            # Add voice announcement
            journey_updates["initial_announcement"] = (
                f"Good day! This is your captain speaking. "
                f"For your {flight_info.get('departure_time').strftime('%I:%M %p')} flight, "
                f"I recommend departing at {departure_calc['recommended_departure'].strftime('%I:%M %p')}. "
                f"This gives us plenty of time for parking and check-in."
            )
        
        # Get parking options
        if flight_info:
            start_date = flight_info.get("departure_time", datetime.now())
            end_date = flight_info.get("return_date", start_date + timedelta(days=3))
        else:
            start_date = datetime.now()
            end_date = start_date + timedelta(days=3)
        
        parking_options = await self.airport_service.check_parking_availability(
            airport_code=airport_info["code"],
            start_date=start_date,
            end_date=end_date
        )
        
        journey_updates["parking_options"] = parking_options
        journey_updates["recommendations"].append({
            "type": "parking",
            "message": parking_options["recommendation"],
            "action": "book_parking",
            "options": parking_options["options"][:3]  # Top 3 options
        })
        
        # Add TSA wait time info
        tsa_info = await self.airport_service.get_tsa_wait_times(airport_info["code"])
        journey_updates["tsa_info"] = tsa_info
        journey_updates["recommendations"].append({
            "type": "security",
            "message": f"Current security wait: {tsa_info['checkpoints']['main']} minutes. "
                      f"{tsa_info['recommendation']}",
            "data": tsa_info
        })
        
        # Calculate wait time after security
        if flight_info and flight_info.get("departure_time"):
            departure_time = flight_info["departure_time"]
            current_time = datetime.now()
            security_time = timedelta(minutes=tsa_info['checkpoints']['main'] + 15)  # Buffer
            time_after_security = current_time + security_time
            wait_time_minutes = int((departure_time - time_after_security).total_seconds() / 60)
            
            if wait_time_minutes > 45:
                # Get amenity recommendations
                terminal = flight_info.get("terminal", "4")
                amenity_recs = await self.amenities_service.get_recommendations_by_wait_time(
                    airport_info["code"],
                    terminal,
                    wait_time_minutes,
                    context.get("user_preferences")
                )
                
                journey_updates["amenity_recommendations"] = amenity_recs
                
                # Add voice announcement about amenities
                journey_updates["amenity_announcement"] = (
                    f"With {wait_time_minutes} minutes after security, "
                    f"you'll have time to relax. I've found some excellent lounges and dining options."
                )
                
                # Add top recommendations
                for rec in amenity_recs[:2]:  # Top 2 categories
                    if rec["options"]:
                        journey_updates["recommendations"].append({
                            "type": "amenity",
                            "category": rec["category"],
                            "message": rec["reason"],
                            "options": rec["options"][:2]  # Top 2 options per category
                        })
        
        return journey_updates
    
    async def _create_pickup_journey(
        self,
        user_id: str,
        airport_info: Dict[str, Any],
        flight_info: Optional[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a journey for picking someone up from the airport."""
        
        journey_updates = {
            "pickup_mode": True,
            "recommendations": []
        }
        
        # If we have flight info, track the flight
        if flight_info and flight_info.get("flight_number"):
            flight_status = await flight_tracker.track_flight(
                flight_number=flight_info["flight_number"],
                departure_date=flight_info.get("departure_date", datetime.now())
            )
            
            journey_updates["flight_tracking"] = flight_status
            
            # Calculate when to leave for pickup
            if flight_status.get("arrival", {}).get("estimated"):
                arrival_time = flight_status["arrival"]["estimated"]
                
                # Add time for deplaning and baggage claim
                pickup_time = arrival_time + timedelta(minutes=30)
                
                # Calculate departure time
                from backend.app.services.directions_service import DirectionsService
                directions = DirectionsService()
                route = await directions.get_directions(
                    origin=context.get("origin", "Current location"),
                    destination=f"{airport_info['code']} Airport Arrivals"
                )
                
                drive_time = timedelta(seconds=route.get("duration", 1800))
                departure_time = pickup_time - drive_time - timedelta(minutes=10)  # Buffer
                
                journey_updates["pickup_timing"] = {
                    "flight_arrives": arrival_time,
                    "estimated_pickup": pickup_time,
                    "leave_by": departure_time,
                    "cell_phone_lot_arrival": departure_time + drive_time
                }
                
                journey_updates["initial_announcement"] = (
                    f"Flight {flight_info['flight_number']} is currently "
                    f"{flight_status['status'].replace('_', ' ')}. "
                    f"Scheduled arrival at {arrival_time.strftime('%I:%M %p')}. "
                    f"I'll guide you to the cell phone lot, then to arrivals when they land."
                )
                
                # Add notifications
                journey_updates["notifications"] = [
                    {
                        "time": departure_time - timedelta(minutes=30),
                        "message": "Flight tracking active. Prepare to leave soon."
                    },
                    {
                        "time": departure_time,
                        "message": "Time to head to the airport!"
                    },
                    {
                        "time": arrival_time,
                        "message": "Flight has landed! Head to arrivals pickup."
                    }
                ]
        
        # Add cell phone lot information
        journey_updates["recommendations"].append({
            "type": "waiting_area",
            "message": f"I'll guide you to {airport_info['name']}'s cell phone waiting lot. "
                      f"Free parking while you wait for arrival notification.",
            "location": "Cell Phone Lot"
        })
        
        return journey_updates
    
    async def _create_dropoff_journey(
        self,
        user_id: str,
        airport_info: Dict[str, Any],
        flight_info: Optional[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a journey for dropping someone off at the airport."""
        
        journey_updates = {
            "dropoff_mode": True,
            "recommendations": []
        }
        
        terminal = flight_info.get("terminal") if flight_info else None
        
        journey_updates["initial_announcement"] = (
            f"This is your captain speaking. I'll guide you to "
            f"{airport_info['name']} departures"
            f"{f' Terminal {terminal}' if terminal else ''}. "
            f"Current traffic conditions look favorable."
        )
        
        # Get real-time terminal traffic
        journey_updates["recommendations"].append({
            "type": "dropoff_zone",
            "message": f"Departures drop-off is on the upper level. "
                      f"Follow signs for {'Terminal ' + terminal if terminal else 'Departures'}.",
            "location": "Departures Level",
            "instructions": [
                "Use right lane for immediate dropoff",
                "Left lanes for longer goodbyes",
                "No parking at curbside"
            ]
        })
        
        # Add TSA wait info for passenger
        tsa_info = await self.airport_service.get_tsa_wait_times(
            airport_info["code"],
            terminal
        )
        
        journey_updates["recommendations"].append({
            "type": "passenger_info",
            "message": f"Let your passenger know: Security wait is currently "
                      f"{tsa_info['checkpoints']['main']} minutes.",
            "data": tsa_info
        })
        
        return journey_updates
    
    async def _create_return_journey(
        self,
        user_id: str,
        airport_info: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a journey returning from the airport."""
        
        journey_updates = {
            "return_mode": True,
            "recommendations": []
        }
        
        # Check if user has a parking reservation
        # In production, this would query the database
        has_parking = context.get("has_parking_reservation", False)
        
        if has_parking:
            journey_updates["initial_announcement"] = (
                f"Welcome back! Let's get you to your vehicle. "
                f"Your car is in {context.get('parking_lot', 'the parking area')}. "
                f"I have your parking location saved."
            )
            
            journey_updates["recommendations"].append({
                "type": "parking_retrieval",
                "message": "Follow signs to Ground Transportation, then to shuttle pickup.",
                "parking_info": context.get("parking_info", {})
            })
        else:
            journey_updates["initial_announcement"] = (
                f"Welcome to {airport_info['name']}! "
                f"Let's get you on your way. Where would you like to go?"
            )
        
        return journey_updates
    
    def _extract_flight_info(self, user_input: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract flight information from user input and context."""
        flight_info = {}
        
        # Look for flight number
        flight_match = self.flight_pattern.search(user_input)
        if flight_match:
            flight_info["flight_number"] = f"{flight_match.group(1)}{flight_match.group(2)}".upper()
        
        # Look for time information
        time_patterns = [
            r'(\d{1,2}):(\d{2})\s*(am|pm)',
            r'(\d{1,2})\s*(am|pm)',
            r'at\s+(\d{1,2})',
        ]
        
        for pattern in time_patterns:
            time_match = re.search(pattern, user_input, re.IGNORECASE)
            if time_match:
                # Parse time (simplified - in production use proper parsing)
                try:
                    if len(time_match.groups()) >= 3:
                        hour = int(time_match.group(1))
                        minute = int(time_match.group(2))
                        ampm = time_match.group(3).lower()
                        
                        if ampm == 'pm' and hour != 12:
                            hour += 12
                        elif ampm == 'am' and hour == 12:
                            hour = 0
                        
                        departure_time = datetime.now().replace(
                            hour=hour, minute=minute, second=0, microsecond=0
                        )
                        
                        # If time is in the past today, assume tomorrow
                        if departure_time < datetime.now():
                            departure_time += timedelta(days=1)
                        
                        flight_info["departure_time"] = departure_time
                except:
                    pass
                break
        
        # Check for other keywords
        if "international" in user_input.lower():
            flight_info["international"] = True
        
        if "no bags" in user_input.lower() or "carry on" in user_input.lower():
            flight_info["checked_bags"] = False
        else:
            flight_info["checked_bags"] = True
        
        # Get additional info from context
        if context.get("flight_number"):
            flight_info["flight_number"] = context["flight_number"]
        
        if context.get("departure_time"):
            flight_info["departure_time"] = context["departure_time"]
        
        return flight_info if flight_info else None
    
    @trace_method(name="airport_agent.handle_parking_query")
    async def handle_parking_query(
        self,
        user_id: str,
        airport_code: str,
        dates: Dict[str, datetime],
        preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle specific parking queries.
        
        Args:
            user_id: User ID
            airport_code: Airport IATA code
            dates: Start and end dates
            preferences: User preferences (budget, type, etc.)
            
        Returns:
            Parking recommendations
        """
        # Get parking options
        parking_options = await self.airport_service.check_parking_availability(
            airport_code=airport_code,
            start_date=dates["start"],
            end_date=dates["end"]
        )
        
        # Filter based on preferences
        if preferences:
            if preferences.get("max_price"):
                parking_options["options"] = [
                    opt for opt in parking_options["options"]
                    if opt["total_price"] <= preferences["max_price"]
                ]
            
            if preferences.get("covered_only"):
                parking_options["options"] = [
                    opt for opt in parking_options["options"]
                    if "Covered" in opt.get("features", [])
                ]
        
        # Generate voice response
        voice_response = self._generate_parking_voice_response(parking_options)
        
        return {
            "parking_options": parking_options,
            "voice_response": voice_response,
            "quick_actions": [
                {
                    "label": f"Book {opt['name']}",
                    "action": "book_parking",
                    "data": {
                        "type": opt["type"],
                        "price": opt["total_price"]
                    }
                }
                for opt in parking_options["options"][:3]
            ]
        }
    
    def _generate_parking_voice_response(self, parking_options: Dict[str, Any]) -> str:
        """Generate natural voice response for parking options."""
        if not parking_options["options"]:
            return "I'm sorry, but there doesn't appear to be any parking available for those dates."
        
        duration = parking_options["duration_days"]
        options = parking_options["options"]
        
        response = f"For your {duration} day trip, I found {len(options)} parking options. "
        
        # Describe top 3 options
        for i, opt in enumerate(options[:3]):
            if i == 0:
                response += f"The most economical is {opt['name']} at ${opt['total_price']:.0f} total"
                if opt['shuttle_frequency'] > 0:
                    response += f", with shuttles every {opt['shuttle_frequency']} minutes"
                response += ". "
            elif i == 1:
                response += f"For more convenience, {opt['name']} is ${opt['total_price']:.0f}"
                if opt['walk_time'] < 10:
                    response += f", just a {opt['walk_time']} minute walk to the terminal"
                response += ". "
            elif i == 2:
                response += f"Or for premium service, {opt['name']} at ${opt['total_price']:.0f}. "
        
        response += parking_options.get("recommendation", "")
        
        return response
    
    @trace_method(name="airport_agent.handle_amenity_query")
    async def handle_amenity_query(
        self,
        user_id: str,
        airport_code: str,
        terminal: str,
        query_type: str,
        wait_time_minutes: int,
        preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle queries about airport amenities (lounges, dining, etc).
        
        Args:
            user_id: User ID
            airport_code: Airport IATA code
            terminal: Terminal identifier
            query_type: Type of amenity query (lounge, dining, all)
            wait_time_minutes: Available wait time
            preferences: User preferences
            
        Returns:
            Amenity recommendations with booking options
        """
        # Get amenity types based on query
        amenity_types = None
        if query_type == "lounge":
            amenity_types = ["lounge"]
        elif query_type == "dining":
            amenity_types = ["restaurant", "cafe", "bar"]
        
        # Get amenities
        amenities = await self.amenities_service.get_airport_amenities(
            airport_code,
            terminal,
            amenity_types,
            preferences
        )
        
        # Get time-based recommendations
        recommendations = await self.amenities_service.get_recommendations_by_wait_time(
            airport_code,
            terminal,
            wait_time_minutes,
            preferences
        )
        
        # Generate voice response
        voice_response = self._generate_amenity_voice_response(
            amenities[:5],  # Top 5
            recommendations,
            wait_time_minutes
        )
        
        return {
            "amenities": amenities,
            "recommendations": recommendations,
            "voice_response": voice_response,
            "wait_time_minutes": wait_time_minutes,
            "booking_available": True,
            "quick_actions": self._generate_amenity_quick_actions(amenities[:3])
        }
    
    def _generate_amenity_voice_response(
        self,
        amenities: List[Any],
        recommendations: List[Dict[str, Any]],
        wait_time: int
    ) -> str:
        """Generate natural voice response for amenity recommendations."""
        if not amenities:
            return "I couldn't find any amenities in your terminal. Let me check other terminals."
        
        response = f"With {wait_time} minutes before your flight, "
        
        if wait_time < 30:
            response += "you have time for a quick refreshment. "
        elif wait_time < 90:
            response += "you can enjoy a meal or relax in a lounge. "
        else:
            response += "you have plenty of time to unwind. "
        
        # Describe top recommendations
        for i, rec in enumerate(recommendations[:2]):
            if rec["options"]:
                top_option = rec["options"][0]
                if i == 0:
                    response += f"I recommend {top_option.name}, "
                    if top_option.walking_time_minutes:
                        response += f"just a {top_option.walking_time_minutes} minute walk, "
                    if top_option.rating:
                        response += f"with a {top_option.rating:.1f} star rating. "
                else:
                    response += f"Or try {top_option.name} for {rec['category'].lower()}. "
        
        response += "Would you like me to check availability or book a spot?"
        
        return response
    
    def _generate_amenity_quick_actions(self, amenities: List[Any]) -> List[Dict[str, Any]]:
        """Generate quick action buttons for amenities."""
        actions = []
        
        for amenity in amenities:
            if amenity.booking_status == "available":
                action = {
                    "label": f"Book {amenity.name}",
                    "action": "book_amenity",
                    "data": {
                        "amenity_id": amenity.id,
                        "type": amenity.type,
                        "name": amenity.name,
                        "price_range": amenity.price_range
                    }
                }
                actions.append(action)
        
        return actions
    
    @trace_method(name="airport_agent.handle_navigation_query")
    async def handle_navigation_query(
        self,
        user_id: str,
        current_location: str,
        destination: str,
        mobility_needs: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle terminal navigation queries.
        
        Args:
            user_id: User ID
            current_location: Current location in terminal
            destination: Where user wants to go
            mobility_needs: Any accessibility requirements
            
        Returns:
            Navigation guidance with route options
        """
        # Determine route type
        route_type = "accessible" if mobility_needs else "fastest"
        
        # Get navigation route
        navigation = await self.navigation_service.calculate_route(
            "LAX",  # Would be dynamic
            current_location,
            destination,
            route_type
        )
        
        if not navigation:
            return {
                "error": "Unable to calculate route",
                "voice_response": f"I'm having trouble finding a route to {destination}. "
                                 f"Please ask airport staff for assistance."
            }
        
        # Generate turn-by-turn voice guidance
        voice_guidance = self._generate_navigation_voice_guidance(navigation)
        
        # Get nearby amenities along route
        nearby_amenities = []
        for segment in navigation.segments:
            if segment.amenities_along_route:
                nearby_amenities.extend(segment.amenities_along_route)
        
        return {
            "navigation": navigation,
            "voice_guidance": voice_guidance,
            "estimated_time": navigation.total_walking_time_minutes,
            "distance_meters": navigation.total_distance_meters,
            "nearby_amenities": list(set(nearby_amenities)),
            "real_time_alerts": navigation.real_time_alerts
        }
    
    def _generate_navigation_voice_guidance(self, navigation: Any) -> List[str]:
        """Generate voice-friendly navigation instructions."""
        guidance = []
        
        # Initial summary
        guidance.append(
            f"I'll guide you there. It's about a {navigation.total_walking_time_minutes} minute walk. "
            f"Let's begin."
        )
        
        # Turn-by-turn directions
        for i, segment in enumerate(navigation.segments):
            instruction = segment.direction
            
            # Add landmarks for easier navigation
            if segment.landmarks:
                instruction += f" You'll pass {segment.landmarks[0]}."
            
            # Add distance context for longer segments
            if segment.walking_time_minutes > 2:
                instruction += f" Continue for about {segment.walking_time_minutes} minutes."
            
            guidance.append(instruction)
        
        # Add alerts if any
        if navigation.real_time_alerts:
            guidance.append(
                f"Quick update: {navigation.real_time_alerts[0]}"
            )
        
        return guidance