#!/usr/bin/env python3
"""
Metrics aggregation and analysis script for AI Road Trip Storyteller.
Collects metrics from Prometheus and generates reports.
"""

import asyncio
import aiohttp
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
import os
from dataclasses import dataclass
import matplotlib.pyplot as plt
import seaborn as sns
from jinja2 import Template


@dataclass
class MetricQuery:
    name: str
    query: str
    description: str
    unit: str = ""
    aggregation: str = "avg"


class MetricsAggregator:
    def __init__(self, prometheus_url: str, config: Dict[str, Any]):
        self.prometheus_url = prometheus_url.rstrip("/")
        self.config = config
        self.logger = self._setup_logging()
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Define standard queries
        self.queries = self._define_queries()
        
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        logger = logging.getLogger("metrics_aggregator")
        logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _define_queries(self) -> List[MetricQuery]:
        """Define standard metric queries."""
        return [
            # Request metrics
            MetricQuery(
                name="request_rate",
                query='sum(rate(http_requests_total[5m]))',
                description="Request rate per second",
                unit="req/s"
            ),
            MetricQuery(
                name="error_rate",
                query='sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))',
                description="Error rate percentage",
                unit="%",
                aggregation="avg"
            ),
            MetricQuery(
                name="p95_latency",
                query='histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le)) * 1000',
                description="95th percentile latency",
                unit="ms"
            ),
            MetricQuery(
                name="p99_latency",
                query='histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le)) * 1000',
                description="99th percentile latency",
                unit="ms"
            ),
            
            # Database metrics
            MetricQuery(
                name="db_connections",
                query='database_pool_connections_used',
                description="Active database connections",
                unit="connections"
            ),
            MetricQuery(
                name="db_pool_usage",
                query='(database_pool_connections_used / database_pool_connections_max) * 100',
                description="Database pool usage",
                unit="%"
            ),
            
            # Redis metrics
            MetricQuery(
                name="cache_hit_rate",
                query='sum(rate(cache_hits_total[5m])) / sum(rate(cache_requests_total[5m])) * 100',
                description="Cache hit rate",
                unit="%"
            ),
            MetricQuery(
                name="redis_memory_usage",
                query='(redis_memory_used_bytes / redis_memory_max_bytes) * 100',
                description="Redis memory usage",
                unit="%"
            ),
            
            # AI service metrics
            MetricQuery(
                name="ai_request_rate",
                query='sum(rate(ai_requests_total[5m]))',
                description="AI requests per second",
                unit="req/s"
            ),
            MetricQuery(
                name="ai_error_rate",
                query='sum(rate(ai_requests_total{status="error"}[5m])) / sum(rate(ai_requests_total[5m])) * 100',
                description="AI service error rate",
                unit="%"
            ),
            
            # Business metrics
            MetricQuery(
                name="user_registrations",
                query='sum(increase(user_registrations_total[1h]))',
                description="New user registrations per hour",
                unit="users/hour"
            ),
            MetricQuery(
                name="stories_generated",
                query='sum(increase(story_generated_total[1h]))',
                description="Stories generated per hour",
                unit="stories/hour"
            ),
            MetricQuery(
                name="booking_revenue",
                query='sum(increase(booking_revenue_total[1h]))',
                description="Booking revenue per hour",
                unit="$/hour"
            ),
            
            # Infrastructure metrics
            MetricQuery(
                name="cpu_usage",
                query='avg(100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100))',
                description="Average CPU usage",
                unit="%"
            ),
            MetricQuery(
                name="memory_usage",
                query='avg(100 - ((node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100))',
                description="Average memory usage",
                unit="%"
            )
        ]
    
    async def start(self):
        """Start the metrics aggregation process."""
        self.session = aiohttp.ClientSession()
        self.logger.info("Starting metrics aggregation")
        
        try:
            # Run aggregation based on config
            if self.config.get("mode") == "continuous":
                await self._run_continuous()
            else:
                await self._run_once()
                
        except Exception as e:
            self.logger.error(f"Aggregation error: {e}")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up resources."""
        if self.session:
            await self.session.close()
    
    async def _run_once(self):
        """Run aggregation once and generate report."""
        # Collect metrics for different time ranges
        time_ranges = {
            "1h": "Last Hour",
            "24h": "Last 24 Hours",
            "7d": "Last 7 Days"
        }
        
        all_metrics = {}
        
        for range_key, range_name in time_ranges.items():
            self.logger.info(f"Collecting metrics for {range_name}")
            metrics = await self._collect_metrics(range_key)
            all_metrics[range_key] = metrics
        
        # Generate report
        report = await self._generate_report(all_metrics)
        
        # Save report
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        report_file = f"metrics_report_{timestamp}.html"
        
        with open(report_file, 'w') as f:
            f.write(report)
        
        self.logger.info(f"Report saved to {report_file}")
        
        # Generate visualizations if enabled
        if self.config.get("generate_charts", True):
            await self._generate_charts(all_metrics, timestamp)
    
    async def _run_continuous(self):
        """Run continuous metrics collection."""
        interval = self.config.get("interval", 300)  # 5 minutes default
        
        while True:
            try:
                metrics = await self._collect_metrics("5m")
                await self._process_metrics(metrics)
                
                # Check for anomalies
                anomalies = await self._detect_anomalies(metrics)
                if anomalies:
                    self.logger.warning(f"Anomalies detected: {anomalies}")
                
            except Exception as e:
                self.logger.error(f"Collection error: {e}")
            
            await asyncio.sleep(interval)
    
    async def _collect_metrics(self, time_range: str) -> Dict[str, Any]:
        """Collect metrics for a specific time range."""
        metrics = {}
        
        for query in self.queries:
            try:
                # Modify query for time range
                query_str = query.query.replace("[5m]", f"[{time_range}]")
                
                # Execute query
                result = await self._query_prometheus(query_str)
                
                if result:
                    metrics[query.name] = {
                        "value": result,
                        "description": query.description,
                        "unit": query.unit
                    }
                    
            except Exception as e:
                self.logger.error(f"Failed to collect {query.name}: {e}")
        
        return metrics
    
    async def _query_prometheus(self, query: str) -> Optional[float]:
        """Execute a Prometheus query."""
        url = f"{self.prometheus_url}/api/v1/query"
        params = {"query": query}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data["status"] == "success":
                        result = data["data"]["result"]
                        
                        if result and len(result) > 0:
                            # Get the first result value
                            value = float(result[0]["value"][1])
                            return value
                            
        except Exception as e:
            self.logger.error(f"Prometheus query failed: {e}")
        
        return None
    
    async def _query_prometheus_range(self, query: str, start: datetime, end: datetime, step: str = "5m") -> pd.DataFrame:
        """Execute a Prometheus range query."""
        url = f"{self.prometheus_url}/api/v1/query_range"
        params = {
            "query": query,
            "start": int(start.timestamp()),
            "end": int(end.timestamp()),
            "step": step
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data["status"] == "success":
                        result = data["data"]["result"]
                        
                        if result and len(result) > 0:
                            # Convert to dataframe
                            values = result[0]["values"]
                            df = pd.DataFrame(values, columns=["timestamp", "value"])
                            df["timestamp"] = pd.to_datetime(df["timestamp"], unit='s')
                            df["value"] = df["value"].astype(float)
                            return df
                            
        except Exception as e:
            self.logger.error(f"Prometheus range query failed: {e}")
        
        return pd.DataFrame()
    
    async def _detect_anomalies(self, metrics: Dict[str, Any]) -> List[str]:
        """Detect anomalies in metrics."""
        anomalies = []
        
        # Check error rate
        error_rate = metrics.get("error_rate", {}).get("value", 0)
        if error_rate > 5:  # 5% threshold
            anomalies.append(f"High error rate: {error_rate:.1f}%")
        
        # Check latency
        p95_latency = metrics.get("p95_latency", {}).get("value", 0)
        if p95_latency > 2000:  # 2 seconds
            anomalies.append(f"High P95 latency: {p95_latency:.0f}ms")
        
        # Check cache hit rate
        cache_hit_rate = metrics.get("cache_hit_rate", {}).get("value", 100)
        if cache_hit_rate < 70:  # 70% threshold
            anomalies.append(f"Low cache hit rate: {cache_hit_rate:.1f}%")
        
        # Check resource usage
        cpu_usage = metrics.get("cpu_usage", {}).get("value", 0)
        if cpu_usage > 80:
            anomalies.append(f"High CPU usage: {cpu_usage:.1f}%")
        
        memory_usage = metrics.get("memory_usage", {}).get("value", 0)
        if memory_usage > 85:
            anomalies.append(f"High memory usage: {memory_usage:.1f}%")
        
        return anomalies
    
    async def _generate_report(self, all_metrics: Dict[str, Dict[str, Any]]) -> str:
        """Generate HTML report from metrics."""
        template = Template("""
<!DOCTYPE html>
<html>
<head>
    <title>AI Road Trip Storyteller - Metrics Report</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .header {
            background-color: #2c3e50;
            color: white;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .section {
            background-color: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .metric {
            display: inline-block;
            margin: 10px;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 5px;
            min-width: 200px;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
        }
        .metric-name {
            font-size: 14px;
            color: #7f8c8d;
            margin-top: 5px;
        }
        .alert {
            background-color: #e74c3c;
            color: white;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
        .warning {
            background-color: #f39c12;
            color: white;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        th, td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #2c3e50;
            color: white;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>AI Road Trip Storyteller - Metrics Report</h1>
        <p>Generated: {{ timestamp }}</p>
    </div>
    
    {% for time_range, metrics in all_metrics.items() %}
    <div class="section">
        <h2>{{ time_ranges[time_range] }}</h2>
        
        <h3>Application Performance</h3>
        <div>
            {% for key in ['request_rate', 'error_rate', 'p95_latency', 'p99_latency'] %}
            {% if key in metrics %}
            <div class="metric">
                <div class="metric-value">
                    {{ "%.2f"|format(metrics[key].value) }}{{ metrics[key].unit }}
                </div>
                <div class="metric-name">{{ metrics[key].description }}</div>
            </div>
            {% endif %}
            {% endfor %}
        </div>
        
        <h3>Database & Cache</h3>
        <div>
            {% for key in ['db_pool_usage', 'cache_hit_rate', 'redis_memory_usage'] %}
            {% if key in metrics %}
            <div class="metric">
                <div class="metric-value">
                    {{ "%.1f"|format(metrics[key].value) }}{{ metrics[key].unit }}
                </div>
                <div class="metric-name">{{ metrics[key].description }}</div>
            </div>
            {% endif %}
            {% endfor %}
        </div>
        
        <h3>Business Metrics</h3>
        <div>
            {% for key in ['user_registrations', 'stories_generated', 'booking_revenue'] %}
            {% if key in metrics %}
            <div class="metric">
                <div class="metric-value">
                    {{ "%.0f"|format(metrics[key].value) }}
                </div>
                <div class="metric-name">{{ metrics[key].description }}</div>
            </div>
            {% endif %}
            {% endfor %}
        </div>
        
        <h3>Infrastructure</h3>
        <div>
            {% for key in ['cpu_usage', 'memory_usage'] %}
            {% if key in metrics %}
            <div class="metric">
                <div class="metric-value">
                    {{ "%.1f"|format(metrics[key].value) }}{{ metrics[key].unit }}
                </div>
                <div class="metric-name">{{ metrics[key].description }}</div>
            </div>
            {% endif %}
            {% endfor %}
        </div>
    </div>
    {% endfor %}
    
    <div class="section">
        <h2>Alerts & Warnings</h2>
        {% if anomalies %}
            {% for anomaly in anomalies %}
            <div class="alert">{{ anomaly }}</div>
            {% endfor %}
        {% else %}
            <p>No anomalies detected</p>
        {% endif %}
    </div>
</body>
</html>
        """)
        
        # Detect anomalies for the most recent metrics
        anomalies = await self._detect_anomalies(all_metrics.get("1h", {}))
        
        return template.render(
            all_metrics=all_metrics,
            timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            time_ranges={"1h": "Last Hour", "24h": "Last 24 Hours", "7d": "Last 7 Days"},
            anomalies=anomalies
        )
    
    async def _generate_charts(self, all_metrics: Dict[str, Dict[str, Any]], timestamp: str):
        """Generate visualization charts."""
        self.logger.info("Generating charts...")
        
        # Set up plot style
        plt.style.use('seaborn-v0_8')
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('AI Road Trip Storyteller - Metrics Overview', fontsize=16)
        
        # Get historical data for charts
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)
        
        # Chart 1: Request rate over time
        ax = axes[0, 0]
        query = 'sum(rate(http_requests_total[5m]))'
        df = await self._query_prometheus_range(query, start_time, end_time)
        if not df.empty:
            ax.plot(df['timestamp'], df['value'])
            ax.set_title('Request Rate (24h)')
            ax.set_ylabel('Requests/sec')
            ax.set_xlabel('Time')
        
        # Chart 2: Error rate over time
        ax = axes[0, 1]
        query = 'sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100'
        df = await self._query_prometheus_range(query, start_time, end_time)
        if not df.empty:
            ax.plot(df['timestamp'], df['value'], color='red')
            ax.set_title('Error Rate (24h)')
            ax.set_ylabel('Error %')
            ax.set_xlabel('Time')
            ax.axhline(y=5, color='orange', linestyle='--', label='5% threshold')
        
        # Chart 3: Response time percentiles
        ax = axes[1, 0]
        p50_query = 'histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket[5m])) by (le)) * 1000'
        p95_query = 'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le)) * 1000'
        p99_query = 'histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le)) * 1000'
        
        for query, label, color in [(p50_query, 'P50', 'green'), 
                                    (p95_query, 'P95', 'orange'), 
                                    (p99_query, 'P99', 'red')]:
            df = await self._query_prometheus_range(query, start_time, end_time)
            if not df.empty:
                ax.plot(df['timestamp'], df['value'], label=label, color=color)
        
        ax.set_title('Response Time Percentiles (24h)')
        ax.set_ylabel('Latency (ms)')
        ax.set_xlabel('Time')
        ax.legend()
        
        # Chart 4: Resource usage
        ax = axes[1, 1]
        cpu_query = 'avg(100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100))'
        mem_query = 'avg(100 - ((node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100))'
        
        cpu_df = await self._query_prometheus_range(cpu_query, start_time, end_time)
        mem_df = await self._query_prometheus_range(mem_query, start_time, end_time)
        
        if not cpu_df.empty:
            ax.plot(cpu_df['timestamp'], cpu_df['value'], label='CPU %', color='blue')
        if not mem_df.empty:
            ax.plot(mem_df['timestamp'], mem_df['value'], label='Memory %', color='green')
        
        ax.set_title('Resource Usage (24h)')
        ax.set_ylabel('Usage %')
        ax.set_xlabel('Time')
        ax.legend()
        ax.set_ylim(0, 100)
        
        plt.tight_layout()
        
        # Save chart
        chart_file = f"metrics_chart_{timestamp}.png"
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        self.logger.info(f"Charts saved to {chart_file}")
    
    async def _process_metrics(self, metrics: Dict[str, Any]):
        """Process metrics for continuous mode."""
        # Store in time series database or file
        timestamp = datetime.utcnow()
        
        # Create metrics line for storage
        metrics_line = {
            "timestamp": timestamp.isoformat(),
            "metrics": {
                name: data["value"] 
                for name, data in metrics.items() 
                if data.get("value") is not None
            }
        }
        
        # Append to metrics file
        metrics_file = self.config.get("metrics_file", "metrics.jsonl")
        with open(metrics_file, 'a') as f:
            f.write(json.dumps(metrics_line) + '\n')


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Metrics Aggregator for Road Trip AI")
    parser.add_argument("prometheus_url", help="Prometheus server URL")
    parser.add_argument("-m", "--mode", choices=["once", "continuous"], 
                       default="once", help="Aggregation mode")
    parser.add_argument("-i", "--interval", type=int, default=300,
                       help="Collection interval in seconds (continuous mode)")
    parser.add_argument("-c", "--charts", action="store_true",
                       help="Generate visualization charts")
    
    args = parser.parse_args()
    
    config = {
        "mode": args.mode,
        "interval": args.interval,
        "generate_charts": args.charts
    }
    
    aggregator = MetricsAggregator(args.prometheus_url, config)
    asyncio.run(aggregator.start())


if __name__ == "__main__":
    main()