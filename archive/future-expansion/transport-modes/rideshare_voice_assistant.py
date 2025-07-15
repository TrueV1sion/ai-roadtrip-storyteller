"""
Rideshare Voice Assistant
Simplified voice commands and safety-first interactions for rideshare mode
"""
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import asyncio

from ..core.logger import get_logger
from ..core.ai_client import ai_client
from .voice_safety_validator import voice_safety_validator
from .rideshare_mode_manager import rideshare_mode_manager, RideshareUserType

logger = get_logger(__name__)


class RideshareVoiceAssistant:
    """Specialized voice assistant for rideshare scenarios"""
    
    # Simplified command set for drivers
    DRIVER_COMMANDS = {
        "find gas": "locate_fuel",
        "gas station": "locate_fuel",
        "need gas": "locate_fuel",
        "find food": "find_quick_food",
        "quick food": "find_quick_food",
        "hungry": "find_quick_food",
        "take break": "suggest_break",
        "need break": "suggest_break",
        "rest stop": "suggest_break",
        "best spot": "optimal_waiting",
        "where wait": "optimal_waiting",
        "earnings": "show_earnings",
        "how much made": "show_earnings",
        "end shift": "end_driving_session"
    }
    
    # Entertainment commands for passengers
    PASSENGER_COMMANDS = {
        "play game": "start_game",
        "trivia": "start_trivia",
        "tell story": "tell_story",
        "play music": "play_music",
        "how long": "trip_duration",
        "are we there": "trip_status",
        "local facts": "local_trivia"
    }
    
    def __init__(self):
        self.active_sessions: Dict[int, Dict[str, Any]] = {}
        self.command_history: Dict[int, List[Tuple[str, datetime]]] = {}
        
    async def process_rideshare_command(
        self,
        user_id: int,
        voice_input: str,
        mode: RideshareUserType,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process voice commands with rideshare-specific handling"""
        try:
            # Safety check for drivers
            if mode == RideshareUserType.DRIVER:
                is_safe = await self._check_driver_safety(context)
                if not is_safe:
                    return {
                        "response": "Please wait until you're stopped safely.",
                        "action": "safety_warning",
                        "speak": True
                    }
            
            # Normalize and match command
            command_key = self._match_command(voice_input.lower(), mode)
            
            if not command_key:
                return await self._handle_general_query(
                    voice_input, mode, context
                )
            
            # Execute command
            if mode == RideshareUserType.DRIVER:
                return await self._execute_driver_command(
                    user_id, command_key, context
                )
            else:
                return await self._execute_passenger_command(
                    user_id, command_key, context
                )
                
        except Exception as e:
            logger.error(f"Error processing rideshare command: {e}")
            return {
                "response": "Sorry, I couldn't process that. Try again.",
                "action": "error",
                "speak": True
            }
    
    def _match_command(
        self,
        input_text: str,
        mode: RideshareUserType
    ) -> Optional[str]:
        """Match input to simplified command set"""
        commands = (self.DRIVER_COMMANDS if mode == RideshareUserType.DRIVER 
                   else self.PASSENGER_COMMANDS)
        
        # Look for keyword matches
        for keyword, command in commands.items():
            if keyword in input_text:
                return command
                
        return None
    
    async def _check_driver_safety(self, context: Dict[str, Any]) -> bool:
        """Enhanced safety check for driver mode"""
        speed = context.get("vehicle_speed", 0)
        is_moving = context.get("is_moving", False)
        
        # Very strict for drivers - only when stopped
        if is_moving or speed > 5:
            return False
            
        return True
    
    async def _execute_driver_command(
        self,
        user_id: int,
        command: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute driver-specific commands"""
        
        if command == "locate_fuel":
            return await self._find_nearest_gas(context)
            
        elif command == "find_quick_food":
            return await self._find_quick_food(context)
            
        elif command == "suggest_break":
            return await self._suggest_break_spot(context)
            
        elif command == "optimal_waiting":
            return await self._find_optimal_waiting(context)
            
        elif command == "show_earnings":
            return await self._show_earnings_summary(user_id)
            
        elif command == "end_driving_session":
            return await self._end_driving_session(user_id)
            
        return {
            "response": "Command not recognized",
            "action": "unknown",
            "speak": True
        }
    
    async def _execute_passenger_command(
        self,
        user_id: int,
        command: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute passenger entertainment commands"""
        
        if command == "start_trivia":
            return await self._start_trivia_game(user_id, context)
            
        elif command == "tell_story":
            return await self._tell_short_story(context)
            
        elif command == "play_music":
            return await self._suggest_music(user_id)
            
        elif command == "trip_duration":
            return await self._estimate_arrival(context)
            
        elif command == "local_trivia":
            return await self._share_local_facts(context)
            
        return {
            "response": "What would you like to do?",
            "action": "unknown",
            "speak": True
        }
    
    async def _find_nearest_gas(
        self,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Find nearest gas station"""
        # Would integrate with maps API
        return {
            "response": "Shell station 0.8 miles ahead on your right. " +
                       "Current price $3.49 per gallon.",
            "action": "navigate_gas",
            "data": {
                "station": "Shell",
                "distance": 0.8,
                "price": 3.49,
                "direction": "right"
            },
            "speak": True,
            "quick_actions": ["Navigate there", "Find cheaper"]
        }
    
    async def _find_quick_food(
        self,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Find quick food options"""
        return {
            "response": "McDonald's drive-thru 0.5 miles ahead. " +
                       "Chipotle 1.2 miles. Which do you prefer?",
            "action": "food_options",
            "data": {
                "options": [
                    {"name": "McDonald's", "distance": 0.5, "type": "drive-thru"},
                    {"name": "Chipotle", "distance": 1.2, "type": "quick-serve"}
                ]
            },
            "speak": True,
            "quick_actions": ["McDonald's", "Chipotle", "Other options"]
        }
    
    async def _suggest_break_spot(
        self,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Suggest break locations"""
        spots = await rideshare_mode_manager.suggest_break_locations(
            context.get("location", {}),
            {}
        )
        
        if spots:
            top_spot = spots[0]
            return {
                "response": f"{top_spot['name']} is {top_spot['distance']} away. " +
                           f"Has {', '.join(top_spot['amenities'][:2])}.",
                "action": "break_suggestion",
                "data": {"spots": spots},
                "speak": True,
                "quick_actions": ["Navigate", "Other options"]
            }
            
        return {
            "response": "No good break spots nearby. Try in a few minutes.",
            "action": "no_breaks",
            "speak": True
        }
    
    async def _show_earnings_summary(
        self,
        user_id: int
    ) -> Dict[str, Any]:
        """Show driver earnings summary"""
        stats = await rideshare_mode_manager.track_driver_earnings(
            user_id,
            {"earnings": 0}  # Just get current stats
        )
        
        return {
            "response": f"You've earned ${stats.get('total_earnings', 0):.2f} " +
                       f"from {stats.get('trips_completed', 0)} trips. " +
                       f"Hourly rate: ${stats.get('hourly_rate', 0):.2f}",
            "action": "earnings_summary",
            "data": stats,
            "speak": True
        }
    
    async def _start_trivia_game(
        self,
        user_id: int,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Start a quick trivia game for passengers"""
        # Generate contextual trivia
        location = context.get("location", {})
        
        trivia_prompt = f"""Generate a fun trivia question suitable for a rideshare passenger.
        Make it engaging but not too difficult. Current area: {location.get('city', 'Unknown')}.
        Return: question, 4 options (A-D), correct answer letter, fun fact."""
        
        trivia = await ai_client.generate(trivia_prompt)
        
        return {
            "response": trivia.get("question", "What's the capital of California?"),
            "action": "trivia_question",
            "data": {
                "options": trivia.get("options", ["Sacramento", "Los Angeles", "San Francisco", "San Diego"]),
                "correct": trivia.get("correct", "A"),
                "fact": trivia.get("fact", "Sacramento became the capital in 1854!")
            },
            "speak": True
        }
    
    async def _tell_short_story(
        self,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Tell a short entertaining story"""
        # Generate a 3-5 minute story
        story_prompt = """Create a short, entertaining story (3-5 minutes reading time) 
        suitable for a rideshare passenger. Make it engaging with a twist ending.
        Topics: mystery, comedy, or inspiring. Keep it PG-rated."""
        
        story = await ai_client.generate(story_prompt)
        
        return {
            "response": story.get("text", "Let me tell you about the time..."),
            "action": "story",
            "data": {
                "title": story.get("title", "The Mysterious Passenger"),
                "duration": "5 minutes"
            },
            "speak": True
        }
    
    async def _handle_general_query(
        self,
        query: str,
        mode: RideshareUserType,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle queries that don't match commands"""
        # Generate contextual response
        prompt = f"""User ({mode.value}) asked: "{query}"
        Context: {context}
        Provide a helpful, concise response appropriate for rideshare {mode.value}.
        Keep it under 2 sentences."""
        
        response = await ai_client.generate(prompt)
        
        return {
            "response": response.get("text", "I can help with that."),
            "action": "general_response",
            "speak": True
        }
    
    def get_driver_voice_prompts(self) -> List[str]:
        """Get example voice prompts for drivers"""
        return [
            "Find gas",
            "Quick food nearby",
            "Take a break",
            "Where should I wait?",
            "Show my earnings",
            "End shift"
        ]
    
    def get_passenger_voice_prompts(self) -> List[str]:
        """Get example voice prompts for passengers"""
        return [
            "Play trivia",
            "Tell me a story",
            "Play some music",
            "How long until we arrive?",
            "Tell me about this area"
        ]


# Global instance
rideshare_voice_assistant = RideshareVoiceAssistant()