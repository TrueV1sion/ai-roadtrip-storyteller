"""
Story Queue Manager - Manages and prioritizes story opportunities

This service queues stories for perfect moments and ensures optimal delivery timing.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from enum import Enum
import heapq
import asyncio
from uuid import uuid4
import threading
from concurrent.futures import ThreadPoolExecutor
import weakref
from collections import defaultdict

from app.core.logger import get_logger

logger = get_logger(__name__)


class StoryPriority(Enum):
    """Story priority levels"""
    IMMEDIATE = 1     # User request, critical safety
    HIGH = 2          # Perfect moments (POI, golden hour)
    MEDIUM = 3        # Regular timing intervals
    LOW = 4           # Background/filler stories
    DEFERRED = 5      # Can wait indefinitely


class StoryTriggerType(Enum):
    """Types of story triggers"""
    USER_REQUEST = "user_request"
    POI_PROXIMITY = "poi_proximity"
    GOLDEN_HOUR = "golden_hour"
    JOURNEY_MILESTONE = "journey_milestone"
    SCHEDULED = "scheduled"
    CONTEXTUAL = "contextual"
    SAFETY = "safety"


@dataclass
class QueuedStory:
    """A story waiting to be told"""
    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    priority: StoryPriority = StoryPriority.MEDIUM
    trigger_type: StoryTriggerType = StoryTriggerType.SCHEDULED
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Timing constraints
    earliest_time: datetime = field(default_factory=datetime.utcnow)
    latest_time: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    # Story details
    story_theme: Optional[str] = None
    poi_reference: Optional[Dict[str, Any]] = None
    estimated_duration_seconds: int = 60
    
    # State
    created_at: datetime = field(default_factory=datetime.utcnow)
    attempts: int = 0
    last_attempt: Optional[datetime] = None
    delivered: bool = False
    delivered_at: Optional[datetime] = None
    
    def __lt__(self, other):
        """Compare for priority queue ordering"""
        # Lower priority value = higher priority
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        # Earlier earliest_time = higher priority for same priority level
        return self.earliest_time < other.earliest_time
    
    def is_ready(self, current_time: datetime = None) -> bool:
        """Check if story is ready to be delivered"""
        current_time = current_time or datetime.utcnow()
        
        # Check if expired
        if self.expires_at and current_time > self.expires_at:
            return False
        
        # Check if too early
        if current_time < self.earliest_time:
            return False
        
        # Check if too late
        if self.latest_time and current_time > self.latest_time:
            return False
        
        return not self.delivered
    
    def should_retry(self) -> bool:
        """Check if story should be retried after failure"""
        return self.attempts < 3 and not self.delivered


class StoryQueueManager:
    """Manages story queues for all active users with thread safety"""
    
    def __init__(self):
        """Initialize the queue manager"""
        # User-specific priority queues
        self.user_queues: Dict[str, List[QueuedStory]] = {}
        
        # Global story registry with TTL tracking
        self.all_stories: Dict[str, QueuedStory] = {}
        self._story_timestamps: Dict[str, datetime] = {}  # Track creation time for cleanup
        
        # Active story delivery tracking
        self.stories_in_progress: Set[str] = set()
        
        # Thread safety
        self._lock = threading.RLock()  # Reentrant lock for nested calls
        self._cleanup_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="story_cleanup")
        self._last_cleanup = datetime.utcnow()
        self._cleanup_interval_minutes = 5
        
        # Configuration
        self.max_queue_size_per_user = 10
        self.default_story_expiry_minutes = 30
        self.min_story_spacing_seconds = 90
        self.max_story_age_hours = 24  # Remove stories older than this
        
        logger.info("Story Queue Manager initialized with thread safety")
    
    def queue_story(
        self,
        user_id: str,
        priority: StoryPriority,
        trigger_type: StoryTriggerType,
        context: Dict[str, Any],
        **kwargs
    ) -> str:
        """
        Queue a story for delivery with thread safety.
        
        Returns story ID or empty string if rejected.
        """
        story = QueuedStory(
            user_id=user_id,
            priority=priority,
            trigger_type=trigger_type,
            context=context,
            **kwargs
        )
        
        # Set default expiry if not specified
        if not story.expires_at:
            story.expires_at = datetime.utcnow() + timedelta(
                minutes=self.default_story_expiry_minutes
            )
        
        with self._lock:
            # Initialize user queue if needed
            if user_id not in self.user_queues:
                self.user_queues[user_id] = []
            
            # Check queue size limit
            if len(self.user_queues[user_id]) >= self.max_queue_size_per_user:
                # Remove lowest priority expired stories
                self._cleanup_user_queue(user_id)
                
                # If still full, reject if this isn't high priority
                if (len(self.user_queues[user_id]) >= self.max_queue_size_per_user and 
                    priority.value > StoryPriority.HIGH.value):
                    logger.warning(f"Story queue full for user {user_id}, rejecting low priority story")
                    return ""
            
            # Add to queue
            heapq.heappush(self.user_queues[user_id], story)
            self.all_stories[story.id] = story
            self._story_timestamps[story.id] = datetime.utcnow()
            
            queue_size = len(self.user_queues[user_id])
        
        # Trigger cleanup if needed (outside lock)
        self._maybe_trigger_cleanup()
        
        logger.info(
            f"Story queued: {story.id}",
            extra={
                "user_id": user_id,
                "priority": priority.name,
                "trigger_type": trigger_type.value,
                "queue_size": queue_size
            }
        )
        
        return story.id
    
    def get_next_story(self, user_id: str, current_time: datetime = None) -> Optional[QueuedStory]:
        """
        Get the next story ready for delivery.
        
        Returns None if no story is ready.
        """
        current_time = current_time or datetime.utcnow()
        
        if user_id not in self.user_queues:
            return None
        
        # Clean up expired stories first
        self._cleanup_user_queue(user_id)
        
        # Find next ready story
        while self.user_queues[user_id]:
            # Peek at highest priority story
            story = self.user_queues[user_id][0]
            
            # Skip if already delivered or in progress
            if story.delivered or story.id in self.stories_in_progress:
                heapq.heappop(self.user_queues[user_id])
                continue
            
            # Check if ready
            if story.is_ready(current_time):
                # Check minimum spacing from last story
                if self._check_story_spacing(user_id, current_time):
                    return story
                else:
                    logger.debug(f"Story {story.id} ready but too soon after last story")
                    return None
            
            # If highest priority isn't ready, nothing is
            break
        
        return None
    
    def mark_story_delivered(self, story_id: str, success: bool = True):
        """Mark a story as delivered or failed"""
        if story_id not in self.all_stories:
            logger.warning(f"Unknown story ID: {story_id}")
            return
        
        story = self.all_stories[story_id]
        
        if success:
            story.delivered = True
            story.delivered_at = datetime.utcnow()
            
            # Remove from queue
            if story.user_id in self.user_queues:
                self.user_queues[story.user_id] = [
                    s for s in self.user_queues[story.user_id] 
                    if s.id != story_id
                ]
                heapq.heapify(self.user_queues[story.user_id])
            
            logger.info(f"Story {story_id} delivered successfully")
        else:
            story.attempts += 1
            story.last_attempt = datetime.utcnow()
            
            if not story.should_retry():
                # Give up on this story
                story.delivered = True  # Mark as delivered to remove from queue
                logger.warning(f"Story {story_id} failed after {story.attempts} attempts")
            else:
                # Will retry later
                logger.info(f"Story {story_id} failed, will retry (attempt {story.attempts})")
        
        # Remove from in-progress
        self.stories_in_progress.discard(story_id)
    
    def mark_story_in_progress(self, story_id: str):
        """Mark a story as being delivered"""
        self.stories_in_progress.add(story_id)
    
    def _cleanup_user_queue(self, user_id: str):
        """Remove expired and delivered stories from user queue"""
        current_time = datetime.utcnow()
        
        if user_id not in self.user_queues:
            return
        
        # Filter out expired and delivered stories
        active_stories = [
            story for story in self.user_queues[user_id]
            if not story.delivered and 
            (not story.expires_at or story.expires_at > current_time)
        ]
        
        # Rebuild heap
        self.user_queues[user_id] = active_stories
        heapq.heapify(self.user_queues[user_id])
    
    def _check_story_spacing(self, user_id: str, current_time: datetime) -> bool:
        """Check if enough time has passed since last story"""
        # Find most recent delivered story
        recent_stories = [
            story for story in self.all_stories.values()
            if story.user_id == user_id and 
            story.delivered and 
            story.delivered_at
        ]
        
        if not recent_stories:
            return True
        
        last_story = max(recent_stories, key=lambda s: s.delivered_at)
        time_since_last = (current_time - last_story.delivered_at).total_seconds()
        
        return time_since_last >= self.min_story_spacing_seconds
    
    def get_queue_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics about a user's story queue"""
        if user_id not in self.user_queues:
            return {
                "queue_size": 0,
                "stories_by_priority": {},
                "next_story_ready": False
            }
        
        queue = self.user_queues[user_id]
        
        # Count by priority
        priority_counts = {}
        for story in queue:
            if not story.delivered:
                priority_name = story.priority.name
                priority_counts[priority_name] = priority_counts.get(priority_name, 0) + 1
        
        # Check if next story is ready
        next_story = self.get_next_story(user_id)
        
        return {
            "queue_size": len([s for s in queue if not s.delivered]),
            "stories_by_priority": priority_counts,
            "next_story_ready": next_story is not None,
            "next_story_priority": next_story.priority.name if next_story else None,
            "in_progress_count": len([s for s in self.stories_in_progress if s in [story.id for story in queue]])
        }
    
    def clear_user_queue(self, user_id: str):
        """Clear all stories for a user with thread safety"""
        with self._lock:
            if user_id in self.user_queues:
                # Mark all as delivered to prevent delivery
                for story in self.user_queues[user_id]:
                    story.delivered = True
                
                self.user_queues[user_id] = []
            
        logger.info(f"Cleared story queue for user {user_id}")
    
    def _maybe_trigger_cleanup(self):
        """Trigger cleanup if enough time has passed"""
        now = datetime.utcnow()
        if (now - self._last_cleanup).total_seconds() > self._cleanup_interval_minutes * 60:
            self._cleanup_executor.submit(self._cleanup_old_stories)
            self._last_cleanup = now
    
    def _cleanup_old_stories(self):
        """Remove old stories from registry to prevent memory leak"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=self.max_story_age_hours)
            
            with self._lock:
                # Find stories to remove
                stories_to_remove = [
                    story_id for story_id, timestamp in self._story_timestamps.items()
                    if timestamp < cutoff_time
                ]
                
                # Remove old stories
                for story_id in stories_to_remove:
                    self.all_stories.pop(story_id, None)
                    self._story_timestamps.pop(story_id, None)
                    self.stories_in_progress.discard(story_id)
                
                if stories_to_remove:
                    logger.info(f"Cleaned up {len(stories_to_remove)} old stories from registry")
                    
        except Exception as e:
            logger.error(f"Error during story cleanup: {str(e)}", exc_info=True)
    
    def shutdown(self):
        """Shutdown the queue manager cleanly"""
        self._cleanup_executor.shutdown(wait=True)
        logger.info("Story queue manager shutdown complete")


# Global queue manager instance
story_queue_manager = StoryQueueManager()