"""
Real-time Performance Monitoring System
======================================

Continuous performance monitoring with real-time alerting and automated
performance regression detection.
"""

import asyncio
import time
import json
import psutil
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
import numpy as np
import redis.asyncio as redis
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import logging
from pathlib import Path
import sqlite3

logger = logging.getLogger(__name__)


@dataclass
class PerformanceAlert:
    """Performance alert definition"""
    id: str
    metric_name: str
    threshold: float
    comparison: str  # "gt", "lt", "eq"
    severity: str  # "warning", "critical"
    duration_minutes: int  # Alert only if condition persists
    description: str
    enabled: bool = True
    last_triggered: Optional[datetime] = None
    

@dataclass
class PerformanceMetric:
    """Performance metric data point"""
    timestamp: datetime
    name: str
    value: float
    tags: Dict[str, str] = field(default_factory=dict)
    

@dataclass
class PerformanceReport:
    """Performance monitoring report"""
    timestamp: datetime
    period_minutes: int
    summary: Dict[str, Any]
    alerts_triggered: List[PerformanceAlert]
    recommendations: List[str]
    raw_metrics: List[PerformanceMetric]


class PerformanceMonitor:
    """Real-time performance monitoring system"""
    
    def __init__(self,
                 api_base_url: str = "http://localhost:8000",
                 redis_url: str = "redis://localhost:6379",
                 db_path: str = "performance_monitoring.db"):
        self.api_base_url = api_base_url
        self.redis_url = redis_url
        self.db_path = db_path
        self.session: Optional[aiohttp.ClientSession] = None
        self.redis_client: Optional[redis.Redis] = None
        self.running = False
        self.monitoring_tasks: List[asyncio.Task] = []
        self.metrics_buffer: List[PerformanceMetric] = []
        self.alerts: List[PerformanceAlert] = []
        self.last_report_time = datetime.now()
        
        # Prometheus metrics
        self.registry = CollectorRegistry()
        self.response_time_histogram = Histogram(
            'api_response_time_seconds',
            'API response time in seconds',
            ['endpoint', 'method'],
            registry=self.registry
        )
        self.error_rate_gauge = Gauge(
            'api_error_rate',
            'API error rate percentage',
            ['endpoint'],
            registry=self.registry
        )
        self.active_connections_gauge = Gauge(
            'database_active_connections',
            'Number of active database connections',
            registry=self.registry
        )
        self.cache_hit_rate_gauge = Gauge(
            'cache_hit_rate',
            'Cache hit rate percentage',
            registry=self.registry
        )
        self.system_cpu_gauge = Gauge(
            'system_cpu_usage',
            'System CPU usage percentage',
            registry=self.registry
        )
        self.system_memory_gauge = Gauge(
            'system_memory_usage',
            'System memory usage percentage',
            registry=self.registry
        )
        
        # Initialize database
        self._init_database()
        
        # Setup default alerts
        self._setup_default_alerts()
        
    def _init_database(self):
        """Initialize SQLite database for metrics storage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                name TEXT NOT NULL,
                value REAL NOT NULL,
                tags TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                alert_id TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                threshold REAL NOT NULL,
                actual_value REAL NOT NULL,
                severity TEXT NOT NULL,
                description TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        
    def _setup_default_alerts(self):
        """Setup default performance alerts"""
        self.alerts = [
            PerformanceAlert(
                id="high_api_response_time",
                metric_name="api_response_time_avg",
                threshold=1000,  # 1 second
                comparison="gt",
                severity="warning",
                duration_minutes=2,
                description="API response time is above 1 second"
            ),
            PerformanceAlert(
                id="critical_api_response_time",
                metric_name="api_response_time_avg",
                threshold=3000,  # 3 seconds
                comparison="gt",
                severity="critical",
                duration_minutes=1,
                description="API response time is critically high (>3s)"
            ),
            PerformanceAlert(
                id="high_error_rate",
                metric_name="api_error_rate",
                threshold=5.0,  # 5%
                comparison="gt",
                severity="warning",
                duration_minutes=3,
                description="API error rate is above 5%"
            ),
            PerformanceAlert(
                id="critical_error_rate",
                metric_name="api_error_rate",
                threshold=15.0,  # 15%
                comparison="gt",
                severity="critical",
                duration_minutes=1,
                description="API error rate is critically high (>15%)"
            ),
            PerformanceAlert(
                id="low_cache_hit_rate",
                metric_name="cache_hit_rate",
                threshold=70.0,  # 70%
                comparison="lt",
                severity="warning",
                duration_minutes=5,
                description="Cache hit rate is below 70%"
            ),
            PerformanceAlert(
                id="high_cpu_usage",
                metric_name="system_cpu_usage",
                threshold=80.0,  # 80%
                comparison="gt",
                severity="warning",
                duration_minutes=5,
                description="System CPU usage is above 80%"
            ),
            PerformanceAlert(
                id="high_memory_usage",
                metric_name="system_memory_usage",
                threshold=85.0,  # 85%
                comparison="gt",
                severity="critical",
                duration_minutes=3,
                description="System memory usage is above 85%"
            ),
            PerformanceAlert(
                id="database_connection_saturation",
                metric_name="database_active_connections",
                threshold=80,  # 80 connections
                comparison="gt",
                severity="warning",
                duration_minutes=2,
                description="Database connection pool is near saturation"
            )
        ]
        
    async def setup(self):
        """Initialize monitoring system"""
        logger.info("Setting up performance monitoring...")
        
        # HTTP session for API monitoring
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
        # Redis client for cache monitoring
        try:
            self.redis_client = await redis.from_url(self.redis_url)
            await self.redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            
    async def teardown(self):
        """Cleanup monitoring system"""
        logger.info("Shutting down performance monitoring...")
        
        self.running = False
        
        # Cancel all monitoring tasks
        for task in self.monitoring_tasks:
            task.cancel()
            
        # Wait for tasks to complete
        if self.monitoring_tasks:
            await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
            
        # Cleanup connections
        if self.session:
            await self.session.close()
        if self.redis_client:
            await self.redis_client.close()
            
    async def start_monitoring(self, interval_seconds: int = 30):
        """Start continuous performance monitoring"""
        logger.info(f"Starting performance monitoring (interval: {interval_seconds}s)")
        
        self.running = True
        
        # Start monitoring tasks
        self.monitoring_tasks = [
            asyncio.create_task(self._monitor_api_performance(interval_seconds)),
            asyncio.create_task(self._monitor_system_resources(interval_seconds)),
            asyncio.create_task(self._monitor_cache_performance(interval_seconds)),
            asyncio.create_task(self._monitor_database_performance(interval_seconds)),
            asyncio.create_task(self._check_alerts(interval_seconds)),
            asyncio.create_task(self._generate_periodic_reports(300))  # 5-minute reports
        ]
        
        # Wait for all tasks
        await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
        
    async def _monitor_api_performance(self, interval: int):
        """Monitor API endpoint performance"""
        endpoints = [
            ("/api/health", "GET"),
            ("/api/voice-assistant/interact", "POST"),
            ("/api/directions", "POST"),
            ("/api/poi/search", "GET"),
            ("/api/personalized-story", "POST")
        ]
        
        while self.running:
            for endpoint, method in endpoints:
                try:
                    start_time = time.time()
                    
                    if method == "GET":
                        async with self.session.get(f"{self.api_base_url}{endpoint}") as response:
                            await response.text()
                            status_code = response.status
                    else:
                        # POST with minimal test data
                        test_data = self._get_test_data_for_endpoint(endpoint)
                        async with self.session.post(
                            f"{self.api_base_url}{endpoint}",
                            json=test_data
                        ) as response:
                            await response.text()
                            status_code = response.status
                            
                    response_time = (time.time() - start_time) * 1000  # Convert to ms
                    
                    # Record metrics
                    self._record_metric("api_response_time", response_time, {
                        "endpoint": endpoint,
                        "method": method,
                        "status_code": str(status_code)
                    })
                    
                    # Update Prometheus metrics
                    self.response_time_histogram.labels(
                        endpoint=endpoint,
                        method=method
                    ).observe(response_time / 1000)
                    
                    # Record error if status code indicates failure
                    if status_code >= 400:
                        self._record_metric("api_error", 1, {
                            "endpoint": endpoint,
                            "status_code": str(status_code)
                        })
                        
                except Exception as e:
                    logger.warning(f"Error monitoring {endpoint}: {e}")
                    self._record_metric("api_error", 1, {
                        "endpoint": endpoint,
                        "error": "connection_failed"
                    })
                    
            await asyncio.sleep(interval)
            
    async def _monitor_system_resources(self, interval: int):
        """Monitor system resource usage"""
        while self.running:
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self._record_metric("system_cpu_usage", cpu_percent)
                self.system_cpu_gauge.set(cpu_percent)
                
                # Memory usage
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                self._record_metric("system_memory_usage", memory_percent)
                self.system_memory_gauge.set(memory_percent)
                
                # Disk usage
                disk = psutil.disk_usage('/')
                disk_percent = (disk.used / disk.total) * 100
                self._record_metric("system_disk_usage", disk_percent)
                
                # Network I/O
                network = psutil.net_io_counters()
                self._record_metric("network_bytes_sent", network.bytes_sent)
                self._record_metric("network_bytes_recv", network.bytes_recv)
                
                # Process-specific metrics
                try:
                    # Find main application process (gunicorn/uvicorn)
                    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                        if 'uvicorn' in proc.info['name'] or 'gunicorn' in proc.info['name']:
                            self._record_metric("app_cpu_usage", proc.info['cpu_percent'])
                            self._record_metric("app_memory_usage", proc.info['memory_percent'])
                            break
                except psutil.NoSuchProcess:
                    pass
                    
            except Exception as e:
                logger.warning(f"Error monitoring system resources: {e}")
                
            await asyncio.sleep(interval)
            
    async def _monitor_cache_performance(self, interval: int):
        """Monitor Redis cache performance"""
        if not self.redis_client:
            return
            
        while self.running:
            try:
                # Get Redis info
                info = await self.redis_client.info()
                
                # Cache hit rate
                hits = info.get('keyspace_hits', 0)
                misses = info.get('keyspace_misses', 0)
                total = hits + misses
                hit_rate = (hits / total * 100) if total > 0 else 0
                
                self._record_metric("cache_hit_rate", hit_rate)
                self.cache_hit_rate_gauge.set(hit_rate)
                
                # Memory usage
                used_memory = info.get('used_memory', 0)
                max_memory = info.get('maxmemory', 0)
                if max_memory > 0:
                    memory_usage = (used_memory / max_memory) * 100
                    self._record_metric("cache_memory_usage", memory_usage)
                    
                # Connected clients
                connected_clients = info.get('connected_clients', 0)
                self._record_metric("cache_connected_clients", connected_clients)
                
                # Operations per second
                total_commands = info.get('total_commands_processed', 0)
                self._record_metric("cache_ops_per_second", total_commands)
                
            except Exception as e:
                logger.warning(f"Error monitoring cache performance: {e}")
                
            await asyncio.sleep(interval)
            
    async def _monitor_database_performance(self, interval: int):
        """Monitor database performance"""
        while self.running:
            try:
                # This would require actual database connection
                # For now, we'll simulate some basic metrics
                
                # Simulate active connections (would query pg_stat_activity)
                active_connections = 45  # Placeholder
                self._record_metric("database_active_connections", active_connections)
                self.active_connections_gauge.set(active_connections)
                
                # Simulate query performance metrics
                # In production, you'd query pg_stat_statements or similar
                self._record_metric("database_avg_query_time", 25.5)  # Placeholder ms
                self._record_metric("database_slow_queries", 3)  # Placeholder count
                
            except Exception as e:
                logger.warning(f"Error monitoring database performance: {e}")
                
            await asyncio.sleep(interval)
            
    async def _check_alerts(self, interval: int):
        """Check alert conditions and trigger notifications"""
        while self.running:
            current_time = datetime.now()
            
            for alert in self.alerts:
                if not alert.enabled:
                    continue
                    
                try:
                    # Get recent metrics for this alert
                    recent_metrics = self._get_recent_metrics(
                        alert.metric_name,
                        alert.duration_minutes
                    )
                    
                    if not recent_metrics:
                        continue
                        
                    # Calculate average value over the duration
                    avg_value = sum(m.value for m in recent_metrics) / len(recent_metrics)
                    
                    # Check alert condition
                    condition_met = False
                    if alert.comparison == "gt" and avg_value > alert.threshold:
                        condition_met = True
                    elif alert.comparison == "lt" and avg_value < alert.threshold:
                        condition_met = True
                    elif alert.comparison == "eq" and abs(avg_value - alert.threshold) < 0.001:
                        condition_met = True
                        
                    if condition_met:
                        # Check if enough time has passed since last trigger
                        if (alert.last_triggered is None or 
                            (current_time - alert.last_triggered).total_seconds() > 300):  # 5 min cooldown
                            
                            await self._trigger_alert(alert, avg_value)
                            alert.last_triggered = current_time
                            
                except Exception as e:
                    logger.error(f"Error checking alert {alert.id}: {e}")
                    
            await asyncio.sleep(interval)
            
    async def _generate_periodic_reports(self, interval: int):
        """Generate periodic performance reports"""
        while self.running:
            try:
                current_time = datetime.now()
                
                # Generate report every interval
                if (current_time - self.last_report_time).total_seconds() >= interval:
                    report = await self._generate_performance_report(interval // 60)
                    await self._save_report(report)
                    self.last_report_time = current_time
                    
            except Exception as e:
                logger.error(f"Error generating periodic report: {e}")
                
            await asyncio.sleep(60)  # Check every minute
            
    def _get_test_data_for_endpoint(self, endpoint: str) -> Dict[str, Any]:
        """Get minimal test data for API endpoint testing"""
        test_data = {
            "/api/voice-assistant/interact": {
                "user_input": "health check",
                "context": {"location": {"lat": 37.7749, "lng": -122.4194}}
            },
            "/api/directions": {
                "origin": "San Francisco, CA",
                "destination": "Los Angeles, CA"
            },
            "/api/personalized-story": {
                "origin": "San Francisco, CA",
                "destination": "Los Angeles, CA",
                "interests": ["test"]
            }
        }
        return test_data.get(endpoint, {})
        
    def _record_metric(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a performance metric"""
        metric = PerformanceMetric(
            timestamp=datetime.now(),
            name=name,
            value=value,
            tags=tags or {}
        )
        
        self.metrics_buffer.append(metric)
        
        # Persist to database periodically
        if len(self.metrics_buffer) >= 100:
            self._persist_metrics()
            
    def _persist_metrics(self):
        """Persist metrics buffer to database"""
        if not self.metrics_buffer:
            return
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for metric in self.metrics_buffer:
                cursor.execute(
                    "INSERT INTO metrics (timestamp, name, value, tags) VALUES (?, ?, ?, ?)",
                    (
                        metric.timestamp.isoformat(),
                        metric.name,
                        metric.value,
                        json.dumps(metric.tags)
                    )
                )
                
            conn.commit()
            conn.close()
            
            self.metrics_buffer.clear()
            
        except Exception as e:
            logger.error(f"Error persisting metrics: {e}")
            
    def _get_recent_metrics(self, metric_name: str, duration_minutes: int) -> List[PerformanceMetric]:
        """Get recent metrics for alert checking"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_time = (datetime.now() - timedelta(minutes=duration_minutes)).isoformat()
            
            cursor.execute(
                "SELECT timestamp, name, value, tags FROM metrics WHERE name = ? AND timestamp > ? ORDER BY timestamp DESC",
                (metric_name, cutoff_time)
            )
            
            rows = cursor.fetchall()
            conn.close()
            
            metrics = []
            for row in rows:
                metric = PerformanceMetric(
                    timestamp=datetime.fromisoformat(row[0]),
                    name=row[1],
                    value=row[2],
                    tags=json.loads(row[3]) if row[3] else {}
                )
                metrics.append(metric)
                
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting recent metrics: {e}")
            return []
            
    async def _trigger_alert(self, alert: PerformanceAlert, actual_value: float):
        """Trigger a performance alert"""
        logger.warning(f"ALERT TRIGGERED: {alert.id} - {alert.description} "
                      f"(actual: {actual_value}, threshold: {alert.threshold})")
        
        # Record alert in database
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO alerts (timestamp, alert_id, metric_name, threshold, actual_value, severity, description) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    datetime.now().isoformat(),
                    alert.id,
                    alert.metric_name,
                    alert.threshold,
                    actual_value,
                    alert.severity,
                    alert.description
                )
            )
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error recording alert: {e}")
            
        # Send notification (placeholder - implement email/Slack/etc.)
        await self._send_alert_notification(alert, actual_value)
        
    async def _send_alert_notification(self, alert: PerformanceAlert, actual_value: float):
        """Send alert notification"""
        # This is a placeholder - implement actual notification system
        logger.info(f"Would send {alert.severity} notification for {alert.id}")
        
        # Example: Send email notification
        # self._send_email_alert(alert, actual_value)
        
        # Example: Send Slack notification
        # await self._send_slack_alert(alert, actual_value)
        
    async def _generate_performance_report(self, period_minutes: int) -> PerformanceReport:
        """Generate comprehensive performance report"""
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=period_minutes)
        
        # Get metrics for period
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT name, AVG(value) as avg_value, MIN(value) as min_value, MAX(value) as max_value, COUNT(*) as count "
            "FROM metrics WHERE timestamp > ? GROUP BY name",
            (start_time.isoformat(),)
        )
        
        metric_summary = {}
        for row in cursor.fetchall():
            metric_summary[row[0]] = {
                "avg": row[1],
                "min": row[2],
                "max": row[3],
                "count": row[4]
            }
            
        # Get alerts triggered in period
        cursor.execute(
            "SELECT alert_id, metric_name, threshold, actual_value, severity, description "
            "FROM alerts WHERE timestamp > ?",
            (start_time.isoformat(),)
        )
        
        alerts_triggered = []
        for row in cursor.fetchall():
            alert = PerformanceAlert(
                id=row[0],
                metric_name=row[1],
                threshold=row[2],
                comparison="gt",  # Simplified
                severity=row[4],
                duration_minutes=0,  # Not stored
                description=row[5]
            )
            alerts_triggered.append(alert)
            
        conn.close()
        
        # Generate recommendations
        recommendations = self._generate_recommendations(metric_summary)
        
        return PerformanceReport(
            timestamp=end_time,
            period_minutes=period_minutes,
            summary=metric_summary,
            alerts_triggered=alerts_triggered,
            recommendations=recommendations,
            raw_metrics=[]  # Not included in summary
        )
        
    def _generate_recommendations(self, metric_summary: Dict[str, Any]) -> List[str]:
        """Generate performance recommendations based on metrics"""
        recommendations = []
        
        # API performance recommendations
        if "api_response_time" in metric_summary:
            avg_response_time = metric_summary["api_response_time"]["avg"]
            if avg_response_time > 500:
                recommendations.append(
                    f"API response time averaging {avg_response_time:.0f}ms is high. "
                    "Consider implementing caching, optimizing database queries, or horizontal scaling."
                )
                
        # Cache performance recommendations
        if "cache_hit_rate" in metric_summary:
            hit_rate = metric_summary["cache_hit_rate"]["avg"]
            if hit_rate < 70:
                recommendations.append(
                    f"Cache hit rate of {hit_rate:.1f}% is low. "
                    "Review caching strategy and consider pre-warming frequently accessed data."
                )
                
        # System resource recommendations
        if "system_cpu_usage" in metric_summary:
            cpu_usage = metric_summary["system_cpu_usage"]["avg"]
            if cpu_usage > 75:
                recommendations.append(
                    f"CPU usage averaging {cpu_usage:.1f}% is high. "
                    "Consider scaling horizontally or optimizing CPU-intensive operations."
                )
                
        if "system_memory_usage" in metric_summary:
            memory_usage = metric_summary["system_memory_usage"]["avg"]
            if memory_usage > 80:
                recommendations.append(
                    f"Memory usage averaging {memory_usage:.1f}% is high. "
                    "Review memory leaks and consider increasing available memory."
                )
                
        if not recommendations:
            recommendations.append("All performance metrics are within acceptable ranges.")
            
        return recommendations
        
    async def _save_report(self, report: PerformanceReport):
        """Save performance report"""
        report_dir = Path("tests/performance/reports/monitoring")
        report_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"performance_report_{report.timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        
        report_data = {
            "timestamp": report.timestamp.isoformat(),
            "period_minutes": report.period_minutes,
            "summary": report.summary,
            "alerts_triggered": [
                {
                    "id": alert.id,
                    "metric_name": alert.metric_name,
                    "threshold": alert.threshold,
                    "severity": alert.severity,
                    "description": alert.description
                }
                for alert in report.alerts_triggered
            ],
            "recommendations": report.recommendations
        }
        
        with open(report_dir / filename, "w") as f:
            json.dump(report_data, f, indent=2)
            
        logger.info(f"Performance report saved: {filename}")
        
        # Also log key metrics
        logger.info(f"Performance Summary ({report.period_minutes}min): "
                   f"API avg response: {report.summary.get('api_response_time', {}).get('avg', 0):.0f}ms, "
                   f"Cache hit rate: {report.summary.get('cache_hit_rate', {}).get('avg', 0):.1f}%, "
                   f"Alerts: {len(report.alerts_triggered)}")
        
    def get_prometheus_metrics(self) -> str:
        """Get Prometheus-formatted metrics"""
        return generate_latest(self.registry).decode('utf-8')
        
    async def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status"""
        recent_metrics = {}
        
        # Get recent averages for key metrics
        key_metrics = [
            "api_response_time",
            "api_error_rate", 
            "cache_hit_rate",
            "system_cpu_usage",
            "system_memory_usage"
        ]
        
        for metric_name in key_metrics:
            metrics = self._get_recent_metrics(metric_name, 5)  # Last 5 minutes
            if metrics:
                recent_metrics[metric_name] = sum(m.value for m in metrics) / len(metrics)
                
        # Determine overall health
        health_score = 100
        status = "healthy"
        
        if recent_metrics.get("api_response_time", 0) > 1000:
            health_score -= 20
            status = "degraded"
            
        if recent_metrics.get("api_error_rate", 0) > 5:
            health_score -= 30
            status = "unhealthy"
            
        if recent_metrics.get("system_cpu_usage", 0) > 80:
            health_score -= 15
            
        if recent_metrics.get("system_memory_usage", 0) > 85:
            health_score -= 20
            status = "unhealthy"
            
        return {
            "status": status,
            "health_score": max(0, health_score),
            "recent_metrics": recent_metrics,
            "last_updated": datetime.now().isoformat()
        }


async def main():
    """Run performance monitoring"""
    monitor = PerformanceMonitor()
    
    try:
        await monitor.setup()
        
        # Start monitoring
        await monitor.start_monitoring(interval_seconds=30)
        
    except KeyboardInterrupt:
        logger.info("Shutting down monitoring...")
    finally:
        await monitor.teardown()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())