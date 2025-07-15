"""
MVP Booking Flow Tests
Tests the booking functionality for restaurants and activities
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from backend.app.services.booking_agent import BookingAgent, BookingType
from backend.app.services.reservation_management_service import ReservationManagementService
from backend.app.models.user import User
from backend.app.models.booking import Booking


@pytest.mark.mvp
class TestMVPRestaurantBooking:
    """Test restaurant booking functionality"""
    
    @pytest.fixture
    def booking_agent(self):
        """Create booking agent with mocked dependencies"""
        mock_ai = Mock()
        mock_ai.generate_response = AsyncMock(return_value="I found some great restaurants for you!")
        mock_ai.generate_structured_response = AsyncMock(
            return_value={
                "type": "restaurant",
                "preferences": {"cuisine": "Italian", "price_range": 2},
                "party_size": 2,
                "desired_date": datetime.now().isoformat()
            }
        )
        agent = BookingAgent(mock_ai)
        agent.reservation_service = Mock(spec=ReservationManagementService)
        return agent
    
    @pytest.mark.asyncio
    async def test_restaurant_search(self, booking_agent):
        """Test: Search for restaurants based on preferences"""
        # Mock restaurant search results
        mock_restaurants = [
            {
                "id": "rest1",
                "name": "Luigi's Italian",
                "cuisine": "Italian",
                "rating": 4.5,
                "price_range": 2,
                "distance": 0.5,
                "available_times": ["6:00 PM", "7:00 PM", "8:00 PM"]
            },
            {
                "id": "rest2", 
                "name": "Mama's Kitchen",
                "cuisine": "Italian",
                "rating": 4.8,
                "price_range": 2,
                "distance": 1.2,
                "available_times": ["6:30 PM", "7:30 PM"]
            }
        ]
        
        booking_agent.reservation_service.search_restaurants = AsyncMock(
            return_value=mock_restaurants
        )
        
        # Execute search
        context = {
            "location": {"lat": 37.7749, "lng": -122.4194, "name": "San Francisco"}
        }
        user = Mock(spec=User)
        
        response = await booking_agent.process_booking_request(
            "Find me an Italian restaurant for tonight",
            context,
            user
        )
        
        # Verify
        assert response["status"] in ["success", "info"]
        assert "restaurants" in response or "recommendations" in response
        assert len(response.get("recommendations", [])) > 0 or "Italian" in response.get("message", "")
    
    @pytest.mark.asyncio
    async def test_restaurant_booking_confirmation(self, booking_agent):
        """Test: Confirm restaurant booking"""
        # Setup selected restaurant
        selected_restaurant = {
            "id": "rest1",
            "name": "Luigi's Italian",
            "time": "7:00 PM",
            "party_size": 2
        }
        
        # Mock booking confirmation
        booking_agent.reservation_service.create_reservation = AsyncMock(
            return_value={
                "confirmation_code": "ABC123",
                "status": "confirmed",
                "restaurant": selected_restaurant["name"],
                "time": selected_restaurant["time"]
            }
        )
        
        # Execute booking
        user = Mock(spec=User)
        user.id = "user123"
        
        response = await booking_agent.confirm_booking(
            BookingType.RESTAURANT,
            selected_restaurant,
            user
        )
        
        # Verify
        assert response["status"] == "success"
        assert "confirmation_code" in response
        assert response["confirmation_code"] == "ABC123"
    
    @pytest.mark.asyncio
    async def test_booking_history_check(self, booking_agent):
        """Test: Check user's booking history"""
        # Mock booking history
        mock_bookings = [
            {
                "id": "book1",
                "type": "restaurant",
                "vendor": "Luigi's Italian",
                "datetime": (datetime.now() + timedelta(hours=3)).isoformat(),
                "status": "confirmed",
                "confirmation_code": "ABC123"
            }
        ]
        
        # Mock database query
        booking_agent.db = AsyncMock()
        
        with patch('backend.app.services.booking_agent.select') as mock_select:
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = [
                Mock(
                    id="book1",
                    booking_type="restaurant",
                    vendor_name="Luigi's Italian",
                    booking_datetime=datetime.now() + timedelta(hours=3),
                    status="confirmed",
                    confirmation_code="ABC123",
                    booking_details={}
                )
            ]
            
            booking_agent.db().__aenter__.return_value.execute = AsyncMock(
                return_value=mock_result
            )
            
            # Check bookings
            user = Mock(spec=User)
            user.id = "user123"
            
            response = await booking_agent.check_existing_reservations(user, "upcoming")
            
            # Verify
            assert response["status"] == "success"
            assert len(response["reservations"]) == 1
            assert response["reservations"][0]["vendor"] == "Luigi's Italian"


@pytest.mark.mvp
class TestMVPActivityBooking:
    """Test activity and attraction booking"""
    
    @pytest.mark.asyncio
    async def test_activity_search(self):
        """Test: Search for activities near location"""
        mock_ai = Mock()
        agent = BookingAgent(mock_ai)
        
        # Mock activity search
        agent.ticketmaster_client = Mock()
        agent.ticketmaster_client.search_events = AsyncMock(
            return_value=[
                {
                    "id": "event1",
                    "name": "Golden Gate Park Concert",
                    "type": "concert",
                    "date": datetime.now() + timedelta(days=2),
                    "price": 45.00,
                    "venue": "Golden Gate Park",
                    "available": True
                }
            ]
        )
        
        agent.rec_gov_client = Mock()
        agent.rec_gov_client.search_activities = AsyncMock(return_value=[])
        
        # Search for activities
        context = {
            "location": {"lat": 37.7749, "lng": -122.4194}
        }
        user = Mock(spec=User)
        
        response = await agent._handle_activity_booking(
            {"activity_type": "concert"},
            context,
            user
        )
        
        # Verify
        assert response["status"] in ["success", "info"]
        if response["status"] == "success":
            assert len(response["recommendations"]) > 0
            assert response["recommendations"][0]["name"] == "Golden Gate Park Concert"
    
    @pytest.mark.asyncio
    async def test_outdoor_activity_booking(self):
        """Test: Book outdoor activities through Recreation.gov"""
        mock_ai = Mock()
        agent = BookingAgent(mock_ai)
        
        # Mock campsite search
        agent.rec_gov_client = Mock()
        agent.rec_gov_client.search_activities = AsyncMock(
            return_value=[
                {
                    "id": "camp1",
                    "name": "Yosemite Valley Campground",
                    "type": "camping",
                    "available_dates": ["2024-07-15", "2024-07-16"],
                    "price": 35.00,
                    "amenities": ["restrooms", "fire_pit", "picnic_table"]
                }
            ]
        )
        
        agent.ticketmaster_client = Mock()
        agent.ticketmaster_client.search_events = AsyncMock(return_value=[])
        
        # Search for camping
        response = await agent._handle_activity_booking(
            {"activity_type": "camping", "date": "2024-07-15"},
            {"location": {"lat": 37.8651, "lng": -119.5383}},
            Mock(spec=User)
        )
        
        # Verify
        assert response["status"] in ["success", "info"]
        if response["status"] == "success":
            assert any("Yosemite" in str(rec) for rec in response["recommendations"])


@pytest.mark.mvp
class TestMVPBookingIntegration:
    """Test booking integration with other services"""
    
    @pytest.mark.asyncio
    async def test_booking_with_story_context(self):
        """Test: Booking suggestions based on story context"""
        # Setup
        mock_ai = Mock()
        mock_ai.generate_response = AsyncMock(
            return_value="Since you're visiting the Golden Gate Bridge, you might enjoy dining at a restaurant with a view!"
        )
        
        agent = BookingAgent(mock_ai)
        
        # Context includes story elements
        context = {
            "location": {
                "name": "Golden Gate Bridge",
                "lat": 37.8199,
                "lng": -122.4783
            },
            "current_story_theme": "bridges",
            "time_of_day": "sunset"
        }
        
        user = Mock(spec=User)
        
        # Process request
        response = await agent.suggest_proactive_bookings(context, user)
        
        # Verify contextual suggestions
        assert response is not None
        if response:
            assert response["type"] in ["restaurant", "activity"]
            assert "message" in response
    
    @pytest.mark.asyncio
    async def test_commission_tracking(self):
        """Test: Track commissions for bookings"""
        from backend.app.services.commission_service import CommissionService
        
        commission_service = CommissionService()
        
        # Record a booking
        booking_data = {
            "provider": "opentable",
            "booking_id": "book123",
            "amount": 150.00,
            "commission_rate": 0.10,
            "user_id": "user123"
        }
        
        commission = await commission_service.record_commission(booking_data)
        
        # Verify commission calculation
        assert commission["amount"] == 15.00  # 10% of $150
        assert commission["status"] == "pending"
        assert commission["provider"] == "opentable"
    
    @pytest.mark.asyncio
    async def test_booking_error_handling(self):
        """Test: Handle booking failures gracefully"""
        mock_ai = Mock()
        agent = BookingAgent(mock_ai)
        
        # Mock failing reservation service
        agent.reservation_service = Mock()
        agent.reservation_service.create_reservation = AsyncMock(
            side_effect=Exception("Restaurant API unavailable")
        )
        
        # Attempt booking
        user = Mock(spec=User)
        
        response = await agent.confirm_booking(
            BookingType.RESTAURANT,
            {"id": "rest1", "name": "Test Restaurant"},
            user
        )
        
        # Verify graceful failure
        assert response["status"] == "error"
        assert "couldn't complete" in response["message"].lower()
        assert response.get("fallback") is True


@pytest.mark.mvp
class TestMVPBookingNotifications:
    """Test booking notifications and reminders"""
    
    @pytest.mark.asyncio
    async def test_booking_confirmation_notification(self):
        """Test: Send booking confirmation"""
        from backend.app.services.notification_service import NotificationService
        
        notification_service = NotificationService()
        notification_service.send_notification = AsyncMock(return_value=True)
        
        # Send confirmation
        booking = {
            "type": "restaurant",
            "vendor": "Luigi's Italian",
            "time": "7:00 PM",
            "confirmation_code": "ABC123"
        }
        
        result = await notification_service.send_booking_confirmation(
            "user123",
            booking
        )
        
        # Verify notification sent
        assert result is True
        notification_service.send_notification.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_booking_reminder(self):
        """Test: Send booking reminder before reservation"""
        from backend.app.services.notification_service import NotificationService
        
        notification_service = NotificationService()
        
        # Mock upcoming booking
        booking = Mock(
            booking_type="restaurant",
            vendor_name="Luigi's Italian",
            booking_datetime=datetime.now() + timedelta(hours=2),
            user_id="user123"
        )
        
        # Check if reminder should be sent
        should_remind = notification_service.should_send_reminder(booking)
        
        # 2 hours before is a good time for reminder
        assert should_remind is True


@pytest.mark.mvp
class TestMVPBookingCancellation:
    """Test booking cancellation flow"""
    
    @pytest.mark.asyncio
    async def test_cancel_restaurant_booking(self):
        """Test: Cancel restaurant reservation"""
        mock_ai = Mock()
        agent = BookingAgent(mock_ai)
        
        # Mock cancellation
        agent.reservation_service = Mock()
        agent.reservation_service.cancel_reservation = AsyncMock(
            return_value={
                "status": "cancelled",
                "confirmation": "CANCEL123",
                "refund": "Full refund processed"
            }
        )
        
        # Cancel booking
        user = Mock(spec=User)
        user.id = "user123"
        
        response = await agent.cancel_booking("book123", user)
        
        # Verify
        assert response["status"] == "cancelled"
        assert "refund" in response
        assert response["confirmation"] == "CANCEL123"