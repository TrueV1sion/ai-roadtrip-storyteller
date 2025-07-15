"""
Enhanced health check and monitoring endpoints for production readiness.
Provides deep health checks, dependency validation, and performance insights.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import asyncio
import psutil
import os
import time
import json
from collections import defaultdict
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import redis
import aiohttp

from app.core.database_manager import DatabaseManager
from app.core.config import settings
from app.core.logger import get_logger
from app.core.cache import get_cache
from app.core.token_blacklist import token_blacklist
from app.db.base import get_db
from app.middleware.performance_middleware import PerformanceOptimizationMiddleware
from app.monitoring.metrics_collector import metrics_collector

logger = get_logger(__name__)
router = APIRouter(prefix="/health/v2", tags=["monitoring"])


class HealthCheckService:
    """Service for comprehensive health checks."""
    
    def __init__(self):
        self.checks_cache = {}
        self.cache_ttl = 30  # seconds
        self.performance_history = defaultdict(list)
        self.max_history_size = 100
        
    async def check_database_deep(self, db: Session) -> Dict[str, Any]:
        """Perform deep database health check."""
        try:
            start_time = time.time()
            checks = {}
            
            # Basic connectivity
            result = db.execute(text("SELECT 1"))
            result.scalar()
            checks["connectivity"] = "pass"
            
            # Check tables exist
            tables = db.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)).fetchall()
            checks["table_count"] = len(tables)
            
            # Check database size
            db_size = db.execute(text("""
                SELECT pg_database_size(current_database()) as size
            """)).scalar()
            checks["database_size_mb"] = round(db_size / 1024 / 1024, 2)
            
            # Check active connections
            active_connections = db.execute(text("""
                SELECT count(*) FROM pg_stat_activity 
                WHERE state = 'active'
            """)).scalar()
            checks["active_connections"] = active_connections
            
            # Check for long-running queries
            long_queries = db.execute(text("""
                SELECT count(*) FROM pg_stat_activity 
                WHERE state = 'active' 
                AND query_start < NOW() - INTERVAL '5 minutes'
            """)).scalar()
            checks["long_running_queries"] = long_queries
            
            # Check replication status if applicable
            replication = db.execute(text("""
                SELECT client_addr, state, sync_state 
                FROM pg_stat_replication
            """)).fetchall()
            if replication:
                checks["replication"] = [
                    {"client": r[0], "state": r[1], "sync": r[2]} 
                    for r in replication
                ]
            
            # Connection pool stats
            engine = db.get_bind()
            if hasattr(engine.pool, 'size'):
                checks["pool_stats"] = {
                    "size": engine.pool.size(),
                    "checked_in": engine.pool.checkedin(),
                    "overflow": engine.pool.overflow(),
                    "total": engine.pool._created
                }
            
            response_time = (time.time() - start_time) * 1000
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "checks": checks,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Database deep health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def check_redis_deep(self) -> Dict[str, Any]:
        """Perform deep Redis health check."""
        try:
            start_time = time.time()
            cache = get_cache()
            
            if not cache or not cache.redis_client:
                return {
                    "status": "unavailable",
                    "error": "Redis not configured"
                }
            
            checks = {}
            
            # Test operations
            test_key = "_health_check_deep"
            test_value = {"timestamp": datetime.utcnow().isoformat()}
            
            # SET operation
            cache.redis_client.setex(test_key, 10, json.dumps(test_value))
            checks["set_operation"] = "pass"
            
            # GET operation
            retrieved = cache.redis_client.get(test_key)
            if retrieved:
                checks["get_operation"] = "pass"
            
            # DELETE operation
            cache.redis_client.delete(test_key)
            checks["delete_operation"] = "pass"
            
            # Get detailed info
            info = cache.redis_client.info()
            
            # Memory analysis
            memory_info = {
                "used_memory_human": info.get("used_memory_human"),
                "used_memory_peak_human": info.get("used_memory_peak_human"),
                "mem_fragmentation_ratio": info.get("mem_fragmentation_ratio"),
                "evicted_keys": info.get("evicted_keys", 0),
                "maxmemory_policy": info.get("maxmemory_policy", "noeviction")
            }
            
            # Performance metrics
            performance_info = {
                "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec"),
                "total_commands_processed": info.get("total_commands_processed"),
                "expired_keys": info.get("expired_keys", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }
            
            # Calculate hit ratio
            hits = performance_info["keyspace_hits"]
            misses = performance_info["keyspace_misses"]
            if hits + misses > 0:
                performance_info["hit_ratio"] = round(hits / (hits + misses), 3)
            
            # Persistence info
            persistence_info = {
                "rdb_last_save_time": info.get("rdb_last_save_time"),
                "rdb_changes_since_last_save": info.get("rdb_changes_since_last_save"),
                "aof_enabled": info.get("aof_enabled", 0)
            }
            
            response_time = (time.time() - start_time) * 1000
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "version": info.get("redis_version"),
                "uptime_seconds": info.get("uptime_in_seconds"),
                "connected_clients": info.get("connected_clients"),
                "checks": checks,
                "memory": memory_info,
                "performance": performance_info,
                "persistence": persistence_info,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Redis deep health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def check_external_dependencies(self) -> Dict[str, Any]:
        """Check health of external API dependencies."""
        results = {}
        
        # Define endpoints to check
        endpoints = {
            "google_maps": {
                "url": "https://maps.googleapis.com/maps/api/geocode/json",
                "params": {"address": "test", "key": settings.GOOGLE_MAPS_API_KEY},
                "timeout": 5
            },
            "openweathermap": {
                "url": "https://api.openweathermap.org/data/2.5/weather",
                "params": {"q": "London", "appid": settings.OPENWEATHERMAP_API_KEY},
                "timeout": 5
            }
        }
        
        async with aiohttp.ClientSession() as session:
            for service, config in endpoints.items():
                try:
                    start_time = time.time()
                    
                    if not config["params"].get("key") and not config["params"].get("appid"):
                        results[service] = {
                            "status": "not_configured",
                            "response_time_ms": None
                        }
                        continue
                    
                    async with session.get(
                        config["url"],
                        params=config["params"],
                        timeout=aiohttp.ClientTimeout(total=config["timeout"])
                    ) as response:
                        response_time = (time.time() - start_time) * 1000
                        
                        results[service] = {
                            "status": "healthy" if response.status == 200 else "unhealthy",
                            "status_code": response.status,
                            "response_time_ms": round(response_time, 2)
                        }
                        
                except asyncio.TimeoutError:
                    results[service] = {
                        "status": "timeout",
                        "response_time_ms": config["timeout"] * 1000
                    }
                except Exception as e:
                    results[service] = {
                        "status": "error",
                        "error": str(e),
                        "response_time_ms": None
                    }
        
        return results
    
    async def check_ai_service_health(self) -> Dict[str, Any]:
        """Check AI service health and quota."""
        try:
            # Check if AI service is configured
            if not settings.GOOGLE_AI_PROJECT_ID:
                return {
                    "status": "not_configured",
                    "error": "Google AI not configured"
                }
            
            # Get metrics from metrics collector
            ai_metrics = await metrics_collector.get_ai_metrics()
            
            # Calculate success rate
            total_requests = ai_metrics.get("total_requests", 0)
            failed_requests = ai_metrics.get("failed_requests", 0)
            success_rate = 0
            if total_requests > 0:
                success_rate = (total_requests - failed_requests) / total_requests
            
            return {
                "status": "healthy" if success_rate > 0.95 else "degraded",
                "total_requests_24h": total_requests,
                "failed_requests_24h": failed_requests,
                "success_rate": round(success_rate, 3),
                "avg_response_time_ms": ai_metrics.get("avg_response_time_ms", 0),
                "models_used": ai_metrics.get("models_used", []),
                "estimated_cost_24h": ai_metrics.get("estimated_cost_24h", 0),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"AI service health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get application performance metrics."""
        try:
            # Get metrics from performance middleware
            # This would integrate with your actual metrics collection
            return {
                "request_rate": {
                    "current": 0,  # Would be populated from metrics
                    "avg_1m": 0,
                    "avg_5m": 0
                },
                "response_times": {
                    "p50": 0,
                    "p95": 0,
                    "p99": 0
                },
                "error_rate": {
                    "current": 0,
                    "avg_1m": 0,
                    "avg_5m": 0
                },
                "active_requests": 0,
                "queued_requests": 0
            }
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {"error": str(e)}


# Initialize health check service
health_service = HealthCheckService()


@router.get("/deep")
async def deep_health_check(db: Session = Depends(get_db)):
    """
    Comprehensive deep health check for all system components.
    Provides detailed diagnostics for troubleshooting.
    """
    start_time = time.time()
    
    # Run all health checks concurrently
    db_task = asyncio.create_task(health_service.check_database_deep(db))
    redis_task = asyncio.create_task(health_service.check_redis_deep())
    external_task = asyncio.create_task(health_service.check_external_dependencies())
    ai_task = asyncio.create_task(health_service.check_ai_service_health())
    
    # Wait for all checks
    db_health = await db_task
    redis_health = await redis_task
    external_health = await external_task
    ai_health = await ai_task
    
    # Get system metrics
    system_metrics = {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory": {
            "percent": psutil.virtual_memory().percent,
            "available_mb": round(psutil.virtual_memory().available / 1024 / 1024),
            "total_mb": round(psutil.virtual_memory().total / 1024 / 1024)
        },
        "disk": {
            "percent": psutil.disk_usage('/').percent,
            "free_gb": round(psutil.disk_usage('/').free / 1024 / 1024 / 1024, 2)
        }
    }
    
    # Get performance metrics
    performance_metrics = health_service.get_performance_metrics()
    
    # Determine overall health status
    critical_services = ["database", "ai_service"]
    overall_health = "healthy"
    
    if db_health["status"] != "healthy":
        overall_health = "critical"
    elif ai_health["status"] not in ["healthy", "not_configured"]:
        overall_health = "degraded"
    elif redis_health["status"] != "healthy":
        overall_health = "degraded"
    
    # Check system resources
    if system_metrics["cpu_percent"] > 90 or system_metrics["memory"]["percent"] > 90:
        overall_health = "degraded" if overall_health == "healthy" else overall_health
    
    total_time = (time.time() - start_time) * 1000
    
    response = {
        "status": overall_health,
        "timestamp": datetime.utcnow().isoformat(),
        "total_check_time_ms": round(total_time, 2),
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "components": {
            "database": db_health,
            "cache": redis_health,
            "ai_service": ai_health,
            "external_apis": external_health
        },
        "system": system_metrics,
        "performance": performance_metrics
    }
    
    # Return appropriate status code
    if overall_health == "critical":
        return response, status.HTTP_503_SERVICE_UNAVAILABLE
    elif overall_health == "degraded":
        return response, status.HTTP_200_OK  # Still operational
    
    return response


@router.get("/dependencies")
async def check_dependencies():
    """Check status of all external dependencies."""
    dependencies = await health_service.check_external_dependencies()
    
    # Add internal service dependencies
    internal_deps = {
        "database": "configured" if settings.DATABASE_URL else "not_configured",
        "redis": "configured" if settings.REDIS_URL else "not_configured",
        "ai_service": "configured" if settings.GOOGLE_AI_PROJECT_ID else "not_configured"
    }
    
    return {
        "external": dependencies,
        "internal": internal_deps,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/performance")
async def performance_metrics():
    """Get detailed performance metrics."""
    metrics = health_service.get_performance_metrics()
    
    # Add cache performance
    cache = get_cache()
    if cache and cache.redis_client:
        info = cache.redis_client.info()
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        
        if hits + misses > 0:
            cache_hit_rate = hits / (hits + misses)
        else:
            cache_hit_rate = 0
        
        metrics["cache"] = {
            "hit_rate": round(cache_hit_rate, 3),
            "total_hits": hits,
            "total_misses": misses
        }
    
    return {
        "metrics": metrics,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/startup")
async def startup_check():
    """
    Startup health check to verify system is ready to accept traffic.
    Used by orchestrators during deployment.
    """
    checks = []
    all_passed = True
    
    # Check database
    try:
        db = next(get_db())
        result = db.execute(text("SELECT 1"))
        result.scalar()
        checks.append({"name": "database", "status": "pass"})
    except Exception as e:
        checks.append({"name": "database", "status": "fail", "error": str(e)})
        all_passed = False
    finally:
        if 'db' in locals():
            db.close()
    
    # Check Redis
    try:
        cache = get_cache()
        if cache and cache.redis_client:
            cache.redis_client.ping()
            checks.append({"name": "redis", "status": "pass"})
        else:
            checks.append({"name": "redis", "status": "skip", "reason": "not configured"})
    except Exception as e:
        checks.append({"name": "redis", "status": "fail", "error": str(e)})
        # Redis is not critical for startup
    
    # Check critical configuration
    config_checks = {
        "jwt_secret": bool(settings.JWT_SECRET_KEY),
        "database_url": bool(settings.DATABASE_URL),
        "environment": settings.ENVIRONMENT in ["development", "staging", "production"]
    }
    
    for check_name, passed in config_checks.items():
        if not passed:
            checks.append({"name": f"config_{check_name}", "status": "fail"})
            all_passed = False
        else:
            checks.append({"name": f"config_{check_name}", "status": "pass"})
    
    response = {
        "ready": all_passed,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if not all_passed:
        return response, status.HTTP_503_SERVICE_UNAVAILABLE
    
    return response


@router.get("/diagnostics")
async def system_diagnostics():
    """
    Detailed system diagnostics for troubleshooting.
    Should be protected in production.
    """
    diagnostics = {
        "timestamp": datetime.utcnow().isoformat(),
        "environment": {
            "name": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "version": settings.APP_VERSION,
            "python_version": os.sys.version
        },
        "process": {
            "pid": os.getpid(),
            "uptime_seconds": time.time() - psutil.Process().create_time(),
            "memory_mb": round(psutil.Process().memory_info().rss / 1024 / 1024, 2),
            "cpu_percent": psutil.Process().cpu_percent(interval=0.1),
            "num_threads": psutil.Process().num_threads()
        },
        "system": {
            "platform": os.sys.platform,
            "cpu_count": psutil.cpu_count(),
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
        }
    }
    
    # Add connection pool diagnostics
    try:
        db = next(get_db())
        engine = db.get_bind()
        if hasattr(engine.pool, 'status'):
            diagnostics["database_pool"] = {
                "size": engine.pool.size(),
                "checked_in": engine.pool.checkedin(),
                "overflow": engine.pool.overflow(),
                "total": engine.pool._created
            }
        db.close()
    except:
        pass
    
    return diagnostics