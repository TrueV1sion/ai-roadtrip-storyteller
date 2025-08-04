"""
Base Lifecycle Agent - Common functionality for all lifecycle agents.

This base class provides shared functionality for pre-trip, in-trip, and post-trip
agents, integrating Google's travel-concierge patterns with the AI Road Trip
Storyteller's narrative capabilities.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from app.core.unified_ai_client import UnifiedAIClient
from app.core.cache import get_cache
from app.core.standardized_errors import handle_errors
from app.models.user import User
from app.models.trip import Trip
from app.services.memory.trip_memory_system import TripMemorySystem, TripPhase, TripMemory
from app.services.story_generation_agent import StoryGenerationAgent

logger = logging.getLogger(__name__)


class LifecycleState(Enum):
    """States within each lifecycle phase."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    TRANSITIONING = "transitioning"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class LifecycleContext:
    """Context information for lifecycle operations."""
    user: User
    trip: Trip
    current_location: Optional[Dict[str, float]] = None
    weather: Optional[Dict[str, Any]] = None
    time_of_day: Optional[str] = None
    companions: List[Dict[str, Any]] = None
    preferences: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.companions is None:
            self.companions = []
        if self.preferences is None:
            self.preferences = {}


@dataclass
class LifecycleResponse:
    """Response from lifecycle agent operations."""
    success: bool
    message: str
    data: Dict[str, Any]
    actions: List[Dict[str, Any]] = None
    memories_created: List[str] = None
    next_suggestions: List[str] = None
    
    def __post_init__(self):
        if self.actions is None:
            self.actions = []
        if self.memories_created is None:
            self.memories_created = []
        if self.next_suggestions is None:
            self.next_suggestions = []


class BaseLifecycleAgent(ABC):
    """
    Base class for all lifecycle agents (pre-trip, in-trip, post-trip).
    
    Provides common functionality for:
    - Memory management
    - AI integration
    - State management
    - Error handling
    - Caching
    """
    
    def __init__(self, ai_client: UnifiedAIClient, memory_system: TripMemorySystem):
        self.ai_client = ai_client
        self.memory_system = memory_system
        self.cache = get_cache()
        self.story_agent = StoryGenerationAgent(ai_client)
        
        # Configuration
        self.max_retries = 3
        self.cache_ttl = 3600  # 1 hour
        self.response_timeout = 30  # seconds
        
        # State management
        self.current_state = LifecycleState.INITIALIZING
        self.active_sessions = {}  # user_id -> session_info
        
        logger.info(f"{self.__class__.__name__} initialized")
    
    @abstractmethod
    async def initialize(self, context: LifecycleContext) -> LifecycleResponse:
        """Initialize the agent for a specific trip context."""
        pass
    
    @abstractmethod
    async def process_request(self, request: str, context: LifecycleContext) -> LifecycleResponse:
        """Process a user request within this lifecycle phase."""
        pass
    
    @abstractmethod
    async def finalize(self, context: LifecycleContext) -> LifecycleResponse:
        """Finalize operations for this lifecycle phase."""
        pass
    
    @abstractmethod
    def get_phase(self) -> TripPhase:
        """Return the trip phase this agent handles."""
        pass
    
    @handle_errors(default_error_code="LIFECYCLE_AGENT_ERROR")
    async def create_memory(self, context: LifecycleContext, memory_context: Dict[str, Any]) -> str:
        """Create a memory entry for the current context."""
        try:
            memory = await self.memory_system.create_trip_memory(
                trip_id=context.trip.id,
                phase=self.get_phase(),
                context=memory_context,
                location=context.current_location
            )
            
            memory_id = str(memory.timestamp.timestamp())
            logger.info(f"Created memory {memory_id} for trip {context.trip.id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"Failed to create memory: {e}")
            raise
    
    async def get_relevant_memories(self, context: LifecycleContext, 
                                   lookback_hours: int = 24) -> List[TripMemory]:
        """Get relevant memories for the current context."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=lookback_hours)
        
        # Get memories from the current phase
        memories = await self.memory_system.get_trip_memories(
            trip_id=context.trip.id,
            phase=self.get_phase(),
            start_time=start_time,
            end_time=end_time
        )
        
        # Also get contextual memories if location is available
        if context.current_location:
            contextual_memories = await self.memory_system.get_contextual_memories(
                trip_id=context.trip.id,
                current_location=context.current_location,
                radius_km=10.0
            )
            
            # Merge and deduplicate
            all_memories = memories + contextual_memories
            seen_timestamps = set()
            unique_memories = []
            
            for memory in all_memories:
                timestamp_key = memory.timestamp.timestamp()
                if timestamp_key not in seen_timestamps:
                    seen_timestamps.add(timestamp_key)
                    unique_memories.append(memory)
            
            return unique_memories
        
        return memories
    
    async def generate_contextual_story(self, context: LifecycleContext,
                                      story_theme: str = "general",
                                      duration: str = "medium") -> Dict[str, Any]:
        """Generate a story appropriate for the current context."""
        if not context.current_location:
            return {
                "narrative": "I'd love to share a story, but I need to know where you are first.",
                "theme": story_theme,
                "duration": "short"
            }
        
        # Get user preferences for story generation
        user_preferences = {
            "interests": context.preferences.get("interests", []),
            "age_group": context.preferences.get("age_group", "adult"),
            "avoid_topics": context.preferences.get("avoid_topics", [])
        }
        
        # Generate story using the story agent
        story_data = await self.story_agent.generate_story(
            location={
                "name": context.current_location.get("name", "Current Location"),
                "coordinates": context.current_location,
                "type": "location"
            },
            user_preferences=user_preferences,
            story_theme=story_theme,
            duration=duration
        )
        
        # Create memory for the story
        await self.create_memory(context, {
            "story_generated": True,
            "story_theme": story_theme,
            "narrative": story_data.get("narrative", ""),
            "location": context.current_location
        })
        
        return story_data
    
    async def cache_get(self, key: str) -> Optional[Any]:
        """Get value from cache with error handling."""
        try:
            return await self.cache.get(key)
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def cache_set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with error handling."""
        try:
            await self.cache.set(key, value, expire=ttl or self.cache_ttl)
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    def create_cache_key(self, *components: str) -> str:
        """Create a cache key from components."""
        safe_components = [str(c).replace(":", "_") for c in components]
        return f"{self.__class__.__name__.lower()}:{':'.join(safe_components)}"
    
    async def ai_generate_response(self, prompt: str, context: LifecycleContext,
                                  expected_format: Optional[str] = None) -> str:
        """Generate AI response with context and error handling."""
        try:
            # Add context to prompt
            enhanced_prompt = self._enhance_prompt_with_context(prompt, context)
            
            # Generate response
            if expected_format:
                response = await self.ai_client.generate_structured_response(
                    enhanced_prompt, expected_format=expected_format
                )
            else:
                response = await asyncio.wait_for(
                    self.ai_client.generate_response(enhanced_prompt),
                    timeout=self.response_timeout
                )
            
            return response
            
        except asyncio.TimeoutError:
            logger.error(f"AI response timeout for {self.__class__.__name__}")
            return "I'm taking a moment to think. Could you try again?"
        except Exception as e:
            logger.error(f"AI generation error: {e}")
            return "I'm having trouble processing that right now. Please try again."
    
    def _enhance_prompt_with_context(self, prompt: str, context: LifecycleContext) -> str:
        """Enhance prompt with contextual information."""
        context_info = []
        
        # Add basic context
        context_info.append(f"Trip Phase: {self.get_phase().value}")
        context_info.append(f"User: {context.user.email}")
        context_info.append(f"Trip: {context.trip.name}")
        
        # Add location if available
        if context.current_location:
            context_info.append(f"Location: {context.current_location}")
        
        # Add weather if available
        if context.weather:
            context_info.append(f"Weather: {context.weather.get('summary', 'Unknown')}")
        
        # Add companions
        if context.companions:
            companion_info = ", ".join([c.get("name", "Unknown") for c in context.companions])
            context_info.append(f"Companions: {companion_info}")
        
        # Add time context
        if context.time_of_day:
            context_info.append(f"Time: {context.time_of_day}")
        
        # Combine context with prompt
        enhanced_prompt = f"""
        Context Information:
        {' | '.join(context_info)}
        
        User Request: {prompt}
        
        As an AI Road Trip Storyteller agent in the {self.get_phase().value} phase,
        provide a helpful, engaging response that considers the context above.
        Maintain the friendly, knowledgeable travel guide personality.
        """
        
        return enhanced_prompt
    
    async def transition_to_state(self, new_state: LifecycleState, 
                                 context: LifecycleContext) -> bool:
        """Transition to a new lifecycle state."""
        try:
            old_state = self.current_state
            self.current_state = new_state
            
            # Log the transition
            logger.info(f"{self.__class__.__name__} transitioned from {old_state} to {new_state}")
            
            # Create memory for state transition
            await self.create_memory(context, {
                "state_transition": True,
                "from_state": old_state.value,
                "to_state": new_state.value,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"State transition failed: {e}")
            self.current_state = LifecycleState.ERROR
            return False
    
    def get_session_info(self, user_id: str) -> Dict[str, Any]:
        """Get session information for a user."""
        return self.active_sessions.get(user_id, {})
    
    def update_session_info(self, user_id: str, updates: Dict[str, Any]):
        """Update session information for a user."""
        if user_id not in self.active_sessions:
            self.active_sessions[user_id] = {}
        self.active_sessions[user_id].update(updates)
    
    def create_success_response(self, message: str, data: Dict[str, Any],
                              actions: List[Dict[str, Any]] = None,
                              memories: List[str] = None,
                              suggestions: List[str] = None) -> LifecycleResponse:
        """Create a successful response."""
        return LifecycleResponse(
            success=True,
            message=message,
            data=data,
            actions=actions or [],
            memories_created=memories or [],
            next_suggestions=suggestions or []
        )
    
    def create_error_response(self, message: str, error_data: Dict[str, Any] = None) -> LifecycleResponse:
        """Create an error response."""
        return LifecycleResponse(
            success=False,
            message=message,
            data=error_data or {"error": True},
            actions=[],
            memories_created=[],
            next_suggestions=[]
        )
    
    async def cleanup_session(self, user_id: str):
        """Clean up session data for a user."""
        if user_id in self.active_sessions:
            del self.active_sessions[user_id]
        logger.info(f"Cleaned up session for user {user_id}")