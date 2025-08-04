"""
Master Orchestration Agent - Central coordination for all user interactions

This agent maintains the primary user interface while coordinating with specialized 
sub-agents behind the scenes. The user always communicates with this single agent,
creating a seamless, conversational experience.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from ..core.unified_ai_client import UnifiedAIClient
from ..models.user import User
from ..models.story import Story
from .story_generation_agent import StoryGenerationAgent
from .booking_agent import BookingAgent
from .navigation_agent import NavigationAgent
from .navigation_voice_service import navigation_voice_service
from .contextual_awareness_agent import ContextualAwarenessAgent
from .local_expert_agent import LocalExpertAgent
from .spatial_audio_engine import spatial_audio_engine, AudioEnvironment, SoundSource, SpatialAudioSource, AudioPosition
from .story_timing_orchestrator import StoryTimingOrchestrator, TimingContext, JourneyPhase, DrivingComplexity
from .passenger_engagement_tracker import PassengerEngagementTracker, EngagementEventType

logger = logging.getLogger(__name__)

# Try to import metrics, but make it optional
try:
    from app.monitoring.metrics import metrics
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    logger.warning("Metrics not available - metrics recording disabled")


class IntentType(Enum):
    STORY_REQUEST = "story_request"
    BOOKING_INQUIRY = "booking_inquiry"
    NAVIGATION_HELP = "navigation_help"
    NAVIGATION_VOICE = "navigation_voice"  # Turn-by-turn voice navigation
    GENERAL_CHAT = "general_chat"
    COMPLEX_ASSISTANCE = "complex_assistance"


class UrgencyLevel(Enum):
    IMMEDIATE = "immediate"
    CAN_WAIT = "can_wait"
    BACKGROUND = "background"


@dataclass
class IntentAnalysis:
    primary_intent: IntentType
    secondary_intents: List[IntentType]
    required_agents: Dict[str, Dict[str, Any]]
    urgency: UrgencyLevel
    context_requirements: List[str]
    expected_response_type: str


@dataclass
class AgentTask:
    task_type: str
    parameters: Dict[str, Any]
    priority: int
    timeout_seconds: int


@dataclass
class AgentResponse:
    text: str
    audio_url: Optional[str]
    actions: List[Dict[str, Any]]
    booking_opportunities: List[Dict[str, Any]]
    conversation_state_updates: Dict[str, Any]
    requires_followup: bool = False


@dataclass
class JourneyContext:
    current_location: Dict[str, Any]
    current_time: datetime
    journey_stage: str
    passengers: List[Dict[str, Any]]
    vehicle_info: Dict[str, Any]
    weather: Dict[str, Any]
    route_info: Dict[str, Any]


class ConversationState:
    """Manages conversation context and history"""
    
    def __init__(self):
        self.message_history: List[Dict[str, Any]] = []
        self.active_topics: Dict[str, Any] = {}
        self.pending_actions: List[Dict[str, Any]] = []
        self.user_preferences: Dict[str, Any] = {}
        self.booking_context: Dict[str, Any] = {}
        
    def add_user_message(self, message: str, context: Dict[str, Any] = None):
        """Add user message to conversation history"""
        self.message_history.append({
            'timestamp': datetime.now(),
            'speaker': 'user',
            'content': message,
            'context': context or {}
        })
        self._clean_old_messages()
    
    def add_agent_message(self, response: AgentResponse):
        """Add agent response to conversation history"""
        self.message_history.append({
            'timestamp': datetime.now(),
            'speaker': 'agent',
            'content': response.text,
            'actions': response.actions,
            'booking_opportunities': response.booking_opportunities
        })
        
        if response.actions:
            self.pending_actions.extend(response.actions)
    
    def get_recent_context(self, lookback_minutes: int = 10) -> str:
        """Get recent conversation context for AI processing"""
        cutoff_time = datetime.now() - timedelta(minutes=lookback_minutes)
        recent_messages = [
            msg for msg in self.message_history 
            if msg['timestamp'] > cutoff_time
        ]
        
        context_lines = []
        for msg in recent_messages[-6:]:  # Last 3 exchanges
            speaker = "User" if msg['speaker'] == 'user' else "Guide"
            context_lines.append(f"{speaker}: {msg['content']}")
        
        return "\n".join(context_lines)
    
    def _clean_old_messages(self, max_messages: int = 50):
        """Keep conversation history manageable"""
        if len(self.message_history) > max_messages:
            self.message_history = self.message_history[-max_messages:]


class MasterOrchestrationAgent:
    """
    Central orchestrator for all user interactions.
    
    This agent maintains the primary conversation with users while coordinating
    specialized sub-agents behind the scenes. Users experience a single, coherent
    assistant personality.
    """
    
    def __init__(self, ai_client: UnifiedAIClient):
        self.ai_client = ai_client
        self.conversation_state = ConversationState()
        self.personality = "friendly_knowledgeable_guide"
        
        # Initialize sub-agents
        self.sub_agents = {
            'story': StoryGenerationAgent(ai_client),
            'booking': BookingAgent(ai_client),
            'navigation': NavigationAgent(),
            'context': ContextualAwarenessAgent(ai_client),
            'local_expert': LocalExpertAgent(ai_client)
        }
        
        # Navigation voice coordination state
        self.navigation_voice_state = {
            'active_route_id': None,
            'current_instruction_index': 0,
            'last_instruction_time': None,
            'voice_navigation_active': False
        }
        
        # Spatial audio state
        self.spatial_audio_state = {
            'environment': AudioEnvironment.RURAL,
            'active_soundscape': None,
            'story_position': AudioPosition(0, 0, 0.3),  # Slightly in front
            'navigation_position': AudioPosition(0, 0.2, 0.5),  # Front and slightly up
            'last_environment_update': None
        }
        
        # Initialize dynamic story timing system
        self.story_timing = StoryTimingOrchestrator()
        self.engagement_trackers = {}  # user_id -> PassengerEngagementTracker
        
        # Story timing state
        self.story_timing_state = {
            'last_story_time': None,
            'next_story_check_time': None,
            'stories_told_count': 0,
            'journey_start_time': None,
            'total_journey_distance': None,
            'last_timing_context': None
        }
        
        logger.info("Master Orchestration Agent initialized with dynamic story timing")
    
    async def process_user_input(self, user_input: str, context: JourneyContext, 
                               user: User) -> AgentResponse:
        """
        Main entry point for all user interactions.
        
        This method:
        1. Analyzes user intent
        2. Coordinates appropriate sub-agents
        3. Synthesizes a natural response
        4. Maintains conversation continuity
        """
        try:
            # Update conversation state
            self.conversation_state.add_user_message(user_input, {
                'location': context.current_location,
                'time': context.current_time.isoformat()
            })
            
            # Analyze what the user wants
            intent_analysis = await self._analyze_intent(user_input, context, user)
            
            # Coordinate with sub-agents (invisible to user)
            sub_agent_responses = await self._coordinate_sub_agents(
                intent_analysis, context, user
            )
            
            # Create natural, conversational response
            final_response = await self._synthesize_response(
                user_input, intent_analysis, sub_agent_responses, context
            )
            
            # Update conversation state
            self.conversation_state.add_agent_message(final_response)
            
            logger.info(f"Processed user input successfully: {intent_analysis.primary_intent}")
            return final_response
            
        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            return await self._create_fallback_response(user_input, context)
    
    async def _analyze_intent(self, user_input: str, context: JourneyContext, 
                            user: User) -> IntentAnalysis:
        """Analyze user intent and determine required sub-agents"""
        
        analysis_prompt = f"""
        You are analyzing a user's request during a road trip conversation.
        
        User input: "{user_input}"
        
        Current context:
        - Location: {context.current_location.get('name', 'Unknown')}
        - Time: {context.current_time.strftime('%I:%M %p')}
        - Journey stage: {context.journey_stage}
        - Recent conversation: {self.conversation_state.get_recent_context()}
        
        Analyze and categorize this request:
        
        1. Primary intent (story_request, booking_inquiry, navigation_help, navigation_voice, general_chat, complex_assistance)
        2. Which specialized agents are needed:
           - story: for historical/cultural narratives
           - booking: for reservations and purchases
           - navigation: for directions and route planning
           - context: for situational awareness and suggestions
           - local_expert: for authentic local recommendations
        
        3. Urgency level (immediate, can_wait, background)
        4. Expected response type (story, booking_suggestion, directions, information, mixed)
        
        Consider:
        - Does the user want entertainment/education (story agent)?
        - Are they looking for services/activities (booking agent)?
        - Do they need route help (navigation agent)?
        - Should I proactively suggest something (context agent)?
        - Would local insights be valuable (local_expert agent)?
        
        Respond in JSON format.
        """
        
        try:
            response = await self.ai_client.generate_structured_response(
                analysis_prompt, expected_format="intent_analysis"
            )
            
            return IntentAnalysis(
                primary_intent=IntentType(response.get('primary_intent', 'general_chat')),
                secondary_intents=[IntentType(i) for i in response.get('secondary_intents', [])],
                required_agents=response.get('required_agents', {}),
                urgency=UrgencyLevel(response.get('urgency', 'can_wait')),
                context_requirements=response.get('context_requirements', []),
                expected_response_type=response.get('expected_response_type', 'information')
            )
            
        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
            # Fallback to general chat with basic agents
            return IntentAnalysis(
                primary_intent=IntentType.GENERAL_CHAT,
                secondary_intents=[],
                required_agents={'context': {'task': 'general_assistance'}},
                urgency=UrgencyLevel.CAN_WAIT,
                context_requirements=[],
                expected_response_type='information'
            )
    
    async def _coordinate_sub_agents(self, intent: IntentAnalysis, context: JourneyContext, 
                                   user: User) -> Dict[str, Any]:
        """Coordinate multiple sub-agents concurrently"""
        
        tasks = []
        
        # Create tasks for each required sub-agent
        for agent_name, task_details in intent.required_agents.items():
            if agent_name in self.sub_agents:
                task = self._create_agent_task(agent_name, task_details, context, user)
                if task:
                    tasks.append((agent_name, self._call_sub_agent(agent_name, task, context)))
        
        # Execute sub-agent calls concurrently
        results = {}
        if tasks:
            try:
                completed_tasks = await asyncio.gather(
                    *[task for _, task in tasks], 
                    return_exceptions=True
                )
                
                for i, (agent_name, _) in enumerate(tasks):
                    task_result = completed_tasks[i]
                    if isinstance(task_result, Exception):
                        logger.error(f"Sub-agent {agent_name} failed: {task_result}")
                        results[agent_name] = {'status': 'error', 'fallback': True}
                    else:
                        results[agent_name] = task_result
                        
            except Exception as e:
                logger.error(f"Sub-agent coordination failed: {e}")
        
        return results
    
    def _create_agent_task(self, agent_name: str, task_details: Dict[str, Any], 
                          context: JourneyContext, user: User) -> Optional[AgentTask]:
        """Create appropriate task for specific agent"""
        
        task_configs = {
            'story': {
                'task_type': 'generate_story',
                'parameters': {
                    'location': context.current_location,
                    'user_preferences': user.preferences,
                    'story_theme': task_details.get('theme', 'general'),
                    'duration': task_details.get('duration', 'medium')
                },
                'priority': 1,
                'timeout_seconds': 30
            },
            'booking': {
                'task_type': 'find_opportunities',
                'parameters': {
                    'location': context.current_location,
                    'journey_context': context,
                    'user_preferences': user.preferences,
                    'booking_type': task_details.get('type', 'any')
                },
                'priority': 2,
                'timeout_seconds': 15
            },
            'navigation': {
                'task_type': 'route_assistance',
                'parameters': {
                    'current_location': context.current_location,
                    'route_info': context.route_info,
                    'assistance_type': task_details.get('assistance_type', 'general')
                },
                'priority': 1,
                'timeout_seconds': 10
            },
            'context': {
                'task_type': 'assess_situation',
                'parameters': {
                    'journey_context': context,
                    'conversation_history': self.conversation_state.get_recent_context(),
                    'assessment_focus': task_details.get('focus', 'general')
                },
                'priority': 3,
                'timeout_seconds': 10
            },
            'local_expert': {
                'task_type': 'provide_insights',
                'parameters': {
                    'location': context.current_location,
                    'insight_type': task_details.get('insight_type', 'general'),
                    'user_interests': user.preferences.get('interests', [])
                },
                'priority': 2,
                'timeout_seconds': 20
            }
        }
        
        if agent_name in task_configs:
            config = task_configs[agent_name]
            return AgentTask(**config)
        
        return None
    
    async def _call_sub_agent(self, agent_name: str, task: AgentTask, 
                            context: JourneyContext) -> Dict[str, Any]:
        """Call specific sub-agent with error handling"""
        
        try:
            agent = self.sub_agents[agent_name]
            
            # Route to appropriate agent method based on task type
            if hasattr(agent, task.task_type):
                method = getattr(agent, task.task_type)
                result = await asyncio.wait_for(
                    method(**task.parameters), 
                    timeout=task.timeout_seconds
                )
                return {'status': 'success', 'data': result, 'agent': agent_name}
            else:
                logger.warning(f"Agent {agent_name} doesn't support task {task.task_type}")
                return {'status': 'error', 'reason': 'unsupported_task', 'agent': agent_name}
                
        except asyncio.TimeoutError:
            logger.error(f"Sub-agent {agent_name} timed out")
            return {'status': 'error', 'reason': 'timeout', 'agent': agent_name}
        except Exception as e:
            logger.error(f"Sub-agent {agent_name} failed: {e}")
            return {'status': 'error', 'reason': str(e), 'agent': agent_name}
    
    async def _synthesize_response(self, user_input: str, intent: IntentAnalysis, 
                                 sub_agent_responses: Dict[str, Any], 
                                 context: JourneyContext) -> AgentResponse:
        """Create natural, conversational response from sub-agent results"""
        
        # Prepare sub-agent data for synthesis
        agent_data = self._format_agent_responses(sub_agent_responses)
        
        synthesis_prompt = f"""
        You are a friendly, knowledgeable road trip guide having a natural conversation.
        
        User asked: "{user_input}"
        Primary intent: {intent.primary_intent.value}
        
        Information from your knowledge sources:
        {agent_data}
        
        Current situation:
        - Location: {context.current_location.get('name', 'Unknown')}
        - Time: {context.current_time.strftime('%I:%M %p')}
        - Journey stage: {context.journey_stage}
        
        Previous conversation:
        {self.conversation_state.get_recent_context()}
        
        Create a natural, engaging response that:
        1. Addresses the user's request directly
        2. Integrates available information naturally
        3. Maintains conversational flow
        4. Includes relevant suggestions or opportunities
        5. Stays in character as a helpful travel guide
        6. Never mentions "agents" or internal processes
        7. Keeps driving safety in mind (voice-first interaction)
        
        If booking opportunities exist, weave them naturally into the conversation.
        If stories are available, tell them engagingly.
        If navigation help is needed, provide it clearly.
        
        Format your response as a natural conversation.
        """
        
        try:
            response_content = await self.ai_client.generate_response(synthesis_prompt)
            
            # Extract actions and booking opportunities from agent responses
            actions = self._extract_actions(sub_agent_responses)
            booking_opportunities = self._extract_booking_opportunities(sub_agent_responses)
            
            return AgentResponse(
                text=response_content,
                audio_url=None,  # Will be generated by TTS service
                actions=actions,
                booking_opportunities=booking_opportunities,
                conversation_state_updates={},
                requires_followup=self._check_requires_followup(intent, sub_agent_responses)
            )
            
        except Exception as e:
            logger.error(f"Response synthesis failed: {e}")
            return await self._create_fallback_response(user_input, context)
    
    def _format_agent_responses(self, responses: Dict[str, Any]) -> str:
        """Format sub-agent responses for synthesis prompt"""
        
        formatted_data = []
        
        for agent_name, response in responses.items():
            if response.get('status') == 'success' and response.get('data'):
                data = response['data']
                
                if agent_name == 'story':
                    formatted_data.append(f"Story content: {data.get('narrative', '')}")
                elif agent_name == 'booking':
                    opportunities = data.get('opportunities', [])
                    if opportunities:
                        formatted_data.append(f"Booking opportunities: {opportunities}")
                elif agent_name == 'navigation':
                    nav_info = data.get('assistance', '')
                    if nav_info:
                        formatted_data.append(f"Navigation info: {nav_info}")
                elif agent_name == 'context':
                    suggestions = data.get('suggestions', [])
                    if suggestions:
                        formatted_data.append(f"Contextual suggestions: {suggestions}")
                elif agent_name == 'local_expert':
                    insights = data.get('insights', '')
                    if insights:
                        formatted_data.append(f"Local insights: {insights}")
        
        return "\n".join(formatted_data) if formatted_data else "No additional information available."
    
    def _extract_actions(self, responses: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract actionable items from sub-agent responses"""
        actions = []
        
        for agent_name, response in responses.items():
            if response.get('status') == 'success' and response.get('data'):
                data = response['data']
                if 'actions' in data:
                    actions.extend(data['actions'])
        
        return actions
    
    def _extract_booking_opportunities(self, responses: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract booking opportunities from sub-agent responses"""
        opportunities = []
        
        booking_response = responses.get('booking', {})
        if booking_response.get('status') == 'success':
            data = booking_response.get('data', {})
            opportunities.extend(data.get('opportunities', []))
        
        return opportunities
    
    def _check_requires_followup(self, intent: IntentAnalysis, 
                               responses: Dict[str, Any]) -> bool:
        """Determine if response requires user followup"""
        
        # Check if any booking opportunities were presented
        booking_response = responses.get('booking', {})
        if booking_response.get('status') == 'success':
            opportunities = booking_response.get('data', {}).get('opportunities', [])
            if opportunities:
                return True
        
        # Check if navigation assistance requires confirmation
        if intent.primary_intent == IntentType.NAVIGATION_HELP:
            return True
        
        return False
    
    async def _create_fallback_response(self, user_input: str, 
                                      context: JourneyContext) -> AgentResponse:
        """Create fallback response when normal processing fails"""
        
        fallback_responses = [
            "I'm here to help with your journey. Could you tell me more about what you're looking for?",
            "Let me think about that. What specifically would be most helpful right now?",
            "I want to make sure I give you the best information. Could you rephrase your question?",
        ]
        
        import random
        response_text = random.choice(fallback_responses)
        
        return AgentResponse(
            text=response_text,
            audio_url=None,
            actions=[],
            booking_opportunities=[],
            conversation_state_updates={},
            requires_followup=True
        )
    
    async def coordinate_navigation_voice(self, navigation_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Coordinate turn-by-turn voice navigation with story/audio orchestration.
        
        This method integrates navigation instructions with the audio playback system,
        ensuring safety-first prioritization while maintaining engagement.
        """
        try:
            # Check if we have an active route
            if not self.navigation_voice_state['active_route_id']:
                logger.warning("No active route for voice navigation")
                return {
                    'status': 'no_route',
                    'message': 'No active navigation route'
                }
            
            # Get current instruction from navigation voice service
            nav_instruction = await navigation_voice_service.get_current_instruction(
                navigation_context['navigation_state'],
                {
                    'route_id': self.navigation_voice_state['active_route_id'],
                    'story_playing': navigation_context.get('story_playing', False),
                    'audio_priority': navigation_context.get('audio_priority', 'balanced')
                }
            )
            
            if not nav_instruction:
                return {
                    'status': 'no_instruction',
                    'message': 'No navigation instruction needed at this time'
                }
            
            # Determine audio orchestration based on priority
            orchestration_action = self._determine_audio_orchestration(
                nav_instruction,
                navigation_context
            )
            
            # Generate voice audio
            voice_audio = await navigation_voice_service.generate_voice_audio(
                nav_instruction,
                personality_override=self._get_navigation_voice_personality(navigation_context)
            )
            
            # Update navigation state
            self.navigation_voice_state['last_instruction_time'] = datetime.now()
            
            return {
                'status': 'success',
                'instruction': nav_instruction,
                'audio': voice_audio,
                'orchestration': orchestration_action,
                'next_check_seconds': self._calculate_next_check_interval(nav_instruction)
            }
            
        except Exception as e:
            logger.error(f"Navigation voice coordination failed: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _determine_audio_orchestration(self, instruction: Any, 
                                     context: Dict[str, Any]) -> Dict[str, Any]:
        """Determine how to orchestrate audio based on navigation priority"""
        
        if instruction.priority.value == 'critical':
            return {
                'action': 'interrupt_all',
                'restore_after': True,
                'fade_duration_ms': 500
            }
        elif instruction.priority.value == 'high':
            return {
                'action': 'pause_story',
                'duck_music': True,
                'restore_after': True,
                'fade_duration_ms': 1000
            }
        elif instruction.priority.value == 'medium':
            return {
                'action': 'duck_all',
                'duck_level_db': -12,
                'restore_after': True
            }
        else:  # low priority
            return {
                'action': 'wait_for_gap',
                'max_wait_seconds': 10
            }
    
    def _get_navigation_voice_personality(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get navigation voice personality based on context"""
        
        # Use different voice personalities based on situation
        if context.get('emergency_mode'):
            return {
                'voice_name': 'en-US-Neural2-A',  # Clear, urgent female voice
                'speaking_rate': 1.2,
                'pitch': 2,
                'volume_gain_db': 5.0
            }
        elif context.get('user_preference_voice'):
            # Use user's preferred navigation voice
            return context['user_preference_voice']
        
        # Use default navigation voice
        return None
    
    def _calculate_next_check_interval(self, instruction: Any) -> int:
        """Calculate when to check for next navigation instruction"""
        
        # Based on the instruction type and current speed
        if instruction.timing == 'immediate':
            return 5  # Check again in 5 seconds
        elif instruction.timing == 'prepare':
            return 10  # Check again in 10 seconds
        elif instruction.timing == 'reminder':
            return 20  # Check again in 20 seconds
        else:
            return 30  # Default check interval
    
    async def start_navigation_voice(self, route: Dict[str, Any], 
                                   journey_context: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize voice navigation for a route"""
        try:
            # Process route for voice navigation
            voice_data = await navigation_voice_service.process_route_for_voice(
                route,
                journey_context['current_location'],
                journey_context
            )
            
            # Update navigation state
            self.navigation_voice_state['active_route_id'] = voice_data['route_id']
            self.navigation_voice_state['current_instruction_index'] = 0
            self.navigation_voice_state['voice_navigation_active'] = True
            
            logger.info(f"Started voice navigation for route {voice_data['route_id']}")
            
            return {
                'status': 'success',
                'route_id': voice_data['route_id'],
                'total_instructions': len(voice_data['instruction_templates']),
                'coordination_rules': voice_data['coordination_rules']
            }
            
        except Exception as e:
            logger.error(f"Failed to start navigation voice: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def stop_navigation_voice(self):
        """Stop voice navigation"""
        self.navigation_voice_state = {
            'active_route_id': None,
            'current_instruction_index': 0,
            'last_instruction_time': None,
            'voice_navigation_active': False
        }
        logger.info("Stopped voice navigation")
    
    async def coordinate_spatial_audio(self, audio_type: str, 
                                     location_context: Dict[str, Any], 
                                     audio_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Coordinate spatial audio processing for immersive soundscapes
        
        Args:
            audio_type: 'story', 'navigation', 'ambient', etc.
            location_context: Current location and environment info
            audio_metadata: Details about the audio content
            
        Returns:
            Spatial audio configuration and processing details
        """
        try:
            # Update environment based on location
            new_environment = await self._determine_audio_environment(location_context)
            if new_environment != self.spatial_audio_state['environment']:
                await spatial_audio_engine.set_environment(new_environment)
                self.spatial_audio_state['environment'] = new_environment
                
                # Generate transition effect if needed
                if self.spatial_audio_state['last_environment_update']:
                    time_since_last = (datetime.now() - self.spatial_audio_state['last_environment_update']).seconds
                    if time_since_last < 300:  # Within 5 minutes
                        await self._create_environment_transition(
                            self.spatial_audio_state['environment'],
                            new_environment
                        )
                
                self.spatial_audio_state['last_environment_update'] = datetime.now()
            
            # Create soundscape for current conditions
            soundscape = await spatial_audio_engine.create_soundscape(
                location_context,
                self._get_time_of_day(),
                location_context.get('weather', {}).get('condition', 'clear')
            )
            
            # Position audio sources based on type
            if audio_type == 'story':
                # Add story narrator to spatial audio
                story_source = SpatialAudioSource(
                    source_id="story_narrator",
                    source_type=SoundSource.NARRATOR,
                    position=self.spatial_audio_state['story_position'],
                    volume=1.0,
                    priority=8,
                    doppler_enabled=False,  # Narrator doesn't move
                    distance_attenuation=False  # Always clear
                )
                await spatial_audio_engine.add_source(story_source)
                
                # Add character voices if present
                if audio_metadata.get('characters'):
                    await self._position_character_voices(audio_metadata['characters'])
                    
            elif audio_type == 'navigation':
                # Position navigation voice optimally
                nav_source = SpatialAudioSource(
                    source_id="navigation_voice",
                    source_type=SoundSource.NAVIGATION,
                    position=self.spatial_audio_state['navigation_position'],
                    volume=1.0,
                    priority=10,  # Highest priority
                    doppler_enabled=False,
                    distance_attenuation=False
                )
                await spatial_audio_engine.add_source(nav_source)
            
            # Add ambient sources from soundscape
            for source_config in soundscape['sources']:
                if source_config['type'] != SoundSource.NARRATOR:  # Skip narrator, already added
                    ambient_source = SpatialAudioSource(
                        source_id=source_config['id'],
                        source_type=SoundSource[source_config['type']],
                        position=source_config['position'],
                        volume=source_config['volume'],
                        priority=source_config.get('priority', 3),
                        movement_path=source_config.get('movement_path')
                    )
                    await spatial_audio_engine.add_source(ambient_source)
            
            # Update listener position based on vehicle
            await spatial_audio_engine.update_listener(
                AudioPosition(0, 0, 0),  # Driver position
                location_context.get('heading', 0),
                location_context.get('speed', 0)
            )
            
            return {
                'status': 'success',
                'environment': new_environment.value,
                'active_sources': len(spatial_audio_engine.active_sources),
                'soundscape': soundscape,
                'processing_config': {
                    'sample_rate': spatial_audio_engine.sample_rate,
                    'hrtf_profile': spatial_audio_engine.current_hrtf
                }
            }
            
        except Exception as e:
            logger.error(f"Error coordinating spatial audio: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'fallback': 'stereo'
            }
    
    async def _determine_audio_environment(self, location_context: Dict[str, Any]) -> AudioEnvironment:
        """Determine appropriate audio environment from location"""
        # Extract relevant features
        terrain = location_context.get('terrain', '').lower()
        landmarks = location_context.get('landmarks', [])
        road_type = location_context.get('road_type', '').lower()
        population_density = location_context.get('population_density', 'low')
        
        # Map to audio environments
        if 'tunnel' in road_type or any('tunnel' in str(l).lower() for l in landmarks):
            return AudioEnvironment.TUNNEL
        elif 'bridge' in road_type or any('bridge' in str(l).lower() for l in landmarks):
            return AudioEnvironment.BRIDGE
        elif 'highway' in road_type or 'interstate' in road_type:
            return AudioEnvironment.HIGHWAY
        elif population_density == 'high' or 'city' in terrain:
            return AudioEnvironment.CITY
        elif 'forest' in terrain or 'woods' in terrain:
            return AudioEnvironment.FOREST
        elif 'mountain' in terrain or 'alpine' in terrain:
            return AudioEnvironment.MOUNTAIN
        elif 'coast' in terrain or 'beach' in terrain:
            return AudioEnvironment.COASTAL
        elif 'desert' in terrain:
            return AudioEnvironment.DESERT
        else:
            return AudioEnvironment.RURAL
    
    async def _create_environment_transition(self, from_env: AudioEnvironment, 
                                           to_env: AudioEnvironment) -> None:
        """Create smooth audio transition between environments"""
        try:
            # Generate transition effect
            transition_audio = await spatial_audio_engine.generate_transition_effect(
                from_env, to_env, 2.0  # 2 second transition
            )
            
            # This would be sent to the audio playback system
            logger.info(f"Created environment transition from {from_env.value} to {to_env.value}")
            
        except Exception as e:
            logger.error(f"Failed to create environment transition: {e}")
    
    async def _position_character_voices(self, characters: List[Dict[str, Any]]) -> None:
        """Position character voices in 3D space for stories"""
        positions = [
            AudioPosition(-0.7, 0, 0.2),   # Left side
            AudioPosition(0.7, 0, 0.2),    # Right side
            AudioPosition(-0.4, 0.2, 0.4), # Left front
            AudioPosition(0.4, 0.2, 0.4),  # Right front
        ]
        
        for i, character in enumerate(characters[:4]):  # Max 4 character positions
            character_source = SpatialAudioSource(
                source_id=f"character_{character['name']}",
                source_type=SoundSource.CHARACTER,
                position=positions[i],
                volume=0.9,
                priority=7,
                doppler_enabled=True  # Characters can move
            )
            await spatial_audio_engine.add_source(character_source)
    
    def _get_time_of_day(self) -> str:
        """Get current time of day category"""
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"
    
    async def update_spatial_audio_preferences(self, preferences: Dict[str, Any]) -> None:
        """Update spatial audio preferences"""
        if 'hrtf_profile' in preferences:
            spatial_audio_engine.current_hrtf = preferences['hrtf_profile']
        
        if 'story_position' in preferences:
            pos = preferences['story_position']
            self.spatial_audio_state['story_position'] = AudioPosition(
                pos.get('x', 0), pos.get('y', 0), pos.get('z', 0.3)
            )
        
        if 'navigation_position' in preferences:
            pos = preferences['navigation_position']
            self.spatial_audio_state['navigation_position'] = AudioPosition(
                pos.get('x', 0), pos.get('y', 0.2), pos.get('z', 0.5)
            )
        
        logger.info("Updated spatial audio preferences")
    
    async def check_story_opportunity(self, context: JourneyContext) -> bool:
        """
        Check if it's time for a new story based on dynamic timing.
        
        Returns True if a story should be generated now.
        """
        try:
            # Initialize journey tracking if needed
            if self.story_timing_state['journey_start_time'] is None:
                self.story_timing_state['journey_start_time'] = context.current_time
                self.story_timing_state['total_journey_distance'] = context.route_info.get('total_distance_km', 100)
            
            # Get or create engagement tracker for user
            user_id = context.passengers[0].get('user_id', 'default') if context.passengers else 'default'
            if user_id not in self.engagement_trackers:
                self.engagement_trackers[user_id] = PassengerEngagementTracker(user_id)
            
            engagement_tracker = self.engagement_trackers[user_id]
            
            # Check if stories should be paused
            if engagement_tracker.should_pause_stories():
                logger.info("Stories paused due to low engagement or user request")
                return False
            
            # Build timing context
            timing_context = self._build_timing_context(context, engagement_tracker)
            self.story_timing_state['last_timing_context'] = timing_context
            
            # Calculate next story time
            next_story_minutes, reasoning = self.story_timing.calculate_next_story_time(timing_context)
            
            # Check if enough time has passed
            minutes_since_last = self._minutes_since_last_story()
            
            if minutes_since_last is None or minutes_since_last >= next_story_minutes:
                logger.info(
                    f"Story opportunity detected: {minutes_since_last:.1f} min since last story >= {next_story_minutes:.1f} min threshold",
                    extra={
                        "reasoning": reasoning,
                        "engagement_level": timing_context.engagement_level,
                        "journey_phase": timing_context.journey_phase.value
                    }
                )
                
                # Record metrics if available
                if METRICS_AVAILABLE:
                    try:
                        metrics.increment_counter("story_opportunity_checks_triggered", 1)
                        if minutes_since_last is not None:
                            metrics.observe_histogram("story_interval_actual_minutes", minutes_since_last)
                    except Exception as e:
                        logger.warning(f"Failed to record story opportunity metrics: {str(e)}")
                
                return True
            else:
                remaining_minutes = next_story_minutes - minutes_since_last
                logger.debug(
                    f"Not time for story yet: {remaining_minutes:.1f} min remaining",
                    extra={"next_check_minutes": min(remaining_minutes, 1.0)}
                )
                
                # Record metrics if available
                if METRICS_AVAILABLE:
                    try:
                        metrics.increment_counter("story_opportunity_checks_skipped", 1)
                        metrics.observe_histogram("story_timing_remaining_minutes", remaining_minutes)
                    except Exception as e:
                        logger.warning(f"Failed to record story opportunity metrics: {str(e)}")
                
                return False
                
        except Exception as e:
            logger.error(f"Error checking story opportunity: {str(e)}")
            
            # Record error metric if available
            if METRICS_AVAILABLE:
                try:
                    metrics.increment_counter("story_opportunity_check_errors", 1)
                except Exception as me:
                    logger.warning(f"Failed to record error metric: {str(me)}")
            
            # Fallback to safe default
            return self._minutes_since_last_story() is None or self._minutes_since_last_story() >= 5.0
    
    def _build_timing_context(self, journey_context: JourneyContext, engagement_tracker: PassengerEngagementTracker) -> TimingContext:
        """Build timing context from journey state"""
        # Calculate journey progress
        journey_progress = self._calculate_journey_progress(journey_context)
        
        # Determine journey phase
        journey_phase = self._determine_journey_phase(journey_progress)
        
        # Assess driving complexity
        driving_complexity = self._assess_driving_complexity(journey_context)
        
        # Calculate elapsed time
        elapsed_minutes = 0
        if self.story_timing_state['journey_start_time']:
            elapsed_minutes = (journey_context.current_time - self.story_timing_state['journey_start_time']).total_seconds() / 60
        
        # Extract passenger info
        passenger_count = len(journey_context.passengers)
        has_children = any(p.get('age', 100) < 12 for p in journey_context.passengers)
        passenger_type = self._determine_passenger_type(journey_context.passengers)
        
        # Check for golden hour
        is_golden_hour = self._is_golden_hour(journey_context.current_time)
        
        # Get POI information
        nearest_poi = journey_context.route_info.get('nearest_poi', {})
        
        # Build context
        return TimingContext(
            # Journey information
            journey_phase=journey_phase,
            journey_progress=journey_progress,
            total_distance_km=self.story_timing_state['total_journey_distance'] or 100,
            remaining_distance_km=journey_context.route_info.get('remaining_distance_km', 50),
            elapsed_time_minutes=elapsed_minutes,
            
            # Driving conditions
            current_speed_kmh=journey_context.vehicle_info.get('speed_kmh', 60),
            average_speed_kmh=journey_context.vehicle_info.get('average_speed_kmh', 60),
            driving_complexity=driving_complexity,
            is_highway=journey_context.route_info.get('road_type', '').lower() in ['highway', 'interstate'],
            traffic_level=journey_context.route_info.get('traffic_level', 'moderate'),
            weather_condition=journey_context.weather.get('condition', 'clear'),
            
            # Passenger context
            engagement_level=engagement_tracker.get_current_engagement_level(),
            passenger_count=passenger_count,
            has_children=has_children,
            passenger_type=passenger_type,
            last_interaction_minutes=self._minutes_since_last_interaction(),
            
            # Environmental context
            time_of_day=journey_context.current_time,
            is_golden_hour=is_golden_hour,
            is_night_driving=self._get_time_of_day() == "night",
            
            # POI context
            nearest_poi_distance_km=nearest_poi.get('distance_km'),
            nearest_poi_name=nearest_poi.get('name'),
            nearest_poi_type=nearest_poi.get('type'),
            
            # Story context
            stories_told_count=self.story_timing_state['stories_told_count'],
            last_story_minutes_ago=self._minutes_since_last_story(),
            last_story_was_interrupted=False,  # TODO: Track from story agent
            user_requested_story=False  # This would be set by intent analysis
        )
    
    def _calculate_journey_progress(self, context: JourneyContext) -> float:
        """Calculate journey progress from 0.0 to 1.0"""
        total_distance = self.story_timing_state['total_journey_distance'] or 100
        remaining_distance = context.route_info.get('remaining_distance_km', 0)
        
        if total_distance > 0:
            progress = (total_distance - remaining_distance) / total_distance
            return max(0.0, min(1.0, progress))
        return 0.5
    
    def _determine_journey_phase(self, progress: float) -> JourneyPhase:
        """Determine journey phase based on progress"""
        if progress < 0.05:
            return JourneyPhase.DEPARTURE
        elif progress < 0.2:
            return JourneyPhase.EARLY
        elif progress < 0.8:
            return JourneyPhase.CRUISE
        elif progress < 0.95:
            return JourneyPhase.APPROACHING
        else:
            return JourneyPhase.ARRIVAL
    
    def _assess_driving_complexity(self, context: JourneyContext) -> DrivingComplexity:
        """Assess current driving complexity"""
        # Factors to consider
        speed = context.vehicle_info.get('speed_kmh', 60)
        traffic = context.route_info.get('traffic_level', 'moderate')
        weather = context.weather.get('condition', 'clear')
        road_type = context.route_info.get('road_type', '').lower()
        
        # Score complexity
        complexity_score = 0
        
        # Speed factors
        if speed < 20:  # Very slow/stopped
            complexity_score += 2
        elif speed > 100:  # Very fast
            complexity_score += 1
        
        # Traffic factors
        if traffic == 'heavy':
            complexity_score += 3
        elif traffic == 'moderate':
            complexity_score += 1
        
        # Weather factors
        if weather in ['rain', 'snow', 'fog']:
            complexity_score += 2
        elif weather == 'storm':
            complexity_score += 3
        
        # Road type factors
        if 'city' in road_type or 'urban' in road_type:
            complexity_score += 2
        elif 'highway' in road_type and traffic != 'heavy':
            complexity_score -= 1
        
        # Map score to complexity level
        if complexity_score <= 0:
            return DrivingComplexity.VERY_LOW
        elif complexity_score <= 2:
            return DrivingComplexity.LOW
        elif complexity_score <= 4:
            return DrivingComplexity.MODERATE
        elif complexity_score <= 6:
            return DrivingComplexity.HIGH
        else:
            return DrivingComplexity.VERY_HIGH
    
    def _determine_passenger_type(self, passengers: List[Dict[str, Any]]) -> str:
        """Determine passenger type from passenger list"""
        if not passengers:
            return "solo"
        
        # Check for children
        if any(p.get('age', 100) < 12 for p in passengers):
            return "children"
        
        # Check for family indicators
        relationships = [p.get('relationship', '') for p in passengers]
        if any(rel in ['spouse', 'parent', 'child', 'sibling'] for rel in relationships):
            return "family"
        
        # Default to friends
        return "friends"
    
    def _minutes_since_last_story(self) -> Optional[float]:
        """Calculate minutes since last story"""
        if self.story_timing_state['last_story_time'] is None:
            return None
        
        elapsed = datetime.now() - self.story_timing_state['last_story_time']
        return elapsed.total_seconds() / 60
    
    def _minutes_since_last_interaction(self) -> float:
        """Calculate minutes since last user interaction"""
        if not self.conversation_state.message_history:
            return 999  # Large number if no interactions
        
        # Find last user message
        for msg in reversed(self.conversation_state.message_history):
            if msg['speaker'] == 'user':
                elapsed = datetime.now() - msg['timestamp']
                return elapsed.total_seconds() / 60
        
        return 999
    
    def _is_golden_hour(self, current_time: datetime) -> bool:
        """Check if current time is during golden hour"""
        hour = current_time.hour
        # Golden hour: 1 hour after sunrise and before sunset
        # Simplified: 6-7 AM and 6-7 PM
        return hour in [6, 18]
    
    def record_story_delivered(self):
        """Record that a story was delivered"""
        self.story_timing_state['last_story_time'] = datetime.now()
        self.story_timing_state['stories_told_count'] += 1
        logger.info(f"Story delivered. Total count: {self.story_timing_state['stories_told_count']}")
        
        # Record metrics if available
        if METRICS_AVAILABLE:
            try:
                metrics.increment_counter("stories_delivered_total", 1)
                metrics.set_gauge("stories_told_in_journey", self.story_timing_state['stories_told_count'])
            except Exception as e:
                logger.warning(f"Failed to record story delivery metrics: {str(e)}")
    
    def record_engagement_event(self, user_id: str, event_type: EngagementEventType, metadata: Optional[Dict] = None):
        """Record an engagement event for a user"""
        if user_id not in self.engagement_trackers:
            self.engagement_trackers[user_id] = PassengerEngagementTracker(user_id)
        
        self.engagement_trackers[user_id].record_event(event_type, metadata)