"""
Cache Monitoring and Analytics System
Provides real-time monitoring, alerting, and performance analytics for the multi-tier cache
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
import statistics
import json

from app.core.multi_tier_cache import multi_tier_cache, ContentType, CacheMetrics
from app.core.logger import get_logger
from app.core.monitoring import metrics_collector

logger = get_logger(__name__)


@dataclass
class CacheAlert:
    """Alert for cache performance issues."""
    alert_type: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    metrics: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            'alert_type': self.alert_type,
            'severity': self.severity,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'metrics': self.metrics,
            'resolved': self.resolved
        }


@dataclass
class PerformanceThresholds:
    """Configurable performance thresholds for alerting."""
    min_hit_rate: float = 0.80              # 80% minimum hit rate
    max_response_time_ms: float = 100.0     # 100ms max response time
    max_memory_usage_mb: float = 80.0       # 80MB max memory usage
    min_cost_savings_per_hour: float = 1.0  # $1/hour minimum savings
    max_eviction_rate: float = 0.1          # 10% max eviction rate
    max_error_rate: float = 0.05            # 5% max error rate


class CacheMonitor:
    """Real-time cache monitoring with alerting and analytics."""
    
    def __init__(self, alert_webhook_url: Optional[str] = None):
        self.cache = multi_tier_cache
        self.alert_webhook_url = alert_webhook_url
        self.thresholds = PerformanceThresholds()
        
        # Metrics tracking
        self.metrics_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.alerts: List[CacheAlert] = []
        self.active_alerts: Dict[str, CacheAlert] = {}
        
        # Performance baselines
        self.performance_baselines: Dict[str, float] = {}
        
        # Start monitoring
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._analytics_task = asyncio.create_task(self._analytics_loop())
    
    async def _monitoring_loop(self):
        """Main monitoring loop that collects metrics."""
        while True:
            try:
                await asyncio.sleep(10)  # Collect every 10 seconds
                
                # Collect current metrics
                metrics = await self._collect_metrics()
                
                # Store in history
                for key, value in metrics.items():
                    self.metrics_history[key].append({
                        'timestamp': time.time(),
                        'value': value
                    })
                
                # Check thresholds and generate alerts
                await self._check_thresholds(metrics)
                
                # Send to monitoring system
                await self._send_to_monitoring(metrics)
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
    
    async def _analytics_loop(self):
        """Analytics loop for deeper insights."""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                # Generate analytics report
                report = await self.generate_analytics_report()
                
                # Log key insights
                self._log_insights(report)
                
                # Update baselines
                self._update_baselines(report)
                
            except Exception as e:
                logger.error(f"Analytics loop error: {e}")
    
    async def _collect_metrics(self) -> Dict[str, float]:
        """Collect current cache metrics."""
        # Get cache performance report
        report = self.cache.get_performance_report()
        
        # Extract key metrics
        metrics = {
            'hit_rate': report['overall']['hit_rate'],
            'cost_saved_usd': report['overall']['cost_saved_usd'],
            'api_calls_saved': report['overall']['api_calls_saved'],
            'response_time_ms': report['overall']['avg_response_time_ms'],
            'l1_memory_mb': report['l1_memory']['memory_mb'],
            'l1_entries': report['l1_memory']['entries'],
            'l1_evictions': report['l1_memory']['evictions'],
            'redis_available': 1.0 if report['l2_redis']['available'] else 0.0
        }
        
        # Calculate derived metrics
        metrics['eviction_rate'] = self._calculate_eviction_rate()
        metrics['error_rate'] = self._calculate_error_rate()
        metrics['cost_savings_rate'] = self._calculate_cost_savings_rate()
        
        return metrics
    
    async def _check_thresholds(self, metrics: Dict[str, float]):
        """Check metrics against thresholds and generate alerts."""
        # Hit rate check
        if metrics['hit_rate'] < self.thresholds.min_hit_rate:
            await self._create_alert(
                alert_type='low_hit_rate',
                severity='high',
                message=f"Cache hit rate {metrics['hit_rate']:.1%} below threshold {self.thresholds.min_hit_rate:.1%}",
                metrics={'hit_rate': metrics['hit_rate']}
            )
        else:
            await self._resolve_alert('low_hit_rate')
        
        # Response time check
        if metrics['response_time_ms'] > self.thresholds.max_response_time_ms:
            await self._create_alert(
                alert_type='high_response_time',
                severity='medium',
                message=f"Response time {metrics['response_time_ms']:.1f}ms above threshold {self.thresholds.max_response_time_ms}ms",
                metrics={'response_time_ms': metrics['response_time_ms']}
            )
        else:
            await self._resolve_alert('high_response_time')
        
        # Memory usage check
        if metrics['l1_memory_mb'] > self.thresholds.max_memory_usage_mb:
            await self._create_alert(
                alert_type='high_memory_usage',
                severity='medium',
                message=f"Memory usage {metrics['l1_memory_mb']:.1f}MB above threshold {self.thresholds.max_memory_usage_mb}MB",
                metrics={'memory_mb': metrics['l1_memory_mb']}
            )
        else:
            await self._resolve_alert('high_memory_usage')
        
        # Redis availability check
        if metrics['redis_available'] == 0:
            await self._create_alert(
                alert_type='redis_unavailable',
                severity='critical',
                message="Redis cache tier is unavailable",
                metrics={}
            )
        else:
            await self._resolve_alert('redis_unavailable')
        
        # Cost savings check
        if metrics['cost_savings_rate'] < self.thresholds.min_cost_savings_per_hour:
            await self._create_alert(
                alert_type='low_cost_savings',
                severity='low',
                message=f"Cost savings ${metrics['cost_savings_rate']:.2f}/hour below target ${self.thresholds.min_cost_savings_per_hour}/hour",
                metrics={'cost_savings_rate': metrics['cost_savings_rate']}
            )
        else:
            await self._resolve_alert('low_cost_savings')
    
    async def _create_alert(
        self,
        alert_type: str,
        severity: str,
        message: str,
        metrics: Dict[str, Any]
    ):
        """Create or update an alert."""
        # Check if alert already exists
        if alert_type in self.active_alerts:
            # Update existing alert
            alert = self.active_alerts[alert_type]
            alert.timestamp = datetime.now()
            alert.metrics = metrics
        else:
            # Create new alert
            alert = CacheAlert(
                alert_type=alert_type,
                severity=severity,
                message=message,
                metrics=metrics
            )
            
            self.active_alerts[alert_type] = alert
            self.alerts.append(alert)
            
            # Send alert notification
            await self._send_alert_notification(alert)
            
            logger.warning(f"Cache alert created: {message}")
    
    async def _resolve_alert(self, alert_type: str):
        """Resolve an active alert."""
        if alert_type in self.active_alerts:
            alert = self.active_alerts[alert_type]
            alert.resolved = True
            del self.active_alerts[alert_type]
            
            logger.info(f"Cache alert resolved: {alert_type}")
    
    async def _send_alert_notification(self, alert: CacheAlert):
        """Send alert notification via webhook or logging."""
        if self.alert_webhook_url:
            # Send to webhook
            try:
                # Implementation would send to actual webhook
                pass
            except Exception as e:
                logger.error(f"Failed to send alert webhook: {e}")
        
        # Log based on severity
        if alert.severity == 'critical':
            logger.critical(f"CACHE ALERT: {alert.message}")
        elif alert.severity == 'high':
            logger.error(f"CACHE ALERT: {alert.message}")
        else:
            logger.warning(f"CACHE ALERT: {alert.message}")
    
    async def _send_to_monitoring(self, metrics: Dict[str, float]):
        """Send metrics to monitoring system."""
        try:
            for metric_name, value in metrics.items():
                await metrics_collector.record_metric(f"cache.{metric_name}", value)
        except Exception as e:
            logger.error(f"Failed to send metrics: {e}")
    
    def _calculate_eviction_rate(self) -> float:
        """Calculate eviction rate over last period."""
        evictions = self.metrics_history['l1_evictions']
        if len(evictions) < 2:
            return 0.0
        
        # Get evictions in last minute
        current_time = time.time()
        recent_evictions = [
            e for e in evictions
            if current_time - e['timestamp'] < 60
        ]
        
        if len(recent_evictions) < 2:
            return 0.0
        
        # Calculate rate
        eviction_delta = recent_evictions[-1]['value'] - recent_evictions[0]['value']
        time_delta = recent_evictions[-1]['timestamp'] - recent_evictions[0]['timestamp']
        
        if time_delta > 0:
            return eviction_delta / time_delta * 60  # Per minute
        return 0.0
    
    def _calculate_error_rate(self) -> float:
        """Calculate cache error rate."""
        # This would track actual errors
        # For now, return 0
        return 0.0
    
    def _calculate_cost_savings_rate(self) -> float:
        """Calculate cost savings rate per hour."""
        cost_history = self.metrics_history['cost_saved_usd']
        if len(cost_history) < 2:
            return 0.0
        
        # Get last hour of data
        current_time = time.time()
        hour_ago = current_time - 3600
        
        recent_costs = [
            c for c in cost_history
            if c['timestamp'] > hour_ago
        ]
        
        if len(recent_costs) < 2:
            return 0.0
        
        # Calculate hourly rate
        cost_delta = recent_costs[-1]['value'] - recent_costs[0]['value']
        time_delta = (recent_costs[-1]['timestamp'] - recent_costs[0]['timestamp']) / 3600
        
        if time_delta > 0:
            return cost_delta / time_delta
        return 0.0
    
    async def generate_analytics_report(self) -> Dict[str, Any]:
        """Generate comprehensive analytics report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': await self._generate_summary(),
            'trends': self._analyze_trends(),
            'patterns': await self._analyze_patterns(),
            'recommendations': await self._generate_recommendations(),
            'cost_analysis': self._analyze_costs(),
            'performance_score': self._calculate_performance_score()
        }
        
        return report
    
    async def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary statistics."""
        metrics = await self._collect_metrics()
        
        return {
            'current_hit_rate': metrics['hit_rate'],
            'avg_response_time_ms': metrics['response_time_ms'],
            'total_cost_saved': metrics['cost_saved_usd'],
            'api_calls_saved': metrics['api_calls_saved'],
            'active_alerts': len(self.active_alerts),
            'cache_efficiency': self._calculate_cache_efficiency()
        }
    
    def _analyze_trends(self) -> Dict[str, Any]:
        """Analyze metric trends."""
        trends = {}
        
        for metric_name in ['hit_rate', 'response_time_ms', 'cost_saved_usd']:
            history = self.metrics_history[metric_name]
            if len(history) > 10:
                values = [h['value'] for h in history[-100:]]
                
                trends[metric_name] = {
                    'current': values[-1] if values else 0,
                    'avg_1h': statistics.mean(values[-360:]) if len(values) > 360 else statistics.mean(values),
                    'trend': self._calculate_trend(values),
                    'volatility': statistics.stdev(values) if len(values) > 1 else 0
                }
        
        return trends
    
    async def _analyze_patterns(self) -> Dict[str, Any]:
        """Analyze usage patterns."""
        # Get content type distribution
        content_type_hits = defaultdict(int)
        
        # This would analyze actual cache hits by content type
        # For now, return estimated distribution
        return {
            'content_type_distribution': {
                'ai_response': 0.4,
                'story_content': 0.3,
                'voice_audio': 0.2,
                'other': 0.1
            },
            'peak_hours': [9, 10, 11, 17, 18, 19],  # Morning and evening peaks
            'cache_misses_by_type': {
                'cold_start': 0.3,
                'expired': 0.4,
                'invalidated': 0.2,
                'not_cacheable': 0.1
            }
        }
    
    async def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        metrics = await self._collect_metrics()
        
        # Hit rate recommendations
        if metrics['hit_rate'] < 0.8:
            recommendations.append(
                f"Increase cache TTL or size. Current hit rate {metrics['hit_rate']:.1%} is below 80% target."
            )
        
        # Memory recommendations
        if metrics['l1_memory_mb'] > 80:
            recommendations.append(
                "Consider increasing L1 memory limit or adjusting eviction policy. Memory usage is high."
            )
        
        # Response time recommendations
        if metrics['response_time_ms'] > 100:
            recommendations.append(
                "Optimize cache key generation or consider pre-warming frequently accessed content."
            )
        
        # Cost optimization
        if metrics['cost_savings_rate'] < 5:
            recommendations.append(
                "Identify and cache more expensive API calls to increase cost savings."
            )
        
        # Eviction rate
        if metrics['eviction_rate'] > 10:
            recommendations.append(
                "High eviction rate detected. Consider increasing cache size or optimizing TTL strategies."
            )
        
        return recommendations
    
    def _analyze_costs(self) -> Dict[str, Any]:
        """Analyze cost savings in detail."""
        cost_history = self.metrics_history['cost_saved_usd']
        
        if not cost_history:
            return {}
        
        values = [h['value'] for h in cost_history]
        
        return {
            'total_saved': values[-1] if values else 0,
            'hourly_rate': self._calculate_cost_savings_rate(),
            'daily_projection': self._calculate_cost_savings_rate() * 24,
            'monthly_projection': self._calculate_cost_savings_rate() * 24 * 30,
            'roi_percentage': self._calculate_roi()
        }
    
    def _calculate_performance_score(self) -> float:
        """Calculate overall performance score (0-100)."""
        weights = {
            'hit_rate': 0.4,
            'response_time': 0.3,
            'cost_savings': 0.2,
            'availability': 0.1
        }
        
        scores = {}
        
        # Hit rate score (0-100)
        hit_rate = self.metrics_history['hit_rate'][-1]['value'] if self.metrics_history['hit_rate'] else 0
        scores['hit_rate'] = min(hit_rate / 0.9 * 100, 100)  # 90% = 100 score
        
        # Response time score (100-0)
        response_time = self.metrics_history['response_time_ms'][-1]['value'] if self.metrics_history['response_time_ms'] else 100
        scores['response_time'] = max(100 - (response_time / 2), 0)  # 200ms = 0 score
        
        # Cost savings score
        cost_rate = self._calculate_cost_savings_rate()
        scores['cost_savings'] = min(cost_rate / 10 * 100, 100)  # $10/hour = 100 score
        
        # Availability score
        redis_available = self.metrics_history['redis_available'][-1]['value'] if self.metrics_history['redis_available'] else 1
        scores['availability'] = redis_available * 100
        
        # Calculate weighted score
        total_score = sum(scores[k] * weights[k] for k in weights)
        
        return round(total_score, 1)
    
    def _calculate_cache_efficiency(self) -> float:
        """Calculate cache efficiency metric."""
        # Efficiency = (hits * avg_cost_per_hit) / (memory_used * time)
        # Simplified version
        hit_rate = self.metrics_history['hit_rate'][-1]['value'] if self.metrics_history['hit_rate'] else 0
        memory_mb = self.metrics_history['l1_memory_mb'][-1]['value'] if self.metrics_history['l1_memory_mb'] else 1
        
        efficiency = (hit_rate * 100) / max(memory_mb, 1)
        return round(efficiency, 2)
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction."""
        if len(values) < 10:
            return 'stable'
        
        # Simple linear regression
        recent = values[-10:]
        older = values[-20:-10] if len(values) >= 20 else values[:10]
        
        recent_avg = statistics.mean(recent)
        older_avg = statistics.mean(older)
        
        change_percent = ((recent_avg - older_avg) / older_avg * 100) if older_avg else 0
        
        if change_percent > 5:
            return 'increasing'
        elif change_percent < -5:
            return 'decreasing'
        else:
            return 'stable'
    
    def _calculate_roi(self) -> float:
        """Calculate return on investment."""
        # Simplified ROI based on cost savings vs infrastructure cost
        # Assume $50/month for cache infrastructure
        monthly_cost = 50
        monthly_savings = self._calculate_cost_savings_rate() * 24 * 30
        
        if monthly_cost > 0:
            roi = ((monthly_savings - monthly_cost) / monthly_cost) * 100
            return round(roi, 1)
        return 0.0
    
    def _update_baselines(self, report: Dict[str, Any]):
        """Update performance baselines."""
        # Update baselines with recent averages
        for metric in ['hit_rate', 'response_time_ms']:
            if metric in report['trends']:
                self.performance_baselines[metric] = report['trends'][metric]['avg_1h']
    
    def _log_insights(self, report: Dict[str, Any]):
        """Log key insights from analytics."""
        logger.info(
            f"Cache Analytics - "
            f"Score: {report['performance_score']}/100, "
            f"Hit Rate: {report['summary']['current_hit_rate']:.1%}, "
            f"Cost Saved: ${report['cost_analysis'].get('total_saved', 0):.2f}, "
            f"Efficiency: {report['summary']['cache_efficiency']:.1f}"
        )
        
        # Log recommendations if any
        if report['recommendations']:
            logger.info(f"Cache Recommendations: {', '.join(report['recommendations'][:2])}")
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for monitoring dashboard."""
        return {
            'current_metrics': {
                metric: history[-1]['value'] if history else 0
                for metric, history in self.metrics_history.items()
            },
            'active_alerts': [
                alert.to_dict() for alert in self.active_alerts.values()
            ],
            'performance_score': self._calculate_performance_score(),
            'cost_savings': {
                'total': self.metrics_history['cost_saved_usd'][-1]['value'] 
                        if self.metrics_history['cost_saved_usd'] else 0,
                'hourly': self._calculate_cost_savings_rate()
            },
            'charts': self._generate_chart_data()
        }
    
    def _generate_chart_data(self) -> Dict[str, Any]:
        """Generate data for monitoring charts."""
        charts = {}
        
        # Hit rate over time
        hit_rate_history = self.metrics_history['hit_rate']
        charts['hit_rate_trend'] = [
            {
                'timestamp': h['timestamp'],
                'value': h['value'] * 100  # Convert to percentage
            }
            for h in hit_rate_history[-100:]  # Last 100 data points
        ]
        
        # Response time trend
        response_history = self.metrics_history['response_time_ms']
        charts['response_time_trend'] = [
            {
                'timestamp': h['timestamp'],
                'value': h['value']
            }
            for h in response_history[-100:]
        ]
        
        # Cost savings accumulation
        cost_history = self.metrics_history['cost_saved_usd']
        charts['cost_savings_cumulative'] = [
            {
                'timestamp': h['timestamp'],
                'value': h['value']
            }
            for h in cost_history[-100:]
        ]
        
        return charts


# Global cache monitor instance
cache_monitor = CacheMonitor()


# Export components
__all__ = [
    'cache_monitor',
    'CacheMonitor',
    'CacheAlert',
    'PerformanceThresholds'
]