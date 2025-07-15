from typing import Dict, List, Any, Callable, Optional, TypeVar, cast
import time
import functools
import threading
from collections import defaultdict
from sqlalchemy.engine import Engine
from sqlalchemy import event
from sqlalchemy.orm import Session
from fastapi import Request, Depends

from app.core.logger import get_logger
from app.core.db_optimized import get_optimized_db

logger = get_logger(__name__)

T = TypeVar('T')

# Global variables for tracking
_query_stats = defaultdict(list)
_stats_lock = threading.Lock()
_max_tracked_queries = 1000  # Maximum number of queries to track
_slow_query_threshold = 0.1  # 100ms


class DBPerformanceMonitor:
    """
    Database performance monitoring system.
    Tracks query execution times and provides insights for optimization.
    """
    
    @staticmethod
    def track_query(
        query_text: str,
        parameters: Dict[str, Any],
        execution_time: float,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track a query's execution details.
        
        Args:
            query_text: The SQL query text
            parameters: The query parameters
            execution_time: Execution time in seconds
            context: Optional request context information
        """
        with _stats_lock:
            normalized_query = DBPerformanceMonitor._normalize_query(query_text)
            
            # Store query details
            _query_stats[normalized_query].append({
                "execution_time": execution_time,
                "timestamp": time.time(),
                "parameters": parameters,
                "context": context
            })
            
            # Limit size by removing oldest entry from the longest list if needed
            if sum(len(stats) for stats in _query_stats.values()) > _max_tracked_queries:
                longest_key = max(_query_stats.keys(), key=lambda k: len(_query_stats[k]))
                if _query_stats[longest_key]:
                    _query_stats[longest_key].pop(0)
    
    @staticmethod
    def _normalize_query(query_text: str) -> str:
        """
        Normalize a SQL query by replacing literals with placeholders.
        This helps group similar queries together.
        
        Args:
            query_text: The original SQL query
            
        Returns:
            Normalized SQL query
        """
        # Simple normalization - replace numeric literals with ?
        # This is a basic implementation - a production system would use a more robust parser
        import re
        normalized = re.sub(r'\b\d+\b', '?', query_text)
        normalized = re.sub(r"'[^']*'", '?', normalized)
        return normalized
    
    @staticmethod
    def get_slow_queries(threshold: float = _slow_query_threshold) -> List[Dict[str, Any]]:
        """
        Get a list of slow queries (queries that take longer than the threshold).
        
        Args:
            threshold: Time threshold in seconds
            
        Returns:
            List of slow query statistics
        """
        slow_queries = []
        
        with _stats_lock:
            for query, stats in _query_stats.items():
                # Calculate average execution time
                if not stats:
                    continue
                    
                avg_time = sum(stat["execution_time"] for stat in stats) / len(stats)
                max_time = max(stat["execution_time"] for stat in stats)
                
                if avg_time > threshold or max_time > threshold * 2:
                    slow_queries.append({
                        "query": query,
                        "avg_execution_time": avg_time,
                        "max_execution_time": max_time,
                        "call_count": len(stats),
                        "last_execution": stats[-1]["timestamp"] if stats else None,
                        "samples": stats[:5]  # Include a few sample executions
                    })
        
        # Sort by average execution time (slowest first)
        slow_queries.sort(key=lambda q: q["avg_execution_time"], reverse=True)
        return slow_queries
    
    @staticmethod
    def get_query_stats() -> Dict[str, Any]:
        """
        Get overall database query statistics.
        
        Returns:
            Dictionary with query statistics
        """
        with _stats_lock:
            # Calculate overall stats
            total_queries = sum(len(stats) for stats in _query_stats.values())
            total_time = sum(stat["execution_time"] for stats in _query_stats.values() for stat in stats)
            unique_queries = len(_query_stats)
            
            if total_queries == 0:
                avg_time = 0
            else:
                avg_time = total_time / total_queries
                
            # Get top queries by frequency
            query_counts = {query: len(stats) for query, stats in _query_stats.items()}
            top_by_frequency = sorted(query_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # Get top queries by average time
            query_avg_times = {}
            for query, stats in _query_stats.items():
                if stats:
                    query_avg_times[query] = sum(stat["execution_time"] for stat in stats) / len(stats)
            top_by_time = sorted(query_avg_times.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                "total_queries_tracked": total_queries,
                "unique_queries": unique_queries,
                "total_execution_time": total_time,
                "average_execution_time": avg_time,
                "top_queries_by_frequency": top_by_frequency,
                "top_queries_by_time": top_by_time
            }
    
    @staticmethod
    def clear_stats() -> None:
        """Clear all tracked statistics."""
        with _stats_lock:
            _query_stats.clear()
    
    @staticmethod
    def track_function_db_performance(func: Callable[..., T]) -> Callable[..., T]:
        """
        Decorator to track database performance of a function.
        
        Args:
            func: Function to decorate
            
        Returns:
            Decorated function
        """
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Get request object if available
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if request is None:
                request = kwargs.get('request')
                
            # Get context information
            context = {
                "function": func.__name__,
                "request_path": request.url.path if request else None,
                "request_method": request.method if request else None,
                "client_ip": request.client.host if request and request.client else None
            }
            
            # Execute the function
            result = await func(*args, **kwargs)
            
            # Track overall function execution time
            execution_time = time.time() - start_time
            
            # Log slow endpoint executions
            if execution_time > 0.5:  # 500ms threshold for endpoints
                logger.warning(
                    f"Slow endpoint detected: {func.__name__} took {execution_time:.4f}s"
                )
            
            return result
            
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Get context information (simplified for sync functions)
            context = {
                "function": func.__name__,
            }
            
            # Execute the function
            result = func(*args, **kwargs)
            
            # Track overall function execution time
            execution_time = time.time() - start_time
            
            # Log slow function executions
            if execution_time > 0.5:  # 500ms threshold
                logger.warning(
                    f"Slow function detected: {func.__name__} took {execution_time:.4f}s"
                )
            
            return result
        
        # Choose appropriate wrapper based on whether the function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper


# Initialize SQLAlchemy event listeners for query tracking
@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    execution_time = time.time() - context._query_start_time
    
    # Track all queries
    DBPerformanceMonitor.track_query(statement, parameters, execution_time)
    
    # Log slow queries
    if execution_time > _slow_query_threshold:
        logger.warning(
            f"Slow query detected ({execution_time:.4f}s): {statement[:300]}"
        )


# FastAPI dependency for injecting DB session with performance tracking
async def get_db_with_performance() -> Session:
    """
    FastAPI dependency that provides a database session with performance tracking.
    """
    db = next(get_optimized_db())
    
    try:
        yield db
    finally:
        db.close()