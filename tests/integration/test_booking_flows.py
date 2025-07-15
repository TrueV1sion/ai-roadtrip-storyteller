"""Integration tests for complete booking flows."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.models.user import User
from backend.app.models.reservation import Reservation, ReservationStatus
from backend.app.services.booking_agent import BookingAgent, BookingType
from backend.app.services.booking_service import BookingService
from backend.app.services.master_orchestration_agent import MasterOrchestrationAgent
from backend.app.core.auth import create_access_token
from backend.app.database import get_db


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Create authentication headers."""
    token = create_access_token(data={"sub": "test@example.com", "user_id": 1})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_external_apis():
    """Mock external booking APIs."""
    with patch('backend.app.services.booking_service.OpenTableAPI') as mock_opentable, \
         patch('backend.app.services.booking_service.TicketmasterAPI') as mock_ticketmaster, \
         patch('backend.app.services.booking_service.BookingDotComAPI') as mock_booking_com:
        
        # Mock OpenTable responses
        mock_opentable.return_value.search_restaurants = AsyncMock(return_value=[
            {
                "id": "rest-1",
                "name": "Italian Bistro",
                "cuisine": "italian",
                "rating": 4.5,
                "price_range": "$$"
            }
        ])
        
        mock_opentable.return_value.check_availability = AsyncMock(return_value={
            "available": True,
            "slots": ["6:30 PM", "7:00 PM", "7:30 PM"]
        })
        
        mock_opentable.return_value.create_reservation = AsyncMock(return_value={
            "reservation_id": "OT-123456",
            "confirmation_code": "CONF123",
            "status": "confirmed"
        })
        
        # Mock Ticketmaster responses
        mock_ticketmaster.return_value.search_events = AsyncMock(return_value=[
            {
                "id": "event-1",
                "name": "City Museum",
                "type": "attraction",
                "price_range": {"min": 15, "max": 25}
            }
        ])
        
        mock_ticketmaster.return_value.purchase_tickets = AsyncMock(return_value={
            "order_id": "TM-789012",
            "confirmation_code": "TKT789",
            "tickets": [
                {"type": "adult", "price": 25.00},
                {"type": "adult", "price": 25.00}
            ]
        })
        
        # Mock Booking.com responses
        mock_booking_com.return_value.search_hotels = AsyncMock(return_value=[
            {
                "id": "hotel-1",
                "name": "Comfort Inn",
                "rating": 4.0,
                "price_per_night": 120.00
            }
        ])
        
        mock_booking_com.return_value.create_booking = AsyncMock(return_value={
            "booking_id": "BC-345678",
            "confirmation_code": "HTL345",
            "total_price": 240.00
        })
        
        yield {
            "opentable": mock_opentable,
            "ticketmaster": mock_ticketmaster,
            "booking_com": mock_booking_com
        }


class TestBookingFlowsIntegration:
    """Integration tests for complete booking flows."""
    
    @pytest.mark.asyncio
    async def test_restaurant_booking_flow_via_voice(self, client, auth_headers, mock_external_apis):
        """Test complete restaurant booking flow initiated by voice command."""
        # Step 1: Voice command to book restaurant
        voice_command = {
            "command": "Book a table for 4 at an Italian restaurant tonight at 7pm",
            "location": {"lat": 37.7749, "lng": -122.4194}
        }
        
        response = client.post(
            "/api/v1/voice/process",
            json=voice_command,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        result = response.json()
        
        # Should identify booking intent and provide options
        assert result["intent"] == "booking"
        assert result["booking_type"] == "restaurant"
        assert "options" in result
        assert len(result["options"]) > 0
        
        # Step 2: User selects restaurant
        selection = {
            "booking_id": result["session_id"],
            "selected_option": result["options"][0]["id"],
            "confirm": True
        }
        
        response = client.post(
            "/api/v1/booking/confirm",
            json=selection,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        booking = response.json()
        
        assert booking["status"] == "confirmed"
        assert booking["confirmation_code"] == "CONF123"
        assert booking["details"]["restaurant_name"] == "Italian Bistro"
        assert booking["details"]["party_size"] == 4
        assert booking["details"]["time"] == "7:00 PM"
        
        # Step 3: Verify commission was calculated
        assert "commission" in booking
        assert booking["commission"] > 0
        
        # Step 4: Check booking in database
        response = client.get(
            f"/api/v1/booking/{booking['booking_id']}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        stored_booking = response.json()
        assert stored_booking["status"] == "confirmed"
    
    @pytest.mark.asyncio
    async def test_multi_step_booking_with_preferences(self, client, auth_headers, mock_external_apis):
        """Test multi-step booking flow with user preferences."""
        # Step 1: Update user preferences
        preferences = {
            "dietary_restrictions": ["vegetarian", "gluten-free"],
            "cuisine_preferences": ["italian", "japanese"],
            "price_range": "moderate"
        }
        
        response = client.put(
            "/api/v1/user/preferences",
            json=preferences,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Step 2: Request restaurant recommendations
        response = client.post(
            "/api/v1/booking/recommendations",
            json={
                "booking_type": "restaurant",
                "location": {"lat": 37.7749, "lng": -122.4194},
                "date": "2024-01-20",
                "time": "7:00 PM",
                "party_size": 2
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        recommendations = response.json()
        
        # Should filter based on preferences
        assert len(recommendations["restaurants"]) > 0
        assert all(r["dietary_options"]["vegetarian"] for r in recommendations["restaurants"])
        
        # Step 3: Check availability for selected restaurant
        restaurant_id = recommendations["restaurants"][0]["id"]
        
        response = client.post(
            "/api/v1/booking/availability",
            json={
                "booking_type": "restaurant",
                "vendor_id": restaurant_id,
                "date": "2024-01-20",
                "time": "7:00 PM",
                "party_size": 2
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        availability = response.json()
        assert availability["available"] == True
        
        # Step 4: Create booking
        response = client.post(
            "/api/v1/booking/create",
            json={
                "booking_type": "restaurant",
                "vendor_id": restaurant_id,
                "date": "2024-01-20",
                "time": "7:00 PM",
                "party_size": 2,
                "special_requests": "Table by the window please"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        booking = response.json()
        assert booking["status"] == "confirmed"
        assert booking["special_requests"] == "Table by the window please"
    
    @pytest.mark.asyncio
    async def test_attraction_booking_with_family(self, client, auth_headers, mock_external_apis):
        """Test attraction ticket booking for a family."""
        # Step 1: Search for family-friendly attractions
        response = client.post(
            "/api/v1/booking/search",
            json={
                "booking_type": "attraction",
                "location": {"lat": 37.7749, "lng": -122.4194},
                "date": "2024-01-21",
                "filters": {
                    "family_friendly": True,
                    "age_groups": ["adult", "child"]
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        attractions = response.json()
        assert len(attractions["results"]) > 0
        
        # Step 2: Get pricing for selected attraction
        attraction_id = attractions["results"][0]["id"]
        
        response = client.post(
            "/api/v1/booking/pricing",
            json={
                "booking_type": "attraction",
                "vendor_id": attraction_id,
                "date": "2024-01-21",
                "tickets": [
                    {"type": "adult", "quantity": 2},
                    {"type": "child", "quantity": 2}
                ]
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        pricing = response.json()
        assert pricing["total"] > 0
        assert len(pricing["breakdown"]) == 2
        
        # Step 3: Book tickets
        response = client.post(
            "/api/v1/booking/create",
            json={
                "booking_type": "attraction",
                "vendor_id": attraction_id,
                "date": "2024-01-21",
                "tickets": [
                    {"type": "adult", "quantity": 2},
                    {"type": "child", "quantity": 2}
                ]
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        booking = response.json()
        assert booking["status"] == "confirmed"
        assert len(booking["tickets"]) == 4
    
    @pytest.mark.asyncio
    async def test_hotel_booking_with_modification(self, client, auth_headers, mock_external_apis):
        """Test hotel booking with subsequent modification."""
        # Step 1: Create initial hotel booking
        response = client.post(
            "/api/v1/booking/create",
            json={
                "booking_type": "hotel",
                "check_in": "2024-01-25",
                "check_out": "2024-01-27",
                "rooms": 1,
                "guests": 2,
                "location": {"lat": 37.7749, "lng": -122.4194}
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        booking = response.json()
        booking_id = booking["booking_id"]
        
        # Step 2: Modify booking (extend stay)
        response = client.put(
            f"/api/v1/booking/{booking_id}",
            json={
                "check_out": "2024-01-28",  # One day extension
                "special_requests": "Late checkout please"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        modified = response.json()
        assert modified["check_out"] == "2024-01-28"
        assert modified["nights"] == 3
        assert modified["price_difference"] > 0
        
        # Step 3: Verify commission adjustment
        assert modified["commission_adjustment"] > 0
    
    @pytest.mark.asyncio
    async def test_booking_cancellation_flow(self, client, auth_headers, mock_external_apis):
        """Test booking cancellation with refund processing."""
        # Step 1: Create a booking
        response = client.post(
            "/api/v1/booking/create",
            json={
                "booking_type": "restaurant",
                "vendor_id": "rest-1",
                "date": "2024-01-30",
                "time": "7:00 PM",
                "party_size": 4
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        booking = response.json()
        booking_id = booking["booking_id"]
        original_commission = booking["commission"]
        
        # Step 2: Cancel booking
        response = client.delete(
            f"/api/v1/booking/{booking_id}",
            json={"reason": "Change of plans"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        cancellation = response.json()
        
        assert cancellation["status"] == "cancelled"
        assert "refund_amount" in cancellation
        assert "cancellation_fee" in cancellation
        assert cancellation["commission_reversed"] == original_commission
    
    @pytest.mark.asyncio
    async def test_concurrent_booking_handling(self, client, auth_headers, mock_external_apis):
        """Test handling of concurrent booking requests."""
        # Simulate multiple users trying to book the same slot
        async def make_booking(user_id: int):
            headers = {
                "Authorization": f"Bearer {create_access_token(data={'sub': f'user{user_id}@example.com', 'user_id': user_id})}"
            }
            
            return client.post(
                "/api/v1/booking/create",
                json={
                    "booking_type": "restaurant",
                    "vendor_id": "rest-1",
                    "date": "2024-01-20",
                    "time": "7:00 PM",
                    "party_size": 2
                },
                headers=headers
            )
        
        # Make 3 concurrent booking attempts
        with patch.object(mock_external_apis["opentable"].return_value, 'create_reservation') as mock_create:
            # First call succeeds, others fail
            mock_create.side_effect = [
                {"reservation_id": "OT-1", "status": "confirmed"},
                {"error": "Slot no longer available"},
                {"error": "Slot no longer available"}
            ]
            
            responses = await asyncio.gather(
                make_booking(1),
                make_booking(2),
                make_booking(3),
                return_exceptions=True
            )
            
            # One should succeed, others should get appropriate error
            success_count = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code == 201)
            assert success_count == 1
    
    @pytest.mark.asyncio
    async def test_booking_with_payment_processing(self, client, auth_headers, mock_external_apis):
        """Test booking flow with payment processing."""
        with patch('backend.app.services.payment_service.PaymentService') as mock_payment:
            mock_payment.return_value.process_payment = AsyncMock(return_value={
                "payment_id": "PAY-123",
                "status": "completed",
                "amount": 100.00
            })
            
            # Create booking requiring payment
            response = client.post(
                "/api/v1/booking/create",
                json={
                    "booking_type": "attraction",
                    "vendor_id": "event-1",
                    "date": "2024-01-21",
                    "tickets": [
                        {"type": "adult", "quantity": 2}
                    ],
                    "payment_method": {
                        "type": "card",
                        "token": "tok_visa"
                    }
                },
                headers=auth_headers
            )
            
            assert response.status_code == 201
            booking = response.json()
            
            assert booking["payment_status"] == "completed"
            assert booking["payment_id"] == "PAY-123"
            assert booking["total_paid"] == 50.00  # 2 adults @ $25
    
    @pytest.mark.asyncio
    async def test_booking_error_recovery(self, client, auth_headers, mock_external_apis):
        """Test error recovery in booking flow."""
        # Simulate API failure and retry
        call_count = 0
        
        def create_reservation_with_retry(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary API error")
            return {
                "reservation_id": "OT-RETRY",
                "status": "confirmed"
            }
        
        mock_external_apis["opentable"].return_value.create_reservation = AsyncMock(
            side_effect=create_reservation_with_retry
        )
        
        response = client.post(
            "/api/v1/booking/create",
            json={
                "booking_type": "restaurant",
                "vendor_id": "rest-1",
                "date": "2024-01-20",
                "time": "7:00 PM",
                "party_size": 2
            },
            headers=auth_headers
        )
        
        # Should succeed after retries
        assert response.status_code == 201
        assert call_count == 3  # Failed twice, succeeded on third attempt
    
    @pytest.mark.asyncio
    async def test_booking_with_special_requirements(self, client, auth_headers, mock_external_apis):
        """Test booking with special requirements and accommodations."""
        response = client.post(
            "/api/v1/booking/create",
            json={
                "booking_type": "restaurant",
                "vendor_id": "rest-1",
                "date": "2024-01-20",
                "time": "7:00 PM",
                "party_size": 4,
                "special_requirements": {
                    "wheelchair_accessible": True,
                    "dietary_restrictions": ["vegetarian", "nut-allergy"],
                    "seating_preference": "quiet area",
                    "occasion": "birthday"
                }
            },
            headers=auth_headers
        )
        
        assert response.status_code == 201
        booking = response.json()
        
        # Verify special requirements were processed
        assert booking["special_requirements"]["wheelchair_accessible"] == True
        assert "vegetarian" in booking["special_requirements"]["dietary_restrictions"]
        assert booking["special_requirements"]["occasion"] == "birthday"
    
    @pytest.mark.asyncio
    async def test_booking_analytics_tracking(self, client, auth_headers, mock_external_apis):
        """Test that bookings are properly tracked for analytics."""
        # Create multiple bookings
        bookings = []
        for i in range(3):
            response = client.post(
                "/api/v1/booking/create",
                json={
                    "booking_type": "restaurant",
                    "vendor_id": f"rest-{i}",
                    "date": "2024-01-20",
                    "time": f"{6+i}:00 PM",
                    "party_size": 2
                },
                headers=auth_headers
            )
            bookings.append(response.json())
        
        # Get analytics
        response = client.get(
            "/api/v1/analytics/bookings",
            params={
                "start_date": "2024-01-01",
                "end_date": "2024-01-31"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        analytics = response.json()
        
        assert analytics["total_bookings"] >= 3
        assert analytics["total_revenue"] > 0
        assert analytics["total_commission"] > 0
        assert "bookings_by_type" in analytics
        assert analytics["bookings_by_type"]["restaurant"] >= 3