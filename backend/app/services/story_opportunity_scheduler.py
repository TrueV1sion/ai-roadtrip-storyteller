"""
Story Opportunity Scheduler - Background task for proactive story checking

This service runs periodically to check if it's time for a new story
based on the dynamic timing system.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, Set
from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.database import get_db
from app.services.master_orchestration_agent import MasterOrchestrationAgent, JourneyContext
from app.core.unified_ai_client import get_unified_ai_client
from app.models.user import User
from app.core.cache import cache_manager
from app.services.story_queue_manager import story_queue_manager, StoryPriority, StoryTriggerType

logger = get_logger(__name__)

# Try to import metrics
try:
    from app.monitoring.metrics import metrics
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False


class StoryOpportunityScheduler:
    """Manages background story opportunity checking for active journeys"""
    
    def __init__(self):
        """Initialize the scheduler"""
        self.active_journeys: Set[str] = set()
        self.check_interval_seconds = 30  # Check every 30 seconds
        self.orchestrator: Optional[MasterOrchestrationAgent] = None
        self._running = False
        self._task = None
        self._lock = asyncio.Lock()  # Thread safety for shared state
        self._shutdown_event = asyncio.Event()
        
        logger.info("Story Opportunity Scheduler initialized")
    
    def _get_orchestrator(self) -> MasterOrchestrationAgent:
        """Get or create the orchestrator instance"""
        if self.orchestrator is None:
            ai_client = get_unified_ai_client()
            self.orchestrator = MasterOrchestrationAgent(ai_client)
        return self.orchestrator
    
    async def start(self):
        """Start the background scheduler"""
        if self._running:
            logger.warning("Story scheduler already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info("Story opportunity scheduler started")
    
    async def stop(self):
        """Stop the background scheduler with graceful shutdown"""
        logger.info("Stopping story opportunity scheduler...")
        self._running = False
        self._shutdown_event.set()
        
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await asyncio.wait_for(self._task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                logger.warning("Scheduler task cancelled or timed out during shutdown")
        
        logger.info("Story opportunity scheduler stopped")
    
    async def _run_scheduler(self):
        """Main scheduler loop with proper error handling and shutdown"""
        while self._running:
            try:
                # Check story opportunities for all active journeys
                await self._check_all_journeys()
                
                # Wait before next check with interruptible sleep
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=self.check_interval_seconds
                    )
                    # If we get here, shutdown was requested
                    break
                except asyncio.TimeoutError:
                    # Normal timeout, continue loop
                    pass
                
            except asyncio.CancelledError:
                logger.info("Scheduler task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in story scheduler: {str(e)}", exc_info=True)
                
                # Record error metric
                if METRICS_AVAILABLE:
                    try:
                        metrics.increment_counter("story_scheduler_errors", 1)
                    except Exception as metric_error:
                        logger.warning(f"Failed to record metric: {metric_error}")
                
                # Wait a bit longer on error with interruptible sleep
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=60
                    )
                    break  # Shutdown requested
                except asyncio.TimeoutError:
                    pass  # Continue after error backoff
    
    async def _check_all_journeys(self):
        """Check story opportunities for all active journeys with thread safety"""
        async with self._lock:
            if not self.active_journeys:
                return
            
            # Create a copy to avoid modification during iteration
            active_users = list(self.active_journeys)
        
        logger.debug(f"Checking story opportunities for {len(active_users)} active journeys")
        
        # Process users concurrently with limited parallelism
        max_concurrent = 10  # Limit concurrent checks for resource management
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def check_with_semaphore(user_id: str):
            async with semaphore:
                try:
                    await self._check_journey_story_opportunity(user_id)
                except Exception as e:
                    logger.error(
                        f"Error checking story opportunity for user {user_id}: {str(e)}",
                        exc_info=True
                    )
        
        # Run checks concurrently
        tasks = [check_with_semaphore(user_id) for user_id in active_users]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_journey_story_opportunity(self, user_id: str):
        """Check if a specific journey needs a story"""
        try:
            # Get current journey context from cache
            journey_data = await cache_manager.get(f"journey_context_{user_id}")
            if not journey_data:
                logger.debug(f"No journey context found for user {user_id}")
                return
            
            # Build journey context
            journey_context = JourneyContext(
                current_location=journey_data.get("current_location", {"lat": 0, "lng": 0}),
                current_time=datetime.utcnow(),
                journey_stage=journey_data.get("journey_stage", "cruise"),
                passengers=journey_data.get("passengers", [{"user_id": user_id}]),
                vehicle_info=journey_data.get("vehicle_info", {}),
                weather=journey_data.get("weather", {}),
                route_info=journey_data.get("route_info", {})
            )
            
            # Check with orchestrator
            orchestrator = self._get_orchestrator()
            should_tell_story = await orchestrator.check_story_opportunity(journey_context)
            
            if should_tell_story:
                logger.info(f"Story opportunity detected for user {user_id}")
                
                # Trigger story generation through the event system
                await self._trigger_story_generation(user_id, journey_context)
                
                # Record metric
                if METRICS_AVAILABLE:
                    try:
                        metrics.increment_counter("story_scheduler_triggers", 1)
                    except Exception as e:
                        pass
        
        except Exception as e:
            logger.error(f"Error in journey story check: {str(e)}")
            raise
    
    async def _trigger_story_generation(self, user_id: str, journey_context: JourneyContext):
        """Trigger story generation for a user"""
        try:
            # Determine story priority based on context
            priority = StoryPriority.MEDIUM
            trigger_type = StoryTriggerType.SCHEDULED
            
            # Check for special conditions
            if journey_context.journey_stage == "departure":
                priority = StoryPriority.HIGH
                trigger_type = StoryTriggerType.JOURNEY_MILESTONE
            elif journey_context.route_info.get("nearest_poi", {}).get("distance_km", 999) < 2:
                priority = StoryPriority.HIGH
                trigger_type = StoryTriggerType.POI_PROXIMITY
            
            # Queue the story
            story_id = story_queue_manager.queue_story(
                user_id=user_id,
                priority=priority,
                trigger_type=trigger_type,
                context={
                    "location": journey_context.current_location,
                    "stage": journey_context.journey_stage,
                    "weather": journey_context.weather,
                    "route_info": journey_context.route_info
                },
                poi_reference=journey_context.route_info.get("nearest_poi")
            )
            
            if story_id:
                # Set a flag in cache that the API can check
                await cache_manager.set(
                    f"pending_story_{user_id}",
                    {
                        "story_id": story_id,
                        "triggered_at": datetime.utcnow().isoformat(),
                        "journey_context": {
                            "location": journey_context.current_location,
                            "stage": journey_context.journey_stage,
                            "weather": journey_context.weather
                        }
                    },
                    ttl=300  # 5 minutes
                )
                
                logger.info(f"Story generation triggered for user {user_id}, story_id: {story_id}")
            else:
                logger.warning(f"Failed to queue story for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error triggering story generation: {str(e)}")
    
    async def add_active_journey(self, user_id: str):
        """Add a journey to active monitoring with thread safety"""
        async with self._lock:
            self.active_journeys.add(user_id)
            journey_count = len(self.active_journeys)
        
        logger.info(f"Added user {user_id} to active journey monitoring")
        
        # Record metric
        if METRICS_AVAILABLE:
            try:
                metrics.set_gauge("active_journeys_count", journey_count)
            except Exception as e:
                logger.warning(f"Failed to record metric: {e}")
    
    async def remove_active_journey(self, user_id: str):
        """Remove a journey from active monitoring with thread safety"""
        async with self._lock:
            self.active_journeys.discard(user_id)
            journey_count = len(self.active_journeys)
        
        logger.info(f"Removed user {user_id} from active journey monitoring")
        
        # Record metric
        if METRICS_AVAILABLE:
            try:
                metrics.set_gauge("active_journeys_count", journey_count)
            except Exception as e:
                logger.warning(f"Failed to record metric: {e}")
    
    async def is_journey_active(self, user_id: str) -> bool:
        """Check if a journey is being monitored with thread safety"""
        async with self._lock:
            return user_id in self.active_journeys


# Global scheduler instance
story_scheduler = StoryOpportunityScheduler()