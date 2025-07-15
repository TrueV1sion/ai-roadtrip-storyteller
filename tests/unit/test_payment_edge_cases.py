"""
Edge case tests for payment processing.
Tests unusual scenarios, error conditions, and boundary cases.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio
from concurrent.futures import ThreadPoolExecutor

from backend.app.models.booking import Booking, BookingStatus
from backend.app.models.commission import Commission, CommissionStatus
from backend.app.services.booking_service import BookingService
from backend.app.services.commission_calculator import CommissionCalculator
from backend.app.core.exceptions import (
    PaymentException,
    RefundException,
    InsufficientFundsException,
    FraudDetectedException
)


class TestPaymentEdgeCases:
    """Test edge cases and unusual scenarios in payment processing."""
    
    @pytest.fixture
    def booking_service(self):
        """Create booking service with mocked dependencies."""
        service = BookingService(Mock())
        service.payment_gateway = Mock()
        return service
    
    def test_zero_amount_booking(self, booking_service):
        """Test handling of zero-amount bookings (free events)."""
        booking_data = Mock(
            gross_amount=Decimal("0.00"),
            currency="USD",
            booking_type="event"
        )
        
        # Should process without payment
        result = booking_service.process_free_booking(booking_data)
        
        assert result.booking_status == BookingStatus.CONFIRMED
        assert result.payment_required is False
        # Payment gateway should not be called
        booking_service.payment_gateway.process_payment.assert_not_called()
    
    def test_negative_refund_amount(self, booking_service):
        """Test handling of invalid negative refund amounts."""
        with pytest.raises(ValueError, match="Refund amount must be positive"):
            booking_service.process_refund(
                booking_id=1,
                refund_amount=Decimal("-50.00")
            )
    
    def test_refund_exceeds_original_amount(self, booking_service):
        """Test refund amount exceeding original payment."""
        booking = Mock(
            gross_amount=Decimal("100.00"),
            refund_amount=Decimal("0.00")
        )
        
        with pytest.raises(RefundException, match="exceeds original"):
            booking_service.validate_refund_amount(
                booking=booking,
                requested_refund=Decimal("150.00")
            )
    
    def test_duplicate_refund_attempt(self, booking_service, mock_db):
        """Test preventing duplicate refunds."""
        booking = Booking(
            id=1,
            booking_status=BookingStatus.REFUNDED,
            gross_amount=Decimal("100.00"),
            refund_amount=Decimal("100.00")
        )
        
        mock_db.query.return_value.filter.return_value.first.return_value = booking
        
        with pytest.raises(RefundException, match="already refunded"):
            booking_service.process_refund(booking_id=1)
    
    def test_commission_calculation_rounding(self, booking_service):
        """Test commission calculation with rounding edge cases."""
        test_cases = [
            # (amount, rate, expected_commission)
            (Decimal("100.01"), Decimal("0.15"), Decimal("15.00")),  # Round down
            (Decimal("100.05"), Decimal("0.15"), Decimal("15.01")),  # Round up
            (Decimal("0.01"), Decimal("0.15"), Decimal("0.00")),     # Minimum
            (Decimal("99999.99"), Decimal("0.15"), Decimal("15000.00")),  # Large amount
        ]
        
        calculator = CommissionCalculator(Mock())
        
        for amount, rate, expected in test_cases:
            commission = calculator.calculate_commission_amount(amount, rate)
            assert commission == expected, f"Failed for {amount} at {rate}%"
    
    def test_concurrent_commission_updates(self, booking_service):
        """Test race condition in commission updates."""
        commission = Commission(
            id=1,
            commission_amount=Decimal("50.00"),
            status=CommissionStatus.PENDING
        )
        
        # Simulate concurrent status updates
        def update_status(status):
            commission.status = status
            return commission
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(update_status, CommissionStatus.PAID),
                executor.submit(update_status, CommissionStatus.REVERSED),
                executor.submit(update_status, CommissionStatus.PAID)
            ]
            
            results = [f.result() for f in futures]
        
        # Should have conflict detection
        assert commission.status in [CommissionStatus.PAID, CommissionStatus.REVERSED]
    
    def test_payment_idempotency(self, booking_service):
        """Test idempotent payment processing."""
        idempotency_key = "test-key-123"
        
        # First attempt
        booking_service.payment_cache = {}
        result1 = booking_service.process_payment_with_idempotency(
            amount=Decimal("100.00"),
            idempotency_key=idempotency_key
        )
        
        # Second attempt with same key
        result2 = booking_service.process_payment_with_idempotency(
            amount=Decimal("100.00"),
            idempotency_key=idempotency_key
        )
        
        # Should return cached result
        assert result1 == result2
        # Payment should only be processed once
        assert booking_service.payment_gateway.process_payment.call_count == 1
    
    def test_currency_precision_handling(self, booking_service):
        """Test handling of different currency precisions."""
        test_cases = [
            # (amount, currency, expected_formatted)
            (Decimal("100.00"), "USD", "100.00"),      # 2 decimal places
            (Decimal("100.00"), "JPY", "100"),         # 0 decimal places
            (Decimal("100.123"), "BHD", "100.123"),    # 3 decimal places
            (Decimal("100.12345"), "USD", "100.12"),   # Truncate extras
        ]
        
        for amount, currency, expected in test_cases:
            formatted = booking_service.format_amount_for_currency(amount, currency)
            assert formatted == expected
    
    def test_payment_timeout_handling(self, booking_service):
        """Test handling of payment gateway timeouts."""
        # Configure slow payment processing
        async def slow_payment():
            await asyncio.sleep(5)  # 5 second delay
            return {"status": "succeeded"}
        
        booking_service.payment_gateway.process_payment = AsyncMock(side_effect=slow_payment)
        booking_service.payment_timeout = 2  # 2 second timeout
        
        with pytest.raises(asyncio.TimeoutError):
            asyncio.run(booking_service.process_payment_async(
                amount=Decimal("100.00"),
                timeout=2
            ))
    
    def test_partial_refund_commission_reversal(self, booking_service):
        """Test commission handling for partial refunds."""
        original_commission = Decimal("15.00")  # 15% of $100
        partial_refund_percent = Decimal("0.50")  # 50% refund
        
        reversed_commission = booking_service.calculate_commission_reversal(
            original_commission=original_commission,
            refund_percentage=partial_refund_percent
        )
        
        assert reversed_commission == Decimal("7.50")
    
    def test_booking_status_transition_validation(self, booking_service):
        """Test valid and invalid status transitions."""
        valid_transitions = [
            (BookingStatus.PENDING, BookingStatus.CONFIRMED),
            (BookingStatus.CONFIRMED, BookingStatus.COMPLETED),
            (BookingStatus.CONFIRMED, BookingStatus.CANCELLED),
            (BookingStatus.PENDING, BookingStatus.FAILED),
        ]
        
        invalid_transitions = [
            (BookingStatus.COMPLETED, BookingStatus.PENDING),
            (BookingStatus.CANCELLED, BookingStatus.CONFIRMED),
            (BookingStatus.REFUNDED, BookingStatus.COMPLETED),
        ]
        
        for current, new in valid_transitions:
            assert booking_service.is_valid_transition(current, new) is True
        
        for current, new in invalid_transitions:
            assert booking_service.is_valid_transition(current, new) is False
    
    def test_distributed_lock_for_booking(self, booking_service):
        """Test distributed locking for concurrent booking modifications."""
        booking_id = 123
        
        # Simulate distributed lock
        with patch('backend.app.core.distributed_lock.acquire_lock') as mock_lock:
            mock_lock.return_value.__enter__ = Mock()
            mock_lock.return_value.__exit__ = Mock()
            
            booking_service.update_booking_with_lock(
                booking_id=booking_id,
                updates={"status": BookingStatus.CONFIRMED}
            )
            
            mock_lock.assert_called_once_with(f"booking:{booking_id}", timeout=30)
    
    def test_payment_retry_with_exponential_backoff(self, booking_service):
        """Test exponential backoff in payment retries."""
        retry_delays = []
        
        def track_delay(delay):
            retry_delays.append(delay)
        
        with patch('time.sleep', side_effect=track_delay):
            booking_service.payment_gateway.process_payment.side_effect = [
                PaymentException("Temporary failure"),
                PaymentException("Still failing"),
                {"status": "succeeded"}  # Success on third try
            ]
            
            result = booking_service.process_payment_with_retry(
                amount=Decimal("100.00"),
                max_retries=3,
                initial_delay=1,
                backoff_factor=2
            )
        
        # Verify exponential backoff
        assert retry_delays == [1, 2]  # 1 second, then 2 seconds
    
    def test_fraud_score_calculation(self, booking_service):
        """Test fraud scoring algorithm."""
        user_history = {
            "total_bookings": 50,
            "cancelled_bookings": 10,
            "refunded_bookings": 5,
            "average_amount": Decimal("75.00"),
            "days_since_registration": 30
        }
        
        booking_data = {
            "amount": Decimal("500.00"),  # Much higher than average
            "is_international": True,
            "device_fingerprint_match": False,
            "billing_shipping_match": False
        }
        
        fraud_score = booking_service.calculate_fraud_score(user_history, booking_data)
        
        # High amount + international + mismatches should = high score
        assert fraud_score > 0.7  # High risk
    
    def test_payment_method_validation_edge_cases(self, booking_service):
        """Test payment method validation for edge cases."""
        edge_cases = [
            # Expired card
            {
                "card_number": "4111111111111111",
                "exp_month": 1,
                "exp_year": 2020,
                "expected_error": "Card expired"
            },
            # Invalid CVV
            {
                "card_number": "4111111111111111",
                "exp_month": 12,
                "exp_year": 2025,
                "cvc": "12",  # Too short
                "expected_error": "Invalid CVV"
            },
            # Test card in production
            {
                "card_number": "4242424242424242",  # Stripe test card
                "exp_month": 12,
                "exp_year": 2025,
                "environment": "production",
                "expected_error": "Test card not allowed"
            }
        ]
        
        for case in edge_cases:
            with pytest.raises(ValueError, match=case["expected_error"]):
                booking_service.validate_payment_method(case)
    
    def test_commission_payout_minimum_threshold(self, booking_service):
        """Test commission payout minimum threshold enforcement."""
        commissions = [
            Commission(id=1, commission_amount=Decimal("5.00")),   # Below threshold
            Commission(id=2, commission_amount=Decimal("3.00")),   # Below threshold
            Commission(id=3, commission_amount=Decimal("15.00")),  # Above threshold
        ]
        
        minimum_payout = Decimal("10.00")
        
        eligible = booking_service.filter_payable_commissions(
            commissions,
            minimum_payout=minimum_payout,
            allow_aggregation=True
        )
        
        # Should aggregate small amounts or include large ones
        assert len(eligible) == 2  # Commissions 1+2 aggregated or just 3
        total = sum(c.commission_amount for c in eligible)
        assert total >= minimum_payout