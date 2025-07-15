"""
Intelligent Conversation Manager
Maintains context and flow across multi-turn conversations
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import asyncio
import logging
from collections import deque

from ..core.cache import cache_manager
from ..core.unified_ai_client import unified_ai_client

logger = logging.getLogger(__name__)


class ConversationTopic(Enum):
    """Conversation topics"""
    NAVIGATION = "navigation"
    STORYTELLING = "storytelling"
    BOOKING = "booking"
    GENERAL_CHAT = "general_chat"
    EMERGENCY = "emergency"
    SETTINGS = "settings"
    GAMES = "games"
    INFORMATION = "information"


class IntentType(Enum):
    """User intent types"""
    QUESTION = "question"
    COMMAND = "command"
    CONFIRMATION = "confirmation"
    CLARIFICATION = "clarification"
    INTERRUPTION = "interruption"
    CONTINUATION = "continuation"
    TOPIC_CHANGE = "topic_change"


@dataclass
class ConversationTurn:
    """Single turn in conversation"""
    turn_id: str
    timestamp: datetime
    user_input: str
    assistant_response: str
    intent: IntentType
    topic: ConversationTopic
    context_used: Dict[str, Any]
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationState:
    """Current conversation state"""
    session_id: str
    user_id: str
    started_at: datetime
    last_interaction: datetime
    current_topic: ConversationTopic
    topics_discussed: List[ConversationTopic]
    turn_count: int
    context: Dict[str, Any]
    awaiting_response: Optional[str] = None
    clarification_needed: bool = False
    user_preferences: Dict[str, Any] = field(default_factory=dict)


class ConversationManager:
    """
    Advanced conversation management with:
    - Multi-turn context tracking
    - Topic management and transitions
    - Clarification handling
    - Context carryover
    - Memory management
    - Proactive engagement
    """
    
    def __init__(self):
        self.ai_client = unified_ai_client
        self.active_conversations: Dict[str, ConversationState] = {}
        self.conversation_history: Dict[str, deque] = {}  # Limited history per user
        self.topic_models = self._initialize_topic_models()
        self.intent_patterns = self._initialize_intent_patterns()
        
        # Configuration
        self.max_history_turns = 20
        self.context_window = 5  # Turns to consider for context
        self.session_timeout = timedelta(minutes=30)
        
        logger.info("Conversation Manager initialized")
    
    async def process_turn(
        self,
        user_id: str,
        user_input: str,
        current_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a conversation turn
        
        Returns:
            Dict containing response, intent, topic, and action recommendations
        """
        # Get or create conversation state
        state = await self._get_or_create_conversation(user_id, current_context)
        
        # Detect intent and topic
        intent = await self._detect_intent(user_input, state)
        topic = await self._detect_topic(user_input, state, intent)
        
        # Handle topic transitions
        if topic != state.current_topic:
            await self._handle_topic_transition(state, topic)
        
        # Build conversation context
        conv_context = await self._build_conversation_context(state, user_input, intent)
        
        # Generate contextual response
        response = await self._generate_contextual_response(
            user_input,
            intent,
            topic,
            conv_context,
            state
        )
        
        # Create conversation turn
        turn = ConversationTurn(
            turn_id=f"{state.session_id}_{state.turn_count}",
            timestamp=datetime.now(),
            user_input=user_input,
            assistant_response=response["text"],
            intent=intent,
            topic=topic,
            context_used=conv_context,
            confidence=response["confidence"],
            metadata=response.get("metadata", {})
        )
        
        # Update state
        await self._update_conversation_state(state, turn)
        
        # Store turn in history
        await self._store_turn(user_id, turn)
        
        return {
            "response": response["text"],
            "intent": intent.value,
            "topic": topic.value,
            "confidence": response["confidence"],
            "requires_action": response.get("requires_action", False),
            "suggested_actions": response.get("suggested_actions", []),
            "context_carryover": self._get_context_carryover(state),
            "clarification_needed": state.clarification_needed,
            "session_id": state.session_id
        }
    
    async def handle_clarification(
        self,
        user_id: str,
        clarification: str
    ) -> Dict[str, Any]:
        """Handle user clarification"""
        state = self.active_conversations.get(user_id)
        if not state or not state.clarification_needed:
            return await self.process_turn(user_id, clarification, {})
        
        # Process clarification
        state.clarification_needed = False
        clarified_context = {
            **state.context,
            "clarification": clarification,
            "original_ambiguity": state.awaiting_response
        }
        
        # Re-process with clarified context
        return await self.process_turn(user_id, clarification, clarified_context)
    
    async def get_conversation_summary(self, user_id: str) -> Dict[str, Any]:
        """Get summary of current conversation"""
        state = self.active_conversations.get(user_id)
        if not state:
            return {"active": False}
        
        history = self.conversation_history.get(user_id, deque())
        recent_turns = list(history)[-5:]
        
        # Generate summary
        summary_prompt = f"""Summarize this conversation in 2-3 sentences:
        
        Topics discussed: {', '.join([t.value for t in state.topics_discussed])}
        Turn count: {state.turn_count}
        Recent exchanges:
        {self._format_turns_for_summary(recent_turns)}
        """
        
        summary = await self.ai_client.generate_response(summary_prompt)
        
        return {
            "active": True,
            "session_id": state.session_id,
            "duration": (datetime.now() - state.started_at).total_seconds(),
            "turn_count": state.turn_count,
            "current_topic": state.current_topic.value,
            "topics_discussed": [t.value for t in state.topics_discussed],
            "summary": summary,
            "last_interaction": state.last_interaction.isoformat()
        }
    
    async def suggest_next_turn(self, user_id: str) -> Optional[str]:
        """Suggest proactive engagement based on conversation state"""
        state = self.active_conversations.get(user_id)
        if not state:
            return None
        
        # Check if enough time has passed
        silence_duration = (datetime.now() - state.last_interaction).total_seconds()
        if silence_duration < 30:  # Wait at least 30 seconds
            return None
        
        # Generate contextual suggestion
        suggestion_prompt = f"""Based on the conversation about {state.current_topic.value},
        suggest a natural follow-up question or comment to keep the user engaged.
        Keep it brief and relevant. The user has been silent for {int(silence_duration)} seconds.
        
        Recent context: {state.context.get('last_response', '')}
        """
        
        suggestion = await self.ai_client.generate_response(suggestion_prompt)
        return suggestion
    
    async def reset_conversation(self, user_id: str):
        """Reset conversation state for user"""
        if user_id in self.active_conversations:
            del self.active_conversations[user_id]
        if user_id in self.conversation_history:
            self.conversation_history[user_id].clear()
        
        logger.info(f"Reset conversation for user {user_id}")
    
    # Private methods
    
    async def _get_or_create_conversation(
        self,
        user_id: str,
        current_context: Dict[str, Any]
    ) -> ConversationState:
        """Get existing or create new conversation state"""
        if user_id in self.active_conversations:
            state = self.active_conversations[user_id]
            
            # Check for session timeout
            if datetime.now() - state.last_interaction > self.session_timeout:
                # Start new session
                logger.info(f"Session timeout for user {user_id}, starting new conversation")
                return await self._create_new_conversation(user_id, current_context)
            
            return state
        
        return await self._create_new_conversation(user_id, current_context)
    
    async def _create_new_conversation(
        self,
        user_id: str,
        current_context: Dict[str, Any]
    ) -> ConversationState:
        """Create new conversation state"""
        state = ConversationState(
            session_id=f"{user_id}_{datetime.now().timestamp()}",
            user_id=user_id,
            started_at=datetime.now(),
            last_interaction=datetime.now(),
            current_topic=ConversationTopic.GENERAL_CHAT,
            topics_discussed=[],
            turn_count=0,
            context=current_context,
            user_preferences=current_context.get("user_preferences", {})
        )
        
        self.active_conversations[user_id] = state
        
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = deque(maxlen=self.max_history_turns)
        
        return state
    
    async def _detect_intent(
        self,
        user_input: str,
        state: ConversationState
    ) -> IntentType:
        """Detect user intent from input"""
        # Check for explicit patterns
        input_lower = user_input.lower()
        
        if any(word in input_lower for word in ["?", "what", "where", "when", "how", "why"]):
            return IntentType.QUESTION
        elif any(word in input_lower for word in ["yes", "no", "okay", "sure", "confirm"]):
            return IntentType.CONFIRMATION
        elif any(word in input_lower for word in ["wait", "stop", "hold on", "actually"]):
            return IntentType.INTERRUPTION
        elif any(word in input_lower for word in ["i mean", "rather", "instead"]):
            return IntentType.CLARIFICATION
        elif state.awaiting_response:
            return IntentType.CONTINUATION
        
        # Use AI for complex intent detection
        intent_prompt = f"""Classify the intent of this user input:
        Input: "{user_input}"
        Previous topic: {state.current_topic.value}
        
        Options: question, command, confirmation, clarification, interruption, continuation, topic_change
        Return only the intent type."""
        
        try:
            intent_str = await self.ai_client.generate_response(intent_prompt)
            return IntentType(intent_str.strip().lower())
        except:
            return IntentType.COMMAND
    
    async def _detect_topic(
        self,
        user_input: str,
        state: ConversationState,
        intent: IntentType
    ) -> ConversationTopic:
        """Detect conversation topic"""
        # Quick topic detection based on keywords
        input_lower = user_input.lower()
        
        topic_keywords = {
            ConversationTopic.NAVIGATION: ["direction", "route", "turn", "navigate", "where", "map"],
            ConversationTopic.STORYTELLING: ["story", "tell me", "history", "legend", "tale"],
            ConversationTopic.BOOKING: ["book", "restaurant", "hotel", "reservation", "reserve"],
            ConversationTopic.EMERGENCY: ["emergency", "help", "urgent", "hospital", "police"],
            ConversationTopic.GAMES: ["play", "game", "trivia", "bingo", "quiz"],
            ConversationTopic.SETTINGS: ["setting", "preference", "change", "adjust", "volume"]
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in input_lower for keyword in keywords):
                return topic
        
        # If continuation of current topic
        if intent in [IntentType.CONTINUATION, IntentType.CLARIFICATION]:
            return state.current_topic
        
        # Use AI for ambiguous cases
        if intent == IntentType.TOPIC_CHANGE or len(user_input.split()) > 5:
            topic_prompt = f"""Determine the topic of this input:
            Input: "{user_input}"
            Options: {', '.join([t.value for t in ConversationTopic])}
            Return only the topic."""
            
            try:
                topic_str = await self.ai_client.generate_response(topic_prompt)
                return ConversationTopic(topic_str.strip().lower())
            except:
                pass
        
        return ConversationTopic.GENERAL_CHAT
    
    async def _handle_topic_transition(
        self,
        state: ConversationState,
        new_topic: ConversationTopic
    ):
        """Handle transition between topics"""
        old_topic = state.current_topic
        
        # Add to topics discussed
        if new_topic not in state.topics_discussed:
            state.topics_discussed.append(new_topic)
        
        # Update current topic
        state.current_topic = new_topic
        
        # Log transition
        logger.info(f"Topic transition: {old_topic.value} -> {new_topic.value}")
        
        # Clear topic-specific context
        if old_topic != new_topic:
            state.context["previous_topic"] = old_topic.value
            state.context["topic_transition"] = True
    
    async def _build_conversation_context(
        self,
        state: ConversationState,
        user_input: str,
        intent: IntentType
    ) -> Dict[str, Any]:
        """Build context for current turn"""
        # Get recent history
        history = self.conversation_history.get(state.user_id, deque())
        recent_turns = list(history)[-self.context_window:]
        
        context = {
            "session_id": state.session_id,
            "turn_count": state.turn_count,
            "current_topic": state.current_topic.value,
            "user_intent": intent.value,
            "recent_history": [
                {
                    "user": turn.user_input,
                    "assistant": turn.assistant_response,
                    "topic": turn.topic.value
                }
                for turn in recent_turns
            ],
            "user_preferences": state.user_preferences,
            "location_context": state.context.get("location", {}),
            "time_context": {
                "time_of_day": datetime.now().strftime("%H:%M"),
                "session_duration": (datetime.now() - state.started_at).total_seconds()
            }
        }
        
        # Add topic-specific context
        if state.current_topic == ConversationTopic.NAVIGATION:
            context["navigation_state"] = state.context.get("navigation", {})
        elif state.current_topic == ConversationTopic.BOOKING:
            context["booking_context"] = state.context.get("booking", {})
        
        return context
    
    async def _generate_contextual_response(
        self,
        user_input: str,
        intent: IntentType,
        topic: ConversationTopic,
        context: Dict[str, Any],
        state: ConversationState
    ) -> Dict[str, Any]:
        """Generate response with full context"""
        # Build prompt based on intent and topic
        response_prompt = self._build_response_prompt(
            user_input,
            intent,
            topic,
            context,
            state
        )
        
        # Generate response
        response_text = await self.ai_client.generate_response(response_prompt)
        
        # Determine if action is required
        requires_action = topic in [
            ConversationTopic.NAVIGATION,
            ConversationTopic.BOOKING,
            ConversationTopic.EMERGENCY
        ]
        
        # Suggest actions based on topic
        suggested_actions = self._get_suggested_actions(topic, intent, user_input)
        
        # Check if clarification is needed
        clarification_needed = self._needs_clarification(response_text, intent)
        
        return {
            "text": response_text,
            "confidence": 0.85,  # Would be calculated based on context match
            "requires_action": requires_action,
            "suggested_actions": suggested_actions,
            "metadata": {
                "topic": topic.value,
                "intent": intent.value,
                "context_used": len(context["recent_history"])
            }
        }
    
    def _build_response_prompt(
        self,
        user_input: str,
        intent: IntentType,
        topic: ConversationTopic,
        context: Dict[str, Any],
        state: ConversationState
    ) -> str:
        """Build appropriate prompt for response generation"""
        base_prompt = f"""You are a conversational AI assistant for a road trip app.
        Current conversation topic: {topic.value}
        User intent: {intent.value}
        Turn number: {context['turn_count']}
        
        User input: "{user_input}"
        """
        
        # Add conversation history if available
        if context["recent_history"]:
            base_prompt += "\nRecent conversation:\n"
            for turn in context["recent_history"][-3:]:
                base_prompt += f"User: {turn['user']}\nAssistant: {turn['assistant']}\n"
        
        # Add topic-specific instructions
        topic_instructions = {
            ConversationTopic.NAVIGATION: "Provide clear navigation assistance.",
            ConversationTopic.STORYTELLING: "Share an engaging story or fact.",
            ConversationTopic.BOOKING: "Help with booking or recommendations.",
            ConversationTopic.EMERGENCY: "Provide immediate, clear emergency assistance.",
            ConversationTopic.GAMES: "Engage in the game or activity.",
            ConversationTopic.SETTINGS: "Help adjust settings or preferences."
        }
        
        base_prompt += f"\n{topic_instructions.get(topic, 'Have a natural conversation.')}"
        
        # Add intent-specific guidance
        if intent == IntentType.CLARIFICATION:
            base_prompt += "\nThe user is clarifying their previous statement."
        elif intent == IntentType.INTERRUPTION:
            base_prompt += "\nThe user is interrupting. Acknowledge and address their new concern."
        
        base_prompt += "\nRespond naturally and concisely."
        
        return base_prompt
    
    async def _update_conversation_state(
        self,
        state: ConversationState,
        turn: ConversationTurn
    ):
        """Update conversation state after turn"""
        state.last_interaction = datetime.now()
        state.turn_count += 1
        
        # Update context with latest response
        state.context["last_response"] = turn.assistant_response
        state.context["last_intent"] = turn.intent.value
        
        # Check if awaiting response
        if "?" in turn.assistant_response or turn.intent == IntentType.QUESTION:
            state.awaiting_response = turn.assistant_response
        else:
            state.awaiting_response = None
        
        # Update clarification status
        state.clarification_needed = self._needs_clarification(
            turn.assistant_response,
            turn.intent
        )
    
    async def _store_turn(self, user_id: str, turn: ConversationTurn):
        """Store conversation turn in history"""
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = deque(maxlen=self.max_history_turns)
        
        self.conversation_history[user_id].append(turn)
        
        # Also cache for persistence
        cache_key = f"conv_turn:{turn.turn_id}"
        await cache_manager.set(cache_key, turn.__dict__, ttl=86400)  # 24 hours
    
    def _get_context_carryover(self, state: ConversationState) -> Dict[str, Any]:
        """Get context to carry over to next turn"""
        return {
            "topic": state.current_topic.value,
            "awaiting_response": state.awaiting_response,
            "clarification_needed": state.clarification_needed,
            "topics_discussed": [t.value for t in state.topics_discussed]
        }
    
    def _needs_clarification(self, response: str, intent: IntentType) -> bool:
        """Check if clarification is needed"""
        clarification_phrases = [
            "not sure what you mean",
            "could you clarify",
            "did you mean",
            "can you be more specific"
        ]
        
        return any(phrase in response.lower() for phrase in clarification_phrases)
    
    def _get_suggested_actions(
        self,
        topic: ConversationTopic,
        intent: IntentType,
        user_input: str
    ) -> List[str]:
        """Get suggested actions based on context"""
        actions = []
        
        if topic == ConversationTopic.NAVIGATION:
            actions.extend(["show_map", "update_route", "find_alternate"])
        elif topic == ConversationTopic.BOOKING:
            actions.extend(["show_options", "make_reservation", "get_details"])
        elif topic == ConversationTopic.EMERGENCY:
            actions.extend(["call_emergency", "show_nearest_hospital", "send_location"])
        elif topic == ConversationTopic.GAMES:
            actions.extend(["start_game", "show_scores", "change_difficulty"])
        
        return actions
    
    def _format_turns_for_summary(self, turns: List[ConversationTurn]) -> str:
        """Format conversation turns for summary"""
        formatted = []
        for turn in turns:
            formatted.append(f"User: {turn.user_input}\nAssistant: {turn.assistant_response}")
        return "\n".join(formatted)
    
    def _initialize_topic_models(self) -> Dict[ConversationTopic, Any]:
        """Initialize topic-specific models"""
        return {
            # Topic models would go here
        }
    
    def _initialize_intent_patterns(self) -> Dict[IntentType, List[str]]:
        """Initialize intent detection patterns"""
        return {
            # Intent patterns would go here
        }


# Global instance
conversation_manager = ConversationManager()