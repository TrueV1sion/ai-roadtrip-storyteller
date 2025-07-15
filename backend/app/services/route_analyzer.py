from typing import Dict, List, Optional
from datetime import datetime, timedelta
import statistics
from dataclasses import dataclass

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RouteStatistics:
    """Statistics for a route."""
    total_distance: float
    total_duration: float
    avg_speed: float
    traffic_delay: Optional[float]
    confidence_score: float
    segments_count: int
    turns_count: int
    traffic_signals: int
    elevation_gain: float
    complexity_score: float


class RouteAnalyzer:
    """Analyzes routes and provides statistical insights."""

    def analyze_route(self, route: Dict) -> RouteStatistics:
        """
        Analyze a route and compute various statistics.
        
        Args:
            route: Route data from Google Directions API
            
        Returns:
            RouteStatistics object containing route metrics
        """
        try:
            total_distance = 0
            total_duration = 0
            total_duration_in_traffic = 0
            turns_count = 0
            traffic_signals = 0
            
            # Process each leg
            for leg in route.get("legs", []):
                total_distance += leg.get("distance", {}).get("value", 0)
                total_duration += leg.get("duration", {}).get("value", 0)
                
                if "duration_in_traffic" in leg:
                    total_duration_in_traffic += leg.get(
                        "duration_in_traffic", {}
                    ).get("value", 0)
                
                # Count turns and traffic signals
                for step in leg.get("steps", []):
                    if step.get("maneuver"):
                        turns_count += 1
                    if "traffic_signal" in step.get("html_instructions", "").lower():
                        traffic_signals += 1
            
            # Calculate average speed (m/s)
            avg_speed = (
                total_distance / total_duration if total_duration > 0 else 0
            )
            
            # Calculate traffic delay
            traffic_delay = None
            if total_duration_in_traffic > 0:
                traffic_delay = total_duration_in_traffic - total_duration
            
            # Calculate route complexity
            complexity_score = self._calculate_complexity(
                route,
                turns_count,
                traffic_signals
            )
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence(
                route,
                traffic_delay,
                complexity_score
            )
            
            return RouteStatistics(
                total_distance=total_distance,
                total_duration=total_duration,
                avg_speed=avg_speed,
                traffic_delay=traffic_delay,
                confidence_score=confidence_score,
                segments_count=len(route.get("legs", [])),
                turns_count=turns_count,
                traffic_signals=traffic_signals,
                elevation_gain=self._calculate_elevation_gain(route),
                complexity_score=complexity_score
            )
            
        except Exception as e:
            logger.error(f"Error analyzing route: {str(e)}")
            return None

    def predict_eta(
        self,
        route: Dict,
        departure_time: Optional[datetime] = None
    ) -> Dict:
        """
        Predict ETA with confidence intervals.
        
        Args:
            route: Route data from Google Directions API
            departure_time: Optional departure time
            
        Returns:
            Dict containing ETA predictions and confidence intervals
        """
        try:
            stats = self.analyze_route(route)
            if not stats:
                return None
            
            base_duration = stats.total_duration
            
            # Adjust for time of day if departure_time provided
            if departure_time:
                base_duration = self._adjust_for_time_of_day(
                    base_duration,
                    departure_time
                )
            
            # Calculate confidence intervals
            margin = base_duration * (1 - stats.confidence_score)
            
            return {
                "eta": {
                    "optimistic": base_duration - margin,
                    "expected": base_duration,
                    "pessimistic": base_duration + margin
                },
                "confidence_score": stats.confidence_score,
                "factors": self._get_eta_factors(route, departure_time)
            }
            
        except Exception as e:
            logger.error(f"Error predicting ETA: {str(e)}")
            return None

    def _calculate_complexity(
        self,
        route: Dict,
        turns_count: int,
        traffic_signals: int
    ) -> float:
        """Calculate route complexity score (0-1)."""
        try:
            # Factors that increase complexity
            factors = [
                turns_count / 10,  # Normalize turns
                traffic_signals / 5,  # Normalize signals
                len(route.get("legs", [])) / 3,  # Normalize segments
                len(str(route.get("warnings", []))) > 0,  # Has warnings
                route.get("fare") is not None  # Involves transit
            ]
            
            # Weight and combine factors
            weights = [0.3, 0.2, 0.2, 0.15, 0.15]
            complexity = sum(f * w for f, w in zip(factors, weights))
            
            return min(max(complexity, 0), 1)  # Clamp to 0-1
            
        except Exception as e:
            logger.error(f"Error calculating complexity: {str(e)}")
            return 0.5

    def _calculate_confidence(
        self,
        route: Dict,
        traffic_delay: Optional[float],
        complexity: float
    ) -> float:
        """Calculate confidence score for predictions (0-1)."""
        try:
            # Factors that affect confidence
            factors = [
                1 - complexity,  # Less complex routes are more predictable
                traffic_delay is not None,  # Having traffic data increases confidence
                len(route.get("legs", [])) == 1,  # Single segment routes are more predictable
                not route.get("warnings", []),  # No warnings increases confidence
                route.get("traffic_speed_entry", []) != []  # Having speed data helps
            ]
            
            # Weight and combine factors
            weights = [0.3, 0.25, 0.2, 0.15, 0.1]
            confidence = sum(f * w for f, w in zip(factors, weights))
            
            return min(max(confidence, 0), 1)  # Clamp to 0-1
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {str(e)}")
            return 0.5

    def _calculate_elevation_gain(self, route: Dict) -> float:
        """Calculate total elevation gain (if available)."""
        try:
            elevation_gain = 0
            for leg in route.get("legs", []):
                for step in leg.get("steps", []):
                    if "elevation" in step:
                        points = step["elevation"]
                        for i in range(1, len(points)):
                            diff = points[i] - points[i-1]
                            if diff > 0:
                                elevation_gain += diff
            return elevation_gain
        except Exception as e:
            logger.error(f"Error calculating elevation gain: {str(e)}")
            return 0

    def _adjust_for_time_of_day(
        self,
        duration: float,
        departure_time: datetime
    ) -> float:
        """Adjust duration based on historical time-of-day patterns."""
        try:
            hour = departure_time.hour
            
            # Define time-based multipliers
            if 6 <= hour <= 9:  # Morning rush
                return duration * 1.3
            elif 16 <= hour <= 19:  # Evening rush
                return duration * 1.4
            elif 22 <= hour or hour <= 5:  # Night
                return duration * 0.8
            else:  # Normal hours
                return duration
                
        except Exception as e:
            logger.error(f"Error adjusting for time of day: {str(e)}")
            return duration

    def _get_eta_factors(
        self,
        route: Dict,
        departure_time: Optional[datetime]
    ) -> List[Dict]:
        """Get factors affecting ETA prediction."""
        factors = []
        
        try:
            # Time of day
            if departure_time:
                hour = departure_time.hour
                if 6 <= hour <= 9:
                    factors.append({
                        "type": "time_of_day",
                        "impact": "high",
                        "description": "Morning rush hour"
                    })
                elif 16 <= hour <= 19:
                    factors.append({
                        "type": "time_of_day",
                        "impact": "high",
                        "description": "Evening rush hour"
                    })
            
            # Traffic conditions
            if route.get("traffic_speed_entry"):
                factors.append({
                    "type": "traffic",
                    "impact": "medium",
                    "description": "Live traffic data available"
                })
            
            # Route complexity
            turns_count = sum(
                1 for leg in route.get("legs", [])
                for step in leg.get("steps", [])
                if step.get("maneuver")
            )
            if turns_count > 10:
                factors.append({
                    "type": "complexity",
                    "impact": "medium",
                    "description": f"Complex route with {turns_count} turns"
                })
            
            # Weather (placeholder)
            factors.append({
                "type": "weather",
                "impact": "low",
                "description": "Normal weather conditions"
            })
            
            return factors
            
        except Exception as e:
            logger.error(f"Error getting ETA factors: {str(e)}")
            return factors


# Global analyzer instance
route_analyzer = RouteAnalyzer() 