"""Unit tests for the Commission Calculator."""

import pytest
from decimal import Decimal
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch

from backend.app.services.commission_calculator import (
    CommissionCalculator,
    CommissionRate,
    CommissionTier,
    BookingType,
    VendorCommission,
    CommissionReport
)
from backend.app.core.config import get_settings


@pytest.fixture
def commission_calculator():
    """Create a commission calculator instance."""
    return CommissionCalculator()


@pytest.fixture
def mock_vendor_rates():
    """Mock vendor-specific commission rates."""
    return {
        "Premium Restaurant": VendorCommission(
            vendor_name="Premium Restaurant",
            base_rate=Decimal("0.15"),
            tier_rates={
                CommissionTier.BRONZE: Decimal("0.15"),
                CommissionTier.SILVER: Decimal("0.18"),
                CommissionTier.GOLD: Decimal("0.20"),
                CommissionTier.PLATINUM: Decimal("0.25")
            },
            volume_bonus=Decimal("0.02")
        ),
        "Budget Hotel": VendorCommission(
            vendor_name="Budget Hotel",
            base_rate=Decimal("0.08"),
            tier_rates={
                CommissionTier.BRONZE: Decimal("0.08"),
                CommissionTier.SILVER: Decimal("0.10"),
                CommissionTier.GOLD: Decimal("0.12"),
                CommissionTier.PLATINUM: Decimal("0.15")
            },
            volume_bonus=Decimal("0.01")
        ),
        "City Museum": VendorCommission(
            vendor_name="City Museum",
            base_rate=Decimal("0.10"),
            tier_rates={
                CommissionTier.BRONZE: Decimal("0.10"),
                CommissionTier.SILVER: Decimal("0.12"),
                CommissionTier.GOLD: Decimal("0.15"),
                CommissionTier.PLATINUM: Decimal("0.18")
            },
            volume_bonus=Decimal("0.015")
        )
    }


class TestCommissionCalculator:
    """Test suite for Commission Calculator."""
    
    def test_default_commission_rates(self, commission_calculator):
        """Test default commission rates by booking type."""
        rates = {
            BookingType.RESTAURANT: Decimal("0.12"),
            BookingType.HOTEL: Decimal("0.10"),
            BookingType.ATTRACTION: Decimal("0.08"),
            BookingType.TRANSPORTATION: Decimal("0.05"),
            BookingType.EXPERIENCE: Decimal("0.15")
        }
        
        for booking_type, expected_rate in rates.items():
            rate = commission_calculator.get_base_rate(booking_type)
            assert rate == expected_rate
    
    def test_calculate_basic_commission(self, commission_calculator):
        """Test basic commission calculation without tiers."""
        test_cases = [
            (BookingType.RESTAURANT, Decimal("100.00"), Decimal("12.00")),
            (BookingType.HOTEL, Decimal("500.00"), Decimal("50.00")),
            (BookingType.ATTRACTION, Decimal("75.00"), Decimal("6.00")),
            (BookingType.TRANSPORTATION, Decimal("50.00"), Decimal("2.50")),
            (BookingType.EXPERIENCE, Decimal("200.00"), Decimal("30.00"))
        ]
        
        for booking_type, amount, expected_commission in test_cases:
            commission = commission_calculator.calculate_commission(
                booking_type=booking_type,
                booking_amount=amount
            )
            assert commission == expected_commission
    
    def test_vendor_specific_rates(self, commission_calculator, mock_vendor_rates):
        """Test vendor-specific commission rates."""
        with patch.object(commission_calculator, 'vendor_rates', mock_vendor_rates):
            # Premium Restaurant
            commission = commission_calculator.calculate_commission(
                booking_type=BookingType.RESTAURANT,
                booking_amount=Decimal("100.00"),
                vendor_name="Premium Restaurant"
            )
            assert commission == Decimal("15.00")  # 15% rate
            
            # Budget Hotel
            commission = commission_calculator.calculate_commission(
                booking_type=BookingType.HOTEL,
                booking_amount=Decimal("200.00"),
                vendor_name="Budget Hotel"
            )
            assert commission == Decimal("16.00")  # 8% rate
    
    def test_volume_based_tiers(self, commission_calculator):
        """Test volume-based commission tiers."""
        # Mock volume history
        with patch.object(commission_calculator, 'get_monthly_volume', return_value=Decimal("15000.00")):
            tier = commission_calculator.get_volume_tier(user_id=1)
            assert tier == CommissionTier.GOLD
            
            # Calculate commission with tier bonus
            commission = commission_calculator.calculate_commission(
                booking_type=BookingType.RESTAURANT,
                booking_amount=Decimal("100.00"),
                user_id=1
            )
            # Base 12% + Gold tier bonus (e.g., 3%) = 15%
            assert commission >= Decimal("12.00")
    
    def test_promotional_rates(self, commission_calculator):
        """Test promotional commission rates."""
        promo_rate = CommissionRate(
            booking_type=BookingType.RESTAURANT,
            base_rate=Decimal("0.20"),
            effective_from=datetime.now() - timedelta(days=1),
            effective_to=datetime.now() + timedelta(days=1),
            is_promotional=True,
            promo_code="SUMMER20"
        )
        
        with patch.object(commission_calculator, 'get_promotional_rate', return_value=promo_rate):
            commission = commission_calculator.calculate_commission(
                booking_type=BookingType.RESTAURANT,
                booking_amount=Decimal("100.00"),
                promo_code="SUMMER20"
            )
            assert commission == Decimal("20.00")  # 20% promotional rate
    
    def test_bulk_booking_discount(self, commission_calculator):
        """Test commission calculation for bulk bookings."""
        # Large group booking should have different commission structure
        commission = commission_calculator.calculate_commission(
            booking_type=BookingType.RESTAURANT,
            booking_amount=Decimal("1000.00"),
            booking_details={"party_size": 20}
        )
        
        # Commission should consider bulk discount
        standard_commission = Decimal("1000.00") * Decimal("0.12")
        assert commission <= standard_commission
    
    def test_commission_caps(self, commission_calculator):
        """Test maximum commission caps."""
        # Very large booking amount
        commission = commission_calculator.calculate_commission(
            booking_type=BookingType.HOTEL,
            booking_amount=Decimal("10000.00")
        )
        
        # Check if commission respects any caps
        max_commission = commission_calculator.get_max_commission(BookingType.HOTEL)
        if max_commission:
            assert commission <= max_commission
    
    def test_commission_report_generation(self, commission_calculator):
        """Test commission report generation."""
        # Mock booking data
        with patch.object(commission_calculator, 'get_bookings_for_period') as mock_bookings:
            mock_bookings.return_value = [
                {
                    "booking_id": "B1",
                    "booking_type": BookingType.RESTAURANT,
                    "amount": Decimal("100.00"),
                    "commission": Decimal("12.00"),
                    "date": datetime.now()
                },
                {
                    "booking_id": "B2",
                    "booking_type": BookingType.HOTEL,
                    "amount": Decimal("500.00"),
                    "commission": Decimal("50.00"),
                    "date": datetime.now()
                }
            ]
            
            report = commission_calculator.generate_commission_report(
                start_date=date.today() - timedelta(days=30),
                end_date=date.today()
            )
            
            assert isinstance(report, CommissionReport)
            assert report.total_bookings == 2
            assert report.total_booking_amount == Decimal("600.00")
            assert report.total_commission == Decimal("62.00")
            assert len(report.breakdown_by_type) == 2
    
    def test_commission_by_time_of_day(self, commission_calculator):
        """Test time-based commission adjustments."""
        # Peak hours might have different rates
        peak_hour = datetime.now().replace(hour=19)  # 7 PM
        off_peak = datetime.now().replace(hour=15)  # 3 PM
        
        with patch('backend.app.services.commission_calculator.datetime') as mock_datetime:
            # Peak hour commission
            mock_datetime.now.return_value = peak_hour
            peak_commission = commission_calculator.calculate_commission(
                booking_type=BookingType.RESTAURANT,
                booking_amount=Decimal("100.00"),
                booking_time=peak_hour
            )
            
            # Off-peak commission
            mock_datetime.now.return_value = off_peak
            off_peak_commission = commission_calculator.calculate_commission(
                booking_type=BookingType.RESTAURANT,
                booking_amount=Decimal("100.00"),
                booking_time=off_peak
            )
            
            # Peak hours might have higher commission
            assert peak_commission >= off_peak_commission
    
    def test_commission_adjustments_for_cancellations(self, commission_calculator):
        """Test commission adjustments for cancelled bookings."""
        original_commission = Decimal("20.00")
        
        # Full cancellation
        adjusted = commission_calculator.adjust_commission_for_cancellation(
            original_commission=original_commission,
            cancellation_type="full",
            hours_before_booking=48
        )
        assert adjusted == Decimal("0.00")  # Full refund
        
        # Partial cancellation (less than 24 hours)
        adjusted = commission_calculator.adjust_commission_for_cancellation(
            original_commission=original_commission,
            cancellation_type="partial",
            hours_before_booking=12
        )
        assert adjusted < original_commission  # Partial refund
        assert adjusted > Decimal("0.00")
    
    def test_multi_currency_support(self, commission_calculator):
        """Test commission calculation with different currencies."""
        # USD booking
        usd_commission = commission_calculator.calculate_commission(
            booking_type=BookingType.HOTEL,
            booking_amount=Decimal("100.00"),
            currency="USD"
        )
        
        # EUR booking (might have different rate or conversion)
        eur_commission = commission_calculator.calculate_commission(
            booking_type=BookingType.HOTEL,
            booking_amount=Decimal("100.00"),
            currency="EUR"
        )
        
        # Commissions should be calculated appropriately for each currency
        assert usd_commission > Decimal("0.00")
        assert eur_commission > Decimal("0.00")
    
    def test_commission_validation(self, commission_calculator):
        """Test commission calculation validation."""
        # Negative amount should raise error
        with pytest.raises(ValueError):
            commission_calculator.calculate_commission(
                booking_type=BookingType.RESTAURANT,
                booking_amount=Decimal("-100.00")
            )
        
        # Zero amount should return zero commission
        commission = commission_calculator.calculate_commission(
            booking_type=BookingType.RESTAURANT,
            booking_amount=Decimal("0.00")
        )
        assert commission == Decimal("0.00")
        
        # Invalid booking type should raise error
        with pytest.raises(ValueError):
            commission_calculator.calculate_commission(
                booking_type="INVALID_TYPE",
                booking_amount=Decimal("100.00")
            )
    
    def test_commission_rounding(self, commission_calculator):
        """Test proper rounding of commission amounts."""
        # Test various amounts that might cause rounding issues
        test_amounts = [
            Decimal("33.33"),
            Decimal("66.67"),
            Decimal("99.99"),
            Decimal("101.01")
        ]
        
        for amount in test_amounts:
            commission = commission_calculator.calculate_commission(
                booking_type=BookingType.RESTAURANT,
                booking_amount=amount
            )
            # Commission should be rounded to 2 decimal places
            assert commission == commission.quantize(Decimal("0.01"))
    
    def test_commission_audit_trail(self, commission_calculator):
        """Test commission calculation audit trail."""
        commission_result = commission_calculator.calculate_commission_with_details(
            booking_type=BookingType.RESTAURANT,
            booking_amount=Decimal("100.00"),
            vendor_name="Test Restaurant",
            user_id=1
        )
        
        assert "commission_amount" in commission_result
        assert "base_rate" in commission_result
        assert "applied_rate" in commission_result
        assert "calculation_method" in commission_result
        assert "timestamp" in commission_result
        assert commission_result["commission_amount"] == Decimal("12.00")
    
    def test_partner_revenue_share(self, commission_calculator):
        """Test revenue sharing with partners."""
        # Some vendors might have revenue sharing agreements
        commission_details = commission_calculator.calculate_commission_with_revenue_share(
            booking_type=BookingType.HOTEL,
            booking_amount=Decimal("1000.00"),
            vendor_name="Partner Hotel",
            revenue_share_percentage=Decimal("0.30")  # 30% to partner
        )
        
        assert "total_commission" in commission_details
        assert "platform_share" in commission_details
        assert "partner_share" in commission_details
        
        total = commission_details["total_commission"]
        platform = commission_details["platform_share"]
        partner = commission_details["partner_share"]
        
        assert platform + partner == total
        assert partner == total * Decimal("0.30")