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
from .contextual_awareness_agent import ContextualAwarenessAgent
from .local_expert_agent import LocalExpertAgent

logger = logging.getLogger(__name__)


class IntentType(Enum):
    STORY_REQUEST = "story_request"
    BOOKING_INQUIRY = "booking_inquiry"
    NAVIGATION_HELP = "navigation_help"
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
        
        logger.info("Master Orchestration Agent initialized")
    
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
        
        1. Primary intent (story_request, booking_inquiry, navigation_help, general_chat, complex_assistance)
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