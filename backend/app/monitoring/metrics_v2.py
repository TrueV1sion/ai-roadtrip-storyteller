"""
Production Metrics System V2 - Six Sigma Implementation
Comprehensive Prometheus metrics with business KPIs
"""

import os
import time
from typing import Dict, Any, Optional, Callable
from functools import wraps
from contextlib import contextmanager

from prometheus_client import (
    Counter, Gauge, Histogram, Summary, Info,
    CollectorRegistry, multiprocess, generate_latest,
    CONTENT_TYPE_LATEST, REGISTRY
)
from prometheus_client.multiprocess import MultiProcessCollector

from app.core.logger import get_logger

logger = get_logger(__name__)


class MetricsSystem:
    """Production-grade metrics system with Prometheus integration."""
    
    def __init__(self):
        # Use multiprocess mode for Gunicorn workers
        self.multiprocess_mode = os.environ.get('PROMETHEUS_MULTIPROC_DIR')
        
        if self.multiprocess_mode:
            # Clean up any stale metrics
            multiprocess.mark_process_dead(os.getpid())
            # Use global registry for multiprocess
            self.registry = REGISTRY
        else:
            # Use custom registry for single process
            self.registry = CollectorRegistry()
        
        # Initialize all metrics
        self._init_http_metrics()
        self._init_business_metrics()
        self._init_system_metrics()
        self._init_ai_metrics()
        self._init_cache_metrics()
        self._init_security_metrics()
        
        logger.info("Production metrics system initialized")
    
    def _init_http_metrics(self):
        """Initialize HTTP-related metrics."""
        # Request metrics
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )
        
        self.http_request_duration_seconds = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry
        )
        
        self.http_request_size_bytes = Summary(
            'http_request_size_bytes',
            'HTTP request size in bytes',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        self.http_response_size_bytes = Summary(
            'http_response_size_bytes',
            'HTTP response size in bytes',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        # Active requests gauge
        self.http_requests_active = Gauge(
            'http_requests_active',
            'Active HTTP requests',
            ['method', 'endpoint'],
            registry=self.registry,
            multiprocess_mode='livesum'
        )
    
    def _init_business_metrics(self):
        """Initialize business-specific metrics."""
        # Story generation metrics
        self.stories_generated_total = Counter(
            'stories_generated_total',
            'Total stories generated',
            ['story_type', 'voice_personality'],
            registry=self.registry
        )
        
        self.story_generation_duration_seconds = Histogram(
            'story_generation_duration_seconds',
            'Story generation duration in seconds',
            ['story_type'],
            buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
            registry=self.registry
        )
        
        # Revenue metrics
        self.bookings_total = Counter(
            'bookings_total',
            'Total bookings made',
            ['booking_type', 'partner'],
            registry=self.registry
        )
        
        self.booking_revenue_usd = Counter(
            'booking_revenue_usd',
            'Total booking revenue in USD',
            ['booking_type', 'partner'],
            registry=self.registry
        )
        
        # User engagement metrics
        self.active_users = Gauge(
            'active_users',
            'Currently active users',
            ['user_type'],
            registry=self.registry,
            multiprocess_mode='livesum'
        )
        
        self.user_sessions_total = Counter(
            'user_sessions_total',
            'Total user sessions',
            ['platform', 'session_type'],
            registry=self.registry
        )
        
        self.trip_duration_minutes = Histogram(
            'trip_duration_minutes',
            'Trip duration in minutes',
            ['trip_type'],
            buckets=(15, 30, 60, 120, 240, 480, 960),
            registry=self.registry
        )
    
    def _init_system_metrics(self):
        """Initialize system-level metrics."""
        # Database metrics
        self.db_connections_active = Gauge(
            'db_connections_active',
            'Active database connections',
            ['pool_name'],
            registry=self.registry,
            multiprocess_mode='livesum'
        )
        
        self.db_query_duration_seconds = Histogram(
            'db_query_duration_seconds',
            'Database query duration in seconds',
            ['query_type', 'table'],
            buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
            registry=self.registry
        )
        
        # Background job metrics
        self.celery_tasks_total = Counter(
            'celery_tasks_total',
            'Total Celery tasks',
            ['task_name', 'status'],
            registry=self.registry
        )
        
        self.celery_task_duration_seconds = Histogram(
            'celery_task_duration_seconds',
            'Celery task duration in seconds',
            ['task_name'],
            buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0),
            registry=self.registry
        )
        
        # Worker metrics
        self.worker_info = Info(
            'worker_info',
            'Worker information',
            registry=self.registry
        )
        self.worker_info.info({
            'pid': str(os.getpid()),
            'python_version': os.environ.get('PYTHON_VERSION', 'unknown')
        })
    
    def _init_ai_metrics(self):
        """Initialize AI service metrics."""
        # AI API calls
        self.ai_api_calls_total = Counter(
            'ai_api_calls_total',
            'Total AI API calls',
            ['service', 'operation', 'status'],
            registry=self.registry
        )
        
        self.ai_api_latency_seconds = Histogram(
            'ai_api_latency_seconds',
            'AI API call latency in seconds',
            ['service', 'operation'],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
            registry=self.registry
        )
        
        self.ai_tokens_used_total = Counter(
            'ai_tokens_used_total',
            'Total AI tokens consumed',
            ['service', 'model'],
            registry=self.registry
        )
        
        self.ai_cost_usd = Counter(
            'ai_cost_usd',
            'AI service cost in USD',
            ['service', 'model'],
            registry=self.registry
        )
        
        # Voice service metrics
        self.voice_synthesis_total = Counter(
            'voice_synthesis_total',
            'Total voice synthesis operations',
            ['voice_id', 'language'],
            registry=self.registry
        )
        
        self.voice_recognition_total = Counter(
            'voice_recognition_total',
            'Total voice recognition operations',
            ['language', 'status'],
            registry=self.registry
        )
    
    def _init_cache_metrics(self):
        """Initialize cache metrics."""
        self.cache_operations_total = Counter(
            'cache_operations_total',
            'Total cache operations',
            ['operation', 'cache_tier', 'status'],
            registry=self.registry
        )
        
        self.cache_hit_rate = Gauge(
            'cache_hit_rate',
            'Cache hit rate',
            ['cache_tier'],
            registry=self.registry
        )
        
        self.cache_memory_bytes = Gauge(
            'cache_memory_bytes',
            'Cache memory usage in bytes',
            ['cache_tier'],
            registry=self.registry
        )
        
        self.cache_evictions_total = Counter(
            'cache_evictions_total',
            'Total cache evictions',
            ['cache_tier', 'reason'],
            registry=self.registry
        )
    
    def _init_security_metrics(self):
        """Initialize security-related metrics."""
        self.security_events_total = Counter(
            'security_events_total',
            'Total security events',
            ['event_type', 'severity', 'action'],
            registry=self.registry
        )
        
        self.rate_limit_exceeded_total = Counter(
            'rate_limit_exceeded_total',
            'Total rate limit exceeded events',
            ['endpoint', 'user_type'],
            registry=self.registry
        )
        
        self.authentication_attempts_total = Counter(
            'authentication_attempts_total',
            'Total authentication attempts',
            ['method', 'status'],
            registry=self.registry
        )
        
        self.csrf_violations_total = Counter(
            'csrf_violations_total',
            'Total CSRF violations',
            ['endpoint'],
            registry=self.registry
        )
    
    # Decorator for timing functions
    def time_function(self, metric_name: str, labels: Dict[str, str] = None):
        """Decorator to time function execution."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    if hasattr(self, metric_name):
                        metric = getattr(self, metric_name)
                        if labels:
                            metric.labels(**labels).observe(duration)
                        else:
                            metric.observe(duration)
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    if hasattr(self, metric_name):
                        metric = getattr(self, metric_name)
                        if labels:
                            metric.labels(**labels).observe(duration)
                        else:
                            metric.observe(duration)
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator
    
    @contextmanager
    def time_block(self, metric_name: str, labels: Dict[str, str] = None):
        """Context manager for timing code blocks."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            if hasattr(self, metric_name):
                metric = getattr(self, metric_name)
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)
    
    def track_request(self, method: str, endpoint: str, status: int):
        """Track HTTP request metrics."""
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=str(status)
        ).inc()
    
    def track_active_request(self, method: str, endpoint: str, delta: int):
        """Track active requests."""
        self.http_requests_active.labels(
            method=method,
            endpoint=endpoint
        ).inc(delta)
    
    def track_story_generation(self, story_type: str, voice_personality: str, duration: float):
        """Track story generation metrics."""
        self.stories_generated_total.labels(
            story_type=story_type,
            voice_personality=voice_personality
        ).inc()
        
        self.story_generation_duration_seconds.labels(
            story_type=story_type
        ).observe(duration)
    
    def track_booking(self, booking_type: str, partner: str, revenue: float):
        """Track booking metrics."""
        self.bookings_total.labels(
            booking_type=booking_type,
            partner=partner
        ).inc()
        
        self.booking_revenue_usd.labels(
            booking_type=booking_type,
            partner=partner
        ).inc(revenue)
    
    def track_ai_usage(self, service: str, operation: str, tokens: int, cost: float, latency: float, status: str = "success"):
        """Track AI service usage."""
        self.ai_api_calls_total.labels(
            service=service,
            operation=operation,
            status=status
        ).inc()
        
        self.ai_api_latency_seconds.labels(
            service=service,
            operation=operation
        ).observe(latency)
        
        if tokens > 0:
            self.ai_tokens_used_total.labels(
                service=service,
                model="default"
            ).inc(tokens)
        
        if cost > 0:
            self.ai_cost_usd.labels(
                service=service,
                model="default"
            ).inc(cost)
    
    def track_cache_operation(self, operation: str, cache_tier: str, hit: bool):
        """Track cache operations."""
        status = "hit" if hit else "miss"
        self.cache_operations_total.labels(
            operation=operation,
            cache_tier=cache_tier,
            status=status
        ).inc()
    
    def track_security_event(self, event_type: str, severity: str, action: str):
        """Track security events."""
        self.security_events_total.labels(
            event_type=event_type,
            severity=severity,
            action=action
        ).inc()
    
    def generate_metrics(self) -> bytes:
        """Generate metrics for Prometheus scraping."""
        if self.multiprocess_mode:
            # Collect from all processes
            registry = CollectorRegistry()
            MultiProcessCollector(registry)
            return generate_latest(registry)
        else:
            return generate_latest(self.registry)
    
    def get_content_type(self) -> str:
        """Get Prometheus content type."""
        return CONTENT_TYPE_LATEST


# Global metrics instance
metrics_v2 = MetricsSystem()


# Convenience functions for backward compatibility
def track_request(method: str, endpoint: str, status: int):
    """Track HTTP request."""
    metrics_v2.track_request(method, endpoint, status)


def track_story_generation(story_type: str, voice_personality: str, duration: float):
    """Track story generation."""
    metrics_v2.track_story_generation(story_type, voice_personality, duration)


def track_booking(booking_type: str, partner: str, revenue: float):
    """Track booking."""
    metrics_v2.track_booking(booking_type, partner, revenue)


def track_ai_usage(service: str, operation: str, tokens: int = 0, cost: float = 0, latency: float = 0, status: str = "success"):
    """Track AI service usage."""
    metrics_v2.track_ai_usage(service, operation, tokens, cost, latency, status)


import asyncio