"""
Production Health Check System V2
Supports horizontal scaling and graceful shutdown
"""

import asyncio
import os
import signal
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum
import psutil
import aioredis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db
from app.core.cache import cache_manager
from app.core.logger import get_logger

logger = get_logger(__name__)


class HealthStatus(str, Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    SHUTDOWN = "shutdown"


class GracefulShutdown:
    """Manages graceful shutdown for horizontal scaling."""
    
    def __init__(self):
        self.shutdown_initiated = False
        self.shutdown_time: Optional[datetime] = None
        self.active_requests = 0
        self.shutdown_timeout = 30  # seconds
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, self._handle_sigterm)
        signal.signal(signal.SIGINT, self._handle_sigint)
    
    def _handle_sigterm(self, signum, frame):
        """Handle SIGTERM for graceful shutdown."""
        logger.info("SIGTERM received, initiating graceful shutdown")
        self.initiate_shutdown()
    
    def _handle_sigint(self, signum, frame):
        """Handle SIGINT for immediate shutdown."""
        logger.warning("SIGINT received, forcing shutdown")
        os._exit(1)
    
    def initiate_shutdown(self):
        """Start graceful shutdown process."""
        if not self.shutdown_initiated:
            self.shutdown_initiated = True
            self.shutdown_time = datetime.now()
            logger.info(f"Graceful shutdown initiated, waiting up to {self.shutdown_timeout}s")
    
    def increment_request(self):
        """Track active request."""
        self.active_requests += 1
    
    def decrement_request(self):
        """Track completed request."""
        self.active_requests = max(0, self.active_requests - 1)
    
    def should_accept_requests(self) -> bool:
        """Check if new requests should be accepted."""
        return not self.shutdown_initiated
    
    def can_shutdown(self) -> bool:
        """Check if shutdown can proceed."""
        if not self.shutdown_initiated:
            return False
        
        # Check timeout
        if self.shutdown_time:
            elapsed = (datetime.now() - self.shutdown_time).total_seconds()
            if elapsed > self.shutdown_timeout:
                logger.warning(f"Shutdown timeout reached with {self.active_requests} active requests")
                return True
        
        # Check active requests
        if self.active_requests == 0:
            logger.info("All requests completed, ready for shutdown")
            return True
        
        return False


class HealthChecker:
    """Advanced health checking for horizontally scaled deployment."""
    
    def __init__(self):
        self.startup_time = datetime.now()
        self.graceful_shutdown = GracefulShutdown()
        self.worker_id = os.getpid()
        self.checks_performed = 0
        self.last_check_time: Optional[datetime] = None
        self.component_status: Dict[str, Dict[str, Any]] = {}
    
    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity and performance."""
        start_time = time.time()
        status = HealthStatus.HEALTHY
        details = {}
        
        try:
            async with get_db() as db:
                # Simple connectivity check
                result = await db.execute(text("SELECT 1"))
                
                # Check connection pool stats
                from app.core.database import engine
                pool = engine.pool
                
                details = {
                    "connected": True,
                    "response_time_ms": (time.time() - start_time) * 1000,
                    "pool_size": pool.size(),
                    "checked_out_connections": pool.checked_out(),
                    "overflow": pool.overflow(),
                    "worker_id": self.worker_id
                }
                
                # Determine health based on pool usage
                pool_usage = pool.checked_out() / pool.size() if pool.size() > 0 else 0
                if pool_usage > 0.9:
                    status = HealthStatus.UNHEALTHY
                    details["warning"] = "Connection pool nearly exhausted"
                elif pool_usage > 0.7:
                    status = HealthStatus.DEGRADED
                    details["warning"] = "High connection pool usage"
                
        except Exception as e:
            status = HealthStatus.UNHEALTHY
            details = {
                "connected": False,
                "error": str(e),
                "response_time_ms": (time.time() - start_time) * 1000
            }
        
        return {
            "status": status,
            "details": details
        }
    
    async def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity and performance."""
        start_time = time.time()
        status = HealthStatus.HEALTHY
        details = {}
        
        try:
            # Test Redis connectivity
            redis_client = cache_manager.redis_client
            if redis_client and hasattr(redis_client, 'client'):
                await redis_client.client.ping()
                
                # Get Redis info
                info = await redis_client.client.info()
                
                details = {
                    "connected": True,
                    "response_time_ms": (time.time() - start_time) * 1000,
                    "used_memory_mb": info.get('used_memory', 0) / 1024 / 1024,
                    "connected_clients": info.get('connected_clients', 0),
                    "worker_id": self.worker_id
                }
                
                # Check memory usage
                max_memory = info.get('maxmemory', 0)
                if max_memory > 0:
                    memory_usage = info.get('used_memory', 0) / max_memory
                    if memory_usage > 0.9:
                        status = HealthStatus.DEGRADED
                        details["warning"] = "High Redis memory usage"
            else:
                status = HealthStatus.DEGRADED
                details = {
                    "connected": False,
                    "warning": "Redis client not initialized"
                }
                
        except Exception as e:
            status = HealthStatus.UNHEALTHY
            details = {
                "connected": False,
                "error": str(e),
                "response_time_ms": (time.time() - start_time) * 1000
            }
        
        return {
            "status": status,
            "details": details
        }
    
    async def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage."""
        status = HealthStatus.HEALTHY
        
        try:
            # Get process info
            process = psutil.Process()
            
            # System-wide metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            # Process-specific metrics
            process_memory = process.memory_info()
            process_cpu = process.cpu_percent(interval=0.1)
            
            details = {
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available_mb": memory.available / 1024 / 1024
                },
                "process": {
                    "pid": self.worker_id,
                    "cpu_percent": process_cpu,
                    "memory_mb": process_memory.rss / 1024 / 1024,
                    "threads": process.num_threads(),
                    "connections": len(process.connections()),
                    "open_files": len(process.open_files())
                }
            }
            
            # Determine health based on resource usage
            if cpu_percent > 90 or memory.percent > 90:
                status = HealthStatus.UNHEALTHY
                details["warning"] = "Critical resource usage"
            elif cpu_percent > 70 or memory.percent > 70:
                status = HealthStatus.DEGRADED
                details["warning"] = "High resource usage"
            
        except Exception as e:
            status = HealthStatus.DEGRADED
            details = {"error": str(e)}
        
        return {
            "status": status,
            "details": details
        }
    
    async def check_worker_health(self) -> Dict[str, Any]:
        """Check worker-specific health metrics."""
        uptime = (datetime.now() - self.startup_time).total_seconds()
        
        details = {
            "worker_id": self.worker_id,
            "uptime_seconds": uptime,
            "checks_performed": self.checks_performed,
            "last_check": self.last_check_time.isoformat() if self.last_check_time else None,
            "active_requests": self.graceful_shutdown.active_requests,
            "accepting_requests": self.graceful_shutdown.should_accept_requests()
        }
        
        # Check if worker is shutting down
        if self.graceful_shutdown.shutdown_initiated:
            return {
                "status": HealthStatus.SHUTDOWN,
                "details": {
                    **details,
                    "shutdown_initiated": True,
                    "shutdown_time": self.graceful_shutdown.shutdown_time.isoformat()
                }
            }
        
        # Worker is healthy if it's been up for at least 10 seconds
        status = HealthStatus.HEALTHY if uptime > 10 else HealthStatus.DEGRADED
        
        return {
            "status": status,
            "details": details
        }
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status."""
        self.checks_performed += 1
        self.last_check_time = datetime.now()
        
        # Run all health checks concurrently
        results = await asyncio.gather(
            self.check_worker_health(),
            self.check_database(),
            self.check_redis(),
            self.check_system_resources(),
            return_exceptions=True
        )
        
        # Process results
        worker_health = results[0] if not isinstance(results[0], Exception) else {"status": HealthStatus.UNHEALTHY, "details": {"error": str(results[0])}}
        db_health = results[1] if not isinstance(results[1], Exception) else {"status": HealthStatus.UNHEALTHY, "details": {"error": str(results[1])}}
        redis_health = results[2] if not isinstance(results[2], Exception) else {"status": HealthStatus.UNHEALTHY, "details": {"error": str(results[2])}}
        system_health = results[3] if not isinstance(results[3], Exception) else {"status": HealthStatus.UNHEALTHY, "details": {"error": str(results[3])}}
        
        # Store component status
        self.component_status = {
            "worker": worker_health,
            "database": db_health,
            "redis": redis_health,
            "system": system_health
        }
        
        # Determine overall status
        statuses = [
            worker_health["status"],
            db_health["status"],
            redis_health["status"],
            system_health["status"]
        ]
        
        if HealthStatus.SHUTDOWN in statuses:
            overall_status = HealthStatus.SHUTDOWN
        elif HealthStatus.UNHEALTHY in statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.now().isoformat(),
            "worker_id": self.worker_id,
            "components": {
                name: {
                    "status": health["status"].value,
                    **health["details"]
                }
                for name, health in self.component_status.items()
            }
        }
    
    async def liveness_check(self) -> Dict[str, Any]:
        """Simple liveness check for load balancer."""
        # Check if we should accept new requests
        if not self.graceful_shutdown.should_accept_requests():
            return {
                "status": "shutdown",
                "message": "Worker shutting down"
            }
        
        return {
            "status": "alive",
            "worker_id": self.worker_id,
            "timestamp": datetime.now().isoformat()
        }
    
    async def readiness_check(self) -> Dict[str, Any]:
        """Readiness check for load balancer."""
        # Quick checks only
        if not self.graceful_shutdown.should_accept_requests():
            return {
                "ready": False,
                "status": "shutdown",
                "message": "Worker shutting down"
            }
        
        # Check critical components
        try:
            # Quick DB check
            async with get_db() as db:
                await db.execute(text("SELECT 1"))
            
            # Quick Redis check
            if cache_manager.redis_client:
                await cache_manager.redis_client.client.ping()
            
            return {
                "ready": True,
                "status": "ready",
                "worker_id": self.worker_id
            }
            
        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            return {
                "ready": False,
                "status": "not_ready",
                "error": str(e)
            }


# Global health checker instance
health_checker = HealthChecker()


# Middleware for request tracking
class RequestTrackingMiddleware:
    """Track active requests for graceful shutdown."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Track request start
            health_checker.graceful_shutdown.increment_request()
            
            try:
                await self.app(scope, receive, send)
            finally:
                # Track request completion
                health_checker.graceful_shutdown.decrement_request()
                
                # Check if we can shutdown
                if health_checker.graceful_shutdown.can_shutdown():
                    logger.info("Graceful shutdown complete, exiting")
                    os._exit(0)
        else:
            await self.app(scope, receive, send)


# Export components
__all__ = [
    'health_checker',
    'HealthStatus',
    'GracefulShutdown',
    'RequestTrackingMiddleware'
]