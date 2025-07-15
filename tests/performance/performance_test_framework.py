"""
Comprehensive Performance Testing Framework for AI Road Trip Storyteller
========================================================================

This framework provides advanced load testing, stress testing, and performance
benchmarking capabilities with real-time monitoring and reporting.
"""

import asyncio
import time
import json
import statistics
import psutil
import aiohttp
import redis.asyncio as redis
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import numpy as np
from locust import HttpUser, task, between, events
from locust.env import Environment
from locust.stats import StatsEntry
import matplotlib.pyplot as plt
import pandas as pd
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
request_count = Counter('roadtrip_requests_total', 'Total requests', ['endpoint', 'method', 'status'])
request_duration = Histogram('roadtrip_request_duration_seconds', 'Request duration', ['endpoint'])
active_users = Gauge('roadtrip_active_users', 'Number of active users')
cache_hit_rate = Gauge('roadtrip_cache_hit_rate', 'Cache hit rate percentage')
ai_api_calls = Counter('roadtrip_ai_api_calls_total', 'Total AI API calls')
database_connections = Gauge('roadtrip_database_connections', 'Active database connections')
error_rate = Gauge('roadtrip_error_rate', 'Error rate percentage')


@dataclass
class PerformanceMetrics:
    """Performance metrics for a test run"""
    timestamp: str
    scenario: str
    duration_seconds: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time_ms: float
    median_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    requests_per_second: float
    error_rate: float
    cpu_usage_avg: float
    memory_usage_avg: float
    database_pool_usage: float
    cache_hit_rate: float
    ai_api_calls: int
    concurrent_users: int
    

@dataclass
class EndpointMetrics:
    """Metrics for individual endpoints"""
    endpoint: str
    method: str
    total_calls: int
    success_rate: float
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    errors: Dict[int, int]  # status_code: count


class PerformanceTestRunner:
    """Main performance test runner with advanced monitoring"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.metrics: List[PerformanceMetrics] = []
        self.endpoint_metrics: Dict[str, EndpointMetrics] = {}
        self.redis_client: Optional[redis.Redis] = None
        self.start_time: Optional[float] = None
        self.system_monitor_task: Optional[asyncio.Task] = None
        
    async def setup(self):
        """Initialize test environment"""
        logger.info("Setting up performance test environment...")
        
        # Start Prometheus metrics server
        start_http_server(9091)
        
        # Connect to Redis for cache monitoring
        try:
            self.redis_client = await redis.from_url("redis://localhost:6379")
            await self.redis_client.ping()
            logger.info("Connected to Redis for cache monitoring")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            
        # Start system monitoring
        self.system_monitor_task = asyncio.create_task(self._monitor_system_resources())
        
    async def teardown(self):
        """Cleanup test environment"""
        logger.info("Tearing down performance test environment...")
        
        if self.system_monitor_task:
            self.system_monitor_task.cancel()
            
        if self.redis_client:
            await self.redis_client.close()
            
    async def _monitor_system_resources(self):
        """Monitor system resources during tests"""
        while True:
            try:
                # CPU and Memory monitoring
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                
                # Database connection monitoring (would need actual DB client)
                # This is a placeholder - implement based on your DB setup
                db_connections = await self._get_database_connections()
                
                # Update Prometheus metrics
                database_connections.set(db_connections)
                
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"System monitoring error: {e}")
                
    async def _get_database_connections(self) -> int:
        """Get active database connections"""
        # Placeholder - implement based on your PostgreSQL setup
        # Example: Query pg_stat_activity
        return 0
        
    async def _get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate from Redis"""
        if not self.redis_client:
            return 0.0
            
        try:
            info = await self.redis_client.info()
            hits = info.get('keyspace_hits', 0)
            misses = info.get('keyspace_misses', 0)
            total = hits + misses
            return (hits / total * 100) if total > 0 else 0.0
        except Exception:
            return 0.0
            
    async def run_scenario(self, scenario: Dict[str, Any]) -> PerformanceMetrics:
        """Run a single test scenario"""
        logger.info(f"Running scenario: {scenario['name']}")
        
        start_time = time.time()
        scenario_start = datetime.now()
        
        # Initialize metrics collection
        response_times = []
        errors = []
        cpu_usage = []
        memory_usage = []
        
        # Create environment
        env = Environment(
            user_classes=scenario['user_classes'],
            host=self.base_url
        )
        
        # Setup event listeners
        @events.request.add_listener
        def on_request(request_type, name, response_time, response_length, exception, **kwargs):
            response_times.append(response_time)
            if exception:
                errors.append(exception)
                
            # Update Prometheus metrics
            status = "error" if exception else "success"
            request_count.labels(endpoint=name, method=request_type, status=status).inc()
            request_duration.labels(endpoint=name).observe(response_time / 1000.0)
            
        # Start load test
        env.create_local_runner()
        env.runner.start(
            user_count=scenario['users'],
            spawn_rate=scenario['spawn_rate']
        )
        
        # Monitor during test
        test_duration = scenario['duration']
        monitor_interval = min(5, test_duration / 10)
        
        for _ in range(int(test_duration / monitor_interval)):
            await asyncio.sleep(monitor_interval)
            
            # Collect system metrics
            cpu_usage.append(psutil.cpu_percent())
            memory_usage.append(psutil.virtual_memory().percent)
            active_users.set(env.runner.user_count)
            
        # Stop test
        env.runner.quit()
        
        # Calculate metrics
        duration = time.time() - start_time
        total_requests = len(response_times)
        failed_requests = len(errors)
        successful_requests = total_requests - failed_requests
        
        # Response time statistics
        if response_times:
            avg_response = statistics.mean(response_times)
            median_response = statistics.median(response_times)
            p95_response = np.percentile(response_times, 95)
            p99_response = np.percentile(response_times, 99)
            min_response = min(response_times)
            max_response = max(response_times)
        else:
            avg_response = median_response = p95_response = p99_response = 0
            min_response = max_response = 0
            
        # System resource averages
        avg_cpu = statistics.mean(cpu_usage) if cpu_usage else 0
        avg_memory = statistics.mean(memory_usage) if memory_usage else 0
        
        # Cache and AI metrics
        cache_hit_rate = await self._get_cache_hit_rate()
        
        metrics = PerformanceMetrics(
            timestamp=scenario_start.isoformat(),
            scenario=scenario['name'],
            duration_seconds=duration,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time_ms=avg_response,
            median_response_time_ms=median_response,
            p95_response_time_ms=p95_response,
            p99_response_time_ms=p99_response,
            min_response_time_ms=min_response,
            max_response_time_ms=max_response,
            requests_per_second=total_requests / duration if duration > 0 else 0,
            error_rate=(failed_requests / total_requests * 100) if total_requests > 0 else 0,
            cpu_usage_avg=avg_cpu,
            memory_usage_avg=avg_memory,
            database_pool_usage=0,  # Placeholder
            cache_hit_rate=cache_hit_rate,
            ai_api_calls=0,  # Placeholder
            concurrent_users=scenario['users']
        )
        
        self.metrics.append(metrics)
        return metrics
        
    def generate_report(self, output_dir: str = "tests/performance/reports"):
        """Generate comprehensive performance report"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = output_path / f"report_{timestamp}"
        report_dir.mkdir(exist_ok=True)
        
        # Save raw metrics
        with open(report_dir / "metrics.json", "w") as f:
            json.dump([asdict(m) for m in self.metrics], f, indent=2)
            
        # Generate visualizations
        self._generate_charts(report_dir)
        
        # Generate HTML report
        self._generate_html_report(report_dir)
        
        logger.info(f"Report generated at: {report_dir}")
        
    def _generate_charts(self, output_dir: Path):
        """Generate performance charts"""
        if not self.metrics:
            return
            
        # Convert metrics to DataFrame
        df = pd.DataFrame([asdict(m) for m in self.metrics])
        
        # Response time chart
        plt.figure(figsize=(12, 6))
        scenarios = df['scenario'].unique()
        x = np.arange(len(scenarios))
        width = 0.2
        
        plt.bar(x - width, df.groupby('scenario')['avg_response_time_ms'].mean(), width, label='Average')
        plt.bar(x, df.groupby('scenario')['p95_response_time_ms'].mean(), width, label='95th percentile')
        plt.bar(x + width, df.groupby('scenario')['p99_response_time_ms'].mean(), width, label='99th percentile')
        
        plt.xlabel('Scenario')
        plt.ylabel('Response Time (ms)')
        plt.title('Response Time by Scenario')
        plt.xticks(x, scenarios, rotation=45)
        plt.legend()
        plt.tight_layout()
        plt.savefig(output_dir / 'response_times.png')
        plt.close()
        
        # Throughput chart
        plt.figure(figsize=(10, 6))
        plt.bar(scenarios, df.groupby('scenario')['requests_per_second'].mean())
        plt.xlabel('Scenario')
        plt.ylabel('Requests per Second')
        plt.title('Throughput by Scenario')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(output_dir / 'throughput.png')
        plt.close()
        
        # Error rate chart
        plt.figure(figsize=(10, 6))
        plt.bar(scenarios, df.groupby('scenario')['error_rate'].mean(), color='red')
        plt.xlabel('Scenario')
        plt.ylabel('Error Rate (%)')
        plt.title('Error Rate by Scenario')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(output_dir / 'error_rates.png')
        plt.close()
        
        # System resources chart
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
        
        ax1.bar(scenarios, df.groupby('scenario')['cpu_usage_avg'].mean(), color='blue')
        ax1.set_ylabel('CPU Usage (%)')
        ax1.set_title('Average CPU Usage by Scenario')
        
        ax2.bar(scenarios, df.groupby('scenario')['memory_usage_avg'].mean(), color='green')
        ax2.set_xlabel('Scenario')
        ax2.set_ylabel('Memory Usage (%)')
        ax2.set_title('Average Memory Usage by Scenario')
        
        plt.tight_layout()
        plt.savefig(output_dir / 'system_resources.png')
        plt.close()
        
    def _generate_html_report(self, output_dir: Path):
        """Generate HTML performance report"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>AI Road Trip Storyteller - Performance Test Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                h2 {{ color: #666; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .metric {{ font-weight: bold; }}
                .good {{ color: green; }}
                .warning {{ color: orange; }}
                .bad {{ color: red; }}
                img {{ max-width: 100%; height: auto; margin: 10px 0; }}
                .summary {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <h1>AI Road Trip Storyteller - Performance Test Report</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <div class="summary">
                <h2>Executive Summary</h2>
                {self._generate_summary()}
            </div>
            
            <h2>Test Scenarios</h2>
            <table>
                <tr>
                    <th>Scenario</th>
                    <th>Duration (s)</th>
                    <th>Users</th>
                    <th>Total Requests</th>
                    <th>RPS</th>
                    <th>Avg Response (ms)</th>
                    <th>P95 Response (ms)</th>
                    <th>Error Rate (%)</th>
                    <th>Status</th>
                </tr>
                {self._generate_scenario_rows()}
            </table>
            
            <h2>Performance Charts</h2>
            <img src="response_times.png" alt="Response Times">
            <img src="throughput.png" alt="Throughput">
            <img src="error_rates.png" alt="Error Rates">
            <img src="system_resources.png" alt="System Resources">
            
            <h2>Detailed Metrics</h2>
            {self._generate_detailed_metrics()}
            
            <h2>Recommendations</h2>
            {self._generate_recommendations()}
        </body>
        </html>
        """
        
        with open(output_dir / 'report.html', 'w') as f:
            f.write(html_content)
            
    def _generate_summary(self) -> str:
        """Generate executive summary"""
        if not self.metrics:
            return "<p>No test data available</p>"
            
        total_requests = sum(m.total_requests for m in self.metrics)
        total_errors = sum(m.failed_requests for m in self.metrics)
        avg_response = statistics.mean(m.avg_response_time_ms for m in self.metrics)
        max_rps = max(m.requests_per_second for m in self.metrics)
        
        status = "PASS" if total_errors / total_requests < 0.01 and avg_response < 500 else "FAIL"
        status_class = "good" if status == "PASS" else "bad"
        
        return f"""
        <p><strong>Overall Status:</strong> <span class="{status_class}">{status}</span></p>
        <p><strong>Total Requests:</strong> {total_requests:,}</p>
        <p><strong>Total Errors:</strong> {total_errors:,} ({total_errors/total_requests*100:.2f}%)</p>
        <p><strong>Average Response Time:</strong> {avg_response:.2f}ms</p>
        <p><strong>Peak Throughput:</strong> {max_rps:.2f} requests/second</p>
        """
        
    def _generate_scenario_rows(self) -> str:
        """Generate scenario table rows"""
        rows = []
        for m in self.metrics:
            status = self._get_scenario_status(m)
            status_class = self._get_status_class(status)
            
            rows.append(f"""
            <tr>
                <td>{m.scenario}</td>
                <td>{m.duration_seconds:.1f}</td>
                <td>{m.concurrent_users}</td>
                <td>{m.total_requests:,}</td>
                <td>{m.requests_per_second:.2f}</td>
                <td>{m.avg_response_time_ms:.2f}</td>
                <td>{m.p95_response_time_ms:.2f}</td>
                <td>{m.error_rate:.2f}</td>
                <td class="{status_class}">{status}</td>
            </tr>
            """)
        return ''.join(rows)
        
    def _get_scenario_status(self, metrics: PerformanceMetrics) -> str:
        """Determine scenario status based on thresholds"""
        if metrics.error_rate > 5:
            return "FAIL"
        elif metrics.avg_response_time_ms > 1000:
            return "FAIL"
        elif metrics.error_rate > 1 or metrics.avg_response_time_ms > 500:
            return "WARNING"
        else:
            return "PASS"
            
    def _get_status_class(self, status: str) -> str:
        """Get CSS class for status"""
        return {
            "PASS": "good",
            "WARNING": "warning",
            "FAIL": "bad"
        }.get(status, "")
        
    def _generate_detailed_metrics(self) -> str:
        """Generate detailed metrics section"""
        sections = []
        
        for m in self.metrics:
            sections.append(f"""
            <h3>{m.scenario}</h3>
            <table>
                <tr><td>Response Time (min/avg/max)</td><td>{m.min_response_time_ms:.2f} / {m.avg_response_time_ms:.2f} / {m.max_response_time_ms:.2f} ms</td></tr>
                <tr><td>Response Time (median/p95/p99)</td><td>{m.median_response_time_ms:.2f} / {m.p95_response_time_ms:.2f} / {m.p99_response_time_ms:.2f} ms</td></tr>
                <tr><td>CPU Usage</td><td>{m.cpu_usage_avg:.1f}%</td></tr>
                <tr><td>Memory Usage</td><td>{m.memory_usage_avg:.1f}%</td></tr>
                <tr><td>Cache Hit Rate</td><td>{m.cache_hit_rate:.1f}%</td></tr>
            </table>
            """)
            
        return ''.join(sections)
        
    def _generate_recommendations(self) -> str:
        """Generate performance recommendations"""
        recommendations = []
        
        # Analyze metrics and generate recommendations
        for m in self.metrics:
            if m.error_rate > 1:
                recommendations.append(f"High error rate ({m.error_rate:.2f}%) in {m.scenario} - investigate error logs")
                
            if m.avg_response_time_ms > 500:
                recommendations.append(f"High response time ({m.avg_response_time_ms:.0f}ms) in {m.scenario} - consider optimization")
                
            if m.cpu_usage_avg > 80:
                recommendations.append(f"High CPU usage ({m.cpu_usage_avg:.0f}%) in {m.scenario} - consider scaling horizontally")
                
            if m.cache_hit_rate < 70:
                recommendations.append(f"Low cache hit rate ({m.cache_hit_rate:.0f}%) - review caching strategy")
                
        if not recommendations:
            recommendations.append("All performance metrics are within acceptable thresholds")
            
        return "<ul>" + "".join(f"<li>{r}</li>" for r in recommendations) + "</ul>"


# Test scenario definitions
LOAD_TEST_SCENARIOS = [
    {
        "name": "Baseline Load",
        "description": "Normal expected load",
        "users": 100,
        "spawn_rate": 10,
        "duration": 300,  # 5 minutes
        "user_classes": []  # Will be populated with actual user classes
    },
    {
        "name": "Peak Hours",
        "description": "Expected peak load during busy hours",
        "users": 500,
        "spawn_rate": 50,
        "duration": 600,  # 10 minutes
        "user_classes": []
    },
    {
        "name": "Stress Test",
        "description": "Beyond expected capacity",
        "users": 1000,
        "spawn_rate": 100,
        "duration": 900,  # 15 minutes
        "user_classes": []
    },
    {
        "name": "Spike Test",
        "description": "Sudden traffic spike",
        "users": 2000,
        "spawn_rate": 500,
        "duration": 120,  # 2 minutes
        "user_classes": []
    },
    {
        "name": "Soak Test",
        "description": "Extended duration test",
        "users": 200,
        "spawn_rate": 20,
        "duration": 3600,  # 1 hour
        "user_classes": []
    },
    {
        "name": "Breaking Point",
        "description": "Find system breaking point",
        "users": 5000,
        "spawn_rate": 200,
        "duration": 600,  # 10 minutes
        "user_classes": []
    }
]


async def main():
    """Main entry point for performance testing"""
    runner = PerformanceTestRunner()
    
    try:
        await runner.setup()
        
        # Run all scenarios
        for scenario in LOAD_TEST_SCENARIOS:
            metrics = await runner.run_scenario(scenario)
            logger.info(f"Completed {scenario['name']}: RPS={metrics.requests_per_second:.2f}, "
                       f"Avg Response={metrics.avg_response_time_ms:.2f}ms, "
                       f"Error Rate={metrics.error_rate:.2f}%")
            
            # Cool down between scenarios
            await asyncio.sleep(30)
            
        # Generate report
        runner.generate_report()
        
    finally:
        await runner.teardown()


if __name__ == "__main__":
    asyncio.run(main())