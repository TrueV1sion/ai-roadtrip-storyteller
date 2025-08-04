"""
Health check and monitoring endpoints for production readiness.
Provides comprehensive system health information.
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
import asyncio
import psutil
import os
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text
import redis

from app.core.database_manager import DatabaseManager
from app.core.config import settings
from app.core.logger import get_logger
from app.core.cache import get_cache
from app.core.token_blacklist import token_blacklist
from app.database import get_db

logger = get_logger(__name__)
router = APIRouter(prefix="/health", tags=["monitoring"])


async def check_database_health(db: Session) -> Dict[str, Any]:
    """Check database connectivity and basic operations."""
    try:
        start_time = datetime.utcnow()
        
        # Test basic query
        result = db.execute(text("SELECT 1"))
        result.scalar()
        
        # Get connection pool stats if available
        engine = db.get_bind()
        pool_status = {
            "size": engine.pool.size() if hasattr(engine.pool, 'size') else "N/A",
            "checked_in": engine.pool.checkedin() if hasattr(engine.pool, 'checkedin') else "N/A",
            "overflow": engine.pool.overflow() if hasattr(engine.pool, 'overflow') else "N/A",
            "total": engine.pool._created if hasattr(engine.pool, '_created') else "N/A"
        }
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            "status": "healthy",
            "response_time_ms": round(response_time, 2),
            "pool_status": pool_status
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "response_time_ms": None
        }


async def check_redis_health() -> Dict[str, Any]:
    """Check Redis connectivity and operations."""
    try:
        start_time = datetime.utcnow()
        
        # Get cache instance
        cache = get_cache()
        if not cache or not cache.redis_client:
            return {
                "status": "unavailable",
                "error": "Redis not configured",
                "response_time_ms": None
            }
        
        # Test basic operations
        test_key = "_health_check_test"
        cache.redis_client.setex(test_key, 10, "test_value")
        value = cache.redis_client.get(test_key)
        cache.redis_client.delete(test_key)
        
        # Get Redis info
        info = cache.redis_client.info()
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return {
            "status": "healthy",
            "response_time_ms": round(response_time, 2),
            "connected_clients": info.get("connected_clients", 0),
            "used_memory_human": info.get("used_memory_human", "N/A"),
            "uptime_in_seconds": info.get("uptime_in_seconds", 0)
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "response_time_ms": None
        }


async def check_external_apis() -> Dict[str, Any]:
    """Check connectivity to external APIs."""
    api_statuses = {}
    
    # List of APIs to check
    apis_to_check = [
        ("Google Maps", settings.GOOGLE_MAPS_API_KEY is not None),
        ("Ticketmaster", settings.TICKETMASTER_API_KEY is not None),
        ("OpenWeatherMap", settings.OPENWEATHERMAP_API_KEY is not None),
        ("Recreation.gov", settings.RECREATION_GOV_API_KEY is not None),
        ("Google AI", settings.GOOGLE_AI_PROJECT_ID is not None),
    ]
    
    for api_name, is_configured in apis_to_check:
        api_statuses[api_name] = {
            "configured": is_configured,
            "status": "configured" if is_configured else "not_configured"
        }
    
    return api_statuses


def get_system_metrics() -> Dict[str, Any]:
    """Get system resource metrics."""
    try:
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        
        # Memory metrics
        memory = psutil.virtual_memory()
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        
        # Process metrics
        process = psutil.Process()
        process_info = {
            "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
            "cpu_percent": process.cpu_percent(interval=0.1),
            "num_threads": process.num_threads(),
            "open_files": len(process.open_files()) if hasattr(process, 'open_files') else "N/A"
        }
        
        return {
            "cpu": {
                "percent": cpu_percent,
                "count": cpu_count
            },
            "memory": {
                "total_gb": round(memory.total / 1024 / 1024 / 1024, 2),
                "available_gb": round(memory.available / 1024 / 1024 / 1024, 2),
                "percent": memory.percent
            },
            "disk": {
                "total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
                "free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
                "percent": disk.percent
            },
            "process": process_info
        }
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        return {"error": str(e)}


@router.get("/", status_code=status.HTTP_200_OK)
async def health_check():
    """Basic health check endpoint for load balancers."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.APP_VERSION
    }


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_probe():
    """Kubernetes liveness probe - checks if service is alive."""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/ready")
async def readiness_probe(db: Session = Depends(get_db)):
    """
    Kubernetes readiness probe - checks if service is ready to accept traffic.
    Returns 503 if any critical dependency is unhealthy.
    """
    checks = {
        "database": await check_database_health(db),
        "redis": await check_redis_health()
    }
    
    # Determine overall health
    is_ready = all(
        check.get("status") == "healthy" 
        for check in checks.values() 
        if check.get("status") != "unavailable"  # Redis is optional
    )
    
    response = {
        "status": "ready" if is_ready else "not_ready",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks
    }
    
    if not is_ready:
        return response, status.HTTP_503_SERVICE_UNAVAILABLE
    
    return response


@router.get("/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """
    Detailed health check with comprehensive system information.
    Useful for monitoring dashboards and debugging.
    """
    # Run all health checks concurrently
    db_health_task = asyncio.create_task(check_database_health(db))
    redis_health_task = asyncio.create_task(check_redis_health())
    api_health_task = asyncio.create_task(check_external_apis())
    
    # Wait for all checks to complete
    db_health = await db_health_task
    redis_health = await redis_health_task
    api_health = await api_health_task
    
    # Get synchronous metrics
    system_metrics = get_system_metrics()
    
    # Token blacklist status
    blacklist_size = token_blacklist.get_blacklist_size() if token_blacklist.redis_client else 0
    
    # Build comprehensive response
    return {
        "status": "detailed_check",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "uptime_seconds": (datetime.utcnow() - datetime.fromtimestamp(psutil.boot_time())).total_seconds(),
        "health_checks": {
            "database": db_health,
            "redis": redis_health,
            "external_apis": api_health
        },
        "system_metrics": system_metrics,
        "application_metrics": {
            "token_blacklist_size": blacklist_size,
            "debug_mode": settings.DEBUG,
            "log_level": settings.LOG_LEVEL
        }
    }


@router.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus-compatible metrics endpoint.
    Returns metrics in Prometheus text format.
    """
    # Get current metrics
    system_metrics = get_system_metrics()
    
    # Format as Prometheus metrics
    metrics_lines = [
        "# HELP app_info Application information",
        "# TYPE app_info gauge",
        f'app_info{{version="{settings.APP_VERSION}",environment="{settings.ENVIRONMENT}"}} 1',
        "",
        "# HELP system_cpu_percent CPU usage percentage",
        "# TYPE system_cpu_percent gauge",
        f"system_cpu_percent {system_metrics.get('cpu', {}).get('percent', 0)}",
        "",
        "# HELP system_memory_percent Memory usage percentage", 
        "# TYPE system_memory_percent gauge",
        f"system_memory_percent {system_metrics.get('memory', {}).get('percent', 0)}",
        "",
        "# HELP system_disk_percent Disk usage percentage",
        "# TYPE system_disk_percent gauge",
        f"system_disk_percent {system_metrics.get('disk', {}).get('percent', 0)}",
        "",
        "# HELP process_memory_mb Process memory usage in MB",
        "# TYPE process_memory_mb gauge",
        f"process_memory_mb {system_metrics.get('process', {}).get('memory_mb', 0)}",
        ""
    ]
    
    return "\n".join(metrics_lines), 200, {"Content-Type": "text/plain; charset=utf-8"}