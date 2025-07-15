from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import statistics
from collections import deque
from prometheus_client import Counter, Histogram, Gauge

from app.core.logger import get_logger


logger = get_logger(__name__)

# Prometheus metrics definitions
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'path', 'status_code']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'path']
)

REQUEST_IN_PROGRESS = Gauge(
    'http_requests_in_progress',
    'Number of HTTP requests currently being processed'
)

EXCEPTION_COUNT = Counter(
    'http_exceptions_total',
    'Total number of exceptions raised during request processing',
    ['method', 'path', 'exception_type']
)

# AI-specific metrics
AI_REQUEST_COUNT = Counter(
    'ai_requests_total',
    'Total number of AI service requests',
    ['service', 'model', 'status']
)

AI_REQUEST_LATENCY = Histogram(
    'ai_request_duration_seconds',
    'AI service request latency in seconds',
    ['service', 'model']
)

# Cache metrics
CACHE_HIT_COUNT = Counter(
    'cache_hits_total',
    'Total number of cache hits',
    ['cache_type']
)

CACHE_MISS_COUNT = Counter(
    'cache_misses_total',
    'Total number of cache misses',
    ['cache_type']
)

# Database metrics
DB_QUERY_COUNT = Counter(
    'db_queries_total',
    'Total number of database queries',
    ['query_type', 'table']
)

DB_QUERY_LATENCY = Histogram(
    'db_query_duration_seconds',
    'Database query latency in seconds',
    ['query_type', 'table']
)

# Business metrics
BOOKING_COUNT = Counter(
    'bookings_total',
    'Total number of bookings',
    ['booking_type', 'status']
)

STORY_GENERATION_COUNT = Counter(
    'stories_generated_total',
    'Total number of stories generated',
    ['story_type', 'voice_personality']
)


@dataclass
class RequestMetrics:
    """Metrics for a single request."""
    timestamp: datetime
    endpoint: str
    status_code: int
    response_time: float
    cache_hit: bool
    client_id: Optional[str]
    error: Optional[str]


class MetricsCollector:
    """Collects and analyzes service metrics."""
    
    def __init__(self, window_size: int = 3600):  # 1 hour window
        self.window_size = window_size
        self.requests: deque[RequestMetrics] = deque(maxlen=window_size)
        self.errors: deque[RequestMetrics] = deque(maxlen=1000)
        self.last_cleanup = datetime.now()

    def record_request(
        self,
        endpoint: str,
        status_code: int,
        response_time: float,
        cache_hit: bool = False,
        client_id: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """Record metrics for a request."""
        try:
            metrics = RequestMetrics(
                timestamp=datetime.now(),
                endpoint=endpoint,
                status_code=status_code,
                response_time=response_time,
                cache_hit=cache_hit,
                client_id=client_id,
                error=error
            )
            
            self.requests.append(metrics)
            if error:
                self.errors.append(metrics)
                
            # Cleanup old data periodically
            if (datetime.now() - self.last_cleanup).seconds > 3600:
                self._cleanup_old_data()
                
        except Exception as e:
            logger.error(f"Error recording metrics: {str(e)}")

    def get_summary(
        self,
        minutes: int = 5,
        include_client_stats: bool = False
    ) -> Dict:
        """Get summary statistics for recent requests."""
        try:
            cutoff = datetime.now() - timedelta(minutes=minutes)
            recent_requests = [
                r for r in self.requests
                if r.timestamp > cutoff
            ]
            
            if not recent_requests:
                return self._empty_summary()
            
            response_times = [r.response_time for r in recent_requests]
            status_codes = [r.status_code for r in recent_requests]
            
            summary = {
                "request_count": len(recent_requests),
                "error_count": sum(1 for r in recent_requests if r.error),
                "cache_hit_rate": sum(
                    1 for r in recent_requests if r.cache_hit
                ) / len(recent_requests),
                "response_time": {
                    "avg": statistics.mean(response_times),
                    "p50": statistics.median(response_times),
                    "p95": self._percentile(response_times, 95),
                    "p99": self._percentile(response_times, 99)
                },
                "status_codes": {
                    str(code): status_codes.count(code)
                    for code in set(status_codes)
                }
            }
            
            if include_client_stats:
                summary["clients"] = self._get_client_stats(recent_requests)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating metrics summary: {str(e)}")
            return self._empty_summary()

    def get_error_summary(self, hours: int = 24) -> List[Dict]:
        """Get summary of recent errors."""
        try:
            cutoff = datetime.now() - timedelta(hours=hours)
            recent_errors = [
                e for e in self.errors
                if e.timestamp > cutoff
            ]
            
            error_summary = []
            for error in recent_errors:
                error_summary.append({
                    "timestamp": error.timestamp.isoformat(),
                    "endpoint": error.endpoint,
                    "status_code": error.status_code,
                    "error": error.error,
                    "client_id": error.client_id
                })
            
            return error_summary
            
        except Exception as e:
            logger.error(f"Error generating error summary: {str(e)}")
            return []

    def _cleanup_old_data(self) -> None:
        """Remove data older than the window size."""
        try:
            cutoff = datetime.now() - timedelta(seconds=self.window_size)
            
            while (
                self.requests and
                self.requests[0].timestamp < cutoff
            ):
                self.requests.popleft()
                
            while (
                self.errors and
                self.errors[0].timestamp < cutoff
            ):
                self.errors.popleft()
                
            self.last_cleanup = datetime.now()
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {str(e)}")

    def _get_client_stats(
        self,
        requests: List[RequestMetrics]
    ) -> Dict[str, Dict]:
        """Get per-client statistics."""
        try:
            client_stats = {}
            
            for request in requests:
                if not request.client_id:
                    continue
                    
                if request.client_id not in client_stats:
                    client_stats[request.client_id] = {
                        "request_count": 0,
                        "error_count": 0,
                        "cache_hits": 0,
                        "response_times": []
                    }
                    
                stats = client_stats[request.client_id]
                stats["request_count"] += 1
                if request.error:
                    stats["error_count"] += 1
                if request.cache_hit:
                    stats["cache_hits"] += 1
                stats["response_times"].append(request.response_time)
            
            # Calculate averages
            for client_id, stats in client_stats.items():
                response_times = stats.pop("response_times")
                stats["avg_response_time"] = (
                    statistics.mean(response_times)
                    if response_times else 0
                )
                stats["cache_hit_rate"] = (
                    stats["cache_hits"] / stats["request_count"]
                    if stats["request_count"] > 0 else 0
                )
            
            return client_stats
            
        except Exception as e:
            logger.error(f"Error calculating client stats: {str(e)}")
            return {}

    def _empty_summary(self) -> Dict:
        """Return empty metrics summary structure."""
        return {
            "request_count": 0,
            "error_count": 0,
            "cache_hit_rate": 0,
            "response_time": {
                "avg": 0,
                "p50": 0,
                "p95": 0,
                "p99": 0
            },
            "status_codes": {}
        }

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile value from a list of numbers."""
        try:
            size = len(data)
            if not size:
                return 0
                
            sorted_data = sorted(data)
            k = (size - 1) * percentile / 100
            f = int(k)
            
            if f == k:
                return sorted_data[f]
                
            c = k - f
            return sorted_data[f] * (1 - c) + sorted_data[f + 1] * c
            
        except Exception as e:
            logger.error(f"Error calculating percentile: {str(e)}")
            return 0


# Global metrics collector instance
metrics_collector = MetricsCollector() 