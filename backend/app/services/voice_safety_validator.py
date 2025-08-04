"""
Voice Interaction Safety Validator Service

Ensures all voice interactions comply with driving safety requirements
and hands-free regulations.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import logging
from dataclasses import dataclass, field

from app.core.config import get_settings
from app.services.driving_assistant import DrivingContext
from app.services.navigation.navigationService import NavigationService

logger = logging.getLogger(__name__)
settings = get_settings()


class SafetyLevel(Enum):
    """Safety levels for different driving conditions"""
    PARKED = "parked"  # Vehicle is stopped
    LOW_SPEED = "low_speed"  # < 25 mph, residential
    MODERATE = "moderate"  # 25-55 mph, normal driving
    HIGHWAY = "highway"  # > 55 mph
    CRITICAL = "critical"  # Complex maneuvers, merging, etc.
    EMERGENCY = "emergency"  # Emergency vehicles, hazards


class InteractionComplexity(Enum):
    """Complexity levels for voice interactions"""
    SIMPLE = "simple"  # Yes/no, single word responses
    MODERATE = "moderate"  # Short phrases, selections
    COMPLEX = "complex"  # Multi-step, requires thinking
    PROHIBITED = "prohibited"  # Not allowed while driving


@dataclass
class SafetyContext:
    """Current safety context for the vehicle"""
    safety_level: SafetyLevel
    speed_mph: float
    is_navigating: bool
    upcoming_maneuver_distance: Optional[float] = None
    traffic_density: str = "normal"  # light, normal, heavy
    weather_condition: str = "clear"  # clear, rain, snow, fog
    time_since_last_interaction: timedelta = field(default_factory=lambda: timedelta(0))
    interaction_count_last_minute: int = 0
    driver_fatigue_score: float = 0.0  # 0-1, higher is more fatigued


@dataclass
class SafetyValidation:
    """Result of safety validation"""
    is_safe: bool
    safety_score: float  # 0-1, higher is safer
    allowed_complexity: InteractionComplexity
    warnings: List[str] = field(default_factory=list)
    restrictions: List[str] = field(default_factory=list)
    recommended_delay_seconds: float = 0.0


@dataclass
class InteractionMetrics:
    """Metrics for a voice interaction"""
    duration_seconds: float
    complexity: InteractionComplexity
    was_interrupted: bool
    error_count: int
    timestamp: datetime
    safety_level_at_time: SafetyLevel


class VoiceSafetyValidator:
    """Validates and monitors voice interaction safety"""
    
    def __init__(self, navigation_service: NavigationService):
        self.navigation_service = navigation_service
        self.current_context: Optional[SafetyContext] = None
        self.interaction_history: List[InteractionMetrics] = []
        self.emergency_stop_active = False
        self.safety_overrides: Dict[str, Any] = {}
        
        # Safety thresholds
        self.CRITICAL_MANEUVER_DISTANCE = 0.25  # miles
        self.MAX_INTERACTIONS_PER_MINUTE = 3
        self.MAX_INTERACTION_DURATION = {
            SafetyLevel.PARKED: 60.0,
            SafetyLevel.LOW_SPEED: 10.0,
            SafetyLevel.MODERATE: 5.0,
            SafetyLevel.HIGHWAY: 3.0,
            SafetyLevel.CRITICAL: 0.0,
            SafetyLevel.EMERGENCY: 0.0
        }
        
        # Complexity allowed by safety level
        self.ALLOWED_COMPLEXITY = {
            SafetyLevel.PARKED: InteractionComplexity.COMPLEX,
            SafetyLevel.LOW_SPEED: InteractionComplexity.MODERATE,
            SafetyLevel.MODERATE: InteractionComplexity.SIMPLE,
            SafetyLevel.HIGHWAY: InteractionComplexity.SIMPLE,
            SafetyLevel.CRITICAL: InteractionComplexity.PROHIBITED,
            SafetyLevel.EMERGENCY: InteractionComplexity.PROHIBITED
        }
    
    async def update_context(self, driving_context: DrivingContext) -> SafetyContext:
        """Update current safety context from driving data"""
        safety_level = self._calculate_safety_level(driving_context)
        
        # Get navigation info
        nav_info = await self._get_navigation_info()
        
        # Calculate interaction metrics
        recent_interactions = self._get_recent_interactions(minutes=1)
        interaction_count = len(recent_interactions)
        
        # Calculate time since last interaction
        time_since_last = timedelta(minutes=5)  # Default
        if self.interaction_history:
            time_since_last = datetime.now() - self.interaction_history[-1].timestamp
        
        self.current_context = SafetyContext(
            safety_level=safety_level,
            speed_mph=driving_context.speed_mph,
            is_navigating=driving_context.is_navigating,
            upcoming_maneuver_distance=nav_info.get("next_maneuver_distance"),
            traffic_density=driving_context.traffic_condition,
            weather_condition=driving_context.weather_condition,
            time_since_last_interaction=time_since_last,
            interaction_count_last_minute=interaction_count,
            driver_fatigue_score=self._estimate_fatigue_score(driving_context)
        )
        
        return self.current_context
    
    async def validate_interaction(
        self,
        interaction_type: str,
        estimated_complexity: InteractionComplexity,
        estimated_duration: float
    ) -> SafetyValidation:
        """Validate if a voice interaction is safe to perform"""
        if not self.current_context:
            return SafetyValidation(
                is_safe=False,
                safety_score=0.0,
                allowed_complexity=InteractionComplexity.PROHIBITED,
                warnings=["No safety context available"],
                restrictions=["All interactions prohibited"]
            )
        
        # Check emergency stop
        if self.emergency_stop_active:
            return SafetyValidation(
                is_safe=False,
                safety_score=0.0,
                allowed_complexity=InteractionComplexity.PROHIBITED,
                warnings=["Emergency stop active"],
                restrictions=["All interactions prohibited"]
            )
        
        # Calculate safety score
        safety_score = self._calculate_safety_score()
        
        # Get allowed complexity for current context
        allowed_complexity = self.ALLOWED_COMPLEXITY.get(
            self.current_context.safety_level,
            InteractionComplexity.SIMPLE
        )
        
        # Build validation result
        warnings = []
        restrictions = []
        is_safe = True
        recommended_delay = 0.0
        
        # Check complexity
        if estimated_complexity.value > allowed_complexity.value:
            is_safe = False
            restrictions.append(f"Complexity too high for {self.current_context.safety_level.value} driving")
        
        # Check interaction frequency
        if self.current_context.interaction_count_last_minute >= self.MAX_INTERACTIONS_PER_MINUTE:
            warnings.append("High interaction frequency")
            recommended_delay = 30.0  # Wait 30 seconds
            if self.current_context.safety_level != SafetyLevel.PARKED:
                is_safe = False
                restrictions.append("Too many recent interactions")
        
        # Check upcoming maneuvers
        if self.current_context.upcoming_maneuver_distance:
            if self.current_context.upcoming_maneuver_distance < self.CRITICAL_MANEUVER_DISTANCE:
                is_safe = False
                restrictions.append("Critical maneuver approaching")
                recommended_delay = 60.0  # Wait until after maneuver
        
        # Check duration
        max_duration = self.MAX_INTERACTION_DURATION.get(
            self.current_context.safety_level,
            5.0
        )
        if estimated_duration > max_duration:
            warnings.append(f"Interaction too long (max {max_duration}s)")
            if self.current_context.safety_level != SafetyLevel.PARKED:
                is_safe = False
                restrictions.append("Duration exceeds safety limit")
        
        # Check fatigue
        if self.current_context.driver_fatigue_score > 0.7:
            warnings.append("High driver fatigue detected")
            safety_score *= 0.7
            if self.current_context.driver_fatigue_score > 0.85:
                is_safe = False
                restrictions.append("Driver fatigue too high")
        
        # Weather adjustments
        if self.current_context.weather_condition in ["rain", "snow", "fog"]:
            safety_score *= 0.8
            if self.current_context.safety_level == SafetyLevel.HIGHWAY:
                allowed_complexity = InteractionComplexity.PROHIBITED
                warnings.append(f"Poor weather conditions: {self.current_context.weather_condition}")
        
        # Traffic adjustments
        if self.current_context.traffic_density == "heavy":
            safety_score *= 0.8
            if self.current_context.safety_level != SafetyLevel.PARKED:
                allowed_complexity = min(allowed_complexity, InteractionComplexity.SIMPLE)
                warnings.append("Heavy traffic conditions")
        
        return SafetyValidation(
            is_safe=is_safe,
            safety_score=safety_score,
            allowed_complexity=allowed_complexity,
            warnings=warnings,
            restrictions=restrictions,
            recommended_delay_seconds=recommended_delay
        )
    
    async def record_interaction(self, metrics: InteractionMetrics):
        """Record completed interaction metrics"""
        self.interaction_history.append(metrics)
        
        # Keep only recent history (last hour)
        cutoff_time = datetime.now() - timedelta(hours=1)
        self.interaction_history = [
            m for m in self.interaction_history
            if m.timestamp > cutoff_time
        ]
        
        # Log if interaction was interrupted or had errors
        if metrics.was_interrupted:
            logger.info(f"Interaction interrupted after {metrics.duration_seconds}s")
        if metrics.error_count > 0:
            logger.warning(f"Interaction had {metrics.error_count} errors")
    
    async def emergency_stop(self):
        """Activate emergency stop for all voice interactions"""
        self.emergency_stop_active = True
        logger.warning("Emergency stop activated for voice interactions")
        
        # Auto-release after 30 seconds
        await asyncio.sleep(30)
        self.emergency_stop_active = False
        logger.info("Emergency stop released")
    
    def should_auto_pause(self) -> Tuple[bool, str]:
        """Check if interactions should be automatically paused"""
        if not self.current_context:
            return False, ""
        
        # Critical safety level
        if self.current_context.safety_level in [SafetyLevel.CRITICAL, SafetyLevel.EMERGENCY]:
            return True, f"Auto-paused: {self.current_context.safety_level.value} driving conditions"
        
        # Upcoming critical maneuver
        if self.current_context.upcoming_maneuver_distance:
            if self.current_context.upcoming_maneuver_distance < 0.1:  # 0.1 miles
                return True, "Auto-paused: Critical maneuver imminent"
        
        # High fatigue
        if self.current_context.driver_fatigue_score > 0.9:
            return True, "Auto-paused: High driver fatigue"
        
        return False, ""
    
    def get_safe_commands(self) -> List[str]:
        """Get list of always-safe voice commands"""
        if not self.current_context:
            return ["stop", "pause", "emergency", "help"]
        
        base_commands = ["stop", "pause", "quiet", "emergency", "help", "cancel"]
        
        if self.current_context.safety_level == SafetyLevel.PARKED:
            # All commands available when parked
            return None  # No restrictions
        elif self.current_context.safety_level in [SafetyLevel.LOW_SPEED, SafetyLevel.MODERATE]:
            return base_commands + [
                "yes", "no", "next", "previous",
                "louder", "quieter", "repeat",
                "play", "pause music", "skip"
            ]
        else:
            # Highway or critical - only essential commands
            return base_commands + ["yes", "no", "louder", "quieter"]
    
    def _calculate_safety_level(self, context: DrivingContext) -> SafetyLevel:
        """Calculate current safety level from driving context"""
        # Emergency conditions
        if context.emergency_vehicle_nearby:
            return SafetyLevel.EMERGENCY
        
        # Critical maneuvers
        if context.is_merging or context.complex_intersection:
            return SafetyLevel.CRITICAL
        
        # Speed-based levels
        if context.speed_mph == 0:
            return SafetyLevel.PARKED
        elif context.speed_mph < 25:
            return SafetyLevel.LOW_SPEED
        elif context.speed_mph < 55:
            return SafetyLevel.MODERATE
        else:
            return SafetyLevel.HIGHWAY
    
    def _calculate_safety_score(self) -> float:
        """Calculate overall safety score (0-1)"""
        if not self.current_context:
            return 0.0
        
        score = 1.0
        
        # Safety level factor
        level_scores = {
            SafetyLevel.PARKED: 1.0,
            SafetyLevel.LOW_SPEED: 0.9,
            SafetyLevel.MODERATE: 0.7,
            SafetyLevel.HIGHWAY: 0.5,
            SafetyLevel.CRITICAL: 0.2,
            SafetyLevel.EMERGENCY: 0.0
        }
        score *= level_scores.get(self.current_context.safety_level, 0.5)
        
        # Interaction frequency factor
        if self.current_context.interaction_count_last_minute > 0:
            frequency_factor = max(0.3, 1.0 - (self.current_context.interaction_count_last_minute * 0.2))
            score *= frequency_factor
        
        # Time since last interaction factor
        if self.current_context.time_since_last_interaction < timedelta(seconds=10):
            score *= 0.7
        
        # Fatigue factor
        score *= (1.0 - self.current_context.driver_fatigue_score * 0.5)
        
        return max(0.0, min(1.0, score))
    
    def _get_recent_interactions(self, minutes: int) -> List[InteractionMetrics]:
        """Get interactions from the last N minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [
            m for m in self.interaction_history
            if m.timestamp > cutoff_time
        ]
    
    async def _get_navigation_info(self) -> Dict[str, Any]:
        """Get current navigation information"""
        # This would integrate with the navigation service
        # Placeholder implementation
        return {
            "next_maneuver_distance": None,
            "route_complexity": "normal"
        }
    
    def _estimate_fatigue_score(self, context: DrivingContext) -> float:
        """Estimate driver fatigue based on trip duration and patterns"""
        # Simple estimation based on trip duration
        # In production, would use more sophisticated metrics
        hours_driving = context.trip_duration_minutes / 60.0
        
        if hours_driving < 1:
            return 0.0
        elif hours_driving < 2:
            return 0.2
        elif hours_driving < 3:
            return 0.4
        elif hours_driving < 4:
            return 0.6
        else:
            return min(0.9, 0.6 + (hours_driving - 4) * 0.1)


class SafetyMetricsCollector:
    """Collects and analyzes safety metrics"""
    
    def __init__(self):
        self.metrics_buffer: List[Dict[str, Any]] = []
        self.safety_incidents: List[Dict[str, Any]] = []
    
    async def log_safety_event(
        self,
        event_type: str,
        safety_score: float,
        context: SafetyContext,
        details: Dict[str, Any]
    ):
        """Log a safety-related event"""
        event = {
            "timestamp": datetime.now(),
            "event_type": event_type,
            "safety_score": safety_score,
            "safety_level": context.safety_level.value,
            "speed_mph": context.speed_mph,
            "details": details
        }
        
        self.metrics_buffer.append(event)
        
        # Check if this is a safety incident
        if safety_score < 0.3 or event_type in ["emergency_stop", "unsafe_interaction"]:
            self.safety_incidents.append(event)
            logger.warning(f"Safety incident logged: {event_type} (score: {safety_score})")
    
    async def generate_safety_report(self) -> Dict[str, Any]:
        """Generate safety metrics report"""
        if not self.metrics_buffer:
            return {"status": "no_data"}
        
        total_events = len(self.metrics_buffer)
        avg_safety_score = sum(e["safety_score"] for e in self.metrics_buffer) / total_events
        
        # Count events by safety level
        safety_level_counts = {}
        for event in self.metrics_buffer:
            level = event["safety_level"]
            safety_level_counts[level] = safety_level_counts.get(level, 0) + 1
        
        # Analyze incidents
        incident_types = {}
        for incident in self.safety_incidents:
            event_type = incident["event_type"]
            incident_types[event_type] = incident_types.get(event_type, 0) + 1
        
        return {
            "period": {
                "start": self.metrics_buffer[0]["timestamp"],
                "end": self.metrics_buffer[-1]["timestamp"]
            },
            "summary": {
                "total_events": total_events,
                "average_safety_score": avg_safety_score,
                "total_incidents": len(self.safety_incidents),
                "incident_rate": len(self.safety_incidents) / total_events if total_events > 0 else 0
            },
            "safety_levels": safety_level_counts,
            "incident_types": incident_types,
            "recommendations": self._generate_recommendations(avg_safety_score, incident_types)
        }
    
    def _generate_recommendations(
        self,
        avg_safety_score: float,
        incident_types: Dict[str, int]
    ) -> List[str]:
        """Generate safety recommendations based on metrics"""
        recommendations = []
        
        if avg_safety_score < 0.7:
            recommendations.append("Consider reducing interaction complexity during driving")
        
        if incident_types.get("high_frequency", 0) > 5:
            recommendations.append("Implement stricter interaction frequency limits")
        
        if incident_types.get("complexity_violation", 0) > 3:
            recommendations.append("Simplify voice commands for better safety")
        
        return recommendations