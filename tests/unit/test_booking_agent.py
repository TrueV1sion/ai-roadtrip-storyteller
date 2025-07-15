"""Unit tests for the Booking Agent."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, date
from decimal import Decimal

from backend.app.services.booking_agent import (
    BookingAgent,
    BookingRequest,
    BookingResponse,
    BookingStatus,
    BookingType,
    RestaurantBooking,
    AttractionBooking,
    HotelBooking
)
from backend.app.services.booking_service import BookingService
from backend.app.services.commission_calculator import CommissionCalculator
from backend.app.models.user import User


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = Mock(spec=User)
    user.id = 1
    user.email = "test@example.com"
    user.phone = "+1234567890"
    user.preferences = {
        "dietary_restrictions": ["vegetarian", "gluten-free"],
        "cuisine_preferences": ["italian", "japanese"],
        "price_range": "moderate",
        "accessibility_needs": []
    }
    return user


@pytest.fixture
def mock_booking_service():
    """Create a mock booking service."""
    service = Mock(spec=BookingService)
    service.create_restaurant_reservation = AsyncMock(return_value={
        "reservation_id": "REST-123",
        "confirmation_code": "ABC123",
        "status": "confirmed",
        "details": {
            "restaurant_name": "Test Restaurant",
            "party_size": 4,
            "time": "7:00 PM",
            "date": "2024-01-20"
        }
    })
    
    service.book_attraction_tickets = AsyncMock(return_value={
        "booking_id": "ATTR-456",
        "confirmation_code": "XYZ789",
        "status": "confirmed",
        "tickets": [
            {"type": "adult", "quantity": 2, "price": 25.00},
            {"type": "child", "quantity": 1, "price": 15.00}
        ],
        "total": 65.00
    })
    
    service.reserve_hotel_room = AsyncMock(return_value={
        "booking_id": "HOTEL-789",
        "confirmation_code": "HTL789",
        "status": "confirmed",
        "details": {
            "hotel_name": "Test Hotel",
            "room_type": "double",
            "check_in": "2024-01-20",
            "check_out": "2024-01-22",
            "total": 300.00
        }
    })
    
    service.check_availability = AsyncMock(return_value={
        "available": True,
        "options": [
            {"time": "6:30 PM", "available": True},
            {"time": "7:00 PM", "available": True},
            {"time": "7:30 PM", "available": False}
        ]
    })
    
    service.get_recommendations = AsyncMock(return_value=[
        {
            "name": "Recommended Restaurant",
            "rating": 4.5,
            "price_range": "$$",
            "cuisine": "italian",
            "distance": "0.5 miles"
        }
    ])
    
    return service


@pytest.fixture
def mock_commission_calculator():
    """Create a mock commission calculator."""
    calculator = Mock(spec=CommissionCalculator)
    calculator.calculate_commission = Mock(return_value=Decimal("5.25"))
    calculator.get_commission_rate = Mock(return_value=Decimal("0.10"))
    return calculator


@pytest.fixture
def booking_agent(mock_booking_service, mock_commission_calculator):
    """Create a booking agent with mocked dependencies."""
    with patch('backend.app.services.booking_agent.BookingService', return_value=mock_booking_service), \
         patch('backend.app.services.booking_agent.CommissionCalculator', return_value=mock_commission_calculator):
        
        agent = BookingAgent()
        agent.booking_service = mock_booking_service
        agent.commission_calculator = mock_commission_calculator
        return agent


class TestBookingAgent:
    """Test suite for Booking Agent."""
    
    @pytest.mark.asyncio
    async def test_parse_restaurant_booking_request(self, booking_agent):
        """Test parsing restaurant booking requests."""
        requests = [
            ("Book a table for 4 at 7pm tonight", {
                "party_size": 4,
                "time": "7:00 PM",
                "date": "tonight"
            }),
            ("Make a reservation for 2 people at Italian restaurant tomorrow at 8", {
                "party_size": 2,
                "time": "8:00 PM",
                "date": "tomorrow",
                "cuisine": "italian"
            }),
            ("Reserve dinner for 6 at Japanese place this Friday 6:30pm", {
                "party_size": 6,
                "time": "6:30 PM",
                "date": "friday",
                "cuisine": "japanese"
            })
        ]
        
        for text, expected in requests:
            parsed = await booking_agent.parse_booking_request(text, BookingType.RESTAURANT)
            assert parsed["party_size"] == expected["party_size"]
            assert parsed["time"] == expected["time"]
            assert "date" in parsed
            if "cuisine" in expected:
                assert expected["cuisine"] in parsed.get("cuisine", "").lower()
    
    @pytest.mark.asyncio
    async def test_parse_attraction_booking_request(self, booking_agent):
        """Test parsing attraction ticket requests."""
        requests = [
            ("Buy 2 adult tickets for the museum", {
                "adult_tickets": 2,
                "child_tickets": 0,
                "attraction_type": "museum"
            }),
            ("Get 2 adult and 3 child tickets for the zoo tomorrow", {
                "adult_tickets": 2,
                "child_tickets": 3,
                "attraction_type": "zoo",
                "date": "tomorrow"
            }),
            ("Book tickets for 4 people to the aquarium", {
                "total_tickets": 4,
                "attraction_type": "aquarium"
            })
        ]
        
        for text, expected in requests:
            parsed = await booking_agent.parse_booking_request(text, BookingType.ATTRACTION)
            if "adult_tickets" in expected:
                assert parsed.get("adult_tickets", 0) == expected["adult_tickets"]
            if "child_tickets" in expected:
                assert parsed.get("child_tickets", 0) == expected["child_tickets"]
            assert expected["attraction_type"] in parsed.get("attraction_type", "").lower()
    
    @pytest.mark.asyncio
    async def test_parse_hotel_booking_request(self, booking_agent):
        """Test parsing hotel reservation requests."""
        requests = [
            ("Book a hotel for tonight", {
                "check_in": "tonight",
                "nights": 1,
                "rooms": 1
            }),
            ("Reserve 2 rooms for 3 nights starting Friday", {
                "check_in": "friday",
                "nights": 3,
                "rooms": 2
            }),
            ("I need a hotel from Jan 20 to Jan 23", {
                "check_in": "Jan 20",
                "check_out": "Jan 23",
                "rooms": 1
            })
        ]
        
        for text, expected in requests:
            parsed = await booking_agent.parse_booking_request(text, BookingType.HOTEL)
            assert parsed.get("rooms", 1) == expected.get("rooms", 1)
            if "nights" in expected:
                assert parsed.get("nights", 1) == expected["nights"]
            assert "check_in" in parsed
    
    @pytest.mark.asyncio
    async def test_restaurant_booking_success(self, booking_agent, mock_user, mock_booking_service):
        """Test successful restaurant reservation."""
        request = BookingRequest(
            user_id=1,
            booking_type=BookingType.RESTAURANT,
            details={
                "party_size": 4,
                "time": "7:00 PM",
                "date": "2024-01-20",
                "cuisine": "italian"
            },
            user_preferences=mock_user.preferences
        )
        
        response = await booking_agent.process_booking(request)
        
        assert response.success
        assert response.booking_id == "REST-123"
        assert response.confirmation_code == "ABC123"
        assert response.status == BookingStatus.CONFIRMED
        assert response.commission == Decimal("5.25")
        
        mock_booking_service.create_restaurant_reservation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_attraction_booking_success(self, booking_agent, mock_user, mock_booking_service):
        """Test successful attraction ticket booking."""
        request = BookingRequest(
            user_id=1,
            booking_type=BookingType.ATTRACTION,
            details={
                "attraction_name": "City Museum",
                "adult_tickets": 2,
                "child_tickets": 1,
                "date": "2024-01-20"
            },
            user_preferences=mock_user.preferences
        )
        
        response = await booking_agent.process_booking(request)
        
        assert response.success
        assert response.booking_id == "ATTR-456"
        assert response.total_amount == Decimal("65.00")
        assert response.commission == Decimal("5.25")
        
        mock_booking_service.book_attraction_tickets.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_hotel_booking_success(self, booking_agent, mock_user, mock_booking_service):
        """Test successful hotel reservation."""
        request = BookingRequest(
            user_id=1,
            booking_type=BookingType.HOTEL,
            details={
                "check_in": "2024-01-20",
                "check_out": "2024-01-22",
                "rooms": 1,
                "room_type": "double"
            },
            user_preferences=mock_user.preferences
        )
        
        response = await booking_agent.process_booking(request)
        
        assert response.success
        assert response.booking_id == "HOTEL-789"
        assert response.total_amount == Decimal("300.00")
        assert response.commission == Decimal("5.25")
        
        mock_booking_service.reserve_hotel_room.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_booking_with_availability_check(self, booking_agent, mock_user, mock_booking_service):
        """Test booking with availability verification."""
        request = BookingRequest(
            user_id=1,
            booking_type=BookingType.RESTAURANT,
            details={
                "party_size": 4,
                "time": "7:00 PM",
                "date": "2024-01-20",
                "restaurant_name": "Test Restaurant"
            },
            check_availability=True
        )
        
        response = await booking_agent.process_booking(request)
        
        # Should check availability first
        mock_booking_service.check_availability.assert_called_once()
        # Then proceed with booking
        mock_booking_service.create_restaurant_reservation.assert_called_once()
        
        assert response.success
    
    @pytest.mark.asyncio
    async def test_booking_unavailable(self, booking_agent, mock_user, mock_booking_service):
        """Test handling of unavailable booking."""
        mock_booking_service.check_availability.return_value = {
            "available": False,
            "alternatives": [
                {"time": "6:00 PM", "available": True},
                {"time": "8:30 PM", "available": True}
            ]
        }
        
        request = BookingRequest(
            user_id=1,
            booking_type=BookingType.RESTAURANT,
            details={
                "party_size": 4,
                "time": "7:00 PM",
                "date": "2024-01-20"
            },
            check_availability=True
        )
        
        response = await booking_agent.process_booking(request)
        
        assert not response.success
        assert response.status == BookingStatus.UNAVAILABLE
        assert "alternatives" in response.metadata
        assert len(response.metadata["alternatives"]) == 2
    
    @pytest.mark.asyncio
    async def test_booking_with_preferences(self, booking_agent, mock_user, mock_booking_service):
        """Test booking considering user preferences."""
        request = BookingRequest(
            user_id=1,
            booking_type=BookingType.RESTAURANT,
            details={
                "party_size": 2,
                "time": "7:00 PM",
                "date": "2024-01-20"
            },
            user_preferences={
                "dietary_restrictions": ["vegetarian"],
                "cuisine_preferences": ["italian"],
                "price_range": "moderate"
            },
            use_preferences=True
        )
        
        response = await booking_agent.process_booking(request)
        
        # Verify preferences were passed to booking service
        call_args = mock_booking_service.create_restaurant_reservation.call_args[1]
        assert "dietary_restrictions" in call_args
        assert "vegetarian" in call_args["dietary_restrictions"]
        
        assert response.success
    
    @pytest.mark.asyncio
    async def test_booking_error_handling(self, booking_agent, mock_user, mock_booking_service):
        """Test error handling during booking."""
        mock_booking_service.create_restaurant_reservation.side_effect = Exception("Service unavailable")
        
        request = BookingRequest(
            user_id=1,
            booking_type=BookingType.RESTAURANT,
            details={
                "party_size": 4,
                "time": "7:00 PM",
                "date": "2024-01-20"
            }
        )
        
        response = await booking_agent.process_booking(request)
        
        assert not response.success
        assert response.status == BookingStatus.FAILED
        assert response.error is not None
        assert "Service unavailable" in response.error
    
    @pytest.mark.asyncio
    async def test_commission_calculation(self, booking_agent, mock_commission_calculator):
        """Test commission calculation for bookings."""
        booking_details = {
            "booking_type": BookingType.RESTAURANT,
            "amount": Decimal("100.00"),
            "vendor": "Test Restaurant"
        }
        
        commission = await booking_agent.calculate_booking_commission(booking_details)
        
        mock_commission_calculator.calculate_commission.assert_called_once_with(
            booking_type=BookingType.RESTAURANT,
            booking_amount=Decimal("100.00"),
            vendor_name="Test Restaurant"
        )
        
        assert commission == Decimal("5.25")
    
    @pytest.mark.asyncio
    async def test_booking_cancellation(self, booking_agent, mock_booking_service):
        """Test booking cancellation."""
        mock_booking_service.cancel_booking = AsyncMock(return_value={
            "success": True,
            "refund_amount": Decimal("90.00"),
            "cancellation_fee": Decimal("10.00")
        })
        
        result = await booking_agent.cancel_booking("REST-123", BookingType.RESTAURANT)
        
        assert result["success"]
        assert result["refund_amount"] == Decimal("90.00")
        mock_booking_service.cancel_booking.assert_called_once_with("REST-123")
    
    @pytest.mark.asyncio
    async def test_booking_modification(self, booking_agent, mock_booking_service):
        """Test booking modification."""
        mock_booking_service.modify_booking = AsyncMock(return_value={
            "success": True,
            "new_confirmation_code": "MOD123",
            "changes": {"time": "8:00 PM"}
        })
        
        modifications = {
            "time": "8:00 PM",
            "party_size": 5
        }
        
        result = await booking_agent.modify_booking("REST-123", modifications, BookingType.RESTAURANT)
        
        assert result["success"]
        assert result["new_confirmation_code"] == "MOD123"
        mock_booking_service.modify_booking.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_booking_recommendations(self, booking_agent, mock_booking_service):
        """Test getting booking recommendations."""
        criteria = {
            "location": {"lat": 37.7749, "lng": -122.4194},
            "cuisine": "italian",
            "price_range": "moderate",
            "party_size": 4
        }
        
        recommendations = await booking_agent.get_recommendations(
            BookingType.RESTAURANT,
            criteria
        )
        
        assert len(recommendations) > 0
        assert recommendations[0]["cuisine"] == "italian"
        mock_booking_service.get_recommendations.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_voice_command_processing(self, booking_agent, mock_user):
        """Test processing voice commands for bookings."""
        voice_commands = [
            {
                "text": "Book dinner for 4 at an Italian place tonight at 7",
                "expected_type": BookingType.RESTAURANT,
                "expected_details": {"party_size": 4, "time": "7:00 PM", "cuisine": "italian"}
            },
            {
                "text": "Get me 3 tickets to the museum",
                "expected_type": BookingType.ATTRACTION,
                "expected_details": {"total_tickets": 3, "attraction_type": "museum"}
            },
            {
                "text": "I need a hotel for tomorrow night",
                "expected_type": BookingType.HOTEL,
                "expected_details": {"nights": 1, "check_in": "tomorrow"}
            }
        ]
        
        for command in voice_commands:
            parsed = await booking_agent.process_voice_command(command["text"], mock_user)
            
            assert parsed["booking_type"] == command["expected_type"]
            for key, value in command["expected_details"].items():
                if key in parsed["details"]:
                    assert str(value).lower() in str(parsed["details"][key]).lower()
    
    @pytest.mark.asyncio
    async def test_booking_history_tracking(self, booking_agent, mock_user):
        """Test tracking of booking history."""
        # Create multiple bookings
        bookings = []
        for i in range(3):
            request = BookingRequest(
                user_id=mock_user.id,
                booking_type=BookingType.RESTAURANT,
                details={
                    "party_size": 2,
                    "time": f"{6+i}:00 PM",
                    "date": "2024-01-20"
                }
            )
            response = await booking_agent.process_booking(request)
            bookings.append(response)
        
        # Get booking history
        history = await booking_agent.get_user_booking_history(mock_user.id)
        
        assert len(history) >= 3
        # History should be sorted by date (most recent first)
        assert all(b.booking_id in [booking.booking_id for booking in bookings] for b in history[-3:])