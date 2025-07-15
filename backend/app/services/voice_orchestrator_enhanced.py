"""
Enhanced Voice Orchestrator with World-Class Features
Implements caching, circuit breakers, performance monitoring, and advanced audio integration
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache, wraps
import hashlib
import json
from collections import defaultdict

from ..core.cache import cache_manager
from ..monitoring.metrics import metrics
from ..services.circuit_breaker import CircuitBreaker
from ..services.spatial_audio_engine import spatial_audio_engine, AudioEnvironment
from ..services.voice_personality_service import voice_personality_service
from ..services.audio_orchestration_service import get_audio_orchestrator, AudioPriority
from ..core.unified_ai_client import unified_ai_client

import logging
logger = logging.getLogger(__name__)


def timed_operation(operation_name: str):
    """Decorator to measure operation timing"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                metrics.record_voice_latency(operation_name, duration)
                
                if duration > 2.0:  # Log slow operations
                    logger.warning(f"{operation_name} took {duration:.2f}s - exceeds 2s target")
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                metrics.record_voice_error(operation_name, str(e))
                raise
        return wrapper
    return decorator


def cached_response(ttl_seconds: int = 300):
    """Decorator for caching AI responses"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"voice:{func.__name__}:{hashlib.md5(str(args).encode()).hexdigest()}"
            
            # Try to get from cache
            cached = await cache_manager.get(cache_key)
            if cached:
                metrics.increment_cache_hit("voice_response")
                return cached
            
            # Generate fresh response
            result = await func(self, *args, **kwargs)
            
            # Cache the result
            await cache_manager.set(cache_key, result, ttl=ttl_seconds)
            metrics.increment_cache_miss("voice_response")
            
            return result
        return wrapper
    return decorator


class EnhancedConversationState(Enum):
    """Extended conversation states for better tracking"""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    GATHERING_INFO = "gathering_info"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    EXECUTING_ACTION = "executing_action"
    TELLING_STORY = "telling_story"
    ERROR_RECOVERY = "error_recovery"
    OFFLINE_MODE = "offline_mode"


@dataclass
class AudioContext:
    """Enhanced audio context for world-class audio experience"""
    environment: AudioEnvironment
    active_sounds: List[str]
    music_volume: float = 0.3
    effects_volume: float = 0.5
    voice_volume: float = 1.0
    spatial_enabled: bool = True
    noise_level: float = 0.0  # Ambient noise level
    ducking_active: bool = False


class VoiceOrchestratorEnhanced:
    """
    World-class voice orchestrator with advanced features:
    - Response caching for performance
    - Circuit breakers for reliability
    - Spatial audio integration
    - Advanced error recovery
    - Offline mode support
    - Performance monitoring
    """
    
    def __init__(self, master_agent, ai_client):
        self.master_agent = master_agent
        self.ai_client = ai_client
        
        # Enhanced conversation tracking
        self.conversations: Dict[str, Any] = {}
        self.audio_contexts: Dict[str, AudioContext] = {}
        
        # Circuit breakers for external services
        self.circuit_breakers = {
            "stt": CircuitBreaker(failure_threshold=3, recovery_timeout=30),
            "tts": CircuitBreaker(failure_threshold=3, recovery_timeout=30),
            "ai": CircuitBreaker(failure_threshold=5, recovery_timeout=60),
            "booking": CircuitBreaker(failure_threshold=3, recovery_timeout=30),
        }
        
        # Performance tracking
        self.performance_stats = defaultdict(list)
        
        # Offline mode cache
        self.offline_responses = self._load_offline_responses()
        
        # Request deduplication
        self.pending_requests: Dict[str, asyncio.Future] = {}
        
        # Initialize audio orchestrator
        self.audio_orchestrator = get_audio_orchestrator()
        
        logger.info("Enhanced Voice Orchestrator initialized with world-class features")
    
    @timed_operation("total_voice_processing")
    async def process_voice_input(
        self,
        user_id: str,
        audio_input: bytes,
        location: Dict[str, float],
        context_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enhanced voice processing with all world-class features
        """
        # Request deduplication
        request_key = f"{user_id}:{hashlib.md5(audio_input[:100]).hexdigest()}"
        if request_key in self.pending_requests:
            logger.info(f"Deduplicating request for user {user_id}")
            return await self.pending_requests[request_key]
        
        # Create future for this request
        future = asyncio.Future()
        self.pending_requests[request_key] = future
        
        try:
            # Get or create enhanced context
            ctx = await self._get_or_create_context(user_id, location, context_data)
            
            # Update state
            ctx["state"] = EnhancedConversationState.PROCESSING
            
            # 1. Speech-to-Text with circuit breaker
            transcript = await self._transcribe_with_circuit_breaker(audio_input)
            
            # 2. Intent analysis with caching
            intent = await self._analyze_intent_cached(transcript, ctx)
            
            # 3. Update audio context for spatial audio
            await self._update_audio_context(user_id, location, intent)
            
            # 4. Orchestrate services with timeout and parallel execution
            try:
                response_data = await asyncio.wait_for(
                    self._orchestrate_services_parallel(intent, ctx),
                    timeout=3.0  # 3 second timeout for service calls
                )
            except asyncio.TimeoutError:
                logger.warning("Service orchestration timeout - using cached response")
                response_data = await self._get_cached_or_fallback_response(intent, ctx)
            
            # 5. Blend responses with personality
            unified_response = await self._blend_with_personality(response_data, ctx)
            
            # 6. Generate voice with spatial audio and orchestration
            voice_audio = await self._generate_spatial_voice(unified_response, ctx)
            
            # 7. Play through audio orchestrator for intelligent mixing
            stream_id = await self.audio_orchestrator.play_voice(
                voice_audio,
                ctx.get("personality", "wise_narrator"),
                ctx,
                priority=self._determine_audio_priority(intent)
            )
            ctx["current_voice_stream"] = stream_id
            
            # 8. Record performance metrics
            self._record_conversation_metrics(user_id, transcript, intent, response_data)
            
            # Build response
            result = {
                "voice_audio": voice_audio,
                "transcript": unified_response,
                "visual_data": response_data.get("visual_elements"),
                "actions_taken": response_data.get("actions", []),
                "state": ctx["state"].value,
                "performance_metrics": {
                    "total_latency": time.time() - ctx["request_start"],
                    "cache_hits": ctx.get("cache_hits", 0),
                    "services_called": len(response_data.get("services_used", []))
                }
            }
            
            # Complete the future
            future.set_result(result)
            return result
            
        except Exception as e:
            logger.error(f"Enhanced voice processing error: {e}")
            
            # Try offline mode
            if self._is_offline_capable(intent):
                result = await self._handle_offline_mode(transcript, ctx)
            else:
                result = await self._handle_error_with_recovery(e, ctx)
            
            future.set_result(result)
            return result
            
        finally:
            # Cleanup
            del self.pending_requests[request_key]
    
    async def _transcribe_with_circuit_breaker(self, audio_input: bytes) -> str:
        """Transcribe audio with circuit breaker protection"""
        @self.circuit_breakers["stt"]
        async def transcribe():
            # Actual STT implementation
            return await self.master_agent.stt_service.transcribe(audio_input)
        
        try:
            return await transcribe()
        except Exception as e:
            logger.error(f"STT failed: {e}")
            # Return empty transcript as fallback
            return ""
    
    @cached_response(ttl_seconds=300)
    async def _analyze_intent_cached(self, transcript: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze intent with caching"""
        @self.circuit_breakers["ai"]
        async def analyze():
            prompt = self._build_intent_prompt(transcript, context)
            return await self.ai_client.generate_json(prompt)
        
        return await analyze()
    
    async def _orchestrate_services_parallel(
        self,
        intent: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Orchestrate services in parallel with optimizations"""
        required_services = intent.get("required_services", [])
        
        # Create parallel tasks
        tasks = []
        service_names = []
        
        for service in required_services:
            if service == "restaurants":
                tasks.append(self._get_restaurants_optimized(context))
                service_names.append("restaurants")
            elif service == "hotels":
                tasks.append(self._get_hotels_optimized(context))
                service_names.append("hotels")
            elif service == "stories":
                tasks.append(self._get_story_optimized(context))
                service_names.append("stories")
            elif service == "navigation":
                tasks.append(self._get_navigation_optimized(context))
                service_names.append("navigation")
        
        # Execute all tasks in parallel
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            response_data = {
                "services_used": [],
                "results": {},
                "actions": [],
                "visual_elements": None
            }
            
            for i, (service_name, result) in enumerate(zip(service_names, results)):
                if isinstance(result, Exception):
                    logger.error(f"Service {service_name} failed: {result}")
                    # Use cached or fallback data
                    result = await self._get_service_fallback(service_name, context)
                
                if result:
                    response_data["services_used"].append(service_name)
                    response_data["results"][service_name] = result
            
            return response_data
        
        return {"services_used": [], "results": {}, "actions": []}
    
    @cached_response(ttl_seconds=600)
    async def _get_restaurants_optimized(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get restaurant data with caching and optimization"""
        location = context.get("location", {})
        
        @self.circuit_breakers["booking"]
        async def fetch_restaurants():
            return await self.master_agent.vertex_travel_agent.search_restaurants(
                latitude=location.get("lat"),
                longitude=location.get("lng"),
                radius_miles=20,
                preferences=context.get("user_preferences", {}).get("food", {})
            )
        
        restaurants = await fetch_restaurants()
        
        # Enhance with real-time availability (parallel calls)
        if restaurants:
            availability_tasks = [
                self._check_availability_cached(r["place_id"], "restaurant")
                for r in restaurants[:3]
            ]
            availabilities = await asyncio.gather(*availability_tasks, return_exceptions=True)
            
            for restaurant, availability in zip(restaurants[:3], availabilities):
                if not isinstance(availability, Exception):
                    restaurant.update(availability)
        
        return restaurants[:3]
    
    async def _update_audio_context(
        self,
        user_id: str,
        location: Dict[str, float],
        intent: Dict[str, Any]
    ) -> None:
        """Update audio context for spatial audio experience"""
        # Get or create audio context
        if user_id not in self.audio_contexts:
            self.audio_contexts[user_id] = AudioContext(
                environment=AudioEnvironment.RURAL,
                active_sounds=[]
            )
        
        audio_ctx = self.audio_contexts[user_id]
        
        # Determine environment from location
        new_environment = await self._determine_environment(location)
        if new_environment != audio_ctx.environment:
            audio_ctx.environment = new_environment
            await self.audio_orchestrator.update_environment(new_environment, location)
        
        # Adjust audio based on intent
        if intent.get("primary_intent") == "navigation_help":
            audio_ctx.ducking_active = True
            audio_ctx.music_volume = 0.1  # Duck music
        elif intent.get("primary_intent") == "story_request":
            audio_ctx.effects_volume = 0.3  # Reduce effects during story
        
        # Update speed-based audio adjustments
        speed = location.get("speed", 0)
        await self.audio_orchestrator.handle_speed_change(speed)
    
    async def _generate_spatial_voice(
        self,
        text: str,
        context: Dict[str, Any]
    ) -> bytes:
        """Generate voice with spatial audio positioning"""
        personality = context.get("personality", "wise_narrator")
        audio_ctx = self.audio_contexts.get(context.get("user_id"), AudioContext(
            environment=AudioEnvironment.RURAL,
            active_sounds=[]
        ))
        
        # Get voice configuration
        voice_config = voice_personality_service.get_personality_config(personality)
        
        # Adjust for audio context
        if audio_ctx.ducking_active:
            voice_config["volume"] = audio_ctx.voice_volume * 1.2  # Boost voice
        
        # Generate base audio
        @self.circuit_breakers["tts"]
        async def generate_tts():
            return await self.master_agent.tts_service.synthesize(
                text=text,
                voice_config=voice_config
            )
        
        voice_audio = await generate_tts()
        
        # Apply spatial audio if enabled
        if audio_ctx.spatial_enabled:
            # Position voice appropriately
            if "navigation" in context.get("intent", {}).get("primary_intent", ""):
                position = {"x": 0, "y": 0.2, "z": 0.5}  # Front and up
            else:
                position = {"x": 0, "y": 0, "z": 0.3}  # Slightly forward
            
            voice_audio = await spatial_audio_engine.process_audio(
                voice_audio,
                position,
                audio_ctx.environment
            )
        
        return voice_audio
    
    def _record_conversation_metrics(
        self,
        user_id: str,
        transcript: str,
        intent: Dict[str, Any],
        response_data: Dict[str, Any]
    ) -> None:
        """Record detailed metrics for performance monitoring"""
        metrics.record_conversation_metric(
            user_id=user_id,
            intent_type=intent.get("primary_intent", "unknown"),
            services_used=len(response_data.get("services_used", [])),
            cache_hits=response_data.get("cache_hits", 0),
            success=True
        )
    
    async def _handle_offline_mode(
        self,
        transcript: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle requests in offline mode"""
        logger.info("Handling request in offline mode")
        
        # Use pre-cached responses for common queries
        response_key = self._get_offline_response_key(transcript)
        offline_response = self.offline_responses.get(response_key, {
            "text": "I'm currently offline, but I can help with basic navigation and information.",
            "actions": []
        })
        
        return {
            "voice_audio": await self._generate_offline_audio(offline_response["text"]),
            "transcript": offline_response["text"],
            "visual_data": None,
            "actions_taken": offline_response.get("actions", []),
            "state": EnhancedConversationState.OFFLINE_MODE.value
        }
    
    def _load_offline_responses(self) -> Dict[str, Dict[str, Any]]:
        """Load pre-cached offline responses"""
        return {
            "navigation": {
                "text": "Continue straight on your current route. I'll update you when we're back online.",
                "actions": []
            },
            "restaurant": {
                "text": "I have some saved restaurant recommendations from earlier. Would you like to hear them?",
                "actions": [{"type": "show_cached_restaurants"}]
            },
            "emergency": {
                "text": "For emergencies, please call 911. I've saved the nearest hospital location.",
                "actions": [{"type": "show_emergency_info"}]
            }
        }
    
    @lru_cache(maxsize=128)
    def _get_offline_response_key(self, transcript: str) -> str:
        """Determine offline response key from transcript"""
        transcript_lower = transcript.lower()
        
        if any(word in transcript_lower for word in ["restaurant", "food", "hungry", "eat"]):
            return "restaurant"
        elif any(word in transcript_lower for word in ["emergency", "help", "hospital"]):
            return "emergency"
        elif any(word in transcript_lower for word in ["direction", "navigate", "route"]):
            return "navigation"
        
        return "default"
    
    async def _get_or_create_context(
        self,
        user_id: str,
        location: Dict[str, float],
        context_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get or create enhanced conversation context"""
        if user_id not in self.conversations:
            self.conversations[user_id] = {
                "state": EnhancedConversationState.IDLE,
                "history": [],
                "personality": context_data.get("personality", "wise_narrator"),
                "user_preferences": context_data.get("user_preferences", {}),
                "location": location,
                "request_start": time.time(),
                "cache_hits": 0
            }
        else:
            # Update location and start time
            self.conversations[user_id]["location"] = location
            self.conversations[user_id]["request_start"] = time.time()
        
        return self.conversations[user_id]
    
    async def cleanup_old_conversations(self) -> None:
        """Clean up old conversation contexts to prevent memory leaks"""
        current_time = datetime.now()
        to_remove = []
        
        for user_id, context in self.conversations.items():
            last_update = context.get("last_update", current_time)
            if current_time - last_update > timedelta(hours=1):
                to_remove.append(user_id)
        
        for user_id in to_remove:
            del self.conversations[user_id]
            if user_id in self.audio_contexts:
                del self.audio_contexts[user_id]
        
        logger.info(f"Cleaned up {len(to_remove)} old conversations")
    
    def _determine_audio_priority(self, intent: Dict[str, Any]) -> AudioPriority:
        """Determine audio priority based on intent"""
        intent_type = intent.get("primary_intent", "")
        
        if "emergency" in intent_type or "warning" in intent_type:
            return AudioPriority.CRITICAL
        elif "navigation" in intent_type:
            return AudioPriority.HIGH
        elif "story" in intent_type:
            return AudioPriority.MEDIUM
        elif "music" in intent_type or "ambient" in intent_type:
            return AudioPriority.LOW
        else:
            return AudioPriority.HIGH  # Default for voice
    
    async def _determine_environment(self, location: Dict[str, float]) -> AudioEnvironment:
        """Determine audio environment from location data"""
        # This would integrate with maps/location services
        # For now, simplified logic based on speed
        speed = location.get("speed", 0)
        
        if speed > 60:
            return AudioEnvironment.HIGHWAY
        elif speed > 40:
            return AudioEnvironment.RURAL
        else:
            return AudioEnvironment.CITY


# Circuit Breaker implementation
class CircuitBreaker:
    """Circuit breaker pattern for fault tolerance"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def __call__(self, func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if self.state == "open":
                if self._should_attempt_reset():
                    self.state = "half-open"
                else:
                    raise Exception("Circuit breaker is open")
            
            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except Exception as e:
                self._on_failure()
                raise e
        
        return wrapper
    
    def _should_attempt_reset(self) -> bool:
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self):
        self.failure_count = 0
        self.state = "closed"
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")