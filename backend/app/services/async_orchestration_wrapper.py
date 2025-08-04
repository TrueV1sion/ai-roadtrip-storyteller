"""
Async wrapper for Master Orchestration Agent.

Provides immediate API responses by delegating heavy processing to Celery tasks.
Maintains the same interface while achieving <3s response times.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import hashlib
import json

from app.core.cache import cache_manager
from app.core.logger import get_logger
from app.services.master_orchestration_agent import (
    MasterOrchestrationAgent, JourneyContext, AgentResponse
)
from app.models.user import User
from app.tasks.ai_enhanced import generate_story_with_status, synthesize_story_voice
from app.monitoring.metrics import metrics_collector

logger = get_logger(__name__)

class AsyncOrchestrationWrapper:
    """
    Wrapper that provides async task submission for orchestration requests.
    
    This maintains API response times under 3 seconds by:
    1. Checking cache for immediate responses
    2. Submitting long-running tasks to Celery
    3. Returning job IDs for polling
    """
    
    def __init__(self, orchestrator: MasterOrchestrationAgent):
        self.orchestrator = orchestrator
        self._response_cache_ttl = 3600  # 1 hour
        
    async def process_user_input_async(
        self,
        user_input: str,
        context: JourneyContext,
        user: User,
        priority: int = 5
    ) -> Dict[str, Any]:
        """
        Process user input asynchronously with immediate response.
        
        Returns either:
        - Cached response if available
        - Job ID for polling if processing needed
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(user_input, context, user)
            
            # Check cache first
            cached_response = await self._get_cached_response(cache_key)
            if cached_response:
                metrics_collector.increment('orchestration.cache_hit')
                return {
                    'type': 'immediate',
                    'response': cached_response,
                    'cached': True,
                    'processing_time': asyncio.get_event_loop().time() - start_time
                }
            
            # Check if this is a simple query that can be handled quickly
            if self._is_simple_query(user_input):
                # Process synchronously for simple queries
                try:
                    response = await asyncio.wait_for(
                        self.orchestrator.process_user_input(user_input, context, user),
                        timeout=2.5  # 2.5 second timeout
                    )
                    
                    # Cache the response
                    await self._cache_response(cache_key, response)
                    
                    return {
                        'type': 'immediate',
                        'response': response,
                        'cached': False,
                        'processing_time': asyncio.get_event_loop().time() - start_time
                    }
                    
                except asyncio.TimeoutError:
                    logger.info("Simple query exceeded timeout, switching to async")
            
            # For complex queries, submit to Celery
            request_data = {
                'user_input': user_input,
                'context': self._serialize_context(context),
                'user_id': user.id,
                'user_preferences': user.preferences or {},
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Determine task type based on input analysis
            task_type = self._analyze_task_type(user_input, context)
            
            if task_type == 'story_generation':
                # Submit story generation task
                task = generate_story_with_status.apply_async(
                    args=[{
                        'location': context.current_location,
                        'interests': self._extract_interests(user_input),
                        'context': self._serialize_context(context),
                        'user_id': user.id,
                        'include_voice': 'voice' in user_input.lower(),
                        'preferences': user.preferences or {}
                    }],
                    priority=priority
                )
                
                return {
                    'type': 'async',
                    'job_id': task.id,
                    'status_url': f"/api/v1/jobs/status/{task.id}",
                    'estimated_completion_time': 30,
                    'task_type': 'story_generation'
                }
            
            else:
                # For other complex queries, use a generic orchestration task
                # (This would be implemented as another Celery task)
                return {
                    'type': 'async',
                    'job_id': f"orch_{datetime.utcnow().timestamp()}",
                    'status_url': f"/api/v1/jobs/status/orch_{datetime.utcnow().timestamp()}",
                    'estimated_completion_time': 15,
                    'task_type': 'orchestration'
                }
                
        except Exception as e:
            logger.error(f"Error in async orchestration: {str(e)}")
            metrics_collector.increment('orchestration.error')
            
            # Fallback response
            return {
                'type': 'error',
                'message': "I'm having trouble processing your request. Please try again.",
                'error': str(e)
            }
    
    def _generate_cache_key(self, user_input: str, context: JourneyContext, user: User) -> str:
        """Generate consistent cache key for orchestration requests."""
        key_data = {
            'input': user_input.lower().strip(),
            'location': {
                'lat': round(context.current_location.get('latitude', 0), 3),
                'lng': round(context.current_location.get('longitude', 0), 3)
            },
            'journey_stage': context.journey_stage,
            'user_id': user.id
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return f"orch:{hashlib.md5(key_string.encode()).hexdigest()}"
    
    async def _get_cached_response(self, cache_key: str) -> Optional[AgentResponse]:
        """Retrieve cached response if available."""
        try:
            cached_data = cache_manager.get(cache_key)
            if cached_data:
                # Reconstruct AgentResponse
                return AgentResponse(**cached_data)
        except Exception as e:
            logger.warning(f"Error retrieving cached response: {str(e)}")
        return None
    
    async def _cache_response(self, cache_key: str, response: AgentResponse) -> None:
        """Cache orchestration response."""
        try:
            # Serialize response for caching
            cache_data = {
                'text': response.text,
                'audio_url': response.audio_url,
                'actions': response.actions,
                'booking_opportunities': response.booking_opportunities,
                'conversation_state_updates': response.conversation_state_updates,
                'requires_followup': response.requires_followup
            }
            cache_manager.set(cache_key, cache_data, ttl=self._response_cache_ttl)
        except Exception as e:
            logger.warning(f"Error caching response: {str(e)}")
    
    def _is_simple_query(self, user_input: str) -> bool:
        """Determine if query can be handled quickly."""
        simple_patterns = [
            'hello', 'hi', 'hey',
            'thank', 'thanks',
            'yes', 'no', 'okay', 'ok',
            'help', 'what can you do',
            'where are we', 'current location',
            'how long', 'eta', 'time remaining'
        ]
        
        input_lower = user_input.lower().strip()
        
        # Check if it's a simple greeting or acknowledgment
        if len(input_lower.split()) <= 5:
            for pattern in simple_patterns:
                if pattern in input_lower:
                    return True
        
        return False
    
    def _analyze_task_type(self, user_input: str, context: JourneyContext) -> str:
        """Analyze what type of task this request requires."""
        input_lower = user_input.lower()
        
        story_keywords = ['tell me about', 'story', 'history', 'what happened', 'interesting']
        booking_keywords = ['book', 'reserve', 'restaurant', 'hotel', 'ticket']
        navigation_keywords = ['directions', 'route', 'how to get', 'navigate']
        
        if any(keyword in input_lower for keyword in story_keywords):
            return 'story_generation'
        elif any(keyword in input_lower for keyword in booking_keywords):
            return 'booking'
        elif any(keyword in input_lower for keyword in navigation_keywords):
            return 'navigation'
        else:
            return 'general'
    
    def _serialize_context(self, context: JourneyContext) -> Dict[str, Any]:
        """Serialize journey context for task submission."""
        return {
            'current_location': context.current_location,
            'current_time': context.current_time.isoformat(),
            'journey_stage': context.journey_stage,
            'passengers': context.passengers,
            'vehicle_info': context.vehicle_info,
            'weather': context.weather,
            'route_info': context.route_info
        }
    
    def _extract_interests(self, user_input: str) -> List[str]:
        """Extract interests from user input."""
        interest_map = {
            'history': ['history', 'historical', 'past', 'heritage'],
            'culture': ['culture', 'cultural', 'tradition', 'customs'],
            'food': ['food', 'restaurant', 'eat', 'cuisine', 'dining'],
            'nature': ['nature', 'park', 'scenic', 'outdoors', 'hiking'],
            'architecture': ['building', 'architecture', 'design', 'structure']
        }
        
        input_lower = user_input.lower()
        interests = []
        
        for interest, keywords in interest_map.items():
            if any(keyword in input_lower for keyword in keywords):
                interests.append(interest)
        
        return interests if interests else ['general']


# Factory function for creating async wrapper
def create_async_orchestrator() -> AsyncOrchestrationWrapper:
    """Create async orchestration wrapper with initialized orchestrator."""
    from app.core.unified_ai_client import UnifiedAIClient
    
    ai_client = UnifiedAIClient()
    orchestrator = MasterOrchestrationAgent(ai_client)
    
    return AsyncOrchestrationWrapper(orchestrator)