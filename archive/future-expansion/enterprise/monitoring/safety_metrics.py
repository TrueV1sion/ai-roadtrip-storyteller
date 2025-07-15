"""
Safety Metrics Collection and Monitoring

Tracks and analyzes safety-related metrics for voice interactions
and driving conditions.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import logging
from dataclasses import dataclass, field
from enum import Enum

from prometheus_client import Counter, Histogram, Gauge, Summary
from backend.app.core.cache import cache_manager
from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# Prometheus metrics for safety monitoring
safety_validation_counter = Counter(
    'voice_safety_validations_total',
    'Total number of safety validations performed',
    ['result', 'safety_level', 'complexity']
)

safety_score_histogram = Histogram(
    'voice_safety_score',
    'Distribution of safety scores',
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

interaction_duration_summary = Summary(
    'voice_interaction_duration_seconds',
    'Duration of voice interactions',
    ['safety_level', 'complexity']
)

emergency_stop_counter = Counter(
    'voice_emergency_stops_total',
    'Total number of emergency stops triggered'
)

current_safety_level_gauge = Gauge(
    'current_safety_level',
    'Current driving safety level (0=emergency, 5=parked)'
)

driver_fatigue_gauge = Gauge(
    'driver_fatigue_score',
    'Current driver fatigue score (0-1)'
)


class MetricType(Enum):
    """Types of safety metrics"""
    VALIDATION = "validation"
    INTERACTION = "interaction"
    EMERGENCY = "emergency"
    CONTEXT_CHANGE = "context_change"
    SAFETY_VIOLATION = "safety_violation"
    AUTO_PAUSE = "auto_pause"


@dataclass
class SafetyMetric:
    """Individual safety metric entry"""
    timestamp: datetime
    metric_type: MetricType
    safety_level: str
    safety_score: float
    details: Dict[str, Any]
    location: Optional[Dict[str, float]] = None
    session_id: Optional[str] = None


@dataclass
class SafetyAnalysis:
    """Safety analysis results"""
    time_period: timedelta
    total_interactions: int
    average_safety_score: float
    safety_violations: int
    emergency_stops: int
    auto_pauses: int
    risk_patterns: List[Dict[str, Any]]
    recommendations: List[str]
    compliance_score: float  # 0-1, regulatory compliance


class SafetyMetricsCollector:
    """Collects and analyzes safety metrics in real-time"""
    
    def __init__(self):
        self.metrics_buffer: List[SafetyMetric] = []
        self.session_metrics: Dict[str, List[SafetyMetric]] = defaultdict(list)
        self.real_time_alerts: List[Dict[str, Any]] = []
        self.risk_threshold = 0.3  # Safety score below this triggers alerts
        
        # Start background tasks
        asyncio.create_task(self._periodic_analysis())
        asyncio.create_task(self._cleanup_old_metrics())
    
    async def record_metric(self, metric: SafetyMetric):
        """Record a safety metric"""
        self.metrics_buffer.append(metric)
        
        if metric.session_id:
            self.session_metrics[metric.session_id].append(metric)
        
        # Update Prometheus metrics
        self._update_prometheus_metrics(metric)
        
        # Check for immediate safety concerns
        await self._check_safety_alerts(metric)
        
        # Cache recent metrics
        await self._cache_metric(metric)
    
    async def record_validation(
        self,
        is_safe: bool,
        safety_level: str,
        safety_score: float,
        complexity: str,
        warnings: List[str],
        location: Optional[Dict[str, float]] = None,
        session_id: Optional[str] = None
    ):
        """Record a safety validation event"""
        metric = SafetyMetric(
            timestamp=datetime.now(),
            metric_type=MetricType.VALIDATION,
            safety_level=safety_level,
            safety_score=safety_score,
            details={
                "is_safe": is_safe,
                "complexity": complexity,
                "warnings": warnings,
                "result": "allowed" if is_safe else "blocked"
            },
            location=location,
            session_id=session_id
        )
        
        await self.record_metric(metric)
        
        # Update counters
        safety_validation_counter.labels(
            result="allowed" if is_safe else "blocked",
            safety_level=safety_level,
            complexity=complexity
        ).inc()
    
    async def record_interaction(
        self,
        duration_seconds: float,
        safety_level: str,
        complexity: str,
        was_interrupted: bool,
        error_count: int,
        safety_score: float,
        session_id: Optional[str] = None
    ):
        """Record a completed interaction"""
        metric = SafetyMetric(
            timestamp=datetime.now(),
            metric_type=MetricType.INTERACTION,
            safety_level=safety_level,
            safety_score=safety_score,
            details={
                "duration_seconds": duration_seconds,
                "complexity": complexity,
                "was_interrupted": was_interrupted,
                "error_count": error_count,
                "completed": not was_interrupted
            },
            session_id=session_id
        )
        
        await self.record_metric(metric)
        
        # Update duration metric
        interaction_duration_summary.labels(
            safety_level=safety_level,
            complexity=complexity
        ).observe(duration_seconds)
    
    async def record_emergency_stop(
        self,
        reason: str,
        safety_level: str,
        location: Optional[Dict[str, float]] = None,
        session_id: Optional[str] = None
    ):
        """Record an emergency stop event"""
        metric = SafetyMetric(
            timestamp=datetime.now(),
            metric_type=MetricType.EMERGENCY,
            safety_level=safety_level,
            safety_score=0.0,  # Emergency is always unsafe
            details={
                "reason": reason,
                "severity": "critical"
            },
            location=location,
            session_id=session_id
        )
        
        await self.record_metric(metric)
        
        # Update counter
        emergency_stop_counter.inc()
        
        # Send immediate alert
        await self._send_safety_alert({
            "type": "emergency_stop",
            "reason": reason,
            "timestamp": datetime.now(),
            "location": location
        })
    
    async def record_auto_pause(
        self,
        reason: str,
        safety_level: str,
        duration_seconds: Optional[float] = None,
        session_id: Optional[str] = None
    ):
        """Record an automatic pause event"""
        metric = SafetyMetric(
            timestamp=datetime.now(),
            metric_type=MetricType.AUTO_PAUSE,
            safety_level=safety_level,
            safety_score=0.5,  # Auto-pause is precautionary
            details={
                "reason": reason,
                "duration_seconds": duration_seconds
            },
            session_id=session_id
        )
        
        await self.record_metric(metric)
    
    async def update_driving_context(
        self,
        safety_level: str,
        safety_level_numeric: int,
        fatigue_score: float,
        speed_mph: float,
        session_id: Optional[str] = None
    ):
        """Update current driving context metrics"""
        # Update Prometheus gauges
        current_safety_level_gauge.set(safety_level_numeric)
        driver_fatigue_gauge.set(fatigue_score)
        
        # Record context change if significant
        if self._is_significant_change(safety_level, fatigue_score):
            metric = SafetyMetric(
                timestamp=datetime.now(),
                metric_type=MetricType.CONTEXT_CHANGE,
                safety_level=safety_level,
                safety_score=self._context_to_safety_score(safety_level_numeric),
                details={
                    "fatigue_score": fatigue_score,
                    "speed_mph": speed_mph
                },
                session_id=session_id
            )
            await self.record_metric(metric)
    
    async def get_session_analysis(self, session_id: str) -> SafetyAnalysis:
        """Get safety analysis for a specific session"""
        session_metrics = self.session_metrics.get(session_id, [])
        
        if not session_metrics:
            return SafetyAnalysis(
                time_period=timedelta(0),
                total_interactions=0,
                average_safety_score=1.0,
                safety_violations=0,
                emergency_stops=0,
                auto_pauses=0,
                risk_patterns=[],
                recommendations=[],
                compliance_score=1.0
            )
        
        # Calculate time period
        start_time = min(m.timestamp for m in session_metrics)
        end_time = max(m.timestamp for m in session_metrics)
        time_period = end_time - start_time
        
        # Count metrics
        interactions = [m for m in session_metrics if m.metric_type == MetricType.INTERACTION]
        violations = [m for m in session_metrics if m.safety_score < self.risk_threshold]
        emergencies = [m for m in session_metrics if m.metric_type == MetricType.EMERGENCY]
        auto_pauses = [m for m in session_metrics if m.metric_type == MetricType.AUTO_PAUSE]
        
        # Calculate average safety score
        all_scores = [m.safety_score for m in session_metrics if m.safety_score > 0]
        avg_safety_score = sum(all_scores) / len(all_scores) if all_scores else 1.0
        
        # Identify risk patterns
        risk_patterns = self._identify_risk_patterns(session_metrics)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            avg_safety_score,
            len(violations),
            len(emergencies),
            risk_patterns
        )
        
        # Calculate compliance score
        compliance_score = self._calculate_compliance_score(session_metrics)
        
        return SafetyAnalysis(
            time_period=time_period,
            total_interactions=len(interactions),
            average_safety_score=avg_safety_score,
            safety_violations=len(violations),
            emergency_stops=len(emergencies),
            auto_pauses=len(auto_pauses),
            risk_patterns=risk_patterns,
            recommendations=recommendations,
            compliance_score=compliance_score
        )
    
    async def get_real_time_alerts(self) -> List[Dict[str, Any]]:
        """Get current real-time safety alerts"""
        # Return recent alerts (last 5 minutes)
        cutoff_time = datetime.now() - timedelta(minutes=5)
        return [
            alert for alert in self.real_time_alerts
            if alert["timestamp"] > cutoff_time
        ]
    
    async def _check_safety_alerts(self, metric: SafetyMetric):
        """Check if metric triggers any safety alerts"""
        # Low safety score alert
        if metric.safety_score < self.risk_threshold:
            await self._send_safety_alert({
                "type": "low_safety_score",
                "score": metric.safety_score,
                "safety_level": metric.safety_level,
                "timestamp": metric.timestamp,
                "details": metric.details
            })
        
        # High error rate alert
        if metric.metric_type == MetricType.INTERACTION:
            error_count = metric.details.get("error_count", 0)
            if error_count > 2:
                await self._send_safety_alert({
                    "type": "high_error_rate",
                    "error_count": error_count,
                    "timestamp": metric.timestamp
                })
        
        # Frequent interruptions alert
        if metric.details.get("was_interrupted", False):
            recent_interruptions = await self._count_recent_interruptions(minutes=5)
            if recent_interruptions > 3:
                await self._send_safety_alert({
                    "type": "frequent_interruptions",
                    "count": recent_interruptions,
                    "timestamp": metric.timestamp
                })
    
    async def _send_safety_alert(self, alert: Dict[str, Any]):
        """Send a safety alert"""
        alert["id"] = f"alert_{datetime.now().timestamp()}"
        self.real_time_alerts.append(alert)
        
        # Log critical alerts
        if alert["type"] in ["emergency_stop", "low_safety_score"]:
            logger.warning(f"Safety alert: {alert}")
        
        # Could also send to monitoring system, notifications, etc.
    
    async def _periodic_analysis(self):
        """Perform periodic safety analysis"""
        while True:
            await asyncio.sleep(300)  # Every 5 minutes
            
            try:
                # Analyze recent metrics
                recent_metrics = self._get_recent_metrics(minutes=30)
                if recent_metrics:
                    analysis = await self._analyze_metrics(recent_metrics)
                    
                    # Cache analysis results
                    await cache_manager.set(
                        "safety:recent_analysis",
                        analysis,
                        ttl=600
                    )
                    
                    # Check for concerning trends
                    if analysis["average_safety_score"] < 0.5:
                        await self._send_safety_alert({
                            "type": "concerning_trend",
                            "average_score": analysis["average_safety_score"],
                            "timestamp": datetime.now()
                        })
                        
            except Exception as e:
                logger.error(f"Error in periodic safety analysis: {e}")
    
    async def _cleanup_old_metrics(self):
        """Clean up old metrics to prevent memory issues"""
        while True:
            await asyncio.sleep(3600)  # Every hour
            
            try:
                cutoff_time = datetime.now() - timedelta(hours=24)
                
                # Clean buffer
                self.metrics_buffer = [
                    m for m in self.metrics_buffer
                    if m.timestamp > cutoff_time
                ]
                
                # Clean session metrics
                for session_id in list(self.session_metrics.keys()):
                    self.session_metrics[session_id] = [
                        m for m in self.session_metrics[session_id]
                        if m.timestamp > cutoff_time
                    ]
                    
                    # Remove empty sessions
                    if not self.session_metrics[session_id]:
                        del self.session_metrics[session_id]
                
                # Clean alerts
                self.real_time_alerts = [
                    a for a in self.real_time_alerts
                    if a["timestamp"] > cutoff_time
                ]
                
            except Exception as e:
                logger.error(f"Error in metrics cleanup: {e}")
    
    def _update_prometheus_metrics(self, metric: SafetyMetric):
        """Update Prometheus metrics"""
        safety_score_histogram.observe(metric.safety_score)
    
    async def _cache_metric(self, metric: SafetyMetric):
        """Cache metric for quick access"""
        key = f"safety:metric:{metric.timestamp.timestamp()}"
        await cache_manager.set(key, metric.__dict__, ttl=3600)
    
    def _is_significant_change(self, safety_level: str, fatigue_score: float) -> bool:
        """Check if context change is significant enough to record"""
        # Implementation would check against previous values
        # For now, always record critical changes
        return safety_level in ["critical", "emergency"] or fatigue_score > 0.8
    
    def _context_to_safety_score(self, safety_level_numeric: int) -> float:
        """Convert numeric safety level to score"""
        # 0=emergency, 5=parked
        return safety_level_numeric / 5.0
    
    def _get_recent_metrics(self, minutes: int) -> List[SafetyMetric]:
        """Get metrics from the last N minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [
            m for m in self.metrics_buffer
            if m.timestamp > cutoff_time
        ]
    
    async def _count_recent_interruptions(self, minutes: int) -> int:
        """Count recent interrupted interactions"""
        recent_metrics = self._get_recent_metrics(minutes)
        return sum(
            1 for m in recent_metrics
            if m.metric_type == MetricType.INTERACTION
            and m.details.get("was_interrupted", False)
        )
    
    async def _analyze_metrics(self, metrics: List[SafetyMetric]) -> Dict[str, Any]:
        """Analyze a set of metrics"""
        if not metrics:
            return {"status": "no_data"}
        
        total_count = len(metrics)
        safety_scores = [m.safety_score for m in metrics if m.safety_score > 0]
        avg_score = sum(safety_scores) / len(safety_scores) if safety_scores else 1.0
        
        # Count by type
        type_counts = defaultdict(int)
        for m in metrics:
            type_counts[m.metric_type.value] += 1
        
        # Count by safety level
        level_counts = defaultdict(int)
        for m in metrics:
            level_counts[m.safety_level] += 1
        
        return {
            "total_metrics": total_count,
            "average_safety_score": avg_score,
            "metric_types": dict(type_counts),
            "safety_levels": dict(level_counts),
            "violations": sum(1 for m in metrics if m.safety_score < self.risk_threshold),
            "time_range": {
                "start": min(m.timestamp for m in metrics),
                "end": max(m.timestamp for m in metrics)
            }
        }
    
    def _identify_risk_patterns(self, metrics: List[SafetyMetric]) -> List[Dict[str, Any]]:
        """Identify patterns in safety risks"""
        patterns = []
        
        # Pattern: Frequent low scores at high speed
        high_speed_low_scores = [
            m for m in metrics
            if m.details.get("speed_mph", 0) > 55 and m.safety_score < 0.5
        ]
        if len(high_speed_low_scores) > 5:
            patterns.append({
                "type": "high_speed_interactions",
                "count": len(high_speed_low_scores),
                "risk": "high"
            })
        
        # Pattern: Degrading scores over time (fatigue)
        if len(metrics) > 10:
            first_half = metrics[:len(metrics)//2]
            second_half = metrics[len(metrics)//2:]
            
            first_avg = sum(m.safety_score for m in first_half) / len(first_half)
            second_avg = sum(m.safety_score for m in second_half) / len(second_half)
            
            if second_avg < first_avg * 0.8:
                patterns.append({
                    "type": "degrading_performance",
                    "score_drop": first_avg - second_avg,
                    "risk": "medium"
                })
        
        # Pattern: Complexity violations
        complexity_violations = [
            m for m in metrics
            if m.metric_type == MetricType.VALIDATION
            and not m.details.get("is_safe", True)
            and "complexity" in str(m.details.get("warnings", []))
        ]
        if complexity_violations:
            patterns.append({
                "type": "complexity_violations",
                "count": len(complexity_violations),
                "risk": "medium"
            })
        
        return patterns
    
    def _generate_recommendations(
        self,
        avg_safety_score: float,
        violations: int,
        emergencies: int,
        patterns: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate safety recommendations"""
        recommendations = []
        
        if avg_safety_score < 0.6:
            recommendations.append("Consider implementing stricter safety thresholds")
        
        if violations > 10:
            recommendations.append("High violation rate detected - review interaction complexity")
        
        if emergencies > 0:
            recommendations.append("Emergency stops occurred - investigate root causes")
        
        # Pattern-based recommendations
        for pattern in patterns:
            if pattern["type"] == "high_speed_interactions":
                recommendations.append("Limit complex interactions at highway speeds")
            elif pattern["type"] == "degrading_performance":
                recommendations.append("Implement fatigue detection and mandatory breaks")
            elif pattern["type"] == "complexity_violations":
                recommendations.append("Simplify voice command structure")
        
        return recommendations
    
    def _calculate_compliance_score(self, metrics: List[SafetyMetric]) -> float:
        """Calculate regulatory compliance score"""
        if not metrics:
            return 1.0
        
        # Check for hands-free compliance
        violations = [
            m for m in metrics
            if m.metric_type == MetricType.VALIDATION
            and not m.details.get("is_safe", True)
        ]
        
        # Check for proper emergency handling
        emergencies = [m for m in metrics if m.metric_type == MetricType.EMERGENCY]
        emergency_compliance = 1.0 if not emergencies else 0.8
        
        # Calculate overall compliance
        violation_rate = len(violations) / len(metrics)
        compliance_score = (1.0 - violation_rate) * 0.7 + emergency_compliance * 0.3
        
        return max(0.0, min(1.0, compliance_score))


# Global instance
safety_metrics_collector = SafetyMetricsCollector()