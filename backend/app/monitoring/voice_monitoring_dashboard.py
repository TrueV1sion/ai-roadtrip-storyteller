"""
Real-time Voice System Monitoring Dashboard
Provides comprehensive monitoring for world-class voice system
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import asyncio
from collections import defaultdict, deque
import statistics

from prometheus_client import Counter, Histogram, Gauge, Info
from ..core.cache import cache_manager
from ..core.logger import get_logger

logger = get_logger(__name__)


class VoiceMonitoringDashboard:
    """
    Comprehensive monitoring for voice orchestration system
    Tracks performance, reliability, and user experience metrics
    """
    
    def __init__(self):
        # Performance Metrics
        self.voice_response_time = Histogram(
            'voice_response_duration_seconds',
            'Time taken to process voice requests',
            buckets=[0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0]
        )
        
        self.operation_latency = Histogram(
            'voice_operation_duration_seconds',
            'Latency for individual operations',
            ['operation'],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.0]
        )
        
        # Reliability Metrics
        self.error_counter = Counter(
            'voice_errors_total',
            'Total number of voice processing errors',
            ['error_type', 'operation']
        )
        
        self.circuit_breaker_state = Gauge(
            'voice_circuit_breaker_state',
            'Circuit breaker state (0=closed, 1=open, 2=half-open)',
            ['service']
        )
        
        # Usage Metrics
        self.active_sessions = Gauge(
            'voice_active_sessions',
            'Number of active voice sessions'
        )
        
        self.requests_per_minute = Gauge(
            'voice_requests_per_minute',
            'Voice requests in the last minute'
        )
        
        self.cache_hit_rate = Gauge(
            'voice_cache_hit_rate',
            'Cache hit rate percentage'
        )
        
        # Quality Metrics
        self.user_satisfaction = Gauge(
            'voice_user_satisfaction_score',
            'User satisfaction score (0-10)'
        )
        
        self.intent_accuracy = Gauge(
            'voice_intent_accuracy',
            'Intent recognition accuracy percentage'
        )
        
        # System Health
        self.system_health = Info(
            'voice_system_health',
            'Overall system health status'
        )
        
        # Real-time tracking
        self.recent_requests = deque(maxlen=1000)
        self.error_log = deque(maxlen=100)
        self.performance_buffer = defaultdict(lambda: deque(maxlen=60))
        
        # Thresholds and SLOs
        self.slo_thresholds = {
            "response_time_p95": 2.0,  # 95th percentile < 2 seconds
            "error_rate": 0.01,         # < 1% error rate
            "availability": 0.999,      # 99.9% availability
            "cache_hit_rate": 0.3,      # > 30% cache hits
        }
        
        # Initialize background monitoring
        asyncio.create_task(self._monitoring_loop())
        
        logger.info("Voice Monitoring Dashboard initialized")
    
    def record_request(
        self,
        user_id: str,
        duration: float,
        intent: str,
        success: bool,
        cache_hit: bool = False,
        error: Optional[str] = None
    ):
        """Record a voice request for monitoring"""
        # Record to Prometheus
        self.voice_response_time.observe(duration)
        
        # Track in recent requests
        self.recent_requests.append({
            "timestamp": datetime.now(),
            "user_id": user_id,
            "duration": duration,
            "intent": intent,
            "success": success,
            "cache_hit": cache_hit,
            "error": error
        })
        
        # Update error counter if failed
        if not success and error:
            self.error_counter.labels(
                error_type=self._categorize_error(error),
                operation="voice_processing"
            ).inc()
            
            self.error_log.append({
                "timestamp": datetime.now(),
                "user_id": user_id,
                "error": error,
                "intent": intent
            })
    
    def record_operation_latency(self, operation: str, duration: float):
        """Record latency for specific operations"""
        self.operation_latency.labels(operation=operation).observe(duration)
        self.performance_buffer[operation].append(duration)
    
    def update_circuit_breaker(self, service: str, state: str):
        """Update circuit breaker state"""
        state_map = {"closed": 0, "open": 1, "half-open": 2}
        self.circuit_breaker_state.labels(service=service).set(state_map.get(state, 0))
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time dashboard metrics"""
        now = datetime.now()
        one_minute_ago = now - timedelta(minutes=1)
        
        # Calculate recent metrics
        recent_minute = [
            r for r in self.recent_requests 
            if r["timestamp"] > one_minute_ago
        ]
        
        # Response time statistics
        recent_durations = [r["duration"] for r in recent_minute if r["success"]]
        response_time_stats = self._calculate_stats(recent_durations) if recent_durations else {}
        
        # Error rate
        error_count = sum(1 for r in recent_minute if not r["success"])
        error_rate = error_count / len(recent_minute) if recent_minute else 0
        
        # Cache hit rate
        cache_hits = sum(1 for r in recent_minute if r.get("cache_hit", False))
        cache_hit_rate = cache_hits / len(recent_minute) if recent_minute else 0
        
        # Intent distribution
        intent_counts = defaultdict(int)
        for r in recent_minute:
            intent_counts[r["intent"]] += 1
        
        # SLO compliance
        slo_compliance = self._check_slo_compliance(
            response_time_stats.get("p95", 0),
            error_rate,
            cache_hit_rate
        )
        
        return {
            "timestamp": now.isoformat(),
            "requests_per_minute": len(recent_minute),
            "active_sessions": self.active_sessions._value.get(),
            "response_time": response_time_stats,
            "error_rate": error_rate,
            "cache_hit_rate": cache_hit_rate,
            "intent_distribution": dict(intent_counts),
            "recent_errors": list(self.error_log)[-10:],
            "slo_compliance": slo_compliance,
            "system_status": self._get_system_status(slo_compliance)
        }
    
    def get_performance_trends(self, window_minutes: int = 60) -> Dict[str, Any]:
        """Get performance trends over specified window"""
        cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
        
        # Filter requests within window
        windowed_requests = [
            r for r in self.recent_requests
            if r["timestamp"] > cutoff_time
        ]
        
        # Group by minute
        minute_buckets = defaultdict(list)
        for req in windowed_requests:
            minute_key = req["timestamp"].strftime("%Y-%m-%d %H:%M")
            minute_buckets[minute_key].append(req)
        
        # Calculate metrics per minute
        trends = []
        for minute, requests in sorted(minute_buckets.items()):
            durations = [r["duration"] for r in requests if r["success"]]
            errors = sum(1 for r in requests if not r["success"])
            
            trends.append({
                "minute": minute,
                "requests": len(requests),
                "avg_response_time": statistics.mean(durations) if durations else 0,
                "p95_response_time": self._calculate_percentile(durations, 95) if durations else 0,
                "error_count": errors,
                "error_rate": errors / len(requests) if requests else 0
            })
        
        return {
            "window_minutes": window_minutes,
            "trends": trends,
            "summary": self._calculate_trend_summary(trends)
        }
    
    def get_error_analysis(self) -> Dict[str, Any]:
        """Analyze error patterns"""
        error_categories = defaultdict(list)
        
        for error_entry in self.error_log:
            category = self._categorize_error(error_entry["error"])
            error_categories[category].append(error_entry)
        
        analysis = {}
        for category, errors in error_categories.items():
            analysis[category] = {
                "count": len(errors),
                "latest": errors[-1]["timestamp"].isoformat() if errors else None,
                "affected_intents": list(set(e["intent"] for e in errors)),
                "sample_errors": [e["error"] for e in errors[-3:]]
            }
        
        return {
            "total_errors": len(self.error_log),
            "categories": analysis,
            "error_rate_trend": self._calculate_error_trend(),
            "recommendations": self._generate_error_recommendations(analysis)
        }
    
    def _calculate_stats(self, values: List[float]) -> Dict[str, float]:
        """Calculate statistical metrics"""
        if not values:
            return {}
        
        sorted_values = sorted(values)
        return {
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "p50": self._calculate_percentile(sorted_values, 50),
            "p95": self._calculate_percentile(sorted_values, 95),
            "p99": self._calculate_percentile(sorted_values, 99),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0
        }
    
    def _calculate_percentile(self, sorted_values: List[float], percentile: int) -> float:
        """Calculate percentile from sorted values"""
        if not sorted_values:
            return 0
        
        index = int((percentile / 100) * len(sorted_values))
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def _categorize_error(self, error_message: str) -> str:
        """Categorize errors for analysis"""
        error_lower = error_message.lower()
        
        if "timeout" in error_lower:
            return "timeout"
        elif "circuit breaker" in error_lower:
            return "circuit_breaker"
        elif "stt" in error_lower or "speech" in error_lower:
            return "speech_recognition"
        elif "tts" in error_lower or "voice" in error_lower:
            return "voice_synthesis"
        elif "network" in error_lower or "connection" in error_lower:
            return "network"
        elif "auth" in error_lower or "permission" in error_lower:
            return "authentication"
        else:
            return "other"
    
    def _check_slo_compliance(
        self,
        response_time_p95: float,
        error_rate: float,
        cache_hit_rate: float
    ) -> Dict[str, bool]:
        """Check SLO compliance"""
        return {
            "response_time": response_time_p95 <= self.slo_thresholds["response_time_p95"],
            "error_rate": error_rate <= self.slo_thresholds["error_rate"],
            "cache_performance": cache_hit_rate >= self.slo_thresholds["cache_hit_rate"]
        }
    
    def _get_system_status(self, slo_compliance: Dict[str, bool]) -> str:
        """Determine overall system status"""
        violations = sum(1 for compliant in slo_compliance.values() if not compliant)
        
        if violations == 0:
            return "healthy"
        elif violations == 1:
            return "degraded"
        else:
            return "critical"
    
    def _calculate_error_trend(self) -> List[Dict[str, Any]]:
        """Calculate error rate trend"""
        # Group errors by 5-minute buckets
        buckets = defaultdict(int)
        
        for error in self.error_log:
            bucket_key = (error["timestamp"].minute // 5) * 5
            buckets[bucket_key] += 1
        
        return [
            {"minute": k, "errors": v} 
            for k, v in sorted(buckets.items())
        ]
    
    def _generate_error_recommendations(self, error_analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on error patterns"""
        recommendations = []
        
        for category, data in error_analysis.items():
            if data["count"] > 10:
                if category == "timeout":
                    recommendations.append(
                        "High timeout errors - Consider increasing service timeouts or optimizing slow operations"
                    )
                elif category == "circuit_breaker":
                    recommendations.append(
                        "Circuit breakers triggering - Check external service health and consider fallback strategies"
                    )
                elif category == "speech_recognition":
                    recommendations.append(
                        "STT errors elevated - Verify audio quality and STT service status"
                    )
        
        return recommendations
    
    def _calculate_trend_summary(self, trends: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize performance trends"""
        if not trends:
            return {}
        
        response_times = [t["avg_response_time"] for t in trends]
        error_rates = [t["error_rate"] for t in trends]
        
        return {
            "avg_response_time": statistics.mean(response_times),
            "response_time_trend": "increasing" if response_times[-1] > response_times[0] else "decreasing",
            "avg_error_rate": statistics.mean(error_rates),
            "error_trend": "increasing" if error_rates[-1] > error_rates[0] else "decreasing",
            "total_requests": sum(t["requests"] for t in trends)
        }
    
    async def _monitoring_loop(self):
        """Background monitoring loop"""
        while True:
            try:
                # Update active metrics
                self.requests_per_minute.set(
                    len([r for r in self.recent_requests 
                         if r["timestamp"] > datetime.now() - timedelta(minutes=1)])
                )
                
                # Calculate and update cache hit rate
                recent = list(self.recent_requests)[-100:]
                if recent:
                    cache_hits = sum(1 for r in recent if r.get("cache_hit", False))
                    self.cache_hit_rate.set(cache_hits / len(recent) * 100)
                
                # Update system health
                metrics = self.get_real_time_metrics()
                self.system_health.info({
                    "status": metrics["system_status"],
                    "timestamp": datetime.now().isoformat()
                })
                
                await asyncio.sleep(10)  # Update every 10 seconds
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(30)


# Global monitoring instance
voice_monitoring = VoiceMonitoringDashboard()