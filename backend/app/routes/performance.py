"""
Performance monitoring and optimization endpoints
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app.core.auth import get_current_active_user
from app.core.authorization import require_permissions
from app.models.user import User
from app.core.query_analyzer import query_analyzer, analyze_query_performance
from app.core.connection_pool import get_connection_pool_metrics, pool_manager
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/performance",
    tags=["performance"],
    responses={404: {"description": "Not found"}},
)


@router.get("/query-stats", response_model=Dict[str, Any])
async def get_query_statistics(
    current_user: User = Depends(require_permissions(["admin", "developer"]))
) -> Dict[str, Any]:
    """
    Get comprehensive query performance statistics.
    
    Requires admin or developer permissions.
    """
    try:
        stats = query_analyzer.get_query_statistics()
        return {
            "status": "success",
            "data": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting query statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve query statistics")


@router.get("/slow-queries", response_model=Dict[str, Any])
async def get_slow_queries(
    limit: int = Query(10, ge=1, le=100),
    threshold: float = Query(0.1, ge=0.01, le=10.0),
    current_user: User = Depends(require_permissions(["admin", "developer"]))
) -> Dict[str, Any]:
    """
    Get top slow queries with optimization suggestions.
    
    Args:
        limit: Number of queries to return
        threshold: Slow query threshold in seconds
        
    Requires admin or developer permissions.
    """
    try:
        # Get all query metrics
        all_metrics = []
        for metrics_list in query_analyzer.query_metrics.values():
            all_metrics.extend([
                m for m in metrics_list 
                if m.duration >= threshold
            ])
        
        # Sort by duration and get top N
        slow_queries = sorted(
            all_metrics,
            key=lambda x: x.duration,
            reverse=True
        )[:limit]
        
        # Format response
        formatted_queries = []
        for query in slow_queries:
            query_hash = query_analyzer._hash_query(query.query)
            suggestions = query_analyzer.optimization_suggestions.get(query_hash, [])
            
            formatted_queries.append({
                "query": query.query[:500] + "..." if len(query.query) > 500 else query.query,
                "duration": query.duration,
                "rows_returned": query.rows_returned,
                "timestamp": query.timestamp.isoformat(),
                "suggestions": suggestions
            })
        
        return {
            "status": "success",
            "data": {
                "slow_queries": formatted_queries,
                "threshold": threshold,
                "total_found": len(all_metrics)
            }
        }
    except Exception as e:
        logger.error(f"Error getting slow queries: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve slow queries")


@router.post("/analyze-query", response_model=Dict[str, Any])
async def analyze_specific_query(
    query_data: Dict[str, str],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(["admin", "developer"]))
) -> Dict[str, Any]:
    """
    Analyze performance of a specific query.
    
    Args:
        query_data: Dictionary with 'query' key containing SQL query
        
    Requires admin or developer permissions.
    """
    query = query_data.get("query", "").strip()
    
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Validate it's a SELECT query (for safety)
    if not query.upper().startswith("SELECT"):
        raise HTTPException(
            status_code=400, 
            detail="Only SELECT queries can be analyzed"
        )
    
    try:
        # Analyze the query
        analysis = await analyze_query_performance(db, query)
        
        return {
            "status": "success",
            "data": analysis,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error analyzing query: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to analyze query: {str(e)}"
        )


@router.get("/connection-pools", response_model=Dict[str, Any])
async def get_connection_pool_stats(
    current_user: User = Depends(require_permissions(["admin", "developer"]))
) -> Dict[str, Any]:
    """
    Get connection pool statistics and health.
    
    Requires admin or developer permissions.
    """
    try:
        metrics = get_connection_pool_metrics()
        health = pool_manager.get_health_status()
        
        return {
            "status": "success",
            "data": {
                "metrics": metrics,
                "health": health
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting connection pool stats: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to retrieve connection pool statistics"
        )


@router.post("/optimize-pool/{pool_name}", response_model=Dict[str, Any])
async def optimize_connection_pool(
    pool_name: str = "default",
    current_user: User = Depends(require_permissions(["admin"]))
) -> Dict[str, Any]:
    """
    Trigger optimization for a specific connection pool.
    
    Args:
        pool_name: Name of the pool to optimize
        
    Requires admin permissions.
    """
    try:
        # Get before stats
        before_stats = pool_manager.get_pool_statistics(pool_name)
        
        # Run optimization
        pool_manager.optimize_pool(pool_name)
        
        # Get after stats
        after_stats = pool_manager.get_pool_statistics(pool_name)
        
        return {
            "status": "success",
            "data": {
                "pool_name": pool_name,
                "before": before_stats,
                "after": after_stats,
                "recommendations": []  # Will be populated by optimize_pool
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error optimizing pool: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to optimize pool: {str(e)}"
        )


@router.get("/optimization-report", response_model=Dict[str, Any])
async def get_optimization_report(
    current_user: User = Depends(require_permissions(["admin", "developer"]))
) -> Dict[str, Any]:
    """
    Get comprehensive database optimization report.
    
    Requires admin or developer permissions.
    """
    try:
        report = query_analyzer.get_optimization_report()
        
        # Add connection pool info
        pool_metrics = get_connection_pool_metrics()
        
        # Get database statistics
        db_stats = await _get_database_statistics()
        
        return {
            "status": "success",
            "data": {
                "query_report": report,
                "connection_pools": pool_metrics,
                "database_stats": db_stats,
                "recommendations": _generate_recommendations(report, pool_metrics, db_stats)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error generating optimization report: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to generate optimization report"
        )


@router.get("/cache-stats", response_model=Dict[str, Any])
async def get_cache_statistics(
    current_user: User = Depends(require_permissions(["admin", "developer"]))
) -> Dict[str, Any]:
    """
    Get cache performance statistics.
    
    Requires admin or developer permissions.
    """
    try:
        from app.core.cache import get_cache_stats
        
        cache_stats = await get_cache_stats()
        
        return {
            "status": "success",
            "data": cache_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting cache statistics: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to retrieve cache statistics"
        )


async def _get_database_statistics() -> Dict[str, Any]:
    """Get PostgreSQL database statistics"""
    try:
        stats = {}
        
        # Get database size
        with pool_manager.get_db_session() as db:
            result = db.execute(text("""
                SELECT 
                    pg_database_size(current_database()) as db_size,
                    pg_size_pretty(pg_database_size(current_database())) as db_size_pretty
            """))
            row = result.fetchone()
            stats["database_size"] = {
                "bytes": row.db_size,
                "formatted": row.db_size_pretty
            }
            
            # Get table statistics
            result = db.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
                    n_live_tup as row_count,
                    n_dead_tup as dead_rows
                FROM pg_stat_user_tables
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 10
            """))
            
            stats["largest_tables"] = [
                {
                    "schema": row.schemaname,
                    "table": row.tablename,
                    "size": row.size,
                    "row_count": row.row_count,
                    "dead_rows": row.dead_rows
                }
                for row in result
            ]
            
            # Get index usage
            result = db.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan as index_scans,
                    idx_tup_read as tuples_read,
                    idx_tup_fetch as tuples_fetched
                FROM pg_stat_user_indexes
                WHERE idx_scan = 0
                LIMIT 10
            """))
            
            stats["unused_indexes"] = [
                {
                    "schema": row.schemaname,
                    "table": row.tablename,
                    "index": row.indexname
                }
                for row in result
            ]
            
        return stats
    except Exception as e:
        logger.error(f"Error getting database statistics: {e}")
        return {"error": str(e)}


def _generate_recommendations(
    query_report: str, 
    pool_metrics: Dict[str, Any], 
    db_stats: Dict[str, Any]
) -> List[str]:
    """Generate optimization recommendations based on collected data"""
    recommendations = []
    
    # Check slow query percentage
    if "slow_query_percentage" in query_report:
        # Extract percentage from report
        for line in query_report.split("\n"):
            if "Slow Queries:" in line and "%" in line:
                percentage = float(line.split("(")[1].split("%")[0])
                if percentage > 10:
                    recommendations.append(
                        f"High slow query rate ({percentage:.1f}%). "
                        "Review and optimize slow queries."
                    )
    
    # Check connection pool efficiency
    summary = pool_metrics.get("summary", {})
    pool_efficiency = summary.get("pool_efficiency", 100)
    if pool_efficiency < 80:
        recommendations.append(
            f"Low connection pool efficiency ({pool_efficiency:.1f}%). "
            "Consider adjusting pool size or investigating connection leaks."
        )
    
    # Check for unused indexes
    unused_indexes = db_stats.get("unused_indexes", [])
    if unused_indexes:
        recommendations.append(
            f"Found {len(unused_indexes)} unused indexes. "
            "Consider removing them to improve write performance."
        )
    
    # Check for tables with high dead row count
    largest_tables = db_stats.get("largest_tables", [])
    for table in largest_tables:
        if table.get("dead_rows", 0) > table.get("row_count", 1) * 0.2:
            recommendations.append(
                f"Table {table['table']} has high dead row ratio. "
                "Consider running VACUUM ANALYZE."
            )
    
    if not recommendations:
        recommendations.append("Database performance appears optimal.")
    
    return recommendations