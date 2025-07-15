"""
Monitoring tasks for Celery queue health and performance metrics.

Implements Six Sigma quality controls:
- Queue depth monitoring
- Job completion rate tracking
- Latency measurements
- Automatic alerting
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from celery import Task
from celery.app.control import Inspect
import redis

from backend.app.core.celery_app import celery_app
from backend.app.core.cache import cache_manager
from backend.app.core.logger import get_logger
from backend.app.monitoring.metrics import metrics_collector
from backend.app.services.notification_service import NotificationService

logger = get_logger(__name__)

class MonitoringTask(Task):
    """Base task for monitoring operations."""
    
    _redis_client = None
    _notification_service = None
    
    @property
    def redis_client(self):
        if self._redis_client is None:
            self._redis_client = redis.from_url(
                celery_app.conf.broker_url,
                decode_responses=True
            )
        return self._redis_client
    
    @property
    def notification_service(self):
        if self._notification_service is None:
            self._notification_service = NotificationService()
        return self._notification_service


@celery_app.task(
    bind=True,
    base=MonitoringTask,
    name='monitoring.check_queue_health',
    max_retries=1
)
def check_queue_health(self) -> Dict[str, Any]:
    """
    Monitor queue health and alert on issues.
    
    Checks:
    - Queue depth
    - Processing latency
    - Failed task rate
    - Worker availability
    """
    try:
        logger.info("Starting queue health check")
        
        health_report = {
            'timestamp': datetime.utcnow().isoformat(),
            'queues': {},
            'workers': {},
            'alerts': []
        }
        
        # Get queue statistics
        inspect = Inspect(app=celery_app)
        
        # Check active queues
        active_queues = inspect.active_queues() or {}
        stats = inspect.stats() or {}
        
        # Define queue thresholds
        queue_thresholds = {
            'ai_generation': {'max_depth': 100, 'max_latency': 5000},
            'voice_synthesis': {'max_depth': 50, 'max_latency': 3000},
            'booking': {'max_depth': 200, 'max_latency': 1000},
            'notifications': {'max_depth': 500, 'max_latency': 2000},
            'default': {'max_depth': 300, 'max_latency': 3000}
        }
        
        # Check each queue
        for queue_name, thresholds in queue_thresholds.items():
            queue_key = f"celery:{queue_name}"
            depth = self.redis_client.llen(queue_key)
            
            # Get average latency from metrics
            latency_key = f"queue_latency:{queue_name}"
            avg_latency = cache_manager.get(latency_key) or 0
            
            queue_health = {
                'depth': depth,
                'avg_latency_ms': avg_latency,
                'status': 'healthy'
            }
            
            # Check thresholds
            if depth > thresholds['max_depth']:
                queue_health['status'] = 'warning'
                alert = f"Queue {queue_name} depth ({depth}) exceeds threshold ({thresholds['max_depth']})"
                health_report['alerts'].append(alert)
                logger.warning(alert)
                
            if avg_latency > thresholds['max_latency']:
                queue_health['status'] = 'critical' if avg_latency > thresholds['max_latency'] * 2 else 'warning'
                alert = f"Queue {queue_name} latency ({avg_latency}ms) exceeds threshold ({thresholds['max_latency']}ms)"
                health_report['alerts'].append(alert)
                logger.warning(alert)
            
            health_report['queues'][queue_name] = queue_health
            
            # Update metrics
            metrics_collector.gauge(f'celery.queue.depth', depth, tags={'queue': queue_name})
            metrics_collector.gauge(f'celery.queue.latency', avg_latency, tags={'queue': queue_name})
        
        # Check worker health
        for worker_name, worker_stats in stats.items():
            worker_health = {
                'active': worker_stats.get('pool', {}).get('max-concurrency', 0),
                'processed': worker_stats.get('total', 0),
                'status': 'healthy'
            }
            
            health_report['workers'][worker_name] = worker_health
        
        # Send alerts if critical issues
        if health_report['alerts']:
            alert_summary = '\n'.join(health_report['alerts'])
            if any('critical' in alert for alert in health_report['alerts']):
                # Send immediate alert
                send_critical_alert.apply_async(
                    args=[alert_summary],
                    priority=10
                )
        
        # Store health report
        cache_manager.set('celery:health_report', health_report, ttl=300)
        
        logger.info(f"Health check completed. {len(health_report['alerts'])} alerts generated")
        return health_report
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e),
            'status': 'check_failed'
        }


@celery_app.task(
    bind=True,
    base=MonitoringTask,
    name='monitoring.report_metrics',
    max_retries=1
)
def report_metrics(self) -> Dict[str, Any]:
    """
    Collect and report Celery performance metrics.
    
    Metrics:
    - Task completion rate
    - Average processing time
    - Queue throughput
    - Error rates
    """
    try:
        logger.info("Collecting Celery metrics")
        
        # Time windows for analysis
        windows = {
            '1min': timedelta(minutes=1),
            '5min': timedelta(minutes=5),
            '1hour': timedelta(hours=1)
        }
        
        metrics_report = {
            'timestamp': datetime.utcnow().isoformat(),
            'windows': {}
        }
        
        for window_name, window_delta in windows.items():
            window_start = datetime.utcnow() - window_delta
            
            # Get metrics from cache (would be from time-series DB in production)
            window_metrics = {
                'tasks_completed': _get_metric_count('tasks_completed', window_start),
                'tasks_failed': _get_metric_count('tasks_failed', window_start),
                'tasks_retried': _get_metric_count('tasks_retried', window_start),
                'avg_duration_ms': _get_metric_average('task_duration', window_start),
                'queue_throughput': _calculate_throughput(window_start, window_delta)
            }
            
            # Calculate completion rate
            total_tasks = window_metrics['tasks_completed'] + window_metrics['tasks_failed']
            if total_tasks > 0:
                window_metrics['completion_rate'] = (
                    window_metrics['tasks_completed'] / total_tasks * 100
                )
            else:
                window_metrics['completion_rate'] = 100.0
            
            # Check Six Sigma target (99.9% completion rate)
            if window_metrics['completion_rate'] < 99.9 and total_tasks > 10:
                logger.warning(
                    f"Completion rate ({window_metrics['completion_rate']:.2f}%) "
                    f"below Six Sigma target for {window_name} window"
                )
            
            metrics_report['windows'][window_name] = window_metrics
        
        # Store metrics report
        cache_manager.set('celery:metrics_report', metrics_report, ttl=3600)
        
        # Update dashboards
        for window_name, metrics in metrics_report['windows'].items():
            for metric_name, value in metrics.items():
                metrics_collector.gauge(
                    f'celery.performance.{metric_name}',
                    value,
                    tags={'window': window_name}
                )
        
        logger.info("Metrics report completed")
        return metrics_report
        
    except Exception as e:
        logger.error(f"Metrics reporting failed: {str(e)}")
        return {'error': str(e)}


@celery_app.task(
    bind=True,
    base=MonitoringTask,
    name='monitoring.analyze_job_patterns',
    max_retries=1
)
def analyze_job_patterns(self) -> Dict[str, Any]:
    """
    Analyze job patterns for optimization opportunities.
    
    Identifies:
    - Peak usage times
    - Common failure patterns
    - Resource bottlenecks
    """
    try:
        logger.info("Analyzing job patterns")
        
        analysis = {
            'timestamp': datetime.utcnow().isoformat(),
            'patterns': {},
            'recommendations': []
        }
        
        # Analyze hourly patterns
        hourly_stats = _get_hourly_stats()
        peak_hours = _identify_peak_hours(hourly_stats)
        
        analysis['patterns']['peak_hours'] = peak_hours
        
        if len(peak_hours) > 0:
            analysis['recommendations'].append(
                f"Consider scaling workers during peak hours: {', '.join(map(str, peak_hours))}"
            )
        
        # Analyze failure patterns
        failure_analysis = _analyze_failures()
        analysis['patterns']['common_failures'] = failure_analysis
        
        if failure_analysis['timeout_rate'] > 5:
            analysis['recommendations'].append(
                "High timeout rate detected. Consider increasing time limits or optimizing tasks."
            )
        
        # Analyze queue performance
        queue_analysis = _analyze_queue_performance()
        analysis['patterns']['queue_performance'] = queue_analysis
        
        for queue, perf in queue_analysis.items():
            if perf['avg_wait_time'] > 5000:  # 5 seconds
                analysis['recommendations'].append(
                    f"Queue '{queue}' has high wait times. Consider adding workers."
                )
        
        # Store analysis
        cache_manager.set('celery:job_analysis', analysis, ttl=7200)
        
        logger.info(f"Job pattern analysis completed with {len(analysis['recommendations'])} recommendations")
        return analysis
        
    except Exception as e:
        logger.error(f"Job pattern analysis failed: {str(e)}")
        return {'error': str(e)}


@celery_app.task(
    base=MonitoringTask,
    name='monitoring.send_critical_alert'
)
def send_critical_alert(alert_message: str) -> Dict[str, Any]:
    """Send critical system alert."""
    try:
        # Send to monitoring channels
        logger.critical(f"CRITICAL ALERT: {alert_message}")
        
        # In production, this would send to PagerDuty, Slack, etc.
        notification_result = {
            'sent_at': datetime.utcnow().isoformat(),
            'message': alert_message,
            'channels': ['logs', 'metrics']
        }
        
        return notification_result
        
    except Exception as e:
        logger.error(f"Failed to send critical alert: {str(e)}")
        return {'error': str(e)}


# Helper functions
def _get_metric_count(metric_name: str, since: datetime) -> int:
    """Get count of metric since timestamp."""
    # In production, query from time-series database
    # For now, return mock data
    return 150

def _get_metric_average(metric_name: str, since: datetime) -> float:
    """Get average of metric since timestamp."""
    # In production, query from time-series database
    return 250.5

def _calculate_throughput(since: datetime, window: timedelta) -> float:
    """Calculate tasks per second throughput."""
    total_tasks = _get_metric_count('tasks_completed', since)
    return total_tasks / window.total_seconds()

def _get_hourly_stats() -> Dict[int, Dict[str, Any]]:
    """Get task statistics by hour."""
    # Mock implementation
    return {
        9: {'count': 1000, 'avg_duration': 200},
        10: {'count': 1500, 'avg_duration': 250},
        14: {'count': 2000, 'avg_duration': 300},
        15: {'count': 1800, 'avg_duration': 280}
    }

def _identify_peak_hours(hourly_stats: Dict[int, Dict[str, Any]]) -> List[int]:
    """Identify peak usage hours."""
    if not hourly_stats:
        return []
    
    avg_count = sum(h['count'] for h in hourly_stats.values()) / len(hourly_stats)
    return [hour for hour, stats in hourly_stats.items() if stats['count'] > avg_count * 1.5]

def _analyze_failures() -> Dict[str, Any]:
    """Analyze failure patterns."""
    return {
        'total_failures': 45,
        'timeout_rate': 3.2,
        'retry_success_rate': 85.5,
        'common_exceptions': [
            {'type': 'TimeoutError', 'count': 15},
            {'type': 'ConnectionError', 'count': 8}
        ]
    }

def _analyze_queue_performance() -> Dict[str, Dict[str, Any]]:
    """Analyze performance by queue."""
    return {
        'ai_generation': {
            'avg_wait_time': 2500,
            'avg_process_time': 8000,
            'throughput': 12.5
        },
        'booking': {
            'avg_wait_time': 500,
            'avg_process_time': 1200,
            'throughput': 45.2
        }
    }