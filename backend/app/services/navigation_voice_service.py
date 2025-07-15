"""
Navigation Voice Service - Turn-by-turn voice guidance
Integrates with Master Orchestration Agent for intelligent coordination
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from ..models.directions import RouteStep, RouteLeg, Route
from ..services.tts_service import TTSSynthesizer
from ..core.cache import cache_manager

logger = logging.getLogger(__name__)


class NavigationPriority(Enum):
    """Priority levels for navigation instructions"""
    CRITICAL = "critical"  # Immediate turns, exits
    HIGH = "high"         # Upcoming maneuvers
    MEDIUM = "medium"     # Distance updates
    LOW = "low"           # General guidance


class ManeuverType(Enum):
    """Types of navigation maneuvers"""
    TURN_LEFT = "turn-left"
    TURN_RIGHT = "turn-right"
    SHARP_LEFT = "turn-sharp-left"
    SHARP_RIGHT = "turn-sharp-right"
    SLIGHT_LEFT = "turn-slight-left"
    SLIGHT_RIGHT = "turn-slight-right"
    STRAIGHT = "straight"
    MERGE = "merge"
    RAMP_LEFT = "ramp-left"
    RAMP_RIGHT = "ramp-right"
    FORK_LEFT = "fork-left"
    FORK_RIGHT = "fork-right"
    ROUNDABOUT = "roundabout"
    UTURN = "uturn"
    EXIT = "exit"
    ARRIVE = "arrive"


@dataclass
class NavigationInstruction:
    """Structured navigation instruction ready for voice synthesis"""
    text: str
    priority: NavigationPriority
    timing: str  # "immediate", "500ft", "1mi", etc.
    maneuver_type: Optional[ManeuverType]
    street_name: Optional[str]
    exit_number: Optional[str]
    audio_cues: Dict[str, Any]  # Spatial audio, alerts
    requires_story_pause: bool
    estimated_duration: float  # seconds


@dataclass
class NavigationContext:
    """Current navigation state for intelligent orchestration"""
    current_step_index: int
    distance_to_next_maneuver: float  # meters
    time_to_next_maneuver: float  # seconds
    current_speed: float  # km/h
    is_on_highway: bool
    approaching_complex_intersection: bool
    story_playing: bool
    last_instruction_time: Optional[datetime]


class NavigationVoiceService:
    """
    Converts route data into intelligent voice navigation instructions
    Coordinates with Master Orchestration Agent for seamless integration
    """
    
    def __init__(self):
        self.tts_service = TTSSynthesizer()
        
        # Distance thresholds for instruction timing (meters)
        self.distance_thresholds = {
            'highway': {
                'initial': 3200,      # 2 miles
                'reminder': 1600,     # 1 mile
                'prepare': 800,       # 0.5 miles
                'immediate': 200      # 650 feet
            },
            'city': {
                'initial': 800,       # 0.5 miles
                'reminder': 400,      # 0.25 miles
                'prepare': 150,       # 500 feet
                'immediate': 50       # 165 feet
            }
        }
        
        # Voice personality for navigation (clear, authoritative)
        self.navigation_voice_config = {
            'voice_name': 'en-US-Neural2-J',  # Professional male voice
            'speaking_rate': 1.0,
            'pitch': 0,
            'volume_gain_db': 2.0  # Slightly louder for clarity
        }
        
        logger.info("Navigation Voice Service initialized")
    
    async def process_route_for_voice(
        self,
        route_data: Dict[str, Any],
        current_location: Dict[str, float],
        journey_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process route data to prepare voice navigation instructions
        Returns data for Master Orchestration Agent
        """
        try:
            # Extract all navigation steps from route data
            all_steps = []
            legs = route_data.get('legs', [])
            for leg_index, leg in enumerate(legs):
                for step in leg.get('steps', []):
                    all_steps.append({
                        'step': step,
                        'leg_index': leg_index
                    })
            
            # Analyze route characteristics
            route_analysis = self._analyze_route_characteristics(route_data)
            
            # Generate instruction templates
            instruction_templates = []
            for i, step_data in enumerate(all_steps):
                step = step_data['step']
                next_step = all_steps[i + 1]['step'] if i + 1 < len(all_steps) else None
                
                instructions = await self._generate_step_instructions(
                    step, 
                    next_step,
                    route_analysis
                )
                
                instruction_templates.append({
                    'step_index': i,
                    'instructions': instructions,
                    'maneuver': step.get('maneuver'),
                    'distance': step.get('distance', {}).get('value', 0),
                    'duration': step.get('duration', {}).get('value', 0)
                })
            
            # Prepare orchestration data
            orchestration_data = {
                'route_id': f"route_{datetime.now().timestamp()}",
                'total_steps': len(all_steps),
                'instruction_templates': instruction_templates,
                'route_characteristics': route_analysis,
                'voice_config': self.navigation_voice_config,
                'coordination_rules': self._get_coordination_rules(journey_context),
                'estimated_voice_events': self._estimate_voice_events(instruction_templates)
            }
            
            # Cache for quick access during navigation
            await cache_manager.set(
                f"nav_voice:{orchestration_data['route_id']}",
                orchestration_data,
                expire=86400  # 24 hours
            )
            
            return orchestration_data
            
        except Exception as e:
            logger.error(f"Error processing route for voice: {e}")
            raise
    
    async def get_current_instruction(
        self,
        navigation_context: NavigationContext,
        orchestration_state: Dict[str, Any]
    ) -> Optional[NavigationInstruction]:
        """
        Get the appropriate navigation instruction for current position
        Coordinates with orchestration state (story playing, etc.)
        """
        try:
            # Get cached route data
            route_data = await cache_manager.get(f"nav_voice:{orchestration_state.get('route_id')}")
            if not route_data:
                logger.error("No cached navigation data found")
                return None
            
            # Get current step instructions
            current_templates = route_data['instruction_templates'][navigation_context.current_step_index]
            
            # Determine which instruction to give based on distance
            instruction = self._select_instruction_by_distance(
                current_templates['instructions'],
                navigation_context.distance_to_next_maneuver,
                navigation_context.is_on_highway
            )
            
            if not instruction:
                return None
            
            # Check orchestration rules
            if not self._should_speak_now(instruction, navigation_context, orchestration_state):
                return None
            
            # Enhance instruction with context
            enhanced_instruction = self._enhance_instruction_with_context(
                instruction,
                navigation_context,
                orchestration_state
            )
            
            return enhanced_instruction
            
        except Exception as e:
            logger.error(f"Error getting current instruction: {e}")
            return None
    
    async def generate_voice_audio(
        self,
        instruction: NavigationInstruction,
        personality_override: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate voice audio for navigation instruction
        Can override voice personality for special situations
        """
        try:
            # Use navigation voice or personality override
            voice_config = personality_override or self.navigation_voice_config
            
            # Add SSML markup for better pronunciation
            ssml_text = self._create_ssml_instruction(instruction)
            
            # Generate audio
            audio_url = self.tts_service.synthesize_and_upload(
                text=ssml_text,  # Use SSML version
                voice_name=voice_config['voice_name'],
                language_code='en-US'
            )
            
            return {
                'audio_url': audio_url,
                'duration': instruction.estimated_duration,
                'instruction': instruction,
                'metadata': {
                    'priority': instruction.priority.value,
                    'requires_story_pause': instruction.requires_story_pause,
                    'audio_cues': instruction.audio_cues
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating voice audio: {e}")
            raise
    
    def _analyze_route_characteristics(self, route_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze route to understand its characteristics"""
        legs = route_data.get('legs', [])
        total_distance = sum(leg.get('distance', {}).get('value', 0) for leg in legs)
        highway_distance = 0
        city_distance = 0
        complex_intersections = 0
        
        for leg in legs:
            for step in leg.get('steps', []):
                step_distance = step.get('distance', {}).get('value', 0)
                instructions = step.get('html_instructions', '').lower()
                
                # Detect highway driving
                if any(keyword in instructions 
                      for keyword in ['highway', 'freeway', 'interstate', 'i-']):
                    highway_distance += step_distance
                else:
                    city_distance += step_distance
                
                # Detect complex maneuvers
                maneuver = step.get('maneuver', '')
                if maneuver and any(complex in maneuver 
                                  for complex in ['roundabout', 'fork', 'merge']):
                    complex_intersections += 1
        
        return {
            'total_distance_km': total_distance / 1000,
            'highway_percentage': (highway_distance / total_distance * 100) if total_distance > 0 else 0,
            'city_percentage': (city_distance / total_distance * 100) if total_distance > 0 else 0,
            'complex_intersections': complex_intersections,
            'estimated_duration_minutes': sum(leg.get('duration', {}).get('value', 0) for leg in legs) / 60
        }
    
    async def _generate_step_instructions(
        self,
        step: Dict[str, Any],
        next_step: Optional[Dict[str, Any]],
        route_analysis: Dict[str, Any]
    ) -> List[NavigationInstruction]:
        """Generate multiple instruction variants for a single step"""
        instructions = []
        
        # Parse the HTML instructions
        html_instructions = step.get('html_instructions', '')
        plain_instruction = self._strip_html(html_instructions)
        street_name = self._extract_street_name(plain_instruction)
        exit_number = self._extract_exit_number(plain_instruction)
        
        # Determine maneuver type
        maneuver_type = self._parse_maneuver_type(step.get('maneuver'))
        
        # Generate instruction variants
        
        # 1. Initial announcement (2 miles / 0.5 miles)
        initial_text = self._create_initial_instruction(
            maneuver_type, street_name, exit_number, plain_instruction
        )
        instructions.append(NavigationInstruction(
            text=initial_text,
            priority=NavigationPriority.MEDIUM,
            timing="initial",
            maneuver_type=maneuver_type,
            street_name=street_name,
            exit_number=exit_number,
            audio_cues={'tone': 'navigation_chime'},
            requires_story_pause=False,
            estimated_duration=self._estimate_speech_duration(initial_text)
        ))
        
        # 2. Reminder (1 mile / 0.25 miles)
        reminder_text = self._create_reminder_instruction(
            maneuver_type, street_name, exit_number
        )
        instructions.append(NavigationInstruction(
            text=reminder_text,
            priority=NavigationPriority.HIGH,
            timing="reminder",
            maneuver_type=maneuver_type,
            street_name=street_name,
            exit_number=exit_number,
            audio_cues={'tone': 'navigation_chime', 'volume_boost': 2},
            requires_story_pause=True,
            estimated_duration=self._estimate_speech_duration(reminder_text)
        ))
        
        # 3. Prepare instruction (500 feet / 165 feet)
        prepare_text = self._create_prepare_instruction(
            maneuver_type, street_name, exit_number
        )
        instructions.append(NavigationInstruction(
            text=prepare_text,
            priority=NavigationPriority.CRITICAL,
            timing="prepare",
            maneuver_type=maneuver_type,
            street_name=street_name,
            exit_number=exit_number,
            audio_cues={'tone': 'navigation_alert', 'volume_boost': 3},
            requires_story_pause=True,
            estimated_duration=self._estimate_speech_duration(prepare_text)
        ))
        
        # 4. Immediate instruction (200 feet / 50 feet)
        immediate_text = self._create_immediate_instruction(maneuver_type)
        instructions.append(NavigationInstruction(
            text=immediate_text,
            priority=NavigationPriority.CRITICAL,
            timing="immediate",
            maneuver_type=maneuver_type,
            street_name=None,  # Keep it short
            exit_number=None,
            audio_cues={'tone': 'navigation_urgent', 'volume_boost': 5},
            requires_story_pause=True,
            estimated_duration=self._estimate_speech_duration(immediate_text)
        ))
        
        # 5. Confirmation (after maneuver)
        if next_step:
            next_distance_text = next_step.get('distance', {}).get('text', '')
            confirm_text = self._create_confirmation_instruction(
                street_name, next_distance_text
            )
            instructions.append(NavigationInstruction(
                text=confirm_text,
                priority=NavigationPriority.LOW,
                timing="confirmation",
                maneuver_type=None,
                street_name=street_name,
                exit_number=None,
                audio_cues={'tone': 'navigation_confirm'},
                requires_story_pause=False,
                estimated_duration=self._estimate_speech_duration(confirm_text)
            ))
        
        return instructions
    
    def _strip_html(self, html_text: str) -> str:
        """Remove HTML tags from instruction text"""
        # Remove HTML tags
        clean = re.compile('<.*?>')
        text = re.sub(clean, '', html_text)
        # Clean up whitespace
        text = ' '.join(text.split())
        return text
    
    def _extract_street_name(self, instruction: str) -> Optional[str]:
        """Extract street name from instruction"""
        # Common patterns for street names
        patterns = [
            r'onto\s+(.+?)(?:\s+toward|$)',
            r'on\s+(.+?)(?:\s+toward|$)',
            r'to\s+(.+?)(?:\s+toward|$)',
            r'toward\s+(.+?)$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, instruction, re.IGNORECASE)
            if match:
                street = match.group(1).strip()
                # Clean up common suffixes
                street = re.sub(r'\s*\([^)]*\)$', '', street)  # Remove parentheses
                return street
        
        return None
    
    def _extract_exit_number(self, instruction: str) -> Optional[str]:
        """Extract exit number from instruction"""
        # Match patterns like "exit 42" or "exit 42A"
        match = re.search(r'exit\s+(\d+[A-Z]?)', instruction, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
    def _parse_maneuver_type(self, maneuver: Optional[str]) -> Optional[ManeuverType]:
        """Parse maneuver string into enum"""
        if not maneuver:
            return None
        
        maneuver_map = {
            'turn-left': ManeuverType.TURN_LEFT,
            'turn-right': ManeuverType.TURN_RIGHT,
            'turn-sharp-left': ManeuverType.SHARP_LEFT,
            'turn-sharp-right': ManeuverType.SHARP_RIGHT,
            'turn-slight-left': ManeuverType.SLIGHT_LEFT,
            'turn-slight-right': ManeuverType.SLIGHT_RIGHT,
            'straight': ManeuverType.STRAIGHT,
            'merge': ManeuverType.MERGE,
            'ramp-left': ManeuverType.RAMP_LEFT,
            'ramp-right': ManeuverType.RAMP_RIGHT,
            'fork-left': ManeuverType.FORK_LEFT,
            'fork-right': ManeuverType.FORK_RIGHT,
            'roundabout': ManeuverType.ROUNDABOUT,
            'uturn': ManeuverType.UTURN,
            'exit': ManeuverType.EXIT,
            'arrive': ManeuverType.ARRIVE
        }
        
        return maneuver_map.get(maneuver)
    
    def _create_initial_instruction(
        self,
        maneuver: Optional[ManeuverType],
        street: Optional[str],
        exit_num: Optional[str],
        full_instruction: str
    ) -> str:
        """Create initial navigation announcement"""
        if exit_num:
            return f"In 2 miles, take exit {exit_num}"
        elif maneuver == ManeuverType.TURN_LEFT:
            return f"In half a mile, turn left{' onto ' + street if street else ''}"
        elif maneuver == ManeuverType.TURN_RIGHT:
            return f"In half a mile, turn right{' onto ' + street if street else ''}"
        else:
            # Fallback to cleaned instruction
            return full_instruction
    
    def _create_reminder_instruction(
        self,
        maneuver: Optional[ManeuverType],
        street: Optional[str],
        exit_num: Optional[str]
    ) -> str:
        """Create reminder instruction"""
        if exit_num:
            return f"Exit {exit_num} in 1 mile"
        elif maneuver == ManeuverType.TURN_LEFT:
            return f"Turn left{' onto ' + street if street else ''} in a quarter mile"
        elif maneuver == ManeuverType.TURN_RIGHT:
            return f"Turn right{' onto ' + street if street else ''} in a quarter mile"
        else:
            return "Prepare for your next turn"
    
    def _create_prepare_instruction(
        self,
        maneuver: Optional[ManeuverType],
        street: Optional[str],
        exit_num: Optional[str]
    ) -> str:
        """Create preparation instruction"""
        if exit_num:
            return f"Take exit {exit_num} on the right"
        elif maneuver == ManeuverType.TURN_LEFT:
            return f"Prepare to turn left{' onto ' + street if street else ''}"
        elif maneuver == ManeuverType.TURN_RIGHT:
            return f"Prepare to turn right{' onto ' + street if street else ''}"
        else:
            return "Turn ahead"
    
    def _create_immediate_instruction(self, maneuver: Optional[ManeuverType]) -> str:
        """Create immediate/urgent instruction"""
        if maneuver == ManeuverType.TURN_LEFT:
            return "Turn left now"
        elif maneuver == ManeuverType.TURN_RIGHT:
            return "Turn right now"
        elif maneuver == ManeuverType.EXIT:
            return "Take the exit now"
        else:
            return "Turn now"
    
    def _create_confirmation_instruction(
        self,
        street: Optional[str],
        next_distance: str
    ) -> str:
        """Create post-maneuver confirmation"""
        if street:
            return f"Continue on {street} for {next_distance}"
        else:
            return f"Continue for {next_distance}"
    
    def _select_instruction_by_distance(
        self,
        instructions: List[NavigationInstruction],
        distance_meters: float,
        is_highway: bool
    ) -> Optional[NavigationInstruction]:
        """Select appropriate instruction based on distance"""
        thresholds = self.distance_thresholds['highway' if is_highway else 'city']
        
        # Find the right instruction for current distance
        if distance_meters <= thresholds['immediate']:
            return next((i for i in instructions if i.timing == 'immediate'), None)
        elif distance_meters <= thresholds['prepare']:
            return next((i for i in instructions if i.timing == 'prepare'), None)
        elif distance_meters <= thresholds['reminder']:
            return next((i for i in instructions if i.timing == 'reminder'), None)
        elif distance_meters <= thresholds['initial']:
            return next((i for i in instructions if i.timing == 'initial'), None)
        
        return None
    
    def _should_speak_now(
        self,
        instruction: NavigationInstruction,
        nav_context: NavigationContext,
        orch_state: Dict[str, Any]
    ) -> bool:
        """Determine if instruction should be spoken based on orchestration state"""
        # Always speak critical instructions
        if instruction.priority == NavigationPriority.CRITICAL:
            return True
        
        # Check if enough time has passed since last instruction
        if nav_context.last_instruction_time:
            time_since_last = (datetime.now() - nav_context.last_instruction_time).total_seconds()
            min_interval = 10 if instruction.priority == NavigationPriority.HIGH else 30
            if time_since_last < min_interval:
                return False
        
        # Check story state
        if nav_context.story_playing and not instruction.requires_story_pause:
            # Only interrupt story for high priority
            if instruction.priority == NavigationPriority.LOW:
                return False
        
        # Check if we're in a complex situation
        if nav_context.approaching_complex_intersection:
            # Be more verbose in complex situations
            return True
        
        return True
    
    def _enhance_instruction_with_context(
        self,
        instruction: NavigationInstruction,
        nav_context: NavigationContext,
        orch_state: Dict[str, Any]
    ) -> NavigationInstruction:
        """Enhance instruction based on current context"""
        # Add speed-based timing adjustments
        if nav_context.current_speed < 30:  # Slow speed, city driving
            instruction.audio_cues['speaking_rate'] = 1.1  # Speak slightly faster
        elif nav_context.current_speed > 100:  # Highway speed
            instruction.audio_cues['speaking_rate'] = 0.9  # Speak slightly slower
        
        # Add spatial audio cues for turns
        if instruction.maneuver_type:
            if 'left' in instruction.maneuver_type.value:
                instruction.audio_cues['spatial_position'] = 'left'
            elif 'right' in instruction.maneuver_type.value:
                instruction.audio_cues['spatial_position'] = 'right'
        
        # Adjust for story context
        if nav_context.story_playing and instruction.requires_story_pause:
            instruction.audio_cues['pre_announcement'] = 'gentle_fade'
            instruction.audio_cues['post_announcement'] = 'gentle_resume'
        
        return instruction
    
    def _create_ssml_instruction(self, instruction: NavigationInstruction) -> str:
        """Create SSML markup for better pronunciation"""
        ssml_parts = ['<speak>']
        
        # Add appropriate emphasis and pauses
        text = instruction.text
        
        # Emphasize direction words
        text = re.sub(r'\b(left|right|straight)\b', r'<emphasis level="strong">\1</emphasis>', text, flags=re.IGNORECASE)
        
        # Add pauses before numbers
        text = re.sub(r'(\d+)', r'<break time="200ms"/>\1', text)
        
        # Spell out exit numbers
        text = re.sub(r'exit (\d+)([A-Z]?)', r'exit <say-as interpret-as="number">\1</say-as>\2', text, flags=re.IGNORECASE)
        
        ssml_parts.append(text)
        ssml_parts.append('</speak>')
        
        return ''.join(ssml_parts)
    
    def _estimate_speech_duration(self, text: str) -> float:
        """Estimate how long the instruction will take to speak"""
        # Rough estimate: 150 words per minute
        word_count = len(text.split())
        return (word_count / 150) * 60 + 0.5  # Add 0.5s padding
    
    def _get_coordination_rules(self, journey_context: Dict[str, Any]) -> Dict[str, Any]:
        """Get rules for coordinating with other audio"""
        return {
            'story_pause_threshold': NavigationPriority.HIGH.value,
            'music_duck_threshold': NavigationPriority.MEDIUM.value,
            'voice_overlap_allowed': False,
            'min_instruction_gap_seconds': 10,
            'complex_intersection_verbosity': 'high',
            'highway_verbosity': 'medium',
            'city_verbosity': 'high',
            'user_preferences': journey_context.get('navigation_preferences', {})
        }
    
    def _estimate_voice_events(
        self,
        instruction_templates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Estimate when voice events will occur for orchestration planning"""
        events = []
        cumulative_distance = 0
        
        for template in instruction_templates:
            step_distance = template['distance']
            
            # Estimate events for this step
            for instruction in template['instructions']:
                event_distance = cumulative_distance + self._get_instruction_trigger_distance(
                    instruction['timing'],
                    step_distance
                )
                
                events.append({
                    'distance_meters': event_distance,
                    'instruction_type': instruction['timing'],
                    'priority': instruction['priority'].value,
                    'estimated_duration': instruction['estimated_duration'],
                    'requires_story_pause': instruction['requires_story_pause']
                })
            
            cumulative_distance += step_distance
        
        return events
    
    def _get_instruction_trigger_distance(self, timing: str, step_distance: float) -> float:
        """Calculate when to trigger instruction relative to maneuver"""
        # Work backwards from the maneuver point
        if timing == 'immediate':
            return step_distance - 50  # 50m before
        elif timing == 'prepare':
            return step_distance - 200  # 200m before
        elif timing == 'reminder':
            return step_distance - 800  # 800m before
        elif timing == 'initial':
            return step_distance - 2000  # 2km before
        else:  # confirmation
            return step_distance + 50  # 50m after
        
        return step_distance


# Create singleton instance
navigation_voice_service = NavigationVoiceService()