"""
Health Check Routes V2 - Production Ready
Supports horizontal scaling and graceful shutdown
"""

from fastapi import APIRouter, Response, status
from fastapi.responses import JSONResponse

from app.core.health_check_v2 import health_checker, HealthStatus
from app.core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/health/v2", tags=["health-v2"])


@router.get("/live")
async def liveness_probe(response: Response):
    """
    Kubernetes liveness probe endpoint.
    Returns 200 if the worker is alive, 503 if shutting down.
    """
    try:
        result = await health_checker.liveness_check()
        
        if result["status"] == "shutdown":
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return result
        
        return result
        
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "error", "message": str(e)}


@router.get("/ready")
async def readiness_probe(response: Response):
    """
    Kubernetes readiness probe endpoint.
    Returns 200 if ready to accept traffic, 503 if not ready.
    """
    try:
        result = await health_checker.readiness_check()
        
        if not result["ready"]:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        
        return result
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "ready": False,
            "status": "error",
            "message": str(e)
        }


@router.get("/status")
async def health_status(response: Response):
    """
    Comprehensive health status endpoint.
    Returns detailed health information for all components.
    """
    try:
        result = await health_checker.get_health_status()
        
        # Set appropriate status code
        if result["status"] == HealthStatus.UNHEALTHY.value:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif result["status"] == HealthStatus.DEGRADED.value:
            response.status_code = status.HTTP_200_OK  # Still operational
        elif result["status"] == HealthStatus.SHUTDOWN.value:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        
        return result
        
    except Exception as e:
        logger.error(f"Health status check failed: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "error",
            "message": str(e),
            "worker_id": health_checker.worker_id
        }


@router.get("/worker")
async def worker_info():
    """
    Get information about the current worker.
    Useful for debugging load balancing.
    """
    return {
        "worker_id": health_checker.worker_id,
        "uptime_seconds": (
            health_checker.graceful_shutdown.shutdown_time or 
            health_checker.startup_time
        ).timestamp(),
        "checks_performed": health_checker.checks_performed,
        "active_requests": health_checker.graceful_shutdown.active_requests,
        "accepting_requests": health_checker.graceful_shutdown.should_accept_requests(),
        "shutting_down": health_checker.graceful_shutdown.shutdown_initiated
    }


@router.post("/shutdown/graceful")
async def initiate_graceful_shutdown(
    response: Response,
    timeout: int = 30
):
    """
    Initiate graceful shutdown of this worker.
    Used for rolling updates and scaling operations.
    """
    if health_checker.graceful_shutdown.shutdown_initiated:
        return {
            "status": "already_initiated",
            "shutdown_time": health_checker.graceful_shutdown.shutdown_time.isoformat()
        }
    
    # Update timeout if provided
    health_checker.graceful_shutdown.shutdown_timeout = timeout
    
    # Initiate shutdown
    health_checker.graceful_shutdown.initiate_shutdown()
    
    response.status_code = status.HTTP_202_ACCEPTED
    return {
        "status": "shutdown_initiated",
        "timeout_seconds": timeout,
        "worker_id": health_checker.worker_id
    }


@router.get("/metrics/worker")
async def worker_metrics():
    """
    Get Prometheus-compatible metrics for this worker.
    """
    metrics = []
    
    # Worker uptime
    uptime = (datetime.now() - health_checker.startup_time).total_seconds()
    metrics.append(f'worker_uptime_seconds{{worker_id="{health_checker.worker_id}"}} {uptime}')
    
    # Active requests
    metrics.append(
        f'worker_active_requests{{worker_id="{health_checker.worker_id}"}} '
        f'{health_checker.graceful_shutdown.active_requests}'
    )
    
    # Health checks performed
    metrics.append(
        f'worker_health_checks_total{{worker_id="{health_checker.worker_id}"}} '
        f'{health_checker.checks_performed}'
    )
    
    # Component status
    for component, status in health_checker.component_status.items():
        status_value = 1 if status["status"] == HealthStatus.HEALTHY else 0
        metrics.append(
            f'component_health{{component="{component}",worker_id="{health_checker.worker_id}"}} '
            f'{status_value}'
        )
    
    return Response(
        content="\n".join(metrics),
        media_type="text/plain"
    )


# Import datetime for metrics
from datetime import datetime