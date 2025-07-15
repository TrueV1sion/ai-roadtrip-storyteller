from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
from pydantic import BaseModel

from app.core.security import get_current_user
from app.core.authorization import require_admin
from app.core.enums import Action, ResourceType
from app.models.user import User
from app.monitoring.db_performance import DBPerformanceMonitor
from app.core.db_optimized import get_db_stats, check_db_connection

router = APIRouter()


class SlowQueryResponse(BaseModel):
    """Response model for slow query information."""
    query: str
    avg_execution_time: float
    max_execution_time: float
    call_count: int
    last_execution: float


class DBStatsResponse(BaseModel):
    """Response model for database statistics."""
    total_queries_tracked: int
    unique_queries: int
    total_execution_time: float
    average_execution_time: float
    pool_size: int
    connections_checkedin: int
    connections_checkedout: int
    connection_status: str


@router.get("/db/stats", response_model=DBStatsResponse, tags=["Monitoring"])
async def get_database_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Get database performance statistics.
    Requires admin permissions.
    """
    # Ensure the user has admin permissions
    require_admin(current_user, Action.READ, ResourceType.SYSTEM)
    
    # Get query stats
    query_stats = DBPerformanceMonitor.get_query_stats()
    
    # Get connection pool stats
    pool_stats = get_db_stats()
    
    # Check connection status
    connection_status = "healthy" if check_db_connection() else "unhealthy"
    
    return DBStatsResponse(
        total_queries_tracked=query_stats["total_queries_tracked"],
        unique_queries=query_stats["unique_queries"],
        total_execution_time=query_stats["total_execution_time"],
        average_execution_time=query_stats["average_execution_time"],
        pool_size=pool_stats["pool_size"],
        connections_checkedin=pool_stats["checkedin"],
        connections_checkedout=pool_stats["checkedout"],
        connection_status=connection_status
    )


@router.get("/db/slow-queries", response_model=List[SlowQueryResponse], tags=["Monitoring"])
async def get_slow_queries(
    threshold: float = 0.1,
    current_user: User = Depends(get_current_user)
):
    """
    Get list of slow database queries.
    Requires admin permissions.
    
    Args:
        threshold: Time threshold in seconds (default: 0.1s)
    """
    # Ensure the user has admin permissions
    require_admin(current_user, Action.READ, ResourceType.SYSTEM)
    
    # Get slow queries
    slow_queries = DBPerformanceMonitor.get_slow_queries(threshold)
    
    return [
        SlowQueryResponse(
            query=item["query"],
            avg_execution_time=item["avg_execution_time"],
            max_execution_time=item["max_execution_time"],
            call_count=item["call_count"],
            last_execution=item["last_execution"]
        )
        for item in slow_queries
    ]


@router.post("/db/clear-stats", tags=["Monitoring"])
async def clear_db_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Clear database performance statistics.
    Requires admin permissions.
    """
    # Ensure the user has admin permissions
    require_admin(current_user, Action.DELETE, ResourceType.SYSTEM)
    
    # Clear stats
    DBPerformanceMonitor.clear_stats()
    
    return {"status": "success", "message": "Database statistics cleared successfully"}