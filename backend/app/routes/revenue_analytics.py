"""Revenue analytics API endpoints."""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.core.auth import get_current_user
from backend.app.core.authorization import require_permission
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.services.revenue_analytics import RevenueAnalyticsService
from backend.app.services.commission_calculator import CommissionCalculator
from backend.app.core.logger import logger


router = APIRouter(
    prefix="/api/revenue",
    tags=["revenue-analytics"]
)


@router.get("/dashboard")
async def get_revenue_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Get real-time revenue dashboard metrics.
    
    Returns comprehensive revenue metrics including:
    - Today's performance
    - Week/Month/Year to date metrics
    - Top performing partners
    - Booking type distribution
    """
    require_permission(current_user, "revenue:view")
    
    try:
        analytics_service = RevenueAnalyticsService(db)
        dashboard = await analytics_service.get_real_time_dashboard()
        return dashboard
    except Exception as e:
        logger.error(f"Error fetching revenue dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard metrics")


@router.get("/conversion-analytics")
async def get_conversion_analytics(
    start_date: date = Query(..., description="Start date for analytics"),
    end_date: date = Query(..., description="End date for analytics"),
    group_by: str = Query("day", regex="^(day|week|month)$", description="Grouping period"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Get conversion rate analytics for a date range.
    
    Provides detailed conversion metrics grouped by time period and booking type.
    """
    require_permission(current_user, "revenue:view")
    
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")
    
    if (end_date - start_date).days > 365:
        raise HTTPException(status_code=400, detail="Date range cannot exceed 365 days")
    
    try:
        analytics_service = RevenueAnalyticsService(db)
        analytics = await analytics_service.get_conversion_analytics(
            start_date=start_date,
            end_date=end_date,
            group_by=group_by
        )
        return analytics
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching conversion analytics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch conversion analytics")


@router.get("/forecast")
async def get_revenue_forecast(
    days_ahead: int = Query(30, ge=7, le=90, description="Number of days to forecast"),
    confidence_level: float = Query(0.95, ge=0.8, le=0.99, description="Confidence level for forecast"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Get revenue forecast based on historical data.
    
    Uses time series analysis to predict future revenue with confidence intervals.
    """
    require_permission(current_user, "revenue:forecast")
    
    try:
        analytics_service = RevenueAnalyticsService(db)
        forecast = analytics_service.forecast_revenue(
            days_ahead=days_ahead,
            confidence_level=confidence_level
        )
        return forecast
    except Exception as e:
        logger.error(f"Error generating revenue forecast: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate revenue forecast")


@router.get("/partner/{partner_id}/performance")
async def get_partner_performance(
    partner_id: int,
    start_date: date = Query(..., description="Start date for analysis"),
    end_date: date = Query(..., description="End date for analysis"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Get detailed performance metrics for a specific partner.
    
    Includes:
    - Booking and revenue metrics
    - Booking type breakdown
    - Time-based patterns
    - Customer retention metrics
    """
    require_permission(current_user, "revenue:view")
    
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")
    
    try:
        analytics_service = RevenueAnalyticsService(db)
        performance = analytics_service.calculate_partner_performance(
            partner_id=partner_id,
            start_date=start_date,
            end_date=end_date
        )
        return performance
    except Exception as e:
        logger.error(f"Error fetching partner performance: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch partner performance")


@router.get("/commissions/summary")
async def get_commission_summary(
    partner_id: Optional[int] = Query(None, description="Filter by partner ID"),
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Get commission summary for a date range.
    
    Optionally filter by partner to get partner-specific commission data.
    """
    require_permission(current_user, "commission:view")
    
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")
    
    try:
        calculator = CommissionCalculator(db)
        
        if partner_id:
            summary = calculator.get_partner_commission_summary(
                partner_id=partner_id,
                start_date=datetime.combine(start_date, datetime.min.time()),
                end_date=datetime.combine(end_date, datetime.max.time())
            )
            return summary
        else:
            # Get summary for all partners
            from backend.app.models.partner import Partner
            partners = db.query(Partner).filter(Partner.is_active == True).all()
            
            summaries = []
            for partner in partners:
                partner_summary = calculator.get_partner_commission_summary(
                    partner_id=partner.id,
                    start_date=datetime.combine(start_date, datetime.min.time()),
                    end_date=datetime.combine(end_date, datetime.max.time())
                )
                partner_summary["partner_name"] = partner.name
                partner_summary["partner_code"] = partner.partner_code
                summaries.append(partner_summary)
            
            return {
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "partners": summaries
            }
    except Exception as e:
        logger.error(f"Error fetching commission summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch commission summary")


@router.get("/commissions/monthly-share")
async def get_monthly_revenue_share(
    year: int = Query(..., ge=2020, le=2030, description="Year"),
    month: int = Query(..., ge=1, le=12, description="Month"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[Dict]:
    """
    Calculate monthly revenue share for all partners.
    
    Shows gross revenue, commissions, and net revenue for each partner.
    """
    require_permission(current_user, "commission:view")
    
    try:
        calculator = CommissionCalculator(db)
        revenue_shares = calculator.calculate_monthly_revenue_share(
            year=year,
            month=month
        )
        return revenue_shares
    except Exception as e:
        logger.error(f"Error calculating monthly revenue share: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to calculate revenue share")


@router.post("/analytics/update-cache")
async def update_analytics_cache(
    target_date: Optional[date] = Query(None, description="Date to update (defaults to yesterday)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Update pre-calculated analytics cache for a specific date.
    
    This endpoint is typically called by a scheduled job to maintain analytics data.
    """
    require_permission(current_user, "revenue:admin")
    
    if not target_date:
        target_date = date.today() - timedelta(days=1)
    
    try:
        analytics_service = RevenueAnalyticsService(db)
        await analytics_service.update_analytics_cache(target_date)
        return {
            "message": "Analytics cache updated successfully",
            "date": target_date.isoformat()
        }
    except Exception as e:
        logger.error(f"Error updating analytics cache: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update analytics cache")


@router.get("/booking-trends")
async def get_booking_trends(
    period: str = Query("30d", regex="^(7d|14d|30d|90d|1y)$", description="Time period"),
    booking_type: Optional[str] = Query(None, description="Filter by booking type"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Get booking trends over different time periods.
    
    Shows trend data with comparisons to previous periods.
    """
    require_permission(current_user, "revenue:view")
    
    # Calculate date range based on period
    end_date = date.today()
    period_map = {
        "7d": 7,
        "14d": 14,
        "30d": 30,
        "90d": 90,
        "1y": 365
    }
    days = period_map[period]
    start_date = end_date - timedelta(days=days)
    
    try:
        analytics_service = RevenueAnalyticsService(db)
        
        # Get current period metrics
        current_metrics = analytics_service._calculate_period_metrics(start_date, end_date)
        
        # Get previous period metrics for comparison
        prev_start = start_date - timedelta(days=days)
        prev_end = start_date - timedelta(days=1)
        previous_metrics = analytics_service._calculate_period_metrics(prev_start, prev_end)
        
        # Calculate trends
        def calculate_change(current, previous):
            if previous == 0:
                return 100.0 if current > 0 else 0.0
            return ((current - previous) / previous) * 100
        
        trends = {
            "period": period,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "current": current_metrics,
            "previous": previous_metrics,
            "changes": {
                "bookings": {
                    "value": calculate_change(
                        current_metrics["bookings"]["total"],
                        previous_metrics["bookings"]["total"]
                    ),
                    "direction": "up" if current_metrics["bookings"]["total"] > previous_metrics["bookings"]["total"] else "down"
                },
                "revenue": {
                    "value": calculate_change(
                        current_metrics["revenue"]["gross"],
                        previous_metrics["revenue"]["gross"]
                    ),
                    "direction": "up" if current_metrics["revenue"]["gross"] > previous_metrics["revenue"]["gross"] else "down"
                },
                "conversion": {
                    "value": current_metrics["bookings"]["conversion_rate"] - previous_metrics["bookings"]["conversion_rate"],
                    "direction": "up" if current_metrics["bookings"]["conversion_rate"] > previous_metrics["bookings"]["conversion_rate"] else "down"
                }
            }
        }
        
        return trends
    except Exception as e:
        logger.error(f"Error fetching booking trends: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch booking trends")