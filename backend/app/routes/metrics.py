"""
Prometheus Metrics Endpoint
Exposes metrics for scraping
"""

from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse

from app.monitoring.metrics_v2 import metrics_v2
from app.core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics() -> Response:
    """
    Prometheus metrics endpoint.
    Returns metrics in Prometheus text format.
    """
    try:
        # Generate metrics
        metrics_data = metrics_v2.generate_metrics()
        
        # Return with appropriate content type
        return Response(
            content=metrics_data,
            media_type=metrics_v2.get_content_type(),
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        return Response(
            content=f"# Error generating metrics: {str(e)}\n",
            media_type="text/plain",
            status_code=500
        )


@router.get("/metrics/health")
async def metrics_health():
    """
    Health check for metrics system.
    """
    return {
        "status": "healthy",
        "multiprocess_mode": bool(metrics_v2.multiprocess_mode),
        "registry_type": "global" if metrics_v2.multiprocess_mode else "custom"
    }