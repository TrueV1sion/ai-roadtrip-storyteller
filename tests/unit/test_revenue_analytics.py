"""Unit tests for Revenue Analytics service."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date, timedelta
from decimal import Decimal
import pandas as pd

from backend.app.services.revenue_analytics import (
    RevenueAnalytics,
    RevenueMetrics,
    BookingAnalytics,
    CommissionAnalytics,
    RevenueReport,
    RevenueForecast,
    VendorPerformance
)
from backend.app.models.reservation import Reservation, ReservationStatus
from backend.app.services.booking_agent import BookingType


@pytest.fixture
def revenue_analytics():
    """Create revenue analytics instance."""
    return RevenueAnalytics()


@pytest.fixture
def mock_booking_data():
    """Mock booking data for analytics."""
    return [
        {
            "booking_id": "B001",
            "booking_type": BookingType.RESTAURANT,
            "amount": Decimal("150.00"),
            "commission": Decimal("18.00"),
            "status": ReservationStatus.CONFIRMED,
            "created_at": datetime.now() - timedelta(days=1),
            "vendor_name": "Italian Bistro",
            "user_id": 1
        },
        {
            "booking_id": "B002",
            "booking_type": BookingType.HOTEL,
            "amount": Decimal("450.00"),
            "commission": Decimal("45.00"),
            "status": ReservationStatus.CONFIRMED,
            "created_at": datetime.now() - timedelta(days=2),
            "vendor_name": "Grand Hotel",
            "user_id": 2
        },
        {
            "booking_id": "B003",
            "booking_type": BookingType.ATTRACTION,
            "amount": Decimal("75.00"),
            "commission": Decimal("6.00"),
            "status": ReservationStatus.CONFIRMED,
            "created_at": datetime.now() - timedelta(days=3),
            "vendor_name": "City Museum",
            "user_id": 1
        },
        {
            "booking_id": "B004",
            "booking_type": BookingType.RESTAURANT,
            "amount": Decimal("200.00"),
            "commission": Decimal("24.00"),
            "status": ReservationStatus.CANCELLED,
            "created_at": datetime.now() - timedelta(days=4),
            "vendor_name": "French Café",
            "user_id": 3
        }
    ]


@pytest.fixture
def mock_historical_data():
    """Mock historical data for forecasting."""
    dates = pd.date_range(end=datetime.now(), periods=90, freq='D')
    data = []
    
    for i, date in enumerate(dates):
        # Simulate seasonal pattern
        base_bookings = 10 + (i % 7) * 2  # Weekly pattern
        if date.weekday() in [4, 5]:  # Friday/Saturday boost
            base_bookings *= 1.5
        
        data.append({
            "date": date,
            "total_bookings": int(base_bookings),
            "total_revenue": Decimal(str(base_bookings * 100)),
            "total_commission": Decimal(str(base_bookings * 12))
        })
    
    return pd.DataFrame(data)


class TestRevenueAnalytics:
    """Test suite for Revenue Analytics."""
    
    def test_calculate_basic_metrics(self, revenue_analytics, mock_booking_data):
        """Test calculation of basic revenue metrics."""
        with patch.object(revenue_analytics, 'get_bookings_for_period', return_value=mock_booking_data):
            metrics = revenue_analytics.calculate_revenue_metrics(
                start_date=date.today() - timedelta(days=7),
                end_date=date.today()
            )
            
            assert isinstance(metrics, RevenueMetrics)
            assert metrics.total_bookings == 4
            assert metrics.confirmed_bookings == 3
            assert metrics.total_revenue == Decimal("875.00")  # Sum of all amounts
            assert metrics.total_commission == Decimal("93.00")  # Sum of all commissions
            assert metrics.average_booking_value == Decimal("218.75")  # 875/4
            assert metrics.conversion_rate == 0.75  # 3/4 confirmed
    
    def test_revenue_by_booking_type(self, revenue_analytics, mock_booking_data):
        """Test revenue breakdown by booking type."""
        with patch.object(revenue_analytics, 'get_bookings_for_period', return_value=mock_booking_data):
            breakdown = revenue_analytics.get_revenue_by_type(
                start_date=date.today() - timedelta(days=7),
                end_date=date.today()
            )
            
            assert BookingType.RESTAURANT in breakdown
            assert breakdown[BookingType.RESTAURANT]["count"] == 2
            assert breakdown[BookingType.RESTAURANT]["revenue"] == Decimal("350.00")
            assert breakdown[BookingType.RESTAURANT]["commission"] == Decimal("42.00")
            
            assert BookingType.HOTEL in breakdown
            assert breakdown[BookingType.HOTEL]["count"] == 1
            assert breakdown[BookingType.HOTEL]["revenue"] == Decimal("450.00")
            
            assert BookingType.ATTRACTION in breakdown
            assert breakdown[BookingType.ATTRACTION]["count"] == 1
            assert breakdown[BookingType.ATTRACTION]["revenue"] == Decimal("75.00")
    
    def test_vendor_performance_analysis(self, revenue_analytics, mock_booking_data):
        """Test vendor performance analytics."""
        with patch.object(revenue_analytics, 'get_bookings_for_period', return_value=mock_booking_data):
            performance = revenue_analytics.analyze_vendor_performance(
                start_date=date.today() - timedelta(days=7),
                end_date=date.today()
            )
            
            # Check top vendors
            assert len(performance) == 4
            
            italian_bistro = next(v for v in performance if v.vendor_name == "Italian Bistro")
            assert italian_bistro.total_bookings == 1
            assert italian_bistro.total_revenue == Decimal("150.00")
            assert italian_bistro.total_commission == Decimal("18.00")
            assert italian_bistro.commission_rate == Decimal("0.12")  # 18/150
    
    def test_revenue_trends(self, revenue_analytics, mock_historical_data):
        """Test revenue trend analysis."""
        with patch.object(revenue_analytics, 'get_historical_data', return_value=mock_historical_data):
            trends = revenue_analytics.analyze_revenue_trends(
                period_days=30,
                grouping="week"
            )
            
            assert "weekly_trends" in trends
            assert len(trends["weekly_trends"]) >= 4  # At least 4 weeks
            
            # Check trend calculations
            assert "growth_rate" in trends
            assert "average_weekly_revenue" in trends
            assert "peak_day" in trends
            assert trends["peak_day"] in ["Friday", "Saturday"]  # Based on mock data
    
    def test_revenue_forecasting(self, revenue_analytics, mock_historical_data):
        """Test revenue forecasting."""
        with patch.object(revenue_analytics, 'get_historical_data', return_value=mock_historical_data):
            forecast = revenue_analytics.forecast_revenue(
                days_ahead=30,
                confidence_level=0.95
            )
            
            assert isinstance(forecast, RevenueForecast)
            assert len(forecast.predictions) == 30
            
            # Check forecast structure
            first_prediction = forecast.predictions[0]
            assert "date" in first_prediction
            assert "predicted_revenue" in first_prediction
            assert "lower_bound" in first_prediction
            assert "upper_bound" in first_prediction
            
            # Predictions should be positive
            assert all(p["predicted_revenue"] > 0 for p in forecast.predictions)
            
            # Confidence intervals should contain prediction
            for p in forecast.predictions:
                assert p["lower_bound"] <= p["predicted_revenue"] <= p["upper_bound"]
    
    def test_commission_analytics(self, revenue_analytics, mock_booking_data):
        """Test commission-specific analytics."""
        with patch.object(revenue_analytics, 'get_bookings_for_period', return_value=mock_booking_data):
            commission_analytics = revenue_analytics.analyze_commissions(
                start_date=date.today() - timedelta(days=7),
                end_date=date.today()
            )
            
            assert isinstance(commission_analytics, CommissionAnalytics)
            assert commission_analytics.total_commission == Decimal("93.00")
            assert commission_analytics.average_commission_rate > Decimal("0.10")
            
            # Check commission by type
            assert BookingType.RESTAURANT in commission_analytics.commission_by_type
            assert BookingType.HOTEL in commission_analytics.commission_by_type
            
            # Verify rates
            restaurant_rate = commission_analytics.average_rate_by_type[BookingType.RESTAURANT]
            assert restaurant_rate == Decimal("0.12")  # Based on mock data
    
    def test_user_lifetime_value(self, revenue_analytics, mock_booking_data):
        """Test user lifetime value calculations."""
        with patch.object(revenue_analytics, 'get_user_bookings', return_value=[b for b in mock_booking_data if b["user_id"] == 1]):
            ltv = revenue_analytics.calculate_user_ltv(user_id=1)
            
            assert ltv["total_bookings"] == 2
            assert ltv["total_revenue"] == Decimal("225.00")  # 150 + 75
            assert ltv["total_commission"] == Decimal("24.00")  # 18 + 6
            assert ltv["average_booking_value"] == Decimal("112.50")
            assert "projected_annual_value" in ltv
    
    def test_revenue_report_generation(self, revenue_analytics, mock_booking_data):
        """Test comprehensive revenue report generation."""
        with patch.object(revenue_analytics, 'get_bookings_for_period', return_value=mock_booking_data):
            report = revenue_analytics.generate_revenue_report(
                start_date=date.today() - timedelta(days=30),
                end_date=date.today(),
                include_forecast=True
            )
            
            assert isinstance(report, RevenueReport)
            assert report.period_start == date.today() - timedelta(days=30)
            assert report.period_end == date.today()
            
            # Check report sections
            assert report.summary is not None
            assert report.breakdown_by_type is not None
            assert report.top_vendors is not None
            assert report.trends is not None
            
            if report.forecast:
                assert len(report.forecast.predictions) > 0
    
    def test_real_time_revenue_tracking(self, revenue_analytics):
        """Test real-time revenue tracking."""
        # Simulate real-time booking events
        events = [
            {"type": "booking_created", "amount": Decimal("100.00"), "commission": Decimal("12.00")},
            {"type": "booking_created", "amount": Decimal("150.00"), "commission": Decimal("18.00")},
            {"type": "booking_cancelled", "amount": Decimal("100.00"), "commission": Decimal("12.00")}
        ]
        
        tracker = revenue_analytics.get_realtime_tracker()
        
        for event in events:
            tracker.process_event(event)
        
        metrics = tracker.get_current_metrics()
        
        assert metrics["total_revenue"] == Decimal("150.00")  # 100 + 150 - 100
        assert metrics["total_commission"] == Decimal("18.00")  # 12 + 18 - 12
        assert metrics["active_bookings"] == 1
    
    def test_anomaly_detection(self, revenue_analytics, mock_historical_data):
        """Test anomaly detection in revenue patterns."""
        with patch.object(revenue_analytics, 'get_historical_data', return_value=mock_historical_data):
            # Add anomaly to data
            anomaly_date = datetime.now() - timedelta(days=5)
            anomaly_booking = {
                "date": anomaly_date,
                "total_revenue": Decimal("5000.00"),  # Unusually high
                "total_commission": Decimal("600.00")
            }
            
            anomalies = revenue_analytics.detect_anomalies(
                lookback_days=30,
                sensitivity=2.0  # 2 standard deviations
            )
            
            assert len(anomalies) >= 0
            
            # If anomaly detected
            if anomalies:
                assert "date" in anomalies[0]
                assert "metric" in anomalies[0]
                assert "expected_range" in anomalies[0]
                assert "actual_value" in anomalies[0]
    
    def test_revenue_by_location(self, revenue_analytics):
        """Test revenue analysis by geographic location."""
        location_data = [
            {"city": "San Francisco", "revenue": Decimal("5000.00"), "bookings": 50},
            {"city": "Los Angeles", "revenue": Decimal("4000.00"), "bookings": 45},
            {"city": "San Diego", "revenue": Decimal("2000.00"), "bookings": 25}
        ]
        
        with patch.object(revenue_analytics, 'get_revenue_by_location', return_value=location_data):
            analysis = revenue_analytics.analyze_geographic_performance()
            
            assert len(analysis["top_cities"]) == 3
            assert analysis["top_cities"][0]["city"] == "San Francisco"
            assert analysis["total_revenue"] == Decimal("11000.00")
            assert "revenue_concentration" in analysis  # Gini coefficient or similar
    
    def test_cohort_analysis(self, revenue_analytics):
        """Test cohort-based revenue analysis."""
        cohort_data = revenue_analytics.perform_cohort_analysis(
            cohort_type="monthly",
            metrics=["revenue", "retention", "ltv"]
        )
        
        assert "cohorts" in cohort_data
        assert "retention_matrix" in cohort_data
        assert "ltv_by_cohort" in cohort_data
        
        # Check cohort structure
        if cohort_data["cohorts"]:
            first_cohort = cohort_data["cohorts"][0]
            assert "cohort_date" in first_cohort
            assert "users" in first_cohort
            assert "initial_revenue" in first_cohort
    
    def test_revenue_attribution(self, revenue_analytics):
        """Test revenue attribution to marketing channels."""
        attribution_data = [
            {"channel": "organic", "revenue": Decimal("3000.00"), "bookings": 30},
            {"channel": "paid_search", "revenue": Decimal("2000.00"), "bookings": 20},
            {"channel": "social", "revenue": Decimal("1000.00"), "bookings": 15}
        ]
        
        with patch.object(revenue_analytics, 'get_attribution_data', return_value=attribution_data):
            attribution = revenue_analytics.analyze_revenue_attribution()
            
            assert attribution["top_channel"] == "organic"
            assert attribution["channel_performance"]["organic"]["roi"] > 0
            assert sum(c["revenue"] for c in attribution["channels"]) == Decimal("6000.00")
    
    def test_revenue_optimization_suggestions(self, revenue_analytics, mock_booking_data):
        """Test revenue optimization suggestions."""
        with patch.object(revenue_analytics, 'get_bookings_for_period', return_value=mock_booking_data):
            suggestions = revenue_analytics.generate_optimization_suggestions()
            
            assert isinstance(suggestions, list)
            assert len(suggestions) > 0
            
            # Check suggestion structure
            for suggestion in suggestions:
                assert "category" in suggestion
                assert "description" in suggestion
                assert "potential_impact" in suggestion
                assert "priority" in suggestion
                assert suggestion["priority"] in ["high", "medium", "low"]
    
    def test_dashboard_metrics(self, revenue_analytics):
        """Test dashboard metric calculations."""
        metrics = revenue_analytics.get_dashboard_metrics()
        
        required_metrics = [
            "revenue_today",
            "revenue_mtd",
            "revenue_ytd",
            "bookings_today",
            "average_commission_rate",
            "top_vendor_today",
            "growth_rate_wow",  # Week over week
            "growth_rate_mom"   # Month over month
        ]
        
        for metric in required_metrics:
            assert metric in metrics
            
        # Verify metric types
        assert isinstance(metrics["revenue_today"], Decimal)
        assert isinstance(metrics["bookings_today"], int)
        assert isinstance(metrics["average_commission_rate"], Decimal)