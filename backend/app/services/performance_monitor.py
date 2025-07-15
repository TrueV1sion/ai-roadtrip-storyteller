"""
Performance monitoring service
"""

import time
import asyncio
from typing import Dict, Any, Optional, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
import statistics
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    name: str
    value: float
    unit: str
    timestamp: datetime
    tags: Dict[str, str]


class PerformanceMonitor:
    """Real-time performance monitoring service"""
    
    def __init__(self):
        self.metrics_buffer: List[PerformanceMetric] = []
        self.thresholds = {
            "voice_response_time": 2000,  # ms
            "api_response_time": 200,  # ms
            "database_query_time": 50,  # ms
            "cache_hit_rate": 0.8,  # ratio
            "error_rate": 0.01  # 1%
        }
        self.alerts_enabled = True
        
    @asynccontextmanager
    async def measure_time(self, operation_name: str, **tags):
        """Context manager to measure operation time"""
        start_time = time.time()
        
        try:
            yield
        finally:
            duration = (time.time() - start_time) * 1000  # Convert to ms
            
            metric = PerformanceMetric(
                name=f"{operation_name}_duration",
                value=duration,
                unit="ms",
                timestamp=datetime.now(),
                tags=tags
            )
            
            await self.record_metric(metric)
            
            # Check threshold
            if operation_name in self.thresholds:
                if duration > self.thresholds[operation_name]:
                    await self.trigger_alert(
                        f"{operation_name} exceeded threshold",
                        {"duration": duration, "threshold": self.thresholds[operation_name]}
                    )
    
    async def record_metric(self, metric: PerformanceMetric):
        """Record a performance metric"""
        self.metrics_buffer.append(metric)
        
        # Flush buffer if it's getting large
        if len(self.metrics_buffer) > 1000:
            await self.flush_metrics()
    
    async def flush_metrics(self):
        """Flush metrics to monitoring backend"""
        if not self.metrics_buffer:
            return
        
        try:
            # In production, this would send to Prometheus/Grafana
            metrics_to_send = self.metrics_buffer.copy()
            self.metrics_buffer.clear()
            
            # Log aggregated metrics
            await self._log_aggregated_metrics(metrics_to_send)
            
        except Exception as e:
            logger.error(f"Failed to flush metrics: {e}")
    
    async def _log_aggregated_metrics(self, metrics: List[PerformanceMetric]):
        """Log aggregated metrics for analysis"""
        # Group by metric name
        grouped = {}
        for metric in metrics:
            if metric.name not in grouped:
                grouped[metric.name] = []
            grouped[metric.name].append(metric.value)
        
        # Calculate statistics
        for name, values in grouped.items():
            if values:
                stats = {
                    "count": len(values),
                    "mean": statistics.mean(values),
                    "p50": statistics.median(values),
                    "p95": statistics.quantiles(values, n=20)[18] if len(values) > 20 else max(values),
                    "p99": statistics.quantiles(values, n=100)[98] if len(values) > 100 else max(values)
                }
                
                logger.info(f"Performance stats for {name}: {stats}")
    
    async def trigger_alert(self, message: str, details: Dict[str, Any]):
        """Trigger performance alert"""
        if not self.alerts_enabled:
            return
        
        alert = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "details": details,
            "severity": "warning"
        }
        
        logger.warning(f"Performance Alert: {alert}")
        
        # In production, this would send to alerting service
        # await alert_service.send_alert(alert)
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics summary"""
        if not self.metrics_buffer:
            return {}
        
        # Calculate current metrics
        recent_metrics = [m for m in self.metrics_buffer if 
                         (datetime.now() - m.timestamp).seconds < 60]
        
        summary = {}
        for metric in recent_metrics:
            if metric.name not in summary:
                summary[metric.name] = {
                    "current": metric.value,
                    "unit": metric.unit,
                    "samples": 1
                }
            else:
                # Running average
                prev_avg = summary[metric.name]["current"]
                prev_count = summary[metric.name]["samples"]
                new_avg = (prev_avg * prev_count + metric.value) / (prev_count + 1)
                
                summary[metric.name]["current"] = new_avg
                summary[metric.name]["samples"] = prev_count + 1
        
        return summary


# Global instance
performance_monitor = PerformanceMonitor()


# Decorators for easy monitoring
def monitor_performance(operation_name: str):
    """Decorator to monitor function performance"""
    def decorator(func: Callable):
        async def async_wrapper(*args, **kwargs):
            async with performance_monitor.measure_time(operation_name):
                return await func(*args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = (time.time() - start_time) * 1000
                asyncio.create_task(
                    performance_monitor.record_metric(
                        PerformanceMetric(
                            name=f"{operation_name}_duration",
                            value=duration,
                            unit="ms",
                            timestamp=datetime.now(),
                            tags={}
                        )
                    )
                )
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Usage in routes
@monitor_performance("voice_synthesis")
async def synthesize_voice(text: str, voice_id: str) -> bytes:
    # Voice synthesis logic
    pass


@monitor_performance("story_generation")
async def generate_story(context: dict) -> str:
    # Story generation logic
    pass
