from fastapi import APIRouter, HTTPException, Query, Response
from typing import Dict, Optional
from datetime import datetime
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.monitoring.metrics import metrics_collector
from app.core.cache import cache_manager
from app.core.rate_limiter import rate_limiter
from app.core.logger import get_logger


router = APIRouter()
logger = get_logger(__name__)


@router.get("/metrics", tags=["Monitoring"])
async def get_prometheus_metrics() -> Response:
    """
    Get metrics in Prometheus format.
    
    Returns metrics that can be scraped by Prometheus.
    """
    try:
        metrics_data = generate_latest()
        return Response(
            content=metrics_data,
            media_type=CONTENT_TYPE_LATEST
        )
    except Exception as e:
        logger.error(f"Error generating Prometheus metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error generating metrics"
        )


@router.get("/metrics/summary", tags=["Monitoring"])
async def get_metrics_summary(
    window_minutes: int = Query(5, ge=1, le=60),
    include_clients: bool = False
) -> Dict:
    """
    Get service metrics summary for the specified time window.
    
    Args:
        window_minutes: Time window in minutes (1-60)
        include_clients: Whether to include per-client statistics
    """
    try:
        return metrics_collector.get_summary(
            minutes=window_minutes,
            include_client_stats=include_clients
        )
    except Exception as e:
        logger.error(f"Error fetching metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error fetching metrics"
        )


@router.get("/errors", tags=["Monitoring"])
async def get_errors(
    hours: int = Query(24, ge=1, le=168)  # Up to 1 week
) -> Dict:
    """Get error summary for the specified time window."""
    try:
        return {
            "errors": metrics_collector.get_error_summary(hours=hours)
        }
    except Exception as e:
        logger.error(f"Error fetching error summary: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error fetching error summary"
        )


@router.get("/health", tags=["Monitoring"])
async def health_check() -> Dict:
    """
    Service health check endpoint.
    Verifies connectivity to Redis and other dependencies.
    """
    try:
        # Check Redis connection
        redis_ok = False
        try:
            await cache_manager.set(
                "health_check",
                "ok",
                expire=None
            )
            redis_ok = True
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")

        # Get rate limiter status
        rate_limit_stats = {
            "total_clients": len(rate_limiter.client_usage),
            "active_tokens": rate_limiter.tokens
        }

        # Get basic metrics
        metrics = metrics_collector.get_summary(minutes=5)
        
        return {
            "status": "healthy" if redis_ok else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "redis": "ok" if redis_ok else "error",
                "rate_limiter": "ok"
            },
            "rate_limits": rate_limit_stats,
            "metrics_summary": {
                "requests_5m": metrics["request_count"],
                "errors_5m": metrics["error_count"],
                "cache_hit_rate": metrics["cache_hit_rate"]
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Health check failed"
        )


@router.get("/cache/stats", tags=["Monitoring"])
async def get_cache_stats() -> Dict:
    """Get cache statistics."""
    try:
        metrics = metrics_collector.get_summary(minutes=60)
        return {
            "hit_rate_1h": metrics["cache_hit_rate"],
            "status": "ok" if metrics["cache_hit_rate"] > 0.5 else "warning",
            "size": len(cache_manager._offline_cache)
        }
    except Exception as e:
        logger.error(f"Error fetching cache stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error fetching cache statistics"
        )


@router.get("/rate-limits", tags=["Monitoring"])
async def get_rate_limit_stats() -> Dict:
    """Get rate limiting statistics."""
    try:
        client_stats = {}
        for client_id, usage in rate_limiter.client_usage.items():
            client_stats[client_id] = {
                "requests_24h": usage["count"],
                "first_request": usage["first_request"].isoformat(),
                "status": (
                    "warning"
                    if usage["count"] > 2000
                    else "ok"
                )
            }

        return {
            "global_rate": rate_limiter.rate,
            "burst_capacity": rate_limiter.burst,
            "current_tokens": rate_limiter.tokens,
            "clients": client_stats
        }
    except Exception as e:
        logger.error(f"Error fetching rate limit stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Error fetching rate limit statistics"
        ) 