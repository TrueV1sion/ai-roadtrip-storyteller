"""Revenue analytics service for business intelligence."""

from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from sqlalchemy import and_, func, extract, case
from sqlalchemy.orm import Session
import numpy as np
from scipy import stats

from app.models.booking import Booking, BookingStatus
from app.core.enums import BookingType
from backend.app.models.commission import Commission, CommissionStatus
from backend.app.models.partner import Partner
from backend.app.models.revenue_analytics import RevenueAnalytics
from backend.app.core.logger import logger
from backend.app.core.cache import cache_manager


class RevenueAnalyticsService:
    """Service for revenue analytics and forecasting."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_real_time_dashboard(self) -> Dict:
        """Get real-time dashboard metrics."""
        cache_key = "revenue:dashboard:realtime"
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached
        
        today = date.today()
        start_of_day = datetime.combine(today, datetime.min.time())
        
        # Today's metrics
        today_metrics = self._calculate_daily_metrics(start_of_day)
        
        # Last 7 days trend
        week_ago = today - timedelta(days=7)
        week_metrics = self._calculate_period_metrics(week_ago, today)
        
        # Month to date
        start_of_month = date(today.year, today.month, 1)
        mtd_metrics = self._calculate_period_metrics(start_of_month, today)
        
        # Year to date
        start_of_year = date(today.year, 1, 1)
        ytd_metrics = self._calculate_period_metrics(start_of_year, today)
        
        # Active bookings
        active_bookings = self.db.query(func.count(Booking.id)).filter(
            Booking.booking_status.in_([
                BookingStatus.PENDING,
                BookingStatus.CONFIRMED
            ])
        ).scalar()
        
        dashboard = {
            "last_updated": datetime.utcnow().isoformat(),
            "today": today_metrics,
            "week": week_metrics,
            "month_to_date": mtd_metrics,
            "year_to_date": ytd_metrics,
            "active_bookings": active_bookings,
            "top_partners": self._get_top_partners(5),
            "booking_type_distribution": self._get_booking_type_distribution()
        }
        
        # Cache for 1 minute
        await cache_manager.set(cache_key, dashboard, ttl=60)
        
        return dashboard
    
    def _calculate_daily_metrics(self, date: datetime) -> Dict:
        """Calculate metrics for a specific day."""
        end_date = date + timedelta(days=1)
        
        metrics = self.db.query(
            func.count(Booking.id).label('total_bookings'),
            func.sum(case(
                (Booking.booking_status == BookingStatus.COMPLETED, 1),
                else_=0
            )).label('completed_bookings'),
            func.sum(case(
                (Booking.booking_status == BookingStatus.CANCELLED, 1),
                else_=0
            )).label('cancelled_bookings'),
            func.sum(Booking.gross_amount).label('gross_revenue'),
            func.sum(Booking.net_amount).label('net_revenue')
        ).filter(
            and_(
                Booking.booking_date >= date,
                Booking.booking_date < end_date
            )
        ).first()
        
        commission_total = self.db.query(
            func.sum(Commission.commission_amount)
        ).join(
            Booking
        ).filter(
            and_(
                Booking.booking_date >= date,
                Booking.booking_date < end_date
            )
        ).scalar() or Decimal("0")
        
        total_bookings = metrics.total_bookings or 0
        completed = metrics.completed_bookings or 0
        
        return {
            "bookings": {
                "total": total_bookings,
                "completed": completed,
                "cancelled": metrics.cancelled_bookings or 0,
                "conversion_rate": float(completed / total_bookings) if total_bookings > 0 else 0
            },
            "revenue": {
                "gross": float(metrics.gross_revenue or 0),
                "net": float(metrics.net_revenue or 0),
                "commission": float(commission_total),
                "average_booking_value": float(
                    (metrics.gross_revenue or 0) / total_bookings
                ) if total_bookings > 0 else 0
            }
        }
    
    def _calculate_period_metrics(self, start_date: date, end_date: date) -> Dict:
        """Calculate metrics for a date range."""
        metrics = self.db.query(
            func.count(Booking.id).label('total_bookings'),
            func.sum(case(
                (Booking.booking_status == BookingStatus.COMPLETED, 1),
                else_=0
            )).label('completed_bookings'),
            func.sum(Booking.gross_amount).label('gross_revenue'),
            func.sum(Booking.net_amount).label('net_revenue')
        ).filter(
            and_(
                Booking.booking_date >= start_date,
                Booking.booking_date <= end_date
            )
        ).first()
        
        commission_total = self.db.query(
            func.sum(Commission.commission_amount)
        ).join(
            Booking
        ).filter(
            and_(
                Booking.booking_date >= start_date,
                Booking.booking_date <= end_date
            )
        ).scalar() or Decimal("0")
        
        total_bookings = metrics.total_bookings or 0
        completed = metrics.completed_bookings or 0
        
        # Calculate growth vs previous period
        period_length = (end_date - start_date).days
        prev_start = start_date - timedelta(days=period_length)
        prev_end = start_date - timedelta(days=1)
        
        prev_revenue = self.db.query(
            func.sum(Booking.gross_amount)
        ).filter(
            and_(
                Booking.booking_date >= prev_start,
                Booking.booking_date <= prev_end
            )
        ).scalar() or Decimal("0")
        
        current_revenue = metrics.gross_revenue or Decimal("0")
        growth_rate = float(
            ((current_revenue - prev_revenue) / prev_revenue) * 100
        ) if prev_revenue > 0 else 0
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": period_length
            },
            "bookings": {
                "total": total_bookings,
                "completed": completed,
                "conversion_rate": float(completed / total_bookings) if total_bookings > 0 else 0
            },
            "revenue": {
                "gross": float(current_revenue),
                "net": float(metrics.net_revenue or 0),
                "commission": float(commission_total),
                "growth_rate": growth_rate
            }
        }
    
    def _get_top_partners(self, limit: int = 5) -> List[Dict]:
        """Get top performing partners."""
        thirty_days_ago = date.today() - timedelta(days=30)
        
        results = self.db.query(
            Partner.name,
            Partner.partner_code,
            func.count(Booking.id).label('booking_count'),
            func.sum(Booking.gross_amount).label('revenue')
        ).join(
            Booking
        ).filter(
            and_(
                Booking.booking_date >= thirty_days_ago,
                Booking.booking_status == BookingStatus.COMPLETED
            )
        ).group_by(
            Partner.name,
            Partner.partner_code
        ).order_by(
            func.sum(Booking.gross_amount).desc()
        ).limit(limit).all()
        
        return [
            {
                "name": r.name,
                "code": r.partner_code,
                "bookings": r.booking_count,
                "revenue": float(r.revenue)
            }
            for r in results
        ]
    
    def _get_booking_type_distribution(self) -> Dict[str, Dict]:
        """Get booking distribution by type."""
        thirty_days_ago = date.today() - timedelta(days=30)
        
        results = self.db.query(
            Booking.booking_type,
            func.count(Booking.id).label('count'),
            func.sum(Booking.gross_amount).label('revenue')
        ).filter(
            and_(
                Booking.booking_date >= thirty_days_ago,
                Booking.booking_status == BookingStatus.COMPLETED
            )
        ).group_by(Booking.booking_type).all()
        
        distribution = {}
        for booking_type, count, revenue in results:
            distribution[booking_type.value] = {
                "count": count,
                "revenue": float(revenue)
            }
        
        return distribution
    
    async def get_conversion_analytics(
        self,
        start_date: date,
        end_date: date,
        group_by: str = "day"
    ) -> Dict:
        """Get conversion rate analytics."""
        cache_key = f"revenue:conversion:{start_date}:{end_date}:{group_by}"
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached
        
        # Determine grouping
        if group_by == "day":
            date_trunc = func.date_trunc('day', Booking.booking_date)
        elif group_by == "week":
            date_trunc = func.date_trunc('week', Booking.booking_date)
        elif group_by == "month":
            date_trunc = func.date_trunc('month', Booking.booking_date)
        else:
            raise ValueError(f"Invalid group_by value: {group_by}")
        
        # Query conversion data
        results = self.db.query(
            date_trunc.label('period'),
            Booking.booking_type,
            func.count(Booking.id).label('total'),
            func.sum(case(
                (Booking.booking_status == BookingStatus.COMPLETED, 1),
                else_=0
            )).label('completed'),
            func.sum(case(
                (Booking.booking_status == BookingStatus.CANCELLED, 1),
                else_=0
            )).label('cancelled')
        ).filter(
            and_(
                Booking.booking_date >= start_date,
                Booking.booking_date <= end_date
            )
        ).group_by(
            date_trunc,
            Booking.booking_type
        ).order_by(date_trunc).all()
        
        # Process results
        conversion_data = {}
        for period, booking_type, total, completed, cancelled in results:
            period_str = period.strftime('%Y-%m-%d')
            if period_str not in conversion_data:
                conversion_data[period_str] = {}
            
            conversion_rate = float(completed / total) if total > 0 else 0
            cancellation_rate = float(cancelled / total) if total > 0 else 0
            
            conversion_data[period_str][booking_type.value] = {
                "total": total,
                "completed": completed,
                "cancelled": cancelled,
                "conversion_rate": conversion_rate,
                "cancellation_rate": cancellation_rate
            }
        
        analytics = {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "group_by": group_by
            },
            "data": conversion_data,
            "summary": self._calculate_conversion_summary(results)
        }
        
        # Cache for 1 hour
        await cache_manager.set(cache_key, analytics, ttl=3600)
        
        return analytics
    
    def _calculate_conversion_summary(self, results) -> Dict:
        """Calculate overall conversion summary."""
        total_bookings = sum(r.total for r in results)
        total_completed = sum(r.completed for r in results)
        total_cancelled = sum(r.cancelled for r in results)
        
        by_type = {}
        for r in results:
            booking_type = r.booking_type.value
            if booking_type not in by_type:
                by_type[booking_type] = {
                    "total": 0,
                    "completed": 0,
                    "cancelled": 0
                }
            by_type[booking_type]["total"] += r.total
            by_type[booking_type]["completed"] += r.completed
            by_type[booking_type]["cancelled"] += r.cancelled
        
        # Calculate rates by type
        for booking_type, data in by_type.items():
            data["conversion_rate"] = float(
                data["completed"] / data["total"]
            ) if data["total"] > 0 else 0
            data["cancellation_rate"] = float(
                data["cancelled"] / data["total"]
            ) if data["total"] > 0 else 0
        
        return {
            "overall": {
                "total": total_bookings,
                "completed": total_completed,
                "cancelled": total_cancelled,
                "conversion_rate": float(
                    total_completed / total_bookings
                ) if total_bookings > 0 else 0,
                "cancellation_rate": float(
                    total_cancelled / total_bookings
                ) if total_bookings > 0 else 0
            },
            "by_type": by_type
        }
    
    def forecast_revenue(
        self,
        days_ahead: int = 30,
        confidence_level: float = 0.95
    ) -> Dict:
        """Forecast revenue using time series analysis."""
        # Get historical data (last 90 days)
        end_date = date.today()
        start_date = end_date - timedelta(days=90)
        
        daily_revenue = self.db.query(
            func.date_trunc('day', Booking.booking_date).label('date'),
            func.sum(Booking.gross_amount).label('revenue')
        ).filter(
            and_(
                Booking.booking_date >= start_date,
                Booking.booking_date <= end_date,
                Booking.booking_status == BookingStatus.COMPLETED
            )
        ).group_by(
            func.date_trunc('day', Booking.booking_date)
        ).order_by('date').all()
        
        if len(daily_revenue) < 30:
            return {
                "error": "Insufficient historical data for forecasting"
            }
        
        # Extract revenue values
        revenues = [float(r.revenue) for r in daily_revenue]
        dates = [r.date for r in daily_revenue]
        
        # Simple linear regression for trend
        x = np.arange(len(revenues))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, revenues)
        
        # Calculate forecast
        forecast_x = np.arange(len(revenues), len(revenues) + days_ahead)
        forecast_values = slope * forecast_x + intercept
        
        # Calculate confidence intervals
        residuals = revenues - (slope * x + intercept)
        residual_std = np.std(residuals)
        
        z_score = stats.norm.ppf((1 + confidence_level) / 2)
        margin_of_error = z_score * residual_std
        
        # Generate forecast dates
        last_date = dates[-1]
        forecast_dates = [
            last_date + timedelta(days=i+1)
            for i in range(days_ahead)
        ]
        
        # Prepare forecast data
        forecast_data = []
        for i, (date, value) in enumerate(zip(forecast_dates, forecast_values)):
            forecast_data.append({
                "date": date.strftime('%Y-%m-%d'),
                "forecast": float(value),
                "lower_bound": float(value - margin_of_error),
                "upper_bound": float(value + margin_of_error)
            })
        
        # Calculate total forecast
        total_forecast = float(np.sum(forecast_values))
        total_lower = float(np.sum(forecast_values - margin_of_error))
        total_upper = float(np.sum(forecast_values + margin_of_error))
        
        return {
            "forecast_period": {
                "start": forecast_dates[0].strftime('%Y-%m-%d'),
                "end": forecast_dates[-1].strftime('%Y-%m-%d'),
                "days": days_ahead
            },
            "model_metrics": {
                "r_squared": float(r_value ** 2),
                "trend_slope": float(slope),
                "confidence_level": confidence_level
            },
            "forecast": {
                "daily": forecast_data,
                "total": {
                    "forecast": total_forecast,
                    "lower_bound": total_lower,
                    "upper_bound": total_upper
                }
            },
            "historical_average": {
                "daily": float(np.mean(revenues)),
                "weekly": float(np.mean(revenues) * 7),
                "monthly": float(np.mean(revenues) * 30)
            }
        }
    
    def calculate_partner_performance(
        self,
        partner_id: int,
        start_date: date,
        end_date: date
    ) -> Dict:
        """Calculate detailed performance metrics for a partner."""
        # Basic metrics
        metrics = self.db.query(
            func.count(Booking.id).label('total_bookings'),
            func.sum(case(
                (Booking.booking_status == BookingStatus.COMPLETED, 1),
                else_=0
            )).label('completed_bookings'),
            func.sum(Booking.gross_amount).label('gross_revenue'),
            func.avg(Booking.gross_amount).label('avg_booking_value')
        ).filter(
            and_(
                Booking.partner_id == partner_id,
                Booking.booking_date >= start_date,
                Booking.booking_date <= end_date
            )
        ).first()
        
        # Commission metrics
        commission_data = self.db.query(
            func.sum(Commission.commission_amount).label('total_commission'),
            func.avg(Commission.commission_rate).label('avg_commission_rate')
        ).join(
            Booking
        ).filter(
            and_(
                Booking.partner_id == partner_id,
                Booking.booking_date >= start_date,
                Booking.booking_date <= end_date
            )
        ).first()
        
        # Booking type breakdown
        type_breakdown = self.db.query(
            Booking.booking_type,
            func.count(Booking.id).label('count'),
            func.sum(Booking.gross_amount).label('revenue')
        ).filter(
            and_(
                Booking.partner_id == partner_id,
                Booking.booking_date >= start_date,
                Booking.booking_date <= end_date,
                Booking.booking_status == BookingStatus.COMPLETED
            )
        ).group_by(Booking.booking_type).all()
        
        # Time-based patterns (by day of week)
        dow_pattern = self.db.query(
            extract('dow', Booking.booking_date).label('day_of_week'),
            func.count(Booking.id).label('count'),
            func.avg(Booking.gross_amount).label('avg_value')
        ).filter(
            and_(
                Booking.partner_id == partner_id,
                Booking.booking_date >= start_date,
                Booking.booking_date <= end_date,
                Booking.booking_status == BookingStatus.COMPLETED
            )
        ).group_by('day_of_week').order_by('day_of_week').all()
        
        # Customer retention (repeat bookings)
        repeat_customers = self.db.query(
            func.count(func.distinct(Booking.user_id))
        ).filter(
            and_(
                Booking.partner_id == partner_id,
                Booking.booking_date >= start_date,
                Booking.booking_date <= end_date
            )
        ).group_by(Booking.user_id).having(
            func.count(Booking.id) > 1
        ).count()
        
        total_customers = self.db.query(
            func.count(func.distinct(Booking.user_id))
        ).filter(
            and_(
                Booking.partner_id == partner_id,
                Booking.booking_date >= start_date,
                Booking.booking_date <= end_date
            )
        ).scalar()
        
        return {
            "partner_id": partner_id,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "bookings": {
                "total": metrics.total_bookings or 0,
                "completed": metrics.completed_bookings or 0,
                "conversion_rate": float(
                    (metrics.completed_bookings or 0) / (metrics.total_bookings or 1)
                )
            },
            "revenue": {
                "gross": float(metrics.gross_revenue or 0),
                "average_booking_value": float(metrics.avg_booking_value or 0),
                "total_commission": float(commission_data.total_commission or 0),
                "average_commission_rate": float(commission_data.avg_commission_rate or 0)
            },
            "booking_types": [
                {
                    "type": bt.value,
                    "count": count,
                    "revenue": float(revenue)
                }
                for bt, count, revenue in type_breakdown
            ],
            "patterns": {
                "by_day_of_week": [
                    {
                        "day": int(dow),
                        "bookings": count,
                        "avg_value": float(avg_value)
                    }
                    for dow, count, avg_value in dow_pattern
                ]
            },
            "customer_metrics": {
                "total_customers": total_customers or 0,
                "repeat_customers": repeat_customers,
                "retention_rate": float(
                    repeat_customers / (total_customers or 1)
                )
            }
        }
    
    async def update_analytics_cache(self, date: date):
        """Update pre-calculated analytics for a date."""
        # Calculate metrics for each partner and booking type
        results = self.db.query(
            Booking.partner_id,
            Booking.booking_type,
            func.count(Booking.id).label('total_bookings'),
            func.sum(case(
                (Booking.booking_status == BookingStatus.COMPLETED, 1),
                else_=0
            )).label('completed_bookings'),
            func.sum(case(
                (Booking.booking_status == BookingStatus.CANCELLED, 1),
                else_=0
            )).label('cancelled_bookings'),
            func.sum(Booking.gross_amount).label('gross_revenue'),
            func.sum(Booking.net_amount).label('net_revenue')
        ).filter(
            func.date(Booking.booking_date) == date
        ).group_by(
            Booking.partner_id,
            Booking.booking_type
        ).all()
        
        for result in results:
            # Get commission total
            commission_total = self.db.query(
                func.sum(Commission.commission_amount)
            ).join(
                Booking
            ).filter(
                and_(
                    func.date(Booking.booking_date) == date,
                    Booking.partner_id == result.partner_id,
                    Booking.booking_type == result.booking_type
                )
            ).scalar() or Decimal("0")
            
            # Calculate metrics
            total = result.total_bookings or 0
            completed = result.completed_bookings or 0
            gross = result.gross_revenue or Decimal("0")
            
            # Check if record exists
            existing = self.db.query(RevenueAnalytics).filter(
                and_(
                    RevenueAnalytics.date == date,
                    RevenueAnalytics.partner_id == result.partner_id,
                    RevenueAnalytics.booking_type == result.booking_type
                )
            ).first()
            
            if existing:
                # Update existing record
                existing.total_bookings = total
                existing.completed_bookings = completed
                existing.cancelled_bookings = result.cancelled_bookings or 0
                existing.gross_revenue = gross
                existing.net_revenue = result.net_revenue or Decimal("0")
                existing.total_commission = commission_total
                existing.conversion_rate = Decimal(str(completed / total)) if total > 0 else Decimal("0")
                existing.average_booking_value = gross / total if total > 0 else Decimal("0")
            else:
                # Create new record
                analytics = RevenueAnalytics(
                    date=date,
                    partner_id=result.partner_id,
                    booking_type=result.booking_type,
                    total_bookings=total,
                    completed_bookings=completed,
                    cancelled_bookings=result.cancelled_bookings or 0,
                    gross_revenue=gross,
                    net_revenue=result.net_revenue or Decimal("0"),
                    total_commission=commission_total,
                    conversion_rate=Decimal(str(completed / total)) if total > 0 else Decimal("0"),
                    average_booking_value=gross / total if total > 0 else Decimal("0")
                )
                self.db.add(analytics)
        
        self.db.commit()
        logger.info(f"Updated analytics cache for {date}")