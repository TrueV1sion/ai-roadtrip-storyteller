"""
Passenger Engagement Tracker - Monitors and calculates user engagement levels
Used by the story timing system to adjust story frequency based on passenger interest
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import math
from collections import deque

from app.core.logger import get_logger

logger = get_logger(__name__)

# Try to import metrics, but make it optional
try:
    from app.monitoring.metrics import metrics
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    logger.warning("Metrics not available - metrics recording disabled")


class EngagementEventType(Enum):
    """Types of engagement events with their impact scores"""
    USER_REQUEST_STORY = "user_request_story"           # Weight: 1.0
    USER_FOLLOWUP_QUESTION = "user_followup_question"   # Weight: 0.9
    USER_POSITIVE_RESPONSE = "user_positive_response"   # Weight: 0.8
    USER_INTERACTION = "user_interaction"               # Weight: 0.7
    STORY_COMPLETED = "story_completed"                 # Weight: 0.6
    USER_NEUTRAL_RESPONSE = "user_neutral_response"     # Weight: 0.5
    STORY_STARTED = "story_started"                     # Weight: 0.4
    STORY_SKIPPED = "story_skipped"                     # Weight: 0.2
    USER_NEGATIVE_RESPONSE = "user_negative_response"   # Weight: 0.15
    USER_SAYS_STOP = "user_says_stop"                   # Weight: 0.1
    NO_RESPONSE = "no_response"                         # Weight: 0.3


@dataclass
class EngagementEvent:
    """Single engagement event with metadata"""
    event_type: EngagementEventType
    timestamp: datetime
    weight: float
    metadata: Optional[Dict] = None
    
    def age_minutes(self) -> float:
        """Get age of event in minutes"""
        return (datetime.utcnow() - self.timestamp).total_seconds() / 60


class PassengerEngagementTracker:
    """Tracks passenger engagement over time"""
    
    # Event type weights (how much each event contributes to engagement)
    EVENT_WEIGHTS = {
        EngagementEventType.USER_REQUEST_STORY: 1.0,
        EngagementEventType.USER_FOLLOWUP_QUESTION: 0.9,
        EngagementEventType.USER_POSITIVE_RESPONSE: 0.8,
        EngagementEventType.USER_INTERACTION: 0.7,
        EngagementEventType.STORY_COMPLETED: 0.6,
        EngagementEventType.USER_NEUTRAL_RESPONSE: 0.5,
        EngagementEventType.STORY_STARTED: 0.4,
        EngagementEventType.NO_RESPONSE: 0.3,
        EngagementEventType.STORY_SKIPPED: 0.2,
        EngagementEventType.USER_NEGATIVE_RESPONSE: 0.15,
        EngagementEventType.USER_SAYS_STOP: 0.1,
    }
    
    # Time decay parameters
    RELEVANCE_WINDOW_MINUTES = 10.0  # Events older than this have reduced impact
    DECAY_HALF_LIFE_MINUTES = 5.0    # Half-life for exponential decay
    MAX_EVENT_AGE_MINUTES = 30.0      # Events older than this are ignored
    
    # Engagement calculation parameters
    MIN_EVENTS_FOR_CALCULATION = 1   # Need at least this many events
    DEFAULT_ENGAGEMENT = 0.5          # Default when no recent events
    
    def __init__(self, user_id: str):
        """Initialize tracker for a specific user"""
        self.user_id = user_id
        self.events: deque = deque(maxlen=100)  # Keep last 100 events
        self.last_calculation_time = None
        self.last_engagement_level = self.DEFAULT_ENGAGEMENT
        
    def record_event(
        self, 
        event_type: EngagementEventType,
        metadata: Optional[Dict] = None
    ) -> None:
        """Record a new engagement event"""
        try:
            weight = self.EVENT_WEIGHTS.get(event_type, 0.5)
            
            event = EngagementEvent(
                event_type=event_type,
                timestamp=datetime.utcnow(),
                weight=weight,
                metadata=metadata or {}
            )
            
            self.events.append(event)
            
            logger.info(
                f"Engagement event recorded: {event_type.value}",
                extra={
                    "user_id": self.user_id,
                    "event_type": event_type.value,
                    "weight": weight,
                    "metadata": metadata
                }
            )
            
            # Record metrics if available
            if METRICS_AVAILABLE:
                try:
                    # Count engagement events by type
                    metrics.increment_counter(f"engagement_event_{event_type.value}", 1)
                    
                    # Track event weights
                    metrics.observe_histogram("engagement_event_weight", weight)
                except Exception as e:
                    logger.warning(f"Failed to record engagement metrics: {str(e)}")
            
            # Log special events
            if event_type == EngagementEventType.USER_SAYS_STOP:
                logger.warning(
                    f"User {self.user_id} requested to stop stories",
                    extra={"metadata": metadata}
                )
            elif event_type == EngagementEventType.USER_REQUEST_STORY:
                logger.info(
                    f"User {self.user_id} explicitly requested a story",
                    extra={"metadata": metadata}
                )
                
        except Exception as e:
            logger.error(f"Error recording engagement event: {str(e)}")
    
    def get_current_engagement_level(self) -> float:
        """
        Calculate current engagement level (0.0 to 1.0).
        Higher values indicate more engaged passengers.
        """
        try:
            now = datetime.utcnow()
            
            # Get recent events within max age
            recent_events = [
                event for event in self.events
                if event.age_minutes() <= self.MAX_EVENT_AGE_MINUTES
            ]
            
            if len(recent_events) < self.MIN_EVENTS_FOR_CALCULATION:
                # Not enough recent events, return default
                return self.DEFAULT_ENGAGEMENT
            
            # Calculate weighted engagement with time decay
            total_weighted_score = 0.0
            total_decay_weight = 0.0
            
            for event in recent_events:
                age_minutes = event.age_minutes()
                
                # Apply exponential decay based on age
                decay_factor = self._calculate_decay_factor(age_minutes)
                
                # Apply additional penalty for events outside relevance window
                if age_minutes > self.RELEVANCE_WINDOW_MINUTES:
                    decay_factor *= 0.5
                
                weighted_score = event.weight * decay_factor
                total_weighted_score += weighted_score
                total_decay_weight += decay_factor
            
            # Calculate average engagement
            if total_decay_weight > 0:
                engagement_level = total_weighted_score / total_decay_weight
            else:
                engagement_level = self.DEFAULT_ENGAGEMENT
            
            # Apply smoothing to prevent rapid changes
            if self.last_engagement_level is not None:
                smoothing_factor = 0.7  # 70% new value, 30% old value
                engagement_level = (
                    smoothing_factor * engagement_level +
                    (1 - smoothing_factor) * self.last_engagement_level
                )
            
            # Clamp to valid range
            engagement_level = max(0.0, min(1.0, engagement_level))
            
            # Update state
            self.last_calculation_time = now
            self.last_engagement_level = engagement_level
            
            # Log and track metrics
            logger.debug(
                f"Engagement level calculated: {engagement_level:.2f}",
                extra={
                    "user_id": self.user_id,
                    "recent_events_count": len(recent_events),
                    "engagement_level": engagement_level
                }
            )
            
            # Record engagement level metric if available
            if METRICS_AVAILABLE:
                try:
                    metrics.set_gauge("passenger_engagement_level", engagement_level)
                    metrics.observe_histogram("engagement_calculation_events_count", len(recent_events))
                except Exception as e:
                    logger.warning(f"Failed to record engagement level metrics: {str(e)}")
            
            return round(engagement_level, 2)
            
        except Exception as e:
            logger.error(f"Error calculating engagement level: {str(e)}")
            return self.DEFAULT_ENGAGEMENT
    
    def _calculate_decay_factor(self, age_minutes: float) -> float:
        """Calculate exponential decay factor for event age with error handling"""
        try:
            if age_minutes < 0:
                logger.warning(f"Negative age_minutes: {age_minutes}, using 0")
                age_minutes = 0
            
            # Prevent overflow for very large age values
            if age_minutes > 1440:  # More than 24 hours
                return 0.0
            
            # Exponential decay: e^(-λt) where λ = ln(2)/half_life
            decay_rate = math.log(2) / self.DECAY_HALF_LIFE_MINUTES
            return math.exp(-decay_rate * age_minutes)
            
        except (ValueError, OverflowError) as e:
            logger.error(f"Math error in decay calculation: {str(e)}")
            return 0.0
    
    def get_recent_event_summary(self, window_minutes: float = 10.0) -> Dict[str, int]:
        """Get summary of recent events by type"""
        summary = {}
        cutoff_time = datetime.utcnow() - timedelta(minutes=window_minutes)
        
        for event in self.events:
            if event.timestamp >= cutoff_time:
                event_type_name = event.event_type.value
                summary[event_type_name] = summary.get(event_type_name, 0) + 1
        
        return summary
    
    def get_engagement_trend(self) -> str:
        """
        Determine if engagement is trending up, down, or stable.
        
        Returns: "increasing", "decreasing", or "stable"
        """
        if len(self.events) < 5:
            return "stable"
        
        # Compare recent vs older events
        recent_events = [e for e in self.events if e.age_minutes() <= 5]
        older_events = [e for e in self.events if 5 < e.age_minutes() <= 15]
        
        if not recent_events or not older_events:
            return "stable"
        
        recent_avg = sum(e.weight for e in recent_events) / len(recent_events)
        older_avg = sum(e.weight for e in older_events) / len(older_events)
        
        if recent_avg > older_avg * 1.2:
            return "increasing"
        elif recent_avg < older_avg * 0.8:
            return "decreasing"
        else:
            return "stable"
    
    def should_pause_stories(self) -> bool:
        """
        Check if stories should be paused based on negative signals.
        
        Returns True if user has indicated they want stories to stop.
        """
        # Check for recent stop request
        recent_stop = any(
            event.event_type == EngagementEventType.USER_SAYS_STOP and 
            event.age_minutes() < 30
            for event in self.events
        )
        
        if recent_stop:
            return True
        
        # Check for multiple negative responses
        recent_negative_count = sum(
            1 for event in self.events
            if event.event_type == EngagementEventType.USER_NEGATIVE_RESPONSE and
            event.age_minutes() < 10
        )
        
        return recent_negative_count >= 3
    
    def reset(self) -> None:
        """Reset engagement tracking (e.g., for new journey)"""
        self.events.clear()
        self.last_calculation_time = None
        self.last_engagement_level = self.DEFAULT_ENGAGEMENT
        logger.info(f"Engagement tracking reset for user {self.user_id}")
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get current state summary for debugging/logging"""
        return {
            "user_id": self.user_id,
            "current_engagement": self.get_current_engagement_level(),
            "total_events": len(self.events),
            "recent_events": self.get_recent_event_summary(),
            "trend": self.get_engagement_trend(),
            "should_pause": self.should_pause_stories(),
            "last_event": (
                self.events[-1].event_type.value if self.events else None
            )
        }