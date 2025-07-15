"""
Database Monitoring API Routes

Provides endpoints for monitoring database performance and health.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timedelta

from app.core.auth import get_current_user, require_admin
from app.core.database_monitoring import db_performance_monitor
from app.core.database_optimization_v2 import db_optimization_manager
from app.models.user import User
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/database",
    tags=["database-monitoring"],
    responses={404: {"description": "Not found"}},
)


@router.get("/metrics", response_model=Dict[str, Any])
async def get_database_metrics(
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get current database performance metrics.
    
    Requires admin privileges.
    
    Returns comprehensive metrics including:
    - Connection pool usage
    - Query performance statistics
    - Index usage and effectiveness
    - Table health and vacuum status
    - Current database activity
    - Performance alerts
    """
    try:
        metrics = await db_performance_monitor.collect_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Failed to collect database metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to collect metrics")


@router.get("/performance-report", response_model=Dict[str, Any])
async def get_performance_report(
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Generate comprehensive database performance report.
    
    Includes:
    - Current metrics
    - Historical trends
    - Performance recommendations
    """
    try:
        report = await db_performance_monitor.get_performance_report()
        return report
    except Exception as e:
        logger.error(f"Failed to generate performance report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate report")


@router.get("/connection-pool", response_model=Dict[str, Any])
async def get_connection_pool_status(
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get detailed connection pool status.
    
    Returns:
    - Current pool configuration
    - Active connections
    - Usage statistics
    - Wait times
    """
    try:
        from app.core.database_manager import db_manager
        
        if not db_manager.sync_engine:
            raise HTTPException(status_code=503, detail="Database not initialized")
            
        pool = db_manager.sync_engine.pool
        
        return {
            "configuration": {
                "pool_size": pool.size(),
                "max_overflow": pool._max_overflow,
                "timeout": getattr(pool, '_timeout', 30),
                "recycle_time": getattr(pool, '_recycle', 1800),
                "pre_ping": getattr(pool, '_pre_ping', True)
            },
            "current_status": {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "total": pool.checkedout() + pool.overflow(),
                "available": pool.checkedin()
            },
            "usage": {
                "percentage": round((pool.checkedout() + pool.overflow()) / (pool.size() + pool._max_overflow) * 100, 2),
                "efficiency": round(pool.checkedin() / pool.size() * 100, 2) if pool.size() > 0 else 0
            }
        }
    except Exception as e:
        logger.error(f"Failed to get connection pool status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get pool status")


@router.get("/slow-queries", response_model=Dict[str, Any])
async def get_slow_queries(
    threshold_ms: int = Query(default=50, description="Threshold in milliseconds"),
    limit: int = Query(default=20, description="Maximum number of queries to return"),
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get slow queries exceeding the specified threshold.
    
    Parameters:
    - threshold_ms: Query time threshold in milliseconds (default: 50ms)
    - limit: Maximum number of queries to return (default: 20)
    """
    try:
        from app.core.database_manager import db_manager
        from sqlalchemy import text
        
        query = """
        SELECT 
            query,
            calls,
            mean_exec_time,
            max_exec_time,
            total_exec_time,
            rows,
            100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
        FROM pg_stat_statements
        WHERE mean_exec_time > :threshold
        ORDER BY mean_exec_time DESC
        LIMIT :limit
        """
        
        with db_manager.sync_engine.connect() as conn:
            result = conn.execute(
                text(query), 
                {'threshold': threshold_ms, 'limit': limit}
            )
            
            slow_queries = []
            for row in result:
                slow_queries.append({
                    'query': row[0][:200],  # Truncate long queries
                    'calls': row[1],
                    'avg_time_ms': round(row[2], 2),
                    'max_time_ms': round(row[3], 2),
                    'total_time_ms': round(row[4], 2),
                    'rows_returned': row[5],
                    'cache_hit_rate': round(row[6] or 0, 2)
                })
                
            return {
                'threshold_ms': threshold_ms,
                'count': len(slow_queries),
                'queries': slow_queries
            }
            
    except Exception as e:
        logger.error(f"Failed to get slow queries: {e}")
        raise HTTPException(status_code=500, detail="Failed to get slow queries")


@router.get("/index-usage", response_model=Dict[str, Any])
async def get_index_usage(
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get index usage statistics and recommendations.
    
    Returns:
    - Unused indexes that can be dropped
    - Most used indexes
    - Index hit rates
    - Missing index suggestions
    """
    try:
        metrics = await db_performance_monitor._get_index_usage_metrics()
        
        # Add recommendations
        recommendations = []
        
        if metrics['unused_indexes']:
            recommendations.append({
                'type': 'unused_indexes',
                'severity': 'low',
                'message': f"Found {len(metrics['unused_indexes'])} unused indexes that could be dropped to save space"
            })
            
        if metrics['index_hit_rate'] < 95:
            recommendations.append({
                'type': 'low_hit_rate',
                'severity': 'medium',
                'message': f"Index hit rate is {metrics['index_hit_rate']}%. Consider adding more indexes or increasing shared_buffers"
            })
            
        metrics['recommendations'] = recommendations
        
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to get index usage: {e}")
        raise HTTPException(status_code=500, detail="Failed to get index usage")


@router.get("/table-health", response_model=Dict[str, Any])
async def get_table_health(
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get table health metrics including bloat and vacuum status.
    
    Returns:
    - Table sizes and tuple counts
    - Dead tuple percentages
    - Last vacuum/analyze times
    - Tables needing maintenance
    """
    try:
        metrics = await db_performance_monitor._get_table_health_metrics()
        
        # Add maintenance recommendations
        recommendations = []
        
        if metrics['needs_vacuum']:
            recommendations.append({
                'action': 'VACUUM',
                'tables': metrics['needs_vacuum'],
                'reason': 'High dead tuple percentage (>20%)'
            })
            
        if metrics['needs_analyze']:
            recommendations.append({
                'action': 'ANALYZE',
                'tables': metrics['needs_analyze'],
                'reason': 'Statistics outdated (>7 days)'
            })
            
        metrics['maintenance_recommendations'] = recommendations
        
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to get table health: {e}")
        raise HTTPException(status_code=500, detail="Failed to get table health")


@router.post("/optimize", response_model=Dict[str, Any])
async def run_optimization(
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Run database optimization tasks.
    
    This will:
    - Analyze tables to update statistics
    - Refresh materialized views
    - Check and create missing indexes
    - Run VACUUM on tables that need it
    
    Note: This operation may impact performance temporarily.
    """
    try:
        logger.info(f"Database optimization initiated by user {current_user.id}")
        
        # Initialize optimization manager if needed
        await db_optimization_manager.initialize()
        
        # Run maintenance tasks
        from app.core.database_optimization_v2 import MaintenanceScheduler
        scheduler = MaintenanceScheduler()
        
        results = {
            'started_at': datetime.utcnow().isoformat(),
            'tasks_completed': []
        }
        
        # Update statistics
        try:
            await scheduler._update_statistics()
            results['tasks_completed'].append('Updated table statistics')
        except Exception as e:
            logger.error(f"Failed to update statistics: {e}")
            
        # Refresh materialized views
        try:
            await scheduler._refresh_materialized_views()
            results['tasks_completed'].append('Refreshed materialized views')
        except Exception as e:
            logger.error(f"Failed to refresh views: {e}")
            
        # Run vacuum on tables that need it
        try:
            await scheduler._vacuum_analyze_tables()
            results['tasks_completed'].append('Ran VACUUM ANALYZE on tables')
        except Exception as e:
            logger.error(f"Failed to vacuum tables: {e}")
            
        results['completed_at'] = datetime.utcnow().isoformat()
        results['success'] = len(results['tasks_completed']) > 0
        
        return results
        
    except Exception as e:
        logger.error(f"Failed to run optimization: {e}")
        raise HTTPException(status_code=500, detail="Failed to run optimization")


@router.get("/alerts", response_model=Dict[str, Any])
async def get_performance_alerts(
    severity: str = Query(default=None, description="Filter by severity: low, medium, high"),
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get current database performance alerts.
    
    Parameters:
    - severity: Filter alerts by severity level
    """
    try:
        # Get latest metrics with alerts
        metrics = await db_performance_monitor.collect_metrics()
        alerts = metrics.get('alerts', [])
        
        # Filter by severity if specified
        if severity:
            alerts = [a for a in alerts if a.get('severity') == severity]
            
        return {
            'total_alerts': len(alerts),
            'alerts': alerts,
            'checked_at': metrics['timestamp']
        }
        
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get alerts")


@router.get("/health-check", response_model=Dict[str, Any])
async def database_health_check() -> Dict[str, Any]:
    """
    Quick database health check (no auth required).
    
    Returns basic health status for monitoring systems.
    """
    try:
        from app.core.database_manager import get_database_health
        
        health = get_database_health()
        
        # Simplified response for monitoring
        return {
            'status': health.get('status', 'unknown'),
            'response_time_ms': health.get('response_time_ms', 0),
            'connection_pool': {
                'total': health.get('connection_pool', {}).get('size', 0),
                'available': health.get('connection_pool', {}).get('checked_in', 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e)
        }