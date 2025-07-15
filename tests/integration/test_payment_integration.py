"""
Integration tests for end-to-end payment flows.
Tests the complete payment pipeline including external service integration.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal
import json

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.models.booking import Booking, BookingStatus
from backend.app.models.user import User
from backend.app.models.partner import Partner, PartnerType
from backend.app.models.commission import Commission, CommissionStatus
from backend.app.core.auth import create_access_token
from backend.app.core.circuit_breaker import CircuitOpenError


class TestPaymentIntegration:
    """Integration tests for payment processing flows."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers."""
        token = create_access_token(
            data={"sub": "payment.test@example.com", "user_id": 1}
        )
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture
    def mock_payment_providers(self):
        """Mock external payment providers."""
        providers = {
            'stripe': AsyncMock(),
            'paypal': AsyncMock(),
            'square': AsyncMock()
        }
        
        # Configure default responses
        providers['stripe'].create_payment_intent.return_value = {
            'id': 'pi_test_123',
            'status': 'succeeded',
            'amount': 10000,  # Stripe uses cents
            'currency': 'usd'
        }
        
        providers['paypal'].create_order.return_value = {
            'id': 'PAYPAL-ORDER-123',
            'status': 'COMPLETED',
            'purchase_units': [{'amount': {'value': '100.00'}}]
        }
        
        return providers
    
    @pytest.mark.asyncio
    async def test_complete_booking_payment_flow(self, client, auth_headers, mock_payment_providers):
        """Test complete booking with payment flow."""
        with patch('backend.app.services.payment_service.stripe', mock_payment_providers['stripe']):
            # Step 1: Search for availability
            search_response = client.post(
                "/api/bookings/search",
                headers=auth_headers,
                json={
                    "booking_type": "restaurant",
                    "location": {"lat": 37.7749, "lng": -122.4194},
                    "date": (datetime.utcnow() + timedelta(days=2)).isoformat(),
                    "party_size": 4
                }
            )
            assert search_response.status_code == 200
            results = search_response.json()
            assert len(results) > 0
            
            # Step 2: Create booking with payment
            selected = results[0]
            booking_response = client.post(
                "/api/bookings/create",
                headers=auth_headers,
                json={
                    "partner_id": selected["partner_id"],
                    "booking_type": "restaurant",
                    "service_date": selected["available_times"][0],
                    "gross_amount": 100.00,
                    "currency": "USD",
                    "payment_method": "card",
                    "payment_details": {
                        "card_number": "4111111111111111",
                        "exp_month": 12,
                        "exp_year": 2025,
                        "cvc": "123"
                    },
                    "metadata": {
                        "party_size": 4,
                        "special_requests": "Window table"
                    }
                }
            )
            
            assert booking_response.status_code == 201
            booking_data = booking_response.json()
            assert booking_data["booking_status"] == "CONFIRMED"
            assert booking_data["payment_status"] == "SUCCEEDED"
            assert "booking_reference" in booking_data
            
            # Step 3: Verify commission was calculated
            assert "commission_amount" in booking_data
            assert Decimal(booking_data["commission_amount"]) > 0
            
            # Verify payment provider was called
            mock_payment_providers['stripe'].create_payment_intent.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_payment_failure_recovery(self, client, auth_headers, mock_payment_providers):
        """Test payment failure and recovery flow."""
        # Configure payment to fail initially
        mock_payment_providers['stripe'].create_payment_intent.side_effect = [
            Exception("Network error"),  # First attempt fails
            {'id': 'pi_retry_123', 'status': 'succeeded'}  # Retry succeeds
        ]
        
        with patch('backend.app.services.payment_service.stripe', mock_payment_providers['stripe']):
            booking_response = client.post(
                "/api/bookings/create",
                headers=auth_headers,
                json={
                    "partner_id": 1,
                    "booking_type": "hotel",
                    "service_date": (datetime.utcnow() + timedelta(days=5)).isoformat(),
                    "gross_amount": 250.00,
                    "currency": "USD",
                    "payment_method": "card",
                    "enable_retry": True,
                    "payment_details": {
                        "card_number": "4111111111111111",
                        "exp_month": 12,
                        "exp_year": 2025,
                        "cvc": "123"
                    }
                }
            )
            
            # Should succeed after retry
            assert booking_response.status_code == 201
            assert mock_payment_providers['stripe'].create_payment_intent.call_count == 2
    
    @pytest.mark.asyncio
    async def test_concurrent_payment_processing(self, client, auth_headers):
        """Test handling of concurrent payment requests."""
        # Create multiple concurrent booking requests
        async def make_booking(index):
            return client.post(
                "/api/bookings/create",
                headers=auth_headers,
                json={
                    "partner_id": 1,
                    "booking_type": "restaurant",
                    "service_date": (datetime.utcnow() + timedelta(hours=3)).isoformat(),
                    "gross_amount": 75.00,
                    "currency": "USD",
                    "payment_method": "card",
                    "metadata": {"table_id": 5},  # Same table
                    "payment_details": {
                        "card_number": "4111111111111111",
                        "exp_month": 12,
                        "exp_year": 2025,
                        "cvc": "123"
                    }
                }
            )
        
        # Execute concurrent requests
        with patch('backend.app.services.booking_service.check_availability', return_value=True):
            tasks = [make_booking(i) for i in range(3)]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify only one succeeded
        success_count = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code == 201)
        assert success_count == 1
        
        # Others should get conflict error
        conflict_count = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code == 409)
        assert conflict_count == 2
    
    @pytest.mark.asyncio
    async def test_refund_flow(self, client, auth_headers):
        """Test complete refund flow."""
        # First create a booking
        booking_response = client.post(
            "/api/bookings/create",
            headers=auth_headers,
            json={
                "partner_id": 1,
                "booking_type": "event",
                "service_date": (datetime.utcnow() + timedelta(days=30)).isoformat(),
                "gross_amount": 150.00,
                "currency": "USD",
                "payment_method": "card",
                "payment_details": {
                    "card_number": "4111111111111111",
                    "exp_month": 12,
                    "exp_year": 2025,
                    "cvc": "123"
                }
            }
        )
        
        assert booking_response.status_code == 201
        booking_id = booking_response.json()["id"]
        
        # Request refund
        with patch('backend.app.services.payment_service.stripe.create_refund') as mock_refund:
            mock_refund.return_value = {
                'id': 'ref_123',
                'status': 'succeeded',
                'amount': 15000  # cents
            }
            
            refund_response = client.post(
                f"/api/bookings/{booking_id}/refund",
                headers=auth_headers,
                json={
                    "reason": "Event cancelled",
                    "notify_partner": True
                }
            )
            
            assert refund_response.status_code == 200
            refund_data = refund_response.json()
            assert refund_data["booking_status"] == "REFUNDED"
            assert refund_data["refund_status"] == "SUCCEEDED"
            mock_refund.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_payment_webhook_processing(self, client):
        """Test payment webhook handling."""
        # Stripe webhook payload
        webhook_payload = {
            "id": "evt_123",
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_webhook_123",
                    "metadata": {
                        "booking_id": "123",
                        "booking_reference": "BK-ABCD1234"
                    },
                    "amount": 10000,
                    "currency": "usd"
                }
            }
        }
        
        # Mock signature validation
        with patch('backend.app.services.payment_service.validate_webhook_signature', return_value=True):
            webhook_response = client.post(
                "/api/webhooks/stripe",
                json=webhook_payload,
                headers={
                    "Stripe-Signature": "test_signature"
                }
            )
            
            assert webhook_response.status_code == 200
            assert webhook_response.json()["status"] == "processed"
    
    @pytest.mark.asyncio
    async def test_payment_method_management(self, client, auth_headers):
        """Test payment method CRUD operations."""
        # Add payment method
        add_response = client.post(
            "/api/payment-methods",
            headers=auth_headers,
            json={
                "type": "card",
                "card_number": "4242424242424242",
                "exp_month": 12,
                "exp_year": 2025,
                "cvc": "123",
                "billing_address": {
                    "line1": "123 Main St",
                    "city": "San Francisco",
                    "state": "CA",
                    "postal_code": "94105",
                    "country": "US"
                }
            }
        )
        
        assert add_response.status_code == 201
        payment_method = add_response.json()
        assert payment_method["last4"] == "4242"
        assert payment_method["is_default"] is True
        
        # List payment methods
        list_response = client.get("/api/payment-methods", headers=auth_headers)
        assert list_response.status_code == 200
        methods = list_response.json()
        assert len(methods) == 1
        
        # Delete payment method
        delete_response = client.delete(
            f"/api/payment-methods/{payment_method['id']}",
            headers=auth_headers
        )
        assert delete_response.status_code == 204
    
    @pytest.mark.asyncio
    async def test_commission_payout_processing(self, client, auth_headers):
        """Test commission payout batch processing."""
        # Mock admin auth
        admin_token = create_access_token(
            data={"sub": "admin@example.com", "user_id": 999, "is_admin": True}
        )
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Trigger payout batch
        payout_response = client.post(
            "/api/admin/commissions/payout",
            headers=admin_headers,
            json={
                "cutoff_date": (datetime.utcnow() - timedelta(days=7)).isoformat(),
                "minimum_amount": 50.00
            }
        )
        
        assert payout_response.status_code == 200
        payout_data = payout_response.json()
        assert "batch_id" in payout_data
        assert "total_amount" in payout_data
        assert "commission_count" in payout_data
    
    @pytest.mark.asyncio
    async def test_payment_circuit_breaker(self, client, auth_headers):
        """Test circuit breaker for payment provider failures."""
        # Configure payment provider to fail multiple times
        with patch('backend.app.services.payment_service.stripe.create_payment_intent') as mock_payment:
            mock_payment.side_effect = Exception("Service unavailable")
            
            # Make multiple requests to trip circuit breaker
            for i in range(5):
                response = client.post(
                    "/api/bookings/create",
                    headers=auth_headers,
                    json={
                        "partner_id": 1,
                        "booking_type": "hotel",
                        "service_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                        "gross_amount": 100.00,
                        "currency": "USD",
                        "payment_method": "card",
                        "payment_details": {
                            "card_number": "4111111111111111",
                            "exp_month": 12,
                            "exp_year": 2025,
                            "cvc": "123"
                        }
                    }
                )
                
                if i < 3:
                    # First 3 attempts should fail normally
                    assert response.status_code == 502
                else:
                    # Circuit breaker should be open
                    assert response.status_code == 503
                    assert "circuit breaker open" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_multi_currency_booking(self, client, auth_headers):
        """Test booking with currency conversion."""
        # Mock exchange rates
        with patch('backend.app.services.currency_service.get_exchange_rates') as mock_rates:
            mock_rates.return_value = {
                "USD": 1.0,
                "EUR": 0.85,
                "GBP": 0.73
            }
            
            # Create booking in EUR
            booking_response = client.post(
                "/api/bookings/create",
                headers=auth_headers,
                json={
                    "partner_id": 1,
                    "booking_type": "hotel",
                    "service_date": (datetime.utcnow() + timedelta(days=3)).isoformat(),
                    "gross_amount": 100.00,
                    "currency": "EUR",
                    "display_currency": "USD",  # Show in USD
                    "payment_method": "card",
                    "payment_details": {
                        "card_number": "4111111111111111",
                        "exp_month": 12,
                        "exp_year": 2025,
                        "cvc": "123"
                    }
                }
            )
            
            assert booking_response.status_code == 201
            booking_data = booking_response.json()
            
            # Verify currency conversion
            assert booking_data["currency"] == "EUR"
            assert booking_data["gross_amount"] == 100.00
            assert booking_data["display_currency"] == "USD"
            assert booking_data["display_amount"] == pytest.approx(117.65, 0.01)  # 100 EUR / 0.85