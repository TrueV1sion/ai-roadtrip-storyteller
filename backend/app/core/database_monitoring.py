"""
Database Performance Monitoring Module

Provides real-time monitoring of database performance metrics including:
- Connection pool usage
- Query performance
- Index effectiveness
- Table statistics
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict

from sqlalchemy import text
from sqlalchemy.pool import Pool
from sqlalchemy.engine import Engine

from app.core.logger import get_logger
from app.core.cache import cache_manager

logger = get_logger(__name__)


class DatabasePerformanceMonitor:
    """Monitor and report database performance metrics."""
    
    def __init__(self):
        self.metrics_history = defaultdict(list)
        self.alert_thresholds = {
            'connection_pool_usage': 80,  # percentage
            'slow_query_ms': 50,  # milliseconds
            'deadlock_count': 1,  # number of deadlocks
            'failed_connection_rate': 5,  # percentage
        }
        
    async def collect_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive database metrics."""
        from app.core.database_manager import db_manager
        
        metrics = {
            'timestamp': datetime.utcnow().isoformat(),
            'connection_pool': await self._get_connection_pool_metrics(),
            'query_performance': await self._get_query_performance_metrics(),
            'index_usage': await self._get_index_usage_metrics(),
            'table_health': await self._get_table_health_metrics(),
            'database_activity': await self._get_database_activity_metrics(),
            'alerts': []
        }
        
        # Check for alerts
        alerts = self._check_alert_conditions(metrics)
        metrics['alerts'] = alerts
        
        # Store metrics history
        self._store_metrics_history(metrics)
        
        # Cache metrics for dashboard
        await cache_manager.setex('db_metrics:latest', 300, metrics)
        
        return metrics
        
    async def _get_connection_pool_metrics(self) -> Dict[str, Any]:
        """Get detailed connection pool metrics."""
        from app.core.database_manager import db_manager
        
        if not db_manager.sync_engine:
            return {}
            
        pool = db_manager.sync_engine.pool
        
        # Calculate usage percentage
        total_possible = pool.size() + pool._max_overflow
        current_usage = pool.checkedout() + pool.overflow()
        usage_percentage = (current_usage / total_possible * 100) if total_possible > 0 else 0
        
        metrics = {
            'pool_size': pool.size(),
            'max_overflow': pool._max_overflow,
            'checked_in': pool.checkedin(),
            'checked_out': pool.checkedout(),
            'overflow': pool.overflow(),
            'total_connections': current_usage,
            'usage_percentage': round(usage_percentage, 2),
            'connection_timeout': getattr(pool, '_timeout', 30),
            'recycle_time': getattr(pool, '_recycle', 1800),
        }
        
        # Get connection wait times if available
        if hasattr(pool, '_pool'):
            wait_times = []
            for conn in pool._pool:
                if hasattr(conn, 'info'):
                    wait_time = conn.info.get('wait_time', 0)
                    if wait_time:
                        wait_times.append(wait_time)
                        
            if wait_times:
                metrics['avg_wait_time_ms'] = round(sum(wait_times) / len(wait_times) * 1000, 2)
                metrics['max_wait_time_ms'] = round(max(wait_times) * 1000, 2)
                
        return metrics
        
    async def _get_query_performance_metrics(self) -> Dict[str, Any]:
        """Get query performance metrics from pg_stat_statements."""
        from app.core.database_manager import db_manager
        
        metrics = {
            'slow_queries': [],
            'most_frequent': [],
            'most_time_consuming': [],
            'total_queries': 0,
            'avg_execution_time_ms': 0
        }
        
        try:
            with db_manager.sync_engine.connect() as conn:
                # Get slow queries
                slow_queries = conn.execute(text("""
                    SELECT 
                        query,
                        calls,
                        mean_exec_time,
                        max_exec_time,
                        total_exec_time,
                        rows,
                        100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
                    FROM pg_stat_statements
                    WHERE mean_exec_time > 50
                    ORDER BY mean_exec_time DESC
                    LIMIT 10
                """)).fetchall()
                
                metrics['slow_queries'] = [
                    {
                        'query': row[0][:100],
                        'calls': row[1],
                        'avg_time_ms': round(row[2], 2),
                        'max_time_ms': round(row[3], 2),
                        'total_time_ms': round(row[4], 2),
                        'rows_returned': row[5],
                        'cache_hit_rate': round(row[6] or 0, 2)
                    }
                    for row in slow_queries
                ]
                
                # Get overall statistics
                overall = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total_queries,
                        AVG(mean_exec_time) as avg_time,
                        SUM(calls) as total_calls
                    FROM pg_stat_statements
                """)).fetchone()
                
                if overall:
                    metrics['total_queries'] = overall[0]
                    metrics['avg_execution_time_ms'] = round(overall[1] or 0, 2)
                    metrics['total_calls'] = overall[2]
                    
        except Exception as e:
            logger.warning(f"Could not get query performance metrics: {e}")
            
        return metrics
        
    async def _get_index_usage_metrics(self) -> Dict[str, Any]:
        """Get index usage and effectiveness metrics."""
        from app.core.database_manager import db_manager
        
        metrics = {
            'unused_indexes': [],
            'missing_indexes': [],
            'index_hit_rate': 0,
            'most_used_indexes': []
        }
        
        try:
            with db_manager.sync_engine.connect() as conn:
                # Find unused indexes
                unused = conn.execute(text("""
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        idx_scan,
                        pg_size_pretty(pg_relation_size(indexrelid)) as size
                    FROM pg_stat_user_indexes
                    WHERE idx_scan = 0
                    AND indexrelname NOT LIKE 'pg_toast%'
                    ORDER BY pg_relation_size(indexrelid) DESC
                    LIMIT 10
                """)).fetchall()
                
                metrics['unused_indexes'] = [
                    {
                        'table': row[1],
                        'index': row[2],
                        'scans': row[3],
                        'size': row[4]
                    }
                    for row in unused
                ]
                
                # Get index hit rate
                hit_rate = conn.execute(text("""
                    SELECT 
                        100.0 * sum(idx_blks_hit) / nullif(sum(idx_blks_hit + idx_blks_read), 0) as hit_rate
                    FROM pg_statio_user_indexes
                """)).fetchone()
                
                if hit_rate and hit_rate[0]:
                    metrics['index_hit_rate'] = round(hit_rate[0], 2)
                    
                # Get most used indexes
                most_used = conn.execute(text("""
                    SELECT 
                        tablename,
                        indexname,
                        idx_scan,
                        idx_tup_read,
                        idx_tup_fetch
                    FROM pg_stat_user_indexes
                    WHERE idx_scan > 0
                    ORDER BY idx_scan DESC
                    LIMIT 10
                """)).fetchall()
                
                metrics['most_used_indexes'] = [
                    {
                        'table': row[0],
                        'index': row[1],
                        'scans': row[2],
                        'tuples_read': row[3],
                        'tuples_fetched': row[4]
                    }
                    for row in most_used
                ]
                
        except Exception as e:
            logger.warning(f"Could not get index usage metrics: {e}")
            
        return metrics
        
    async def _get_table_health_metrics(self) -> Dict[str, Any]:
        """Get table health metrics including bloat and vacuum status."""
        from app.core.database_manager import db_manager
        
        metrics = {
            'tables': [],
            'total_database_size': 'Unknown',
            'needs_vacuum': [],
            'needs_analyze': []
        }
        
        try:
            with db_manager.sync_engine.connect() as conn:
                # Get table statistics
                tables = conn.execute(text("""
                    SELECT 
                        schemaname,
                        tablename,
                        n_live_tup,
                        n_dead_tup,
                        last_vacuum,
                        last_autovacuum,
                        last_analyze,
                        last_autoanalyze,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
                        n_dead_tup::float / nullif(n_live_tup + n_dead_tup, 0) * 100 as dead_tuple_percent
                    FROM pg_stat_user_tables
                    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                    LIMIT 20
                """)).fetchall()
                
                for row in tables:
                    table_info = {
                        'name': row[1],
                        'live_tuples': row[2],
                        'dead_tuples': row[3],
                        'last_vacuum': row[4].isoformat() if row[4] else None,
                        'last_autovacuum': row[5].isoformat() if row[5] else None,
                        'last_analyze': row[6].isoformat() if row[6] else None,
                        'last_autoanalyze': row[7].isoformat() if row[7] else None,
                        'size': row[8],
                        'dead_tuple_percent': round(row[9] or 0, 2)
                    }
                    
                    metrics['tables'].append(table_info)
                    
                    # Check if needs vacuum (>20% dead tuples)
                    if row[9] and row[9] > 20:
                        metrics['needs_vacuum'].append(row[1])
                        
                    # Check if needs analyze (not analyzed in last 7 days)
                    last_analyze = row[7] or row[6]
                    if not last_analyze or (datetime.utcnow() - last_analyze).days > 7:
                        metrics['needs_analyze'].append(row[1])
                        
                # Get total database size
                db_size = conn.execute(text("""
                    SELECT pg_size_pretty(pg_database_size(current_database()))
                """)).fetchone()
                
                if db_size:
                    metrics['total_database_size'] = db_size[0]
                    
        except Exception as e:
            logger.warning(f"Could not get table health metrics: {e}")
            
        return metrics
        
    async def _get_database_activity_metrics(self) -> Dict[str, Any]:
        """Get current database activity metrics."""
        from app.core.database_manager import db_manager
        
        metrics = {
            'active_connections': 0,
            'idle_connections': 0,
            'idle_in_transaction': 0,
            'waiting_connections': 0,
            'longest_query_duration_ms': 0,
            'blocked_queries': []
        }
        
        try:
            with db_manager.sync_engine.connect() as conn:
                # Get connection states
                activity = conn.execute(text("""
                    SELECT 
                        state,
                        COUNT(*) as count,
                        MAX(EXTRACT(EPOCH FROM (clock_timestamp() - query_start))) * 1000 as max_duration_ms
                    FROM pg_stat_activity
                    WHERE pid != pg_backend_pid()
                    GROUP BY state
                """)).fetchall()
                
                for row in activity:
                    state = row[0]
                    count = row[1]
                    
                    if state == 'active':
                        metrics['active_connections'] = count
                        metrics['longest_query_duration_ms'] = round(row[2] or 0, 2)
                    elif state == 'idle':
                        metrics['idle_connections'] = count
                    elif state == 'idle in transaction':
                        metrics['idle_in_transaction'] = count
                    elif state and 'wait' in state:
                        metrics['waiting_connections'] = count
                        
                # Check for blocked queries
                blocked = conn.execute(text("""
                    SELECT 
                        blocked_locks.pid AS blocked_pid,
                        blocked_activity.usename AS blocked_user,
                        blocking_locks.pid AS blocking_pid,
                        blocking_activity.usename AS blocking_user,
                        blocked_activity.query AS blocked_query,
                        blocking_activity.query AS blocking_query
                    FROM pg_catalog.pg_locks blocked_locks
                    JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
                    JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
                        AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
                        AND blocking_locks.pid != blocked_locks.pid
                    JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
                    WHERE NOT blocked_locks.granted
                    LIMIT 5
                """)).fetchall()
                
                metrics['blocked_queries'] = [
                    {
                        'blocked_pid': row[0],
                        'blocked_user': row[1],
                        'blocking_pid': row[2],
                        'blocking_user': row[3],
                        'blocked_query': row[4][:100] if row[4] else None,
                        'blocking_query': row[5][:100] if row[5] else None
                    }
                    for row in blocked
                ]
                
        except Exception as e:
            logger.warning(f"Could not get database activity metrics: {e}")
            
        return metrics
        
    def _check_alert_conditions(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check metrics against alert thresholds."""
        alerts = []
        
        # Check connection pool usage
        pool_usage = metrics.get('connection_pool', {}).get('usage_percentage', 0)
        if pool_usage > self.alert_thresholds['connection_pool_usage']:
            alerts.append({
                'type': 'connection_pool_exhaustion',
                'severity': 'high',
                'message': f'Connection pool usage at {pool_usage}%',
                'value': pool_usage,
                'threshold': self.alert_thresholds['connection_pool_usage']
            })
            
        # Check for slow queries
        slow_queries = metrics.get('query_performance', {}).get('slow_queries', [])
        if slow_queries:
            worst_query = max(slow_queries, key=lambda x: x.get('avg_time_ms', 0))
            if worst_query.get('avg_time_ms', 0) > self.alert_thresholds['slow_query_ms']:
                alerts.append({
                    'type': 'slow_query',
                    'severity': 'medium',
                    'message': f'Query averaging {worst_query["avg_time_ms"]}ms',
                    'query': worst_query.get('query', ''),
                    'threshold': self.alert_thresholds['slow_query_ms']
                })
                
        # Check for blocked queries
        blocked = metrics.get('database_activity', {}).get('blocked_queries', [])
        if blocked:
            alerts.append({
                'type': 'blocked_queries',
                'severity': 'high',
                'message': f'{len(blocked)} queries are blocked',
                'count': len(blocked)
            })
            
        # Check for tables needing vacuum
        needs_vacuum = metrics.get('table_health', {}).get('needs_vacuum', [])
        if len(needs_vacuum) > 3:
            alerts.append({
                'type': 'vacuum_needed',
                'severity': 'medium',
                'message': f'{len(needs_vacuum)} tables need vacuum',
                'tables': needs_vacuum
            })
            
        return alerts
        
    def _store_metrics_history(self, metrics: Dict[str, Any]):
        """Store metrics in history for trend analysis."""
        # Keep last 24 hours of metrics (every 5 minutes = 288 data points)
        max_history = 288
        
        for key, value in metrics.items():
            if key != 'timestamp' and key != 'alerts':
                self.metrics_history[key].append({
                    'timestamp': metrics['timestamp'],
                    'value': value
                })
                
                # Trim history
                if len(self.metrics_history[key]) > max_history:
                    self.metrics_history[key] = self.metrics_history[key][-max_history:]
                    
    async def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        # Get latest metrics
        latest_metrics = await self.collect_metrics()
        
        # Calculate trends
        trends = self._calculate_trends()
        
        # Get recommendations
        recommendations = self._generate_recommendations(latest_metrics, trends)
        
        return {
            'current_metrics': latest_metrics,
            'trends': trends,
            'recommendations': recommendations,
            'report_generated': datetime.utcnow().isoformat()
        }
        
    def _calculate_trends(self) -> Dict[str, Any]:
        """Calculate performance trends from history."""
        trends = {}
        
        # Connection pool trend
        if 'connection_pool' in self.metrics_history:
            pool_history = [
                h['value'].get('usage_percentage', 0) 
                for h in self.metrics_history['connection_pool'][-12:]  # Last hour
            ]
            
            if pool_history:
                trends['connection_pool_trend'] = {
                    'current': pool_history[-1] if pool_history else 0,
                    'avg_last_hour': sum(pool_history) / len(pool_history),
                    'max_last_hour': max(pool_history),
                    'increasing': pool_history[-1] > pool_history[0] if len(pool_history) > 1 else False
                }
                
        return trends
        
    def _generate_recommendations(self, metrics: Dict[str, Any], trends: Dict[str, Any]) -> List[str]:
        """Generate performance recommendations based on metrics."""
        recommendations = []
        
        # Connection pool recommendations
        pool_usage = metrics.get('connection_pool', {}).get('usage_percentage', 0)
        if pool_usage > 90:
            recommendations.append(
                "CRITICAL: Connection pool near exhaustion. Consider increasing pool_size and max_overflow."
            )
        elif pool_usage > 70:
            recommendations.append(
                "WARNING: High connection pool usage. Monitor for potential exhaustion."
            )
            
        # Query performance recommendations
        slow_queries = metrics.get('query_performance', {}).get('slow_queries', [])
        if len(slow_queries) > 5:
            recommendations.append(
                f"Found {len(slow_queries)} slow queries. Review query optimization and indexing."
            )
            
        # Index recommendations
        unused_indexes = metrics.get('index_usage', {}).get('unused_indexes', [])
        if unused_indexes:
            recommendations.append(
                f"Found {len(unused_indexes)} unused indexes consuming space. Consider dropping them."
            )
            
        # Vacuum recommendations
        needs_vacuum = metrics.get('table_health', {}).get('needs_vacuum', [])
        if needs_vacuum:
            recommendations.append(
                f"Tables needing vacuum: {', '.join(needs_vacuum[:5])}. Run VACUUM to reclaim space."
            )
            
        return recommendations


# Global instance
db_performance_monitor = DatabasePerformanceMonitor()