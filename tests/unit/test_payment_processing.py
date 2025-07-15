"""
Comprehensive payment processing tests for production readiness.
Tests payment gateway integration, transaction handling, and error scenarios.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import asyncio

from sqlalchemy.orm import Session
from fastapi import HTTPException

from backend.app.models.booking import Booking, BookingStatus
from backend.app.models.partner import Partner, PartnerType
from backend.app.models.commission import Commission, CommissionStatus
from backend.app.models.user import User
from backend.app.services.booking_service import BookingService
from backend.app.services.commission_calculator import CommissionCalculator
from backend.app.schemas.booking import BookingCreate
from backend.app.core.exceptions import PaymentException, RefundException


class TestPaymentProcessing:
    """Test suite for payment processing functionality."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_payment_gateway(self):
        """Mock payment gateway client."""
        gateway = Mock()
        gateway.process_payment = Mock()
        gateway.process_refund = Mock()
        gateway.get_transaction_status = Mock()
        gateway.validate_webhook = Mock()
        return gateway
    
    @pytest.fixture
    def booking_service(self, mock_db):
        """Create booking service instance."""
        return BookingService(mock_db)
    
    @pytest.fixture
    def sample_partner(self):
        """Create sample partner."""
        return Partner(
            id=1,
            name="Test Restaurant",
            partner_type=PartnerType.RESTAURANT,
            commission_rate=Decimal("0.15"),
            is_active=True,
            api_credentials={"key": "test_key"}
        )
    
    @pytest.fixture
    def sample_user(self):
        """Create sample user."""
        return User(
            id=1,
            email="test@example.com",
            full_name="Test User",
            is_active=True
        )
    
    def test_successful_payment_processing(self, booking_service, mock_db, mock_payment_gateway, sample_partner):
        """Test successful payment processing flow."""
        # Setup
        booking_data = BookingCreate(
            partner_id=1,
            booking_type="restaurant",
            service_date=datetime.utcnow() + timedelta(days=1),
            gross_amount=Decimal("100.00"),
            currency="USD",
            partner_booking_id="PARTNER-123",
            metadata={"party_size": 4}
        )
        
        mock_db.query.return_value.filter.return_value.first.return_value = sample_partner
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        # Mock payment gateway response
        mock_payment_gateway.process_payment.return_value = {
            "transaction_id": "TXN-123456",
            "status": "succeeded",
            "amount": 100.00,
            "currency": "USD",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Execute with mocked payment gateway
        with patch.object(booking_service, 'payment_gateway', mock_payment_gateway):
            booking = booking_service.create_booking(user_id=1, booking_data=booking_data)
        
        # Verify
        assert mock_db.add.called
        assert mock_db.commit.called
        mock_payment_gateway.process_payment.assert_called_once()
        
    def test_payment_failure_rollback(self, booking_service, mock_db, mock_payment_gateway, sample_partner):
        """Test transaction rollback on payment failure."""
        # Setup
        booking_data = BookingCreate(
            partner_id=1,
            booking_type="restaurant",
            service_date=datetime.utcnow() + timedelta(days=1),
            gross_amount=Decimal("100.00"),
            currency="USD",
            partner_booking_id="PARTNER-123"
        )
        
        mock_db.query.return_value.filter.return_value.first.return_value = sample_partner
        mock_db.rollback = Mock()
        
        # Mock payment failure
        mock_payment_gateway.process_payment.side_effect = PaymentException("Payment declined")
        
        # Execute and verify rollback
        with patch.object(booking_service, 'payment_gateway', mock_payment_gateway):
            with pytest.raises(PaymentException):
                booking_service.create_booking(user_id=1, booking_data=booking_data)
        
        # Verify rollback was called
        mock_db.rollback.assert_called_once()
        
    def test_commission_calculation_accuracy(self, booking_service, mock_db, sample_partner):
        """Test commission calculations for different scenarios."""
        test_cases = [
            # (gross_amount, commission_rate, expected_commission, expected_net)
            (Decimal("100.00"), Decimal("0.15"), Decimal("15.00"), Decimal("85.00")),
            (Decimal("250.50"), Decimal("0.10"), Decimal("25.05"), Decimal("225.45")),
            (Decimal("1000.00"), Decimal("0.20"), Decimal("200.00"), Decimal("800.00")),
            (Decimal("99.99"), Decimal("0.12"), Decimal("12.00"), Decimal("87.99")),  # Rounding
        ]
        
        calculator = CommissionCalculator(mock_db)
        
        for gross, rate, expected_commission, expected_net in test_cases:
            booking = Booking(
                partner_id=1,
                booking_type="restaurant",
                gross_amount=gross
            )
            sample_partner.commission_rate = rate
            mock_db.query.return_value.filter.return_value.first.return_value = sample_partner
            
            commission, actual_rate = calculator.calculate_commission(booking)
            
            assert commission == expected_commission, f"Commission mismatch for {gross} at {rate}"
            assert actual_rate == rate
            assert gross - commission == expected_net
    
    def test_concurrent_booking_conflict(self, booking_service, mock_db):
        """Test handling of concurrent booking attempts."""
        # Setup concurrent booking scenario
        booking_data = BookingCreate(
            partner_id=1,
            booking_type="restaurant",
            service_date=datetime.utcnow() + timedelta(hours=2),
            gross_amount=Decimal("100.00"),
            currency="USD",
            partner_booking_id="TABLE-5",
            metadata={"table_id": 5, "time_slot": "19:00"}
        )
        
        # Simulate concurrent booking exists
        existing_booking = Booking(
            id=100,
            partner_booking_id="TABLE-5",
            service_date=booking_data.service_date,
            booking_status=BookingStatus.CONFIRMED
        )
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            Mock(id=1, is_active=True),  # Partner query
            existing_booking  # Concurrent booking check
        ]
        
        # Execute and verify conflict handling
        with pytest.raises(ValueError, match="already booked"):
            booking_service.create_booking(user_id=1, booking_data=booking_data)
    
    def test_refund_processing(self, booking_service, mock_db, mock_payment_gateway):
        """Test refund processing for cancelled bookings."""
        # Setup existing booking
        booking = Booking(
            id=1,
            booking_reference="BK-12345678",
            booking_status=BookingStatus.CONFIRMED,
            gross_amount=Decimal("150.00"),
            net_amount=Decimal("127.50"),
            payment_transaction_id="TXN-789",
            user_id=1
        )
        
        commission = Commission(
            id=1,
            booking_id=1,
            commission_amount=Decimal("22.50"),
            status=CommissionStatus.PENDING
        )
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            booking,  # Booking query
            commission  # Commission query
        ]
        
        # Mock refund success
        mock_payment_gateway.process_refund.return_value = {
            "refund_id": "REF-123",
            "status": "succeeded",
            "amount": 150.00,
            "original_transaction": "TXN-789"
        }
        
        # Execute refund
        with patch.object(booking_service, 'payment_gateway', mock_payment_gateway):
            result = booking_service.process_refund(booking_id=1, reason="Customer requested")
        
        # Verify
        assert booking.booking_status == BookingStatus.REFUNDED
        assert commission.status == CommissionStatus.REVERSED
        mock_payment_gateway.process_refund.assert_called_once_with(
            transaction_id="TXN-789",
            amount=150.00,
            reason="Customer requested"
        )
    
    def test_partial_refund_handling(self, booking_service, mock_db, mock_payment_gateway):
        """Test partial refund scenarios."""
        booking = Booking(
            id=1,
            gross_amount=Decimal("200.00"),
            net_amount=Decimal("170.00"),
            payment_transaction_id="TXN-456",
            booking_status=BookingStatus.CONFIRMED
        )
        
        mock_db.query.return_value.filter.return_value.first.return_value = booking
        
        # Process 50% refund
        refund_amount = Decimal("100.00")
        mock_payment_gateway.process_refund.return_value = {
            "refund_id": "REF-PARTIAL-123",
            "status": "succeeded",
            "amount": float(refund_amount)
        }
        
        with patch.object(booking_service, 'payment_gateway', mock_payment_gateway):
            result = booking_service.process_partial_refund(
                booking_id=1,
                refund_amount=refund_amount,
                reason="Service partially delivered"
            )
        
        # Verify partial refund recorded
        assert booking.refund_amount == refund_amount
        assert booking.booking_status == BookingStatus.PARTIALLY_REFUNDED
    
    def test_payment_retry_mechanism(self, booking_service, mock_payment_gateway):
        """Test payment retry logic for transient failures."""
        # Setup retry scenario
        mock_payment_gateway.process_payment.side_effect = [
            PaymentException("Network timeout"),  # First attempt fails
            PaymentException("Gateway busy"),     # Second attempt fails
            {                                     # Third attempt succeeds
                "transaction_id": "TXN-RETRY-SUCCESS",
                "status": "succeeded"
            }
        ]
        
        # Execute with retry
        with patch.object(booking_service, 'payment_gateway', mock_payment_gateway):
            with patch('time.sleep'):  # Skip actual delays in tests
                result = booking_service.process_payment_with_retry(
                    amount=100.00,
                    max_retries=3,
                    retry_delay=1
                )
        
        # Verify retry behavior
        assert mock_payment_gateway.process_payment.call_count == 3
        assert result["transaction_id"] == "TXN-RETRY-SUCCESS"
    
    def test_webhook_payment_confirmation(self, booking_service, mock_db, mock_payment_gateway):
        """Test webhook handling for payment confirmations."""
        # Setup webhook payload
        webhook_payload = {
            "event": "payment.succeeded",
            "transaction_id": "TXN-WEBHOOK-123",
            "booking_reference": "BK-87654321",
            "amount": 75.00,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Mock webhook validation
        mock_payment_gateway.validate_webhook.return_value = True
        
        # Mock booking lookup
        booking = Booking(
            id=1,
            booking_reference="BK-87654321",
            booking_status=BookingStatus.PENDING,
            payment_transaction_id="TXN-WEBHOOK-123"
        )
        mock_db.query.return_value.filter.return_value.first.return_value = booking
        
        # Process webhook
        with patch.object(booking_service, 'payment_gateway', mock_payment_gateway):
            booking_service.handle_payment_webhook(webhook_payload, signature="test-sig")
        
        # Verify booking updated
        assert booking.booking_status == BookingStatus.CONFIRMED
        mock_db.commit.assert_called()
    
    def test_fraud_detection(self, booking_service, mock_db):
        """Test fraud detection mechanisms."""
        # Test rapid booking velocity
        user_id = 1
        
        # Mock recent bookings query
        recent_bookings = [
            Booking(created_at=datetime.utcnow() - timedelta(minutes=5)),
            Booking(created_at=datetime.utcnow() - timedelta(minutes=10)),
            Booking(created_at=datetime.utcnow() - timedelta(minutes=15)),
            Booking(created_at=datetime.utcnow() - timedelta(minutes=20)),
            Booking(created_at=datetime.utcnow() - timedelta(minutes=25)),
        ]
        
        mock_db.query.return_value.filter.return_value.filter.return_value.all.return_value = recent_bookings
        
        # Check fraud detection
        is_suspicious = booking_service.check_fraud_indicators(
            user_id=user_id,
            amount=Decimal("1000.00"),  # High amount
            booking_velocity_threshold=3,
            time_window_minutes=30
        )
        
        assert is_suspicious is True  # 5 bookings in 30 minutes is suspicious
    
    def test_payment_method_validation(self, booking_service):
        """Test payment method validation."""
        test_cases = [
            # (card_number, expected_valid)
            ("4111111111111111", True),   # Valid Visa
            ("5500000000000004", True),   # Valid Mastercard
            ("340000000000009", True),    # Valid Amex
            ("4111111111111112", False),  # Invalid checksum
            ("1234567890123456", False),  # Invalid format
            ("", False),                  # Empty
        ]
        
        for card_number, expected_valid in test_cases:
            is_valid = booking_service.validate_card_number(card_number)
            assert is_valid == expected_valid, f"Card validation failed for {card_number}"
    
    def test_commission_payout_scheduling(self, booking_service, mock_db):
        """Test commission payout scheduling logic."""
        # Create confirmed bookings with commissions
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        
        eligible_commissions = [
            Commission(
                id=1,
                booking_id=1,
                commission_amount=Decimal("15.00"),
                status=CommissionStatus.PENDING,
                created_at=cutoff_date - timedelta(days=1)
            ),
            Commission(
                id=2,
                booking_id=2,
                commission_amount=Decimal("25.50"),
                status=CommissionStatus.PENDING,
                created_at=cutoff_date - timedelta(days=2)
            )
        ]
        
        mock_db.query.return_value.filter.return_value.filter.return_value.all.return_value = eligible_commissions
        
        # Schedule payouts
        payout_batch = booking_service.schedule_commission_payouts(
            cutoff_days=7,
            minimum_amount=Decimal("10.00")
        )
        
        # Verify
        assert len(payout_batch) == 2
        assert sum(c.commission_amount for c in payout_batch) == Decimal("40.50")
        
    def test_currency_conversion(self, booking_service):
        """Test currency conversion for international bookings."""
        # Mock exchange rates
        exchange_rates = {
            "USD": 1.0,
            "EUR": 0.85,
            "GBP": 0.73,
            "JPY": 110.0
        }
        
        with patch.object(booking_service, 'get_exchange_rates', return_value=exchange_rates):
            # Test conversions
            usd_amount = Decimal("100.00")
            
            eur_amount = booking_service.convert_currency(usd_amount, "USD", "EUR")
            assert eur_amount == Decimal("85.00")
            
            jpy_amount = booking_service.convert_currency(usd_amount, "USD", "JPY")
            assert jpy_amount == Decimal("11000.00")
            
            # Test reverse conversion
            gbp_to_usd = booking_service.convert_currency(Decimal("73.00"), "GBP", "USD")
            assert gbp_to_usd == Decimal("100.00")