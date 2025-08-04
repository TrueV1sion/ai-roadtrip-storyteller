"""
Story Timing Orchestrator - Dynamic, context-aware story timing system
Replaces fixed 15-minute intervals with intelligent timing based on journey context
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from enum import Enum
import math

from app.core.logger import get_logger

logger = get_logger(__name__)

# Try to import metrics, but make it optional
try:
    from app.monitoring.metrics import metrics
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    logger.warning("Metrics not available - metrics recording disabled")


class JourneyPhase(Enum):
    """Phases of a journey with different timing characteristics"""
    DEPARTURE = "departure"
    EARLY = "early"
    CRUISE = "cruise"
    APPROACHING = "approaching"
    ARRIVAL = "arrival"
    UNKNOWN = "unknown"


class DrivingComplexity(Enum):
    """Driving complexity levels"""
    VERY_LOW = "very_low"    # Highway, no traffic
    LOW = "low"               # Light traffic, easy roads
    MODERATE = "moderate"     # Normal conditions
    HIGH = "high"            # City traffic, complex navigation
    VERY_HIGH = "very_high"  # Heavy traffic, construction, weather


@dataclass
class TimingContext:
    """Complete context for story timing decisions"""
    # Journey information
    journey_phase: JourneyPhase
    journey_progress: float  # 0.0 to 1.0
    total_distance_km: float
    remaining_distance_km: float
    elapsed_time_minutes: float
    
    # Driving conditions
    current_speed_kmh: float
    average_speed_kmh: float
    driving_complexity: DrivingComplexity
    is_highway: bool
    traffic_level: str  # light, moderate, heavy
    weather_condition: str  # clear, rain, snow, fog
    
    # Passenger context
    engagement_level: float  # 0.0 to 1.0
    passenger_count: int
    has_children: bool
    passenger_type: str  # family, friends, solo, business
    last_interaction_minutes: float
    
    # Environmental context
    time_of_day: datetime
    is_golden_hour: bool
    is_night_driving: bool
    
    # POI context
    nearest_poi_distance_km: Optional[float] = None
    nearest_poi_name: Optional[str] = None
    nearest_poi_type: Optional[str] = None
    
    # Story context
    stories_told_count: int = 0
    last_story_minutes_ago: Optional[float] = None
    last_story_was_interrupted: bool = False
    user_requested_story: bool = False


class StoryTimingOrchestrator:
    """Orchestrates dynamic story timing based on journey context"""
    
    # Base timing by journey phase (in minutes)
    BASE_TIMING = {
        JourneyPhase.DEPARTURE: 3.0,
        JourneyPhase.EARLY: 5.0,
        JourneyPhase.CRUISE: 6.0,
        JourneyPhase.APPROACHING: 4.0,
        JourneyPhase.ARRIVAL: 2.5,
        JourneyPhase.UNKNOWN: 5.0
    }
    
    # Multiplier ranges
    COMPLEXITY_MULTIPLIERS = {
        DrivingComplexity.VERY_LOW: 0.7,
        DrivingComplexity.LOW: 0.85,
        DrivingComplexity.MODERATE: 1.0,
        DrivingComplexity.HIGH: 2.0,
        DrivingComplexity.VERY_HIGH: 3.0
    }
    
    ENGAGEMENT_CURVE = {
        # engagement_level: multiplier
        1.0: 0.6,   # Very engaged - more frequent
        0.8: 0.7,
        0.6: 0.85,
        0.4: 1.0,
        0.2: 1.5,
        0.0: 1.8    # Disengaged - less frequent
    }
    
    PASSENGER_TYPE_MULTIPLIERS = {
        "family": 0.8,
        "children": 0.7,
        "friends": 0.85,
        "solo": 1.0,
        "business": 1.0
    }
    
    # Timing bounds
    MIN_INTERVAL_MINUTES = 1.5
    MAX_INTERVAL_MINUTES = 12.0
    
    # Perfect moment overrides
    POI_PROXIMITY_THRESHOLD_KM = 2.0
    POI_OVERRIDE_INTERVAL_SECONDS = 30
    GOLDEN_HOUR_MULTIPLIER = 0.5
    MILESTONE_MULTIPLIER = 0.4
    
    def __init__(self):
        """Initialize the timing orchestrator"""
        self.last_calculation_time = None
        self.last_reasoning = {}
        
    def calculate_next_story_time(self, context: TimingContext) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate the optimal time until the next story.
        
        Returns:
            Tuple of (minutes_until_next_story, reasoning_dict)
        """
        try:
            # Validate context
            if not self._validate_timing_context(context):
                logger.warning("Invalid timing context provided, using defaults")
                return 5.0, {"error": "Invalid context", "fallback": True}
            
            # Start with base timing for journey phase
            base_time = self.BASE_TIMING.get(context.journey_phase, 5.0)
            
            # Check for perfect moment overrides first
            override_time, override_reason = self._check_perfect_moment_overrides(context)
            if override_time is not None:
                reasoning = {
                    "base_time": base_time,
                    "override": override_reason,
                    "final_time": override_time,
                    "timestamp": datetime.utcnow().isoformat()
                }
                self._log_timing_decision(override_time, reasoning, context)
                return override_time, reasoning
            
            # Apply multipliers
            multipliers = {}
            
            # Driving complexity multiplier
            complexity_mult = self.COMPLEXITY_MULTIPLIERS.get(
                context.driving_complexity, 1.0
            )
            multipliers["driving_complexity"] = complexity_mult
            
            # Engagement multiplier (interpolated)
            engagement_mult = self._interpolate_engagement_multiplier(
                context.engagement_level
            )
            multipliers["engagement"] = engagement_mult
            
            # Passenger type multiplier
            passenger_mult = self._get_passenger_type_multiplier(context)
            multipliers["passenger_type"] = passenger_mult
            
            # Time of day multiplier
            time_mult = self._get_time_of_day_multiplier(context)
            multipliers["time_of_day"] = time_mult
            
            # Speed multiplier
            speed_mult = self._get_speed_multiplier(context)
            multipliers["speed"] = speed_mult
            
            # Calculate final timing
            total_multiplier = 1.0
            for mult_name, mult_value in multipliers.items():
                total_multiplier *= mult_value
            
            adjusted_time = base_time * total_multiplier
            
            # Apply bounds
            final_time = max(
                self.MIN_INTERVAL_MINUTES,
                min(self.MAX_INTERVAL_MINUTES, adjusted_time)
            )
            
            # Build reasoning
            reasoning = {
                "base_time": base_time,
                "journey_phase": context.journey_phase.value,
                "multipliers": multipliers,
                "total_multiplier": round(total_multiplier, 2),
                "adjusted_time": round(adjusted_time, 2),
                "final_time": round(final_time, 2),
                "bounded": adjusted_time != final_time,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self._log_timing_decision(final_time, reasoning, context)
            self.last_reasoning = reasoning
            
            return round(final_time, 1), reasoning
            
        except Exception as e:
            logger.error(f"Error calculating story timing: {str(e)}")
            # Fallback to safe default
            return 5.0, {"error": str(e), "fallback": True}
    
    def _check_perfect_moment_overrides(
        self, context: TimingContext
    ) -> Tuple[Optional[float], Optional[Dict[str, Any]]]:
        """Check for perfect moment conditions that override normal timing"""
        
        # User requested a story
        if context.user_requested_story:
            return 0.0, {"type": "user_request", "immediate": True}
        
        # Approaching POI
        if (context.nearest_poi_distance_km is not None and 
            context.nearest_poi_distance_km < self.POI_PROXIMITY_THRESHOLD_KM):
            
            # Only if we haven't told a story very recently
            if (context.last_story_minutes_ago is None or 
                context.last_story_minutes_ago > 1.0):
                
                return 0.5, {
                    "type": "approaching_poi",
                    "poi_name": context.nearest_poi_name,
                    "distance_km": context.nearest_poi_distance_km
                }
        
        # Golden hour override
        if context.is_golden_hour:
            # Check if it's been at least 2 minutes since last story
            if (context.last_story_minutes_ago is None or 
                context.last_story_minutes_ago > 2.0):
                
                base_time = self.BASE_TIMING.get(context.journey_phase, 5.0)
                golden_time = base_time * self.GOLDEN_HOUR_MULTIPLIER
                
                return golden_time, {
                    "type": "golden_hour",
                    "multiplier": self.GOLDEN_HOUR_MULTIPLIER
                }
        
        # Journey milestones (25%, 50%, 75% completion)
        milestones = [0.25, 0.5, 0.75]
        for milestone in milestones:
            if abs(context.journey_progress - milestone) < 0.02:  # Within 2%
                if (context.last_story_minutes_ago is None or 
                    context.last_story_minutes_ago > 3.0):
                    
                    base_time = self.BASE_TIMING.get(context.journey_phase, 5.0)
                    milestone_time = base_time * self.MILESTONE_MULTIPLIER
                    
                    return milestone_time, {
                        "type": "journey_milestone",
                        "milestone": f"{int(milestone * 100)}%",
                        "multiplier": self.MILESTONE_MULTIPLIER
                    }
        
        return None, None
    
    def _interpolate_engagement_multiplier(self, engagement_level: float) -> float:
        """Interpolate engagement multiplier from curve"""
        # Clamp engagement level
        engagement_level = max(0.0, min(1.0, engagement_level))
        
        # Find surrounding points
        levels = sorted(self.ENGAGEMENT_CURVE.keys(), reverse=True)
        
        for i in range(len(levels) - 1):
            if engagement_level >= levels[i + 1]:
                # Interpolate between levels[i] and levels[i+1]
                high_level = levels[i]
                low_level = levels[i + 1]
                high_mult = self.ENGAGEMENT_CURVE[high_level]
                low_mult = self.ENGAGEMENT_CURVE[low_level]
                
                # Linear interpolation
                ratio = (engagement_level - low_level) / (high_level - low_level)
                multiplier = low_mult + ratio * (high_mult - low_mult)
                
                return round(multiplier, 2)
        
        # If we get here, use the lowest level
        return self.ENGAGEMENT_CURVE[0.0]
    
    def _get_passenger_type_multiplier(self, context: TimingContext) -> float:
        """Get multiplier based on passenger type"""
        if context.has_children:
            return self.PASSENGER_TYPE_MULTIPLIERS["children"]
        
        return self.PASSENGER_TYPE_MULTIPLIERS.get(
            context.passenger_type, 1.0
        )
    
    def _get_time_of_day_multiplier(self, context: TimingContext) -> float:
        """Get multiplier based on time of day"""
        hour = context.time_of_day.hour
        
        # Early morning (5-7am) - people might be tired
        if 5 <= hour < 7:
            return 1.2
        
        # Rush hours - more stress, less stories
        if (7 <= hour < 9) or (17 <= hour < 19):
            return 1.3
        
        # Night driving - focus on road
        if context.is_night_driving:
            return 1.2
        
        # Normal hours
        return 1.0
    
    def _get_speed_multiplier(self, context: TimingContext) -> float:
        """Get multiplier based on speed"""
        # Very slow (traffic) - less frequent stories
        if context.current_speed_kmh < 30:
            return 1.2
        
        # Highway speeds - can be boring, more stories
        if context.current_speed_kmh > 90 and context.is_highway:
            return 0.8
        
        # Normal speeds
        return 1.0
    
    def _log_timing_decision(
        self, 
        timing_minutes: float, 
        reasoning: Dict[str, Any], 
        context: TimingContext
    ):
        """Log timing decision with detailed reasoning"""
        logger.info(
            f"Story timing calculated: {timing_minutes} minutes",
            extra={
                "timing_minutes": timing_minutes,
                "reasoning": reasoning,
                "journey_phase": context.journey_phase.value,
                "engagement_level": context.engagement_level,
                "driving_complexity": context.driving_complexity.value,
                "speed_kmh": context.current_speed_kmh
            }
        )
        
        # Record metrics if available
        if METRICS_AVAILABLE:
            try:
                # Record story timing interval histogram
                metrics.observe_histogram("story_timing_interval_minutes", timing_minutes)
                
                # Record engagement level gauge
                metrics.set_gauge("story_engagement_level", context.engagement_level)
                
                # Count timing decisions by journey phase
                metrics.increment_counter(f"story_timing_decisions_{context.journey_phase.value}", 1)
                
                # Count perfect moment overrides
                if "override" in reasoning:
                    override_type = reasoning["override"].get("type", "unknown")
                    metrics.increment_counter(f"story_timing_override_{override_type}", 1)
                
                # Record driving complexity distribution
                metrics.increment_counter(f"story_timing_complexity_{context.driving_complexity.value}", 1)
                
            except Exception as e:
                logger.warning(f"Failed to record metrics: {str(e)}")
    
    def get_timing_explanation(self) -> str:
        """Get human-readable explanation of last timing decision"""
        if not self.last_reasoning:
            return "No timing calculation performed yet"
        
        reasoning = self.last_reasoning
        base = reasoning.get("base_time", 0)
        final = reasoning.get("final_time", 0)
        
        if "override" in reasoning:
            override = reasoning["override"]
            if override.get("type") == "user_request":
                return "Immediate story - user requested"
            elif override.get("type") == "approaching_poi":
                return f"Approaching {override.get('poi_name', 'point of interest')} - story triggered"
            elif override.get("type") == "golden_hour":
                return "Golden hour moment - enhanced story timing"
            elif override.get("type") == "journey_milestone":
                return f"Journey milestone {override.get('milestone', '')} - celebration story"
        
        explanation = f"Base timing {base} min for {reasoning.get('journey_phase', 'journey')}"
        
        multipliers = reasoning.get("multipliers", {})
        if multipliers:
            factors = []
            if multipliers.get("driving_complexity", 1.0) > 1.5:
                factors.append("complex driving conditions")
            elif multipliers.get("driving_complexity", 1.0) < 0.8:
                factors.append("easy driving conditions")
            
            if multipliers.get("engagement", 1.0) < 0.8:
                factors.append("high passenger engagement")
            elif multipliers.get("engagement", 1.0) > 1.3:
                factors.append("low passenger engagement")
            
            if factors:
                explanation += f" adjusted for {', '.join(factors)}"
        
        if reasoning.get("bounded", False):
            explanation += f" (bounded to {final} min)"
        
        return explanation
    
    def _validate_timing_context(self, context: TimingContext) -> bool:
        """Validate timing context for reasonable values"""
        try:
            # Validate journey progress
            if not 0 <= context.journey_progress <= 1.0:
                logger.warning(f"Invalid journey progress: {context.journey_progress}")
                return False
            
            # Validate distances
            if context.total_distance_km < 0 or context.remaining_distance_km < 0:
                logger.warning("Negative distance values")
                return False
            
            # Validate speed
            if context.current_speed_kmh < 0 or context.current_speed_kmh > 300:
                logger.warning(f"Invalid speed: {context.current_speed_kmh}")
                return False
            
            # Validate engagement level
            if not 0 <= context.engagement_level <= 1.0:
                logger.warning(f"Invalid engagement level: {context.engagement_level}")
                return False
            
            # Validate passenger count
            if context.passenger_count < 0 or context.passenger_count > 20:
                logger.warning(f"Invalid passenger count: {context.passenger_count}")
                return False
            
            return True
            
        except AttributeError as e:
            logger.error(f"Missing required context attribute: {str(e)}")
            return False