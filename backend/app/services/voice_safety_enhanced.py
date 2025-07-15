"""
Enhanced Voice Safety Validator with Advanced Features
Includes speed-based complexity filtering, highway merge detection, and emergency overrides
"""
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import asyncio
import re
from geopy import distance
import numpy as np

from app.core.logger import get_logger
from app.services.voice_safety_validator import (
    VoiceSafetyValidator, 
    DrivingContext, 
    SafetyLevel,
    CommandComplexity
)

logger = get_logger(__name__)


class RoadType(Enum):
    """Types of roads for context-aware safety"""
    HIGHWAY = "highway"
    HIGHWAY_RAMP = "highway_ramp"
    URBAN = "urban"
    SUBURBAN = "suburban"
    RURAL = "rural"
    PARKING = "parking"
    CONSTRUCTION = "construction"
    SCHOOL_ZONE = "school_zone"


class MergeStatus(Enum):
    """Highway merge detection status"""
    NO_MERGE = "no_merge"
    APPROACHING_MERGE = "approaching_merge"
    ACTIVELY_MERGING = "actively_merging"
    COMPLETED_MERGE = "completed_merge"


@dataclass
class SpeedComplexityRule:
    """Rules for speed-based command complexity filtering"""
    min_speed: float  # mph
    max_speed: float  # mph
    allowed_complexity: List[CommandComplexity]
    response_delay_ms: int
    simplified_response: bool


@dataclass
class EmergencyCommand:
    """Emergency command definition"""
    pattern: str  # Regex pattern
    action: str
    priority: int  # 1 = highest
    bypass_all_safety: bool
    immediate_response: bool


class EnhancedVoiceSafetyValidator(VoiceSafetyValidator):
    """Enhanced voice safety with advanced features"""
    
    def __init__(self):
        super().__init__()
        self.speed_complexity_rules = self._init_speed_rules()
        self.emergency_commands = self._init_emergency_commands()
        self.merge_detector = HighwayMergeDetector()
        self.road_type_analyzer = RoadTypeAnalyzer()
        
        # Enhanced context tracking
        self.location_history: List[Tuple[float, float, datetime]] = []
        self.merge_history: List[Tuple[MergeStatus, datetime]] = []
        self.command_success_rate: Dict[str, float] = {}
        
    def _init_speed_rules(self) -> List[SpeedComplexityRule]:
        """Initialize speed-based complexity filtering rules"""
        return [
            # Parking/Stopped
            SpeedComplexityRule(
                min_speed=0,
                max_speed=5,
                allowed_complexity=[
                    CommandComplexity.SIMPLE,
                    CommandComplexity.MODERATE,
                    CommandComplexity.COMPLEX,
                    CommandComplexity.CRITICAL
                ],
                response_delay_ms=0,
                simplified_response=False
            ),
            # City driving
            SpeedComplexityRule(
                min_speed=5,
                max_speed=35,
                allowed_complexity=[
                    CommandComplexity.SIMPLE,
                    CommandComplexity.MODERATE,
                    CommandComplexity.CRITICAL
                ],
                response_delay_ms=0,
                simplified_response=False
            ),
            # Suburban driving
            SpeedComplexityRule(
                min_speed=35,
                max_speed=55,
                allowed_complexity=[
                    CommandComplexity.SIMPLE,
                    CommandComplexity.MODERATE,
                    CommandComplexity.CRITICAL
                ],
                response_delay_ms=100,
                simplified_response=True
            ),
            # Highway driving
            SpeedComplexityRule(
                min_speed=55,
                max_speed=75,
                allowed_complexity=[
                    CommandComplexity.SIMPLE,
                    CommandComplexity.CRITICAL
                ],
                response_delay_ms=200,
                simplified_response=True
            ),
            # High-speed highway
            SpeedComplexityRule(
                min_speed=75,
                max_speed=999,
                allowed_complexity=[
                    CommandComplexity.SIMPLE,
                    CommandComplexity.CRITICAL
                ],
                response_delay_ms=300,
                simplified_response=True
            )
        ]
    
    def _init_emergency_commands(self) -> List[EmergencyCommand]:
        """Initialize emergency override commands"""
        return [
            EmergencyCommand(
                pattern=r"(call|dial).*(911|nine one one|emergency)",
                action="emergency_call",
                priority=1,
                bypass_all_safety=True,
                immediate_response=True
            ),
            EmergencyCommand(
                pattern=r"(emergency|help|accident|crash)",
                action="emergency_assist",
                priority=1,
                bypass_all_safety=True,
                immediate_response=True
            ),
            EmergencyCommand(
                pattern=r"(stop|cancel|abort).*(everything|all|now)",
                action="emergency_stop",
                priority=2,
                bypass_all_safety=True,
                immediate_response=True
            ),
            EmergencyCommand(
                pattern=r"(nearest|find).*(hospital|emergency|police)",
                action="find_emergency_services",
                priority=2,
                bypass_all_safety=True,
                immediate_response=True
            ),
            EmergencyCommand(
                pattern=r"(pull over|stop.*car|stop.*vehicle)",
                action="safe_stop_guidance",
                priority=3,
                bypass_all_safety=True,
                immediate_response=True
            )
        ]
    
    async def validate_command_enhanced(
        self,
        command: str,
        context: DrivingContext
    ) -> Dict[str, Any]:
        """Enhanced command validation with all safety features"""
        
        # Check for emergency commands first
        emergency_check = self._check_emergency_command(command)
        if emergency_check:
            logger.warning(f"Emergency command detected: {emergency_check['action']}")
            return {
                "safe": True,
                "complexity": CommandComplexity.CRITICAL,
                "safety_level": SafetyLevel.SAFE,
                "emergency": True,
                "action": emergency_check["action"],
                "immediate_response": emergency_check["immediate_response"],
                "bypass_safety": emergency_check["bypass_all_safety"]
            }
        
        # Update location history
        if context.location:
            self.location_history.append((
                context.location[0],
                context.location[1],
                datetime.now()
            ))
            # Keep only last 60 seconds of history
            cutoff = datetime.now() - timedelta(seconds=60)
            self.location_history = [
                loc for loc in self.location_history if loc[2] > cutoff
            ]
        
        # Detect road type
        road_type = await self.road_type_analyzer.analyze(
            context.location,
            context.speed,
            self.location_history
        )
        
        # Check for highway merge
        merge_status = await self.merge_detector.detect_merge(
            context.location,
            context.heading,
            context.speed,
            road_type
        )
        
        # Get base validation
        base_validation = await self.validate_command(command, context)
        
        # Apply speed-based complexity filtering
        speed_filtered = self._apply_speed_complexity_filter(
            command,
            context.speed,
            base_validation["complexity"]
        )
        
        # Adjust for merge conditions
        if merge_status in [MergeStatus.APPROACHING_MERGE, MergeStatus.ACTIVELY_MERGING]:
            if base_validation["complexity"] not in [CommandComplexity.SIMPLE, CommandComplexity.CRITICAL]:
                speed_filtered["safe"] = False
                speed_filtered["reason"] = "Complex commands disabled during highway merge"
                speed_filtered["defer_duration"] = 15  # seconds
        
        # Add enhanced context
        speed_filtered.update({
            "road_type": road_type.value,
            "merge_status": merge_status.value,
            "location_history_points": len(self.location_history),
            "enhanced_safety": True
        })
        
        # Track command success for adaptive learning
        self._track_command_pattern(command, context.speed, road_type)
        
        return speed_filtered
    
    def _check_emergency_command(self, command: str) -> Optional[Dict[str, Any]]:
        """Check if command is an emergency override"""
        command_lower = command.lower().strip()
        
        for emergency_cmd in self.emergency_commands:
            if re.search(emergency_cmd.pattern, command_lower):
                return {
                    "action": emergency_cmd.action,
                    "priority": emergency_cmd.priority,
                    "bypass_all_safety": emergency_cmd.bypass_all_safety,
                    "immediate_response": emergency_cmd.immediate_response
                }
        
        return None
    
    def _apply_speed_complexity_filter(
        self,
        command: str,
        speed: float,
        complexity: CommandComplexity
    ) -> Dict[str, Any]:
        """Apply speed-based complexity filtering"""
        
        # Find applicable rule
        applicable_rule = None
        for rule in self.speed_complexity_rules:
            if rule.min_speed <= speed <= rule.max_speed:
                applicable_rule = rule
                break
        
        if not applicable_rule:
            # Default to most restrictive
            applicable_rule = self.speed_complexity_rules[-1]
        
        # Check if complexity is allowed
        if complexity not in applicable_rule.allowed_complexity:
            return {
                "safe": False,
                "complexity": complexity,
                "safety_level": SafetyLevel.UNSAFE,
                "reason": f"Command too complex for current speed ({speed:.0f} mph)",
                "allowed_complexity": [c.value for c in applicable_rule.allowed_complexity],
                "defer_until_speed": applicable_rule.min_speed,
                "simplified_alternative": self._get_simplified_command(command)
            }
        
        # Command is allowed but may need modification
        result = {
            "safe": True,
            "complexity": complexity,
            "safety_level": SafetyLevel.SAFE,
            "response_delay_ms": applicable_rule.response_delay_ms,
            "simplified_response": applicable_rule.simplified_response
        }
        
        if applicable_rule.simplified_response:
            result["response_modifications"] = {
                "shorten_response": True,
                "skip_details": True,
                "use_simple_language": True,
                "max_response_duration": 5  # seconds
            }
        
        return result
    
    def _get_simplified_command(self, command: str) -> Optional[str]:
        """Get simplified alternative for complex command"""
        simplifications = {
            r"book.*hotel.*tonight.*near.*with.*pool": "Find hotels",
            r"navigate.*scenic.*route.*avoiding.*highways": "Navigate to destination",
            r"find.*restaurant.*italian.*outdoor.*seating": "Find restaurants",
            r"tell.*story.*history.*this.*area": "Tell story"
        }
        
        command_lower = command.lower()
        for pattern, simplified in simplifications.items():
            if re.search(pattern, command_lower):
                return simplified
        
        # Generic simplification
        if len(command.split()) > 5:
            return "Command saved for later"
        
        return None
    
    def _track_command_pattern(
        self,
        command: str,
        speed: float,
        road_type: RoadType
    ) -> None:
        """Track command patterns for adaptive learning"""
        pattern_key = f"{road_type.value}_{int(speed/10)*10}mph"
        
        if pattern_key not in self.command_success_rate:
            self.command_success_rate[pattern_key] = []
        
        # This would be updated with actual success/failure data
        # For now, we'll simulate based on complexity
        complexity = self._calculate_complexity(command)
        success_probability = {
            CommandComplexity.SIMPLE: 0.95,
            CommandComplexity.MODERATE: 0.85,
            CommandComplexity.COMPLEX: 0.70,
            CommandComplexity.CRITICAL: 0.99
        }
        
        self.command_success_rate[pattern_key].append(
            success_probability.get(complexity, 0.8)
        )
        
        # Keep only recent data
        if len(self.command_success_rate[pattern_key]) > 100:
            self.command_success_rate[pattern_key] = \
                self.command_success_rate[pattern_key][-100:]


class HighwayMergeDetector:
    """Detects highway merge conditions"""
    
    def __init__(self):
        self.merge_patterns = self._init_merge_patterns()
        self.last_detection = None
    
    def _init_merge_patterns(self) -> List[Dict[str, Any]]:
        """Initialize merge detection patterns"""
        return [
            {
                "name": "on_ramp_entry",
                "speed_range": (25, 45),
                "heading_change_rate": 0.5,  # degrees per second
                "duration": 10  # seconds
            },
            {
                "name": "acceleration_lane",
                "speed_range": (45, 65),
                "acceleration": 2.0,  # mph per second
                "heading_change_rate": 0.3
            },
            {
                "name": "active_merge",
                "speed_range": (55, 75),
                "lateral_movement": True,
                "heading_change_rate": 1.0
            }
        ]
    
    async def detect_merge(
        self,
        location: Optional[Tuple[float, float]],
        heading: Optional[float],
        speed: float,
        road_type: RoadType
    ) -> MergeStatus:
        """Detect highway merge status"""
        
        # Only check for highway-related roads
        if road_type not in [RoadType.HIGHWAY, RoadType.HIGHWAY_RAMP]:
            return MergeStatus.NO_MERGE
        
        # Check speed patterns
        if 25 <= speed <= 45 and road_type == RoadType.HIGHWAY_RAMP:
            return MergeStatus.APPROACHING_MERGE
        
        if 45 <= speed <= 65 and self._is_accelerating(speed):
            return MergeStatus.ACTIVELY_MERGING
        
        if speed > 65 and self._recently_merged():
            return MergeStatus.COMPLETED_MERGE
        
        return MergeStatus.NO_MERGE
    
    def _is_accelerating(self, current_speed: float) -> bool:
        """Check if vehicle is accelerating"""
        # This would use historical speed data
        # Simplified for now
        return True if 45 <= current_speed <= 65 else False
    
    def _recently_merged(self) -> bool:
        """Check if merge was recently completed"""
        if self.last_detection:
            time_since = datetime.now() - self.last_detection
            return time_since.total_seconds() < 30
        return False


class RoadTypeAnalyzer:
    """Analyzes road type from context"""
    
    def __init__(self):
        self.road_patterns = {
            RoadType.HIGHWAY: {
                "min_speed": 55,
                "straight_path": True,
                "limited_stops": True
            },
            RoadType.URBAN: {
                "max_speed": 35,
                "frequent_stops": True,
                "grid_pattern": True
            },
            RoadType.SUBURBAN: {
                "speed_range": (25, 50),
                "moderate_stops": True
            },
            RoadType.RURAL: {
                "speed_varies": True,
                "few_stops": True,
                "winding_roads": True
            }
        }
    
    async def analyze(
        self,
        location: Optional[Tuple[float, float]],
        speed: float,
        location_history: List[Tuple[float, float, datetime]]
    ) -> RoadType:
        """Analyze road type from driving patterns"""
        
        # Speed-based initial classification
        if speed >= 55:
            return RoadType.HIGHWAY
        elif speed <= 5:
            return RoadType.PARKING
        elif speed <= 25:
            return RoadType.URBAN
        elif speed <= 45:
            return RoadType.SUBURBAN
        else:
            # Analyze path pattern
            if self._is_straight_path(location_history):
                return RoadType.HIGHWAY_RAMP
            else:
                return RoadType.RURAL
    
    def _is_straight_path(
        self,
        location_history: List[Tuple[float, float, datetime]]
    ) -> bool:
        """Check if recent path is relatively straight"""
        if len(location_history) < 3:
            return True
        
        # Calculate heading changes
        headings = []
        for i in range(1, len(location_history)):
            lat1, lon1, _ = location_history[i-1]
            lat2, lon2, _ = location_history[i]
            
            # Simplified heading calculation
            heading = np.arctan2(lon2 - lon1, lat2 - lat1) * 180 / np.pi
            headings.append(heading)
        
        # Check variance in headings
        if headings:
            heading_variance = np.var(headings)
            return heading_variance < 10  # degrees squared
        
        return True


class VoiceSafetyMetrics:
    """Tracks safety metrics for analysis"""
    
    def __init__(self):
        self.metrics = {
            "total_commands": 0,
            "emergency_commands": 0,
            "deferred_commands": 0,
            "simplified_responses": 0,
            "merge_interruptions": 0,
            "speed_violations": 0,
            "success_by_speed": {},
            "success_by_road_type": {},
            "response_times": []
        }
    
    def record_command(
        self,
        command_result: Dict[str, Any],
        context: DrivingContext
    ) -> None:
        """Record command execution metrics"""
        self.metrics["total_commands"] += 1
        
        if command_result.get("emergency"):
            self.metrics["emergency_commands"] += 1
        
        if not command_result.get("safe"):
            self.metrics["deferred_commands"] += 1
            
            if "speed" in command_result.get("reason", "").lower():
                self.metrics["speed_violations"] += 1
        
        if command_result.get("simplified_response"):
            self.metrics["simplified_responses"] += 1
        
        if command_result.get("merge_status") == MergeStatus.ACTIVELY_MERGING.value:
            self.metrics["merge_interruptions"] += 1
        
        # Track by speed bucket
        speed_bucket = f"{int(context.speed/10)*10}-{int(context.speed/10)*10+10}mph"
        if speed_bucket not in self.metrics["success_by_speed"]:
            self.metrics["success_by_speed"][speed_bucket] = {"success": 0, "total": 0}
        
        self.metrics["success_by_speed"][speed_bucket]["total"] += 1
        if command_result.get("safe"):
            self.metrics["success_by_speed"][speed_bucket]["success"] += 1
    
    def get_safety_report(self) -> Dict[str, Any]:
        """Generate safety metrics report"""
        report = {
            "overview": {
                "total_commands": self.metrics["total_commands"],
                "safety_rate": self._calculate_safety_rate(),
                "emergency_response_rate": self._calculate_emergency_rate()
            },
            "speed_analysis": self._analyze_speed_patterns(),
            "road_type_analysis": self._analyze_road_patterns(),
            "recommendations": self._generate_recommendations()
        }
        
        return report
    
    def _calculate_safety_rate(self) -> float:
        """Calculate overall safety rate"""
        if self.metrics["total_commands"] == 0:
            return 100.0
        
        unsafe = self.metrics["deferred_commands"]
        return (1 - unsafe / self.metrics["total_commands"]) * 100
    
    def _calculate_emergency_rate(self) -> float:
        """Calculate emergency command rate"""
        if self.metrics["total_commands"] == 0:
            return 0.0
        
        return (self.metrics["emergency_commands"] / self.metrics["total_commands"]) * 100
    
    def _analyze_speed_patterns(self) -> Dict[str, Any]:
        """Analyze safety by speed"""
        patterns = {}
        
        for speed_range, data in self.metrics["success_by_speed"].items():
            if data["total"] > 0:
                patterns[speed_range] = {
                    "success_rate": (data["success"] / data["total"]) * 100,
                    "total_commands": data["total"]
                }
        
        return patterns
    
    def _analyze_road_patterns(self) -> Dict[str, Any]:
        """Analyze safety by road type"""
        # Placeholder - would use actual road type data
        return {
            "highway": {"safety_rate": 85.0},
            "urban": {"safety_rate": 92.0},
            "suburban": {"safety_rate": 94.0}
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate safety recommendations"""
        recommendations = []
        
        if self.metrics["speed_violations"] > self.metrics["total_commands"] * 0.1:
            recommendations.append(
                "High rate of speed-related deferrals. "
                "Consider more aggressive command simplification at high speeds."
            )
        
        if self.metrics["merge_interruptions"] > 5:
            recommendations.append(
                "Frequent merge interruptions detected. "
                "Enhance merge detection algorithms for earlier warning."
            )
        
        if self.metrics["emergency_commands"] > self.metrics["total_commands"] * 0.05:
            recommendations.append(
                "Elevated emergency command rate. "
                "Review emergency response protocols and user training."
            )
        
        return recommendations


# Export enhanced validator
enhanced_voice_safety_validator = EnhancedVoiceSafetyValidator()
voice_safety_metrics = VoiceSafetyMetrics()