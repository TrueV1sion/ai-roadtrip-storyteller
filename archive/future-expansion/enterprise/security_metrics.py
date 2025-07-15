"""
Security metrics and reporting endpoints.
"""

from typing import Optional, Literal
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
import csv
import io

from app.core.auth import get_current_admin_user
from app.core.logger import get_logger
from app.models.user import User
from app.monitoring.security_metrics import security_metrics

logger = get_logger(__name__)
router = APIRouter()


@router.get("/security-metrics/summary")
async def get_metrics_summary(
    time_range: Literal["1h", "6h", "24h", "7d", "30d"] = Query("24h"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get security metrics summary for specified time range.
    """
    try:
        # Convert time range to timedelta
        range_map = {
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30)
        }
        
        delta = range_map.get(time_range)
        if not delta:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid time range"
            )
        
        summary = await security_metrics.get_metrics_summary(delta)
        
        return {
            "status": "success",
            "data": summary
        }
        
    except Exception as e:
        logger.error(f"Error getting metrics summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get metrics summary"
        )


@router.get("/security-metrics/time-series")
async def get_time_series_data(
    metric: str = Query(..., description="Metric key (e.g., security_events.total_5min)"),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    resolution: Literal["1m", "5m", "15m", "1h"] = Query("5m"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get time series data for a specific metric.
    """
    try:
        # Default time range if not specified
        if not end_time:
            end_time = datetime.utcnow()
        if not start_time:
            start_time = end_time - timedelta(hours=24)
        
        # Get time series data
        if metric not in security_metrics.time_series_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Metric '{metric}' not found"
            )
        
        # Filter by time range
        data = [
            d for d in security_metrics.time_series_data[metric]
            if start_time <= d["timestamp"] <= end_time
        ]
        
        # Apply resolution (simple sampling for now)
        resolution_map = {"1m": 1, "5m": 5, "15m": 15, "1h": 60}
        sample_interval = resolution_map[resolution]
        
        if sample_interval > 1:
            sampled_data = []
            for i in range(0, len(data), sample_interval):
                if i < len(data):
                    sampled_data.append(data[i])
            data = sampled_data
        
        return {
            "status": "success",
            "data": {
                "metric": metric,
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "resolution": resolution,
                "data_points": data,
                "count": len(data)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting time series data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get time series data"
        )


@router.post("/security-metrics/report")
async def generate_security_report(
    report_type: Literal["hourly", "daily", "weekly", "monthly", "custom"] = Query("daily"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    format: Literal["json", "pdf", "csv"] = Query("json"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Generate comprehensive security report.
    """
    try:
        # Validate custom range
        custom_range = None
        if report_type == "custom":
            if not start_date or not end_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Start and end dates required for custom reports"
                )
            custom_range = (start_date, end_date)
        
        # Generate report
        report = await security_metrics.generate_security_report(
            report_type=report_type,
            custom_range=custom_range
        )
        
        # Format response based on requested format
        if format == "json":
            return {
                "status": "success",
                "data": report
            }
        elif format == "csv":
            # Convert to CSV
            csv_buffer = io.StringIO()
            csv_writer = csv.writer(csv_buffer)
            
            # Write executive summary
            csv_writer.writerow(["Security Report"])
            csv_writer.writerow(["Generated", report["metadata"]["generated_at"]])
            csv_writer.writerow(["Period", report["metadata"]["report_type"]])
            csv_writer.writerow([])
            
            # Write key metrics
            csv_writer.writerow(["Key Metrics"])
            summary = report["executive_summary"]
            csv_writer.writerow(["Security Posture", summary["security_posture"]])
            csv_writer.writerow(["Risk Level", summary["risk_level"]])
            csv_writer.writerow([])
            
            # Write findings
            csv_writer.writerow(["Key Findings"])
            for finding in summary["key_findings"]:
                csv_writer.writerow([finding])
            
            # Return CSV file
            csv_buffer.seek(0)
            return StreamingResponse(
                io.BytesIO(csv_buffer.getvalue().encode()),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=security_report_{report_type}.csv"
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Format '{format}' not implemented"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report"
        )


@router.get("/security-metrics/real-time")
async def get_real_time_metrics(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get real-time security metrics for dashboard.
    """
    try:
        # Get latest metrics
        if not security_metrics.metrics_buffer:
            return {
                "status": "success",
                "data": {
                    "message": "No metrics available yet"
                }
            }
        
        latest = security_metrics.metrics_buffer[-1]
        
        # Calculate deltas from previous
        deltas = {}
        if len(security_metrics.metrics_buffer) > 1:
            previous = security_metrics.metrics_buffer[-2]
            
            # Calculate event rate change
            current_rate = latest["security_events"]["rate_per_minute"]
            previous_rate = previous["security_events"]["rate_per_minute"]
            deltas["event_rate_change"] = current_rate - previous_rate
            
            # Calculate threat change
            current_threats = latest["threats"]["active_threats"]
            previous_threats = previous["threats"]["active_threats"]
            deltas["threat_change"] = current_threats - previous_threats
        
        return {
            "status": "success",
            "data": {
                "timestamp": latest["timestamp"].isoformat(),
                "current_metrics": {
                    "event_rate": latest["security_events"]["rate_per_minute"],
                    "active_threats": latest["threats"]["active_threats"],
                    "threat_score": latest["threats"]["threat_score"],
                    "blocked_ips": latest["threats"]["blocked_ips"],
                    "auth_success_rate": latest["authentication"]["success_rate"],
                    "active_sessions": latest["sessions"]["active_sessions"],
                    "response_time_ms": latest["performance"]["avg_response_time_ms"]
                },
                "deltas": deltas,
                "alerts": await _get_active_alerts()
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting real-time metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get real-time metrics"
        )


@router.get("/security-metrics/trends")
async def get_security_trends(
    metrics: list[str] = Query(
        default=["security_events.total_5min", "threats.active_threats"],
        description="List of metrics to analyze trends"
    ),
    time_range: Literal["1h", "6h", "24h", "7d"] = Query("24h"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get trend analysis for specified metrics.
    """
    try:
        # Convert time range
        range_map = {
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7)
        }
        
        delta = range_map[time_range]
        cutoff = datetime.utcnow() - delta
        
        trends = {}
        
        for metric in metrics:
            if metric in security_metrics.time_series_data:
                # Get data points after cutoff
                data_points = [
                    d for d in security_metrics.time_series_data[metric]
                    if d["timestamp"] > cutoff
                ]
                
                if len(data_points) >= 2:
                    # Calculate trend
                    trend = security_metrics._calculate_trend(data_points)
                    trends[metric] = trend
                else:
                    trends[metric] = {
                        "direction": "insufficient_data",
                        "data_points": len(data_points)
                    }
            else:
                trends[metric] = {"error": "metric_not_found"}
        
        return {
            "status": "success",
            "data": {
                "time_range": time_range,
                "trends": trends
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting trends: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get trends"
        )


@router.get("/security-metrics/benchmarks")
async def get_security_benchmarks(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get security metrics compared to benchmarks.
    """
    try:
        # Get current metrics
        current = await security_metrics.get_metrics_summary(timedelta(hours=24))
        
        # Define industry benchmarks
        benchmarks = {
            "auth_success_rate": {
                "industry_avg": 95.0,
                "best_practice": 98.0,
                "current": current["authentication"]["avg_success_rate"]
            },
            "threat_score": {
                "industry_avg": 15.0,
                "best_practice": 5.0,
                "current": current["threats"]["avg_threat_score"]
            },
            "response_time_ms": {
                "industry_avg": 100.0,
                "best_practice": 50.0,
                "current": current["performance"]["avg_response_time_ms"]
            },
            "2fa_usage": {
                "industry_avg": 40.0,
                "best_practice": 80.0,
                "current": current["authentication"]["avg_2fa_usage"]
            }
        }
        
        # Calculate performance vs benchmarks
        performance = {}
        for metric, values in benchmarks.items():
            current_val = values["current"]
            industry_avg = values["industry_avg"]
            
            # For some metrics, lower is better
            if metric in ["threat_score", "response_time_ms"]:
                performance_vs_industry = (
                    (industry_avg - current_val) / industry_avg * 100
                    if industry_avg > 0 else 0
                )
            else:
                performance_vs_industry = (
                    (current_val - industry_avg) / industry_avg * 100
                    if industry_avg > 0 else 0
                )
            
            performance[metric] = {
                **values,
                "vs_industry": performance_vs_industry,
                "status": _get_benchmark_status(current_val, values)
            }
        
        return {
            "status": "success",
            "data": {
                "benchmarks": performance,
                "overall_rating": _calculate_overall_rating(performance)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting benchmarks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get benchmarks"
        )


async def _get_active_alerts() -> List[Dict]:
    """Get currently active security alerts."""
    # This would integrate with the alerting system
    from app.monitoring.security_monitor import security_monitor
    
    # Get recent critical events
    events = await security_monitor.get_events(
        start_time=datetime.utcnow() - timedelta(minutes=5),
        end_time=datetime.utcnow(),
        filters={"severity": "CRITICAL"}
    )
    
    return [
        {
            "id": event.get("id"),
            "type": event.get("event_type"),
            "message": event.get("details", {}).get("description", "Security alert"),
            "timestamp": event.get("timestamp")
        }
        for event in events[:5]  # Limit to 5 most recent
    ]


def _get_benchmark_status(current: float, benchmark: Dict) -> str:
    """Determine status compared to benchmarks."""
    if "threat_score" in benchmark or "response_time" in benchmark:
        # Lower is better
        if current <= benchmark["best_practice"]:
            return "excellent"
        elif current <= benchmark["industry_avg"]:
            return "good"
        else:
            return "needs_improvement"
    else:
        # Higher is better
        if current >= benchmark["best_practice"]:
            return "excellent"
        elif current >= benchmark["industry_avg"]:
            return "good"
        else:
            return "needs_improvement"


def _calculate_overall_rating(performance: Dict) -> Dict:
    """Calculate overall security rating."""
    statuses = [p["status"] for p in performance.values()]
    
    excellent_count = statuses.count("excellent")
    good_count = statuses.count("good")
    needs_improvement = statuses.count("needs_improvement")
    
    if excellent_count >= len(statuses) * 0.75:
        rating = "A+"
        description = "Excellent security posture"
    elif excellent_count + good_count >= len(statuses) * 0.75:
        rating = "A"
        description = "Strong security posture"
    elif good_count >= len(statuses) * 0.5:
        rating = "B"
        description = "Good security posture"
    else:
        rating = "C"
        description = "Security improvements needed"
    
    return {
        "rating": rating,
        "description": description,
        "breakdown": {
            "excellent": excellent_count,
            "good": good_count,
            "needs_improvement": needs_improvement
        }
    }