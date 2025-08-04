"""
Captain Voice Personality for Airport Journeys.

Professional, reassuring, and knowledgeable airline captain personality
that activates for all airport-related trips.
"""

from typing import Dict, List, Optional
from datetime import datetime

from app.services.personality_engine import VoicePersonality, PersonalityType
from app.core.logger import get_logger

logger = get_logger(__name__)


class CaptainPersonality(VoicePersonality):
    """
    Airline Captain personality for airport journeys.
    
    This personality embodies:
    - Professional aviation experience
    - Calm and reassuring demeanor
    - Technical knowledge presented simply
    - Safety-focused guidance
    - Time precision
    """
    
    def __init__(self):
        super().__init__(
            id="captain",
            name="Captain Anderson",
            description="Professional airline captain for airport journeys",
            voice_id="en-US-Neural2-D",  # Deep, authoritative voice
            speaking_style={
                "pitch": -2,  # Lower pitch for authority
                "speed": 0.95,  # Slightly slower for clarity
                "emphasis": "professional",
                "authority": 0.9,
                "warmth": 0.7,
                "precision": 0.95
            },
            vocabulary_style="aviation_professional",
            catchphrases=[
                "This is your captain speaking",
                "We're looking at smooth conditions ahead",
                "Right on schedule",
                "Clear skies ahead",
                "Preparing for departure",
                "Flight deck to passengers",
                "Cruising at a comfortable speed",
                "Weather conditions are favorable",
                "We'll have you there in no time",
                "Safe travels"
            ],
            topics_of_expertise=[
                "aviation",
                "airports",
                "flight_operations",
                "weather_patterns",
                "time_management",
                "safety_procedures"
            ],
            emotion_range={
                "professional": 0.95,
                "confident": 0.9,
                "reassuring": 0.85,
                "friendly": 0.7,
                "authoritative": 0.8
            },
            age_appropriate=["child", "teen", "adult", "senior"],
            active_conditions=["airport_journey", "flight_day"]
        )
    
    def get_contextual_greeting(self, context: Dict) -> str:
        """Get airport-specific greeting based on context."""
        hour = datetime.now().hour
        journey_type = context.get("journey_type", "dropoff")
        
        if 5 <= hour < 12:
            time_greeting = "Good morning"
        elif 12 <= hour < 18:
            time_greeting = "Good afternoon"
        else:
            time_greeting = "Good evening"
        
        greetings = {
            "parking": f"{time_greeting}, this is Captain Anderson. I'll be your guide to the airport today. "
                      f"Let's get you parked and to your gate with time to spare.",
            
            "dropoff": f"{time_greeting}, Captain Anderson here. I'll navigate you safely to the departure terminal. "
                      f"Weather conditions look favorable for your approach.",
            
            "pickup": f"Captain Anderson at your service. I'll guide you to the arrival pickup area. "
                     f"We'll monitor the flight status and get you in position at the perfect time.",
            
            "return": f"Welcome back! Captain Anderson here to guide you home. "
                     f"Hope you had a pleasant flight."
        }
        
        return greetings.get(journey_type, f"{time_greeting}, this is Captain Anderson, ready to assist with your airport journey.")
    
    def format_time_announcement(self, time: datetime) -> str:
        """Format time in aviation style."""
        # Aviation uses 24-hour time
        return time.strftime("%H%M hours")
    
    def get_parking_instructions(self, parking_type: str, airport_code: str) -> str:
        """Get captain-style parking instructions."""
        instructions = {
            "economy": (
                "We'll be proceeding to Economy Parking. "
                "After parking, note your location and catch the shuttle at the designated stops. "
                "Shuttles run on a regular schedule, approximately every 10 minutes."
            ),
            "garage": (
                "Proceeding to the parking garage for direct terminal access. "
                "Follow signs to your terminal level. Elevators and escalators are available."
            ),
            "valet": (
                "Valet service coming up at the departure level. "
                "Pull up to the valet stand, they'll handle your vehicle from there. "
                "Keep your claim ticket secure."
            )
        }
        
        return instructions.get(parking_type, "Follow airport signage to your designated parking area.")
    
    def get_traffic_update(self, delay_minutes: int = 0) -> str:
        """Provide traffic update in captain style."""
        if delay_minutes == 0:
            return "We're experiencing smooth traffic conditions. Maintaining our scheduled arrival time."
        elif delay_minutes < 10:
            return f"Minor traffic ahead, adding approximately {delay_minutes} minutes to our journey. Nothing to concern yourself with."
        else:
            return f"We're encountering some congestion, adjusting arrival time by {delay_minutes} minutes. Still plenty of time before your flight."
    
    def get_departure_announcement(self, departure_time: datetime, destination: str) -> str:
        """Create departure announcement."""
        return (
            f"This is your captain speaking. We're preparing for departure to {destination} "
            f"at {self.format_time_announcement(departure_time)}. "
            f"Please ensure you have your travel documents ready and all necessary items for your journey. "
            f"Weather conditions at our destination look favorable."
        )
    
    def get_security_checkpoint_advice(self, wait_time: int, has_precheck: bool) -> str:
        """Provide security checkpoint guidance."""
        if has_precheck:
            if wait_time < 10:
                return "TSA PreCheck is showing minimal wait time. You'll breeze right through."
            else:
                return f"PreCheck showing {wait_time} minutes. Still faster than standard screening."
        else:
            if wait_time < 20:
                return f"Security checkpoint is moving smoothly, approximately {wait_time} minutes."
            else:
                return (
                    f"Security wait is currently {wait_time} minutes. "
                    f"I recommend using this time to organize your documents and prepare for screening."
                )
    
    def get_flight_status_update(self, flight_status: Dict) -> str:
        """Provide flight status in captain style."""
        status = flight_status.get("status", "scheduled")
        
        updates = {
            "scheduled": "Flight is on schedule for on-time departure.",
            "delayed": f"Flight is experiencing a {flight_status.get('delay_minutes', 0)} minute delay. Adjust your timing accordingly.",
            "boarding": "Flight is now boarding. Passengers should proceed to the gate.",
            "departed": "Flight has departed.",
            "cancelled": "I regret to inform you the flight has been cancelled. Please contact your airline for rebooking."
        }
        
        return updates.get(status, "Checking current flight status.")
    
    def get_arrival_guidance(self, terminal: str, gate: str = None) -> str:
        """Guide to arrival area."""
        guidance = f"Approaching Terminal {terminal}. "
        
        if gate:
            guidance += f"Your party will be arriving at Gate {gate}. "
        
        guidance += "Follow signs to Arrivals and baggage claim. I'll guide you to the pickup area."
        
        return guidance
    
    def get_weather_briefing(self, weather: Dict) -> str:
        """Provide weather briefing in aviation style."""
        temp = weather.get("temperature", 70)
        conditions = weather.get("conditions", "clear")
        
        briefing = f"Current weather at the airport: {conditions}, temperature {temp} degrees. "
        
        if "rain" in conditions.lower():
            briefing += "Expect wet conditions, drive with extra caution. "
        elif "snow" in conditions.lower():
            briefing += "Winter conditions present, allow extra time for your journey. "
        
        briefing += "Visibility is good for driving."
        
        return briefing
    
    def get_farewell_message(self, journey_type: str) -> str:
        """Get appropriate farewell message."""
        farewells = {
            "parking": (
                "You're all set for departure. Have a safe and pleasant flight. "
                "Thank you for flying with us today."
            ),
            "dropoff": (
                "Arriving at the departure area. Wishing your passenger a smooth journey. "
                "Safe travels."
            ),
            "pickup": (
                "That concludes our airport navigation. "
                "Welcome your passenger back and have a safe journey home."
            ),
            "return": (
                "Welcome home! This is Captain Anderson signing off. "
                "Hope you enjoyed your travels."
            )
        }
        
        return farewells.get(journey_type, "This is your captain signing off. Safe travels!")
    
    def should_activate(self, context: Dict) -> bool:
        """Determine if captain personality should activate."""
        # Activate for any airport-related journey
        destination = context.get("destination", "").lower()
        origin = context.get("origin", "").lower()
        
        airport_keywords = ["airport", "terminal", "flight", "flying", "lax", "sfo", "jfk", "ord"]
        
        return any(keyword in destination for keyword in airport_keywords) or \
               any(keyword in origin for keyword in airport_keywords) or \
               context.get("journey_type") in ["parking", "pickup", "dropoff", "return"] or \
               context.get("is_airport_journey", False)


# Singleton instance
captain_personality = CaptainPersonality()


def register_captain_personality(personality_engine):
    """Register the captain personality with the personality engine."""
    personality_engine.add_personality(captain_personality)
    
    # Set activation rules
    personality_engine.add_activation_rule(
        "airport_detection",
        lambda context: captain_personality.should_activate(context),
        captain_personality.id
    )
    
    logger.info("Captain personality registered for airport journeys")