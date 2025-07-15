"""
Database health check and monitoring endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.database import get_db, get_database_health, get_database_info, check_database_migrations
from app.core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/health/database")
async def database_health_check() -> Dict[str, Any]:
    """
    Check database health and connection status.
    
    Returns:
        Dict with database health information
    """
    try:
        health_status = get_database_health()
        
        # Return appropriate HTTP status
        if health_status.get("status") == "healthy":
            return {
                "status": "healthy",
                "database": health_status,
                "timestamp": health_status.get("last_check")
            }
        else:
            return {
                "status": "unhealthy",
                "database": health_status,
                "timestamp": health_status.get("last_check")
            }
            
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Database health check failed: {str(e)}"
        )


@router.get("/health/database/detailed")
async def detailed_database_health() -> Dict[str, Any]:
    """
    Get detailed database health and configuration information.
    
    Returns:
        Dict with detailed database information
    """
    try:
        health_status = get_database_health()
        connection_info = get_database_info()
        migration_status = await check_database_migrations()
        
        return {
            "health": health_status,
            "connection": connection_info,
            "migrations": migration_status,
            "timestamp": health_status.get("last_check")
        }
        
    except Exception as e:
        logger.error(f"Detailed database health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Detailed database health check failed: {str(e)}"
        )


@router.get("/health/database/test-query")
async def test_database_query(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Test database with a simple query.
    
    Args:
        db: Database session
        
    Returns:
        Dict with query test results
    """
    try:
        from sqlalchemy import text
        import time
        
        start_time = time.time()
        
        # Execute a simple test query
        result = db.execute(text("SELECT 1 as test_value, NOW() as server_time"))
        row = result.fetchone()
        
        query_time = round((time.time() - start_time) * 1000, 2)
        
        if row:
            return {
                "status": "success",
                "test_value": row.test_value,
                "server_time": str(row.server_time),
                "query_time_ms": query_time,
                "message": "Database query test successful"
            }
        else:
            raise HTTPException(
                status_code=503,
                detail="Database query returned no results"
            )
            
    except Exception as e:
        logger.error(f"Database query test failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Database query test failed: {str(e)}"
        )


@router.get("/health/database/migrations")
async def migration_status() -> Dict[str, Any]:
    """
    Check database migration status.
    
    Returns:
        Dict with migration status information
    """
    try:
        migration_info = await check_database_migrations()
        
        if migration_info.get("status") == "error":
            raise HTTPException(
                status_code=503,
                detail=migration_info.get("message", "Migration check failed")
            )
        
        return migration_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Migration status check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Migration status check failed: {str(e)}"
        )